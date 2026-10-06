/**
 * AI RESEARCH WORKBENCH - STATE & VIEW MANAGEMENT MODULE
 * UIState reactive store, DOM elements map, theme handling, dock, and drawer controls
 */

import { showToast } from './utils.js';
import { initBackgroundCanvas, drawBezierConnectors, positionNodeCards } from './canvas.js';
import { loadDocumentLibrary } from './pdf_workspace.js';
import { initDialogueView } from './dialogue.js';

export const UIState = {
  currentView: 'about',
  activeArchitecture: 'system_a', // 'system_a', 'system_b', or 'system_c'
  ragTopK: 5,
  systemApiKeys: { a: '', b: '', c: '' },
  isRunning: false,
  elapsedTimer: null,
  elapsedSeconds: 0.0,
  totalTokens: 0,
  totalPromptTokens: 0,
  totalCompletionTokens: 0,
  activeQuery: "",
  activeNode: 0,
  scale: 1.0,
  lastDossierData: null,
  activeRunId: null,
  activeDialogueLoadedRunId: null,
  citationsSidebarOpen: true,
  activeEventSource: null,
  activeAbortController: null,
  activeTimeouts: [],
  nodePositions: {
    agent1: { x: 70, y: 100 },
    agent2: { x: 440, y: 60 },
    agent3: { x: 440, y: 360 },
    agent4: { x: 820, y: 200 }
  },
  pdfSessionId: null,
  pdfFiles: [],
  pdfAction: 'qa',
  pdfChatHistory: [],
  pdfFigures: [],
  pdfCitationGraph: null,
  pdfEventSource: null
};

// DOM Elements Cache
export const elements = {
  navAbout: document.getElementById('nav-about'),
  navCanvas: document.getElementById('nav-canvas'),
  navDossier: document.getElementById('nav-dossier'),
  navDialogue: document.getElementById('nav-dialogue'),
  navDocuments: document.getElementById('nav-documents'),
  navSettings: document.getElementById('nav-settings'),
  navDatabase: document.getElementById('nav-database'),
  dockHomeBtn: document.getElementById('dock-home-btn'),
  btnToggleDock: document.getElementById('btn-toggle-dock'),
  promptScrapersBadge: document.getElementById('prompt-scrapers-badge'),
  promptScrapersCount: document.getElementById('prompt-scrapers-count'),
  scrapersSummaryText: document.getElementById('scrapers-summary-text'),
  
  viewAbout: document.getElementById('view-about'),
  viewCanvas: document.getElementById('view-canvas'),
  viewDossier: document.getElementById('view-dossier'),
  viewDialogue: document.getElementById('view-dialogue'),
  viewDocuments: document.getElementById('view-documents'),
  
  btnLaunchWorkbench: document.getElementById('btn-launch-workbench'),
  btnReopenCanvas: document.getElementById('btn-reopen-canvas'),
  
  settingsDrawer: document.getElementById('settings-drawer'),
  drawerBackdrop: document.getElementById('drawer-backdrop'),
  btnCloseDrawer: document.getElementById('btn-close-drawer'),
  btnToggleTheme: document.getElementById('btn-toggle-theme'),
  btnAbortPipeline: document.getElementById('btn-abort-pipeline'),
  themeIcon: document.getElementById('theme-icon'),
  toggleDisableFallbackAgent2: document.getElementById('toggle-disable-fallback-agent2'),
  toggleDisableFallbackAgent4: document.getElementById('toggle-disable-fallback-agent4'),
  bottomChatContainer: document.getElementById('bottom-chat-container'),
  
  // History & Shortcuts UI
  navHistory: document.getElementById('nav-history'),
  btnOpenShortcuts: document.getElementById('btn-open-shortcuts'),
  historyModal: document.getElementById('history-modal'),
  btnCloseHistoryModal: document.getElementById('btn-close-history-modal'),
  historySearchInput: document.getElementById('history-search-input'),
  btnRefreshHistory: document.getElementById('btn-refresh-history'),
  historyList: document.getElementById('history-list'),
  historyCountBadge: document.getElementById('history-count-badge'),
  shortcutsModal: document.getElementById('shortcuts-modal'),
  btnCloseShortcutsModal: document.getElementById('btn-close-shortcuts-modal'),
  
  // Quick Answer & Export UI
  quickAnswerCard: document.getElementById('quick-answer-card'),
  quickAnswerText: document.getElementById('quick-answer-text'),
  btnJumpAcademic: document.getElementById('btn-jump-academic'),
  btnExportMenu: document.getElementById('btn-export-menu'),
  exportDropdownMenu: document.getElementById('export-dropdown-menu'),
  btnExportDocx: document.getElementById('btn-export-docx'),
  btnExportLatex: document.getElementById('btn-export-latex'),
  btnExportMarkdown: document.getElementById('btn-export-markdown'),
  searchSuggestionsDropdown: document.getElementById('search-suggestions-dropdown'),
  
  teleElapsed: document.getElementById('tele-elapsed'),
  teleTokens: document.getElementById('tele-tokens'),
  teleStatusDot: document.getElementById('tele-status-dot'),
  teleStatusText: document.getElementById('tele-status-text'),
  
  inputQuery: document.getElementById('research-query-input'),
  queryCharCount: document.getElementById('query-char-count'),
  btnClearInput: document.getElementById('btn-clear-input'),
  btnSendQuery: document.getElementById('btn-send-query'),
  promptModelBadge: document.getElementById('prompt-model-badge'),
  
  dossierTitle: document.getElementById('dossier-query-title'),
  dossierContent: document.getElementById('dossier-content-body'),
  dossierMetaTokens: document.getElementById('dossier-meta-tokens'),
  takeawayList: document.getElementById('takeaway-list'),
  citationsContainer: document.getElementById('citations-list-container'),
  citTotalCount: document.getElementById('cit-total-count'),
  dossierCitationsSidebar: document.getElementById('dossier-citations-sidebar'),
  btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
  lblSidebarToggle: document.getElementById('lbl-sidebar-toggle'),
  btnCopySynthesis: document.getElementById('btn-copy-synthesis'),
  btnExportBibtex: document.getElementById('btn-export-bibtex'),
  
  // Continuous Research Dialogue (CHAT-04, CHAT-05)
  btnLaunchDialogue: document.getElementById('btn-launch-dialogue'),
  dialogueActiveQuery: document.getElementById('dialogue-active-query'),
  dialogueTurnTokens: document.getElementById('dialogue-turn-tokens'),
  dialogueInTokens: document.getElementById('dialogue-in-tokens'),
  dialogueOutTokens: document.getElementById('dialogue-out-tokens'),
  dialogueTokenSavings: document.getElementById('dialogue-token-savings'),
  dialogueAnchorClaims: document.getElementById('dialogue-anchor-claims'),
  dialogueMessages: document.getElementById('dialogue-messages'),
  dialogueUserInput: document.getElementById('dialogue-user-input'),
  btnSendDialogue: document.getElementById('btn-send-dialogue'),
  btnClearDialogue: document.getElementById('btn-clear-dialogue'),
  btnDialogueReturnDossier: document.getElementById('btn-dialogue-return-dossier'),
  
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
  
  cfgOpenaiKey: document.getElementById('cfg-openai-key'),
  cfgAgent2Model: document.getElementById('cfg-agent2-model'),
  cfgAgent4Model: document.getElementById('cfg-agent4-model'),
  cfgPaperLimit: document.getElementById('cfg-paper-limit'),
  valPaperLimit: document.getElementById('val-paper-limit'),
  cfgPdfPageLimit: document.getElementById('cfg-pdf-page-limit'),
  valPdfPageLimit: document.getElementById('val-pdf-page-limit'),
  cfgSimThresh: document.getElementById('cfg-similarity-thresh'),
  valSimThresh: document.getElementById('val-similarity-thresh')
};

// =========================================================
export let currentTheme = localStorage.getItem('workbench_theme') || 'theme-dark';

export function applyTheme(theme) {
  currentTheme = theme;
  document.body.classList.remove('theme-dark', 'theme-beige');
  document.body.classList.add(theme);
  localStorage.setItem('workbench_theme', theme);
  
  if (elements.themeIcon) {
    elements.themeIcon.textContent = (theme === 'theme-beige') ? '🌙' : '☀️';
  }
  
  // Refresh canvas visuals
  initBackgroundCanvas();
  drawBezierConnectors();
}

export function toggleTheme() {
  const nextTheme = currentTheme === 'theme-dark' ? 'theme-beige' : 'theme-dark';
  applyTheme(nextTheme);
  showToast(nextTheme === 'theme-beige' ? "Aesthetic Warm Beige Mode" : "Midnight Obsidian Mode");
}


export function switchView(viewName) {
  UIState.currentView = viewName;
  const isWorkbench = (viewName === 'canvas' || viewName === 'dossier' || viewName === 'documents' || viewName === 'dialogue');

  // Update body view state class for CSS enforcement
  document.body.classList.toggle('on-about', viewName === 'about');
  document.body.classList.toggle('on-canvas', viewName === 'canvas');
  document.body.classList.toggle('on-dossier', viewName === 'dossier');
  document.body.classList.toggle('on-workbench', isWorkbench);
  document.body.classList.toggle('on-documents', viewName === 'documents');
  document.body.classList.toggle('on-dialogue', viewName === 'dialogue');
  
  // Update view sections
  const allViews = [elements.viewAbout, elements.viewCanvas, elements.viewDossier];
  if (elements.viewDocuments) allViews.push(elements.viewDocuments);
  if (elements.viewDialogue) allViews.push(elements.viewDialogue);
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
  if (viewName === 'dialogue' && elements.viewDialogue) {
    elements.viewDialogue.classList.add('active');
    initDialogueView();
  }
  
  // Update dock buttons
  const allDocks = [elements.navAbout, elements.navCanvas, elements.navDossier];
  if (elements.navDocuments) allDocks.push(elements.navDocuments);
  if (elements.navDialogue) allDocks.push(elements.navDialogue);
  allDocks.forEach(b => { if (b) b.classList.remove('active'); });

  if (viewName === 'about' && elements.navAbout) elements.navAbout.classList.add('active');
  if (viewName === 'canvas' && elements.navCanvas) elements.navCanvas.classList.add('active');
  if (viewName === 'dossier' && elements.navDossier) elements.navDossier.classList.add('active');
  if (viewName === 'documents' && elements.navDocuments) elements.navDocuments.classList.add('active');
  if (viewName === 'dialogue' && elements.navDialogue) elements.navDialogue.classList.add('active');
  
  // Update top switch pills
  document.querySelectorAll('.switch-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.view === viewName);
  });

  // HIDE BOTTOM CHAT INTERFACE ON ALL PAGES EXCEPT CANVAS (Dossier, Dialogue & Docs have dedicated reading/chat interfaces)
  if (elements.bottomChatContainer) {
    if (viewName === 'canvas') {
      elements.bottomChatContainer.style.setProperty('display', 'flex', 'important');
    } else {
      elements.bottomChatContainer.style.setProperty('display', 'none', 'important');
    }
  }

  // ALL SIDEBAR OPTIONS AND SETTINGS ARE PERMANENTLY AVAILABLE (At all times across all views)
  if (elements.btnToggleDrawer) {
    elements.btnToggleDrawer.style.setProperty('display', 'flex', 'important');
  }
}

export function openSettingsDrawer() {
  elements.settingsDrawer.classList.add('open');
  elements.settingsDrawer.setAttribute('aria-hidden', 'false');
  elements.settingsDrawer.removeAttribute('inert');
  elements.drawerBackdrop.classList.add('open');
  refreshCacheStats();
}

export function openSettingsDrawerTab(tabName = 'models') {
  openSettingsDrawer();
  document.querySelectorAll('.drawer-tab-btn').forEach(b => {
    const isActive = b.dataset.tab === tabName;
    b.classList.toggle('active', isActive);
    b.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });
  document.querySelectorAll('.drawer-tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `tab-pane-${tabName}`);
  });
}

export function closeSettingsDrawer() {
  elements.settingsDrawer.classList.remove('open');
  elements.settingsDrawer.setAttribute('aria-hidden', 'true');
  elements.settingsDrawer.setAttribute('inert', '');
  elements.drawerBackdrop.classList.remove('open');
}

// Fetch SQLite cache stats from backend API
export async function refreshCacheStats() {
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
    // console.log("Could not load cache stats from backend", err);
  }
  if (statPapers) statPapers.textContent = "0";
  if (statSentences) statSentences.textContent = "0";
  if (statRuns) statRuns.textContent = "0";
}

// Clear SQLite Cache
export async function clearSQLiteCache() {
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
    // console.log("Cache clear API call failed", err);
  }
  showToast("Local cache reset");
  refreshCacheStats();
}

// Reset settings to factory defaults
export function resetFactoryDefaults() {
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
  if (sourceSel) sourceSel.value = 'all';
  const strictSel = document.getElementById('cfg-factcheck-strictness');
  if (strictSel) strictSel.value = 'strict';
  
  // Reset scraper selection to all 6 academic repositories
  UIState.activeScrapers = [...ALL_SCRAPERS];
  saveActiveScrapers(UIState.activeScrapers);
  updateScrapersUI();
  
  // SEC-13: Clear ephemeral session credentials and legacy storage
  sessionStorage.removeItem('workbench_openai_key');
  sessionStorage.removeItem('workbench_gemini_key');
  sessionStorage.removeItem('workbench_anthropic_key');
  sessionStorage.removeItem('workbench_serpapi_key');
  localStorage.removeItem('workbench_openai_key');
  localStorage.removeItem('workbench_gemini_key');
  localStorage.removeItem('workbench_anthropic_key');
  localStorage.removeItem('workbench_serpapi_key');
  localStorage.removeItem('workbench_disable_fallback_agent2');
  localStorage.removeItem('workbench_disable_fallback_agent4');
  if (elements.toggleDisableFallbackAgent2) elements.toggleDisableFallbackAgent2.checked = false;
  if (elements.toggleDisableFallbackAgent4) elements.toggleDisableFallbackAgent4.checked = false;

  const openaiInput = document.getElementById('cfg-openai-key');
  const geminiInput = document.getElementById('cfg-gemini-key');
  const anthropicInput = document.getElementById('cfg-anthropic-key');
  const serpapiInput = document.getElementById('cfg-serpapi-key');
  if (openaiInput) openaiInput.value = '';
  if (geminiInput) geminiInput.value = '';
  if (anthropicInput) anthropicInput.value = '';
  if (serpapiInput) serpapiInput.value = '';

  updateModelLabels();
  showToast("Settings restored to factory academic defaults.");
}

// Save API Keys locally in ephemeral sessionStorage (SEC-13)
export function saveApiKeys() {
  const openaiKey = document.getElementById('cfg-openai-key')?.value.trim() || '';
  const geminiKey = document.getElementById('cfg-gemini-key')?.value.trim() || '';
  const anthropicKey = document.getElementById('cfg-anthropic-key')?.value.trim() || '';
  const serpapiKey = document.getElementById('cfg-serpapi-key')?.value.trim() || '';
  const keySysA = document.getElementById('cfg-key-sys-a')?.value.trim() || '';
  const keySysB = document.getElementById('cfg-key-sys-b')?.value.trim() || '';
  const keySysC = document.getElementById('cfg-key-sys-c')?.value.trim() || '';

  sessionStorage.setItem('workbench_openai_key', openaiKey);
  sessionStorage.setItem('workbench_gemini_key', geminiKey);
  sessionStorage.setItem('workbench_anthropic_key', anthropicKey);
  sessionStorage.setItem('workbench_serpapi_key', serpapiKey);
  sessionStorage.setItem('workbench_key_sys_a', keySysA);
  sessionStorage.setItem('workbench_key_sys_b', keySysB);
  sessionStorage.setItem('workbench_key_sys_c', keySysC);

  UIState.systemApiKeys = {
    a: keySysA,
    b: keySysB,
    c: keySysC
  };
  
  // Clean out any lingering legacy localStorage keys
  localStorage.removeItem('workbench_openai_key');
  localStorage.removeItem('workbench_gemini_key');
  localStorage.removeItem('workbench_anthropic_key');
  updateApiKeyBadges();

  // If user is currently signed in, also automatically sync keys to their encrypted account vault
  import('./auth.js').then(auth => {
    if (auth.getAuthToken && auth.getAuthToken()) {
      if (openaiKey) auth.saveUserApiKey('openai', openaiKey);
      if (geminiKey) auth.saveUserApiKey('gemini', geminiKey);
      if (anthropicKey) auth.saveUserApiKey('anthropic', anthropicKey);
      if (serpapiKey) auth.saveUserApiKey('serpapi', serpapiKey);
      showToast("API credentials saved and synced to your encrypted account vault.");
    } else {
      showToast("API credentials saved to session storage.");
    }
  }).catch(() => {
    showToast("API credentials saved to session storage.");
  });
}

export function updateApiKeyBadges() {
  const openai = sessionStorage.getItem('workbench_openai_key') || document.getElementById('cfg-openai-key')?.value.trim() || '';
  const gemini = sessionStorage.getItem('workbench_gemini_key') || document.getElementById('cfg-gemini-key')?.value.trim() || '';
  const anthropic = sessionStorage.getItem('workbench_anthropic_key') || document.getElementById('cfg-anthropic-key')?.value.trim() || '';
  const keyA = sessionStorage.getItem('workbench_key_sys_a') || document.getElementById('cfg-key-sys-a')?.value.trim() || '';
  const keyB = sessionStorage.getItem('workbench_key_sys_b') || document.getElementById('cfg-key-sys-b')?.value.trim() || '';
  const keyC = sessionStorage.getItem('workbench_key_sys_c') || document.getElementById('cfg-key-sys-c')?.value.trim() || '';

  const setBadge = (elId, key, defLabel = ".env fallback") => {
    const el = document.getElementById(elId);
    if (!el) return;
    if (!key) {
      el.className = "key-badge key-badge-default";
      el.textContent = defLabel;
    } else if (key.startsWith('AIza')) {
      el.className = "key-badge key-badge-valid";
      el.textContent = "Gemini Key";
    } else if (key.startsWith('sk-ant-')) {
      el.className = "key-badge key-badge-valid";
      el.textContent = "Claude Key";
    } else if (key.startsWith('sk-')) {
      el.className = "key-badge key-badge-valid";
      el.textContent = "OpenAI Key";
    } else {
      el.className = "key-badge key-badge-valid";
      el.textContent = "Active Key";
    }
  };

  setBadge('badge-key-openai', openai, ".env fallback");
  setBadge('badge-key-gemini', gemini, ".env fallback");
  setBadge('badge-key-anthropic', anthropic, ".env fallback");
  setBadge('badge-key-sys-a', keyA, "Inherited");
  setBadge('badge-key-sys-b', keyB, "Inherited");
  setBadge('badge-key-sys-c', keyC, "Inherited");

  const statusBadge = document.getElementById('api-keys-status-badge');
  if (statusBadge) {
    if (openai || gemini || anthropic || keyA || keyB || keyC) {
      statusBadge.className = "badge badge-success";
      statusBadge.textContent = "Live Keys Active";
    } else {
      statusBadge.className = "badge badge-subtle";
      statusBadge.textContent = "Default Keys";
    }
  }
}

export function getSystemApiKey(sys = 'a') {
  sys = sys.toLowerCase();
  const perSys = sessionStorage.getItem(`workbench_key_sys_${sys}`) || '';
  if (perSys) return perSys;
  
  // 1. Fall back to preferred model provider key
  const a2Model = (elements.cfgAgent2Model?.value || localStorage.getItem('workbench_agent2_model') || 'gemini-3.6-flash').toLowerCase();
  let candidate = '';
  if (a2Model.includes('gpt') || a2Model.includes('sol') || a2Model.includes('luna') || a2Model.includes('astra') || a2Model.includes('openai')) {
    candidate = sessionStorage.getItem('workbench_openai_key') || '';
  } else if (a2Model.includes('claude') || a2Model.includes('sonnet') || a2Model.includes('opus') || a2Model.includes('haiku')) {
    candidate = sessionStorage.getItem('workbench_anthropic_key') || '';
  } else {
    candidate = sessionStorage.getItem('workbench_gemini_key') || '';
  }
  if (candidate) return candidate;

  // 2. If preferred provider key is not found, check if ANY active provider key is present in session storage
  return sessionStorage.getItem('workbench_gemini_key') || 
         sessionStorage.getItem('workbench_openai_key') || 
         sessionStorage.getItem('workbench_anthropic_key') || 
         '';
}

export function setActiveArchitecture(arch, notify = true) {
  if (!['system_a', 'system_b', 'system_c'].includes(arch)) arch = 'system_a';
  UIState.activeArchitecture = arch;
  try {
    localStorage.setItem('workbench_active_arch', arch);
  } catch (e) {}

  // 1. Sync Settings Drawer radio cards
  document.querySelectorAll('.arch-radio-card').forEach(card => {
    const isMatch = card.dataset.arch === arch;
    card.classList.toggle('active', isMatch);
    const radio = card.querySelector('input[type="radio"]');
    if (radio) radio.checked = isMatch;
  });

  const ragSub = document.getElementById('arch-sub-options-rag');
  if (ragSub) {
    ragSub.style.display = (arch === 'system_b') ? 'block' : 'none';
  }

  const archBadge = document.getElementById('cfg-active-arch-badge');
  if (archBadge) {
    if (arch === 'system_a') {
      archBadge.className = 'badge badge-success';
      archBadge.textContent = 'System A Active';
    } else if (arch === 'system_b') {
      archBadge.className = 'badge badge-warning';
      archBadge.textContent = 'System B (RAG) Active';
    } else {
      archBadge.className = 'badge badge-danger';
      archBadge.textContent = 'System C (Direct API) Active';
    }
  }

  // 2. Sync Canvas Floating Selector Pills
  document.querySelectorAll('.canvas-arch-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.arch === arch);
  });

  // 3. Sync Bottom Bar Quick Toggle
  const quickBtn = document.getElementById('btn-quick-arch-toggle');
  const quickLabel = document.getElementById('prompt-arch-label');
  if (quickBtn && quickLabel) {
    quickBtn.className = `provider-pill-badge arch-pill-badge active-arch-${arch.slice(-1)}`;
    if (arch === 'system_a') {
      quickLabel.textContent = '🏛️ System A: 4-Agent';
      quickBtn.title = 'Active Engine: System A (4-Agent Pipeline). Click to cycle.';
    } else if (arch === 'system_b') {
      quickLabel.textContent = '🔍 System B: RAG';
      quickBtn.title = 'Active Engine: System B (Conventional RAG). Click to cycle.';
    } else {
      quickLabel.textContent = '⚡ System C: Direct API';
      quickBtn.title = 'Active Engine: System C (Direct Single API). Click to cycle.';
    }
  }

  // 4. Update Canvas Node Topology visualization
  import('./canvas.js').then(module => {
    if (module.updateCanvasArchitectureTopology) {
      module.updateCanvasArchitectureTopology(arch);
    }
  }).catch(() => {});

  if (notify) {
    const titles = {
      system_a: "System A Active: 4-Agent ResearchWorkbench (Adversarial Fact-Checking)",
      system_b: "System B Active: Conventional RAG Baseline (Vector Top-K Chunks)",
      system_c: "System C Active: Direct Single API Baseline (Zero-Shot Parametric)"
    };
    showToast(titles[arch] || "Architecture Updated");
  }
}

export function updateModelLabels() {
  if (!elements.cfgAgent2Model || !elements.cfgAgent4Model) return;
  const a2Selected = elements.cfgAgent2Model.options[elements.cfgAgent2Model.selectedIndex]?.text || "Gemini 3.6 Flash";
  const a2Text = a2Selected.replace(/\s*\(.*?\)/, '').trim();
  if (elements.promptModelBadge) elements.promptModelBadge.textContent = `${a2Text} + SQLite`;
  const m2 = document.getElementById('m-agent2-model');
  if (m2) m2.textContent = a2Text;
  
  const a4Selected = elements.cfgAgent4Model.options[elements.cfgAgent4Model.selectedIndex]?.text || "Gemini 3.6 Flash";
  const a4Text = a4Selected.replace(/\s*\(.*?\)/, '').trim();
  const m4 = document.getElementById('m-agent4-model');
  if (m4) m4.textContent = a4Text;

  // Persist selected provider for dialogue, PDF workspace, and claim follow-ups
  sessionStorage.setItem('workbench_selected_provider', elements.cfgAgent2Model.value);
  localStorage.setItem('workbench_agent2_model', elements.cfgAgent2Model.value);
  localStorage.setItem('workbench_agent4_model', elements.cfgAgent4Model.value);
}

export function updateDemoModeUI() {
  if (elements.demoIndicatorTag) {
    elements.demoIndicatorTag.textContent = "Live Backend";
    elements.demoIndicatorTag.style.display = "inline-block";
  }
  if (elements.teleStatusDot) elements.teleStatusDot.className = "pulse-indicator status-blue";
  if (elements.teleStatusText) elements.teleStatusText.textContent = "Live AI Ready";
}

// Load saved API Keys and Settings on startup
export function loadSavedSettings() {
  // Purge any stale localStorage keys from prior versions
  localStorage.removeItem('workbench_openai_key');
  localStorage.removeItem('workbench_gemini_key');
  localStorage.removeItem('workbench_anthropic_key');
  localStorage.removeItem('workbench_serpapi_key');

  const openaiKey = sessionStorage.getItem('workbench_openai_key');
  const geminiKey = sessionStorage.getItem('workbench_gemini_key');
  const anthropicKey = sessionStorage.getItem('workbench_anthropic_key');
  const serpapiKey = sessionStorage.getItem('workbench_serpapi_key');
  const keySysA = sessionStorage.getItem('workbench_key_sys_a');
  const keySysB = sessionStorage.getItem('workbench_key_sys_b');
  const keySysC = sessionStorage.getItem('workbench_key_sys_c');
  const savedDisableFallbackAgent2 = localStorage.getItem('workbench_disable_fallback_agent2');
  const savedDisableFallbackAgent4 = localStorage.getItem('workbench_disable_fallback_agent4');
  const savedArch = localStorage.getItem('workbench_active_arch') || 'system_a';
  const savedTopK = localStorage.getItem('workbench_rag_topk') || '5';

  if (openaiKey && document.getElementById('cfg-openai-key')) {
    document.getElementById('cfg-openai-key').value = openaiKey;
  }
  if (geminiKey && document.getElementById('cfg-gemini-key')) {
    document.getElementById('cfg-gemini-key').value = geminiKey;
  }
  if (anthropicKey && document.getElementById('cfg-anthropic-key')) {
    document.getElementById('cfg-anthropic-key').value = anthropicKey;
  }
  if (serpapiKey && document.getElementById('cfg-serpapi-key')) {
    document.getElementById('cfg-serpapi-key').value = serpapiKey;
  }
  if (keySysA && document.getElementById('cfg-key-sys-a')) {
    document.getElementById('cfg-key-sys-a').value = keySysA;
  }
  if (keySysB && document.getElementById('cfg-key-sys-b')) {
    document.getElementById('cfg-key-sys-b').value = keySysB;
  }
  if (keySysC && document.getElementById('cfg-key-sys-c')) {
    document.getElementById('cfg-key-sys-c').value = keySysC;
  }

  const topkSel = document.getElementById('cfg-rag-topk');
  if (topkSel) {
    topkSel.value = savedTopK;
    UIState.ragTopK = parseInt(savedTopK, 10) || 5;
  }

  if (savedDisableFallbackAgent2 !== null && elements.toggleDisableFallbackAgent2) {
    elements.toggleDisableFallbackAgent2.checked = (savedDisableFallbackAgent2 === 'true');
  }
  if (savedDisableFallbackAgent4 !== null && elements.toggleDisableFallbackAgent4) {
    elements.toggleDisableFallbackAgent4.checked = (savedDisableFallbackAgent4 === 'true');
  }

  const savedA2 = localStorage.getItem('workbench_agent2_model');
  const savedA4 = localStorage.getItem('workbench_agent4_model');
  if (savedA2 && elements.cfgAgent2Model) elements.cfgAgent2Model.value = savedA2;
  if (savedA4 && elements.cfgAgent4Model) elements.cfgAgent4Model.value = savedA4;
  updateModelLabels();
  updateApiKeyBadges();
  setActiveArchitecture(savedArch, false);

  updateDemoModeUI();
}



export const ALL_SCRAPERS = ["crossref", "doaj", "openalex", "semantic_scholar", "europepmc", "pubmed", "core", "base"];
export const SCRAPER_PRESETS = {
  all: ["crossref", "doaj", "openalex", "semantic_scholar", "europepmc", "pubmed", "core", "base"],
  economics: ["crossref", "doaj", "openalex", "core", "base"],
  biomedical: ["pubmed", "europepmc", "semantic_scholar"],
  openaccess: ["doaj", "crossref", "openalex", "core", "base"]
};

export function loadActiveScrapers() {
  try {
    const raw = localStorage.getItem('workbench_active_scrapers');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const valid = parsed.filter(s => ALL_SCRAPERS.includes(s));
        if (valid.length > 0) return valid;
      }
    }
  } catch (e) {
    console.warn("Could not parse saved active scrapers", e);
  }
  return [...ALL_SCRAPERS];
}

export function saveActiveScrapers(scrapers) {
  try {
    localStorage.setItem('workbench_active_scrapers', JSON.stringify(scrapers));
  } catch (e) {
    console.warn("Could not save active scrapers", e);
  }
}

export function updateScrapersUI() {
  const active = UIState.activeScrapers || ALL_SCRAPERS;

  // Sync checkboxes and visual card styles
  document.querySelectorAll('.scraper-checkbox').forEach(cb => {
    const isChecked = active.includes(cb.value);
    cb.checked = isChecked;
    const card = cb.closest('.scraper-card');
    if (card) {
      card.classList.toggle('active', isChecked);
    }
  });

  // Sync summary counter
  const summaryEl = document.getElementById('scrapers-summary-text');
  if (summaryEl) {
    summaryEl.textContent = `Active: ${active.length} of ${ALL_SCRAPERS.length} academic repositories selected`;
  }
  const promptBadgeCount = document.getElementById('prompt-scrapers-count');
  if (promptBadgeCount) {
    promptBadgeCount.textContent = `📚 ${active.length} Repos Active`;
  }

  // Sync preset button active state
  document.querySelectorAll('.scraper-preset-btn').forEach(btn => {
    const preset = btn.dataset.preset;
    if (preset && SCRAPER_PRESETS[preset]) {
      const presetList = SCRAPER_PRESETS[preset];
      const isMatch = presetList.length === active.length && presetList.every(s => active.includes(s));
      btn.classList.toggle('active', isMatch);
    }
  });
}

function setScrapersFromPreset(presetKey) {
  if (SCRAPER_PRESETS[presetKey]) {
    UIState.activeScrapers = [...SCRAPER_PRESETS[presetKey]];
    saveActiveScrapers(UIState.activeScrapers);
    updateScrapersUI();
    const readable = presetKey.charAt(0).toUpperCase() + presetKey.slice(1);
    showToast(`Scraper Preset Applied: ${readable} (${UIState.activeScrapers.length} repos)`);
  }
}

export function initScrapersManager() {
  UIState.activeScrapers = loadActiveScrapers();
  updateScrapersUI();

  // Checkbox change listener
  document.querySelectorAll('.scraper-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const scraper = e.target.value;
      if (e.target.checked) {
        if (!UIState.activeScrapers.includes(scraper)) {
          UIState.activeScrapers.push(scraper);
        }
      } else {
        // Enforce at least 1 scraper active
        if (UIState.activeScrapers.length <= 1) {
          e.target.checked = true;
          showToast("At least one academic repository must remain active.");
          return;
        }
        UIState.activeScrapers = UIState.activeScrapers.filter(s => s !== scraper);
      }
      saveActiveScrapers(UIState.activeScrapers);
      updateScrapersUI();
    });
  });

  // Preset buttons
  document.querySelectorAll('.scraper-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.dataset.preset;
      if (preset) setScrapersFromPreset(preset);
    });
  });

  // Prompt scrapers badge click
  const promptBadge = document.getElementById('prompt-scrapers-badge');
  if (promptBadge) {
    promptBadge.addEventListener('click', () => {
      openSettingsDrawerTab('pipeline');
    });
  }
}

export function initExecutionMode() {
  const modeBtns = document.querySelectorAll('.mode-toggle-btn');
  const savedMode = localStorage.getItem('workbench_execution_mode') || 'deep';
  
  function updateModeUI(mode) {
    modeBtns.forEach(btn => {
      if (btn.dataset.mode === mode) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
  
  updateModeUI(savedMode);
  
  modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const selectedMode = btn.dataset.mode;
      if (selectedMode) {
        localStorage.setItem('workbench_execution_mode', selectedMode);
        updateModeUI(selectedMode);
        showToast(selectedMode === 'rapid' 
          ? '⚡ Rapid Mode Active: Accelerated ~5s response with verified citations' 
          : '🔬 Deep Monograph Active: Full 4-Agent pipeline with 3-tier claim audit (~30s)');
      }
    });
  });

  // Architecture Quick Toggle in bottom prompt bar
  const quickArchBtn = document.getElementById('btn-quick-arch-toggle');
  if (quickArchBtn) {
    quickArchBtn.addEventListener('click', () => {
      const order = ['system_a', 'system_b', 'system_c'];
      const curIdx = order.indexOf(UIState.activeArchitecture);
      const nextArch = order[(curIdx + 1) % order.length];
      setActiveArchitecture(nextArch, true);
    });
  }

  // Preset Benchmark Prompt Chips
  document.querySelectorAll('.query-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.query;
      if (q && elements.inputQuery) {
        elements.inputQuery.value = q;
        import('./utils.js').then(u => {
          u.autoResizeQueryTextarea(elements.inputQuery);
          u.updateQueryCharCounter();
        });
        elements.inputQuery.focus();
        showToast("Benchmark prompt loaded.");
      }
    });
  });
}

export function initArchitectureControls() {
  // 1. Settings Drawer Architecture Radio Cards
  document.querySelectorAll('.arch-radio-card').forEach(card => {
    card.addEventListener('click', (e) => {
      const arch = card.dataset.arch;
      if (arch && arch !== UIState.activeArchitecture) {
        setActiveArchitecture(arch, true);
      }
    });
  });

  document.querySelectorAll('input[name="pipeline_arch"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.checked && e.target.value !== UIState.activeArchitecture) {
        setActiveArchitecture(e.target.value, true);
      }
    });
  });

  // Top-K selector for System B
  const topkSel = document.getElementById('cfg-rag-topk');
  if (topkSel) {
    topkSel.addEventListener('change', (e) => {
      const val = parseInt(e.target.value, 10) || 5;
      UIState.ragTopK = val;
      localStorage.setItem('workbench_rag_topk', String(val));
      showToast(`RAG Retrieval Depth updated: Top ${val} context chunks.`);
    });
  }

  // 2. Canvas Floating Architecture Pills
  document.querySelectorAll('.canvas-arch-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const arch = pill.dataset.arch;
      if (arch && arch !== UIState.activeArchitecture) {
        setActiveArchitecture(arch, true);
      }
    });
  });

  // 3. Per-System Keys Accordion
  const toggleSysKeysBtn = document.getElementById('btnToggleSystemKeys');
  const sysKeysPanel = document.getElementById('customSystemKeysPanel');
  const sysKeysArrow = document.getElementById('sys-keys-arrow');
  if (toggleSysKeysBtn && sysKeysPanel) {
    toggleSysKeysBtn.addEventListener('click', () => {
      const isHidden = sysKeysPanel.style.display === 'none' || !sysKeysPanel.style.display;
      sysKeysPanel.style.display = isHidden ? 'block' : 'none';
      if (sysKeysArrow) sysKeysArrow.textContent = isHidden ? '▼' : '▶';
    });
  }

  // 4. API Key input live badges on typing
  ['cfg-openai-key', 'cfg-gemini-key', 'cfg-anthropic-key', 'cfg-key-sys-a', 'cfg-key-sys-b', 'cfg-key-sys-c'].forEach(id => {
    const inp = document.getElementById(id);
    if (inp) {
      inp.addEventListener('input', () => {
        updateApiKeyBadges();
      });
    }
  });

  // Save API Keys Button
  const saveBtn = document.getElementById('btn-save-keys');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      saveApiKeys();
    });
  }
}


export function toggleSidebarDock(forceState = null) {
  const isCurrentlyExpanded = document.body.classList.contains('dock-expanded');
  const nextExpanded = forceState !== null ? forceState : !isCurrentlyExpanded;

  document.body.classList.toggle('dock-expanded', nextExpanded);
  try {
    localStorage.setItem('workbench_dock_expanded', nextExpanded ? 'true' : 'false');
  } catch (e) {}

  const btn = document.getElementById('btn-toggle-dock');
  if (btn) {
    btn.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
    btn.title = nextExpanded ? "Collapse Sidebar (Ctrl+B)" : "Expand Sidebar (Ctrl+B)";
  }
}

export function initSidebarDock() {
  const saved = localStorage.getItem('workbench_dock_expanded');
  const shouldExpand = saved !== null ? (saved === 'true') : (window.innerWidth >= 1280);
  if (shouldExpand) {
    document.body.classList.add('dock-expanded');
  } else {
    document.body.classList.remove('dock-expanded');
  }

  const toggleBtn = document.getElementById('btn-toggle-dock');
  if (toggleBtn) {
    toggleBtn.setAttribute('aria-expanded', shouldExpand ? 'true' : 'false');
    toggleBtn.title = shouldExpand ? "Collapse Sidebar (Ctrl+B)" : "Expand Sidebar (Ctrl+B)";
    toggleBtn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleSidebarDock();
    };
  }
}


