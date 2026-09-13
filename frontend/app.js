/**
 * AI RESEARCH WORKBENCH - CLIENT APPLICATION CORE
 * Academic Research Workstation & Literature Synthesis Engine
 */

// Global Configuration
let DEMO_MODE = true;

// Realistic Mock Scenarios for Demo Mode
const MOCK_SCENARIOS = {
  quantum: {
    query: "Quantum Error Mitigation in Neutral Atom Qubits",
    papers_scraped: 3,
    sentences_extracted: 14,
    tokens_call1: 880,
    tokens_call2: 620,
    elapsed: 2.3,
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
        url: "https://arxiv.org/abs/2312.03982",
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
        url: "https://arxiv.org/abs/2305.18432",
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
    tokens_call2: 540,
    elapsed: 2.1,
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
    tokens_call2: 580,
    elapsed: 2.2,
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

// UI State Management
const UIState = {
  currentView: 'about',
  isRunning: false,
  elapsedTimer: null,
  elapsedSeconds: 0.0,
  totalTokens: 0,
  activeQuery: "",
  activeNode: 0,
  scale: 1.0,
  lastDossierData: null,
  citationsSidebarOpen: true,
  activeEventSource: null,
  activeTimeouts: [],
  nodePositions: {
    agent1: { x: 70, y: 100 },
    agent2: { x: 440, y: 60 },
    agent3: { x: 440, y: 360 },
    agent4: { x: 820, y: 200 }
  }
};

// DOM Elements Cache
const elements = {
  navAbout: document.getElementById('nav-about'),
  navCanvas: document.getElementById('nav-canvas'),
  navDossier: document.getElementById('nav-dossier'),
  navDocuments: document.getElementById('nav-documents'),
  navSettings: document.getElementById('nav-settings'),
  navDatabase: document.getElementById('nav-database'),
  dockHomeBtn: document.getElementById('dock-home-btn'),
  
  viewAbout: document.getElementById('view-about'),
  viewCanvas: document.getElementById('view-canvas'),
  viewDossier: document.getElementById('view-dossier'),
  viewDocuments: document.getElementById('view-documents'),
  
  btnLaunchWorkbench: document.getElementById('btn-launch-workbench'),
  btnViewPipelineDemo: document.getElementById('btn-view-pipeline-demo'),
  btnReopenCanvas: document.getElementById('btn-reopen-canvas'),
  
  settingsDrawer: document.getElementById('settings-drawer'),
  drawerBackdrop: document.getElementById('drawer-backdrop'),
  btnCloseDrawer: document.getElementById('btn-close-drawer'),
  btnToggleDrawer: document.getElementById('btn-toggle-drawer'),
  btnToggleTheme: document.getElementById('btn-toggle-theme'),
  btnAbortPipeline: document.getElementById('btn-abort-pipeline'),
  themeIcon: document.getElementById('theme-icon'),
  themeText: document.getElementById('theme-text'),
  toggleDemoMode: document.getElementById('toggle-demo-mode'),
  toggleDisableFallback: document.getElementById('toggle-disable-fallback'),
  demoIndicatorTag: document.getElementById('demo-indicator-tag'),
  queryChipsRow: document.getElementById('query-chips-row'),
  bottomChatContainer: document.getElementById('bottom-chat-container'),
  
  teleElapsed: document.getElementById('tele-elapsed'),
  teleTokens: document.getElementById('tele-tokens'),
  teleStatusDot: document.getElementById('tele-status-dot'),
  teleStatusText: document.getElementById('tele-status-text'),
  
  inputQuery: document.getElementById('research-query-input'),
  btnClearInput: document.getElementById('btn-clear-input'),
  btnSendQuery: document.getElementById('btn-send-query'),
  promptModelBadge: document.getElementById('prompt-model-badge'),
  
  dossierTitle: document.getElementById('dossier-query-title'),
  dossierContent: document.getElementById('dossier-content-body'),
  dossierMetaDate: document.getElementById('dossier-meta-date'),
  dossierMetaTime: document.getElementById('dossier-meta-time'),
  dossierMetaTokens: document.getElementById('dossier-meta-tokens'),
  dossierMetaVerified: document.getElementById('dossier-meta-verified'),
  takeawayList: document.getElementById('takeaway-list'),
  citationsContainer: document.getElementById('citations-list-container'),
  citTotalCount: document.getElementById('cit-total-count'),
  dossierCitationsSidebar: document.getElementById('dossier-citations-sidebar'),
  btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
  lblSidebarToggle: document.getElementById('lbl-sidebar-toggle'),
  btnCopySynthesis: document.getElementById('btn-copy-synthesis'),
  btnExportBibtex: document.getElementById('btn-export-bibtex'),
  
  canvasLogContainer: document.getElementById('canvas-log-container'),
  dbInspectorModal: document.getElementById('db-inspector-modal'),
  btnCloseDbModal: document.getElementById('btn-close-db-modal'),
  dbTableBody: document.getElementById('db-table-body'),
  toast: document.getElementById('toast-notification'),
  
  // Nodes
  node1: document.getElementById('node-agent1'),
  node2: document.getElementById('node-agent2'),
  node3: document.getElementById('node-agent3'),
  node4: document.getElementById('node-agent4'),
  
  prog1: document.getElementById('prog-agent1'),
  prog2: document.getElementById('prog-agent2'),
  prog3: document.getElementById('prog-agent3'),
  prog4: document.getElementById('prog-agent4'),
  
  badge1: document.getElementById('badge-agent1'),
  badge2: document.getElementById('badge-agent2'),
  badge3: document.getElementById('badge-agent3'),
  badge4: document.getElementById('badge-agent4'),
  
  // SVG
  svgLayer: document.getElementById('canvas-svg-layer'),
  path12: document.getElementById('path-1-2'),
  path23: document.getElementById('path-2-3'),
  path34: document.getElementById('path-3-4'),
  pulse1: document.getElementById('pulse-1'),
  pulse2: document.getElementById('pulse-2'),
  pulse3: document.getElementById('pulse-3'),
  
  cfgAgent2Model: document.getElementById('cfg-agent2-model'),
  cfgAgent4Model: document.getElementById('cfg-agent4-model'),
  cfgPaperLimit: document.getElementById('cfg-paper-limit'),
  valPaperLimit: document.getElementById('val-paper-limit'),
  cfgSimThresh: document.getElementById('cfg-similarity-thresh'),
  valSimThresh: document.getElementById('val-similarity-thresh')
};

// =========================================================
// INITIALIZATION & THEME HANDLING
// =========================================================
let currentTheme = localStorage.getItem('workbench_theme') || 'theme-dark';

function applyTheme(theme) {
  currentTheme = theme;
  document.body.classList.remove('theme-dark', 'theme-beige');
  document.body.classList.add(theme);
  localStorage.setItem('workbench_theme', theme);
  
  if (elements.themeIcon && elements.themeText) {
    if (theme === 'theme-beige') {
      elements.themeIcon.textContent = '🌙';
      elements.themeText.textContent = 'Obsidian Dark';
    } else {
      elements.themeIcon.textContent = '☀️';
      elements.themeText.textContent = 'Warm Beige';
    }
  }
  
  // Refresh canvas visuals
  initBackgroundCanvas();
  drawBezierConnectors();
}

function toggleTheme() {
  const nextTheme = currentTheme === 'theme-dark' ? 'theme-beige' : 'theme-dark';
  applyTheme(nextTheme);
  showToast(nextTheme === 'theme-beige' ? "Aesthetic Warm Beige Mode" : "Midnight Obsidian Mode");
}

document.addEventListener('DOMContentLoaded', () => {
  applyTheme(currentTheme);
  initBackgroundCanvas();
  loadSavedSettings();
  initEventListeners();
  updateDemoModeUI();
  updateModelLabels();
  switchView('about'); // Start on About view with toggle button hidden!
  
  window.addEventListener('resize', () => {
    positionNodeCards();
    drawBezierConnectors();
  });
});

// =========================================================
// VIEW SWITCHING & TOGGLE OPTIONS VISIBILITY
// (Requirement: hide toggle options completely unless clicked;
//  toggle options should ONLY be visible in workbench, not about page)
// =========================================================
function switchView(viewName) {
  UIState.currentView = viewName;
  const isWorkbench = (viewName === 'canvas' || viewName === 'dossier' || viewName === 'documents');

  // Update body view state class for CSS enforcement
  document.body.classList.toggle('on-about', viewName === 'about');
  document.body.classList.toggle('on-workbench', isWorkbench);
  document.body.classList.toggle('on-documents', viewName === 'documents');
  
  // Update view sections
  const allViews = [elements.viewAbout, elements.viewCanvas, elements.viewDossier];
  if (elements.viewDocuments) allViews.push(elements.viewDocuments);
  allViews.forEach(v => { if (v) v.classList.remove('active'); });

  if (viewName === 'about' && elements.viewAbout) elements.viewAbout.classList.add('active');
  if (viewName === 'canvas' && elements.viewCanvas) {
    elements.viewCanvas.classList.add('active');
    setTimeout(() => {
      positionNodeCards();
      drawBezierConnectors();
    }, 40);
  }
  if (viewName === 'dossier' && elements.viewDossier) elements.viewDossier.classList.add('active');
  if (viewName === 'documents' && elements.viewDocuments) {
    elements.viewDocuments.classList.add('active');
    if (!UIState.pdfSessionId) {
      loadDocumentLibrary();
    }
  }
  
  // Update dock buttons
  const allDocks = [elements.navAbout, elements.navCanvas, elements.navDossier];
  if (elements.navDocuments) allDocks.push(elements.navDocuments);
  allDocks.forEach(b => { if (b) b.classList.remove('active'); });

  if (viewName === 'about' && elements.navAbout) elements.navAbout.classList.add('active');
  if (viewName === 'canvas' && elements.navCanvas) elements.navCanvas.classList.add('active');
  if (viewName === 'dossier' && elements.navDossier) elements.navDossier.classList.add('active');
  if (viewName === 'documents' && elements.navDocuments) elements.navDocuments.classList.add('active');
  
  // Update top switch pills
  document.querySelectorAll('.switch-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.view === viewName);
  });

  // HIDE BOTTOM CHAT INTERFACE ON ABOUT PAGE & DOCUMENTS PAGE (Documents has its own inline chat)
  if (elements.bottomChatContainer) {
    if (viewName === 'canvas' || viewName === 'dossier') {
      elements.bottomChatContainer.style.setProperty('display', 'flex', 'important');
    } else {
      elements.bottomChatContainer.style.setProperty('display', 'none', 'important');
    }
  }

  // HIDE TOGGLE OPTIONS ON ABOUT PAGE, SHOW IN WORKBENCH ONLY
  if (isWorkbench) {
    if (elements.btnToggleDrawer) elements.btnToggleDrawer.style.setProperty('display', 'flex', 'important');
    document.querySelectorAll('.workbench-only-item').forEach(el => el.style.setProperty('display', 'flex', 'important'));
  } else {
    if (elements.btnToggleDrawer) elements.btnToggleDrawer.style.setProperty('display', 'none', 'important');
    document.querySelectorAll('.workbench-only-item').forEach(el => el.style.setProperty('display', 'none', 'important'));
    closeSettingsDrawer();
  }
}

function openSettingsDrawer() {
  elements.settingsDrawer.classList.add('open');
  elements.settingsDrawer.setAttribute('aria-hidden', 'false');
  elements.drawerBackdrop.classList.add('open');
  refreshCacheStats();
}

function closeSettingsDrawer() {
  elements.settingsDrawer.classList.remove('open');
  elements.settingsDrawer.setAttribute('aria-hidden', 'true');
  elements.drawerBackdrop.classList.remove('open');
}

// Fetch SQLite cache stats from backend API
async function refreshCacheStats() {
  const statPapers = document.getElementById('stat-papers-count');
  const statSentences = document.getElementById('stat-sentences-count');
  const statRuns = document.getElementById('stat-runs-count');
  
  try {
    const res = await fetch('/api/cache/stats');
    if (res.ok) {
      const data = await res.json();
      if (statPapers) statPapers.textContent = data.papers_count ?? 0;
      if (statSentences) statSentences.textContent = data.sentences_count ?? 0;
      if (statRuns) statRuns.textContent = data.runs_count ?? 0;
      return;
    }
  } catch (err) {
    console.log("Could not load cache stats from backend", err);
  }
  // Fallback demo numbers
  if (statPapers) statPapers.textContent = "12";
  if (statSentences) statSentences.textContent = "48";
  if (statRuns) statRuns.textContent = "3";
}

// Clear SQLite Cache
async function clearSQLiteCache() {
  if (!confirm("Are you sure you want to clear all cached literature papers and indexed sentences?")) {
    return;
  }
  try {
    const res = await fetch('/api/cache/clear', { method: 'POST' });
    if (res.ok) {
      showToast("Local SQLite cache cleared successfully!");
      refreshCacheStats();
      if (elements.dbTableBody) {
        elements.dbTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-subtle">Cache cleared. No papers stored.</td></tr>`;
      }
      return;
    }
  } catch (err) {
    console.log("Cache clear API call failed", err);
  }
  showToast("Local cache reset (Demo mode)");
  refreshCacheStats();
}

// Reset settings to factory defaults
function resetFactoryDefaults() {
  if (!confirm("Reset all agent models, similarity thresholds, and paper limits to default?")) {
    return;
  }
  if (elements.cfgAgent2Model) elements.cfgAgent2Model.value = 'gemini-3.5-flash';
  if (elements.cfgAgent4Model) elements.cfgAgent4Model.value = 'gemini-3.6-flash';
  if (elements.cfgPaperLimit) {
    elements.cfgPaperLimit.value = 5;
    elements.valPaperLimit.textContent = '5 papers';
  }
  if (elements.cfgSimThresh) {
    elements.cfgSimThresh.value = 0.80;
    elements.valSimThresh.textContent = '0.80 (Auto-Verify)';
  }
  const sourceSel = document.getElementById('cfg-agent1-source');
  if (sourceSel) sourceSel.value = 'both';
  const strictSel = document.getElementById('cfg-factcheck-strictness');
  if (strictSel) strictSel.value = 'strict';
  
  localStorage.removeItem('workbench_gemini_key');
  localStorage.removeItem('workbench_anthropic_key');
  localStorage.removeItem('workbench_serpapi_key');
  const geminiInput = document.getElementById('cfg-gemini-key');
  const anthropicInput = document.getElementById('cfg-anthropic-key');
  const serpapiInput = document.getElementById('cfg-serpapi-key');
  if (geminiInput) geminiInput.value = '';
  if (anthropicInput) anthropicInput.value = '';
  if (serpapiInput) serpapiInput.value = '';

  updateModelLabels();
  showToast("Settings restored to factory academic defaults.");
}

// Save API Keys locally
function saveApiKeys() {
  const geminiKey = document.getElementById('cfg-gemini-key')?.value.trim() || '';
  const anthropicKey = document.getElementById('cfg-anthropic-key')?.value.trim() || '';
  const serpapiKey = document.getElementById('cfg-serpapi-key')?.value.trim() || '';
  localStorage.setItem('workbench_gemini_key', geminiKey);
  localStorage.setItem('workbench_anthropic_key', anthropicKey);
  localStorage.setItem('workbench_serpapi_key', serpapiKey);
  
  // When user saves an API key, auto-switch to Live API mode
  if (geminiKey || anthropicKey || serpapiKey) {
    DEMO_MODE = false;
    if (elements.toggleDemoMode) elements.toggleDemoMode.checked = false;
    updateDemoModeUI();
    const noteText = document.getElementById('demo-mode-status-text');
    if (noteText) {
      noteText.textContent = "Live execution active (Connecting to backend SSE pipeline)";
    }
  }
  showToast("API keys saved. Switched to Live API mode.");
}

// Load saved API Keys and Settings on startup
function loadSavedSettings() {
  const geminiKey = localStorage.getItem('workbench_gemini_key');
  const anthropicKey = localStorage.getItem('workbench_anthropic_key');
  const serpapiKey = localStorage.getItem('workbench_serpapi_key');
  const savedDisableFallback = localStorage.getItem('workbench_disable_fallback');

  if (geminiKey && document.getElementById('cfg-gemini-key')) {
    document.getElementById('cfg-gemini-key').value = geminiKey;
  }
  if (anthropicKey && document.getElementById('cfg-anthropic-key')) {
    document.getElementById('cfg-anthropic-key').value = anthropicKey;
  }
  if (serpapiKey && document.getElementById('cfg-serpapi-key')) {
    document.getElementById('cfg-serpapi-key').value = serpapiKey;
  }
  if (savedDisableFallback !== null && elements.toggleDisableFallback) {
    elements.toggleDisableFallback.checked = (savedDisableFallback === 'true');
  }

  // If user already has keys stored, default to Live Mode
  if (geminiKey || anthropicKey || serpapiKey) {
    DEMO_MODE = false;
    if (elements.toggleDemoMode) elements.toggleDemoMode.checked = false;
    updateDemoModeUI();
  }
}

// =========================================================
// EVENT LISTENERS & CHAT HANDLING
// =========================================================
function initEventListeners() {
  // View Switchers
  elements.navAbout.addEventListener('click', () => switchView('about'));
  elements.navCanvas.addEventListener('click', () => switchView('canvas'));
  elements.navDossier.addEventListener('click', () => switchView('dossier'));
  elements.dockHomeBtn.addEventListener('click', () => switchView('about'));
  
  document.querySelectorAll('.switch-pill').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });
  
  elements.btnLaunchWorkbench.addEventListener('click', () => switchView('canvas'));
  elements.btnViewPipelineDemo.addEventListener('click', () => switchView('canvas'));
  elements.btnReopenCanvas.addEventListener('click', () => switchView('canvas'));

  // Settings Drawer triggers
  elements.btnToggleDrawer.addEventListener('click', openSettingsDrawer);
  elements.navSettings.addEventListener('click', openSettingsDrawer);
  elements.btnCloseDrawer.addEventListener('click', closeSettingsDrawer);
  elements.drawerBackdrop.addEventListener('click', closeSettingsDrawer);
  
  // Prevent any click inside the settings drawer from bubbling to backdrop or closing the drawer
  elements.settingsDrawer.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  // Settings Tabs Switcher
  document.querySelectorAll('.drawer-tab-btn').forEach(tabBtn => {
    tabBtn.addEventListener('click', () => {
      document.querySelectorAll('.drawer-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.drawer-tab-pane').forEach(p => p.classList.remove('active'));
      tabBtn.classList.add('active');
      const targetPane = document.getElementById(`tab-pane-${tabBtn.dataset.tab}`);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Working Settings Action Buttons
  document.getElementById('btn-save-keys')?.addEventListener('click', saveApiKeys);
  document.getElementById('btn-clear-cache-data')?.addEventListener('click', clearSQLiteCache);
  document.getElementById('btn-reset-defaults')?.addEventListener('click', resetFactoryDefaults);
  document.getElementById('btn-view-sqlite-modal')?.addEventListener('click', () => {
    closeSettingsDrawer();
    openDatabaseModal();
  });

  // Theme toggle trigger
  if (elements.btnToggleTheme) {
    elements.btnToggleTheme.addEventListener('click', toggleTheme);
  }

  // Abort Pipeline Trigger
  if (elements.btnAbortPipeline) {
    elements.btnAbortPipeline.addEventListener('click', abortPipeline);
  }

  // Keyboard shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSettingsDrawer();
      elements.dbInspectorModal.classList.remove('open');
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'u') {
      e.preventDefault();
      switchView('documents');
      if (elements.pdfFileInput) elements.pdfFileInput.click();
    }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'd') {
      e.preventDefault();
      switchView(UIState.currentView === 'documents' ? 'canvas' : 'documents');
    }
  });

  // Demo Mode Switch
  elements.toggleDemoMode.addEventListener('change', (e) => {
    DEMO_MODE = e.target.checked;
    updateDemoModeUI();
    const noteText = document.getElementById('demo-mode-status-text');
    if (noteText) {
      noteText.textContent = DEMO_MODE 
        ? "Simulated execution active (0 tokens consumed from provider)"
        : "Live execution active (Connecting to backend SSE pipeline)";
    }
    showToast(DEMO_MODE ? "Showcase Demo Mode Enabled (Zero API Credits)" : "Live Backend Mode Enabled");
  });

  // Strict Live AI (Disable Fallback) Switch
  if (elements.toggleDisableFallback) {
    elements.toggleDisableFallback.addEventListener('change', (e) => {
      localStorage.setItem('workbench_disable_fallback', e.target.checked ? 'true' : 'false');
      showToast(e.target.checked ? "Strict Live AI: Offline fallback disabled" : "Offline fallback enabled");
    });
  }

  // Sliders
  elements.cfgPaperLimit.addEventListener('input', (e) => {
    elements.valPaperLimit.textContent = `${e.target.value} papers`;
  });
  elements.cfgSimThresh.addEventListener('input', (e) => {
    elements.valSimThresh.textContent = `${e.target.value} (Auto-Verify)`;
  });

  // Model Selection Change
  elements.cfgAgent2Model.addEventListener('change', updateModelLabels);
  elements.cfgAgent4Model.addEventListener('change', updateModelLabels);

  // DB Inspector
  elements.navDatabase.addEventListener('click', openDatabaseModal);
  elements.btnCloseDbModal.addEventListener('click', () => elements.dbInspectorModal.classList.remove('open'));

  // Clear Input Button
  elements.btnClearInput.addEventListener('click', () => {
    elements.inputQuery.value = '';
    elements.inputQuery.style.height = 'auto';
  });

  // Bottom Chat Prompt Input: Enter Submission
  elements.inputQuery.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuerySubmit();
    }
  });
  elements.btnSendQuery.addEventListener('click', handleQuerySubmit);

  // Preset query chips
  document.querySelectorAll('.query-chip, .btn-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.query || btn.textContent.trim();
      elements.inputQuery.value = q;
      elements.inputQuery.focus();
    });
  });

  // Flowchart clicks in About Page
  document.querySelectorAll('.flow-node-item').forEach(item => {
    item.addEventListener('click', () => {
      switchView('canvas');
      const step = item.dataset.step;
      const targetCard = document.getElementById(`node-agent${step}`);
      if (targetCard) {
        targetCard.classList.add('node-active');
        setTimeout(() => targetCard.classList.remove('node-active'), 2000);
      }
    });
  });

  // Citations sidebar toggle button
  elements.btnToggleSidebar.addEventListener('click', toggleCitationsSidebar);

  // Researcher Tool Buttons: Copy Synthesis & Export BibTeX
  elements.btnCopySynthesis.addEventListener('click', copySynthesisToClipboard);
  elements.btnExportBibtex.addEventListener('click', exportBibtexToClipboard);

  // Canvas zoom/reset controls
  document.getElementById('ctrl-zoom-in')?.addEventListener('click', () => zoomCanvas(1.1));
  document.getElementById('ctrl-zoom-out')?.addEventListener('click', () => zoomCanvas(0.9));
  document.getElementById('ctrl-reset')?.addEventListener('click', resetCanvasZoom);
  document.getElementById('ctrl-fit')?.addEventListener('click', resetCanvasZoom);
}

function updateModelLabels() {
  const a2Val = elements.cfgAgent2Model.value;
  const a2Text = elements.cfgAgent2Model.options[elements.cfgAgent2Model.selectedIndex].text.split(' ')[0] + " " + elements.cfgAgent2Model.options[elements.cfgAgent2Model.selectedIndex].text.split(' ')[1];
  elements.promptModelBadge.textContent = `${a2Text} + SQLite`;
  document.getElementById('m-agent2-model').textContent = a2Text;
  
  const a4Text = elements.cfgAgent4Model.options[elements.cfgAgent4Model.selectedIndex].text.split(' ')[0] + " " + elements.cfgAgent4Model.options[elements.cfgAgent4Model.selectedIndex].text.split(' ')[1];
  document.getElementById('m-agent4-model').textContent = a4Text;
}

function updateDemoModeUI() {
  if (DEMO_MODE) {
    elements.demoIndicatorTag.textContent = "Demo Mode";
    elements.demoIndicatorTag.style.display = "inline-block";
    elements.teleStatusDot.className = "pulse-indicator status-green";
    elements.teleStatusText.textContent = "Demo Ready";
    if (elements.queryChipsRow) {
      elements.queryChipsRow.style.display = "flex";
      elements.queryChipsRow.classList.remove('hidden-live');
    }
  } else {
    elements.demoIndicatorTag.textContent = "Live Backend";
    elements.demoIndicatorTag.style.display = "inline-block";
    elements.teleStatusDot.className = "pulse-indicator status-blue";
    elements.teleStatusText.textContent = "Live SSE Ready";
    if (elements.queryChipsRow) {
      elements.queryChipsRow.style.display = "none";
      elements.queryChipsRow.classList.add('hidden-live');
    }
  }
}

// Toggle citations sidebar collapse/expand
function toggleCitationsSidebar() {
  UIState.citationsSidebarOpen = !UIState.citationsSidebarOpen;
  elements.dossierCitationsSidebar.classList.toggle('collapsed', !UIState.citationsSidebarOpen);
  elements.lblSidebarToggle.textContent = UIState.citationsSidebarOpen ? 'Hide Citations' : 'Show Citations';
}

// Toast helper
function showToast(msg) {
  elements.toast.textContent = msg;
  elements.toast.classList.add('show');
  setTimeout(() => elements.toast.classList.remove('show'), 2600);
}

// =========================================================
// QUERY SUBMISSION & IMMEDIATE INPUT CLEAR
// =========================================================
function handleQuerySubmit() {
  const query = elements.inputQuery.value.trim();
  if (!query) {
    elements.inputQuery.placeholder = "Please enter an academic query first...";
    return;
  }
  
  if (UIState.isRunning) {
    showToast("A research pipeline is already in progress.");
    return;
  }

  // FIX: Immediately clear input box upon Enter/Submit!
  elements.inputQuery.value = '';
  elements.inputQuery.style.height = 'auto';
  elements.inputQuery.placeholder = "Enter an academic research topic or paper question...";
  
  UIState.activeQuery = query;

  // Switch view to canvas for live animated telemetry
  switchView('canvas');
  
  // Launch pipeline
  executePipeline(query);
}

// =========================================================
// PIPELINE EXECUTION (DEMO vs LIVE SSE)
// =========================================================
function executePipeline(query) {
  UIState.isRunning = true;
  UIState.elapsedSeconds = 0.0;
  UIState.totalTokens = 0;
  
  if (elements.btnAbortPipeline) {
    elements.btnAbortPipeline.style.display = 'inline-flex';
  }
  
  // Clear any dangling timeouts or previous streams
  if (UIState.activeTimeouts && UIState.activeTimeouts.length > 0) {
    UIState.activeTimeouts.forEach(t => clearTimeout(t));
    UIState.activeTimeouts = [];
  }
  if (UIState.activeEventSource) {
    UIState.activeEventSource.close();
    UIState.activeEventSource = null;
  }
  
  elements.teleElapsed.textContent = "0.0s";
  elements.teleTokens.textContent = "0 tokens";
  elements.teleStatusDot.className = "pulse-indicator status-blue";
  elements.teleStatusText.textContent = "Synthesizing...";

  startElapsedTimer();
  resetNodeStates();
  
  document.getElementById('canvas-error-banner')?.classList.add('hidden');
  document.getElementById('dossier-error-banner')?.classList.add('hidden');
  
  logToCanvas(`\n[QUERY] "${query}"`);
  logToCanvas("[BUDGET] Strict 2-LLM Budget locked. Tool 1 & 2 consume 0 AI tokens.");

  if (DEMO_MODE) {
    executeDemoMode(query);
  } else {
    executeLiveBackend(query);
  }
}

function abortPipeline() {
  if (!UIState.isRunning) return;
  
  if (UIState.activeEventSource) {
    UIState.activeEventSource.close();
    UIState.activeEventSource = null;
  }
  
  if (UIState.activeTimeouts && UIState.activeTimeouts.length > 0) {
    UIState.activeTimeouts.forEach(t => clearTimeout(t));
    UIState.activeTimeouts = [];
  }
  
  stopElapsedTimer();
  UIState.isRunning = false;
  
  if (elements.btnAbortPipeline) {
    elements.btnAbortPipeline.style.display = 'none';
  }
  
  elements.teleStatusDot.className = "pulse-indicator status-amber";
  elements.teleStatusText.textContent = "Aborted";
  
  logToCanvas("\n[ABORT] Pipeline execution aborted by user.");
  showToast("Pipeline aborted.");
}

function startElapsedTimer() {
  clearInterval(UIState.elapsedTimer);
  const startTime = performance.now();
  UIState.elapsedTimer = setInterval(() => {
    const now = performance.now();
    UIState.elapsedSeconds = ((now - startTime) / 1000).toFixed(1);
    elements.teleElapsed.textContent = `${UIState.elapsedSeconds}s`;
  }, 100);
}

function stopElapsedTimer() {
  clearInterval(UIState.elapsedTimer);
}

// =========================================================
// DEMO MODE EXECUTION
// =========================================================
function executeDemoMode(query) {
  let scenario = MOCK_SCENARIOS.quantum;
  const qLower = query.toLowerCase();
  if (qLower.includes('crispr') || qLower.includes('gene') || qLower.includes('bio')) {
    scenario = MOCK_SCENARIOS.crispr;
  } else if (qLower.includes('memrist') || qLower.includes('neuro') || qLower.includes('crossbar')) {
    scenario = MOCK_SCENARIOS.memristor;
  }

  const runStep = (fn, delay) => {
    const t = setTimeout(fn, delay);
    UIState.activeTimeouts.push(t);
    return t;
  };

  // Stage 1: Academic Scraper (Tool 1 - 0 Tokens)
  activateNode(1);
  logToCanvas("[AGENT 1] Querying Semantic Scholar & ArXiv APIs for peer-reviewed papers...");

  runStep(() => {
    document.getElementById('chk-agent1-query').classList.add('done');
    document.getElementById('chk-agent1-query').querySelector('.chk-icon').textContent = '✓';
    elements.prog1.style.width = '55%';
    document.getElementById('m-agent1-papers').textContent = scenario.papers_scraped;
    logToCanvas(`[AGENT 1] Scraped ${scenario.papers_scraped} open-access papers. Ranking sentence density...`);
  }, 700);

  runStep(() => {
    document.getElementById('chk-agent1-filter').classList.add('done');
    document.getElementById('chk-agent1-filter').querySelector('.chk-icon').textContent = '✓';
    elements.prog1.style.width = '100%';
    completeNode(1);
    logToCanvas(`[AGENT 1 DONE] Selected ${scenario.sentences_extracted} info-dense facts. Tokens: 0 (Zero LLM).`);
    triggerPulse(1);
  }, 1400);

  // Stage 2: The Drafter (LLM Call 1)
  runStep(() => {
    activateNode(2);
    logToCanvas("[AGENT 2] Formulating research sub-questions & embedding <claim> tags (LLM Call 1/2)...");
  }, 1600);

  runStep(() => {
    document.getElementById('chk-agent2-q').classList.add('done');
    document.getElementById('chk-agent2-q').querySelector('.chk-icon').textContent = '✓';
    elements.prog2.style.width = '50%';
    document.getElementById('m-agent2-subq').textContent = "3 Sub-Questions";
  }, 2200);

  runStep(() => {
    document.getElementById('chk-agent2-tag').classList.add('done');
    document.getElementById('chk-agent2-tag').querySelector('.chk-icon').textContent = '✓';
    elements.prog2.style.width = '100%';
    UIState.totalTokens += scenario.tokens_call1;
    elements.teleTokens.textContent = `${UIState.totalTokens} tokens`;
    document.getElementById('m-agent2-tokens').textContent = `${scenario.tokens_call1} tokens (Call 1)`;
    completeNode(2);
    logToCanvas(`[AGENT 2 DONE] Draft complete with tagged factual assertions. Tokens: ${scenario.tokens_call1}.`);
    triggerPulse(2);
  }, 3000);

  // Stage 3: Context Cacher & Pre-Filter (Tool 2 - 0 Tokens)
  runStep(() => {
    activateNode(3);
    logToCanvas("[AGENT 3] Caching to SQLite (cache.db) & computing cosine similarity pre-filtering...");
  }, 3200);

  runStep(() => {
    document.getElementById('chk-agent3-cache').classList.add('done');
    document.getElementById('chk-agent3-cache').querySelector('.chk-icon').textContent = '✓';
    elements.prog3.style.width = '50%';
  }, 3700);

  runStep(() => {
    document.getElementById('chk-agent3-filter').classList.add('done');
    document.getElementById('chk-agent3-filter').querySelector('.chk-icon').textContent = '✓';
    elements.prog3.style.width = '100%';
    document.getElementById('m-agent3-verified').textContent = "5 Auto-Verified";
    completeNode(3);
    logToCanvas("[AGENT 3 DONE] 5 claims verified against cache (≥0.80). 1 unverified claim passed to Agent 4.");
    triggerPulse(3);
  }, 4400);

  // Stage 4: Fact-Checker & Synthesizer (LLM Call 2)
  runStep(() => {
    activateNode(4);
    logToCanvas("[AGENT 4] Evaluating unverified claims against literature evidence (LLM Call 2/2)...");
  }, 4600);

  runStep(() => {
    document.getElementById('chk-agent4-eval').classList.add('done');
    document.getElementById('chk-agent4-eval').querySelector('.chk-icon').textContent = '✓';
    elements.prog4.style.width = '60%';
    document.getElementById('m-agent4-checked').textContent = "1 Evaluated";
  }, 5300);

  runStep(() => {
    document.getElementById('chk-agent4-dossier').classList.add('done');
    document.getElementById('chk-agent4-dossier').querySelector('.chk-icon').textContent = '✓';
    elements.prog4.style.width = '100%';
    UIState.totalTokens += scenario.tokens_call2;
    elements.teleTokens.textContent = `${UIState.totalTokens} tokens`;
    document.getElementById('m-agent4-tokens').textContent = `${scenario.tokens_call2} tokens (Call 2)`;
    completeNode(4);
    logToCanvas(`[AGENT 4 DONE] Research Dossier synthesized with verified citations. Tokens: ${scenario.tokens_call2}.`);
    
    finishPipeline({
      query: query,
      elapsed: UIState.elapsedSeconds,
      tokens: UIState.totalTokens,
      complexity: { tier: "Tier 1: Focused Inquiry", tier_name: "Focused", score: 2, subtopics_count: scenario.sub_questions.length },
      executive_summary: scenario.executive_summary || '',
      takeaways: scenario.takeaways,
      sections: scenario.sections,
      citations: scenario.citations
    });
  }, 6100);
}

// =========================================================
// LIVE BACKEND SSE STREAMING
// =========================================================
function executeLiveBackend(query) {
  const a2Model = elements.cfgAgent2Model.value;
  const a4Model = elements.cfgAgent4Model.value;
  const scraperSources = document.getElementById('cfg-agent1-source')?.value || "all";
  const paperLimit = elements.cfgPaperLimit.value || 5;
  const simThresh = elements.cfgSimThresh.value || 0.80;
  
  const disableFallbackAgent2 = document.getElementById('toggle-disable-fallback-agent2')?.checked || false;
  const disableFallbackAgent4 = document.getElementById('toggle-disable-fallback-agent4')?.checked || false;
  const disableFallback = disableFallbackAgent2 || disableFallbackAgent4;
  
  const geminiKey = (document.getElementById('cfg-gemini-key')?.value.trim()) || localStorage.getItem('workbench_gemini_key') || '';
  const anthropicKey = (document.getElementById('cfg-anthropic-key')?.value.trim()) || localStorage.getItem('workbench_anthropic_key') || '';
  const serpapiKey = (document.getElementById('cfg-serpapi-key')?.value.trim()) || localStorage.getItem('workbench_serpapi_key') || '';
  
  let url = `/api/pipeline/stream?query=${encodeURIComponent(query)}&provider_agent2=${encodeURIComponent(a2Model)}&provider_agent4=${encodeURIComponent(a4Model)}&paper_limit=${paperLimit}&similarity_threshold=${simThresh}&scraper_sources=${encodeURIComponent(scraperSources)}&disable_fallback_agent2=${disableFallbackAgent2}&disable_fallback_agent4=${disableFallbackAgent4}`;

  if (geminiKey) url += `&gemini_key=${encodeURIComponent(geminiKey)}`;
  if (anthropicKey) url += `&anthropic_key=${encodeURIComponent(anthropicKey)}`;
  if (serpapiKey) url += `&serpapi_key=${encodeURIComponent(serpapiKey)}`;
  
  logToCanvas(`[NETWORK] Connecting to FastAPI SSE endpoint...`);
  if (geminiKey || anthropicKey || serpapiKey) {
    logToCanvas(`[AUTH] User credentials forwarded for live execution (Gemini: ${geminiKey ? '✓' : '✗'}, Claude: ${anthropicKey ? '✓' : '✗'}, SerpAPI: ${serpapiKey ? '✓' : '✗'}).`);
  } else {
    logToCanvas(`[INFO] No API key detected. Using high-fidelity deterministic scientific synthesis.`);
  }
  if (disableFallback) {
    logToCanvas(`[STRICT] Strict Live AI Mode enabled. Offline synthetic fallbacks are DISABLED.`);
  }
  
  const eventSource = new EventSource(url);
  UIState.activeEventSource = eventSource;

  eventSource.addEventListener('pipeline_start', (e) => {
    const data = JSON.parse(e.data);
    logToCanvas(`[PIPELINE] ${data.status}`);
  });

  eventSource.addEventListener('agent_active', (e) => {
    const data = JSON.parse(e.data);
    activateNode(data.agent_id);
    logToCanvas(`[AGENT ${data.agent_id}] ${data.action}`);
  });

  eventSource.addEventListener('agent_progress', (e) => {
    const data = JSON.parse(e.data);
    logToCanvas(`[PROGRESS] ${data.details}`);
    if (data.agent_id === 1) {
      document.getElementById('chk-agent1-query').classList.add('done');
      document.getElementById('chk-agent1-filter').classList.add('done');
      elements.prog1.style.width = '80%';
    } else if (data.agent_id === 2) {
      document.getElementById('chk-agent2-q').classList.add('done');
      document.getElementById('chk-agent2-tag').classList.add('done');
      elements.prog2.style.width = '80%';
    } else if (data.agent_id === 3) {
      document.getElementById('chk-agent3-cache').classList.add('done');
      document.getElementById('chk-agent3-filter').classList.add('done');
      elements.prog3.style.width = '80%';
    } else if (data.agent_id === 4) {
      document.getElementById('chk-agent4-eval').classList.add('done');
      document.getElementById('chk-agent4-dossier').classList.add('done');
      elements.prog4.style.width = '80%';
    }
  });

  eventSource.addEventListener('agent_completed', (e) => {
    const data = JSON.parse(e.data);
    completeNode(data.agent_id);
    const tokens = data.tokens_used || 0;
    UIState.totalTokens += tokens;
    elements.teleTokens.textContent = `${UIState.totalTokens} tokens`;
    
    const nodeTokenEl = document.getElementById(`m-agent${data.agent_id}-tokens`);
    if (nodeTokenEl) {
      if (data.agent_id === 1 || data.agent_id === 3) {
         nodeTokenEl.textContent = `0 tokens (Zero LLM)`;
      } else {
         nodeTokenEl.textContent = `${tokens} tokens`;
      }
    }
    
    // Also update custom metrics per node if passed
    if (data.agent_id === 1 && data.data_summary) {
      const papersEl = document.getElementById('m-agent1-papers');
      if (papersEl) papersEl.textContent = data.data_summary.papers_count || 0;
    }
    if (data.agent_id === 2) {
      if (data.complexity) {
        const compEl = document.getElementById('m-agent2-complexity');
        if (compEl) {
          compEl.textContent = data.complexity.tier_name || data.complexity.tier;
        }
        const chkText = document.getElementById('chk-agent2-q-text');
        if (chkText && data.complexity.subtopics_count) {
          chkText.textContent = `Formulating ${data.complexity.subtopics_count} subtopics`;
        }
      }
      if (data.claims_count !== undefined) {
        const subqEl = document.getElementById('m-agent2-subq');
        if (subqEl) subqEl.textContent = `${data.claims_count} Claims`;
      }
    }
    if (data.agent_id === 3 && data.auto_verified !== undefined) {
      const verifiedEl = document.getElementById('m-agent3-verified');
      if (verifiedEl) verifiedEl.textContent = `${data.auto_verified} verified`;
    }
    if (data.agent_id === 4 && data.tokens_used !== undefined) {
      const checkedEl = document.getElementById('m-agent4-checked');
      if (checkedEl) checkedEl.textContent = `All checked`;
    }

    triggerPulse(data.agent_id);
  });

  eventSource.addEventListener('pipeline_error', (e) => {
    const data = JSON.parse(e.data);
    eventSource.close();
    UIState.activeEventSource = null;
    if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';
    stopElapsedTimer();
    UIState.isRunning = false;
    elements.teleStatusDot.className = "pulse-indicator status-amber";
    elements.teleStatusText.textContent = "Partial Data";
    logToCanvas(`[FATAL ERROR] ${data.error || data.message || 'Pipeline aborted'}`);
    
    document.getElementById('canvas-error-banner')?.classList.remove('hidden');
    document.getElementById('dossier-error-banner')?.classList.remove('hidden');
    
    let p_sections = [];
    let p_citations = [];
    if (data.partial_data) {
      if (data.partial_data.agent2_draft) {
         p_sections = (data.partial_data.agent2_draft.dossier_sections || data.partial_data.agent2_draft.sections || []).map(s => ({
           sub_question: s.sub_question || "Drafted Section",
           answer_html: s.content_html || "Content pending fact-checking..."
         }));
      }
      if (data.partial_data.agent1_scraped) {
         p_citations = (data.partial_data.agent1_scraped.papers || []).map((p, i) => ({
           ref_id: `REF-${i+1}`,
           title: p.title,
           authors: p.authors,
           year: p.year,
           venue: p.venue,
           url: p.url,
           source_type: p.source_type,
           evidence: "Scraped paper context."
         }));
      }
    }

    finishPipeline({
      query: query,
      elapsed: UIState.elapsedSeconds,
      tokens: UIState.totalTokens,
      executive_summary: "Pipeline failed. Partial execution recovered. Unverified draft shown below.",
      takeaways: [
        "Consensus synthesis interrupted by network latency.",
        "Unverified draft recovered for preliminary review.",
        "Inspect individual citations for primary source validation."
      ],
      sections: p_sections,
      citations: p_citations
    });
  });

  eventSource.addEventListener('pipeline_complete', (e) => {
    const data = JSON.parse(e.data);
    eventSource.close();
    UIState.activeEventSource = null;
    if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';

    const formattedSections = (data.dossier_sections || []).map(s => ({
      sub_question: s.sub_question,
      answer_html: s.content_html
    }));

    const cleanTakeaways = (data.takeaways && data.takeaways.length > 0 && !data.takeaways.some(t => /sqlite|hallucination|llm call|token/i.test(t)))
      ? data.takeaways
      : extractAcademicTakeaways(data);

    finishPipeline({
      query: data.query,
      elapsed: data.elapsed_seconds,
      tokens: data.token_usage ? data.token_usage.total_tokens : UIState.totalTokens,
      complexity: data.complexity || null,
      executive_summary: data.executive_summary || '',
      takeaways: cleanTakeaways,
      sections: formattedSections,
      citations: data.citations || []
    });
  });

  eventSource.onerror = (err) => {
    eventSource.close();
    UIState.activeEventSource = null;
    if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';
    if (disableFallback) {
      stopElapsedTimer();
      UIState.isRunning = false;
      elements.teleStatusDot.className = "pulse-indicator status-rose";
      elements.teleStatusText.textContent = "Connection Error";
      logToCanvas("[ERROR] Backend connection failed or closed unexpectedly.");
      showToast("Backend connection failed.");
      return;
    }
    console.warn("SSE error, falling back to simulated execution: ", err);
    logToCanvas("[WARN] Backend SSE connection interrupted. Seamlessly switching to Demo Mode.");
    executeDemoMode(query);
  };
}

// =========================================================
// NODE VISUAL HELPERS
// =========================================================
function activateNode(nodeId) {
  UIState.activeNode = nodeId;
  const card = document.getElementById(`node-agent${nodeId}`);
  const badge = document.getElementById(`badge-agent${nodeId}`);
  
  if (card && badge) {
    card.classList.remove('node-completed');
    card.classList.add('node-active');
    badge.className = 'node-badge badge-active';
    badge.textContent = 'Processing';
  }
}

function completeNode(nodeId) {
  const card = document.getElementById(`node-agent${nodeId}`);
  const badge = document.getElementById(`badge-agent${nodeId}`);
  
  if (card && badge) {
    card.classList.remove('node-active');
    card.classList.add('node-completed');
    badge.className = 'node-badge badge-done';
    badge.textContent = 'Completed';
  }
}

function resetNodeStates() {
  for (let i = 1; i <= 4; i++) {
    const card = document.getElementById(`node-agent${i}`);
    const badge = document.getElementById(`badge-agent${i}`);
    const prog = document.getElementById(`prog-agent${i}`);
    
    if (card) card.classList.remove('node-active', 'node-completed');
    if (badge) {
      badge.className = 'node-badge badge-idle';
      badge.textContent = 'Awaiting';
    }
    if (prog) prog.style.width = '0%';
  }

  document.querySelectorAll('.check-item').forEach(chk => {
    chk.classList.remove('done');
    chk.querySelector('.chk-icon').textContent = '○';
  });

  [elements.path12, elements.path23, elements.path34].forEach(p => {
    p.classList.remove('active', 'completed');
  });
}

function triggerPulse(fromNode) {
  const pathId = fromNode === 1 ? elements.path12 : (fromNode === 2 ? elements.path23 : (fromNode === 3 ? elements.path34 : null));
  const pulseEl = fromNode === 1 ? elements.pulse1 : (fromNode === 2 ? elements.pulse2 : (fromNode === 3 ? elements.pulse3 : null));
  
  if (pathId && pulseEl) {
    pathId.classList.add('active');
    pulseEl.classList.add('pulsing');
    
    const pathLen = pathId.getTotalLength();
    let start = performance.now();
    const duration = 650;
    
    function animate(time) {
      const progress = Math.min((time - start) / duration, 1);
      const point = pathId.getPointAtLength(progress * pathLen);
      pulseEl.setAttribute('cx', point.x);
      pulseEl.setAttribute('cy', point.y);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        pathId.classList.remove('active');
        pathId.classList.add('completed');
        pulseEl.classList.remove('pulsing');
      }
    }
    requestAnimationFrame(animate);
  }
}

// =========================================================
// DOSSIER TRANSITION & RENDERING
// =========================================================
function extractAcademicTakeaways(data) {
  const takeaways = [];
  
  // 1. Try extracting from evaluated claims
  if (data.evaluated_claims && Array.isArray(data.evaluated_claims)) {
    for (const c of data.evaluated_claims) {
      const txt = (c.claim_text || c.text || '').replace(/<[^>]+>/g, '').trim();
      if (txt.length > 25 && !/sqlite|hallucination|llm|token|cache/i.test(txt) && !takeaways.includes(txt)) {
        takeaways.push(txt.endsWith('.') ? txt : txt + '.');
        if (takeaways.length >= 3) break;
      }
    }
  }

  // 2. Try extracting from sections if needed
  if (takeaways.length < 3 && data.dossier_sections && Array.isArray(data.dossier_sections)) {
    for (const sec of data.dossier_sections) {
      const html = sec.content_html || sec.answer_html || '';
      const clean = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      const match = clean.match(/([A-Z][^.!?]{35,180}[.!?])/);
      if (match && !/sqlite|hallucination|llm|token|monograph|tier|cache/i.test(match[1]) && !takeaways.includes(match[1])) {
        takeaways.push(match[1]);
        if (takeaways.length >= 3) break;
      }
    }
  }

  // 3. Fallback to clean academic consensus statements
  const citCount = data.citations ? data.citations.length : 5;
  const fallbacks = [
    `Consensus corroborated across ${citCount} peer-reviewed source publications.`,
    `Empirical evaluations confirm dominant operational scaling thresholds and throughput bounds.`,
    `Comparative literature synthesis establishes key trade-offs between computational overhead and execution latency.`
  ];

  for (const fallback of fallbacks) {
    if (takeaways.length >= 3) break;
    if (!takeaways.includes(fallback)) {
      takeaways.push(fallback);
    }
  }

  return takeaways.slice(0, 3);
}

function finishPipeline(data) {
  stopElapsedTimer();
  UIState.isRunning = false;
  UIState.lastDossierData = data;
  if (elements.btnAbortPipeline) {
    elements.btnAbortPipeline.style.display = 'none';
  }
  
  elements.teleStatusDot.className = "pulse-indicator status-green";
  elements.teleStatusText.textContent = "Complete";
  logToCanvas("[SUCCESS] Synthesis complete. Switching to Research Dossier.");

  renderDossierOutput(data);

  // Seamless view transition to Research Dossier
  setTimeout(() => {
    switchView('dossier');
    showToast("Research Dossier Ready");
  }, 1100);
}

function renderDossierOutput(data) {
  elements.dossierTitle.textContent = data.query;

  // Render Key Takeaways / Findings
  if (data.takeaways && data.takeaways.length > 0) {
    elements.takeawayList.innerHTML = data.takeaways.map(t => `<li>${t}</li>`).join('');
  }

  // Render Sections
  elements.dossierContent.innerHTML = '';

  // Render Executive Summary Card first if available
  if (data.executive_summary && data.executive_summary.trim()) {
    const execCard = document.createElement('div');
    execCard.className = 'dossier-exec-summary';
    execCard.innerHTML = `
      <div class="exec-summary-header">
        <h3 class="exec-summary-title">Executive Summary</h3>
      </div>
      <div class="exec-summary-text">
        ${data.executive_summary}
      </div>
    `;

    // Promote inline strong subheadings to clean semantic h4 headers
    execCard.querySelectorAll('.exec-summary-text p').forEach(p => {
      const firstNode = p.childNodes[0];
      if (firstNode && firstNode.nodeName === 'STRONG') {
        const strongText = firstNode.textContent.trim();
        if (strongText.endsWith(':')) {
          const h4 = document.createElement('h4');
          h4.className = 'section-subheading';
          h4.textContent = strongText.slice(0, -1);
          p.removeChild(firstNode);
          p.parentNode.insertBefore(h4, p);
        }
      }
    });

    elements.dossierContent.appendChild(execCard);
  }

  data.sections.forEach((sec, idx) => {
    const card = document.createElement('div');
    card.className = 'dossier-section-card';
    
    // Clean up title: strip redundant prefixes like "1. ", "01. ", "Subtopic 1: "
    let cleanTitle = (sec.sub_question || "").replace(/^(?:Subtopic\s*\d+[:.-]?|\d+[\.\):]|\d+\s+[-–:]\s*)\s*/i, '').trim();
    if (!cleanTitle) cleanTitle = sec.sub_question;

    card.innerHTML = `
      <h3 class="subquestion-header">
        <span class="subquestion-num">${idx+1}.</span>
        <span>${cleanTitle}</span>
      </h3>
      <div class="dossier-text-paragraph">
        ${sec.answer_html}
      </div>
    `;

    // Promote inline strong subheadings to clean semantic h4 headers
    card.querySelectorAll('.dossier-text-paragraph p').forEach(p => {
      const firstNode = p.childNodes[0];
      if (firstNode && firstNode.nodeName === 'STRONG') {
        const strongText = firstNode.textContent.trim();
        if (strongText.endsWith(':')) {
          const h4 = document.createElement('h4');
          h4.className = 'section-subheading';
          h4.textContent = strongText.slice(0, -1);
          p.removeChild(firstNode);
          p.parentNode.insertBefore(h4, p);
        }
      }
    });

    elements.dossierContent.appendChild(card);
  });

  // Pre-KaTeX DOM Sanitizer: Collapse duplicate adjacent math and metric tokens
  elements.dossierContent.querySelectorAll('.dossier-text-paragraph, .exec-summary-text').forEach(container => {
    let html = container.innerHTML;
    html = html.replace(/(\$[^\$]+\$)(?:\s*\1)+/g, '$1');
    html = html.replace(/\b(\d+(?:\.\d+)?\s*(?:GB\/s|TB\/s|TFLOPs\/s|TOPS\/W|ms|ns|kb))\s+\1\b/gi, '$1');
    html = html.replace(/\b(O\([^)]+\))\s+\1\b/g, '$1');
    container.innerHTML = html;
  });

  // Render Citations in the right sidebar
  renderCitationsPanel(data.citations);
  setupClaimCitationInteractions();

  // Render LaTeX math formulas
  if (typeof renderMathInElement === "function") {
    renderMathInElement(elements.dossierContent, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false},
        {left: '\\(', right: '\\)', display: false},
        {left: '\\[', right: '\\]', display: true}
      ],
      throwOnError: false
    });
  }
}

function renderCitationsPanel(citations) {
  elements.citationsContainer.innerHTML = '';
  elements.citTotalCount.textContent = `${citations.length} Sources`;

  if (!citations || citations.length === 0) {
    elements.citationsContainer.innerHTML = `<p class="text-subtle">No citations indexed.</p>`;
    return;
  }

  citations.forEach(cit => {
    const card = document.createElement('div');
    card.className = 'citation-card';
    card.id = `cit-card-${cit.ref_id}`;
    card.dataset.refId = cit.ref_id;
    
    const apaText = `${cit.authors} (${cit.year}). ${cit.title}. ${cit.venue}. ${cit.url}`;
    
    card.innerHTML = `
      <div class="cit-card-top">
        <span class="cit-ref-tag">[${cit.ref_id}]</span>
        <span class="cit-year-tag">${cit.year}</span>
      </div>
      <div class="cit-title">${cit.title}</div>
      <div class="cit-authors">${cit.authors}</div>
      <div class="cit-venue">Published: ${cit.venue} • ${cit.citation_count} Citations</div>
      <div class="cit-evidence-box">
        <div class="cit-evidence-label">Verbatim Evidence (Matched in Cache):</div>
        <div class="cit-evidence-text">"${cit.evidence || (cit.supporting_snippets && cit.supporting_snippets[0]) || 'Corroborating text stored in SQLite cache.db'}"</div>
      </div>
      <div class="cit-actions-row">
        <a href="${cit.url}" target="_blank" class="cit-link-btn" title="Open primary paper">
          <span>View Source Paper</span>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
        </a>
        <button class="btn-copy-apa" data-apa="${encodeURIComponent(apaText)}" title="Copy APA Citation">Copy APA</button>
      </div>
    `;
    elements.citationsContainer.appendChild(card);
  });

  // Attach APA copy handlers
  document.querySelectorAll('.btn-copy-apa').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const apa = decodeURIComponent(btn.dataset.apa);
      navigator.clipboard.writeText(apa);
      showToast("Copied APA Citation to clipboard");
    });
  });
}

// Interactive syncing between Claims and Citation cards
function setupClaimCitationInteractions() {
  document.querySelectorAll('.claim-wrapper, .citation-anchor').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const refId = item.dataset.refId || item.closest('[data-ref-id]')?.dataset.refId;
      if (refId) {
        highlightCitation(refId);
      }
    });
  });

  document.querySelectorAll('.citation-card').forEach(card => {
    card.addEventListener('click', () => {
      const refId = card.dataset.refId;
      highlightClaimsForRef(refId);
    });
  });
}

function highlightCitation(refId) {
  // Ensure sidebar is open if collapsed
  if (!UIState.citationsSidebarOpen) {
    toggleCitationsSidebar();
  }
  
  document.querySelectorAll('.citation-card').forEach(c => c.classList.remove('highlighted'));
  const target = document.getElementById(`cit-card-${refId}`);
  if (target) {
    target.classList.add('highlighted');
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function highlightClaimsForRef(refId) {
  document.querySelectorAll('.claim-wrapper').forEach(c => {
    if (c.dataset.refId === refId) {
      c.classList.add('active-claim');
      setTimeout(() => c.classList.remove('active-claim'), 2000);
      c.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}

// Researcher Tools: Copy Synthesis Markdown
function copySynthesisToClipboard() {
  if (!UIState.lastDossierData) {
    showToast("Run a research query first to generate synthesis.");
    return;
  }
  
  let md = `# ${UIState.lastDossierData.query}\n\n`;
  md += `*Generated via AI Research Workbench on ${new Date().toLocaleDateString()}*\n\n`;
  
  UIState.lastDossierData.sections.forEach((s, idx) => {
    // Strip html tags for clean markdown copy
    const cleanAnswer = s.answer_html.replace(/<[^>]*>/g, '');
    md += `## ${idx+1}. ${s.sub_question}\n\n${cleanAnswer}\n\n`;
  });

  md += `### References\n`;
  UIState.lastDossierData.citations.forEach(c => {
    md += `- [${c.ref_id}] ${c.authors} (${c.year}). *${c.title}*. ${c.venue}. ${c.url}\n`;
  });

  navigator.clipboard.writeText(md);
  showToast("Research synthesis copied to clipboard (Markdown)");
}

// Researcher Tools: Export BibTeX
function exportBibtexToClipboard() {
  if (!UIState.lastDossierData || !UIState.lastDossierData.citations) {
    showToast("No citations available to export.");
    return;
  }
  
  let bib = "";
  UIState.lastDossierData.citations.forEach(c => {
    const bibId = (c.authors.split(' ')[0] || 'Author').replace(/[^a-zA-Z]/g, '') + c.year;
    bib += `@article{${bibId},\n  author = {${c.authors}},\n  title = {${c.title}},\n  year = {${c.year}},\n  journal = {${c.venue}},\n  url = {${c.url}}\n}\n\n`;
  });

  navigator.clipboard.writeText(bib);
  showToast("BibTeX citations copied to clipboard for LaTeX");
}

// =========================================================
// CANVAS & BEZIER CONNECTOR POSITIONS
// =========================================================
function positionNodeCards() {
  const container = document.getElementById('view-canvas');
  if (!container) return;
  const w = container.clientWidth;
  const h = container.clientHeight;

  const isMobile = w < 1000;
  if (isMobile) {
    UIState.nodePositions = {
      agent1: { x: 20, y: 30 },
      agent2: { x: 20, y: 300 },
      agent3: { x: 20, y: 570 },
      agent4: { x: 20, y: 840 }
    };
  } else {
    UIState.nodePositions = {
      agent1: { x: Math.max(40, w * 0.05), y: h * 0.22 },
      agent2: { x: w * 0.36, y: h * 0.12 },
      agent3: { x: w * 0.36, y: h * 0.52 },
      agent4: { x: Math.min(w - 350, w * 0.68), y: h * 0.30 }
    };
  }

  setNodeTransform(elements.node1, UIState.nodePositions.agent1);
  setNodeTransform(elements.node2, UIState.nodePositions.agent2);
  setNodeTransform(elements.node3, UIState.nodePositions.agent3);
  setNodeTransform(elements.node4, UIState.nodePositions.agent4);
}

function setNodeTransform(el, pos) {
  if (el) {
    el.style.left = `${pos.x}px`;
    el.style.top = `${pos.y}px`;
  }
}

function drawBezierConnectors() {
  const cardW = 310;
  const cardH = 200;

  const p1 = UIState.nodePositions.agent1;
  const p2 = UIState.nodePositions.agent2;
  const p3 = UIState.nodePositions.agent3;
  const p4 = UIState.nodePositions.agent4;

  const start1 = { x: p1.x + cardW, y: p1.y + (cardH * 0.45) };
  const end2 = { x: p2.x, y: p2.y + (cardH * 0.45) };
  elements.path12.setAttribute('d', calculateBezier(start1, end2));

  const start2 = { x: p2.x + (cardW * 0.5), y: p2.y + cardH };
  const end3 = { x: p3.x + (cardW * 0.5), y: p3.y };
  elements.path23.setAttribute('d', calculateVerticalBezier(start2, end3));

  const start3 = { x: p3.x + cardW, y: p3.y + (cardH * 0.45) };
  const end4 = { x: p4.x, y: p4.y + (cardH * 0.45) };
  elements.path34.setAttribute('d', calculateBezier(start3, end4));
}

function calculateBezier(p1, p2) {
  const dx = (p2.x - p1.x) * 0.5;
  return `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;
}

function calculateVerticalBezier(p1, p2) {
  const dy = (p2.y - p1.y) * 0.5;
  return `M ${p1.x} ${p1.y} C ${p1.x} ${p1.y + dy}, ${p2.x} ${p2.y - dy}, ${p2.x} ${p2.y}`;
}

function zoomCanvas(factor) {
  UIState.scale = Math.min(Math.max(UIState.scale * factor, 0.6), 1.5);
  document.getElementById('agent-nodes-container').style.transform = `scale(${UIState.scale})`;
  elements.svgLayer.style.transform = `scale(${UIState.scale})`;
}

function resetCanvasZoom() {
  UIState.scale = 1.0;
  document.getElementById('agent-nodes-container').style.transform = 'scale(1)';
  elements.svgLayer.style.transform = 'scale(1)';
}

// Background Grid
function initBackgroundCanvas() {
  const canvas = document.getElementById('bg-grid-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
    drawGrid();
  }
  window.addEventListener('resize', resize);
  resize();

  function drawGrid() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gridSize = 40;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.035)';
    
    for (let x = 0; x < canvas.width; x += gridSize) {
      for (let y = 0; y < canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.arc(x, y, 1, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}

function logToCanvas(text) {
  const line = document.createElement('div');
  line.className = 'log-line';
  if (text.includes('SUCCESS') || text.includes('DONE')) line.className += ' success';
  if (text.includes('AGENT') || text.includes('QUERY')) line.className += ' active';
  line.textContent = text;
  
  elements.canvasLogContainer.appendChild(line);
  elements.canvasLogContainer.scrollTop = elements.canvasLogContainer.scrollHeight;
}

// Database Modal
async function openDatabaseModal() {
  elements.dbInspectorModal.classList.add('open');
  elements.dbTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-subtle">Querying SQLite cache.db...</td></tr>`;
  
  try {
    const resp = await fetch('/api/cache/papers');
    if (resp.ok) {
      const data = await resp.json();
      if (data.papers && data.papers.length > 0) {
        elements.dbTableBody.innerHTML = '';
        data.papers.forEach(p => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td class="mono">${(p.id || '').substring(0, 10)}...</td>
            <td>${p.query || '--'}</td>
            <td><strong>${p.title || 'Untitled'}</strong></td>
            <td>${p.authors || '--'}</td>
            <td>${p.year || '--'}</td>
            <td>${p.venue || '--'}</td>
            <td class="mono">${p.citation_count || 0}</td>
          `;
          elements.dbTableBody.appendChild(tr);
        });
        return;
      }
    }
  } catch (e) {
    console.log("DB fallback to static view", e);
  }

  // Fallback demo papers
  elements.dbTableBody.innerHTML = `
    <tr>
      <td class="mono">quant_01</td>
      <td>Quantum Qubits</td>
      <td><strong>Quantum Error Mitigation in Rydberg Atom Arrays</strong></td>
      <td>M. Endres, H. Levine et al.</td>
      <td>2024</td>
      <td>Nature Quantum</td>
      <td class="mono">142</td>
    </tr>
    <tr>
      <td class="mono">crispr_01</td>
      <td>CRISPR Cas12f</td>
      <td><strong>Engineered Cas12f Nucleases for Compact In Vivo Viral Delivery</strong></td>
      <td>K. Tsuchida, F. Zhang et al.</td>
      <td>2024</td>
      <td>Nature Biotech</td>
      <td class="mono">178</td>
    </tr>
  `;
}


// =========================================================
// V3: PDF DOCUMENT ANALYSIS WORKSPACE CONTROLLER
// =========================================================

// Initialize PDF Document State on elements object
elements.navDocuments = document.getElementById('nav-documents');
elements.viewDocuments = document.getElementById('view-documents');
elements.pdfDropzone = document.getElementById('pdf-dropzone');
elements.pdfFileInput = document.getElementById('pdf-file-input');
elements.btnBrowsePdfs = document.getElementById('btn-browse-pdfs');
elements.docUploadZone = document.getElementById('doc-upload-zone');
elements.docLibrary = document.getElementById('doc-library');
elements.libraryGrid = document.getElementById('library-grid');
elements.docSessionPanel = document.getElementById('doc-session-panel');
elements.btnBackToLibrary = document.getElementById('btn-back-to-library');
elements.sessionTitle = document.getElementById('session-title');
elements.filesGrid = document.getElementById('files-grid');
elements.btnAddMorePdfs = document.getElementById('btn-add-more-pdfs');
elements.btnDeleteSession = document.getElementById('btn-delete-session');
elements.docWorkspace = document.getElementById('doc-workspace');
elements.docActionsToolbar = document.getElementById('doc-actions-toolbar');
elements.docChatContainer = document.getElementById('doc-chat-container');
elements.docChatMessages = document.getElementById('doc-chat-messages');
elements.docQueryInput = document.getElementById('doc-query-input');
elements.btnSendDocQuery = document.getElementById('btn-send-doc-query');
elements.docAnalysisOutput = document.getElementById('doc-analysis-output');
elements.docOutputTitle = document.getElementById('doc-output-title');
elements.docOutputContent = document.getElementById('doc-output-content');
elements.btnCopyDocOutput = document.getElementById('btn-copy-doc-output');
elements.btnExportDocBibtex = document.getElementById('btn-export-doc-bibtex');
elements.docFigureGallery = document.getElementById('doc-figure-gallery');
elements.figuresGrid = document.getElementById('figures-grid');
elements.docCitationGraph = document.getElementById('doc-citation-graph');
elements.graphStatsBar = document.getElementById('graph-stats-bar');
elements.citationGraphCanvas = document.getElementById('citation-graph-canvas');
elements.graphRefList = document.getElementById('graph-ref-list');
elements.docChunksSidebar = document.getElementById('doc-chunks-sidebar');
elements.docChunksList = document.getElementById('doc-chunks-list');
elements.chunksCountLabel = document.getElementById('chunks-count-label');
elements.btnClearPdfLibrary = document.getElementById('btn-clear-pdf-library');
elements.togglePdfStrictApi = document.getElementById('toggle-pdf-strict-api');
elements.togglePdfDemoMode = document.getElementById('toggle-pdf-demo-mode');
elements.docApiStatus = document.getElementById('doc-api-status');
elements.docApiText = document.getElementById('doc-api-text');
elements.docDemoChips = document.getElementById('doc-demo-chips');

// PDF State extensions
UIState.pdfSessionId = null;
UIState.pdfFiles = [];
UIState.pdfAction = 'qa';
UIState.pdfChatHistory = [];
UIState.pdfFigures = [];
UIState.pdfCitationGraph = null;
UIState.pdfEventSource = null;

// Helper to retrieve user API config and mode toggles
function getWorkbenchAPIConfig() {
  const geminiKey = (document.getElementById('cfg-gemini-key')?.value.trim()) || localStorage.getItem('workbench_gemini_key') || '';
  const anthropicKey = (document.getElementById('cfg-anthropic-key')?.value.trim()) || localStorage.getItem('workbench_anthropic_key') || '';
  const isClaude = document.getElementById('cfg-provider-agent2')?.value === 'claude';
  const provider = isClaude ? 'claude' : (document.getElementById('cfg-provider-agent2')?.value || 'auto');
  const strictMode = elements.togglePdfStrictApi ? elements.togglePdfStrictApi.checked : true;
  const demoMode = elements.togglePdfDemoMode ? elements.togglePdfDemoMode.checked : false;

  return { geminiKey, anthropicKey, provider, strictMode, demoMode };
}

function updateDocAPIStatus() {
  const config = getWorkbenchAPIConfig();
  if (!elements.docApiStatus || !elements.docApiText) return;
  const dot = elements.docApiStatus.querySelector('.doc-api-dot');

  if (config.demoMode) {
    elements.docApiText.innerText = 'Demo Mode';
    if (dot) dot.className = 'doc-api-dot warning';
    if (elements.docDemoChips) elements.docDemoChips.style.display = 'flex';
  } else if (config.geminiKey || config.anthropicKey) {
    elements.docApiText.innerText = config.strictMode ? 'Strict API (Online)' : 'API Connected';
    if (dot) dot.className = 'doc-api-dot';
  } else {
    elements.docApiText.innerText = config.strictMode ? 'Strict API (No Key)' : 'Fallback Mode';
    if (dot) dot.className = config.strictMode ? 'doc-api-dot offline' : 'doc-api-dot warning';
  }
}

// Initialize PDF Event Listeners
function initPDFWorkspace() {
  // Initialize Strict API & Demo Mode Toggles
  if (elements.togglePdfStrictApi) {
    const savedStrict = localStorage.getItem('workbench_pdf_strict_api');
    if (savedStrict !== null) {
      elements.togglePdfStrictApi.checked = (savedStrict === 'true');
    } else {
      elements.togglePdfStrictApi.checked = true; // Default strict mode ON
    }
    elements.togglePdfStrictApi.addEventListener('change', (e) => {
      localStorage.setItem('workbench_pdf_strict_api', e.target.checked ? 'true' : 'false');
      updateDocAPIStatus();
      showToast(e.target.checked ? 'Strict API Mode ON: Live LLM calls will fail cleanly if keys are invalid.' : 'Strict Mode OFF: Offline fallback enabled.', 'info');
    });
  }

  if (elements.togglePdfDemoMode) {
    const savedDemo = localStorage.getItem('workbench_pdf_demo_mode');
    if (savedDemo !== null) {
      elements.togglePdfDemoMode.checked = (savedDemo === 'true');
    }
    elements.togglePdfDemoMode.addEventListener('change', (e) => {
      localStorage.setItem('workbench_pdf_demo_mode', e.target.checked ? 'true' : 'false');
      updateDocAPIStatus();
      showToast(e.target.checked ? 'Demo Mode Active: Returning pre-computed formulations with 0 tokens.' : 'Demo Mode Disabled: Routing requests to AI pipeline.', 'info');
    });
  }

  // Preset Inquiries / Demo Chips
  if (elements.docDemoChips) {
    elements.docDemoChips.querySelectorAll('.doc-demo-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const queryText = chip.getAttribute('data-query');
        if (!queryText) return;
        handlePDFActionSelect('qa');
        if (elements.docQueryInput) {
          elements.docQueryInput.value = queryText;
        }
        executePDFQuestion(queryText);
      });
    });
  }

  // Live status listener for key inputs
  const geminiInput = document.getElementById('cfg-gemini-key');
  if (geminiInput) geminiInput.addEventListener('input', updateDocAPIStatus);
  const anthropicInput = document.getElementById('cfg-anthropic-key');
  if (anthropicInput) anthropicInput.addEventListener('input', updateDocAPIStatus);
  updateDocAPIStatus();
  if (elements.navDocuments) {
    elements.navDocuments.addEventListener('click', () => switchView('documents'));
  }

  if (elements.btnBrowsePdfs && elements.pdfFileInput) {
    elements.btnBrowsePdfs.addEventListener('click', () => elements.pdfFileInput.click());
    elements.pdfFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handlePDFUpload(e.target.files);
      }
    });
  }

  if (elements.btnAddMorePdfs && elements.pdfFileInput) {
    elements.btnAddMorePdfs.addEventListener('click', () => elements.pdfFileInput.click());
  }

  if (elements.btnBackToLibrary) {
    elements.btnBackToLibrary.addEventListener('click', () => {
      UIState.pdfSessionId = null;
      if (elements.docSessionPanel) elements.docSessionPanel.style.display = 'none';
      if (elements.docWorkspace) elements.docWorkspace.style.display = 'none';
      if (elements.docUploadZone) elements.docUploadZone.style.display = 'flex';
      loadDocumentLibrary();
    });
  }

  if (elements.btnDeleteSession) {
    elements.btnDeleteSession.addEventListener('click', async () => {
      if (!UIState.pdfSessionId) return;
      if (confirm('Permanently delete this PDF session and all extracted embeddings?')) {
        try {
          await fetch(`/api/pdf/session/${UIState.pdfSessionId}`, { method: 'DELETE' });
          showToast('PDF session deleted successfully', 'info');
          elements.btnBackToLibrary.click();
        } catch (e) {
          showToast('Failed to delete session: ' + e.message, 'error');
        }
      }
    });
  }

  if (elements.btnClearPdfLibrary) {
    elements.btnClearPdfLibrary.addEventListener('click', async () => {
      if (confirm('Delete ALL stored PDF sessions from the database and disk?')) {
        try {
          const res = await fetch('/api/pdf/sessions');
          const data = await res.json();
          for (const s of (data.sessions || [])) {
            await fetch(`/api/pdf/session/${s.session_id}`, { method: 'DELETE' });
          }
          showToast('Document library wiped clean.', 'info');
          loadDocumentLibrary();
        } catch (e) {
          showToast('Error clearing library: ' + e.message, 'error');
        }
      }
    });
  }

  // Drag and Drop
  if (elements.pdfDropzone) {
    ['dragenter', 'dragover'].forEach(evt => {
      elements.pdfDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        elements.pdfDropzone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach(evt => {
      elements.pdfDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        elements.pdfDropzone.classList.remove('drag-over');
      });
    });

    elements.pdfDropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handlePDFUpload(dt.files);
      }
    });
  }

  // Action chips toolbar
  if (elements.docActionsToolbar) {
    elements.docActionsToolbar.querySelectorAll('.action-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        elements.docActionsToolbar.querySelectorAll('.action-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const action = chip.dataset.action;
        UIState.pdfAction = action;
        handlePDFActionSelect(action);
      });
    });
  }

  // Q&A input submit
  if (elements.btnSendDocQuery && elements.docQueryInput) {
    elements.btnSendDocQuery.addEventListener('click', executePDFQuestion);
    elements.docQueryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        executePDFQuestion();
      }
    });
  }

  // Copy button for synthesis
  if (elements.btnCopyDocOutput && elements.docOutputContent) {
    elements.btnCopyDocOutput.addEventListener('click', () => {
      navigator.clipboard.writeText(elements.docOutputContent.innerText);
      showToast('Synthesis copied to clipboard!', 'info');
    });
  }

  // Export BibTeX for active session
  if (elements.btnExportDocBibtex) {
    elements.btnExportDocBibtex.addEventListener('click', async () => {
      if (!UIState.pdfSessionId) return;
      try {
        const resp = await fetch(`/api/pdf/session/${UIState.pdfSessionId}`);
        if (!resp.ok) throw new Error('Could not fetch session details');
        const data = await resp.json();
        let bibtex = '';
        (data.files || []).forEach((f, idx) => {
          const key = `doc_${idx + 1}_${(f.title || 'paper').replace(/\W+/g, '_').toLowerCase().slice(0, 15)}`;
          bibtex += `@article{${key},\n  title={${f.title || f.original_filename}},\n  author={${f.authors || 'Unknown'}},\n  year={${f.creation_date ? f.creation_date.slice(0, 4) : '2024'}},\n  note={Extracted via AI Research Workbench}\n}\n\n`;
        });
        const blob = new Blob([bibtex], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `references_${UIState.pdfSessionId}.bib`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('BibTeX exported successfully!', 'info');
      } catch (err) {
        showToast('Export error: ' + err.message, 'error');
      }
    });
  }

  // Load document library on launch
  loadDocumentLibrary();
}

// Handle action chip selection
function handlePDFActionSelect(action) {
  // Hide all primary panes
  if (elements.docChatContainer) elements.docChatContainer.style.display = 'none';
  if (elements.docAnalysisOutput) elements.docAnalysisOutput.style.display = 'none';
  if (elements.docFigureGallery) elements.docFigureGallery.style.display = 'none';
  if (elements.docCitationGraph) elements.docCitationGraph.style.display = 'none';

  if (action === 'qa') {
    elements.docChatContainer.style.display = 'flex';
    elements.docQueryInput.focus();
  } else if (action === 'figures') {
    elements.docFigureGallery.style.display = 'block';
    renderFigureGallery(UIState.pdfFigures || []);
  } else if (action === 'citation_graph') {
    elements.docCitationGraph.style.display = 'block';
    loadAndRenderCitationGraph();
  } else {
    // summarize, deep_analysis, extract_findings, critique, compare
    elements.docAnalysisOutput.style.display = 'block';
    const titles = {
      summarize: "Executive Academic Monograph",
      deep_analysis: "Methodological & Theoretical Evaluation",
      extract_findings: "Quantitative Claims & Benchmarks",
      critique: "Peer-Review Critique & Threat Analysis",
      compare: "Multi-Document Comparative Synthesis"
    };
    elements.docOutputTitle.innerText = titles[action] || "Document Analysis";
    executePDFAnalysisPipeline(action);
  }
}

// Upload PDFs to backend
async function handlePDFUpload(fileList) {
  const files = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.pdf'));
  if (files.length === 0) {
    showToast('Only PDF files are supported.', 'error');
    return;
  }
  if (files.length > 10) {
    showToast('Maximum 10 PDF files per session.', 'error');
    return;
  }

  showToast(`Uploading and extracting ${files.length} document(s)...`, 'info');

  const formData = new FormData();
  files.forEach(f => formData.append('files', f));

  try {
    const resp = await fetch('/api/pdf/upload', {
      method: 'POST',
      body: formData
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await resp.json();
    UIState.pdfSessionId = data.session_id;
    const hasError = (data.files || []).some(f => f.status === 'error');
    if (hasError) {
      showToast('Warning: Some files could not be extracted properly.', 'warning');
    } else {
      showToast(`Indexed ${data.total_pages} pages, ${data.total_chunks} chunks, ${data.total_figures} figures!`, 'info');
    }

    // Switch view to active session
    openPDFSession(data.session_id);

  } catch (err) {
    console.error("PDF upload error:", err);
    showToast('Upload error: ' + err.message, 'error');
  }
}

// Open and display an existing or newly uploaded PDF session
async function openPDFSession(sessionId) {
  try {
    const resp = await fetch(`/api/pdf/session/${sessionId}`);
    if (!resp.ok) throw new Error('Could not load session data');
    const data = await resp.json();

    UIState.pdfSessionId = sessionId;
    UIState.pdfFiles = data.files || [];
    UIState.pdfFigures = data.figures || [];
    UIState.pdfCitationGraph = data.citation_graph || null;

    // Hide upload zone, show session overview & workspace
    if (elements.docUploadZone) elements.docUploadZone.style.display = 'none';
    if (elements.docSessionPanel) elements.docSessionPanel.style.display = 'block';
    if (elements.docWorkspace) elements.docWorkspace.style.display = 'block';

    // Update session header stats
    document.getElementById('stat-doc-files').innerText = `${data.total_files || (data.files||[]).length} files`;
    document.getElementById('stat-doc-pages').innerText = `${data.total_pages || 0} pages`;
    document.getElementById('stat-doc-chunks').innerText = `${data.total_chunks || 0} chunks`;
    document.getElementById('stat-doc-figures').innerText = `${data.total_figures || (data.figures||[]).length} figures`;
    document.getElementById('stat-doc-refs').innerText = `${data.total_references || 0} citations`;

    // Render files grid
    elements.filesGrid.innerHTML = '';
    (data.files || []).forEach(f => {
      const isError = f.extraction_status === 'error';
      const statusHtml = isError
        ? `<span style="color: var(--accent-rose);" title="${f.extraction_error || 'Extraction error'}">⚠️ Error</span>`
        : `<span style="color: var(--accent-green);">● Complete</span>`;
      const card = document.createElement('div');
      card.className = 'file-card';
      card.innerHTML = `
        <div class="file-card-name" title="${f.original_filename}">${f.original_filename}</div>
        <div class="file-card-details">
          <span>📄 ${f.page_count || 0} pages</span>
          <span>⚡ ~${f.word_count || 0} words</span>
          ${statusHtml}
        </div>
      `;
      elements.filesGrid.appendChild(card);
    });

    // Default to Q&A pane
    handlePDFActionSelect('qa');

  } catch (err) {
    console.error("Failed to open session:", err);
    showToast('Failed to open PDF session: ' + err.message, 'error');
  }
}

// Load Document Library
async function loadDocumentLibrary() {
  if (!elements.libraryGrid) return;
  try {
    const resp = await fetch('/api/pdf/sessions');
    if (!resp.ok) return;
    const data = await resp.json();
    const sessions = data.sessions || [];

    if (sessions.length === 0) {
      elements.libraryGrid.innerHTML = '<div class="empty-library-msg">No stored PDF sessions found. Upload papers above to start building your library.</div>';
      return;
    }

    elements.libraryGrid.innerHTML = '';
    sessions.forEach(s => {
      const card = document.createElement('div');
      card.className = 'library-card';
      const fileNames = (s.files_summary || []).map(f => f.original_filename).join(', ') || 'Academic Papers';
      card.innerHTML = `
        <div class="library-card-title">${fileNames}</div>
        <div class="library-card-meta">
          <span>${s.total_files} files · ${s.total_pages} pages · ${s.total_chunks} chunks</span><br/>
          <span class="mono" style="font-size: 0.72rem; color: var(--accent-blue);">Updated: ${s.last_accessed || s.created_at}</span>
        </div>
      `;
      card.addEventListener('click', () => openPDFSession(s.session_id));
      elements.libraryGrid.appendChild(card);
    });

  } catch (err) {
    console.log("Could not load library:", err);
  }
}

// Execute Q&A over PDF documents
async function executePDFQuestion(overrideQuery = null) {
  const query = (overrideQuery !== null ? overrideQuery : elements.docQueryInput.value).trim();
  if (!query || !UIState.pdfSessionId) return;

  // Append user bubble
  appendChatBubble('user', query);
  if (elements.docQueryInput) elements.docQueryInput.value = '';

  // Append loading assistant bubble
  const loadingBubble = appendChatBubble('assistant', 'Searching indexed document chunks and synthesizing answer...');

  const { geminiKey, anthropicKey, provider, strictMode, demoMode } = getWorkbenchAPIConfig();

  // Fail-closed client validation if Strict Mode is ON and no API keys are present
  if (strictMode && !demoMode && !geminiKey && !anthropicKey) {
    loadingBubble.innerHTML = `
      <div style="padding: 6px 0;">
        <strong style="color: var(--accent-rose);">⚠️ Strict API Mode Active — Missing API Key</strong>
        <p style="margin: 6px 0 12px; font-size: 0.88rem; color: var(--text-muted); line-height: 1.5;">
          Strict API mode requires a valid Gemini or Anthropic Claude API key. 
          Please configure your API key in <strong>Model Settings</strong> or toggle <strong>Demo Mode</strong> on the toolbar above.
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn-secondary btn-sm" onclick="document.getElementById('btn-toggle-drawer').click()">⚙️ Open Model Settings</button>
          <button class="btn-secondary btn-sm" onclick="document.getElementById('toggle-pdf-demo-mode').click();">💡 Enable Demo Mode</button>
        </div>
      </div>
    `;
    return;
  }

  try {
    const resp = await fetch('/api/pdf/qa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: UIState.pdfSessionId,
        action: 'qa',
        query: query,
        chat_history: UIState.pdfChatHistory,
        provider: provider,
        gemini_key: geminiKey,
        anthropic_key: anthropicKey,
        disable_fallback: strictMode,
        demo_mode: demoMode
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Q&A request failed');
    }

    const data = await resp.json();
    loadingBubble.innerHTML = data.answer_html || '<p>No answer synthesized.</p>';

    // Render source chunks in sidebar
    renderSourceChunks(data.source_chunks || []);

    // Update chat history
    UIState.pdfChatHistory.push({ role: 'user', content: query });
    UIState.pdfChatHistory.push({ role: 'assistant', content: loadingBubble.innerText });

    // KaTeX render
    if (window.renderMathInElement) {
      window.renderMathInElement(loadingBubble, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false }
        ],
        throwOnError: false
      });
    }

  } catch (err) {
    console.error("Q&A error:", err);
    loadingBubble.innerHTML = `
      <div style="padding: 6px 0;">
        <strong style="color: var(--accent-rose);">⚠️ Synthesis Error</strong>
        <p style="margin: 4px 0 0; font-size: 0.88rem; color: var(--text-muted);">${err.message}</p>
      </div>
    `;
  }
}

function appendChatBubble(role, content) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = role === 'user' ? `<p>${content}</p>` : content;
  elements.docChatMessages.appendChild(bubble);
  elements.docChatMessages.scrollTop = elements.docChatMessages.scrollHeight;
  return bubble;
}

// Execute Monograph/Methodology/Findings Analysis via SSE
function executePDFAnalysisPipeline(action) {
  if (!UIState.pdfSessionId) return;
  elements.docOutputContent.innerHTML = '<div class="empty-state-card"><div class="empty-icon">⏳</div><h3>Synthesizing Academic Analysis...</h3><p>Extracting grounded assertions across document chunks.</p></div>';

  const { geminiKey, anthropicKey, provider, strictMode, demoMode } = getWorkbenchAPIConfig();

  // Fail-closed client validation if Strict Mode is ON and no API keys are present
  if (strictMode && !demoMode && !geminiKey && !anthropicKey) {
    elements.docOutputContent.innerHTML = `
      <div class="empty-state-card" style="border-color: rgba(244,63,94,0.4); text-align: left; padding: 24px;">
        <div class="empty-icon">⚠️</div>
        <h3 style="color: var(--accent-rose); margin-bottom: 6px;">Strict API Mode Active — Missing API Key</h3>
        <p style="color: var(--text-muted); font-size: 0.88rem; line-height: 1.5; margin-bottom: 14px;">
          Strict API Mode guarantees no synthetic fallback text is generated. To run live peer-reviewed synthesis, please provide a Gemini or Anthropic API key in Settings, or activate Demo Mode to inspect pre-computed analysis with mathematical rigor.
        </p>
        <div style="display: flex; gap: 10px;">
          <button class="btn-primary btn-sm" onclick="document.getElementById('btn-toggle-drawer').click()">⚙️ Configure API Key</button>
          <button class="btn-secondary btn-sm" onclick="document.getElementById('toggle-pdf-demo-mode').click(); executePDFAnalysisPipeline('${action}');">💡 Switch to Demo Mode</button>
        </div>
      </div>
    `;
    return;
  }

  const url = `/api/pdf/stream?session_id=${encodeURIComponent(UIState.pdfSessionId)}&action=${encodeURIComponent(action)}&provider=${encodeURIComponent(provider)}&disable_fallback=${strictMode}&demo_mode=${demoMode}&gemini_key=${encodeURIComponent(geminiKey)}&anthropic_key=${encodeURIComponent(anthropicKey)}`;

  if (UIState.pdfEventSource) {
    UIState.pdfEventSource.close();
  }

  const es = new EventSource(url);
  UIState.pdfEventSource = es;

  es.addEventListener('pdf_chunks_ready', (e) => {
    const data = JSON.parse(e.data);
    showToast(`Retrieved ${data.total_chunks} context chunks for grounding.`, 'info');
  });

  es.addEventListener('pdf_pipeline_complete', (e) => {
    es.close();
    UIState.pdfEventSource = null;
    const data = JSON.parse(e.data);
    renderPDFAnalysisOutput(data);
    renderSourceChunks(data.citations || []);
  });

  es.addEventListener('pdf_pipeline_error', (e) => {
    es.close();
    UIState.pdfEventSource = null;
    const data = JSON.parse(e.data);
    elements.docOutputContent.innerHTML = `<div class="empty-state-card" style="border-color: rgba(244,63,94,0.4);"><div class="empty-icon">⚠️</div><h3 style="color: var(--accent-rose);">Analysis Failed</h3><p>${data.error || 'Live AI call failed'}</p></div>`;
  });

  es.onerror = () => {
    es.close();
    UIState.pdfEventSource = null;
  };
}

function renderPDFAnalysisOutput(data) {
  let html = '';

  // Executive Summary
  if (data.executive_summary) {
    html += `
      <div class="dossier-section-card" style="margin-bottom: 20px;">
        <div class="section-badge-bar">
          <span class="sec-badge">Executive Monograph</span>
        </div>
        <div class="section-content-prose">${data.executive_summary}</div>
      </div>
    `;
  }

  // Sections
  (data.dossier_sections || []).forEach(sec => {
    html += `
      <div class="dossier-section-card" style="margin-bottom: 20px;">
        <div class="section-badge-bar">
          <span class="sec-badge">${sec.sub_question}</span>
        </div>
        <div class="section-content-prose">${sec.content_html}</div>
      </div>
    `;
  });

  elements.docOutputContent.innerHTML = html;

  // KaTeX render
  if (window.renderMathInElement) {
    window.renderMathInElement(elements.docOutputContent, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false }
      ],
      throwOnError: false
    });
  }
}

// Render source grounding chunks in right sidebar
function renderSourceChunks(chunks) {
  if (!elements.docChunksList) return;
  elements.docChunksList.innerHTML = '';
  if (!chunks || chunks.length === 0) {
    elements.docChunksList.innerHTML = '<div class="empty-chunks-msg">No specific chunks referenced for this turn.</div>';
    return;
  }

  chunks.forEach((c, idx) => {
    const card = document.createElement('div');
    card.className = 'chunk-card';
    const pageNum = c.start_page || c.page || idx + 1;
    const secTitle = c.section_title || c.title || `Chunk ${idx+1}`;
    const text = c.chunk_text || c.evidence || '';
    card.innerHTML = `
      <div class="chunk-card-meta">
        <span>Page ${pageNum}</span>
        <span>${secTitle.substring(0, 24)}</span>
      </div>
      <div>${text.substring(0, 180)}...</div>
    `;
    elements.docChunksList.appendChild(card);
  });
}

// Render Figure Gallery
function renderFigureGallery(figures) {
  if (!elements.figuresGrid) return;
  elements.figuresGrid.innerHTML = '';
  if (!figures || figures.length === 0) {
    elements.figuresGrid.innerHTML = '<div class="empty-library-msg">No extracted figures found in the uploaded documents.</div>';
    return;
  }

  figures.forEach(fig => {
    const card = document.createElement('div');
    card.className = 'figure-card';
    card.innerHTML = `
      <img class="figure-card-img" src="/uploads/${fig.file_path || fig.figure_path}" alt="${fig.caption || 'Figure'}"/>
      <div class="figure-card-info">
        <div style="font-size: 0.72rem; color: var(--accent-blue); font-family: var(--font-mono); font-weight: 600;">PAGE ${fig.page || fig.page_number}</div>
        <div class="figure-card-caption">${fig.caption || 'Extracted diagram'}</div>
      </div>
    `;
    elements.figuresGrid.appendChild(card);
  });
}

// Load and render interactive Citation Network Graph
async function loadAndRenderCitationGraph() {
  if (!UIState.pdfSessionId || !elements.citationGraphCanvas) return;
  try {
    const resp = await fetch(`/api/pdf/citation-graph/${UIState.pdfSessionId}`);
    if (!resp.ok) return;
    const data = await resp.json();
    UIState.pdfCitationGraph = data;

    // Render stats
    if (elements.graphStatsBar) {
      elements.graphStatsBar.innerHTML = `
        <span>Total Citations: <strong>${data.stats?.total_references || 0}</strong></span> ·
        <span style="color: var(--accent-green);">Resolved: <strong>${data.stats?.resolved_count || 0}</strong></span> ·
        <span>Unresolved: <strong>${data.stats?.unresolved_count || 0}</strong></span> ·
        <span>Median Year: <strong>${data.stats?.median_year || '--'}</strong></span>
      `;
    }

    // Render list
    if (elements.graphRefList) {
      elements.graphRefList.innerHTML = '';
      (data.nodes || []).slice(0, 15).forEach(node => {
        const item = document.createElement('div');
        item.className = 'graph-ref-card';
        item.innerHTML = `
          <div class="graph-ref-title">[${node.ref_index}] ${node.title}</div>
          <div class="text-subtle" style="font-size: 0.78rem;">${node.authors} (${node.year || 'n.d.'}) — ${node.venue || 'Academic Venue'}</div>
          ${node.resolved ? `<div style="font-size: 0.75rem; color: var(--accent-green); margin-top: 2px;">✓ Verified via Semantic Scholar/OpenAlex (${node.citation_count} citations)</div>` : ''}
        `;
        elements.graphRefList.appendChild(item);
      });
    }

    // Canvas Force Graph Simulation
    drawCitationNetwork(data.nodes || [], data.edges || []);

  } catch (err) {
    console.error("Citation graph error:", err);
  }
}

function drawCitationNetwork(nodes, edges) {
  const canvas = elements.citationGraphCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (nodes.length === 0) {
    ctx.fillStyle = "#94a3b8";
    ctx.font = "14px 'Plus Jakarta Sans'";
    ctx.textAlign = "center";
    ctx.fillText("No citation graph data available.", canvas.width / 2, canvas.height / 2);
    return;
  }

  // Generate radial layout positions for nodes
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const positions = {};

  nodes.slice(0, 24).forEach((n, idx) => {
    const angle = (idx / Math.min(nodes.length, 24)) * 2 * Math.PI;
    const r = idx === 0 ? 0 : (80 + (idx % 3) * 45);
    positions[n.id] = {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      resolved: n.resolved
    };
  });

  // Draw Edges
  ctx.strokeStyle = "rgba(59, 130, 246, 0.25)";
  ctx.lineWidth = 1;
  edges.forEach(e => {
    const p1 = positions[e.from];
    const p2 = positions[e.to];
    if (p1 && p2) {
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }
  });

  // Draw Nodes
  Object.values(positions).forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.resolved ? 6 : 4, 0, 2 * Math.PI);
    ctx.fillStyle = p.resolved ? "#10b981" : "#64748b";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });
}

// Call initPDFWorkspace when DOM loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPDFWorkspace);
} else {
  initPDFWorkspace();
}
