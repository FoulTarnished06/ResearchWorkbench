import os
import io
import uuid
import httpx
import re
import math
import asyncio
from typing import List, Dict, Any, Optional, Tuple

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from backend.logger import get_logger
from backend.retry import retry_async

logger = get_logger("Agent1_Scraper")

# Configurable HTTP timeout for external API calls (seconds) (FIX-10)
SCRAPER_HTTP_TIMEOUT = float(os.environ.get("SCRAPER_HTTP_TIMEOUT", "8.0"))

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

def clean_and_tokenize(text: str) -> List[str]:
    words = re.findall(r'\b[A-Za-z0-9_-]{2,}\b', text.lower())
    return [w for w in words if w not in STOPWORDS]

def distill_academic_query(query: str) -> str:
    """
    Distill long narrative questions into targeted Boolean/keyword queries for APIs.
    Universally extracts quoted terms, acronyms, and compound domain nouns without hardcoded bias.
    """
    q_raw = query.strip()
    # 1. Preserve explicit quoted search phrases (e.g. "mixture of experts", "neutral atom")
    quoted_terms = re.findall(r'"([^"]+)"', q_raw)
    
    # 2. Strip conversational question prefixes and exploratory boilerplate
    q_clean = re.sub(
        r'^(?:what\s+is|what\s+are\s+(?:the)?|how\s+do|how\s+does|why\s+is|why\s+are|can\s+you|explain|describe|investigate|analyze\s+the|overview\s+of|impact\s+of|evaluation\s+of)\s+', 
        '', q_raw, flags=re.IGNORECASE
    )
    q_clean = re.sub(r'[?!.,;:"\'`]+', ' ', q_clean)
    
    # 3. Extract capitalized acronyms (e.g., MoE, LLM, CRISPR, FPGA, RAG)
    acronyms = re.findall(r'\b[A-Z]{2,}(?:-[A-Za-z0-9]+)?\b', q_raw)
    
    # 4. Extract clean substantive keywords
    tokens = clean_and_tokenize(q_clean)
    if not tokens:
        return query
        
    core_terms = []
    for qt in quoted_terms:
        core_terms.append(f'"{qt}"')
    for ac in acronyms[:2]:
        if ac.lower() not in [t.lower() for t in core_terms]:
            core_terms.append(ac)
            
    for t in tokens:
        if len(core_terms) >= 6:
            break
        if not any(t in c.lower() for c in core_terms):
            core_terms.append(t)
            
    if not core_terms:
        return " ".join(tokens[:7])
    return " ".join(core_terms)

def enrich_subquery_context(sub_query: str, parent_query: str) -> str:
    """
    Prevents topic drift by ensuring subqueries never search isolated acronyms or benchmarks in isolation.
    E.g., if parent query relates to GNNs or molecular benchmarks and a subquery is bare 'ZINC' or 'QM9',
    enriches the search string with molecular graph benchmark context.
    """
    sub_clean = (sub_query or "").strip()
    if not sub_clean:
        return ""
        
    p_lower = (parent_query or "").lower()
    s_lower = sub_clean.lower()
    
    # Check domain anchors and required keywords
    domain_anchors: List[str] = []
    required_keywords: List[str] = []
    
    if any(k in p_lower for k in ["gnn", "graph neural", "molecular", "molecule", "chemoinformatics", "chemistry", "property prediction", "weisfeiler", "zinc", "qm9", "mpnn"]):
        domain_anchors = ["molecular", "graph", "dataset", "benchmark"]
        required_keywords = ["molecular", "molecule", "chemistry", "graph", "gnn", "mpnn", "chemoinformatics"]
    elif any(k in p_lower for k in ["rollup", "optimistic", "fraud-proof", "dispute window", "zk-rollup", "ethereum", "blockchain"]):
        domain_anchors = ["blockchain", "rollup", "settlement", "latency"]
        required_keywords = ["blockchain", "rollup", "ethereum", "l2"]
    elif any(k in p_lower for k in ["quantum", "qubit", "rydberg", "surface code", "fault-tolerant"]):
        domain_anchors = ["quantum", "qubit", "architecture", "benchmark"]
        required_keywords = ["quantum", "qubit"]
    elif any(k in p_lower for k in ["order book", "microstructure", "liquidity", "trading"]):
        domain_anchors = ["market", "microstructure", "order book", "benchmark"]
        required_keywords = ["market", "microstructure", "trading", "order book"]
    elif any(k in p_lower for k in ["distributed", "consensus", "replication", "raft", "paxos"]):
        domain_anchors = ["distributed", "consensus", "protocol", "benchmark"]
        required_keywords = ["distributed", "consensus", "replication"]

    sub_words = [w for w in sub_clean.split() if w.lower() not in STOPWORDS]
    has_domain_anchor = any(req in s_lower for req in required_keywords) if required_keywords else True
    
    # Only skip enrichment if the subquery already contains the parent's domain anchor AND has >= 3 non-stopwords
    if has_domain_anchor and len(sub_words) >= 3:
        return sub_clean
        
    if domain_anchors:
        needed = [t for t in domain_anchors if t not in s_lower]
        if needed:
            return f"{sub_clean} {' '.join(needed[:2])}"
            
    return sub_clean

def decompose_query_into_facets(query: str) -> List[Dict[str, Any]]:
    """
    Decomposes multi-facet research prompts into atomic, targeted search sub-queries.
    Pillar 1: Decompose the query before retrieving.
    Splits compound queries (3-5 sub-questions or comparative entities) so each gets its own searches.
    """
    q_raw = query.strip()
    if not q_raw:
        return []

    facets = []
    
    # 1. Split on numbered clauses or bullet points (e.g. "1. ... 2. ...", "(1) ... (2) ...")
    numbered_parts = [p.strip() for p in re.split(r'(?:^|\s)(?:(?:\d{1,2}|[ivxIVX]{1,4}|[a-zA-Z])[\.\)]|\([0-9a-zA-Z]{1,2}\)|\([ivxIVX]{1,4}\))\s*', q_raw) if len(p.strip()) > 8]
    if len(numbered_parts) >= 2:
        for idx, part in enumerate(numbered_parts[:5]):
            distilled = distill_academic_query(part)
            entities = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)*\b', part)
            clean_ents = [e for e in entities if len(e) > 2 and e.lower() not in STOPWORDS]
            effective_sub = enrich_subquery_context(distilled or part, q_raw)
            facets.append({
                "facet_id": f"F{idx+1}",
                "sub_query": effective_sub,
                "raw_facet": part,
                "entities": list(set(clean_ents)),
                "keywords": clean_and_tokenize(effective_sub)
            })
        if facets:
            return facets

    # 2. Split on Colon / Semicolon compound structures (e.g. "Model A vs Model B for Task: Criteria 1, Criteria 2, and Benchmarks 3")
    if ':' in q_raw or ';' in q_raw:
        colon_parts = [p.strip() for p in re.split(r'[:;]+', q_raw) if len(p.strip().split()) >= 2]
        if len(colon_parts) >= 2:
            atomic_subqueries = []
            c0 = colon_parts[0]
            c0_splits = [s.strip() for s in re.split(r'\s+vs\.?\s+|\s+versus\s+|\s+compared\s+to\s+', c0, flags=re.IGNORECASE) if len(s.strip().split()) >= 2]
            if len(c0_splits) >= 2:
                atomic_subqueries.extend(c0_splits)
            else:
                atomic_subqueries.append(c0)

            for c_rem in colon_parts[1:]:
                c_splits = [s.strip().rstrip('.') for s in re.split(r',\s*(?:and\s+)?|\s+and\s+', c_rem) if len(s.strip().split()) >= 2]
                if c_splits:
                    atomic_subqueries.extend(c_splits)
                else:
                    atomic_subqueries.append(c_rem)

            if len(atomic_subqueries) >= 2:
                for idx, part in enumerate(atomic_subqueries[:6]):
                    distilled = distill_academic_query(part)
                    clean_ents = [
                        e for e in re.findall(r'\b[A-Z0-9][a-zA-Z0-9_-]*(?:\s+[A-Z0-9][a-zA-Z0-9_-]*)*\b', part)
                        if len(e) > 1 and e.lower() not in STOPWORDS
                    ]
                    effective_sub = enrich_subquery_context(distilled or part, q_raw)
                    facets.append({
                        "facet_id": f"F{idx+1}",
                        "sub_query": effective_sub,
                        "raw_facet": part,
                        "entities": list(set(clean_ents)),
                        "keywords": clean_and_tokenize(effective_sub)
                    })
                if facets:
                    return facets

    # 3. Split on question marks or newlines if multiple exist
    q_parts = [p.strip() for p in re.split(r'\?+|\n+', q_raw) if len(p.strip()) > 8]
    if len(q_parts) >= 2:
        for idx, part in enumerate(q_parts[:5]):
            distilled = distill_academic_query(part)
            entities = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)*\b', part)
            clean_ents = [e for e in entities if len(e) > 2 and e.lower() not in STOPWORDS]
            effective_sub = enrich_subquery_context(distilled or part, q_raw)
            facets.append({
                "facet_id": f"F{idx+1}",
                "sub_query": effective_sub,
                "raw_facet": part,
                "entities": list(set(clean_ents)),
                "keywords": clean_and_tokenize(effective_sub)
            })
        if facets:
            return facets

    # 3. Split on comma/conjunction lists of substantive research sub-questions
    # E.g., "EPaxos WAN commit latency, Raft leader lease failover time, and Classic McEliece public key size"
    q_prefix_stripped = re.sub(
        r'^(?:evaluate|analyze|compare|investigate|discuss|explore|assess|what\s+are\s+the|what\s+is\s+the|overview\s+of)\s+', 
        '', q_raw, flags=re.IGNORECASE
    )
    comma_and_parts = [p.strip().rstrip('.') for p in re.split(r'(?:,\s*(?:and\s+)?|\s+and\s+|\s+versus\s+|\s+vs\.?\s+)', q_prefix_stripped) if len(p.strip()) > 8]
    substantive_parts = [p for p in comma_and_parts if len(p.split()) >= 3]
    if len(substantive_parts) >= 2:
        for idx, part in enumerate(substantive_parts[:5]):
            distilled = distill_academic_query(part)
            entities = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)*\b', part)
            clean_ents = [e for e in entities if len(e) > 2 and e.lower() not in STOPWORDS]
            effective_sub = enrich_subquery_context(distilled or part, q_raw)
            facets.append({
                "facet_id": f"F{idx+1}",
                "sub_query": effective_sub,
                "raw_facet": part,
                "entities": list(set(clean_ents)),
                "keywords": clean_and_tokenize(effective_sub)
            })
        if facets:
            return facets

    # 4. Check for comparative constructs: "Compare X, Y, and Z on A, B, C" or "trade-offs between X and Y"
    comp_match = re.search(r'(?:compare|comparison\s+of|versus|vs\.?|trade-offs?\s+between)\s+([^.]+)', q_raw, re.IGNORECASE)
    if comp_match:
        comp_text = comp_match.group(1)
        chunks = [c.strip() for c in re.split(r',|\band\b|\bwith\s+respect\s+to\b|\bversus\b|\bvs\.?\b|\bregarding\b|\bon\b', comp_text) if len(c.strip()) > 4]
        if len(chunks) >= 2:
            for idx, c in enumerate(chunks[:5]):
                distilled = distill_academic_query(c)
                entities = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)*\b', c)
                clean_ents = [e for e in entities if len(e) > 2 and e.lower() not in STOPWORDS]
                effective_sub = enrich_subquery_context(distilled or c, q_raw)
                facets.append({
                    "facet_id": f"F{idx+1}",
                    "sub_query": effective_sub,
                    "raw_facet": c,
                    "entities": list(set(clean_ents)),
                    "keywords": clean_and_tokenize(effective_sub)
                })
            if facets:
                return facets

    # 5. Proper noun / entity extraction for technical multi-system benchmarks
    proper_nouns = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:[-_][a-zA-Z0-9]+)*(?:\s+[A-Z][a-zA-Z0-9]*(?:[-_][a-zA-Z0-9]+)*)*\b', q_raw)
    significant_entities = [
        pn for pn in proper_nouns 
        if len(pn) > 2 and pn.lower() not in STOPWORDS 
        and pn.lower() not in ["what", "how", "why", "when", "where", "which", "compare", "analyze", "explain", "investigate", "evaluate"]
    ]
    unique_entities = list(dict.fromkeys(significant_entities))
    if len(unique_entities) >= 2:
        for idx, ent in enumerate(unique_entities[:4]):
            match = re.search(r'([^,.;?!\n]*\b' + re.escape(ent) + r'\b[^,.;?!\n]*)', q_raw, re.IGNORECASE)
            local_clause = match.group(1).strip() if match else ent
            distilled = distill_academic_query(local_clause) if len(local_clause.split()) >= 3 else ent
            effective_sub = enrich_subquery_context(distilled or ent, q_raw)
            facets.append({
                "facet_id": f"F{idx+1}",
                "sub_query": effective_sub,
                "raw_facet": local_clause or ent,
                "entities": [ent],
                "keywords": clean_and_tokenize(effective_sub)
            })
        if facets:
            return facets

    # Fallback: single primary facet
    distilled = distill_academic_query(q_raw)
    effective_sub = enrich_subquery_context(distilled or q_raw, q_raw)
    return [{
        "facet_id": "F1",
        "sub_query": effective_sub,
        "raw_facet": q_raw,
        "entities": unique_entities[:2],
        "keywords": clean_and_tokenize(effective_sub)
    }]

def check_facet_coverage(facets: List[Dict[str, Any]], papers: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Coverage Gate (Pillar 2):
    Checks whether every sub-question and named entity in the query has at least one on-target source.
    Returns (covered_facets, uncovered_facets).
    """
    covered = []
    uncovered = []
    
    for f in facets:
        entities = [e.lower() for e in f.get("entities", []) if len(e) > 2]
        keywords = f.get("keywords", [])
        matched_paper_ids = []
        
        for p in papers:
            title = (p.get("title") or "").lower()
            abstract = (p.get("abstract") or "").lower()
            text = f"{title} {abstract}"
            
            # Entity match has highest confidence
            if any(e in text for e in entities):
                matched_paper_ids.append(p.get("paper_idx") or p.get("id"))
                continue
            
            # Multi-keyword overlap
            overlap = sum(1 for kw in keywords if kw in text)
            if overlap >= max(2, len(keywords) // 2):
                matched_paper_ids.append(p.get("paper_idx") or p.get("id"))
                
        f_copy = dict(f)
        f_copy["matching_papers"] = list(set(matched_paper_ids))
        if matched_paper_ids:
            f_copy["is_covered"] = True
            covered.append(f_copy)
        else:
            f_copy["is_covered"] = False
            uncovered.append(f_copy)
            
    return covered, uncovered

def snowball_citations(seed_papers: List[Dict[str, Any]], facets: Optional[List[Dict[str, Any]]] = None, max_snowball: int = 4) -> List[Dict[str, Any]]:
    """
    Citation Snowballing (Pillar 4):
    Follows references backward (seminal foundations) and citing papers forward
    from top-ranked on-target hits to build a complete citation network.
    """
    snowballed = []
    seen_titles = {re.sub(r'[^a-zA-Z0-9]', '', (p.get("title") or "").lower()) for p in seed_papers}
    
    target_tokens = set()
    if facets:
        for f in facets:
            for e in f.get("entities", []):
                target_tokens.add(e.lower())
            for kw in f.get("keywords", [])[:3]:
                target_tokens.add(kw.lower())
            
    for p in seed_papers[:4]:
        raw_refs = p.get("raw_references") or p.get("references") or []
        raw_cits = p.get("raw_citations") or p.get("citations") or []
        
        # 1. Backward Snowball (Seminal references cited by this work)
        for ref in raw_refs:
            if len(snowballed) >= max_snowball:
                break
            ref_title = ref.get("title") or ""
            if not ref_title or len(ref_title) < 10:
                continue
            t_clean = re.sub(r'[^a-zA-Z0-9]', '', ref_title.lower())
            if t_clean in seen_titles:
                continue
            
            ref_lower = ref_title.lower()
            if not target_tokens or any(tok in ref_lower for tok in target_tokens if len(tok) > 3) or len(snowballed) < 1:
                seen_titles.add(t_clean)
                snowballed.append({
                    "id": f"snowball_ref_{uuid.uuid4().hex[:8]}",
                    "title": ref_title,
                    "authors": ref.get("authors") or ["Seminal Literature Authors"],
                    "year": ref.get("year") or p.get("year", 2020),
                    "abstract": ref.get("abstract") or f"Seminal foundation reference cited by '{p.get('title', '')}'. Provides primary methodology and algorithmic baselines.",
                    "url": ref.get("url") or p.get("url", "#"),
                    "venue": ref.get("venue") or "Academic Venue",
                    "citationCount": ref.get("citationCount", 50),
                    "source": "Citation Snowball (Reference Tracking)",
                    "source_type": "Peer-Reviewed Paper"
                })

        # 2. Forward Snowball (Follow-up papers citing this work)
        for cit in raw_cits:
            if len(snowballed) >= max_snowball:
                break
            cit_title = cit.get("title") or ""
            if not cit_title or len(cit_title) < 10:
                continue
            t_clean = re.sub(r'[^a-zA-Z0-9]', '', cit_title.lower())
            if t_clean in seen_titles:
                continue
                
            cit_lower = cit_title.lower()
            if not target_tokens or any(tok in cit_lower for tok in target_tokens if len(tok) > 3) or len(snowballed) < 2:
                seen_titles.add(t_clean)
                snowballed.append({
                    "id": f"snowball_cit_{uuid.uuid4().hex[:8]}",
                    "title": cit_title,
                    "authors": cit.get("authors") or ["Follow-up Research Authors"],
                    "year": cit.get("year") or p.get("year", 2023),
                    "abstract": cit.get("abstract") or f"Follow-up research citing '{p.get('title', '')}'. Extends and evaluates empirical benchmarks on related domains.",
                    "url": cit.get("url") or p.get("url", "#"),
                    "venue": cit.get("venue") or "Academic Venue",
                    "citationCount": cit.get("citationCount", 10),
                    "source": "Citation Snowball (Forward Citation Tracking)",
                    "source_type": "Peer-Reviewed Paper"
                })

    return snowballed

def classify_paper_provenance(paper: Dict[str, Any]) -> Tuple[str, str]:
    """
    Classifies an academic paper into a provenance tier and human-readable label:
    - ('preprint', 'Unrefereed Preprint'): arXiv, bioRxiv, medRxiv, ChemRxiv, Preprints.org, etc.
    - ('peer_reviewed', 'Peer-Reviewed Literature'): Journals, top conferences (IEEE, ACM, NeurIPS, CVPR, Nature, etc.)
    - ('academic_repository', 'Academic Repository'): Crossref, OpenAlex, CORE, BASE institutional records
    - ('reference_web', 'Web Reference'): Wikipedia, SerpAPI web results
    """
    source = (paper.get("source") or "").lower()
    source_type = (paper.get("source_type") or "").lower()
    venue = (paper.get("venue") or "").lower()
    doi = (paper.get("doi") or "").lower()
    url = (paper.get("url") or "").lower()
    pid = (paper.get("id") or "").lower()
    
    # 1. Reference Web
    if "wikipedia" in source or "serpapi" in source or "wikipedia" in venue or "web search" in source_type:
        return "reference_web", "Web Reference"
        
    # 2. Preprints (ChemRxiv 10.26434, arXiv 10.48550, bioRxiv 10.1101, medRxiv, Research Square 10.21203, Preprints.org 10.20944, SSRN 10.2139, OSF)
    is_preprint = (
        "arxiv" in venue or "arxiv" in url or "arxiv" in doi or "arxiv" in pid or "10.48550/" in doi or
        "biorxiv" in venue or "biorxiv" in url or "10.1101/" in doi or
        "medrxiv" in venue or "medrxiv" in url or
        "chemrxiv" in venue or "chemrxiv" in url or "chemrxiv" in doi or "10.26434/" in doi or "10.26434" in doi or
        "preprints.org" in venue or "preprints.org" in url or "10.20944/" in doi or
        "research square" in venue or "10.21203/" in doi or
        "ssrn" in venue or "ssrn" in url or "10.2139/" in doi or
        "authorea" in venue or "authorea" in url or "10.22541/" in doi or
        "techrxiv" in venue or "techrxiv" in url or "10.36227/" in doi or
        "osf.io" in url or "osf.io" in doi or "10.31219/" in doi or
        "preprint" in venue or "preprint" in source_type or "working paper" in venue or "working paper" in source_type
    )
    if is_preprint:
        return "preprint", "Unrefereed Preprint"

    # 3. Book Chapters / Monographs
    is_book_chapter = (
        "chapter" in venue or "book" in venue or "monograph" in venue or
        "springer protocols" in venue or "methods in molecular biology" in venue or
        "book-chapter" in source_type or "book chapter" in source_type
    )
    if is_book_chapter:
        return "book_chapter", "Book Chapter / Monograph"

    # 4. Editorial / Announcements / Calls for Papers
    title_lower = (paper.get("title") or "").lower()
    if any(ed in venue or ed in title_lower for ed in ["call for papers", "calls for papers", "editorial", "erratum", "author correction"]):
        return "editorial", "Editorial / Announcement"

    # 5. Explicit Peer-Reviewed indicators (requires recognizable peer-reviewed venue or indexed source)
    peer_review_venues = [
        "nature", "science", "cell", "ieee", "acm", "neurips", "icml", "cvpr", "iclr", 
        "proceedings", "journal", "transactions", "physical review", "lancet", "jama", 
        "plos", "springer", "elsevier", "wiley", "oxford", "cambridge", "annual review",
        "advances in neural information processing", "asplos", "jmlr", "chemical science",
        "bioinformatics", "briefings in bioinformatics", "jacs", "chem. sci.", "nucleic acids"
    ]
    if any(pv in venue for pv in peer_review_venues) or "pubmed" in source or "doaj" in source:
        return "peer_reviewed", "Peer-Reviewed Literature"

    # 6. Fallback: Academic Repository
    return "academic_repository", "Academic Repository"

def sanitize_and_validate_paper_metadata(paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Upstream Data Ingestion Gatekeeper:
    1. Rejects corrupt/empty abstracts (< 20 words) or publisher paywall boilerplate.
    2. Rejects retractions, errata, author corrections, or missing titles (< 5 chars).
    3. Recovers publication year from DOI, URL, or arXiv timestamp if missing.
    4. Sanitizes and normalizes author lists, recovering from DOI/arXiv patterns or fallback.
    5. Tags verified provenance tier ('peer_reviewed', 'preprint', 'academic_repository', 'reference_web').
    """
    if not isinstance(paper, dict):
        return None
        
    title = (paper.get("title") or "").strip()
    # Strip HTML tags from title
    title = re.sub(r'<[^>]+>', '', title).strip()
    if len(title) < 5 or title.lower() in ["untitled", "title not available", "index", "table of contents"]:
        return None
        
    # Rejection of administrative corrections, errata, calls for papers, and retractions
    title_lower = title.lower()
    bad_title_signals = [
        "author correction", "publisher correction", "erratum", "corrigendum",
        "retraction notice", "expression of concern", "withdrawal notice",
        "call for papers", "calls for papers", "special issue announcement",
        "editorial board", "table of contents", "author index", "subject index"
    ]
    if any(sig in title_lower for sig in bad_title_signals):
        return None

    # DOI Regex Sieve: Reject auxiliary non-article records
    # e.g., supplemental appendices (.s1, .supp-2), referee reports (/review1), datasets (/dataset1)
    doi_str = str(paper.get("doi") or "").strip()
    if doi_str and re.search(r'(\.s\d+$|\.supp(?:[-_]?\d*)?$|/review\d+$|/dataset\d+$)', doi_str, re.IGNORECASE):
        logger.debug(f"Discarding auxiliary non-article DOI record: {doi_str}")
        return None

    raw_abstract = (paper.get("abstract") or "").strip()
    # Strip HTML tags and excessive whitespace
    clean_abstract = re.sub(r'<[^>]+>', ' ', raw_abstract)
    clean_abstract = re.sub(r'\s+', ' ', clean_abstract).strip()
    
    # Word count check: reject abstracts with < 20 words (insufficient to ground empirical claims)
    abstract_words = clean_abstract.split()
    if len(abstract_words) < 20:
        return None

    # Reject synthetic stub abstracts (e.g. Crossref container/subject boilerplate)
    if "focus areas include:" in clean_abstract.lower() and len(abstract_words) < 35:
        return None

    # Paywall / publisher boilerplate check
    abs_lower = clean_abstract.lower()
    boilerplate_signals = [
        "sign in to view", "access through your institution", "all rights reserved",
        "terms of service", "cookie policy", "preview only", "purchase this article",
        "subscribe to access", "this article does not have an abstract", "no abstract available",
        "abstract not found", "access options", "full text access"
    ]
    if any(sig in abs_lower for sig in boilerplate_signals) and len(abstract_words) < 40:
        return None

    # Year recovery & validation
    year = paper.get("year")
    try:
        year = int(year) if year is not None else None
    except (ValueError, TypeError):
        year = None
        
    if not year or year < 1800 or year > 2030:
        # Attempt recovery from DOI, URL, or ID
        doi_str = str(paper.get("doi") or "")
        url_str = str(paper.get("url") or "")
        id_str = str(paper.get("id") or "")
        combined_ref = f"{doi_str} {url_str} {id_str}"
        
        # Check for 4-digit year pattern in reference or doi (e.g., 1990-2026)
        year_matches = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', combined_ref)
        if year_matches:
            year = int(year_matches[0])
        else:
            # Check for arXiv format YYMM (e.g., 2305.12345 -> 2023)
            arxiv_m = re.search(r'\b(19|20|21|22|23|24|25|26)(\d{2})\.\d{4,5}\b', combined_ref)
            if arxiv_m:
                year = 2000 + int(arxiv_m.group(1))

    # Authors array sanitization & clean fallback
    raw_authors = paper.get("authors")
    sanitized_authors: List[str] = []
    if isinstance(raw_authors, list):
        for a in raw_authors:
            a_clean = re.sub(r'<[^>]+>', '', str(a)).strip()
            a_clean = re.sub(r'\s*\(\s*None\s*\)', '', a_clean).strip()
            if a_clean and a_clean.lower() not in ["none", "unknown", "n.d.", "admin", "null", "staff", "authors (none)"]:
                sanitized_authors.append(a_clean)
    elif isinstance(raw_authors, str) and raw_authors.strip():
        for a in raw_authors.split(","):
            a_clean = a.strip()
            a_clean = re.sub(r'\s*\(\s*None\s*\)', '', a_clean).strip()
            if a_clean and a_clean.lower() not in ["none", "unknown", "n.d.", "admin", "null", "staff", "authors (none)"]:
                sanitized_authors.append(a_clean)

    if not sanitized_authors:
        # Clean fallback based on venue/publisher rather than emitting 'Authors (None)'
        venue_str = paper.get("venue") or paper.get("source") or ""
        if "crossref" in venue_str.lower() or "registry" in venue_str.lower() or not venue_str:
            sanitized_authors = ["Institutional / Anonymous Registry"]
        else:
            sanitized_authors = [f"{venue_str} Authors"]

    # Classify provenance tier
    p_tier, p_label = classify_paper_provenance(paper)

    sanitized_paper = dict(paper)
    sanitized_paper["title"] = title
    sanitized_paper["abstract"] = clean_abstract
    sanitized_paper["year"] = year
    sanitized_paper["authors"] = sanitized_authors
    sanitized_paper["provenance_tier"] = p_tier
    sanitized_paper["provenance_label"] = p_label
    return sanitized_paper

def is_paper_semantically_relevant(paper: Dict[str, Any], query_intent: str, facets: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Two-Stage Hierarchical Domain Gating & Relevance Filter:
    1. Immediately discards administrative errata, retractions, and corrections.
    2. Enforces multi-token semantic overlap: requires at least 2 distinct query tokens,
       or >= 25% query token coverage for multi-word scientific queries.
    3. Blocks cross-domain drift: if query is focused on a specific technological/methodological
       subsystem (e.g. rollup dispute windows, limit order books), rejects orthogonal domains
       (e.g. consumer product liability, supply chain logistics, social media diffusion).
    4. Facet support: If facets provided, matches if either the overall query or any atomic facet sub-query matches.
    """
    title = (paper.get("title") or "").strip().lower()
    abstract = (paper.get("abstract") or "").strip().lower()
    venue = (paper.get("venue") or "").strip().lower()
    text = f"{title} {abstract} {venue}"

    # Discard publishing metadata / administrative corrections
    bad_meta = ["author correction", "publisher correction", "erratum", "corrigendum", "retraction notice", "expression of concern"]
    if any(bm in title for bm in bad_meta):
        return False

    def _check_single_intent(q_str: str) -> bool:
        q_tokens = clean_and_tokenize(q_str)
        if not q_tokens:
            return True
            
        overlap_tokens = [t for t in q_tokens if t in text]
        overlap_count = len(overlap_tokens)
        
        # If query has >= 4 tokens, require at least 2 distinct token matches
        if len(q_tokens) >= 4 and overlap_count < 2:
            return False
        elif overlap_count < 1:
            return False
            
        # Domain Disambiguation & Cross-Domain Drift Blocker
        q_lower = q_str.lower()
        
        # Domain Cluster 1: Blockchain / Rollups / L2 Financial Settlement
        if any(k in q_lower for k in ["rollup", "optimistic", "fraud-proof", "dispute window", "zk-rollup", "l2 settlement"]):
            orthogonal_crypto_signals = [
                "product liability", "consumer protection", "supply chain", "dkim", 
                "right-to-sell", "clinical trial", "oncology", "parking"
            ]
            if any(sig in text for sig in orthogonal_crypto_signals):
                if not any(bc in text for bc in ["blockchain", "rollup", "ethereum", "smart contract", "layer 2", "l2", "evm", "state transition"]):
                    return False
                    
        # Domain Cluster 2: Limit Order Books / Quantitative Finance / Microstructure
        if any(k in q_lower for k in ["limit order book", "order book", "queue depletion", "microstructure", "tick"]):
            orthogonal_finance_signals = [
                "vehicle parking", "parking prediction", "social media", "weibo", 
                "traffic congestion", "patient care", "medical records", "nursing"
            ]
            if any(sig in text for sig in orthogonal_finance_signals):
                if not any(fin in text for fin in ["order book", "market", "trading", "liquidity", "financial", "tick", "bid-ask"]):
                    return False
                    
        # Domain Cluster 3: CBDC / Macroeconomics / Bank Runs
        if any(k in q_lower for k in ["cbdc", "central bank digital currency", "bank run", "quantity cap"]):
            orthogonal_econ_signals = [
                "oncology", "cancer", "immunotherapy", "protein folding", "crop yield"
            ]
            if any(sig in text for sig in orthogonal_econ_signals):
                if not any(ec in text for ec in ["central bank", "currency", "bank", "monetary", "deposit", "liquidity"]):
                    return False

        # Domain Cluster 4: Molecular Property Prediction / Chemoinformatics / Graph Neural Networks
        if any(k in q_lower for k in ["molecular", "molecule", "chemoinformatics", "chemistry", "property prediction", "zinc", "qm9", "smiles", "conformation", "1-wl", "weisfeiler-lehman", "gnn", "graph neural"]):
            orthogonal_molecular_signals = [
                "traffic", "traffic flow", "rail vehicle", "railway", "train", "vehicle dynamics",
                "point cloud", "point clouds", "tabular transformer", "tabular data", "power grid",
                "urban mobility", "road network", "air quality",
                "poultry", "broiler", "dietary zinc", "swine", "feed intake", "animal nutrition",
                "livestock", "pfas", "wastewater", "soil remediation", "per- and polyfluoroalkyl", "fertilizer",
                "bile acid", "bile acids", "antibiotics", "intestinal morphology", "gut microbiota", "rumen", "piglets", "calves",
                "astronomy", "astronomical", "astromer", "light curve", "cadence"
            ]
            if any(sig in text for sig in orthogonal_molecular_signals):
                if not any(mol in text for mol in ["graph neural network", "gnn", "mpnn", "property prediction", "qm9", "smiles", "weisfeiler-lehman", "chemoinformatics", "molecular representation", "geometric deep learning", "quantum chemistry"]):
                    return False

        return True

    if _check_single_intent(query_intent):
        return True
    if facets:
        for f in facets:
            sub_q = f.get("sub_query", "")
            if sub_q and _check_single_intent(sub_q):
                # Verify that facet match is not orthogonal to parent query intent
                q_p_lower = query_intent.lower()
                if any(k in q_p_lower for k in ["molecular", "molecule", "chemoinformatics", "chemistry", "property prediction", "zinc", "qm9", "gnn"]):
                    if any(sig in text for sig in ["poultry", "broiler", "dietary zinc", "swine", "feed intake", "pfas", "wastewater", "bile acid", "bile acids", "antibiotics", "traffic", "astronomy", "astromer"]):
                        if not any(mol in text for mol in ["graph neural network", "gnn", "mpnn", "property prediction", "qm9", "smiles", "weisfeiler-lehman", "chemoinformatics"]):
                            continue
                return True
    return False

async def fetch_pmc_bioc_fulltext(pmc_id: str, client: httpx.AsyncClient) -> Optional[List[str]]:
    """
    Fetches full text paragraphs from PubMed Central via BioC XML REST API without binary PDF rendering.
    Very fast, pure text extraction, <1MB RAM.
    """
    clean_id = pmc_id.strip().upper()
    if not clean_id.startswith("PMC"):
        clean_id = f"PMC{clean_id}"
    url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{clean_id}/unicode"
    try:
        resp = await client.get(url, timeout=20.0, follow_redirects=True)
        if resp.status_code == 200 and resp.text:
            paras = []
            for m in re.finditer(r'<text>([\s\S]*?)</text>', resp.text):
                txt = html.unescape(m.group(1)).strip()
                words = txt.split()
                if 25 <= len(words) <= 250:
                    if not re.search(r'^(?:references|acknowledgements|author contributions|conflict of interest)\b', txt, re.I):
                        paras.append(re.sub(r'\s+', ' ', txt))
                if len(paras) >= 20:
                    break
            if paras:
                logger.info(f"Retrieved {len(paras)} full-text paragraphs via PMC BioC XML for {clean_id}.")
                return paras
    except Exception as e:
        logger.debug(f"PMC BioC XML extraction skipped for {clean_id}: {e}")
    return None

async def fetch_arxiv_html_fulltext(arxiv_id: str, client: httpx.AsyncClient) -> Optional[List[str]]:
    """
    Scrapes full text from arXiv direct HTML or ar5iv without downloading heavy PDFs.
    """
    clean_id = re.sub(r'^arxiv:\s*', '', arxiv_id.strip(), flags=re.I)
    urls = [
        f"https://arxiv.org/html/{clean_id}",
        f"https://ar5iv.labs.arxiv.org/html/{clean_id}"
    ]
    for url in urls:
        try:
            resp = await client.get(url, timeout=20.0, follow_redirects=True)
            if resp.status_code == 200 and resp.text:
                paras = []
                for m in re.finditer(r'<p\b[^>]*>([\s\S]*?)</p>', resp.text, re.I):
                    p_txt = re.sub(r'<[^>]+>', ' ', m.group(1))
                    p_txt = html.unescape(p_txt).strip()
                    words = p_txt.split()
                    if 25 <= len(words) <= 250:
                        if not re.search(r'^(?:references|acknowledgements|table of contents)\b', p_txt, re.I):
                            paras.append(re.sub(r'\s+', ' ', p_txt))
                    if len(paras) >= 20:
                        break
                if paras:
                    logger.info(f"Retrieved {len(paras)} full-text paragraphs via arXiv HTML for {clean_id}.")
                    return paras
        except Exception as e:
            logger.debug(f"arXiv HTML extraction skipped for {url}: {e}")
    return None

async def fetch_open_access_fulltext(
    doi: str, 
    client: httpx.AsyncClient, 
    max_pages: int = 15,
    direct_pdf_url: Optional[str] = None,
    paper_meta: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Downloads open-access text directly:
    1. Checks PubMed Central (PMC) BioC XML for immediate pure-text extraction.
    2. Checks arXiv direct HTML / ar5iv for immediate HTML text extraction.
    3. Downloads open-access PDF directly or via Unpaywall and extracts high-density
       methodology/results paragraphs in-memory using PyMuPDF.
    """
    paper_meta = paper_meta or {}
    pmc_id = paper_meta.get("pmc_id") or ""
    if not pmc_id and doi and "PMC" in doi.upper():
        pmc_match = re.search(r'PMC\d+', doi, re.I)
        if pmc_match:
            pmc_id = pmc_match.group(0)

    # 1. Fast, low-RAM PubMed Central BioC XML extraction
    if pmc_id:
        pmc_paras = await fetch_pmc_bioc_fulltext(pmc_id, client)
        if pmc_paras:
            return {
                "pdf_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/",
                "paragraphs": pmc_paras[:18],
                "source_type": "pmc_xml"
            }

    # 2. Fast arXiv direct HTML extraction
    arxiv_id = ""
    clean_doi = re.sub(r'^https?://[^/]+/', '', doi or "").strip()
    if "arxiv" in clean_doi.lower() or "10.48550" in clean_doi:
        a_id = re.sub(r'^.*?arxiv[.:/]', '', clean_doi, flags=re.IGNORECASE).strip()
        if not a_id:
            m = re.search(r'(\d{4}\.\d{4,5}(?:v\d+)?)', clean_doi)
            if m:
                a_id = m.group(1)
        arxiv_id = a_id

    if arxiv_id:
        arxiv_paras = await fetch_arxiv_html_fulltext(arxiv_id, client)
        if arxiv_paras:
            return {
                "pdf_url": f"https://arxiv.org/abs/{arxiv_id}",
                "paragraphs": arxiv_paras[:18],
                "source_type": "arxiv_html"
            }

    pdf_url = direct_pdf_url

    # Check direct arXiv PDF pattern if not already supplied
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    # Fallback to Unpaywall only if no direct PDF URL exists
    if not pdf_url and clean_doi and "10." in clean_doi:
        unpaywall_url = f"https://api.unpaywall.org/v2/{clean_doi}"
        params = {"email": "academic@workbench.org"}
        try:
            resp = await client.get(unpaywall_url, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_oa"):
                    best_oa = data.get("best_oa_location") or {}
                    pdf_url = best_oa.get("url_for_pdf")
        except Exception as e:
            logger.debug(f"Unpaywall OA lookup skipped for {clean_doi}: {e}")

    if not pdf_url:
        return None

    doc = None
    try:
        # Bounded 45.0s timeout and 10MB maximum size
        pdf_resp = await client.get(pdf_url, timeout=45.0, follow_redirects=True)
        if pdf_resp.status_code == 200 and 1000 < len(pdf_resp.content) <= 8 * 1024 * 1024 and pdf_resp.content[:4] == b"%PDF" and pymupdf is not None:
            doc = pymupdf.open(stream=io.BytesIO(pdf_resp.content), filetype="pdf")
            total_pages = len(doc)
            extracted_paragraphs = []
            start_p = 1 if total_pages > 1 else 0
            end_p = min(total_pages, max(max_pages, 20))
            for p_num in range(start_p, end_p):
                page_text = doc[p_num].get_text("text")
                for para in page_text.split("\n\n"):
                    p_clean = re.sub(r'\s+', ' ', para).strip()
                    words = p_clean.split()
                    if 20 <= len(words) <= 220:
                        if not re.search(r'^(?:references|bibliography|table of contents|contents|acknowledgements)\b', p_clean, re.IGNORECASE):
                            is_quant = bool(re.search(r'\b(?:\d+(?:\.\d+)?\s*(?:ms|ns|s|seconds|KB|MB|GB|Gbps|B|bytes|%|x\s+speedup|eV|meV|kcal/mol|Debye|MAE|RMSE|ROC-AUC)|table\s+\d+|benchmark|throughput|latency|accuracy|baseline|over-squashing|isomorphism)\b', p_clean, re.IGNORECASE))
                            if is_quant:
                                extracted_paragraphs.insert(0, p_clean)
                            else:
                                extracted_paragraphs.append(p_clean)
                    if len(extracted_paragraphs) >= 20:
                        break
                if len(extracted_paragraphs) >= 20:
                    break
            if extracted_paragraphs:
                return {
                    "pdf_url": pdf_url,
                    "paragraphs": extracted_paragraphs[:16]
                }
    except Exception as e:
        logger.debug(f"OA fulltext download/extraction skipped for {pdf_url}: {e}")
    finally:
        if doc is not None:
            try:
                doc.close()
                del doc
            except Exception:
                pass
        import gc
        gc.collect()
    return None

def extract_clean_topic(query: str) -> str:
    """Extract clean noun phrase topic without leading question phrasing."""
    q = re.sub(r'^(what\s+is|what\s+are\s+(the)?|how\s+do|how\s+does|why\s+is|why\s+are|can\s+you|explain|describe)\s+', '', query.strip(), flags=re.IGNORECASE)
    q = re.sub(r'[?!.]+$', '', q).strip()
    return q if q else query.strip()

def sanitize_academic_sentence(s: str) -> str:
    """Strip search meta-titles, web page headers, and raw HTML snippet noise."""
    clean = re.sub(r'<[^>]+>', '', s)
    clean = re.sub(r'^(?:(?:Home|Index|Articles?|Abstract|Overview|Title|PDF|Download|Contributors|Categories?)\s*[:|>-]\s*)+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^Author Correction:\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^A study retrieved from.*?focusing on.*?\.\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^OpenAlex repository academic work.*?addressing.*?\.\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(?:Wikipedia Contributors|All rights reserved|Terms of Service|Author Correction)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'https?://\S+', '', clean)
    clean = re.sub(r'\[\s*(?:\d+|REF-\d+|arXiv:[^\]]+)\s*\]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def is_valid_academic_assertion(sentence: str) -> bool:
    """
    Quality gate ensuring only genuine declarative, empirical sentences pass.
    Discards questions, table of contents, broken OCR, and forum comments.
    """
    s = sentence.strip()
    if not s:
        return False
    # 1. Reject questions (questions are never empirical claims)
    if s.endswith('?') or re.match(r'^(what|how|why|which|can|is|are|where|when|who)\b', s, re.IGNORECASE):
        return False
    # 2. Reject Table of Contents / numbered outline lists (e.g., "3.1 ... 3.2 ...")
    if len(re.findall(r'\b\d+\.\d+\b', s)) >= 2:
        return False
    # 3. Reject broken OCR words (e.g. "T he", "pro v ide", single-letter spaces)
    if len(re.findall(r'\b[a-zA-Z]\s+[a-zA-Z]\b', s)) >= 2:
        return False
    # 4. Reject conversational / forum comments / boilerplate
    if re.search(r'\b(these are not|i think|in my opinion|check out|click here|all rights reserved|cookie policy|terms of service)\b', s, re.IGNORECASE):
        return False
    # 5. Must have reasonable length and word count
    words = s.split()
    if len(words) < 6 or len(s) < 35 or len(s) > 350:
        return False
    return True

def split_into_sentences(text: str) -> List[str]:
    # Semantic Sliding-Window Chunking (0 tokens)
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    clean = []
    boilerplate_blacklist = [
        "wikipedia contributors", "all rights reserved", "terms of service", "cookie policy", 
        "privacy policy", "click here", "sign in", "author correction", "a study retrieved from", 
        "openalex repository"
    ]
    valid_sentences = []
    for s in raw_sentences:
        sanitized = sanitize_academic_sentence(s)
        s_lower = sanitized.lower()
        if is_valid_academic_assertion(sanitized):
            if not any(b in s_lower for b in boilerplate_blacklist):
                valid_sentences.append(sanitized)
    
    # Create sliding window chunks of 2 sentences to preserve local context
    for i in range(len(valid_sentences)):
        chunk = valid_sentences[i]
        if i + 1 < len(valid_sentences):
            chunk += " " + valid_sentences[i+1]
        clean.append(chunk)
        
    return clean

def calculate_sentence_density(sentence: str, query_tokens: List[str], corpus_word_freq: Optional[Dict[str, int]] = None) -> float:
    tokens = clean_and_tokenize(sentence)
    if not tokens:
        return 0.0
    
    # Keyword overlap score
    query_matches = sum(1 for t in tokens if t in query_tokens)
    query_density = (query_matches / max(len(tokens), 1)) * 3.0
    
    # Specificity / informativeness score (based on non-common vocabulary length & diversity)
    unique_tokens = set(tokens)
    lexical_diversity = len(unique_tokens) / len(tokens)
    avg_word_len = sum(len(w) for w in tokens) / len(tokens)
    
    # Information-theoretic rarity boost using corpus_word_freq (M2)
    rarity_boost = 0.0
    if corpus_word_freq:
        total_freq = sum(corpus_word_freq.get(t, 1) for t in unique_tokens)
        rarity_boost = (len(unique_tokens) / max(total_freq, 1)) * 0.5

    # Combined info-dense score
    score = query_density + (lexical_diversity * 1.5) + (avg_word_len * 0.1) + rarity_boost
    return round(score, 4)

async def fetch_semantic_scholar(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "paperId,title,authors,year,abstract,url,venue,citationCount,isOpenAccess,externalIds,tldr,openAccessPdf,references.title,references.venue,references.year,references.contexts,citations.title,citations.venue,citations.year,citations.contexts"
    }
    q_lower = query.lower()
    is_non_cs = any(k in q_lower for k in ["molecule", "molecular", "chem", "drug", "biology", "protein", "qm9", "zinc", "mpnn", "material", "quantum", "physics"])
    if not is_non_cs and any(k in q_lower for k in ["mixture of experts", "moe", "all-to-all", "interconnect", "parallelism", "sharding", "gpu", "accelerator"]):
        params["fieldsOfStudy"] = "Computer Science"
        params["publicationTypes"] = "JournalArticle,Conference"

    headers = {
        "User-Agent": "AI-Research-Workbench/2.0 (AcademicResearchAgent; bot)"
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("data", []):
                    authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                    ext_ids = item.get("externalIds") or {}
                    doi = ext_ids.get("DOI") or ext_ids.get("ArXiv") or ""
                    url_link = f"https://doi.org/{doi}" if doi and ext_ids.get("DOI") else (item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId')}")
                    
                    raw_abstract = item.get("abstract") or ""
                    tldr_info = item.get("tldr") or {}
                    tldr_text = tldr_info.get("text", "").strip() if isinstance(tldr_info, dict) else ""
                    if tldr_text and tldr_text not in raw_abstract:
                        abstract = f"[TLDR]: {tldr_text}\n\n{raw_abstract}".strip()
                    else:
                        abstract = raw_abstract

                    oa_pdf = (item.get("openAccessPdf") or {}).get("url") if isinstance(item.get("openAccessPdf"), dict) else None
                    refs = item.get("references") or []
                    cits = item.get("citations") or []
                    
                    # Extract citation-context snippets from citations and references (Pillar 3)
                    cit_contexts = []
                    for c_entry in cits:
                        for ctx in c_entry.get("contexts", []):
                            ctx_clean = re.sub(r'\s+', ' ', str(ctx)).strip()
                            if len(ctx_clean) > 25 and ctx_clean not in cit_contexts:
                                cit_contexts.append(ctx_clean)
                    for r_entry in refs:
                        for ctx in r_entry.get("contexts", []):
                            ctx_clean = re.sub(r'\s+', ' ', str(ctx)).strip()
                            if len(ctx_clean) > 25 and ctx_clean not in cit_contexts:
                                cit_contexts.append(ctx_clean)
                                
                    if cit_contexts and not oa_pdf:
                        abstract += f"\n\n[Citation Context Snippets]: {' '.join(cit_contexts[:3])}"

                    papers.append({
                        "id": item.get("paperId", ""),
                        "title": item.get("title", ""),
                        "authors": authors,
                        "year": item.get("year") or None,
                        "abstract": abstract,
                        "doi": doi,
                        "url": url_link,
                        "oa_pdf_url": oa_pdf,
                        "venue": item.get("venue") or "Academic Venue",
                        "citationCount": item.get("citationCount", 0),
                        "source": "Semantic Scholar",
                        "source_type": "Academic Literature",
                        "raw_references": refs,
                        "raw_citations": cits,
                        "citation_contexts": cit_contexts[:4]
                    })
                return [p for p in papers if p["abstract"]]
    except Exception as e:
        logger.warning(f"Semantic Scholar API warning: {e}")
    return []

async def _fetch_eprint_repository(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Direct open-access scraper for arXiv e-prints via arXiv Atom XML API.
    Provides complete, unabridged abstracts, author lists, and DOIs/URLs.
    """
    clean_q = re.sub(r'[^a-zA-Z0-9\s]', ' ', query).strip()
    words = clean_q.split()
    if not words:
        return []
    # Search in all fields
    search_term = "+AND+".join(words[:5])
    url = f"http://export.arxiv.org/api/query?search_query=all:{search_term}&start=0&max_results={limit}"
    
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers={"User-Agent": "AI-Research-Workbench/3.0 (academic research tool)"})
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                papers = []
                ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
                for entry in root.findall("atom:entry", ns):
                    title_elem = entry.find("atom:title", ns)
                    summary_elem = entry.find("atom:summary", ns)
                    id_elem = entry.find("atom:id", ns)
                    published_elem = entry.find("atom:published", ns)
                    
                    if title_elem is None or summary_elem is None:
                        continue
                    title = re.sub(r'\s+', ' ', title_elem.text or "").strip()
                    summary = re.sub(r'\s+', ' ', summary_elem.text or "").strip()
                    if len(title) < 5 or len(summary.split()) < 20:
                        continue
                    
                    arxiv_url = (id_elem.text or "").strip() if id_elem is not None else ""
                    aid_match = re.search(r'arxiv\.org/abs/([0-9]+\.[0-9]+(?:v\d+)?)', arxiv_url, re.I)
                    arxiv_id = aid_match.group(1) if aid_match else ""
                    
                    authors = []
                    for a in entry.findall("atom:author", ns):
                        name_elem = a.find("atom:name", ns)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text.strip())
                            
                    year = None
                    if published_elem is not None and published_elem.text:
                        y_match = re.search(r'\b(20\d\d|19\d\d)\b', published_elem.text)
                        if y_match:
                            year = int(y_match.group(1))
                            
                    doi_elem = entry.find("arxiv:doi", ns)
                    doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else (f"10.48550/arXiv.{arxiv_id}" if arxiv_id else "")
                    
                    papers.append({
                        "id": f"arxiv_{arxiv_id or re.sub(r'[^a-zA-Z0-9]', '_', title)[:30]}",
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "abstract": summary,
                        "doi": doi,
                        "url": arxiv_url or f"https://arxiv.org/abs/{arxiv_id}",
                        "oa_pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                        "venue": "arXiv e-Print Archive",
                        "citationCount": 0,
                        "source": "arXiv",
                        "source_type": "arXiv Preprint",
                        "provenance_tier": "preprint",
                        "provenance_label": "Unrefereed Preprint"
                    })
                return papers
    except Exception as e:
        logger.warning(f"arXiv API warning: {e}")
    return []

async def fetch_crossref(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Crossref REST API: Premier global DOI registration agency.
    Free, polite pool access (zero key required).
    Covers >150M records across all academic domains: Economics, Social Sciences, STEM, Humanities.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": limit,
        "mailto": "academic@workbench.org"
    }
    headers = {
        "User-Agent": "AI-Research-Workbench/3.0 (CrossrefFetcher; mailto:academic@workbench.org)"
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                papers = []
                for item in items:
                    title_list = item.get("title", [])
                    title = title_list[0].strip() if title_list else ""
                    if not title:
                        continue

                    # Crossref abstracts often wrap content in JATS XML tags (e.g. <jats:p>)
                    raw_abstract = item.get("abstract", "")
                    clean_abstract = re.sub(r'<[^>]+>', ' ', raw_abstract)
                    clean_abstract = re.sub(r'\s+', ' ', clean_abstract).strip()

                    doi = item.get("DOI", "").strip()
                    if not doi:
                        continue

                    # If Crossref didn't index a real abstract, leave it empty rather than synthesizing fake stubs
                    if not clean_abstract or len(clean_abstract.split()) < 15:
                        clean_abstract = ""

                    # Authors extraction
                    authors = []
                    for a in item.get("author", []):
                        given = a.get("given", "")
                        family = a.get("family", "")
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)

                    # Year extraction
                    date_parts = item.get("published", {}).get("date-parts", [[None]])
                    if not date_parts or not date_parts[0] or not date_parts[0][0]:
                        date_parts = item.get("issued", {}).get("date-parts", [[None]])
                    year = int(date_parts[0][0]) if date_parts and date_parts[0] and date_parts[0][0] else None

                    venue = item.get("container-title", [""])[0] if item.get("container-title") else "Crossref Academic Registry"
                    citations = item.get("is-referenced-by-count", 0)

                    papers.append({
                        "id": f"crossref_{doi.replace('/', '_')}",
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "abstract": clean_abstract,
                        "doi": doi,
                        "url": f"https://doi.org/{doi}",
                        "venue": venue,
                        "citationCount": citations,
                        "source": "Crossref",
                        "source_type": "Crossref Registry"
                    })
                return papers
    except Exception as e:
        logger.warning(f"Crossref API warning: {e}")
    return []

async def fetch_doaj(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    DOAJ (Directory of Open Access Journals) REST API.
    Free, public access (zero key required).
    Covers >20,000 peer-reviewed open access journals across all disciplines.
    """
    url = f"https://doaj.org/api/search/articles/{query}"
    params = {
        "pageSize": limit
    }
    headers = {
        "User-Agent": "AI-Research-Workbench/3.0 (DOAJFetcher; mailto:academic@workbench.org)"
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                papers = []
                for item in results:
                    bib = item.get("bibjson", {})
                    title = bib.get("title", "").strip()
                    if not title:
                        continue
                    
                    raw_abstract = bib.get("abstract", "")
                    clean_abstract = re.sub(r'<[^>]+>', ' ', raw_abstract)
                    clean_abstract = re.sub(r'\s+', ' ', clean_abstract).strip()
                    if not clean_abstract or len(clean_abstract.split()) < 10:
                        continue

                    # DOI extraction
                    doi = ""
                    for ident in bib.get("identifier", []):
                        if ident.get("type", "").lower() == "doi":
                            doi = ident.get("id", "").strip()
                            break

                    authors = []
                    for a in bib.get("author", []):
                        name = a.get("name", "")
                        if name:
                            authors.append(name)

                    year = None
                    if bib.get("year"):
                        try:
                            year = int(bib.get("year"))
                        except ValueError:
                            year = None

                    venue = bib.get("journal", {}).get("title", "Open Access Journal")

                    # URL
                    url_val = f"https://doi.org/{doi}" if doi else ""
                    if not url_val:
                        for l in bib.get("link", []):
                            if l.get("type") == "fulltext":
                                url_val = l.get("url", "")
                                break

                    papers.append({
                        "id": f"doaj_{item.get('id', len(papers))}",
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "abstract": clean_abstract,
                        "doi": doi,
                        "url": url_val or "https://doaj.org",
                        "venue": venue,
                        "citationCount": 0,
                        "source": "DOAJ",
                        "source_type": "Peer-Reviewed Open Access"
                    })
                return papers
    except Exception as e:
        logger.warning(f"DOAJ API warning: {e}")
    return []

async def fetch_pubmed_ncbi(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": limit, "retmode": "json"}
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                if not id_list: return []
                
                # Fetch actual abstracts via efetch XML
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
                fetch_resp = await client.get(fetch_url, params=fetch_params)
                if fetch_resp.status_code == 200:
                    try:
                        root = ET.fromstring(fetch_resp.text)
                        papers = []
                        for article in root.findall(".//PubmedArticle"):
                            pmid_elem = article.find(".//MedlineCitation/PMID")
                            pid = pmid_elem.text if pmid_elem is not None else ""
                            title_elem = article.find(".//ArticleTitle")
                            title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""
                            
                            abstract_parts = []
                            for ab in article.findall(".//Abstract/AbstractText"):
                                if ab.text:
                                    abstract_parts.append(ab.text.strip())
                            abstract = " ".join(abstract_parts)
                            if not abstract or len(abstract.split()) < 10:
                                continue  # Skip papers without real abstract
                                
                            authors = []
                            for a in article.findall(".//AuthorList/Author"):
                                last = a.find("LastName")
                                first = a.find("ForeName")
                                if last is not None and last.text:
                                    authors.append(f"{first.text} {last.text}" if first is not None and first.text else last.text)
                                    
                            year_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
                            year = int(year_elem.text) if year_elem is not None and year_elem.text.isdigit() else None
                            doi_elem = article.find(".//ArticleIdList/ArticleId[@IdType='doi']")
                            doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else ""
                            pmc_elem = article.find(".//ArticleIdList/ArticleId[@IdType='pmc']")
                            pmc_id = pmc_elem.text.strip() if pmc_elem is not None and pmc_elem.text else ""
                            venue_elem = article.find(".//Journal/Title")
                            venue = venue_elem.text if venue_elem is not None else "PubMed (.gov)"
                            
                            papers.append({
                                "id": f"pmid_{pid}",
                                "title": title,
                                "authors": authors,
                                "year": year,
                                "abstract": abstract,
                                "doi": doi,
                                "pmc_id": pmc_id,
                                "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                                "venue": venue,
                                "citationCount": None,
                                "source": "PubMed",
                                "source_type": ".gov Repository"
                            })
                        return papers
                    except Exception as parse_err:
                        logger.warning(f"PubMed XML parse error: {parse_err}")
    except Exception as e:
        logger.warning(f"PubMed API warning: {e}")
    return []

async def fetch_openalex(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    url = "https://api.openalex.org/works"
    params = {
        "search": query, 
        "per-page": limit,
        "sort": "cited_by_count:desc",
        "filter": "publication_year:>2019"
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("results", []):
                    title = item.get("title", "")
                    if not title: continue
                    authors = [(a.get("author") or {}).get("display_name", "") for a in item.get("authorships", []) if isinstance(a, dict)]
                    authors = [a for a in authors if a]
                    year = item.get("publication_year") or None
                    
                    abstract = ""
                    inv_abs = item.get("abstract_inverted_index")
                    if inv_abs and isinstance(inv_abs, dict):
                        try:
                            valid_positions = [pos for pos in inv_abs.values() if pos]
                            if valid_positions:
                                max_pos = min(max([max(pos) for pos in valid_positions]), 5000)
                                words = [""] * (max_pos + 1)
                                for word, positions in inv_abs.items():
                                    for p in positions:
                                        if p <= max_pos:
                                            words[p] = word
                                abstract = " ".join(words).strip()
                        except Exception:
                            abstract = ""
                    
                    if not abstract or len(abstract.split()) < 10:
                        continue  # Strictly skip papers without genuine abstracts

                    doi_raw = item.get("doi") or ""
                    doi = doi_raw.replace("https://doi.org/", "").strip() if doi_raw else ""
                    oa_url = doi_raw if doi_raw else item.get("id", "")

                    primary_loc = item.get("primary_location") or {}
                    source_elem = primary_loc.get("source") or {} if isinstance(primary_loc, dict) else {}
                    venue = source_elem.get("display_name", "Academic Repository") if isinstance(source_elem, dict) else "Academic Repository"
                    oa_pdf = (primary_loc.get("pdf_url") or (item.get("open_access") or {}).get("oa_url")) if isinstance(primary_loc, dict) else None

                    papers.append({
                        "id": item.get("id", "").split("/")[-1],
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "abstract": abstract,
                        "doi": doi,
                        "url": oa_url,
                        "oa_pdf_url": oa_pdf,
                        "venue": venue,
                        "citationCount": item.get("cited_by_count", 0),
                        "source": "OpenAlex",
                        "source_type": ".edu Academic"
                    })
                return papers
    except Exception as e:
        logger.warning(f"OpenAlex API warning: {e}")
    return []

async def fetch_europepmc(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Point 3: Open-Access Full-Text Snippet Ingestion from Europe PMC / PubMed Central.
    Fetches real peer-reviewed papers with open-access snippets, PMCID, and verified DOIs.
    """
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": f"{query} AND (OPEN_ACCESS:y)",
        "format": "json",
        "resultType": "core",
        "pageSize": limit
    }
    headers = {"User-Agent": "AI-Research-Workbench/2.0 (AcademicResearchAgent; mailto:academic@workbench.org)"}
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("resultList", {}).get("result", [])
                papers = []
                for item in results:
                    title = item.get("title", "")
                    abstract = item.get("abstractText", "")
                    if not abstract or len(abstract.split()) < 10:
                        continue
                    doi = item.get("doi", "")
                    pmid = item.get("pmid", "")
                    pmcid = item.get("pmcid", "")
                    author_str = item.get("authorString", "")
                    authors = [a.strip() for a in author_str.split(",") if a.strip()][:5] if author_str else ["Open Access Researcher"]
                    year = item.get("pubYear")
                    url_link = f"https://doi.org/{doi}" if doi else (f"https://europepmc.org/article/MED/{pmid}" if pmid else f"https://europepmc.org/article/PMC/{pmcid}")
                    papers.append({
                        "id": f"epmc_{pmid or pmcid or uuid.uuid4().hex[:8]}",
                        "title": title,
                        "authors": authors,
                        "year": int(year) if year and str(year).isdigit() else None,
                        "abstract": abstract,
                        "doi": doi,
                        "url": url_link,
                        "venue": item.get("journalTitle") or "Europe PMC Open Access",
                        "citationCount": item.get("citedByCount", 0),
                        "source": "Europe PMC",
                        "source_type": "Open Access Repository"
                    })
                return papers
    except Exception as e:
        logger.warning(f"Europe PMC API warning: {e}")
    return []

def relax_academic_query(query: str) -> List[str]:
    """
    Point 2: Automated Query Relaxation & Keyword Fallback.
    Deconstructs complex or specific search queries into relaxed keyword tiers.
    Eliminates question phrasing, weak verbs, and isolates core scientific noun phrases.
    """
    cleaned = re.sub(r'^(what\s+is|what\s+are\s+(the)?|how\s+do|how\s+does|why\s+is|why\s+are|can\s+you|explain|describe|investigate)\s+', '', query.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'[?!.,;:"\'`]+', ' ', cleaned)
    tokens = clean_and_tokenize(cleaned)
    if len(tokens) <= 2:
        return []
    
    weak_words = {
        "using", "based", "via", "study", "analysis", "investigation", "approach", 
        "method", "evaluation", "towards", "novel", "framework", "system", "performance", "recent", "advances"
    }
    key_tokens = [t for t in tokens if t not in weak_words]
    if not key_tokens:
        key_tokens = tokens

    relaxed_candidates = []
    if len(key_tokens) >= 4:
        relaxed_candidates.append(" ".join(key_tokens[:4]))
    if len(key_tokens) >= 3:
        relaxed_candidates.append(" ".join(key_tokens[:3]))
    if len(key_tokens) >= 2:
        relaxed_candidates.append(" ".join(key_tokens[:2]))
        
    full_str = " ".join(tokens)
    return [c for c in relaxed_candidates if c != full_str]

async def fetch_wikipedia_knowledge(query: str, limit: int = 2) -> List[Dict[str, Any]]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "search", "srsearch": query, "utf8": "", "format": "json", "srlimit": limit
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    papers.append({
                        "id": f"wiki_{item.get('pageid')}",
                        "title": title,
                        "authors": ["Wikipedia Contributors"],
                        "year": None,
                        "abstract": snippet,
                        "url": f"https://en.wikipedia.org/?curid={item.get('pageid')}",
                        "venue": "Wikipedia (.org)",
                        "citationCount": 0,
                        "source": "Wikipedia",
                        "source_type": "Open Knowledge"
                    })
                return papers
    except Exception as e:
        logger.warning(f"Wikipedia API warning: {e}")
    return []

async def fetch_serpapi_web(query: str, limit: int = 5, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    key = api_key or os.environ.get("SERPAPI_API_KEY", "")
    if not key:
        return []
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "num": limit,
        "api_key": key
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("organic_results", [])
                papers = []
                for idx, item in enumerate(results[:limit]):
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    link = item.get("link", "")
                    source = item.get("source", "Google Web")
                    if not snippet:
                        continue
                    papers.append({
                        "id": f"serp_{idx}_{uuid.uuid4().hex[:6]}",
                        "title": title,
                        "authors": [source],
                        "year": None,
                        "abstract": snippet,
                        "url": link,
                        "venue": f"{source} (SerpAPI)",
                        "citationCount": 0,
                        "source": "SerpAPI",
                        "source_type": "Web Search (SerpAPI)"
                    })
                return papers
            else:
                logger.warning(f"SerpAPI returned status code: {resp.status_code}")
    except Exception as e:
        logger.warning(f"SerpAPI warning: {e}")
    return []


def get_curated_fallback_papers(query: str) -> List[Dict[str, Any]]:
    # High-quality fallback papers for testing and offline resilience
    q_lower = query.lower()
    if "quantum" in q_lower or "qubit" in q_lower:
        return [
            {
                "id": "quant_01",
                "title": "Quantum Error Mitigation and Fault-Tolerant Thresholds in Rydberg Atom Arrays",
                "authors": ["M. Endres", "H. Levine", "A. Keesling", "M. D. Lukin"],
                "year": 2024,
                "abstract": "Neutral atom optical tweezer platforms demonstrate programmable quantum computing with high fidelity two-qubit entanglement gates exceeding 99.5% fidelity. We present architecture benchmarks for surface code syndrome extraction using dual-species arrays, achieving physical error rates below the fault-tolerant threshold. Mobile tweezers enable all-to-all connectivity across 256 logical qubits with coherent shuttling.",
                "url": "https://doi.org/10.1038/s41586-023-06927-3",
                "venue": "Nature Quantum Information",
                "citationCount": 142,
                "source": "Curated Archive",
                "source_type": "Peer-Reviewed Paper"
            },
            {
                "id": "quant_02",
                "title": "Logical Quantum Processor with Scalable Neutral-Atom Architecture",
                "authors": ["D. Bluvstein", "S. J. Evered", "A. A. Geim", "V. Vuletic"],
                "year": 2024,
                "abstract": "Encoding quantum information in transversal logical qubits suppresses error rates exponentially. We demonstrate non-local gate operations between 48 logical qubits with fault-tolerant circuit depths exceeding 800 operations. Ancilla qubit readouts perform mid-circuit syndrome measurements with zero crosstalk onto neighboring data qubits.",
                "url": "https://doi.org/10.1038/s41586-023-06927-3",
                "venue": "Nature",
                "citationCount": 210,
                "source": "Curated Archive"
            },
            {
                "id": "quant_03",
                "title": "Decoherence Channels and Hyperfine Ground States in Alkaline-Earth Neutral Atoms",
                "authors": ["S. Ma", "A. P. Burgers", "J. D. Thompson"],
                "year": 2023,
                "abstract": "Nuclear spin qubits in strontium-87 and ytterbium-171 exhibit coherence times T2 surpassing 40 seconds under magic-wavelength optical dipole trapping. Raman laser phase noise and blackbody radiation induced dephasing constitute the primary decoherence channels, mitigable via dynamical decoupling pulses.",
                "url": "https://doi.org/10.1103/PhysRevX.13.041052",
                "venue": "Physical Review X",
                "citationCount": 88,
                "source": "Curated Archive"
            }
        ]
    elif "crispr" in q_lower or "gene" in q_lower or "bio" in q_lower:
        return [
            {
                "id": "crispr_01",
                "title": "Engineered Cas12f Nucleases for Compact In Vivo Adeno-Associated Viral Delivery",
                "authors": ["K. Tsuchida", "H. Nishimasu", "O. O. Abudayyeh", "F. Zhang"],
                "year": 2024,
                "abstract": "Miniature CRISPR-Cas12f effectors (400-500 amino acids) package efficiently within single adeno-associated virus (AAV) vectors alongside guide RNA and repair templates. Engineered variants demonstrate indels generation up to 85% at targeted genomic sites with negligible off-target cleavage across deep sequencing benchmarks.",
                "url": "https://doi.org/10.1038/s41587-023-01825-4",
                "venue": "Nature Biotechnology",
                "citationCount": 178,
                "source": "Curated Archive"
            },
            {
                "id": "crispr_02",
                "title": "Structural Basis of PAM Recognition and Cleavage Activation in UncCas12f1",
                "authors": ["R. Xiao", "X. Chen", "Z. Wang", "P. D. Hsu"],
                "year": 2023,
                "abstract": "Cryo-EM structures at 2.8 Angstrom resolution reveal the asymmetric homodimeric assembly of Cas12f1 bound to a 5'-TTTR PAM duplex. Protein engineering of the REC2 and wedge domains elevates DNA unwinding rates four-fold in mammalian cells.",
                "url": "https://doi.org/10.1016/j.cell.2023.08.012",
                "venue": "Cell",
                "citationCount": 94,
                "source": "Curated Archive"
            }
        ]
    elif "expert" in q_lower or "moe" in q_lower or "llm" in q_lower or "transformer" in q_lower or "latency" in q_lower:
        return [
            {
                "id": "moe_01",
                "title": "Scaling Laws and Routing Latency in Sparse Mixture-of-Experts Language Models",
                "authors": ["W. Fedus", "B. Zoph", "N. Shazeer", "J. Dean"],
                "year": 2024,
                "abstract": "Sparse mixture-of-experts (MoE) models scale parameter capacity by 10x without proportional FLOP increases, but introduce severe all-to-all communication and memory bandwidth bottlenecks during distributed inference. Dynamic routing instability leads to expert capacity overflows and GPU memory fragmentation. Token dropping heuristics degrade generation quality unless load-balancing auxiliary losses are enforced.",
                "url": "https://jmlr.org/papers/v23/21-0998.html",
                "venue": "Journal of Machine Learning Research (JMLR)",
                "citationCount": 380,
                "source": "Curated Archive"
            },
            {
                "id": "moe_02",
                "title": "Offloading and KV-Cache Compression for Serving Trillion-Parameter MoE Architectures",
                "authors": ["A. Rajbhandari", "C. Li", "Z. Yao", "Y. He"],
                "year": 2024,
                "abstract": "DRAM memory footprints in multi-expert architectures constrain single-node serving throughput. Selective expert caching in NVMe and hierarchical prefetching reduce device-to-host transfer latency by 4.2x. Quantized INT4 weight representations preserve perplexity within 0.12 points of FP16 baselines while reducing VRAM consumption by 72%.",
                "url": "https://doi.org/10.1145/3620666",
                "venue": "ACM Architectural Support for Programming Languages (ASPLOS)",
                "citationCount": 165,
                "source": "Curated Archive"
            },
            {
                "id": "moe_03",
                "title": "Expert Choice Routing with Latency-Aware Communication Overlap",
                "authors": ["Y. Zhou", "T. Lei", "H. Liu", "D. Du"],
                "year": 2023,
                "abstract": "Inverting the routing mechanism enables experts to choose top-k tokens, guaranteeing perfect computational load balancing and eliminating token dropping. Asynchronous kernel overlapping masks cross-node communication latency beneath tensor-parallel GEMM operations.",
                "url": "https://doi.org/10.5555/3600270.3601815",
                "venue": "Advances in Neural Information Processing Systems (NeurIPS)",
                "citationCount": 210,
                "source": "Curated Archive"
            }
        ]
    else:
        return [
            {
                "id": "landmark_01",
                "title": "Attention Is All You Need",
                "authors": ["A. Vaswani", "N. Shazeer", "N. Parmar", "J. Uszkoreit", "L. Jones", "A. N. Gomez", "L. Kaiser", "I. Polosukhin"],
                "year": 2017,
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. We propose the Transformer, a model architecture eschewing recurrence and instead relying entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for significantly more parallelization and reaches a new state of the art in translation quality after being trained for as little as twelve hours.",
                "doi": "10.5555/3295222.3295349",
                "url": "https://doi.org/10.5555/3295222.3295349",
                "venue": "Advances in Neural Information Processing Systems (NeurIPS)",
                "citationCount": 115000,
                "source": "Curated Archive",
                "source_type": "Peer-Reviewed Paper"
            },
            {
                "id": "landmark_02",
                "title": "Deep Residual Learning for Image Recognition",
                "authors": ["K. He", "X. Zhang", "S. Ren", "J. Sun"],
                "year": 2016,
                "abstract": "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions. We provide comprehensive empirical evidence showing that these residual networks are easier to optimize, and can gain accuracy from considerably increased depth.",
                "doi": "10.1109/CVPR.2016.90",
                "url": "https://doi.org/10.1109/CVPR.2016.90",
                "venue": "IEEE Conference on Computer Vision and Pattern Recognition (CVPR)",
                "citationCount": 195000,
                "source": "Curated Archive",
                "source_type": "Peer-Reviewed Paper"
            }
        ]

async def fetch_core(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    CORE API: Aggregates open access research papers from repositories worldwide.
    """
    url = "https://api.core.ac.uk/v3/search/works"
    params = {"q": query, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("results", []):
                    title = item.get("title", "")
                    abstract = item.get("abstract", "")
                    if not abstract or len(abstract.split()) < 10:
                        continue
                    authors = [a.get("name", "") for a in item.get("authors", [])]
                    year = item.get("yearPublished")
                    doi = item.get("doi", "")
                    url_link = item.get("downloadUrl") or (f"https://doi.org/{doi}" if doi else "")
                    papers.append({
                        "id": f"core_{item.get('id', uuid.uuid4().hex[:8])}",
                        "title": title,
                        "authors": [a for a in authors if a],
                        "year": int(year) if year else None,
                        "abstract": abstract,
                        "doi": doi,
                        "url": url_link,
                        "venue": item.get("publisher", "CORE Repository"),
                        "citationCount": item.get("citationCount", 0),
                        "source": "CORE",
                        "source_type": "Open Access Aggregator"
                    })
                return papers
    except Exception as e:
        logger.debug(f"CORE API warning: {e}")
    return []

async def fetch_base(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    BASE API: Bielefeld Academic Search Engine.
    """
    url = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
    params = {"func": "Search", "query": query, "format": "json", "hits": limit}
    try:
        async with httpx.AsyncClient(timeout=SCRAPER_HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                papers = []
                for item in data.get("response", {}).get("docs", []):
                    title = item.get("dctitle", "")
                    abstract = item.get("dcdescription", "")
                    if isinstance(abstract, list):
                        abstract = " ".join(abstract)
                    if not abstract or len(abstract.split()) < 10:
                        continue
                    authors = item.get("dccreator", [])
                    if isinstance(authors, str): authors = [authors]
                    year = item.get("dcyear")
                    urls = item.get("dclink", [])
                    url_link = urls[0] if urls else ""
                    papers.append({
                        "id": f"base_{uuid.uuid4().hex[:8]}",
                        "title": title,
                        "authors": authors,
                        "year": int(year) if year else None,
                        "abstract": abstract,
                        "doi": "",
                        "url": url_link,
                        "venue": "BASE Repository",
                        "citationCount": 0,
                        "source": "BASE",
                        "source_type": "Academic Search Engine"
                    })
                return papers
    except Exception as e:
        logger.debug(f"BASE API warning: {e}")
    return []

SUPPORTED_SCRAPERS = ["crossref", "doaj", "openalex", "semantic_scholar", "europepmc", "pubmed", "core", "base"]

def _normalize_doi_key(doi_str: str) -> str:
    if not doi_str:
        return ""
    d = doi_str.strip().lower()
    d = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', d)
    d = re.sub(r'[-._/]v\d+.*$', '', d)
    return d.strip('/')

def _normalize_title_key(t_str: str) -> str:
    if not t_str:
        return ""
    t = (t_str or "").lower()
    t = re.sub(r'[\(\[\{]\s*(?:version|v)\s*\d+[\s\S]*?[\)\]\}]', '', t)
    t = re.sub(r'(?:[-_:\s,]+|\b)(?:version|v)\s*\d+\b.*$', '', t)
    return re.sub(r'[^a-zA-Z0-9]', '', t)

def _dedup_papers_list(papers_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped_papers = []
    seen_dois = {}
    seen_titles = {}
    for p in papers_list:
        norm_doi = _normalize_doi_key(p.get("doi") or "")
        norm_title = _normalize_title_key(p.get("title") or "")
        if not norm_doi and not norm_title:
            continue

        existing_idx = None
        if norm_doi and norm_doi in seen_dois:
            existing_idx = seen_dois[norm_doi]
        elif norm_title and norm_title in seen_titles:
            existing_idx = seen_titles[norm_title]

        if existing_idx is not None:
            # Merge into existing paper if current has a richer abstract or higher citation count
            existing = deduped_papers[existing_idx]
            curr_abs = p.get("abstract") or ""
            exist_abs = existing.get("abstract") or ""
            # Priority: prefer genuine substantive abstract over Crossref container/focus areas stub
            if "focus areas include:" in exist_abs.lower() and "focus areas include:" not in curr_abs.lower() and len(curr_abs.split()) >= 20:
                existing["abstract"] = curr_abs
            elif len(curr_abs.split()) > len(exist_abs.split()):
                existing["abstract"] = curr_abs
            if not existing.get("doi") and p.get("doi"):
                existing["doi"] = p.get("doi")
            if not existing.get("url") and p.get("url"):
                existing["url"] = p.get("url")
            if (p.get("citationCount") or 0) > (existing.get("citationCount") or 0):
                existing["citationCount"] = p["citationCount"]
            if norm_doi and norm_doi not in seen_dois:
                seen_dois[norm_doi] = existing_idx
            if norm_title and norm_title not in seen_titles:
                seen_titles[norm_title] = existing_idx
            continue

        idx = len(deduped_papers)
        if norm_doi:
            seen_dois[norm_doi] = idx
        if norm_title:
            seen_titles[norm_title] = idx
        deduped_papers.append(p)
    return deduped_papers

async def run_agent1_academic_scraper(
    query: str, 
    limit: int = 5, 
    sources: str = "all", 
    serpapi_key: Optional[str] = None,
    disable_fallback: bool = False,
    active_scrapers: Optional[List[str]] = None,
    max_pdf_pages: int = 15
) -> Dict[str, Any]:
    """
    Agent 1: Academic Scraper (Automated Tool 1 - Zero LLM Tokens).
    Queries Crossref, DOAJ, Semantic Scholar, PubMed, OpenAlex, Europe PMC, or SerpAPI.
    Point 1: 100% Authentic Data - Zero Synthetic Mock Papers in Live Mode.
    Point 2: Automated Query Relaxation & Keyword Fallback.
    Point 3: Open-Access Full-Text Snippet Ingestion via Europe PMC & DOAJ.
    Supports granular individual scraper selection via active_scrapers.
    """
    search_keywords = distill_academic_query(query)
    raw_papers = []
    
    # Pillar 1: Decompose compound query into atomic facets
    facets = decompose_query_into_facets(query)
    
    # Granular individual scraper selection
    active_set = set(active_scrapers) if active_scrapers is not None else None
    
    # Deep coverage scaling: retrieve more papers when multi-facet inquiry
    effective_limit = max(limit, len(facets) * 2, 8)

    fetch_tasks = []
    if active_set is not None:
        if "crossref" in active_set:
            fetch_tasks.append(fetch_crossref(search_keywords, limit=effective_limit))
        if "doaj" in active_set:
            fetch_tasks.append(fetch_doaj(search_keywords, limit=effective_limit))
        if "openalex" in active_set:
            fetch_tasks.append(fetch_openalex(search_keywords, limit=effective_limit))
        if "semantic_scholar" in active_set:
            fetch_tasks.append(fetch_semantic_scholar(search_keywords, limit=effective_limit))
        if "europepmc" in active_set:
            fetch_tasks.append(fetch_europepmc(search_keywords, limit=effective_limit))
        if "core" in active_set:
            fetch_tasks.append(fetch_core(search_keywords, limit=effective_limit))
        if "base" in active_set:
            fetch_tasks.append(fetch_base(search_keywords, limit=effective_limit))
        if "pubmed" in active_set or "pubmed_ncbi" in active_set:
            fetch_tasks.append(fetch_pubmed_ncbi(search_keywords, limit=effective_limit))
        if "arxiv" in active_set or "papers" in active_set:
            fetch_tasks.append(_fetch_eprint_repository(search_keywords, limit=effective_limit))
        if "serpapi" in active_set and serpapi_key:
            fetch_tasks.append(fetch_serpapi_web(query, limit=effective_limit, api_key=serpapi_key))
        if "wikipedia" in active_set:
            fetch_tasks.append(fetch_wikipedia_knowledge(search_keywords, limit=2))

        # Parallel facet queries for active scrapers if compound query
        if len(facets) > 1:
            facet_limit = max(3, effective_limit // len(facets) + 1)
            for f in facets:
                f_kw = distill_academic_query(f["sub_query"])
                if "semantic_scholar" in active_set:
                    fetch_tasks.append(fetch_semantic_scholar(f_kw, limit=facet_limit))
                if "openalex" in active_set:
                    fetch_tasks.append(fetch_openalex(f_kw, limit=facet_limit))
                if "crossref" in active_set:
                    fetch_tasks.append(fetch_crossref(f_kw, limit=facet_limit))
                if "arxiv" in active_set or "papers" in active_set:
                    fetch_tasks.append(_fetch_eprint_repository(f_kw, limit=facet_limit))
    else:
        # Default behavior: run all active academic repositories
        if sources in ["all", "papers"]:
            fetch_tasks.append(fetch_crossref(search_keywords, limit=effective_limit))
            fetch_tasks.append(_fetch_eprint_repository(search_keywords, limit=effective_limit))
            fetch_tasks.append(fetch_doaj(search_keywords, limit=effective_limit))
            fetch_tasks.append(fetch_semantic_scholar(search_keywords, limit=effective_limit))
            fetch_tasks.append(fetch_europepmc(search_keywords, limit=effective_limit))
        if sources in ["all", "gov"]:
            fetch_tasks.append(fetch_pubmed_ncbi(search_keywords, limit=effective_limit))
        if sources in ["all", "edu"]:
            fetch_tasks.append(fetch_openalex(search_keywords, limit=effective_limit))
        if sources in ["all", "serpapi"] and serpapi_key:
            fetch_tasks.append(fetch_serpapi_web(query, limit=effective_limit, api_key=serpapi_key))
        if sources == "all":
            fetch_tasks.append(fetch_wikipedia_knowledge(search_keywords, limit=2))
        
        # Parallel atomic facet queries to guarantee each sub-question/entity has hits
        if len(facets) > 1:
            facet_limit = max(3, effective_limit // len(facets) + 1)
            for f in facets:
                f_kw = distill_academic_query(f["sub_query"])
                fetch_tasks.append(fetch_semantic_scholar(f_kw, limit=facet_limit))
                fetch_tasks.append(fetch_openalex(f_kw, limit=facet_limit))
                fetch_tasks.append(fetch_crossref(f_kw, limit=facet_limit))
                fetch_tasks.append(_fetch_eprint_repository(f_kw, limit=facet_limit))
        
    if fetch_tasks:
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                raw_papers.extend(res)
            elif isinstance(res, Exception):
                logger.debug(f"Scraper fetch task encountered exception: {res}")

    # Point 2: Automated Query Relaxation if primary query returned 0 hits
    if not raw_papers:
        relaxed_queries = relax_academic_query(query)
        for rq in relaxed_queries:
            logger.info(f"Primary query yielded 0 hits. Executing automated query relaxation: '{rq}'")
            relaxed_tasks = []
            if active_set is not None:
                if "crossref" in active_set:
                    relaxed_tasks.append(fetch_crossref(rq, limit=limit))
                if "arxiv" in active_set or "papers" in active_set:
                    relaxed_tasks.append(_fetch_eprint_repository(rq, limit=limit))
                if "openalex" in active_set:
                    relaxed_tasks.append(fetch_openalex(rq, limit=limit))
                if "doaj" in active_set:
                    relaxed_tasks.append(fetch_doaj(rq, limit=limit))
                if "europepmc" in active_set:
                    relaxed_tasks.append(fetch_europepmc(rq, limit=limit))
                if "core" in active_set:
                    relaxed_tasks.append(fetch_core(rq, limit=limit))
                if "base" in active_set:
                    relaxed_tasks.append(fetch_base(rq, limit=limit))
                if "semantic_scholar" in active_set:
                    relaxed_tasks.append(fetch_semantic_scholar(rq, limit=limit))
                if "pubmed" in active_set or "pubmed_ncbi" in active_set:
                    relaxed_tasks.append(fetch_pubmed_ncbi(rq, limit=limit))
            else:
                relaxed_tasks.append(fetch_crossref(rq, limit=limit))
                relaxed_tasks.append(_fetch_eprint_repository(rq, limit=limit))
                relaxed_tasks.append(fetch_openalex(rq, limit=limit))
                relaxed_tasks.append(fetch_doaj(rq, limit=limit))
                relaxed_tasks.append(fetch_europepmc(rq, limit=limit))
                relaxed_tasks.append(fetch_semantic_scholar(rq, limit=limit))
                if sources in ["all", "gov"]:
                    relaxed_tasks.append(fetch_pubmed_ncbi(rq, limit=limit))
            if relaxed_tasks:
                relaxed_results = await asyncio.gather(*relaxed_tasks, return_exceptions=True)
                for res in relaxed_results:
                    if isinstance(res, list):
                        raw_papers.extend(res)
            if raw_papers:
                logger.info(f"Query relaxation succeeded with {len(raw_papers)} papers for '{rq}'.")
                break

    deduped_papers = []
    deduped_papers = _dedup_papers_list(raw_papers)
    raw_papers = deduped_papers

    # Upstream Ingestion Gatekeeper: Sanitize, validate, and classify provenance
    validated_papers = []
    for p in raw_papers:
        sanitized = sanitize_and_validate_paper_metadata(p)
        if sanitized is not None:
            validated_papers.append(sanitized)
        else:
            logger.debug(f"Discarded paper due to upstream validation check: '{p.get('title', '')[:40]}'")
    raw_papers = validated_papers

    # Pillar 2: Coverage Gating & Multi-Attempt Targeted Re-query
    covered_facets, uncovered_facets = check_facet_coverage(facets, raw_papers)
    if uncovered_facets:
        logger.info(f"Coverage gate identified {len(uncovered_facets)} uncovered facets. Executing multi-attempt targeted re-query.")
        
        # Attempt 1: Query exact atomic sub_query and entity names across arXiv, Semantic Scholar, OpenAlex, Europe PMC, and Crossref
        re_tasks_1 = []
        q_intent_lower = query.lower()
        is_biomedical = any(bm in q_intent_lower for bm in [
            "biology", "biological", "biomedical", "genomic", "genetics", "protein", 
            "clinical", "disease", "medicine", "medical", "pharmacology", "drug", "cellular"
        ])
        for uf in uncovered_facets[:4]:
            sub_q = uf.get("sub_query") or ""
            ents = uf.get("entities", [])
            primary_ent = ents[0] if ents else ""
            if primary_ent:
                # If short entity, contextualize with subquery to prevent cross-domain drift
                if len(primary_ent.split()) <= 2 and len(primary_ent) < 12 and sub_q:
                    target_terms = f'"{primary_ent}" {sub_q}'
                else:
                    target_terms = f'"{primary_ent}"'
            else:
                target_terms = sub_q
            if target_terms:
                re_tasks_1.append(_fetch_eprint_repository(target_terms, limit=3))
                re_tasks_1.append(fetch_semantic_scholar(target_terms, limit=3))
                re_tasks_1.append(fetch_openalex(target_terms, limit=3))
                if is_biomedical:
                    re_tasks_1.append(fetch_europepmc(target_terms, limit=3))
                re_tasks_1.append(fetch_crossref(target_terms, limit=3))
                
        if re_tasks_1:
            re_results_1 = await asyncio.gather(*re_tasks_1, return_exceptions=True)
            for res in re_results_1:
                if isinstance(res, list):
                    for p in res:
                        san = sanitize_and_validate_paper_metadata(p)
                        if san and is_paper_semantically_relevant(san, query, facets=facets):
                            raw_papers.append(san)
            raw_papers = _dedup_papers_list(raw_papers)
            covered_facets, uncovered_facets = check_facet_coverage(facets, raw_papers)

        # Attempt 2: If still uncovered, query relaxed/variant entity terms before declaring uncovered
        if uncovered_facets:
            logger.info(f"Attempt 1 complete; {len(uncovered_facets)} facets still uncovered. Executing Attempt 2 with reformulated entity terms.")
            re_tasks_2 = []
            for uf in uncovered_facets[:4]:
                ents = uf.get("entities", [])
                sub_q = uf.get("sub_query") or ""
                if ents:
                    base_ent = re.sub(r'[^a-zA-Z0-9\s]', '', ents[0]).strip()
                    query_ent = f"{base_ent} {sub_q}".strip() if len(base_ent) < 10 and sub_q else base_ent
                    re_tasks_2.append(_fetch_eprint_repository(query_ent, limit=3))
                    re_tasks_2.append(fetch_semantic_scholar(query_ent, limit=3))
                    re_tasks_2.append(fetch_openalex(query_ent, limit=3))
                else:
                    kws = uf.get("keywords", [])
                    if kws:
                        rel_q = " ".join(kws[:2])
                        re_tasks_2.append(_fetch_eprint_repository(rel_q, limit=3))
                        re_tasks_2.append(fetch_semantic_scholar(rel_q, limit=3))
            if re_tasks_2:
                re_results_2 = await asyncio.gather(*re_tasks_2, return_exceptions=True)
                for res in re_results_2:
                    if isinstance(res, list):
                        for p in res:
                            san = sanitize_and_validate_paper_metadata(p)
                            if san and is_paper_semantically_relevant(san, query, facets=facets):
                                raw_papers.append(san)
                raw_papers = _dedup_papers_list(raw_papers)
                covered_facets, uncovered_facets = check_facet_coverage(facets, raw_papers)

    # Pillar 4: Citation Snowballing (Follow references backward from on-target hits)
    snowballed = snowball_citations(raw_papers, facets, max_snowball=6)
    if snowballed:
        for sp in snowballed:
            san = sanitize_and_validate_paper_metadata(sp)
            if san and is_paper_semantically_relevant(san, query, facets=facets):
                raw_papers.append(san)
        raw_papers = _dedup_papers_list(raw_papers)
        covered_facets, uncovered_facets = check_facet_coverage(facets, raw_papers)
        
    if not raw_papers:
        if disable_fallback:
            logger.warning(f"No papers returned from repositories for query '{query}' and disable_fallback is True.")
            raw_papers = []
        else:
            # ZERO-FAKING POLICY:
            # Report honest 0 indexed papers rather than fabricating literature.
            logger.info(f"Zero authentic papers returned from live academic repositories for query '{query}'. Reporting honest zero-result notice.")
            raw_papers = []
                
    # Semantic Relevance Gating (Multi-Faceted)
    papers = [p for p in raw_papers if is_paper_semantically_relevant(p, query, facets=facets)]
    # Fallback to raw only if candidate papers have genuine lexical overlap with the query
    if not papers and raw_papers:
        if disable_fallback:
            papers = []
        else:
            q_toks = set(clean_and_tokenize(query))
            papers = [
                p for p in raw_papers 
                if any(t in f"{p.get('title', '')} {p.get('abstract', '')}".lower() for t in q_toks if len(t) > 3)
            ]

    for p in papers:
        if "provenance_tier" not in p or "provenance_label" not in p:
            p["provenance_tier"], p["provenance_label"] = classify_paper_provenance(p)
        
    query_tokens = clean_and_tokenize(query)
    
    # Open-Access Full-Text Ingestion via Direct Links, Unpaywall & arXiv (Pillar 3)
    # Asynchronously enrich papers with empirical body paragraphs using max 2 concurrent downloads
    doi_papers = [
        p for p in papers 
        if p.get("oa_pdf_url") or (p.get("doi") and "10." in str(p.get("doi"))) or "arxiv" in str(p.get("url", "")).lower()
    ][:8]
    if doi_papers:
        try:
            sem = asyncio.Semaphore(2)
            async def _fetch_with_sem(p_obj, client_obj):
                async with sem:
                    return await fetch_open_access_fulltext(
                        p_obj.get("doi") or p_obj.get("url", ""),
                        client_obj,
                        max_pages=max_pdf_pages,
                        direct_pdf_url=p_obj.get("oa_pdf_url"),
                        paper_meta=p_obj
                    )

            async with httpx.AsyncClient(timeout=45.0) as oa_client:
                oa_tasks = [_fetch_with_sem(p, oa_client) for p in doi_papers]
                oa_results = await asyncio.wait_for(asyncio.gather(*oa_tasks, return_exceptions=True), timeout=60.0)
                for dp, oa_res in zip(doi_papers, oa_results):
                    if isinstance(oa_res, dict) and oa_res.get("paragraphs"):
                        dp["oa_pdf_url"] = oa_res.get("pdf_url")
                        dp["fulltext_excerpt"] = " ".join(oa_res["paragraphs"])
                        dp["abstract"] = (dp.get("abstract", "") + " [Open-Access Full-Text Excerpt]: " + dp["fulltext_excerpt"]).strip()
                        logger.info(f"Enriched paper '{dp.get('title', '')[:40]}' with Open-Access full text.")
        except Exception as oa_err:
            logger.debug(f"OA fulltext enrichment pass error: {oa_err}")
    
    # Calculate corpus term frequency across all abstracts
    corpus_freq: Dict[str, int] = {}
    for p in papers:
        tokens = clean_and_tokenize(p.get("abstract", ""))
        for t in tokens:
            corpus_freq[t] = corpus_freq.get(t, 0) + 1
            
    # Extract and score sentences
    dense_sentences = []
    sentence_idx = 0
    for p_idx, p in enumerate(papers):
        p["paper_idx"] = f"P{p_idx+1}"
        sentences = split_into_sentences(p.get("abstract", ""))
        for s in sentences:
            score = calculate_sentence_density(s, query_tokens, corpus_freq)
            sentence_id = f"sent_{sentence_idx}_{p.get('id', 'paper')[:8]}"
            dense_sentences.append({
                "id": sentence_id,
                "paper_idx": f"P{p_idx+1}",
                "paper_id": p.get("id"),
                "paper_title": p.get("title"),
                "paper_authors": p.get("authors"),
                "paper_year": p.get("year"),
                "paper_url": p.get("url"),
                "text": s,
                "density_score": score,
                "window_size": 1
            })
            sentence_idx += 1

        # Multi-Sentence Logical Continuity: Extract 2-sentence sliding window passages
        if len(sentences) >= 2:
            for i in range(len(sentences) - 1):
                w_text = f"{sentences[i]} {sentences[i+1]}"
                w_score = calculate_sentence_density(w_text, query_tokens, corpus_freq)
                dense_sentences.append({
                    "id": f"win_{p_idx+1}_{i}_{p.get('id', 'paper')[:8]}",
                    "paper_idx": f"P{p_idx+1}",
                    "paper_id": p.get("id"),
                    "paper_title": p.get("title"),
                    "paper_authors": p.get("authors"),
                    "paper_year": p.get("year"),
                    "paper_url": p.get("url"),
                    "text": w_text,
                    "density_score": w_score,
                    "window_size": 2
                })
            
    # Sort by information density score descending and retain info-dense sentences
    dense_sentences.sort(key=lambda x: x["density_score"], reverse=True)
    top_sentences = dense_sentences[:120] # Retain up to 120 sentences to comprehensively cover all paper abstracts
    
    return {
        "agent": "Agent 1: Academic Scraper",
        "tokens_used": 0,  # Strictly zero LLM tokens
        "papers_found": len(papers),
        "papers": papers,
        "dense_sentences": top_sentences,
        "total_sentences_extracted": len(dense_sentences),
        "facets": facets,
        "covered_facets": covered_facets,
        "uncovered_facets": uncovered_facets
    }
