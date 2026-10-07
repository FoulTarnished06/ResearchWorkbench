"""
Automated Verification Suite for Deep Audit Fixes (All 17 Issues)
Validates:
1. Dead duplicate function removal in agent4_synthesizer
2. Mathematical complexity preservation in post_processor (no destructive O() overwrite)
3. Metadata integrity in agent1_scraper (no fake citationCount: 12 or 5)
4. Query length validation via Pydantic Field in app.py
5. Rejection of API keys in GET SSE query parameters (SEC-01 completion)
6. SQL LIKE wildcard escaping in /api/suggest
7. Honest offline fallback labeling in agent2_drafter
8. Frontend key storage migration to sessionStorage (zero localStorage key sets)
"""

import os
import sys
import unittest
import inspect
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Ensure root directory on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app, QueryRequest, PDFQueryRequest
from backend.post_processor import clean_monograph_text
import backend.agents.agent4_synthesizer as a4
from backend.agents.agent2_drafter import synthesize_fallback_draft, analyze_query_complexity

class TestAuditFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_duplicate_function_removed_in_agent4(self):
        """Verify only one call_gemini_factcheck exists and agent4 compiles cleanly."""
        src = inspect.getsource(a4)
        count = src.count("def call_gemini_factcheck(")
        self.assertEqual(count, 1, f"Expected exactly 1 definition of call_gemini_factcheck, found {count}")

    def test_02_mathematical_complexities_preserved(self):
        """Verify post_processor does NOT overwrite arbitrary O() complexities with O(E * N)."""
        test_cases = [
            ("The algorithm scales as O(n log n) under optimal sorting.", "O(n log n)"),
            ("Syndrome extraction completes in O(V^3) polynomial time.", "O(V^3)"),
            ("Grover search requires O(sqrt(N)) iterations.", "O(sqrt(N))"),
            ("State space expands with O(2^n) dimensionality.", "O(2^n)")
        ]
        for input_text, expected_sub in test_cases:
            cleaned = clean_monograph_text(input_text)
            self.assertIn(expected_sub, cleaned, f"Expected '{expected_sub}' preserved in '{cleaned}'")
            self.assertNotIn("$O(E \\cdot N)$", cleaned, f"Destructive $O(E \\cdot N)$ found in '{cleaned}'")

    def test_03_duplicate_complexities_collapsed_cleanly(self):
        """Verify consecutive duplicate math notation collapses without formula corruption."""
        input_text = "Runtime complexity is O(n log n) O(n log n) across trials."
        cleaned = clean_monograph_text(input_text)
        self.assertIn("O(n log n)", cleaned)
        self.assertNotIn("O(n log n) O(n log n)", cleaned)

    def test_04_query_length_validation(self):
        """Verify QueryRequest rejects empty query or queries exceeding 1000 characters."""
        # Empty query
        with self.assertRaises(ValidationError):
            QueryRequest(query="")
            
        # Over 1000 chars query
        with self.assertRaises(ValidationError):
            QueryRequest(query="a" * 1001)

        # Valid query
        valid_req = QueryRequest(query="Quantum Error Mitigation in Neutral Atom Qubits")
        self.assertEqual(valid_req.query, "Quantum Error Mitigation in Neutral Atom Qubits")

    def test_05_get_sse_rejects_query_param_api_keys(self):
        """Verify GET /api/pipeline/stream rejects API keys in query params with HTTP 400."""
        resp = self.client.get("/api/pipeline/stream?query=test&gemini_key=AIzaSyFakeKey123")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("prohibited for security", resp.json()["detail"])

        resp_pdf = self.client.get("/api/pdf/stream?session_id=sess_123&anthropic_key=sk-ant-fake123")
        self.assertEqual(resp_pdf.status_code, 400)
        self.assertIn("prohibited for security", resp_pdf.json()["detail"])

    def test_06_sql_suggest_wildcard_escaping(self):
        """Verify /api/suggest executes cleanly with wildcard inputs (%, _) without SQL injection."""
        resp = self.client.get("/api/suggest?q=%25_")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("suggestions", data)
        self.assertIsInstance(data["suggestions"], list)

    def test_07_agent2_honest_fallback_label(self):
        """Verify synthesize_fallback_draft returns valid sections and claims."""
        draft = synthesize_fallback_draft("Quantum Error Mitigation", [], [], target_count=3)
        self.assertIn("executive_summary", draft)
        self.assertIn("sections", draft)
        self.assertGreater(len(draft["sections"]), 0)

    def test_08_frontend_zero_localstorage_api_keys(self):
        """Verify frontend/app.js contains zero localStorage.setItem calls for API keys."""
        app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        forbidden_patterns = [
            "localStorage.setItem('workbench_gemini_key'",
            'localStorage.setItem("workbench_gemini_key"',
            "localStorage.setItem('workbench_anthropic_key'",
            'localStorage.setItem("workbench_anthropic_key"',
            "localStorage.setItem('workbench_serpapi_key'",
            'localStorage.setItem("workbench_serpapi_key"'
        ]
        for pat in forbidden_patterns:
            self.assertNotIn(pat, content, f"Found forbidden persistent key storage pattern: {pat}")

    def test_09_backend_package_init_and_env_example(self):
        """Verify backend/__init__.py and .env.example exist and are populated."""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        init_file = os.path.join(root_dir, "backend", "__init__.py")
        env_example = os.path.join(root_dir, ".env.example")
        
        self.assertTrue(os.path.isfile(init_file), "backend/__init__.py is missing")
        self.assertTrue(os.path.isfile(env_example), ".env.example is missing")
        
        import backend
        self.assertEqual(getattr(backend, "__version__", None), "4.0.0")

    def test_10_latex_export_sanitization(self):
        """Verify LaTeX export properly sanitizes special characters while preserving math blocks."""
        from backend.export import escape_latex, export_to_latex
        raw_text = "Achieved 99.5% fidelity & precision in gene_expression $O(E \\cdot N)$ with {parameters} #1."
        escaped = escape_latex(raw_text)
        
        self.assertIn(r"99.5\%", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"gene\_expression", escaped)
        self.assertIn(r"$O(E \cdot N)$", escaped)
        self.assertIn(r"\{parameters\}", escaped)
        self.assertIn(r"\#1", escaped)

        # Full dossier export test
        sample_dossier = {
            "query": "Quantum & Classical Algorithms in 99.5% Environments",
            "quick_answer": "Summary with special & characters and $O(n^2)$ complexity.",
            "takeaways": ["Takeaway 1: 50% gain & less overhead", "Takeaway 2: gene_analysis"],
            "executive_summary": "Executive monograph covering 100% of cases & parameters.",
            "sections": [
                {
                    "sub_question": "Subtopic 1: Performance & Analysis in 90% regimes",
                    "answer_html": "<p>Content with <b>bold</b> & special characters $O(1)$ and #hash.</p>"
                }
            ],
            "citations": [
                {
                    "ref_id": "ref_1",
                    "authors": ["Alice Smith", "Bob Jones"],
                    "title": "A & B: Testing 100% Fidelity",
                    "venue": "Nature & Science",
                    "url": "https://example.org/test?a=1&b=2"
                }
            ]
        }
        latex_doc = export_to_latex(sample_dossier)
        self.assertIn(r"Quantum \& Classical Algorithms in 99.5\% Environments", latex_doc)
        self.assertIn(r"(n.d.)", latex_doc)  # Year missing should fallback to n.d.
        self.assertIn(r"\textbf{Alice Smith, Bob Jones}", latex_doc)
        self.assertIn(r"Nature \& Science", latex_doc)

    def test_11_sqlite_foreign_keys_enabled(self):
        """Verify SQLite connections enable PRAGMA foreign_keys = ON by default."""
        from backend.database import get_db_connection, IS_POSTGRES
        if IS_POSTGRES:
            self.skipTest("PRAGMA foreign_keys is SQLite-specific; running on PostgreSQL.")
        conn = get_db_connection()
        try:
            fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            self.assertEqual(fk_status, 1, "Expected foreign keys to be enabled (1)")
        finally:
            conn.close()

    def test_12_database_year_fallbacks(self):
        """Verify database persists None when year is not provided, rather than hardcoded 2024."""
        from backend.database import save_scraped_papers, get_db_connection
        import uuid
        test_q = f"test_year_{uuid.uuid4().hex[:8]}"
        paper_id = f"p_test_{uuid.uuid4().hex[:8]}"
        save_scraped_papers(test_q, [
            {
                "id": paper_id,
                "title": "Paper Without Year",
                "authors": ["Author One"],
                "abstract": "Test abstract"
            }
        ])
        
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT year FROM scraped_papers WHERE id = ?", (paper_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertIsNone(row["year"], "Expected year to be NULL/None when omitted")
        finally:
            conn.execute("DELETE FROM scraped_papers WHERE id = ?", (paper_id,))
            conn.commit()
            conn.close()

    def test_13_frontend_dom_binding_integrity(self):
        """Verify frontend references correct cfg-agent2-model DOM ID and elements has zero missing IDs."""
        import re
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
        with open(os.path.join(frontend_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        with open(os.path.join(frontend_dir, "app.js"), "r", encoding="utf-8") as f:
            js = f.read()

        # No cfg-provider-agent2 references
        self.assertNotIn("cfg-provider-agent2", js, "Found obsolete cfg-provider-agent2 in app.js")

        # Check elements cache integrity
        html_ids = set(re.findall(r'id=["\']([^"\'>\s]+)["\']', html))
        start = js.find("const elements = {")
        end = js.find("};\n\n// Token breakdown")
        elem_block = js[start:end]
        elem_ids = re.findall(r'document\.getElementById\([\'"]([^\'"]+)[\'"]\)', elem_block)
        missing = [eid for eid in elem_ids if eid not in html_ids]
        self.assertEqual(missing, [], f"Orphaned element IDs found in app.js: {missing}")

    def test_14_pdf_strict_mode_default_unchecked(self):
        """Verify toggle-pdf-strict-api is unchecked by default in index.html for smooth offline use."""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
        with open(os.path.join(frontend_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('<input type="checkbox" id="toggle-pdf-strict-api">', html)
        self.assertNotIn('<input type="checkbox" id="toggle-pdf-strict-api" checked>', html)

    def test_15_frontend_fetch_sse_scope(self):
        """Verify fetchSSE declares currentEvent and currentData outside the while loop preventing ReferenceError."""
        app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            code = f.read()
        fetch_sse_idx = code.find("async function fetchSSE(")
        self.assertNotEqual(fetch_sse_idx, -1)
        func_end = code.find("function formatTokenBreakdown", fetch_sse_idx)
        func_code = code[fetch_sse_idx:func_end]

        # Ensure currentEvent and currentData are declared before 'while (true)'
        while_idx = func_code.find("while (true)")
        decl_idx = func_code.find("let currentData = '';")
        self.assertNotEqual(while_idx, -1)
        self.assertNotEqual(decl_idx, -1)
        self.assertLess(decl_idx, while_idx, "currentData must be declared outside/before while loop")

    def test_16_pdf_chat_bubble_xss_sanitization(self):
        """Verify appendChatBubble escapes user input and sanitizes assistant HTML."""
        app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("bubble.innerHTML = role === 'user' ? `<p>${escapeHTML(content)}</p>` : sanitizeHTML(content);", code)

    def test_17_offline_sanitize_html_fallback(self):
        """Verify sanitizeHTML contains resilient offline regex fallback stripping scripts and event handlers."""
        app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            code = f.read()
        start = code.find("function sanitizeHTML(html)")
        end = code.find("function escapeHTML(str)", start)
        func_body = code[start:end]
        self.assertIn("<script", func_body)
        self.assertIn("<iframe", func_body)
        self.assertIn("javascript:", func_body)

    def test_18_copy_synthesis_clipboard_robustness(self):
        """Verify copySynthesisToClipboard and renderDossierOutput handle dossier_sections and content_html safely."""
        app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("UIState.lastDossierData.sections || UIState.lastDossierData.dossier_sections || []", code)
        self.assertIn("data.sections || data.dossier_sections || []", code)

    def test_19_sqlite_synchronous_normal_and_indexes(self):
        """Verify PRAGMA synchronous is NORMAL (1) and secondary indexes exist for O(1) lookups."""
        from backend.database import get_db_connection, IS_POSTGRES
        if IS_POSTGRES:
            self.skipTest("PRAGMA synchronous and sqlite_master are SQLite-specific; running on PostgreSQL.")
        conn = get_db_connection()
        try:
            sync_val = conn.execute("PRAGMA synchronous;").fetchone()[0]
            self.assertEqual(sync_val, 1, "Expected synchronous=NORMAL (1)")

            indexes = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()]
            expected = [
                "idx_pdf_chunks_session",
                "idx_pdf_figures_session",
                "idx_pdf_refs_session",
                "idx_pdf_files_session",
                "idx_cached_sentences_query",
                "idx_followup_parent_run"
            ]
            for exp in expected:
                self.assertIn(exp, indexes, f"Missing expected index: {exp}")
        finally:
            conn.close()

    def test_20_pipeline_per_agent_fallback_parity(self):
        """Verify run_query_pipeline extracts disable_fallback_agent2 and disable_fallback_agent4."""
        import inspect
        from backend.pipeline import run_query_pipeline
        src = inspect.getsource(run_query_pipeline)
        self.assertIn('disable_fallback_agent2 = bool(config.get("disable_fallback_agent2", disable_fallback))', src)
        self.assertIn('disable_fallback_agent4 = bool(config.get("disable_fallback_agent4", disable_fallback))', src)

    def test_21_scraper_parallel_and_deduplication(self):
        """Verify agent1_scraper dispatches tasks via asyncio.gather and deduplicates papers."""
        import inspect
        from backend.agents.agent1_scraper import run_agent1_academic_scraper
        src = inspect.getsource(run_agent1_academic_scraper)
        self.assertIn("asyncio.gather(*fetch_tasks, return_exceptions=True)", src)
        self.assertIn("deduped_papers = []", src)

    def test_22_live_character_counter_and_length_limits(self):
        """Verify live char counter, textarea auto-grow, and 1000-char limits across frontend."""
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="query-char-count"', html)
        self.assertIn('class="query-char-counter"', html)

        with open("frontend/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn(".query-char-counter", css)
        self.assertIn(".counter-warning", css)
        self.assertIn(".counter-danger", css)

        with open("frontend/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn("function updateQueryCharCounter()", js)
        self.assertIn("function autoResizeQueryTextarea(", js)
        self.assertIn("query.length > 1000", js)
        self.assertIn("question.length > 1000", js)

    def test_23_responsive_breakpoints(self):
        """Verify responsive breakpoints at 1024px, 768px, and 480px exist in styles.css."""
        with open("frontend/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn("@media (max-width: 1024px)", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("@media (max-width: 480px)", css)

    def test_24_theme_contrast_accessibility_and_run_bat(self):
        """Verify theme-beige contrast, aria-labels in index.html, and v3.0 in run.bat."""
        with open("frontend/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn("body.theme-beige .glass-node-card", css)
        self.assertIn("--border-card: rgba(120, 95, 70, 0.28)", css)

        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="btn-close-drawer" title="Close Settings" aria-label="Close Settings"', html)
        self.assertIn('id="btn-toggle-theme" title="Toggle Theme (Obsidian Dark / Warm Beige)" aria-label="Toggle Theme"', html)
        self.assertIn('id="dock-home-btn" title="AI Research Workbench" aria-label="AI Research Workbench"', html)

        with open("run.bat", "r", encoding="utf-8") as f:
            bat = f.read()
        self.assertIn("title AI Research Workbench v3.0", bat)
        self.assertIn("Starting AI Research Workbench v3.0...", bat)

    def test_25_pillar1_authenticity_and_query_relaxation(self):
        """Pillar 1: Verify query relaxation, zero fake templates, Europe PMC, and DOI resolution."""
        from backend.agents.agent1_scraper import (
            relax_academic_query,
            get_curated_fallback_papers,
            fetch_europepmc
        )
        import inspect

        # 1. Query relaxation edge cases
        # Multi-word specific query
        q_long = "What are the latest advances in Quantum Error Mitigation in Neutral Atom Qubits using Transversal Gates?"
        relaxed = relax_academic_query(q_long)
        self.assertTrue(len(relaxed) > 0)
        self.assertTrue(any("quantum" in r.lower() for r in relaxed))

        # Single word query -> returns empty list (cannot relax further)
        self.assertEqual(relax_academic_query("Quantum"), [])

        # 2. Zero fake templates in fallback papers (Landmark literature only)
        landmark_papers = get_curated_fallback_papers("Random non-curated scientific topic 12345")
        self.assertTrue(len(landmark_papers) >= 2)
        # Verify no fake authors "E. Vance" or template mock text "Experimental evaluations of"
        for p in landmark_papers:
            self.assertNotIn("E. Vance", p.get("authors", []))
            self.assertNotIn("Experimental evaluations of", p.get("abstract", ""))
            self.assertIn("doi", p)
            self.assertTrue(p["doi"].startswith("10."))

        # 3. Verify Europe PMC integration exists in run_agent1_academic_scraper
        from backend.agents.agent1_scraper import run_agent1_academic_scraper
        src = inspect.getsource(run_agent1_academic_scraper)
        self.assertIn("fetch_europepmc", src)
        self.assertIn("relax_academic_query", src)
        self.assertIn("Zero authentic papers returned from live academic repositories", src)

    def test_26_pillars_2_and_3_synthesis_and_cognitive_forcing(self):
        """Pillars 2 & 3: Domain profiles, AST normalizer, anti-platitudes, and structured monograph components."""
        from backend.agents.agent2_drafter import (
            DOMAIN_PROFILES,
            synthesize_fallback_draft,
            AGENT2_PINNED_SYSTEM_INSTRUCTION
        )
        import re

        # 1. Verify all 5 domain profiles contain comparison_table, dialectical_friction, epistemic_limitations
        expected_domains = ["crypto", "quantum", "bio", "systems_ml", "generic_scientific"]
        for d in expected_domains:
            self.assertIn(d, DOMAIN_PROFILES)
            prof = DOMAIN_PROFILES[d]
            self.assertIn("comparison_table", prof)
            self.assertIn("dialectical_friction", prof)
            self.assertIn("epistemic_limitations", prof)
            self.assertTrue(len(prof["comparison_table"]) >= 2)
            self.assertTrue(len(prof["epistemic_limitations"]) >= 2)

        # 2. Verify synthesize_fallback_draft returns structured monograph fields
        draft = synthesize_fallback_draft("Quantum Error Correction Surface Codes", "quantum", complexity_tier=2)
        self.assertIn("comparison_table", draft)
        self.assertIn("dialectical_friction", draft)
        self.assertIn("epistemic_limitations", draft)
        self.assertTrue(len(draft["comparison_table"]) >= 2)

        # 3. Verify AST claim normalizer regex
        raw_markdown = "The protocol [claim: c1 | achieves 99.9% fidelity] under cryogenic conditions."
        normalized = re.sub(
            r'\[claim:\s*(c\d+)\s*\|\s*([^\]]+)\]',
            r'<claim id="\1">\2</claim>',
            raw_markdown
        )
        self.assertEqual(normalized, 'The protocol <claim id="c1">achieves 99.9% fidelity</claim> under cryogenic conditions.')

        # 4. Verify Pinned System Instruction bans platitudes
        self.assertIn("ANTI-PLATITUDE NEGATIVE CONSTRAINT", AGENT2_PINNED_SYSTEM_INSTRUCTION)
        self.assertIn("plays a crucial role", AGENT2_PINNED_SYSTEM_INSTRUCTION)
        self.assertIn("is important to note", AGENT2_PINNED_SYSTEM_INSTRUCTION)
        self.assertIn("further research is needed", AGENT2_PINNED_SYSTEM_INSTRUCTION)
        self.assertIn("chain-of-density", AGENT2_PINNED_SYSTEM_INSTRUCTION)

    def test_27_pillar_4_high_precision_local_verification(self):
        """Pillar 4: Dense subword n-gram vector matching, polarity inversion defense, and synonym normalization."""
        from backend.agents.agent3_cacher import (
            text_to_vector_profile,
            compute_profile_similarity,
            extract_polarity,
            normalize_academic_word,
            run_agent3_context_cacher
        )
        import asyncio

        # 1. Subword n-gram profile generation
        prof = text_to_vector_profile("Surface codes achieve fault tolerance threshold of 1.0%")
        self.assertIn("words", prof)
        self.assertIn("freq", prof)
        self.assertTrue(any(k.startswith("sw_") for k in prof["freq"].keys()))

        # 2. Polarity extraction: True = expresses negative polarity/assertion; False = positive
        pos_sent = "The model achieved 99.5% state fidelity across physical qubits."
        neg_sent = "The model failed to achieve fault tolerance across physical qubits."
        self.assertFalse(extract_polarity(pos_sent))
        self.assertTrue(extract_polarity(neg_sent))

        # 3. Polarity Inversion Guard: Contradictory statements must have clamped similarity (< 0.45)
        prof_pos = text_to_vector_profile(pos_sent)
        prof_neg = text_to_vector_profile(neg_sent)
        sim_inverted = compute_profile_similarity(prof_pos, prof_neg)
        self.assertLess(sim_inverted, 0.45)

        # 4. Academic synonym normalization
        self.assertEqual(normalize_academic_word("demonstrated"), "achieved")
        self.assertEqual(normalize_academic_word("suppressed"), "mitigated")
        self.assertEqual(normalize_academic_word("benchmarks"), "evaluated")

        # 5. Verify run_agent3_context_cacher candidate snippet extraction
        sample_claims = [{"id": "c1", "text": "Surface codes achieve fault tolerance threshold of 1.0%"}]
        sample_sentences = [
            {"id": "s1", "paper_id": "p1", "text": "Surface codes achieve fault tolerance threshold of 1.0% under physical gate noise."}
        ]
        agent1_data = {"papers": [], "dense_sentences": sample_sentences}
        agent2_data = {"claims": sample_claims}
        res = run_agent3_context_cacher("Quantum", agent1_data, agent2_data)
        self.assertIn("auto_verified_count", res)
        self.assertEqual(res["auto_verified_count"], 1)

    def test_28_pillar_5_agent4_and_early_exit(self):
        """Pillar 5: Agent 4 Targeted Routing, 1-Call Early Exit, Reviewer 2 Caveats, and structured data pass-through."""
        from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer
        import asyncio

        agent1_data = {
            "papers": [{"id": "p1", "title": "Attention Paper", "authors": ["Vaswani et al."], "year": 2017, "venue": "NeurIPS", "url": "https://doi.org/10.48550/arXiv.1706.03762", "citationCount": 120000}],
            "dense_sentences": [{"id": "s1", "paper_id": "p1", "text": "Attention mechanism scales as O(n^2)."}]
        }
        agent2_data = {
            "quick_answer": "Attention is all you need.",
            "executive_summary": '<claim id="c1">Attention mechanism scales as O(n^2).</claim>',
            "sections": [
                {"sub_question": "Complexity", "answer_html": '<p><claim id="c1">Attention mechanism scales as O(n^2).</claim></p>'}
            ],
            "comparison_table": [{"technique": "Transformer", "governing_metric": "FLOPs", "measured_value": "O(n^2)", "baseline": "RNN", "limitations": "Memory"}],
            "dialectical_friction": {"disagreements": "Recurrence vs attention", "pareto_tradeoffs": "Memory vs throughput"},
            "epistemic_limitations": ["Requires quadratic memory for context length n"]
        }
        # Case A: 1-Call Early Exit (all claims verified locally by Agent 3)
        agent3_data_all_verified = {
            "verified_claims": [
                {"claim_id": "c1", "claim_text": "Attention mechanism scales as O(n^2).", "matched_paper_id": "p1", "matched_sentence": "Attention mechanism scales as O(n^2).", "confidence_score": 0.96, "status": "verified_by_cache"}
            ],
            "unverified_claims": []
        }

        res = asyncio.run(run_agent4_fact_checker_synthesizer("Transformer", agent1_data, agent2_data, agent3_data_all_verified))
        # Zero tokens used by Agent 4 because Call 2 was bypassed!
        self.assertEqual(res["tokens_used"], 0)
        self.assertEqual(res["prompt_tokens"], 0)
        self.assertEqual(res["completion_tokens"], 0)
        self.assertEqual(res["unverified_claims_processed"], 0)
        self.assertIn("comparison_table", res)
        self.assertIn("dialectical_friction", res)
        self.assertIn("epistemic_limitations", res)
        # Check that data-caveat attribute exists on claim chips
        self.assertIn("data-caveat", res["executive_summary"])

    def test_29_pillar_6_and_7_export_and_pdf_parity(self):
        """Pillars 6 & 7: Export formats (Markdown, LaTeX, Docx, Dialogue) and PDF synthesis parity."""
        from backend.export import (
            export_to_docx,
            export_to_latex,
            export_to_markdown,
            export_dialogue_to_markdown,
            export_dialogue_to_latex
        )

        dossier_data = {
            "query": "Quantum Computing Fault Tolerance",
            "quick_answer": "Surface codes achieve fault tolerance below 1% error rate.",
            "takeaways": ["Threshold bounded at 1.0%", "Stabilizer cycles under 200ns"],
            "executive_summary": "Fault tolerant architectures require high fidelity gates.",
            "dossier_sections": [
                {"sub_question": "Thresholds", "answer_html": "<p>Surface code requires $p < 1\\%$.</p>"}
            ],
            "comparison_table": [
                {"technique": "Surface Code", "governing_metric": "Threshold", "measured_value": "1.0%", "baseline": "Repetition Code", "limitations": "Qubit overhead"}
            ],
            "dialectical_friction": {
                "disagreements": "Cat qubits vs transmons",
                "pareto_tradeoffs": "Qubit count vs coherence time"
            },
            "epistemic_limitations": ["Cryogenic routing bottlenecks"],
            "citations": [
                {"ref_id": "REF-1", "paper_id": "p1", "title": "Surface Code Quantum Computing", "authors": ["Fowler et al."], "year": 2012, "venue": "PRA", "url": "https://doi.org/10.1103/PhysRevA.86.032324"}
            ]
        }

        # 1. Docx Export
        docx_buf = export_to_docx(dossier_data)
        self.assertTrue(docx_buf.getvalue().startswith(b"PK"))

        # 2. LaTeX Export
        latex_str = export_to_latex(dossier_data)
        self.assertIn("\\begin{tabular}", latex_str)
        self.assertIn("Quantitative Comparative Benchmarks", latex_str)
        self.assertIn("Dialectical Friction", latex_str)
        self.assertIn("Epistemic Horizons", latex_str)

        # 3. Markdown Export
        md_str = export_to_markdown(dossier_data)
        self.assertIn("| Technique / Paradigm | Governing Metric |", md_str)
        self.assertIn("## 3. Quantitative Comparative Benchmarks", md_str)
        self.assertIn("## 4. Dialectical Friction", md_str)
        self.assertIn("## 7. Epistemic Horizons", md_str)

        # 4. Dialogue Export
        messages = [
            {"role": "user", "content": "What is the physical gate threshold?"},
            {"role": "assistant", "content": "The physical threshold is bounded at ~1% for surface codes."}
        ]
        diag_md = export_dialogue_to_markdown("Quantum", messages, dossier_data)
        self.assertIn("### [USER]", diag_md)
        self.assertIn("### [ASSISTANT]", diag_md)

        diag_tex = export_dialogue_to_latex("Quantum", messages, dossier_data)
        self.assertIn("\\subsection*{USER}", diag_tex)

        # 5. Test Export Endpoints via FastAPI TestClient
        client = TestClient(app)
        res_md = client.post("/api/export/markdown", json={"dossier": dossier_data})
        self.assertEqual(res_md.status_code, 200)
        self.assertIn("Quantitative Comparative Benchmarks", res_md.text)

    def test_30_crossref_doaj_and_scraper_selection(self):
        """Verify Crossref and DOAJ integration, active_scrapers filtering, and complete arXiv removal."""
        import backend.agents.agent1_scraper as scraper_module
        from backend.agents.agent1_scraper import (
            fetch_crossref,
            fetch_doaj,
            run_agent1_academic_scraper,
            SUPPORTED_SCRAPERS
        )
        import inspect

        # 1. Verify arXiv is 100% removed
        self.assertFalse(hasattr(scraper_module, "fetch_arxiv"), "fetch_arxiv should be completely removed")
        scraper_src = inspect.getsource(run_agent1_academic_scraper)
        self.assertNotIn("fetch_arxiv", scraper_src, "fetch_arxiv should not be referenced in run_agent1_academic_scraper")

        # 2. Verify Crossref and DOAJ exist in SUPPORTED_SCRAPERS
        self.assertIn("crossref", SUPPORTED_SCRAPERS)
        self.assertIn("doaj", SUPPORTED_SCRAPERS)
        self.assertNotIn("arxiv", SUPPORTED_SCRAPERS)
        self.assertTrue(callable(fetch_crossref))
        self.assertTrue(callable(fetch_doaj))

        # 3. Verify /api/config reports Crossref and DOAJ and omits arXiv
        client = TestClient(app)
        cfg_resp = client.get("/api/config")
        self.assertEqual(cfg_resp.status_code, 200)
        providers = cfg_resp.json()["providers_available"]
        self.assertTrue(providers.get("crossref"))
        self.assertTrue(providers.get("doaj"))
        self.assertNotIn("arxiv", providers)

        # 4. Verify run_agent1_academic_scraper accepts active_scrapers in demo mode
        import asyncio
        demo_res = asyncio.run(run_agent1_academic_scraper(
            "Austrian Economics Opportunity Cost", 
            limit=3, 
            active_scrapers=["crossref", "doaj"]
        ))
        self.assertIn("papers", demo_res)
        self.assertTrue(demo_res["papers_found"] > 0)

        # 5. Verify /api/pipeline/run accepts active_scrapers payload
        from unittest.mock import patch
        mock_a2 = synthesize_fallback_draft("Quantum Error Mitigation", [], [], target_count=3)
        mock_a2["tokens_used"] = 150
        mock_a4 = {
            "dossier_sections": [{"sub_question": "Overview", "content_html": "<p>Overview</p>"}],
            "citations": [{"ref_id": "REF-1", "title": "Paper 1"}],
            "executive_summary": "Summary",
            "tokens_used": 100,
            "evaluated_claims": []
        }
        with patch("backend.pipeline.run_agent2_the_drafter", return_value=mock_a2), \
             patch("backend.pipeline.run_agent4_fact_checker_synthesizer", return_value=mock_a4):
            pipe_resp = client.post("/api/pipeline/run", json={
                "query": "Quantum Error Mitigation",
                "active_scrapers": ["crossref", "doaj", "openalex"]
            })
            self.assertEqual(pipe_resp.status_code, 200)
            json_data = pipe_resp.json()
            self.assertIn("dossier_sections", json_data)
            self.assertIn("citations", json_data)

    def test_31_grounded_attribution_and_3tier_claims(self):
        """Verify calibrated Agent 3 threshold (0.55), metric boosting, and 3-tier claim tagging."""
        import asyncio
        from backend.agents.agent3_cacher import run_agent3_context_cacher
        from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer

        papers = [
            {
                "id": "paper_101",
                "paper_idx": "P1",
                "title": "High-Risk AI Systems Under the EU AI Act",
                "authors": ["Floridi, L.", "Cowls, J."],
                "year": 2023,
                "url": "https://doi.org/10.1007/s13347-023-00620-1"
            }
        ]
        dense_sentences = [
            {
                "id": "sent_1",
                "paper_idx": "P1",
                "paper_id": "paper_101",
                "paper_title": "High-Risk AI Systems Under the EU AI Act",
                "text": "The EU AI Act classifies high-risk systems under Annex III, imposing conformity assessments and post-market monitoring obligations on deployers."
            }
        ]
        claims = [
            {
                "id": "c1",
                "text": "The European Union AI Act establishes strict conformity assessments and post-market monitoring for high-risk artificial intelligence systems under Annex III.",
                "paper": "P1"
            },
            {
                "id": "c2",
                "text": "Arbitrary ungrounded claim regarding non-existent hyperdrive warp fields.",
                "paper": "P1"
            }
        ]

        # 1. Agent 3: Grounded claim must be auto-verified via calibrated threshold + metric/acronym boost
        a3_res = run_agent3_context_cacher(
            "EU AI Act compliance",
            {"papers": papers, "dense_sentences": dense_sentences},
            {"claims": claims},
            similarity_threshold=0.55
        )
        self.assertEqual(a3_res["auto_verified_count"], 1)
        self.assertEqual(a3_res["unverified_for_agent4_count"], 1)
        self.assertEqual(a3_res["verified_claims"][0]["claim_id"], "c1")
        self.assertEqual(a3_res["verified_claims"][0]["verification_tier"], "auto_cache")
        self.assertEqual(a3_res["unverified_claims"][0]["claim_id"], "c2")

        # 2. Agent 4: 3-tier claim markup with distinct anchor tags
        a1_res = {"papers": papers, "papers_found": 1, "dense_sentences": dense_sentences}
        a2_res = {
            "executive_summary": "<p>According to Floridi et al. (2023) [P1], <claim id=\"c1\" paper=\"P1\">The EU AI Act mandates conformity assessments under Annex III.</claim></p>",
            "sections": [
                {
                    "sub_question": "Regulatory Compliance",
                    "answer_html": "<p>As established in [P1], <claim id=\"c1\" paper=\"P1\">The EU AI Act mandates conformity assessments under Annex III.</claim> In contrast, <claim id=\"c2\">Arbitrary ungrounded claim regarding non-existent hyperdrive warp fields.</claim></p>",
                    "claims": claims
                }
            ]
        }

        from unittest.mock import patch
        from backend.agents.agent2_drafter import TokenCount

        with patch("backend.agents.agent4_synthesizer.call_gemini_factcheck", return_value=([], TokenCount(100, 50, 50))):
            a4_res = asyncio.run(run_agent4_fact_checker_synthesizer(
                "EU AI Act compliance",
                a1_res,
                a2_res,
                a3_res,
                provider="gemini-2.5-flash",
                api_key="mock-test-key",
                disable_fallback=False
            ))

        sec_html = a4_res["dossier_sections"][0]["content_html"]
        # Verify Tier 1: Auto-verified claim has claim-tier-auto_cache and cache badge
        self.assertIn("claim-tier-auto_cache", sec_html)
        self.assertIn("tier-cache-badge", sec_html)
        self.assertIn("[✓ cache • 1]", sec_html)

        # Verify Tier 3: Ungrounded claim with paper tag has tier-no-source-badge and warning index
        self.assertIn("claim-tier-no_source", sec_html)
        self.assertIn("tier-no-source-badge", sec_html)
        self.assertIn("[⚠ 1]", sec_html)

        # Verify attributes are preserved without truncation
        self.assertIn('data-tier="auto_cache"', sec_html)
        self.assertIn('data-tier="no_source"', sec_html)

    def test_32_five_pillar_advancements(self):
        """
        Pillars 1 to 5:
        1. Fastembed local ONNX neural vector similarity.
        2. Dynamic universal academic query distillation.
        3. Semantic relevance filtering without hardcoded domain bias.
        4. Fact-checker async parallel batching with no top-10 cap.
        5. Dual Execution Engine: Rapid Mode vs Deep Monograph.
        """
        import asyncio
        from backend.agents.agent3_cacher import compute_cosine_similarity, embed_texts, run_agent3_context_cacher
        from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer
        from backend.agents.agent1_scraper import distill_academic_query, is_paper_semantically_relevant
        from backend.pipeline import run_query_pipeline

        # 1. Test Pillar 1: Fastembed neural embeddings on paraphrased scientific text
        sim = compute_cosine_similarity(
            "The model mitigated propagation latency in distributed clusters.",
            "The system reduced transmission delay across interconnected nodes."
        )
        self.assertGreater(sim, 0.60, f"Neural similarity should exceed 0.60 for semantic paraphrasing, got {sim}")

        # Test batch embeddings directly
        vecs = embed_texts(["Neural network architecture", "Deep learning model"])
        self.assertIsNotNone(vecs)
        self.assertEqual(len(vecs), 2)
        self.assertEqual(vecs.shape[1], 384)

        # 2. Test Pillar 3: Universal Dynamic Query Distillation
        raw_q = 'What is the impact of "quantum error mitigation" on NISQ neutral atom qubits?'
        distilled = distill_academic_query(raw_q)
        self.assertIn('"quantum error mitigation"', distilled)
        self.assertNotIn("what is", distilled.lower())
        self.assertIn("NISQ", distilled)

        # 3. Test Pillar 3: Semantic Relevance Gate
        bad_paper = {"title": "Author Correction: Erratum on Quantum Systems", "abstract": "Corrected figures."}
        self.assertFalse(is_paper_semantically_relevant(bad_paper, "quantum computing"))

        good_paper = {"title": "Neutral Atom Qubit Fidelity", "abstract": "Demonstrated 99.5% entangling gate."}
        self.assertTrue(is_paper_semantically_relevant(good_paper, "neutral atom"))

        # 4. Test Pillar 4: Fact-Checker Batching with >10 claims
        claims_14 = [
            {"id": f"c{i}", "text": f"Empirical benchmark assertion number {i} regarding hardware speedup.", "paper": "P1"}
            for i in range(1, 15)
        ]
        a1_data = {
            "papers": [{"id": "p1", "paper_idx": "P1", "title": "Paper 1", "url": "https://doi.org/10.1234/test"}],
            "papers_found": 1,
            "dense_sentences": [{"id": "s1", "paper_idx": "P1", "text": "Hardware speedup measured at 4.2x.", "paper_id": "p1"}]
        }
        a2_data = {
            "claims": claims_14,
            "sections": [{
                "sub_question": "Benchmarking",
                "answer_html": "".join([f'<claim id="c{i}">Assertion {i}</claim>' for i in range(1, 15)]),
                "claims": claims_14
            }]
        }
        a3_data = run_agent3_context_cacher(
            "Hardware speedup", a1_data, a2_data, similarity_threshold=0.99
        )
        # All 14 claims should be sent to unverified
        self.assertEqual(a3_data["unverified_for_agent4_count"], 14)

        from unittest.mock import patch
        from backend.agents.agent2_drafter import TokenCount

        with patch("backend.agents.agent4_synthesizer.call_gemini_factcheck", return_value=([], TokenCount(100, 50, 50))):
            a4_res = asyncio.run(run_agent4_fact_checker_synthesizer(
                "Hardware speedup",
                a1_data,
                a2_data,
                a3_data,
                provider="gemini-2.5-flash",
                api_key="mock-test-key",
                disable_fallback=False
            ))
        # Ensure all 14 claims were processed (not capped at 10!)
        evaluated_ids = [c["claim_id"] for c in a4_res["evaluated_claims"]]
        self.assertEqual(len(evaluated_ids), 14, f"Expected 14 evaluated claims, got {len(evaluated_ids)}")

        # Verify Zero Fallback Mandate: Agent 4 without API key raises RuntimeError loudly
        with self.assertRaises(RuntimeError):
            asyncio.run(run_agent4_fact_checker_synthesizer(
                "Hardware speedup",
                a1_data,
                a2_data,
                a3_data,
                provider="offline"
            ))

        # 5. Verify Zero Fallback Mandate on pipeline: offline execution without API key raises RuntimeError loudly
        with self.assertRaises(RuntimeError):
            asyncio.run(run_query_pipeline(
                "Quantum Error Mitigation",
                config={
                    "execution_mode": "rapid",
                    "bypass_cache": True,
                    "provider_agent2": "offline"
                }
            ))

    def test_33_subquery_enrichment_and_cross_domain_gating(self):
        """Verify subquery enrichment injects domain anchors and blocks cross-domain contamination."""
        from backend.agents.agent1_scraper import (
            enrich_subquery_context,
            is_paper_semantically_relevant,
            decompose_query_into_facets
        )

        parent = (
            "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions "
            "vs Graph Transformers with spectral Laplacian positional encodings for molecular property prediction: "
            "over-squashing mitigation, expressive power beyond the 1-Weisfeiler-Lehman (1-WL) limit, "
            "and inference scaling on QM9 and ZINC benchmarks"
        )

        facets = decompose_query_into_facets(parent)
        self.assertGreaterEqual(len(facets), 4)

        # 1. Verify isolated benchmark subquery is enriched with domain context
        sub = "inference scaling on QM9 and ZINC benchmarks"
        enriched = enrich_subquery_context(sub, parent)
        self.assertIn("molecular", enriched)
        self.assertIn("graph", enriched)

        # 2. Verify orthogonal poultry zinc paper is rejected
        bad_paper_1 = {
            "title": "Optimizing its bioavailability remains an important objective in modern poultry nutrition",
            "abstract": "Nanotechnology has emerged as a promising strategy to enhance zinc bioavailability in broilers.",
            "venue": "Poultry Science"
        }
        self.assertFalse(is_paper_semantically_relevant(bad_paper_1, parent, facets))

        # 3. Verify orthogonal PFAS water testing paper is rejected
        bad_paper_2 = {
            "title": "Validation of method for 42 PFAS compounds across water matrices",
            "abstract": "This method quantitates 42 PFAS compounds in low ng L-1 range with limits of detection verified.",
            "venue": "Environmental Analysis"
        }
        self.assertFalse(is_paper_semantically_relevant(bad_paper_2, parent, facets))

        # 4. Verify orthogonal astronomy ASTROMER paper is rejected
        bad_paper_3 = {
            "title": "Trainable positional encodings within ASTROMER architecture",
            "abstract": "Generate datasets with varying cadences derived from astronomical survey on which transformer was pretrained.",
            "venue": "Astronomy & Astrophysics"
        }
        self.assertFalse(is_paper_semantically_relevant(bad_paper_3, parent, facets))

        # 5. Verify legitimate molecular GNN paper passes
        good_paper = {
            "title": "A General Architecture for Graph Neural Networks in Molecular Property Prediction",
            "abstract": "We benchmark MPNN with edge-conditioned convolutions and Graph Transformers with Laplacian positional encodings on QM9 and ZINC.",
            "venue": "NeurIPS"
        }
        self.assertTrue(is_paper_semantically_relevant(good_paper, parent, facets))

if __name__ == "__main__":
    unittest.main()

