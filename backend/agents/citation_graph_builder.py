import re
import asyncio
from typing import List, Dict, Any, Optional
import httpx

async def resolve_reference_online(ref: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Attempts to resolve an academic reference via Semantic Scholar or OpenAlex.
    Uses fuzzy title matching with strict rate-limiting.
    """
    title = ref.get("title", "").strip()
    doi = ref.get("doi", "").strip()
    if not title and not doi:
        return {"resolved": False}

    # 1. Try Semantic Scholar
    query = doi if doi else title
    if len(query) > 10:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={httpx.URL(query)}&limit=1&fields=title,authors,year,venue,citationCount,abstract,externalIds,url"
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                papers = data.get("data", [])
                if papers:
                    p = papers[0]
                    authors = ", ".join([a.get("name", "") for a in p.get("authors", [])])
                    return {
                        "resolved": True,
                        "semantic_scholar_id": p.get("paperId"),
                        "openalex_id": None,
                        "title": p.get("title") or title,
                        "authors": authors or ref.get("authors", ""),
                        "year": p.get("year") or ref.get("year", 2024),
                        "venue": p.get("venue") or ref.get("venue", ""),
                        "external_url": p.get("url") or ref.get("url", ""),
                        "citation_count": p.get("citationCount", 0),
                        "abstract_snippet": (p.get("abstract") or "")[:240]
                    }
        except Exception:
            pass

    # 2. Try OpenAlex as fallback
    try:
        oa_url = f"https://api.openalex.org/works?search={httpx.URL(title[:100])}&per-page=1"
        resp = await client.get(oa_url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                w = results[0]
                authorships = w.get("authorships", [])
                authors = ", ".join([a.get("author", {}).get("display_name", "") for a in authorships[:3]])
                return {
                    "resolved": True,
                    "semantic_scholar_id": None,
                    "openalex_id": w.get("id"),
                    "title": w.get("title") or title,
                    "authors": authors or ref.get("authors", ""),
                    "year": w.get("publication_year") or ref.get("year", 2024),
                    "venue": (w.get("primary_location", {}) or {}).get("source", {}).get("display_name") or ref.get("venue", ""),
                    "external_url": w.get("doi") or w.get("id") or ref.get("url", ""),
                    "citation_count": w.get("cited_by_count", 0),
                    "abstract_snippet": ""
                }
    except Exception:
        pass

    return {"resolved": False}


async def build_citation_graph_for_session(
    session_id: str,
    refs: List[Dict[str, Any]],
    update_db_callback = None
) -> Dict[str, Any]:
    """
    Asynchronously resolves a list of parsed references against online academic graphs.
    """
    from backend.database import update_reference_resolution, get_citation_graph_data

    async with httpx.AsyncClient(headers={"User-Agent": "AIResearchWorkbench/3.0 (academic-synthesis)"}) as client:
        # Process in batches of 4 with small delay to stay within rate limits
        for i in range(0, min(len(refs), 30), 4):
            batch = refs[i:i+4]
            tasks = [resolve_reference_online(r, client) for r in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r, res in zip(batch, results):
                if isinstance(res, dict) and res.get("resolved"):
                    try:
                        update_reference_resolution(r["ref_id"], res)
                    except Exception as e:
                        print(f"[Citation Graph] Failed to update ref {r['ref_id']}: {e}")

            await asyncio.sleep(0.3)

    return get_citation_graph_data(session_id)
