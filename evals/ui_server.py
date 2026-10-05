"""
Standalone Comparative Study Application Server
Runs on port 8501 (independent from main workbench on port 8000).
Provides interactive side-by-side execution and evaluation across:
  - System A: ResearchWorkbench (Multi-Agent Pipeline)
  - System B: Conventional RAG (Single-Call Vector Retrieval)
  - System C: Direct Single API Call (Zero-Shot)

Supports independent API keys (Anthropic and Gemini) and model selection for each system.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from evals.prompts import BENCHMARK_PROMPTS, get_prompt_by_id
from evals.direct_api_system import DirectAPISystem
from evals.conventional_rag_system import ConventionalRAGSystem
from evals.workbench_system import WorkbenchSystem
from evals.run_study import analyze_text_quality, calculate_estimated_cost
from backend.logger import get_logger

logger = get_logger("StudyAppServer")

app = FastAPI(title="ResearchWorkbench Comparative Study Harness", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DOCX_PATH = Path(__file__).resolve().parent / "Comparative_Study_Protocol_and_Workbook.docx"


class SingleSystemRequest(BaseModel):
    system_type: str  # 'a', 'b', or 'c'
    query: str
    model: str = "claude-sonnet-5.5"
    api_key: Optional[str] = None
    top_k: int = 5


class SystemConfig(BaseModel):
    enabled: bool = True
    model: str = "claude-sonnet-5.5"
    api_key: Optional[str] = None
    top_k: int = 5


class ComparisonRequest(BaseModel):
    query: str
    system_a: SystemConfig
    system_b: SystemConfig
    system_c: SystemConfig


@app.get("/")
async def get_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/prompts")
async def list_prompts():
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "domain": p.domain,
            "query": p.query,
            "ground_truth_anchors": p.ground_truth_anchors,
            "failure_modes_tested": p.failure_modes_tested,
            "evaluation_focus": p.evaluation_focus
        }
        for p in BENCHMARK_PROMPTS
    ]


@app.get("/api/download-docx")
async def download_docx():
    if not DOCX_PATH.exists():
        # Auto-generate if missing
        from evals.build_study_docx import build_docx_report
        build_docx_report(str(DOCX_PATH))
    return FileResponse(
        path=str(DOCX_PATH),
        filename="Comparative_Study_Protocol_and_Workbook.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


async def _run_single_system(sys_type: str, query: str, model: str, api_key: Optional[str], top_k: int = 5) -> Dict[str, Any]:
    sys_type = sys_type.lower()
    if sys_type == "a":
        wb = WorkbenchSystem(model_pref=model)
        res = await wb.execute(query, api_key=api_key)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(model, res.input_tokens, res.output_tokens)
        return {
            **res.to_dict(),
            "cost_usd": cost,
            "text_analysis": analysis
        }
    elif sys_type == "b":
        rag = ConventionalRAGSystem(model_pref=model, top_k=top_k)
        res = await rag.execute(query, api_key=api_key)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(model, res.input_tokens, res.output_tokens)
        return {
            **res.to_dict(),
            "cost_usd": cost,
            "text_analysis": analysis
        }
    elif sys_type == "c":
        direct = DirectAPISystem(model_pref=model)
        res = await direct.execute(query, api_key=api_key)
        analysis = analyze_text_quality(res.output_text)
        cost = calculate_estimated_cost(model, res.input_tokens, res.output_tokens)
        return {
            **res.to_dict(),
            "cost_usd": cost,
            "text_analysis": analysis
        }
    else:
        raise ValueError(f"Invalid system type: '{sys_type}' (expected 'a', 'b', or 'c')")


@app.post("/api/run-system")
async def run_single(req: SingleSystemRequest):
    try:
        result = await _run_single_system(
            sys_type=req.system_type,
            query=req.query,
            model=req.model,
            api_key=req.api_key,
            top_k=req.top_k
        )
        return result
    except Exception as e:
        logger.error(f"Execution error on System {req.system_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-comparison")
async def run_comparison(req: ComparisonRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    tasks = []
    task_keys = []

    if req.system_a.enabled:
        tasks.append(_run_single_system("a", query, req.system_a.model, req.system_a.api_key))
        task_keys.append("system_a")

    if req.system_b.enabled:
        tasks.append(_run_single_system("b", query, req.system_b.model, req.system_b.api_key, req.system_b.top_k))
        task_keys.append("system_b")

    if req.system_c.enabled:
        tasks.append(_run_single_system("c", query, req.system_c.model, req.system_c.api_key))
        task_keys.append("system_c")

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    response_data: Dict[str, Any] = {
        "query": query,
        "results": {}
    }

    for key, res in zip(task_keys, raw_results):
        if isinstance(res, Exception):
            response_data["results"][key] = {
                "error": str(res),
                "system_name": key.upper()
            }
        else:
            response_data["results"][key] = res

    return response_data


def run():
    import uvicorn
    print("\n" + "=" * 70)
    print("  RESEARCHWORKBENCH COMPARATIVE STUDY HARNESS")
    print("  Running independently on: http://127.0.0.1:8501")
    print("=" * 70 + "\n")
    uvicorn.run("evals.ui_server:app", host="127.0.0.1", port=8501, reload=False)


if __name__ == "__main__":
    run()
