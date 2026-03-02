"""Run search pipeline"""
from pathlib import Path
from search import Searcher

# ============================================================
# CONFIGURATION - Modify these values as needed
# ============================================================
QUERY = "limitation period"     # Text query
PDF_PATH = None                 # Or set path like "data/test_case/sample.pdf"
TOP_K = 10                      # Number of results
# ============================================================

if __name__ == "__main__":
    searcher = Searcher()

    pdf = Path(PDF_PATH) if PDF_PATH else None

    results = searcher.search(
        query=QUERY,
        pdf_path=pdf,
        top_k=TOP_K
    )

    print(f"\n{'=' * 60}")
    print(f" TOP {len(results)} SIMILAR CASES")
    print(f"{'=' * 60}\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['case_id']}")
        print(f"   Score: {r['score']}")
        print()
