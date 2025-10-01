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
    TEST_DIR = BASE_DIR / "test_pdf"
    
    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-judgments")
    
    # Embedding Model Configuration
    # Options (ranked by quality):
    # 1. "nomic-ai/nomic-embed-text-v1.5" - Best balance (768 dim)
    # 2. "BAAI/bge-large-en-v1.5" - Excellent quality (1024 dim)
    # 3. "sentence-transformers/all-mpnet-base-v2" - Fast (768 dim)
    
    EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"  # Best overall for 2025
    EMBEDDING_DEVICE = "cuda"  # Using GPU with ONNX Runtime for fastest inference
    
    # Text Splitter Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL = 5
    
    @classmethod
    def setup_directories(cls):
        """Ensure all required directories exist"""
        cls.JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEST_DIR.mkdir(parents=True, exist_ok=True)