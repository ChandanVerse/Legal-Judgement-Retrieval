"""
Flow 1: Create Vector Database from Judgments
Run this script to process PDFs and create the vector database
"""
from dotenv import load_dotenv
load_dotenv()

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
    print("\nAdding documents to ChromaDB...")
    vector_db.add_documents(documents)
    
    # Show statistics
    print("\n" + "="*60)
    print("DATABASE CREATION COMPLETE")
    print("="*60)
    stats = vector_db.get_stats()
    print(f"Total vectors in database: {stats['total_vectors']}")
    print(f"Embedding dimension: {stats['dimension']}")
    print(f"Collection name: {stats['collection_name']}")
    print(f"Database path: {config.CHROMA_DB_PATH}")

    # Show section distribution
    if stats.get('sections'):
        print("\nSection Distribution:")
        for section, count in sorted(stats['sections'].items(), key=lambda x: x[1], reverse=True):
            display_name = config.SECTION_DISPLAY_NAMES.get(section, section)
            percentage = (count / stats['total_vectors']) * 100
            print(f"  {display_name:30s}: {count:5d} chunks ({percentage:.1f}%)")

    print("="*60)

if __name__ == "__main__":
    main()