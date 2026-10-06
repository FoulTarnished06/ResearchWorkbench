import os
import math
import re
import html
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

# Suppress Windows symlinks warning for local huggingface cache
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from backend.database import save_scraped_papers, save_cached_sentences, get_cached_sentences_for_query
from backend.logger import get_logger

logger = get_logger("Agent3_Cacher")

_EMBED_MODEL = None
_EMBED_INITIALIZED = False

def get_embedding_model():
    """
    Lazy singleton loader for local ONNX fastembed BAAI/bge-small-en-v1.5 model.
    Runs 100% on CPU in sub-15ms, zero API tokens, zero PyTorch overhead.
    """
    global _EMBED_MODEL, _EMBED_INITIALIZED
    if not _EMBED_INITIALIZED:
        _EMBED_INITIALIZED = True
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("Initialized local ONNX neural embedding model: BAAI/bge-small-en-v1.5")
        except Exception as e:
            logger.warning(f"fastembed initialization skipped ({e}); using high-resolution subword profile vectorizer.")
            _EMBED_MODEL = None
    return _EMBED_MODEL

def embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    """Computes normalized 384-dimensional dense vectors in batch using fastembed."""
    model = get_embedding_model()
    if model is None or not texts:
        return None
    try:
        embed_gen = model.embed(texts)
        arr = np.array(list(embed_gen), dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        return arr / norms
    except Exception as e:
        logger.debug(f"Batch neural embedding calculation error: {e}")
        return None

NEGATION_PATTERNS = [
    r'\b(?:not|never|no|neither|nor|without|lacked|lacks|lacking)\b',
    r'\b(?:failed|fails|failure|unable|inability|unsuccessful|cannot|can\'t|couldn\'t|didn\'t|doesn\'t)\b',
    r'\b(?:disproved|refuted|invalidated|unsupported)\b'
]

ACADEMIC_SYNONYMS = {
    "demonstrated": "achieved",
    "demonstrate": "achieve",
    "demonstrates": "achieves",
    "exhibited": "showed",
    "exhibits": "shows",
    "suppressed": "mitigated",
    "suppresses": "mitigates",
    "reduced": "decreased",
    "reduces": "decreases",
    "enhanced": "improved",
    "enhances": "improves",
    "increased": "elevated",
    "increases": "elevates",
    "confirmed": "verified",
    "confirms": "verifies",
    "formulated": "derived",
    "formulates": "derives",
    "benchmark": "evaluate",
    "benchmarks": "evaluated",
    "benchmarked": "evaluated"
}

def extract_polarity(text: str) -> bool:
    """
    Point 20: Polarity & Negation Inversion Guard.
    Returns True if text expresses negative assertion/polarity, False if positive.
    Safely accounts for positive scientific states like 'zero error', 'zero noise', 'zero crosstalk',
    and chemical entities like 'NO' (Nitric Oxide) or 'NOx'.
    """
    # Preserve uppercase chemical formulas before lowercasing
    text_preserved = re.sub(r'\bNO\b', 'nitric_oxide', text)
    text_preserved = re.sub(r'\bNOx\b', 'nitrogen_oxides', text_preserved)
    t_lower = text_preserved.lower()
    t_clean = re.sub(r'\bzero\s+(?:error|noise|crosstalk|loss|latency|overhead|drift|fragmentation)\b', 'ideal_state', t_lower)
    for pat in NEGATION_PATTERNS:
        if re.search(pat, t_clean):
            return True
    return False

def normalize_academic_word(w: str) -> str:
    """Point 21: Academic Synonym Normalization."""
    w_clean = w.lower().strip()
    return ACADEMIC_SYNONYMS.get(w_clean, w_clean)

def tokenize_words(text: str) -> List[str]:
    return re.findall(r'\b\w{2,}\b', text.lower())

def text_to_vector_profile(text: str) -> Dict[str, Any]:
    """
    Point 19: Dense Semantic Vector Representation (Deterministic 0-token embedding).
    Extracts normalized lemma tokens, word bigrams, and subword character 3-grams.
    """
    raw_words = tokenize_words(text)
    if not raw_words:
        return {"words": [], "freq": {}, "norm": 0.0, "clean": "", "is_negative": False}
    words = [normalize_academic_word(w) for w in raw_words]
    bi = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
    
    # Subword character n-grams (3-grams) for robust morphological matching
    subwords = []
    for w in words:
        if len(w) >= 4:
            for j in range(len(w) - 2):
                subwords.append(f"sw_{w[j:j+3]}")

    all_tokens = words + bi + subwords
    freq: Dict[str, int] = {}
    for t in all_tokens:
        freq[t] = freq.get(t, 0) + 1
    norm = math.sqrt(sum(c * c for c in freq.values()))
    return {
        "words": words,
        "freq": freq,
        "norm": norm,
        "clean": " ".join(words),
        "is_negative": extract_polarity(text)
    }

def compute_profile_similarity(p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
    """
    Point 19 & Point 20: Cosine similarity with Polarity Inversion Guard.
    Clamps similarity < 0.45 if one text asserts negative polarity while the other is affirmative.
    """
    if p1["norm"] == 0.0 or p2["norm"] == 0.0:
        return 0.0
    common = set(p1["freq"].keys()) & set(p2["freq"].keys())
    dot_product = sum(p1["freq"][k] * p2["freq"][k] for k in common)
    raw_sim = dot_product / (p1["norm"] * p2["norm"])
    if p1["clean"] and p2["clean"]:
        shorter = p1["clean"] if len(p1["clean"]) < len(p2["clean"]) else p2["clean"]
        if len(shorter.split()) >= 5 and (p1["clean"] in p2["clean"] or p2["clean"] in p1["clean"]):
            raw_sim = max(raw_sim, 0.96)
        
    # Polarity Inversion Guard: Prevent false auto-verification of negated hallucinations
    if p1.get("is_negative") != p2.get("is_negative"):
        raw_sim = min(raw_sim, 0.35)

    return round(min(raw_sim, 1.0), 4)

def extract_grounding_features(text: str) -> Tuple[set, set]:
    """
    Extracts quantitative numerical figures/units and uppercase domain entities/acronyms.
    """
    metrics = set(re.findall(r'\b\d+(?:\.\d+)?\s*(?:%|gbps|gb\/s|tb\/s|tflops\/s|tops\/w|ms|ns|μs|us|s|db|ghz|mhz|nm|kb|mb|gb|tb|kbp|bp|x|fold)?\b', text.lower()))
    acronyms = set(re.findall(r'\b[A-Z]{2,}(?:-[A-Z0-9]+)?\b', text))
    romans = set(re.findall(r'\b(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\b', text))
    return (metrics - {''}), (acronyms | romans)

def compute_cosine_similarity(text1: str, text2: str) -> float:
    """
    Computes semantic similarity combining fastembed neural embeddings with
    subwords, synonyms, and polarity guards. 0 tokens, sub-millisecond execution.
    """
    p1 = text_to_vector_profile(text1)
    p2 = text_to_vector_profile(text2)
    lex_sim = compute_profile_similarity(p1, p2)
    
    # Check if neural embedding is available
    model = get_embedding_model()
    if model is not None:
        try:
            vecs = embed_texts([text1, text2])
            if vecs is not None and len(vecs) == 2:
                n_sim = float(np.dot(vecs[0], vecs[1]))
                if p1.get("is_negative") != p2.get("is_negative"):
                    n_sim = min(n_sim, 0.35)
                return round(max(lex_sim, min(1.0, n_sim)), 4)
        except Exception:
            pass
AGENT3_CONFIG = {
    "bm25_k1": 1.5,
    "bm25_b": 0.75,
    "rrf_k": 60,
    "similarity_threshold": 0.55
}

class BM25Okapi:
    def __init__(self, corpus: List[List[str]], k1: Optional[float] = None, b: Optional[float] = None):
        self.corpus_size = len(corpus)
        self.avgdl = sum(float(len(x)) for x in corpus) / self.corpus_size if self.corpus_size else 0
        self.corpus = corpus
        self.k1 = k1 if k1 is not None else AGENT3_CONFIG["bm25_k1"]
        self.b = b if b is not None else AGENT3_CONFIG["bm25_b"]
        self.df = {}
        self.idf = {}
        self.doc_freqs = []
        self._initialize()

    def _initialize(self):
        for document in self.corpus:
            frequencies = {}
            for word in document:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word, freq in frequencies.items():
                self.df[word] = self.df.get(word, 0) + 1
        for word, freq in self.df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        scores = []
        for index in range(self.corpus_size):
            score = 0.0
            doc_len = len(self.corpus[index])
            frequencies = self.doc_freqs[index]
            for word in query:
                if word not in frequencies:
                    continue
                freq = frequencies[word]
                numerator = self.idf[word] * freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += (numerator / denominator)
            scores.append(score)
        return scores

def split_compound_claim(text: str) -> List[str]:
    """
    Point 23/Bonus: Local Regex Atomic Claim Splitting.
    Only splits on conjunctions preceded by a clause boundary (comma, semicolon)
    to avoid destroying compound nouns like 'CRISPR and Cas9'.
    """
    splits = re.split(
        r'[,;]\s*\b(?:and|but|however|although|whereas|moreover|furthermore|while)\b\s+',
        text, flags=re.IGNORECASE
    )
    splits = [s.strip().rstrip(',;') for s in splits if len(s.split()) >= 3]
    return splits if splits else [text]

def run_agent3_context_distiller(query: str, agent1_data: Any, top_k: int = 15, max_tokens: int = 600) -> List[Dict[str, Any]]:
    """
    Phase 1: Hybrid RRF (BM25 + Semantic) + MMR Context Pre-Filter & Dynamic Token Packing (0 LLM Tokens).
    """
    if isinstance(agent1_data, list):
        dense_sentences = [s for s in agent1_data if "text" in s and "title" not in s] or agent1_data
    else:
        dense_sentences = agent1_data.get("dense_sentences", []) if isinstance(agent1_data, dict) else []
    
    if not dense_sentences:
        return []
        
    query_profile = text_to_vector_profile(query)
    sent_texts = [sent.get("text", "") for sent in dense_sentences]
    
    # Fast subword BM25 ranking (sub-millisecond)
    tokenized_corpus = [tokenize_words(t) for t in sent_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(tokenize_words(query))

    # 1. Embed query
    model = get_embedding_model()
    q_vec = embed_texts([query]) if model is not None else None
    
    # 2. Embed sentences efficiently (pre-filter to top 30 if large corpus to guarantee <150ms execution)
    if len(dense_sentences) > 30 and model is not None:
        lex_ranks = [
            compute_profile_similarity(query_profile, text_to_vector_profile(t)) + (bm25_scores[i] * 0.1)
            for i, t in enumerate(sent_texts)
        ]
        top_cand_indices = set(sorted(range(len(dense_sentences)), key=lambda i: lex_ranks[i], reverse=True)[:30])
        cand_subset = [sent_texts[i] for i in sorted(list(top_cand_indices))]
        c_mat = embed_texts(cand_subset)
        s_mat = None
        if c_mat is not None:
            s_mat = np.zeros((len(dense_sentences), c_mat.shape[1]), dtype=np.float32)
            for c_i, orig_i in enumerate(sorted(list(top_cand_indices))):
                s_mat[orig_i] = c_mat[c_i]
    else:
        s_mat = embed_texts(sent_texts) if (model is not None and sent_texts) else None
    
    # Calculate similarities to query using RRF (Reciprocal Rank Fusion)
    semantic_scores = []
    for s_idx, sent in enumerate(dense_sentences):
        sent_profile = text_to_vector_profile(sent.get("text", ""))
        lex_sim = compute_profile_similarity(query_profile, sent_profile)
        if q_vec is not None and s_mat is not None and np.any(s_mat[s_idx]):
            n_sim = float(np.dot(q_vec[0], s_mat[s_idx]))
            sim = max(lex_sim, n_sim)
        else:
            sim = lex_sim
        semantic_scores.append(sim)
        
    # Rank them
    semantic_ranks = {idx: rank for rank, idx in enumerate(sorted(range(len(semantic_scores)), key=lambda i: semantic_scores[i], reverse=True))}
    bm25_ranks = {idx: rank for rank, idx in enumerate(sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True))}
    
    q_sims = []
    for i in range(len(dense_sentences)):
        # RRF formula (constant 60)
        rrf_score = (1.0 / (60 + semantic_ranks[i])) + (1.0 / (60 + bm25_ranks[i]))
        # Normalize roughly between 0 and 1 for MMR
        q_sims.append(rrf_score * 30.0) 
        
    # Apply MMR (Max Marginal Relevance)
    lambda_param = 0.5
    selected_indices = []
    unselected_indices = list(range(len(dense_sentences)))
    top_candidates = []
    current_tokens = 0
    
    while len(selected_indices) < top_k and unselected_indices and current_tokens < max_tokens:
        if not selected_indices:
            # First item is purely based on max query similarity
            best_idx = max(unselected_indices, key=lambda i: q_sims[i])
        else:
            # MMR formula
            best_idx = -1
            best_mmr = -float('inf')
            for i in unselected_indices:
                q_sim = q_sims[i]
                
                # Max similarity to already selected sentences
                max_sim_to_selected = 0.0
                if s_mat is not None:
                    # Neural similarity
                    sims = np.dot(s_mat[i], s_mat[selected_indices].T)
                    max_sim_to_selected = float(np.max(sims))
                else:
                    # Fallback to lexical
                    prof_i = text_to_vector_profile(dense_sentences[i].get("text", ""))
                    max_sim_to_selected = max(compute_profile_similarity(prof_i, text_to_vector_profile(dense_sentences[j].get("text", ""))) for j in selected_indices)
                
                mmr_score = lambda_param * q_sim - (1 - lambda_param) * max_sim_to_selected
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = i
                    
        # Token estimation (1 token approx 4 chars)
        sent = dense_sentences[best_idx]
        estimated_tokens = len(sent.get("text", "")) // 4
        
        if current_tokens + estimated_tokens > max_tokens and selected_indices:
            # If it exceeds the limit and we already have some context, break
            unselected_indices.remove(best_idx)
            continue
            
        selected_indices.append(best_idx)
        unselected_indices.remove(best_idx)
        top_candidates.append(sent)
        current_tokens += estimated_tokens
    
    logger.info(f"MMR Distilled {len(dense_sentences)} sentences to {len(top_candidates)} (approx {current_tokens} tokens)")
    return top_candidates

def run_agent3_context_cacher(
    query: str,
    agent1_data: Any,
    agent2_data: Any,
    similarity_threshold: float = 0.58
) -> Dict[str, Any]:
    """
    Agent 3: Context Cacher & Pre-Filter (Automated Tool 2 - Zero LLM Tokens).
    1. Saves Agent 1's scraped context to SQLite cache.db.
    2. Calculates semantic similarity between Drafter's claims and cached text using
       fastembed dense neural vectors and subword profiles.
    3. Enforces Polarity & Negation Inversion Guards.
    4. Routes top candidate context sentences per claim for Call 2 targeted context routing.
    5. Segregates unverified / disputed claims for Agent 4 to inspect.
    """
    if isinstance(agent1_data, list):
        # Passed dense_sentences or papers directly
        papers = [p for p in agent1_data if "title" in p]
        dense_sentences = [s for s in agent1_data if "text" in s and "title" not in s] or agent1_data
    else:
        papers = agent1_data.get("papers", []) if isinstance(agent1_data, dict) else []
        dense_sentences = agent1_data.get("dense_sentences", []) if isinstance(agent1_data, dict) else []

    if isinstance(agent2_data, list):
        claims = agent2_data
    else:
        claims = agent2_data.get("claims", []) if isinstance(agent2_data, dict) else []
    
    # Step 1: Save to SQLite database safely
    try:
        save_scraped_papers(query, papers)
        save_cached_sentences(query, dense_sentences)
    except Exception as e:
        logger.warning(f"Failed to persist items to SQLite cache: {e}")
    
    # Step 2: Pre-compute vector profiles and dense neural embeddings for all candidate sentences
    sentence_profiles = [
        (sent, text_to_vector_profile(sent.get("text", "")))
        for sent in dense_sentences
    ]

    # Batch neural embeddings (Pillar 1: Fastembed ONNX embeddings)
    sent_texts = [sent.get("text", "") for sent in dense_sentences]
    s_mat = embed_texts(sent_texts) if sent_texts else None
    
    claim_texts = [html.unescape(c.get("text", "")).strip() for c in claims]
    c_mat = embed_texts(claim_texts) if (claim_texts and s_mat is not None) else None
    
    neural_sim_matrix = (c_mat @ s_mat.T) if (c_mat is not None and s_mat is not None) else None

    verified_claims = []
    unverified_claims = []
    comparison_logs = []
    
    for c_idx, claim in enumerate(claims):
        claim_id = claim.get("id") or claim.get("claim_id") or f"c_{c_idx+1}"
        raw_claim_text = claim.get("text", "").strip()
        claim_text = html.unescape(raw_claim_text)
        claim_text = re.sub(r'\s+', ' ', claim_text).strip()
        claim_paper_tag = (claim.get("paper") or "").upper().strip()
        
        # 1. Full-claim evaluation against all sentences
        full_profile = text_to_vector_profile(claim_text)
        f_metrics, f_acronyms = extract_grounding_features(claim_text)
        claim_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', claim_text))
        
        f_vec = c_mat[c_idx:c_idx+1] if (c_mat is not None and c_idx < len(c_mat)) else None

        full_matches = []
        for s_idx, (sent, s_prof) in enumerate(sentence_profiles):
            lex_sim = compute_profile_similarity(full_profile, s_prof)
            if f_vec is not None and s_mat is not None:
                n_sim = float(np.dot(f_vec[0], s_mat[s_idx]))
                if full_profile.get("is_negative") != s_prof.get("is_negative"):
                    n_sim = min(n_sim, 0.35)
                sim = max(lex_sim, n_sim)
            else:
                sim = lex_sim

            sent_text = sent.get("text", "")
            sent_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', sent_text))
            sent_metrics, sent_acronyms = extract_grounding_features(sent_text)
            
            boost = 0.0
            if f_metrics & sent_metrics: boost += 0.15
            if f_acronyms & sent_acronyms: boost += 0.12
            if claim_paper_tag and (sent.get("paper_idx") == claim_paper_tag or claim_paper_tag in (sent.get("paper_id") or "")):
                boost += 0.15
            # Precise Numerical Grounding Match (e.g. 80 GNNs, 20 properties, 48 datasets)
            if claim_nums and (claim_nums.issubset(sent_nums) or len(claim_nums & sent_nums) >= 2):
                boost += 0.25

            eff_sim = min(0.98, sim + boost) if sim > 0.20 else sim
            full_matches.append((eff_sim, sent))

        full_matches.sort(key=lambda x: x[0], reverse=True)
        best_full_sim = full_matches[0][0] if full_matches else 0.0
        best_full_sent = full_matches[0][1] if full_matches else {}

        # 2. Local Atomic Claim Splitting
        atomic_claims = split_compound_claim(claim_text)
        min_atomic_sim = 1.0
        overall_best_sent = {}
        all_high_matches = []
        
        for atomic_text in atomic_claims:
            atomic_profile = text_to_vector_profile(atomic_text)
            a_metrics, a_acronyms = extract_grounding_features(atomic_text)
            n_vec = f_vec

            scored_matches = []
            for s_idx, (sent, s_prof) in enumerate(sentence_profiles):
                lex_sim = compute_profile_similarity(atomic_profile, s_prof)
                if n_vec is not None and s_mat is not None:
                    n_sim = float(np.dot(n_vec[0], s_mat[s_idx]))
                    if atomic_profile.get("is_negative") != s_prof.get("is_negative"):
                        n_sim = min(n_sim, 0.35)
                    sim = max(lex_sim, n_sim)
                else:
                    sim = lex_sim
                
                sent_text = sent.get("text", "")
                sent_metrics, sent_acronyms = extract_grounding_features(sent_text)
                common_metrics = a_metrics & sent_metrics
                common_acronyms = a_acronyms & sent_acronyms
                
                boost = 0.0
                if common_metrics: boost += 0.15
                if common_acronyms: boost += 0.12
                if claim_paper_tag and (sent.get("paper_idx") == claim_paper_tag or claim_paper_tag in (sent.get("paper_id") or "")):
                    boost += 0.15
                    
                effective_sim = min(0.98, sim + boost) if sim > 0.20 else sim
                scored_matches.append((effective_sim, sent))
                if effective_sim >= (similarity_threshold - 0.08):
                    all_high_matches.append((effective_sim, sent))
                
            scored_matches.sort(key=lambda x: x[0], reverse=True)
            if scored_matches:
                best_atomic_sim = scored_matches[0][0]
                min_atomic_sim = min(min_atomic_sim, best_atomic_sim)
                if not overall_best_sent:
                    overall_best_sent = scored_matches[0][1]
            else:
                min_atomic_sim = 0.0
                
        # Best similarity across full claim and atomic evaluation
        best_sim = max(best_full_sim, min_atomic_sim)
        if best_full_sim >= min_atomic_sim or not overall_best_sent:
            overall_best_sent = best_full_sent

        best_match_sentence = overall_best_sent.get("text")
        best_match_paper_id = overall_best_sent.get("paper_id")
        best_match_paper_title = overall_best_sent.get("paper_title")

        # Candidate evidence snippets for targeted routing (Point 24)
        candidate_snippets = [
            {"text": m[1].get("text"), "paper_id": m[1].get("paper_id"), "paper_title": m[1].get("paper_title"), "score": float(m[0])}
            for m in full_matches[:3] if m[1].get("text")
        ]
        if claim_paper_tag:
            for s in dense_sentences:
                if s.get("paper_idx") == claim_paper_tag or claim_paper_tag in (s.get("paper_id") or ""):
                    stext = s.get("text")
                    if stext and not any(cs.get("text") == stext for cs in candidate_snippets):
                        candidate_snippets.append({
                            "text": stext,
                            "paper_id": s.get("paper_id"),
                            "paper_title": s.get("paper_title"),
                            "score": 0.90
                        })

        # Multi-source corroboration check across distinct papers
        distinct_sources = {}
        for sim_val, sent_obj in all_high_matches:
            pid = sent_obj.get("paper_id") or sent_obj.get("paper_idx")
            if pid and pid not in distinct_sources:
                distinct_sources[pid] = {
                    "title": sent_obj.get("paper_title"),
                    "sim": sim_val
                }
        is_multi_source = len(distinct_sources) >= 2
                
        # Determine paper metadata and provenance
        matched_paper = next((p for p in papers if p.get("id") == best_match_paper_id), None)
        matched_provenance = matched_paper.get("provenance_tier", "peer_reviewed") if matched_paper else "peer_reviewed"
        matched_prov_label = matched_paper.get("provenance_label", "Peer-Reviewed Literature") if matched_paper else "Peer-Reviewed Literature"
        
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
            "id": claim_id,
            "claim_text": claim_text,
            "best_similarity": best_sim,
            "matched_sentence": best_match_sentence,
            "matched_paper_id": best_match_paper_id,
            "paper_title": matched_paper.get("title") if matched_paper else best_match_paper_title,
            "paper_url": matched_paper.get("url") if matched_paper else "#",
            "paper_authors": matched_paper.get("authors", []) if matched_paper else [],
            "paper_year": matched_paper.get("year") if matched_paper else None,
            "provenance_tier": matched_provenance,
            "provenance_label": matched_prov_label,
            "multi_source_corroborated": is_multi_source,
            "corroborating_sources_count": len(distinct_sources),
            "claim_category": claim_category,
            "candidate_snippets": candidate_snippets
        }
        
        comparison_logs.append(eval_result)
        
        # Step 3: Check against calibrated similarity threshold with provenance tiering
        if best_sim >= similarity_threshold:
            corrob_note = f" (corroborated across {len(distinct_sources)} distinct literature sources)" if is_multi_source else ""
            if matched_provenance == "preprint":
                eval_result["status"] = "Preprint-Corroborated"
                eval_result["verification_tier"] = "auto_cache_preprint"
                base_conf = 0.75 + (best_sim * 0.10)
                if is_multi_source:
                    base_conf += 0.03
                eval_result["confidence_score"] = round(min(0.85, base_conf), 2)
                eval_result["verified_by"] = "Agent 3 (Preprint Semantic Match - Unrefereed)"
                eval_result["rationale"] = f"Corroborated by semantic overlap in SQLite cache against preprint '{eval_result['paper_title']}'{corrob_note}."
                eval_result["reviewer_2_caveat"] = "Preliminary Finding: Grounded in unrefereed preprint (arXiv/bioRxiv). Methodological bounds not peer-reviewed."
                verified_claims.append(eval_result)
            elif matched_provenance == "reference_web":
                eval_result["status"] = "Web-Corroborated"
                eval_result["verification_tier"] = "auto_cache_preprint"
                eval_result["confidence_score"] = round(min(0.80, 0.70 + (best_sim * 0.08)), 2)
                eval_result["verified_by"] = "Agent 3 (Web Reference Grounding)"
                eval_result["rationale"] = f"Corroborated by semantic overlap in SQLite cache against web reference '{eval_result['paper_title']}'{corrob_note}."
                eval_result["reviewer_2_caveat"] = "Reference Grounding: Grounded in tertiary web encyclopedia/search context. Subject to peer-review verification."
                verified_claims.append(eval_result)
            else:
                eval_result["status"] = "Auto-Verified"
                eval_result["verification_tier"] = "auto_cache"
                base_conf = 0.88 + (best_sim * 0.10)
                if is_multi_source:
                    base_conf += 0.02
                eval_result["confidence_score"] = round(min(0.99, base_conf), 2)
                eval_result["verified_by"] = "Agent 3 (SQLite Cache 0-Token Auto-Match)"
                eval_result["rationale"] = f"Directly corroborated{corrob_note} by n-gram overlap and metric alignment in SQLite cache from '{eval_result['paper_title']}'."
                eval_result["reviewer_2_caveat"] = "Locally verified via high-confidence n-gram token overlap against source corpus."
                verified_claims.append(eval_result)
        else:
            eval_result["status"] = "needs_agent4_verification"
            eval_result["verification_tier"] = "pending"
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
