"""
Vector database operations using ChromaDB for legal judgments
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import json
import asyncio
import uuid

logger = logging.getLogger(__name__)

class VectorDatabase:
    """ChromaDB vector database for storing and retrieving legal judgment embeddings"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_model = None
    
    async def initialize(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.config.CHROMA_STORE_PATH),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"description": "Legal judgment embeddings"}
            )
            
            # Initialize embedding model
            logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(
                self.config.EMBEDDING_MODEL,
                device=self.config.EMBEDDING_DEVICE
            )
            
            logger.info("Vector database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embedding_model.encode(
                texts,
                convert_to_tensor=False,
                show_progress_bar=len(texts) > 10
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def add_documents(self, documents: List[Document], file_metadata: Optional[Dict] = None):
        """Add documents to the vector database"""
        try:
            if not documents:
                logger.warning("No documents to add")
                return
            
            # Extract texts and metadata
            texts = [doc.page_content for doc in documents]
            metadatas = []
            ids = []
            
            for i, doc in enumerate(documents):
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
                    else:
                        clean_metadata[key] = json.dumps(value)
                
                metadatas.append(clean_metadata)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} documents...")
            embeddings = self.generate_embeddings(texts)
            
            # Add to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector database")
            
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
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])[0]
            
            # Build where clause for filtering
            where_clause = None
            if filters:
                where_clause = {}
                for key, value in filters.items():
                    if isinstance(value, list):
                        # Handle multiple values (OR condition)
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
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'distance': results['distances'][0][i]
                    }
                    
                    # Add preview (first 200 characters)
                    result['preview'] = result['content'][:200] + ("..." if len(result['content']) > 200 else "")
                    
                    formatted_results.append(result)
            
            logger.info(f"Retrieved {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            raise
    
    async def get_collection_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all unique documents in the database"""
        try:
            # Get all documents with metadata
            results = self.collection.get(
                include=["metadatas"]
            )
            
            # Extract unique filenames and their info
            documents = {}
            for metadata in results['metadatas']:
                filename = metadata.get('filename', 'unknown')
                if filename not in documents:
                    documents[filename] = {
                        'filename': filename,
                        'sections': set(),
                        'chunk_count': 0
                    }
                
                documents[filename]['sections'].add(metadata.get('section', 'general'))
                documents[filename]['chunk_count'] += 1
            
            # Convert to list and format
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
            # Find all chunks for the filename
            results = self.collection.get(
                where={"filename": filename},
                include=["ids"]
            )
            
            if results['ids']:
                # Delete all chunks
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document: {filename}")
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
            # Delete the collection and recreate it
            self.client.delete_collection(self.config.COLLECTION_NAME)
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
            # ChromaDB requires string values
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = str(value)
                else:
                    clean_metadata[key] = json.dumps(value)
            
            self.collection.update(
                ids=[document_id],
                metadatas=[clean_metadata]
            )
            
            logger.info(f"Updated metadata for document: {document_id}")
            
        except Exception as e:
            logger.error(f"Error updating document metadata: {e}")
            raise