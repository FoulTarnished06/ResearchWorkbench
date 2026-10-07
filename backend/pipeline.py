import asyncio
import json
import time
import uuid
import re
from typing import Dict, Any, Optional, AsyncGenerator

from backend.agents.agent1_scraper import run_agent1_academic_scraper
from backend.agents.agent2_drafter import run_agent2_the_drafter
from backend.agents.agent3_cacher import run_agent3_context_cacher, run_agent3_context_distiller
from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer
from backend.post_processor import post_process_dossier
from backend.database import init_db, log_pipeline_run, get_response_cache, set_response_cache
from backend.logger import get_logger

logger = get_logger("Pipeline")

_db_initialized = False

def ensure_pipeline_db():
    """Ensure SQLite schema exists lazily upon first execution without import side effects."""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

def build_rapid_dossier_output(
    user_query: str,
    run_id: str,
    start_time: float,
    agent1_res: Dict[str, Any],
    agent2_res: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Pillar 5: Formats rapid synthesis monograph (Agent 1 + Agent 2).
    Delivers sub-7s accelerated turnaround with authentic citations and verified DOI links.
    """
    elapsed = round(time.time() - start_time, 2)
    a2_prompt = agent2_res.get("prompt_tokens") or round(agent2_res["tokens_used"] * 0.6)
    a2_comp = agent2_res.get("completion_tokens") or (agent2_res["tokens_used"] - a2_prompt)
    
    raw_sections = agent2_res.get("sections", [])
    rapid_sections = []
    papers = agent1_res.get("papers", [])
    for sec in raw_sections:
        content_html = sec.get("answer_html") or sec.get("content_html") or sec.get("content", "")
        for p_item in papers:
            pidx = p_item.get("paper_idx", "")
            purl = p_item.get("url", "#")
            if pidx and purl and purl != "#":
                content_html = re.sub(
                    rf'\[{pidx}\]',
                    f'<a href="{purl}" target="_blank" rel="noopener noreferrer" class="citation-anchor tier-cache-badge">[{pidx} ↗]</a>',
                    content_html
                )
        rapid_sections.append({
            "heading": sec.get("heading", "Rapid Synthesis"),
            "content_html": content_html,
            "claims": sec.get("claims", [])
        })
        
    citations = []
    for p in papers:
        citations.append({
            "paper_id": p.get("id"),
            "paper_idx": p.get("paper_idx"),
            "title": p.get("title"),
            "authors": p.get("authors"),
            "year": p.get("year"),
            "venue": p.get("venue"),
            "doi": p.get("doi"),
            "url": p.get("url"),
            "source": p.get("source"),
            "source_type": p.get("source_type", "Peer-Reviewed Paper"),
            "provenance_tier": p.get("provenance_tier", "peer_reviewed"),
            "provenance_label": p.get("provenance_label", "Peer-Reviewed Literature"),
            "citation_count": p.get("citationCount", 0)
        })
        
    rapid_output = {
        "run_id": run_id,
        "query": user_query,
        "execution_mode": "rapid",
        "elapsed_seconds": elapsed,
        "token_usage": {
            "total_tokens": agent2_res["tokens_used"],
            "prompt_tokens": a2_prompt,
            "completion_tokens": a2_comp,
            "llm_calls_count": 1,
            "llm_budget_limit": 1,
            "breakdown": {
                "agent1_scraper": 0,
                "agent2_drafter": agent2_res["tokens_used"],
                "agent3_cacher": 0,
                "agent4_fact_checker": 0
            },
            "io_breakdown": {
                "agent1_scraper": {"input": 0, "output": 0, "total": 0},
                "agent2_drafter": {"input": a2_prompt, "output": a2_comp, "total": agent2_res["tokens_used"]},
                "agent3_cacher": {"input": 0, "output": 0, "total": 0},
                "agent4_fact_checker": {"input": 0, "output": 0, "total": 0}
            }
        },
        "quick_answer": agent2_res.get("quick_answer", ""),
        "executive_summary": agent2_res.get("executive_summary", ""),
        "complexity": agent2_res.get("complexity", {}),
        "dossier_sections": rapid_sections,
        "citations": citations,
        "evaluated_claims": [],
        "comparison_table": agent2_res.get("comparison_table", {}),
        "dialectical_friction": agent2_res.get("dialectical_friction", []),
        "epistemic_limitations": agent2_res.get("epistemic_limitations", []),
        "stats": {
            "papers_scraped": agent1_res["papers_found"],
            "claims_total": len(agent2_res.get("claims", [])),
            "auto_verified_zero_token": 0,
            "llm_fact_checked": 0,
            "execution_mode": "rapid"
        }
    }
    return post_process_dossier(rapid_output)

async def run_query_pipeline(user_query: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Core Sequential 4-Step Pipeline.
    Supports 24h Response Caching (TOK-03-REVISED), Dual-Output Mode (DUAL-01),
    and non-blocking async operations (BUG-01, BUG-11).
    """
    config = config or {}
    ensure_pipeline_db()
    user_id = config.get("user_id")

    # 1. Check Query-Level Response Cache for identical queries (0 tokens, 100% quality)
    use_cache = not config.get("bypass_cache", False)
    if use_cache:
        cached_result = await asyncio.to_thread(get_response_cache, user_query)
        if cached_result:
            logger.info(f"Cache hit for query '{user_query[:40]}'. Returning cached synthesis (0 tokens).")
            hit_run_id = f"run_{uuid.uuid4().hex[:8]}"
            cached_result_copy = dict(cached_result)
            cached_result_copy["run_id"] = hit_run_id
            tok_usage = cached_result_copy.get("token_usage", {})
            total_toks = tok_usage.get("total_tokens", 0)
            p_toks = tok_usage.get("prompt_tokens", 0)
            c_toks = tok_usage.get("completion_tokens", 0)
            elapsed = cached_result_copy.get("elapsed_seconds", 0.0)
            await asyncio.to_thread(
                log_pipeline_run, hit_run_id, user_query, total_toks, elapsed, cached_result_copy, p_toks, c_toks, user_id
            )
            return cached_result_copy

    provider_agent2 = config.get("provider_agent2", "auto")
    provider_agent4 = config.get("provider_agent4", "auto")
    similarity_thresh = float(config.get("similarity_threshold", 0.55))
    paper_limit = int(config.get("paper_limit", 5))
    gemini_key = config.get("gemini_key")
    anthropic_key = config.get("anthropic_key")
    openai_key = config.get("openai_key")
    serpapi_key = config.get("serpapi_key")
    disable_fallback = bool(config.get("disable_fallback", False))
    disable_fallback_agent2 = bool(config.get("disable_fallback_agent2", disable_fallback))
    disable_fallback_agent4 = bool(config.get("disable_fallback_agent4", disable_fallback))
    scraper_sources = config.get("scraper_sources", "all")
    active_scrapers = config.get("active_scrapers")
    user_id = config.get("user_id")
    
    start_time = time.time()
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    try:
        # Step 1: Academic Scraper (Tool 1 - 0 Tokens)
        agent1_res = await run_agent1_academic_scraper(
            user_query, 
            limit=paper_limit, 
            sources=scraper_sources, 
            serpapi_key=serpapi_key,
            disable_fallback=disable_fallback_agent2,
            active_scrapers=active_scrapers,
            max_pdf_pages=int(config.get("max_pdf_pages", 15))
        )
        
        # Phase 1 Pre-Filter (Tool 2.1 - 0 Tokens): Feed comprehensive empirical context (~15k tokens)
        max_tokens_budget = int(config.get("max_tokens", 15000)) if config else 15000
        distilled_sentences = await asyncio.to_thread(
            run_agent3_context_distiller,
            user_query, agent1_res, top_k=120, max_tokens=max_tokens_budget
        )
        
        # Equip Drafter with full dense empirical context across all facets
        distilled_agent1_res = dict(agent1_res)
        distilled_agent1_res["dense_sentences"] = distilled_sentences
        
        # Step 2: The Drafter (AI Call 1)
        agent2_res = await run_agent2_the_drafter(
            user_query, 
            distilled_agent1_res, 
            provider=provider_agent2, 
            api_key=gemini_key, 
            anthropic_key=anthropic_key, 
            openai_key=openai_key, 
            disable_fallback=disable_fallback_agent2
        )
        
        # Pillar 5: Dual Execution Engine - Rapid Mode Exit (~5s)
        execution_mode = config.get("execution_mode", "deep")
        if execution_mode == "rapid":
            rapid_res = build_rapid_dossier_output(user_query, run_id, start_time, agent1_res, agent2_res)
            if use_cache:
                asyncio.create_task(asyncio.to_thread(set_response_cache, user_query, rapid_res, ttl_hours=24))
            a2_p = rapid_res["token_usage"]["prompt_tokens"]
            a2_c = rapid_res["token_usage"]["completion_tokens"]
            asyncio.create_task(asyncio.to_thread(
                log_pipeline_run, run_id, user_query, rapid_res["token_usage"]["total_tokens"], rapid_res["elapsed_seconds"], rapid_res, a2_p, a2_c, user_id
            ))
            return rapid_res

        # Step 3: Context Cacher & Pre-Filter (Tool 2 - 0 Tokens, Non-Blocking Async)
        agent3_res = await asyncio.to_thread(
            run_agent3_context_cacher,
            user_query, agent1_res, agent2_res, similarity_threshold=similarity_thresh
        )
        
        # Step 4: Fact-Checker & Synthesizer (AI Call 2 - Maximum Precision Tier)
        resolved_provider_a4 = provider_agent4
        if not resolved_provider_a4 or resolved_provider_a4 == "auto":
            prov_a2_lower = str(provider_agent2).lower()
            if any(k in prov_a2_lower for k in ("gpt", "openai", "sol", "luna", "astra")):
                resolved_provider_a4 = "gpt-6.1-sol"
            elif "claude" in prov_a2_lower or "anthropic" in prov_a2_lower:
                resolved_provider_a4 = "claude-sonnet-5.5"
            else:
                resolved_provider_a4 = "gemini-3.1-pro" if "pro" in prov_a2_lower else "gemini-3.6-flash"

        agent4_res = await run_agent4_fact_checker_synthesizer(
            user_query, 
            agent1_res, 
            agent2_res, 
            agent3_res, 
            provider=resolved_provider_a4, 
            api_key=gemini_key, 
            anthropic_key=anthropic_key, 
            openai_key=openai_key, 
            disable_fallback=disable_fallback_agent4
        )
        
        elapsed = round(time.time() - start_time, 2)
        a2_used = agent2_res.get("tokens_used", 0)
        a4_used = agent4_res.get("tokens_used", 0)
        a2_prompt = agent2_res.get("prompt_tokens") or round(a2_used * 0.6)
        a2_comp = agent2_res.get("completion_tokens") or max(0, a2_used - a2_prompt)
        a4_prompt = agent4_res.get("prompt_tokens") or round(a4_used * 0.6)
        a4_comp = agent4_res.get("completion_tokens") or max(0, a4_used - a4_prompt)
        total_prompt = a2_prompt + a4_prompt
        total_comp = a2_comp + a4_comp
        total_tokens = (
            agent1_res.get("tokens_used", 0) +
            a2_used +
            agent3_res.get("tokens_used", 0) +
            a4_used
        )
        
        quick_answer = agent4_res.get("quick_answer") or agent2_res.get("quick_answer", "")

        final_output = {
            "run_id": run_id,
            "query": user_query,
            "elapsed_seconds": elapsed,
            "token_usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": total_prompt,
                "completion_tokens": total_comp,
                "llm_calls_count": 2,
                "llm_budget_limit": 2,
                "breakdown": {
                    "agent1_scraper": 0,
                    "agent2_drafter": a2_used,
                    "agent3_cacher": 0,
                    "agent4_fact_checker": a4_used
                },
                "io_breakdown": {
                    "agent1_scraper": {"input": 0, "output": 0, "total": 0},
                    "agent2_drafter": {"input": a2_prompt, "output": a2_comp, "total": agent2_res["tokens_used"]},
                    "agent3_cacher": {"input": 0, "output": 0, "total": 0},
                    "agent4_fact_checker": {"input": a4_prompt, "output": a4_comp, "total": agent4_res["tokens_used"]}
                }
            },
            "quick_answer": quick_answer,
            "executive_summary": agent4_res.get("executive_summary", agent2_res.get("executive_summary", "")),
            "complexity": agent2_res.get("complexity", {}),
            "dossier_sections": agent4_res.get("dossier_sections", []),
            "citations": agent4_res.get("citations", []),
            "evaluated_claims": agent4_res.get("evaluated_claims", []),
            "comparison_table": agent4_res.get("comparison_table", agent2_res.get("comparison_table", {})),
            "dialectical_friction": agent4_res.get("dialectical_friction", agent2_res.get("dialectical_friction", [])),
            "epistemic_limitations": agent4_res.get("epistemic_limitations", agent2_res.get("epistemic_limitations", [])),
            "stats": {
                "papers_scraped": agent1_res["papers_found"],
                "claims_total": agent4_res.get("total_claims_synthesized", 0),
                "auto_verified_zero_token": agent3_res["auto_verified_count"],
                "llm_fact_checked": agent4_res.get("unverified_claims_processed", 0)
            },
            "all_scraped_papers": agent1_res.get("papers", []),
            "uncovered_facets": agent1_res.get("uncovered_facets", []),
            "covered_facets": agent1_res.get("covered_facets", []),
            "facets": agent1_res.get("facets", [])
        }
        
        final_output = post_process_dossier(final_output)

        # Asynchronously log to SQLite database (BUG-01)
        await asyncio.to_thread(log_pipeline_run, run_id, user_query, total_tokens, elapsed, final_output, total_prompt, total_comp, user_id)
        
        # Save to query response cache (TOK-03-REVISED)
        await asyncio.to_thread(set_response_cache, user_query, final_output)
        
        return final_output

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise

async def stream_query_pipeline(user_query: str, config: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
    """
    FastAPI Server-Sent Events (SSE) generator streaming real-time stage hand-offs.
    Optimized with zero artificial sleep delays (TOK-04) and dual-output format (DUAL-01).
    """
    config = config or {}
    ensure_pipeline_db()
    start_time = time.time()
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    def sse_message(event_type: str, data: Dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    user_id = config.get("user_id")

    active_scrapers = config.get("active_scrapers")
    scraper_label = f"{len(active_scrapers)} selected" if active_scrapers else "6 public academic"

    # Initial start event
    yield sse_message("pipeline_start", {
        "run_id": run_id,
        "query": user_query,
        "timestamp": time.time(),
        "status": "Pipeline initiated. Strict 2-LLM budget locked."
    })
    # Immediately notify client that Agent 1 is active so UI never hangs in Ready state
    yield sse_message("agent_active", {
        "agent_id": 1,
        "name": "Academic Scraper",
        "action": f"Querying {scraper_label} repositories (Crossref, DOAJ, OpenAlex, Semantic Scholar, Europe PMC, PubMed)...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    # Check cache first with bounded 2s timeout
    use_cache = not config.get("bypass_cache", False)
    if use_cache:
        try:
            cached_result = await asyncio.wait_for(asyncio.to_thread(get_response_cache, user_query), timeout=2.0)
            if cached_result:
                hit_run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
                cached_result_copy = dict(cached_result)
                cached_result_copy["run_id"] = hit_run_id
                tok_usage = cached_result_copy.get("token_usage", {})
                total_toks = tok_usage.get("total_tokens", 0)
                p_toks = tok_usage.get("prompt_tokens", 0)
                c_toks = tok_usage.get("completion_tokens", 0)
                elapsed = cached_result_copy.get("elapsed_seconds", 0.0)
                asyncio.create_task(asyncio.to_thread(
                    log_pipeline_run, hit_run_id, user_query, total_toks, elapsed, cached_result_copy, p_toks, c_toks, user_id
                ))
                yield sse_message("agent_completed", {
                    "agent_id": 0,
                    "name": "Semantic Cache",
                    "tokens_used": 0,
                    "status": "Cache hit: restored from local SQLite response cache (0 tokens)."
                })
                yield sse_message("pipeline_complete", cached_result_copy)
                await asyncio.sleep(0.05)
                return
        except Exception as cache_err:
            logger.debug(f"Cache check bypass/error: {cache_err}")

    disable_fallback_agent2 = bool(config.get("disable_fallback_agent2", False))
    disable_fallback_agent4 = bool(config.get("disable_fallback_agent4", False))
    scraper_sources = config.get("scraper_sources", "all")
    serpapi_key = config.get("serpapi_key")
    
    partial_data = {
        "query": user_query,
        "agent1_scraped": None,
        "agent2_draft": None,
        "agent3_cacher": None
    }
    
    yield sse_message("agent_progress", {
        "agent_id": 1,
        "name": "Academic Scraper",
        "details": f"Dispatching parallel search to {scraper_label} repositories...",
        "tokens_used": 0
    })
    await asyncio.sleep(0.01)
    
    try:
        scraper_task = asyncio.create_task(run_agent1_academic_scraper(
            user_query, 
            limit=int(config.get("paper_limit", 5)), 
            sources=scraper_sources, 
            serpapi_key=serpapi_key,
            disable_fallback=disable_fallback_agent2,
            active_scrapers=active_scrapers,
            max_pdf_pages=int(config.get("max_pdf_pages", 15))
        ))

        scraper_elapsed = 0.0
        while not scraper_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(scraper_task), timeout=1.5)
            except asyncio.TimeoutError:
                scraper_elapsed += 1.5
                yield f": keep-alive scraper {scraper_elapsed:.1f}s\n\n"
                if 2.5 <= scraper_elapsed < 4.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 1,
                        "name": "Academic Scraper",
                        "details": "Querying Crossref DOIs & OpenAlex citation index...",
                        "tokens_used": 0
                    })
                elif 5.5 <= scraper_elapsed < 7.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 1,
                        "name": "Academic Scraper",
                        "details": "Aggregating Semantic Scholar & Europe PMC open-access entries...",
                        "tokens_used": 0
                    })
                elif 9.5 <= scraper_elapsed < 11.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 1,
                        "name": "Academic Scraper",
                        "details": "Extracting full-text empirical findings & scoring information density...",
                        "tokens_used": 0
                    })
                elif scraper_elapsed >= 75.0:
                    logger.warning(f"Scraper task exceeded 75.0s limit for '{user_query}'; canceling.")
                    scraper_task.cancel()
                    break

        try:
            agent1_res = await scraper_task
        except (asyncio.CancelledError, Exception) as exc:
            logger.warning(f"Scraper task recovered after cancellation/exception: {exc}")
            agent1_res = {
                "agent": "Agent 1: Academic Scraper",
                "tokens_used": 0,
                "papers_found": 0,
                "papers": [],
                "dense_sentences": [],
                "total_sentences_extracted": 0,
                "facets": [],
                "covered_facets": [],
                "uncovered_facets": []
            }

        partial_data["agent1_scraped"] = agent1_res
        
        yield sse_message("agent_progress", {
            "agent_id": 1,
            "name": "Academic Scraper",
            "details": f"Retrieved {agent1_res['papers_found']} papers. Selected top {len(agent1_res['dense_sentences'])} info-dense facts.",
            "tokens_used": 0
        })
        
        yield sse_message("agent_completed", {
            "agent_id": 1,
            "name": "Academic Scraper",
            "tokens_used": 0,
            "agent1_scraped": agent1_res,
            "data_summary": {
                "papers_count": agent1_res["papers_found"],
                "top_facts": len(agent1_res["dense_sentences"])
            }
        })
        await asyncio.sleep(0.01)

        # Phase 1 Pre-Filter: Feed comprehensive empirical context (~15k tokens)
        max_tokens_budget = int(config.get("max_tokens", 15000)) if config else 15000
        try:
            distilled_sentences = await asyncio.wait_for(
                asyncio.to_thread(run_agent3_context_distiller, user_query, agent1_res, top_k=120, max_tokens=max_tokens_budget),
                timeout=15.0
            )
        except Exception as dist_err:
            logger.debug(f"Distiller timeout/error: {dist_err}")
            distilled_sentences = agent1_res.get("dense_sentences", [])

        distilled_agent1_res = dict(agent1_res)
        distilled_agent1_res["dense_sentences"] = distilled_sentences

        # AGENT 2: The Drafter (LLM Call 1)
        yield sse_message("agent_active", {
            "agent_id": 2,
            "name": "The Drafter",
            "action": "Synthesizing research draft & embedding <claim> tags (LLM Call 1/2)...",
            "status": "active"
        })
        await asyncio.sleep(0.01)

        drafter_task = asyncio.create_task(run_agent2_the_drafter(
            user_query, 
            distilled_agent1_res, 
            provider=config.get("provider_agent2", "auto"),
            api_key=config.get("gemini_key"),
            anthropic_key=config.get("anthropic_key"),
            openai_key=config.get("openai_key"),
            disable_fallback=disable_fallback_agent2
        ))

        drafter_elapsed = 0.0
        while not drafter_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(drafter_task), timeout=2.0)
            except asyncio.TimeoutError:
                drafter_elapsed += 2.0
                yield f": keep-alive drafter {drafter_elapsed:.1f}s\n\n"
                if 4.0 <= drafter_elapsed < 6.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 2,
                        "name": "The Drafter",
                        "details": "Structuring dialectical sections & embedding atomic <claim> boundaries...",
                        "tokens_used": 0
                    })
                elif 14.0 <= drafter_elapsed < 16.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 2,
                        "name": "The Drafter",
                        "details": "Synthesizing empirical findings across technical subtopics...",
                        "tokens_used": 0
                    })
                elif 28.0 <= drafter_elapsed < 30.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 2,
                        "name": "The Drafter",
                        "details": "Finalizing claim boundaries & formatting section monograph...",
                        "tokens_used": 0
                    })
                elif drafter_elapsed >= 180.0:
                    logger.warning("Drafter task exceeded 180.0s limit; canceling.")
                    drafter_task.cancel()
                    break

        try:
            agent2_res = await drafter_task
        except (asyncio.CancelledError, Exception) as exc:
            logger.warning(f"Drafter task did not complete normally ({exc}). Generating resilient fallback draft...")
            from backend.agents.agent2_drafter import synthesize_fallback_draft
            agent2_res = synthesize_fallback_draft(
                user_query,
                agent1_res.get("papers", []),
                dense_sentences=agent1_res.get("dense_sentences", [])
            )
        partial_data["agent2_draft"] = agent2_res
        
        yield sse_message("agent_progress", {
            "agent_id": 2,
            "name": "The Drafter",
            "details": f"Formulated {len(agent2_res.get('sub_questions', []))} sub-questions with {len(agent2_res.get('claims', []))} tagged empirical claims.",
            "tokens_used": agent2_res["tokens_used"]
        })
        
        a2_prompt = agent2_res.get("prompt_tokens") or round(agent2_res["tokens_used"] * 0.6)
        a2_comp = agent2_res.get("completion_tokens") or (agent2_res["tokens_used"] - a2_prompt)
        yield sse_message("agent_completed", {
            "agent_id": 2,
            "name": "The Drafter",
            "tokens_used": agent2_res["tokens_used"],
            "prompt_tokens": a2_prompt,
            "completion_tokens": a2_comp,
            "claims_count": len(agent2_res.get("claims", [])),
            "complexity": agent2_res.get("complexity", {}),
            "agent2_draft": agent2_res
        })
        await asyncio.sleep(0.01)

        # Pillar 5: Dual Execution Engine - Rapid Mode Exit (~5s)
        execution_mode = config.get("execution_mode", "deep")
        if execution_mode == "rapid":
            rapid_res = build_rapid_dossier_output(user_query, run_id, start_time, agent1_res, agent2_res)
            if not config.get("bypass_cache", False):
                asyncio.create_task(asyncio.to_thread(set_response_cache, user_query, rapid_res, ttl_hours=24))
            a2_p = rapid_res["token_usage"]["prompt_tokens"]
            a2_c = rapid_res["token_usage"]["completion_tokens"]
            asyncio.create_task(asyncio.to_thread(
                log_pipeline_run, run_id, user_query, rapid_res["token_usage"]["total_tokens"], rapid_res["elapsed_seconds"], rapid_res, a2_p, a2_c, user_id
            ))
            yield sse_message("pipeline_complete", rapid_res)
            await asyncio.sleep(0.05)
            return

        # AGENT 3: Context Cacher & Pre-Filter (Tool 2 - 0 Tokens)
        yield sse_message("agent_active", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "action": "Caching to SQLite & executing cosine similarity pre-filtering (0 LLM Tokens)...",
            "status": "active"
        })
        await asyncio.sleep(0.01)

        cacher_task = asyncio.create_task(asyncio.to_thread(
            run_agent3_context_cacher,
            user_query, agent1_res, agent2_res, similarity_threshold=float(config.get("similarity_threshold", 0.55))
        ))
        cacher_elapsed = 0.0
        while not cacher_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(cacher_task), timeout=2.0)
            except asyncio.TimeoutError:
                cacher_elapsed += 2.0
                yield f": keep-alive cacher {cacher_elapsed:.1f}s\n\n"
                if cacher_elapsed >= 60.0:
                    logger.warning("Context cacher task exceeded 60.0s limit; canceling.")
                    cacher_task.cancel()
                    break

        try:
            agent3_res = await cacher_task
        except (asyncio.CancelledError, Exception) as cacher_err:
            logger.warning(f"Context cacher timeout/error: {cacher_err}")
            agent3_res = {
                "auto_verified_count": 0,
                "unverified_for_agent4_count": len(agent2_res.get("claims", [])),
                "verified_claims": [],
                "unverified_claims": agent2_res.get("claims", [])
            }

        partial_data["agent3_cacher"] = agent3_res

        yield sse_message("agent_progress", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "details": f"Auto-verified {agent3_res['auto_verified_count']} claims via SQLite cosine similarity. Queued {agent3_res['unverified_for_agent4_count']} for Agent 4.",
            "tokens_used": 0
        })

        yield sse_message("agent_completed", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "tokens_used": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "auto_verified": agent3_res["auto_verified_count"],
            "unverified_pending": agent3_res["unverified_for_agent4_count"],
            "agent3_cacher": agent3_res
        })
        await asyncio.sleep(0.01)

        # AGENT 4: Fact-Checker & Synthesizer (LLM Call 2 - Maximum Precision Tier)
        yield sse_message("agent_active", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "action": f"Checking {agent3_res['unverified_for_agent4_count']} unverified claims against context & finalizing dossier (LLM Call 2/2)...",
            "status": "active"
        })
        await asyncio.sleep(0.01)

        resolved_stream_provider_a4 = config.get("provider_agent4", "auto")
        if not resolved_stream_provider_a4 or resolved_stream_provider_a4 == "auto":
            prov_a2_lower = str(config.get("provider_agent2", "auto")).lower()
            if any(k in prov_a2_lower for k in ("gpt", "openai", "sol", "luna", "astra")):
                resolved_stream_provider_a4 = "gpt-6.1-sol"
            elif "claude" in prov_a2_lower or "anthropic" in prov_a2_lower:
                resolved_stream_provider_a4 = "claude-sonnet-5.5"
            else:
                resolved_stream_provider_a4 = "gemini-3.1-pro" if "pro" in prov_a2_lower else "gemini-3.6-flash"

        synth_task = asyncio.create_task(run_agent4_fact_checker_synthesizer(
            user_query, 
            agent1_res, 
            agent2_res, 
            agent3_res, 
            provider=resolved_stream_provider_a4, 
            api_key=config.get("gemini_key"),
            anthropic_key=config.get("anthropic_key"),
            openai_key=config.get("openai_key"),
            disable_fallback=disable_fallback_agent4
        ))

        synth_elapsed = 0.0
        while not synth_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(synth_task), timeout=2.0)
            except asyncio.TimeoutError:
                synth_elapsed += 2.0
                yield f": keep-alive synthesizer {synth_elapsed:.1f}s\n\n"
                if 4.0 <= synth_elapsed < 6.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 4,
                        "name": "Fact-Checker & Synthesizer",
                        "details": "Adjudicating claim confidence & indexing citations against source literature...",
                        "tokens_used": 0
                    })
                elif 16.0 <= synth_elapsed < 18.0:
                    yield sse_message("agent_progress", {
                        "agent_id": 4,
                        "name": "Fact-Checker & Synthesizer",
                        "details": "Cross-referencing claims against source evidence and computing verification metrics...",
                        "tokens_used": 0
                    })
                elif synth_elapsed >= 150.0:
                    logger.warning("Synthesizer task exceeded 150.0s limit; canceling.")
                    synth_task.cancel()
                    break

        try:
            agent4_res = await synth_task
        except (asyncio.CancelledError, Exception) as exc:
            logger.warning(f"Synthesizer task interrupted or errored ({exc}). Executing resilient offline synthesis...")
            agent4_res = await run_agent4_fact_checker_synthesizer(
                query=user_query,
                agent1_data=agent1_res,
                agent2_data=agent2_res,
                agent3_data=agent3_res,
                provider=resolved_stream_provider_a4,
                disable_fallback=False
            )

        yield sse_message("agent_progress", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "details": f"Fact-checked all claims. Confidence scores assigned. Citations indexed to source literature.",
            "tokens_used": agent4_res.get("tokens_used", 0)
        })

        a4_used = agent4_res.get("tokens_used", 0)
        a4_prompt = agent4_res.get("prompt_tokens") or round(a4_used * 0.6)
        a4_comp = agent4_res.get("completion_tokens") or max(0, a4_used - a4_prompt)
        yield sse_message("agent_completed", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "tokens_used": a4_used,
            "prompt_tokens": a4_prompt,
            "completion_tokens": a4_comp,
            "model": agent4_res.get("provider", resolved_stream_provider_a4)
        })
        await asyncio.sleep(0.01)

        # FINAL PIPELINE COMPLETE
        elapsed = round(time.time() - start_time, 2)
        total_prompt = a2_prompt + a4_prompt
        total_comp = a2_comp + a4_comp
        a2_used = agent2_res.get("tokens_used", 0)
        total_tokens = (
            agent1_res.get("tokens_used", 0) +
            a2_used +
            agent3_res.get("tokens_used", 0) +
            a4_used
        )
        
        quick_answer = agent4_res.get("quick_answer") or agent2_res.get("quick_answer", "")

        final_payload = {
            "run_id": run_id,
            "query": user_query,
            "elapsed_seconds": elapsed,
            "token_usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": total_prompt,
                "completion_tokens": total_comp,
                "llm_calls_count": 1 if a4_used == 0 else 2,
                "llm_budget_limit": 2,
                "breakdown": {
                    "agent1_scraper": 0,
                    "agent2_drafter": a2_used,
                    "agent3_cacher": 0,
                    "agent4_fact_checker": a4_used
                },
                "io_breakdown": {
                    "agent1_scraper": {"input": 0, "output": 0, "total": 0},
                    "agent2_drafter": {"input": a2_prompt, "output": a2_comp, "total": agent2_res["tokens_used"]},
                    "agent3_cacher": {"input": 0, "output": 0, "total": 0},
                    "agent4_fact_checker": {"input": a4_prompt, "output": a4_comp, "total": agent4_res["tokens_used"]}
                }
            },
            "quick_answer": quick_answer,
            "complexity": agent2_res.get("complexity", {}),
            "executive_summary": agent4_res.get("executive_summary", agent2_res.get("executive_summary", "")),
            "dossier_sections": agent4_res.get("dossier_sections", []),
            "citations": agent4_res.get("citations", []),
            "evaluated_claims": agent4_res.get("evaluated_claims", []),
            "comparison_table": agent4_res.get("comparison_table", agent2_res.get("comparison_table", {})),
            "dialectical_friction": agent4_res.get("dialectical_friction", agent2_res.get("dialectical_friction", [])),
            "epistemic_limitations": agent4_res.get("epistemic_limitations", agent2_res.get("epistemic_limitations", [])),
            "stats": {
                "papers_scraped": agent1_res["papers_found"],
                "claims_total": agent4_res.get("total_claims_synthesized", 0),
                "auto_verified_zero_token": agent3_res["auto_verified_count"],
                "llm_fact_checked": agent4_res.get("unverified_claims_processed", 0)
            },
            "all_scraped_papers": agent1_res.get("papers", []),
            "uncovered_facets": agent1_res.get("uncovered_facets", []),
            "covered_facets": agent1_res.get("covered_facets", []),
            "facets": agent1_res.get("facets", [])
        }
        
        final_payload = post_process_dossier(final_payload)

        # Emit completion IMMEDIATELY to client without blocking on DB write latency
        yield sse_message("pipeline_complete", final_payload)
        await asyncio.sleep(0.4)

        # Asynchronously log to SQLite database and cache in background (BUG-01, TOK-03-REVISED)
        asyncio.create_task(asyncio.to_thread(log_pipeline_run, run_id, user_query, total_tokens, elapsed, final_payload, total_prompt, total_comp, user_id))
        asyncio.create_task(asyncio.to_thread(set_response_cache, user_query, final_payload))
    except (asyncio.CancelledError, Exception) as exc:
        err_msg = str(exc)
        logger.error(f"Pipeline error: {err_msg}")
        if partial_data.get("agent2_draft"):
            a2 = partial_data["agent2_draft"]
            if "sections" in a2 and "dossier_sections" not in a2:
                a2["dossier_sections"] = [
                    {
                        "sub_question": s.get("sub_question", "Draft Section"),
                        "content_html": s.get("answer_html", "")
                    }
                    for s in a2.get("sections", [])
                ]
        if partial_data.get("agent1_scraped") and "agent1_scraper" not in partial_data:
            partial_data["agent1_scraper"] = partial_data["agent1_scraped"]
        yield sse_message("pipeline_error", {
            "error": err_msg,
            "status": "Execution failed. Live AI returned an error.",
            "partial_data": partial_data
        })
