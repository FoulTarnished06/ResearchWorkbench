/**
 * AI RESEARCH WORKBENCH - COMPARATIVE STUDY MODULE
 * Manages 3-System Scientific Evaluation:
 *   - System A: ResearchWorkbench Multi-Agent Pipeline
 *   - System B: Conventional RAG (Top-K Vector Retrieval + 1 LLM Call)
 *   - System C: Direct Single API Call (Zero-Shot)
 *
 * Supports independent API keys & models per system, live telemetry scoreboard,
 * ground-truth verification checklists, and synchronized side-by-side rendering.
 */

import { sanitizeHTML, escapeHTML, showToast } from './utils.js';

let studyPrompts = [];
let activePrompt = null;
let isInitialized = false;

/**
 * Fallback simple Markdown-to-HTML parser when marked.js CDN is unavailable.
 */
function fallbackMarkdownParse(text) {
  if (!text) return '';
  let html = escapeHTML(text);

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Inline code & blocks
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bullet items
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p>');
  html = `<p>${html}</p>`;
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

/**
 * Render Markdown safely using marked or fallback, sanitized via DOMPurify.
 */
export function renderStudyMarkdown(text) {
  if (!text) return '';
  let parsed = '';
  if (typeof window !== 'undefined' && window.marked && typeof window.marked.parse === 'function') {
    try {
      parsed = window.marked.parse(text);
    } catch {
      parsed = fallbackMarkdownParse(text);
    }
  } else {
    parsed = fallbackMarkdownParse(text);
  }
  return sanitizeHTML(parsed);
}

/**
 * Render LaTeX math in element if KaTeX auto-render is loaded.
 */
export function renderStudyMath(element) {
  if (!element) return;
  if (typeof window !== 'undefined' && typeof window.renderMathInElement === 'function') {
    try {
      window.renderMathInElement(element, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true }
        ],
        throwOnError: false
      });
    } catch (e) {
      console.warn('KaTeX rendering error:', e);
    }
  }
}

/**
 * Detect provider type from key prefix for smart UI hints.
 */
function detectKeyProvider(key) {
  if (!key) return null;
  const trimmed = key.trim();
  if (trimmed.startsWith('AIzaSy')) return 'Gemini';
  if (trimmed.startsWith('sk-ant-')) return 'Claude';
  return 'Custom';
}

function updateKeyBadge(sys) {
  const input = document.getElementById(`studyApiKeySys${sys.toUpperCase()}`);
  const badge = document.getElementById(`studyKeyBadgeSys${sys.toUpperCase()}`);
  if (!input || !badge) return;

  const val = input.value.trim();
  if (!val) {
    badge.textContent = 'Using .env default';
    badge.className = 'key-badge key-badge-default';
    return;
  }
  const detected = detectKeyProvider(val);
  if (detected === 'Claude') {
    badge.textContent = 'Claude Key (Anthropic)';
    badge.className = 'key-badge key-badge-claude';
  } else if (detected === 'Gemini') {
    badge.textContent = 'Gemini Key (Google AI)';
    badge.className = 'key-badge key-badge-gemini';
  } else {
    badge.textContent = 'API Key Set';
    badge.className = 'key-badge key-badge-set';
  }
}

/**
 * Load prompts from backend evals API.
 */
export async function loadStudyPrompts() {
  try {
    const res = await fetch('/api/evals/prompts');
    if (!res.ok) {
      throw new Error(`Failed to load benchmark prompts (${res.status})`);
    }
    studyPrompts = await res.json();
    populatePromptSelector();
  } catch (err) {
    console.error('Error loading study prompts:', err);
    showToast('Failed to load benchmark prompts from server.');
  }
}

function populatePromptSelector() {
  const select = document.getElementById('studyPromptSelect');
  if (!select) return;

  select.innerHTML = '<option value="">-- Choose a Standardized Academic Prompt --</option>';
  studyPrompts.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.title} (${p.domain})`;
    select.appendChild(opt);
  });
}

/**
 * Handle prompt selection from dropdown.
 */
export function onSelectStudyPrompt(promptId) {
  if (!promptId) {
    activePrompt = null;
    const banner = document.getElementById('studyGroundTruthSection');
    if (banner) banner.style.display = 'none';
    return;
  }

  activePrompt = studyPrompts.find(p => p.id === promptId || p.slug === promptId);
  if (!activePrompt) return;

  const queryText = document.getElementById('studyQueryText');
  if (queryText) {
    queryText.value = activePrompt.query;
  }

  // Populate Ground Truth Checklist
  const banner = document.getElementById('studyGroundTruthSection');
  const title = document.getElementById('studyGroundTruthTitle');
  const container = document.getElementById('studyAnchorsContainer');
  const failureNotes = document.getElementById('studyFailureModesText');

  if (banner && container) {
    banner.style.display = 'block';
    if (title) title.textContent = `Ground Truth Checklist: ${activePrompt.title}`;

    container.innerHTML = '';
    (activePrompt.ground_truth_anchors || []).forEach((anchor, idx) => {
      const item = document.createElement('label');
      item.className = 'study-anchor-item';
      item.innerHTML = `
        <input type="checkbox" id="anchorCheck_${idx}">
        <span>${escapeHTML(anchor)}</span>
      `;
      container.appendChild(item);
    });

    if (failureNotes) {
      failureNotes.innerHTML = `
        <strong>Evaluated Failure Modes:</strong> ${escapeHTML((activePrompt.failure_modes_tested || []).join(', '))}<br>
        <strong>Core Evaluation Focus:</strong> ${escapeHTML(activePrompt.evaluation_focus || 'Fact-checking and citation fidelity')}
      `;
    }
  }

  showToast(`Loaded benchmark prompt: ${activePrompt.title}`);
}

/**
 * Update telemetry scoreboard row for a specific system.
 */
export function updateStudyTelemetry(sys, data) {
  const u = sys.toUpperCase();

  const setCell = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val !== null && val !== undefined ? val : '—';
  };

  const analysis = data.text_analysis || {};

  setCell(`studyTelSources${u}`, data.external_sources_count ?? (sys === 'c' ? '0 (Pure Parametric)' : '—'));
  setCell(`studyTelConf${u}`, data.confidence_score !== null && data.confidence_score !== undefined ? `${(data.confidence_score * 100).toFixed(0)}%` : 'N/A');
  setCell(`studyTelInTok${u}`, (data.input_tokens || 0).toLocaleString());
  setCell(`studyTelOutTok${u}`, (data.output_tokens || 0).toLocaleString());
  setCell(`studyTelTotTok${u}`, (data.total_tokens || 0).toLocaleString());
  setCell(`studyTelCost${u}`, data.cost_usd !== undefined ? `$${Number(data.cost_usd).toFixed(4)}` : '—');
  setCell(`studyTelLat${u}`, data.wall_clock_seconds !== undefined ? `${Number(data.wall_clock_seconds).toFixed(2)}s` : '—');

  // Text quality analysis
  setCell(`studyTelEq${u}`, analysis.equations_count ?? '0');
  setCell(`studyTelTables${u}`, analysis.tables_count ?? '0');
  setCell(`studyTelCit${u}`, analysis.citations_count ?? '0');
  setCell(`studyTelWords${u}`, (analysis.word_count || 0).toLocaleString());
}

/**
 * Execute a single system run.
 */
export async function runStudySingle(sys) {
  const queryInput = document.getElementById('studyQueryText');
  const query = queryInput ? queryInput.value.trim() : '';
  if (!query) {
    showToast('Please select a benchmark prompt or enter a research query.');
    return;
  }

  const u = sys.toUpperCase();
  const modelSelect = document.getElementById(`studyModelSys${u}`);
  const model = modelSelect ? modelSelect.value : 'claude-sonnet-5.5';

  const keyInput = document.getElementById(`studyApiKeySys${u}`);
  const apiKey = keyInput && keyInput.value.trim() ? keyInput.value.trim() : null;

  const topKSelect = document.getElementById('studyTopKSysB');
  const topK = sys === 'b' && topKSelect ? parseInt(topKSelect.value, 10) : 5;

  const statusEl = document.getElementById(`studyStatus${u}`);
  const outputEl = document.getElementById(`studyOutput${u}`);
  const runBtn = document.getElementById(`btnRunSys${u}`);

  if (statusEl) statusEl.innerHTML = `<span class="study-spinner"></span> Running...`;
  if (outputEl) {
    outputEl.innerHTML = `
      <div class="study-empty-state">
        <span class="study-spinner study-spinner-lg"></span>
        <p style="margin-top: 12px; font-weight: 500;">Synthesizing monograph for System ${u}...</p>
        <span class="text-subtle" style="font-size: 11px;">Running live AI model: ${escapeHTML(model)}</span>
      </div>
    `;
  }
  if (runBtn) runBtn.disabled = true;

  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/evals/run-system', {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify({
        system_type: sys,
        query: query,
        model: model,
        api_key: apiKey,
        top_k: topK
      })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error (${res.status})`);
    }

    const data = await res.json();
    if (statusEl) {
      statusEl.innerHTML = `<span class="badge badge-success">Completed</span>`;
    }
    if (outputEl) {
      outputEl.innerHTML = renderStudyMarkdown(data.output_text || '');
      renderStudyMath(outputEl);
    }
    updateStudyTelemetry(sys, data);
    showToast(`System ${u} execution finished.`);
  } catch (err) {
    console.error(`System ${u} execution error:`, err);
    if (statusEl) {
      statusEl.innerHTML = `<span class="badge badge-danger">Failed</span>`;
    }
    if (outputEl) {
      outputEl.innerHTML = `
        <div class="study-empty-state" style="color: var(--color-danger, #f87171);">
          <p><strong>System ${u} Execution Error:</strong></p>
          <p style="margin-top: 6px; font-size: 12px; color: var(--text-main);">${escapeHTML(err.message)}</p>
        </div>
      `;
    }
    showToast(`System ${u} failed: ${err.message}`);
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

/**
 * Execute all 3 systems in parallel.
 */
export async function runStudyAllConcurrently() {
  const queryInput = document.getElementById('studyQueryText');
  const query = queryInput ? queryInput.value.trim() : '';
  if (!query) {
    showToast('Please select a benchmark prompt or enter a research query.');
    return;
  }

  const btnAll = document.getElementById('btnRunStudyAll');
  if (btnAll) {
    btnAll.disabled = true;
    btnAll.innerHTML = `<span class="study-spinner"></span> <span>Executing 3 Systems Concurrently...</span>`;
  }

  ['A', 'B', 'C'].forEach(u => {
    const statusEl = document.getElementById(`studyStatus${u}`);
    const outputEl = document.getElementById(`studyOutput${u}`);
    const runBtn = document.getElementById(`btnRunSys${u}`);

    if (statusEl) statusEl.innerHTML = `<span class="study-spinner"></span> Running...`;
    if (outputEl) {
      outputEl.innerHTML = `
        <div class="study-empty-state">
          <span class="study-spinner study-spinner-lg"></span>
          <p style="margin-top: 12px; font-weight: 500;">Synthesizing monograph for System ${u}...</p>
        </div>
      `;
    }
    if (runBtn) runBtn.disabled = true;
  });

  const payload = {
    query: query,
    system_a: {
      enabled: true,
      model: document.getElementById('studyModelSysA')?.value || 'claude-sonnet-5.5',
      api_key: document.getElementById('studyApiKeySysA')?.value.trim() || null
    },
    system_b: {
      enabled: true,
      model: document.getElementById('studyModelSysB')?.value || 'claude-sonnet-5.5',
      api_key: document.getElementById('studyApiKeySysB')?.value.trim() || null,
      top_k: parseInt(document.getElementById('studyTopKSysB')?.value || '5', 10)
    },
    system_c: {
      enabled: true,
      model: document.getElementById('studyModelSysC')?.value || 'claude-sonnet-5.5',
      api_key: document.getElementById('studyApiKeySysC')?.value.trim() || null
    }
  };

  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/evals/run-comparison', {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error (${res.status})`);
    }

    const data = await res.json();
    const results = data.results || {};

    ['a', 'b', 'c'].forEach(sys => {
      const u = sys.toUpperCase();
      const sRes = results[`system_${sys}`];
      const statusEl = document.getElementById(`studyStatus${u}`);
      const outputEl = document.getElementById(`studyOutput${u}`);

      if (sRes && !sRes.error) {
        if (statusEl) statusEl.innerHTML = `<span class="badge badge-success">Completed</span>`;
        if (outputEl) {
          outputEl.innerHTML = renderStudyMarkdown(sRes.output_text || '');
          renderStudyMath(outputEl);
        }
        updateStudyTelemetry(sys, sRes);
      } else {
        if (statusEl) statusEl.innerHTML = `<span class="badge badge-danger">Failed</span>`;
        if (outputEl) {
          outputEl.innerHTML = `
            <div class="study-empty-state" style="color: var(--color-danger, #f87171);">
              <p><strong>System ${u} Error:</strong></p>
              <p style="margin-top: 6px; font-size: 12px; color: var(--text-main);">${escapeHTML((sRes && sRes.error) || 'Unknown failure')}</p>
            </div>
          `;
        }
      }
    });

    showToast('Parallel benchmark run completed.');
  } catch (err) {
    console.error('Comparative benchmark runner failed:', err);
    showToast(`Benchmark error: ${err.message}`);
  } finally {
    if (btnAll) {
      btnAll.disabled = false;
      btnAll.innerHTML = `<span>⚡ Run All 3 Systems Concurrently</span>`;
    }
    ['A', 'B', 'C'].forEach(u => {
      const runBtn = document.getElementById(`btnRunSys${u}`);
      if (runBtn) runBtn.disabled = false;
    });
  }
}

/**
 * Copy a system output monograph to clipboard.
 */
export async function copyStudyOutput(sys) {
  const u = sys.toUpperCase();
  const outputEl = document.getElementById(`studyOutput${u}`);
  if (!outputEl) return;
  const text = outputEl.innerText || outputEl.textContent;
  if (!text || text.includes('No output yet') || text.includes('Synthesizing monograph')) {
    showToast(`No output available to copy for System ${u}.`);
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    showToast(`System ${u} monograph copied to clipboard.`);
  } catch (err) {
    showToast('Failed to copy to clipboard.');
  }
}

/**
 * Reset all 3 system outputs and scoreboard cells.
 */
export function clearStudyOutputs() {
  ['A', 'B', 'C'].forEach(u => {
    const statusEl = document.getElementById(`studyStatus${u}`);
    const outputEl = document.getElementById(`studyOutput${u}`);
    if (statusEl) statusEl.innerHTML = '<span class="badge badge-subtle">Ready</span>';
    if (outputEl) {
      outputEl.innerHTML = `
        <div class="study-empty-state">
          <p>No output generated yet.</p>
          <span class="text-subtle" style="font-size: 11px;">Run System ${u} individually or execute all three concurrently.</span>
        </div>
      `;
    }
  });

  const idsToClear = [
    'studyTelSourcesA', 'studyTelSourcesB',
    'studyTelConfA',
    'studyTelInTokA', 'studyTelInTokB', 'studyTelInTokC',
    'studyTelOutTokA', 'studyTelOutTokB', 'studyTelOutTokC',
    'studyTelTotTokA', 'studyTelTotTokB', 'studyTelTotTokC',
    'studyTelCostA', 'studyTelCostB', 'studyTelCostC',
    'studyTelLatA', 'studyTelLatB', 'studyTelLatC',
    'studyTelEqA', 'studyTelEqB', 'studyTelEqC',
    'studyTelTablesA', 'studyTelTablesB', 'studyTelTablesC',
    'studyTelCitA', 'studyTelCitB', 'studyTelCitC',
    'studyTelWordsA', 'studyTelWordsB', 'studyTelWordsC'
  ];
  idsToClear.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '—';
  });

  showToast('Study outputs and scoreboard cleared.');
}

/**
 * Initialize study view components, event listeners, and prompt catalogue.
 */
export function initStudyView() {
  if (isInitialized) return;
  isInitialized = true;

  loadStudyPrompts();

  // Prompt dropdown change
  const promptSelect = document.getElementById('studyPromptSelect');
  if (promptSelect) {
    promptSelect.addEventListener('change', (e) => onSelectStudyPrompt(e.target.value));
  }

  // Master Run All button
  const btnRunAll = document.getElementById('btnRunStudyAll');
  if (btnRunAll) {
    btnRunAll.addEventListener('click', runStudyAllConcurrently);
  }

  // Single system run buttons
  document.getElementById('btnRunSysA')?.addEventListener('click', () => runStudySingle('a'));
  document.getElementById('btnRunSysB')?.addEventListener('click', () => runStudySingle('b'));
  document.getElementById('btnRunSysC')?.addEventListener('click', () => runStudySingle('c'));

  // Copy buttons
  document.getElementById('btnCopySysA')?.addEventListener('click', () => copyStudyOutput('a'));
  document.getElementById('btnCopySysB')?.addEventListener('click', () => copyStudyOutput('b'));
  document.getElementById('btnCopySysC')?.addEventListener('click', () => copyStudyOutput('c'));

  // Clear button
  document.getElementById('btnClearStudyOutputs')?.addEventListener('click', clearStudyOutputs);

  // Key detection listeners
  ['A', 'B', 'C'].forEach(u => {
    const input = document.getElementById(`studyApiKeySys${u}`);
    if (input) {
      input.addEventListener('input', () => updateKeyBadge(u));
      updateKeyBadge(u);
    }
  });
}
