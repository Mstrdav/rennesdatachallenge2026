import re
import unicodedata

class TextPreprocessor:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        """
        Nettoyer le texte en mettant en minuscules, en supprimant les accents et les caractères spéciaux.
        """
        if not isinstance(text, str):
            return ""
            
        # Minuscules
        text = text.lower()
        
        # Supprimer les accents
        text = str(unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8"))
        
        # Supprimer les caractères spéciaux et les espaces supplémentaires
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def preprocess_batch(self, texts: list[str]) -> list[str]:
        """
        Prétraiter une liste de textes.
        """
        return [self.clean_text(t) for t in texts]
