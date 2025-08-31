"""
Legal Judgement Retrieval & Reasoning System - Main FastAPI Server
"""
import os
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

from config import Config
from ingestion import JudgmentIngestor
from vectordb import VectorDatabase
from rag import RAGSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Legal Judgement RAG System",
    description="Retrieve and reason about legal judgments using RAG",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config()
ingestor = JudgmentIngestor(config)
vector_db = VectorDatabase(config)
rag_system = RAGSystem(config, vector_db)

# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    filters: Optional[List[str]] = None  # ['facts', 'grounds', 'prayers']
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    total_results: int

class IngestResponse(BaseModel):
    message: str
    processed_files: List[str]
    total_chunks: int

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    logger.info("Starting Legal Judgement RAG System...")
    
    # Ensure data directories exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.CHROMA_STORE_PATH, exist_ok=True)
    
    # Initialize vector database
    await vector_db.initialize()
    logger.info("System initialized successfully!")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Legal Judgement RAG System is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check if vector DB is accessible
        collection_count = await vector_db.get_collection_count()
        return {
            "status": "healthy",
            "vector_db": "connected",
            "total_documents": collection_count
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_judgments(files: List[UploadFile] = File(...)):
    """
    Ingest new judgment PDFs into the system
    """
    try:
        logger.info(f"Starting ingestion of {len(files)} files")
        
        # Save uploaded files temporarily
        temp_files = []
        for file in files:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"Only PDF files are supported. Got: {file.filename}")
            
            file_path = Path(config.DATA_DIR) / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            temp_files.append(str(file_path))
        
        # Process files
        processed_files = []
        total_chunks = 0
        
        for file_path in temp_files:
            try:
                # Extract text and chunk
                chunks = ingestor.process_pdf(file_path)
                
                # Generate embeddings and store
                await vector_db.add_documents(chunks, {"filename": Path(file_path).name})
                
                processed_files.append(Path(file_path).name)
                total_chunks += len(chunks)
                
                logger.info(f"Processed {Path(file_path).name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        return IngestResponse(
            message=f"Successfully processed {len(processed_files)} files",
            processed_files=processed_files,
            total_chunks=total_chunks
        )
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_judgments(request: QueryRequest):
    """
    Query the judgment database using RAG
    """
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Perform RAG query
        result = await rag_system.query(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k
        )
        
        return QueryResponse(
            query=request.query,
            answer=result["answer"],
            sources=result["sources"],
            total_results=len(result["sources"])
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    """
    List all ingested documents
    """
    try:
        documents = await vector_db.list_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Delete a specific document from the database
    """
    try:
        success = await vector_db.delete_document(filename)
        if success:
            return {"message": f"Document {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.post("/clear")
async def clear_database():
    """
    Clear all documents from the database (use with caution)
    """
    try:
        await vector_db.clear_collection()
        return {"message": "Database cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info" if config.DEBUG else "warning"
    )