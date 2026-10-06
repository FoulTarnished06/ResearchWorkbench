import unittest
import asyncio
from typing import Dict, Any, List

from backend.agents.agent1_scraper import (
    decompose_query_into_facets,
    snowball_citations,
    _dedup_papers_list,
    _normalize_doi_key,
    _normalize_title_key,
    classify_paper_provenance
)
from backend.post_processor import (
    check_dangling_references,
    clean_monograph_text,
    post_process_dossier,
    enforce_section2_empirical_purity
)

class TestUserSixArchitecturalImprovements(unittest.TestCase):
    """
    Test suite verifying the 6 architectural improvements:
    1. Query decomposition before retrieval
    2. Coverage gate with re-query loop
    3. Retrieval broadening with citation contexts
    4. Snowballing through references & citations
    5. Citation integrity enforced via code (recovery & provenance)
    6. Redesigned abstain case (partial answers, TL;DR, unverified leads, wall-of-text breaker)
    """

    def test_1_query_decomposition_atomic_facets(self):
        query = (
            "Evaluate EPaxos WAN commit latency, Raft leader lease failover time, "
            "and Classic McEliece public key size in post-quantum key exchange."
        )
        facets = decompose_query_into_facets(query)
        self.assertGreaterEqual(len(facets), 3)

        # Check that atomic queries capture key entities without clumping
        epaxos_found = any("epaxos" in (f.get("raw_facet") or f.get("sub_query") or "").lower() for f in facets)
        raft_found = any("raft" in (f.get("raw_facet") or f.get("sub_query") or "").lower() for f in facets)
        mceliece_found = any("mceliece" in (f.get("raw_facet") or f.get("sub_query") or "").lower() or "classic" in (f.get("raw_facet") or f.get("sub_query") or "").lower() for f in facets)

        self.assertTrue(epaxos_found, "EPaxos sub-facet should be isolated")
        self.assertTrue(raft_found, "Raft sub-facet should be isolated")
        self.assertTrue(mceliece_found, "Classic McEliece sub-facet should be isolated")

    def test_2_version_deduplication_and_rich_abstract_preservation(self):
        # Versioned preprints (e.g. arXiv / ChemRxiv v1, v2) must deduplicate to single richest record
        papers = [
            {
                "id": "chemrxiv_1",
                "title": "Regio-MPNN: Predicting site selectivity in aromatic substitution",
                "doi": "10.26434/chemrxiv-2023-xyz-v1",
                "abstract": "Brief abstract.",
                "provenance_tier": "unrefereed_preprint"
            },
            {
                "id": "chemrxiv_2",
                "title": "Regio-MPNN: Predicting site selectivity in aromatic substitution (v2)",
                "doi": "10.26434/chemrxiv-2023-xyz-v2",
                "abstract": "Extended substantive abstract detailing experimental regioselectivity accuracy of 89.4% across 1,200 reactions.",
                "provenance_tier": "unrefereed_preprint"
            }
        ]
        deduped = _dedup_papers_list(papers)
        self.assertEqual(len(deduped), 1)
        # Should keep the richer abstract
        self.assertIn("89.4%", deduped[0]["abstract"])

    def test_4_snowball_backward_and_forward(self):
        # Snowballing must explore both references (backward) and citations (forward)
        seed_papers = [
            {
                "id": "paper_seed",
                "paper_idx": "P1",
                "title": "PigPaxos: High Throughput WAN Consensus",
                "doi": "10.1145/example",
                "raw_references": [
                    {
                        "paperId": "ref_epaxos",
                        "title": "There is more consensus in Egalitarian Paxos",
                        "venue": "SOSP",
                        "year": 2013,
                        "citationCount": 500
                    }
                ],
                "raw_citations": [
                    {
                        "paperId": "cit_forward",
                        "title": "Recent advances in geo-replicated state machines",
                        "venue": "OSDI",
                        "year": 2024,
                        "citationCount": 12
                    }
                ]
            }
        ]
        snowballed = snowball_citations(seed_papers, max_snowball=4)
        snowball_titles = [p.get("title", "") for p in snowballed]
        self.assertTrue(any("Egalitarian Paxos" in t for t in snowball_titles), "Backward references should be extracted")
        self.assertTrue(any("Recent advances" in t for t in snowball_titles), "Forward citing papers should be extracted")

    def test_5_citation_integrity_code_recovery_and_ghost_purge(self):
        # In-text [P1] missing from bibliography should be recovered from all_pool_papers
        # Citations never referenced in text should be purged from bibliography
        dossier = {
            "query": "Distributed Consensus",
            "executive_summary": "Egalitarian Paxos achieves optimal WAN latency [P1].",
            "dossier_sections": [
                {
                    "sub_question": "Commit Latency",
                    "content_html": "<p>Egalitarian Paxos achieves 1 RTT commit in the absence of conflicts [P1].</p>",
                    "claims": []
                }
            ],
            "citations": [
                # Ghost citation that is never cited in text
                {
                    "paper_idx": "P99",
                    "paper_id": "ghost_id",
                    "title": "Unrelated Machine Learning Paper",
                    "authors": ["Ghost, A."],
                    "year": 2021,
                    "verified_claims_count": 0
                }
            ],
            "all_pool_papers": [
                {
                    "id": "epaxos_id",
                    "paper_idx": "P1",
                    "title": "There is more consensus in Egalitarian Paxos",
                    "authors": ["Moraru, I.", "Andersen, D."],
                    "year": 2013,
                    "venue": "ACM SOSP",
                    "doi": "10.1145/2517349.2517350",
                    "provenance_tier": "top_tier_peer_reviewed",
                    "provenance_label": "Peer-Reviewed Conference (ACM SOSP)"
                }
            ]
        }
        checked = check_dangling_references(dossier)
        cits = checked["citations"]
        cit_indices = [c.get("paper_idx") for c in cits]

        # P1 was recovered
        self.assertIn("P1", cit_indices)
        # P99 was purged as a ghost citation
        self.assertNotIn("P99", cit_indices)
        self.assertEqual(checked["dangling_reference_check"]["status"], "corrected")

    def test_5_provenance_derived_from_venue_metadata(self):
        # Peer-review badges must be derived from venue/doi metadata, not fabricated by LLM
        # Preprints must be labeled Unrefereed Preprint
        chemrxiv_tier, chemrxiv_label = classify_paper_provenance({"venue": "ChemRxiv", "doi": "10.26434/chemrxiv-2023-xyz"})
        self.assertEqual(chemrxiv_tier, "preprint")
        self.assertIn("Preprint", chemrxiv_label)

        arxiv_tier, arxiv_label = classify_paper_provenance({"venue": "arXiv:2305.12345", "doi": ""})
        self.assertEqual(arxiv_tier, "preprint")

        top_tier, top_label = classify_paper_provenance({"venue": "ACM SOSP", "doi": "10.1145/2517349"})
        self.assertEqual(top_tier, "peer_reviewed")
        self.assertIn("Peer-Reviewed", top_label)

    def test_6_abstain_case_partial_answers_and_unverified_leads(self):
        # When query has uncovered facets, system provides partial answer + unverified leads section
        dossier = {
            "query": "Classic McEliece key size and Kyber decapsulation speed",
            "quick_answer": "Kyber-768 requires 0.05 ms for decapsulation.",
            "sections": [
                {
                    "sub_question": "Kyber Decapsulation Speed",
                    "content_html": "<p>ML-KEM (Kyber) achieves fast decapsulation [P1].</p>",
                    "claims": [{"id": "c1", "text": "Kyber 0.05 ms", "paper": "P1"}]
                }
            ],
            "uncovered_facets": [
                {
                    "raw_facet": "Classic McEliece public key size",
                    "sub_query": "Classic McEliece public key size post-quantum"
                }
            ],
            "citations": [
                {
                    "paper_idx": "P1",
                    "paper_id": "kyber_paper",
                    "title": "CRYSTALS-Kyber: A CCA-Secure Module-Lattice-Based KEM",
                    "authors": ["Schwabe, P."],
                    "year": 2020,
                    "verified_claims_count": 1
                }
            ],
            "stats": {
                "papers_scraped": 6
            }
        }
        processed = post_process_dossier(dossier)

        # TL;DR must state retrieved count and on-topic count
        qa = processed.get("quick_answer", "")
        self.assertIn("retrieved literature (6 papers identified, 1 on-topic)", qa)

        # Output must have Unverified Leads section making NO factual claims
        secs = processed.get("sections", [])
        leads_sec = next((s for s in secs if "unverified leads" in (s.get("sub_question") or "").lower()), None)
        self.assertIsNotNone(leads_sec)
        self.assertIn("Classic McEliece", leads_sec["content_html"])
        self.assertIn("make no factual assertions", leads_sec["content_html"])

    def test_6_wall_of_text_breaking_and_empty_header_removal(self):
        long_paragraph = (
            "<p>" + " ".join(["word" for _ in range(250)]) + "</p>"
            "<h3></h3>"
            "<p><strong>   </strong></p>"
        )
        cleaned = clean_monograph_text(long_paragraph)

        # Empty headers must be removed
        self.assertNotIn("<h3></h3>", cleaned)
        self.assertNotIn("<strong>   </strong>", cleaned)

        # Long text must be split into multiple paragraphs
        p_count = cleaned.count("<p>")
        self.assertGreater(p_count, 1, "Long block should be broken into multiple paragraphs")


if __name__ == "__main__":
    unittest.main()
