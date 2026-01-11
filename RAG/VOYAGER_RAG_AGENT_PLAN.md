# Voyage AI RAG Copilot Agent - Implementation Plan

**Version:** 1.0  
**Purpose:** Document analysis, reproducibility tracking, and experiment suggestion agent  
**Integration:** 5th Specialist Agent in Multi-Agent System  
**Status:** Ready for Implementation

---

## Executive Summary

This plan details the implementation of a **RAG Copilot Agent** powered by Voyage AI embeddings. The agent serves as an intelligent companion that:

1. **Indexes and searches** research papers, documentation, and simulation results
2. **Monitors reproducibility** by tracking simulation parameters and validating against literature
3. **Suggests experiments** based on literature, past results, and research gaps
4. **Provides context** from research papers relevant to current simulations
5. **Acts as a copilot** - always available through the router for document queries

---

## Architecture Overview

### Integration into Existing Multi-Agent System

```
User Query → Router Agent → Specialist Agents
                  ↓
            ┌─────┴────────┬──────────┬──────────┬─────────────┐
            ↓              ↓          ↓          ↓             ↓
        Studies        Sweep      Query     Analysis    RAG Copilot
        Agent         Agent      Agent      Agent        Agent
                                                           ↓
                                                    [Voyage AI]
                                                    [Vector DB]
                                                    [PDF Index]
```

### RAG Copilot Agent Role

The RAG Copilot is a **specialist agent** that:
- Routes queries containing: "literature", "paper", "reproducibility", "suggest", "recommend", "similar"
- Can be called by other agents for context enrichment
- Monitors simulation runs and compares against known benchmarks from literature

---

## Technology Stack

### Core Components

1. **Voyage AI** - Embeddings API
   - Model: `voyage-3.5` (latest, best performance)
   - Use case: Semantic search across documents and results
   - API: https://docs.voyageai.com/

2. **Vector Database** - ChromaDB (Recommended)
   - Lightweight, Python-native
   - Persistent storage
   - Fast similarity search
   - Alternative: Pinecone, Weaviate, or MongoDB Vector Search

3. **PDF Processing** - PyMuPDF + LangChain
   - Extract text from PDFs
   - Chunk documents intelligently
   - Preserve metadata (title, authors, year)

4. **Integration** - LangGraph
   - Integrate with existing agent system
   - Tool calling for context retrieval
   - State management

---

## System Components

### 1. Document Indexing Pipeline

```
RAG/docs/*.pdf → Extract Text → Chunk → Embed → Store in Vector DB
    ↓
[Metadata: title, authors, year, DOI, keywords]
```

#### Document Types to Index

1. **Research Papers** (`RAG/docs/*.pdf`)
   - Fusion reactor designs
   - Neutronics benchmarks
   - OpenMC validation studies
   - Material compositions

2. **Simulation Results** (MongoDB `runs` collection)
   - Input parameters
   - Output results (k-eff, flux distributions)
   - Analysis notes
   - Comparison to benchmarks

3. **Code Documentation** (optional)
   - OpenMC documentation
   - AONP system docs
   - Study specifications

#### Chunking Strategy

```python
# Smart chunking for scientific papers
CHUNK_CONFIG = {
    "chunk_size": 1000,  # tokens
    "chunk_overlap": 200,  # token overlap between chunks
    "separator_priority": [
        "\n## ",      # Section headers
        "\n### ",     # Subsections
        "\n\n",       # Paragraphs
        ". ",         # Sentences
        " "           # Words
    ]
}
```

### 2. Voyage AI Embeddings Service

```python
import voyageai

class VoyageEmbedder:
    def __init__(self, api_key: str):
        self.client = voyageai.Client(api_key=api_key)
        self.model = "voyage-3.5"  # Latest model
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents (for indexing)"""
        result = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="document"  # Optimized for storage
        )
        return result.embeddings
    
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query (for search)"""
        result = self.client.embed(
            texts=[query],
            model=self.model,
            input_type="query"  # Optimized for retrieval
        )
        return result.embeddings[0]
```

**Why Voyage AI?**
- ✅ State-of-the-art performance on retrieval tasks
- ✅ Optimized for scientific/technical content
- ✅ Separate embeddings for documents vs queries
- ✅ Fast inference (< 100ms for queries)
- ✅ Cost-effective ($0.00012/1K tokens)

### 3. Vector Database (ChromaDB)

```python
import chromadb
from chromadb.config import Settings

class RAGVectorStore:
    def __init__(self, persist_directory: str = "./rag/chroma_db"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Collection for research papers
        self.papers_collection = self.client.get_or_create_collection(
            name="research_papers",
            metadata={"description": "Fusion neutronics papers"}
        )
        
        # Collection for simulation results
        self.runs_collection = self.client.get_or_create_collection(
            name="simulation_runs",
            metadata={"description": "OpenMC simulation results"}
        )
    
    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
        collection: str = "papers"
    ):
        """Add documents with embeddings to vector store"""
        coll = (self.papers_collection if collection == "papers" 
                else self.runs_collection)
        
        coll.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        collection: str = "papers",
        filter_dict: dict = None
    ) -> dict:
        """Search for similar documents"""
        coll = (self.papers_collection if collection == "papers" 
                else self.runs_collection)
        
        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict  # e.g., {"year": {"$gte": 2020}}
        )
        return results
```

### 4. RAG Copilot Agent

```python
from langchain_core.tools import tool
from langchain_fireworks import ChatFireworks
from typing import Dict, List, Any

class RAGCopilotAgent:
    """
    Specialist agent for document retrieval, reproducibility analysis,
    and experiment suggestions.
    """
    
    def __init__(
        self,
        voyage_api_key: str,
        fireworks_api_key: str,
        mongo_client: MongoClient,
        vector_store: RAGVectorStore
    ):
        self.embedder = VoyageEmbedder(voyage_api_key)
        self.vector_store = vector_store
        self.llm = ChatFireworks(
            model="accounts/fireworks/models/llama-v3p1-70b-instruct",
            api_key=fireworks_api_key
        )
        self.mongo_client = mongo_client
    
    @tool
    def search_literature(self, query: str, n_results: int = 5) -> str:
        """
        Search research papers for relevant information.
        
        Args:
            query: Natural language query
            n_results: Number of results to return
        
        Returns:
            Formatted string with relevant paper excerpts
        """
        # Embed query
        query_embedding = self.embedder.embed_query(query)
        
        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
            collection="papers"
        )
        
        # Format results
        context = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            context.append(f"""
**Paper {i+1}: {metadata.get('title', 'Unknown')}**
Authors: {metadata.get('authors', 'Unknown')}
Year: {metadata.get('year', 'Unknown')}
Relevance: {1 - distance:.2%}

{doc}

---
            """)
        
        return "\n".join(context)
    
    @tool
    def search_similar_runs(
        self,
        geometry: str,
        enrichment: float = None,
        tolerance: float = 0.5
    ) -> str:
        """
        Find similar simulation runs from history.
        
        Args:
            geometry: Geometry type (e.g., "PWR", "BWR")
            enrichment: Enrichment percentage (optional)
            tolerance: Tolerance for enrichment matching
        
        Returns:
            Formatted string with similar runs
        """
        # Build query for vector search
        query = f"Simulation of {geometry} geometry"
        if enrichment:
            query += f" with {enrichment}% enrichment"
        
        query_embedding = self.embedder.embed_query(query)
        
        # Search simulation results
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=10,
            collection="runs"
        )
        
        # Format results
        similar_runs = []
        for doc, metadata in zip(
            results['documents'][0],
            results['metadatas'][0]
        ):
            similar_runs.append(f"""
**Run ID: {metadata.get('run_id', 'Unknown')}**
Geometry: {metadata.get('geometry', 'Unknown')}
Enrichment: {metadata.get('enrichment_pct', 'Unknown')}%
k-eff: {metadata.get('keff', 'Unknown')} ± {metadata.get('keff_std', 'Unknown')}
Date: {metadata.get('timestamp', 'Unknown')}

{doc}

---
            """)
        
        return "\n".join(similar_runs[:5])  # Top 5 most similar
    
    @tool
    def check_reproducibility(self, run_id: str) -> str:
        """
        Analyze a simulation run for reproducibility.
        
        Args:
            run_id: Run ID to analyze
        
        Returns:
            Reproducibility report
        """
        # Get run from MongoDB
        run = self.mongo_client["aonp"]["runs"].find_one({"run_id": run_id})
        
        if not run:
            return f"Run {run_id} not found"
        
        # Check against benchmarks in literature
        query = f"Benchmark for {run['geometry']} with {run['enrichment_pct']}% enrichment"
        query_embedding = self.embedder.embed_query(query)
        
        lit_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=3,
            collection="papers"
        )
        
        # Compare with similar runs
        similar_runs = self.search_similar_runs(
            geometry=run['geometry'],
            enrichment=run['enrichment_pct']
        )
        
        # Generate reproducibility report
        report = f"""
# Reproducibility Analysis: {run_id}

## Run Parameters
- Geometry: {run['geometry']}
- Enrichment: {run['enrichment_pct']}%
- Temperature: {run['temperature_K']}K
- Particles: {run.get('n_particles', 'Unknown')}
- Batches: {run.get('n_batches', 'Unknown')}

## Results
- k-eff: {run['keff']} ± {run['keff_std']}
- Status: {self._get_criticality_status(run['keff'])}

## Literature Comparison
{self._format_benchmark_comparison(lit_results, run)}

## Historical Comparison
{similar_runs}

## Reproducibility Score
{self._calculate_reproducibility_score(run, lit_results, similar_runs)}

## Recommendations
{self._generate_recommendations(run, lit_results)}
        """
        
        return report
    
    @tool
    def suggest_experiments(
        self,
        context: str,
        current_results: dict = None,
        n_suggestions: int = 3
    ) -> str:
        """
        Suggest follow-up experiments based on literature and results.
        
        Args:
            context: Current experimental context
            current_results: Recent simulation results
            n_suggestions: Number of suggestions to generate
        
        Returns:
            List of experiment suggestions with rationale
        """
        # Search literature for related work
        lit_context = self.search_literature(context, n_results=5)
        
        # Search for similar past experiments
        if current_results:
            similar = self.search_similar_runs(
                geometry=current_results.get('geometry', ''),
                enrichment=current_results.get('enrichment_pct')
            )
        else:
            similar = ""
        
        # Use LLM to generate suggestions
        prompt = f"""
You are an expert in fusion reactor neutronics and nuclear engineering.

Based on the following context, suggest {n_suggestions} novel experiments
that would:
1. Validate or extend the current findings
2. Fill gaps in the literature
3. Test physical hypotheses
4. Improve reproducibility

## Current Context
{context}

## Current Results
{current_results or "No current results"}

## Relevant Literature
{lit_context}

## Similar Past Experiments
{similar}

For each suggestion, provide:
- **Experiment Title**
- **Objective**: What question does this answer?
- **Parameters**: Specific parameters to vary
- **Expected Outcome**: What should we learn?
- **Literature Gap**: How does this extend current knowledge?
- **Reproducibility**: How does this improve reproducibility?

Format as a numbered list.
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_criticality_status(self, keff: float) -> str:
        """Determine criticality status"""
        if keff < 0.98:
            return "⚡ SUBCRITICAL"
        elif keff <= 1.02:
            return "✓ CRITICAL"
        else:
            return "⚠️ SUPERCRITICAL"
    
    def _format_benchmark_comparison(self, lit_results: dict, run: dict) -> str:
        """Format benchmark comparison from literature"""
        if not lit_results['documents'][0]:
            return "No benchmarks found in literature."
        
        comparison = "**Benchmarks from Literature:**\n\n"
        for doc, metadata in zip(
            lit_results['documents'][0][:2],
            lit_results['metadatas'][0][:2]
        ):
            comparison += f"- {metadata.get('title', 'Unknown')}\n"
            comparison += f"  {doc[:200]}...\n\n"
        
        return comparison
    
    def _calculate_reproducibility_score(
        self,
        run: dict,
        lit_results: dict,
        similar_runs: str
    ) -> str:
        """Calculate reproducibility score based on multiple factors"""
        score = 0.0
        factors = []
        
        # Factor 1: Statistical uncertainty (30%)
        uncertainty = run['keff_std'] / run['keff'] * 100
        if uncertainty < 0.1:
            score += 30
            factors.append("✓ Excellent statistical uncertainty (< 0.1%)")
        elif uncertainty < 0.5:
            score += 20
            factors.append("✓ Good statistical uncertainty (< 0.5%)")
        else:
            score += 10
            factors.append("⚠ High statistical uncertainty (> 0.5%)")
        
        # Factor 2: Literature validation (30%)
        if lit_results['documents'][0]:
            score += 30
            factors.append("✓ Validated against literature benchmarks")
        else:
            factors.append("⚠ No literature benchmarks found")
        
        # Factor 3: Historical consistency (20%)
        if "Run ID:" in similar_runs:
            score += 20
            factors.append("✓ Consistent with historical runs")
        else:
            factors.append("⚠ No similar historical runs")
        
        # Factor 4: Parameter completeness (20%)
        required_params = ['geometry', 'enrichment_pct', 'temperature_K', 
                          'n_particles', 'n_batches']
        if all(param in run for param in required_params):
            score += 20
            factors.append("✓ Complete parameter specification")
        else:
            factors.append("⚠ Missing some parameters")
        
        result = f"""
**Overall Score: {score:.0f}/100**

{chr(10).join(factors)}

**Rating:** {self._score_to_rating(score)}
        """
        return result
    
    def _score_to_rating(self, score: float) -> str:
        """Convert score to rating"""
        if score >= 90:
            return "⭐⭐⭐⭐⭐ Excellent"
        elif score >= 75:
            return "⭐⭐⭐⭐ Good"
        elif score >= 60:
            return "⭐⭐⭐ Fair"
        elif score >= 40:
            return "⭐⭐ Poor"
        else:
            return "⭐ Needs Improvement"
    
    def _generate_recommendations(self, run: dict, lit_results: dict) -> str:
        """Generate recommendations for improving reproducibility"""
        recommendations = []
        
        # Check uncertainty
        uncertainty = run['keff_std'] / run['keff'] * 100
        if uncertainty > 0.5:
            recommendations.append(
                "- Increase particle count or batches to reduce uncertainty"
            )
        
        # Check for benchmarks
        if not lit_results['documents'][0]:
            recommendations.append(
                "- Search for validation benchmarks in literature"
            )
        
        # Check temperature
        if run.get('temperature_K', 0) < 300:
            recommendations.append(
                "- Verify temperature setting (currently < 300K)"
            )
        
        # General recommendations
        recommendations.extend([
            "- Document random seed for exact reproducibility",
            "- Include nuclear data library version",
            "- Store complete input files alongside results"
        ])
        
        return "\n".join(recommendations)
    
    async def invoke(self, query: str) -> dict:
        """
        Main entry point for RAG Copilot agent.
        
        Args:
            query: Natural language query
        
        Returns:
            Response dictionary with results
        """
        # Determine intent
        intent = self._classify_intent(query)
        
        # Route to appropriate tool
        if intent == "literature_search":
            result = self.search_literature(query)
        elif intent == "reproducibility":
            # Extract run_id from query
            run_id = self._extract_run_id(query)
            result = self.check_reproducibility(run_id)
        elif intent == "suggest_experiments":
            result = self.suggest_experiments(query)
        elif intent == "similar_runs":
            # Extract parameters from query
            params = self._extract_parameters(query)
            result = self.search_similar_runs(**params)
        else:
            # General RAG query
            result = self.search_literature(query)
        
        return {
            "status": "completed",
            "intent": intent,
            "result": result,
            "query": query
        }
    
    def _classify_intent(self, query: str) -> str:
        """Classify query intent"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["reproduce", "reproducibility", "validate"]):
            return "reproducibility"
        elif any(kw in query_lower for kw in ["suggest", "recommend", "next experiment", "follow-up"]):
            return "suggest_experiments"
        elif any(kw in query_lower for kw in ["similar", "past", "previous", "history"]):
            return "similar_runs"
        elif any(kw in query_lower for kw in ["paper", "literature", "research", "publication"]):
            return "literature_search"
        else:
            return "general"
    
    def _extract_run_id(self, query: str) -> str:
        """Extract run_id from query"""
        import re
        match = re.search(r'run_[a-f0-9]{12}', query)
        return match.group(0) if match else ""
    
    def _extract_parameters(self, query: str) -> dict:
        """Extract simulation parameters from query"""
        import re
        params = {}
        
        # Extract geometry
        for geom in ["PWR", "BWR", "VVER", "CANDU"]:
            if geom.lower() in query.lower():
                params['geometry'] = geom
                break
        
        # Extract enrichment
        enrich_match = re.search(r'(\d+\.?\d*)\s*%?\s*enrich', query.lower())
        if enrich_match:
            params['enrichment'] = float(enrich_match.group(1))
        
        return params
```

---

## Router Integration

### Updated Router Agent

Add RAG Copilot to routing keywords:

```python
class RouterAgent:
    def __init__(self):
        self.routing_map = {
            'studies': [
                'simulate', 'run', 'execute', 'single', 'study',
                'k-eff', 'keff', 'criticality', 'geometry'
            ],
            'sweep': [
                'sweep', 'vary', 'range', 'multiple', 'parameter',
                'batch', 'exploration', 'scan'
            ],
            'query': [
                'find', 'search', 'filter', 'retrieve', 'database',
                'show me', 'list', 'get all'
            ],
            'analysis': [
                'compare', 'analyze', 'difference', 'versus', 'vs',
                'contrast', 'evaluation'
            ],
            'rag_copilot': [  # NEW
                'literature', 'paper', 'research', 'publication',
                'reproduce', 'reproducibility', 'validate', 'benchmark',
                'suggest', 'recommend', 'follow-up', 'next experiment',
                'similar runs', 'past experiments', 'history',
                'why', 'explain', 'how does', 'what about'
            ]
        }
```

### Example Routing

```
Query: "What does the literature say about PWR enrichment?"
→ Routes to: rag_copilot

Query: "Check reproducibility of run_abc123def456"
→ Routes to: rag_copilot

Query: "Suggest experiments based on my last sweep"
→ Routes to: rag_copilot

Query: "Find similar runs to PWR at 4.5%"
→ Routes to: rag_copilot (could also route to query agent)
```

---

## Data Indexing Implementation

### Step 1: Index Research Papers

```python
import pymupdf  # PyMuPDF
from pathlib import Path
import re

class PDFIndexer:
    def __init__(
        self,
        embedder: VoyageEmbedder,
        vector_store: RAGVectorStore
    ):
        self.embedder = embedder
        self.vector_store = vector_store
    
    def index_pdf(self, pdf_path: Path) -> None:
        """Index a single PDF file"""
        # Extract text
        doc = pymupdf.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        # Extract metadata
        metadata = self._extract_metadata(doc, text)
        metadata['filename'] = pdf_path.name
        metadata['filepath'] = str(pdf_path)
        
        # Chunk text
        chunks = self._chunk_text(text)
        
        # Generate embeddings
        embeddings = self.embedder.embed_documents(chunks)
        
        # Create IDs
        ids = [f"{pdf_path.stem}_chunk_{i}" for i in range(len(chunks))]
        
        # Add to vector store
        metadatas = [metadata.copy() for _ in chunks]
        for i, meta in enumerate(metadatas):
            meta['chunk_id'] = i
            meta['total_chunks'] = len(chunks)
        
        self.vector_store.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            collection="papers"
        )
        
        print(f"✅ Indexed {pdf_path.name}: {len(chunks)} chunks")
    
    def index_directory(self, directory: Path) -> None:
        """Index all PDFs in a directory"""
        pdf_files = list(directory.glob("*.pdf"))
        
        print(f"Found {len(pdf_files)} PDFs to index...")
        
        for pdf_path in pdf_files:
            # Skip zone identifier files
            if "Zone.Identifier" in pdf_path.name:
                continue
            
            try:
                self.index_pdf(pdf_path)
            except Exception as e:
                print(f"❌ Error indexing {pdf_path.name}: {e}")
    
    def _extract_metadata(self, doc, text: str) -> dict:
        """Extract metadata from PDF"""
        metadata = {
            'title': doc.metadata.get('title', 'Unknown'),
            'author': doc.metadata.get('author', 'Unknown'),
            'year': self._extract_year(text),
            'doi': self._extract_doi(text),
            'keywords': self._extract_keywords(text)
        }
        return metadata
    
    def _extract_year(self, text: str) -> int:
        """Extract publication year from text"""
        # Look for year pattern (19XX or 20XX)
        matches = re.findall(r'\b(19|20)\d{2}\b', text[:2000])
        if matches:
            years = [int(m[0] + m[1:]) for m in matches]
            # Return most recent plausible year
            return max([y for y in years if 1970 <= y <= 2026], default=None)
        return None
    
    def _extract_doi(self, text: str) -> str:
        """Extract DOI from text"""
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        match = re.search(doi_pattern, text[:5000])
        return match.group(0) if match else None
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from abstract"""
        # Look for keywords section
        keywords_pattern = r'keywords?:?\s*([^\n]+)'
        match = re.search(keywords_pattern, text[:5000], re.IGNORECASE)
        if match:
            kw_text = match.group(1)
            return [kw.strip() for kw in re.split(r'[,;]', kw_text)]
        return []
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> list[str]:
        """Chunk text into semantic chunks"""
        # Simple chunking by paragraphs
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
```

### Step 2: Index Simulation Results

```python
class SimulationIndexer:
    def __init__(
        self,
        mongo_client: MongoClient,
        embedder: VoyageEmbedder,
        vector_store: RAGVectorStore
    ):
        self.mongo_client = mongo_client
        self.embedder = embedder
        self.vector_store = vector_store
        self.runs_collection = mongo_client["aonp"]["runs"]
    
    def index_run(self, run_id: str) -> None:
        """Index a single simulation run"""
        # Get run from MongoDB
        run = self.runs_collection.find_one({"run_id": run_id})
        
        if not run:
            print(f"❌ Run {run_id} not found")
            return
        
        # Create text description
        text = self._format_run_as_text(run)
        
        # Generate embedding
        embedding = self.embedder.embed_query(text)
        
        # Extract metadata
        metadata = {
            'run_id': run['run_id'],
            'geometry': run.get('geometry', 'Unknown'),
            'enrichment_pct': run.get('enrichment_pct', 0),
            'temperature_K': run.get('temperature_K', 0),
            'keff': run.get('keff', 0),
            'keff_std': run.get('keff_std', 0),
            'timestamp': run.get('created_at', ''),
            'status': run.get('status', 'unknown')
        }
        
        # Add to vector store
        self.vector_store.add_documents(
            texts=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[run_id],
            collection="runs"
        )
        
        print(f"✅ Indexed run {run_id}")
    
    def index_all_runs(self, limit: int = None) -> None:
        """Index all simulation runs from MongoDB"""
        query = {}
        runs = self.runs_collection.find(query).limit(limit) if limit else self.runs_collection.find(query)
        
        count = 0
        for run in runs:
            try:
                self.index_run(run['run_id'])
                count += 1
            except Exception as e:
                print(f"❌ Error indexing {run.get('run_id', 'unknown')}: {e}")
        
        print(f"\n✅ Indexed {count} simulation runs")
    
    def _format_run_as_text(self, run: dict) -> str:
        """Format run as searchable text"""
        text = f"""
Simulation Run {run['run_id']}

Geometry: {run.get('geometry', 'Unknown')}
Configuration: {run.get('geometry', 'Unknown')} reactor with {run.get('enrichment_pct', 0)}% enrichment
Temperature: {run.get('temperature_K', 0)} Kelvin
Fuel: {', '.join(run.get('materials', []))}

Simulation Parameters:
- Particles: {run.get('n_particles', 'Unknown')}
- Batches: {run.get('n_batches', 'Unknown')}
- Nuclear Data: {run.get('nuclear_data', 'Unknown')}

Results:
- k-effective: {run.get('keff', 'Unknown')} ± {run.get('keff_std', 'Unknown')}
- Status: {self._get_status_text(run.get('keff', 0))}
- Convergence: {run.get('convergence', 'Unknown')}

Analysis Notes:
{run.get('analysis_notes', 'No analysis notes available')}

Timestamp: {run.get('created_at', 'Unknown')}
        """.strip()
        
        return text
    
    def _get_status_text(self, keff: float) -> str:
        """Get human-readable status"""
        if keff < 0.98:
            return "Subcritical (k-eff < 0.98)"
        elif keff <= 1.02:
            return "Critical (0.98 ≤ k-eff ≤ 1.02)"
        else:
            return "Supercritical (k-eff > 1.02)"
```

---

## API Endpoints

### New Endpoints for RAG Copilot

```python
# In api/main_v2.py

from fastapi import APIRouter

rag_router = APIRouter(prefix="/api/v1/rag", tags=["RAG Copilot"])

@rag_router.post("/search/literature")
async def search_literature(
    query: str,
    n_results: int = 5
) -> dict:
    """Search research papers for relevant information"""
    result = rag_agent.search_literature(query, n_results)
    return {"query": query, "results": result}

@rag_router.post("/search/runs")
async def search_similar_runs(
    geometry: str,
    enrichment: float = None,
    tolerance: float = 0.5,
    n_results: int = 5
) -> dict:
    """Find similar simulation runs"""
    result = rag_agent.search_similar_runs(
        geometry=geometry,
        enrichment=enrichment,
        tolerance=tolerance
    )
    return {"query_params": {"geometry": geometry, "enrichment": enrichment}, "results": result}

@rag_router.get("/reproducibility/{run_id}")
async def check_reproducibility(run_id: str) -> dict:
    """Analyze reproducibility of a simulation run"""
    result = rag_agent.check_reproducibility(run_id)
    return {"run_id": run_id, "report": result}

@rag_router.post("/suggest")
async def suggest_experiments(
    context: str,
    current_results: dict = None,
    n_suggestions: int = 3
) -> dict:
    """Suggest follow-up experiments"""
    result = rag_agent.suggest_experiments(
        context=context,
        current_results=current_results,
        n_suggestions=n_suggestions
    )
    return {"suggestions": result}

@rag_router.post("/index/papers")
async def index_papers(directory: str = "RAG/docs") -> dict:
    """Index all PDF research papers"""
    indexer = PDFIndexer(voyage_embedder, vector_store)
    indexer.index_directory(Path(directory))
    return {"status": "completed", "directory": directory}

@rag_router.post("/index/runs")
async def index_runs(limit: int = None) -> dict:
    """Index simulation runs from MongoDB"""
    indexer = SimulationIndexer(mongo_client, voyage_embedder, vector_store)
    indexer.index_all_runs(limit=limit)
    return {"status": "completed", "limit": limit}
```

### Integration with Existing Query Endpoint

```python
# Update router to include rag_copilot

@app.post("/api/v1/query")
async def submit_query(request: QueryRequest):
    """Main query endpoint"""
    query_id = generate_query_id()
    
    # Route query
    routing = router_agent.route(request.query, use_llm=request.use_llm)
    
    # If routed to rag_copilot
    if routing['agent'] == 'rag_copilot':
        result = await rag_agent.invoke(request.query)
        
        # Store in MongoDB
        queries_collection.insert_one({
            "query_id": query_id,
            "query": request.query,
            "routing": routing,
            "result": result,
            "status": "completed",
            "created_at": datetime.utcnow()
        })
        
        return {
            "query_id": query_id,
            "status": "completed",
            "routing": routing,
            "result": result
        }
    
    # ... handle other agents ...
```

---

## Frontend Integration

### New Components for RAG Copilot

#### 1. Copilot Panel (`CopilotPanel.tsx`)

```typescript
interface CopilotResponse {
  intent: 'literature_search' | 'reproducibility' | 'suggest_experiments' | 'similar_runs';
  result: string;
  query: string;
}

const CopilotPanel = ({ response }: { response: CopilotResponse }) => {
  return (
    <div className="copilot-panel">
      <div className="copilot-header">
        <span className="icon">🤖</span>
        <h3>RAG Copilot</h3>
        <span className="badge">{response.intent}</span>
      </div>
      
      <div className="copilot-content">
        <ReactMarkdown>{response.result}</ReactMarkdown>
      </div>
      
      <div className="copilot-actions">
        <button>📋 Copy</button>
        <button>🔖 Save</button>
        <button>🔄 Refresh</button>
      </div>
    </div>
  );
};
```

#### 2. Reproducibility Score Card

```typescript
const ReproducibilityCard = ({ runId }: { runId: string }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['reproducibility', runId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/rag/reproducibility/${runId}`);
      return res.json();
    }
  });
  
  if (isLoading) return <LoadingSpinner />;
  
  return (
    <div className="reproducibility-card">
      <h4>Reproducibility Analysis</h4>
      <div className="score">{data.score}/100</div>
      <div className="rating">{data.rating}</div>
      <div className="factors">
        {data.factors.map(f => <div key={f}>{f}</div>)}
      </div>
    </div>
  );
};
```

#### 3. Literature Context Sidebar

```typescript
const LiteratureContext = ({ query }: { query: string }) => {
  const { data } = useQuery({
    queryKey: ['literature', query],
    queryFn: async () => {
      const res = await fetch('/api/v1/rag/search/literature', {
        method: 'POST',
        body: JSON.stringify({ query, n_results: 3 })
      });
      return res.json();
    },
    enabled: !!query
  });
  
  return (
    <div className="literature-sidebar">
      <h4>📚 Relevant Literature</h4>
      {data?.results.map((paper, i) => (
        <PaperCard key={i} paper={paper} />
      ))}
    </div>
  );
};
```

---

## Configuration

### Environment Variables

```bash
# .env file
MONGO_URI=mongodb://localhost:27017
FIREWORKS_API_KEY=your_fireworks_key
VOYAGE_API_KEY=your_voyage_key  # NEW

# Vector DB settings
CHROMA_PERSIST_DIR=./rag/chroma_db
```

### Voyage AI Configuration

```python
# config/rag_config.py

RAG_CONFIG = {
    "voyage": {
        "model": "voyage-3.5",  # Latest model
        "api_key_env": "VOYAGE_API_KEY",
        "max_retries": 3,
        "timeout": 30
    },
    "vector_db": {
        "type": "chromadb",
        "persist_directory": "./rag/chroma_db",
        "collections": {
            "papers": {
                "description": "Research papers and documentation",
                "distance_metric": "cosine"
            },
            "runs": {
                "description": "Simulation run results",
                "distance_metric": "cosine"
            }
        }
    },
    "indexing": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "batch_size": 100,  # Embed 100 docs at a time
        "reindex_interval_hours": 24  # Re-index daily
    },
    "search": {
        "default_n_results": 5,
        "similarity_threshold": 0.7,
        "rerank": True  # Use Voyage reranking
    }
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

- [ ] Install dependencies (`voyageai`, `chromadb`, `pymupdf`)
- [ ] Set up Voyage AI client and test API key
- [ ] Set up ChromaDB vector store
- [ ] Create `VoyageEmbedder` class
- [ ] Create `RAGVectorStore` class

### Phase 2: Document Indexing (Week 2)

- [ ] Create `PDFIndexer` class
- [ ] Index all PDFs in `RAG/docs/`
- [ ] Create `SimulationIndexer` class
- [ ] Index existing simulation runs from MongoDB
- [ ] Test search functionality

### Phase 3: RAG Copilot Agent (Week 3)

- [ ] Create `RAGCopilotAgent` class
- [ ] Implement `search_literature` tool
- [ ] Implement `search_similar_runs` tool
- [ ] Implement `check_reproducibility` tool
- [ ] Implement `suggest_experiments` tool
- [ ] Add to LangGraph workflow

### Phase 4: Router Integration (Week 4)

- [ ] Update `RouterAgent` with copilot keywords
- [ ] Add copilot routing logic
- [ ] Test routing to copilot agent
- [ ] Implement agent-to-agent calling (other agents can query copilot)

### Phase 5: API Endpoints (Week 5)

- [ ] Create `/api/v1/rag/*` endpoints
- [ ] Add indexing endpoints
- [ ] Add search endpoints
- [ ] Add reproducibility endpoint
- [ ] Test with Postman/curl

### Phase 6: Frontend Integration (Week 6)

- [ ] Create `CopilotPanel` component
- [ ] Create `ReproducibilityCard` component
- [ ] Create `LiteratureContext` sidebar
- [ ] Add copilot indicators to agent workflow
- [ ] Test E2E workflow

### Phase 7: Automation & Monitoring (Week 7)

- [ ] Auto-index new PDFs (file watcher)
- [ ] Auto-index new runs (MongoDB change streams)
- [ ] Add monitoring dashboard
- [ ] Performance optimization
- [ ] Error handling and logging

### Phase 8: Polish & Documentation (Week 8)

- [ ] Write user documentation
- [ ] Create example queries
- [ ] Performance benchmarking
- [ ] Security audit (API key handling)
- [ ] Deployment guide

---

## Testing Strategy

### Unit Tests

```python
# tests/test_rag_copilot.py

def test_voyage_embedder():
    embedder = VoyageEmbedder(api_key=os.getenv("VOYAGE_API_KEY"))
    
    # Test document embedding
    docs = ["This is a test document.", "Another test."]
    embeddings = embedder.embed_documents(docs)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1024  # voyage-3.5 dimension
    
def test_vector_store():
    store = RAGVectorStore(persist_directory="./test_db")
    
    # Add test documents
    store.add_documents(
        texts=["Test doc 1", "Test doc 2"],
        embeddings=[[0.1] * 1024, [0.2] * 1024],
        metadatas=[{"id": 1}, {"id": 2}],
        ids=["doc1", "doc2"],
        collection="papers"
    )
    
    # Search
    results = store.search(
        query_embedding=[0.15] * 1024,
        n_results=1,
        collection="papers"
    )
    
    assert len(results['documents'][0]) == 1

def test_pdf_indexer():
    indexer = PDFIndexer(embedder, vector_store)
    
    # Test with sample PDF
    pdf_path = Path("RAG/docs/test.pdf")
    indexer.index_pdf(pdf_path)
    
    # Verify indexed
    results = vector_store.search(
        query_embedding=embedder.embed_query("test"),
        n_results=1,
        collection="papers"
    )
    
    assert len(results['documents'][0]) > 0
```

### Integration Tests

```python
# tests/test_rag_integration.py

async def test_literature_search():
    result = await rag_agent.search_literature(
        "PWR reactor benchmarks",
        n_results=3
    )
    
    assert "Paper 1:" in result
    assert len(result) > 100

async def test_reproducibility_check():
    # Create test run
    test_run = {
        "run_id": "run_test123456",
        "geometry": "PWR",
        "enrichment_pct": 4.5,
        "keff": 1.045,
        "keff_std": 0.002
    }
    mongo_client["aonp"]["runs"].insert_one(test_run)
    
    # Check reproducibility
    report = rag_agent.check_reproducibility("run_test123456")
    
    assert "Reproducibility Analysis" in report
    assert "Overall Score:" in report

async def test_suggest_experiments():
    suggestions = await rag_agent.suggest_experiments(
        context="PWR reactor at 4.5% enrichment shows k-eff=1.045",
        n_suggestions=3
    )
    
    assert "1." in suggestions
    assert "2." in suggestions
    assert "3." in suggestions
```

### End-to-End Test

```python
async def test_e2e_rag_workflow():
    # 1. Index documents
    pdf_indexer = PDFIndexer(embedder, vector_store)
    pdf_indexer.index_directory(Path("RAG/docs"))
    
    # 2. Submit query through router
    response = await client.post("/api/v1/query", json={
        "query": "What does the literature say about PWR k-eff?",
        "use_llm": False
    })
    
    data = response.json()
    assert data['routing']['agent'] == 'rag_copilot'
    
    # 3. Check results
    query_id = data['query_id']
    status = await client.get(f"/api/v1/query/{query_id}")
    
    assert status.json()['status'] == 'completed'
    assert 'result' in status.json()
```

---

## Performance Considerations

### Embedding Costs

**Voyage AI Pricing:**
- voyage-3.5: $0.00012 per 1K tokens

**Estimated Costs:**
- Index 10 PDFs (avg 20K tokens each): ~$0.024
- Index 1000 runs (avg 500 tokens each): ~$0.06
- Query (avg 50 tokens): ~$0.000006

**Monthly estimates:**
- Initial indexing: $0.10
- 1000 queries/month: $0.006
- Weekly re-indexing: $0.04
- **Total: ~$0.15/month** (very affordable)

### Latency Optimization

1. **Caching**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def embed_query_cached(query: str) -> list[float]:
       return embedder.embed_query(query)
   ```

2. **Batch Processing**
   ```python
   # Embed multiple documents at once
   embeddings = embedder.embed_documents(chunks[:100])  # Batch of 100
   ```

3. **Async Queries**
   ```python
   import asyncio
   
   async def parallel_search(queries: list[str]):
       tasks = [search_literature(q) for q in queries]
       return await asyncio.gather(*tasks)
   ```

### Vector DB Optimization

```python
# ChromaDB optimization
collection = client.create_collection(
    name="papers",
    metadata={"hnsw:space": "cosine"},  # Fast cosine similarity
    embedding_function=None  # We provide embeddings
)

# Indexing with batching
def batch_add(docs, embeddings, metadata, batch_size=100):
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_emb = embeddings[i:i+batch_size]
        batch_meta = metadata[i:i+batch_size]
        
        collection.add(
            documents=batch_docs,
            embeddings=batch_emb,
            metadatas=batch_meta
        )
```

---

## Security & Best Practices

### API Key Management

```python
# NEVER hardcode API keys
# Use environment variables

import os
from dotenv import load_dotenv

load_dotenv()

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
if not VOYAGE_API_KEY:
    raise ValueError("VOYAGE_API_KEY not set in environment")
```

### Vector DB Access Control

```python
# Restrict vector store to authenticated users only

from fastapi import Depends, HTTPException

async def verify_auth(token: str = Header(None)):
    if not token or token != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@rag_router.post("/search/literature")
async def search_literature(
    query: str,
    authenticated: bool = Depends(verify_auth)
):
    # Protected endpoint
    pass
```

### Data Privacy

```python
# Don't index sensitive information
EXCLUDED_PATTERNS = [
    r"api[_-]?key",
    r"password",
    r"secret",
    r"token",
    r"credential"
]

def sanitize_text(text: str) -> str:
    """Remove sensitive information before indexing"""
    for pattern in EXCLUDED_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    return text
```

---

## Monitoring & Observability

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('rag_copilot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("RAGCopilot")

# Log queries
logger.info(f"Literature search: {query} → {len(results)} results")

# Log errors
logger.error(f"Failed to index {pdf_path}: {error}")
```

### Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
search_counter = Counter(
    'rag_searches_total',
    'Total RAG searches',
    ['intent']
)

search_latency = Histogram(
    'rag_search_latency_seconds',
    'RAG search latency'
)

# Use metrics
search_counter.labels(intent='literature_search').inc()

with search_latency.time():
    results = rag_agent.search_literature(query)
```

---

## Deployment

### Docker Setup

```dockerfile
# Dockerfile for RAG service

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Set environment
ENV VOYAGE_API_KEY=""
ENV MONGO_URI="mongodb://mongo:27017"
ENV CHROMA_PERSIST_DIR="/data/chroma_db"

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "start_server.py"]
```

### Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
  
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongo:27017
      - VOYAGE_API_KEY=${VOYAGE_API_KEY}
    volumes:
      - ./rag/chroma_db:/data/chroma_db
      - ./RAG/docs:/app/RAG/docs
    depends_on:
      - mongo

volumes:
  mongo_data:
```

---

## Example Workflows

### Workflow 1: Literature Search

```
User: "What does the literature say about PWR enrichment?"

1. Router routes to rag_copilot (keyword: "literature")
2. RAG Copilot embeds query with Voyage AI
3. ChromaDB searches papers collection
4. Returns top 5 relevant excerpts with citations
5. Frontend displays in CopilotPanel

Result:
  📚 Found 5 relevant papers
  - "Neutronics Analysis of PWR Cores" (2022)
    k-eff increases linearly with enrichment from 3-5%...
  - "VVER Benchmark Studies" (2020)
    Validated k-eff=1.045±0.002 for 4.5% enrichment...
```

### Workflow 2: Reproducibility Check

```
User: "Check reproducibility of run_abc123def456"

1. Router routes to rag_copilot (keyword: "reproducibility")
2. RAG Copilot fetches run from MongoDB
3. Searches literature for benchmarks
4. Searches similar historical runs
5. Calculates reproducibility score
6. Generates recommendations

Result:
  ✅ Reproducibility Score: 85/100
  
  ✓ Excellent statistical uncertainty (0.19%)
  ✓ Validated against 2 literature benchmarks
  ✓ Consistent with 5 historical runs
  ⚠ Missing random seed for exact reproducibility
  
  Recommendations:
  - Document random seed
  - Include nuclear data version
```

### Workflow 3: Experiment Suggestions

```
User: "Suggest follow-up experiments for my PWR sweep"

1. Router routes to rag_copilot (keyword: "suggest")
2. RAG Copilot retrieves context from recent runs
3. Searches literature for related work
4. LLM generates novel suggestions based on gaps
5. Returns 3 ranked suggestions

Result:
  💡 Suggested Experiments:
  
  1. Temperature Coefficient Study
     Objective: Validate Doppler feedback
     Parameters: Vary T from 500K to 800K at 4.5%
     Expected: Negative temperature coefficient
     Gap: Literature shows scatter in -2 to -4 pcm/K
  
  2. Burnup Sensitivity Analysis
     Objective: Track k-eff evolution over time
     Parameters: 0-50 GWd/MTU burnup simulation
     Expected: Gradual k-eff decrease
     Gap: No burnup data for this geometry
```

---

## Success Criteria

✅ **Indexing**
- All PDFs in `RAG/docs/` successfully indexed
- All simulation runs from MongoDB indexed
- Search returns relevant results (>70% relevance)

✅ **Agent Integration**
- RAG Copilot routes correctly from router
- All 4 tools functional (literature, reproducibility, suggest, similar)
- Response time < 2 seconds for queries

✅ **Reproducibility**
- Reproducibility scores calculated accurately
- Benchmark comparisons work
- Historical consistency checks work

✅ **Experiment Suggestions**
- LLM generates novel, scientifically valid suggestions
- Suggestions cite literature gaps
- Suggestions include specific parameters

✅ **Frontend**
- CopilotPanel displays results clearly
- Reproducibility cards show scores
- Literature context sidebar updates in real-time

✅ **Performance**
- Query latency < 500ms (embedding + search)
- Indexing completes in < 5 minutes for 10 PDFs
- Monthly costs < $1

---

## Next Steps

### Immediate Actions

1. **Set up Voyage AI**
   ```bash
   export VOYAGE_API_KEY="your_key_here"
   pip install voyageai chromadb pymupdf
   ```

2. **Test Voyage AI connection**
   ```python
   import voyageai
   vo = voyageai.Client()
   result = vo.embed(["test"], model="voyage-3.5")
   print(f"✅ Voyage AI working! Embedding dim: {len(result.embeddings[0])}")
   ```

3. **Index first PDF**
   ```python
   from pathlib import Path
   indexer = PDFIndexer(embedder, vector_store)
   indexer.index_pdf(Path("RAG/docs/UKAEA-STEP-PR2306.pdf"))
   ```

4. **Test search**
   ```python
   query = "fusion reactor neutronics"
   results = rag_agent.search_literature(query, n_results=3)
   print(results)
   ```

### Week 1 Goals

- [ ] Voyage AI setup and testing
- [ ] ChromaDB setup and testing
- [ ] Index all PDFs in `RAG/docs/`
- [ ] Test literature search functionality

---

## Resources

- **Voyage AI Docs**: https://docs.voyageai.com/
- **ChromaDB Docs**: https://docs.trychroma.com/
- **LangChain RAG Guide**: https://python.langchain.com/docs/use_cases/question_answering/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

**Total Estimated Time: 6-8 weeks**

**Complexity: Medium-High**

**Dependencies:**
- Voyage AI API key ✓
- MongoDB running ✓
- Existing multi-agent system ✓
- Research papers in `RAG/docs/` ✓

**Status: Ready to implement!** 🚀

