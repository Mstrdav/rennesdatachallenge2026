import pandas as pd
import os
import json
import logging

def load_data(file_path: str, file_type: str = None) -> pd.DataFrame:
    """
    Charger des données depuis un fichier CSV ou Excel.
    
    Args:
        file_path (str): Chemin vers le fichier.
        file_type (str): 'csv' ou 'excel'. Si None, déduit de l'extension.
        
    Returns:
        pd.DataFrame: Données chargées.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
        
    try:
        if file_type is None:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                file_type = 'excel'
            else:
                file_type = 'csv'

        if file_type == 'csv':
            return pd.read_csv(file_path)
        elif file_type == 'excel':
            return pd.read_excel(file_path)
        else:
            raise ValueError("Type de fichier non supporté")
    except Exception as e:
        logging.error(f"Erreur lors du chargement des données: {e}")
        raise

def save_results(df: pd.DataFrame, output_path: str):
    """
    Sauvegarder les résultats dans un fichier CSV.
    
    Args:
        df (pd.DataFrame): Données à sauvegarder.
        output_path (str): Chemin pour sauvegarder le fichier.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    logging.info(f"Résultats sauvegardés dans {output_path}")

def setup_logger(name: str = 'Bilan Carbone CHU', log_file: str = 'app.log', level=logging.INFO):
    """
    Petit logger ! pour que ce soit joli hehehe
    """
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
    
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger
