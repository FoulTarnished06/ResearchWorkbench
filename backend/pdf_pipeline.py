import asyncio
import json
import time
import uuid
import re
from typing import Dict, Any, Optional, AsyncGenerator, List
from backend.database import (
    get_pdf_session, get_pdf_files_by_session, get_pdf_chunks_by_session,
    get_pdf_figures_by_session, get_pdf_references_by_session, get_citation_graph_data,
    log_pipeline_run, update_pdf_session_last_accessed
)
from backend.agents.pdf_synthesizer import run_pdf_summarize, run_pdf_qa, run_pdf_deep_analysis
from backend.agents.citation_graph_builder import build_citation_graph_for_session
from backend.post_processor import post_process_pdf_output

def _stem(word: str) -> str:
    w = word.lower()
    for suffix in ("ations", "ation", "ions", "ion", "ings", "ing", "ments", "ment", "ers", "er", "ies", "ied", "ed", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[:-len(suffix)]
    return w

def compute_query_similarity(query: str, chunk_vec: Dict[str, float], chunk_text: str = "") -> float:
    """Cosine similarity between query words/stems/bigrams and chunk vector."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
    if not words or not chunk_vec:
        if chunk_text and any(w in chunk_text.lower() for w in words):
            return 0.5
        return 0.0

    score = 0.0
    lower_text = chunk_text.lower() if chunk_text else ""
    for w in words:
        if w in chunk_vec:
            score += chunk_vec[w]
        stem = _stem(w)
        stem_key = f"stem_{stem}"
        if stem_key in chunk_vec:
            score += chunk_vec[stem_key] * 0.9
        elif stem in lower_text:
            score += 0.4

    for i in range(len(words) - 1):
        bg = f"{words[i]}_{words[i+1]}"
        if bg in chunk_vec:
            score += chunk_vec[bg] * 1.5
    return score

def select_top_chunks(query: str, chunks: List[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    """Selects top chunks based on cosine similarity, stemming, and document ordering."""
    def is_bp(c):
        txt = (c.get("chunk_text") or "").lower()
        return c.get("is_boilerplate") or any(b in txt for b in [
            "proper attribution is provided",
            "grants permission to reproduce",
            "for use in journalistic or scholarly",
            "permission to make digital or hard copies",
            "all rights reserved"
        ])

    scored = []
    for c in chunks:
        vec = c.get("vector", {})
        if not vec and c.get("vector_json"):
            try:
                vec = json.loads(c["vector_json"])
            except Exception:
                vec = {}
        txt = c.get("chunk_text", "")
        score = compute_query_similarity(query, vec, txt)
        sec = (c.get("section_title") or "").lower()
        if any(w in sec for w in re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())):
            score += 1.2
        if is_bp(c):
            score *= 0.05
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] <= 0.01:
        clean_chunks = [c for c in chunks if not is_bp(c)]
        return clean_chunks[:limit] if clean_chunks else chunks[:limit]
    return [c for score, c in scored[:limit]]


async def run_pdf_pipeline(
    session_id: str,
    action: str,
    query: str = "",
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous PDF analysis pipeline execution.
    """
    config = config or {}
    provider = config.get("provider", "auto")
    gemini_key = config.get("gemini_key")
    anthropic_key = config.get("anthropic_key")
    disable_fallback = bool(config.get("disable_fallback", False))
    demo_mode = bool(config.get("demo_mode", False))
    chat_history = config.get("chat_history", [])
    analysis_type = config.get("analysis_type", "methodology")

    start_time = time.time()
    update_pdf_session_last_accessed(session_id)

    session = get_pdf_session(session_id)
    if not session:
        raise ValueError(f"PDF session not found: {session_id}")

    files = get_pdf_files_by_session(session_id)
    first_file = files[0] if files else {}
    doc_metadata = {
        "title": first_file.get("title") or first_file.get("original_filename", "Uploaded Document"),
        "authors": first_file.get("authors", ""),
        "subject": first_file.get("subject", "")
    }

    chunks = get_pdf_chunks_by_session(session_id)
    figures = get_pdf_figures_by_session(session_id)
    references = get_pdf_references_by_session(session_id)

    if action == "citation_graph":
        graph_data = get_citation_graph_data(session_id)
        if not graph_data.get("nodes"):
            graph_data = await build_citation_graph_for_session(session_id, references)
        return {
            "session_id": session_id,
            "action": "citation_graph",
            "citation_graph": graph_data,
            "tokens_used": 0,
            "elapsed_seconds": round(time.time() - start_time, 2)
        }

    elif action == "qa":
        top_chunks = select_top_chunks(query, chunks, limit=8)
        res = await run_pdf_qa(
            query=query,
            relevant_chunks=top_chunks,
            metadata=doc_metadata,
            figures=figures,
            chat_history=chat_history,
            provider=provider,
            api_key=gemini_key,
            anthropic_key=anthropic_key,
            disable_fallback=disable_fallback,
            demo_mode=demo_mode
        )
        res["elapsed_seconds"] = round(time.time() - start_time, 2)
        res["session_id"] = session_id
        return post_process_pdf_output(res)

    elif action == "summarize":
        top_chunks = select_top_chunks(query or "executive problem statement and empirical benchmarks", chunks, limit=10)
        res = await run_pdf_summarize(
            chunks=top_chunks,
            metadata=doc_metadata,
            figures=figures,
            provider=provider,
            api_key=gemini_key,
            anthropic_key=anthropic_key,
            disable_fallback=disable_fallback,
            demo_mode=demo_mode
        )
        res["elapsed_seconds"] = round(time.time() - start_time, 2)
        res["session_id"] = session_id
        return post_process_pdf_output(res)

    else:
        # deep_analysis / critique / compare / extract_findings
        analysis_type = "critique" if action == "critique" else ("compare" if action == "compare" else ("findings" if action == "extract_findings" else analysis_type))
        top_chunks = select_top_chunks(query or analysis_type, chunks, limit=12)
        res = await run_pdf_deep_analysis(
            query=query or analysis_type,
            chunks=top_chunks,
            metadata=doc_metadata,
            figures=figures,
            references=references,
            analysis_type=analysis_type,
            provider=provider,
            api_key=gemini_key,
            anthropic_key=anthropic_key,
            disable_fallback=disable_fallback,
            demo_mode=demo_mode
        )
        res["elapsed_seconds"] = round(time.time() - start_time, 2)
        res["session_id"] = session_id
        return post_process_pdf_output(res)


async def stream_pdf_pipeline(
    session_id: str,
    action: str,
    query: str = "",
    config: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events (SSE) generator streaming stage updates for PDF operations.
    """
    config = config or {}
    start_time = time.time()
    run_id = f"pdf_run_{uuid.uuid4().hex[:8]}"

    def sse_message(event_type: str, data: Dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    yield sse_message("pdf_pipeline_start", {
        "run_id": run_id,
        "session_id": session_id,
        "action": action,
        "query": query,
        "status": "PDF Analysis Pipeline Initiated."
    })
    await asyncio.sleep(0.3)

    try:
        session = get_pdf_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found in database.")

        yield sse_message("pdf_chunks_ready", {
            "session_id": session_id,
            "total_chunks": session.get("total_chunks", 0),
            "total_figures": session.get("total_figures", 0),
            "total_references": session.get("total_references", 0)
        })
        await asyncio.sleep(0.2)

        yield sse_message("pdf_agent_active", {
            "agent": "Agent P2: Document Retrieval Engine",
            "status": f"Scanning indexed chunks for '{query or action}'..."
        })
        await asyncio.sleep(0.3)

        yield sse_message("pdf_agent_active", {
            "agent": "Agent P3: Scientific Document Synthesizer",
            "status": "Generating authoritative analysis..."
        })

        result = await run_pdf_pipeline(session_id, action, query, config)
        result["run_id"] = run_id
        result["elapsed_seconds"] = round(time.time() - start_time, 2)

        yield sse_message("pdf_agent_completed", {
            "agent": "Agent P3: Scientific Document Synthesizer",
            "tokens_used": result.get("tokens_used", 0)
        })
        await asyncio.sleep(0.2)

        log_pipeline_run(
            run_id=run_id,
            query=f"[PDF {action.upper()}] {query or session_id}",
            tokens_used=result.get("tokens_used", 0),
            elapsed_seconds=result.get("elapsed_seconds", 0.0),
            results=result
        )

        yield sse_message("pdf_pipeline_complete", result)

    except Exception as e:
        err_msg = str(e)
        print(f"[PDF Pipeline Error] {err_msg}")
        yield sse_message("pdf_pipeline_error", {
            "error": err_msg,
            "status": "PDF Analysis failed."
        })
