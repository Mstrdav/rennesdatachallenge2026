import json
import os
import hashlib
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
import torch
import logging
from tqdm import tqdm

class LLMRefiner:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-0.5B-Instruct", cache_file: str = "llm_cache.json"):
        """
        Initialise le modèle LLM pour le raffinement de texte.
        Supporte les modèles CausalLM (comme GPT, Llama) et Seq2Seq (comme T5).
        """
        self.logger = logging.getLogger('Bilan Carbone CHU')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cache_file = cache_file
        self.cache = self._load_cache()
        
        self.logger.info(f"Chargement du modèle LLM {model_name} sur {self.device}...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Optimisation : Utilisation de float16 si GPU disponible
            dtype = torch.float16 if self.device.type == 'cuda' else torch.float32
            
            # Essayer de déterminer le type de modèle (Causal ou Seq2Seq)
            if any(x in model_name.lower() for x in ["t5", "bart"]):
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=dtype).to(self.device)
                self.is_seq2seq = True
            else:
                self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype).to(self.device)
                self.is_seq2seq = False
                # IMPORTANT pour CausalLM : left padding pour la génération par batch
                self.tokenizer.padding_side = 'left'
                
            # S'assurer qu'un pad_token est défini
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model.eval()
            self.logger.info("Modèle LLM chargé avec succès.")
            
        except Exception as e:
            self.logger.error(f"Échec du chargement du modèle LLM: {e}")
            raise

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Impossible de charger le cache: {e}. Nouveau cache créé.")
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde du cache: {e}")

    def refine_batch(self, texts: list[str], batch_size: int = 8) -> list[str]:
        """
        Raffine une liste de textes en utilisant le LLM.
        """
        refined_texts = []
        texts_to_process = []
        indices_to_process = []
        
        # Vérification du cache
        for i, text in enumerate(texts):
            # Utiliser le texte comme clé (attention si très long)
            if text in self.cache:
                refined_texts.append(self.cache[text])
            else:
                refined_texts.append(None) # Placeholder
                texts_to_process.append(text)
                indices_to_process.append(i)
        
        if not texts_to_process:
            self.logger.info("Tous les textes sont déjà en cache.")
            return refined_texts

        prompt_template = "Transforme la description de produit suivante en une phrase courte, claire et sans ambiguïté (en français) : '{}'. Réponse :"
        
        self.logger.info(f"Traitement de {len(texts_to_process)} textes (Batch size: {batch_size})...")
        
        for i in tqdm(range(0, len(texts_to_process), batch_size), desc="Raffinement LLM", unit="batch"):
            batch_texts = texts_to_process[i:i + batch_size]
            batch_indices = indices_to_process[i:i + batch_size]
            
            prompts = [prompt_template.format(t) for t in batch_texts]
            
            try:
                inputs = self.tokenizer(prompts, padding=True, truncation=True, return_tensors="pt", max_length=512).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs, 
                        max_new_tokens=50, 
                        do_sample=False, 
                        num_return_sequences=1,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                decoded = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
                
                # Post-processing
                for j, raw_output in enumerate(decoded):
                    if not self.is_seq2seq:
                         if "Réponse :" in raw_output:
                             cleaned = raw_output.split("Réponse :")[-1].strip()
                         elif prompt_template.format("").split(" :")[0] in raw_output:
                             cleaned = raw_output[len(prompts[j]):].strip()
                         else:
                             cleaned = raw_output
                    else:
                        cleaned = raw_output.strip()
                    
                    original_text = batch_texts[j]
                    original_index = batch_indices[j]
                    
                    # Mise à jour resultats et cache
                    refined_texts[original_index] = cleaned
                    self.cache[original_text] = cleaned
                
                # Sauvegarde périodique du cache (tous les 10 batches pour ne pas ralentir trop)
                if (i // batch_size) % 10 == 0:
                     self._save_cache()
                     
            except Exception as e:
                self.logger.error(f"Erreur lors du raffinement du lot {i // batch_size}: {e}")
                # Fallback pour ce lot
                for j, idx in enumerate(batch_indices):
                     refined_texts[idx] = batch_texts[j]
        
        # Sauvegarde finale
        self._save_cache()
                
        return refined_texts
