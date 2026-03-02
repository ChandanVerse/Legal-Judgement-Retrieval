# Legal Case Similarity RAG System

A production-grade, local legal case similarity retrieval system built in Python. This is a **retrieval-first** system designed for finding semantically similar legal judgments based on section-aware matching.

## Features

- **Section-Aware Search**: Search within specific sections (Facts, Grounds, Judgment, Ratio, etc.)
- **Paragraph-Level Matching**: Semantic matching at the paragraph level for precise results
- **Graph-First Narrowing**: Uses Neo4j citation network to narrow candidates before vector search
- **Hybrid Reranking**: Combines semantic similarity, PageRank, and recency scores
- **Deduplication**: SHA256-based paragraph deduplication for efficient storage
- **Local Object Store**: Paragraph text stored as files, not in vector DB
- **Explainable Results**: Shows matched paragraphs and score breakdowns

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  PDF → Extract → Sections → Paragraphs → Dedupe → Embed → Store │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ pdfplumber│→│  Section  │→│ Paragraph │→│  SHA256 Dedupe   │ │
│  │          │  │ Detection │  │ Chunking  │  │                  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│                                    ↓                             │
│                           ┌──────────────┐                       │
│                           │  Embeddings  │                       │
│                           │ (nomic/BGE)  │                       │
│                           └──────────────┘                       │
│                                    ↓                             │
│            ┌───────────────────────┼───────────────────────┐     │
│            ↓                       ↓                       ↓     │
│     ┌──────────┐           ┌──────────┐           ┌──────────┐  │
│     │  Neo4j   │           │ Pinecone │           │  Local   │  │
│     │  Graph   │           │  Vectors │           │  Files   │  │
│     └──────────┘           └──────────┘           └──────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         SEARCH PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│  Query → Embed → Graph Narrow → Vector Search → Rerank → Top 10 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │Test Case │→│  Section  │→│  Graph   │→│   Vector Search  │ │
│  │   PDF    │  │ Selection │  │ Narrow   │  │   (Pinecone)    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│                                                     ↓            │
│                                            ┌──────────────────┐  │
│                                            │  Hybrid Rerank   │  │
│                                            │ Sim+PR+Recency   │  │
│                                            └──────────────────┘  │
│                                                     ↓            │
│                                            ┌──────────────────┐  │
│                                            │   Top 10 Cases   │  │
│                                            └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
legal-rag/
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── README.md             # This file
│
├── data/
│   ├── dataset_pdfs/     # Knowledge base PDFs
│   └── test_case/        # Test case PDF for search
│
├── ingest/
│   ├── extract.py        # PDF text extraction
│   ├── sections.py       # Legal section detection
│   ├── paragraphs.py     # Semantic paragraph chunking
│   ├── dedupe.py         # SHA256 deduplication
│   ├── embed.py          # Embedding generation
│   └── indexer.py        # Main ingestion pipeline
│
├── search/
│   ├── search_case.py    # Main search interface
│   ├── candidate_graph.py # Graph-based narrowing
│   └── reranker.py       # Hybrid reranking
│
├── storage/
│   ├── object_store.py   # Local file storage
│   └── registry.py       # Paragraph registry
│
├── vectordb/
│   └── client.py         # Pinecone/Qdrant client
│
└── graphdb/
    └── client.py         # Neo4j client
```

## Installation

### 1. Clone and Setup Environment

```bash
cd legal-rag
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Setup Databases

#### Pinecone (Vector DB)
1. Create account at [pinecone.io](https://www.pinecone.io/)
2. Create a serverless index
3. Add API key to `.env`

#### Neo4j (Graph DB)
Option A: Local Installation
```bash
# Download from https://neo4j.com/download/
# Start Neo4j and set password
```

Option B: Neo4j AuraDB (Cloud)
1. Create free instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/)
2. Add connection URI and credentials to `.env`

## Usage

### Ingest Legal Documents

Place your PDF files in `data/dataset_pdfs/`, then run:

```bash
# Ingest all PDFs
python ingest/indexer.py

# Ingest with options
python ingest/indexer.py --input ./my_pdfs --limit 100 --verbose

# Reset and re-ingest
python ingest/indexer.py --reset
```

### Search for Similar Cases

```bash
# Interactive search with PDF
python search/search_case.py path/to/test_case.pdf

# Search specific section
python search/search_case.py test.pdf --section facts

# Direct text query
python search/search_case.py --query "breach of contract damages" --section judgment

# View database stats
python search/search_case.py --stats
```

### Example Output

```
======================================================================
TOP 10 SIMILAR CASES
======================================================================

[1] ABC Corporation v. State of Maharashtra
    Citation: (2023) 5 SCC 123
    Court: Supreme Court of India
    Year: 2023
    Section: facts
    Scores:
      - Similarity: 0.8542
      - PageRank:   0.7231
      - Recency:    0.9500
      - Final:      0.8324
    Matched text:
      "The appellant company entered into a contract with the respondent..."
----------------------------------------------------------------------

[2] XYZ Industries v. Union of India
    Citation: 2022 AIR SC 456
    ...
```

## Storage Design

### Neo4j Graph Schema

**Nodes:**
- `Case`: case_id, case_name, citation, court, year, pagerank
- `Section`: name, case_id, confidence
- `Paragraph`: hash, case_id, section, paragraph_path

**Relationships:**
- `(Case)-[:HAS_SECTION]->(Section)`
- `(Section)-[:HAS_PARAGRAPH]->(Paragraph)`
- `(Case)-[:CITES]->(Case)`

### Pinecone Vector Schema

Each vector contains:
- `id`: Unique paragraph identifier
- `values`: 768-dim embedding
- `metadata`:
  - `case_id`: Reference to case
  - `section`: Section name
  - `paragraph_id`: Short hash
  - `paragraph_path`: Path to full text

**Note:** Full paragraph text is NOT stored in the vector DB.

### Local Object Store

```
storage/paragraphs/
├── case_001/
│   ├── facts/
│   │   ├── abc123.txt
│   │   └── def456.txt
│   └── analysis/
│       └── ghi789.txt
└── case_002/
    └── ...
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | nomic-ai/nomic-embed-text-v1.5 | Sentence transformer model |
| `CHUNK_SIZE` | 500 | Max paragraph size |
| `TOP_K_RESULTS` | 10 | Number of results |
| `WEIGHT_SIMILARITY` | 0.6 | Semantic similarity weight |
| `WEIGHT_PAGERANK` | 0.25 | Citation authority weight |
| `WEIGHT_RECENCY` | 0.15 | Recency bias weight |

## Supported Sections

The system detects and supports these legal document sections:
- Facts
- Issues
- Arguments
- Grounds
- Analysis
- Ratio (Decidendi)
- Judgment
- Order
- Headnote
- Preamble

## Performance Notes

- **Batch Processing**: Embeddings generated in batches of 32
- **Vector Upserts**: Batched in groups of 100
- **Deduplication**: ~20-30% storage savings typical
- **Graph Narrowing**: Reduces vector search space by 50-80%

## Troubleshooting

### CUDA Not Available
Set `EMBEDDING_DEVICE=cpu` in `.env`

### Neo4j Connection Failed
- Check if Neo4j is running
- Verify credentials in `.env`
- For AuraDB, ensure URI uses `neo4j+s://` protocol

### Pinecone Index Not Found
The system auto-creates the index on first run. Ensure API key is valid.

## API Reference

### SearchEngine

```python
from search.search_case import SearchEngine

engine = SearchEngine()

# Search by text
results = engine.search_by_text(
    query_text="contract breach damages",
    section="judgment",
    top_k=10
)

# Search by PDF
results, info = engine.search_by_pdf(
    pdf_path="test_case.pdf",
    section="facts"
)

engine.close()
```

### LegalDocumentIndexer

```python
from ingest.indexer import LegalDocumentIndexer

indexer = LegalDocumentIndexer()

# Process single document
result = indexer.process_document(Path("case.pdf"))

# Process directory
summary = indexer.process_directory(Path("./pdfs"), limit=100)

indexer.close()
```

## License

MIT License - See LICENSE file for details.
