"""
Vector database operations using Pinecone for legal judgments
"""
import pinecone
import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorDatabase:
    """Pinecone vector database for storing and retrieving legal judgment embeddings"""
    
    def __init__(self, config: Any):
        self.config = config
        self.index: Optional[pinecone.Index] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self._model_initialized = False
        self.embedding_dim: Optional[int] = None
    
    async def initialize(self):
        try:
            await self._initialize_embedding_model()
            
            pinecone.init(
                api_key=self.config.PINECONE_API_KEY,
                environment=self.config.PINECONE_ENVIRONMENT
            )
            
            index_name = self.config.PINECONE_INDEX_NAME
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=self.embedding_dim,
                    metric="cosine"
                )
            
            self.index = pinecone.Index(index_name)
            logger.info("Pinecone vector database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise
    
    async def _initialize_embedding_model(self):
        try:
            logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(
                self.config.EMBEDDING_MODEL,
                device=self.config.EMBEDDING_DEVICE
            )
            test_embedding = self.embedding_model.encode(["test"])
            self.embedding_dim = test_embedding.shape[1]
            self._model_initialized = True
            logger.info(f"Embedding model loaded successfully. Dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
            
    def _ensure_model_ready(self):
        if not self._model_initialized or self.embedding_model is None:
            raise RuntimeError("Embedding model not initialized. Call initialize() first.")
            
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        self._ensure_model_ready()
        return self.embedding_model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)

    async def add_documents(self, documents: List[Document], file_metadata: Optional[Dict] = None):
        if not documents:
            return
        self._ensure_model_ready()
        
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        vectors_to_upsert = []
        for i, doc in enumerate(documents):
            doc_id = str(uuid.uuid4())
            metadata = doc.metadata.copy()
            if file_metadata:
                metadata.update(file_metadata)
            
            # Pinecone metadata values must be string, number, boolean, or list of strings.
            # Ensure all values are compliant.
            for key, value in metadata.items():
                if not isinstance(value, (str, int, float, bool, list)):
                    metadata[key] = str(value)

            metadata['content'] = doc.page_content
            
            vectors_to_upsert.append({
                "id": doc_id,
                "values": embeddings[i].tolist(),
                "metadata": metadata
            })
            
        if self.index:
            self.index.upsert(vectors=vectors_to_upsert, batch_size=100)
            
    async def similarity_search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._ensure_model_ready()
        query_embedding = self.generate_embeddings([query])[0].tolist()
        
        if self.index:
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filters,
                include_metadata=True
            )
            
            formatted_results = []
            for match in results['matches']:
                content = match['metadata'].pop('content', '')
                formatted_results.append({
                    'id': match['id'],
                    'content': content,
                    'metadata': match['metadata'],
                    'similarity_score': match['score']
                })
            return formatted_results
        return []

    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        if self.index:
            response = self.index.fetch(ids=[document_id])
            if response and response['vectors']:
                vector_data = response['vectors'].get(document_id)
                if vector_data:
                    content = vector_data['metadata'].pop('content', '')
                    return {
                        'id': vector_data['id'],
                        'content': content,
                        'metadata': vector_data['metadata']
                    }
        return None

    async def get_collection_count(self) -> int:
        if self.index:
            try:
                stats = self.index.describe_index_stats()
                return stats.get('total_vector_count', 0)
            except Exception as e:
                logger.error(f"Could not get collection count from Pinecone: {e}")
        return 0

    async def clear_collection(self):
        if self.index:
            self.index.delete(delete_all=True)

    async def delete_document(self, filename: str) -> bool:
        """Deletes all vectors associated with a given filename."""
        if not self.index:
            return False

        try:
            # Pinecone doesn't support direct deletion by metadata.
            # The strategy is to query for the vector IDs using a filter, then delete by ID.
            # This can be slow and is not recommended for frequent use on large datasets.
            # A dummy vector is used because the query is based on the filter, not similarity.
            dummy_vector = [0.0] * self.embedding_dim
            query_result = self.index.query(
                vector=dummy_vector,
                filter={"filename": {"$eq": filename}},
                top_k=10000, # Max limit to fetch as many as possible
                include_metadata=False # We only need the IDs
            )

            ids_to_delete = [match['id'] for match in query_result['matches']]

            if not ids_to_delete:
                logger.warning(f"No documents found with filename '{filename}' to delete.")
                return False

            self.index.delete(ids=ids_to_delete)
            logger.info(f"Successfully deleted {len(ids_to_delete)} vectors for filename '{filename}'.")
            return True
        except Exception as e:
            logger.error(f"Error deleting document '{filename}': {e}")
            return False

    async def list_documents(self) -> List[Dict[str, Any]]:
        """
        Lists unique documents. NOTE: This is NOT efficient in Pinecone
        and should not be used in production on large indexes. It is here
        for simple admin/debugging purposes.
        """
        logger.warning("Listing all documents is inefficient and not recommended for large Pinecone indexes.")
        if not self.index:
            return []

        try:
            # In a real application, you would store and query this from a separate
            # relational or document database, not the vector index.
            # This is a functional but slow workaround.
            stats = await self.get_collection_count()
            if stats == 0:
                return []
            
            # Fetch all vector IDs. This can be very slow.
            dummy_vector = [0.0] * self.embedding_dim
            response = self.index.query(vector=dummy_vector, top_k=10000, include_metadata=True)
            
            documents = {}
            for match in response['matches']:
                metadata = match.get('metadata', {})
                filename = metadata.get('filename', 'unknown')
                if filename not in documents:
                    documents[filename] = {
                        'filename': filename,
                        'chunk_count': 0
                    }
                documents[filename]['chunk_count'] += 1
            
            return list(documents.values())
        except Exception as e:
            logger.error(f"Could not list documents from Pinecone: {e}")
            return []