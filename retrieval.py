"""
Retrieval module for Legal Judgments Similarity Retrieval System.
Handles query processing and retrieval of most similar legal judgment chunks.
"""

from typing import List, Dict, Any, Optional
import config
import utils
from embeddings import EmbeddingGenerator
from vectordb import VectorDatabase

# Set up logging
logger = utils.setup_logging()

class SimilarityRetriever:
    """
    Handles query processing and similarity-based retrieval of legal judgment chunks.
    Integrates embedding generation with vector database search.
    """
    
    def __init__(self, embedding_generator: Optional[EmbeddingGenerator] = None, vector_db: Optional[VectorDatabase] = None):
        """
        Initialize the similarity retriever.
        
        Args:
            embedding_generator: EmbeddingGenerator instance (creates new if None)
            vector_db: VectorDatabase instance (creates new if None)
        """
        # Initialize components
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.vector_db = vector_db or VectorDatabase()
        
        logger.info("Initialized SimilarityRetriever")
    
    def process_query(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Process a query and retrieve most similar judgment chunks.
        
        Args:
            query: User query string
            top_k: Number of results to return (uses config default if None)
            
        Returns:
            List of result dictionaries with similarity scores and metadata
        """
        top_k = top_k or config.DEFAULT_TOP_K
        
        # Validate query
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        query = query.strip()
        logger.info(f"Processing query: '{query[:100]}...' (top_k={top_k})")
        
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_generator.generate_embedding(query)
            
            # Search for similar chunks
            similar_chunks = self.vector_db.search_similar(query_embedding, top_k)
            
            # Format results for display
            formatted_results = self._format_results(query, similar_chunks)
            
            logger.info(f"Retrieved {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return []
    
    def _format_results(self, query: str, similar_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format search results for display.
        
        Args:
            query: Original query string
            similar_chunks: Raw results from vector database
            
        Returns:
            Formatted results with rank, filename, score, and preview
        """
        formatted_results = []
        
        for rank, chunk in enumerate(similar_chunks, 1):
            metadata = chunk.get('metadata', {})
            content = chunk.get('content', '')
            similarity_score = chunk.get('similarity_score', 0.0)
            
            # Create formatted result
            result = {
                'rank': rank,
                'filename': metadata.get('filename', 'Unknown'),
                'score': similarity_score,
                'preview': utils.format_preview(content),
                'full_content': content,  # Keep full content for potential detailed view
                'metadata': metadata,
                'query': query
            }
            
            formatted_results.append(result)
        
        return formatted_results
    
    def interactive_search(self) -> None:
        """
        Run interactive search loop in terminal.
        Continuously accepts queries until user types 'exit'.
        """
        utils.print_banner()
        print("Type your legal queries below. Type 'exit' to quit, 'help' for commands.\n")
        
        # Check if database is populated
        if not self.vector_db.collection_exists_and_populated():
            print("⚠️  No documents found in database. Please ensure PDFs are ingested first.")
            return
        
        # Display collection statistics
        stats = self.vector_db.get_collection_stats()
        print(f"📊 Database Stats: {stats.get('total_chunks', 0)} chunks from legal judgments\n")
        
        while True:
            try:
                # Get user input
                query = input("🔍 Enter your query: ").strip()
                
                # Handle special commands
                if query.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye! Thank you for using Legal RAG System.")
                    break
                
                elif query.lower() in ['help', 'h']:
                    self._show_help()
                    continue
                
                elif query.lower() in ['stats', 'status']:
                    self._show_stats()
                    continue
                
                elif query.lower().startswith('top '):
                    # Allow user to change top_k, e.g., "top 10 contract law"
                    parts = query.split(' ', 2)
                    if len(parts) >= 3 and parts[1].isdigit():
                        top_k = int(parts[1])
                        query = parts[2]
                        print(f"🔧 Changed results limit to {top_k}")
                    else:
                        print("❌ Invalid format. Use: top <number> <query>")
                        continue
                else:
                    top_k = config.DEFAULT_TOP_K
                
                # Skip empty queries
                if not query:
                    print("⚠️  Please enter a valid query or type 'help' for commands.")
                    continue
                
                # Process the query
                print(f"\n🔎 Searching for: '{query}'...")
                results = self.process_query(query, top_k)
                
                # Display results
                if results:
                    utils.print_results_table(results)
                    self._show_result_actions(results)
                else:
                    print("❌ No relevant results found. Try rephrasing your query.")
                
                print()  # Add spacing between searches
                
            except KeyboardInterrupt:
                print("\n\n👋 Search interrupted. Goodbye!")
                break
            
            except Exception as e:
                logger.error(f"Error in interactive search: {str(e)}")
                print(f"❌ An error occurred: {str(e)}")
                print("Please try again or type 'exit' to quit.\n")
    
    def _show_help(self) -> None:
        """Display help information."""
        help_text = """
    📖 Legal RAG System - Help
    
    Commands:
    • Just type your query to search legal judgments
    • 'exit' or 'quit' - Exit the system
    • 'help' - Show this help message
    • 'stats' - Show database statistics
    • 'top <N> <query>' - Change number of results (e.g., 'top 10 contract law')
    
    Query Examples:
    • "constitutional rights and privacy"
    • "breach of contract damages"
    • "criminal procedure and evidence"
    • "property law and ownership"
    
    Tips:
    • Use specific legal terms for better results
    • Longer, descriptive queries often work better
    • Results are ranked by semantic similarity
        """
        print(help_text)
    
    def _show_stats(self) -> None:
        """Display database statistics."""
        stats = self.vector_db.get_collection_stats()
        model_info = self.embedding_generator.get_model_info()
        
        print("\n📊 System Statistics:")
        utils.print_separator()
        print(f"Database Collection: {stats.get('collection_name', 'Unknown')}")
        print(f"Total Chunks: {stats.get('total_chunks', 0)}")
        print(f"Storage Location: {stats.get('persist_directory', 'Unknown')}")
        print(f"Embedding Model: {model_info.get('model_name', 'Unknown')}")
        print(f"Embedding Dimension: {model_info.get('embedding_dimension', 'Unknown')}")
        print(f"Device: {model_info.get('device', 'Unknown')}")
        utils.print_separator()
    
    def _show_result_actions(self, results: List[Dict[str, Any]]) -> None:
        """
        Show available actions after displaying results.
        
        Args:
            results: List of search results
        """
        if not results:
            return
        
        print(f"\n💡 Actions: Type a number (1-{len(results)}) to view full content, or press Enter for new search")
        
        try:
            action = input("Action: ").strip()
            
            if action.isdigit():
                result_idx = int(action) - 1
                if 0 <= result_idx < len(results):
                    self._show_full_content(results[result_idx])
                else:
                    print("❌ Invalid result number.")
        
        except (ValueError, KeyboardInterrupt):
            pass  # Just continue to next search
    
    def _show_full_content(self, result: Dict[str, Any]) -> None:
        """
        Display full content of a selected result.
        
        Args:
            result: Result dictionary
        """
        utils.print_separator("═")
        print(f"📄 Full Content - {result['filename']} (Rank {result['rank']})")
        print(f"🎯 Similarity Score: {result['score']:.4f}")
        utils.print_separator("─")
        print(result['full_content'])
        utils.print_separator("═")
        
        input("\nPress Enter to continue...")
    
    def batch_search(self, queries: List[str], top_k: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process multiple queries in batch.
        
        Args:
            queries: List of query strings
            top_k: Number of results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        top_k = top_k or config.DEFAULT_TOP_K
        results = {}
        
        logger.info(f"Processing {len(queries)} queries in batch mode")
        
        for i, query in enumerate(queries):
            logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")
            
            query_results = self.process_query(query, top_k)
            results[query] = query_results
        
        logger.info(f"Completed batch processing of {len(queries)} queries")
        return results
    
    def export_results(self, results: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Export search results to a file.
        
        Args:
            results: Search results to export
            output_file: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            # Prepare results for export (remove large content fields)
            export_data = []
            for result in results:
                export_result = {
                    'rank': result['rank'],
                    'filename': result['filename'],
                    'score': result['score'],
                    'preview': result['preview'],
                    'query': result['query']
                }
                export_data.append(export_result)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(results)} results to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export results: {str(e)}")
            return False