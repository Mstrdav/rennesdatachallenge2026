import re
import unicodedata
import pandas as pd
import logging
import sys
import os

# Add src to path if needed or just relative import if package structure allows
# Assuming running from root (app.py), but relative imports inside src might need care
# Using absolute imports based on app.py structure
from src.utils import load_data, save_results

class TextPreprocessor:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        """
        Nettoyer le texte : minuscules, sans accents, sans chiffres, sans caractères spéciaux.
        """
        if not isinstance(text, str):
            return ""
            
        # Minuscules
        text = text.lower()
        
        # Supprimer les accents
        text = str(unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8"))
        
        # Supprimer les chiffres (ajout demandé)
        text = re.sub(r'\d+', ' ', text)
        
        # Supprimer les caractères spéciaux et les espaces supplémentaires
        text = re.sub(r'[^a-z\s]', ' ', text) # Retrait de 0-9 du regex
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def preprocess_batch(self, texts: list[str]) -> list[str]:
        """
        Prétraiter une liste de textes.
        """
        return [self.clean_text(t) for t in texts]

    def process_and_save(self, input_file: str, output_file: str, columns: list[str], target_keep: list[str] = []):
        """
        Pretraitement des données, pour ne garder que les colonnes interessantes (dans le target) et nettoyer les textes.
        """
        logger = logging.getLogger('Bilan Carbone CHU')
        logger.info(f"Traitement de {input_file} -> {output_file}")
        
        try:
            df = load_data(input_file)
            
            # Vérifier les colonnes
            missing_cols = [c for c in columns if c not in df.columns]
            if missing_cols:
                logger.warning(f"Colonnes manquantes dans {input_file}: {missing_cols}. Elles seront ignorées.")
                valid_cols = [c for c in columns if c in df.columns]
            else:
                valid_cols = columns
                
            if not valid_cols:
                logger.error("Aucune colonne valide trouvée.")
                return 

            # Concaténation
            raw_texts = df[valid_cols].fillna('').astype(str).agg(' '.join, axis=1).tolist()
            
            # Nettoyage
            clean_texts = self.preprocess_batch(raw_texts)

            # Ajout des colonnes du target
            df_out = pd.DataFrame({'text': clean_texts})
            df_out[target_keep] = df[target_keep]

            # suppression de lignes qui ont le meme text, en mettant dans les colonnes du target les valeurs de la ligne supprimée
            if target_keep:
                df_out = df_out.drop_duplicates(subset='text', keep='first')
            
            # Sauvegarde
            save_results(df_out, output_file)
            
        except Exception as e:
            logger.error(f"Erreur lors du preprocessing de {input_file}: {e}")
            raise
