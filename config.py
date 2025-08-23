"""
Configuration file for Legal Judgments Similarity Retrieval System.
Contains all configurable parameters including paths, model settings, and chunking parameters.
"""

import os
from pathlib import Path

# Directory paths - using pathlib for cross-platform compatibility
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data" / "judgments"
VECTOR_DB_DIR = PROJECT_ROOT / "chroma_store"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

# Model configuration
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"  # BGE model for high-quality embeddings
EMBEDDING_DEVICE = "auto"  # Will auto-detect CUDA or fallback to CPU

# Text chunking parameters
CHUNK_SIZE = 1000  # Characters per chunk - balance between context and precision
CHUNK_OVERLAP = 200  # Overlap between chunks to maintain context continuity

# Retrieval settings
DEFAULT_TOP_K = 5  # Number of similar chunks to retrieve by default
SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score (0.0 to 1.0)

# ChromaDB collection settings
COLLECTION_NAME = "legal_judgments"  # Name of the ChromaDB collection

# Logging settings
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
SHOW_PROGRESS = True  # Show progress bars during processing

# File processing settings
SUPPORTED_FORMATS = [".pdf"]  # Currently only PDF support
MAX_FILE_SIZE_MB = 100  # Maximum file size to process (in MB)

# Preview settings for query results
PREVIEW_LENGTH = 200  # Characters to show in result preview