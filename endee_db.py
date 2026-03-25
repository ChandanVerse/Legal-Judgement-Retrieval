"""Minimal Endee vector database client"""
from endee import Endee, Precision
from endee.exceptions import NotFoundException
import config


class EndeeDB:
    def __init__(self):
        self.client = Endee(config.ENDEE_AUTH_TOKEN) if config.ENDEE_AUTH_TOKEN else Endee()
        if config.ENDEE_URL:
            self.client.set_base_url(config.ENDEE_URL)
        self.index = None

    def _create_index(self):
        self.client.create_index(
            name=config.ENDEE_INDEX,
            dimension=config.EMBEDDING_DIM,
            space_type="cosine",
            precision=Precision.INT8,
        )

    def connect(self, create_if_missing: bool = True) -> bool:
        """Connect to index, optionally creating it if missing"""
        try:
            self.index = self.client.get_index(name=config.ENDEE_INDEX)
        except NotFoundException:
            if not create_if_missing:
                raise ValueError(f"Index '{config.ENDEE_INDEX}' not found")
            print(f"Creating index '{config.ENDEE_INDEX}'...")
            self._create_index()
            self.index = self.client.get_index(name=config.ENDEE_INDEX)
            print(f"Index '{config.ENDEE_INDEX}' created successfully")
        return True

    def upsert(self, vectors: list[dict], batch_size: int = 100) -> int:
        """Upsert vectors: [{id, vector, meta}]"""
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors[i : i + batch_size])
        return len(vectors)

    def search(self, embedding: list[float], top_k: int = 10) -> list[dict]:
        """Search similar vectors"""
        results = self.index.query(vector=embedding, top_k=top_k)
        output = []
        for m in results:
            meta = m.get("meta", {})
            cid = meta.get("cid")
            if not cid:
                # Fallback: extract from vector id (format: {case_id}_{hash})
                vid = m["id"]
                cid = "_".join(vid.split("_")[:-1]) if "_" in vid else vid
            output.append({
                "id": m["id"],
                "score": m["similarity"],
                "cid": cid,
            })
        return output

    def delete_all(self):
        """Reset index by deleting and recreating it"""
        self.client.delete_index(config.ENDEE_INDEX)
        self._create_index()
        self.index = self.client.get_index(name=config.ENDEE_INDEX)

    def stats(self) -> dict:
        """Get index stats"""
        return self.index.describe()
