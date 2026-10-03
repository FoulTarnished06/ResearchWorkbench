/**
 * AI RESEARCH WORKBENCH - MOCK SCENARIOS MODULE
 * Realistic peer-reviewed scientific scenarios for zero-credit offline demo mode
 */

export const MOCK_SCENARIOS = {
  quantum: {
    query: "Quantum Error Mitigation in Neutral Atom Qubits",
    papers_scraped: 3,
    sentences_extracted: 14,
    tokens_call1: 880,
    prompt_tokens_call1: 520,
    completion_tokens_call1: 360,
    tokens_call2: 620,
    prompt_tokens_call2: 390,
    completion_tokens_call2: 230,
    elapsed: 2.3,
    quick_answer: "Neutral atom optical tweezer platforms have surpassed key operational milestones for fault-tolerant quantum computing, achieving two-qubit gate fidelities exceeding 99.5% and nuclear spin coherence times beyond 40 seconds. Mobile optical tweezers enable dynamic, all-to-all qubit connectivity across hundreds of physical atoms, making transversal surface-code error syndrome extraction practically feasible.",
    executive_summary: "Recent empirical evaluations in neutral atom architectures demonstrate that high-density optical tweezer arrays have surpassed key thresholds for fault-tolerant quantum computing. With two-qubit gate fidelities exceeding 99.5% and nuclear spin coherence times extending beyond 40 seconds, transversal syndrome extraction across hundreds of physical qubits offers a viable pathway toward scalable, hardware-efficient quantum processors.",
    takeaways: [
      "Two-qubit entanglement gates exceed 99.5% fidelity in neutral atom tweezer arrays.",
      "Nuclear spin qubits in Sr-87 and Yb-171 achieve coherence times T2 surpassing 40 seconds.",
      "Mobile optical tweezers enable all-to-all connectivity across 256 logical qubits with transversal syndrome extraction."
    ],
    sub_questions: [
      "What are the foundational thresholds and two-qubit gate fidelities achieved in optical tweezer arrays?",
      "What dominant decoherence channels and laser phase noise mechanisms currently limit deep circuit execution?",
      "How do transversal syndrome extraction and coherent atom shuttling suppress error rates below the fault-tolerant threshold?"
    ],
    sections: [
      {
        sub_question: "What are the foundational thresholds and two-qubit gate fidelities achieved in optical tweezer arrays?",
        answer_html: `Empirical evaluations across high-density optical tweezer arrays demonstrate significant operational milestones for scalable architectures. Specifically, experimental benchmarks establish that <span class="claim-wrapper" data-claim-id="c1" data-ref-id="REF-1"><span class="claim-text">neutral atom optical tweezer platforms demonstrate programmable quantum computing with high fidelity two-qubit entanglement gates exceeding 99.5% fidelity.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span> Furthermore, dual-species hardware architectures confirm that <span class="claim-wrapper" data-claim-id="c2" data-ref-id="REF-1"><span class="claim-text">mobile optical tweezers enable all-to-all connectivity across 256 logical qubits with coherent shuttling.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span> These verified physical thresholds validate that fault-tolerant surface code syndrome extraction is experimentally feasible.`
      },
      {
        sub_question: "What dominant decoherence channels and laser phase noise mechanisms currently limit deep circuit execution?",
        answer_html: `Despite rapid gate fidelity improvements, coherent multi-qubit storage encounters physical dephasing limits under ambient thermal excitation. Detailed spectroscopic analyses demonstrate that <span class="claim-wrapper" data-claim-id="c3" data-ref-id="REF-3"><span class="claim-text">nuclear spin qubits in strontium-87 and ytterbium-171 exhibit coherence times $T_2$ surpassing 40 seconds under magic-wavelength optical dipole trapping.</span><sup class="citation-anchor" data-ref-id="REF-3"><a href="#cit-card-REF-3">[3]</a></sup></span> Diagnostic telemetry further indicates that <span class="claim-wrapper" data-claim-id="c4" data-ref-id="REF-3"><span class="claim-text">Raman laser phase noise and blackbody radiation-induced dephasing constitute the primary decoherence channels, mitigable via dynamical decoupling pulses.</span><sup class="citation-anchor" data-ref-id="REF-3"><a href="#cit-card-REF-3">[3]</a></sup></span>`
      },
      {
        sub_question: "How do transversal syndrome extraction and coherent atom shuttling suppress error rates below the fault-tolerant threshold?",
        answer_html: `Architectural scaling beyond the physical error threshold requires active fault tolerance through logical encoding. Demonstrations confirm that <span class="claim-wrapper" data-claim-id="c5" data-ref-id="REF-2"><span class="claim-text">encoding quantum information in transversal logical qubits suppresses error rates exponentially with circuit depths exceeding 800 operations.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span> Meanwhile, integrated optical interconnect analyses establish that <span class="claim-wrapper" data-claim-id="c6" data-ref-id="REF-2"><span class="claim-text">shuttling-based topologies eliminate intermediate swap network overhead in cryogenic vacuum cells.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span>`
      }
    ],
    citations: [
      {
        ref_id: "REF-1",
        paper_id: "quant_01",
        title: "Quantum Error Mitigation and Fault-Tolerant Thresholds in Rydberg Atom Arrays",
        authors: "M. Endres, H. Levine, A. Keesling, M. D. Lukin",
        year: 2024,
        venue: "Nature Quantum Information",
        url: "https://doi.org/10.1038/s41586-023-06927-3",
        citation_count: 142,
        verified_claims_count: 2,
        evidence: "Neutral atom optical tweezer platforms demonstrate programmable quantum computing with high fidelity two-qubit entanglement gates exceeding 99.5% fidelity. Mobile tweezers enable all-to-all connectivity across 256 logical qubits with coherent shuttling."
      },
      {
        ref_id: "REF-2",
        paper_id: "quant_02",
        title: "Logical Quantum Processor with Scalable Neutral-Atom Architecture",
        authors: "D. Bluvstein, S. J. Evered, A. A. Geim, V. Vuletic",
        year: 2024,
        venue: "Nature",
        url: "https://doi.org/10.1038/s41586-023-06927-3",
        citation_count: 210,
        verified_claims_count: 2,
        evidence: "Encoding quantum information in transversal logical qubits suppresses error rates exponentially with circuit depths exceeding 800 operations."
      },
      {
        ref_id: "REF-3",
        paper_id: "quant_03",
        title: "Decoherence Channels and Hyperfine Ground States in Alkaline-Earth Neutral Atoms",
        authors: "S. Ma, A. P. Burgers, J. D. Thompson",
        year: 2023,
        venue: "Physical Review X",
        url: "https://doi.org/10.1103/PhysRevX.13.041052",
        citation_count: 88,
        verified_claims_count: 2,
        evidence: "Nuclear spin qubits in strontium-87 and ytterbium-171 exhibit coherence times T2 surpassing 40 seconds under magic-wavelength optical dipole trapping."
      }
    ]
  },
  crispr: {
    query: "Engineered Cas12f Nucleases for Compact In Vivo Delivery",
    papers_scraped: 2,
    sentences_extracted: 10,
    tokens_call1: 820,
    prompt_tokens_call1: 480,
    completion_tokens_call1: 340,
    tokens_call2: 540,
    prompt_tokens_call2: 330,
    completion_tokens_call2: 210,
    elapsed: 2.1,
    quick_answer: "Engineered miniature Cas12f nucleases (400-500 amino acids) fit within single adeno-associated virus (AAV) delivery vectors alongside guide RNA and donor templates. Structural modifications in the REC2 domain enhance DNA unwinding velocity four-fold in mammalian cells, achieving high target-site indel rates with negligible off-target cleavage.",
    executive_summary: "Miniature Cas12f effectors overcome conventional AAV viral packaging barriers while engineered REC2 modifications achieve high editing fidelity across mammalian model systems.",
    takeaways: [
      "Miniature Cas12f nucleases (400-500 amino acids) fit within single adeno-associated virus (AAV) payloads.",
      "Cryo-EM structures at 2.8Å reveal asymmetric homodimer binding to 5'-TTTR PAM motifs.",
      "Engineered REC2 domain mutations increase DNA unwinding velocity four-fold in mammalian cells."
    ],
    sub_questions: [
      "How does Cas12f effector miniaturization facilitate single-AAV viral packaging?",
      "What structural modifications elevate editing efficacy in human mammalian cell lines?",
      "What off-target specificity benchmarks distinguish Cas12f from standard SpCas9 systems?"
    ],
    sections: [
      {
        sub_question: "How does Cas12f effector miniaturization facilitate single-AAV viral packaging?",
        answer_html: `Conventional CRISPR-Cas9 systems (~1368 amino acids) exceed standard packaging limits of adeno-associated virus (AAV) capsids ($4.7\\text{ kb}$). Recent structural investigations establish that <span class="claim-wrapper" data-claim-id="c1" data-ref-id="REF-1"><span class="claim-text">miniature CRISPR-Cas12f effectors (400-500 amino acids) package efficiently within single adeno-associated virus (AAV) vectors alongside guide RNA and repair templates.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span> This compact payload overcomes transduction overhead associated with dual-vector platforms.`
      },
      {
        sub_question: "What structural modifications elevate editing efficacy in human mammalian cell lines?",
        answer_html: `Wild-type Cas12f enzymes demonstrate moderate cleavage rates in mammalian chromatin due to slower unwinding kinetics. Cryo-EM analysis shows that <span class="claim-wrapper" data-claim-id="c2" data-ref-id="REF-2"><span class="claim-text">Cryo-EM structures at $2.8\\text{ \\AA}$ resolution reveal the asymmetric homodimeric assembly of Cas12f1 bound to a 5'-TTTR PAM duplex.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span> Furthermore, engineered mutagenesis indicates that <span class="claim-wrapper" data-claim-id="c3" data-ref-id="REF-2"><span class="claim-text">protein engineering of the REC2 and wedge domains elevates DNA unwinding rates four-fold in mammalian cells.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span>`
      },
      {
        sub_question: "What off-target specificity benchmarks distinguish Cas12f from standard SpCas9 systems?",
        answer_html: `Genome-wide cleavage sequencing reveals distinct safety advantages. Quantitative benchmarks document that <span class="claim-wrapper" data-claim-id="c4" data-ref-id="REF-1"><span class="claim-text">engineered Cas12f variants demonstrate high target site indel generation with negligible off-target cleavage across deep sequencing benchmarks.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span> Preliminary studies also demonstrate that <span class="claim-wrapper" data-claim-id="c5" data-ref-id="REF-1"><span class="claim-text">non-viral lipid nanoparticle formulations achieve targeted tissue tropism in murine models.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span>`
      }
    ],
    citations: [
      {
        ref_id: "REF-1",
        paper_id: "crispr_01",
        title: "Engineered Cas12f Nucleases for Compact In Vivo Adeno-Associated Viral Delivery",
        authors: "K. Tsuchida, H. Nishimasu, O. O. Abudayyeh, F. Zhang",
        year: 2024,
        venue: "Nature Biotechnology",
        url: "https://doi.org/10.1038/s41587-023-01825-4",
        citation_count: 178,
        verified_claims_count: 2,
        evidence: "Miniature CRISPR-Cas12f effectors (400-500 amino acids) package efficiently within single adeno-associated virus (AAV) vectors alongside guide RNA and repair templates."
      },
      {
        ref_id: "REF-2",
        paper_id: "crispr_02",
        title: "Structural Basis of PAM Recognition and Cleavage Activation in UncCas12f1",
        authors: "R. Xiao, X. Chen, Z. Wang, P. D. Hsu",
        year: 2023,
        venue: "Cell",
        url: "https://doi.org/10.1016/j.cell.2023.08.012",
        citation_count: 94,
        verified_claims_count: 2,
        evidence: "Cryo-EM structures at 2.8 Angstrom resolution reveal the asymmetric homodimeric assembly of Cas12f1 bound to a 5'-TTTR PAM duplex."
      }
    ]
  },
  memristor: {
    query: "Memristive Crossbars for Edge Neuromorphic Computing",
    papers_scraped: 2,
    sentences_extracted: 12,
    tokens_call1: 850,
    prompt_tokens_call1: 510,
    completion_tokens_call1: 340,
    tokens_call2: 580,
    prompt_tokens_call2: 360,
    completion_tokens_call2: 220,
    elapsed: 2.2,
    quick_answer: "Memristive crossbar arrays execute analog vector-matrix multiplication in memory via Ohm's and Kirchhoff's laws at 100x lower energy than digital accelerators. Bilayer HfOx/AlOx oxide interfaces maintain cycle-to-cycle conductance dispersion below 1.8%, enabling monolithic 65nm chips to achieve 42.8 TOPS/W inferencing efficiency.",
    executive_summary: "Analog memristive crossbar arrays execute high-density matrix arithmetic at two orders of magnitude lower energy than conventional digital accelerators, providing a breakthrough architecture for edge intelligence.",
    takeaways: [
      "Analog crossbar arrays compute vector-matrix multiplication via Ohm's law with 100x lower energy.",
      "Bilayer HfOx/AlOx oxide interfaces maintain cycle conductance dispersion below 1.8%.",
      "Integrated 65nm CMOS-memristor chips demonstrate 42.8 TOPS/W inferencing efficiency."
    ],
    sub_questions: [
      "How do analog filamentary memristors perform vector-matrix multiplication in memory?",
      "What cycle-to-cycle conductance variability controls exist for high-density crossbars?",
      "What energy efficiency gains are demonstrated over standard digital systolic arrays?"
    ],
    sections: [
      {
        sub_question: "How do analog filamentary memristors perform vector-matrix multiplication in memory?",
        answer_html: `Hardware acceleration of deep neural networks requires bypassing the von Neumann memory transfer bottleneck. Experimental crossbars demonstrate that <span class="claim-wrapper" data-claim-id="c1" data-ref-id="REF-1"><span class="claim-text">analog resistive switching crossbars execute $\\mathcal{O}(1)$ vector-matrix multiplication via Ohm's and Kirchhoff's laws at two orders of magnitude lower energy dissipation.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span>`
      },
      {
        sub_question: "What cycle-to-cycle conductance variability controls exist for high-density crossbars?",
        answer_html: `Filamentary stochasticity poses precision limits during in-situ training. Material characterizations reveal that <span class="claim-wrapper" data-claim-id="c2" data-ref-id="REF-2"><span class="claim-text">bilayer metal-oxide interfaces (HfOx/AlOx) suppress cycle-to-cycle conductance dispersion below $1.8\\%$ over $10^7$ programming cycles.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span>`
      },
      {
        sub_question: "What energy efficiency gains are demonstrated over standard digital systolic arrays?",
        answer_html: `Edge inferencing platforms require high energy efficiency under strict thermal dissipation budgets. Benchmarking on physical test silicon displays that <span class="claim-wrapper" data-claim-id="c3" data-ref-id="REF-1"><span class="claim-text">fully integrated $65\\text{nm}$ CMOS-memristor chips deliver $42.8\\text{ TOPS/W}$ for convolutional vision transformers.</span><sup class="citation-anchor" data-ref-id="REF-1"><a href="#cit-card-REF-1">[1]</a></sup></span> Experimental characterization also indicates that <span class="claim-wrapper" data-claim-id="c4" data-ref-id="REF-2"><span class="claim-text">monolithic 3D vertical memristor stacking expands crossbar bisection bandwidth density.</span><sup class="citation-anchor" data-ref-id="REF-2"><a href="#cit-card-REF-2">[2]</a></sup></span>`
      }
    ],
    citations: [
      {
        ref_id: "REF-1",
        paper_id: "mem_01",
        title: "A 42.8 TOPS/W Neuromorphic Inference Processor with Integrated Memristor Crossbar Arrays",
        authors: "W. Zhang, C. Gao, H. Yao, Y. Chai",
        year: 2024,
        venue: "IEEE International Solid-State Circuits Conference (ISSCC)",
        url: "https://doi.org/10.1109/ISSCC.2024.10454321",
        citation_count: 85,
        verified_claims_count: 2,
        evidence: "Analog resistive switching crossbars execute vector-matrix multiplication via Ohm's and Kirchhoff's laws at 100x lower energy dissipation."
      },
      {
        ref_id: "REF-2",
        paper_id: "mem_02",
        title: "Atomic-Scale Defect Engineering in Metal-Oxide Memristive Synapses",
        authors: "S. Kumar, J. P. Strachan, R. S. Williams",
        year: 2023,
        venue: "Nature Electronics",
        url: "https://doi.org/10.1038/s41928-023-00984-2",
        citation_count: 140,
        verified_claims_count: 2,
        evidence: "Bilayer metal-oxide interfaces suppress cycle-to-cycle conductance dispersion below 1.8% over 10^7 programming cycles."
      }
    ]
  }
};

/**
 * SEC-01: Secure SSE streaming client using HTTP POST.
 * Transmits API keys and parameters in the POST body,
 * completely preventing credential leakage into URLs or browser history.
 */
export async function fetchSSE(url, payload, eventHandlers, abortSignal) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify(payload),
    signal: abortSignal
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let currentEvent = 'message';
  let currentData = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const rawLine of lines) {
      const line = rawLine.replace(/\r$/, '');
      if (line === '') {
        if (currentData) {
          if (eventHandlers[currentEvent]) {
            try {
              eventHandlers[currentEvent]({ data: currentData });
            } catch (err) {
              console.error('SSE handler error for event', currentEvent, err);
            }
          }
          currentEvent = 'message';
          currentData = '';
        }
      } else if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const d = line.slice(5).trim();
        currentData = currentData ? currentData + '\n' + d : d;
      }
    }
  }

  if (buffer) {
    const line = buffer.replace(/\r$/, '');
    if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      const d = line.slice(5).trim();
      currentData = currentData ? currentData + '\n' + d : d;
    }
  }

  if (currentData && eventHandlers[currentEvent]) {
    try {
      eventHandlers[currentEvent]({ data: currentData });
    } catch (err) {
      console.error('SSE handler flush error', err);
    }
  }
}
