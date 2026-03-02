"""PDF ingestion utilities and Ingester class"""
import hashlib
import pdfplumber
from pathlib import Path
from tqdm import tqdm
import config
from embedder import Embedder
from pinecone_db import PineconeDB

from aws_db import AWSStorage as StorageClient


def extract_text(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber"""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def chunk_text(text: str) -> list[str]:
    """Split text into paragraphs"""
    chunks = []
    for para in text.split("\n\n"):
        para = para.strip()
        if len(para) >= config.MIN_CHUNK_LEN:
            if len(para) > config.MAX_CHUNK_LEN:
                # Split long paragraphs
                for i in range(0, len(para), config.MAX_CHUNK_LEN):
                    chunk = para[i : i + config.MAX_CHUNK_LEN]
                    if len(chunk) >= config.MIN_CHUNK_LEN:
                        chunks.append(chunk)
            else:
                chunks.append(para)
    return chunks


def case_id_from_path(pdf_path: Path) -> str:
    """Generate case_id from filename"""
    return pdf_path.stem[:50].replace(" ", "_")


def hash_text(text: str) -> str:
    """Short hash for deduplication"""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


class Ingester:
    """Full ingestion pipeline using MongoDB + Pinecone"""

    def __init__(self):
        self.embedder = Embedder()
        self.pinecone = PineconeDB()
        self.pinecone.connect()
        self.mongo = StorageClient()

    def ingest_all(
        self, pdf_dir: Path = None, limit: int = None, reset: bool = False
    ):
        """Two-phase ingestion: Extract -> Embed"""
        pdf_dir = pdf_dir or config.DATASET_DIR
        pdfs = list(pdf_dir.glob("*.pdf"))[:limit]

        if reset:
            print("Resetting databases...")
            self.pinecone.delete_all()
            self.mongo.delete_all()

        # ============ PHASE 1: EXTRACT & STORE IN MONGODB ============
        print(f"\n[PHASE 1] Extracting {len(pdfs)} PDFs -> MongoDB")

        pdf_data = {}  # {case_id: {"chunks": list}}

        for pdf_path in tqdm(pdfs, desc="Extracting"):
            cid = case_id_from_path(pdf_path)
            text = extract_text(pdf_path)
            chunks = chunk_text(text)

            if not chunks:
                continue

            # Store full text in MongoDB
            page_count = len(text.split('\f')) if '\f' in text else text.count('\n\n') // 10 + 1
            self.mongo.upsert_case(
                case_id=cid,
                filename=pdf_path.name,
                full_text=text,
                page_count=page_count
            )

            pdf_data[cid] = {"chunks": chunks}

        print(f"   Stored {len(pdf_data)} cases in MongoDB")

        # ============ PHASE 2: EMBED -> PINECONE ============
        print(f"\n[PHASE 2] Embedding chunks -> Pinecone")

        chunk_metadata = []  # [(cid, chunk), ...]
        for cid, data in pdf_data.items():
            for chunk in data["chunks"]:
                chunk_metadata.append((cid, chunk))

        print(f"   Total chunks: {len(chunk_metadata)}")

        # Batch embed
        all_chunks = [chunk for _, chunk in chunk_metadata]
        all_embeddings = self.embedder.embed_batch(all_chunks)

        # Upsert to Pinecone
        vectors = []
        for (cid, chunk), emb in zip(chunk_metadata, all_embeddings):
            vid = f"{cid}_{hash_text(chunk)}"
            vectors.append({
                "id": vid,
                "values": emb,
                "metadata": {"cid": cid}
            })

        self.pinecone.upsert(vectors)
        print(f"   Stored {len(vectors)} vectors")

        print(f"\nIngestion complete: {len(chunk_metadata)} chunks from {len(pdfs)} PDFs")
