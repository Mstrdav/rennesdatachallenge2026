import sys
import os
import pandas as pd
import logging
import argparse

# Ajouter le répertoire courant au chemin pour permettre l'importation depuis src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, load_data, save_results
from src.preprocess import TextPreprocessor
from src.inference import EmbeddingModel
from src.matching import Matcher

def main():
    # Parsing des arguments
    parser = argparse.ArgumentParser(description="Application de matching de produits pour le Bilan Carbone")
    parser.add_argument("-p", "--preprocess-only", action="store_true", help="Exécuter uniquement le prétraitement et quitter")
    parser.add_argument("-f", "--force", action="store_true", help="Forcer le prétraitement même si les fichiers existent")
    parser.add_argument("-m", "--model", type=str, default="sentence-transformers/all-mpnet-base-v2", help="Nom du modèle HuggingFace à utiliser (défaut: sentence-transformers/all-mpnet-base-v2)")
    parser.add_argument("--llm-refine", action="store_true", help="Activer le raffinement du texte par LLM")
    parser.add_argument("--llm-model", type=str, default="Qwen/Qwen2.5-3B-Instruct", help="Nom du modèle LLM pour le raffinement (défaut: Qwen/Qwen2.5-0.5B-Instruct)")
    parser.add_argument("--batch-size", type=int, default=32, help="Taille du batch pour le LLM (défaut: 32). Augmenter pour plus de vitesse si GPU le permet.")
    parser.add_argument("--alpha", type=float, default=0.5, help="Poids de la recherche dense vs BM25 (0.5 = équilibré, 1.0 = Dense uniquement, 0.0 = BM25 uniquement)")
    args = parser.parse_args()

    logger = setup_logger()
    logger.info("Début du traitement (embedding)")
    
    SOURCE_FILE = "../DATA/RAW/PRODUITS.xlsx"
    TARGET_FILE = "../DATA/RAW/FE_ADEME.xlsx"
    
    # Modifier les noms de fichiers si LLM est utilisé pour éviter la confusion ou l'écrasement involontaire
    if args.llm_refine:
        PROCESSED_SOURCE = "../DATA/PROCESSED/source_processed_llm.csv"
        PROCESSED_TARGET = "../DATA/PROCESSED/target_processed_llm.csv"
    else:
        PROCESSED_SOURCE = "../DATA/PROCESSED/source_processed.csv"
        PROCESSED_TARGET = "../DATA/PROCESSED/target_processed.csv"
    
    OUTPUT_FILE = "../DATA/PROCESSED/MATCHES.xlsx"
    
    COLUMNS_SOURCE = ["DB.LIB", "COMPTE.LIB"]
    COLUMNS_TARGET = ["FE.LIB2", "FE.LIB3"]
    SOURCE_KEEP = ["PRODUIT.ID"]
    TARGET_KEEP = ["FE.ADEME.ID", "FE.VAL", "FE.Incertitude"] # Colonnes à garder dans le fichier preprocessed
    
    preprocessor = TextPreprocessor()
    
    # 1. Étape de Prétraitement
    files_exist = os.path.exists(PROCESSED_SOURCE) and os.path.exists(PROCESSED_TARGET)
    do_preprocess = args.force or args.preprocess_only or not files_exist
    
    # Vérification de l'intégrité des fichiers existants (colonnes manquantes ?)
    if files_exist and not do_preprocess:
        try:
            df_s = pd.read_csv(PROCESSED_SOURCE, nrows=5)
            df_t = pd.read_csv(PROCESSED_TARGET, nrows=5)
            # On vérifie text + les colonnes ID
            req_s = ["text"] + SOURCE_KEEP
            req_t = ["text"] + TARGET_KEEP
            if not all(col in df_s.columns for col in req_s) or not all(col in df_t.columns for col in req_t):
                logger.warning("Fichiers prétraités incomplets (colonnes manquantes). On force le prétraitement.")
                do_preprocess = True
        except Exception:
             logger.warning("Fichiers prétraités illisibles. On force le prétraitement.")
             do_preprocess = True
    
    if do_preprocess:
        logger.info("Lancement du prétraitement...")
        if os.path.exists(SOURCE_FILE) and os.path.exists(TARGET_FILE):
             try:
                # Appel avec arguments LLM
                # Appel avec arguments LLM pour la SOURCE uniquement
                preprocessor.process_and_save(SOURCE_FILE, PROCESSED_SOURCE, COLUMNS_SOURCE, SOURCE_KEEP, use_llm=args.llm_refine, llm_model_name=args.llm_model, batch_size=args.batch_size)
                # JAMAIS de LLM pour la TARGET (Ademe = référence)
                preprocessor.process_and_save(TARGET_FILE, PROCESSED_TARGET, COLUMNS_TARGET, TARGET_KEEP, use_llm=False, llm_model_name=None, batch_size=args.batch_size)
                logger.info("Prétraitement terminé avec succès.")
             except Exception as e:
                logger.error(f"Erreur durant le prétraitement : {e}")
                return
        else:
             logger.error("Fichiers sources RAW non trouvés. Impossible de prétraiter.")
             return
    else:
        logger.info("Les fichiers prétraités existent déjà, on saute l'étape de prétraitement (utiliser -f pour forcer).")

    # Si on voulait juste prétraiter, on s'arrête là
    if args.preprocess_only:
        logger.info("Mode 'Preprocess Only' activé. Fin du programme.")
        return

    # 2. Étape d'Embedding et Matching
    try:
        # Chargement des données traitées
        logger.info("Chargement des données prétraitées...")
        if not (os.path.exists(PROCESSED_SOURCE) and os.path.exists(PROCESSED_TARGET)):
            logger.error("Fichiers prétraités manquants pour l'étape suivante.")
            return

        # On charge avec pd.read_csv. On s'attend à une colonne 'text'
        df_source_proc = pd.read_csv(PROCESSED_SOURCE)
        df_target_proc = pd.read_csv(PROCESSED_TARGET)
        
        # Gestion des valeurs NaN
        # Gestion des valeurs NaN
        source_texts = df_source_proc['text'].fillna('').astype(str).tolist()
        # Récupération des versions raw si disponibles (sinon fallback sur text)
        source_texts_raw = df_source_proc['text_raw'].fillna('').astype(str).tolist() if 'text_raw' in df_source_proc.columns else source_texts
        
        target_texts = df_target_proc['text'].fillna('').astype(str).tolist()
        target_texts = df_target_proc['text'].fillna('').astype(str).tolist()
        
        # Génération des embeddings
        logger.info(f"Génération des embeddings avec le modèle : {args.model}...")
        model = EmbeddingModel(model_name=args.model)
        source_embeddings = model.get_embeddings(source_texts)
        target_embeddings = model.get_embeddings(target_texts)
        
        # Matching
        logger.info(f"Matching hybride (Alpha={args.alpha})...")
        matcher = Matcher(use_faiss=True, alpha=args.alpha)
        # On passe les textes cibles pour l'indexation BM25
        matcher.fit(target_embeddings, target_texts=target_texts)
        # On passe les textes sources pour le scoring BM25
        distances, indices = matcher.match(source_embeddings, source_texts=source_texts, k=1)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances, indices)):
            match_idx = idx[0]
            similarity_score = dist[0]
            
            # construction du fichier sortie :
            # id source, text source, id target, text target, score
            # trié par score décroissant
            results.append({
                "id_source": df_source_proc.iloc[i]["PRODUIT.ID"],
                "text_source_raw": source_texts_raw[i],
                "text_source_refined": source_texts[i],
                "id_target": df_target_proc.iloc[match_idx]["FE.ADEME.ID"],
                "text_target": target_texts[match_idx],
                "score": similarity_score
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        df_results = pd.DataFrame(results)
        print("\n--- Top Matches ---")
        print(df_results.head())
        
        # Sauvegarde
        save_results(df_results, OUTPUT_FILE)
        logger.info("Fichier de résultats enregistré.")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement: {e}")
        # raise e 

if __name__ == "__main__":
    main()
