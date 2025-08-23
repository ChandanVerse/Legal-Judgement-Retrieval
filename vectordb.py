"""
Vector database module for Legal Judgments Similarity Retrieval System.
Handles ChromaDB operations including storing and retrieving embeddings with metadata.
"""

import chromadb
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import config
import utils

# Set up logging
logger = utils.setup_logging()

class VectorDatabase:
    """
    Handles ChromaDB operations for storing and retrieving document embeddings.
    Provides persistent storage with efficient similarity search capabilities.
    """
    
    def __init__(self, persist_directory: str = None, collection_name: str = None):
        """
        Initialize the vector database.
        
        Args:
            persist_directory: Directory for persistent storage (uses config default if None)
            collection_name: Name of the ChromaDB collection (uses config default if None)
        """
        self.persist_directory = persist_directory or str(config.VECTOR_DB_DIR)
        self.collection_name = collection_name or config.COLLECTION_NAME
        self.client = None
        self.collection = None
        
        # Initialize ChromaDB client and collection
        self._initialize_client()
        self._get_or_create_collection()
    
    def _initialize_client(self) -> None:
        """Initialize ChromaDB client with persistent storage."""
        try:
            # Create ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,  # Disable telemetry for privacy
                    allow_reset=True
                )
            )
            
            logger.info(f"Initialized ChromaDB client with persistence at: {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise Exception(f"Database initialization error: {str(e)}")
    
    def _get_or_create_collection(self) -> None:
        """Get existing collection or create new one."""
        try:
            # Try to get existing collection first
            collections = self.client.list_collections()
            existing_collection_names = [col.name for col in collections]
            
            if self.collection_name in existing_collection_names:
                self.collection = self.client.get_collection(self.collection_name)
                count = self.collection.count()
                logger.info(f"Retrieved existing collection '{self.collection_name}' with {count} items")
            else:
                # Create new collection with cosine similarity
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}  # Use cosine distance for similarity
                )
                logger.info(f"Created new collection '{self.collection_name}'")
                
        except Exception as e:
            logger.error(f"Failed to get/create collection: {str(e)}")
            raise Exception(f"Collection setup error: {str(e)}")
    
    def store_embeddings(self, chunks_with_embeddings: List[Dict[str, Any]]) -> bool:
        """
        Store document chunks with their embeddings in the database.
        
        Args:
            chunks_with_embeddings: List of chunks with 'content', 'metadata', and 'embedding'
            
        Returns:
            True if successful, False otherwise
        """
        if not chunks_with_embeddings:
            logger.warning("No chunks provided for storage")
            return False
        
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for i, chunk in enumerate(chunks_with_embeddings):
                # Create unique ID for each chunk
                chunk_metadata = chunk.get('metadata', {})
                chunk_id = chunk_metadata.get('chunk_index', f"chunk_{i}")
                
                # Prepare data
                ids.append(chunk_id)
                documents.append(chunk.get('content', ''))
                embeddings.append(chunk.get('embedding', []).tolist())  # Convert numpy to list
                
                # Prepare metadata (ChromaDB requires JSON-serializable values)
                metadata = self._prepare_metadata(chunk_metadata)
                metadatas.append(metadata)
            
            # Store in ChromaDB (upsert to handle duplicates)
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks_with_embeddings)} chunks in vector database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {str(e)}")
            return False
    
    def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for ChromaDB storage (ensure JSON serializable).
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            ChromaDB-compatible metadata
        """
        prepared_metadata = {}
        
        for key, value in metadata.items():
            # Convert non-serializable types to strings
            if isinstance(value, (str, int, float, bool)):
                prepared_metadata[key] = value
            elif value is None:
                prepared_metadata[key] = ""
            else:
                prepared_metadata[key] = str(value)
        
        return prepared_metadata
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Search for most similar chunks to query embedding.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return (uses config default if None)
            
        Returns:
            List of similar chunks with scores and metadata
        """
        top_k = top_k or config.DEFAULT_TOP_K
        
        if self.collection.count() == 0:
            logger.warning("No documents in collection for search")
            return []
        
        try:
            # Convert numpy array to list for ChromaDB
            query_embedding_list = query_embedding.tolist()
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding_list],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            similar_chunks = []
            
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    # ChromaDB returns cosine distance, convert to similarity
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    # Skip results below similarity threshold
                    if similarity < config.SIMILARITY_THRESHOLD:
                        continue
                    
                    chunk_data = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': similarity,
                        'distance': distance
                    }
                    
                    similar_chunks.append(chunk_data)
            
            logger.debug(f"Found {len(similar_chunks)} similar chunks (threshold: {config.SIMILARITY_THRESHOLD})")
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            stats = {
                'collection_name': self.collection_name,
                'total_chunks': count,
                'persist_directory': self.persist_directory
            }
            
            # Get sample of documents for additional stats
            if count > 0:
                sample_size = min(10, count)
                sample_results = self.collection.get(limit=sample_size)
                
                if sample_results['metadatas']:
                    # Count unique documents
                    unique_files = set()
                    for metadata in sample_results['metadatas']:
                        filename = metadata.get('filename', 'unknown')
                        unique_files.add(filename)
                    
                    stats['sample_unique_files'] = len(unique_files)
                    stats['sample_size'] = len(sample_results['metadatas'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {'error': str(e)}
    
    def delete_collection(self) -> bool:
        """
        Delete the current collection (useful for reset).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'")
            
            # Recreate empty collection
            self._get_or_create_collection()
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            return False
    
    def collection_exists_and_populated(self) -> bool:
        """
        Check if collection exists and has documents.
        
        Returns:
            True if collection exists and has documents, False otherwise
        """
        try:
            if not self.collection:
                return False
            
            count = self.collection.count()
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking collection status: {str(e)}")
            return False
    
    def backup_collection(self, backup_path: str) -> bool:
        """
        Create a simple backup of collection metadata.
        
        Args:
            backup_path: Path to save backup info
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stats = self.get_collection_stats()
            
            with open(backup_path, 'w') as f:
                json.dump(stats, f, indent=2)
            
            logger.info(f"Backed up collection info to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False