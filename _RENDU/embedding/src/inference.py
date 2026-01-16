from transformers import AutoTokenizer, AutoModel
import torch
import logging

from tqdm import tqdm

class EmbeddingModel:
    def __init__(self, model_name: str = "Dr-BERT/DrBERT-4GB"):
        """
        Initialiser le modèle d'embedding.
        """
        self.logger = logging.getLogger('Bilan Carbone CHU')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Chargement du modèle {model_name} sur {self.device}...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
            self.logger.info("Modèle chargé avec succès.")
        except Exception as e:
            self.logger.error(f"Échec du chargement du modèle: {e}")
            raise

    def get_embeddings(self, texts: list[str], batch_size: int = 32):
        """
        Générer des embeddings pour une liste de textes.
        """
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Génération des embeddings", unit="batch"):
            batch_texts = texts[i:i + batch_size]
            
            try:
                inputs = self.tokenizer(batch_texts, padding=True, truncation=True, return_tensors="pt", max_length=512).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    # Utiliser l'embedding du token CLS (premier token)
                    cls_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                    
                all_embeddings.extend(cls_embeddings)
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement du lot {i // batch_size}: {e}")
                # Selon les besoins, on pourrait sauter ou ajouter des zéros, ou relancer l'exception
                # Pour l'instant, on relance pour garantir l'intégrité
                raise

        return all_embeddings
