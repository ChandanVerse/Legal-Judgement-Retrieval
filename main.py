"""CLI entry point"""
import argparse
import sys
from pathlib import Path
import config


def cmd_test(args):
    """Test system components"""
    from embedder import Embedder
    from pinecone_db import PineconeDB

    print("=" * 50)
    print(" LEGAL CASE SIMILARITY - SYSTEM TEST")
    print("=" * 50)

    all_passed = True

    # Test Embedder (sentence-transformers)
    print("\n[Embedder - sentence-transformers]")
    try:
        embedder = Embedder()
        emb = embedder.embed("This is a test sentence.")
        print(f"  Model: {config.EMBEDDING_MODEL}")
        print(f"  Device: {embedder.device}")
        print(f"  Dimension: {len(emb)}")
    except Exception as e:
        print(f"  ERROR: {e}")
        all_passed = False

    # Test Pinecone
    print("\n[Pinecone]")
    try:
        db = PineconeDB()
        db.connect()
        stats = db.stats()
        print(f"  Index: {config.PINECONE_INDEX}")
        print(f"  Vectors: {stats.total_vector_count}")
    except Exception as e:
        print(f"  ERROR: {e}")
        all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print(" ALL TESTS PASSED")
    else:
        print(" SOME TESTS FAILED")
    print("=" * 50)


def cmd_ingest(args):
    """Ingest PDFs"""
    from ingest import Ingester

    ingester = Ingester()
    ingester.ingest_all(limit=args.limit, reset=args.reset)


def cmd_search(args):
    """Search for similar cases"""
    from search import Searcher

    searcher = Searcher()

    # Determine query type
    pdf_path = None
    query = args.text

    if args.query:
        p = Path(args.query)
        if p.exists() and p.suffix == ".pdf":
            pdf_path = p
        else:
            query = args.query

    if not query and not pdf_path:
        query = input("Enter search query: ")

    # Search
    results = searcher.search(
        query=query, pdf_path=pdf_path, top_k=args.top_k
    )

    # Display
    print(f"\n{'='*50}")
    print(f" TOP {len(results)} SIMILAR CASES")
    print(f"{'='*50}\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['case_id']}")
        print(f"   Score: {r['score']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Legal Case Similarity Search")
    subparsers = parser.add_subparsers(dest="command")

    # test
    p_test = subparsers.add_parser("test", help="Test system components")
    p_test.set_defaults(func=cmd_test)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest PDFs")
    p_ingest.add_argument("--reset", action="store_true", help="Clear index first")
    p_ingest.add_argument("--limit", type=int, help="Limit number of PDFs")
    p_ingest.set_defaults(func=cmd_ingest)

    # search
    p_search = subparsers.add_parser("search", help="Search similar cases")
    p_search.add_argument("query", nargs="?", help="Search query or PDF path")
    p_search.add_argument("-q", "--text", help="Text query")
    p_search.add_argument(
        "-k", "--top-k", type=int, default=10, help="Number of results"
    )
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
