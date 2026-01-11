"""
RAG Components for Voyage AI Integration
Embeddings, Vector Store, and Document Indexing
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

import voyageai
import chromadb
from chromadb.config import Settings
from pymongo import MongoClient
import pymupdf  # PyMuPDF

from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# VOYAGE AI EMBEDDER
# ============================================================================

class VoyageEmbedder:
    """
    Voyage AI embedding service for semantic search
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Voyage AI client
        
        Args:
            api_key: Voyage AI API key (defaults to VOYAGE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment")
        
        self.client = voyageai.Client(api_key=self.api_key, max_retries=3, timeout=30)
        self.model = "voyage-3"  # Latest model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents for indexing
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        result = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="document"  # Optimized for storage
        )
        return result.embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query for search
        
        Args:
            query: Query string
            
        Returns:
            Embedding vector
        """
        result = self.client.embed(
            texts=[query],
            model=self.model,
            input_type="query"  # Optimized for retrieval
        )
        return result.embeddings[0]
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Embed documents in batches for large collections
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embed_documents(batch)
            all_embeddings.extend(embeddings)
            print(f"Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        return all_embeddings


# ============================================================================
# VECTOR STORE (ChromaDB)
# ============================================================================

class RAGVectorStore:
    """
    Vector database for semantic search using ChromaDB
    """
    
    def __init__(self, persist_directory: str = "./rag/chroma_db"):
        """
        Initialize ChromaDB vector store
        
        Args:
            persist_directory: Directory to persist vector database
        """
        self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collections
        self.papers_collection = self.client.get_or_create_collection(
            name="research_papers",
            metadata={"description": "Fusion neutronics research papers"}
        )
        
        self.runs_collection = self.client.get_or_create_collection(
            name="simulation_runs",
            metadata={"description": "OpenMC simulation results"}
        )
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection: str = "papers"
    ):
        """
        Add documents to vector store
        
        Args:
            texts: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of unique document IDs
            collection: Collection name ("papers" or "runs")
        """
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
        query_embedding: List[float],
        n_results: int = 5,
        collection: str = "papers",
        filter_dict: Dict = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            collection: Collection to search ("papers" or "runs")
            filter_dict: Metadata filters (e.g., {"year": {"$gte": 2020}})
            
        Returns:
            Search results with documents, metadatas, distances
        """
        coll = (self.papers_collection if collection == "papers" 
                else self.runs_collection)
        
        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict
        )
        
        return results
    
    def get_collection_count(self, collection: str = "papers") -> int:
        """Get number of documents in collection"""
        coll = (self.papers_collection if collection == "papers" 
                else self.runs_collection)
        return coll.count()
    
    def delete_collection(self, collection: str):
        """Delete a collection"""
        self.client.delete_collection(
            name="research_papers" if collection == "papers" else "simulation_runs"
        )


# ============================================================================
# PDF INDEXER
# ============================================================================

class PDFIndexer:
    """
    Index PDF research papers into vector store
    """
    
    def __init__(
        self,
        embedder: VoyageEmbedder,
        vector_store: RAGVectorStore
    ):
        self.embedder = embedder
        self.vector_store = vector_store
    
    def index_pdf(self, pdf_path: Path) -> None:
        """
        Index a single PDF file
        
        Args:
            pdf_path: Path to PDF file
        """
        print(f"📄 Indexing {pdf_path.name}...")
        
        # Extract text
        doc = pymupdf.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        if not text.strip():
            print(f"⚠️  Warning: {pdf_path.name} appears to be empty or image-only")
            return
        
        # Extract metadata
        metadata = self._extract_metadata(doc, text, pdf_path)
        
        # Chunk text
        chunks = self._chunk_text(text)
        print(f"  Created {len(chunks)} chunks")
        
        # Generate embeddings
        print(f"  Generating embeddings...")
        embeddings = self.embedder.embed_documents(chunks)
        
        # Create IDs
        ids = [f"{pdf_path.stem}_chunk_{i}" for i in range(len(chunks))]
        
        # Add metadata to each chunk
        metadatas = []
        for i in range(len(chunks)):
            chunk_meta = metadata.copy()
            chunk_meta['chunk_id'] = i
            chunk_meta['total_chunks'] = len(chunks)
            metadatas.append(chunk_meta)
        
        # Add to vector store
        self.vector_store.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
            collection="papers"
        )
        
        print(f"✅ Indexed {pdf_path.name}: {len(chunks)} chunks")
    
    def index_directory(self, directory: Path) -> None:
        """
        Index all PDFs in a directory
        
        Args:
            directory: Directory containing PDF files
        """
        pdf_files = list(directory.glob("*.pdf"))
        
        # Filter out Zone.Identifier files
        pdf_files = [p for p in pdf_files if "Zone.Identifier" not in p.name]
        
        print(f"\n📚 Found {len(pdf_files)} PDFs to index...\n")
        
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}]", end=" ")
            try:
                self.index_pdf(pdf_path)
            except Exception as e:
                print(f"❌ Error indexing {pdf_path.name}: {e}")
        
        print(f"\n✅ Indexing complete!")
        print(f"   Total documents in collection: {self.vector_store.get_collection_count('papers')}")
    
    def _extract_metadata(self, doc, text: str, pdf_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        keywords = self._extract_keywords(text)
        year = self._extract_year(text)
        doi = self._extract_doi(text)
        
        # Build metadata dict, filtering out None values (ChromaDB doesn't accept None)
        metadata = {
            'title': doc.metadata.get('title') or pdf_path.stem,
            'author': doc.metadata.get('author') or 'Unknown',
            'keywords': ', '.join(keywords) if keywords else 'None',
            'filename': pdf_path.name,
            'filepath': str(pdf_path)
        }
        
        # Only add year and doi if they're not None
        if year is not None:
            metadata['year'] = year
        if doi is not None:
            metadata['doi'] = doi
            
        return metadata
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract publication year from text"""
        # Look for year pattern in first 2000 chars
        matches = re.findall(r'\b(19|20)\d{2}\b', text[:2000])
        if matches:
            # Reconstruct full years from the matches
            years = []
            for match in matches:
                try:
                    # match is the full 4-digit year as a string
                    year = int(match)
                    years.append(year)
                except ValueError:
                    continue
            # Return most recent plausible year
            valid_years = [y for y in years if 1970 <= y <= 2026]
            return max(valid_years) if valid_years else None
        return None
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text"""
        doi_pattern = r'10\.\d{4,}/[^\s]+'
        match = re.search(doi_pattern, text[:5000])
        return match.group(0) if match else None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        keywords_pattern = r'keywords?:?\s*([^\n]+)'
        match = re.search(keywords_pattern, text[:5000], re.IGNORECASE)
        if match:
            kw_text = match.group(1)
            return [kw.strip() for kw in re.split(r'[,;]', kw_text)]
        return []
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Chunk text into smaller pieces
        
        Args:
            text: Full text to chunk
            chunk_size: Target size for each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


# ============================================================================
# SIMULATION RUNS INDEXER
# ============================================================================

class SimulationIndexer:
    """
    Index simulation runs from MongoDB into vector store
    """
    
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
        """
        Index a single simulation run
        
        Args:
            run_id: Run ID to index
        """
        # Get run from MongoDB
        run = self.runs_collection.find_one({"run_id": run_id})
        
        if not run:
            print(f"❌ Run {run_id} not found")
            return
        
        # Create text description
        text = self._format_run_as_text(run)
        
        # Generate embedding
        embedding = self.embedder.embed_query(text)
        
        # Extract metadata (filter out None values for ChromaDB)
        metadata = {
            'run_id': run['run_id'],
            'geometry': run.get('geometry') or 'Unknown',
            'enrichment_pct': float(run.get('enrichment_pct', 0)),
            'temperature_K': float(run.get('temperature_K', 0)),
            'keff': float(run.get('keff', 0)),
            'keff_std': float(run.get('keff_std', 0)),
            'timestamp': str(run.get('created_at', '')),
            'status': run.get('status') or 'unknown'
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
        """
        Index all simulation runs from MongoDB
        
        Args:
            limit: Maximum number of runs to index (None = all)
        """
        query = {}
        cursor = self.runs_collection.find(query)
        
        if limit:
            cursor = cursor.limit(limit)
        
        runs = list(cursor)
        total = len(runs)
        
        print(f"\n🔬 Indexing {total} simulation runs...\n")
        
        count = 0
        for i, run in enumerate(runs, 1):
            try:
                print(f"[{i}/{total}] ", end="")
                self.index_run(run['run_id'])
                count += 1
            except Exception as e:
                print(f"❌ Error indexing {run.get('run_id', 'unknown')}: {e}")
        
        print(f"\n✅ Indexed {count} simulation runs")
        print(f"   Total documents in collection: {self.vector_store.get_collection_count('runs')}")
    
    def _format_run_as_text(self, run: Dict[str, Any]) -> str:
        """Format run as searchable text"""
        criticality = self._get_criticality_status(run.get('keff', 0))
        
        text = f"""
Simulation Run {run['run_id']}

Geometry: {run.get('geometry', 'Unknown')}
Configuration: {run.get('geometry', 'Unknown')} reactor with {run.get('enrichment_pct', 0)}% enrichment
Temperature: {run.get('temperature_K', 0)} Kelvin
Materials: {', '.join(run.get('materials', []))}

Simulation Parameters:
- Particles: {run.get('n_particles', 'Unknown')}
- Batches: {run.get('n_batches', 'Unknown')}
- Nuclear Data: {run.get('nuclear_data', 'Unknown')}

Results:
- k-effective: {run.get('keff', 'Unknown')} ± {run.get('keff_std', 'Unknown')}
- Status: {criticality}

Timestamp: {run.get('created_at', 'Unknown')}
        """.strip()
        
        return text
    
    def _get_criticality_status(self, keff: float) -> str:
        """Get criticality status text"""
        if keff < 0.98:
            return "Subcritical (k-eff < 0.98)"
        elif keff <= 1.02:
            return "Critical (0.98 ≤ k-eff ≤ 1.02)"
        else:
            return "Supercritical (k-eff > 1.02)"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def setup_rag_components(
    voyage_api_key: str = None,
    mongo_uri: str = None,
    chroma_dir: str = "./rag/chroma_db"
) -> tuple:
    """
    Setup all RAG components
    
    Args:
        voyage_api_key: Voyage AI API key
        mongo_uri: MongoDB URI
        chroma_dir: ChromaDB persist directory
        
    Returns:
        Tuple of (embedder, vector_store, pdf_indexer, sim_indexer)
    """
    # Initialize embedder
    embedder = VoyageEmbedder(api_key=voyage_api_key)
    
    # Initialize vector store
    vector_store = RAGVectorStore(persist_directory=chroma_dir)
    
    # Initialize PDF indexer
    pdf_indexer = PDFIndexer(embedder, vector_store)
    
    # Initialize simulation indexer (if MongoDB available)
    sim_indexer = None
    if mongo_uri:
        mongo_client = MongoClient(mongo_uri)
        sim_indexer = SimulationIndexer(mongo_client, embedder, vector_store)
    
    return embedder, vector_store, pdf_indexer, sim_indexer


if __name__ == "__main__":
    # Test setup
    print("Testing RAG components...")
    
    embedder, vector_store, pdf_indexer, sim_indexer = setup_rag_components()
    
    print(f"✅ Voyage AI embedder initialized")
    print(f"✅ Vector store initialized")
    print(f"   Papers collection: {vector_store.get_collection_count('papers')} documents")
    print(f"   Runs collection: {vector_store.get_collection_count('runs')} documents")

