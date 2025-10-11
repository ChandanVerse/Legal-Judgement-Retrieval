"""
Flow 2: Similarity Search with Section Filtering
Run this script to search the vector database
"""
from dotenv import load_dotenv
load_dotenv()

from config import Config
from vectordb import VectorDatabase
from typing import Optional, List

def display_results(results, query, section_filter=None):
    """Display search results in a readable format with section information"""
    print("\n" + "="*80)
    print(f"QUERY: {query}")
    if section_filter:
        section_names = [Config.SECTION_DISPLAY_NAMES.get(s, s) for s in section_filter]
        print(f"SECTIONS: {', '.join(section_names)}")
    else:
        print(f"SECTIONS: All")
    print("="*80)

    if not results:
        print("\nNo results found")
        return

    # Group results by section for better display
    sections_dict = {}
    for result in results:
        section = result['metadata'].get('section', 'general')
        if section not in sections_dict:
            sections_dict[section] = []
        sections_dict[section].append(result)

    # Display results grouped by section
    for section, section_results in sections_dict.items():
        section_display = Config.SECTION_DISPLAY_NAMES.get(section, section)
        print(f"\n{'='*80}")
        print(f"SECTION: {section_display.upper()}")
        print(f"{'='*80}")

        for i, result in enumerate(section_results, 1):
            print(f"\n{'-'*80}")
            print(f"RESULT #{i}")
            print(f"{'-'*80}")
            print(f"Similarity Score: {result['similarity_score']:.4f}")
            print(f"Source File: {result['metadata']['filename']}")

            # Show section-specific metadata
            section_header = result['metadata'].get('section_header', '')
            if section_header:
                print(f"Section Header: {section_header}")

            chunk_info = result['metadata'].get('chunk_index', 0)
            total_chunks = result['metadata'].get('total_chunks_in_section',
                                                 result['metadata'].get('total_chunks', 0))
            if total_chunks > 0:
                print(f"Chunk: {chunk_info + 1}/{total_chunks} in this section")

            print(f"\nContent Preview:")
            content_preview = result['content'][:500]
            print(f"{content_preview}{'...' if len(result['content']) > 500 else ''}")
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
    print(f"  Collection name: {stats['collection_name']}")
    
    if stats['total_vectors'] == 0:
        print("\nERROR: Database is empty!")
        print("Please run create_database.py first to populate the database")
        return
    
    # Display available sections
    print("\n" + "="*80)
    print("AVAILABLE SECTIONS:")
    print("="*80)
    for i, section in enumerate(config.LEGAL_SECTIONS, 1):
        display_name = config.SECTION_DISPLAY_NAMES.get(section, section)
        print(f"  {i}. {section:25s} - {display_name}")

    # Interactive search loop
    print("\n" + "="*80)
    print("SEARCH INSTRUCTIONS")
    print("="*80)
    print("Enter your search query, then optionally filter by sections")
    print("Commands:")
    print("  'exit' - quit the program")
    print("  'sections' - show available sections")
    print("="*80)

    while True:
        query = input("\nEnter query: ").strip()

        if query.lower() == 'exit':
            print("\nExiting search...")
            break

        if query.lower() == 'sections':
            print("\nAvailable sections:")
            for i, section in enumerate(config.LEGAL_SECTIONS, 1):
                display_name = config.SECTION_DISPLAY_NAMES.get(section, section)
                print(f"  {i}. {section:25s} - {display_name}")
            continue

        if not query:
            print("Please enter a valid query")
            continue

        # Ask for section filtering
        print("\nFilter by sections? (Enter section names separated by commas, or press Enter for all)")
        print("Examples: facts,prayers  OR  grounds  OR  just press Enter")
        section_input = input("Sections: ").strip()

        section_filter = None
        if section_input:
            # Parse section input
            requested_sections = [s.strip().lower() for s in section_input.split(',')]
            # Validate sections
            valid_sections = [s for s in requested_sections if s in config.LEGAL_SECTIONS]

            if valid_sections:
                section_filter = valid_sections
                print(f"Filtering by: {', '.join(valid_sections)}")
            else:
                print(f"Warning: No valid sections found. Searching all sections.")

        # Perform similarity search
        print("\nSearching...")
        if section_filter:
            filter_dict = {"section": {"$in": section_filter}}
            results = vector_db.similarity_search(query, top_k=config.TOP_K_RETRIEVAL, filters=filter_dict)
        else:
            results = vector_db.similarity_search(query, top_k=config.TOP_K_RETRIEVAL)

        # Display results
        display_results(results, query, section_filter)

if __name__ == "__main__":
    main()