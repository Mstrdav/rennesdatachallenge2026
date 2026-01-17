import numpy as np
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import minmax_scale
import logging
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

class Matcher:
    def __init__(self, use_faiss: bool = True, alpha: float = 0.5):
        self.logger = logging.getLogger('Bilan Carbone CHU')
        self.use_faiss = use_faiss
        self.alpha = alpha # Poids du Dense (0.5 = équilibré)
        self.index = None
        self.target_embeddings = None
        self.bm25 = None
        self.target_texts = None

    def fit(self, target_embeddings: np.ndarray, target_texts: list[str] = None):
        """
        Adapter le matcher avec les embeddings cibles et les textes pour BM25.
        """
        self.target_embeddings = np.array(target_embeddings).astype('float32')
        self.target_texts = target_texts
        
        # 1. Construction Index Dense
        if self.use_faiss:
            self.logger.info("Construction de l'index FAISS...")
            dimension = self.target_embeddings.shape[1]
            faiss.normalize_L2(self.target_embeddings)
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(self.target_embeddings)
            self.logger.info(f"Index FAISS construit avec {self.index.ntotal} vecteurs.")
        else:
            self.logger.info("Utilisation de la similarité cosinus Scikit-Learn.")

        # 2. Construction Index Sparse (BM25)
        if target_texts and BM25Okapi:
            self.logger.info("Construction de l'index BM25...")
            # Tokenisation simple pour l'exemple (split espace)
            tokenized_corpus = [doc.lower().split() for doc in target_texts]
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.logger.info("Index BM25 construit.")
        elif target_texts and not BM25Okapi:
            self.logger.warning("rank_bm25 non installé. Hybrid Search désactivé (Dense uniquement).")

    def match(self, source_embeddings: np.ndarray, source_texts: list[str] = None, k: int = 1):
        """
        Trouver les top-k correspondances en combinant Dense et Sparse.
        """
        source_embeddings = np.array(source_embeddings).astype('float32')
        num_queries = len(source_embeddings)
        num_targets = len(self.target_embeddings)
        
        # --- A. Score Dense (Cosinus) ---
        if self.use_faiss:
            faiss.normalize_L2(source_embeddings)
            # FAISS search renvoie les distances et indices des top-k. 
            # Pour hybride, on a besoin de TOUS les scores ou au moins d'un large top-k pour rerank.
            # Ici, pour faire simple et précis, on va calculer la matrice complète avec FAISS ou numpy si pas trop gros.
            # MAIS FAISS est fait pour le top-k.
            # Astuce: On demande un k plus grand (ex: 50 ou 100) à FAISS pour filtrer, puis on rerank avec BM25 sur ce sous-ensemble.
            # OU on fait tout en numpy si dataset < 100k.
            
            # Approche Exacte hybride : on calcule tout (peut être lourd)
            # Approche "Rerank" : On prend Top-50 Dense, et on ajoute le score BM25.
            
            # Faisons simple : Si la target est petite (< 10000), on calcule tout.
            if num_targets < 10000:
                # Produit scalaire global (car normalisé L2 = Cosinus)
                dense_scores = np.dot(source_embeddings, self.target_embeddings.T)
            else:
                 # Fallback sur FAISS search standard (PAS Hybride complet sur tout le corpus)
                 # On ne pourra mixer qu'avec les scores des items retournés par FAISS
                 dense_scores, indices = self.index.search(source_embeddings, k=min(k*10, num_targets))
                 # TODO: gérer le cas complexe du large scale hybrid
                 pass
        else:
            dense_scores = cosine_similarity(source_embeddings, self.target_embeddings)

        # --- B. Score Sparse (BM25) ---
        if self.bm25 and source_texts:
            sparse_scores = np.zeros((num_queries, num_targets))
            for i, text in enumerate(source_texts):
                tokenized_query = text.lower().split()
                scores = self.bm25.get_scores(tokenized_query)
                sparse_scores[i] = scores
        else:
            sparse_scores = np.zeros(dense_scores.shape)

        # --- C. Normalisation et Fusion ---
        # Il est CRITIQUE de normaliser car BM25 va de 0 à infini (souvent 10-20) et Cosine de -1 à 1.
        
        # MinMax par query (ligne par ligne) ou global ? Global est souvent plus stable pour le corpus.
        # Mais Cosine est borné [-1, 1], BM25 non.
        
        # Normalisation Cosine -> [0, 1] (grosso modo, car on veut que 1 soit match parfait)
        # Cosine est déjà souvent entre 0 et 1 pour des embeddings de texte positifs (ReLU etc), mais peut être négatif.
        dense_norm = (dense_scores + 1) / 2 # Map [-1, 1] -> [0, 1]
        
        # Normalisation BM25 -> [0, 1]
        if self.bm25 and source_texts:
            # On normalise ligne par ligne car la magnitude BM25 dépend de la longueur de la query
            max_bm25 = sparse_scores.max(axis=1, keepdims=True)
            max_bm25[max_bm25 == 0] = 1 # éviter division par zero
            sparse_norm = sparse_scores / max_bm25
        else:
            sparse_norm = np.zeros(dense_scores.shape)
            
        # Fusion
        final_scores = self.alpha * dense_norm + (1 - self.alpha) * sparse_norm
        
        # --- D. Top-K ---
        # Argsort renvoie les indices triés du plus petit au plus grand, on prend la fin (reverse)
        top_indices = np.argsort(-final_scores, axis=1)[:, :k]
        
        # On récupère les scores correspondants
        # np.take_along_axis est pratique pour récupérer les valeurs avec des indices
        top_scores = np.take_along_axis(final_scores, top_indices, axis=1)
        
        return top_scores, top_indices
