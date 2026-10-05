"""
System B: Conventional RAG Baseline
Retrieves academic papers using standard search, performs dense vector
embedding similarity to select top-k chunks, and generates a research monograph
via a single augmented LLM call without multi-agent verification or claim caching.
"""

import os
import time
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from backend.logger import get_logger
from backend.agents.agent1_scraper import run_agent1_academic_scraper
from backend.agents.agent2_drafter import (
    AGENT2_PINNED_SYSTEM_INSTRUCTION,
    call_anthropic_api,
    call_gemini_api,
    call_openai_api,
    resolve_anthropic_model,
    resolve_openai_model,
    TokenCount
)
from backend.agents.agent3_cacher import (
    embed_texts,
    compute_profile_similarity,
    text_to_vector_profile
)

logger = get_logger("ConventionalRAGSystem")


@dataclass
class RetrievedChunk:
    title: str
    source_venue: str
    url: str
    text: str
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source_venue": self.source_venue,
            "url": self.url,
            "text": self.text,
            "similarity_score": round(self.similarity_score, 4)
        }


@dataclass
class ConventionalRAGResult:
    system_name: str
    query: str
    model: str
    provider: str
    output_text: str
    retrieved_chunks: List[RetrievedChunk]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_seconds: float
    retrieval_latency: float
    retrieved_sources_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "query": self.query,
            "model": self.model,
            "provider": self.provider,
            "output_text": self.output_text,
            "retrieved_chunks": [c.to_dict() for c in self.retrieved_chunks],
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": round(self.latency_seconds, 2),
            "retrieval_latency": round(self.retrieval_latency, 2),
            "retrieved_sources_count": self.retrieved_sources_count
        }


class ConventionalRAGSystem:
    """
    Conventional RAG baseline: Vector retrieval (Top-K) + Single Augmented Generation Call.
    """

    def __init__(self, model_pref: str = "claude-sonnet-5.5", provider: Optional[str] = None, top_k: int = 5):
        self.model_pref = model_pref or "claude-sonnet-5.5"
        self.top_k = max(1, int(top_k))
        pref_lower = self.model_pref.lower()
        if provider:
            self.provider = provider.lower()
        elif any(x in pref_lower for x in ["gpt", "sol", "luna", "astra", "openai"]):
            self.provider = "openai"
        elif "claude" in pref_lower or "anthropic" in pref_lower or "opus" in pref_lower or "sonnet" in pref_lower or "haiku" in pref_lower:
            self.provider = "claude"
        else:
            self.provider = "gemini"

    async def execute(
        self,
        query: str,
        api_key: Optional[str] = None,
        cached_papers: Optional[List[Dict[str, Any]]] = None
    ) -> ConventionalRAGResult:
        # Smart key & provider auto-detection
        if api_key:
            api_key_clean = api_key.strip()
            if api_key_clean.startswith("AIzaSy"):
                self.provider = "gemini"
                if "gemini" not in self.model_pref.lower():
                    self.model_pref = "gemini-3.8-flash"
            elif api_key_clean.startswith("sk-ant-"):
                self.provider = "claude"
                if "claude" not in self.model_pref.lower() and "opus" not in self.model_pref.lower() and "sonnet" not in self.model_pref.lower():
                    self.model_pref = "claude-sonnet-5.5"
            elif api_key_clean.startswith("sk-") and not api_key_clean.startswith("sk-ant-"):
                self.provider = "openai"
                if not any(x in self.model_pref.lower() for x in ["gpt", "sol", "luna", "astra"]):
                    self.model_pref = "gpt-6.1-sol"

        logger.info(f"Executing Conventional RAG baseline for query '{query[:60]}...' with {self.provider} ({self.model_pref})")
        start_time = time.perf_counter()

        # Step 1: Retrieval (Scrape or use provided papers)
        retrieval_start = time.perf_counter()
        if cached_papers is not None:
            raw_papers = cached_papers
        else:
            try:
                scraper_res = await run_agent1_academic_scraper(query, limit=5, sources="all")
                raw_papers = scraper_res.get("papers", [])
            except Exception as e:
                logger.warning(f"Academic search encountered issue: {e}")
                raw_papers = []

        # Step 2: Passage Chunking
        candidate_chunks: List[Dict[str, Any]] = []
        for p in raw_papers:
            title = p.get("title", "Untitled Academic Work")
            venue = p.get("venue", p.get("source", "Peer-Reviewed Literature"))
            url = p.get("url", p.get("doi", ""))
            abstract = p.get("abstract", p.get("snippet", "")).strip()

            if not abstract:
                continue

            # Split abstract into ~2-3 sentence passages
            sentences = [s.strip() for s in abstract.replace("\n", " ").split(". ") if len(s.strip()) > 20]
            if len(sentences) <= 2:
                candidate_chunks.append({
                    "title": title,
                    "venue": venue,
                    "url": url,
                    "text": abstract
                })
            else:
                for i in range(0, len(sentences), 2):
                    passage = ". ".join(sentences[i:i+2])
                    if not passage.endswith("."):
                        passage += "."
                    candidate_chunks.append({
                        "title": title,
                        "venue": venue,
                        "url": url,
                        "text": passage
                    })

        # Step 3: Dense Vector Similarity Ranking
        selected_chunks: List[RetrievedChunk] = []
        if candidate_chunks:
            chunk_texts = [c["text"] for c in candidate_chunks]
            # Try ONNX FastEmbed first
            query_vecs = embed_texts([query])
            chunk_vecs = embed_texts(chunk_texts)

            if query_vecs is not None and chunk_vecs is not None:
                # Cosine similarity via dot product (vectors are L2-normalized)
                scores = np.dot(chunk_vecs, query_vecs[0])
                ranked_indices = np.argsort(scores)[::-1][:self.top_k]
                for idx in ranked_indices:
                    c = candidate_chunks[idx]
                    selected_chunks.append(RetrievedChunk(
                        title=c["title"],
                        source_venue=c["venue"],
                        url=c["url"],
                        text=c["text"],
                        similarity_score=float(scores[idx])
                    ))
            else:
                # High-resolution subword profile fallback
                q_prof = text_to_vector_profile(query)
                scored = []
                for c in candidate_chunks:
                    c_prof = text_to_vector_profile(c["text"])
                    sim, _ = compute_profile_similarity(q_prof, c_prof)
                    scored.append((sim, c))
                scored.sort(key=lambda x: x[0], reverse=True)
                for sim, c in scored[:self.top_k]:
                    selected_chunks.append(RetrievedChunk(
                        title=c["title"],
                        source_venue=c["venue"],
                        url=c["url"],
                        text=c["text"],
                        similarity_score=float(sim)
                    ))

        retrieval_latency = time.perf_counter() - retrieval_start

        # Step 4: Construct Canonical RAG Prompt
        context_blocks = []
        for idx, chunk in enumerate(selected_chunks, 1):
            context_blocks.append(
                f"[{idx}] Source: {chunk.title} ({chunk.source_venue})\n"
                f"Excerpt: {chunk.text}"
            )
        context_str = "\n\n".join(context_blocks) if context_blocks else "No external literature retrieved."

        system_instruction = (
            f"{AGENT2_PINNED_SYSTEM_INSTRUCTION}\n\n"
            "TASK DIRECTIVE (CONVENTIONAL RAG):\n"
            "Synthesize a publication-grade academic research monograph strictly based on the retrieved literature below.\n"
            "Cite the retrieved documents using bracketed citations [1], [2], etc., corresponding to the provided sources.\n"
            "Organize your monograph into:\n"
            "1. Executive Synthesis & Core Direct Answer (with exact physical/empirical numbers)\n"
            "2. Theoretical & Mathematical Foundations (with LaTeX equations)\n"
            "3. Empirical Evidence & Benchmark Comparisons (with named hardware/benchmarks and comparative markdown table)\n"
            "4. Dialectical Friction & Conflicting Scientific Perspectives\n"
            "5. Epistemic Limitations & Open Questions"
        )

        user_prompt = (
            f"RETRIEVED LITERATURE CONTEXT:\n{context_str}\n\n"
            f"<user_research_query>\n{query}\n</user_research_query>"
        )

        # Step 5: Execute Single Augmented LLM Call
        output_text = ""
        p_tok, c_tok, tot_tok = 0, 0, 0
        canonical_model = self.model_pref

        if self.provider == "claude":
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY is required to run ConventionalRAGSystem with Claude.")
            canonical_model = resolve_anthropic_model(self.model_pref)
            raw_output, tok_usage = await call_anthropic_api(
                prompt=user_prompt,
                api_key=key,
                model_pref=self.model_pref,
                system_instruction=system_instruction
            )
            output_text = raw_output
            if isinstance(tok_usage, TokenCount):
                p_tok = tok_usage.input_tokens
                c_tok = tok_usage.output_tokens
                tot_tok = int(tok_usage)
            else:
                tot_tok = int(tok_usage)
                p_tok = round(tot_tok * 0.5)
                c_tok = tot_tok - p_tok
        elif self.provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY", "")
            if not key:
                raise ValueError("OPENAI_API_KEY is required to run ConventionalRAGSystem with OpenAI.")
            canonical_model = resolve_openai_model(self.model_pref)
            raw_output, tok_usage = await call_openai_api(
                prompt=user_prompt,
                api_key=key,
                model_pref=self.model_pref,
                system_instruction=system_instruction
            )
            output_text = raw_output
            if isinstance(tok_usage, TokenCount):
                p_tok = tok_usage.input_tokens
                c_tok = tok_usage.output_tokens
                tot_tok = int(tok_usage)
            else:
                tot_tok = int(tok_usage)
                p_tok = round(tot_tok * 0.5)
                c_tok = tot_tok - p_tok
        else:
            key = api_key or os.getenv("GEMINI_API_KEY", "")
            if not key:
                raise ValueError("GEMINI_API_KEY is required to run ConventionalRAGSystem with Gemini.")
            raw_output, tok_usage = await call_gemini_api(
                prompt=f"{system_instruction}\n\n{user_prompt}",
                api_key=key,
                model_pref=self.model_pref,
                system_instruction=system_instruction
            )
            output_text = raw_output
            if isinstance(tok_usage, TokenCount):
                p_tok = tok_usage.input_tokens
                c_tok = tok_usage.output_tokens
                tot_tok = int(tok_usage)
            else:
                tot_tok = int(tok_usage)
                p_tok = round(tot_tok * 0.5)
                c_tok = tot_tok - p_tok

        total_latency = time.perf_counter() - start_time

        return ConventionalRAGResult(
            system_name="System B: Conventional RAG (Single Call)",
            query=query,
            model=canonical_model,
            provider=self.provider,
            output_text=output_text,
            retrieved_chunks=selected_chunks,
            input_tokens=p_tok,
            output_tokens=c_tok,
            total_tokens=tot_tok,
            latency_seconds=total_latency,
            retrieval_latency=retrieval_latency,
            retrieved_sources_count=len(selected_chunks)
        )
