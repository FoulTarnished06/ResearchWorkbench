"""
Passage Verifier & 3-Way Verdict Adjudicator (Tier 1 Verification Depth)
- Full-Text Semantic Chunking (200-400 words)
- Deterministic Exact-Match Number, Unit, and Metric Auditing (0 LLM Tokens)
- 3-Way Verdicts: SUPPORTED | CONTRADICTED | NOT_FOUND_IN_CHECKED_TEXT
- Explicit Scope Tracking: full_text vs. abstract
- Calibrated Confidence Categories
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from backend.logger import get_logger

logger = get_logger("PassageVerifier_v5")

# Numeric + Unit extraction regex pattern
NUMERIC_METRIC_PATTERN = re.compile(
    r'(?:\b|(?<=\s))(\d+(?:\.\d+)?)\s*(%|meV|eV|MAE|RMSE|AUROC|F1|ms|ns|fs|GHz|MHz|Å|kDa|mol|K|ppm|nm)?\b|'
    r'(\b[1-3]-WL\b)|\bO\([A-Za-z0-9\|\+\s\^]+\)',
    re.IGNORECASE
)

def chunk_paper_content(paper: Dict[str, Any], chunk_words: int = 250, overlap_words: int = 50) -> List[Dict[str, Any]]:
    """
    Tier 1 Innovation: Slices paper full-text or abstract into overlapping semantic windows.
    Tracks provenance scope (full_text vs abstract) for transparent verification depth.
    """
    chunks: List[Dict[str, Any]] = []
    
    full_text = paper.get("full_text", "")
    abstract = paper.get("abstract", "")
    
    # Prefer full text if available; fallback to abstract
    if full_text and full_text.strip():
        source_text = full_text.strip()
        scope = "full_text"
    elif abstract and abstract.strip():
        source_text = abstract.strip()
        scope = "abstract"
    else:
        return chunks

    words = source_text.split()
    if not words:
        return chunks

    step = max(1, chunk_words - overlap_words)
    chunk_idx = 0
    for i in range(0, len(words), step):
        passage_words = words[i:i + chunk_words]
        if not passage_words:
            break
        passage_text = " ".join(passage_words)
        chunks.append({
            "chunk_id": f"{paper.get('paper_idx', 'P?')}_c{chunk_idx}",
            "paper_idx": paper.get("paper_idx", "P?"),
            "paper_title": paper.get("title", ""),
            "venue": paper.get("venue", ""),
            "scope": scope,
            "text": passage_text,
            "word_count": len(passage_words)
        })
        chunk_idx += 1
        if i + chunk_words >= len(words):
            break

    return chunks

def extract_numerical_entities(text: str) -> List[str]:
    """Extract distinct numbers, metrics, asymptotic bounds, and percentages from text."""
    matches = NUMERIC_METRIC_PATTERN.findall(text)
    entities = []
    for m in matches:
        val = next((item for item in m if item), "")
        if val:
            entities.append(val.strip().lower())
    return list(set(entities))

def check_contradiction_cues(claim_text: str, chunk_text: str) -> bool:
    """Detect explicit semantic contradictions or opposite polarity."""
    negation_pairs = [
        ("exceed", "fail to exceed"),
        ("exceed", "strictly bounded"),
        ("exceed", "below"),
        ("eliminat", "suffer"),
        ("outperform", "inferior"),
        ("increas", "decreas"),
        ("linear", "quadratic"),
        ("superior", "inferior"),
        ("exceeding", "only"),
        ("ambient", "vacuum"),
        ("faster", "slower"),
        ("degrad", "improv")
    ]
    claim_lower = claim_text.lower()
    chunk_lower = chunk_text.lower()
    
    for word_a, word_b in negation_pairs:
        if (word_a in claim_lower and word_b in chunk_lower) or (word_b in claim_lower and word_a in chunk_lower):
            claim_kw = set(re.findall(r'[A-Za-z0-9\-]{4,}', claim_lower))
            chunk_kw = set(re.findall(r'[A-Za-z0-9\-]{4,}', chunk_lower))
            generic = {"spatial", "temporal", "neural", "system", "method", "model", "paper", "graph", "graphs", "limit"}
            specific_common = (claim_kw & chunk_kw) - generic
            if len(specific_common) >= 2:
                return True
    return False

def deterministic_exact_match_audit(
    claim_text: str, 
    chunks: List[Dict[str, Any]]
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Tier 1 Innovation: Exact-Match Number & Metric Check without an LLM.
    Verifies reported figures, units, and complexity notations directly against text.
    Returns (has_exact_match, matched_entity, best_matching_chunk).
    """
    claim_nums = extract_numerical_entities(claim_text)
    if not claim_nums:
        return False, None, None

    for chunk in chunks:
        chunk_text = chunk["text"]
        chunk_nums = extract_numerical_entities(chunk_text)
        
        shared = [num for num in claim_nums if num in chunk_nums]
        if shared:
            # Check sentence level topical proximity
            sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
            for s in sentences:
                s_nums = extract_numerical_entities(s)
                if any(num in s_nums for num in shared):
                    claim_keywords = [w.lower() for w in re.findall(r'[A-Za-z]{4,}', claim_text)]
                    s_keywords = [w.lower() for w in re.findall(r'[A-Za-z]{4,}', s)]
                    common_words = set(claim_keywords) & set(s_keywords)
                    generic = {"achieved", "scales", "complexity", "reported", "experiments"}
                    specific_common = common_words - generic
                    if len(specific_common) >= 1 or len(common_words) >= 2:
                        return True, shared[0], chunk

    return False, None, None

def compute_lexical_overlap(text_a: str, text_b: str) -> float:
    """Compute normalized token overlap ratio between two passages."""
    tokens_a = set(re.findall(r'\b[a-zA-Z]{3,}\b', text_a.lower()))
    tokens_b = set(re.findall(r'\b[a-zA-Z]{3,}\b', text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    return len(intersection) / len(tokens_a)

def adjudicate_claim_with_passages(
    claim: Dict[str, Any], 
    all_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Tier 1 Innovation: Comprehensive 3-Way Claim Adjudication with Scope Tracking.
    """
    claim_text = claim.get("claim", "")

    # 1. First check for explicit contradiction against all chunks
    contradiction_found = False
    contradiction_chunk: Optional[Dict[str, Any]] = None
    for chunk in all_chunks:
        if check_contradiction_cues(claim_text, chunk["text"]):
            contradiction_found = True
            contradiction_chunk = chunk
            break

    if contradiction_found and contradiction_chunk:
        return {
            "claim": claim_text,
            "verdict": "CONTRADICTED",
            "confidence_category": "CONTRADICTED",
            "numerical_confidence": 0.15,
            "scope_checked": contradiction_chunk["scope"],
            "exact_match_verified": False,
            "supporting_passage": contradiction_chunk["text"][:300] + "...",
            "source_paper": contradiction_chunk["paper_title"],
            "source_idx": contradiction_chunk["paper_idx"]
        }

    # 2. Check deterministic exact-match for numbers/units
    claim_nums = extract_numerical_entities(claim_text)
    exact_match, matched_num, best_chunk = deterministic_exact_match_audit(claim_text, all_chunks)
    if exact_match and best_chunk:
        return {
            "claim": claim_text,
            "verdict": "SUPPORTED",
            "confidence_category": "HIGH_CONFIDENCE",
            "numerical_confidence": 0.95,
            "scope_checked": best_chunk["scope"],
            "exact_match_verified": True,
            "matched_entity": matched_num,
            "supporting_passage": best_chunk["text"][:300] + "...",
            "source_paper": best_chunk["paper_title"],
            "source_idx": best_chunk["paper_idx"]
        }

    # If the claim contains specific numerical figures/metrics, it CANNOT be marked
    # SUPPORTED via lexical overlap alone unless at least one number matched!
    if claim_nums:
        # Check if the corpus contains conflicting numbers for the same keywords
        for chunk in all_chunks:
            chunk_nums = extract_numerical_entities(chunk["text"])
            if chunk_nums and not any(num in chunk_nums for num in claim_nums):
                claim_kw = set(re.findall(r'[A-Za-z]{4,}', claim_text.lower()))
                chunk_kw = set(re.findall(r'[A-Za-z]{4,}', chunk["text"].lower()))
                if len(claim_kw & chunk_kw) >= 3:
                    return {
                        "claim": claim_text,
                        "verdict": "CONTRADICTED",
                        "confidence_category": "CONTRADICTED",
                        "numerical_confidence": 0.10,
                        "scope_checked": chunk["scope"],
                        "exact_match_verified": False,
                        "supporting_passage": chunk["text"][:300] + "...",
                        "source_paper": chunk["paper_title"],
                        "source_idx": chunk["paper_idx"]
                    }
        # If numbers didn't match and no explicit contradiction, it is NOT_FOUND_IN_CHECKED_TEXT
        return {
            "claim": claim_text,
            "verdict": "NOT_FOUND_IN_CHECKED_TEXT",
            "confidence_category": "UNVERIFIED",
            "numerical_confidence": 0.25,
            "scope_checked": "full_text" if any(c["scope"] == "full_text" for c in all_chunks) else "abstract",
            "exact_match_verified": False,
            "supporting_passage": "Specific numeric quantity or metric not verified in ingested literature.",
            "source_paper": "Unverified against literature",
            "source_idx": "N/A"
        }

    # 3. Semantic passage search for non-numerical claims
    best_overlap = 0.0
    best_candidate_chunk: Optional[Dict[str, Any]] = None
    for chunk in all_chunks:
        overlap = compute_lexical_overlap(claim_text, chunk["text"])
        if overlap > best_overlap:
            best_overlap = overlap
            best_candidate_chunk = chunk

    if best_overlap >= 0.50 and best_candidate_chunk:
        return {
            "claim": claim_text,
            "verdict": "SUPPORTED",
            "confidence_category": "HIGH_CONFIDENCE" if best_candidate_chunk["scope"] == "full_text" else "MODERATE_CONFIDENCE",
            "numerical_confidence": 0.85,
            "scope_checked": best_candidate_chunk["scope"],
            "exact_match_verified": False,
            "supporting_passage": best_candidate_chunk["text"][:300] + "...",
            "source_paper": best_candidate_chunk["paper_title"],
            "source_idx": best_candidate_chunk["paper_idx"]
        }

    # 4. Default: NOT_FOUND_IN_CHECKED_TEXT
    scope_checked = best_candidate_chunk["scope"] if best_candidate_chunk else "abstract"
    return {
        "claim": claim_text,
        "verdict": "NOT_FOUND_IN_CHECKED_TEXT",
        "confidence_category": "UNVERIFIED",
        "numerical_confidence": 0.35,
        "scope_checked": scope_checked,
        "exact_match_verified": False,
        "supporting_passage": "No direct confirming or refuting passage identified within the ingested texts.",
        "source_paper": "Unverified against literature",
        "source_idx": "N/A"
    }

def verify_all_claims_depth(
    claims: List[Dict[str, Any]], 
    papers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Verifies an entire set of extracted claims against all ingested papers using
    full-text passages, exact numeric matches, and 3-way verdicts.
    """
    # 1. Chunk all papers into passages
    all_chunks: List[Dict[str, Any]] = []
    full_text_count = 0
    abstract_count = 0
    for p in papers:
        p_chunks = chunk_paper_content(p)
        all_chunks.extend(p_chunks)
        if any(c["scope"] == "full_text" for c in p_chunks):
            full_text_count += 1
        elif p_chunks:
            abstract_count += 1

    # 2. Adjudicate each claim
    evaluated_claims = []
    verdict_counts = {
        "SUPPORTED": 0,
        "CONTRADICTED": 0,
        "NOT_FOUND_IN_CHECKED_TEXT": 0
    }
    exact_matches_count = 0

    for cl in claims:
        adj = adjudicate_claim_with_passages(cl, all_chunks)
        evaluated_claims.append(adj)
        verdict_counts[adj["verdict"]] = verdict_counts.get(adj["verdict"], 0) + 1
        if adj.get("exact_match_verified"):
            exact_matches_count += 1

    return {
        "evaluated_claims": evaluated_claims,
        "verdict_summary": verdict_counts,
        "exact_matches_count": exact_matches_count,
        "total_chunks_inspected": len(all_chunks),
        "full_text_papers_count": full_text_count,
        "abstract_papers_count": abstract_count
    }
