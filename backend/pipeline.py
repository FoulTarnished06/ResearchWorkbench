import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from backend.agents.agent1_scraper import run_agent1_academic_scraper
from backend.agents.agent2_drafter import run_agent2_the_drafter
from backend.agents.agent3_cacher import run_agent3_context_cacher
from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer
from backend.post_processor import post_process_dossier
from backend.database import init_db, log_pipeline_run

# Ensure SQLite schema exists
init_db()

async def run_query_pipeline(user_query: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Core Sequential 4-Step Pipeline (v2 Architecture).
    Strict 2-LLM Budget: Agent 1 (0 tokens) -> Agent 2 (LLM 1) -> Agent 3 (0 tokens) -> Agent 4 (LLM 2).
    """
    config = config or {}
    provider_agent2 = config.get("provider_agent2", "auto")
    provider_agent4 = config.get("provider_agent4", "auto")
    similarity_thresh = float(config.get("similarity_threshold", 0.80))
    paper_limit = int(config.get("paper_limit", 5))
    gemini_key = config.get("gemini_key")
    anthropic_key = config.get("anthropic_key")
    serpapi_key = config.get("serpapi_key")
    disable_fallback = bool(config.get("disable_fallback", False))
    scraper_sources = config.get("scraper_sources", "all")
    
    start_time = time.time()
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    # Step 1: Academic Scraper (Tool 1 - 0 Tokens)
    agent1_res = await run_agent1_academic_scraper(user_query, limit=paper_limit, sources=scraper_sources, serpapi_key=serpapi_key)
    
    # Step 2: The Drafter (AI Call 1)
    agent2_res = await run_agent2_the_drafter(
        user_query, agent1_res, provider=provider_agent2, api_key=gemini_key, anthropic_key=anthropic_key, disable_fallback=disable_fallback
    )
    
    # Step 3: Context Cacher & Pre-Filter (Tool 2 - 0 Tokens)
    agent3_res = run_agent3_context_cacher(
        user_query, agent1_res, agent2_res, similarity_threshold=similarity_thresh
    )
    
    # Step 4: Fact-Checker & Synthesizer (AI Call 2)
    agent4_res = await run_agent4_fact_checker_synthesizer(
        user_query, agent1_res, agent2_res, agent3_res, provider=provider_agent4, api_key=gemini_key, anthropic_key=anthropic_key, disable_fallback=disable_fallback
    )
    
    elapsed = round(time.time() - start_time, 2)
    total_tokens = agent1_res["tokens_used"] + agent2_res["tokens_used"] + agent3_res["tokens_used"] + agent4_res["tokens_used"]
    
    final_output = {
        "run_id": run_id,
        "query": user_query,
        "elapsed_seconds": elapsed,
        "token_usage": {
            "total_tokens": total_tokens,
            "llm_calls_count": 2,
            "llm_budget_limit": 2,
            "breakdown": {
                "agent1_scraper": 0,
                "agent2_drafter": agent2_res["tokens_used"],
                "agent3_cacher": 0,
                "agent4_fact_checker": agent4_res["tokens_used"]
            }
        },
        "executive_summary": agent4_res.get("executive_summary", agent2_res.get("executive_summary", "")),
        "complexity": agent2_res.get("complexity", {}),
        "agent1_data": agent1_res,
        "agent2_data": agent2_res,
        "agent3_data": agent3_res,
        "agent4_data": agent4_res,
        "dossier_sections": agent4_res["dossier_sections"],
        "citations": agent4_res["citations"]
    }
    
    final_output = post_process_dossier(final_output)

    # Log to SQLite
    log_pipeline_run(run_id, user_query, total_tokens, elapsed, final_output)
    
    return final_output

async def stream_query_pipeline(user_query: str, config: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
    """
    FastAPI Server-Sent Events (SSE) generator streaming real-time stage hand-offs.
    """
    config = config or {}
    start_time = time.time()
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    def sse_message(event_type: str, data: Dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # Initial start event
    yield sse_message("pipeline_start", {
        "run_id": run_id,
        "query": user_query,
        "timestamp": time.time(),
        "status": "Pipeline initiated. Strict 2-LLM budget locked."
    })
    await asyncio.sleep(0.3)

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
    
    #AGENT 1: Academic Scraper
    yield sse_message("agent_active", {
        "agent_id": 1,
        "name": "Academic Scraper",
        "action": f"Querying {scraper_sources} APIs (0 LLM Tokens)...",
        "status": "active"
    })
    await asyncio.sleep(0.4)
    
    try:
        agent1_res = await run_agent1_academic_scraper(user_query, limit=int(config.get("paper_limit", 5)), sources=scraper_sources, serpapi_key=serpapi_key)
        partial_data["agent1_scraped"] = agent1_res
        
        yield sse_message("agent_progress", {
            "agent_id": 1,
            "name": "Academic Scraper",
            "details": f"Retrieved {agent1_res['papers_found']} papers. Extracted {agent1_res['total_sentences_extracted']} sentences, selected top {len(agent1_res['dense_sentences'])} info-dense facts.",
            "tokens_used": 0
        })
        await asyncio.sleep(0.4)
        
        yield sse_message("agent_completed", {
            "agent_id": 1,
            "name": "Academic Scraper",
            "tokens_used": 0,
            "data_summary": {
                "papers_count": agent1_res["papers_found"],
                "top_facts": len(agent1_res["dense_sentences"])
            }
        })
        await asyncio.sleep(0.4)

        #AGENT 2: The Drafter (LLM Call 1)
        yield sse_message("agent_active", {
            "agent_id": 2,
            "name": "The Drafter",
            "action": "Synthesizing research draft & embedding <claim> tags (LLM Call 1/2)...",
            "status": "active"
        })
        await asyncio.sleep(0.5)

        agent2_res = await run_agent2_the_drafter(
            user_query, 
            agent1_res, 
            provider=config.get("provider_agent2", "auto"),
            api_key=config.get("gemini_key"),
            anthropic_key=config.get("anthropic_key"),
            disable_fallback=disable_fallback_agent2
        )
        partial_data["agent2_draft"] = agent2_res
        
        yield sse_message("agent_progress", {
            "agent_id": 2,
            "name": "The Drafter",
            "details": f"Formulated {len(agent2_res['sub_questions'])} sub-questions with {len(agent2_res['claims'])} tagged empirical claims.",
            "tokens_used": agent2_res["tokens_used"]
        })
        await asyncio.sleep(0.4)

        yield sse_message("agent_completed", {
            "agent_id": 2,
            "name": "The Drafter",
            "tokens_used": agent2_res["tokens_used"],
            "claims_count": len(agent2_res["claims"]),
            "complexity": agent2_res.get("complexity", {})
        })
        await asyncio.sleep(0.4)

        #AGENT 3: Context Cacher & Pre-Filter (Tool 2 - 0 Tokens)
        yield sse_message("agent_active", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "action": "Caching to SQLite & executing cosine similarity pre-filtering (0 LLM Tokens)...",
            "status": "active"
        })
        await asyncio.sleep(0.5)

        agent3_res = run_agent3_context_cacher(
            user_query, agent1_res, agent2_res, similarity_threshold=float(config.get("similarity_threshold", 0.80))
        )
        partial_data["agent3_cacher"] = agent3_res

        yield sse_message("agent_progress", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "details": f"Auto-verified {agent3_res['auto_verified_count']} claims via SQLite cosine similarity (Saved LLM tokens). Queued {agent3_res['unverified_for_agent4_count']} for Agent 4.",
            "tokens_used": 0
        })
        await asyncio.sleep(0.4)

        yield sse_message("agent_completed", {
            "agent_id": 3,
            "name": "Context Cacher & Pre-Filter",
            "tokens_used": 0,
            "auto_verified": agent3_res["auto_verified_count"],
            "unverified_pending": agent3_res["unverified_for_agent4_count"]
        })
        await asyncio.sleep(0.4)

        # --- AGENT 4: Fact-Checker & Synthesizer (LLM Call 2) ---
        yield sse_message("agent_active", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "action": f"Checking {agent3_res['unverified_for_agent4_count']} unverified claims against context & finalizing dossier (LLM Call 2/2)...",
            "status": "active"
        })
        await asyncio.sleep(0.5)

        agent4_res = await run_agent4_fact_checker_synthesizer(
            user_query, 
            agent1_res, 
            agent2_res, 
            agent3_res, 
            provider=config.get("provider_agent4", "auto"),
            api_key=config.get("gemini_key"),
            anthropic_key=config.get("anthropic_key"),
            disable_fallback=disable_fallback_agent4
        )

        yield sse_message("agent_progress", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "details": f"Fact-checked all claims. Confidence scores assigned. Citations indexed to source literature.",
            "tokens_used": agent4_res["tokens_used"]
        })
        await asyncio.sleep(0.4)

        yield sse_message("agent_completed", {
            "agent_id": 4,
            "name": "Fact-Checker & Synthesizer",
            "tokens_used": agent4_res["tokens_used"]
        })
        await asyncio.sleep(0.4)

        # --- FINAL PIPELINE COMPLETE ---
        elapsed = round(time.time() - start_time, 2)
        total_tokens = agent1_res["tokens_used"] + agent2_res["tokens_used"] + agent3_res["tokens_used"] + agent4_res["tokens_used"]
        
        final_payload = {
            "run_id": run_id,
            "query": user_query,
            "elapsed_seconds": elapsed,
            "token_usage": {
                "total_tokens": total_tokens,
                "llm_calls_count": 2,
                "llm_budget_limit": 2,
                "breakdown": {
                    "agent1_scraper": 0,
                    "agent2_drafter": agent2_res["tokens_used"],
                    "agent3_cacher": 0,
                    "agent4_fact_checker": agent4_res["tokens_used"]
                }
            },
            "complexity": agent2_res.get("complexity", {}),
            "executive_summary": agent4_res.get("executive_summary", agent2_res.get("executive_summary", "")),
            "dossier_sections": agent4_res["dossier_sections"],
            "citations": agent4_res["citations"],
            "evaluated_claims": agent4_res.get("evaluated_claims", []),
            "stats": {
                "papers_scraped": agent1_res["papers_found"],
                "claims_total": agent4_res["total_claims_synthesized"],
                "auto_verified_zero_token": agent3_res["auto_verified_count"],
                "llm_fact_checked": agent4_res["unverified_claims_processed"]
            }
        }
        
        final_payload = post_process_dossier(final_payload)

        log_pipeline_run(run_id, user_query, total_tokens, elapsed, final_payload)

        yield sse_message("pipeline_complete", final_payload)
    except Exception as exc:
        err_msg = str(exc)
        print(f"[Pipeline Error] {err_msg}")
        yield sse_message("pipeline_error", {
            "error": err_msg,
            "status": "Execution failed. Live AI returned an error.",
            "partial_data": partial_data
        })
