"""
Ingestion Pipeline with Progress Bars

Usage:
    python run_ingest.py              # Ingest all PDFs
    python run_ingest.py --reset      # Clear databases first
    python run_ingest.py --limit 10   # Ingest first 10 PDFs
"""
import argparse
from pathlib import Path
from tqdm import tqdm
import config
from ingest import extract_text, chunk_text, case_id_from_path, hash_text
from embedder import Embedder
from pinecone_db import PineconeDB
from aws_db import AWSStorage


def main():
    parser = argparse.ArgumentParser(description="Ingest legal PDFs")
    parser.add_argument("--reset", action="store_true", help="Clear databases first")
    parser.add_argument("--limit", type=int, help="Limit number of PDFs")
    args = parser.parse_args()

    # Initialize components
    print("Initializing components...")
    embedder = Embedder()
    pinecone = PineconeDB()
    pinecone.connect()
    aws = AWSStorage()

    # Get PDFs
    pdfs = list(config.DATASET_DIR.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[:args.limit]

    if args.reset:
        print("Resetting databases...")
        pinecone.delete_all()
        aws.delete_all()

    # ============ PHASE 1: Extract & Store Full Text in AWS DynamoDB ============
    print(f"\n[PHASE 1] Extracting text from {len(pdfs)} PDFs -> DynamoDB")

    pdf_data = {}  # {case_id: {"text": str, "chunks": list, "filename": str, "pages": int}}

    for pdf_path in tqdm(pdfs, desc="Extracting PDFs"):
        cid = case_id_from_path(pdf_path)
        text = extract_text(pdf_path)
        chunks = chunk_text(text)
        page_count = len(text.split('\f')) if '\f' in text else text.count('\n\n') // 10 + 1

        # Store full text in DynamoDB
        aws.upsert_case(
            case_id=cid,
            filename=pdf_path.name,
            full_text=text,
            page_count=page_count
        )

        pdf_data[cid] = {"text": text, "chunks": chunks, "filename": pdf_path.name}

    print(f"   Stored {len(pdf_data)} cases in DynamoDB")

    # ============ PHASE 2: Embed Chunks -> Pinecone ============
    print(f"\n[PHASE 2] Embedding chunks -> Pinecone")

    all_chunks = []
    chunk_metadata = []  # [(cid, chunk), ...]

    for cid, data in pdf_data.items():
        for chunk in data["chunks"]:
            all_chunks.append(chunk)
            chunk_metadata.append((cid, chunk))

    print(f"   Total chunks to embed: {len(all_chunks)}")

    # Batch embed with progress
    batch_size = 32
    all_embeddings = []
    for i in tqdm(range(0, len(all_chunks), batch_size), desc="Embedding"):
        batch = all_chunks[i:i + batch_size]
        embeddings = embedder.embed_batch(batch)
        all_embeddings.extend(embeddings)

    # Prepare vectors for Pinecone
    vectors = []
    for (cid, chunk), emb in zip(chunk_metadata, all_embeddings):
        vid = f"{cid}_{hash_text(chunk)}"
        vectors.append({
            "id": vid,
            "values": emb,
            "metadata": {"cid": cid}
        })

    # Upsert to Pinecone
    pinecone.upsert(vectors)
    print(f"   Stored {len(vectors)} vectors in Pinecone")

    # ============ DONE ============
    print(f"\n{'='*50}")
    print(f"INGESTION COMPLETE")
    print(f"  PDFs processed: {len(pdfs)}")
    print(f"  Cases in DynamoDB: {aws.count()}")
    print(f"  Vectors in Pinecone: {len(vectors)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
