import os
import json
import uuid
import re
import shutil
import asyncio
import aiofiles
import secrets
import httpx
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Response, Query, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, RedirectResponse
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
    save_scraped_papers, save_cached_sentences, append_source_to_run,
    save_pdf_session, get_pdf_session, get_all_pdf_sessions, update_pdf_session_status,
    delete_pdf_session, save_pdf_file, update_pdf_file_status, save_pdf_chunks,
    save_pdf_figures, get_pdf_figures_by_session, save_pdf_references,
    get_citation_graph_data, get_pdf_chunks_by_session,
    get_run_history, get_run_by_id, delete_run, log_pipeline_run,
    get_all_prompt_history, get_followups_for_run, delete_followup,
    save_dialogue_message, get_dialogue_history, clear_dialogue_history,
    create_user, get_user_by_username, get_user_by_email, get_user_by_id, update_user_last_login,
    create_or_update_oauth_user, save_user_api_key, get_user_api_key_hints, get_user_encrypted_key, delete_user_api_key
)
from backend.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    get_current_user_optional, get_current_user_required,
    encrypt_api_key_for_user, decrypt_api_key_for_user,
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    SaveApiKeyRequest, ApiKeysStatusResponse, OAuthProvidersResponse
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
    title="AI Research Workbench v4.0 Backend",
    description="Multi-Agent Autonomous Research Agent with Dual-Mode Literature Synthesis and PDF Document Analysis",
    version="4.0.0"
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
    paper_limit: Optional[int] = 8
    execution_mode: Optional[str] = "deep"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    scraper_sources: Optional[str] = "all"
    active_scrapers: Optional[List[str]] = None
    max_pdf_pages: Optional[int] = 25
    max_tokens: Optional[int] = 15000
    disable_fallback: Optional[bool] = False
    disable_fallback_agent2: Optional[bool] = False
    disable_fallback_agent4: Optional[bool] = False
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
    openai_key: Optional[str] = None
    disable_fallback: Optional[bool] = False

class FollowupRequest(BaseModel):
    parent_run_id: str
    claim_id: Optional[str] = None
    target_topic: Optional[str] = None
    query: str = Field(..., min_length=1, max_length=1000, description="Targeted follow-up question")
    provider: Optional[str] = "auto"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None
    disable_fallback: Optional[bool] = False

class DialogueChatRequest(BaseModel):
    run_id: str
    message: str = Field(..., min_length=1, max_length=1000, description="Inquiry for continuous research dialogue")
    provider: Optional[str] = "auto"
    gemini_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    openai_key: Optional[str] = None
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
    return {"status": "ok", "version": "4.0.0"}

@app.get("/api/status")
def get_api_status():
    """Returns runtime health and provider readiness (v4.0.0)."""
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {
        "status": "online",
        "service": "AI Research Workbench v4.0",
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
        "service": "AI Research Workbench v4.0",
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
        oauth_provider=user.get("oauth_provider", "local"),
        avatar_url=user.get("avatar_url"),
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
        
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Account not registered. No account exists with this username or email. Please register to create an account."
        )
    
    if not user.get("password_hash") or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password. Please verify your credentials and try again.")
    
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
        oauth_provider=user.get("oauth_provider", "local"),
        avatar_url=user.get("avatar_url"),
        created_at=str(user.get("created_at") or ""),
        last_login=str(user.get("last_login") or "")
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_profile(response: Response, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Returns the profile of the currently authenticated user and refreshes access cookie."""
    token = create_access_token({"sub": current_user["id"], "username": current_user["username"], "role": current_user.get("role", "user")})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user.get("role", "user"),
        oauth_provider=current_user.get("oauth_provider", "local"),
        avatar_url=current_user.get("avatar_url"),
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
# OAUTH 2.0 / SOCIAL LOGIN ENDPOINTS (GOOGLE & GITHUB)
# =========================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()

def get_oauth_redirect_uri(request: Request, provider: str) -> str:
    app_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if app_base:
        return f"{app_base}/api/auth/{provider}/callback"
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/{provider}/callback"

@app.get("/api/auth/providers", response_model=OAuthProvidersResponse)
def get_auth_providers_endpoint():
    """Returns the availability status of third-party OAuth providers."""
    return OAuthProvidersResponse(
        local=True,
        google=bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        github=bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
    )

@app.get("/api/auth/google/login")
def google_login_redirect(request: Request):
    """Redirects the client to Google's OAuth 2.0 authorization page."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."
        )
    redirect_uri = get_oauth_redirect_uri(request, "google")
    state = secrets.token_urlsafe(32)
    scope = "openid email profile"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&response_type=code&scope={scope}&"
        f"redirect_uri={redirect_uri}&access_type=offline&prompt=select_account&state={state}"
    )
    resp = RedirectResponse(url)
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return resp

@app.get("/api/auth/google/callback")
async def google_oauth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Exchanges Google OAuth code for tokens and issues a secure JWT."""
    if error or not code:
        return RedirectResponse(f"/?auth_error={error or 'cancelled'}")
    
    redirect_uri = get_oauth_redirect_uri(request, "google")
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        })
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            err_msg = token_json.get("error_description") or "Failed to exchange Google OAuth code"
            return RedirectResponse(f"/?auth_error={err_msg}")
        
        info_res = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
            "Authorization": f"Bearer {access_token}"
        })
        info = info_res.json()

    email = info.get("email")
    if not email:
        return RedirectResponse("/?auth_error=google_missing_email")

    user = create_or_update_oauth_user(
        provider="google",
        oauth_id=str(info.get("id")),
        email=email,
        username=info.get("name") or email.split("@")[0],
        avatar_url=info.get("picture", "")
    )

    token = create_access_token({"sub": user["id"], "username": user["username"], "role": user.get("role", "user")})
    resp = RedirectResponse(f"/?auth_token={token}&auth_provider=google")
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    return resp

@app.get("/api/auth/github/login")
def github_login_redirect(request: Request):
    """Redirects the client to GitHub's OAuth authorization page."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in your .env file."
        )
    redirect_uri = get_oauth_redirect_uri(request, "github")
    state = secrets.token_urlsafe(32)
    scope = "read:user user:email"
    url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope={scope}&state={state}"
    )
    resp = RedirectResponse(url)
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return resp

@app.get("/api/auth/github/callback")
async def github_oauth_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Exchanges GitHub OAuth code for tokens and issues a secure JWT."""
    if error or not code:
        return RedirectResponse(f"/?auth_error={error or 'cancelled'}")
    
    redirect_uri = get_oauth_redirect_uri(request, "github")
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.post("https://github.com/login/oauth/access_token", headers={"Accept": "application/json"}, data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri
        })
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            err_msg = token_json.get("error_description") or "Failed to exchange GitHub OAuth code"
            return RedirectResponse(f"/?auth_error={err_msg}")

        user_res = await client.get("https://api.github.com/user", headers={
            "Authorization": f"Bearer {access_token}"
        })
        gh_user = user_res.json()

        email = gh_user.get("email")
        if not email:
            emails_res = await client.get("https://api.github.com/user/emails", headers={
                "Authorization": f"Bearer {access_token}"
            })
            emails = emails_res.json()
            if isinstance(emails, list):
                primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
                email = primary or (emails[0]["email"] if emails else None)
        
        if not email:
            email = f"{gh_user.get('login', 'github_user')}@users.noreply.github.com"

    user = create_or_update_oauth_user(
        provider="github",
        oauth_id=str(gh_user.get("id")),
        email=email,
        username=gh_user.get("login") or gh_user.get("name") or "github_user",
        avatar_url=gh_user.get("avatar_url", "")
    )

    token = create_access_token({"sub": user["id"], "username": user["username"], "role": user.get("role", "user")})
    resp = RedirectResponse(f"/?auth_token={token}&auth_provider=github")
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )
    return resp

# =========================================================
# ENCRYPTED PER-USER API KEY VAULT (AES-256-GCM)
# =========================================================

@app.get("/api/auth/api-keys", response_model=ApiKeysStatusResponse)
async def get_user_api_keys_endpoint(current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """
    Returns masked previews and configured indicators for the user's encrypted API keys.
    Plaintext decrypted keys are NEVER returned over the API!
    """
    hints = get_user_api_key_hints(current_user["id"])
    return ApiKeysStatusResponse(status="success", keys=hints)

@app.post("/api/auth/api-keys")
async def save_user_api_key_endpoint(req: SaveApiKeyRequest, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """
    Securely encrypts an API key using authenticated AES-256-GCM and stores it in the database for the user.
    """
    try:
        encrypted_blob, hint = encrypt_api_key_for_user(req.api_key, current_user["id"])
        save_user_api_key(current_user["id"], req.provider, encrypted_blob, hint)
        return {
            "status": "success",
            "provider": req.provider,
            "hint": hint,
            "message": f"Successfully encrypted and stored {req.provider.capitalize()} API key."
        }
    except Exception as e:
        logger.error(f"Failed to encrypt user API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to securely encrypt API key.")

@app.delete("/api/auth/api-keys/{provider}")
async def delete_user_api_key_endpoint(provider: str, current_user: Dict[str, Any] = Depends(get_current_user_required)):
    """Deletes the stored encrypted API key for the specified provider."""
    clean_prov = provider.lower().strip()
    if clean_prov not in ["gemini", "anthropic", "openai", "serpapi"]:
        raise HTTPException(status_code=400, detail="Invalid provider.")
    deleted = delete_user_api_key(current_user["id"], clean_prov)
    return {"status": "success", "provider": clean_prov, "deleted": deleted}

def get_user_decrypted_keys(user_id: Optional[str]) -> Dict[str, str]:
    """Retrieves all decrypted API keys stored in Neon PostgreSQL vault for the user."""
    if not user_id:
        return {}
    decrypted: Dict[str, str] = {}
    for prov in ["gemini", "anthropic", "openai", "serpapi"]:
        try:
            enc = get_user_encrypted_key(user_id, prov)
            if enc:
                plain = decrypt_api_key_for_user(enc, user_id)
                if plain:
                    decrypted[prov] = plain
        except Exception as e:
            logger.warning(f"Failed to decrypt vault key for {prov} (user {user_id}): {e}")
    return decrypted

def resolve_api_key_for_model(model: str, user_id: Optional[str] = None, explicit_key: Optional[str] = None) -> tuple[Optional[str], str]:
    """
    Intelligently resolves the required API key and aligned model across:
    1. Explicit key parameter or header (auto-detecting provider prefix)
    2. User's encrypted PostgreSQL vault (via user_id)
    3. Server-level environment variables
    """
    m = (model or "gemini-3.6-flash").strip()
    if explicit_key and explicit_key.strip():
        k = explicit_key.strip()
        if k.startswith("AIzaSy"):
            return k, (m if "gemini" in m.lower() else "gemini-3.6-flash")
        elif k.startswith("sk-ant-"):
            return k, (m if "claude" in m.lower() else "claude-sonnet-5.5")
        elif k.startswith("sk-") and not k.startswith("sk-ant-"):
            return k, (m if any(x in m.lower() for x in ["gpt", "sol", "luna", "astra"]) else "gpt-6.1-sol")
        return k, m

    m_lower = m.lower()
    is_openai = any(k in m_lower for k in ("gpt", "sol", "luna", "astra", "o1", "o3", "openai", "text-embedding"))
    is_claude = any(k in m_lower for k in ("claude", "sonnet", "opus", "haiku", "anthropic"))
    is_gemini = "gemini" in m_lower

    vault_keys = get_user_decrypted_keys(user_id) if user_id else {}
    openai_key = vault_keys.get("openai") or os.environ.get("OPENAI_API_KEY")
    claude_key = vault_keys.get("anthropic") or os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = vault_keys.get("gemini") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if is_openai and openai_key:
        return openai_key, m
    elif is_claude and claude_key:
        return claude_key, m
    elif is_gemini and gemini_key:
        return gemini_key, m

    # Intelligent fallback: If preferred provider has no key, use whichever provider HAS a key
    if gemini_key:
        return gemini_key, "gemini-3.6-flash"
    elif openai_key:
        return openai_key, "gpt-6.1-sol"
    elif claude_key:
        return claude_key, "claude-sonnet-5.5"

    return None, m

def inject_user_api_keys(cfg: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
    """
    Securely decrypts and injects the authenticated user's stored API keys into the execution config
    for any providers where a key was not explicitly provided in the request body/headers.
    Also aligns provider settings if user only has keys configured for a specific provider.
    """
    if not user_id:
        return cfg
    
    vault_keys = get_user_decrypted_keys(user_id)
    for prov in ["gemini", "anthropic", "openai", "serpapi"]:
        key_field = f"{prov}_key"
        if not cfg.get(key_field) and vault_keys.get(prov):
            cfg[key_field] = vault_keys[prov]

    # Intelligent Provider Alignment:
    # If user has an OpenAI key, but no Gemini/Anthropic keys, and default Gemini was selected:
    has_gemini = bool(cfg.get("gemini_key") or os.environ.get("GEMINI_API_KEY"))
    has_anthropic = bool(cfg.get("anthropic_key") or os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(cfg.get("openai_key") or os.environ.get("OPENAI_API_KEY"))

    p2 = str(cfg.get("provider_agent2", "")).lower()
    p4 = str(cfg.get("provider_agent4", "")).lower()

    if has_openai and not has_gemini and not has_anthropic:
        if not p2 or p2 == "auto" or p2.startswith("gemini") or "claude" in p2:
            cfg["provider_agent2"] = "gpt-6.1-sol"
        if not p4 or p4 == "auto" or p4.startswith("gemini") or "claude" in p4:
            cfg["provider_agent4"] = "gpt-6-luna"
    elif has_anthropic and not has_gemini and not has_openai:
        if not p2 or p2 == "auto" or p2.startswith("gemini") or "gpt" in p2:
            cfg["provider_agent2"] = "claude-sonnet-5.5"
        if not p4 or p4 == "auto" or p4.startswith("gemini") or "gpt" in p4:
            cfg["provider_agent4"] = "claude-haiku-4.5"
    elif has_gemini and not has_openai and not has_anthropic:
        if not p2 or p2 == "auto" or "gpt" in p2 or "claude" in p2:
            cfg["provider_agent2"] = "gemini-3.6-flash"
        if not p4 or p4 == "auto" or "gpt" in p4 or "claude" in p4:
            cfg["provider_agent4"] = "gemini-3.6-flash"

    return cfg


# =========================================================
# RESEARCH PIPELINE EXECUTION (CORE AGENTS 1-4)
# =========================================================

@app.post("/api/pipeline/run")
@limiter.limit("20/minute")
async def run_pipeline_sync(request: Request, req: QueryRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Executes full research pipeline synchronously."""
    # BUG-04: Upgrade .dict() to .model_dump()
    cfg = req.model_dump()
    if not cfg.get("openai_key") and request.headers.get("x-openai-key"):
        cfg["openai_key"] = request.headers.get("x-openai-key")
    if not cfg.get("gemini_key") and request.headers.get("x-gemini-key"):
        cfg["gemini_key"] = request.headers.get("x-gemini-key")
    if not cfg.get("anthropic_key") and request.headers.get("x-anthropic-key"):
        cfg["anthropic_key"] = request.headers.get("x-anthropic-key")
    if not cfg.get("serpapi_key") and request.headers.get("x-serpapi-key"):
        cfg["serpapi_key"] = request.headers.get("x-serpapi-key")
    if current_user:
        cfg["user_id"] = current_user["id"]
        cfg = inject_user_api_keys(cfg, current_user["id"])
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
    if not cfg.get("openai_key") and request.headers.get("x-openai-key"):
        cfg["openai_key"] = request.headers.get("x-openai-key")
    if not cfg.get("gemini_key") and request.headers.get("x-gemini-key"):
        cfg["gemini_key"] = request.headers.get("x-gemini-key")
    if not cfg.get("anthropic_key") and request.headers.get("x-anthropic-key"):
        cfg["anthropic_key"] = request.headers.get("x-anthropic-key")
    if not cfg.get("serpapi_key") and request.headers.get("x-serpapi-key"):
        cfg["serpapi_key"] = request.headers.get("x-serpapi-key")
    if current_user:
        cfg["user_id"] = current_user["id"]
        cfg = inject_user_api_keys(cfg, current_user["id"])
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
    scraper_sources: str = "all",
    similarity_threshold: float = 0.55,
    paper_limit: int = 5,
    execution_mode: str = "deep",
    gemini_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    serpapi_key: Optional[str] = None,
    max_tokens: int = 15000,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Backward-compatible GET SSE stream (prefer POST /api/pipeline/stream for maximum credential privacy).
    """
    if not query:
        raise HTTPException(status_code=400, detail="Parameter 'query' is required.")

    if gemini_key or anthropic_key or openai_key or serpapi_key:
        raise HTTPException(
            status_code=400,
            detail="Passing API keys in GET query parameters is prohibited for security. Please use POST /api/pipeline/stream."
        )

    config = {
        "provider_agent2": provider_agent2,
        "provider_agent4": provider_agent4,
        "disable_fallback_agent2": disable_fallback_agent2,
        "disable_fallback_agent4": disable_fallback_agent4,
        "scraper_sources": scraper_sources,
        "similarity_threshold": similarity_threshold,
        "paper_limit": paper_limit,
        "execution_mode": execution_mode,
        "max_tokens": max_tokens,
        "gemini_key": gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": anthropic_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        "openai_key": openai_key or os.environ.get("OPENAI_API_KEY", ""),
        "serpapi_key": serpapi_key or os.environ.get("SERPAPI_API_KEY", ""),
        "user_id": current_user["id"] if current_user else None
    }
    if current_user:
        config = inject_user_api_keys(config, current_user["id"])
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
def get_prompt_history_endpoint(limit: int = 50, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    Returns the comprehensive hierarchical prompt & follow-up tree:
    Every parent query along with all nested follow-up questions,
    timestamps, and total thread token metrics.
    """
    user_id = current_user["id"] if current_user else None
    prompts = get_all_prompt_history(limit=limit, user_id=user_id)
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
async def pipeline_followup_endpoint(request: Request, req: FollowupRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    FOL-02 / FOL-03: Executes an ultra-low-token targeted follow-up synthesis.
    Extracts atomic context from local SQLite (IDCC), bypassing external web re-scraping.
    Consumes ~400-650 tokens total (an 80%+ reduction vs standard multi-turn chat).
    """
    clean_parent_id = os.path.basename(req.parent_run_id.strip("/\\"))
    gemini_k = req.gemini_key or request.headers.get("x-gemini-key")
    anthropic_k = req.anthropic_key or request.headers.get("x-anthropic-key")
    openai_k = req.openai_key or request.headers.get("x-openai-key")
    
    if current_user:
        dummy = {"gemini_key": gemini_k, "anthropic_key": anthropic_k, "openai_key": openai_k}
        dummy = inject_user_api_keys(dummy, current_user["id"])
        gemini_k = dummy.get("gemini_key")
        anthropic_k = dummy.get("anthropic_key")
        openai_k = dummy.get("openai_key")

    try:
        result = await run_followup_synthesis(
            parent_run_id=clean_parent_id,
            query=req.query,
            claim_id=req.claim_id,
            target_topic=req.target_topic,
            provider=req.provider or "auto",
            gemini_key=gemini_k,
            anthropic_key=anthropic_k,
            openai_key=openai_k,
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
async def dialogue_chat_endpoint(request: Request, req: DialogueChatRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """
    CHAT-03: Executes a continuous multi-turn research dialogue turn via DHS-RCC.
    Strictly bounds prompt input to <= 750 tokens, yielding 80-88% savings vs web chat.
    """
    clean_run_id = os.path.basename(req.run_id.strip("/\\"))
    gemini_k = req.gemini_key or request.headers.get("x-gemini-key")
    anthropic_k = req.anthropic_key or request.headers.get("x-anthropic-key")
    openai_k = req.openai_key or request.headers.get("x-openai-key")

    if current_user:
        dummy = {"gemini_key": gemini_k, "anthropic_key": anthropic_k, "openai_key": openai_k}
        dummy = inject_user_api_keys(dummy, current_user["id"])
        gemini_k = dummy.get("gemini_key")
        anthropic_k = dummy.get("anthropic_key")
        openai_k = dummy.get("openai_key")

    try:
        result = await run_dialogue_turn(
            run_id=clean_run_id,
            user_message=req.message,
            provider=req.provider or "auto",
            gemini_key=gemini_k,
            anthropic_key=anthropic_k,
            openai_key=openai_k,
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
                "SELECT query FROM pipeline_runs WHERE LOWER(query) LIKE ? ESCAPE '\\' GROUP BY query ORDER BY MAX(created_at) DESC LIMIT ?",
                (f"%{safe_prefix}%", limit)
            )
        else:
            cursor.execute(
                "SELECT query FROM pipeline_runs GROUP BY query ORDER BY MAX(created_at) DESC LIMIT ?",
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
def list_past_runs(limit: int = 10, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = current_user["id"] if current_user else None
    runs = get_run_history(limit=limit, user_id=user_id)
    return {"runs": runs}

@app.get("/api/cache/stats")
def cache_stats():
    return get_cache_stats()

@app.post("/api/cache/clear")
def clear_cache():
    result = clear_all_cache()
    return {"status": "success", "cleared": result}

# =========================================================
# DOSSIER CUSTOM SOURCE UPLOAD ENDPOINT
# =========================================================

@app.post("/api/dossier/upload-source")
@limiter.limit("20/minute")
async def upload_dossier_source(
    request: Request,
    file: UploadFile = File(...),
    run_id: Optional[str] = Form(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Upload a custom research paper PDF directly into the Research Dossier as an authoritative source.
    Extracts title, authors, abstract, benchmark excerpts, and dense context sentences.
    Indexes the paper into scraped_papers and cached_sentences.
    If run_id is provided, automatically appends the paper to the pipeline run's saved citations.
    """
    import datetime
    import pymupdf as fitz

    raw_name = os.path.basename(file.filename or "document.pdf")
    safe_name = re.sub(r'[^\w\s\-.]', '_', raw_name).strip()
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF document (.pdf).")

    # Read bytes with memory bound (max 15MB)
    MAX_SIZE = 15 * 1024 * 1024
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="PDF size exceeds 15MB limit.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {str(e)}")

    try:
        page_count = len(doc)
        raw_meta = doc.metadata or {}
        doc_title = (raw_meta.get("title") or "").strip()
        doc_author = (raw_meta.get("author") or "").strip()

        # Extract text from first 10 pages bounded to ~25,000 characters to prevent memory spikes
        pages_text = []
        max_pages = min(10, page_count)
        for i in range(max_pages):
            p_text = doc[i].get_text("text")
            if p_text:
                pages_text.append(p_text.strip())

        full_extracted = "\n\n".join(pages_text)
        if len(full_extracted) > 25000:
            full_extracted = full_extracted[:25000]

        # Extract or infer title if meta_title is missing or generic
        if not doc_title or doc_title.lower() in ("untitled", "pdf", "microsoft word", "unknown"):
            lines = [ln.strip() for ln in full_extracted.split("\n") if len(ln.strip()) > 5]
            if lines:
                doc_title = lines[0][:150]
            else:
                doc_title = safe_name.replace(".pdf", "").replace("_", " ")

        # Extract abstract or page 1 lead
        abstract_match = re.search(r'(?:abstract|summary)\s*[:\-\n]([\s\S]{50,1500}?)(?:\n\s*(?:1[\.\s]|introduction|keywords|index terms|background))', full_extracted, re.IGNORECASE)
        if abstract_match:
            abstract_text = re.sub(r'\s+', ' ', abstract_match.group(1)).strip()
        else:
            abstract_text = re.sub(r'\s+', ' ', full_extracted[:800]).strip()

        # Split into dense sentences for context matching
        raw_sentences = re.split(r'(?<=[.!?])\s+', full_extracted)
        dense_sentences = []
        for s in raw_sentences:
            clean_s = re.sub(r'\s+', ' ', s).strip()
            if 35 <= len(clean_s) <= 400 and not any(kw in clean_s.lower() for kw in ("http", "arxiv:", "all rights reserved", "downloaded from")):
                dense_sentences.append(clean_s)
                if len(dense_sentences) >= 25:
                    break

        paper_suffix = uuid.uuid4().hex[:4].upper()
        paper_idx = f"P_USER_{paper_suffix}"
        paper_id = f"upload_{uuid.uuid4().hex[:12]}"
        year_val = datetime.datetime.now().year
        authors_list = [doc_author] if doc_author else ["User Upload"]

        citation = {
            "id": paper_id,
            "paper_id": paper_id,
            "paper_idx": paper_idx,
            "ref_id": paper_idx,
            "title": doc_title,
            "authors": authors_list,
            "year": year_val,
            "venue": "User Uploaded Source",
            "url": "#",
            "source": "User Upload",
            "source_type": "User Uploaded Paper",
            "provenance_tier": "user_upload",
            "provenance_label": "User Uploaded Source",
            "citation_count": 0,
            "abstract": abstract_text[:1000],
            "fulltext_excerpt": full_extracted[:5000],
            "evidence": dense_sentences[0] if dense_sentences else (abstract_text[:250]),
            "supporting_snippets": dense_sentences[:3],
            "dense_sentences": [{"id": f"ds_{uuid.uuid4().hex[:8]}", "text": s, "paper_idx": paper_idx, "paper_id": paper_id} for s in dense_sentences]
        }

        # Index paper into database
        db_paper_obj = {
            "id": paper_id,
            "paperId": paper_id,
            "title": doc_title,
            "authors": authors_list,
            "year": year_val,
            "abstract": abstract_text,
            "url": "#",
            "venue": "User Uploaded Source",
            "citationCount": 0
        }
        active_query = "user_uploaded_source"
        if run_id:
            run_data = get_run_by_id(run_id)
            if run_data:
                active_query = run_data.get("query", active_query)

        save_scraped_papers(active_query, [db_paper_obj])
        db_sentences = [
            {"id": f"s_{uuid.uuid4().hex[:12]}", "paper_id": paper_id, "text": s, "density_score": 0.95}
            for s in dense_sentences
        ]
        if db_sentences:
            save_cached_sentences(active_query, db_sentences)

        # Update run history if run_id provided
        if run_id:
            append_source_to_run(run_id, citation)

        return {
            "status": "success",
            "message": f"Successfully parsed and indexed '{doc_title}' as {paper_idx}.",
            "citation": citation
        }
    finally:
        doc.close()
        del doc

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
async def pdf_qa_endpoint(request: Request, req: PDFQueryRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    cfg = req.model_dump()
    if not cfg.get("openai_key") and request.headers.get("x-openai-key"):
        cfg["openai_key"] = request.headers.get("x-openai-key")
    if not cfg.get("gemini_key") and request.headers.get("x-gemini-key"):
        cfg["gemini_key"] = request.headers.get("x-gemini-key")
    if not cfg.get("anthropic_key") and request.headers.get("x-anthropic-key"):
        cfg["anthropic_key"] = request.headers.get("x-anthropic-key")
    if current_user:
        cfg["user_id"] = current_user["id"]
        cfg = inject_user_api_keys(cfg, current_user["id"])
    result = await run_pdf_pipeline(
        session_id=req.session_id,
        action="qa",
        query=req.query or "",
        config=cfg
    )
    return result

@app.post("/api/pdf/stream")
@limiter.limit("30/minute")
async def stream_pdf_endpoint_post(request: Request, req: PDFQueryRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """SEC-01: Secure POST streaming for PDF analysis."""
    cfg = req.model_dump()
    if not cfg.get("openai_key") and request.headers.get("x-openai-key"):
        cfg["openai_key"] = request.headers.get("x-openai-key")
    if not cfg.get("gemini_key") and request.headers.get("x-gemini-key"):
        cfg["gemini_key"] = request.headers.get("x-gemini-key")
    if not cfg.get("anthropic_key") and request.headers.get("x-anthropic-key"):
        cfg["anthropic_key"] = request.headers.get("x-anthropic-key")
    if current_user:
        cfg["user_id"] = current_user["id"]
        cfg = inject_user_api_keys(cfg, current_user["id"])
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
    analysis_type: str = "methodology",
    gemini_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None
):
    if gemini_key or anthropic_key or openai_key:
        raise HTTPException(
            status_code=400,
            detail="Passing API keys in GET query parameters is prohibited for security. Please use POST /api/pdf/stream."
        )

    config = {
        "provider": provider,
        "disable_fallback": disable_fallback,
        "analysis_type": analysis_type,
        "gemini_key": gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        "anthropic_key": anthropic_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        "openai_key": openai_key or os.environ.get("OPENAI_API_KEY", "")
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

# -------------------------------------------------------------
# Comparative Scientific Study Harness Endpoints (3-System Benchmark)
# -------------------------------------------------------------
try:
    from evals.prompts import BENCHMARK_PROMPTS
    from evals.direct_api_system import DirectAPISystem
    from evals.conventional_rag_system import ConventionalRAGSystem
    from evals.workbench_system import WorkbenchSystem
    from evals.run_study import analyze_text_quality, calculate_estimated_cost
except Exception as e:
    logger.warning(f"Could not import evals modules: {e}")

EVALS_DOCX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evals", "Comparative_Study_Protocol_and_Workbook.docx")

class EvalSingleSystemRequest(BaseModel):
    system_type: str  # 'a', 'b', or 'c'
    query: str
    model: str = "claude-sonnet-5.5"
    api_key: Optional[str] = None
    top_k: int = 5

class EvalSystemConfig(BaseModel):
    enabled: bool = True
    model: str = "claude-sonnet-5.5"
    api_key: Optional[str] = None
    top_k: int = 5

class EvalComparisonRequest(BaseModel):
    query: str
    system_a: EvalSystemConfig
    system_b: EvalSystemConfig
    system_c: EvalSystemConfig

async def _run_eval_single_system(sys_type: str, query: str, model: str, api_key: Optional[str], top_k: int = 5, user_id: Optional[str] = None) -> Dict[str, Any]:
    sys_type = sys_type.lower()
    resolved_key, resolved_model = resolve_api_key_for_model(model, user_id=user_id, explicit_key=api_key)
    if sys_type == "a":
        wb = WorkbenchSystem(model_pref=resolved_model)
        res = await wb.execute(query, api_key=resolved_key, user_id=user_id)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(resolved_model, res.input_tokens, res.output_tokens)
        return {
            **res.to_dict(),
            "run_id": res.run_id,
            "cost_usd": cost,
            "text_analysis": analysis,
            "dossier": res.dossier
        }
    elif sys_type == "b":
        rag = ConventionalRAGSystem(model_pref=resolved_model, top_k=top_k)
        res = await rag.execute(query, api_key=resolved_key)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(resolved_model, res.input_tokens, res.output_tokens)
        
        run_id = f"run_b_{uuid.uuid4().hex[:8]}"
        citations = [
            {
                "ref_id": str(idx + 1),
                "title": chunk.title or f"Retrieved Chunk {idx + 1}",
                "authors": chunk.source_venue or "Academic Literature Vector Index",
                "year": "2024",
                "venue": chunk.source_venue or "FastEmbed ONNX Vector Index",
                "url": chunk.url or "#",
                "evidence": (chunk.text[:240] + "...") if chunk.text else "Direct passage match retrieved via cosine similarity.",
                "supporting_snippets": [chunk.text] if chunk.text else []
            }
            for idx, chunk in enumerate(res.retrieved_chunks)
        ]
        rag_dossier = {
            "run_id": run_id,
            "query": query,
            "architecture": "system_b",
            "model": res.model,
            "output_text": res.output_text,
            "latency_seconds": round(res.latency_seconds, 2),
            "elapsed_seconds": round(res.latency_seconds, 2),
            "tokens": res.total_tokens,
            "prompt_tokens": res.input_tokens,
            "completion_tokens": res.output_tokens,
            "cost_usd": cost,
            "citations": citations,
            "quick_answer": "Generated via System B: Conventional RAG Baseline (FastEmbed ONNX Vector Retrieval + Single LLM Call). Multi-agent verification and claim caching bypassed.",
            "takeaways": [
                f"Top-{res.retrieved_sources_count or len(citations) or top_k} dense vector passages retrieved via ONNX embeddings.",
                "Single augmented generation pass synthesizes retrieved context into monograph.",
                "Unverified: No multi-agent claim verification or 0-token caching applied."
            ],
            "evaluated_claims": [],
            "dossier_sections": []
        }
        await asyncio.to_thread(
            log_pipeline_run,
            run_id,
            query,
            res.total_tokens,
            res.latency_seconds,
            rag_dossier,
            res.input_tokens,
            res.output_tokens,
            user_id
        )
        return {
            **res.to_dict(),
            "run_id": run_id,
            "cost_usd": cost,
            "text_analysis": analysis,
            "dossier": rag_dossier
        }
    elif sys_type == "c":
        direct = DirectAPISystem(model_pref=resolved_model)
        res = await direct.execute(query, api_key=resolved_key)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(resolved_model, res.input_tokens, res.output_tokens)
        
        run_id = f"run_c_{uuid.uuid4().hex[:8]}"
        direct_dossier = {
            "run_id": run_id,
            "query": query,
            "architecture": "system_c",
            "model": res.model,
            "output_text": res.output_text,
            "latency_seconds": round(res.latency_seconds, 2),
            "elapsed_seconds": round(res.latency_seconds, 2),
            "tokens": res.total_tokens,
            "prompt_tokens": res.input_tokens,
            "completion_tokens": res.output_tokens,
            "cost_usd": cost,
            "citations": [],
            "quick_answer": "Generated via System C: Direct Single API Baseline (Zero-Shot Parametric Memory). External retrieval and verification bypassed.",
            "takeaways": [
                "Synthesized entirely from internal LLM parametric training weights.",
                "Zero external scientific literature retrieved or corroborated.",
                "Elevated hallucination risk: Citations and post-cutoff numerical bounds are unverified."
            ],
            "evaluated_claims": [],
            "dossier_sections": []
        }
        await asyncio.to_thread(
            log_pipeline_run,
            run_id,
            query,
            res.total_tokens,
            res.latency_seconds,
            direct_dossier,
            res.input_tokens,
            res.output_tokens,
            user_id
        )
        return {
            **res.to_dict(),
            "run_id": run_id,
            "cost_usd": cost,
            "text_analysis": analysis,
            "dossier": direct_dossier
        }
    else:
        raise ValueError(f"Invalid system type: '{sys_type}' (expected 'a', 'b', or 'c')")

@app.get("/api/evals/prompts")
async def get_eval_prompts():
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "domain": p.domain,
            "query": p.query,
            "ground_truth_anchors": p.ground_truth_anchors,
            "failure_modes_tested": p.failure_modes_tested,
            "evaluation_focus": p.evaluation_focus
        }
        for p in BENCHMARK_PROMPTS
    ]

@app.get("/api/evals/download-docx")
async def download_eval_docx():
    if not os.path.exists(EVALS_DOCX_PATH):
        from evals.build_study_docx import build_docx_report
        build_docx_report(EVALS_DOCX_PATH)
    return FileResponse(
        path=EVALS_DOCX_PATH,
        filename="Comparative_Study_Protocol_and_Workbook.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.post("/api/evals/run-system")
async def run_eval_single(
    req: EvalSingleSystemRequest, 
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    try:
        active_key = req.api_key or request.headers.get("x-openai-key") or request.headers.get("x-anthropic-key") or request.headers.get("x-api-key")
        user_id = (current_user.get("id") or current_user.get("user_id")) if current_user else None
        result = await _run_eval_single_system(
            sys_type=req.system_type,
            query=req.query,
            model=req.model,
            api_key=active_key,
            top_k=req.top_k,
            user_id=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Evaluation error on System {req.system_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evals/run-comparison")
async def run_eval_comparison(
    req: EvalComparisonRequest, 
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    header_key = request.headers.get("x-openai-key") or request.headers.get("x-anthropic-key") or request.headers.get("x-api-key")
    key_a = req.system_a.api_key or header_key
    key_b = req.system_b.api_key or header_key
    key_c = req.system_c.api_key or header_key
    user_id = (current_user.get("id") or current_user.get("user_id")) if current_user else None

    tasks = []
    task_keys = []

    if req.system_a.enabled:
        tasks.append(_run_eval_single_system("a", query, req.system_a.model, key_a, user_id=user_id))
        task_keys.append("system_a")

    if req.system_b.enabled:
        tasks.append(_run_eval_single_system("b", query, req.system_b.model, key_b, req.system_b.top_k, user_id=user_id))
        task_keys.append("system_b")

    if req.system_c.enabled:
        tasks.append(_run_eval_single_system("c", query, req.system_c.model, key_c, user_id=user_id))
        task_keys.append("system_c")

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    response_data: Dict[str, Any] = {
        "query": query,
        "results": {}
    }

    for key, res in zip(task_keys, raw_results):
        if isinstance(res, Exception):
            response_data["results"][key] = {
                "error": str(res),
                "system_name": key.upper()
            }
        else:
            response_data["results"][key] = res

    return response_data

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon_ico():
    ico_path = os.path.join(frontend_dir, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/favicon.svg", include_in_schema=False)
def serve_favicon_svg():
    svg_path = os.path.join(frontend_dir, "favicon.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path, media_type="image/svg+xml")
    return Response(status_code=204)

@app.get("/apple-touch-icon.png", include_in_schema=False)
def serve_apple_touch_icon():
    png_path = os.path.join(frontend_dir, "apple-touch-icon.png")
    if os.path.exists(png_path):
        return FileResponse(png_path, media_type="image/png")
    return Response(status_code=204)

@app.get("/login", response_class=FileResponse)
def serve_login_page():
    """Serves the dedicated full-screen login and registration portal."""
    login_path = os.path.join(frontend_dir, "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/")
@app.get("/index.html")
async def serve_root(request: Request):
    """
    Serves the Research Workbench if authenticated, otherwise redirects directly to /login.
    Strictly mandates authentication and disables guest mode.
    """
    # 1. If auth_token or auth_error query param exists (e.g. OAuth callback redirect),
    # allow serving index.html so frontend client script can ingest it.
    if request.query_params.get("auth_token") or request.query_params.get("auth_error"):
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    # 2. Check for token in cookie or Authorization header
    token = request.cookies.get("access_token") or request.cookies.get("workbench_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    # 3. Verify token validity and existing user in database
    user = None
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user = get_user_by_id(payload["sub"])

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return FileResponse(os.path.join(frontend_dir, "index.html"))

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
