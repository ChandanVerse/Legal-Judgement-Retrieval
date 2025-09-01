"""
Vector database operations using ChromaDB for legal judgments
"""
import chromadb
import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import json
import asyncio
import uuid
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorDatabase:
    """ChromaDB vector database for storing and retrieving legal judgment embeddings"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self._model_initialized = False
    
    async def initialize(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.config.CHROMA_STORE_PATH)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.config.COLLECTION_NAME
                )
                logger.info(f"Found existing collection: {self.config.COLLECTION_NAME}")
            except ValueError:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.config.COLLECTION_NAME,
                    metadata={"description": "Legal judgment embeddings"}
                )
                logger.info(f"Created new collection: {self.config.COLLECTION_NAME}")
            
            # Initialize embedding model
            await self._initialize_embedding_model()
            
            logger.info("Vector database initialized successfully")
            
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
            self._model_initialized = True
            
            logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None
            self._model_initialized = False
            raise RuntimeError(f"Failed to initialize embedding model: {e}")
    
    def _ensure_model_ready(self):
        """Ensure embedding model is initialized before use"""
        if not self._model_initialized or self.embedding_model is None:
            raise RuntimeError(
                "Embedding model not initialized. Call initialize() first."
            )
    
    def _encode_texts_safely(self, texts: List[str]):
        """Safely encode texts and return in ChromaDB compatible format"""
        if self.embedding_model is None:
            raise RuntimeError("Embedding model is not initialized")
        
        # Generate embeddings
        raw_result = self.embedding_model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=True
        )
        
        # Convert to proper format step by step
        if isinstance(raw_result, np.ndarray):
            # Convert numpy array to nested lists
            embeddings_list = []
            for i in range(raw_result.shape[0]):
                embedding_vector = raw_result[i].tolist()
                embeddings_list.append(embedding_vector)
            return embeddings_list
        else:
            # Assume it's already a list, convert each embedding to list
            embeddings_list = []
            for emb in raw_result:
                if isinstance(emb, np.ndarray):
                    embeddings_list.append(emb.tolist())
                elif isinstance(emb, (list, tuple)):
                    embeddings_list.append(list(emb))
                else:
                    embeddings_list.append([float(emb)])
            return embeddings_list
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            self._ensure_model_ready()
            
            if not texts:
                return []
            
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            return self._encode_texts_safely(texts)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def _encode_single_query(self, query: str) -> List[float]:
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
            
            if self.collection is None:
                raise RuntimeError("Collection not initialized")
            
            # Extract texts and metadata
            texts = [doc.page_content for doc in documents]
            metadatas = []
            ids = []
            
            for doc in documents:
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
                
                # Combine document metadata with file metadata
                metadata = doc.metadata.copy()
                if file_metadata:
                    metadata.update(file_metadata)
                
                # ChromaDB requires string values for metadata
                clean_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = str(value)
                    elif value is not None:
                        clean_metadata[key] = json.dumps(value)
                
                metadatas.append(clean_metadata)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} documents...")
            embeddings = self._encode_texts_safely(texts)
            
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                end_idx = min(i + batch_size, len(texts))
                
                self.collection.add(
                    documents=texts[i:end_idx],
                    embeddings=embeddings[i:end_idx],  # This should now work
                    metadatas=metadatas[i:end_idx],
                    ids=ids[i:end_idx]
                )
                
                logger.debug(f"Added batch {i//batch_size + 1}: documents {i} to {end_idx}")
            
            logger.info(f"Successfully added {len(documents)} documents to vector database")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform similarity search in the vector database"""
        try:
            self._ensure_model_ready()
            
            if self.collection is None:
                raise RuntimeError("Collection not initialized")
            
            # Generate query embedding
            query_embedding = self._encode_single_query(query)
            
            # Build where clause for filtering
            where_clause = None
            if filters:
                where_clause = {}
                for key, value in filters.items():
                    if isinstance(value, list):
                        where_clause[key] = {"$in": [str(v) for v in value]}
                    else:
                        where_clause[key] = str(value)
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results with safe access
            formatted_results = []
            
            # Safely extract results
            documents = []
            metadatas = []
            distances = []
            
            if results.get('documents') and len(results['documents']) > 0:
                documents = results['documents'][0]
            
            if results.get('metadatas') and len(results['metadatas']) > 0:
                metadatas = results['metadatas'][0]
            
            if results.get('distances') and len(results['distances']) > 0:
                distances = results['distances'][0]
            
            # Process results
            for i in range(len(documents)):
                distance = distances[i] if i < len(distances) else 1.0
                similarity_score = max(0.0, 1.0 - distance)
                metadata = metadatas[i] if i < len(metadatas) else {}
                
                result = {
                    'content': documents[i],
                    'metadata': metadata,
                    'similarity_score': similarity_score,
                    'distance': distance
                }
                
                # Add preview
                content = result['content']
                result['preview'] = content[:300] + ("..." if len(content) > 300 else "")
                
                formatted_results.append(result)
            
            logger.info(f"Retrieved {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            raise
    
    async def get_collection_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            if self.collection is None:
                return 0
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all unique documents in the database"""
        try:
            if self.collection is None:
                return []
                
            results = self.collection.get(include=["metadatas"])
            documents = {}
            metadatas = results.get('metadatas', [])
            
            for metadata in metadatas:
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
            if self.collection is None:
                return False
                
            results = self.collection.get(
                where={"filename": filename},
                include=["ids"]
            )
            
            ids = results.get('ids', [])
            if ids:
                self.collection.delete(ids=ids)
                logger.info(f"Deleted {len(ids)} chunks for document: {filename}")
                return True
            else:
                logger.warning(f"No chunks found for document: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting document {filename}: {e}")
            raise
    
    async def clear_collection(self):
        """Clear all documents from the collection"""
        try:
            if self.client is None:
                return
                
            try:
                self.client.delete_collection(self.config.COLLECTION_NAME)
            except ValueError:
                pass
                
            self.collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"description": "Legal judgment embeddings"}
            )
            logger.info("Collection cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise
    
    async def update_document_metadata(self, document_id: str, metadata: Dict[str, Any]):
        """Update metadata for a specific document"""
        try:
            if self.collection is None:
                raise RuntimeError("Collection not initialized")
                
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = str(value)
                elif value is not None:
                    clean_metadata[key] = json.dumps(value)
            
            self.collection.update(
                ids=[document_id],
                metadatas=[clean_metadata]
            )
            
            logger.info(f"Updated metadata for document: {document_id}")
            
        except Exception as e:
            logger.error(f"Error updating document metadata: {e}")
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by its ID"""
        try:
            if self.collection is None:
                return None
                
            results = self.collection.get(
                ids=[document_id],
                include=["documents", "metadatas"]
            )
            
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            
            if documents and len(documents) > 0:
                return {
                    'id': document_id,
                    'content': documents[0],
                    'metadata': metadatas[0] if metadatas and len(metadatas) > 0 else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None