"""
System C: Direct Single API Call Baseline
Invokes a single LLM API call (Claude or Gemini) using the exact same
Principal Academic Research Scientist system persona and token ceilings
without external literature retrieval or multi-agent orchestration.
"""

import os
import time
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

from backend.logger import get_logger
from backend.agents.agent2_drafter import (
    AGENT2_PINNED_SYSTEM_INSTRUCTION,
    call_anthropic_api,
    call_gemini_api,
    call_openai_api,
    resolve_anthropic_model,
    resolve_openai_model,
    TokenCount
)

logger = get_logger("DirectAPISystem")


@dataclass
class DirectAPIResult:
    system_name: str
    query: str
    model: str
    provider: str
    output_text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_seconds: float
    retrieved_sources_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "query": self.query,
            "model": self.model,
            "provider": self.provider,
            "output_text": self.output_text,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": round(self.latency_seconds, 2),
            "retrieved_sources_count": self.retrieved_sources_count
        }


class DirectAPISystem:
    """
    Direct single API call baseline for comparative scientific evaluation.
    Evaluates pure parametric model memory under elite persona instructions.
    """

    def __init__(self, model_pref: str = "claude-sonnet-5.5", provider: Optional[str] = None):
        self.model_pref = model_pref or "claude-sonnet-5.5"
        pref_lower = self.model_pref.lower()
        if provider:
            self.provider = provider.lower()
        elif any(x in pref_lower for x in ["gpt", "sol", "luna", "astra", "openai"]):
            self.provider = "openai"
        elif "claude" in pref_lower or "anthropic" in pref_lower or "opus" in pref_lower or "sonnet" in pref_lower or "haiku" in pref_lower:
            self.provider = "claude"
        else:
            self.provider = "gemini"

    async def execute(self, query: str, api_key: Optional[str] = None) -> DirectAPIResult:
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

        logger.info(f"Executing Direct API baseline for query '{query[:60]}...' with {self.provider} ({self.model_pref})")
        start_time = time.perf_counter()

        system_instruction = (
            f"{AGENT2_PINNED_SYSTEM_INSTRUCTION}\n\n"
            "TASK DIRECTIVE:\n"
            "Synthesize a publication-grade academic research monograph directly answering the research query.\n"
            "Organize your monograph into:\n"
            "1. Executive Synthesis & Core Direct Answer (with exact physical/empirical numbers)\n"
            "2. Theoretical & Mathematical Foundations (with LaTeX equations)\n"
            "3. Empirical Evidence & Benchmark Comparisons (with named hardware/benchmarks and comparative markdown table)\n"
            "4. Dialectical Friction & Conflicting Scientific Perspectives\n"
            "5. Epistemic Limitations & Open Questions"
        )

        user_prompt = f"<user_research_query>\n{query}\n</user_research_query>"

        output_text = ""
        p_tok, c_tok, tot_tok = 0, 0, 0
        canonical_model = self.model_pref

        if self.provider == "claude":
            key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY is required to run DirectAPISystem with Claude.")
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
                p_tok = round(tot_tok * 0.4)
                c_tok = tot_tok - p_tok
        elif self.provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY", "")
            if not key:
                raise ValueError("OPENAI_API_KEY is required to run DirectAPISystem with OpenAI.")
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
                p_tok = round(tot_tok * 0.4)
                c_tok = tot_tok - p_tok
        else:
            key = api_key or os.getenv("GEMINI_API_KEY", "")
            if not key:
                raise ValueError("GEMINI_API_KEY is required to run DirectAPISystem with Gemini.")
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
                p_tok = round(tot_tok * 0.4)
                c_tok = tot_tok - p_tok

        latency = time.perf_counter() - start_time

        return DirectAPIResult(
            system_name="System C: Direct Single API Call",
            query=query,
            model=canonical_model,
            provider=self.provider,
            output_text=output_text,
            input_tokens=p_tok,
            output_tokens=c_tok,
            total_tokens=tot_tok,
            latency_seconds=latency,
            retrieved_sources_count=0
        )
