import sys
import os
import pandas as pd
import logging

# Ajouter le répertoire courant au chemin pour permettre l'importation depuis src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, load_data, save_results
from src.preprocess import TextPreprocessor
from src.inference import EmbeddingModel
from src.matching import Matcher

def main():
    logger = setup_logger()
    logger.info("Début du traitement (embedding)")
    
    SOURCE_FILE = "../DATA/RAW/PRODUITS.xlsx"
    TARGET_FILE = "../DATA/RAW/FE_ADEME.xlsx" # Le fichier Ademe
    OUTPUT_FILE = "../DATA/PROCESSED/MATCHES.xlsx"
    COLUMNS_SOURCE = ["DB.LIB", "COMPTE.LIB"]
    COLUMNS_TARGET = ["FE.LIB1", "FE.LIB3"]
    
    try:
        if os.path.exists(SOURCE_FILE) and os.path.exists(TARGET_FILE):
             logger.info("Chargement des données réelles...")
             df_source = load_data(SOURCE_FILE)
             df_target = load_data(TARGET_FILE)
             
             # Combiner plusieurs colonnes en une seule chaîne
             # fillna('') est utilisé pour gérer les valeurs NaN potentielles en les remplaçant par des chaînes vides
             source_texts = df_source[COLUMNS_SOURCE].fillna('').astype(str).agg(' '.join, axis=1).tolist()
             target_texts = df_target[COLUMNS_TARGET].fillna('').astype(str).agg(' '.join, axis=1).tolist()
        else:
             logger.error("Fichiers sources non trouvés. Arrêt du traitement.")
             return

        # Prétraitement des textes
        logger.info("Prétraitement des textes...")
        preprocessor = TextPreprocessor()
        clean_source = preprocessor.preprocess_batch(source_texts)
        clean_target = preprocessor.preprocess_batch(target_texts)
        
        # Génération des embeddings
        logger.info("Génération des embeddings...")
        model = EmbeddingModel()
        source_embeddings = model.get_embeddings(clean_source)
        target_embeddings = model.get_embeddings(clean_target)
        
        # Matching
        matcher = Matcher(use_faiss=True) # Définir use_faiss=False si problèmes avec FAISS
        matcher.fit(target_embeddings)
        distances, indices = matcher.match(source_embeddings, k=1)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances, indices)):
            match_idx = idx[0]
            similarity_score = dist[0]
            
            results.append({
                "source_text": source_texts[i],
                "matched_target_text": target_texts[match_idx],
                "similarity_score": similarity_score,
                "target_index": match_idx
            })
            
        df_results = pd.DataFrame(results)
        print("\n--- Top Matches ---")
        print(df_results.head())
        
        # 6. Sauvegarde
        save_results(df_results, OUTPUT_FILE)
        logger.info("Fichier de résultats enregistré.")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement: {e}")
        # raise e # Décommenter pour déboguer

if __name__ == "__main__":
    main()
