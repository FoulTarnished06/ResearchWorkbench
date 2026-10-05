/**
 * AI RESEARCH WORKBENCH - PDF DOCUMENT ANALYSIS WORKSPACE MODULE
 * Document upload, chunk viewer, raster figure gallery, interactive citation graph, and paper Q&A
 */

import { UIState, elements, switchView } from './state.js';
import { sanitizeHTML, escapeHTML, safeURL, safeSetHTML, showToast, formatTokenBreakdown } from './utils.js';
import { fetchSSE } from './scenarios.js';
import { buildComparisonTableHTML, buildDialecticalFrictionHTML, buildEpistemicLimitationsHTML } from './dossier.js';



// Helper to retrieve user API config and mode toggles
export function getWorkbenchAPIConfig() {
  const openaiKey = (document.getElementById('cfg-openai-key')?.value.trim()) || sessionStorage.getItem('workbench_openai_key') || '';
  const geminiKey = (document.getElementById('cfg-gemini-key')?.value.trim()) || sessionStorage.getItem('workbench_gemini_key') || '';
  const anthropicKey = (document.getElementById('cfg-anthropic-key')?.value.trim()) || sessionStorage.getItem('workbench_anthropic_key') || '';
  const agent2ModelVal = document.getElementById('cfg-agent2-model')?.value || 'gemini-3.6-flash';
  const provider = agent2ModelVal;
  const strictMode = elements.togglePdfStrictApi ? elements.togglePdfStrictApi.checked : false;

  return { openaiKey, geminiKey, anthropicKey, provider, strictMode };
}

export function updateDocAPIStatus() {
  const config = getWorkbenchAPIConfig();
  if (!elements.docApiStatus || !elements.docApiText) return;
  const dot = elements.docApiStatus.querySelector('.doc-api-dot');

  if (config.openaiKey || config.geminiKey || config.anthropicKey) {
    elements.docApiText.innerText = config.strictMode ? 'Strict API (Online)' : 'API Connected';
    if (dot) dot.className = 'doc-api-dot';
  } else {
    elements.docApiText.innerText = config.strictMode ? 'Strict API (No Key)' : 'Fallback Mode';
    if (dot) dot.className = config.strictMode ? 'doc-api-dot offline' : 'doc-api-dot warning';
  }
}

// Initialize PDF Event Listeners
export function initPDFWorkspace() {
  // Bind PDF elements to elements cache
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
  elements.docApiStatus = document.getElementById('doc-api-status');
  elements.docApiText = document.getElementById('doc-api-text');
  elements.docDemoChips = document.getElementById('doc-demo-chips');

  // Initialize Strict API Toggle
  if (elements.togglePdfStrictApi) {
    const savedStrict = localStorage.getItem('workbench_pdf_strict_api');
    if (savedStrict !== null) {
      elements.togglePdfStrictApi.checked = (savedStrict === 'true');
    } else {
      elements.togglePdfStrictApi.checked = false; // Default offline heuristic mode enabled
    }
    elements.togglePdfStrictApi.addEventListener('change', (e) => {
      localStorage.setItem('workbench_pdf_strict_api', e.target.checked ? 'true' : 'false');
      updateDocAPIStatus();
      showToast(e.target.checked ? 'Strict API Mode ON: Live LLM calls will fail cleanly if keys are invalid.' : 'Strict Mode OFF: Offline fallback enabled.', 'info');
    });
  }

  // Preset Inquiries / Suggested Chips
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
          bibtex += `@article{${key},\n  title={${f.title || f.original_filename}},\n  author={${f.authors || 'Unknown'}},\n  year={${f.creation_date ? f.creation_date.slice(0, 4) : 'n.d.'}},\n  note={Extracted via AI Research Workbench}\n}\n\n`;
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
export function handlePDFActionSelect(action) {
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
export async function handlePDFUpload(fileList) {
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
export async function openPDFSession(sessionId) {
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
export async function loadDocumentLibrary() {
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
    // console.log("Could not load library:", err);
  }
}

// Execute Q&A over PDF documents
export async function executePDFQuestion(overrideQuery = null) {
  const query = (overrideQuery !== null ? overrideQuery : elements.docQueryInput.value).trim();
  if (!query || !UIState.pdfSessionId) return;

  if (query.length > 1000) {
    showToast(`PDF question exceeds the 1,000 character limit (${query.length.toLocaleString()} characters). Please shorten your question.`);
    return;
  }

  // Append user bubble
  appendChatBubble('user', query);
  if (elements.docQueryInput) {
    elements.docQueryInput.value = '';
    elements.docQueryInput.style.height = 'auto';
  }

  // Append loading assistant bubble
  const loadingBubble = appendChatBubble('assistant', 'Searching indexed document chunks and synthesizing answer...');

  const { openaiKey, geminiKey, anthropicKey, provider, strictMode } = getWorkbenchAPIConfig();

  // Fail-closed client validation if Strict Mode is ON and no API keys are present
  if (strictMode && !openaiKey && !geminiKey && !anthropicKey) {
    loadingBubble.innerHTML = `
      <div style="padding: 6px 0;">
        <strong style="color: var(--accent-rose);">⚠️ Strict API Mode Active — Missing API Key</strong>
        <p style="margin: 6px 0 12px; font-size: 0.88rem; color: var(--text-muted); line-height: 1.5;">
          Strict API mode requires a valid OpenAI, Gemini, or Anthropic Claude API key. 
          Configure your API key in <strong>Model Settings</strong>, or switch to <strong>Offline Heuristic Mode</strong> to analyze locally.
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn-primary btn-sm" onclick="document.getElementById('nav-settings')?.click()">⚙️ Configure API Key</button>
          <button class="btn-secondary btn-sm" onclick="if(elements.togglePdfStrictApi){ elements.togglePdfStrictApi.checked = false; elements.togglePdfStrictApi.dispatchEvent(new Event('change')); showToast('Switched to Offline Heuristic Mode'); }">⚡ Offline Heuristic Mode</button>
        </div>
      </div>
    `;
    return;
  }

  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const resp = await fetch('/api/pdf/qa', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(openaiKey ? { 'x-openai-key': openaiKey } : {}),
        ...(geminiKey ? { 'x-gemini-key': geminiKey } : {}),
        ...(anthropicKey ? { 'x-anthropic-key': anthropicKey } : {})
      },
      credentials: 'same-origin',
      body: JSON.stringify({
        session_id: UIState.pdfSessionId,
        action: 'qa',
        query: query,
        chat_history: UIState.pdfChatHistory,
        provider: provider,
        openai_key: openaiKey,
        gemini_key: geminiKey,
        anthropic_key: anthropicKey,
        disable_fallback: strictMode
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Q&A request failed');
    }

    const data = await resp.json();
    let tokenBadge = '';
    if (data.tokens_used) {
      const pTok = data.prompt_tokens ?? Math.round(data.tokens_used * 0.65);
      const cTok = data.completion_tokens ?? Math.max(0, data.tokens_used - pTok);
      tokenBadge = `<div style="margin-top: 8px; font-size: 0.72rem; color: var(--text-subtle); display: flex; align-items: center; gap: 6px;"><span class="followup-token-chip">⚡ ${data.tokens_used} tokens (In: ${pTok} · Out: ${cTok})</span></div>`;
    }
    safeSetHTML(loadingBubble, (data.answer_html || '<p>No answer synthesized.</p>') + tokenBadge);

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
        <p style="margin: 4px 0 0; font-size: 0.88rem; color: var(--text-muted);">${escapeHTML(err.message)}</p>
      </div>
    `;
  }
}

export function appendChatBubble(role, content) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = role === 'user' ? `<p>${escapeHTML(content)}</p>` : sanitizeHTML(content);
  elements.docChatMessages.appendChild(bubble);
  elements.docChatMessages.scrollTop = elements.docChatMessages.scrollHeight;
  return bubble;
}

// Execute Monograph/Methodology/Findings Analysis via SSE
export async function executePDFAnalysisPipeline(action) {
  if (!UIState.pdfSessionId) return;
  elements.docOutputContent.innerHTML = '<div class="empty-state-card"><div class="empty-icon">⏳</div><h3>Synthesizing Academic Analysis...</h3><p>Extracting grounded assertions across document chunks.</p></div>';

  const { openaiKey, geminiKey, anthropicKey, provider, strictMode } = getWorkbenchAPIConfig();

  // Fail-closed client validation if Strict Mode is ON and no API keys are present
  if (strictMode && !openaiKey && !geminiKey && !anthropicKey) {
    elements.docOutputContent.innerHTML = `
      <div class="empty-state-card" style="border-color: rgba(244,63,94,0.4); text-align: left; padding: 24px;">
        <div class="empty-icon">⚠️</div>
        <h3 style="color: var(--accent-rose); margin-bottom: 6px;">Strict API Mode Active — Missing API Key</h3>
        <p style="color: var(--text-muted); font-size: 0.88rem; line-height: 1.5; margin-bottom: 14px;">
          Strict API Mode guarantees no synthetic fallback text is generated. Provide an API key in Model Settings, or switch to Offline Heuristic Mode to analyze this document locally.
        </p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button class="btn-primary btn-sm" onclick="document.getElementById('nav-settings')?.click()">⚙️ Configure API Key</button>
          <button class="btn-secondary btn-sm" onclick="if(elements.togglePdfStrictApi){ elements.togglePdfStrictApi.checked = false; elements.togglePdfStrictApi.dispatchEvent(new Event('change')); executePDFAnalysisPipeline('${action}'); }">⚡ Offline Heuristic Mode</button>
        </div>
      </div>
    `;
    return;
  }

  const payload = {
    session_id: UIState.pdfSessionId,
    action: action,
    query: "",
    provider: provider,
    disable_fallback: strictMode,
    openai_key: openaiKey,
    gemini_key: geminiKey,
    anthropic_key: anthropicKey
  };

  const abortController = new AbortController();
  UIState.pdfAbortController = abortController;

  const eventHandlers = {
    pdf_chunks_ready: (e) => {
      const data = JSON.parse(e.data);
      showToast(`Retrieved ${data.total_chunks} context chunks for grounding.`, 'info');
    },
    pdf_pipeline_complete: (e) => {
      UIState.pdfAbortController = null;
      const data = JSON.parse(e.data);
      renderPDFAnalysisOutput(data);
      renderSourceChunks(data.citations || []);
    },
    pdf_pipeline_error: (e) => {
      UIState.pdfAbortController = null;
      const data = JSON.parse(e.data);
      elements.docOutputContent.innerHTML = `<div class="empty-state-card" style="border-color: rgba(244,63,94,0.4);"><div class="empty-icon">⚠️</div><h3 style="color: var(--accent-rose);">Analysis Failed</h3><p>${escapeHTML(data.error || 'Live AI call failed')}</p></div>`;
    }
  };

  try {
    await fetchSSE('/api/pdf/stream', payload, eventHandlers, abortController.signal);
  } catch (err) {
    if (!abortController.signal.aborted) {
      console.error("PDF stream error:", err);
      elements.docOutputContent.innerHTML = `<div class="empty-state-card" style="border-color: rgba(244,63,94,0.4);"><div class="empty-icon">⚠️</div><h3 style="color: var(--accent-rose);">Stream Interrupted</h3><p>${escapeHTML(err.message)}</p></div>`;
    }
  }
}

export function renderPDFAnalysisOutput(data) {
  let html = '';

  // Monograph Token Telemetry Banner (TOK-PRECISION)
  const totTok = data.token_usage?.total_tokens || data.tokens_used;
  if (totTok) {
    const pTok = data.token_usage?.prompt_tokens ?? data.prompt_tokens ?? Math.round(totTok * 0.65);
    const cTok = data.completion_tokens ?? data.token_usage?.completion_tokens ?? Math.max(0, totTok - pTok);
    html += `
      <div class="pdf-token-telemetry-banner" style="margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
        <span class="dossier-tokens-tag">⚡ ${formatTokenBreakdown(totTok, pTok, cTok)}</span>
      </div>
    `;
  }

  // Dual output: Quick Answer (Plain-English Summary) if available
  if (data.quick_answer && data.quick_answer.trim()) {
    html += `
      <div class="quick-answer-card" style="margin-bottom: 20px;">
        <div class="quick-answer-header">
          <div class="quick-answer-badge">
            <span class="qa-badge-icon">💡</span>
            <span class="qa-badge-title">Executive Plain-English Summary</span>
          </div>
        </div>
        <div class="quick-answer-body">${sanitizeHTML(data.quick_answer)}</div>
      </div>
    `;
  }

  // Executive Summary
  if (data.executive_summary) {
    html += `
      <div class="dossier-section-card" style="margin-bottom: 20px;">
        <div class="section-badge-bar">
          <span class="sec-badge">Executive Monograph</span>
        </div>
        <div class="section-content-prose">${sanitizeHTML(data.executive_summary)}</div>
      </div>
    `;
  }

  // Quantitative Comparative Benchmarks (PDF Parity)
  if (data.comparison_table) {
    html += buildComparisonTableHTML(data.comparison_table);
  }

  // Dialectical Friction & Methodological Disagreements (PDF Parity)
  if (data.dialectical_friction) {
    html += buildDialecticalFrictionHTML(data.dialectical_friction);
  }

  // Sections
  (data.dossier_sections || []).forEach(sec => {
    html += `
      <div class="dossier-section-card" style="margin-bottom: 20px;">
        <div class="section-badge-bar">
          <span class="sec-badge">${escapeHTML(sec.sub_question || 'Section')}</span>
        </div>
        <div class="section-content-prose">${sanitizeHTML(sec.content_html)}</div>
      </div>
    `;
  });

  // Epistemic Horizons & Unresolved Frontiers (PDF Parity)
  if (data.epistemic_limitations) {
    html += buildEpistemicLimitationsHTML(data.epistemic_limitations);
  }

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
export function renderSourceChunks(chunks) {
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
export function renderFigureGallery(figures) {
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
export async function loadAndRenderCitationGraph() {
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

export function drawCitationNetwork(nodes, edges) {
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


