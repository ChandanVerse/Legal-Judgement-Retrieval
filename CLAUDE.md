# CLAUDE.md - Project Context for Claude Code

## Project Overview

**Legal Case Similarity RAG System** - A semantic search system for Indian legal judgments with chat interface.

**Key Characteristics:**
- Retrieval-first design with LLM chat interface
- Chunk-based PDF-to-PDF search for accurate similarity matching
- **Embeddings:** sentence-transformers (GPU locally, CPU on EC2)
- **Google Gemini** for chat with function calling
- Storage: Endee (vectors) + MongoDB Atlas (full text + PDFs)
- **Deployed on AWS EC2** (m7i-flex.large)

## Tech Stack

- **Python 3.11** with CUDA (RTX 4060)
- **Endee** - Vector database (768-dim embeddings)
- **MongoDB Atlas** - Full case text + GridFS for PDFs
- **sentence-transformers** - nomic-ai/nomic-embed-text-v1.5 (GPU batched)
- **Google Gemini** - Chat with function calling (gemini-1.5-flash)
- **FastAPI** - Backend API server
- **Next.js** - Frontend chat interface
- **pdfplumber** - PDF text extraction

## Project Structure

```
├── api_server.py       # FastAPI backend with Gemini chat
├── config.py           # Central configuration
├── embedder.py         # sentence-transformers (GPU, fast)
├── endee_db.py         # Endee vector DB client
├── mongo_db.py         # MongoDB + GridFS client
├── ingest.py           # Ingestion pipeline
├── search.py           # Search pipeline
├── main.py             # CLI entry point
├── run_ingest.py       # Quick ingestion runner
├── run_search.py       # Quick search runner
├── clear_database.py   # Clear all data
├── test_system.py      # Full system tests
├── frontend/           # Next.js chat interface
│   ├── app/
│   ├── components/
│   └── lib/
└── data/
    ├── dataset_pdfs/   # Source PDFs
    └── test_case/      # Test PDFs
```

## Quick Start

```bash
# Activate environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API server
python api_server.py

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with Gemini (uses search tools) |
| `/api/search` | GET | Direct search |
| `/api/case/{id}` | GET | Get full case text |
| `/api/download/{id}` | GET | Download PDF |
| `/api/cases` | GET | List all cases |

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
│               │  - search       │──► Endee + GPU            │
│               │  - get_case     │──► MongoDB               │
│               └─────────────────┘                          │
│                         │                                   │
│                         ▼                                   │
│               Gemini Response ──────► Frontend             │
└─────────────────────────────────────────────────────────────┘
```

## Endee Vector Schema

```python
{
    "id": "{case_id}_{hash12}",
    "vector": [768-dim embedding],
    "meta": {
        "cid": "Case_Name",    # Case identifier
    }
}
```

## MongoDB Schema

```python
# Cases collection
{
    "case_id": "Case_Name",
    "filename": "case.pdf",
    "full_text": "...",
    "page_count": 10
}

# GridFS for PDF storage
```

## AWS Deployment

**Instance:** m7i-flex.large (2 vCPU, 8GB RAM) - ap-south-1 (Mumbai)

**Live URLs:**
- Frontend: http://13.232.16.19:3000
- API: http://13.232.16.19:8000

**SSH Access:**
```bash
ssh -i "C:\Users\chand\Downloads\legal-key.pem" ubuntu@13.232.16.19
```

**Services (systemd):**
```bash
# Check status
sudo systemctl status legal-api legal-frontend

# Restart services
sudo systemctl restart legal-api legal-frontend

# View logs
sudo journalctl -u legal-api -f
sudo journalctl -u legal-frontend -f
```

**Service Files:**
- `/etc/systemd/system/legal-api.service`
- `/etc/systemd/system/legal-frontend.service`

**Environment Files:**
- API: `~/Legal-Judgement-Retrieval/.env`
- Frontend: `~/Legal-Judgement-Retrieval/frontend/.env.local`

**Key Dependencies (EC2):**
- `einops` - Required for nomic embedding model on CPU

**Deployment Steps:**
1. Push changes: `git push origin main`
2. SSH to EC2
3. Pull: `cd ~/Legal-Judgement-Retrieval && git pull`
4. Restart: `sudo systemctl restart legal-api legal-frontend`
