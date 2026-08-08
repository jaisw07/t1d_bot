import os
import sys

# Add the project root to the Python path so imports like `src.*` work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import threading

load_dotenv()

from src.ingestion.hindi_decoder import is_scrambled_hindi, decode_hindi_text
from src.sheets_logger import log_query

# Shared singletons for CorpusStore and Generator
_corpus_store = None
_generator = None
_model_ready = False
_store_lock = threading.Lock()
_generator_lock = threading.Lock()

def get_corpus_store(collection_name: str = "t1d_corpus"):
    global _corpus_store
    if _corpus_store is None:
        with _store_lock:
            if _corpus_store is None:
                from src.corpus_store.store import CorpusStore
                _corpus_store = CorpusStore(collection_name=collection_name)
                if hasattr(_corpus_store.embedder, "_init_model"):
                    _corpus_store.embedder._init_model()
    return _corpus_store

def get_generator():
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                from src.llm import get_llm_client
                from src.generation.generator import Generator
                try:
                    client = get_llm_client()
                    _generator = Generator(llm_client=client)
                except Exception as e:
                    print(f"[WARNING] Failed to initialize LLM generator: {e}")
                    return None
    return _generator

def _bg_eager_load():
    global _model_ready
    try:
        collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
        store = get_corpus_store(collection_name)
        device_name = "CPU"
        if store and hasattr(store, "embedder") and hasattr(store.embedder, "device") and store.embedder.device:
            device_name = str(store.embedder.device).upper()
        get_generator()
        _model_ready = True
        print(f"[INFO] BGE-M3 and RAGBot models loaded and ready (embedder on {device_name}, LLM via Ollama).")
    except Exception as e:
        print(f"Warning: Eager model initialization failed during startup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eagerly load BGE-M3 embedder and LLM generator in background thread on startup."""
    threading.Thread(target=_bg_eager_load, daemon=True).start()
    yield

app = FastAPI(
    title="T1D RAG Bot Service",
    description="Microservice API & Static SPA for RAG exploration & clinical query generation",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static SPA directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

class QueryRequest(BaseModel):
    query: str = Field(..., description="User search / clinical query string")
    language: str = Field(default="english", description="Target response language (english, hindi, etc.)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    collection: Optional[str] = None
    content_type: Optional[str] = None
    contains_dosage: Optional[bool] = None
    contains_recommendation: Optional[bool] = None
    topic: Optional[str] = None
    language_filter: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    citations: List[str]
    language: str
    retrieved_chunks: List[Dict[str, Any]]

@app.get("/")
def serve_spa():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Static SPA index.html not found"}

@app.get("/health")
def health_check():
    collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
    return {
        "status": "ok",
        "service": "t1d_ragbot_service",
        "collection": collection_name,
        "ready": _model_ready
    }

def _clean_and_serialize_chunks(results: List[Any]) -> List[Dict[str, Any]]:
    """Helper to convert SearchResult objects to dicts and auto-decode scrambled Hindi text."""
    serialized = []
    for c in results:
        cdict = c.__dict__.copy()
        sec_title = cdict.get("section_title", "")
        if sec_title and is_scrambled_hindi(sec_title):
            cdict["section_title"] = decode_hindi_text(sec_title)
        
        text_val = cdict.get("text", "")
        if text_val and is_scrambled_hindi(text_val):
            cdict["text"] = decode_hindi_text(text_val)
            
        serialized.append(cdict)
    return serialized

@app.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
    store = get_corpus_store(collection_name)
    
    # Build filter dictionary
    filters = {}
    if req.collection:
        filters["collection"] = req.collection
    if req.content_type:
        filters["content_type"] = req.content_type
    if req.contains_dosage is not None:
        filters["contains_dosage"] = req.contains_dosage
    if req.contains_recommendation is not None:
        filters["contains_recommendation"] = req.contains_recommendation
    if req.topic:
        filters["topic"] = req.topic
    if req.language_filter:
        filters["language"] = req.language_filter

    try:
        results = store.search(query=req.query, filters=filters, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search execution failed: {str(e)}")

    cleaned_chunks = _clean_and_serialize_chunks(results)

    generator = get_generator()
    if not generator:
        # Fallback response if LLM client is unavailable
        citations = [f"{c.source_document}, p.{c.start_page}" for c in results]
        return QueryResponse(
            answer="LLM generator unavailable. Context chunks retrieved successfully.",
            citations=citations,
            language=req.language,
            retrieved_chunks=cleaned_chunks
        )

    try:
        rag_resp = generator.generate(
            query=req.query,
            retrieved_chunks=results,
            language=req.language
        )
        
        # Log query-answer pair to Google Sheets & local JSONL
        if rag_resp and rag_resp.answer:
            try:
                log_query(
                    question=req.query,
                    answer=rag_resp.answer,
                    citations=rag_resp.citations or []
                )
            except Exception as log_err:
                print(f"[WARNING] Query logging failed: {log_err}")

        return QueryResponse(
            answer=rag_resp.answer,
            citations=rag_resp.citations,
            language=rag_resp.language,
            retrieved_chunks=cleaned_chunks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG generation failed: {str(e)}")

@app.post("/search")
def handle_search(req: QueryRequest):
    collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
    try:
        store = get_corpus_store(collection_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to corpus store: {str(e)}")
        
    filters = {}
    if req.collection:
        filters["collection"] = req.collection
    if req.content_type:
        filters["content_type"] = req.content_type
    if req.contains_dosage is not None:
        filters["contains_dosage"] = req.contains_dosage
    if req.contains_recommendation is not None:
        filters["contains_recommendation"] = req.contains_recommendation
    if req.topic:
        filters["topic"] = req.topic
    if req.language_filter:
        filters["language"] = req.language_filter

    try:
        results = store.search(query=req.query, filters=filters, top_k=req.top_k)
        cleaned_chunks = _clean_and_serialize_chunks(results)
        return {"retrieved_chunks": cleaned_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search execution failed: {str(e)}")

@app.get("/stats")
def get_stats():
    collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")
    try:
        store = get_corpus_store(collection_name)
        if store.client.has_collection(collection_name):
            store.client.load_collection(collection_name)
            res_count = store.client.query(collection_name=collection_name, filter="", output_fields=["count(*)"])
            num_entities = res_count[0].get("count(*)", 0) if res_count else 0
            
            # Query unique source documents
            samples = store.client.query(
                collection_name=collection_name,
                filter="",
                limit=16384,
                output_fields=["source_document"]
            )
            unique_docs = list(set(s.get("source_document") for s in samples if s.get("source_document")))
            
            return {
                "collection": collection_name,
                "num_entities": num_entities,
                "documents": unique_docs
            }
        else:
            return {"error": f"Collection '{collection_name}' does not exist."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("RAG_SERVICE_PORT", "8002"))
    reload_env = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("src.service:app", host="0.0.0.0", port=port, reload=reload_env)
