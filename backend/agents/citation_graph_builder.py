import os
import re
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from backend.logger import get_logger

logger = get_logger("CitationGraphBuilder")

# Configurable HTTP timeout for citation lookups (seconds) (FIX-10)
CITATION_HTTP_TIMEOUT = float(os.environ.get("CITATION_HTTP_TIMEOUT", "5.0"))

async def resolve_reference_online(ref: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Attempts to resolve an academic reference via Semantic Scholar or OpenAlex.
    Uses proper parameter encoding and structured error handling (SEC-12, BUG-09).
    """
    title = ref.get("title", "").strip()
    doi = ref.get("doi", "").strip()
    if not title and not doi:
        return {"resolved": False}

    # 1. Try Semantic Scholar
    query = doi if doi else title
    if len(query) > 10:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": 1,
                "fields": "title,authors,year,venue,citationCount,abstract,externalIds,url"
            }
            resp = await client.get(url, params=params, timeout=CITATION_HTTP_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                papers = data.get("data", [])
                if papers:
                    p = papers[0]
                    authors = ", ".join([a.get("name", "") for a in p.get("authors", [])])
                    ext_ids = p.get("externalIds") or {}
                    p_doi = ext_ids.get("DOI") or doi
                    ext_url = f"https://doi.org/{p_doi}" if p_doi else (p.get("url") or ref.get("url", ""))
                    return {
                        "resolved": True,
                        "semantic_scholar_id": p.get("paperId"),
                        "openalex_id": None,
                        "title": p.get("title") or title,
                        "authors": authors or ref.get("authors", ""),
                        "year": p.get("year") or ref.get("year"),
                        "venue": p.get("venue") or ref.get("venue", ""),
                        "doi": p_doi,
                        "external_url": ext_url,
                        "citation_count": p.get("citationCount", 0),
                        "abstract_snippet": (p.get("abstract") or "")[:240]
                    }
        except Exception as e:
            logger.debug(f"Semantic Scholar lookup exception for '{query[:30]}': {e}")

    # 2. Try OpenAlex as fallback
    try:
        oa_url = "https://api.openalex.org/works"
        params = {
            "search": title[:100],
            "per-page": 1
        }
        resp = await client.get(oa_url, params=params, timeout=CITATION_HTTP_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                w = results[0]
                authorships = w.get("authorships", [])
                authors = ", ".join([a.get("author", {}).get("display_name", "") for a in authorships[:3]])
                w_doi = w.get("doi") or doi
                return {
                    "resolved": True,
                    "semantic_scholar_id": None,
                    "openalex_id": w.get("id"),
                    "title": w.get("title") or title,
                    "authors": authors or ref.get("authors", ""),
                    "year": w.get("publication_year") or ref.get("year"),
                    "venue": (w.get("primary_location", {}) or {}).get("source", {}).get("display_name") or ref.get("venue", ""),
                    "doi": w_doi,
                    "external_url": w_doi if w_doi else (w.get("id") or ref.get("url", "")),
                    "citation_count": w.get("cited_by_count", 0),
                    "abstract_snippet": ""
                }
    except Exception as e:
        logger.debug(f"OpenAlex lookup exception for '{title[:30]}': {e}")

    return {"resolved": False}


async def build_citation_graph_for_session(
    session_id: str,
    refs: List[Dict[str, Any]],
    update_db_callback = None
) -> Dict[str, Any]:
    """
    Asynchronously resolves parsed references against online academic graphs.
    Uses non-blocking async threads for database updates (BUG-01).
    """
    from backend.database import update_reference_resolution, get_citation_graph_data

    async with httpx.AsyncClient(headers={"User-Agent": "AIResearchWorkbench/3.0 (academic-synthesis)"}) as client:
        for i in range(0, min(len(refs), 30), 4):
            batch = refs[i:i+4]
            tasks = [resolve_reference_online(r, client) for r in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Serialize DB writes to avoid SQLite concurrent write contention (FIX-02)
            resolved_updates = []
            for r, res in zip(batch, results):
                if isinstance(res, dict) and res.get("resolved"):
                    resolved_updates.append((r["ref_id"], res))

            if resolved_updates:
                def _batch_update(updates):
                    for ref_id, res_data in updates:
                        update_reference_resolution(ref_id, res_data)

                try:
                    await asyncio.to_thread(_batch_update, resolved_updates)
                except Exception as e:
                    logger.error(f"Failed batch DB update for {len(resolved_updates)} refs: {e}")

            await asyncio.sleep(0.3)

    return await asyncio.to_thread(get_citation_graph_data, session_id)
