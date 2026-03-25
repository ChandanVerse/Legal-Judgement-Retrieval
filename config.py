"""Central configuration"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = DATA_DIR / "dataset_pdfs"
TEST_DIR = DATA_DIR / "test_case"

# Embedding (sentence-transformers with CUDA)
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"

# Endee Vector Database
ENDEE_URL = os.getenv("ENDEE_URL", "http://localhost:8080/api/v1")
ENDEE_AUTH_TOKEN = os.getenv("ENDEE_AUTH_TOKEN")
ENDEE_INDEX = "legal_rag"
EMBEDDING_DIM = 768

# MongoDB Atlas (local development)
MONGO_URI = os.getenv("MONGO_URI")  # mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB_NAME = "legal_cases"

# AWS (production deployment)
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "legal-cases")
S3_BUCKET = os.getenv("S3_BUCKET", "legal-case-pdfs")

# Chunking
MIN_CHUNK_LEN = 100
MAX_CHUNK_LEN = 1000

# Search
DEFAULT_TOP_K = 10

# API Server
API_PORT = 8000
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
