"""Search pipeline with AWS DynamoDB snippet retrieval"""
from pathlib import Path
from embedder import Embedder
from pinecone_db import PineconeDB
from aws_db import AWSStorage
from ingest import extract_text, chunk_text


class Searcher:
    def __init__(self):
        self.embedder = Embedder()  # sentence-transformers (fast GPU)
        self.db = PineconeDB()
        self.db.connect()
        self.storage = AWSStorage()  # AWS DynamoDB for snippets

    def search(
        self,
        query: str = None,
        pdf_path: Path = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Search for similar cases with adaptive chunking"""

        CHUNK_THRESHOLD = 500  # Characters

        if pdf_path:
            # PDF search: embed chunks, aggregate results
            text = extract_text(pdf_path)
            chunks = chunk_text(text)

            # Batch embed all chunks at once (fast)
            chunks_to_search = chunks[:10]  # Limit chunks for speed
            embeddings = self.embedder.embed_batch(chunks_to_search)

            all_results = []
            for emb in embeddings:
                results = self.db.search(emb, top_k=top_k * 2)
                all_results.extend(results)

        elif len(query) >= CHUNK_THRESHOLD:
            # Long text: chunk and search each
            chunks = chunk_text(query)
            if not chunks:
                chunks = [query]  # Fallback if no valid chunks

            chunks_to_search = chunks[:10]
            embeddings = self.embedder.embed_batch(chunks_to_search)

            all_results = []
            for emb in embeddings:
                results = self.db.search(emb, top_k=top_k * 2)
                all_results.extend(results)

        else:
            # Short query: single embedding
            emb = self.embedder.embed(query)
            all_results = self.db.search(emb, top_k=top_k * 3)

        # Aggregate by case
        return self._aggregate_by_case(all_results, top_k)

    def _aggregate_by_case(self, results: list[dict], top_k: int) -> list[dict]:
        """Group by case_id, use max score, fetch snippet from MongoDB"""
        case_scores = {}

        for r in results:
            cid = r["cid"]
            case_scores[cid] = max(case_scores.get(cid, 0), r["score"])

        # Rank by max score
        ranked = sorted(case_scores.items(), key=lambda x: -x[1])[:top_k]

        # Fetch snippets from MongoDB for top cases
        output = []
        for cid, score in ranked:
            case_doc = self.storage.get_case(cid)
            snippet = ""
            if case_doc:
                # Get first 300 chars as snippet
                snippet = case_doc.get("full_text", "")[:300].replace("\n", " ")

            output.append({
                "case_id": cid,
                "score": round(score, 4),
                "snippet": snippet,
            })

        return output
