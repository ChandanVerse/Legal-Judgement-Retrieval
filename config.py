"""
Configuration settings for the Legal Judgement RAG System
"""
import os
from pathlib import Path

class Config:
    """Configuration class for the RAG system"""
    
    # Directory Paths
    BASE_DIR = Path(__file__).parent
    JUDGMENTS_DIR = BASE_DIR / "judgments_pdf"
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
    
    # ChromaDB Configuration
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal-judgments")
    
    # Embedding Model Configuration
    EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
    EMBEDDING_DEVICE = "cuda"  # or "cpu"
    
    # Text Splitter Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL = 5
    SIMILARITY_THRESHOLD = 0.3  # Minimum cosine similarity score
    
    @classmethod
    def setup_directories(cls):
        """Ensure all required directories exist"""
        cls.JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        Path(cls.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)