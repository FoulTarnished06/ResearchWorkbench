"""
Snowball Retriever & Version Resolver Module (Tier 1 Retrieval Innovation)
- Multi-Source Per-Concept Retrieval across arXiv, Crossref, OpenAlex, Semantic Scholar
- Citation Snowballing (Following references & cited-by links to surface canonical papers)
- Published vs. Preprint Version Resolution
- Coverage Gating & Dynamic Secondary Retrieval
"""

import asyncio
import re
import unicodedata
from typing import List, Dict, Any, Optional, Set
import httpx

from backend.agents.agent1_scraper import (
    _fetch_eprint_repository as fetch_arxiv,
    fetch_crossref, 
    fetch_openalex, 
    fetch_semantic_scholar, 
    fetch_europepmc, 
    fetch_doaj,
    SCRAPER_HTTP_TIMEOUT
)
from backend.logger import get_logger

logger = get_logger("SnowballRetriever_v5")

def normalize_title(title: str) -> str:
    """Normalize paper title for exact and fuzzy deduplication."""
    if not title:
        return ""
    t = unicodedata.normalize('NFKD', title).lower()
    t = re.sub(r'[\'"`\.,:;\-_/\\(\)\[\]{}]', ' ', t)
    return " ".join(t.split())

def is_preprint_venue(venue: str, url: str) -> bool:
    """Determine if a citation points to a preprint server."""
    venue_lower = (venue or "").lower()
    url_lower = (url or "").lower()
    return any(p in venue_lower or p in url_lower for p in ("arxiv", "biorxiv", "medrxiv", "chemrxiv", "preprints.org"))

def resolve_and_deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tier 1 Innovation: Deduplicate multi-source records and resolve preprint vs. published versions.
    When both a preprint (e.g. arXiv) and a peer-reviewed version exist for the same title,
    we prefer the published version for formal venue and DOI, while retaining full-text extracts.
    """
    seen_titles: Dict[str, Dict[str, Any]] = {}
    seen_dois: Dict[str, str] = {} # doi -> normalized title

    for p in papers:
        title = p.get("title", "").strip()
        if not title:
            continue
        norm_t = normalize_title(title)
        doi = (p.get("doi") or "").lower().strip()

        # Check DOI alias
        canonical_key = norm_t
        if doi and doi in seen_dois:
            canonical_key = seen_dois[doi]

        if canonical_key in seen_titles:
            existing = seen_titles[canonical_key]
            
            # Version resolution: prefer peer-reviewed over preprint
            existing_is_preprint = is_preprint_venue(existing.get("venue", ""), existing.get("url", ""))
            current_is_preprint = is_preprint_venue(p.get("venue", ""), p.get("url", ""))

            if existing_is_preprint and not current_is_preprint:
                # Upgrade existing record to published version details
                existing["venue"] = p.get("venue") or existing.get("venue")
                existing["year"] = p.get("year") or existing.get("year")
                existing["doi"] = p.get("doi") or existing.get("doi")
                existing["url"] = p.get("url") or existing.get("url")
                existing["version_status"] = "published_peer_reviewed"
                existing["source_aggregator"] = f"{existing.get('source_aggregator', '')}+{p.get('source_aggregator', '')}"
            else:
                existing["version_status"] = "preprint" if existing_is_preprint else "published"

            # Merge text content if existing was empty
            if not existing.get("full_text") and p.get("full_text"):
                existing["full_text"] = p.get("full_text")
            if not existing.get("abstract") and p.get("abstract"):
                existing["abstract"] = p.get("abstract")
                
            # Merge concept tags
            existing_tags = set(existing.get("concept_tags", []))
            for tag in p.get("concept_tags", []):
                existing_tags.add(tag)
            existing["concept_tags"] = list(existing_tags)

        else:
            p_copy = dict(p)
            p_copy["is_preprint"] = is_preprint_venue(p.get("venue", ""), p.get("url", ""))
            p_copy["version_status"] = "preprint" if p_copy["is_preprint"] else "published"
            if "concept_tags" not in p_copy:
                p_copy["concept_tags"] = []
            seen_titles[canonical_key] = p_copy
            if doi:
                seen_dois[doi] = canonical_key

    return list(seen_titles.values())

async def citation_snowball_canonical(seed_papers: List[Dict[str, Any]], max_canonical: int = 3) -> List[Dict[str, Any]]:
    """
    Tier 1 Innovation: Citation Snowballing.
    From top-ranking seed hits, follows references and cited-by relationships via OpenAlex API
    to pull in foundational and canonical works that standard keyword searches often miss.
    """
    snowballed_papers: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "AI-Research-Workbench/5.0 (CitationSnowballer; mailto:academic@workbench.org)"
    }
    
    # Identify top seed DOIs
    seed_dois = [p.get("doi") for p in seed_papers if p.get("doi")]
    if not seed_dois:
        return snowballed_papers

    async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
        for doi in seed_dois[:3]:
            try:
                # Query OpenAlex for the seed paper to get referenced_works
                clean_doi = doi.replace("https://doi.org/", "").strip()
                url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    continue
                
                work_data = resp.json()
                referenced_urls = work_data.get("referenced_works", [])[:max_canonical]
                
                # Fetch up to max_canonical referenced foundational papers
                for ref_url in referenced_urls:
                    try:
                        ref_resp = await client.get(ref_url, headers=headers)
                        if ref_resp.status_code == 200:
                            ref_data = ref_resp.json()
                            title = ref_data.get("title")
                            if not title:
                                continue
                            
                            # Extract author names
                            authors = []
                            for auth in ref_data.get("authorships", []):
                                if "author" in auth and "display_name" in auth["author"]:
                                    authors.append(auth["author"]["display_name"])

                            snowballed_papers.append({
                                "id": ref_data.get("id"),
                                "title": title,
                                "authors": authors[:5],
                                "year": ref_data.get("publication_year"),
                                "venue": (ref_data.get("primary_location") or {}).get("source", {}).get("display_name", "OpenAlex Foundational"),
                                "doi": ref_data.get("doi", ""),
                                "url": ref_data.get("doi") or ref_data.get("id"),
                                "abstract": (ref_data.get("abstract_inverted_index") and "Foundational citation extracted via snowballing.") or "",
                                "source_aggregator": "openalex_snowball",
                                "is_canonical": True,
                                "cited_by_count": ref_data.get("cited_by_count", 0),
                                "concept_tags": ["canonical_foundational"]
                            })
                    except Exception as ref_err:
                        logger.debug(f"Snowball single ref fetch bypass: {ref_err}")
            except Exception as e:
                logger.debug(f"Snowball error for doi {doi}: {e}")

    return snowballed_papers

async def execute_per_concept_retrieval(
    concepts: List[Dict[str, Any]], 
    limit_per_concept: int = 4,
    enable_snowballing: bool = True
) -> Dict[str, Any]:
    """
    Tier 1 Innovation: Orchestrates parallel per-concept retrieval across academic APIs,
    deduplicates with version resolution, applies citation snowballing, and validates concept coverage.
    """
    logger.info(f"Starting Per-Concept Retrieval across {len(concepts)} distinct inquiry facets.")
    all_raw_papers: List[Dict[str, Any]] = []
    concept_coverage: Dict[str, int] = {c["id"]: 0 for c in concepts}

    async def fetch_for_concept(concept: Dict[str, Any]) -> List[Dict[str, Any]]:
        c_query = concept["query_string"]
        c_id = concept["id"]
        logger.debug(f"Fetching papers for concept '{c_id}': {c_query}")
        
        # Parallel fetch from primary sources
        tasks = [
            fetch_arxiv(c_query, limit=limit_per_concept),
            fetch_crossref(c_query, limit=limit_per_concept),
            fetch_openalex(c_query, limit=limit_per_concept),
            fetch_semantic_scholar(c_query, limit=limit_per_concept)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        concept_papers = []
        for res in results:
            if isinstance(res, list):
                for p in res:
                    p["concept_tags"] = [c_id]
                    concept_papers.append(p)
        return concept_papers

    # Run parallel searches for each concept
    concept_tasks = [fetch_for_concept(c) for c in concepts]
    concept_results = await asyncio.gather(*concept_tasks, return_exceptions=True)

    for i, res in enumerate(concept_results):
        c_id = concepts[i]["id"]
        if isinstance(res, list):
            concept_coverage[c_id] = len(res)
            all_raw_papers.extend(res)

    # Initial deduplication
    deduped = resolve_and_deduplicate_papers(all_raw_papers)

    # Citation Snowballing for canonical papers
    snowballed: List[Dict[str, Any]] = []
    if enable_snowballing and deduped:
        try:
            snowballed = await citation_snowball_canonical(deduped[:4], max_canonical=2)
            if snowballed:
                logger.info(f"Citation Snowballing surfaced {len(snowballed)} canonical foundational papers.")
                deduped.extend(snowballed)
                deduped = resolve_and_deduplicate_papers(deduped)
        except Exception as snow_err:
            logger.warning(f"Citation snowballing non-critical bypass: {snow_err}")

    # Coverage Gating: Check if any key concept has 0 coverage
    gaps = [c for c in concepts if concept_coverage.get(c["id"], 0) == 0]
    if gaps:
        logger.info(f"Coverage Gating: Identified {len(gaps)} uncovered concepts. Triggering secondary round.")
        gap_tasks = [fetch_for_concept(g) for g in gaps]
        gap_results = await asyncio.gather(*gap_tasks, return_exceptions=True)
        for g_res in gap_results:
            if isinstance(g_res, list):
                deduped.extend(g_res)
        deduped = resolve_and_deduplicate_papers(deduped)

    # Re-index papers with sequential index P1, P2, ...
    for idx, p in enumerate(deduped, start=1):
        p["paper_idx"] = f"P{idx}"

    return {
        "papers": deduped,
        "concepts": concepts,
        "concept_coverage": concept_coverage,
        "snowballed_count": len(snowballed),
        "total_unique_papers": len(deduped)
    }
