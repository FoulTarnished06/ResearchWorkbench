"""
Unit and Integration Tests for Upstream Data Ingestion Hygiene, Provenance Classification,
and Provenance-Aware Verification (Tiers: auto_cache vs auto_cache_preprint vs llm_rag).
"""

import unittest
from backend.agents.agent1_scraper import (
    classify_paper_provenance,
    sanitize_and_validate_paper_metadata,
)
from backend.agents.agent3_cacher import run_agent3_context_cacher
from backend.agents.agent4_synthesizer import run_agent4_fact_checker_synthesizer

class TestProvenanceAndHygiene(unittest.TestCase):
    def test_classify_provenance_peer_reviewed(self):
        """Verify peer-reviewed venues and sources are classified as peer_reviewed."""
        p_nature = {"venue": "Nature Communications", "doi": "10.1038/s41467-023-12345", "source_type": "Peer-Reviewed Paper"}
        tier, label = classify_paper_provenance(p_nature)
        self.assertEqual(tier, "peer_reviewed")
        self.assertEqual(label, "Peer-Reviewed Literature")

        p_neurips = {"venue": "Advances in Neural Information Processing Systems (NeurIPS)", "doi": "10.5555/123456"}
        tier, label = classify_paper_provenance(p_neurips)
        self.assertEqual(tier, "peer_reviewed")

        p_pubmed = {"source": "PubMed", "venue": "Biomedical Reports", "doi": "10.1016/j.cell.2023.01.001"}
        tier, label = classify_paper_provenance(p_pubmed)
        self.assertEqual(tier, "peer_reviewed")

    def test_classify_provenance_preprint(self):
        """Verify arXiv, bioRxiv, and medRxiv are accurately classified as preprint."""
        p_arxiv = {"venue": "arXiv preprint arXiv:2401.12345", "url": "https://arxiv.org/abs/2401.12345"}
        tier, label = classify_paper_provenance(p_arxiv)
        self.assertEqual(tier, "preprint")
        self.assertEqual(label, "Unrefereed Preprint")

        p_biorxiv = {"doi": "10.1101/2023.05.12.540456", "venue": "bioRxiv"}
        tier, label = classify_paper_provenance(p_biorxiv)
        self.assertEqual(tier, "preprint")

        p_rs = {"doi": "10.21203/rs.3.rs-12345/v1", "venue": "Research Square"}
        tier, label = classify_paper_provenance(p_rs)
        self.assertEqual(tier, "preprint")

    def test_classify_provenance_web(self):
        """Verify Wikipedia and SerpAPI are classified as reference_web."""
        p_wiki = {"source": "Wikipedia", "venue": "Wikipedia (.org)"}
        tier, label = classify_paper_provenance(p_wiki)
        self.assertEqual(tier, "reference_web")
        self.assertEqual(label, "Web Reference")

    def test_sanitize_and_validate_rejects_empty_or_short_abstracts(self):
        """Upstream gatekeeper must reject abstracts with fewer than 20 words."""
        p_empty = {"title": "Valid Long Enough Title", "abstract": "Too short abstract."}
        self.assertIsNone(sanitize_and_validate_paper_metadata(p_empty))

    def test_sanitize_and_validate_rejects_publisher_boilerplate(self):
        """Upstream gatekeeper must reject publisher paywalls/sign-in boilerplate."""
        p_paywall = {
            "title": "Quantum Entanglement Analysis",
            "abstract": "Sign in to view full text. Access through your institution or subscribe to access this article. All rights reserved."
        }
        self.assertIsNone(sanitize_and_validate_paper_metadata(p_paywall))

    def test_sanitize_and_validate_rejects_errata_and_retractions(self):
        """Upstream gatekeeper must reject corrections and errata."""
        p_erratum = {
            "title": "Author Correction: Quantum Error Correction",
            "abstract": "A correction to this paper has been published and can be accessed via the link provided in the article."
        }
        self.assertIsNone(sanitize_and_validate_paper_metadata(p_erratum))

    def test_sanitize_and_validate_recovers_year_and_sanitizes_authors(self):
        """Verify year recovery from DOI and author normalization."""
        p_valid = {
            "title": "Scalable Neutral Atom Quantum Processors with High Fidelity",
            "abstract": "We present a 256-qubit neutral atom platform utilizing optical tweezers with two-qubit gate fidelities exceeding 99.5 percent. Physical error syndrome measurements show suppression below fault-tolerant thresholds.",
            "doi": "10.1038/s41586-2023-06927-3",
            "authors": ["M. Lukin", "None", "unknown", "H. Levine"],
            "venue": "Nature"
        }
        sanitized = sanitize_and_validate_paper_metadata(p_valid)
        self.assertIsNotNone(sanitized)
        self.assertEqual(sanitized["year"], 2023)
        self.assertEqual(sanitized["authors"], ["M. Lukin", "H. Levine"])
        self.assertEqual(sanitized["provenance_tier"], "peer_reviewed")

    def test_agent3_cacher_differentiates_peer_reviewed_vs_preprint(self):
        """Agent 3 must badge preprints as Preprint-Corroborated and peer-reviewed as Auto-Verified."""
        papers = [
            {
                "id": "p_peer",
                "title": "Fault-Tolerant Neutral Atom Arrays",
                "authors": ["M. Lukin"],
                "year": 2024,
                "venue": "Nature",
                "provenance_tier": "peer_reviewed",
                "provenance_label": "Peer-Reviewed Literature"
            },
            {
                "id": "p_prep",
                "title": "Mamba State-Space Models for Vision",
                "authors": ["A. Gu"],
                "year": 2024,
                "venue": "arXiv preprint",
                "provenance_tier": "preprint",
                "provenance_label": "Unrefereed Preprint"
            }
        ]
        dense_sentences = [
            {
                "id": "s1",
                "paper_id": "p_peer",
                "paper_title": "Fault-Tolerant Neutral Atom Arrays",
                "text": "Two-qubit gate fidelities exceed 99.5% in dual-species neutral atom optical tweezer arrays."
            },
            {
                "id": "s2",
                "paper_id": "p_prep",
                "paper_title": "Mamba State-Space Models for Vision",
                "text": "Selective state space models scale linearly with context length while preserving memory bandwidth."
            }
        ]
        claims = [
            {
                "id": "c1",
                "text": "Two-qubit gate fidelities exceed 99.5% in neutral atom arrays.",
                "paper": "P1"
            },
            {
                "id": "c2",
                "text": "Selective state space models scale linearly with context length.",
                "paper": "P2"
            }
        ]

        agent1_data = {"papers": papers, "dense_sentences": dense_sentences}
        agent2_data = {"claims": claims}

        res = run_agent3_context_cacher("test query", agent1_data, agent2_data, similarity_threshold=0.60)
        verified = {c["claim_id"]: c for c in res["verified_claims"]}

        # c1 matched peer-reviewed paper
        self.assertIn("c1", verified)
        self.assertEqual(verified["c1"]["verification_tier"], "auto_cache")
        self.assertEqual(verified["c1"]["status"], "Auto-Verified")

        # c2 matched preprint
        self.assertIn("c2", verified)
        self.assertEqual(verified["c2"]["verification_tier"], "auto_cache_preprint")
        self.assertEqual(verified["c2"]["status"], "Preprint-Corroborated")
        self.assertTrue(verified["c2"]["confidence_score"] <= 0.85)
        self.assertIn("preprint", verified["c2"]["reviewer_2_caveat"].lower())

    def test_agent4_synthesizer_renders_preprint_badges(self):
        """Agent 4 must render [✓ preprint • X] badge for auto_cache_preprint claims."""
        papers = [
            {
                "id": "p1",
                "paper_idx": "P1",
                "title": "Mamba State-Space Architecture",
                "authors": ["A. Gu", "T. Dao"],
                "year": 2024,
                "venue": "arXiv preprint",
                "url": "https://arxiv.org/abs/2312.00752",
                "provenance_tier": "preprint",
                "provenance_label": "Unrefereed Preprint"
            }
        ]
        agent1_data = {"papers": papers, "dense_sentences": []}
        agent2_data = {
            "sections": [
                {
                    "sub_question": "State Space Models",
                    "answer_html": '<claim id="c1" paper="P1">Selective SSMs scale linearly with sequence length.</claim>'
                }
            ],
            "quick_answer": "SSMs provide linear scaling.",
            "executive_summary": '<claim id="c1" paper="P1">Selective SSMs scale linearly.</claim>'
        }
        agent3_data = {
            "verified_claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "Selective SSMs scale linearly with sequence length.",
                    "status": "Preprint-Corroborated",
                    "verification_tier": "auto_cache_preprint",
                    "confidence_score": 0.82,
                    "matched_paper_id": "p1",
                    "reviewer_2_caveat": "Preliminary Finding: Grounded in unrefereed preprint."
                }
            ],
            "unverified_claims": []
        }

        import asyncio
        res = asyncio.run(run_agent4_fact_checker_synthesizer(
            query="SSMs",
            agent1_data=agent1_data,
            agent2_data=agent2_data,
            agent3_data=agent3_data,
            disable_fallback=False
        ))

        sec_html = res["dossier_sections"][0]["content_html"]
        self.assertIn("tier-preprint-badge", sec_html)
        self.assertIn("[✓ preprint • 1]", sec_html)
        self.assertIn("claim-tier-auto_cache_preprint", sec_html)
        self.assertEqual(res["citations"][0]["provenance_tier"], "preprint")
        self.assertEqual(res["citations"][0]["provenance_label"], "Unrefereed Preprint")


if __name__ == "__main__":
    unittest.main()
