"""
Vector database operations using Pinecone with manual cosine similarity fallback
"""
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import numpy as np
from sentence_transformers import SentenceTransformer
import uuid
import time
import os

class VectorDatabase:
    """Pinecone vector database for legal judgment embeddings"""

    def __init__(self, config):
        self.config = config
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.embedding_dim = None
        self.index_name = None

    def initialize(self):
        """Initialize Pinecone and embedding model"""
        print("Initializing embedding model...")

        # Verify CUDA availability
        import torch
        if self.config.EMBEDDING_DEVICE == "cuda":
            if torch.cuda.is_available():
                print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
            else:
                print("✗ CUDA not available, falling back to CPU")
                self.config.EMBEDDING_DEVICE = "cpu"

        # Load embedding model
        self.embedding_model = SentenceTransformer(
            self.config.EMBEDDING_MODEL,
            device=self.config.EMBEDDING_DEVICE,
            trust_remote_code=True
        )

        # Get embedding dimension
        test_embedding = self.embedding_model.encode(["test"])
        self.embedding_dim = test_embedding.shape[1]
        print(f"Embedding dimension: {self.embedding_dim}")

        # Initialize Pinecone
        print("Initializing Pinecone...")
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set. Please set it in .env file")

        self.pc = Pinecone(api_key=api_key)

        # Get index name from config or environment
        self.index_name = os.getenv("PINECONE_INDEX_NAME", self.config.COLLECTION_NAME)

        # Check if index exists, create if not
        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            print(f"Creating new Pinecone index: {self.index_name}")

            # Get environment from config or use default
            environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")

            self.pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dim,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=environment
                )
            )

            # Wait for index to be ready
            print("Waiting for index to be ready...")
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)
            print(f"✓ Index {self.index_name} is ready")
        else:
            print(f"✓ Connected to existing index: {self.index_name}")

        # Connect to index
        self.index = self.pc.Index(self.index_name)

        # Wait a moment for connection to be established
        time.sleep(1)

        print("Vector database initialized successfully")

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        embeddings = self.embedding_model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10
        )
        return embeddings

    def add_documents(self, documents: List[Document]):
        """Add documents to Pinecone"""
        if not documents:
            return

        print(f"Adding {len(documents)} documents to vector database...")

        # Prepare data
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings(texts)

        # Prepare vectors for Pinecone
        vectors = []
        for i, doc in enumerate(documents):
            doc_id = str(uuid.uuid4())

            # Pinecone metadata must be JSON-serializable
            # Convert all metadata values to proper types
            metadata = {
                'content': doc.page_content,  # Store content in metadata
                'filename': str(doc.metadata.get('filename', '')),
                'section': str(doc.metadata.get('section', 'general')),
                'section_confidence': float(doc.metadata.get('section_confidence', 0.0)),
                'section_header': str(doc.metadata.get('section_header', '')),
                'chunk_index': int(doc.metadata.get('chunk_index', 0)),
                'total_chunks_in_section': int(doc.metadata.get('total_chunks_in_section', 1))
            }

            vectors.append({
                'id': doc_id,
                'values': embeddings[i].tolist(),
                'metadata': metadata
            })

        # Upsert to Pinecone in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            end_idx = min(i + batch_size, len(vectors))
            batch = vectors[i:end_idx]
            self.index.upsert(vectors=batch)
            print(f"Uploaded batch {i//batch_size + 1}/{(len(vectors) + batch_size - 1)//batch_size}")

        print(f"Successfully added {len(documents)} documents")

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using Pinecone

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters (Pinecone filter syntax)
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]

        # Convert ChromaDB-style filters to Pinecone filters
        pinecone_filter = None
        if filters:
            pinecone_filter = self._convert_filters(filters)

        # Query Pinecone
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True,
            filter=pinecone_filter
        )

        # Format results to match ChromaDB format for compatibility
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                'id': match.id,
                'content': match.metadata.get('content', ''),
                'metadata': {
                    'filename': match.metadata.get('filename', ''),
                    'section': match.metadata.get('section', 'general'),
                    'section_confidence': match.metadata.get('section_confidence', 0.0),
                    'section_header': match.metadata.get('section_header', ''),
                    'chunk_index': match.metadata.get('chunk_index', 0),
                    'total_chunks_in_section': match.metadata.get('total_chunks_in_section', 1)
                },
                'similarity_score': float(match.score)
            })

        return formatted_results

    def _convert_filters(self, chromadb_filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ChromaDB-style filters to Pinecone filter format

        ChromaDB format: {"section": "facts"}
        Pinecone format: {"section": {"$eq": "facts"}}
        """
        if not chromadb_filters:
            return None

        pinecone_filter = {}
        for key, value in chromadb_filters.items():
            if isinstance(value, (str, int, float, bool)):
                pinecone_filter[key] = {"$eq": value}
            elif isinstance(value, dict):
                # Already in Pinecone format
                pinecone_filter[key] = value
            elif isinstance(value, list):
                pinecone_filter[key] = {"$in": value}

        return pinecone_filter

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics including section breakdown"""
        stats = self.index.describe_index_stats()

        # Get total vector count
        total_vectors = stats.total_vector_count

        # Get section distribution (requires fetching samples)
        section_stats = self._get_section_distribution()

        return {
            'total_vectors': total_vectors,
            'dimension': self.embedding_dim,
            'collection_name': self.index_name,
            'sections': section_stats,
            'namespaces': stats.namespaces
        }

    def _get_section_distribution(self) -> Dict[str, int]:
        """
        Get distribution of documents across sections
        Note: Pinecone doesn't support full scans, so this is an approximation
        based on querying with filters
        """
        try:
            section_counts = {}

            # Query for each known section
            for section in self.config.LEGAL_SECTIONS:
                # Query with filter to get count
                results = self.index.query(
                    vector=[0.0] * self.embedding_dim,  # Dummy vector
                    top_k=1,
                    filter={"section": {"$eq": section}},
                    include_metadata=True
                )

                # Note: This is an approximation since Pinecone doesn't return exact counts
                # We can only check if documents exist for each section
                if results.matches:
                    section_counts[section] = "exists"

            return section_counts
        except Exception as e:
            print(f"Warning: Could not get section distribution: {e}")
            return {}

    def reset_database(self):
        """Reset the entire database (use with caution)"""
        print(f"Resetting database: {self.index_name}...")

        try:
            # Delete the index
            self.pc.delete_index(self.index_name)
            print("Index deleted, waiting...")
            time.sleep(5)

            # Recreate the index
            environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")

            self.pc.create_index(
                name=self.index_name,
                dimension=self.embedding_dim,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=environment
                )
            )

            # Wait for index to be ready
            print("Waiting for new index to be ready...")
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)

            # Reconnect
            self.index = self.pc.Index(self.index_name)
            time.sleep(1)

            print("Database reset complete")
        except Exception as e:
            print(f"Error resetting database: {e}")
            raise
