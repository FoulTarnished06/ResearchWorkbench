/**
 * AI RESEARCH WORKBENCH - PIPELINE EXECUTION MODULE
 * Orchestration of Demo Mode simulation, Live Backend SSE Streaming, and Telemetry
 */

import { UIState, elements, switchView, ALL_SCRAPERS } from './state.js';
import { showToast, autoResizeQueryTextarea, updateQueryCharCounter, formatTokenBreakdown, escapeHTML } from './utils.js';
import { MOCK_SCENARIOS, fetchSSE } from './scenarios.js';
import { activateNode, completeNode, resetNodeStates, triggerPulse, logToCanvas } from './canvas.js';
import { finishPipeline, extractAcademicTakeaways } from './dossier.js';

export let DEMO_MODE = true;
export function setDemoMode(val) { DEMO_MODE = val; }
export function getDemoMode() { return DEMO_MODE; }

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
// PIPELINE EXECUTION (DEMO vs LIVE SSE)
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
  logToCanvas("[BUDGET] Strict 2-LLM Budget locked. Tool 1 & 2 consume 0 AI tokens.");

  if (DEMO_MODE) {
    executeDemoMode(query);
  } else {
    executeLiveBackend(query);
  }
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
// DEMO MODE EXECUTION
// =========================================================
export function executeDemoMode(query) {
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
  logToCanvas("[AGENT 1] Querying Academic Repositories (Crossref, DOAJ, OpenAlex, Semantic Scholar, Europe PMC, PubMed)...");

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
    UIState.totalPromptTokens += (scenario.prompt_tokens_call1 || 0);
    UIState.totalCompletionTokens += (scenario.completion_tokens_call1 || 0);
    elements.teleTokens.textContent = formatTokenBreakdown(UIState.totalTokens, UIState.totalPromptTokens, UIState.totalCompletionTokens);
    const pTok1 = scenario.prompt_tokens_call1 || 0;
    const cTok1 = scenario.completion_tokens_call1 || 0;
    document.getElementById('m-agent2-tokens').textContent = `${scenario.tokens_call1} tokens (In: ${pTok1} · Out: ${cTok1})`;
    completeNode(2);
    logToCanvas(`[AGENT 2 DONE] Draft complete with tagged factual assertions. Tokens: ${scenario.tokens_call1} (In: ${pTok1} · Out: ${cTok1}).`);
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
    logToCanvas("[AGENT 3 DONE] 5 claims verified against cache (≥0.80). 1 unverified claim passed to Agent 4. Tokens: 0 (Zero LLM).");
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
    UIState.totalPromptTokens += (scenario.prompt_tokens_call2 || 0);
    UIState.totalCompletionTokens += (scenario.completion_tokens_call2 || 0);
    elements.teleTokens.textContent = formatTokenBreakdown(UIState.totalTokens, UIState.totalPromptTokens, UIState.totalCompletionTokens);
    const pTok2 = scenario.prompt_tokens_call2 || 0;
    const cTok2 = scenario.completion_tokens_call2 || 0;
    document.getElementById('m-agent4-tokens').textContent = `${scenario.tokens_call2} tokens (In: ${pTok2} · Out: ${cTok2})`;
    completeNode(4);
    logToCanvas(`[AGENT 4 DONE] Research Dossier synthesized with verified citations. Tokens: ${scenario.tokens_call2} (In: ${pTok2} · Out: ${cTok2}).`);
    
    finishPipeline({
      query: query,
      quick_answer: scenario.quick_answer || scenario.executive_summary || '',
      elapsed: UIState.elapsedSeconds,
      tokens: UIState.totalTokens,
      prompt_tokens: UIState.totalPromptTokens,
      completion_tokens: UIState.totalCompletionTokens,
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
    demo_mode: DEMO_MODE,
    gemini_key: geminiKey,
    anthropic_key: anthropicKey,
    serpapi_key: serpapiKey
  };

  logToCanvas(`[NETWORK] Connecting to FastAPI secure POST SSE endpoint...`);
  logToCanvas(`[MODE] Pipeline Mode: ${currentExecutionMode === 'rapid' ? '⚡ Rapid Synthesis (~5s)' : '🔬 Deep Monograph & 3-Tier Audit (~30s)'}`);
  logToCanvas(`[AGENT 1] Dispatching query to ${activeScrapersList.length} active academic repositories: [${activeScrapersList.join(', ')}]`);
  if (geminiKey || anthropicKey || serpapiKey) {
    logToCanvas(`[AUTH] User credentials forwarded via secure POST body (Gemini: ${geminiKey ? '✓' : '✗'}, Claude: ${anthropicKey ? '✓' : '✗'}, SerpAPI: ${serpapiKey ? '✓' : '✗'}).`);
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
      if (data.agent_id === 4 && data.tokens_used !== undefined) {
        const checkedEl = document.getElementById('m-agent4-checked');
        if (checkedEl) checkedEl.textContent = `All checked`;
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
    console.warn("SSE error, falling back to simulated execution: ", err);
    logToCanvas("[WARN] Backend SSE connection interrupted. Seamlessly switching to Demo Mode.");
    executeDemoMode(query);
  }
}


