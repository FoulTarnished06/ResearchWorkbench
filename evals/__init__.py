"""
Comparative Evaluation Suite for ResearchWorkbench
Compares:
  - System A: ResearchWorkbench (Multi-Agent System)
  - System B: Conventional RAG (Single-Call Vector Retrieval)
  - System C: Direct API Call (Zero-Shot Parametric Memory)
"""

from evals.prompts import BENCHMARK_PROMPTS, BenchmarkPrompt
from evals.direct_api_system import DirectAPISystem
from evals.conventional_rag_system import ConventionalRAGSystem
from evals.workbench_system import WorkbenchSystem

__all__ = [
    "BENCHMARK_PROMPTS",
    "BenchmarkPrompt",
    "DirectAPISystem",
    "ConventionalRAGSystem",
    "WorkbenchSystem",
]
