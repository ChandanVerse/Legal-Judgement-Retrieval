"""
Main entry point for Legal Judgments Similarity Retrieval System.
Orchestrates the complete pipeline: PDF ingestion -> chunking -> embeddings -> storage -> interactive search.

Usage:
    python main.py

The system will:
1. Check for existing vector database
2. If not found, process PDFs from ./data/judgments/ directory
3. Launch interactive search interface
"""

import sys
import time
from pathlib import Path
from typing import Optional

# Import all modules
import config
import utils
from ingestion import DocumentIngestion
from chunking import DocumentChunker
from embeddings import EmbeddingGenerator
from vectordb import VectorDatabase
from retrieval import SimilarityRetriever

# Set up logging
logger = utils.setup_logging()

class LegalRAGSystem:
    """
    Main orchestrator for the Legal Judgments Similarity Retrieval System.
    Handles the complete pipeline from document ingestion to interactive search.
    """
    
    def __init__(self):
        """Initialize the Legal RAG System."""
        self.ingestion = None
        self.chunker = None
        self.embedding_generator = None
        self.vector_db = None
        self.retriever = None
        
        logger.info("Initialized Legal RAG System")
    
    def setup_components(self) -> bool:
        """
        Initialize all system components.
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        try:
            logger.info("Setting up system components...")
            
            # Initialize document ingestion
            self.ingestion = DocumentIngestion()
            
            # Initialize chunker
            self.chunker = DocumentChunker()
            
            # Initialize embedding generator (this may take time for model download)
            logger.info("Loading embedding model (this may take a few minutes on first run)...")
            self.embedding_generator = EmbeddingGenerator()
            
            # Initialize vector database
            self.vector_db = VectorDatabase()
            
            # Initialize retriever
            self.retriever = SimilarityRetriever(
                embedding_generator=self.embedding_generator,
                vector_db=self.vector_db
            )
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup components: {str(e)}")
            return False
    
    def check_data_directory(self) -> bool:
        """
        Check if data directory exists and contains PDF files.
        
        Returns:
            True if PDFs found, False otherwise
        """
        data_dir = config.DATA_DIR
        
        if not data_dir.exists():
            logger.error(f"Data directory not found: {data_dir}")
            print(f"❌ Data directory not found: {data_dir}")
            print(f"📁 Please create the directory and add PDF files: {data_dir}")
            return False
        
        pdf_files = utils.get_file_list(data_dir, config.SUPPORTED_FORMATS)
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {data_dir}")
            print(f"📂 Data directory exists but no PDF files found: {data_dir}")
            print(f"📄 Please add PDF files to: {data_dir}")
            print(f"🔧 Supported formats: {', '.join(config.SUPPORTED_FORMATS)}")
            return False
        
        logger.info(f"Found {len(pdf_files)} PDF files in data directory")
        return True
    
    def ingest_and_process_documents(self) -> bool:
        """
        Complete document processing pipeline: ingest -> chunk -> embed -> store.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting document processing pipeline...")
            
            # Step 1: Ingest documents
            print("📖 Step 1: Loading PDF documents...")
            documents = self.ingestion.load_documents()
            
            if not documents:
                print("❌ No documents could be loaded. Check your PDF files.")
                return False
            
            print(f"✅ Loaded {len(documents)} documents")
            
            # Step 2: Chunk documents
            print("✂️  Step 2: Splitting documents into chunks...")
            chunks = self.chunker.chunk_documents(documents)
            
            if not chunks:
                print("❌ No chunks created from documents.")
                return False
            
            print(f"✅ Created {len(chunks)} chunks")
            
            # Display chunk statistics
            chunk_stats = self.chunker.get_chunk_statistics(chunks)
            print(f"📊 Average chunk size: {chunk_stats.get('avg_chunk_size', 0):.0f} characters")
            
            # Step 3: Generate embeddings
            print("🧮 Step 3: Generating embeddings (this may take several minutes)...")
            chunks_with_embeddings = self.embedding_generator.embed_chunks(chunks)
            
            if not chunks_with_embeddings:
                print("❌ Failed to generate embeddings.")
                return False
            
            print(f"✅ Generated embeddings for {len(chunks_with_embeddings)} chunks")
            
            # Step 4: Store in vector database
            print("💾 Step 4: Storing embeddings in vector database...")
            storage_success = self.vector_db.store_embeddings(chunks_with_embeddings)
            
            if not storage_success:
                print("❌ Failed to store embeddings in database.")
                return False
            
            print("✅ Successfully stored all embeddings")
            
            # Display final statistics
            db_stats = self.vector_db.get_collection_stats()
            print(f"\n📈 Processing Complete!")
            print(f"   📊 Total chunks stored: {db_stats.get('total_chunks', 0)}")
            print(f"   🏛️  Database location: {db_stats.get('persist_directory', 'Unknown')}")
            
            logger.info("Document processing pipeline completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in document processing pipeline: {str(e)}")
            print(f"❌ Pipeline error: {str(e)}")
            return False
    
    def run_interactive_search(self) -> None:
        """Launch the interactive search interface."""
        try:
            logger.info("Starting interactive search interface")
            self.retriever.interactive_search()
            
        except Exception as e:
            logger.error(f"Error in interactive search: {str(e)}")
            print(f"❌ Search interface error: {str(e)}")
    
    def run(self) -> None:
        """
        Main execution flow of the Legal RAG System.
        """
        # Print welcome banner
        utils.print_banner()
        
        # Check data directory
        print("🔍 Checking for PDF files...")
        if not self.check_data_directory():
            print("\n💡 To get started:")
            print(f"   1. Create directory: {config.DATA_DIR}")
            print("   2. Add your PDF legal judgment files")
            print("   3. Run this script again")
            sys.exit(1)
        
        # Setup system components
        print("⚙️  Initializing system components...")
        if not self.setup_components():
            print("❌ Failed to initialize system. Check the logs for details.")
            sys.exit(1)
        
        # Check if database is already populated
        if self.vector_db.collection_exists_and_populated():
            print("✅ Found existing vector database with processed documents")
            
            # Ask user if they want to reprocess or use existing
            response = input("Do you want to reprocess documents? (y/N): ").strip().lower()
            
            if response in ['y', 'yes']:
                print("🔄 Reprocessing documents...")
                # Delete existing collection and reprocess
                self.vector_db.delete_collection()
                
                if not self.ingest_and_process_documents():
                    print("❌ Failed to reprocess documents.")
                    sys.exit(1)
            else:
                print("📚 Using existing processed documents")
        else:
            # No existing database, process documents
            print("🆕 No existing database found. Processing documents...")
            
            if not self.ingest_and_process_documents():
                print("❌ Failed to process documents.")
                sys.exit(1)
        
        # Launch interactive search
        print("\n🚀 Launching interactive search interface...")
        print("   (Press Ctrl+C to exit at any time)")
        
        try:
            self.run_interactive_search()
        except KeyboardInterrupt:
            print("\n\n👋 System interrupted. Goodbye!")
            sys.exit(0)


def main():
    """Main entry point."""
    try:
        # Create and run the system
        system = LegalRAGSystem()
        system.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 System interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        print(f"❌ Fatal error: {str(e)}")
        print("Please check the logs for detailed error information.")
        sys.exit(1)


if __name__ == "__main__":
    main()