"""Minimal Pinecone client"""
from pinecone import Pinecone, ServerlessSpec
import config


class PineconeDB:
    def __init__(self):
        self.pc = Pinecone(api_key=config.PINECONE_API_KEY)
        self.index = None

    def connect(self, create_if_missing: bool = True) -> bool:
        """Connect to index, optionally creating it if missing"""
        # Check if index exists
        existing = [idx.name for idx in self.pc.list_indexes()]

        if config.PINECONE_INDEX not in existing:
            if create_if_missing:
                print(f"Creating index '{config.PINECONE_INDEX}'...")
                self.pc.create_index(
                    name=config.PINECONE_INDEX,
                    dimension=config.EMBEDDING_DIM,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                print(f"Index '{config.PINECONE_INDEX}' created successfully")
            else:
                raise ValueError(f"Index '{config.PINECONE_INDEX}' not found")

        self.index = self.pc.Index(config.PINECONE_INDEX)
        return True

    def upsert(self, vectors: list[dict], batch_size: int = 100) -> int:
        """Upsert vectors: [{id, values, metadata}]"""
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i : i + batch_size])
        return len(vectors)

    def update_metadata(self, vid: str, metadata: dict):
        """Update metadata for a vector"""
        self.index.update(id=vid, set_metadata=metadata)

    def search(
        self, embedding: list[float], top_k: int = 10
    ) -> list[dict]:
        """Search similar vectors"""
        results = self.index.query(
            vector=embedding, top_k=top_k, include_metadata=True
        )
        output = []
        for m in results.matches:
            # Extract case_id from metadata or from vector id
            cid = m.metadata.get("cid")
            if not cid:
                # Fallback: extract from vector id (format: {case_id}_{hash})
                cid = "_".join(m.id.split("_")[:-1]) if "_" in m.id else m.id
            output.append({
                "id": m.id,
                "score": m.score,
                "cid": cid,
            })
        return output

    def delete_all(self):
        """Reset index (skip if already empty)"""
        try:
            self.index.delete(delete_all=True)
        except Exception as e:
            if "Namespace not found" in str(e):
                pass  # Already empty
            else:
                raise

    def stats(self) -> dict:
        """Get index stats"""
        return self.index.describe_index_stats()
