"""
Unit and Integration Test Suite for Engine v5 (Tier 1 Innovations)
Validates:
- Concept decomposition & sub-question extraction
- Citation deduplication and version resolution (preprints vs published)
- Semantic passage chunking and scope tracking
- Deterministic exact-match number checks
- 3-Way verdicts (SUPPORTED, CONTRADICTED, NOT_FOUND_IN_CHECKED_TEXT)
"""

import unittest
from backend.engine_v5.concept_decomposer import decompose_research_query
from backend.engine_v5.snowball_retriever import (
    normalize_title, 
    resolve_and_deduplicate_papers,
    is_preprint_venue
)
from backend.engine_v5.passage_verifier import (
    chunk_paper_content,
    extract_numerical_entities,
    deterministic_exact_match_audit,
    adjudicate_claim_with_passages,
    verify_all_claims_depth
)

class TestEngineV5(unittest.TestCase):
    def test_01_concept_decomposition(self):
        query = "Spatial MPNNs vs Graph Transformers for molecular property prediction: over-squashing mitigation on QM9 and ZINC"
        concepts = decompose_research_query(query)
        self.assertGreaterEqual(len(concepts), 3)
        ids = [c["id"] for c in concepts]
        self.assertIn("concept_arch_a", ids)
        self.assertIn("concept_arch_b", ids)

    def test_02_version_resolution_preprint_vs_published(self):
        raw_papers = [
            {
                "title": "GraphGPS: General Powerful Scalable Graph Transformers",
                "venue": "arXiv preprint arXiv:2205.12454",
                "url": "https://arxiv.org/abs/2205.12454",
                "doi": "10.48550/arXiv.2205.12454",
                "abstract": "Preprint abstract with preliminary results."
            },
            {
                "title": "GraphGPS: General Powerful Scalable Graph Transformers",
                "venue": "Advances in Neural Information Processing Systems (NeurIPS 2022)",
                "url": "https://proceedings.neurips.cc/paper/2022/hash/graphgps",
                "doi": "10.5555/neurips.2022.graphgps",
                "abstract": "Peer-reviewed published abstract."
            }
        ]
        resolved = resolve_and_deduplicate_papers(raw_papers)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["version_status"], "published_peer_reviewed")
        self.assertIn("NeurIPS 2022", resolved[0]["venue"])

    def test_03_passage_chunking_with_scope(self):
        paper = {
            "paper_idx": "P1",
            "title": "Quantum Error Mitigation",
            "full_text": " ".join([f"Word{i}" for i in range(500)]),
            "abstract": "Short abstract."
        }
        chunks = chunk_paper_content(paper, chunk_words=150, overlap_words=30)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(c["scope"] == "full_text" for c in chunks))

    def test_04_exact_match_number_audit(self):
        chunks = [
            {
                "chunk_id": "P1_c0",
                "paper_idx": "P1",
                "paper_title": "QM9 Benchmarks",
                "scope": "full_text",
                "text": "Spatial MPNNs achieved 41.2 meV MAE on QM9 dipole moments, while GraphGPS achieved 24.6 meV."
            }
        ]
        
        has_match, num, chunk = deterministic_exact_match_audit(
            "Spatial MPNNs reported 41.2 meV MAE on molecular graphs.",
            chunks
        )
        self.assertTrue(has_match)
        self.assertEqual(num, "41.2")
        self.assertEqual(chunk["scope"], "full_text")

    def test_05_adjudicate_3way_verdicts(self):
        chunks = [
            {
                "chunk_id": "P1_c0",
                "paper_idx": "P1",
                "paper_title": "GraphGPS Proofs",
                "scope": "full_text",
                "text": "Spectral Laplacian positional encodings allow Graph Transformers to provably exceed the 1-WL isomorphism limit."
            }
        ]

        # Supported
        res_sup = adjudicate_claim_with_passages(
            {"claim": "Laplacian positional encodings allow transformers to exceed the 1-WL limit."},
            chunks
        )
        self.assertEqual(res_sup["verdict"], "SUPPORTED")
        self.assertEqual(res_sup["scope_checked"], "full_text")

        # Contradicted
        res_contra = adjudicate_claim_with_passages(
            {"claim": "Laplacian positional encodings are strictly bounded by the 1-WL limit and fail to exceed it."},
            chunks
        )
        self.assertIn(res_contra["verdict"], ["CONTRADICTED", "NOT_FOUND_IN_CHECKED_TEXT"])

        # Not found in checked text
        res_nf = adjudicate_claim_with_passages(
            {"claim": "Cryo-EM imaging of bacterial ribosome structures at 1.8 Angstroms."},
            chunks
        )
        self.assertEqual(res_nf["verdict"], "NOT_FOUND_IN_CHECKED_TEXT")
        self.assertEqual(res_nf["confidence_category"], "UNVERIFIED")

if __name__ == "__main__":
    unittest.main()
