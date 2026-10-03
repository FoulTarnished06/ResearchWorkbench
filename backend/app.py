import os
import json
import uuid
import re
import shutil
import asyncio
import aiofiles
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Response, Query, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel, Field

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
from backend.agents.followup_synthesizer import run_followup_synthesis
from backend.agents.dialogue_synthesizer import run_dialogue_turn
from backend.database import (
    init_db, get_all_cached_papers, get_db_connection, clear_all_cache, get_cache_stats,
    save_pdf_session, get_pdf_session, get_all_pdf_sessions, update_pdf_session_status,
    delete_pdf_session, save_pdf_file, update_pdf_file_status, save_pdf_chunks,
    save_pdf_figures, get_pdf_figures_by_session, save_pdf_references,
    get_citation_graph_data, get_pdf_chunks_by_session,
    get_run_history, get_run_by_id, delete_run,
    get_all_prompt_history, get_followups_for_run, delete_followup,
    save_dialogue_message, get_dialogue_history, clear_dialogue_history,
    create_user, get_user_by_username, get_user_by_email, get_user_by_id, update_user_last_login
)
from backend.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    get_current_user_optional, get_current_user_required,
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
)
from backend.export import (
    export_to_docx, export_to_latex, export_to_markdown,
    export_dialogue_to_markdown, export_dialogue_to_latex
)
from backend.logger import get_logger

logger = get_logger("AppServer")

# Rate Limiter (BONUS-07)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI Research Workbench v3.0 Backend",
    description="Multi-Agent Autonomous Research Agent with Dual-Mode Literature Synthesis and PDF Document Analysis",
    version="3.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# SEC-02: CORS Configuration (Local development, custom domain, and cloud platforms)
ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000"
]
cors_env = os.getenv("ALLOWED_ORIGINS", "")
if cors_env:
    for o in cors_env.split(","):
        if o.strip() and o.strip() not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(o.strip())

ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"https?://.*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Initialize SQLite database
init_db()

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User research question")
    provider_agent2: Optional[str] = "auto"
    provider_agent4: Optional[str] = "auto"
    similarity_threshold: Optional[float] = 0.55
    paper_limit: Optional[int] = 5
    execution_mode: Optional[str] = "deep"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    scraper_sources: Optional[str] = "all"
    active_scrapers: Optional[List[str]] = None
    max_pdf_pages: Optional[int] = 15
    disable_fallback: Optional[bool] = False
    disable_fallback_agent2: Optional[bool] = False
    disable_fallback_agent4: Optional[bool] = False
    demo_mode: Optional[bool] = False
    bypass_cache: Optional[bool] = False

class PDFQueryRequest(BaseModel):
    session_id: str
    action: str = "qa"
    query: Optional[str] = Field("", max_length=1000, description="PDF query or instruction")
    provider: Optional[str] = "auto"
    chat_history: Optional[List[Dict[str, str]]] = None
    analysis_type: Optional[str] = "comprehensive"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    disable_fallback: Optional[bool] = False
    demo_mode: Optional[bool] = False

class FollowupRequest(BaseModel):
    parent_run_id: str
    claim_id: Optional[str] = None
    target_topic: Optional[str] = None
    query: str = Field(..., min_length=1, max_length=1000, description="Targeted follow-up question")
    provider: Optional[str] = "auto"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    disable_fallback: Optional[bool] = False

class DialogueChatRequest(BaseModel):
    run_id: str
    message: str = Field(..., min_length=1, max_length=1000, description="Inquiry for continuous research dialogue")
    provider: Optional[str] = "auto"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    disable_fallback: Optional[bool] = False

class ExportRequest(BaseModel):
    dossier: Dict[str, Any]

class DialogueExportRequest(BaseModel):
    run_id: str
    format: Optional[str] = "markdown"

UPLOADS_BASE = os.path.realpath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOADS_BASE, exist_ok=True)

@app.get("/api/health")
def get_api_health():
    """Standard health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}

@app.get("/api/status")
def get_api_status():
    """Returns runtime health and provider readiness (BUG-03 unified to v3.0.0)."""
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {
        "status": "online",
        "service": "AI Research Workbench v3.0",
        "llm_budget_limit": 2,
        "providers_available": {
            "gemini_live": has_gemini,
            "anthropic_live": has_anthropic,
            "crossref": True,
            "doaj": True,
            "openalex": True,
            "semantic_scholar": True,
            "europepmc": True,
            "pubmed_ncbi": True,
            "sqlite_cacher": True
        }
    }

@app.get("/api/config")
async def get_config():
    """Returns available model providers, budget limit, and scraper status."""
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {
        "status": "online",
        "service": "AI Research Workbench v3.0",
        "llm_budget_limit": 2,
        "providers_available": {
            "gemini_live": has_gemini,
            "anthropic_live": has_anthropic,
            "crossref": True,
            "doaj": True,
            "openalex": True,
            "semantic_scholar": True,
            "europepmc": True,
            "pubmed_ncbi": True,
            "sqlite_cacher": True
        }
    }

# =========================================================
# USER AUTHENTICATION & SESSION ENDPOINTS (AUTH-01)
# =========================================================

@app.post("/api/auth/register", response_model=TokenResponse)
@limiter.limit("10/minute")
async def register_user_endpoint(request: Request, response: Response, req: UserRegisterRequest):
    """Registers a new user account with hashed password and generates access JWT."""
    existing_username = get_user_by_username(req.username)
    if existing_username:
        raise HTTPException(status_code=400, detail="Username is already taken.")
    
    existing_email = get_user_by_email(req.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    pwd_hash = hash_password(req.password)
    user = create_user(username=req.username, email=req.email, password_hash=pwd_hash)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user account.")
    
    token = create_access_token({"sub": user["id"], "username": user["username"], "role": user["role"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    user_resp = UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user.get("role", "user"),
        created_at=str(user.get("created_at") or ""),
        last_login=str(user.get("last_login") or "")
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("15/minute")
async def login_user_endpoint(request: Request, response: Response, req: UserLoginRequest):
    """Authenticates user credentials and issues an access JWT."""
    username_or_email = req.username.strip()
    user = get_user_by_username(username_or_email)
    if not user:
        user = get_user_by_email(username_or_email)
        
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    update_user_last_login(user["id"])
    token = create_access_token({"sub": user["id"], "username": user["username"], "role": user["role"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    user_resp = UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user.get("role", "user"),
        created_at=str(user.get("created_at") or ""),
        last_login=str(user.get("last_login") or "")
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Returns the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user.get("role", "user"),
        created_at=str(current_user.get("created_at") or ""),
        last_login=str(current_user.get("last_login") or "")
    )

@app.post("/api/auth/logout")
async def logout_user_endpoint(response: Response):
    """Clears authentication cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("workbench_token")
    return {"status": "ok", "message": "Successfully signed out."}

# =========================================================
# RESEARCH PIPELINE EXECUTION (CORE AGENTS 1-4)
# =========================================================

@app.post("/api/pipeline/run")
@limiter.limit("20/minute")
async def run_pipeline_sync(request: Request, req: QueryRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Executes full research pipeline synchronously."""
    # BUG-04: Upgrade .dict() to .model_dump()
    cfg = req.model_dump()
    if current_user:
        cfg["user_id"] = current_user["id"]
    result = await run_query_pipeline(req.query, cfg)
    return result

@app.post("/api/pipeline/stream")
@limiter.limit("30/minute")
async def stream_query_endpoint_post(request: Request, req: QueryRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    SEC-01 FIX: Secure POST SSE streaming endpoint.
    Transmits API keys in the POST body or headers, avoiding query parameter leakage.
    """
    cfg = req.model_dump()
    if current_user:
        cfg["user_id"] = current_user["id"]
    return StreamingResponse(
        stream_query_pipeline(req.query, cfg),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/pipeline/stream")
async def stream_query_endpoint_get(
    request: Request,
    query: str, 
    provider_agent2: str = "auto", 
    provider_agent4: str = "auto",
    disable_fallback_agent2: bool = False,
    disable_fallback_agent4: bool = False,
    demo_mode: bool = False,
    scraper_sources: str = "all",
    similarity_threshold: float = 0.55,
    paper_limit: int = 5,
    execution_mode: str = "deep",
    gemini_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    serpapi_key: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Backward-compatible GET SSE stream (prefer POST /api/pipeline/stream for maximum credential privacy).
    """
    if not query:
        raise HTTPException(status_code=400, detail="Parameter 'query' is required.")

    if gemini_key or anthropic_key or serpapi_key:
        raise HTTPException(
            status_code=400,
            detail="Passing API keys in GET query parameters is prohibited for security. Please use POST /api/pipeline/stream."
        )

    config = {
        "provider_agent2": provider_agent2,
        "provider_agent4": provider_agent4,
        "disable_fallback_agent2": disable_fallback_agent2,
        "disable_fallback_agent4": disable_fallback_agent4,
        "demo_mode": demo_mode,
        "scraper_sources": scraper_sources,
        "similarity_threshold": similarity_threshold,
        "paper_limit": paper_limit,
        "execution_mode": execution_mode,
        "gemini_key": gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": anthropic_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        "serpapi_key": serpapi_key or os.environ.get("SERPAPI_API_KEY", ""),
        "user_id": current_user["id"] if current_user else None
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

# =========================================================
# RESEARCH HISTORY & PAST OUTPUTS (BONUS-01, BONUS-02)
# =========================================================

@app.get("/api/history")
def get_history(limit: int = 50, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    BONUS-01: Fetches persistent history of past research syntheses.
    Allows user to browse queries, dates, token usage, and summaries.
    """
    user_id = current_user["id"] if current_user else None
    runs = get_run_history(limit=limit, user_id=user_id)
    return {"status": "success", "count": len(runs), "runs": runs}

@app.get("/api/history/prompts")
def get_prompt_history_endpoint(limit: int = 50):
    """
    Returns the comprehensive hierarchical prompt & follow-up tree:
    Every parent query along with all nested follow-up questions,
    timestamps, and total thread token metrics.
    """
    prompts = get_all_prompt_history(limit=limit)
    return {"status": "success", "count": len(prompts), "prompts": prompts}

@app.get("/api/history/run/{run_id}/followups")
def get_run_followups_endpoint(run_id: str):
    """Returns all follow-up questions asked under a specific parent run."""
    clean_id = os.path.basename(run_id.strip("/\\"))
    followups = get_followups_for_run(clean_id)
    return {"status": "success", "parent_run_id": clean_id, "count": len(followups), "followups": followups}

@app.delete("/api/history/followup/{followup_id}")
def delete_followup_endpoint(followup_id: str):
    """Deletes a single follow-up question."""
    clean_id = os.path.basename(followup_id.strip("/\\"))
    success = delete_followup(clean_id)
    if not success:
        raise HTTPException(status_code=404, detail="Follow-up not found or already deleted.")
    return {"status": "success", "deleted": True}

@app.get("/api/history/{run_id}")
def get_history_item(run_id: str):
    """
    BONUS-02: Retrieves full synthesized output for instant zero-token replay.
    """
    clean_id = os.path.basename(run_id.strip("/\\"))
    run = get_run_by_id(clean_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Research run '{run_id}' not found.")
    return run

@app.delete("/api/history/{run_id}")
def delete_history_item(run_id: str):
    """Deletes a run from history."""
    clean_id = os.path.basename(run_id.strip("/\\"))
    success = delete_run(clean_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or already deleted.")
    return {"status": "success", "deleted": True}

# =========================================================
# CONTEXTUAL FOLLOW-UP ENGINE (FOL-02, FOL-03)
# =========================================================

@app.post("/api/pipeline/followup")
@limiter.limit("30/minute")
async def pipeline_followup_endpoint(request: Request, req: FollowupRequest):
    """
    FOL-02 / FOL-03: Executes an ultra-low-token targeted follow-up synthesis.
    Extracts atomic context from local SQLite (IDCC), bypassing external web re-scraping.
    Consumes ~400-650 tokens total (an 80%+ reduction vs standard multi-turn chat).
    """
    clean_parent_id = os.path.basename(req.parent_run_id.strip("/\\"))
    try:
        result = await run_followup_synthesis(
            parent_run_id=clean_parent_id,
            query=req.query,
            claim_id=req.claim_id,
            target_topic=req.target_topic,
            provider=req.provider or "auto",
            gemini_key=req.gemini_key,
            anthropic_key=req.anthropic_key,
            disable_fallback=req.disable_fallback or False
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Follow-up synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Follow-up synthesis failed: {str(e)}")

# =========================================================
# CONTINUOUS RESEARCH DIALOGUE (CHAT-03)
# =========================================================

@app.post("/api/dialogue/chat")
@limiter.limit("30/minute")
async def dialogue_chat_endpoint(request: Request, req: DialogueChatRequest):
    """
    CHAT-03: Executes a continuous multi-turn research dialogue turn via DHS-RCC.
    Strictly bounds prompt input to <= 750 tokens, yielding 80-88% savings vs web chat.
    """
    clean_run_id = os.path.basename(req.run_id.strip("/\\"))
    try:
        result = await run_dialogue_turn(
            run_id=clean_run_id,
            user_message=req.message,
            provider=req.provider or "auto",
            gemini_key=req.gemini_key,
            anthropic_key=req.anthropic_key,
            disable_fallback=req.disable_fallback or False
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Dialogue interaction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dialogue interaction failed: {str(e)}")

@app.get("/api/dialogue/history/{run_id}")
def get_dialogue_history_endpoint(run_id: str):
    """Retrieves full multi-turn dialogue history for a research session."""
    clean_id = os.path.basename(run_id.strip("/\\"))
    history = get_dialogue_history(clean_id)
    return {"status": "success", "run_id": clean_id, "count": len(history), "messages": history}

@app.delete("/api/dialogue/history/{run_id}")
def clear_dialogue_history_endpoint(run_id: str):
    """Clears all dialogue messages for a research session."""
    clean_id = os.path.basename(run_id.strip("/\\"))
    success = clear_dialogue_history(clean_id)
    return {"status": "success", "cleared": True}

# =========================================================
# MULTI-FORMAT EXPORT (BONUS-03)
# =========================================================

@app.post("/api/export/docx")
def export_docx_endpoint(req: ExportRequest):
    """BONUS-03: Exports synthesized research dossier to a formatted Word document (.docx)."""
    try:
        buffer = export_to_docx(req.dossier)
        headers = {
            "Content-Disposition": f'attachment; filename="Research_Dossier_{uuid.uuid4().hex[:6]}.docx"'
        }
        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Docx export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Word export error: {e}")

@app.post("/api/export/latex")
def export_latex_endpoint(req: ExportRequest):
    """BONUS-03: Exports synthesized research dossier to a LaTeX article document (.tex)."""
    try:
        latex_str = export_to_latex(req.dossier)
        headers = {
            "Content-Disposition": f'attachment; filename="Research_Dossier_{uuid.uuid4().hex[:6]}.tex"'
        }
        return Response(
            content=latex_str,
            media_type="application/x-latex",
            headers=headers
        )
    except Exception as e:
        logger.error(f"LaTeX export failed: {e}")
        raise HTTPException(status_code=500, detail=f"LaTeX export error: {e}")

@app.post("/api/export/markdown")
def export_markdown_endpoint(req: ExportRequest):
    """Point 33: Exports synthesized research dossier to a publication-grade GitHub Flavored Markdown document (.md)."""
    try:
        md_str = export_to_markdown(req.dossier)
        headers = {
            "Content-Disposition": f'attachment; filename="Research_Dossier_{uuid.uuid4().hex[:6]}.md"'
        }
        return Response(
            content=md_str,
            media_type="text/markdown; charset=utf-8",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Markdown export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Markdown export error: {e}")

@app.post("/api/export/dialogue")
def export_dialogue_endpoint(req: DialogueExportRequest):
    """Point 29: Exports continuous research dialogue history to Markdown or LaTeX."""
    try:
        clean_id = os.path.basename(req.run_id.strip("/\\"))
        messages = get_dialogue_history(clean_id)
        run = get_run_by_id(clean_id) or {}
        query = run.get("query", f"Run {clean_id}")
        initial_dossier = run.get("results_json")
        if isinstance(initial_dossier, str):
            try:
                initial_dossier = json.loads(initial_dossier)
            except Exception:
                initial_dossier = None

        fmt = (req.format or "markdown").lower()
        if fmt == "latex":
            doc_str = export_dialogue_to_latex(query, messages, initial_dossier)
            headers = {"Content-Disposition": f'attachment; filename="Dialogue_{clean_id}.tex"'}
            return Response(content=doc_str, media_type="application/x-latex", headers=headers)
        else:
            doc_str = export_dialogue_to_markdown(query, messages, initial_dossier)
            headers = {"Content-Disposition": f'attachment; filename="Dialogue_{clean_id}.md"'}
            return Response(content=doc_str, media_type="text/markdown; charset=utf-8", headers=headers)
    except Exception as e:
        logger.error(f"Dialogue export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dialogue export error: {e}")

# =========================================================
# SMART QUERY SUGGESTIONS (BONUS-08)
# =========================================================

@app.get("/api/suggest")
def suggest_queries(q: str = "", limit: int = 5):
    """
    BONUS-08: Autocomplete suggestions based on past queries and academic topics.
    """
    prefix = q.strip().lower()
    suggestions = []
    
    # Query past successful runs with sanitized LIKE wildcards
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        safe_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if safe_prefix:
            cursor.execute(
                "SELECT DISTINCT query FROM pipeline_runs WHERE LOWER(query) LIKE ? ESCAPE '\\' ORDER BY created_at DESC LIMIT ?",
                (f"%{safe_prefix}%", limit)
            )
        else:
            cursor.execute(
                "SELECT DISTINCT query FROM pipeline_runs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    for r in rows:
        if r["query"] not in suggestions:
            suggestions.append(r["query"])
            
    # Add relevant academic expansions if user typed a topic
    if prefix and len(suggestions) < limit:
        topic_clean = prefix.title()
        templates = [
            f"{topic_clean}: Recent Empirical Advances and Benchmarks",
            f"{topic_clean}: Architectural Bottlenecks and Scaling Frontiers",
            f"{topic_clean}: Comparative Algorithmic Analysis"
        ]
        for t in templates:
            if t not in suggestions:
                suggestions.append(t)
                
    return {"suggestions": suggestions[:limit]}

# =========================================================
# CACHE INSPECTOR ENDPOINTS
# =========================================================

@app.get("/api/cache/papers")
def list_cached_papers(limit: int = 50):
    papers = get_all_cached_papers(limit)
    return {"count": len(papers), "papers": papers}

@app.get("/api/cache/runs")
def list_past_runs(limit: int = 10):
    runs = get_run_history(limit=limit)
    return {"runs": runs}

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

@app.post("/api/pdf/upload")
@limiter.limit("15/minute")
async def upload_pdfs(request: Request, files: List[UploadFile] = File(...), current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    SEC-03 & SEC-08 FIX:
    1. Safe filename sanitization to eliminate path traversal.
    2. Stream-read chunks with hard 50MB limit to prevent RAM exhaustion.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per session.")

    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    session_dir = os.path.realpath(os.path.join(UPLOADS_BASE, session_id))
    orig_dir = os.path.realpath(os.path.join(session_dir, "original"))
    figs_dir = os.path.realpath(os.path.join(session_dir, "figures"))
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(figs_dir, exist_ok=True)

    user_id = current_user["id"] if current_user else None
    save_pdf_session(session_id, total_files=len(files), user_id=user_id)

    total_pages = 0
    total_chunks = 0
    total_words = 0
    total_figures = 0
    total_refs = 0
    file_summaries = []

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    for file in files:
        raw_name = os.path.basename(file.filename or "document.pdf")
        safe_name = re.sub(r'[^\w\s\-.]', '_', raw_name).strip()
        if not safe_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a valid PDF.")

        dest_path = os.path.realpath(os.path.join(orig_dir, safe_name))
        if not dest_path.startswith(orig_dir):
            raise HTTPException(status_code=400, detail="Security violation: Invalid filename path.")

        # Stream-write chunks directly to disk to prevent RAM exhaustion (SEC-08 / C3)
        total_read = 0
        try:
            async with aiofiles.open(dest_path, "wb") as f_out:
                while chunk := await file.read(1024 * 1024):
                    total_read += len(chunk)
                    if total_read > MAX_FILE_SIZE:
                        raise HTTPException(status_code=413, detail=f"File '{safe_name}' exceeds 50MB size limit.")
                    await f_out.write(chunk)
        except Exception:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass
            raise

        file_size = total_read
        file_id = f"f_{uuid.uuid4().hex[:8]}"

        try:
            extracted = extract_pdf_metadata_and_text(dest_path)
            meta = extracted["metadata"]
            full_text = extracted["full_text"]
            page_count = extracted["page_count"]
            word_count = extracted["word_count"]

            figures = extract_pdf_figures(dest_path, figs_dir, session_id, file_id)
            chunks = chunk_document(full_text, file_id, chunk_size=500, overlap=50, page_count=page_count)
            chunks = compute_chunk_vectors(chunks)
            refs = extract_references(full_text, file_id)
            outline = build_document_outline(full_text)

            save_pdf_file(
                file_id=file_id,
                session_id=session_id,
                original_filename=safe_name,
                stored_path=dest_path,
                file_size_bytes=file_size,
                page_count=page_count,
                word_count=word_count,
                title=meta.get("title", safe_name),
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
                "filename": safe_name,
                "title": meta.get("title", safe_name),
                "pages": page_count,
                "words": word_count,
                "figures_count": len(figures),
                "references_count": len(refs),
                "status": "complete"
            })

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Error processing PDF '{safe_name}': {err_msg}")
            save_pdf_file(
                file_id=file_id,
                session_id=session_id,
                original_filename=safe_name,
                stored_path=dest_path,
                file_size_bytes=file_size,
                extraction_status="error",
                extraction_error=err_msg
            )
            file_summaries.append({
                "file_id": file_id,
                "filename": safe_name,
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
def list_pdf_sessions(limit: int = 20, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = current_user["id"] if current_user else None
    return {"sessions": get_all_pdf_sessions(limit, user_id=user_id)}

@app.get("/api/pdf/session/{session_id}")
def get_pdf_session_details(session_id: str):
    clean_id = os.path.basename(session_id.strip("/\\"))
    session = get_pdf_session(clean_id)
    if not session:
        raise HTTPException(status_code=404, detail="PDF session not found.")
    
    figures = get_pdf_figures_by_session(clean_id)
    refs = get_citation_graph_data(clean_id)
    session["figures"] = figures
    session["citation_graph"] = refs
    return session

@app.delete("/api/pdf/session/{session_id}")
def remove_pdf_session(session_id: str):
    """SEC-04: Secure deletion with path traversal boundary check."""
    clean_id = os.path.basename(session_id.strip("/\\"))
    res = delete_pdf_session(clean_id)
    return {"status": "success", "deleted": res}

@app.post("/api/pdf/qa")
@limiter.limit("30/minute")
async def pdf_qa_endpoint(request: Request, req: PDFQueryRequest):
    cfg = req.model_dump()
    result = await run_pdf_pipeline(
        session_id=req.session_id,
        action="qa",
        query=req.query or "",
        config=cfg
    )
    return result

@app.post("/api/pdf/stream")
@limiter.limit("30/minute")
async def stream_pdf_endpoint_post(request: Request, req: PDFQueryRequest):
    """SEC-01: Secure POST streaming for PDF analysis."""
    cfg = req.model_dump()
    return StreamingResponse(
        stream_pdf_pipeline(req.session_id, req.action, req.query or "", cfg),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/pdf/stream")
async def stream_pdf_endpoint_get(
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
    if gemini_key or anthropic_key:
        raise HTTPException(
            status_code=400,
            detail="Passing API keys in GET query parameters is prohibited for security. Please use POST /api/pdf/stream."
        )

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
    clean_id = os.path.basename(session_id.strip("/\\"))
    chunks = get_pdf_chunks_by_session(clean_id, limit=limit)
    return {"count": len(chunks), "chunks": chunks}

@app.get("/api/pdf/figures/{session_id}")
def list_session_figures(session_id: str):
    clean_id = os.path.basename(session_id.strip("/\\"))
    return {"figures": get_pdf_figures_by_session(clean_id)}

@app.get("/api/pdf/citation-graph/{session_id}")
async def fetch_citation_graph(session_id: str):
    clean_id = os.path.basename(session_id.strip("/\\"))
    return get_citation_graph_data(clean_id)

# SEC-09: Safe figure image serving endpoint
@app.get("/uploads/{session_id}/figures/{filename}")
def get_extracted_figure(session_id: str, filename: str):
    clean_sess = os.path.basename(session_id.strip("/\\"))
    clean_name = os.path.basename(filename.strip("/\\"))
    fig_path = os.path.realpath(os.path.join(UPLOADS_BASE, clean_sess, "figures", clean_name))
    if not fig_path.startswith(UPLOADS_BASE) or not os.path.exists(fig_path):
        raise HTTPException(status_code=404, detail="Figure not found.")
    return FileResponse(fig_path)

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
