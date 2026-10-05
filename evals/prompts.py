"""
Standardized Academic Research Prompts for Comparative Evaluation
Provides 5 carefully designed scientific queries targeting specific LLM failure modes:
1. Numerical & Hardware Precision (Quantum Neutral Atoms vs Transmons)
2. Dialectical Friction & Model Collapse (Synthetic Data Scaling)
3. Biomedical Grounding & Clinical Trials (GLP-1 in Alzheimer's)
4. Epistemic Calibration & Replication Failure (LK-99 Cu2S Transition)
5. Mathematical Rigor & IO Complexity (FlashAttention-3 vs FlashAttention-2)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class BenchmarkPrompt:
    id: int
    slug: str
    title: str
    domain: str
    query: str
    ground_truth_anchors: List[str]
    failure_modes_tested: List[str]
    evaluation_focus: str


BENCHMARK_PROMPTS: List[BenchmarkPrompt] = [
    BenchmarkPrompt(
        id=1,
        slug="neural_hawkes_vs_transformers_lob",
        title="Neural Hawkes Processes vs Transformers in High-Frequency Order Books",
        domain="Quantitative Finance & Financial Econometrics",
        query=(
            "Neural Hawkes processes vs deep transformer architectures for limit order book "
            "microstructure modeling and high-frequency queue depletion prediction"
        ),
        ground_truth_anchors=[
            "Point process mechanics: Neural Hawkes models capture self-exciting continuous-time conditional intensity lambda(t) of marked order events.",
            "Transformer limitations in LOB: Discrete time-binning issues, quadratic self-attention complexity, and inability to natively model asynchronous inter-arrival gaps.",
            "Queue depletion formulation: Modeled as a marked first-passage time problem for displayed depth Q_{p,s}(t) at price level p and side s.",
            "Current benchmark state: Pure empirical LOB microstructure benchmarks directly comparing Neural Hawkes to transformers under identical microsecond tick feeds are scarce.",
            "Dialectical tradeoff: Continuous-time physical interpretability and causality vs transformer capacity for large-scale multi-horizon pattern extraction."
        ],
        failure_modes_tested=[
            "Retrieval drift pulling unrelated event sequences (social media diffusion, vehicle parking).",
            "Collapsing into generic machine learning prose without defining intensity functions or first-passage queues.",
            "Failing to report the absence of standardized public tick-by-tick comparative benchmark leaderboards."
        ],
        evaluation_focus="Mathematical formulation of intensity functions, queue depletion first-passage targets, and sensitivity to continuous event timing."
    ),
    BenchmarkPrompt(
        id=2,
        slug="recursive_zk_vs_optimistic_rollups",
        title="Recursive ZK-Rollup Proof Verification vs Optimistic Dispute Windows",
        domain="Cryptographic Engineering & Distributed Systems",
        query=(
            "Recursive zero-knowledge rollup proof verification overhead vs optimistic fraud-proof dispute "
            "windows for cross-chain institutional financial settlement latency"
        ),
        ground_truth_anchors=[
            "Settlement latency comparison: ZK validity proofs provide deterministic cryptographic finality within minutes/hours vs optimistic 7-day challenge dispute windows.",
            "Computational overhead of recursion: Generating recursive SNARK/STARK proofs incurs high GPU/ASIC proving latency and compute cost, amortized over thousands of transactions.",
            "L1 on-chain verification costs: SNARK pairing checks require ~200k-300k gas on Ethereum, whereas optimistic settlement is near-zero gas in the happy path but requires continuous state post.",
            "Institutional capital efficiency: Optimistic 7-day windows impose significant liquidity lockup and market-maker bridge risk, whereas ZK proofs unlock immediate atomic cross-chain settlement.",
            "Dialectical tradeoff: High prover compute cost and hardware centralization in ZK vs capital inefficiency and censorship attack vectors during dispute windows in optimistic systems."
        ],
        failure_modes_tested=[
            "Inventing arbitrary proof generation times or L1 gas numbers without architectural qualification.",
            "Failing to analyze institutional liquidity lockup costs under multi-day challenge windows.",
            "Confusing L2 transaction sequencing finality with L1 state verification finality."
        ],
        evaluation_focus="Cryptographic verification complexity, economic capital efficiency, L1 settlement gas bounds, and institutional dispute latency."
    ),
    BenchmarkPrompt(
        id=3,
        slug="cbdc_two_tier_architecture",
        title="CBDC Two-Tier Architecture: Quantity Caps vs Wholesale Settlement",
        domain="Computational Macroeconomics & Central Bank Digital Currencies",
        query=(
            "Central bank digital currency two-tier architectural design: interest-bearing quantity caps vs "
            "wholesale settlement rails in mitigating commercial bank run dynamics"
        ),
        ground_truth_anchors=[
            "Balance-sheet transmission mechanics: CBDC as a direct central-bank liability vs commercial bank deposits.",
            "Retail quantity caps (holding limits H) and tiered remuneration as deposit flight mitigation controls.",
            "Wholesale CBDC rails restricting access to financial institutions for interbank gross/net settlement.",
            "Lack of empirical crisis stress-test data: Current literature relies on two-sided adoption models and architectural proposals rather than causal bank-run crisis observations.",
            "Dialectical tradeoff: Strict individual holding limits prevent sudden disintermediation but reduce payment velocity and utility."
        ],
        failure_modes_tested=[
            "Fabricating causal bank-run empirical statistics or non-existent crisis simulation findings.",
            "Conflating retail CBDC holding caps with wholesale interbank liquidity requirements.",
            "Failing to articulate the two-tier balance-sheet accounting identity."
        ],
        evaluation_focus="Balance-sheet accounting rigor, distinction between retail caps and wholesale rails, and epistemic calibration regarding lack of causal crisis data."
    ),
    BenchmarkPrompt(
        id=4,
        slug="protac_kinetics_vs_molecular_glues",
        title="PROTAC Ternary Complex Thermodynamics vs Molecular Glues",
        domain="Chemical Biology & Targeted Protein Degradation",
        query=(
            "PROTAC ternary complex thermodynamic stability and hook effect kinetics vs "
            "molecular glues for degrading non-druggable oncogenic transcription factors"
        ),
        ground_truth_anchors=[
            "Ternary complex equilibrium: Formation of POI-PROTAC-E3 ligase complex governed by cooperativity factor alpha (alpha > 1 positive, alpha < 1 negative).",
            "Hook effect kinetics: Bell-shaped dose-response curve caused by non-productive binary saturation ([PROTAC-POI] and [PROTAC-E3]) at elevated concentrations.",
            "Molecular glues mechanism: Induce de novo protein-protein interfaces directly between ubiquitin ligase (e.g. CRBN, VHL) and target without a flexible linker.",
            "Transcription factor targeting: Molecular glues excel for non-druggable transcription factors lacking defined binding pockets; PROTACs require modular target-binding warheads.",
            "Dialectical tradeoff: PROTAC rational modular design vs molecular glue screening serendipity and superior oral bioavailability (Lipinski's Rule of 5 compliance)."
        ],
        failure_modes_tested=[
            "Fabricating dissociation constants (K_D) or cooperativity factors (alpha) for specific oncogenic targets.",
            "Failing to explain the thermodynamic origin of the hook effect autoinhibition.",
            "Conflating bifunctional degradation tags with monovalent molecular glues."
        ],
        evaluation_focus="Biochemical rigor, mathematical formulation of cooperativity and hook kinetics, and structural comparison between modular linkers and composite interfaces."
    ),
    BenchmarkPrompt(
        id=5,
        slug="cucu_hybrid_bonding_cowos",
        title="Direct Cu-Cu Hybrid Bonding vs Micro-Bump CoWoS Interposers",
        domain="Semiconductor Advanced Packaging & Thermal Microelectronics",
        query=(
            "Direct copper-to-copper dielectric hybrid bonding vs micro-bump CoWoS interposers for "
            "sub-micron chiplet interconnect density and thermal dissipation"
        ),
        ground_truth_anchors=[
            "Interconnect pitch scaling: Direct Cu-Cu hybrid bonding achieves sub-micron pitches (< 1-3 um) vs CoWoS micro-bump pitches (25-45 um).",
            "Thermal dissipation mechanics: Elimination of solder bump standoff layers and underfill reduces interface thermal resistance R_th.",
            "Manufacturing constraints: Extreme chemical mechanical planarization (CMP) surface dishing requirements (< 2-3 nm) and ultra-clean ISO class bonding environments.",
            "TSMC CoWoS-S / CoWoS-L architectural boundaries: Silicon interposer micro-bumps provide proven manufacturing yield for large reticle assemblies but suffer parasitics.",
            "Dialectical tradeoff: True 3D hybrid bonding delivers orders-of-magnitude higher areal interconnect density but imposes stringent die flatness and thermal expansion matching."
        ],
        failure_modes_tested=[
            "Conflating CoWoS silicon interposer micro-bumps with direct dielectric hybrid bonding pitches.",
            "Fabricating thermal junction temperature reductions without physical boundary models.",
            "Ignoring CMP dishing and particle contamination yield bottlenecks."
        ],
        evaluation_focus="Exact interconnect pitch dimensions, thermal resistance modeling, CMP planarization constraints, and packaging trade-off frontiers."
    )
]


def get_prompt_by_id(prompt_id: int) -> BenchmarkPrompt:
    for p in BENCHMARK_PROMPTS:
        if p.id == prompt_id:
            return p
    raise ValueError(f"Prompt ID {prompt_id} not found in benchmark prompts (1-5 available).")
