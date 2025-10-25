# Migration Guide: ChromaDB to Pinecone

This document guides you through migrating from ChromaDB to Pinecone for your Legal Judgement Retrieval system.

## Why Migrate to Pinecone?

### Advantages of Pinecone

1. **Serverless & Scalable**
   - No infrastructure management
   - Automatic scaling based on usage
   - Pay only for what you use

2. **Production-Ready Performance**
   - Sub-100ms query latency
   - High availability (99.9% uptime SLA)
   - Global distribution

3. **Better for Production**
   - Managed service (no maintenance)
   - Built-in monitoring and observability
   - Enterprise-grade security

4. **Cost-Effective**
   - Free tier available for development
   - Serverless pricing: ~$0.10 per 1M queries
   - No upfront infrastructure costs

5. **Advanced Features**
   - Hybrid search (sparse + dense vectors)
   - Metadata filtering at scale
   - Native multi-tenancy support

### ChromaDB vs Pinecone

| Feature | ChromaDB | Pinecone |
|---------|----------|----------|
| Deployment | Self-hosted | Fully managed |
| Scalability | Limited by hardware | Auto-scaling |
| Latency | Variable | Consistent <100ms |
| Maintenance | Manual | Zero |
| Cost | Infrastructure costs | Pay-per-use |
| Best For | Local development | Production systems |

---

## Migration Steps

### Step 1: Install Dependencies

```bash
# Install new requirements
pip install -r requirements.txt

# This will install:
# - pinecone-client
# - pinecone[grpc]
```

### Step 2: Get Pinecone API Key

1. Sign up for Pinecone at [https://www.pinecone.io/](https://www.pinecone.io/)
2. Create a new project
3. Get your API key from the dashboard
4. Note your environment (e.g., `us-east-1-aws`)

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Pinecone Configuration
PINECONE_API_KEY=your_actual_api_key_here
PINECONE_ENVIRONMENT=us-east-1-aws  # or your region

# Optional: Override default index name
PINECONE_INDEX_NAME=legal-judgments

# Google Gemini (if using RAG)
GOOGLE_API_KEY=your_google_api_key_here
```

You can copy from the example:
```bash
cp .env.example .env
# Then edit .env with your actual keys
```

### Step 4: Remove Old ChromaDB Data (Optional)

The ChromaDB database is no longer used. You can safely remove it:

```bash
# Backup first (optional)
mv chroma_db chroma_db.backup

# Or delete
rm -rf chroma_db
```

### Step 5: Re-index Your Documents

Since Pinecone is a different database, you need to re-index your legal documents:

```bash
# Make sure your PDFs are in judgments_pdf/
python create_database.py
```

This will:
- Create a Pinecone index (if it doesn't exist)
- Process all PDFs in `judgments_pdf/`
- Generate embeddings using the same model (nomic-embed-text-v1.5)
- Upload vectors to Pinecone

**Note**: The first run will take a few minutes as it creates the index.

### Step 6: Test the Migration

Run a search query to verify everything works:

```bash
python search.py
```

Try searching for a legal concept, e.g.:
- "contract breach remedy"
- "criminal liability"
- "constitutional rights"

### Step 7: Verify Section Filtering

Test section-specific searches:

```bash
python example_section_search.py
```

This will test:
- General search
- Facts-only search
- Legal reasoning (ratio decidendi) search
- Arguments search

---

## API Compatibility

### No Code Changes Required!

The new `vectordb.py` maintains the same interface as the ChromaDB version:

```python
# Existing code continues to work
vector_db = VectorDatabase(config)
vector_db.initialize()
vector_db.add_documents(documents)
results = vector_db.similarity_search(query, top_k=5)
```

### Method Compatibility

| Method | Status | Notes |
|--------|--------|-------|
| `initialize()` | ✅ Compatible | Now creates Pinecone index |
| `add_documents()` | ✅ Compatible | Uses Pinecone upsert |
| `similarity_search()` | ✅ Compatible | Native Pinecone query |
| `get_stats()` | ⚠️ Modified | Returns Pinecone-specific stats |
| `reset_database()` | ✅ Compatible | Deletes and recreates index |

### Metadata Filter Syntax

ChromaDB filters are automatically converted to Pinecone format:

```python
# This works with both ChromaDB and Pinecone
filters = {"section": "facts"}
results = vector_db.similarity_search(query, filters=filters)

# The new code automatically converts:
# ChromaDB: {"section": "facts"}
# → Pinecone: {"section": {"$eq": "facts"}}
```

---

## Migrating Data from Existing ChromaDB

If you have an existing ChromaDB database with important data:

### Option 1: Simple Re-indexing (Recommended)

Just re-run the ingestion pipeline:

```bash
python create_database.py
```

This will:
- Re-process PDFs from `judgments_pdf/`
- Generate fresh embeddings
- Upload to Pinecone

**Pros**: Clean, ensures consistency
**Cons**: Takes time for large document sets

### Option 2: Export and Import (Advanced)

If you want to preserve exact vector IDs or have processed documents not available as PDFs:

```python
# export_from_chroma.py
import chromadb
from chromadb.config import Settings

# Connect to old ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("legal-judgments")

# Export all data
results = collection.get(include=["embeddings", "documents", "metadatas"])

# Save to JSON
import json
export_data = {
    'ids': results['ids'],
    'embeddings': results['embeddings'],
    'documents': results['documents'],
    'metadatas': results['metadatas']
}

with open('chromadb_export.json', 'w') as f:
    json.dump(export_data, f)
print(f"Exported {len(results['ids'])} vectors")
```

```python
# import_to_pinecone.py
import json
from vectordb import VectorDatabase
from config import Config

# Load exported data
with open('chromadb_export.json', 'r') as f:
    data = json.load(f)

# Initialize Pinecone
config = Config()
vector_db = VectorDatabase(config)
vector_db.initialize()

# Import in batches
batch_size = 100
for i in range(0, len(data['ids']), batch_size):
    end_idx = min(i + batch_size, len(data['ids']))

    vectors = []
    for j in range(i, end_idx):
        vectors.append({
            'id': data['ids'][j],
            'values': data['embeddings'][j],
            'metadata': {
                **data['metadatas'][j],
                'content': data['documents'][j]
            }
        })

    vector_db.index.upsert(vectors=vectors)
    print(f"Imported batch {i//batch_size + 1}")

print("Import complete!")
```

---

## Troubleshooting

### Issue: "PINECONE_API_KEY environment variable not set"

**Solution**: Make sure you've created a `.env` file with your API key:

```bash
echo "PINECONE_API_KEY=your_key_here" > .env
echo "PINECONE_ENVIRONMENT=us-east-1-aws" >> .env
```

### Issue: "Index creation failed"

**Possible causes**:
1. Invalid API key
2. Invalid environment/region
3. Network connectivity issues

**Solution**:
```bash
# Test your API key
python -c "
from pinecone import Pinecone
import os
from dotenv import load_dotenv
load_dotenv()
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
print('API key valid!')
print('Existing indexes:', [idx.name for idx in pc.list_indexes()])
"
```

### Issue: "Metadata exceeds size limit"

Pinecone has a 40KB metadata limit per vector.

**Solution**: Already handled in the new code - document content is stored in metadata (truncated if needed).

### Issue: Slow query performance

**Possible causes**:
1. Cold start (first query after idle)
2. Large metadata

**Solutions**:
- First query may be slower (100-200ms), subsequent queries are <100ms
- Reduce metadata size if needed
- Use appropriate Pinecone plan for production

### Issue: Different search results than ChromaDB

This is expected and normal:
- Different indexing algorithms (HNSW parameters)
- Pinecone's optimized approximate nearest neighbor search
- Generally, Pinecone results are more consistent

**Validation**:
```bash
# Run search tests
python search.py

# Compare top results - they should be similar
# Minor ranking differences are normal
```

---

## Cost Estimation

### Development / Testing
- **Pinecone Free Tier**:
  - 1 serverless index
  - Up to 2M vectors
  - Sufficient for 10,000-20,000 legal documents

**Cost**: $0/month

### Production (10,000 legal cases)
- **Vectors**: ~90,000 (9 sections per case)
- **Storage**: ~500 MB (1536-dim vectors)
- **Queries**: ~100,000/month

**Pinecone Serverless Cost**:
- Storage: ~$0.30/month
- Read units: ~$0.10/month
- **Total**: ~$0.40/month

### Production (100,000 legal cases)
- **Vectors**: ~900,000
- **Storage**: ~5 GB

**Pinecone Serverless Cost**:
- Storage: ~$3.00/month
- Read units: ~$0.10/month
- **Total**: ~$3.10/month

**Extremely affordable** compared to infrastructure costs!

---

## Performance Comparison

Based on typical legal document retrieval:

| Metric | ChromaDB (Local) | Pinecone (Serverless) |
|--------|------------------|----------------------|
| Query Latency | 50-200ms (variable) | 30-80ms (consistent) |
| Scalability | Limited by RAM | Millions of vectors |
| Concurrent Users | 1-5 | 1000s |
| Maintenance | Manual | Zero |
| High Availability | Single point of failure | 99.9% uptime SLA |

---

## Rollback Plan (If Needed)

If you need to rollback to ChromaDB:

1. **Keep backup of `chroma_db/` directory**
   ```bash
   cp -r chroma_db chroma_db.backup
   ```

2. **Restore old vectordb.py**
   ```bash
   git checkout HEAD~1 vectordb.py config.py
   ```

3. **Reinstall ChromaDB**
   ```bash
   pip install chromadb
   ```

---

## Next Steps

After successful migration:

1. ✅ **Test thoroughly** with your actual queries
2. ✅ **Monitor performance** using Pinecone dashboard
3. ✅ **Consider knowledge graph integration** (see KNOWLEDGE_GRAPH_GUIDE.md)
4. ✅ **Set up monitoring** for your production system
5. ✅ **Implement caching** for frequently accessed queries

---

## Support

- **Pinecone Docs**: https://docs.pinecone.io/
- **Pinecone Community**: https://community.pinecone.io/
- **Issues**: Check the project GitHub issues

---

## Summary

✅ **Migration is straightforward** - just update env vars and re-index
✅ **No code changes needed** in your application
✅ **Better performance** and reliability
✅ **Lower operational overhead** (fully managed)
✅ **Cost-effective** for production

Welcome to production-ready vector search with Pinecone! 🚀
