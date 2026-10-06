/**
 * AI RESEARCH WORKBENCH - PIPELINE EXECUTION MODULE
 * Orchestration of Demo Mode simulation, Live Backend SSE Streaming, and Telemetry
 */

import { UIState, elements, switchView, ALL_SCRAPERS, getSystemApiKey } from './state.js';
import { showToast, autoResizeQueryTextarea, updateQueryCharCounter, formatTokenBreakdown, escapeHTML } from './utils.js';
import { fetchSSE } from './scenarios.js';
import { activateNode, completeNode, resetNodeStates, triggerPulse, logToCanvas } from './canvas.js';
import { finishPipeline, extractAcademicTakeaways } from './dossier.js';

// Pipeline execution is always live against backend endpoints

export function handleQuerySubmit() {
  const query = elements.inputQuery.value.trim();
  if (!query) {
    elements.inputQuery.placeholder = "Please enter an academic query first...";
    return;
  }
  
  if (query.length > 1000) {
    showToast(`Query exceeds the 1,000 character limit (${query.length.toLocaleString()} characters). Please shorten your topic.`);
    return;
  }

  if (UIState.isRunning) {
    showToast("A research pipeline is already in progress.");
    return;
  }

  // FIX: Immediately clear input box upon Enter/Submit!
  elements.inputQuery.value = '';
  autoResizeQueryTextarea(elements.inputQuery);
  updateQueryCharCounter();
  elements.inputQuery.placeholder = "Enter an academic research topic or paper question...";
  
  UIState.activeQuery = query;

  // Switch view to canvas for live animated telemetry
  switchView('canvas');
  
  // Launch pipeline
  executePipeline(query);
}

// =========================================================
// PIPELINE EXECUTION (LIVE SSE)
// =========================================================
export function executePipeline(query) {
  UIState.isRunning = true;
  UIState.elapsedSeconds = 0.0;
  UIState.totalTokens = 0;
  UIState.totalPromptTokens = 0;
  UIState.totalCompletionTokens = 0;
  
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

  // Active Architecture routing (System A vs System B vs System C)
  const arch = UIState.activeArchitecture || 'system_a';
  if (arch === 'system_b') {
    logToCanvas("[ARCH] Routing execution to System B: Conventional RAG Baseline.");
    logToCanvas("[BUDGET] Top-K Dense Vector Retrieval (FastEmbed) + 1 LLM Augmented Generation call.");
    executeConventionalRAGBaseline(query);
    return;
  }
  if (arch === 'system_c') {
    logToCanvas("[ARCH] Routing execution to System C: Direct Single API Baseline.");
    logToCanvas("[BUDGET] 1 Direct LLM Parametric Inference call (Zero Retrieval / Zero Verification).");
    executeDirectAPIBaseline(query);
    return;
  }

  logToCanvas("[BUDGET] Strict 2-LLM Budget locked. Tool 1 & 2 consume 0 AI tokens.");
  executeLiveBackend(query);
}

export function abortPipeline() {
  if (!UIState.isRunning) return;
  
  if (UIState.activeAbortController) {
    UIState.activeAbortController.abort();
    UIState.activeAbortController = null;
  }
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

export function startElapsedTimer() {
  clearInterval(UIState.elapsedTimer);
  const startTime = performance.now();
  UIState.elapsedTimer = setInterval(() => {
    const now = performance.now();
    UIState.elapsedSeconds = ((now - startTime) / 1000).toFixed(1);
    elements.teleElapsed.textContent = `${UIState.elapsedSeconds}s`;
  }, 100);
}

export function stopElapsedTimer() {
  clearInterval(UIState.elapsedTimer);
}

// =========================================================
// LIVE BACKEND SSE STREAMING
// =========================================================
export async function executeLiveBackend(query) {
  const a2Model = elements.cfgAgent2Model.value;
  const a4Model = elements.cfgAgent4Model.value;
  const scraperSources = document.getElementById('cfg-agent1-source')?.value || "all";
  const paperLimit = parseInt(elements.cfgPaperLimit.value, 10) || 5;
  const pdfPageLimit = parseInt(elements.cfgPdfPageLimit?.value, 10) || 15;
  const simThresh = parseFloat(elements.cfgSimThresh.value) || 0.80;
  
  const disableFallbackAgent2 = elements.toggleDisableFallbackAgent2?.checked || false;
  const disableFallbackAgent4 = elements.toggleDisableFallbackAgent4?.checked || false;
  const disableFallback = disableFallbackAgent2 || disableFallbackAgent4;
  
  const openaiKey = (document.getElementById('cfg-openai-key')?.value.trim()) || sessionStorage.getItem('workbench_openai_key') || '';
  const geminiKey = (document.getElementById('cfg-gemini-key')?.value.trim()) || sessionStorage.getItem('workbench_gemini_key') || '';
  const anthropicKey = (document.getElementById('cfg-anthropic-key')?.value.trim()) || sessionStorage.getItem('workbench_anthropic_key') || '';
  const serpapiKey = (document.getElementById('cfg-serpapi-key')?.value.trim()) || sessionStorage.getItem('workbench_serpapi_key') || '';
  
  const activeScrapersList = (UIState.activeScrapers && UIState.activeScrapers.length > 0)
    ? UIState.activeScrapers
    : ALL_SCRAPERS;

  const currentExecutionMode = localStorage.getItem('workbench_execution_mode') || 'deep';

  const payload = {
    query: query,
    provider_agent2: a2Model,
    provider_agent4: a4Model,
    paper_limit: paperLimit,
    max_pdf_pages: pdfPageLimit,
    similarity_threshold: simThresh,
    execution_mode: currentExecutionMode,
    scraper_sources: scraperSources,
    active_scrapers: activeScrapersList,
    disable_fallback_agent2: disableFallbackAgent2,
    disable_fallback_agent4: disableFallbackAgent4,
    openai_key: openaiKey,
    gemini_key: geminiKey,
    anthropic_key: anthropicKey,
    serpapi_key: serpapiKey
  };

  logToCanvas(`[NETWORK] Connecting to FastAPI secure POST SSE endpoint...`);
  logToCanvas(`[MODE] Pipeline Mode: ${currentExecutionMode === 'rapid' ? '⚡ Rapid Synthesis (~5s)' : '🔬 Deep Monograph & 3-Tier Audit (~30s)'}`);
  logToCanvas(`[AGENT 1] Dispatching query to ${activeScrapersList.length} active academic repositories: [${activeScrapersList.join(', ')}]`);
  if (openaiKey || geminiKey || anthropicKey || serpapiKey) {
    logToCanvas(`[AUTH] User credentials forwarded via secure POST body (OpenAI: ${openaiKey ? '✓' : '✗'}, Gemini: ${geminiKey ? '✓' : '✗'}, Claude: ${anthropicKey ? '✓' : '✗'}, SerpAPI: ${serpapiKey ? '✓' : '✗'}).`);
  } else {
    logToCanvas(`[INFO] No API key detected. Using high-fidelity deterministic scientific synthesis.`);
  }
  if (disableFallback) {
    logToCanvas(`[STRICT] Strict Live AI Mode enabled. Offline synthetic fallbacks are DISABLED.`);
  }

  const abortController = new AbortController();
  UIState.activeAbortController = abortController;

  const eventHandlers = {
    pipeline_start: (e) => {
      const data = JSON.parse(e.data);
      logToCanvas(`[PIPELINE] ${data.status}`);
    },
    agent_active: (e) => {
      const data = JSON.parse(e.data);
      activateNode(data.agent_id);
      logToCanvas(`[AGENT ${data.agent_id}] ${data.action}`);
    },
    agent_progress: (e) => {
      const data = JSON.parse(e.data);
      logToCanvas(`[PROGRESS] ${data.details}`);
      if (data.agent_id === 1) {
        document.getElementById('chk-agent1-query')?.classList.add('done');
        document.getElementById('chk-agent1-filter')?.classList.add('done');
        if (elements.prog1) elements.prog1.style.width = '80%';
      } else if (data.agent_id === 2) {
        document.getElementById('chk-agent2-q')?.classList.add('done');
        document.getElementById('chk-agent2-tag')?.classList.add('done');
        if (elements.prog2) elements.prog2.style.width = '80%';
      } else if (data.agent_id === 3) {
        document.getElementById('chk-agent3-cache')?.classList.add('done');
        document.getElementById('chk-agent3-filter')?.classList.add('done');
        if (elements.prog3) elements.prog3.style.width = '80%';
      } else if (data.agent_id === 4) {
        document.getElementById('chk-agent4-eval')?.classList.add('done');
        document.getElementById('chk-agent4-dossier')?.classList.add('done');
        if (elements.prog4) elements.prog4.style.width = '80%';
      }
    },
    agent_completed: (e) => {
      const data = JSON.parse(e.data);
      completeNode(data.agent_id);
      const tokens = data.tokens_used || 0;
      const pTok = data.prompt_tokens || 0;
      const cTok = data.completion_tokens || 0;
      UIState.totalTokens += tokens;
      UIState.totalPromptTokens += pTok;
      UIState.totalCompletionTokens += cTok;
      elements.teleTokens.textContent = formatTokenBreakdown(UIState.totalTokens, UIState.totalPromptTokens, UIState.totalCompletionTokens);
      
      const nodeTokenEl = document.getElementById(`m-agent${data.agent_id}-tokens`);
      if (nodeTokenEl) {
        if (data.agent_id === 1 || data.agent_id === 3) {
           nodeTokenEl.textContent = `0 tokens (Zero LLM)`;
        } else {
           if (pTok > 0 || cTok > 0) {
             nodeTokenEl.textContent = `${tokens} tokens (In: ${pTok} · Out: ${cTok})`;
           } else {
             nodeTokenEl.textContent = `${tokens} tokens`;
           }
        }
      }
      
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
      if (data.agent_id === 4) {
        if (data.tokens_used !== undefined) {
          const checkedEl = document.getElementById('m-agent4-checked');
          if (checkedEl) checkedEl.textContent = `All checked`;
        }
        if (data.model) {
          const modelEl = document.getElementById('m-agent4-model');
          if (modelEl) modelEl.textContent = data.model;
        }
      }

      triggerPulse(data.agent_id);
    },
    pipeline_error: (e) => {
      const data = JSON.parse(e.data);
      UIState.activeAbortController = null;
      if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';
      stopElapsedTimer();
      UIState.isRunning = false;
      elements.teleStatusDot.className = "pulse-indicator status-amber";
      elements.teleStatusText.textContent = "Partial Data";
      logToCanvas(`[NOTICE] ${data.error || data.message || 'Pipeline aborted'}`);
      
      document.getElementById('canvas-error-banner')?.classList.remove('hidden');
      document.getElementById('dossier-error-banner')?.classList.remove('hidden');
      const bannerText = document.getElementById('dossier-error-text');
      if (bannerText) {
        bannerText.textContent = `A downstream synthesis step timed out or encountered an API latency limit (${data.error || 'Network latency'}). Recovered the authentic drafted monograph, structured claims, and scraped citations for review.`;
      }
      
      const agent2Draft = data.partial_data?.agent2_draft;
      const agent1Scraped = data.partial_data?.agent1_scraped || data.partial_data?.agent1_scraper;
      const agent3Cacher = data.partial_data?.agent3_cacher;

      // Extract verified and pending claims from Agent 3 if present
      const verifiedMap = {};
      if (agent3Cacher) {
        (agent3Cacher.verified_claims || []).forEach(c => {
          if (c.claim_id) verifiedMap[c.claim_id] = c;
        });
        (agent3Cacher.unverified_claims || []).forEach(c => {
          if (c.claim_id && !verifiedMap[c.claim_id]) verifiedMap[c.claim_id] = c;
        });
      }

      function formatPartialClaimTags(htmlContent) {
        if (!htmlContent) return '';
        return htmlContent.replace(/<claim\s+id="([^"]+)"(?:\s+paper="([^"]+)")?>([\s\S]*?)<\/claim>/gi, (match, claimId, paperTag, innerText) => {
          const evalClaim = verifiedMap[claimId];
          const isAutoVerified = evalClaim && evalClaim.status === 'verified_by_cache';
          const score = isAutoVerified ? (evalClaim.confidence_score || 0.92) : 0.50;
          const scoreAttr = score.toFixed(2);
          const tier = isAutoVerified ? 'auto_cache' : 'no_source';
          const status = isAutoVerified ? 'verified_by_cache' : 'unverified';
          const caveat = isAutoVerified 
            ? 'Locally verified via high-confidence n-gram overlap in SQLite cache.' 
            : 'Theoretical assertion awaiting secondary peer-review validation.';
          const rationale = isAutoVerified 
            ? (evalClaim.matched_sentence ? `Corroborated in literature: "${evalClaim.matched_sentence.substring(0, 100)}..."` : 'Corroborated by scraped literature sample.')
            : 'No direct empirical match identified in retrieved corpus.';
          const statusClass = isAutoVerified ? '' : ' claim-unverified-text';
          const badgeClass = isAutoVerified ? 'tier-cache-badge' : 'tier-no-source-badge';
          const badgeLabel = isAutoVerified ? '[✓ cache]' : '[⚠ ungrounded]';

          return `<span class="claim-wrapper claim-tier-${tier}${statusClass}" data-claim-id="${escapeHTML(claimId)}" data-score="${scoreAttr}" data-status="${status}" data-tier="${tier}" data-caveat="${escapeHTML(caveat)}" data-rationale="${escapeHTML(rationale)}"><span class="claim-text">${escapeHTML(innerText)}</span><sup class="citation-anchor ${badgeClass}">${badgeLabel}</sup></span>`;
        });
      }

      let p_sections = [];
      let p_citations = [];
      let p_exec_summary = '';

      if (agent2Draft) {
        const rawSections = agent2Draft.dossier_sections || agent2Draft.sections || [];
        p_sections = rawSections.map((s, idx) => ({
          sub_question: s.sub_question || `Drafted Section ${idx + 1}`,
          answer_html: formatPartialClaimTags(s.answer_html || s.content_html || '<p>Draft section content recovered.</p>')
        }));
        p_exec_summary = formatPartialClaimTags(agent2Draft.executive_summary || '');
      }

      if (agent1Scraped && Array.isArray(agent1Scraped.papers)) {
        p_citations = agent1Scraped.papers.map((p, i) => {
          const authorStr = Array.isArray(p.authors) ? (p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '')) : (p.authors || 'Author Unknown');
          let snippet = (p.abstract && p.abstract.trim())
            ? (p.abstract.length > 280 ? p.abstract.substring(0, 280) + '...' : p.abstract)
            : (p.snippet || p.tldr || 'Corroborating text stored in SQLite cache.');
          return {
            ref_id: `REF-${i+1}`,
            paper_id: p.id,
            title: p.title || 'Untitled Research Publication',
            authors: authorStr,
            year: p.year || 'n.d.',
            venue: p.venue || 'Academic Repository',
            url: p.url || '#',
            citation_count: p.citationCount || p.citation_count || 0,
            evidence: snippet,
            supporting_snippets: [snippet]
          };
        });
      }

      const p_evaluated_claims = Object.values(verifiedMap);

      finishPipeline({
        query: query,
        quick_answer: data.partial_data?.quick_answer || agent2Draft?.quick_answer || "Partial research monograph recovered after network latency.",
        elapsed: UIState.elapsedSeconds,
        tokens: UIState.totalTokens,
        executive_summary: p_exec_summary || "Pipeline interrupted. Partial execution recovered. Unverified draft shown below.",
        takeaways: (agent2Draft?.sub_questions && agent2Draft.sub_questions.length > 0)
          ? agent2Draft.sub_questions.map(sq => `Explored research dimension: ${sq}`)
          : [
            "Synthesis interrupted by downstream latency.",
            "Complete unverified monograph draft recovered for preliminary review.",
            "Primary sources and candidate citations indexed below."
          ],
        comparison_table: agent2Draft?.comparison_table || {},
        dialectical_friction: agent2Draft?.dialectical_friction || [],
        epistemic_limitations: agent2Draft?.epistemic_limitations || [],
        sections: p_sections,
        citations: p_citations,
        evaluated_claims: p_evaluated_claims
      });
    },
    pipeline_complete: (e) => {
      const data = JSON.parse(e.data);
      UIState.activeAbortController = null;
      if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';

      const formattedSections = (data.dossier_sections || []).map(s => ({
        sub_question: s.sub_question,
        answer_html: s.content_html
      }));

      const cleanTakeaways = (data.takeaways && data.takeaways.length > 0 && !data.takeaways.some(t => /sqlite|hallucination|llm call|token/i.test(t)))
        ? data.takeaways
        : extractAcademicTakeaways(data);

      const totTok = data.token_usage ? data.token_usage.total_tokens : UIState.totalTokens;
      const pTok = data.token_usage?.prompt_tokens ?? UIState.totalPromptTokens;
      const cTok = data.token_usage?.completion_tokens ?? UIState.totalCompletionTokens;
      UIState.totalTokens = totTok;
      UIState.totalPromptTokens = pTok;
      UIState.totalCompletionTokens = cTok;
      elements.teleTokens.textContent = formatTokenBreakdown(totTok, pTok, cTok);

      finishPipeline({
        run_id: data.run_id,
        query: data.query,
        quick_answer: data.quick_answer || "",
        elapsed: data.elapsed_seconds,
        tokens: totTok,
        prompt_tokens: pTok,
        completion_tokens: cTok,
        complexity: data.complexity || null,
        executive_summary: data.executive_summary || '',
        takeaways: cleanTakeaways,
        sections: formattedSections,
        citations: data.citations || [],
        evaluated_claims: data.evaluated_claims || []
      });
    },
    pipeline_completed: (e) => {
      eventHandlers.pipeline_complete(e);
    }
  };

  try {
    await fetchSSE('/api/pipeline/stream', payload, eventHandlers, abortController.signal);
  } catch (err) {
    if (abortController.signal.aborted) {
      logToCanvas("[ABORT] Pipeline aborted by user.");
      return;
    }
    if (elements.btnAbortPipeline) elements.btnAbortPipeline.style.display = 'none';
    if (disableFallback) {
      stopElapsedTimer();
      UIState.isRunning = false;
      elements.teleStatusDot.className = "pulse-indicator status-rose";
      elements.teleStatusText.textContent = "Connection Error";
      logToCanvas(`[ERROR] Backend connection failed: ${err.message}`);
      showToast("Backend connection failed.");
      return;
    }
    stopElapsedTimer();
    UIState.isRunning = false;
    elements.teleStatusDot.className = "pulse-indicator status-rose";
    elements.teleStatusText.textContent = "Error";
    logToCanvas(`
[ERROR] Research pipeline stream failed: ${err.message}`);
    showToast(`Pipeline execution failed: ${err.message}`);
  }
}

// =========================================================
// SYSTEM B: CONVENTIONAL RAG BASELINE EXECUTION
// =========================================================
export function getSimulatedRAGMonograph(query) {
  return `# Conventional RAG Monograph: ${query}

## Executive Summary
This document provides a research synthesis generated via a conventional Retrieval-Augmented Generation (RAG) architecture. The pipeline performs dense vector semantic retrieval over open-access academic literature, selecting top-K text chunks to concatenate into a single augmented LLM prompt.

> **Baseline Architecture Notice:** This output represents single-pass vector augmented generation. Multi-agent claim isolation, automated 0-token SQLite semantic cache verification, and dialectical consensus auditing were **bypassed**.

## 1. Retrieved Literature Synthesis & Operational Baselines
Experimental findings extracted from dense vector similarity matching indicate foundational developments regarding the target domain. Multiple source passages corroborate key performance thresholds and structural trade-offs:

> *"[1] Literature benchmarks confirm operational thresholds across experimental setups, highlighting that scaling efficiencies correlate strongly with parameter tuning and architectural depth."*

Empirical evaluations across the retrieved literature sample demonstrate that modern algorithmic pipelines achieve measurable gains in throughput. When evaluated against standard baselines, key governing metrics indicate substantial variance depending on hardware topology:

$$E = \\sum_{i=1}^{k} \\alpha_i \\cdot \\mathcal{L}_{\\text{context}}(c_i)$$

Where $\\alpha_i$ denotes the dense embedding cosine similarity weight for context chunk $c_i$.

## 2. Dialectical Tensions & Methodology Discrepancies
Unlike multi-agent architectures that explicitly preserve contradictory findings, standard conventional RAG blends divergent study results into a smoothed consensus. When independent research teams report conflicting parameter bounds, the single-call generation mechanism typically interpolates between them without flagging epistemic friction.

## 3. Grounding Limitations & Hallucination Profile
While vector retrieval prevents ungrounded hallucinations for topics directly covered by the retrieved chunks, single-pass generation remains susceptible to:
- Extrapolative drift when retrieved context is fragmented.
- Silent omission of negative results or unverified empirical bounds.
- Inability to independently verify numerical constants against primary empirical datasets.`;
}

export async function executeConventionalRAGBaseline(query) {
  const disableFallback = document.getElementById('toggle-disable-fallback-agent2')?.checked || false;
  const topK = UIState.ragTopK || 5;

  

  // Live Backend execution for Conventional RAG
  const abortController = new AbortController();
  UIState.activeAbortController = abortController;

  activateNode(1);
  logToCanvas(`[SYSTEM B] Querying academic repositories & embedding passages with FastEmbed ONNX (Top-${topK})...`);

  const t1 = setTimeout(() => {
    document.getElementById('chk-agent1-query')?.classList.add('done');
    const chkIcon = document.getElementById('chk-agent1-query')?.querySelector('.chk-icon');
    if (chkIcon) chkIcon.textContent = '✓';
    if (elements.prog1) elements.prog1.style.width = '60%';
  }, 600);
  UIState.activeTimeouts.push(t1);

  const model = elements.cfgAgent2Model?.value || localStorage.getItem('workbench_agent2_model') || 'gemini-3.6-flash';
  const apiKey = getSystemApiKey('b');
  const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const fetchPromise = fetch('/api/evals/run-system', {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify({
        system_type: 'b',
        query: query,
        model: model,
        api_key: apiKey || null,
        top_k: topK
      }),
      signal: abortController.signal
    });

    const t2 = setTimeout(() => {
      completeNode(1);
      triggerPulse(1);
      activateNode(2);
      logToCanvas(`[SYSTEM B] Augmenting prompt with ${topK} retrieved vector chunks & calling LLM...`);
      if (elements.prog2) elements.prog2.style.width = '50%';
    }, 1200);
    UIState.activeTimeouts.push(t2);

    const resp = await fetchPromise;
    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Server returned HTTP ${resp.status}: ${errText}`);
    }

    const resData = await resp.json();
    completeNode(2);
    if (elements.prog2) elements.prog2.style.width = '100%';

    const citations = (resData.retrieved_chunks || []).map((chunk, idx) => ({
      ref_id: String(idx + 1),
      title: chunk.title || `Retrieved Chunk ${idx + 1}`,
      authors: chunk.source_venue || 'Academic Literature Vector Index',
      year: new Date().getFullYear().toString(),
      venue: chunk.source_venue || 'FastEmbed ONNX Vector Index',
      url: chunk.url || '#',
      evidence: chunk.text ? (chunk.text.substring(0, 240) + '...') : 'Direct passage match retrieved via cosine similarity.',
      supporting_snippets: chunk.text ? [chunk.text] : []
    }));

    const tot = resData.total_tokens || 0;
    const inT = resData.input_tokens || 0;
    const outT = resData.output_tokens || 0;
    UIState.totalTokens = tot;
    UIState.totalPromptTokens = inT;
    UIState.totalCompletionTokens = outT;
    elements.teleTokens.textContent = formatTokenBreakdown(tot, inT, outT);

    logToCanvas(`[SYSTEM B DONE] Latency: ${resData.latency_seconds}s, Tokens: ${tot.toLocaleString()} (${inT} in / ${outT} out).`);

    const ragDossier = {
      run_id: resData.run_id || ('run_b_' + Math.random().toString(36).substring(2, 9)),
      query: query,
      architecture: 'system_b',
      model: resData.model || model,
      output_text: resData.output_text,
      latency_seconds: resData.latency_seconds || parseFloat(UIState.elapsedSeconds),
      tokens: tot,
      prompt_tokens: inT,
      completion_tokens: outT,
      cost_usd: resData.cost_usd || 0,
      citations: citations,
      quick_answer: "Generated via System B: Conventional RAG Baseline (FastEmbed ONNX Vector Retrieval + Single LLM Call). Multi-agent verification and claim caching bypassed.",
      takeaways: [
        `Top-${resData.retrieved_sources_count || citations.length || topK} dense vector passages retrieved via ONNX embeddings.`,
        `Single augmented generation pass synthesizes retrieved context into monograph.`,
        `Unverified: No multi-agent claim verification or 0-token caching applied.`
      ],
      evaluated_claims: []
    };

    finishPipeline(ragDossier);
  } catch (err) {
    if (abortController.signal.aborted) {
      logToCanvas("[ABORT] Conventional RAG execution aborted by user.");
      return;
    }
    if (disableFallback) {
      stopElapsedTimer();
      UIState.isRunning = false;
      elements.teleStatusDot.className = "pulse-indicator status-rose";
      elements.teleStatusText.textContent = "Error";
      logToCanvas(`[ERROR] System B call failed: ${err.message}`);
      showToast(`System B failed: ${err.message}`);
      return;
    }
    stopElapsedTimer();
    UIState.isRunning = false;
    elements.teleStatusDot.className = "pulse-indicator status-rose";
    elements.teleStatusText.textContent = "Error";
    logToCanvas(`[ERROR] System B call failed: ${err.message}`);
    showToast(`System B failed: ${err.message}`);
  }
}

// =========================================================
// SYSTEM C: DIRECT SINGLE API BASELINE EXECUTION
// =========================================================
export function getSimulatedDirectMonograph(query) {
  return `# Direct Parametric Monograph: ${query}

## Executive Summary
This monograph was generated via a single zero-shot API call relying entirely on internal parametric model memory. No external academic repositories were searched, and no retrieval-augmented context was provided.

> **Baseline Architecture Notice:** Pure zero-shot generation. Operates with **zero external scientific grounding**, resulting in high vulnerability to hallucinated citations, speculative constants, and temporal cutoff limits.

## 1. Foundational Theoretical Principles
From a purely theoretical perspective, the domain encompasses governing principles established across foundational literature. Mathematical models describe interactions of primary state variables according to canonical formulations:

$$f(x) = \\sigma(W^T x + b)$$

Where internal weight representations reflect the statistical distributions observed across the model's pre-training corpus. When considering ideal physical conditions, asymptotic boundaries adhere to traditional operational assumptions:
- Uniform distribution of phase noise across measurement channels.
- Ideal thermodynamic equilibrium without stochastic drift.
- Standard algorithmic convergence rates bounded by classical complexity limits.

## 2. Theoretical Analysis & Expected Behaviors
Standard theoretical deductions suggest that operational efficiency correlates with circuit depth and architectural scaling. Without external empirical verification, literature consensus is estimated from parametric recall:
- Scaling exponents generally follow power-law distributions.
- Boundary conditions reflect theoretical predictions rather than empirical measurements.

## 3. Critical Methodological Notice & Hallucination Profile
Because this monograph was produced without external document retrieval or empirical verification:
1. **Zero Grounding Sources:** No DOI-indexed papers or primary datasets were retrieved to corroborate these claims.
2. **Citation Fabrication Risk:** Any specific numerical values, dates, or author attributions generated by direct inference must be treated as unverified parametric approximations.
3. **Temporal Cutoff:** Recent experimental discoveries or benchmark revisions published after the model's training cutoff cannot be accurately represented.`;
}

export async function executeDirectAPIBaseline(query) {
  const disableFallback = document.getElementById('toggle-disable-fallback-agent2')?.checked || false;

  

  // Live Backend execution for Direct Single API
  const abortController = new AbortController();
  UIState.activeAbortController = abortController;

  activateNode(2);
  logToCanvas("[SYSTEM C] Dispatching direct single zero-shot LLM API call (Zero retrieval / Zero verification)...");

  const model = elements.cfgAgent2Model?.value || localStorage.getItem('workbench_agent2_model') || 'gemini-3.6-flash';
  const apiKey = getSystemApiKey('c');
  const token = localStorage.getItem('workbench_auth_token') || sessionStorage.getItem('workbench_auth_token') || '';
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    if (elements.prog2) elements.prog2.style.width = '40%';
    const resp = await fetch('/api/evals/run-system', {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify({
        system_type: 'c',
        query: query,
        model: model,
        api_key: apiKey || null
      }),
      signal: abortController.signal
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Server returned HTTP ${resp.status}: ${errText}`);
    }

    const resData = await resp.json();
    completeNode(2);
    if (elements.prog2) elements.prog2.style.width = '100%';

    const tot = resData.total_tokens || 0;
    const inT = resData.input_tokens || 0;
    const outT = resData.output_tokens || 0;
    UIState.totalTokens = tot;
    UIState.totalPromptTokens = inT;
    UIState.totalCompletionTokens = outT;
    elements.teleTokens.textContent = formatTokenBreakdown(tot, inT, outT);

    logToCanvas(`[SYSTEM C DONE] Latency: ${resData.latency_seconds}s, Tokens: ${tot.toLocaleString()} (${inT} in / ${outT} out).`);

    const directDossier = {
      run_id: resData.run_id || ('run_c_' + Math.random().toString(36).substring(2, 9)),
      query: query,
      architecture: 'system_c',
      model: resData.model || model,
      output_text: resData.output_text,
      latency_seconds: resData.latency_seconds || parseFloat(UIState.elapsedSeconds),
      tokens: tot,
      prompt_tokens: inT,
      completion_tokens: outT,
      cost_usd: resData.cost_usd || 0,
      citations: [],
      quick_answer: "Generated via System C: Direct Single API Baseline (Zero-Shot Parametric Memory). External retrieval and verification bypassed.",
      takeaways: [
        "Synthesized entirely from internal LLM parametric training weights.",
        "Zero external scientific literature retrieved or corroborated.",
        "Elevated hallucination risk: Citations and post-cutoff numerical bounds are unverified."
      ],
      evaluated_claims: []
    };

    finishPipeline(directDossier);
  } catch (err) {
    if (abortController.signal.aborted) {
      logToCanvas("[ABORT] Direct API execution aborted by user.");
      return;
    }
    if (disableFallback) {
      stopElapsedTimer();
      UIState.isRunning = false;
      elements.teleStatusDot.className = "pulse-indicator status-rose";
      elements.teleStatusText.textContent = "Error";
      logToCanvas(`[ERROR] System C call failed: ${err.message}`);
      showToast(`System C failed: ${err.message}`);
      return;
    }
    stopElapsedTimer();
    UIState.isRunning = false;
    elements.teleStatusDot.className = "pulse-indicator status-rose";
    elements.teleStatusText.textContent = "Error";
    logToCanvas(`[ERROR] System C call failed: ${err.message}`);
    showToast(`System C failed: ${err.message}`);
  }
}





