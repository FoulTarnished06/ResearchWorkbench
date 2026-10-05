/**
 * AI RESEARCH WORKBENCH - MAIN APPLICATION ENTRY POINT (ES MODULE)
 * Central bootstrap, event delegation, and modular coordinator
 */

import {
  sanitizeHTML,
  escapeHTML,
  safeURL,
  safeSetHTML,
  showToast,
  formatTokenBreakdown,
  updateQueryCharCounter,
  autoResizeQueryTextarea,
  debounce
} from './modules/utils.js';

import {
  UIState,
  elements,
  ALL_SCRAPERS,
  SCRAPER_PRESETS,
  currentTheme,
  applyTheme,
  toggleTheme,
  toggleSidebarDock,
  initSidebarDock,
  switchView,
  openSettingsDrawer,
  closeSettingsDrawer,
  updateModelLabels,
  updateDemoModeUI,
  loadSavedSettings,
  loadActiveScrapers,
  saveActiveScrapers,
  updateScrapersUI,
  initScrapersManager,
  initExecutionMode,
  initArchitectureControls,
  saveApiKeys,
  clearSQLiteCache,
  resetFactoryDefaults,
  refreshCacheStats
} from './modules/state.js';

import {
  activateNode,
  completeNode,
  resetNodeStates,
  positionNodeCards,
  setNodeTransform,
  drawBezierConnectors,
  initBackgroundCanvas,
  zoomCanvas,
  resetCanvasZoom,
  openDatabaseModal
} from './modules/canvas.js';

import {
  extractAcademicTakeaways,
  finishPipeline,
  buildComparisonTableHTML,
  buildDialecticalFrictionHTML,
  buildEpistemicLimitationsHTML,
  initClaimInspector,
  showClaimInspector,
  hideClaimInspector,
  renderDossierOutput,
  renderCitationsPanel,
  setupClaimCitationInteractions,
  highlightCitation,
  highlightClaimsForRef,
  copySynthesisToClipboard,
  exportBibtexToClipboard,
  toggleCitationsSidebar
} from './modules/dossier.js';

import {
  handleQuerySubmit,
  executePipeline,
  abortPipeline,
  startElapsedTimer,
  stopElapsedTimer,
  executeLiveBackend
} from './modules/pipeline.js';

import {
  initPDFWorkspace,
  handlePDFActionSelect,
  handlePDFUpload,
  openPDFSession,
  loadDocumentLibrary,
  executePDFQuestion,
  appendChatBubble,
  executePDFAnalysisPipeline,
  renderPDFAnalysisOutput,
  renderSourceChunks,
  renderFigureGallery,
  loadAndRenderCitationGraph,
  drawCitationNetwork
} from './modules/pdf_workspace.js';

import {
  openHistoryModal,
  closeHistoryModal,
  loadResearchHistory,
  renderHistoryList,
  replayResearchRun,
  deleteHistoryRun,
  openFollowupDrawer,
  submitFollowupInquiry,
  loadPromptHistory,
  renderPromptHistoryList,
  exportDossier,
  downloadBlob,
  initQuerySuggestions,
  renderSuggestions,
  openShortcutsModal,
  closeShortcutsModal,
  initDialogueView,
  loadDialogueHistory,
  renderDialogueMessage,
  handleDialogueSubmit,
  clearActiveDialogue
} from './modules/dialogue.js';

import {
  initAuth,
  openAuthModal,
  closeAuthModal,
  getAuthToken,
  getCurrentUser
} from './modules/auth.js';

function initEventListeners() {
  // View Switchers - Retractable Sidebar & Navigation Dock
  elements.navAbout?.addEventListener('click', () => switchView('about'));
  elements.navCanvas?.addEventListener('click', () => switchView('canvas'));
  elements.navDossier?.addEventListener('click', () => switchView('dossier'));
  elements.navDialogue?.addEventListener('click', () => switchView('dialogue'));
  elements.navDocuments?.addEventListener('click', () => switchView('documents'));
  elements.navSettings?.addEventListener('click', openSettingsDrawer);
  elements.navDatabase?.addEventListener('click', openDatabaseModal);
  elements.navHistory?.addEventListener('click', openHistoryModal);
  elements.dockHomeBtn?.addEventListener('click', () => switchView('about'));
  elements.btnToggleDock?.addEventListener('click', () => toggleSidebarDock());
  
  document.querySelectorAll('.switch-pill').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });
  
  elements.btnLaunchWorkbench?.addEventListener('click', () => switchView('canvas'));
  elements.btnViewPipelineDemo?.addEventListener('click', () => switchView('canvas'));
  elements.btnReopenCanvas?.addEventListener('click', () => switchView('canvas'));
  elements.btnOpenDialogueToolbar?.addEventListener('click', () => switchView('dialogue'));
  elements.btnLaunchDialogue?.addEventListener('click', () => switchView('dialogue'));
  elements.btnDialogueReturnDossier?.addEventListener('click', () => switchView('dossier'));
  elements.btnClearDialogue?.addEventListener('click', clearActiveDialogue);
  elements.btnSendDialogue?.addEventListener('click', handleDialogueSubmit);
  
  elements.dialogueUserInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleDialogueSubmit();
    }
  });

  document.addEventListener('click', (e) => {
    const pill = e.target.closest('.dialogue-pill');
    if (pill && elements.dialogueUserInput) {
      const prompt = pill.dataset.prompt;
      if (prompt) {
        elements.dialogueUserInput.value = prompt;
        handleDialogueSubmit();
      }
    }
  });

  // Settings Drawer triggers
  elements.btnToggleDrawer?.addEventListener('click', openSettingsDrawer);
  elements.btnCloseDrawer?.addEventListener('click', closeSettingsDrawer);
  elements.drawerBackdrop?.addEventListener('click', closeSettingsDrawer);
  
  // Prevent any click inside the settings drawer from bubbling to backdrop or closing the drawer
  elements.settingsDrawer?.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  // Settings Tabs Switcher
  document.querySelectorAll('.drawer-tab-btn').forEach(tabBtn => {
    tabBtn.addEventListener('click', () => {
      document.querySelectorAll('.drawer-tab-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      document.querySelectorAll('.drawer-tab-pane').forEach(p => p.classList.remove('active'));
      tabBtn.classList.add('active');
      tabBtn.setAttribute('aria-selected', 'true');
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

  // Canvas Log Drawer Toggle (Minimize / Expand)
  const logDrawer = document.getElementById('canvas-log-drawer');
  const logToggleBtn = document.getElementById('btn-log-drawer-toggle');
  const logHeader = document.getElementById('log-drawer-header');
  
  if (logDrawer && localStorage.getItem('workbench_log_drawer_collapsed') === 'true') {
    logDrawer.classList.add('collapsed');
    if (logToggleBtn) logToggleBtn.textContent = '+';
  }

  const toggleLogDrawer = (e) => {
    if (e) e.stopPropagation();
    if (!logDrawer) return;
    logDrawer.classList.toggle('collapsed');
    const isCollapsed = logDrawer.classList.contains('collapsed');
    if (logToggleBtn) logToggleBtn.textContent = isCollapsed ? '+' : '−';
    localStorage.setItem('workbench_log_drawer_collapsed', isCollapsed ? 'true' : 'false');
  };
  logToggleBtn?.addEventListener('click', toggleLogDrawer);
  logHeader?.addEventListener('click', (e) => {
    if (e.target !== logToggleBtn) toggleLogDrawer(e);
  });

  // Keyboard shortcuts (BONUS-09)
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSettingsDrawer();
      closeHistoryModal();
      closeShortcutsModal();
      elements.dbInspectorModal?.classList.remove('open');
      elements.exportDropdownMenu?.classList.add('hidden');
      elements.searchSuggestionsDropdown?.classList.add('hidden');
    }
    if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      openShortcutsModal();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      toggleSidebarDock();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'h') {
      e.preventDefault();
      openHistoryModal();
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

  // Strict Live AI (Disable Fallback) Switches (FE-03)
  if (elements.toggleDisableFallbackAgent2) {
    elements.toggleDisableFallbackAgent2.addEventListener('change', (e) => {
      localStorage.setItem('workbench_disable_fallback_agent2', e.target.checked ? 'true' : 'false');
      showToast(e.target.checked ? "Agent 2: Offline fallback disabled" : "Agent 2: Offline fallback enabled");
    });
  }
  if (elements.toggleDisableFallbackAgent4) {
    elements.toggleDisableFallbackAgent4.addEventListener('change', (e) => {
      localStorage.setItem('workbench_disable_fallback_agent4', e.target.checked ? 'true' : 'false');
      showToast(e.target.checked ? "Agent 4: Offline fallback disabled" : "Agent 4: Offline fallback enabled");
    });
  }

  // Sliders
  elements.cfgPaperLimit.addEventListener('input', (e) => {
    elements.valPaperLimit.textContent = `${e.target.value} papers`;
  });
  elements.cfgPdfPageLimit?.addEventListener('input', (e) => {
    if (elements.valPdfPageLimit) {
      elements.valPdfPageLimit.textContent = `${e.target.value} pages`;
    }
  });
  elements.cfgSimThresh?.addEventListener('input', (e) => {
    if (elements.valSimThresh) elements.valSimThresh.textContent = `${e.target.value} (Auto-Verify)`;
  });

  // Model Selection Change
  elements.cfgAgent2Model?.addEventListener('change', updateModelLabels);
  elements.cfgAgent4Model?.addEventListener('change', updateModelLabels);

  // DB Inspector
  elements.navDatabase?.addEventListener('click', openDatabaseModal);
  elements.btnCloseDbModal?.addEventListener('click', () => elements.dbInspectorModal?.classList.remove('open'));

  // Clear Input Button
  elements.btnClearInput?.addEventListener('click', () => {
    if (elements.inputQuery) {
      elements.inputQuery.value = '';
      autoResizeQueryTextarea(elements.inputQuery);
      updateQueryCharCounter();
    }
  });

  // Bottom Chat Prompt Input: Live Character Counter and Auto-Resize
  elements.inputQuery.addEventListener('input', () => {
    autoResizeQueryTextarea(elements.inputQuery);
    updateQueryCharCounter();
  });

  // Auto-resize other textareas if present
  elements.dialogueUserInput?.addEventListener('input', () => {
    autoResizeQueryTextarea(elements.dialogueUserInput);
  });
  elements.docQueryInput?.addEventListener('input', () => {
    autoResizeQueryTextarea(elements.docQueryInput);
  });

  // Bottom Chat Prompt Input: Enter Submission
  elements.inputQuery.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuerySubmit();
    }
  });
  elements.btnSendQuery?.addEventListener('click', handleQuerySubmit);

  // Preset query chips
  document.querySelectorAll('.query-chip, .btn-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.query || btn.textContent.trim();
      if (elements.inputQuery) {
        elements.inputQuery.value = q;
        autoResizeQueryTextarea(elements.inputQuery);
        updateQueryCharCounter();
        elements.inputQuery.focus();
      }
    });
  });

  // Starter topic chips in Dossier Hero card
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.starter-chip');
    if (chip && elements.inputQuery) {
      const q = chip.dataset.query || chip.textContent.trim();
      elements.inputQuery.value = q;
      autoResizeQueryTextarea(elements.inputQuery);
      updateQueryCharCounter();
      handleQuerySubmit();
    }
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
  elements.btnToggleSidebar?.addEventListener('click', toggleCitationsSidebar);

  // Researcher Tool Buttons: Copy Synthesis & Export
  elements.btnCopySynthesis?.addEventListener('click', copySynthesisToClipboard);
  elements.btnExportBibtex?.addEventListener('click', exportBibtexToClipboard);

  // Multi-Format Export Dropdown triggers (BONUS-03)
  elements.btnExportMenu?.addEventListener('click', (e) => {
    e.stopPropagation();
    elements.exportDropdownMenu?.classList.toggle('hidden');
  });
  elements.btnExportDocx?.addEventListener('click', () => {
    elements.exportDropdownMenu?.classList.add('hidden');
    exportDossier('docx');
  });
  elements.btnExportLatex?.addEventListener('click', () => {
    elements.exportDropdownMenu?.classList.add('hidden');
    exportDossier('latex');
  });
  elements.btnExportMarkdown?.addEventListener('click', () => {
    elements.exportDropdownMenu?.classList.add('hidden');
    exportDossier('markdown');
  });

  document.addEventListener('click', (e) => {
    if (!elements.exportDropdownMenu?.contains(e.target) && !elements.btnExportMenu?.contains(e.target)) {
      elements.exportDropdownMenu?.classList.add('hidden');
    }
  });

  // Past Outputs History triggers (BONUS-01, BONUS-02, FOL-06)
  elements.navHistory?.addEventListener('click', openHistoryModal);
  elements.btnOpenHistory?.addEventListener('click', openHistoryModal);
  elements.btnCloseHistoryModal?.addEventListener('click', closeHistoryModal);
  elements.btnRefreshHistory?.addEventListener('click', () => {
    const isPromptsTab = document.getElementById('tab-history-prompts')?.classList.contains('active');
    if (isPromptsTab) {
      loadPromptHistory();
    } else {
      loadResearchHistory();
    }
  });

  // History Tab Switcher
  const tabDossiers = document.getElementById('tab-history-dossiers');
  const tabPrompts = document.getElementById('tab-history-prompts');
  const dossierView = document.getElementById('history-list');
  const promptView = document.getElementById('prompt-history-list');

  tabDossiers?.addEventListener('click', () => {
    tabDossiers.classList.add('active');
    tabPrompts?.classList.remove('active');
    if (dossierView) dossierView.style.display = 'flex';
    if (promptView) promptView.style.display = 'none';
  });

  tabPrompts?.addEventListener('click', () => {
    tabPrompts.classList.add('active');
    tabDossiers?.classList.remove('active');
    if (dossierView) dossierView.style.display = 'none';
    if (promptView) promptView.style.display = 'flex';
    loadPromptHistory();
  });

  elements.historySearchInput?.addEventListener('input', () => {
    const isPromptsTab = tabPrompts?.classList.contains('active');
    if (isPromptsTab) {
      renderPromptHistoryList(UIState.cachedPrompts || []);
    } else {
      renderHistoryList(UIState.cachedRuns || []);
    }
  });

  // Keyboard Shortcuts modal triggers (BONUS-09)
  elements.btnOpenShortcuts?.addEventListener('click', openShortcutsModal);
  elements.btnCloseShortcutsModal?.addEventListener('click', closeShortcutsModal);

  // Quick Answer jump button (DUAL-03)
  elements.btnJumpAcademic?.addEventListener('click', () => {
    const target = document.getElementById('key-takeaways-card') || elements.dossierContent;
    target?.scrollIntoView({ behavior: 'smooth' });
  });

  // Autocomplete Query Suggestions (BONUS-08)
  initQuerySuggestions();

  // Canvas zoom/reset controls
  document.getElementById('ctrl-zoom-in')?.addEventListener('click', () => zoomCanvas(1.1));
  document.getElementById('ctrl-zoom-out')?.addEventListener('click', () => zoomCanvas(0.9));
  document.getElementById('ctrl-reset')?.addEventListener('click', resetCanvasZoom);
  document.getElementById('ctrl-fit')?.addEventListener('click', resetCanvasZoom);
}

// Application Bootstrap
function initApp() {
  applyTheme(currentTheme);
  initSidebarDock();
  initScrapersManager();
  initExecutionMode();
  initArchitectureControls();
  initBackgroundCanvas();
  loadSavedSettings();
  initEventListeners();
  updateDemoModeUI();
  updateModelLabels();
  updateQueryCharCounter(elements.inputQuery, elements.queryCharCount);
  initClaimInspector();
  initQuerySuggestions();
  initPDFWorkspace();
  initAuth();
  switchView('about');
  
  window.addEventListener('resize', () => {
    positionNodeCards();
    drawBezierConnectors();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
