"""
Vector database operations using Pinecone
"""
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any
from langchain.schema import Document
import uuid
from sentence_transformers import SentenceTransformer

class VectorDatabase:
    """Pinecone vector database for legal judgment embeddings"""
    
    def __init__(self, config):
        self.config = config
        self.pc = None
        self.index = None
        self.embedding_model = None
        self.embedding_dim = None
    
    def initialize(self):
        """Initialize Pinecone and embedding model"""
        print("Initializing embedding model with ONNX Runtime...")
        
        # Verify CUDA availability
        import torch
        if self.config.EMBEDDING_DEVICE == "cuda":
            if torch.cuda.is_available():
                print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
                print("✓ Using ONNX Runtime GPU for faster inference")
            else:
                print("✗ CUDA not available, falling back to CPU")
                self.config.EMBEDDING_DEVICE = "cpu"
        
        # Load model with ONNX Runtime backend
        self.embedding_model = SentenceTransformer(
            self.config.EMBEDDING_MODEL,
            device=self.config.EMBEDDING_DEVICE,
            backend="onnx",  # Use ONNX Runtime for optimized inference
            trust_remote_code=True,
            model_kwargs={"file_name": "onnx/model.onnx"}  # Specify the ONNX model file
        )
        
        # Get embedding dimension
        test_embedding = self.embedding_model.encode(["test"])
        self.embedding_dim = test_embedding.shape[1]
        print(f"Embedding dimension: {self.embedding_dim}")
        
        # Initialize Pinecone
        print("Initializing Pinecone...")
        self.pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
        
        index_name = self.config.PINECONE_INDEX_NAME
        
        # Create index if it doesn't exist
        if index_name not in self.pc.list_indexes().names():
            print(f"Creating index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=self.embedding_dim,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.config.PINECONE_ENVIRONMENT
                )
            )
        
        self.index = self.pc.Index(index_name)
        print("Vector database initialized successfully")
    
    def generate_embeddings(self, texts: List[str]):
        """Generate embeddings for texts"""
        return self.embedding_model.encode(
            texts, 
            convert_to_tensor=False, 
            normalize_embeddings=True
        )
    
    def add_documents(self, documents: List[Document]):
        """Add documents to Pinecone"""
        if not documents:
            return
        
        print(f"Adding {len(documents)} documents to vector database...")
        
        texts = [doc.page_content for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        vectors = []
        for i, doc in enumerate(documents):
            doc_id = str(uuid.uuid4())
            metadata = doc.metadata.copy()
            metadata['content'] = doc.page_content
            
            vectors.append({
                "id": doc_id,
                "values": embeddings[i].tolist(),
                "metadata": metadata
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
        
        print(f"Successfully added {len(documents)} documents")
    
    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform similarity search"""
        query_embedding = self.generate_embeddings([query])[0].tolist()
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
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
    
    def get_stats(self):
        """Get index statistics"""
        stats = self.index.describe_index_stats()
        return {
            'total_vectors': stats.get('total_vector_count', 0),
            'dimension': stats.get('dimension', 0)
        }