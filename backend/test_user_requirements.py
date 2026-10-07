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
from backend.agents.agent2_drafter import (
    detect_query_domain,
    synthesize_fallback_draft
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

    def test_spatial_mpnn_query_decomposition(self):
        query = (
            "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions vs "
            "Graph Transformers with spectral Laplacian positional encodings for molecular property prediction: "
            "over-squashing mitigation, expressive power beyond the 1-Weisfeiler-Lehman (1-WL) limit, "
            "and inference scaling on QM9 and ZINC benchmarks"
        )
        facets = decompose_query_into_facets(query)
        self.assertGreaterEqual(len(facets), 4)
        facet_texts = " ".join((f.get("raw_facet") or f.get("sub_query") or "").lower() for f in facets)
        self.assertTrue("mpnn" in facet_texts or "message passing" in facet_texts)
        self.assertTrue("transformer" in facet_texts or "laplacian" in facet_texts)
        self.assertTrue("over-squashing" in facet_texts or "1-wl" in facet_texts or "weisfeiler" in facet_texts)
        self.assertTrue("qm9" in facet_texts or "zinc" in facet_texts)

    def test_spatial_mpnn_domain_detection(self):
        query = (
            "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions vs "
            "Graph Transformers with spectral Laplacian positional encodings for molecular property prediction: "
            "over-squashing mitigation, expressive power beyond the 1-Weisfeiler-Lehman (1-WL) limit, "
            "and inference scaling on QM9 and ZINC benchmarks"
        )
        domain = detect_query_domain(query)
        self.assertEqual(domain, "graph_ml", "Should be classified into graph_ml, NOT systems_ml")

    def test_spatial_mpnn_parametric_derivations_and_zero_moe_leakage(self):
        query = (
            "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions vs "
            "Graph Transformers with spectral Laplacian positional encodings for molecular property prediction: "
            "over-squashing mitigation, expressive power beyond the 1-Weisfeiler-Lehman (1-WL) limit, "
            "and inference scaling on QM9 and ZINC benchmarks"
        )
        draft = synthesize_fallback_draft(query=query, papers=[], dense_sentences=[], domain="graph_ml")
        
        # Verify draft contains labelled parametric derivations
        sections = draft.get("sections", [])
        full_draft_text = draft.get("executive_summary", "") + " " + " ".join(s.get("answer_html", "") for s in sections)
        
        # Mathematical formulations must be present
        self.assertTrue(
            r"h_i^{(t+1)}" in full_draft_text or "Laplacian" in full_draft_text or "1-WL" in full_draft_text or "QM9" in full_draft_text,
            "Monograph must preserve labelled parametric derivations for graph ML"
        )
        
        # Zero MoE / Systems ML leakage
        forbidden_moe_terms = ["mixture-of-experts", "ncclalltoallv", "expert weights", "infiniband", "nvme"]
        for term in forbidden_moe_terms:
            self.assertNotIn(term, full_draft_text.lower(), f"Draft leaked systems_ml term '{term}' into graph_ml query")

    def test_no_sentence_duplication_in_fallback_draft(self):
        query = (
            "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions vs "
            "Graph Transformers with spectral Laplacian positional encodings for molecular property prediction"
        )
        # Even with only 2 input sentences, subsequent sections must not loop back and duplicate sentences
        dummy_sentences = [
            {"text": "Spatial message passing networks aggregate localized atomic neighborhoods efficiently.", "paper_id": "p1", "paper_title": "Paper 1"},
            {"text": "Graph transformers apply global dense self-attention to mitigate structural over-squashing.", "paper_id": "p2", "paper_title": "Paper 2"}
        ]
        draft = synthesize_fallback_draft(query=query, dense_sentences=dummy_sentences, domain="graph_ml", target_count=3)
        
        all_claim_texts = [c.get("text", "").strip() for c in draft.get("claims", []) if c.get("text")]
        # Every single claim text must be unique
        unique_claim_texts = set(all_claim_texts)
        self.assertEqual(len(all_claim_texts), len(unique_claim_texts), "All claim texts across fallback draft must be distinct without recycling")


if __name__ == "__main__":
    unittest.main()
