# Legal Case Similarity RAG System

A semantic search system for Indian legal judgments with an AI chat interface. Uses chunk-based PDF-to-PDF matching for accurate case similarity retrieval, powered by Google Gemini with function calling.

## Features

- **Chunk-Based PDF Search**: Upload a PDF or type a query to find similar legal cases
- **AI Chat Interface**: Conversational search powered by Google Gemini with tool calling
- **GPU-Accelerated Embeddings**: sentence-transformers with CUDA support (CPU fallback on EC2)
- **Streaming Responses**: Real-time SSE streaming for chat responses
- **PDF Upload Search**: Upload a case PDF to find similar judgments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js)                        │
│                   Chat Interface                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ POST /api/chat
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                         │
│                                                             │
│   Chat Request ──► Gemini API (with tools)                 │
│                         │                                   │
│                         ▼                                   │
│               ┌─────────────────┐                          │
│               │  Tool Calls     │                          │
│               │  - search       │──► Endee + GPU           │
│               │  - get_case     │──► DynamoDB              │
│               └─────────────────┘                          │
│                         │                                   │
│                         ▼                                   │
│               Gemini Response ──────► Frontend             │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │   External Services  │
                    │  - Endee (vectors)   │
                    │  - AWS DynamoDB+S3   │
                    │  - Google Gemini API │
                    └──────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI (Python 3.11) |
| **Frontend** | Next.js |
| **Vector DB** | Endee (768-dim, cosine similarity) |
| **Storage** | AWS DynamoDB (case text) + S3 (PDFs) |
| **Embeddings** | sentence-transformers / nomic-embed-text-v1.5 |
| **Chat LLM** | Google Gemini (gemini-2.0-flash) |
| **PDF Parsing** | pdfplumber |

## Project Structure

```
├── api_server.py       # FastAPI backend with Gemini chat + streaming
├── config.py           # Central configuration
├── embedder.py         # sentence-transformers embedder (GPU/CPU)
├── endee_db.py         # Endee vector DB client
├── aws_db.py           # AWS DynamoDB + S3 storage client
├── ingest.py           # Ingestion pipeline (extract → embed → store)
├── search.py           # Search pipeline (embed → vector search → aggregate)
├── main.py             # CLI entry point (test/ingest/search)
├── run_ingest.py       # Quick ingestion runner with progress bars
├── run_search.py       # Quick search runner
├── clear_database.py   # Clear all data from Endee + DynamoDB
├── test_system.py      # Full system tests (8 tests)
├── frontend/           # Next.js chat interface
│   ├── app/
│   ├── components/
│   └── lib/
└── data/
    ├── dataset_pdfs/   # Source PDFs for ingestion
    └── test_case/      # Test PDFs for search
```

## Quick Start

### 1. Setup Environment

```bash
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

### 3. Setup Endee (Vector DB)

**Option A: Docker (recommended)**
```bash
docker run -p 8080:8080 -v endee-data:/data endeeio/endee-server:latest
```

**Option B: Endee Cloud**
1. Create account at [endee.io](https://endee.io/)
2. Set `ENDEE_URL` and `ENDEE_AUTH_TOKEN` in `.env`

### 4. Setup AWS

1. Create a DynamoDB table: `legal-cases` (partition key: `case_id`, type: String)
2. Create an S3 bucket for PDFs
3. Add AWS credentials to `.env`

### 5. Run

```bash
# Verify everything works
python test_system.py

# Ingest PDFs
python run_ingest.py

# Start API server
python api_server.py

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with Gemini (uses search tools) |
| `/api/chat/stream` | POST | Streaming chat via SSE |
| `/api/search` | GET | Direct vector search (`?q=...&top_k=5`) |
| `/api/search/pdf` | POST | Search by uploading a PDF |
| `/api/case/{case_id}` | GET | Get full case text |
| `/api/download/{case_id}` | GET | Download case PDF |
| `/api/cases` | GET | List all ingested cases |
| `/health` | GET | Health check |

## CLI Usage

```bash
# Run all system tests
python test_system.py

# Ingest PDFs into Endee + DynamoDB
python run_ingest.py
python run_ingest.py --reset        # Clear and re-ingest
python run_ingest.py --limit 10     # Ingest first 10 PDFs

# Search from CLI
python main.py search "breach of contract"
python main.py search path/to/case.pdf
python main.py search -q "limitation period" -k 5

# Test system components
python main.py test

# Clear all data
python clear_database.py
```

## Data Schemas

### Endee Vector Schema

```python
{
    "id": "{case_id}_{hash12}",
    "vector": [768-dim float array],
    "meta": {
        "cid": "Case_Name"
    }
}
```

### DynamoDB Schema

```python
{
    "case_id": "Case_Name",       # Partition key
    "filename": "case.pdf",
    "full_text": "...",
    "page_count": 10
}
```

## How It Works

### Ingestion Pipeline

1. **Extract**: Parse PDFs with pdfplumber
2. **Chunk**: Split text into paragraphs (100-1000 chars)
3. **Store text**: Save full text + metadata to DynamoDB
4. **Embed**: Generate 768-dim embeddings with sentence-transformers (GPU batched)
5. **Index**: Upsert vectors to Endee with case ID metadata

### Search Pipeline

1. **Embed query**: Generate embedding for query text (or chunk a PDF and embed each chunk)
2. **Vector search**: Find similar vectors in Endee
3. **Aggregate**: Group results by case, use max similarity score
4. **Enrich**: Fetch snippets from DynamoDB for top results

### Chat Pipeline

1. User sends message via Next.js frontend
2. FastAPI sends message to Gemini with tool definitions
3. Gemini calls `search_legal_cases` or `get_legal_case` tools
4. FastAPI executes tools (vector search + DynamoDB lookup)
5. Gemini generates response using tool results
6. Response streamed back to frontend via SSE

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `ENDEE_URL` | Endee server URL (default: `http://localhost:8080/api/v1`) |
| `ENDEE_AUTH_TOKEN` | Endee auth token (optional for local) |
| `AWS_ACCESS_KEY_ID` | AWS credentials for DynamoDB + S3 |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_REGION` | AWS region (default: `ap-south-1`) |
| `DYNAMODB_TABLE` | DynamoDB table name (default: `legal-cases`) |
| `S3_BUCKET` | S3 bucket for PDFs |
| `GOOGLE_API_KEY` | Google Gemini API key |

## Deployment (AWS EC2)

See [deploy/README.md](deploy/README.md) for full EC2 deployment guide.

**Instance:** m7i-flex.large (2 vCPU, 8GB RAM) - ap-south-1 (Mumbai)

```bash
# SSH to EC2
ssh -i "legal-key.pem" ubuntu@<EC2_IP>

# Deploy
cd ~/Legal-Judgement-Retrieval && git pull
sudo systemctl restart legal-api legal-frontend
```

## Troubleshooting

### CUDA Not Available
Set `EMBEDDING_DEVICE=cpu` in `.env`. The system works on CPU, just slower.

### Endee Connection Failed
Ensure the Endee server is running. The system auto-creates the index on first run.

### DynamoDB Access Denied
Check AWS credentials and IAM permissions (needs `dynamodb:*` and `s3:*` on your resources).

## License

MIT License
