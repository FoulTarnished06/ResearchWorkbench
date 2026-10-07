"""
test_followup.py - Automated test suite for the Low-Token Follow-Up Inquiry Engine (FOL-01..07)
Validates:
1. SQLite schema & CRUD (followup_interactions table, cascade deletion).
2. Inverted Differential Context Compression (IDCC) context retrieval.
3. Sub-600 token budget verification and LaTeX math formatting.
4. FastAPI endpoints: POST /api/pipeline/followup, GET /api/history/prompts,
   GET /api/history/run/{id}/followups, DELETE /api/history/followup/{id}.
"""

import os
import sys

# Ensure root directory on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.database import (
    init_db,
    log_pipeline_run,
    save_scraped_papers,
    save_cached_sentences,
    save_followup_interaction,
    get_followups_for_run,
    get_all_prompt_history,
    delete_followup,
    delete_run,
    get_run_by_id
)
from backend.agents.followup_synthesizer import (
    retrieve_idcc_context,
    run_followup_synthesis
)
from backend.app import app

client = TestClient(app)

class TestFollowupEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Create a unique test run
        self.test_run_id = f"test_run_fol_{os.urandom(4).hex()}"
        self.test_query = "Transformer Attention Scaling Laws in Large Models"
        
        dummy_results = {
            "query": self.test_query,
            "quick_answer": "Attention complexity scales quadratically $O(N^2)$ without sparse approximations.",
            "executive_summary": "Transformers display $O(N^2)$ complexity.",
            "takeaways": ["Quadratic computational bound", "KV-cache memory saturation"],
            "dossier_sections": [
                {
                    "sub_question": "What is the asymptotic complexity of standard self-attention?",
                    "content_html": "<p>Standard scaled dot-product attention scales as $O(N^2)$ where $N$ is sequence length.</p>"
                }
            ],
            "citations": [
                {
                    "ref_id": "ref_vaswani2017",
                    "title": "Attention Is All You Need",
                    "authors": "Vaswani et al.",
                    "year": 2017,
                    "venue": "NeurIPS",
                    "url": "https://arxiv.org/abs/1706.03762"
                }
            ],
            "evaluated_claims": [
                {
                    "claim_id": "c1",
                    "text": "Self-attention has quadratic asymptotic computational complexity.",
                    "confidence_score": 0.95,
                    "verification_method": "Verified in SQLite"
                }
            ]
        }
        
        # Log parent run
        log_pipeline_run(self.test_run_id, self.test_query, 1200, 3.5, dummy_results)
        
        # Save sample cached sentences for IDCC retrieval
        save_cached_sentences(self.test_query, [
            {
                "sentence": "Scaled dot-product attention exhibits quadratic memory and computational scaling $O(N^2)$ with respect to context window length $N$.",
                "score": 0.94,
                "ref_id": "ref_vaswani2017"
            },
            {
                "sentence": "FlashAttention avoids materialization of the $N \\times N$ attention matrix in HBM, executing in $O(N)$ SRAM IO operations.",
                "score": 0.91,
                "ref_id": "ref_vaswani2017"
            }
        ])

    def tearDown(self):
        # Clean up test run (cascades to follow-ups)
        delete_run(self.test_run_id)

    def test_fol_01_db_crud_and_cascade(self):
        """FOL-01: Verifies followup_interactions CRUD and cascade deletion on parent run removal."""
        fol_id = save_followup_interaction(
            parent_run_id=self.test_run_id,
            question="What is the SRAM IO complexity?",
            quick_summary="FlashAttention achieves $O(N)$ IO operations.",
            answer_html="<p>FlashAttention optimizes SRAM usage.</p>",
            claim_id="c1",
            target_topic="Transformer Attention",
            ref_id="ref_vaswani2017",
            tokens_used=410
        )
        self.assertIsNotNone(fol_id)

        # Retrieve follow-ups for run
        followups = get_followups_for_run(self.test_run_id)
        self.assertEqual(len(followups), 1)
        self.assertEqual(followups[0]["id"], fol_id)
        self.assertEqual(followups[0]["question"], "What is the SRAM IO complexity?")
        self.assertEqual(followups[0]["tokens_used"], 410)

        # Delete individual follow-up
        deleted = delete_followup(fol_id)
        self.assertTrue(deleted)
        self.assertEqual(len(get_followups_for_run(self.test_run_id)), 0)

        # Re-add and test cascade deletion
        fol_id2 = save_followup_interaction(
            parent_run_id=self.test_run_id,
            question="What happens during parent run deletion?",
            quick_summary="Follow-ups should be cascade deleted.",
            answer_html="<p>Testing cascade.</p>",
            tokens_used=350
        )
        self.assertEqual(len(get_followups_for_run(self.test_run_id)), 1)
        
        delete_run(self.test_run_id)
        self.assertEqual(len(get_followups_for_run(self.test_run_id)), 0)
        self.assertIsNone(get_run_by_id(self.test_run_id))

    def test_fol_02_idcc_context_retrieval(self):
        """FOL-02: Verifies Inverted Differential Context Compression retrieves top dense context from SQLite."""
        top_sentences = retrieve_idcc_context(
            parent_run_id=self.test_run_id,
            target_topic="FlashAttention memory complexity",
            claim_id="c1",
            max_sentences=3
        )
        self.assertIsInstance(top_sentences, list)
        self.assertGreater(len(top_sentences), 0)
        self.assertTrue(any("FlashAttention" in s["text"] for s in top_sentences))

    def test_fol_03_sub_600_token_synthesis_and_math(self):
        """FOL-02: Verifies follow-up synthesis respects sub-600 token budget and includes LaTeX math."""
        from unittest.mock import patch
        mock_resp = (
            '{"quick_summary": "FlashAttention uses tiling to bound memory IO by O(N).", "answer_html": "<p>Tiling bounds IO complexity to $O(N)$ with SRAM blocks.</p>"}',
            350
        )
        with patch("backend.agents.followup_synthesizer.call_gemini_api", return_value=mock_resp):
            res = asyncio.run(run_followup_synthesis(
                parent_run_id=self.test_run_id,
                query="Can you formalize the IO complexity and memory bounds?",
                claim_id="c1",
                target_topic="Attention Complexity",
                gemini_key="mock-key",
                disable_fallback=False
            ))
        
        self.assertIn("id", res)
        self.assertIn("quick_summary", res)
        self.assertIn("answer_html", res)
        self.assertIn("prompt_tokens", res)
        self.assertIn("completion_tokens", res)
        self.assertEqual(res["tokens_used"], res["prompt_tokens"] + res["completion_tokens"])
        self.assertLessEqual(res["tokens_used"], 600, "Follow-up must strictly consume <= 600 tokens")
        self.assertGreaterEqual(res["token_savings_pct"], 70, "Token savings should be at least 70% vs 3,600 chat baseline")
        # Check math preservation in HTML
        self.assertTrue("$" in res["answer_html"] or "O(" in res["answer_html"])

    def test_fol_04_api_pipeline_followup_endpoint(self):
        """FOL-03: Tests POST /api/pipeline/followup endpoint with valid payload."""
        from unittest.mock import patch
        mock_resp = (
            '{"quick_summary": "FlashAttention uses tiling to bound memory IO by O(N).", "answer_html": "<p>Tiling bounds IO complexity to $O(N)$ with SRAM blocks.</p>"}',
            350
        )
        with patch("backend.agents.followup_synthesizer.call_gemini_api", return_value=mock_resp):
            response = client.post("/api/pipeline/followup", json={
                "parent_run_id": self.test_run_id,
                "claim_id": "c1",
                "target_topic": "Transformer Attention",
                "query": "How does FlashAttention avoid quadratic IO overhead?",
                "provider": "auto",
                "gemini_key": "mock-key",
                "disable_fallback": False
            })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["parent_run_id"], self.test_run_id)
        self.assertIn("quick_summary", data)
        self.assertIn("answer_html", data)
        self.assertIn("prompt_tokens", data)
        self.assertIn("completion_tokens", data)
        self.assertEqual(data["tokens_used"], data["prompt_tokens"] + data["completion_tokens"])
        self.assertLessEqual(data["tokens_used"], 600)
        self.assertGreaterEqual(data["token_savings_pct"], 70)

    def test_fol_05_api_prompt_history_endpoints(self):
        """FOL-06: Tests GET /api/history/prompts and follow-up tree lineage."""
        from unittest.mock import patch
        mock_resp = (
            '{"quick_summary": "KV-cache memory scales linearly with sequence length.", "answer_html": "<p>KV-cache memory bound is $O(L \\cdot d)$.</p>"}',
            300
        )
        # Add a follow-up first
        with patch("backend.agents.followup_synthesizer.call_gemini_api", return_value=mock_resp):
            client.post("/api/pipeline/followup", json={
                "parent_run_id": self.test_run_id,
                "query": "What is the memory bound for KV-cache?",
                "target_topic": "KV-cache scaling",
                "gemini_key": "mock-key"
            })

        # Test GET /api/history/prompts
        res = client.get("/api/history/prompts?limit=50")
        self.assertEqual(res.status_code, 200)
        tree_data = res.json()
        self.assertEqual(tree_data["status"], "success")
        self.assertGreater(tree_data["count"], 0)
        
        # Verify our run exists in the prompt tree
        matched_run = next((p for p in tree_data["prompts"] if p["id"] == self.test_run_id), None)
        self.assertIsNotNone(matched_run)
        self.assertIn("followups", matched_run)
        self.assertEqual(matched_run["followup_count"], 1)
        self.assertIn("What is the memory bound for KV-cache?", matched_run["followups"][0]["question"])

        # Test GET /api/history/run/{run_id}/followups
        res_run = client.get(f"/api/history/run/{self.test_run_id}/followups")
        self.assertEqual(res_run.status_code, 200)
        run_fol_data = res_run.json()
        self.assertEqual(run_fol_data["count"], 1)

        # Test DELETE /api/history/followup/{id}
        fol_id = run_fol_data["followups"][0]["id"]
        res_del = client.delete(f"/api/history/followup/{fol_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["deleted"])

    def test_fol_06_nonexistent_run_error_handling(self):
        """FOL-03: Tests 404 behavior for invalid or non-existent parent run ID."""
        response = client.post("/api/pipeline/followup", json={
            "parent_run_id": "nonexistent_run_999999",
            "query": "Will this fail gracefully?"
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())

if __name__ == "__main__":
    unittest.main()
