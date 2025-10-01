"""
Flow 2: Similarity Search
Run this script to search the vector database
"""
from config import Config
from vectordb import VectorDatabase

def display_results(results, query):
    """Display search results in a readable format"""
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    print("="*80)
    
    if not results:
        print("\nNo results found")
        return
    
    for i, result in enumerate(results, 1):
        print(f"\n{'-'*80}")
        print(f"RESULT #{i}")
        print(f"{'-'*80}")
        print(f"Similarity Score: {result['similarity_score']:.4f}")
        print(f"Source File: {result['metadata']['filename']}")
        print(f"Chunk: {result['metadata']['chunk_index'] + 1}/{result['metadata']['total_chunks']}")
        print(f"\nContent Preview:")
        print(f"{result['content'][:500]}...")
        print(f"{'-'*80}")

def main():
    print("="*80)
    print("LEGAL RAG SYSTEM - SIMILARITY SEARCH")
    print("="*80)
    
    # Initialize configuration
    config = Config()
    
    # Initialize vector database
    print("\nInitializing vector database...")
    vector_db = VectorDatabase(config)
    vector_db.initialize()
    
    # Check database status
    stats = vector_db.get_stats()
    print(f"\nDatabase Status:")
    print(f"  Total vectors: {stats['total_vectors']}")
    print(f"  Embedding dimension: {stats['dimension']}")
    
    if stats['total_vectors'] == 0:
        print("\nERROR: Database is empty!")
        print("Please run create_database.py first to populate the database")
        return
    
    # Interactive search loop
    print("\n" + "="*80)
    print("Enter your search queries (type 'exit' to quit)")
    print("="*80)
    
    while True:
        query = input("\nEnter query: ").strip()
        
        if query.lower() == 'exit':
            print("\nExiting search...")
            break
        
        if not query:
            print("Please enter a valid query")
            continue
        
        # Perform similarity search
        print("\nSearching...")
        results = vector_db.similarity_search(query, top_k=config.TOP_K_RETRIEVAL)
        
        # Display results
        display_results(results, query)

if __name__ == "__main__":
    main()