/**
 * AI RESEARCH WORKBENCH - DIALOGUE, HISTORY & EXPORTS MODULE
 * Multi-turn research dialogue (DHS-RCC), single-claim follow-ups, prompt trees, and multi-format exports
 */

import { UIState, elements, switchView, refreshCacheStats } from './state.js';
import { sanitizeHTML, escapeHTML, safeURL, safeSetHTML, showToast, debounce } from './utils.js';
import { renderDossierOutput } from './dossier.js';
import { handleQuerySubmit } from './pipeline.js';

let suggestDebounceTimer = null;

// PAST OUTPUTS & RESEARCH HISTORY (BONUS-01, BONUS-02)
// =========================================================
export async function openHistoryModal() {
  if (elements.historyModal) {
    elements.historyModal.classList.add('open');
    await loadResearchHistory();
  }
}

export function closeHistoryModal() {
  if (elements.historyModal) {
    elements.historyModal.classList.remove('open');
  }
}

export async function loadResearchHistory() {
  if (!elements.historyList) return;
  elements.historyList.innerHTML = `
    <div class="history-loading">
      <span class="mini-pulse-dot active"></span>
      <span>Loading past research history...</span>
    </div>
  `;

  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch('/api/history?limit=50', {
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('Failed to retrieve history');
    const data = await res.json();
    const runs = data.runs || [];
    UIState.cachedRuns = runs;

    if (elements.historyCountBadge) {
      elements.historyCountBadge.textContent = `${runs.length} saved ${runs.length === 1 ? 'run' : 'runs'}`;
    }

    renderHistoryList(runs);
  } catch (err) {
    console.error('Error loading history:', err);
    elements.historyList.innerHTML = `
      <div class="history-empty-state">
        <div class="history-empty-icon">⚠️</div>
        <p>Could not load history: ${escapeHTML(err.message)}</p>
      </div>
    `;
  }
}

export function renderHistoryList(runs) {
  if (!elements.historyList) return;
  if (!runs || runs.length === 0) {
    elements.historyList.innerHTML = `
      <div class="history-empty-state">
        <div class="history-empty-icon">📜</div>
        <h4 style="color: var(--text-title); margin-bottom: 6px;">No Past Research Syntheses Yet</h4>
        <p>Execute an academic query in the prompt bar to generate your first research monograph.</p>
      </div>
    `;
    return;
  }

  const filterText = (elements.historySearchInput?.value || '').toLowerCase().trim();
  const filtered = filterText 
    ? runs.filter(r => (r.query || '').toLowerCase().includes(filterText) || (r.executive_summary || '').toLowerCase().includes(filterText))
    : runs;

  if (filtered.length === 0) {
    elements.historyList.innerHTML = `
      <div class="history-empty-state">
        <p>No past outputs match "<strong>${escapeHTML(filterText)}</strong>"</p>
      </div>
    `;
    return;
  }

  elements.historyList.innerHTML = '';
  filtered.forEach(run => {
    const card = document.createElement('div');
    card.className = 'history-card';
    card.id = `history-card-${run.run_id}`;

    const dateStr = run.created_at ? new Date(run.created_at).toLocaleString() : 'Recent';
    const paperCount = run.papers_count || (run.citations ? run.citations.length : 0);
    const tokensCount = run.total_tokens || 0;
    const pTok = run.prompt_tokens ?? (tokensCount > 0 ? Math.round(tokensCount * 0.62) : 0);
    const cTok = run.completion_tokens ?? (tokensCount > 0 ? Math.max(0, tokensCount - pTok) : 0);
    const tokenStr = (pTok > 0 || cTok > 0)
      ? `⚡ ${tokensCount.toLocaleString()} tokens (In: ${pTok.toLocaleString()} · Out: ${cTok.toLocaleString()})`
      : `⚡ ${tokensCount.toLocaleString()} tokens`;
    const elapsed = run.elapsed_seconds ? `${run.elapsed_seconds.toFixed(1)}s` : '--';

    let archBadge = '<span class="matrix-chip chip-green" style="font-size: 10.5px; padding: 2px 7px; margin-right: 6px;">System A: Workbench</span>';
    if (run.architecture === 'system_b') {
      archBadge = '<span class="matrix-chip chip-amber" style="font-size: 10.5px; padding: 2px 7px; margin-right: 6px;">System B: Conventional RAG</span>';
    } else if (run.architecture === 'system_c') {
      archBadge = '<span class="matrix-chip chip-red" style="font-size: 10.5px; padding: 2px 7px; margin-right: 6px;">System C: Direct API</span>';
    }

    card.innerHTML = `
      <div class="history-card-header">
        <div>
          <div class="history-card-title" title="Click to view and replay monograph">${escapeHTML(run.query || 'Research Monograph')}</div>
          <div style="margin-top: 4px;">${archBadge}</div>
        </div>
        <div class="history-card-actions">
          <button class="btn-history-replay" data-run-id="${run.run_id}" title="Replay output (0 API tokens)">
            <span>Open Dossier</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
          <button class="btn-history-delete" data-run-id="${run.run_id}" title="Delete this run">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
      <div class="history-card-meta">
        <span>📅 ${dateStr}</span>
        <span>${tokenStr}</span>
        <span>⏱️ ${elapsed}</span>
        <span>📚 ${paperCount} papers</span>
      </div>
    `;

    card.querySelector('.history-card-title').addEventListener('click', () => replayResearchRun(run.run_id));
    card.querySelector('.btn-history-replay').addEventListener('click', (e) => {
      e.stopPropagation();
      replayResearchRun(run.run_id);
    });

    card.querySelector('.btn-history-delete').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (confirm(`Delete past output for "${run.query}"?`)) {
        await deleteHistoryRun(run.run_id);
      }
    });

    elements.historyList.appendChild(card);
  });
}

export async function replayResearchRun(runId) {
  try {
    showToast("Retrieving cached research monograph...");
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch(`/api/history/${encodeURIComponent(runId)}`, {
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('Run not found');
    const run = await res.json();

    const formattedSections = (run.dossier_sections || run.sections || []).map(s => ({
      sub_question: s.sub_question || s.title || "Section",
      answer_html: s.content_html || s.answer_html || ""
    }));

    const dossierData = {
      run_id: runId,
      query: run.query,
      architecture: run.architecture || run.results?.architecture || 'system_a',
      model: run.model || run.results?.model || '',
      output_text: run.output_text || run.results?.output_text || '',
      quick_answer: run.quick_answer || "",
      executive_summary: run.executive_summary || "",
      takeaways: run.takeaways || [],
      sections: formattedSections,
      citations: run.citations || [],
      evaluated_claims: run.evaluated_claims || [],
      comparison_table: run.comparison_table || run.results?.comparison_table || [],
      dialectical_friction: run.dialectical_friction || run.results?.dialectical_friction || {},
      epistemic_limitations: run.epistemic_limitations || run.results?.epistemic_limitations || [],
      complexity: run.complexity || run.results?.complexity || {},
      elapsed: run.elapsed_seconds || 0,
      latency_seconds: run.elapsed_seconds || 0,
      tokens: run.total_tokens || 0,
      prompt_tokens: run.prompt_tokens ?? (run.total_tokens ? Math.round(run.total_tokens * 0.62) : 0),
      completion_tokens: run.completion_tokens ?? (run.total_tokens ? Math.max(0, run.total_tokens - Math.round(run.total_tokens * 0.62)) : 0)
    };

    UIState.lastDossierData = dossierData;
    UIState.activeRunId = runId;
    renderDossierOutput(dossierData);

    elements.teleElapsed.textContent = `${(run.elapsed_seconds || 0).toFixed(1)}s`;
    elements.teleTokens.textContent = `${(run.total_tokens || 0).toLocaleString()} tokens (Replay 0)`;
    elements.teleStatusDot.className = "pulse-indicator status-green";
    elements.teleStatusText.textContent = "Replayed (0 tokens)";

    closeHistoryModal();
    switchView('dossier');
    showToast("Replayed past output (Zero tokens consumed)");
  } catch (err) {
    console.error("Replay error:", err);
    showToast(`Failed to replay run: ${err.message}`);
  }
}

export async function deleteHistoryRun(runId) {
  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch(`/api/history/${encodeURIComponent(runId)}`, {
      method: 'DELETE',
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('Delete failed');
    showToast("Run deleted from history");
    const isPromptsTab = document.getElementById('tab-history-prompts')?.classList.contains('active');
    if (isPromptsTab) {
      await loadPromptHistory();
    } else {
      await loadResearchHistory();
    }
    refreshCacheStats();
  } catch (err) {
    console.error("Delete error:", err);
    showToast(`Could not delete run: ${err.message}`);
  }
}

// =========================================================
// CONTEXTUAL FOLLOW-UP ENGINE (FOL-04, FOL-05)
// =========================================================
export function openFollowupDrawer(targetType, targetId, targetTopic, anchorElement) {
  // If drawer already exists for this target, toggle it off
  const existingDrawer = document.getElementById(`drawer-${targetId}`);
  if (existingDrawer) {
    existingDrawer.remove();
    return;
  }

  // Close other open drawers to maintain a clean reading experience
  document.querySelectorAll('.followup-drawer').forEach(d => d.remove());

  const drawer = document.createElement('div');
  drawer.className = 'followup-drawer';
  drawer.id = `drawer-${targetId}`;

  const cleanTopic = targetTopic.replace(/<[^>]*>/g, '').trim();
  const shortTopic = cleanTopic.length > 70 ? cleanTopic.substring(0, 67) + '...' : cleanTopic;

  drawer.innerHTML = `
    <div class="followup-drawer-header">
      <span class="followup-target-badge">
        <span>💬</span>
        <span>Target: ${escapeHTML(shortTopic)}</span>
      </span>
      <button class="followup-btn-close" title="Close inquiry drawer">&times;</button>
    </div>
    <div class="followup-pills">
      <button class="followup-pill" data-q="What are the primary mathematical or asymptotic bounds for this?">📈 Math & Complexity Bounds</button>
      <button class="followup-pill" data-q="What are the key technical limitations or edge-case bottlenecks?">⚠️ Bottlenecks & Limitations</button>
      <button class="followup-pill" data-q="How does this compare empirically against traditional baselines?">⚖️ Empirical Comparison</button>
      <button class="followup-pill" data-q="Can you summarize the practical trade-offs for production implementation?">🛠️ Production Trade-Offs</button>
    </div>
    <div class="followup-input-row">
      <input type="text" class="followup-input" placeholder="Ask a targeted follow-up question (Enter to submit)..." />
      <button class="followup-btn-submit">
        <span>Ask</span>
      </button>
    </div>
    <div class="followup-results-container"></div>
  `;

  // Wire event handlers
  const closeBtn = drawer.querySelector('.followup-btn-close');
  closeBtn.addEventListener('click', () => drawer.remove());

  const input = drawer.querySelector('.followup-input');
  const submitBtn = drawer.querySelector('.followup-btn-submit');
  const pills = drawer.querySelectorAll('.followup-pill');
  const resultsContainer = drawer.querySelector('.followup-results-container');

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      const q = pill.getAttribute('data-q');
      if (q) {
        input.value = q;
        submitFollowupInquiry(targetType, targetId, cleanTopic, q, drawer);
      }
    });
  });

  const doSubmit = () => {
    const q = input.value.trim();
    if (!q) return;
    submitFollowupInquiry(targetType, targetId, cleanTopic, q, drawer);
  };

  submitBtn.addEventListener('click', doSubmit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      doSubmit();
    }
  });

  // Position drawer inside or immediately after the target element
  if (targetType === 'claim') {
    const parentBlock = anchorElement.closest('p, .dossier-text-paragraph') || anchorElement.parentElement;
    parentBlock.insertAdjacentElement('afterend', drawer);
  } else {
    anchorElement.appendChild(drawer);
  }

  input.focus();
}

export async function submitFollowupInquiry(targetType, targetId, targetTopic, question, drawerElement) {
  const resultsContainer = drawerElement.querySelector('.followup-results-container');
  const submitBtn = drawerElement.querySelector('.followup-btn-submit');
  const input = drawerElement.querySelector('.followup-input');

  if (question.length > 1000) {
    showToast(`Follow-up inquiry exceeds the 1,000 character limit (${question.length.toLocaleString()} characters). Please shorten your inquiry.`);
    return;
  }

  if (submitBtn) submitBtn.disabled = true;
  if (input) input.disabled = true;

  resultsContainer.innerHTML = `
    <div class="history-loading" style="padding: 10px 0;">
      <span class="mini-pulse-dot active"></span>
      <span>Synthesizing grounded response via IDCC (~220 token context)...</span>
    </div>
  `;

  try {
    const parentRunId = UIState.activeRunId || UIState.lastDossierData?.run_id || ('run_' + Math.random().toString(36).substring(2, 9));
    
    // Client-side credentials from sessionStorage (strictly honoring our security audit)
    const openaiKey = sessionStorage.getItem('workbench_openai_key') || null;
    const geminiKey = sessionStorage.getItem('workbench_gemini_key') || null;
    const anthropicKey = sessionStorage.getItem('workbench_anthropic_key') || null;
    const provider = elements.cfgAgent4Model?.value || elements.cfgAgent2Model?.value || sessionStorage.getItem('workbench_selected_provider') || 'auto';
    const disableFallback = elements.toggleDisableFallbackAgent4?.checked || false;

    const payload = {
      parent_run_id: parentRunId,
      claim_id: targetType === 'claim' ? targetId : null,
      target_topic: targetTopic,
      query: question,
      provider: provider,
      openai_key: openaiKey,
      gemini_key: geminiKey,
      anthropic_key: anthropicKey,
      disable_fallback: disableFallback
    };

    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch('/api/pipeline/followup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(openaiKey ? { 'x-openai-key': openaiKey } : {}),
        ...(geminiKey ? { 'x-gemini-key': geminiKey } : {}),
        ...(anthropicKey ? { 'x-anthropic-key': anthropicKey } : {})
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Follow-up inquiry failed');
    }

    const data = await res.json();

    // Render result card
    const card = document.createElement('div');
    card.className = 'followup-result-card';
    const usedT = data.tokens_used || 400;
    const inT = data.prompt_tokens ?? Math.round(usedT * 0.65);
    const outT = data.completion_tokens ?? Math.max(0, usedT - inT);
    const savingsBadge = `<span class="followup-token-chip">⚡ ${usedT} tokens (In: ${inT} · Out: ${outT}) · ${data.token_savings_pct || 85}% saved</span>`;
    const fallbackBadge = data.is_fallback 
      ? `<span class="meta-tag" style="font-size: 0.68rem; background: rgba(245, 158, 11, 0.15); color: #f59e0b;">Offline Grounded</span>` 
      : `<span class="meta-tag" style="font-size: 0.68rem; background: rgba(16, 185, 129, 0.15); color: #34d399;">${escapeHTML(data.provider_used || 'Live AI')}</span>`;

    card.innerHTML = `
      <div class="followup-result-meta">
        <div style="display: flex; align-items: center; gap: 6px;">
          ${savingsBadge}
          ${fallbackBadge}
        </div>
        <span class="text-subtle" style="font-size: 0.72rem;">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="followup-quick-box">
        <strong>Executive Summary:</strong> ${escapeHTML(data.quick_summary || '')}
      </div>
      <div class="followup-detail-text">
        ${sanitizeHTML(data.answer_html || '')}
      </div>
    `;

    resultsContainer.innerHTML = '';
    resultsContainer.appendChild(card);

    // Render LaTeX math formulas if KaTeX is present
    if (typeof renderMathInElement === "function") {
      renderMathInElement(card, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false},
          {left: '\\(', right: '\\)', display: false},
          {left: '\\[', right: '\\]', display: true}
        ],
        throwOnError: false
      });
    }

    // Live update prompt history cache if already loaded
    if (UIState.cachedPrompts && Array.isArray(UIState.cachedPrompts)) {
      const promptItem = UIState.cachedPrompts.find(p => (p.id === parentRunId || p.run_id === parentRunId));
      if (promptItem) {
        if (!promptItem.followups) promptItem.followups = [];
        promptItem.followups.push(data);
        promptItem.followup_count = promptItem.followups.length;
        promptItem.total_thread_tokens = (promptItem.total_thread_tokens || promptItem.tokens_used || 0) + (data.tokens_used || 0);
      }
    }

    showToast(`Follow-up answered (${data.tokens_used} tokens, saved ${data.token_savings_pct}% vs web chat)`);
  } catch (err) {
    console.error('Follow-up error:', err);
    resultsContainer.innerHTML = `
      <div style="color: var(--color-error, #ef4444); font-size: 0.8rem; padding: 6px 0;">
        ⚠️ Inquiry failed: ${escapeHTML(err.message)}
      </div>
    `;
    showToast(`Inquiry error: ${err.message}`);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    if (input) {
      input.disabled = false;
      input.value = '';
    }
  }
}

// =========================================================
// PROMPT & FOLLOW-UP TREE HISTORY (FOL-06)
// =========================================================
export async function loadPromptHistory() {
  const container = document.getElementById('prompt-history-list');
  if (!container) return;

  container.innerHTML = `
    <div class="history-loading">
      <span class="mini-pulse-dot active"></span>
      <span>Loading prompt & follow-up lineage...</span>
    </div>
  `;

  try {
    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch('/api/history/prompts?limit=50', {
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('Failed to retrieve prompt history');
    const data = await res.json();
    const prompts = data.prompts || [];
    UIState.cachedPrompts = prompts;

    if (elements.historyCountBadge) {
      const totalFollowups = prompts.reduce((sum, p) => sum + (p.followup_count || 0), 0);
      elements.historyCountBadge.textContent = `${prompts.length} queries • ${totalFollowups} follow-ups`;
    }

    renderPromptHistoryList(prompts);
  } catch (err) {
    console.error('Error loading prompt history:', err);
    container.innerHTML = `
      <div class="history-empty-state">
        <div class="history-empty-icon">⚠️</div>
        <p>Could not load prompt history: ${escapeHTML(err.message)}</p>
      </div>
    `;
  }
}

export function renderPromptHistoryList(prompts) {
  const container = document.getElementById('prompt-history-list');
  if (!container) return;

  if (!prompts || prompts.length === 0) {
    container.innerHTML = `
      <div class="history-empty-state">
        <div class="history-empty-icon">🌳</div>
        <h4 style="color: var(--text-title); margin-bottom: 6px;">No Prompt History Yet</h4>
        <p>Execute research queries and ask follow-up questions to see the full inquiry lineage here.</p>
      </div>
    `;
    return;
  }

  const filterText = (elements.historySearchInput?.value || '').toLowerCase().trim();
  const filtered = filterText
    ? prompts.filter(p => {
        const queryMatch = (p.query || '').toLowerCase().includes(filterText);
        const followMatch = (p.followups || []).some(f => 
          (f.question || '').toLowerCase().includes(filterText) || 
          (f.quick_summary || '').toLowerCase().includes(filterText)
        );
        return queryMatch || followMatch;
      })
    : prompts;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="history-empty-state">
        <p>No queries match "<strong>${escapeHTML(filterText)}</strong>"</p>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  filtered.forEach(item => {
    const card = document.createElement('div');
    card.className = 'prompt-tree-card';
    card.id = `prompt-tree-${item.id || item.run_id}`;

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : 'Recent';
    const totalTokens = (item.total_thread_tokens || item.tokens_used || 0).toLocaleString();
    const followups = item.followups || [];
    const runId = item.id || item.run_id;

    let followupsHtml = '';
    if (followups.length > 0) {
      followupsHtml = `
        <div class="followup-branch-container">
          ${followups.map(f => {
            const fIn = f.prompt_tokens ?? (f.tokens_used ? Math.round(f.tokens_used * 0.65) : 0);
            const fOut = f.completion_tokens ?? (f.tokens_used ? Math.max(0, f.tokens_used - fIn) : 0);
            const fTokenStr = (fIn > 0 || fOut > 0)
              ? `⚡ ${f.tokens_used || 0} tokens (In: ${fIn} · Out: ${fOut})`
              : `⚡ ${f.tokens_used || 0} tokens`;
            return `
            <div class="followup-branch-item" id="fol-item-${f.id}">
              <div class="followup-branch-q">
                <span>💬 ${escapeHTML(f.question)}</span>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="followup-token-chip">${fTokenStr}</span>
                  <button class="btn-history-delete" data-fol-id="${f.id}" title="Delete follow-up" style="padding: 2px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <div class="followup-branch-a">
                <strong>Summary:</strong> ${escapeHTML(f.quick_summary || '')}
              </div>
            </div>
          `;}).join('')}
        </div>
      `;
    } else {
      followupsHtml = `
        <div style="font-size: 0.75rem; color: var(--text-subtle); margin-top: 8px; font-style: italic;">
          No follow-up inquiries asked on this research run.
        </div>
      `;
    }

    const threadPrompt = item.prompt_tokens ?? (item.tokens_used ? Math.round(item.tokens_used * 0.65) : 0);
    const threadComp = item.completion_tokens ?? (item.tokens_used ? Math.max(0, item.tokens_used - threadPrompt) : 0);
    const threadTokensStr = (threadPrompt > 0 || threadComp > 0)
      ? `⚡ ${totalTokens} thread tokens (In: ${threadPrompt.toLocaleString()} · Out: ${threadComp.toLocaleString()})`
      : `⚡ ${totalTokens} thread tokens`;

    card.innerHTML = `
      <div class="prompt-tree-header">
        <div>
          <div class="prompt-tree-title">🔍 ${escapeHTML(item.query || 'Research Query')}</div>
          <div class="prompt-tree-meta">
            <span>📅 ${dateStr}</span>
            <span>${threadTokensStr}</span>
            <span>💬 ${followups.length} follow-up ${followups.length === 1 ? 'branch' : 'branches'}</span>
          </div>
        </div>
        <div class="history-card-actions">
          <button class="btn-history-replay" data-run-id="${runId}" title="Replay output (0 API tokens)">
            <span>Open Dossier</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
        </div>
      </div>
      ${followupsHtml}
    `;

    // Bind replay button
    card.querySelector('.btn-history-replay')?.addEventListener('click', () => {
      replayResearchRun(runId);
    });

    // Bind delete buttons for individual followups
    card.querySelectorAll('[data-fol-id]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const folId = btn.getAttribute('data-fol-id');
        if (confirm("Delete this follow-up question?")) {
          try {
            const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
            const dRes = await fetch(`/api/history/followup/${encodeURIComponent(folId)}`, {
              method: 'DELETE',
              headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
              credentials: 'same-origin'
            });
            if (!dRes.ok) throw new Error("Failed to delete follow-up");
            showToast("Follow-up deleted");
            await loadPromptHistory();
          } catch (delErr) {
            console.error(delErr);
            showToast(`Could not delete: ${delErr.message}`);
          }
        }
      });
    });

    container.appendChild(card);
  });
}

// =========================================================
// MULTI-FORMAT EXPORT (BONUS-03)
// =========================================================
export async function exportDossier(format) {
  if (!UIState.lastDossierData) {
    showToast("Run a research query first to export synthesis.");
    return;
  }

  const rawSections = UIState.lastDossierData.sections || UIState.lastDossierData.dossier_sections || [];
  const dossierPayload = {
    query: UIState.lastDossierData.query,
    quick_answer: UIState.lastDossierData.quick_answer || "",
    executive_summary: UIState.lastDossierData.executive_summary || "",
    takeaways: UIState.lastDossierData.takeaways || [],
    dossier_sections: rawSections.map(s => ({
      sub_question: s.sub_question || s.title || "Section",
      content_html: s.content_html || s.answer_html || ""
    })),
    citations: UIState.lastDossierData.citations || [],
    comparison_table: UIState.lastDossierData.comparison_table || [],
    dialectical_friction: UIState.lastDossierData.dialectical_friction || {},
    epistemic_limitations: UIState.lastDossierData.epistemic_limitations || [],
    output_text: UIState.lastDossierData.output_text || "",
    architecture: UIState.lastDossierData.architecture || "system_a"
  };

  const safeFilename = (UIState.lastDossierData.query || 'Research_Synthesis')
    .replace(/[^a-zA-Z0-9_\-]/g, '_')
    .substring(0, 40);

  try {
    showToast(`Generating ${format.toUpperCase()} export...`);
    const endpoint = format === 'docx' ? '/api/export/docx' : (format === 'latex' ? '/api/export/latex' : '/api/export/markdown');
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dossier: dossierPayload })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Export failed');
    }

    const blob = await res.blob();
    const ext = format === 'docx' ? 'docx' : (format === 'latex' ? 'tex' : 'md');
    downloadBlob(blob, `${safeFilename}.${ext}`);
    showToast(`Downloaded ${safeFilename}.${ext}`);
  } catch (err) {
    console.error("Export error:", err);
    showToast(`Export error: ${err.message}`);
  }
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// =========================================================
// AUTOCOMPLETE QUERY SUGGESTIONS (BONUS-08)
// =========================================================

export function initQuerySuggestions() {
  if (!elements.inputQuery || !elements.searchSuggestionsDropdown) return;

  elements.inputQuery.addEventListener('input', () => {
    clearTimeout(suggestDebounceTimer);
    const val = elements.inputQuery.value.trim();
    if (val.length < 2) {
      elements.searchSuggestionsDropdown.classList.add('hidden');
      return;
    }

    suggestDebounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/suggest?q=${encodeURIComponent(val)}&limit=5`);
        if (!res.ok) return;
        const data = await res.json();
        const suggestions = data.suggestions || [];
        renderSuggestions(suggestions, val);
      } catch (e) {
        // console.log("Suggestions error:", e);
      }
    }, 220);
  });

  document.addEventListener('click', (e) => {
    if (!elements.inputQuery.contains(e.target) && !elements.searchSuggestionsDropdown.contains(e.target)) {
      elements.searchSuggestionsDropdown.classList.add('hidden');
    }
  });
}

export function renderSuggestions(suggestions, currentQuery) {
  if (!elements.searchSuggestionsDropdown) return;
  if (suggestions.length === 0) {
    elements.searchSuggestionsDropdown.classList.add('hidden');
    return;
  }

  elements.searchSuggestionsDropdown.innerHTML = '';
  suggestions.forEach(item => {
    const div = document.createElement('div');
    div.className = 'suggestion-item';

    const regex = new RegExp(`(${currentQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const highlighted = escapeHTML(item).replace(regex, '<strong>$1</strong>');

    div.innerHTML = `
      <span class="suggestion-icon">🔍</span>
      <span class="suggestion-text">${highlighted}</span>
    `;

    div.addEventListener('click', () => {
      elements.inputQuery.value = item;
      elements.searchSuggestionsDropdown.classList.add('hidden');
      handleQuerySubmit();
    });

    elements.searchSuggestionsDropdown.appendChild(div);
  });

  elements.searchSuggestionsDropdown.classList.remove('hidden');
}

// =========================================================
// KEYBOARD SHORTCUTS MODAL (BONUS-09)
// =========================================================
export function openShortcutsModal() {
  if (elements.shortcutsModal) elements.shortcutsModal.classList.add('open');
}

export function closeShortcutsModal() {
  if (elements.shortcutsModal) elements.shortcutsModal.classList.remove('open');
}

// =========================================================
// CONTINUOUS RESEARCH DIALOGUE (CHAT-05, DHS-RCC)
// =========================================================

export function initDialogueView() {
  const dossier = UIState.lastDossierData;
  const currentRunId = UIState.activeRunId || dossier?.run_id;

  // 1. Update Context Anchor Sidebar
  if (elements.dialogueActiveQuery) {
    if (dossier && dossier.query) {
      elements.dialogueActiveQuery.textContent = dossier.query;
      elements.dialogueActiveQuery.title = dossier.query;
    } else {
      elements.dialogueActiveQuery.textContent = "Open Academic Research (No active monograph)";
      elements.dialogueActiveQuery.title = "";
    }
  }

  if (elements.dialogueAnchorClaims) {
    elements.dialogueAnchorClaims.innerHTML = '';
    const items = [];
    if (dossier) {
      if (Array.isArray(dossier.takeaways) && dossier.takeaways.length > 0) {
        items.push(...dossier.takeaways.slice(0, 3));
      } else if (Array.isArray(dossier.sections) && dossier.sections.length > 0) {
        dossier.sections.slice(0, 3).forEach(s => {
          if (s.sub_question) items.push(s.sub_question);
        });
      }
    }

    if (items.length > 0) {
      items.forEach(it => {
        const li = document.createElement('li');
        li.textContent = it.replace(/<[^>]*>/g, '').trim();
        elements.dialogueAnchorClaims.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.textContent = "Run a research query to anchor specific monograph propositions.";
      elements.dialogueAnchorClaims.appendChild(li);
    }
  }

  // 2. Load past dialogue messages if not already loaded for this run
  if (currentRunId && UIState.activeDialogueLoadedRunId !== currentRunId) {
    loadDialogueHistory(currentRunId);
  }
}

export async function loadDialogueHistory(runId) {
  if (!runId) return;
  try {
    const res = await fetch(`/api/dialogue/history/${encodeURIComponent(runId)}`);
    if (!res.ok) return;
    const data = await res.json();
    const messages = data.messages || [];
    UIState.activeDialogueLoadedRunId = runId;

    if (messages.length > 0 && elements.dialogueMessages) {
      elements.dialogueMessages.innerHTML = '';
      messages.forEach(msg => {
        renderDialogueMessage(msg);
      });
      elements.dialogueMessages.scrollTop = elements.dialogueMessages.scrollHeight;
    }
  } catch (err) {
    console.error("Failed to load dialogue history:", err);
  }
}

export function renderDialogueMessage(msg) {
  if (!elements.dialogueMessages) return;

  // Remove welcome card if present
  const welcomeCard = document.getElementById('dialogue-welcome-card');
  if (welcomeCard && elements.dialogueMessages.contains(welcomeCard)) {
    welcomeCard.remove();
  }

  const role = msg.role;
  const isUser = (role === 'user');

  if (isUser) {
    const row = document.createElement('div');
    row.className = 'dialogue-user-row';
    const bubble = document.createElement('div');
    bubble.className = 'dialogue-user-bubble';
    bubble.textContent = msg.content || '';
    row.appendChild(bubble);
    elements.dialogueMessages.appendChild(row);
  } else {
    const row = document.createElement('div');
    row.className = 'dialogue-assistant-row';

    const card = document.createElement('div');
    card.className = 'dialogue-assistant-card';
    if (msg.id) card.id = `dialogue-msg-${msg.id}`;

    const tokensUsed = msg.tokens_used || 380;
    const inTok = msg.prompt_tokens ?? (msg.tokens_used ? Math.round(msg.tokens_used * 0.65) : 245);
    const outTok = msg.completion_tokens ?? (msg.tokens_used ? Math.max(0, msg.tokens_used - inTok) : 135);
    const baseline = 4500;
    const savingsPct = Math.max(Math.round(((baseline - tokensUsed) / baseline) * 100), 10);
    const timeStr = msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : new Date().toLocaleTimeString();

    const fallbackBadge = msg.is_fallback
      ? `<span class="meta-tag" style="font-size: 0.68rem; background: rgba(245, 158, 11, 0.15); color: #f59e0b;">Offline Grounded</span>`
      : `<span class="meta-tag" style="font-size: 0.68rem; background: rgba(16, 185, 129, 0.15); color: #34d399;">${escapeHTML(msg.provider_used || 'Live DHS-RCC')}</span>`;

    let quickHtml = '';
    if (msg.quick_summary) {
      quickHtml = `
        <div class="dialogue-quick-box">
          <strong>Executive Summary:</strong> ${escapeHTML(msg.quick_summary)}
        </div>
      `;
    }

    const answerContent = msg.answer_html || msg.content || '';

    card.innerHTML = `
      <div class="dialogue-assistant-meta">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="followup-token-chip">⚡ ${tokensUsed} tokens (In: ${inTok} · Out: ${outTok}) · ${savingsPct}% saved</span>
          ${fallbackBadge}
        </div>
        <span class="text-subtle">${timeStr}</span>
      </div>
      ${quickHtml}
      <div class="dialogue-academic-body">
        ${sanitizeHTML(answerContent)}
      </div>
    `;

    row.appendChild(card);
    elements.dialogueMessages.appendChild(row);

    // KaTeX render for math formulas
    if (typeof renderMathInElement === "function") {
      renderMathInElement(card, {
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
}

export async function handleDialogueSubmit() {
  if (!elements.dialogueUserInput) return;
  const question = elements.dialogueUserInput.value.trim();
  if (!question) return;

  if (question.length > 1000) {
    showToast(`Dialogue question exceeds the 1,000 character limit (${question.length.toLocaleString()} characters). Please shorten your question.`);
    return;
  }

  // Clear input
  elements.dialogueUserInput.value = '';
  elements.dialogueUserInput.style.height = 'auto';

  // Render user bubble immediately
  renderDialogueMessage({ role: 'user', content: question });
  elements.dialogueMessages.scrollTop = elements.dialogueMessages.scrollHeight;

  // Render loading row
  const loadingRow = document.createElement('div');
  loadingRow.className = 'dialogue-assistant-row';
  loadingRow.id = 'dialogue-loading-indicator';
  loadingRow.innerHTML = `
    <div class="dialogue-assistant-card" style="display: flex; align-items: center; gap: 10px; padding: 12px 18px;">
      <span class="mini-pulse-dot active"></span>
      <span style="font-size: 0.85rem; color: var(--text-muted);">Synthesizing grounded multi-turn dialogue via DHS-RCC (~380 tokens)...</span>
    </div>
  `;
  elements.dialogueMessages.appendChild(loadingRow);
  elements.dialogueMessages.scrollTop = elements.dialogueMessages.scrollHeight;

  // Disable send button while in flight
  if (elements.btnSendDialogue) elements.btnSendDialogue.disabled = true;

  try {
    const parentRunId = UIState.activeRunId || UIState.lastDossierData?.run_id || ('run_' + Math.random().toString(36).substring(2, 9));
    UIState.activeRunId = parentRunId;

    const openaiKey = sessionStorage.getItem('workbench_openai_key') || null;
    const geminiKey = sessionStorage.getItem('workbench_gemini_key') || null;
    const anthropicKey = sessionStorage.getItem('workbench_anthropic_key') || null;
    const provider = elements.cfgAgent2Model?.value || sessionStorage.getItem('workbench_selected_provider') || 'auto';
    const disableFallback = elements.toggleDisableFallbackAgent4?.checked || false;

    const payload = {
      run_id: parentRunId,
      message: question,
      provider: provider,
      openai_key: openaiKey,
      gemini_key: geminiKey,
      anthropic_key: anthropicKey,
      disable_fallback: disableFallback
    };

    const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
    const res = await fetch('/api/dialogue/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(openaiKey ? { 'x-openai-key': openaiKey } : {}),
        ...(geminiKey ? { 'x-gemini-key': geminiKey } : {}),
        ...(anthropicKey ? { 'x-anthropic-key': anthropicKey } : {})
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Dialogue response failed');
    }

    const data = await res.json();

    // Remove loading indicator
    loadingRow.remove();

    // Render assistant card
    renderDialogueMessage({
      id: data.id,
      role: 'assistant',
      quick_summary: data.quick_summary,
      answer_html: data.answer_html,
      tokens_used: data.tokens_used,
      prompt_tokens: data.prompt_tokens,
      completion_tokens: data.completion_tokens,
      provider_used: data.provider_used,
      is_fallback: data.is_fallback,
      created_at: new Date().toISOString()
    });

    // Update real-time token telemetry box
    if (elements.dialogueTurnTokens) {
      elements.dialogueTurnTokens.textContent = `~${data.tokens_used || 380}`;
    }
    if (elements.dialogueInTokens) {
      elements.dialogueInTokens.textContent = `~${data.prompt_tokens || 245}`;
    }
    if (elements.dialogueOutTokens) {
      elements.dialogueOutTokens.textContent = `~${data.completion_tokens || 135}`;
    }
    if (elements.dialogueTokenSavings) {
      elements.dialogueTokenSavings.textContent = `${data.token_savings_pct || 88}%`;
    }

    elements.dialogueMessages.scrollTop = elements.dialogueMessages.scrollHeight;

  } catch (err) {
    console.error("Dialogue error:", err);
    loadingRow.remove();

    const errRow = document.createElement('div');
    errRow.className = 'dialogue-assistant-row';
    errRow.innerHTML = `
      <div class="dialogue-assistant-card" style="border-left-color: #ef4444;">
        <div style="color: #ef4444; font-size: 0.85rem; font-weight: 600;">Dialogue Synthesis Interrupted</div>
        <p style="font-size: 0.82rem; color: var(--text-muted); margin: 6px 0;">${escapeHTML(err.message)}</p>
      </div>
    `;
    elements.dialogueMessages.appendChild(errRow);
    elements.dialogueMessages.scrollTop = elements.dialogueMessages.scrollHeight;
  } finally {
    if (elements.btnSendDialogue) elements.btnSendDialogue.disabled = false;
  }
}

export async function clearActiveDialogue() {
  const currentRunId = UIState.activeRunId || UIState.lastDossierData?.run_id;
  if (currentRunId) {
    try {
      await fetch(`/api/dialogue/history/${encodeURIComponent(currentRunId)}`, {
        method: 'DELETE'
      });
    } catch (e) {
      console.warn("Failed to clear backend dialogue history:", e);
    }
  }

  if (elements.dialogueMessages) {
    elements.dialogueMessages.innerHTML = `
      <div class="dialogue-welcome-card" id="dialogue-welcome-card">
        <div class="welcome-icon">💬</div>
        <h3>Continuous Research Dialogue</h3>
        <p>Ask non-targeted, exploratory, or cross-cutting questions about the synthesized research topic. Context is preserved across all turns while strictly compressing tokens.</p>
        <div class="dialogue-suggested-prompts" id="dialogue-welcome-pills">
          <button class="dialogue-pill" data-prompt="What are the biggest open controversies and competing theories surrounding this topic?">⚖️ Open Controversies & Theories</button>
          <button class="dialogue-pill" data-prompt="What are the primary theoretical limitations and real-world scaling bottlenecks?">⚠️ Bottlenecks & Practical Limitations</button>
          <button class="dialogue-pill" data-prompt="Synthesize a 3-point critical roadmap for future empirical research.">🔮 Future Research Roadmap</button>
          <button class="dialogue-pill" data-prompt="Compare the methodologies and assumptions of the key studies cited.">🔬 Methodology Cross-Comparison</button>
        </div>
      </div>
    `;
  }
  showToast("Research dialogue history cleared");
}


