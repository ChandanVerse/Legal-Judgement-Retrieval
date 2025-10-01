"""
Flow 1: Create Vector Database from Judgments
Run this script to process PDFs and create the vector database
"""
from config import Config
from ingestion import JudgmentIngestor
from vectordb import VectorDatabase

def main():
    print("="*60)
    print("LEGAL RAG SYSTEM - DATABASE CREATION")
    print("="*60)
    
    # Initialize configuration
    config = Config()
    config.setup_directories()
    
    # Check if judgments directory has PDFs
    pdf_files = list(config.JUDGMENTS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"\nERROR: No PDF files found in {config.JUDGMENTS_DIR}")
        print("Please add PDF files to the judgments_pdf folder")
        return
    
    print(f"\nFound {len(pdf_files)} PDF files in judgments_pdf folder")
    
    # Initialize components
    print("\nInitializing components...")
    ingestor = JudgmentIngestor(config)
    vector_db = VectorDatabase(config)
    vector_db.initialize()
    
    # Process PDFs and create chunks
    print("\nProcessing PDFs...")
    documents = ingestor.process_directory(str(config.JUDGMENTS_DIR))
    
    if not documents:
        print("\nERROR: No documents created from PDFs")
        return
    
    # Add to vector database
    print("\nAdding documents to Pinecone...")
    vector_db.add_documents(documents)
    
    # Show statistics
    print("\n" + "="*60)
    print("DATABASE CREATION COMPLETE")
    print("="*60)
    stats = vector_db.get_stats()
    print(f"Total vectors in database: {stats['total_vectors']}")
    print(f"Embedding dimension: {stats['dimension']}")
    print(f"Index name: {config.PINECONE_INDEX_NAME}")
    print("="*60)

if __name__ == "__main__":
    main()