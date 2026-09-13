import os
import json
import uuid
import shutil
from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from backend.pipeline import run_query_pipeline, stream_query_pipeline
from backend.pdf_pipeline import run_pdf_pipeline, stream_pdf_pipeline
from backend.agents.pdf_processor import (
    extract_pdf_metadata_and_text, extract_pdf_figures, chunk_document,
    compute_chunk_vectors, extract_references, build_document_outline
)
from backend.agents.citation_graph_builder import build_citation_graph_for_session
from backend.database import (
    init_db, get_all_cached_papers, get_db_connection, clear_all_cache, get_cache_stats,
    save_pdf_session, get_pdf_session, get_all_pdf_sessions, update_pdf_session_status,
    delete_pdf_session, save_pdf_file, update_pdf_file_status, save_pdf_chunks,
    save_pdf_figures, get_pdf_figures_by_session, save_pdf_references,
    get_citation_graph_data, get_pdf_chunks_by_session
)

app = FastAPI(
    title="AI Research Workbench v3 Backend",
    description="Multi-Agent Autonomous Research Agent with Dual-Mode Literature Synthesis and PDF Document Analysis",
    version="3.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite database
init_db()

class QueryRequest(BaseModel):
    query: str
    provider_agent2: Optional[str] = "auto"
    provider_agent4: Optional[str] = "auto"
    similarity_threshold: Optional[float] = 0.80
    paper_limit: Optional[int] = 5
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    scraper_sources: Optional[str] = "all"
    disable_fallback: Optional[bool] = False
    disable_fallback_agent2: Optional[bool] = False
    disable_fallback_agent4: Optional[bool] = False

@app.get("/api/status")
def get_api_status():
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {
        "status": "online",
        "service": "AI Research Workbench v2",
        "llm_budget_limit": 2,
        "providers_available": {
            "gemini_live": has_gemini,
            "anthropic_live": has_anthropic,
            "openai_live": has_openai,
            "semantic_scholar": True,
            "arxiv": True,
            "sqlite_cacher": True
        }
    }

@app.post("/api/pipeline/run")
async def run_pipeline_sync(req: QueryRequest):
    result = await run_query_pipeline(req.query, req.dict())
    return result

@app.get("/api/pipeline/stream")
async def stream_query_endpoint(
    query: str, 
    provider_agent2: str = "auto", 
    provider_agent4: str = "auto",
    disable_fallback_agent2: bool = False,
    disable_fallback_agent4: bool = False,
    scraper_sources: str = "all",
    similarity_threshold: float = 0.80,
    paper_limit: int = 5,
    gemini_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    serpapi_key: Optional[str] = None
):
    """
    Server-Sent Events (SSE) endpoint for streaming real-time stage hand-offs.
    """
    if not query:
        return {"error": "Query parameter 'query' is required"}

    config = {
        "provider_agent2": provider_agent2,
        "provider_agent4": provider_agent4,
        "disable_fallback_agent2": disable_fallback_agent2,
        "disable_fallback_agent4": disable_fallback_agent4,
        "scraper_sources": scraper_sources,
        "similarity_threshold": similarity_threshold,
        "paper_limit": paper_limit,
        "gemini_key": gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": anthropic_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        "serpapi_key": serpapi_key or os.environ.get("SERPAPI_API_KEY", "")
    }
    return StreamingResponse(
        stream_query_pipeline(query, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/cache/papers")
def list_cached_papers(limit: int = 50):
    papers = get_all_cached_papers(limit)
    return {"count": len(papers), "papers": papers}

@app.get("/api/cache/runs")
def list_past_runs(limit: int = 10):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, query, tokens_used, elapsed_seconds, created_at FROM pipeline_runs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"runs": rows}

@app.get("/api/cache/stats")
def cache_stats():
    return get_cache_stats()

@app.post("/api/cache/clear")
def clear_cache():
    result = clear_all_cache()
    return {"status": "success", "cleared": result}


# =========================================================
# V3: PDF DOCUMENT ANALYSIS ENDPOINTS
# =========================================================

class PDFQueryRequest(BaseModel):
    session_id: str
    action: str = "qa"
    query: Optional[str] = ""
    provider: Optional[str] = "auto"
    chat_history: Optional[List[Dict[str, str]]] = None
    analysis_type: Optional[str] = "comprehensive"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    disable_fallback: Optional[bool] = False
    demo_mode: Optional[bool] = False

UPLOADS_BASE = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_BASE, exist_ok=True)

@app.post("/api/pdf/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Accepts 1 to 10 PDF files (max 50MB each).
    Saves to backend/uploads/{session_id}/original/.
    Runs Agent P1 extraction immediately (text, figures, chunks, references, outline).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per session.")

    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    session_dir = os.path.join(UPLOADS_BASE, session_id)
    orig_dir = os.path.join(session_dir, "original")
    figs_dir = os.path.join(session_dir, "figures")
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(figs_dir, exist_ok=True)

    save_pdf_session(session_id, total_files=len(files))

    total_pages = 0
    total_chunks = 0
    total_words = 0
    total_figures = 0
    total_refs = 0
    file_summaries = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a PDF.")

        file_id = f"f_{uuid.uuid4().hex[:8]}"
        dest_path = os.path.join(orig_dir, file.filename)
        
        # Save file to disk
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File '{file.filename}' exceeds 50MB limit.")
            
        with open(dest_path, "wb") as f_out:
            f_out.write(content)

        file_size = len(content)

        # Agent P1 extraction
        try:
            extracted = extract_pdf_metadata_and_text(dest_path)
            meta = extracted["metadata"]
            full_text = extracted["full_text"]
            page_count = extracted["page_count"]
            word_count = extracted["word_count"]

            # Figures
            figures = extract_pdf_figures(dest_path, figs_dir, session_id, file_id)

            # Chunks
            chunks = chunk_document(full_text, file_id, chunk_size=500, overlap=50, page_count=page_count)
            chunks = compute_chunk_vectors(chunks)

            # References
            refs = extract_references(full_text, file_id)

            # Outline
            outline = build_document_outline(full_text)

            # Save in SQLite
            save_pdf_file(
                file_id=file_id,
                session_id=session_id,
                original_filename=file.filename,
                stored_path=dest_path,
                file_size_bytes=file_size,
                page_count=page_count,
                word_count=word_count,
                title=meta.get("title", file.filename),
                authors=meta.get("authors", ""),
                subject=meta.get("subject", ""),
                creation_date=meta.get("creation_date", ""),
                outline_json=json.dumps(outline),
                extraction_status="complete"
            )
            save_pdf_chunks(session_id, file_id, chunks)
            save_pdf_figures(session_id, file_id, figures)
            save_pdf_references(session_id, file_id, refs)

            total_pages += page_count
            total_chunks += len(chunks)
            total_words += word_count
            total_figures += len(figures)
            total_refs += len(refs)

            file_summaries.append({
                "file_id": file_id,
                "filename": file.filename,
                "title": meta.get("title", file.filename),
                "pages": page_count,
                "words": word_count,
                "figures_count": len(figures),
                "references_count": len(refs),
                "status": "complete"
            })

        except Exception as e:
            err_msg = str(e)
            print(f"[Upload Error] Error processing {file.filename}: {err_msg}")
            save_pdf_file(
                file_id=file_id,
                session_id=session_id,
                original_filename=file.filename,
                stored_path=dest_path,
                file_size_bytes=file_size,
                extraction_status="error",
                extraction_error=err_msg
            )
            file_summaries.append({
                "file_id": file_id,
                "filename": file.filename,
                "status": "error",
                "error": err_msg
            })

    update_pdf_session_status(
        session_id=session_id,
        status="ready",
        total_files=len(files),
        total_pages=total_pages,
        total_chunks=total_chunks,
        total_words=total_words,
        total_figures=total_figures,
        total_references=total_refs
    )

    return {
        "status": "success",
        "session_id": session_id,
        "files": file_summaries,
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "total_figures": total_figures,
        "total_references": total_refs
    }

@app.get("/api/pdf/sessions")
def list_pdf_sessions(limit: int = 20):
    return {"sessions": get_all_pdf_sessions(limit)}

@app.get("/api/pdf/session/{session_id}")
def get_pdf_session_details(session_id: str):
    session = get_pdf_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="PDF session not found.")
    
    figures = get_pdf_figures_by_session(session_id)
    refs = get_citation_graph_data(session_id)
    session["figures"] = figures
    session["citation_graph"] = refs
    return session

@app.delete("/api/pdf/session/{session_id}")
def remove_pdf_session(session_id: str):
    res = delete_pdf_session(session_id)
    return {"status": "success", "deleted": res}

@app.post("/api/pdf/qa")
async def pdf_qa_endpoint(req: PDFQueryRequest):
    result = await run_pdf_pipeline(
        session_id=req.session_id,
        action="qa",
        query=req.query or "",
        config=req.dict()
    )
    return result

@app.get("/api/pdf/stream")
async def stream_pdf_endpoint(
    session_id: str,
    action: str = "summarize",
    query: str = "",
    provider: str = "auto",
    disable_fallback: bool = False,
    demo_mode: bool = False,
    analysis_type: str = "methodology",
    gemini_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
):
    config = {
        "provider": provider,
        "disable_fallback": disable_fallback,
        "demo_mode": demo_mode,
        "analysis_type": analysis_type,
        "gemini_key": gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": anthropic_key or os.environ.get("ANTHROPIC_API_KEY", "")
    }
    return StreamingResponse(
        stream_pdf_pipeline(session_id, action, query, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/pdf/chunks/{session_id}")
def list_session_chunks(session_id: str, limit: int = 50):
    chunks = get_pdf_chunks_by_session(session_id, limit=limit)
    return {"count": len(chunks), "chunks": chunks}

@app.get("/api/pdf/figures/{session_id}")
def list_session_figures(session_id: str):
    return {"figures": get_pdf_figures_by_session(session_id)}

@app.get("/api/pdf/citation-graph/{session_id}")
async def fetch_citation_graph(session_id: str):
    return get_citation_graph_data(session_id)

# Mount uploads static directory for figure image rendering
app.mount("/uploads", StaticFiles(directory=UPLOADS_BASE), name="uploads")

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


