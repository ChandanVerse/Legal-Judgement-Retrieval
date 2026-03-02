"""Test script to verify all system components are working"""
import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported"""
    print("\n[1] Testing imports...")
    try:
        import config
        from embedder import Embedder
        from pinecone_db import PineconeDB
        from ingest import extract_text, chunk_text, case_id_from_path, hash_text, Ingester
        from search import Searcher
        print("    OK - All modules imported successfully")
        return True
    except ImportError as e:
        print(f"    FAIL - Import error: {e}")
        return False


def test_config():
    """Test configuration"""
    print("\n[2] Testing configuration...")
    import config

    errors = []
    if not config.PINECONE_API_KEY:
        errors.append("PINECONE_API_KEY not set")
    if not config.DATASET_DIR.exists():
        errors.append(f"Dataset dir not found: {config.DATASET_DIR}")

    if errors:
        for e in errors:
            print(f"    FAIL - {e}")
        return False

    print(f"    OK - Pinecone API key: {config.PINECONE_API_KEY[:10]}...")
    print(f"    OK - Dataset dir: {config.DATASET_DIR}")
    print(f"    OK - Embedding model: {config.EMBEDDING_MODEL}")
    return True


def test_cuda():
    """Test CUDA availability"""
    print("\n[3] Testing CUDA...")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"    OK - CUDA available")
            print(f"    OK - Device: {torch.cuda.get_device_name(0)}")
            return True
        else:
            print("    WARN - CUDA not available, using CPU (slower)")
            return True  # Not a failure, just slower
    except Exception as e:
        print(f"    WARN - {e}")
        return True


def test_embedder():
    """Test sentence-transformers embedder"""
    print("\n[4] Testing Embedder (sentence-transformers)...")
    from embedder import Embedder

    try:
        embedder = Embedder()
        emb = embedder.embed("This is a test sentence for embedding.")
        if len(emb) == 768:
            print(f"    OK - Device: {embedder.device}")
            print(f"    OK - Dimension: {len(emb)}")
            return True
        else:
            print(f"    FAIL - Expected 768 dimensions, got {len(emb)}")
            return False
    except Exception as e:
        print(f"    FAIL - Embedder error: {e}")
        return False


def test_embedder_batch():
    """Test batch embedding"""
    print("\n[5] Testing batch embedding...")
    from embedder import Embedder
    import time

    embedder = Embedder()
    texts = ["Test sentence " + str(i) for i in range(10)]

    try:
        start = time.time()
        embeddings = embedder.embed_batch(texts)
        elapsed = time.time() - start
        print(f"    OK - Embedded {len(texts)} texts in {elapsed:.2f}s")
        print(f"    OK - Speed: {len(texts)/elapsed:.1f} texts/sec")
        return True
    except Exception as e:
        print(f"    FAIL - Batch embedding error: {e}")
        return False


def test_pinecone_connection():
    """Test Pinecone connection"""
    print("\n[6] Testing Pinecone connection...")
    from pinecone_db import PineconeDB
    import config

    try:
        db = PineconeDB()
        db.connect()
        stats = db.stats()
        print(f"    OK - Connected to index: {config.PINECONE_INDEX}")
        print(f"    OK - Current vectors: {stats.total_vector_count}")
        return True
    except Exception as e:
        print(f"    FAIL - Pinecone error: {e}")
        return False


def test_pinecone_operations():
    """Test Pinecone upsert/search/delete"""
    print("\n[7] Testing Pinecone operations...")
    from pinecone_db import PineconeDB
    from embedder import Embedder

    db = PineconeDB()
    db.connect()
    embedder = Embedder()

    # Test upsert
    test_id = "test_vector_12345"
    try:
        emb = embedder.embed("Test document for Pinecone operations")
        db.upsert([{
            "id": test_id,
            "values": emb,
            "metadata": {"cid": "test_case"}
        }])
        print("    OK - Upsert successful")
    except Exception as e:
        print(f"    FAIL - Upsert error: {e}")
        return False

    # Test search
    try:
        import time
        time.sleep(1)  # Wait for indexing
        results = db.search(emb, top_k=1)
        if results and results[0]["id"] == test_id:
            print("    OK - Search successful")
        else:
            print("    WARN - Search returned unexpected results")
    except Exception as e:
        print(f"    FAIL - Search error: {e}")
        return False

    # Cleanup
    try:
        db.index.delete(ids=[test_id])
        print("    OK - Cleanup successful")
    except Exception as e:
        print(f"    WARN - Cleanup failed: {e}")

    return True


def test_pdf_extraction():
    """Test PDF text extraction"""
    print("\n[8] Testing PDF extraction...")
    from ingest import extract_text, chunk_text
    import config

    pdfs = list(config.DATASET_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"    FAIL - No PDFs found in {config.DATASET_DIR}")
        return False

    pdf = pdfs[0]
    try:
        text = extract_text(pdf)
        if len(text) > 100:
            print(f"    OK - Extracted {len(text)} chars from {pdf.name}")
        else:
            print(f"    WARN - Very short text ({len(text)} chars)")

        chunks = chunk_text(text)
        print(f"    OK - Split into {len(chunks)} chunks")
        return True
    except Exception as e:
        print(f"    FAIL - Extraction error: {e}")
        return False


def main():
    print("=" * 60)
    print(" LEGAL CASE SIMILARITY - FULL SYSTEM TEST")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("CUDA", test_cuda),
        ("Embedder", test_embedder),
        ("Batch Embedding", test_embedder_batch),
        ("Pinecone Connection", test_pinecone_connection),
        ("Pinecone Operations", test_pinecone_operations),
        ("PDF Extraction", test_pdf_extraction),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"    FATAL - {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "PASS" if p else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\n  {passed}/{total} tests passed")

    if passed == total:
        print("\n  ALL TESTS PASSED - System ready for ingestion")
        print("=" * 60)
        return 0
    else:
        print("\n  SOME TESTS FAILED - Fix issues before ingestion")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
