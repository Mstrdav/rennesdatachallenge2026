from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
import torch
import logging
from tqdm import tqdm

class LLMRefiner:
    def __init__(self, model_name: str = "HuggingFaceTB/SmolLM2-1.7B-Instruct"):
        """
        Initialise le modèle LLM pour le raffinement de texte.
        Supporte les modèles CausalLM (comme GPT, Llama) et Seq2Seq (comme T5).
        """
        self.logger = logging.getLogger('Bilan Carbone CHU')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Chargement du modèle LLM {model_name} sur {self.device}...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Essayer de déterminer le type de modèle (Causal ou Seq2Seq)
            # Une heuristique simple : si "t5" ou "bart" dans le nom -> Seq2Seq, sinon Causal
            if any(x in model_name.lower() for x in ["t5", "bart"]):
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
                self.is_seq2seq = True
            else:
                self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
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

    def refine_batch(self, texts: list[str], batch_size: int = 8) -> list[str]:
        """
        Raffine une liste de textes en utilisant le LLM.
        """
        refined_texts = []
        
        prompt_template = "Transforme la description de produit suivante en une phrase courte, claire et sans ambiguïté (en français) : '{}'. Réponse :"
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Raffinement LLM", unit="batch"):
            batch_texts = texts[i:i + batch_size]
            
            prompts = [prompt_template.format(t) for t in batch_texts]
            
            try:
                inputs = self.tokenizer(prompts, padding=True, truncation=True, return_tensors="pt", max_length=512).to(self.device)
                
                with torch.no_grad():
                    # Paramètres de génération conservateurs pour la rapidité et la clarté
                    outputs = self.model.generate(
                        **inputs, 
                        max_new_tokens=50, 
                        do_sample=False, # Déterministe
                        num_return_sequences=1,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                decoded = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
                
                # Post-processing pour extraire la réponse
                batch_refined = []
                for j, raw_output in enumerate(decoded):
                    # Si CausalLM, le prompt est inclus dans la sortie, il faut l'enlever
                    if not self.is_seq2seq:
                         # On cherche la séparation si possible, sinon on prend tout (souvent le modèle ne répète pas exactement le prompt si bien tuné pour instruct, mais SmolLM/Llama le font souvent)
                         # Une méthode simple est de retirer le prompt exact
                         prompt_len = len(prompts[j])
                         # Attention, la tokenisation/détokenisation peut altérer légèrement les espaces
                         # On va plutôt splitter sur "Réponse :" si présent
                         if "Réponse :" in raw_output:
                             cleaned = raw_output.split("Réponse :")[-1].strip()
                         elif prompt_template.format("").split(" :")[0] in raw_output: # Partie statique du prompt
                             # Fallback simple
                             cleaned = raw_output[len(prompts[j]):].strip()
                         else:
                             cleaned = raw_output
                    else:
                        cleaned = raw_output.strip()
                        
                    batch_refined.append(cleaned)
                    
                refined_texts.extend(batch_refined)
                
            except Exception as e:
                self.logger.error(f"Erreur lors du raffinement du lot {i // batch_size}: {e}")
                refined_texts.extend(batch_texts) # Fallback sur l'original en cas d'erreur
                
        return refined_texts
