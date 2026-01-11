# RAG Copilot - Quick Start Guide

## Overview

The RAG (Retrieval Augmented Generation) Copilot is an AI agent that provides:
- **Literature search** across research papers
- **Similarity search** for past simulation runs
- **Reproducibility analysis** for simulation results
- **Experiment suggestions** based on literature and past work

## Prerequisites

1. **Voyage AI API Key** - Get from https://www.voyageai.com/
2. **MongoDB** - Running locally or remote
3. **Python 3.10+**
4. **Dependencies installed** (see below)

## Installation

### 1. Install Dependencies

```bash
pip install voyageai chromadb pymupdf python-dotenv
```

Or use the requirements:
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create or update `.env` file:

```bash
# Required
VOYAGE_API_KEY=your_voyage_key_here
MONGO_URI=mongodb://localhost:27017

# Optional (already set)
FIREWORKS=your_fireworks_key
```

### 3. Initialize RAG System

```bash
python setup_rag.py
```

This will:
- ✅ Test Voyage AI connection
- ✅ Initialize ChromaDB vector store
- ✅ Offer to index PDFs from `RAG/docs/`
- ✅ Offer to index simulation runs from MongoDB

### 4. Test the System

```bash
python test_rag.py
```

This runs comprehensive tests:
- Voyage AI embedder test
- Vector store connectivity
- RAG agent functionality
- Search capabilities
- Reproducibility analysis

### 5. Start the API Server

```bash
python start_server.py
```

The server will start with RAG endpoints available at:
```
http://localhost:8000/api/v1/rag/
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/api/v1/rag/health
```

### Literature Search

```bash
curl -X POST http://localhost:8000/api/v1/rag/search/literature \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PWR reactor enrichment effects",
    "n_results": 5
  }'
```

### Similar Runs Search

```bash
curl -X POST http://localhost:8000/api/v1/rag/search/similar_runs \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": "PWR",
    "enrichment": 4.5,
    "n_results": 5
  }'
```

### Reproducibility Check

```bash
curl http://localhost:8000/api/v1/rag/reproducibility/run_abc123def456
```

### Experiment Suggestions

```bash
curl -X POST http://localhost:8000/api/v1/rag/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "context": "PWR at 4.5% enrichment shows k-eff=1.045",
    "current_results": {
      "geometry": "PWR",
      "enrichment_pct": 4.5,
      "keff": 1.045
    },
    "n_suggestions": 3
  }'
```

### RAG Stats

```bash
curl http://localhost:8000/api/v1/rag/stats
```

### Index Papers (Background)

```bash
curl -X POST http://localhost:8000/api/v1/rag/index/papers \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "RAG/docs"
  }'
```

### Index Runs (Background)

```bash
curl -X POST http://localhost:8000/api/v1/rag/index/runs \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 100
  }'
```

## Integration with Multi-Agent System

The RAG Copilot is automatically integrated into the router:

```bash
# This query will route to RAG Copilot
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does the literature say about PWR enrichment?",
    "use_llm": false
  }'
```

### Routing Keywords

Queries containing these keywords route to RAG Copilot:
- `literature`, `paper`, `research`, `publication`
- `reproduce`, `reproducibility`, `validate`, `benchmark`
- `suggest`, `recommend`, `follow-up`, `next experiment`
- `similar runs`, `past experiments`, `history`
- `why`, `explain`, `how does`, `what about`

## Usage Examples

### Example 1: Literature Search

```python
import asyncio
from rag_agent import RAGCopilotAgent
from rag_components import setup_rag_components
from pymongo import MongoClient
import os

async def main():
    # Setup
    embedder, vector_store, _, _ = setup_rag_components()
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    
    agent = RAGCopilotAgent(embedder, vector_store, mongo_client)
    
    # Search literature
    result = await agent.invoke("What does the literature say about PWR enrichment?")
    print(result['result'])

asyncio.run(main())
```

### Example 2: Reproducibility Check

```python
# Check reproducibility of a run
result = agent.check_reproducibility("run_abc123def456")
print(result)
```

### Example 3: Suggest Experiments

```python
# Get experiment suggestions
suggestions = agent.suggest_experiments(
    context="PWR at 4.5% enrichment shows k-eff=1.045",
    current_results={"geometry": "PWR", "enrichment_pct": 4.5}
)
print(suggestions)
```

## File Structure

```
Playground/backend/
├── rag_components.py       # Voyage AI, ChromaDB, Indexers
├── rag_agent.py            # RAG Copilot Agent
├── api/
│   ├── rag_endpoints.py    # FastAPI endpoints
│   └── main_v2.py          # Main API (includes RAG router)
├── setup_rag.py            # Setup script
├── test_rag.py             # Test script
└── rag/
    └── chroma_db/          # Vector database storage

RAG/docs/                   # PDF research papers (to be indexed)
```

## Troubleshooting

### Error: "VOYAGE_API_KEY not found"

Solution:
```bash
export VOYAGE_API_KEY="your_key_here"
# Or add to .env file
```

### Error: "No papers indexed"

Solution:
```bash
python setup_rag.py
# Select 'y' when asked to index PDFs
```

### Error: "ChromaDB connection failed"

Solution:
```bash
# Remove existing database and reinitialize
rm -rf rag/chroma_db
python setup_rag.py
```

### Error: "MongoDB connection failed"

Solution:
```bash
# Start MongoDB
sudo systemctl start mongod

# Or check connection
mongosh --eval "db.version()"
```

## Performance

### Costs (Voyage AI)

- Embedding: $0.00012 per 1K tokens
- Typical query: ~$0.000006
- Index 10 papers: ~$0.024
- Index 1000 runs: ~$0.06

**Estimated monthly cost: < $1**

### Latency

- Query embedding: 50-100ms
- Vector search: 10-50ms
- Total query: 200-500ms

## Advanced Usage

### Custom Indexing

```python
from pathlib import Path
from rag_components import PDFIndexer, setup_rag_components

embedder, vector_store, _, _ = setup_rag_components()
indexer = PDFIndexer(embedder, vector_store)

# Index specific PDF
indexer.index_pdf(Path("my_paper.pdf"))

# Index directory
indexer.index_directory(Path("my_papers/"))
```

### Direct Vector Search

```python
# Embed query
query_embedding = embedder.embed_query("PWR enrichment")

# Search
results = vector_store.search(
    query_embedding=query_embedding,
    n_results=5,
    collection="papers"
)

# Results contain documents, metadata, distances
for doc, meta, dist in zip(
    results['documents'][0],
    results['metadatas'][0],
    results['distances'][0]
):
    print(f"Relevance: {1-dist:.2%}")
    print(f"Title: {meta['title']}")
    print(f"Content: {doc[:200]}...")
```

### Custom LLM for Suggestions

```python
from langchain_fireworks import ChatFireworks

custom_llm = ChatFireworks(
    model="accounts/fireworks/models/llama-v3p1-405b-instruct",
    temperature=0.8
)

agent = RAGCopilotAgent(
    embedder=embedder,
    vector_store=vector_store,
    mongo_client=mongo_client,
    llm=custom_llm
)
```

## Next Steps

1. ✅ Complete setup: `python setup_rag.py`
2. ✅ Run tests: `python test_rag.py`
3. ✅ Start server: `python start_server.py`
4. ✅ Test endpoints: See API examples above
5. ✅ Integrate with frontend: Use mission control UI

## Resources

- **Voyage AI Docs**: https://docs.voyageai.com/
- **ChromaDB Docs**: https://docs.trychroma.com/
- **Full Plan**: `RAG/VOYAGER_RAG_AGENT_PLAN.md`

---

**Ready to go!** 🚀

For questions or issues, check the logs or run `python test_rag.py` for diagnostics.

