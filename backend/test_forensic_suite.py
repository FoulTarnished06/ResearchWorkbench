import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.agent1_scraper import (
    sanitize_and_validate_paper_metadata,
    is_paper_semantically_relevant
)
from backend.post_processor import clean_monograph_text
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

if __name__ == "__main__":
    unittest.main()
