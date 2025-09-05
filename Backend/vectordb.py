"""
Vector database operations using FAISS for legal judgments
"""
import faiss
import pickle
import logging
from typing import List, Dict, Any, Optional, cast, Union
from langchain.schema import Document
import json
import asyncio
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class VectorDatabase:
    """FAISS vector database for storing and retrieving legal judgment embeddings"""
    
    def __init__(self, config: Any):
        """Initialize with type hints"""
        self.config = config
        self.index: Optional[faiss.Index] = None  # type: ignore[valid-type]
        self.documents_store: List[Dict[str, Any]] = []
        self.id_to_index_map: Dict[str, int] = {}
        self.embedding_model: Optional[SentenceTransformer] = None
        self._model_initialized = False
        self.embedding_dim: Optional[int] = None
        
        # File paths for persistence
        self.index_path = Path(self.config.CHROMA_STORE_PATH) / "faiss_index.idx"
        self.documents_path = Path(self.config.CHROMA_STORE_PATH) / "documents.pkl"
        self.metadata_path = Path(self.config.CHROMA_STORE_PATH) / "metadata.pkl"
    
    async def initialize(self):
        """Initialize FAISS index and embedding model"""
        try:
            # Ensure storage directory exists
            self.config.CHROMA_STORE_PATH.mkdir(parents=True, exist_ok=True)
            
            # Initialize embedding model first
            await self._initialize_embedding_model()
            
            # Load existing index if available
            await self._load_existing_data()
            
            logger.info("FAISS vector database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise
    
    async def _initialize_embedding_model(self):
        """Initialize the embedding model with error handling"""
        try:
            logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            
            def load_model() -> SentenceTransformer:
                return SentenceTransformer(
                    self.config.EMBEDDING_MODEL,
                    device=self.config.EMBEDDING_DEVICE
                )
            
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(None, load_model)
            
            # Get embedding dimension with proper error handling
            try:
                if self.embedding_model is None:
                    raise RuntimeError("Embedding model initialization failed")
                test_embedding = self.embedding_model.encode(
                    ["test"], 
                    convert_to_tensor=False,
                    normalize_embeddings=True
                )
                if not isinstance(test_embedding, np.ndarray):
                    test_embedding = np.array(test_embedding)
                self.embedding_dim = test_embedding.shape[1]  # Get dimension from shape
            except Exception as e:
                raise RuntimeError(f"Failed to determine embedding dimension: {e}")
            
            self._model_initialized = True
            logger.info(f"Embedding model loaded successfully. Dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None
            self._model_initialized = False
            raise RuntimeError(f"Failed to initialize embedding model: {e}")
    
    async def _load_existing_data(self):
        """Load existing FAISS index and document store if available"""
        try:
            if (self.index_path.exists() and 
                self.documents_path.exists() and 
                self.metadata_path.exists()):
                
                logger.info("Loading existing FAISS index...")
                
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))  # type: ignore[attr-defined]
                
                # Load documents and metadata
                with open(self.documents_path, 'rb') as f:
                    self.documents_store = pickle.load(f)
                
                with open(self.metadata_path, 'rb') as f:
                    self.id_to_index_map = pickle.load(f)
                
                logger.info(f"Loaded existing index with {len(self.documents_store)} documents")
            else:
                logger.info("No existing index found. Creating new FAISS index...")
                self._create_new_index()
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            logger.info("Creating new index...")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        if self.embedding_dim is None:
            raise RuntimeError("Embedding dimension not set. Initialize embedding model first.")
        
        # Create FAISS index with Inner Product (for cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # type: ignore[attr-defined]
        self.documents_store = []
        self.id_to_index_map = {}
        
        logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")
    
    def _ensure_model_ready(self):
        """Ensure embedding model is initialized before use"""
        if not self._model_initialized or self.embedding_model is None:
            raise RuntimeError(
                "Embedding model not initialized. Call initialize() first."
            )
    
    def _encode_texts_safely(self, texts: List[str]) -> np.ndarray:
        """Safely encode texts with input validation"""
        if not texts or not isinstance(texts, list):
            raise ValueError("Input must be a non-empty list of strings")
        if not all(isinstance(text, str) for text in texts):
            raise ValueError("All inputs must be strings")
        
        if self.embedding_model is None:
            raise RuntimeError("Embedding model is not initialized")
            
        try:
            # Generate embeddings with explicit typing
            embeddings: np.ndarray = self.embedding_model.encode(
                texts,
                convert_to_tensor=False,
                normalize_embeddings=True,  # Normalize for cosine similarity
                show_progress_bar=False
            )
            
            # Ensure correct shape and type
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings, dtype=np.float32)
            elif embeddings.dtype != np.float32:
                embeddings = embeddings.astype(np.float32)
                
            # Validate embedding dimensions
            if embeddings.ndim != 2:
                raise ValueError(f"Expected 2D array, got {embeddings.ndim}D")
            if self.embedding_dim and embeddings.shape[1] != self.embedding_dim:
                raise ValueError(f"Embedding dimension mismatch: got {embeddings.shape[1]}, expected {self.embedding_dim}")
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            raise RuntimeError(f"Failed to encode texts: {e}")
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            self._ensure_model_ready()
            
            if not texts:
                return np.array([])
            
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            return self._encode_texts_safely(texts)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def _encode_single_query(self, query: str) -> np.ndarray:
        """Helper method to encode a single query"""
        try:
            self._ensure_model_ready()
            
            # Encode single query
            embeddings = self._encode_texts_safely([query])
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"Error encoding query: {e}")
            raise
    
    async def add_documents(self, documents: List[Document], file_metadata: Optional[Dict] = None):
        """Add documents to the vector database"""
        try:
            if not documents:
                logger.warning("No documents to add")
                return
            
            self._ensure_model_ready()
            
            if self.index is None:
                self._create_new_index()
            
            # Extract texts and prepare metadata
            texts = [doc.page_content for doc in documents]
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} documents...")
            embeddings = self._encode_texts_safely(texts)
            
            # Add documents to store
            start_index = len(self.documents_store)
            
            for i, doc in enumerate(documents):
                doc_id = str(uuid.uuid4())
                
                # Combine document metadata with file metadata
                metadata = doc.metadata.copy()
                if file_metadata:
                    metadata.update(file_metadata)
                
                # Store document info
                doc_info = {
                    'id': doc_id,
                    'content': doc.page_content,
                    'metadata': metadata
                }
                
                self.documents_store.append(doc_info)
                self.id_to_index_map[doc_id] = start_index + i
            
            # Add embeddings to FAISS index
            self.index.add(embeddings)  # type: ignore[union-attr]
            
            # Save to disk
            await self._save_data()
            
            logger.info(f"Successfully added {len(documents)} documents to FAISS index")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Union[str, List[str]]]] = None
    ) -> List[Dict[str, Any]]:
        """Perform similarity search in the vector database"""
        try:
            self._ensure_model_ready()
            
            if self.index is None or len(self.documents_store) == 0:
                logger.warning("No documents in index for search")
                return []
            
            # Generate query embedding
            query_embedding = self._encode_single_query(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Perform search
            scores, indices = self.index.search(  # type: ignore[union-attr]
                query_embedding, 
                min(top_k, len(self.documents_store))
            )
            
            # Format results
            formatted_results = []
            
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    continue
                    
                if idx >= len(self.documents_store):
                    continue
                
                doc_info = self.documents_store[idx]
                
                # Apply filters if specified
                if filters and not self._matches_filters(doc_info['metadata'], filters):
                    continue
                
                # Convert FAISS score (inner product) to similarity score
                similarity_score = float(score)
                distance = 1.0 - similarity_score
                
                result = {
                    'content': doc_info['content'],
                    'metadata': doc_info['metadata'],
                    'similarity_score': similarity_score,
                    'distance': distance
                }
                
                # Add preview
                content = result['content']
                result['preview'] = content[:300] + ("..." if len(content) > 300 else "")
                
                formatted_results.append(result)
            
            # Sort by similarity score (descending)
            formatted_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(f"Retrieved {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            raise
    
    def _matches_filters(
        self, 
        metadata: Dict[str, Any], 
        filters: Dict[str, Union[str, List[str]]]
    ) -> bool:
        """Improved filter matching with type safety"""
        try:
            for key, filter_value in filters.items():
                if key not in metadata:
                    return False
                    
                meta_value = metadata[key]
                if isinstance(filter_value, list):
                    if not isinstance(meta_value, (str, int, float)):
                        return False
                    if str(meta_value) not in [str(v) for v in filter_value]:
                        return False
                else:
                    if str(meta_value) != str(filter_value):
                        return False
            return True
        except Exception:
            return False
    
    async def get_collection_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            return len(self.documents_store)
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all unique documents in the database"""
        try:
            documents = {}
            
            for doc_info in self.documents_store:
                metadata = doc_info['metadata']
                filename = metadata.get('filename', 'unknown')
                
                if filename not in documents:
                    documents[filename] = {
                        'filename': filename,
                        'sections': set(),
                        'chunk_count': 0
                    }
                
                documents[filename]['sections'].add(metadata.get('section', 'general'))
                documents[filename]['chunk_count'] += 1
            
            document_list = []
            for filename, info in documents.items():
                document_list.append({
                    'filename': filename,
                    'sections': list(info['sections']),
                    'chunk_count': info['chunk_count']
                })
            
            return document_list
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    async def delete_document(self, filename: str) -> bool:
        """Delete all chunks of a specific document"""
        try:
            indices_to_remove = []
            
            # Find indices of documents to remove
            for i, doc_info in enumerate(self.documents_store):
                if doc_info['metadata'].get('filename') == filename:
                    indices_to_remove.append(i)
            
            if not indices_to_remove:
                logger.warning(f"No chunks found for document: {filename}")
                return False
            
            # Remove from documents store (in reverse order to maintain indices)
            for idx in reversed(indices_to_remove):
                del self.documents_store[idx]
            
            # Update ID mapping
            new_id_map = {}
            for doc_id, old_idx in self.id_to_index_map.items():
                # Skip deleted documents
                if old_idx in indices_to_remove:
                    continue
                
                # Calculate new index after removals
                new_idx = old_idx - sum(1 for removed_idx in indices_to_remove if removed_idx < old_idx)
                new_id_map[doc_id] = new_idx
            
            self.id_to_index_map = new_id_map
            
            # Rebuild FAISS index (FAISS doesn't support deletion easily)
            await self._rebuild_index()
            
            logger.info(f"Deleted {len(indices_to_remove)} chunks for document: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {filename}: {e}")
            raise
    
    async def _rebuild_index(self):
        """Rebuild FAISS index from current documents"""
        try:
            if not self.documents_store:
                self._create_new_index()
                await self._save_data()
                return
            
            # Extract texts
            texts = [doc_info['content'] for doc_info in self.documents_store]
            
            # Generate embeddings
            embeddings = self._encode_texts_safely(texts)
            
            # Create new index
            self._create_new_index()
            self.index.add(embeddings)  # type: ignore[union-attr]
            
            # Update ID mapping
            new_id_map = {}
            for i, doc_info in enumerate(self.documents_store):
                new_id_map[doc_info['id']] = i
            
            self.id_to_index_map = new_id_map
            
            # Save to disk
            await self._save_data()
            
            logger.info(f"Rebuilt FAISS index with {len(self.documents_store)} documents")
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            raise
    
    async def clear_collection(self):
        """Clear all documents from the collection"""
        try:
            self._create_new_index()
            await self._save_data()
            logger.info("Collection cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise
    
    async def _save_data(self):
        """Save FAISS index and document store to disk"""
        try:
            # Save FAISS index
            if self.index is not None:
                faiss.write_index(self.index, str(self.index_path))  # type: ignore[attr-defined]
            
            # Save documents store
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents_store, f)
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.id_to_index_map, f)
            
            logger.debug("Data saved to disk successfully")
            
        except Exception as e:
            logger.error(f"Error saving data to disk: {e}")
            raise
    
    async def update_document_metadata(self, document_id: str, metadata: Dict[str, Any]):
        """Update metadata for a specific document"""
        try:
            if document_id not in self.id_to_index_map:
                raise ValueError(f"Document {document_id} not found")
            
            idx = self.id_to_index_map[document_id]
            if idx >= len(self.documents_store):
                raise ValueError(f"Invalid document index: {idx}")
            
            # Update metadata
            self.documents_store[idx]['metadata'].update(metadata)
            
            # Save to disk
            await self._save_data()
            
            logger.info(f"Updated metadata for document: {document_id}")
            
        except Exception as e:
            logger.error(f"Error updating document metadata: {e}")
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by its ID"""
        try:
            if document_id not in self.id_to_index_map:
                return None
            
            idx = self.id_to_index_map[document_id]
            if idx >= len(self.documents_store):
                return None
            
            doc_info = self.documents_store[idx]
            return {
                'id': document_id,
                'content': doc_info['content'],
                'metadata': doc_info['metadata']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None