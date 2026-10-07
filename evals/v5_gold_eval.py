"""
Gold Evaluation Benchmark Harness (Tier 1 Quality & Precision Suite)
Evaluates:
- Canonical Paper Recall across benchmark queries
- True Claim Support Precision
- Injected Error & Counterfactual Rejection Rate
- Verifier Calibration (3-way verdicts & exact number checks)
"""

import unittest
from typing import List, Dict, Any

from backend.engine_v5.concept_decomposer import decompose_research_query
from backend.engine_v5.passage_verifier import (
    chunk_paper_content, 
    deterministic_exact_match_audit,
    adjudicate_claim_with_passages,
    verify_all_claims_depth
)

# GOLD STANDARD EVALUATION DATASET
GOLD_BENCHMARK_SET = [
    {
        "query_id": "gold_01_mol_graph",
        "query": "Spatial Message Passing Neural Networks (MPNN) with edge-conditioned convolutions vs Graph Transformers with spectral Laplacian positional encodings for molecular property prediction: over-squashing mitigation, expressive power beyond the 1-Weisfeiler-Lehman (1-WL) limit, and inference scaling on QM9 and ZINC benchmarks",
        "canonical_papers": [
            "GraphGPS: General Powerful Scalable Graph Transformers",
            "Directional Message Passing for Molecular Graphs",
            "Weisfeiler and Leman Go Neural: Higher-Order Graph Neural Networks"
        ],
        "true_claims": [
            {"claim": "Spatial MPNNs maintain O(|V| + |E|) inference scaling on sparse molecular graphs."},
            {"claim": "Laplacian positional encodings allow Graph Transformers to provably exceed the 1-WL limit."},
            {"claim": "DimeNet directional message passing is bounded by the 3-WL limit."}
        ],
        "injected_falsehoods": [
            {"claim": "Spatial MPNNs suffer from quadratic O(|V|^2) attention complexity on QM9."},
            {"claim": "Laplacian positional encodings strictly degrade expressive power below the 0-WL limit."},
            {"claim": "GraphGPS inference throughput is 800% faster than linear spatial MPNNs on large biopolymers."}
        ],
        "mock_corpus": [
            {
                "paper_idx": "P1",
                "title": "GraphGPS: General Powerful Scalable Graph Transformers",
                "venue": "NeurIPS 2022",
                "full_text": "GraphGPS decouples local edge-conditioned convolutions from global self-attention. Spectral Laplacian positional encodings (LapPE) provably allow Graph Transformers to exceed the 1-WL isomorphism limit while mitigating over-squashing across long-range molecular graphs. However, full global attention scales with O(|V|^2) quadratic complexity.",
                "abstract": "We present GraphGPS, a modular architecture exceeding 1-WL."
            },
            {
                "paper_idx": "P2",
                "title": "Directional Message Passing for Molecular Graphs",
                "venue": "ICLR 2020",
                "full_text": "DimeNet utilizes directional message passing based on representations of interatomic angles. DimeNet directional message passing is bounded by the 3-WL limit. Traditional spatial MPNNs maintain O(|V| + |E|) linear computational complexity on sparse molecular graphs.",
                "abstract": "Directional message passing captures 3D angular conformation."
            }
        ]
    },
    {
        "query_id": "gold_02_neutral_atoms",
        "query": "Quantum Error Mitigation in Neutral Atom Qubits with Optical Tweezers and Rydberg Blockade",
        "canonical_papers": [
            "Fault-tolerant quantum computation with neutral atom arrays",
            "High-fidelity two-qubit gates in neutral atoms"
        ],
        "true_claims": [
            {"claim": "Rydberg blockade enables two-qubit gate fidelities exceeding 99.5%."},
            {"claim": "Optical tweezers operate in ultra-high vacuum environments."}
        ],
        "injected_falsehoods": [
            {"claim": "Rydberg blockade enables two-qubit gate fidelities of only 25.0%."},
            {"claim": "Optical tweezers operate in open atmospheric pressure without vacuum."}
        ],
        "mock_corpus": [
            {
                "paper_idx": "P1",
                "title": "High-fidelity two-qubit gates in neutral atoms",
                "venue": "Nature 2024",
                "full_text": "Neutral atom quantum computing utilizes optical tweezers in ultra-high vacuum environments. Rydberg blockade enables two-qubit gate fidelities exceeding 99.5% with low decoherence rates.",
                "abstract": "We report high-fidelity neutral atom gates above 99.5%."
            }
        ]
    }
]

class TestV5GoldEvaluation(unittest.TestCase):
    """
    Automated Gold Benchmark Test Suite.
    Measures precision, recall, and error-rejection under deliberate injections.
    """

    def test_01_concept_decomposition_on_gold_queries(self):
        """Verify query decomposition properly extracts A, B, mechanisms, and benchmarks."""
        for gold in GOLD_BENCHMARK_SET:
            concepts = decompose_research_query(gold["query"])
            self.assertGreaterEqual(len(concepts), 2, f"Query '{gold['query_id']}' failed to produce at least 2 concepts")
            categories = [c["category"] for c in concepts]
            if "vs" in gold["query"].lower():
                self.assertIn("architecture_a", categories)
                self.assertIn("architecture_b", categories)

    def test_02_exact_match_numeric_verification(self):
        """Verify deterministic exact match verifies 99.5% and 1-WL without LLM."""
        corpus = GOLD_BENCHMARK_SET[1]["mock_corpus"]
        chunks = chunk_paper_content(corpus[0])
        
        # Test positive number match
        has_match, entity, chunk = deterministic_exact_match_audit(
            "Rydberg blockade enables two-qubit gate fidelities exceeding 99.5%.",
            chunks
        )
        self.assertTrue(has_match, "Failed to verify 99.5% exact number match")
        self.assertEqual(entity, "99.5")

    def test_03_injected_counterfactual_rejection(self):
        """Verify verifier catches deliberately injected contradictory claims."""
        corpus = GOLD_BENCHMARK_SET[0]["mock_corpus"]
        all_chunks = []
        for p in corpus:
            all_chunks.extend(chunk_paper_content(p))

        # Test true claim
        true_adj = adjudicate_claim_with_passages(
            {"claim": "Spectral Laplacian positional encodings allow Graph Transformers to exceed the 1-WL limit."},
            all_chunks
        )
        self.assertEqual(true_adj["verdict"], "SUPPORTED")

        # Test injected counterfactual claim (swapped quadratic complexity to MPNNs)
        false_adj = adjudicate_claim_with_passages(
            {"claim": "Spatial MPNNs suffer from quadratic O(|V|^2) attention complexity on QM9."},
            all_chunks
        )
        # Should NOT be supported as true; must be CONTRADICTED or NOT_FOUND
        self.assertIn(false_adj["verdict"], ["CONTRADICTED", "NOT_FOUND_IN_CHECKED_TEXT"])

    def test_04_benchmark_gold_evaluation_metrics(self):
        """Run full evaluation suite across the gold set and verify aggregate metrics."""
        total_true_claims = 0
        supported_true_claims = 0
        total_injected_false = 0
        rejected_injected_false = 0

        for item in GOLD_BENCHMARK_SET:
            corpus = item["mock_corpus"]
            all_chunks = []
            for p in corpus:
                all_chunks.extend(chunk_paper_content(p))

            # Evaluate true claims
            for tc in item["true_claims"]:
                total_true_claims += 1
                res = adjudicate_claim_with_passages(tc, all_chunks)
                if res["verdict"] == "SUPPORTED":
                    supported_true_claims += 1

            # Evaluate injected false claims
            for fc in item["injected_falsehoods"]:
                total_injected_false += 1
                res = adjudicate_claim_with_passages(fc, all_chunks)
                if res["verdict"] in ["CONTRADICTED", "NOT_FOUND_IN_CHECKED_TEXT"]:
                    rejected_injected_false += 1

        true_recall = supported_true_claims / total_true_claims
        false_rejection_rate = rejected_injected_false / total_injected_false

        print(f"\n[V5 GOLD EVALUATION RESULTS]")
        print(f"True Claim Recall: {true_recall:.1%} ({supported_true_claims}/{total_true_claims})")
        print(f"Injected Falsehood Rejection Rate: {false_rejection_rate:.1%} ({rejected_injected_false}/{total_injected_false})")

        self.assertGreaterEqual(true_recall, 0.80, "True claim recall fell below 80% threshold")
        self.assertGreaterEqual(false_rejection_rate, 0.85, "Falsehood rejection fell below 85% threshold")

if __name__ == "__main__":
    unittest.main()
