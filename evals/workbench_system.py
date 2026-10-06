"""
System A: ResearchWorkbench Wrapper
Invokes the full 4-agent ResearchWorkbench pipeline:
  Agent 1 (Scraper) -> Agent 2 (Drafter) -> Agent 3 (Cacher/MMR) -> Agent 4 (Fact-Checker/Synthesizer)
Exposes the exact same telemetry interface for comparative benchmark evaluation.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import re
from backend.logger import get_logger
from backend.pipeline import run_query_pipeline
from backend.export import _normalize_comparison_table, _normalize_dialectical_friction, _normalize_epistemic_limitations, strip_html_tags

logger = get_logger("WorkbenchSystem")


@dataclass
class WorkbenchResult:
    system_name: str
    query: str
    model: str
    provider: str
    output_text: str
    executive_summary: str
    quick_answer: str
    dossier_sections: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    evaluated_claims: List[Dict[str, Any]]
    confidence_score: float
    verified_claims_count: int
    unverified_claims_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_seconds: float
    retrieved_sources_count: int
    dialectical_friction: Any = None
    comparison_table: Any = None
    run_id: str = ""
    dossier: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "query": self.query,
            "model": self.model,
            "provider": self.provider,
            "run_id": self.run_id,
            "output_text": self.output_text,
            "executive_summary": self.executive_summary,
            "quick_answer": self.quick_answer,
            "confidence_score": round(self.confidence_score, 1),
            "verified_claims_count": self.verified_claims_count,
            "unverified_claims_count": self.unverified_claims_count,
            "citations_count": len(self.citations),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": round(self.latency_seconds, 2),
            "retrieved_sources_count": self.retrieved_sources_count
        }


class WorkbenchSystem:
    """
    ResearchWorkbench Multi-Agent evaluation wrapper.
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

    async def execute(self, query: str, api_key: Optional[str] = None, user_id: Optional[str] = None) -> WorkbenchResult:
        start_time = time.perf_counter()

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        # Smart key & provider auto-detection
        if api_key:
            api_key_clean = api_key.strip()
            if api_key_clean.startswith("AIzaSy"):
                self.provider = "gemini"
                if "gemini" not in self.model_pref.lower():
                    self.model_pref = "gemini-3.8-flash"
                gemini_key = api_key_clean
            elif api_key_clean.startswith("sk-ant-"):
                self.provider = "claude"
                if "claude" not in self.model_pref.lower() and "opus" not in self.model_pref.lower() and "sonnet" not in self.model_pref.lower():
                    self.model_pref = "claude-sonnet-5.5"
                anthropic_key = api_key_clean
            elif api_key_clean.startswith("sk-") and not api_key_clean.startswith("sk-ant-"):
                self.provider = "openai"
                if not any(x in self.model_pref.lower() for x in ["gpt", "sol", "luna", "astra"]):
                    self.model_pref = "gpt-6.1-sol"
                openai_key = api_key_clean
            else:
                if self.provider == "claude":
                    anthropic_key = api_key_clean
                elif self.provider == "openai":
                    openai_key = api_key_clean
                else:
                    gemini_key = api_key_clean

        active_key = anthropic_key if self.provider == "claude" else (openai_key if self.provider == "openai" else gemini_key)
        if not active_key:
            if self.provider == "claude":
                expected_provider = "Anthropic Claude (sk-ant-...)"
            elif self.provider == "openai":
                expected_provider = "OpenAI (sk-proj-... / sk-...)"
            else:
                expected_provider = "Google Gemini (AIzaSy...)"
            raise ValueError(
                f"No API key provided for System A using {expected_provider}. "
                f"Please enter your API key in the System A configuration card or configure .env."
            )

        logger.info(f"Executing ResearchWorkbench Multi-Agent pipeline for '{query[:60]}...' with {self.provider} ({self.model_pref})")

        config = {
            "provider_agent2": self.model_pref if self.provider in ("claude", "openai") else (self.model_pref or "gemini"),
            "provider_agent4": self.model_pref if self.provider in ("claude", "openai") else (self.model_pref or "gemini"),
            "anthropic_key": anthropic_key,
            "gemini_key": gemini_key,
            "openai_key": openai_key,
            "bypass_cache": True,  # Always bypass query cache during scientific benchmarking
            "disable_fallback": True,  # Strictly require live AI execution during comparative evaluation
            "disable_fallback_agent2": True,
            "disable_fallback_agent4": True,
            "paper_limit": 5,
            "scraper_sources": "all",
            "user_id": user_id
        }

        pipeline_res = await run_query_pipeline(query, config=config)

        # Reconstruct full publication-grade academic monograph from all pipeline components
        monograph_parts = []
        
        # 1. Quick Answer & Executive Monograph
        quick = pipeline_res.get("quick_answer", "").strip()
        if quick:
            monograph_parts.append(f"## 1. Executive Synthesis & Quick Answer\n\n> **Executive Quick Answer:** {strip_html_tags(quick)}\n")
        else:
            monograph_parts.append("## 1. Executive Synthesis & Quick Answer\n")

        exec_sum = pipeline_res.get("executive_summary", "").strip()
        if exec_sum:
            monograph_parts.append(f"### Executive Monograph\n\n{strip_html_tags(exec_sum)}\n")

        # 2. Comparative Benchmark Matrix Table (GFM Markdown Table)
        cols, rows = _normalize_comparison_table(pipeline_res.get("comparison_table"))
        if cols and rows:
            table_lines = [
                "## 2. Quantitative Comparative Benchmarks & Method Taxonomy\n",
                "| " + " | ".join(cols) + " |",
                "| " + " | ".join([":---"] * len(cols)) + " |"
            ]
            for r in rows:
                clean_row = [strip_html_tags(str(cell)).replace("|", "\\|").replace("\n", " ") for cell in r]
                table_lines.append("| " + " | ".join(clean_row) + " |")
            monograph_parts.append("\n".join(table_lines) + "\n")

        # 3. Dialectical Friction & Methodological Disagreements
        friction_items = _normalize_dialectical_friction(pipeline_res.get("dialectical_friction"))
        if friction_items:
            fric_lines = ["## 3. Dialectical Friction & Scientific Trade-Offs\n"]
            for f_label, f_body in friction_items:
                fric_lines.append(f"- **{strip_html_tags(f_label)}:** {strip_html_tags(f_body)}")
            monograph_parts.append("\n".join(fric_lines) + "\n")

        # 4. Detailed Thematic Sections
        sections = pipeline_res.get("dossier_sections", [])
        if sections:
            sec_lines = ["## 4. Thematic Literature Synthesis & In-Depth Analysis\n"]
            for idx, sec in enumerate(sections, 1):
                raw_heading = sec.get("sub_question") or sec.get("heading") or f"Subtopic {idx}"
                clean_heading = re.sub(r'^(?:Subtopic\s*\d+[:.-]?|\d+[\.\):]|\d+\s+[-–:]\s*)\s*', '', raw_heading, flags=re.IGNORECASE).strip()
                if not clean_heading:
                    clean_heading = raw_heading
                sec_lines.append(f"### 4.{idx} {clean_heading}\n")
                raw_body = sec.get("content_html") or sec.get("answer_html") or ""
                clean_body = strip_html_tags(raw_body)
                sec_lines.append(f"{clean_body}\n")
            monograph_parts.append("\n".join(sec_lines))

        # 5. Epistemic Horizons & Boundary Conditions
        epistemic_items = _normalize_epistemic_limitations(pipeline_res.get("epistemic_limitations"))
        if epistemic_items:
            epis_lines = ["## 5. Epistemic Horizons & Boundary Conditions\n"]
            for item in epistemic_items:
                epis_lines.append(f"- {strip_html_tags(item)}")
            monograph_parts.append("\n".join(epis_lines) + "\n")

        # 6. Peer-Reviewed Citations & Evidence Grounding
        citations = pipeline_res.get("citations", [])
        if citations:
            cit_lines = ["## 6. Peer-Reviewed Citations & Grounded Sources\n"]
            for cit in citations:
                ref_id = cit.get("ref_id", "REF")
                raw_authors = cit.get("authors", "Unknown Authors")
                authors = ", ".join(str(a) for a in raw_authors) if isinstance(raw_authors, list) else str(raw_authors)
                year = cit.get("year", "n.d.")
                p_title = cit.get("title", "Untitled")
                venue = cit.get("venue", "Academic Publication")
                url = cit.get("url", "")
                prov_tag = f" [{cit.get('provenance_label')}]" if cit.get('provenance_label') else ""
                cit_lines.append(f"- **[{ref_id}]** {authors} ({year}). *{p_title}*. {venue}.{prov_tag}" + (f" [{url}]({url})" if url else ""))
                evidence = cit.get("evidence", "")
                if evidence:
                    cit_lines.append(f"  > *Evidence:* \"{strip_html_tags(evidence)}\"")
            monograph_parts.append("\n".join(cit_lines) + "\n")

        assembled_output = "\n\n".join(monograph_parts)

        tokens = pipeline_res.get("token_usage", {})
        prompt_tokens = tokens.get("prompt_tokens", 0)
        completion_tokens = tokens.get("completion_tokens", 0)
        total_tokens = tokens.get("total_tokens", prompt_tokens + completion_tokens)

        claims = pipeline_res.get("evaluated_claims", [])
        verified_count = sum(
            1 for c in claims 
            if c.get("status") in ["verified", "verified_in_source", True, "Auto-Verified", "LLM-Verified", "Preprint-Corroborated"]
            or c.get("verification_tier") in ["auto_cache", "auto_cache_preprint", "llm_rag"]
        )
        unverified_count = len(claims) - verified_count

        conf_score = float(pipeline_res.get("confidence_score", 0.0) or 0.0)
        if conf_score <= 0.0 and claims:
            conf_score = round((verified_count / len(claims)) * 100, 1)

        citations = pipeline_res.get("citations", [])
        elapsed = time.perf_counter() - start_time

        return WorkbenchResult(
            system_name="System A: ResearchWorkbench (Multi-Agent)",
            query=query,
            model=self.model_pref,
            provider=self.provider,
            output_text=assembled_output,
            executive_summary=pipeline_res.get("executive_summary", ""),
            quick_answer=pipeline_res.get("quick_answer", ""),
            dossier_sections=pipeline_res.get("dossier_sections", []),
            citations=citations,
            evaluated_claims=claims,
            confidence_score=conf_score,
            verified_claims_count=verified_count,
            unverified_claims_count=unverified_count,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_seconds=elapsed,
            retrieved_sources_count=len(citations),
            dialectical_friction=pipeline_res.get("dialectical_friction"),
            comparison_table=pipeline_res.get("comparison_table"),
            run_id=pipeline_res.get("run_id", ""),
            dossier=pipeline_res
        )
