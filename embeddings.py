"""
Embeddings generation module for Legal Judgments Similarity Retrieval System.
Uses BAAI/bge-large-en-v1.5 model from sentence-transformers for high-quality embeddings.
Supports GPU acceleration with automatic fallback to CPU.
"""

import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Union, Optional
import config
import utils

# Set up logging
logger = utils.setup_logging()

class EmbeddingGenerator:
    """
    Handles embedding generation using BGE model with GPU/CPU support.
    Optimized for legal document similarity tasks.
    """
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence transformer model (uses config default if None)
            device: Device to use ('cuda', 'cpu', or 'auto' for auto-detection)
        """
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.device = self._determine_device(device or config.EMBEDDING_DEVICE)
        self.model: Optional[SentenceTransformer] = None
        
        # Load the model
        self._load_model()
    
    def _determine_device(self, device_preference: str) -> str:
        """
        Determine the best device to use for embeddings.
        
        Args:
            device_preference: User preference ('cuda', 'cpu', or 'auto')
            
        Returns:
            Device string to use
        """
        if device_preference == 'auto':
            if torch.cuda.is_available():
                device = 'cuda'
                logger.info(f"CUDA available - using GPU: {torch.cuda.get_device_name()}")
            else:
                device = 'cpu'
                logger.info("CUDA not available - using CPU")
        else:
            device = device_preference
            logger.info(f"Using specified device: {device}")
        
        return device
    
    def _load_model(self) -> None:
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            
            # Load model with appropriate device settings
            self.model = SentenceTransformer(self.model_name)
            
            # Move model to specified device
            if self.device == 'cuda' and torch.cuda.is_available():
                self.model = self.model.to('cuda')
                # Use half precision for better GPU memory usage
                if hasattr(self.model, 'half'):
                    self.model.half()
            else:
                self.model = self.model.to('cpu')
            
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {str(e)}")
            raise Exception(f"Model loading error: {str(e)}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array containing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            # Get dimension from model or use default
            if self.model is not None:
                dim = self.model.get_sentence_embedding_dimension()
                if dim is not None:
                    return np.zeros(dim, dtype=np.float32)
            # Fallback dimension for BGE model
            return np.zeros(1024, dtype=np.float32)
        
        if self.model is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")
        
        try:
            # Generate embedding
            embedding = self.model.encode(
                text.strip(),
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 normalization for better similarity computation
            )
            
            return embedding.astype(np.float32)  # Use float32 to save memory
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            dim = self.model.get_sentence_embedding_dimension() or 1024
            return np.zeros(dim, dtype=np.float32)
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches for efficiency.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding arrays
        """
        if not texts:
            logger.warning("No texts provided for batch embedding")
            return []
        
        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        
        if not valid_texts:
            logger.warning("All provided texts are empty")
            return []
        
        if self.model is None:
            raise RuntimeError("Model not loaded. Call _load_model() first.")
        
        try:
            logger.info(f"Generating embeddings for {len(valid_texts)} texts...")
            
            # Generate embeddings in batches
            all_embeddings = []
            
            for i in range(0, len(valid_texts), batch_size):
                batch_texts = valid_texts[i:i + batch_size]
                
                # Generate embeddings for current batch
                batch_embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=batch_size,
                    show_progress_bar=config.SHOW_PROGRESS
                )
                
                # Convert to float32 and add to results
                batch_embeddings = batch_embeddings.astype(np.float32)
                all_embeddings.extend(batch_embeddings)
                
                if config.SHOW_PROGRESS and i % (batch_size * 10) == 0:
                    logger.info(f"Processed {min(i + batch_size, len(valid_texts))}/{len(valid_texts)} texts")
            
            logger.info(f"Generated {len(all_embeddings)} embeddings successfully")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error in batch embedding generation: {str(e)}")
            # Return list of zero vectors as fallback
            dim = self.model.get_sentence_embedding_dimension() or 1024
            return [np.zeros(dim, dtype=np.float32) for _ in valid_texts]
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
            
        Returns:
            List of chunks with added 'embedding' field
        """
        if not chunks:
            logger.warning("No chunks provided for embedding")
            return []
        
        # Extract texts from chunks
        texts = [chunk.get('content', '') for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings_batch(texts)
        
        # Add embeddings to chunks
        embedded_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding['embedding'] = embedding
            embedded_chunks.append(chunk_with_embedding)
        
        logger.info(f"Added embeddings to {len(embedded_chunks)} chunks")
        return embedded_chunks
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        if self.model is None:
            return {'error': 'Model not loaded'}
        
        info = {
            'model_name': self.model_name,
            'device': self.device,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'max_sequence_length': getattr(self.model, 'max_seq_length', 'Unknown'),
            'pytorch_model': str(type(self.model._modules.get('0', 'Unknown')))
        }
        
        return info
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        try:
            # Compute cosine similarity (dot product since embeddings are normalized)
            similarity = np.dot(embedding1, embedding2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return 0.0