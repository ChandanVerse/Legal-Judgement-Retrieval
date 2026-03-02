"""Fast GPU embeddings using sentence-transformers"""
import torch
from sentence_transformers import SentenceTransformer
import config


class Embedder:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading embedding model on {self.device}...")
        self.model = SentenceTransformer(
            config.EMBEDDING_MODEL,
            trust_remote_code=True,
            device=self.device
        )
        print(f"Model loaded: {config.EMBEDDING_MODEL}")

    def embed(self, text: str) -> list[float]:
        """Embed single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed multiple texts with GPU batching - MUCH FASTER"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 50,
            convert_to_numpy=True
        )
        return embeddings.tolist()
