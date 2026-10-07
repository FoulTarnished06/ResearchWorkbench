"""
AI Research Workbench v5.0 Deep-Verification Streaming Pipeline (Tier 1 Architecture)
Orchestrates:
- Per-Concept Sub-Question Retrieval (Multi-Source arXiv, Crossref, OpenAlex, Semantic Scholar)
- Citation Snowballing & Canonical Paper Surfacing
- Preprint vs. Peer-Reviewed Published Version Resolution
- Passage-Level Full-Text Chunk Verification
- Exact-Match Deterministic Number & Unit Auditing
- 3-Way Verdicts (SUPPORTED / CONTRADICTED / NOT_FOUND_IN_CHECKED_TEXT)
- SSE Event-Streaming to Workbench Canvas
"""

import asyncio
import json
import time
import uuid
import re
from typing import Dict, Any, Optional, AsyncGenerator

from backend.engine_v5.concept_decomposer import decompose_research_query
from backend.engine_v5.snowball_retriever import execute_per_concept_retrieval
from backend.engine_v5.passage_verifier import verify_all_claims_depth
from backend.agents.agent2_drafter import run_agent2_the_drafter
from backend.agents.agent3_cacher import run_agent3_context_cacher
from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer
from backend.post_processor import post_process_dossier
from backend.database import init_db, log_pipeline_run, get_response_cache, set_response_cache
from backend.logger import get_logger

logger = get_logger("Pipeline_v5")

def sse_message(event_type: str, data: Dict[str, Any]) -> str:
    """Format SSE event frame."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

async def stream_query_pipeline_v5(user_query: str, config: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
    """
    Tier 1 Deep Verification Streaming Pipeline.
    Emits real-time SSE progress events for per-concept decomposition, snowball retrieval,
    passage auditing, and 3-way claim verification.
    """
    if config is None:
        config = {}

    start_time = time.time()
    run_id = str(uuid.uuid4())
    logger.info(f"Starting v5 Deep Verification Pipeline for run_id={run_id}, query='{user_query}'")

    yield sse_message("pipeline_started", {
        "run_id": run_id,
        "query": user_query,
        "engine": "v5.0_deep_verification",
        "timestamp": time.time()
    })
    await asyncio.sleep(0.01)

    # 1. DECOMPOSE QUERY INTO PER-CONCEPT FACETS
    yield sse_message("agent_active", {
        "agent_id": 1,
        "name": "Concept Decomposer",
        "action": "Decomposing research query into distinct sub-questions and theoretical facets...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    concepts = decompose_research_query(user_query)
    concept_labels = [c["label"] for c in concepts]

    yield sse_message("agent_progress", {
        "agent_id": 1,
        "name": "Concept Decomposer",
        "details": f"Formulated {len(concepts)} inquiry facets: {', '.join(concept_labels)}",
        "tokens_used": 0
    })
    await asyncio.sleep(0.01)

    # 2. PER-CONCEPT RETRIEVAL & CITATION SNOWBALLING
    yield sse_message("agent_active", {
        "agent_id": 1,
        "name": "Snowball & Multi-Source Retriever",
        "action": "Executing per-concept retrieval & snowballing canonical citations across repositories...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    paper_limit = int(config.get("paper_limit", 5))
    retrieval_res = await execute_per_concept_retrieval(
        concepts=concepts,
        limit_per_concept=max(2, paper_limit // len(concepts) + 1),
        enable_snowballing=True
    )
    papers = retrieval_res["papers"]

    yield sse_message("agent_progress", {
        "agent_id": 1,
        "name": "Snowball & Multi-Source Retriever",
        "details": f"Retrieved {len(papers)} unique records (surfaced {retrieval_res['snowballed_count']} canonical papers via citation snowballing).",
        "tokens_used": 0
    })

    yield sse_message("agent_completed", {
        "agent_id": 1,
        "name": "Multi-Source Concept Retriever",
        "tokens_used": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "papers_found": len(papers),
        "concepts_covered": retrieval_res["concept_coverage"],
        "papers": papers
    })
    await asyncio.sleep(0.01)

    # 3. ONNX CONTEXT CACHING & DENSE VECTOR PRE-FILTER
    yield sse_message("agent_active", {
        "agent_id": 3,
        "name": "Semantic Cacher & Distiller",
        "action": "Building FastEmbed dense vector representations for passages...",
        "status": "active"
    })
    agent1_compat = {"papers": papers, "tokens_used": 0}
    agent3_res = run_agent3_context_cacher(agent1_compat)

    yield sse_message("agent_completed", {
        "agent_id": 3,
        "name": "Semantic Cacher & Distiller",
        "tokens_used": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_sentences": agent3_res.get("total_cached_sentences", 0)
    })
    await asyncio.sleep(0.01)

    # 4. SYNTHESIS DRAFTER (Agent 2 LLM Call)
    yield sse_message("agent_active", {
        "agent_id": 2,
        "name": "The Drafter",
        "action": "Synthesizing comparative monograph across sub-concepts with embedded claims (LLM Call 1/2)...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    disable_fallback = bool(config.get("disable_fallback", True))
    disable_fallback_agent2 = bool(config.get("disable_fallback_agent2", disable_fallback))
    disable_fallback_agent4 = bool(config.get("disable_fallback_agent4", disable_fallback))

    agent2_res = await run_agent2_the_drafter(
        user_query,
        agent1_compat,
        provider=config.get("provider_agent2", "auto"),
        api_key=config.get("gemini_key"),
        anthropic_key=config.get("anthropic_key"),
        openai_key=config.get("openai_key"),
        disable_fallback=disable_fallback_agent2
    )

    a2_prompt = agent2_res.get("prompt_tokens") or round(agent2_res["tokens_used"] * 0.6)
    a2_comp = agent2_res.get("completion_tokens") or (agent2_res["tokens_used"] - a2_prompt)
    
    yield sse_message("agent_completed", {
        "agent_id": 2,
        "name": "The Drafter",
        "tokens_used": agent2_res["tokens_used"],
        "prompt_tokens": a2_prompt,
        "completion_tokens": a2_comp,
        "claims_count": len(agent2_res.get("claims", []))
    })
    await asyncio.sleep(0.01)

    # 5. TIER 1 PASSAGE-LEVEL FULL-TEXT VERIFICATION & 3-WAY VERDICTS (0 Tokens)
    yield sse_message("agent_active", {
        "agent_id": 4,
        "name": "Passage Verifier & 3-Way Auditor",
        "action": "Auditing claims against 250-word passages and verifying exact numeric quantities (0 Tokens)...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    raw_claims = agent2_res.get("claims", [])
    passage_eval = verify_all_claims_depth(raw_claims, papers)
    evaluated_claims = passage_eval["evaluated_claims"]
    verdict_summary = passage_eval["verdict_summary"]

    yield sse_message("agent_progress", {
        "agent_id": 4,
        "name": "Passage Verifier & 3-Way Auditor",
        "details": f"Audited {len(raw_claims)} claims across {passage_eval['total_chunks_inspected']} passages. Supported: {verdict_summary['SUPPORTED']}, Contradicted: {verdict_summary['CONTRADICTED']}, Not Found in Checked Text: {verdict_summary['NOT_FOUND_IN_CHECKED_TEXT']} (Exact Numeric Matches: {passage_eval['exact_matches_count']}).",
        "tokens_used": 0
    })

    # 6. SEMANTIC REVIEW & FINAL DOSSIER SYNTHESIS (Agent 4 LLM Call)
    yield sse_message("agent_active", {
        "agent_id": 4,
        "name": "Fact-Checker & Synthesizer",
        "action": "Finalizing executive monograph and cross-examining borderline claims (LLM Call 2/2)...",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    resolved_a4_prov = config.get("provider_agent4", "auto")
    agent4_res = await run_agent4_fact_checker_synthesizer(
        user_query,
        agent1_compat,
        agent2_res,
        agent3_res,
        provider=resolved_a4_prov,
        api_key=config.get("gemini_key"),
        anthropic_key=config.get("anthropic_key"),
        openai_key=config.get("openai_key"),
        disable_fallback=disable_fallback_agent4
    )

    a4_used = agent4_res.get("tokens_used", 0)
    a4_prompt = agent4_res.get("prompt_tokens") or round(a4_used * 0.6)
    a4_comp = agent4_res.get("completion_tokens") or max(0, a4_used - a4_prompt)

    yield sse_message("agent_completed", {
        "agent_id": 4,
        "name": "Fact-Checker & Synthesizer",
        "tokens_used": a4_used,
        "prompt_tokens": a4_prompt,
        "completion_tokens": a4_comp
    })
    await asyncio.sleep(0.01)

    # 7. COMPOSE ENHANCED V5 DOSSIER
    elapsed = round(time.time() - start_time, 2)
    total_tokens = agent2_res["tokens_used"] + a4_used
    
    # Merge evaluated claims with passage verifications
    # If passage verifier found an exact match or 3-way verdict, preserve it
    final_claims_map = {c.get("claim", ""): c for c in evaluated_claims}
    merged_claims = []
    for c4 in agent4_res.get("evaluated_claims", []):
        c_text = c4.get("claim", "")
        if c_text in final_claims_map:
            p_val = final_claims_map[c_text]
            # Augment with 3-way verdict and scope
            c4["verdict_3way"] = p_val["verdict"]
            c4["scope_checked"] = p_val["scope_checked"]
            c4["exact_match_verified"] = p_val.get("exact_match_verified", False)
            c4["confidence_category"] = p_val.get("confidence_category", "MODERATE_CONFIDENCE")
            c4["supporting_passage"] = p_val.get("supporting_passage", "")
            # Sync status with 3-way verdict
            if p_val["verdict"] == "CONTRADICTED":
                c4["status"] = "debunked"
            elif p_val["verdict"] == "NOT_FOUND_IN_CHECKED_TEXT":
                c4["status"] = "unverified"
        merged_claims.append(c4)

    # Format structured citations
    citations = []
    for p in papers:
        citations.append({
            "paper_id": p.get("id"),
            "paper_idx": p.get("paper_idx"),
            "title": p.get("title"),
            "authors": p.get("authors", []),
            "year": p.get("year"),
            "venue": p.get("venue"),
            "doi": p.get("doi"),
            "url": p.get("url"),
            "is_canonical": p.get("is_canonical", False),
            "version_status": p.get("version_status", "published"),
            "concept_tags": p.get("concept_tags", [])
        })

    final_payload = {
        "run_id": run_id,
        "query": user_query,
        "elapsed_seconds": elapsed,
        "architecture": "system_v5",
        "pipeline_engine": "v5.0_deep_verification",
        "token_usage": {
            "total_tokens": total_tokens,
            "prompt_tokens": a2_prompt + a4_prompt,
            "completion_tokens": a2_comp + a4_comp,
            "llm_calls_count": 2,
            "llm_budget_limit": 2,
            "breakdown": {
                "agent1_concept_retriever": 0,
                "agent2_drafter": agent2_res["tokens_used"],
                "agent3_cacher": 0,
                "passage_verifier": 0,
                "agent4_fact_checker": a4_used
            }
        },
        "quick_answer": agent4_res.get("quick_answer") or agent2_res.get("quick_answer", ""),
        "executive_summary": agent4_res.get("executive_summary") or agent2_res.get("executive_summary", ""),
        "concepts_analyzed": concepts,
        "concept_coverage": retrieval_res["concept_coverage"],
        "snowballed_canonical_count": retrieval_res["snowballed_count"],
        "dossier_sections": agent4_res.get("dossier_sections") or agent2_res.get("sections", []),
        "evaluated_claims": merged_claims,
        "verdict_summary": verdict_summary,
        "verification_depth": {
            "full_text_papers": passage_eval["full_text_papers_count"],
            "abstract_papers": passage_eval["abstract_papers_count"],
            "total_passages_inspected": passage_eval["total_chunks_inspected"],
            "exact_numeric_matches": passage_eval["exact_matches_count"]
        },
        "citations": citations
    }

    # Apply HTML and math post-processor
    final_payload = post_process_dossier(final_payload, papers)

    # Persist run to SQLite history
    try:
        log_pipeline_run(user_query, final_payload, elapsed, total_tokens)
    except Exception as db_err:
        logger.warning(f"Could not persist run: {db_err}")

    yield sse_message("pipeline_complete", final_payload)
    await asyncio.sleep(0.01)
