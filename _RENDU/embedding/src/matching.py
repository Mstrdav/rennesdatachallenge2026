import numpy as np
import faiss
from sklearn.metrics.pairwise import cosine_similarity
import logging

class Matcher:
    def __init__(self, use_faiss: bool = True):
        self.logger = logging.getLogger('Bilan Carbone CHU')
        self.use_faiss = use_faiss
        self.index = None
        self.target_embeddings = None

    def fit(self, target_embeddings: np.ndarray):
        """
        Adapter le matcher avec les embeddings cibles (ex: bibliothèque Ademe).
        """
        self.target_embeddings = np.array(target_embeddings).astype('float32')
        
        if self.use_faiss:
            self.logger.info("Construction de l'index FAISS...")
            dimension = self.target_embeddings.shape[1]
            # Normaliser pour la similarité cosinus (Normalisation L2 + Produit Scalaire)
            faiss.normalize_L2(self.target_embeddings)
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(self.target_embeddings)
            self.logger.info(f"Index FAISS construit avec {self.index.ntotal} vecteurs.")
        else:
            self.logger.info("Utilisation de la similarité cosinus Scikit-Learn (pas d'index).")

    def match(self, source_embeddings: np.ndarray, k: int = 1):
        """
        Trouver les top-k correspondances pour les embeddings source.
        
        Returns:
            distances (np.ndarray): Scores de similarité.
            indices (np.ndarray): Indices des voisins les plus proches dans target_embeddings.
        """
        source_embeddings = np.array(source_embeddings).astype('float32')
        
        if self.use_faiss:
            faiss.normalize_L2(source_embeddings)
            distances, indices = self.index.search(source_embeddings, k)
            return distances, indices
        else:
            # Similarité cosinus utilisant sklearn
            # Calculer la matrice de similarité de toutes les paires (peut être lourd pour de grands jeux de données)
            sim_matrix = cosine_similarity(source_embeddings, self.target_embeddings)
            # Trouver les top k
            indices = np.argsort(-sim_matrix, axis=1)[:, :k]
            distances = -np.sort(-sim_matrix, axis=1)[:, :k] # Obtenir les valeurs
            return distances, indices
