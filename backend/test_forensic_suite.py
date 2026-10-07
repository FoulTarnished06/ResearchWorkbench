import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.agent1_scraper import (
    sanitize_and_validate_paper_metadata,
    is_paper_semantically_relevant
)
from backend.post_processor import (
    clean_monograph_text,
    check_dangling_references,
    enforce_section2_empirical_purity
)
from backend.export import sanitize_author_display, filter_active_citations

class TestForensicSuite(unittest.TestCase):
    def test_doi_regex_filtering(self):
        # Supplemental appendices and referee reports should be dropped at ingestion boundary
        supp_paper = {
            "title": "Supplemental Information for Protein Crystallography",
            "abstract": "Detailed tables and supplementary figures for protein structure analysis.",
            "doi": "10.1021/acsomega.5c06923.s001",
            "venue": "ACS Omega"
        }
        self.assertIsNone(sanitize_and_validate_paper_metadata(supp_paper))

        review_paper = {
            "title": "Open Peer Review Report for Manuscript 70117",
            "abstract": "Referee commentary and responses for manuscript evaluation.",
            "doi": "10.1002/prot.70117/v1/review2",
            "venue": "Proteins"
        }
        self.assertIsNone(sanitize_and_validate_paper_metadata(review_paper))

    def test_author_metadata_sanitization(self):
        # Empty/None author records should cleanly fall back without emitting 'Authors (None)'
        self.assertEqual(
            sanitize_author_display(["Crossref Academic Registry Authors (None)"], "Crossref"),
            "Crossref Academic Registry"
        )
        self.assertEqual(
            sanitize_author_display(None, "Nature Biotechnology"),
            "Nature Biotechnology Authors"
        )

    def test_two_stage_domain_gating(self):
        # Product liability / supply chain should be blocked for rollup queries
        llm_liability_paper = {
            "title": "Binding LLM Providers to Product Liability and Proof-of-Usage",
            "abstract": "Analyzing consumer protection and civil liability when AI models fail.",
            "venue": "Stanford Law Review"
        }
        self.assertFalse(is_paper_semantically_relevant(
            llm_liability_paper,
            "Recursive zero-knowledge rollup proof verification overhead vs optimistic fraud-proof dispute windows"
        ))

        # True crypto rollup paper should pass
        rollup_paper = {
            "title": "Succinct Non-Interactive Arguments for Recursive Zero-Knowledge Rollups",
            "abstract": "Evaluating proof verification overhead and state transition batching in Layer-2 rollups.",
            "venue": "IEEE S&P"
        }
        self.assertTrue(is_paper_semantically_relevant(
            rollup_paper,
            "Recursive zero-knowledge rollup proof verification overhead vs optimistic fraud-proof dispute windows"
        ))

    def test_internal_tag_scrubber(self):
        dirty_text = "The proof verification overhead was 2.5 ms [✓ cache • 7] and dispute resolution window was 7 days [⚠ 5]."
        clean_text = clean_monograph_text(dirty_text)
        self.assertNotIn("[✓ cache • 7]", clean_text)
        self.assertNotIn("[⚠ 5]", clean_text)
        self.assertIn("2.5 ms and dispute resolution window was 7 days.", clean_text)

    def test_consecutive_repetition_sieve(self):
        repetitive_text = (
            "Proof generation requires 1 second and verification takes 2 milliseconds.\n"
            "Proof generation requires 1 second and verification takes 2 milliseconds.\n"
            "Proof generation requires 1 second and verification takes 2 milliseconds."
        )
        cleaned = clean_monograph_text(repetitive_text)
        self.assertEqual(cleaned.count("Proof generation requires 1 second"), 1)

    def test_active_citation_filter_purges_ghost_bibliography(self):
        dossier = {
            "output_text": "We evaluate recursive proofs following [P1] and compare with [P2].",
            "citations": [
                {"ref_id": "REF-1", "paper_idx": "P1", "title": "Paper One", "authors": ["Alice"]},
                {"ref_id": "REF-2", "paper_idx": "P2", "title": "Paper Two", "authors": ["Bob"]},
                {"ref_id": "REF-3", "paper_idx": "P3", "title": "Uncited Ghost Paper", "authors": ["Charlie"]},
                {"ref_id": "REF-4", "paper_idx": "P4", "title": "Another Ghost Paper", "authors": ["Diana"]}
            ]
        }
        active = filter_active_citations(dossier)
        self.assertEqual(len(active), 2)
        self.assertEqual([c["paper_idx"] for c in active], ["P1", "P2"])

    def test_dangling_reference_check_in_code(self):
        dossier = {
            "executive_summary": "Recursive rollups achieve 2.5 ms verification [P1], while older systems require 50 ms [P9].",
            "sections": [
                {
                    "sub_question": "Theoretical Foundations",
                    "content_html": "<p>Protocol semantics follow [P1] and [REF-1]. However, external claims cite [P7] without indexing.</p>",
                    "claims": []
                },
                {
                    "sub_question": "Empirical Benchmarks",
                    "content_html": "<p>Empirical runs confirm throughput from [P2].</p>",
                    "claims": []
                }
            ],
            "citations": [
                {"ref_id": "REF-1", "paper_idx": "P1", "title": "Succinct Verifier", "authors": ["Alice"]},
                {"ref_id": "REF-2", "paper_idx": "P2", "title": "Throughput Benchmarks", "authors": ["Bob"]},
                {"ref_id": "REF-3", "paper_idx": "P3", "title": "Ghost Uncited Paper", "authors": ["Charlie"], "verified_claims_count": 0}
            ]
        }
        processed = check_dangling_references(dossier)
        # 1. P9 and P7 should be converted to citation-orphan spans
        self.assertNotIn("[P9]", processed["executive_summary"])
        self.assertIn("citation-orphan", processed["executive_summary"])
        self.assertIn("[Unverified External Citation]", processed["executive_summary"])
        self.assertNotIn("[P7]", processed["sections"][0]["content_html"])
        self.assertIn("[Unverified External Citation]", processed["sections"][0]["content_html"])
        # Legitimate [P1] should remain intact
        self.assertIn("[P1]", processed["executive_summary"])

        # 2. Ghost bibliography entry P3 should be purged
        active_ids = [c["paper_idx"] for c in processed["citations"]]
        self.assertIn("P1", active_ids)
        self.assertIn("P2", active_ids)
        self.assertNotIn("P3", active_ids)

        # 3. Audit log verification
        audit = processed.get("dangling_reference_check", {})
        self.assertEqual(audit.get("status"), "corrected")
        self.assertIn("P9", audit.get("dangling_pointers_sanitized", []))
        self.assertIn("P7", audit.get("dangling_pointers_sanitized", []))
        self.assertIn("P3", audit.get("ghost_references_purged", []))

    def test_section2_empirical_purity_enforcement(self):
        dossier = {
            "sections": [
                {
                    "sub_question": "Foundations",
                    "content_html": "<p>Theory of zero-knowledge proofs.</p>",
                    "claims": [{"id": "c1", "text": "Theory", "paper": "P1"}]
                },
                {
                    "sub_question": "Empirical Validation & Benchmark Delta",
                    "content_html": (
                        '<p>Empirical verification takes 2.5 ms <span class="claim-wrapper claim-tier-verified"><span class="claim-text">2.5 ms verification</span></span>. '
                        'Furthermore, speculative dispute window is estimated <span class="claim-wrapper claim-tier-no_source"><span class="claim-text">dispute window 7 days without measurement</span></span>.</p>'
                    ),
                    "claims": [
                        {"id": "c2", "text": "2.5 ms verification", "paper": "P1"},
                        {"id": "c3", "text": "dispute window 7 days without measurement"}
                    ]
                }
            ]
        }
        processed = enforce_section2_empirical_purity(dossier)
        sec2_html = processed["sections"][1]["content_html"]
        self.assertNotIn("claim-tier-no_source", sec2_html)
        self.assertIn("empirical-gap-notice", sec2_html)
        self.assertIn("[No empirical measurement reported in retrieved evidence: dispute window 7 days without measurement]", sec2_html)
        # Claims array in Section 2 should filter out the claim without paper
        sec2_claims = processed["sections"][1]["claims"]
        self.assertEqual(len(sec2_claims), 1)
        self.assertEqual(sec2_claims[0]["id"], "c2")

    def test_html_attribute_leakage_sanitization(self):
        """Defect A: Ensure strip_html_tags completely scrubs complex data attributes and prevents raw leakage."""
        from backend.export import strip_html_tags
        raw_html = (
            '<p>We introduce a message passing framework. '
            '<span class="claim-wrapper" data-claim="To integrate electronic effects with steric effects, we propose a method." '
            'data-rationale="Electronic &gt; steric effects" data-paper-url="https://doi.org/10.1002/anie.20240123" '
            'data-ref-id="REF-3">To integrate electronic effects with steric effects, we propose a quantitative method to measure the steric hindrance effect.</span> '
            'This demonstrates substantial progress.</p>'
        )
        cleaned = strip_html_tags(raw_html)
        self.assertNotIn("data-paper-url", cleaned)
        self.assertNotIn("data-ref-id", cleaned)
        self.assertNotIn("data-rationale", cleaned)
        self.assertNotIn("https://doi.org", cleaned)
        self.assertIn("To integrate electronic effects with steric effects", cleaned)
        self.assertIn("Electronic > steric effects" if "Electronic >" in cleaned else "We introduce", cleaned)

    def test_active_citation_filter_retains_badge_and_attribute_references(self):
        """Defect B: Ensure filter_active_citations retains citations cited via badges [✓ peer-rev • 2] or attributes."""
        from backend.export import filter_active_citations
        dossier = {
            "output_text": "We evaluate spatial convolutions [✓ peer-rev • 2] and Graph Transformers [✓ peer-rev • 3].",
            "evaluated_claims": [
                {"claim_text": "Claim 1", "ref_id": "REF-2", "paper_idx": "P2"}
            ],
            "citations": [
                {"ref_id": "REF-1", "paper_idx": "P1", "title": "Unreferenced Ghost Paper"},
                {"ref_id": "REF-2", "paper_idx": "P2", "title": "Message Passing Neural Networks"},
                {"ref_id": "REF-3", "paper_idx": "P3", "title": "Spectral Graph Transformers"}
            ]
        }
        active = filter_active_citations(dossier)
        active_ids = [c["ref_id"] for c in active]
        self.assertIn("REF-2", active_ids)
        self.assertIn("REF-3", active_ids)
        self.assertNotIn("REF-1", active_ids)

    def test_comparison_table_and_friction_deterministic_fallback(self):
        """Defect C: Ensure benchmark tables and dialectical friction are always present in exports."""
        from backend.export import ensure_comparison_table, ensure_dialectical_friction, export_to_markdown
        empty_dossier = {"query": "Graph Transformers vs MPNNs", "citations": []}
        cols, rows = ensure_comparison_table(empty_dossier)
        self.assertEqual(len(cols), 5)
        self.assertGreaterEqual(len(rows), 2)

        friction = ensure_dialectical_friction(empty_dossier)
        self.assertGreaterEqual(len(friction), 2)

        md = export_to_markdown(empty_dossier)
        self.assertIn("Quantitative Comparative Benchmarks", md)
        self.assertIn("Dialectical Friction & Methodological Disagreements", md)

    def test_semantic_takeaway_deduplication(self):
        """Defect D: Ensure _is_duplicate_takeaway flags near-duplicate sentences with high token overlap."""
        from backend.post_processor import _is_duplicate_takeaway, extract_academic_takeaways
        cand1 = "Nandi et al. introduce a multi-fidelity dataset for QM9 molecular property prediction with edge convolutions."
        cand2 = "MultiXC-QM9 introduces a multi-fidelity dataset for QM9 molecular property prediction with edge convolutions."
        is_dup = _is_duplicate_takeaway(cand2, [cand1])
        self.assertTrue(is_dup)

        dossier = {
            "evaluated_claims": [
                {"claim_text": cand1},
                {"claim_text": cand2},
                {"claim_text": "Graph Transformers with Laplacian positional encodings break the 1-WL isomorphism limit."}
            ]
        }
        takeaways = extract_academic_takeaways(dossier)
        self.assertEqual(len(takeaways), 3)
        self.assertIn(cand1, takeaways)
        self.assertNotIn(cand2, takeaways)

if __name__ == "__main__":
    unittest.main()

