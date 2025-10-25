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

    # Vector Database Configuration (Pinecone)
    COLLECTION_NAME = os.getenv("PINECONE_INDEX_NAME", "legal-judgments")

    # Legacy ChromaDB path (kept for reference, no longer used)
    # CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
    
    # Embedding Model Configuration
    EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
    EMBEDDING_DEVICE = "cuda"  # or "cpu"
    
    # Text Splitter Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Retrieval Configuration
    TOP_K_RETRIEVAL = 5
    SIMILARITY_THRESHOLD = 0.3  # Minimum cosine similarity score

    # Section Detection Configuration
    ENABLE_SECTION_DETECTION = True  # Enable section-aware processing

    # Supported legal document sections
    LEGAL_SECTIONS = [
        'facts',                    # Facts of the case
        'grounds',                  # Issues/Grounds/Questions of law
        'prayers',                  # Relief sought/Prayers
        'arguments_petitioner',     # Petitioner's arguments
        'arguments_respondent',     # Respondent's arguments
        'ratio_decidendi',          # Legal reasoning/Ratio
        'obiter_dicta',            # Obiter remarks
        'judgment',                 # Final judgment/Order
        'general',                  # Fallback for unclassified sections
    ]

    # Section display names for user interface
    SECTION_DISPLAY_NAMES = {
        'facts': 'Facts',
        'grounds': 'Grounds/Issues',
        'prayers': 'Prayers/Relief Sought',
        'arguments_petitioner': 'Petitioner Arguments',
        'arguments_respondent': 'Respondent Arguments',
        'ratio_decidendi': 'Legal Reasoning (Ratio)',
        'obiter_dicta': 'Observations (Obiter)',
        'judgment': 'Judgment/Order',
        'general': 'General/Other',
    }

    @classmethod
    def setup_directories(cls):
        """Ensure all required directories exist"""
        cls.JUDGMENTS_DIR.mkdir(parents=True, exist_ok=True)