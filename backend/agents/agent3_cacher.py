import math
import re
from typing import Dict, Any, List, Tuple
from backend.database import save_scraped_papers, save_cached_sentences, get_cached_sentences_for_query

def tokenize_words(text: str) -> List[str]:
    return re.findall(r'\b\w{2,}\b', text.lower())

def compute_cosine_similarity(text1: str, text2: str) -> float:
    """
    Computes word-vector cosine similarity with bigram weighting.
    Lightweight, deterministic, 0 tokens, sub-millisecond execution.
    """
    words1 = tokenize_words(text1)
    words2 = tokenize_words(text2)
    
    if not words1 or not words2:
        return 0.0

    # Also build bigrams for phrase match
    bi1 = [f"{words1[i]}_{words1[i+1]}" for i in range(len(words1)-1)]
    bi2 = [f"{words2[i]}_{words2[i+1]}" for i in range(len(words2)-1)]
    
    all_tokens1 = words1 + bi1
    all_tokens2 = words2 + bi2
    
    freq1: Dict[str, int] = {}
    for t in all_tokens1:
        freq1[t] = freq1.get(t, 0) + 1
        
    freq2: Dict[str, int] = {}
    for t in all_tokens2:
        freq2[t] = freq2.get(t, 0) + 1
        
    all_vocab = set(freq1.keys()).union(set(freq2.keys()))
    
    dot_product = 0.0
    for v in all_vocab:
        dot_product += freq1.get(v, 0) * freq2.get(v, 0)
        
    norm1 = math.sqrt(sum(c * c for c in freq1.values()))
    norm2 = math.sqrt(sum(c * c for c in freq2.values()))
    
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
        
    raw_sim = dot_product / (norm1 * norm2)
    
    # Substring bonus for verbatim extractions
    clean1 = " ".join(words1)
    clean2 = " ".join(words2)
    if clean1 in clean2 or clean2 in clean1:
        raw_sim = max(raw_sim, 0.96)
        
    return round(min(raw_sim, 1.0), 4)

def run_agent3_context_cacher(
    query: str,
    agent1_data: Dict[str, Any],
    agent2_data: Dict[str, Any],
    similarity_threshold: float = 0.80
) -> Dict[str, Any]:
    """
    Agent 3: Context Cacher & Pre-Filter (Automated Tool 2 - Zero LLM Tokens).
    1. Saves Agent 1's scraped context to SQLite cache.db.
    2. Calculates semantic similarity between Drafter's claims and cached text.
    3. Auto-verifies identical or high-similarity matches (>= similarity_threshold).
    4. Segregates unverified / disputed claims for Agent 4 to inspect.
    """
    papers = agent1_data.get("papers", [])
    dense_sentences = agent1_data.get("dense_sentences", [])
    claims = agent2_data.get("claims", [])
    
    # Step 1: Save to SQLite database
    save_scraped_papers(query, papers)
    save_cached_sentences(query, dense_sentences)
    
    # Step 2: Compare each claim against all cached sentences
    verified_claims = []
    unverified_claims = []
    comparison_logs = []
    
    for claim in claims:
        claim_id = claim.get("id")
        claim_text = claim.get("text", "").strip()
        
        best_sim = 0.0
        best_match_sentence = None
        best_match_paper_id = None
        best_match_paper_title = None
        
        for sent in dense_sentences:
            sim = compute_cosine_similarity(claim_text, sent.get("text", ""))
            if sim > best_sim:
                best_sim = sim
                best_match_sentence = sent.get("text")
                best_match_paper_id = sent.get("paper_id")
                best_match_paper_title = sent.get("paper_title")
                
        # Determine paper metadata
        matched_paper = next((p for p in papers if p.get("id") == best_match_paper_id), None)
        
        # Determine logical category if no strong match
        claim_category = "empirical_measurement"
        if best_sim < similarity_threshold:
            claim_lower = claim_text.lower()
            if "o(" in claim_lower or "scale" in claim_lower or "limit" in claim_lower or "bound" in claim_lower:
                claim_category = "theoretical_formulation"
            elif "architecture" in claim_lower or "overlap" in claim_lower or "pipeline" in claim_lower or "mechanism" in claim_lower:
                claim_category = "architectural_mechanism"

        eval_result = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "best_similarity": best_sim,
            "matched_sentence": best_match_sentence,
            "matched_paper_id": best_match_paper_id,
            "paper_title": matched_paper.get("title") if matched_paper else best_match_paper_title,
            "paper_url": matched_paper.get("url") if matched_paper else "#",
            "paper_authors": matched_paper.get("authors", []) if matched_paper else [],
            "paper_year": matched_paper.get("year", 2024) if matched_paper else 2024,
            "claim_category": claim_category
        }
        
        comparison_logs.append(eval_result)
        
        # Step 3: Check against similarity threshold
        if best_sim >= similarity_threshold:
            eval_result["status"] = "verified_by_cache"
            eval_result["confidence_score"] = round(0.90 + (best_sim * 0.09), 2)
            eval_result["verified_by"] = "Agent 3 (SQLite Cache Pre-Filter)"
            verified_claims.append(eval_result)
        else:
            eval_result["status"] = "needs_agent4_verification"
            eval_result["confidence_score"] = None
            eval_result["verified_by"] = "Pending Agent 4 Fact-Checker"
            unverified_claims.append(eval_result)
            
    return {
        "agent": "Agent 3: Context Cacher & Pre-Filter",
        "tokens_used": 0,  # Strictly zero LLM tokens
        "sqlite_database": "cache.db",
        "papers_cached": len(papers),
        "sentences_indexed": len(dense_sentences),
        "similarity_threshold": similarity_threshold,
        "auto_verified_count": len(verified_claims),
        "unverified_for_agent4_count": len(unverified_claims),
        "verified_claims": verified_claims,
        "unverified_claims": unverified_claims,
        "all_claim_evals": comparison_logs
    }
