"""
Vector database operations using ChromaDB with manual cosine similarity
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import numpy as np
from sentence_transformers import SentenceTransformer
import uuid

class VectorDatabase:
    """ChromaDB vector database for legal judgment embeddings with manual cosine similarity"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.embedding_dim = None
    
    def initialize(self):
        """Initialize ChromaDB and embedding model"""
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
        
        # Initialize ChromaDB with local persistence
        print("Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=self.config.CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.config.COLLECTION_NAME
            )
            print(f"Loaded existing collection: {self.config.COLLECTION_NAME}")
        except:
            self.collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Created new collection: {self.config.COLLECTION_NAME}")
        
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
        """Add documents to ChromaDB"""
        if not documents:
            return
        
        print(f"Adding {len(documents)} documents to vector database...")
        
        # Prepare data
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        ids = []
        metadatas = []
        documents_list = []
        embeddings_list = []
        
        for i, doc in enumerate(documents):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            documents_list.append(doc.page_content)
            embeddings_list.append(embeddings[i].tolist())
            metadatas.append(doc.metadata)
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings_list[i:end_idx],
                documents=documents_list[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
        
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
        Perform manual cosine similarity search
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters (ChromaDB where clause)
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Get all documents from collection (or filtered subset)
        results = self.collection.get(
            where=filters,
            include=["embeddings", "documents", "metadatas"]
        )
        
        if not results['ids']:
            return []
        
        # Calculate cosine similarity manually
        similarities = []
        for i, embedding in enumerate(results['embeddings']):
            embedding_array = np.array(embedding)
            similarity = self.cosine_similarity(query_embedding, embedding_array)
            similarities.append({
                'id': results['ids'][i],
                'content': results['documents'][i],
                'metadata': results['metadatas'][i],
                'similarity_score': float(similarity)
            })
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Return top_k results
        return similarities[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics including section breakdown"""
        count = self.collection.count()

        # Get section statistics
        section_stats = self.get_section_distribution()

        return {
            'total_vectors': count,
            'dimension': self.embedding_dim,
            'collection_name': self.config.COLLECTION_NAME,
            'sections': section_stats
        }

    def get_section_distribution(self) -> Dict[str, int]:
        """Get distribution of documents across sections"""
        try:
            results = self.collection.get(include=["metadatas"])

            if not results['metadatas']:
                return {}

            section_counts = {}
            for metadata in results['metadatas']:
                section = metadata.get('section', 'unknown')
                section_counts[section] = section_counts.get(section, 0) + 1

            return section_counts
        except Exception as e:
            print(f"Error getting section distribution: {e}")
            return {}
    
    def reset_database(self):
        """Reset the entire database (use with caution)"""
        print("Resetting database...")
        self.client.delete_collection(name=self.config.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("Database reset complete")