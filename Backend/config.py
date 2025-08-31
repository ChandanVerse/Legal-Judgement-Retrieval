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
    CHROMA_STORE_PATH = BASE_DIR / "chroma_store"
    
    # Embedding Model Configuration
    EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DEVICE = "cpu"  # Change to "cuda" if GPU available
    
    # Text Splitter Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Vector Database Configuration
    COLLECTION_NAME = "legal_judgments"
    
    # Language Model Configuration
    LLM_MODEL = "microsoft/DialoGPT-medium"  # Using lighter model for local deployment
    # Alternative: "mistralai/Mistral-7B-Instruct-v0.1" (requires more resources)
    LLM_DEVICE = "cpu"
    MAX_NEW_TOKENS = 512
    TEMPERATURE = 0.7
    
    # RAG Configuration
    TOP_K_RETRIEVAL = 5
    SIMILARITY_THRESHOLD = 0.7
    
    # Legal Document Sections
    LEGAL_SECTIONS = ["facts", "grounds", "prayers", "judgment", "ratio", "obiter"]
    
    # API Rate Limiting
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILES_PER_REQUEST = 5
    
    @classmethod
    def get_huggingface_cache_dir(cls):
        """Get HuggingFace cache directory"""
        return os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    
    @classmethod
    def setup_directories(cls):
        """Ensure all required directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.CHROMA_STORE_PATH.mkdir(parents=True, exist_ok=True)
        
    def __init__(self):
        """Initialize configuration and setup directories"""
        self.setup_directories()
        
    def to_dict(self):
        """Convert config to dictionary for logging"""
        return {
            "HOST": self.HOST,
            "PORT": self.PORT,
            "DEBUG": self.DEBUG,
            "DATA_DIR": str(self.DATA_DIR),
            "CHROMA_STORE_PATH": str(self.CHROMA_STORE_PATH),
            "EMBEDDING_MODEL": self.EMBEDDING_MODEL,
            "LLM_MODEL": self.LLM_MODEL,
            "CHUNK_SIZE": self.CHUNK_SIZE,
            "TOP_K_RETRIEVAL": self.TOP_K_RETRIEVAL
        }