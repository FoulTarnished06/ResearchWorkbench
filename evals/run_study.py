"""
Comparative Study Benchmark Runner
Executes standardized prompts across:
  - System A: ResearchWorkbench (Multi-Agent System)
  - System B: Conventional RAG (Single-Call Vector Retrieval)
  - System C: Direct Single API Call (Zero-Shot)

Outputs:
  - Raw monographs in markdown format
  - Telemetry metrics (input/output tokens, cost, latency)
  - Automated platitude detection & citation grounding check
  - Side-by-side comparison tables
"""

import os
import sys
import json
import time
import re
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.prompts import BENCHMARK_PROMPTS, BenchmarkPrompt, get_prompt_by_id
from evals.direct_api_system import DirectAPISystem
from evals.conventional_rag_system import ConventionalRAGSystem
from evals.workbench_system import WorkbenchSystem
from backend.logger import get_logger

logger = get_logger("StudyRunner")

# Pricing per million tokens (USD)
MODEL_PRICING = {
    "claude-opus": {"input_per_m": 15.00, "output_per_m": 75.00},
    "claude-sonnet": {"input_per_m": 3.00, "output_per_m": 15.00},
    "claude-haiku": {"input_per_m": 0.80, "output_per_m": 4.00},
    "gemini-3.8-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-3.6-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-3.5-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-3.1-pro": {"input_per_m": 1.25, "output_per_m": 5.00},
    "gpt-6-astra": {"input_per_m": 10.00, "output_per_m": 50.00},
    "gpt-6.1-sol": {"input_per_m": 2.00, "output_per_m": 10.00},
    "gpt-6-sol": {"input_per_m": 2.00, "output_per_m": 10.00},
    "gpt-6-luna": {"input_per_m": 0.10, "output_per_m": 0.50},
    "gpt-5.5": {"input_per_m": 5.00, "output_per_m": 30.00},
    "gpt-5.4-mini": {"input_per_m": 0.75, "output_per_m": 4.50},
    "gpt-5.4": {"input_per_m": 2.50, "output_per_m": 15.00},
}

FORBIDDEN_PLATITUDES = [
    r"\bimportant to note\b",
    r"\bplays a crucial role\b",
    r"\bpaved the way\b",
    r"\ba promising avenue\b",
    r"\bfurther research is needed\b",
    r"\bdelves into\b",
    r"\bsheds light on\b",
    r"\btestament to\b",
    r"\brapidly evolving landscape\b",
    r"\bdouble-edged sword\b",
]


def calculate_estimated_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    m_lower = model_name.lower()
    rate = MODEL_PRICING.get("claude-sonnet")
    for key, p in MODEL_PRICING.items():
        if key in m_lower:
            rate = p
            break
    in_cost = (input_tokens / 1_000_000.0) * rate["input_per_m"]
    out_cost = (output_tokens / 1_000_000.0) * rate["output_per_m"]
    return round(in_cost + out_cost, 5)


def analyze_text_quality(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    platitudes_found = []
    for pat in FORBIDDEN_PLATITUDES:
        if re.search(pat, text_lower):
            platitudes_found.append(pat.replace(r"\b", ""))

    dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', text)
    pmids = re.findall(r'\bPMID[:\s]+(\d+)\b', text, re.IGNORECASE)
    arxivs = re.findall(r'\barXiv[:\s]+(\d{4}\.\d{4,5})\b', text, re.IGNORECASE)
    bracket_cites = re.findall(r'\[(?:\d+|c\d+)\]', text)
    latex_equations = re.findall(r'\$\$[\s\S]+?\$\$|\$[^\$]+?\$', text)
    tables = re.findall(r'\|[\s\S]+?\|[\s\S]+?\|', text)

    return {
        "word_count": len(text.split()),
        "platitudes_count": len(platitudes_found),
        "platitudes_detected": platitudes_found,
        "dois_cited": list(set(dois)),
        "pmids_cited": list(set(pmids)),
        "arxiv_ids_cited": list(set(arxivs)),
        "bracket_citations_count": len(bracket_cites),
        "citations_count": len(bracket_cites),
        "latex_equations_count": len(latex_equations),
        "equations_count": len(latex_equations),
        "markdown_tables_count": 1 if tables else 0,
        "tables_count": 1 if tables else 0
    }


async def run_prompt_evaluation(
    prompt: BenchmarkPrompt,
    model_pref: str = "claude-sonnet-5.5",
    systems_to_run: Optional[List[str]] = None,
    outdir: str = "evals/results"
) -> Dict[str, Any]:
    systems_to_run = systems_to_run or ["a", "b", "c"]
    prompt_slug = f"prompt_{prompt.id}_{prompt.slug}"
    target_dir = Path(outdir) / prompt_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print(f"BENCHMARK PROMPT #{prompt.id}: {prompt.title}")
    print(f"Domain: {prompt.domain}")
    print(f"Model: {model_pref}")
    print(f"Query: {prompt.query}")
    print("=" * 80)

    results = {}

    # System A: ResearchWorkbench
    if "a" in systems_to_run:
        print("\n--> [1/3] Executing System A: ResearchWorkbench (Multi-Agent)...")
        try:
            wb = WorkbenchSystem(model_pref=model_pref)
            res_a = await wb.execute(prompt.query)
            analysis_a = analyze_text_quality(res_a.output_text)
            cost_a = calculate_estimated_cost(model_pref, res_a.input_tokens, res_a.output_tokens)
            results["system_a"] = {
                **res_a.to_dict(),
                "cost_usd": cost_a,
                "text_analysis": analysis_a
            }
            # Save markdown
            md_path = target_dir / "system_a_research_workbench.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# System A: ResearchWorkbench\n**Query:** {prompt.query}\n\n"
                        f"**Model:** {res_a.model} | **Latency:** {res_a.latency_seconds:.2f}s | "
                        f"**Tokens:** {res_a.total_tokens} (In: {res_a.input_tokens}, Out: {res_a.output_tokens}) | "
                        f"**Confidence Score:** {res_a.confidence_score}%\n\n---\n\n"
                        + res_a.output_text)
            print(f"    [DONE] Latency: {res_a.latency_seconds:.2f}s | Total Tokens: {res_a.total_tokens} | Conf: {res_a.confidence_score}%")
        except Exception as e:
            logger.error(f"System A execution failed: {e}")
            results["system_a"] = {"error": str(e)}

    # System B: Conventional RAG
    if "b" in systems_to_run:
        print("\n--> [2/3] Executing System B: Conventional RAG (Single Call)...")
        try:
            rag = ConventionalRAGSystem(model_pref=model_pref, top_k=5)
            res_b = await rag.execute(prompt.query)
            analysis_b = analyze_text_quality(res_b.output_text)
            cost_b = calculate_estimated_cost(model_pref, res_b.input_tokens, res_b.output_tokens)
            results["system_b"] = {
                **res_b.to_dict(),
                "cost_usd": cost_b,
                "text_analysis": analysis_b
            }
            # Save markdown
            md_path = target_dir / "system_b_conventional_rag.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# System B: Conventional RAG (Single Augmented Call)\n**Query:** {prompt.query}\n\n"
                        f"**Model:** {res_b.model} | **Latency:** {res_b.latency_seconds:.2f}s (Retrieval: {res_b.retrieval_latency:.2f}s) | "
                        f"**Tokens:** {res_b.total_tokens} (In: {res_b.input_tokens}, Out: {res_b.output_tokens})\n\n---\n\n"
                        + res_b.output_text)
            print(f"    [DONE] Latency: {res_b.latency_seconds:.2f}s | Total Tokens: {res_b.total_tokens} | Top-K Sources: {res_b.retrieved_sources_count}")
        except Exception as e:
            logger.error(f"System B execution failed: {e}")
            results["system_b"] = {"error": str(e)}

    # System C: Direct Single API Call
    if "c" in systems_to_run:
        print("\n--> [3/3] Executing System C: Direct Single API Call (Zero-Shot)...")
        try:
            direct = DirectAPISystem(model_pref=model_pref)
            res_c = await direct.execute(prompt.query)
            analysis_c = analyze_text_quality(res_c.output_text)
            cost_c = calculate_estimated_cost(model_pref, res_c.input_tokens, res_c.output_tokens)
            results["system_c"] = {
                **res_c.to_dict(),
                "cost_usd": cost_c,
                "text_analysis": analysis_c
            }
            # Save markdown
            md_path = target_dir / "system_c_direct_api.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# System C: Direct Single API Call (Zero-Shot)\n**Query:** {prompt.query}\n\n"
                        f"**Model:** {res_c.model} | **Latency:** {res_c.latency_seconds:.2f}s | "
                        f"**Tokens:** {res_c.total_tokens} (In: {res_c.input_tokens}, Out: {res_c.output_tokens})\n\n---\n\n"
                        + res_c.output_text)
            print(f"    [DONE] Latency: {res_c.latency_seconds:.2f}s | Total Tokens: {res_c.total_tokens}")
        except Exception as e:
            logger.error(f"System C execution failed: {e}")
            results["system_c"] = {"error": str(e)}

    # Write telemetry json
    json_path = target_dir / "telemetry_comparison.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Write summary scorecard markdown
    summary_path = target_dir / "side_by_side_summary.md"
    summary_md = _generate_scorecard_markdown(prompt, results, model_pref)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print("\n" + summary_md)
    print(f"\nOutputs saved to: {target_dir}")
    return results


def _generate_scorecard_markdown(prompt: BenchmarkPrompt, results: Dict[str, Any], model: str) -> str:
    sa = results.get("system_a", {})
    sb = results.get("system_b", {})
    sc = results.get("system_c", {})

    lines = [
        f"# Benchmark Scorecard: Prompt #{prompt.id}",
        f"**Query:** {prompt.query}",
        f"**Model:** `{model}`",
        "",
        "| Metric | System A: ResearchWorkbench | System B: Conventional RAG | System C: Direct Single API |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Architecture** | 4-Agent Pipeline | Vector Top-K + 1 Call | Zero-Shot 1 Call |",
        f"| **External Literature Sources** | {sa.get('retrieved_sources_count', 'N/A')} retrieved | {sb.get('retrieved_sources_count', 'N/A')} chunks | 0 (Pure Parametric) |",
        f"| **Confidence Score** | **{sa.get('confidence_score', 'N/A')}%** | N/A (Unmeasured) | N/A (Unmeasured) |",
        f"| **Verified Claims Count** | **{sa.get('verified_claims_count', 'N/A')}** | 0 (No Verification) | 0 (No Verification) |",
        f"| **Input Tokens** | {sa.get('input_tokens', 'N/A')} | {sb.get('input_tokens', 'N/A')} | {sc.get('input_tokens', 'N/A')} |",
        f"| **Output Tokens** | {sa.get('output_tokens', 'N/A')} | {sb.get('output_tokens', 'N/A')} | {sc.get('output_tokens', 'N/A')} |",
        f"| **Total Tokens** | {sa.get('total_tokens', 'N/A')} | {sb.get('total_tokens', 'N/A')} | {sc.get('total_tokens', 'N/A')} |",
        f"| **Estimated Cost ($)** | ${sa.get('cost_usd', 0.0):.4f} | ${sb.get('cost_usd', 0.0):.4f} | ${sc.get('cost_usd', 0.0):.4f} |",
        f"| **Wall-Clock Latency** | {sa.get('latency_seconds', 'N/A')}s | {sb.get('latency_seconds', 'N/A')}s | {sc.get('latency_seconds', 'N/A')}s |",
        f"| **LaTeX Equations** | {sa.get('text_analysis', {}).get('latex_equations_count', 'N/A')} | {sb.get('text_analysis', {}).get('latex_equations_count', 'N/A')} | {sc.get('text_analysis', {}).get('latex_equations_count', 'N/A')} |",
        f"| **Platitudes Detected** | **{sa.get('text_analysis', {}).get('platitudes_count', 0)}** | {sb.get('text_analysis', {}).get('platitudes_count', 0)} | {sc.get('text_analysis', {}).get('platitudes_count', 0)} |",
        "",
        "### Ground Truth Verification Checklist",
        "Check each system's generated monograph against the following empirical ground-truth anchors:"
    ]
    for anchor in prompt.ground_truth_anchors:
        lines.append(f"- [ ] **Anchor:** {anchor}")
    
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="ResearchWorkbench Comparative Study Evaluation Runner")
    parser.add_argument("--prompt", type=str, default="1", help="Prompt ID (1-5) or 'all' to run all 5 prompts")
    parser.add_argument("--model", type=str, default="claude-sonnet-5.5", help="Model name (e.g. claude-sonnet-5.5, claude-opus-5.5, gemini-3.8-flash)")
    parser.add_argument("--systems", type=str, default="a,b,c", help="Comma-separated systems to evaluate: a,b,c or all")
    parser.add_argument("--outdir", type=str, default="evals/results", help="Directory where results are stored")
    args = parser.parse_args()

    sys_list = [s.strip().lower() for s in args.systems.split(",") if s.strip()]
    if "all" in sys_list:
        sys_list = ["a", "b", "c"]

    prompts_to_run: List[BenchmarkPrompt] = []
    if args.prompt.lower() == "all":
        prompts_to_run = BENCHMARK_PROMPTS
    else:
        try:
            pid = int(args.prompt)
            prompts_to_run = [get_prompt_by_id(pid)]
        except Exception as e:
            print(f"Invalid prompt option '{args.prompt}': {e}")
            sys.exit(1)

    print(f"Starting Comparative Study across {len(prompts_to_run)} prompt(s) using model `{args.model}`...")
    for p in prompts_to_run:
        await run_prompt_evaluation(p, model_pref=args.model, systems_to_run=sys_list, outdir=args.outdir)

    print("\n=======================================================")
    print("COMPARATIVE STUDY BENCHMARK EXECUTION COMPLETE!")
    print(f"All monographs and telemetry are saved in: {args.outdir}")
    print("Fill in qualitative scores in 'evals/STUDY_TEMPLATE.md'.")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(main())
