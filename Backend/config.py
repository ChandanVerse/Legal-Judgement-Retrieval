"""
Configuration settings for the Legal Judgement RAG System
"""
import os
from pathlib import Path

class Config:
    """Configuration class for the RAG system"""
    
    # Server Configuration
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # Directory Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data" / "judgments"
    
    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-judgments")
    
    # Embedding Model Configuration
    EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DEVICE = "cpu"  # Change to "cuda" if GPU available
    
    # Text Splitter Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Language Model Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LLM_MODEL = "gemini-pro"
    
    # RAG Configuration
    TOP_K_RETRIEVAL = 5
    SIMILARITY_THRESHOLD = 0.6
    
    # Legal Document Sections
    LEGAL_SECTIONS = ["facts", "grounds", "prayers", "judgment", "ratio", "obiter"]
    
    # API Rate Limiting
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILES_PER_REQUEST = 5
    
    @classmethod
    def setup_directories(cls):
        """Ensure all required directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
    def __init__(self):
        """Initialize configuration and setup directories"""
        self.setup_directories()