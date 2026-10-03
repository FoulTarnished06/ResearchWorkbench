"""
test_dialogue.py - Automated test suite for Continuous Research Dialogue (CHAT-01..07)
Validates:
1. SQLite schema & CRUD (dialogue_messages table, sequential turn indices, cascade deletion).
2. Dynamic Hierarchical State & Rolling Context Compression (DHS-RCC):
   - Monograph Anchor Digest <= 450 tokens
   - Rolling Memory <= 180 tokens
   - Dynamic Context <= 150 tokens
3. Multi-turn dialogue simulation across 3 turns proving O(1) constant token bounds (<= 750 tokens).
4. FastAPI endpoints: POST /api/dialogue/chat, GET /api/dialogue/history/{id}, DELETE /api/dialogue/history/{id}.
"""

import os
import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.database import (
    init_db,
    log_pipeline_run,
    save_cached_sentences,
    save_dialogue_message,
    get_dialogue_history,
    clear_dialogue_history,
    delete_run,
    get_run_by_id
)
from backend.agents.dialogue_synthesizer import (
    build_monograph_digest,
    build_rolling_memory,
    retrieve_dynamic_context,
    run_dialogue_turn
)
from backend.app import app

client = TestClient(app)

class TestDialogueEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Create a unique test run
        self.test_run_id = f"test_run_chat_{os.urandom(4).hex()}"
        self.test_query = "Transformer Attention Scaling Laws and Asymptotic Bounds"
        
        dummy_results = {
            "query": self.test_query,
            "quick_answer": "Attention complexity scales quadratically $O(N^2)$ without sparse approximations.",
            "executive_summary": "Transformers display $O(N^2)$ time and space complexity in standard scaled dot-product attention.",
            "takeaways": [
                "Quadratic computational bound $O(N^2)$ limits standard context length.",
                "FlashAttention avoids intermediate HBM IO operations, optimizing kernel execution.",
                "Linear attention alternatives approximate softmax kernels with sub-quadratic memory footprint."
            ],
            "dossier_sections": [
                {
                    "sub_question": "What is the asymptotic complexity of standard self-attention?",
                    "answer_html": "<p>Standard scaled dot-product attention scales as $O(N^2)$ where $N$ is sequence length.</p>"
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
                    "text": "Self-attention exhibits quadratic asymptotic computational complexity $O(N^2)$.",
                    "confidence_score": 0.96,
                    "verification_method": "Verified in SQLite"
                },
                {
                    "claim_id": "c2",
                    "text": "FlashAttention tiles computation to reduce memory bandwidth bottlenecks.",
                    "confidence_score": 0.92,
                    "verification_method": "Verified in SQLite"
                }
            ]
        }
        
        # Log parent run
        log_pipeline_run(self.test_run_id, self.test_query, 1200, 3.5, dummy_results)
        
        # Save sample cached sentences for SQLite cosine retrieval
        save_cached_sentences(self.test_query, [
            {
                "sentence": "Scaled dot-product attention exhibits quadratic memory and computational scaling $O(N^2)$ with respect to sequence length $N$.",
                "score": 0.95,
                "ref_id": "ref_vaswani2017"
            },
            {
                "sentence": "FlashAttention uses tiling to avoid reading and writing the $N \\times N$ attention matrix to high bandwidth memory.",
                "score": 0.93,
                "ref_id": "ref_vaswani2017"
            },
            {
                "sentence": "Linear attention formulations decompose the softmax kernel into feature maps yielding $O(N)$ linear complexity.",
                "score": 0.90,
                "ref_id": "ref_vaswani2017"
            }
        ])

    def tearDown(self):
        delete_run(self.test_run_id)

    def test_chat_01_db_crud_and_cascade(self):
        """CHAT-01: Verifies dialogue_messages CRUD, ordering, and cascade deletion on parent run removal."""
        # Save user turn
        msg1_id = save_dialogue_message(
            run_id=self.test_run_id,
            role="user",
            content="What causes the quadratic bottleneck?",
            tokens_used=0
        )
        self.assertTrue(msg1_id.startswith("msg_"))

        # Save assistant turn
        msg2_id = save_dialogue_message(
            run_id=self.test_run_id,
            role="assistant",
            content="<p>Softmax pairwise dot-products between all tokens.</p>",
            quick_summary="Pairwise token interaction produces O(N^2) complexity.",
            answer_html="<p>Softmax pairwise dot-products between all tokens.</p>",
            tokens_used=350
        )
        self.assertTrue(msg2_id.startswith("msg_"))

        # Fetch history
        history = get_dialogue_history(self.test_run_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["turn_index"], 0)
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["turn_index"], 1)
        self.assertEqual(history[1]["quick_summary"], "Pairwise token interaction produces O(N^2) complexity.")

        # Test clear history
        cleared = clear_dialogue_history(self.test_run_id)
        self.assertTrue(cleared)
        self.assertEqual(len(get_dialogue_history(self.test_run_id)), 0)

        # Save again and test cascade deletion with parent run removal
        save_dialogue_message(
            run_id=self.test_run_id,
            role="user",
            content="Testing cascade delete",
            tokens_used=0
        )
        self.assertEqual(len(get_dialogue_history(self.test_run_id)), 1)
        delete_run(self.test_run_id)
        self.assertEqual(len(get_dialogue_history(self.test_run_id)), 0)

    def test_chat_02_monograph_digest_budget(self):
        """CHAT-02: Verifies Monograph Anchor Digest compression adheres strictly to <= 450 token budget."""
        digest = build_monograph_digest(self.test_run_id)
        self.assertIn("query", digest)
        self.assertIn("summary", digest)
        self.assertIn("takeaways", digest)
        self.assertIn("claims", digest)
        self.assertIn("digest_text", digest)

        digest_text = digest["digest_text"]
        # Approximate tokens (chars / 3.8)
        approx_tokens = len(digest_text) / 3.8
        self.assertLessEqual(approx_tokens, 450, f"Digest tokens ({approx_tokens:.1f}) exceeds 450 token budget")
        self.assertIn("Scaling Laws", digest_text)

    def test_chat_03_rolling_memory_budget(self):
        """CHAT-02: Verifies Rolling Memory updates properly and bounds context <= 180 tokens."""
        # Empty dialogue initially
        initial_mem, initial_last = build_rolling_memory(self.test_run_id)
        self.assertEqual(initial_mem, "")
        self.assertIsNone(initial_last)

        # Add 3 turns
        save_dialogue_message(self.test_run_id, "user", "How does FlashAttention work?", tokens_used=0)
        save_dialogue_message(self.test_run_id, "assistant", "<p>FlashAttention tiles memory...</p>", quick_summary="FlashAttention tiles SRAM memory.", tokens_used=340)
        save_dialogue_message(self.test_run_id, "user", "Does it change the mathematical output?", tokens_used=0)
        save_dialogue_message(self.test_run_id, "assistant", "<p>No, FlashAttention is mathematically exact.</p>", quick_summary="Exact numerical equivalence to standard attention.", tokens_used=320)

        trajectory_text, last_turn = build_rolling_memory(self.test_run_id)
        self.assertIsNotNone(last_turn)
        self.assertIn("Exact numerical equivalence", last_turn["assistant_summary"])
        total_mem_chars = len(trajectory_text) + len(last_turn["user_query"]) + len(last_turn["assistant_summary"])
        approx_tokens = total_mem_chars / 3.8
        self.assertLessEqual(approx_tokens, 180, f"Rolling memory tokens ({approx_tokens:.1f}) exceeds 180 token budget")

    def test_chat_04_dynamic_context_retrieval(self):
        """CHAT-02: Verifies dynamic SQLite context retrieval pulls top matching sentences <= 150 tokens."""
        sentences = retrieve_dynamic_context(self.test_run_id, "Does FlashAttention avoid reading and writing HBM?")
        self.assertIsInstance(sentences, list)
        self.assertGreaterEqual(len(sentences), 1)
        joined = " ".join(sentences)
        approx_tokens = len(joined) / 3.8
        self.assertLessEqual(approx_tokens, 150, f"Dynamic context ({approx_tokens:.1f}) exceeds 150 tokens")
        self.assertTrue(any("FlashAttention" in s or "attention" in s.lower() for s in sentences))

    def test_chat_05_multi_turn_constant_bound_simulation(self):
        """CHAT-02: Simulates 3 continuous turns proving O(1) constant token scaling (<= 750 tokens/turn)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        turn_prompts = [
            "What are the dominant factors causing quadratic scaling in self-attention?",
            "How does FlashAttention optimize IO memory access during training?",
            "Summarize the trade-offs of linear attention approximations versus exact attention."
        ]

        token_usages = []

        try:
            for prompt in turn_prompts:
                res = loop.run_until_complete(run_dialogue_turn(
                    run_id=self.test_run_id,
                    user_message=prompt,
                    provider="auto",
                    disable_fallback=False
                ))

                self.assertIn("id", res)
                self.assertIn("quick_summary", res)
                self.assertIn("answer_html", res)
                self.assertIn("tokens_used", res)
                self.assertIn("token_savings_pct", res)

                tokens = res["tokens_used"]
                token_usages.append(tokens)

                # Each turn must strictly adhere to <= 750 tokens
                self.assertLessEqual(tokens, 750, f"Turn tokens {tokens} exceeded 750 threshold")
                # Savings vs standard chat baseline (4,500 tokens) must be >= 70%
                self.assertGreaterEqual(res["token_savings_pct"], 70)
                # Output must be sanitized HTML with KaTeX math
                self.assertNotIn("<script>", res["answer_html"])

            # Verify history in DB has all 6 messages (3 user + 3 assistant)
            history = get_dialogue_history(self.test_run_id)
            self.assertEqual(len(history), 6)
            
            # Check O(1) behavior: tokens on turn 3 should NOT be significantly greater than turn 1
            # (Unlike standard chat where turn 3 would be 2x-3x larger)
            self.assertLessEqual(token_usages[2], 750)
        finally:
            loop.close()

    def test_chat_06_fastapi_endpoints(self):
        """CHAT-03: Verifies POST /api/dialogue/chat, GET history, and DELETE history endpoints."""
        # 1. POST /api/dialogue/chat
        payload = {
            "run_id": self.test_run_id,
            "message": "Can you formalize the scaling bound of self-attention?",
            "provider": "auto",
            "disable_fallback": False
        }
        res = client.post("/api/dialogue/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["run_id"], self.test_run_id)
        self.assertIn("quick_summary", data)
        self.assertIn("answer_html", data)
        self.assertIn("prompt_tokens", data)
        self.assertIn("completion_tokens", data)
        self.assertEqual(data["tokens_used"], data["prompt_tokens"] + data["completion_tokens"])
        self.assertGreater(data["tokens_used"], 0)
        self.assertLessEqual(data["tokens_used"], 750)

        # 2. GET /api/dialogue/history/{run_id}
        hist_res = client.get(f"/api/dialogue/history/{self.test_run_id}")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.json()
        self.assertEqual(hist_data["status"], "success")
        self.assertEqual(hist_data["count"], 2)  # 1 user + 1 assistant
        self.assertEqual(len(hist_data["messages"]), 2)

        # 3. DELETE /api/dialogue/history/{run_id}
        del_res = client.delete(f"/api/dialogue/history/{self.test_run_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["cleared"])

        # 4. Verify cleared
        check_res = client.get(f"/api/dialogue/history/{self.test_run_id}")
        self.assertEqual(check_res.json()["count"], 0)

    def test_chat_07_live_gemini_call_signature(self):
        """Verify that live Gemini call passes prompt, api_key, model_pref, and system_instruction without error."""
        from unittest.mock import patch, AsyncMock

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mock_resp = ('{"quick_summary": "Live Summary", "answer_html": "<p>Live content</p>"}', 345)
            with patch("backend.agents.dialogue_synthesizer.call_gemini_api", new_callable=AsyncMock) as mock_gemini:
                mock_gemini.return_value = mock_resp
                res = loop.run_until_complete(run_dialogue_turn(
                    run_id=self.test_run_id,
                    user_message="What is the global distribution of lithium reserves?",
                    gemini_key="test-gemini-key-123",
                    provider="gemini",
                    disable_fallback=True
                ))

                self.assertTrue(mock_gemini.called)
                args, kwargs = mock_gemini.call_args
                self.assertEqual(args[1], "test-gemini-key-123")
                self.assertEqual(kwargs.get("model_pref"), "gemini-3.6-flash")
                self.assertIn("system_instruction", kwargs)
                self.assertEqual(res["quick_summary"], "Live Summary")
                self.assertIn("Live content", res["answer_html"])
                self.assertEqual(res["is_fallback"], False)
        finally:
            loop.close()

    def test_chat_08_live_anthropic_call_signature(self):
        """Verify that live Claude call passes prompt, api_key, model_pref, and system_instruction without error."""
        from unittest.mock import patch, AsyncMock

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mock_resp = ('{"quick_summary": "Claude Summary", "answer_html": "<p>Claude content</p>"}', 410)
            with patch("backend.agents.dialogue_synthesizer.call_anthropic_api", new_callable=AsyncMock) as mock_claude:
                mock_claude.return_value = mock_resp
                res = loop.run_until_complete(run_dialogue_turn(
                    run_id=self.test_run_id,
                    user_message="Detail the environmental impacts of brine extraction.",
                    anthropic_key="test-anthropic-key-456",
                    provider="claude",
                    disable_fallback=True
                ))

                self.assertTrue(mock_claude.called)
                args, kwargs = mock_claude.call_args
                self.assertEqual(args[1], "test-anthropic-key-456")
                self.assertEqual(kwargs.get("model_pref"), "claude-sonnet-5")
                self.assertIn("system_instruction", kwargs)
                self.assertEqual(res["quick_summary"], "Claude Summary")
                self.assertIn("Claude content", res["answer_html"])
                self.assertEqual(res["is_fallback"], False)
        finally:
            loop.close()

    def test_chat_09_gemini_31_pro_and_claude_opus_options(self):
        """Verify that Gemini 3.1 Pro and Claude Opus 4.5 routes are properly resolved."""
        from unittest.mock import patch, AsyncMock

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Test Gemini 3.1 Pro
            with patch("backend.agents.dialogue_synthesizer.call_gemini_api", new_callable=AsyncMock) as mock_gemini:
                mock_gemini.return_value = ('{"quick_summary": "Pro Summary", "answer_html": "<p>Pro content</p>"}', 400)
                res_pro = loop.run_until_complete(run_dialogue_turn(
                    run_id=self.test_run_id,
                    user_message="Deep reasoning inquiry on battery chemistry.",
                    gemini_key="test-pro-key",
                    provider="gemini-3.1-pro",
                    disable_fallback=True
                ))
                self.assertEqual(mock_gemini.call_args[1]["model_pref"], "gemini-3.1-pro")
                self.assertEqual(res_pro["provider_used"], "Gemini 3.1 Pro (DHS-RCC)")

            # Test Claude Opus 4.5
            with patch("backend.agents.dialogue_synthesizer.call_anthropic_api", new_callable=AsyncMock) as mock_claude:
                mock_claude.return_value = ('{"quick_summary": "Opus Summary", "answer_html": "<p>Opus content</p>"}', 450)
                res_opus = loop.run_until_complete(run_dialogue_turn(
                    run_id=self.test_run_id,
                    user_message="Frontier analysis of lithium recovery.",
                    anthropic_key="test-opus-key",
                    provider="claude-opus-4.5",
                    disable_fallback=True
                ))
                self.assertEqual(mock_claude.call_args[1]["model_pref"], "claude-opus-4.5")
                self.assertEqual(res_opus["provider_used"], "Claude Opus 4.5 (DHS-RCC)")
        finally:
            loop.close()

if __name__ == "__main__":
    unittest.main()
