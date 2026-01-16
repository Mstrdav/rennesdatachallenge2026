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

# Tentative d'import optionnel pour éviter les erreurs si dependencies manquantes (même si user a demandé)
try:
    from src.llm_utils import LLMRefiner
except ImportError:
    LLMRefiner = None

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

    def process_and_save(self, input_file: str, output_file: str, columns: list[str], keep: list[str], use_llm: bool = False, llm_model_name: str = None, batch_size: int = 8):
        """
        Pretraitement des données, pour ne garder que les colonnes interessantes (dans le target) et nettoyer les textes.
        Optionally refine with LLM.
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
            
            # 1. Nettoyage initial (toujours effectué en premier maintenant)
            # Cela permet de réduire la variabilité avant le LLM et de réduire la taille des inputs.
            logger.info("Début du nettoyage textuel de base...")
            clean_texts = self.preprocess_batch(raw_texts)
            
            if use_llm:
                if LLMRefiner is None:
                    logger.error("LLMRefiner n'a pas pu être importé. Passage en mode classique.")
                    final_texts = clean_texts
                else:
                    logger.info(f"Raffinement par LLM activé avec le modèle {llm_model_name} (Batch: {batch_size})...")
                    
                    # Optimisation majeure : Déduplication avant LLM
                    # On ne traite que les textes uniques pour éviter de recalculer 1000 fois la même description
                    unique_texts = list(set(clean_texts))
                    logger.info(f"Nombre de textes uniques à raffiner : {len(unique_texts)} / {len(clean_texts)} total")
                    
                    refiner = LLMRefiner(model_name=llm_model_name)
                    refined_uniques = refiner.refine_batch(unique_texts, batch_size=batch_size)
                    
                    # Création d'un mapping {original_clean: refined}
                    mapping = dict(zip(unique_texts, refined_uniques))
                    
                    # On réapplique le mapping à toute la liste
                    # On refait peut-être un passage de clean_text sur le résultat du LLM pour être sûr (formatage uniforme)
                    # Mais attention, si le LLM sort des phrases bien formées, clean_text (qui vire les accents) peut être destructeur si on voulait garder le sens riche.
                    # Cependant, pour le matching embedding actuel, on semble vouloir du texte "plat" (sans accents, minuscules).
                    # Le user a demandé de "transformer toutes les descriptions en courtes phrases claires".
                    # Si on re-nettoie trop agressivement derrière, on perd peut-être l'intérêt de la grammaire du LLM.
                    # MAIS, le pipeline de matching s'attend probablement à du texte normalisé.
                    # On va appliquer un nettoyage léger (minuscule) sur la sortie LLM, ou réutiliser clean_text si cohérent.
                    # Pour l'instant, appliquons simplement le mapping.
                    
                    refined_full_list = [mapping[t] for t in clean_texts]
                    
                    # Optionnel: Re-clean le résultat du LLM pour enlever potentielles hallucinations de format
                    final_texts = self.preprocess_batch(refined_full_list)
            else:
                final_texts = clean_texts

            # Ajout des colonnes du target
            df_out = pd.DataFrame({'text': final_texts})
            df_out[keep] = df[keep]

            # suppression de lignes qui ont le meme id ou texte
            if output_file.endswith("target_processed_llm.csv") or output_file.endswith("target_processed.csv"):
                 df_out = df_out.drop_duplicates(subset='text', keep='first')
            elif output_file.endswith("source_processed_llm.csv") or output_file.endswith("source_processed.csv"):
                 df_out = df_out.drop_duplicates(subset='text', keep='first')
            
            # Sauvegarde
            save_results(df_out, output_file)
            
        except Exception as e:
            logger.error(f"Erreur lors du preprocessing de {input_file}: {e}")
            raise
