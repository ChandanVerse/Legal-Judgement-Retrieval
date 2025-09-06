"""
Legal Judgement Retrieval & Reasoning System - Main FastAPI Server
"""
import os
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from config import Config
from ingestion import JudgmentIngestor
from vectordb import VectorDatabase
from rag import RAGSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for system components
config = None
ingestor = None
vector_db = None
rag_system = None

async def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files after processing"""
    for path in file_paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Error cleaning up {path}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper async initialization"""
    global config, ingestor, vector_db, rag_system
    
    # Startup
    logger.info("Starting Legal Judgement RAG System...")
    try:
        # Initialize configuration
        config = Config()
        await asyncio.sleep(0)  # Yield control
        
        # Initialize components with timeouts
        try:
            async with asyncio.timeout(60):  # 60 second timeout
                ingestor = JudgmentIngestor(config)
                vector_db = VectorDatabase(config)
                await vector_db.initialize()
                rag_system = RAGSystem(config, vector_db)
                await rag_system.initialize()
        except asyncio.TimeoutError:
            logger.error("System initialization timed out")
            raise RuntimeError("System initialization timed out")
        
        logger.info("System initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise
    
    yield
    
    # Shutdown cleanup
    logger.info("Shutting down Legal Judgement RAG System...")
    try:
        await asyncio.gather(
            vector_db.clear_collection() if vector_db else asyncio.sleep(0),
            # Add other cleanup tasks here
        )
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Legal Judgement RAG System",
    description="Retrieve and reason about legal judgments using RAG",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def check_system_ready():
    """Check if all system components are initialized"""
    if not all([config, ingestor, vector_db, rag_system]):
        raise HTTPException(
            status_code=503, 
            detail="System not fully initialized. Please wait and try again."
        )
    
    if not vector_db._model_initialized:
        raise HTTPException(
            status_code=503,
            detail="Embedding model not ready. Please wait for initialization to complete."
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Legal Judgement RAG System is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check system initialization
        if not all([config, vector_db]):
            return {
                "status": "initializing",
                "message": "System is still starting up"
            }
        
        # Check if vector DB is accessible
        collection_count = await vector_db.get_collection_count()
        
        return {
            "status": "healthy",
            "vector_db": "connected",
            "embedding_model": "ready" if vector_db._model_initialized else "loading",
            "total_documents": collection_count
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "vector_db": "disconnected"
        }

@app.post("/ingest", response_model=IngestResponse)
async def ingest_judgments(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks
):
    """
    Ingest new judgment PDFs into the system
    """
    temp_files: List[str] = []
    try:
        check_system_ready()
        
        logger.info(f"Starting ingestion of {len(files)} files")
        
        # Validate file size and count
        if len(files) > config.MAX_FILES_PER_REQUEST:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many files. Maximum {config.MAX_FILES_PER_REQUEST} files per request."
            )
        
        # Create data directory if it doesn't exist
        data_dir = Path(config.DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save and process files
        for file in files:
            if not file.filename or not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only PDF files are supported. Got: {file.filename}"
                )
            
            content = await file.read()
            if len(content) > config.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large. Maximum size: {config.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            # Use secure filename
            safe_filename = Path(file.filename).name
            file_path = data_dir / safe_filename
            
            # Write file safely
            try:
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                temp_files.append(str(file_path))
            except OSError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save file {safe_filename}: {str(e)}"
                )

        # Process files
        processed_files = []
        total_chunks = 0
        
        for file_path in temp_files:
            try:
                # Extract text and chunk
                chunks = ingestor.process_pdf(file_path)
                
                if not chunks:
                    logger.warning(f"No content extracted from {file_path}")
                    continue
                
                # Generate embeddings and store
                await vector_db.add_documents(chunks, {"filename": Path(file_path).name})
                
                processed_files.append(Path(file_path).name)
                total_chunks += len(chunks)
                
                logger.info(f"Processed {Path(file_path).name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        if not processed_files:
            raise HTTPException(
                status_code=400,
                detail="No files could be processed successfully"
            )
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_files, temp_files)
        
        return IngestResponse(
            message=f"Successfully processed {len(processed_files)} files",
            processed_files=processed_files,
            total_chunks=total_chunks
        )
        
    except HTTPException:
        # Clean up on error
        await cleanup_temp_files(temp_files)
        raise
    except Exception as e:
        # Clean up on error
        await cleanup_temp_files(temp_files)
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_judgments(request: QueryRequest):
    """
    Query the judgment database using RAG
    """
    try:
        check_system_ready()
        
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Validate query
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Validate top_k parameter
        if request.top_k and (request.top_k < 1 or request.top_k > 20):
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 20")
        
        # Perform RAG query
        result = await rag_system.query(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k or 5
        )
        
        return QueryResponse(
            query=request.query,
            answer=result["answer"],
            sources=result["sources"],
            total_results=len(result["sources"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    """
    List all ingested documents
    """
    try:
        check_system_ready()
        
        documents = await vector_db.list_documents()
        return {"documents": documents}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Delete a specific document from the database
    """
    try:
        check_system_ready()
        
        if not filename.strip():
            raise HTTPException(status_code=400, detail="Filename cannot be empty")
        
        success = await vector_db.delete_document(filename)
        if success:
            return {"message": f"Document {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.post("/clear")
async def clear_database():
    """
    Clear all documents from the database (use with caution)
    """
    try:
        check_system_ready()
        
        await vector_db.clear_collection()
        return {"message": "Database cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        check_system_ready()
        
        total_docs = await vector_db.get_collection_count()
        documents = await vector_db.list_documents()
        
        stats = {
            "total_chunks": total_docs,
            "unique_documents": len(documents),
            "sections_available": list(set(
                section for doc in documents 
                for section in doc.get('sections', [])
            )),
            "model_info": {
                "embedding_model": config.EMBEDDING_MODEL,
                "llm_model": config.LLM_MODEL,
                "embedding_device": config.EMBEDDING_DEVICE
            }
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/config")
async def get_config():
    """Get current system configuration (safe subset)"""
    try:
        safe_config = {
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "top_k_retrieval": config.TOP_K_RETRIEVAL,
            "similarity_threshold": config.SIMILARITY_THRESHOLD,
            "legal_sections": config.LEGAL_SECTIONS,
            "max_file_size_mb": config.MAX_FILE_SIZE // (1024 * 1024),
            "max_files_per_request": config.MAX_FILES_PER_REQUEST
        }
        return safe_config
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

if __name__ == "__main__":
    # Initialize config for running directly
    config = Config()
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info" if config.DEBUG else "warning"
    )