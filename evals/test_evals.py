"""
Unit Tests for Comparative Evaluation Suite
Tests:
  - Benchmark prompts catalog integrity
  - DirectAPISystem model resolution and execution with mocks
  - ConventionalRAGSystem chunking, vector embedding, and context generation
  - Quality metrics extraction (platitudes, citations, equations)
  - Telemetry and cost calculations
"""

import unittest
from unittest.mock import patch, AsyncMock
import numpy as np

from evals.prompts import BENCHMARK_PROMPTS, get_prompt_by_id
from evals.direct_api_system import DirectAPISystem, DirectAPIResult
from evals.conventional_rag_system import ConventionalRAGSystem, RetrievedChunk
from evals.workbench_system import WorkbenchSystem
from evals.run_study import (
    calculate_estimated_cost,
    analyze_text_quality,
    _generate_scorecard_markdown
)
from backend.agents.agent2_drafter import TokenCount


class TestEvalPrompts(unittest.TestCase):
    def test_benchmark_prompts_count(self):
        self.assertEqual(len(BENCHMARK_PROMPTS), 5)

    def test_prompt_retrieval(self):
        p1 = get_prompt_by_id(1)
        self.assertEqual(p1.id, 1)
        self.assertIn("neural hawkes", p1.query.lower())
        self.assertTrue(len(p1.ground_truth_anchors) >= 4)
        self.assertTrue(len(p1.failure_modes_tested) >= 2)

    def test_invalid_prompt_id_raises(self):
        with self.assertRaises(ValueError):
            get_prompt_by_id(99)


class TestDirectAPISystem(unittest.IsolatedAsyncioTestCase):
    def test_provider_resolution(self):
        s_claude = DirectAPISystem(model_pref="claude-sonnet-5.5")
        self.assertEqual(s_claude.provider, "claude")

        s_opus = DirectAPISystem(model_pref="claude-opus-5.5")
        self.assertEqual(s_opus.provider, "claude")

        s_gemini = DirectAPISystem(model_pref="gemini-3.8-flash")
        self.assertEqual(s_gemini.provider, "gemini")

        s_sol = DirectAPISystem(model_pref="gpt-6.1-sol")
        self.assertEqual(s_sol.provider, "openai")

        s_luna = DirectAPISystem(model_pref="gpt-6-luna")
        self.assertEqual(s_luna.provider, "openai")

        s_mini = DirectAPISystem(model_pref="gpt-5.4-mini")
        self.assertEqual(s_mini.provider, "openai")

        s_astra = DirectAPISystem(model_pref="gpt-6-astra")
        self.assertEqual(s_astra.provider, "openai")

    @patch("evals.direct_api_system.call_anthropic_api", new_callable=AsyncMock)
    async def test_direct_api_claude_execution(self, mock_call):
        mock_call.return_value = (
            "Synthesis of neutral-atom coherence: T2* reaches 10s in 171Yb.",
            TokenCount(1200, 800, 400)
        )
        sys_c = DirectAPISystem(model_pref="claude-sonnet-5.5")
        res = await sys_c.execute(
            query="Test query",
            api_key="mock-key-12345"
        )
        self.assertIsInstance(res, DirectAPIResult)
        self.assertEqual(res.input_tokens, 800)
        self.assertEqual(res.output_tokens, 400)
        self.assertEqual(res.total_tokens, 1200)
        self.assertEqual(res.retrieved_sources_count, 0)
        self.assertIn("171Yb", res.output_text)
        self.assertTrue(res.latency_seconds >= 0.0)

    @patch("evals.direct_api_system.call_openai_api", new_callable=AsyncMock)
    async def test_direct_api_openai_execution(self, mock_call):
        mock_call.return_value = (
            "Synthesis of Rydberg quantum simulation via gpt-6.1-sol.",
            TokenCount(1500, 1000, 500)
        )
        sys_c = DirectAPISystem(model_pref="gpt-6.1-sol")
        res = await sys_c.execute(
            query="Test query",
            api_key="sk-proj-test12345"
        )
        self.assertIsInstance(res, DirectAPIResult)
        self.assertEqual(res.provider, "openai")
        self.assertEqual(res.input_tokens, 1000)
        self.assertEqual(res.output_tokens, 500)
        self.assertEqual(res.total_tokens, 1500)
        self.assertIn("Rydberg", res.output_text)


class TestConventionalRAGSystem(unittest.IsolatedAsyncioTestCase):
    @patch("evals.conventional_rag_system.call_anthropic_api", new_callable=AsyncMock)
    async def test_conventional_rag_chunking_and_execution(self, mock_call):
        mock_call.return_value = (
            "RAG synthesis: Neutral-atom arrays achieve 99.5% fidelity [1].",
            TokenCount(1800, 1200, 600)
        )
        sample_papers = [
            {
                "title": "High-fidelity gates in neutral atoms",
                "venue": "Nature 2023",
                "url": "https://doi.org/10.1038/example",
                "abstract": (
                    "Neutral-atom optical tweezer arrays have demonstrated two-qubit gate fidelities "
                    "exceeding 99.5% using Rydberg blockade interactions. Coherence times in nuclear spin-1/2 "
                    "isotopes like 171Yb exhibit seconds of T2* coherence."
                )
            }
        ]

        sys_b = ConventionalRAGSystem(model_pref="claude-sonnet-5.5", top_k=3)
        res = await sys_b.execute(
            query="neutral atom gate fidelity and coherence times",
            api_key="mock-key-12345",
            cached_papers=sample_papers
        )
        self.assertEqual(res.system_name, "System B: Conventional RAG (Single Call)")
        self.assertEqual(res.input_tokens, 1200)
        self.assertEqual(res.output_tokens, 600)
        self.assertEqual(res.total_tokens, 1800)
        self.assertTrue(res.retrieved_sources_count >= 1)
        self.assertIn("99.5%", res.output_text)


class TestWorkbenchSystem(unittest.IsolatedAsyncioTestCase):
    @patch("evals.workbench_system.run_query_pipeline", new_callable=AsyncMock)
    async def test_workbench_execution_mapping(self, mock_pipeline):
        mock_pipeline.return_value = {
            "quick_answer": "Neutral atoms achieve 99.5% fidelity.",
            "executive_summary": "Comprehensive executive summary.",
            "dossier_sections": [
                {"heading": "Hardware Gates", "content_html": "<p>Content</p>", "claims": []}
            ],
            "citations": [{"paper_id": "p1", "title": "Paper 1"}],
            "evaluated_claims": [{"id": "c1", "status": "verified"}],
            "confidence_score": 98.5,
            "token_usage": {"prompt_tokens": 1500, "completion_tokens": 500, "total_tokens": 2000}
        }
        wb = WorkbenchSystem(model_pref="claude-sonnet-5.5")
        res = await wb.execute("Quantum fidelity", api_key="sk-ant-test-12345")
        self.assertEqual(res.system_name, "System A: ResearchWorkbench (Multi-Agent)")
        self.assertEqual(res.confidence_score, 98.5)
        self.assertEqual(res.verified_claims_count, 1)
        self.assertEqual(res.total_tokens, 2000)
        self.assertIn("Quick Answer", res.output_text)


class TestTextAnalysisAndMetrics(unittest.TestCase):
    def test_platitude_detection(self):
        text_with_platitudes = (
            "It is important to note that quantum computing plays a crucial role in future encryption. "
            "This sheds light on a rapidly evolving landscape."
        )
        analysis = analyze_text_quality(text_with_platitudes)
        self.assertTrue(analysis["platitudes_count"] >= 3)

    def test_platitude_clean_text(self):
        clean_text = (
            "Neutral-atom tweezer arrays using 171Yb achieve 99.5% two-qubit gate fidelity with "
            "$$H = \\sum_i \\Omega_i |g_i\\rangle\\langle r_i|$$ and 200 ns pulse durations."
        )
        analysis = analyze_text_quality(clean_text)
        self.assertEqual(analysis["platitudes_count"], 0)
        self.assertTrue(analysis["latex_equations_count"] >= 1)

    def test_cost_calculation(self):
        cost_sonnet = calculate_estimated_cost("claude-sonnet-5.5", 10_000, 2_000)
        # 10k * $3/M = $0.030, 2k * $15/M = $0.030 -> Total = $0.060
        self.assertAlmostEqual(cost_sonnet, 0.06, places=3)

        cost_luna = calculate_estimated_cost("gpt-6-luna", 10_000, 2_000)
        # 10k * $0.10/M = $0.001, 2k * $0.50/M = $0.001 -> Total = $0.002
        self.assertAlmostEqual(cost_luna, 0.002, places=4)

        cost_sol = calculate_estimated_cost("gpt-6.1-sol", 10_000, 2_000)
        # 10k * $2.00/M = $0.020, 2k * $10.00/M = $0.020 -> Total = $0.040
        self.assertAlmostEqual(cost_sol, 0.040, places=4)

        cost_mini = calculate_estimated_cost("gpt-5.4-mini", 10_000, 2_000)
        # 10k * $0.75/M = $0.0075, 2k * $4.50/M = $0.009 -> Total = $0.0165
        self.assertAlmostEqual(cost_mini, 0.0165, places=4)

        cost_astra = calculate_estimated_cost("gpt-6-astra", 10_000, 2_000)
        # 10k * $10.00/M = $0.100, 2k * $50.00/M = $0.100 -> Total = $0.200
        self.assertAlmostEqual(cost_astra, 0.200, places=4)


class TestStudyUIServer(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from evals.ui_server import app
        self.client = TestClient(app)

    def test_index_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ResearchWorkbench", res.text)
        self.assertIn("Comparative Scientific Study", res.text)

    def test_api_prompts(self):
        res = self.client.get("/api/prompts")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 5)
        self.assertEqual(data[0]["id"], 1)

    def test_download_docx(self):
        res = self.client.get("/api/download-docx")
        self.assertEqual(res.status_code, 200)
        self.assertIn("openxmlformats", res.headers.get("content-type", ""))
        self.assertTrue(len(res.content) > 10_000)

    @patch("evals.ui_server._run_single_system", new_callable=AsyncMock)
    def test_run_system_with_custom_key(self, mock_run):
        mock_run.return_value = {
            "system_name": "System C: Direct Single API Call",
            "query": "Test",
            "model": "claude-opus-5.5",
            "output_text": "Monograph",
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
            "latency_seconds": 1.5,
            "cost_usd": 0.015,
            "text_analysis": {"platitudes_count": 0}
        }
        res = self.client.post("/api/run-system", json={
            "system_type": "c",
            "query": "Test query",
            "model": "claude-opus-5.5",
            "api_key": "sk-ant-custom-key-12345"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["system_name"], "System C: Direct Single API Call")
        mock_run.assert_called_once_with(
            sys_type="c",
            query="Test query",
            model="claude-opus-5.5",
            api_key="sk-ant-custom-key-12345",
            top_k=5
        )


class TestMainAppEvalsEndpoints(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.app import app
        self.client = TestClient(app)

    def test_frontend_has_study_integration(self):
        res = self.client.get("/?auth_token=test_client_token")
        self.assertEqual(res.status_code, 200)
        self.assertIn('canvasArchBar', res.text)
        self.assertIn('arch-radio-group', res.text)
        self.assertIn('btn-quick-arch-toggle', res.text)
        self.assertIn('about-comparison-card', res.text)

    def test_api_evals_prompts(self):
        res = self.client.get("/api/evals/prompts")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 5)
        self.assertEqual(data[0]["id"], 1)

    def test_api_evals_download_docx(self):
        res = self.client.get("/api/evals/download-docx")
        self.assertEqual(res.status_code, 200)
        self.assertIn("openxmlformats", res.headers.get("content-type", ""))
        self.assertTrue(len(res.content) > 10_000)

    @patch("backend.app._run_eval_single_system", new_callable=AsyncMock)
    def test_api_evals_run_system(self, mock_run):
        mock_run.return_value = {
            "system_name": "System C: Direct Single API Call",
            "query": "Neutral atom",
            "model": "claude-sonnet-5.5",
            "output_text": "Monograph",
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300
        }
        res = self.client.post("/api/evals/run-system", json={
            "system_type": "c",
            "query": "Neutral atom",
            "model": "claude-sonnet-5.5",
            "api_key": "sk-ant-key"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["system_name"], "System C: Direct Single API Call")

    @patch("backend.app._run_eval_single_system", new_callable=AsyncMock)
    def test_api_evals_run_comparison(self, mock_run):
        mock_run.return_value = {
            "system_name": "System Result",
            "output_text": "Comparison text"
        }
        res = self.client.post("/api/evals/run-comparison", json={
            "query": "Neutral atom comparison",
            "system_a": {"enabled": True, "model": "claude-sonnet-5.5", "api_key": "key-a"},
            "system_b": {"enabled": True, "model": "claude-sonnet-5.5", "api_key": "key-b", "top_k": 5},
            "system_c": {"enabled": False, "model": "claude-sonnet-5.5", "api_key": None}
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("system_a", data["results"])
        self.assertIn("system_b", data["results"])


if __name__ == "__main__":
    unittest.main()

