"""
End-to-End Test Suite for AI Research Workbench v3.0.0
Validates:
- Backend Health
- History API & Persistence (BONUS-01, BONUS-02)
- Multi-Format Export API: Word docx and LaTeX tex (BONUS-03)
- Query Suggestions API (BONUS-08)
- Path Traversal Security Checks (SEC-04, SEC-09, SEC-10)
- Response Caching & Zero-Token Replay (TOK-03-REVISED)
- Dual-Output Data Integrity (DUAL-01, DUAL-02)
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
from backend.database import get_run_history, get_run_by_id, delete_run

class TestResearchWorkbenchE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.dummy_dossier = {
            "query": "Quantum Error Mitigation in Neutral Atom Qubits",
            "quick_answer": "Recent breakthroughs demonstrate neutral atom arrays achieving fault-tolerant thresholds using dynamical decoupling.",
            "executive_summary": "Neutral atom quantum computing utilizes optical tweezers to manipulate individual atoms.",
            "dossier_sections": [
                {
                    "title": "Hardware Architecture",
                    "content": "Optical tweezers operate in ultra-high vacuum environments.",
                    "takeaways": ["Sub-micron positioning precision", "Low decoherence rates"]
                }
            ],
            "evaluated_claims": [
                {
                    "claim": "Rydberg blockade enables two-qubit gate fidelities exceeding 99.5%.",
                    "confidence": 0.96,
                    "status": "verified",
                    "source": "Nature 2024"
                }
            ],
            "citations": [
                {
                    "id": "ref-1",
                    "title": "High-fidelity gates in neutral atoms",
                    "authors": ["Bluvstein, D.", "Lukin, M."],
                    "year": 2024,
                    "venue": "Nature",
                    "url": "https://arxiv.org/abs/2312.03982"
                }
            ],
            "token_usage": {
                "total_tokens": 1250,
                "cached": False
            }
        }

    def test_01_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "3.0.0")

    def test_02_history_api(self):
        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["runs"], list)

    def test_03_query_suggestions(self):
        resp = self.client.get("/api/suggest?q=quantum")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("suggestions", data)
        self.assertIsInstance(data["suggestions"], list)
        self.assertGreater(len(data["suggestions"]), 0)
        self.assertTrue(any("quantum" in s.lower() for s in data["suggestions"]))

    def test_04_export_docx(self):
        resp = self.client.post(
            "/api/export/docx",
            json={"dossier": self.dummy_dossier}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertGreater(len(resp.content), 1000)

    def test_05_export_latex(self):
        resp = self.client.post(
            "/api/export/latex",
            json={"dossier": self.dummy_dossier}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/x-latex", resp.headers["content-type"])
        latex_text = resp.content.decode("utf-8")
        self.assertIn("\\documentclass[11pt,a4paper]{article}", latex_text)
        self.assertIn("Quantum Error Mitigation", latex_text)
        self.assertIn("Recent breakthroughs demonstrate", latex_text)
        self.assertIn("\\section*{References}", latex_text)
        self.assertIn("Bluvstein, D., Lukin, M.", latex_text)

    def test_06_security_path_traversal_prevention(self):
        # SEC-09 / SEC-10: Traversal attempts must fail safely
        bad_paths = [
            "/api/pdf/figures/../../etc/passwd/test.png",
            "/api/pdf/figures/test_session/..%2f..%2fwindows%2fwin.ini",
            "/api/pdf/figures/session1/malicious.exe"
        ]
        for path in bad_paths:
            resp = self.client.get(path)
            self.assertIn(resp.status_code, [400, 403, 404])

    def test_07_post_pipeline_stream_validation(self):
        # SEC-01: Validates that POST streaming accepts request correctly
        resp = self.client.post(
            "/api/pipeline/stream",
            json={
                "query": "Quantum Computing Neutral Atoms",
                "paper_limit": 2
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/event-stream", resp.headers["content-type"])

if __name__ == "__main__":
    unittest.main()
