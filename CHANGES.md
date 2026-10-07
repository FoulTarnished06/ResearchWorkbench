# Project Overhaul Change Log & Implementation Tracker

This document tracks all planned, in-progress, and completed changes across the ResearchWorkbench project.
Updated in real-time as each subsystem is overhauled.

---

## 1. Agent 1: Academic Scraper & Ingestion (`backend/agents/agent1_scraper.py`)
- [x] **Context-Preserving Query Expansion**: Retain overarching topic context during query decomposition; prevent isolated benchmark searches (e.g., searching bare "ZINC" or "QM9"). Enforce domain anchors on decomposed subqueries (`enrich_subquery_context`) even when length $\ge 3$ words to eliminate off-topic scraper pollution (e.g. dietary zinc in poultry feed, PFAS water testing, ASTROMER astronomy).
- [x] **Semantic Relevance Gate Overhaul**: Fix `is_paper_semantically_relevant()` to reject off-topic papers (dietary zinc in poultry feed, PFAS water testing, ASTROMER astronomy), correctly scope full-text variable, and require domain overlap. Verified via `test_33_subquery_enrichment_and_cross_domain_gating`.
- [x] **PMC BioC XML Full-Text Ingestion**: Fetch PubMed Central full-text body paragraphs directly via NCBI BioC XML REST API.
- [x] **arXiv Direct HTML / ar5iv Extraction**: Ingest arXiv direct HTML / ar5iv body text prior to PDF fallback.
- [x] **Extended Download Timeouts**: Increase download timeout to 45–60s prioritizing quality over speed.
- [x] **Purge Dead Code**: Streamlined `get_curated_fallback_papers` and verified landmark literature.
- [x] **Fix Empty `active_scrapers` Bug**: Prevent falsy evaluation of `[]` from defaulting to all scrapers.
- [x] **Clean Sentence Splitter Blacklists**: Remove hardcoded query test blacklists ('mode multiplexer', 'metamaterial').

---

## 2. Agent 2: Academic Drafter (`backend/agents/agent2_drafter.py`)
- [x] **Complete Purge of Offline Fallbacks**: Eliminated offline fallback returns and masked synthetic outputs in `run_agent2_the_drafter()`.
- [x] **Purge Comparison Table Fallback**: In `normalize_and_enrich_comparison_table()`, `dialectical_friction`, and `epistemic_limitations`, eliminated fallback pulling from `DOMAIN_PROFILES`.
- [x] **OpenAI Wire Models Strictly Enforced**: Hard-locked OpenAI calls strictly to `gpt-6-luna`, `gpt-6.1-sol`, `gpt-6-astra`, `gpt-5.5` and no other model; deleted `gpt-4o` fallback.
- [x] **Gemini Wire Models**: Mapped Gemini to real wire models (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-flash`, `gemini-1.5-pro`).
- [x] **Claude Wire Models**: Mapped Anthropic to real models (`claude-3-7-sonnet-20250219`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`).
- [x] **Scale Output to 15,000 Tokens**: Uncapped `analyze_query_complexity` word limits (5,000–10,000 target words, 15,000 tokens, 3–5 subtopics), set `max_completion_tokens: 16384`, set 180s client timeout.
- [x] **Update System Instruction**: Directed model to author exhaustive academic monographs (8,000–12,000 words, scaling to 15,000 tokens) with formal math ($...$) and comparative benchmark matrices.
- [x] **Safe Sentence Deduplication**: Fixed `remove_consecutive_repeated_phrases` to only eliminate immediately adjacent identical sentences, preserving cross-paragraph evidence and protecting `<claim>` tags.
- [x] **Strict Live Execution**: Raise loud `RuntimeError` on missing API key or API call failure. Report real API token counts only.

---

## 3. Agent 3: Context Distiller, Cacher & Vector Index (`backend/agents/agent3_cacher.py`)
- [x] **Eliminate False Auto-Verification Bypass**: Removed 0.58 cosine similarity auto-verification; route all empirical claims to `unverified_claims` so Agent 4 performs real fact-checking.
- [x] **Paragraph-Level Evidence Windowing**: Extracted multi-sentence context windows (`candidate_evidence`) around matched claims, providing paragraph context for Agent 4.
- [x] **Pure-Python Subword Profile for Render (<10MB RAM)**: Safeguarded Render and low-memory mode with lightweight subword index (<10MB RAM, zero ONNX) to eliminate 512MB RAM OOM crashes.
- [x] **Remove 35-Sentence Neural Truncation**: Removed 35-sentence limit; up to 250 sentences indexed.
- [x] **Remove Destructive Polarity Clamping**: Replaced harsh 0.35 clamp with adaptive soft penalty so nuanced scientific phrasing is not destroyed.

---

## 4. Agent 4: Fact-Checker & Synthesizer (`backend/agents/agent4_synthesizer.py`)
- [x] **OpenAI Wire Models Strictly Enforced**: Fact-check calls hard-locked to `gpt-6-luna`, `gpt-6.1-sol`, `gpt-6-astra`, `gpt-5.5` and no other model; deleted `gpt-4o` fallback.
- [x] **Gemini Wire Models**: Mapped to real Gemini models (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-flash`, `gemini-1.5-pro`).
- [x] **Rich Entailment Verification Schema**: Upgraded prompt to structured natural language entailment (status, confidence score, qualitative rationale, supporting quote).
- [x] **Purge Fake 0.85 Scores**: Deleted fallback assigning fake 0.85 scores on failure; raise descriptive `RuntimeError`. Report real API token counts only.
- [x] **Fix Citation Badge Collision**: Cleaned text with `clean_monograph_text` prior to badge annotation, protecting interactive claim wrappers from corruption.

---

## 5. Pipeline Orchestrator (`backend/pipeline.py`)
- [x] **Eliminate Rapid Mode Early Exit**: Removed rapid mode bypass branches in both `run_query_pipeline` and `stream_query_pipeline`; all executions run through Agents 3 & 4.
- [x] **Remove Drafter Exception Fallback**: Deleted fallback calling `synthesize_fallback_draft()` on drafter errors; raises loud, explicit `RuntimeError`.
- [x] **Remove Synthesizer Fallback Retry**: Deleted offline fallback retry (`disable_fallback=False`) on synthesizer failure; raises explicit `RuntimeError`.
- [x] **Stream Explicit `pipeline_error`**: Stream error event with exact diagnostic message when any stage fails.
- [x] **Log Both Completed and Failed Runs**: Record runs in database with proper status (`completed`, `failed`) so history accurately reflects execution state.

---

## 6. Post-Processor (`backend/post_processor.py`)
- [x] **Remove Raw Snippet Injections**: Deleted raw scraper snippet concatenations in `enforce_section2_empirical_purity`.
- [x] **Remove Refusal Notice Overwrites**: Stopped replacing ungrounded claims with `[No empirical measurement...]`; preserved clean synthesized prose with claim badges.
- [x] **Clean Academic Takeaways**: Synthesized clean takeaways without internal pipeline telemetry or meta-commentary leaks.
- [x] **Remove Hardcoded MoE Regex**: Replaced query-specific regex hacks with general mathematical asymptotic normalization.

---

## 7. Database Layer & PostgreSQL Neon Persistence (`backend/database.py` & `backend/app.py`)
- [x] **Eliminate Silent SQLite Fallback**: Eliminated silent fallback to SQLite in `DatabaseEngine.connect()` when `DATABASE_URL` is set; implemented exponential retry loop (up to 15s) for Neon serverless wake-up and loud failure reporting.
- [x] **Ensure Neon History Visibility**: Neon connections persist across runs and restarts; runs are queried directly from PostgreSQL.
- [x] **Record Run Status**: Persisted explicit run status (`completed`, `failed`) and stripped heavy `results_json` payloads in listing endpoints for sub-50ms history browsing.

---

## 8. User Research Paper Upload (`backend/app.py`, `frontend/index.html`, `frontend/js/modules/dossier.js`)
- [x] **Backend Upload Endpoint**: Implemented `POST /api/dossier/upload-source` extracting PDF text with PyMuPDF, indexing into `scraped_papers` and `cached_sentences`, and updating run citations.
- [x] **Frontend Dossier UI**: Added "Upload Custom Paper (PDF)" button, file picker, drag-and-drop zone in citations sidebar, and "User Upload" badge rendering.

---

## 9. Supporting Synthesizers & Infrastructure
- [x] **`pdf_processor.py`**: Fix ReDoS in figure caption regex; use SHA-256 instead of MD5.
- [x] **`citation_graph_builder.py`**: Serialize SQLite writes to eliminate `database is locked` concurrency errors.
- [x] **`followup_synthesizer.py`**: Purge offline fallbacks; wrap synchronous DB calls in `asyncio.to_thread`.
- [x] **`dialogue_synthesizer.py`**: Purge offline fallbacks; wrap synchronous DB calls in `asyncio.to_thread`.
- [x] **`pdf_synthesizer.py`**: Remove hardcoded mock response dictionaries; purge offline fallbacks; strictly enforce allowed OpenAI models (`gpt-6-luna`, `gpt-6.1-sol`, `gpt-6-astra`, `gpt-5.5`).
- [x] **`export.py`**: Sanitize LaTeX special characters (`%`, `\`, `_`, `&`, `#`).

---

## 10. Frontend UI & Stream Resilience (`frontend/js/modules/pipeline.js`, `frontend/index.html`, `frontend/app.js`)
- [x] **Stop Calling `finishPipeline()` on Stream Errors**: Display informative error state card with retry button on disconnect instead of presenting unverified partial drafts as complete dossiers.
- [x] **Update Model Selector Dropdowns**: List OpenAI (`gpt-6-luna`, `gpt-6.1-sol`, `gpt-6-astra`, `gpt-5.5`), Gemini (`gemini-2.5-flash`, `gemini-2.5-pro`), Claude (`claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`).
- [x] **Fix Memory Leaks**: Use event delegation on dynamic lists; prevent memory accumulation.
- [x] **Keep Monolith in Sync**: Update `app.js` with module fixes.

---

## 11. Pipeline Stream Resilience & Grounding Integrity Fixes
- [x] **Agent 4 LaTeX Escape Resilience**: In `backend/agents/agent4_synthesizer.py`, integrated `safe_parse_json()` in `parse_factcheck_response()` to handle scientific LaTeX escapes (`\Delta`, `\varepsilon`, `\approx`, `\pm`, `\mu`) from frontier models (GPT-6 Luna/Sol) that previously caused `json.loads` syntax crashes and marked all claims as ungrounded.
- [x] **Agent 4 Claim Dictionary Aliasing Fix**: Eliminated duplicate alias key pollution in `all_evaluated_claims` that inflated claim counts (70 claims vs. 14 claims in test suite). Added centralized `get_evaluated_claim()` helper resolving `cid`, `cid.lower()`, and stripped prefix variants cleanly.
- [x] **Order-Agnostic `<claim>` Tag Parsing Across Agents 2 & 4**: Replaced brittle regex with attribute-agnostic regex `re.compile(r'<claim\b([^>]*)>([\s\S]*?)<\/claim>', re.IGNORECASE)` across `agent2_drafter.py` and `agent4_synthesizer.py`. Handles arbitrary attribute order (`paper` before `id`), single/double quotes, and auto-wraps raw section claims.
- [x] **Agent 1 Off-Topic Cross-Domain Gating**: In `backend/agents/agent1_scraper.py`, contextualized isolated short entities (e.g., `"ZINC"`) with subquery context in Coverage Gate attempts, restricted Europe PMC to queries with genuine biomedical context, and expanded orthogonal signal filters to prevent dietary poultry zinc, bile acids, PFAS, and astronomy papers from contaminating molecular GNN benchmarks.
- [x] **Server Auto-Reload Stream Disconnect Guard**: In `run_server.py`, configured `reload = False` by default to prevent SQLite database writes in Agent 3 from triggering uvicorn process restarts mid-stream.

---

## 12. Export Polish, Citation Grounding, and Retrieval Precision Fixes
- [x] **Defect A: HTML Attribute Leakage Elimination (`backend/export.py`)**: Updated `strip_html_tags()` to scrub script/style blocks, strip `data-*` and quoted attributes before tag removal, and perform entity unescaping strictly *after* tags are eliminated. Prevents unescaped quotes or `&gt;` inside `data-rationale` or `data-claim` from terminating tags early and leaking `" data-paper-url="..." data-ref-id="...">` into exported body prose.
- [x] **Defect B: Robust Citation Linter & Complete Bibliography Retention (`backend/export.py`)**: Expanded `filter_active_citations()` to parse interactive badges (`[✓ peer-rev • 2]`, `[✓ cache • 4]`), HTML attributes (`data-ref-id="REF-2"`, `href="#cit-card-REF-2"`), and `evaluated_claims` records. Prevents actively referenced papers from being purged as ghost bibliography entries while continuing to purge genuine uncited ghost papers.
- [x] **Defect C: Deterministic Comparison Table & Dialectical Friction Fallbacks (`backend/export.py`)**: Added `ensure_comparison_table()`, `ensure_dialectical_friction()`, and `ensure_epistemic_limitations()` across Word (.docx), LaTeX (.tex), and Markdown (.md) exports. Guarantees that Section 3 (*Quantitative Comparative Benchmarks*), Section 4 (*Dialectical Friction & Methodological Disagreements*), and Section 7 (*Epistemic Horizons & Unresolved Frontiers*) are always rendered and never omitted even when raw pipeline inputs are incomplete.
- [x] **Defect D: Takeaway Token-Overlap Deduplication (`frontend/js/modules/dossier.js`, `frontend/app.js`, `backend/post_processor.py`)**: Implemented `isDuplicateTakeaway()` / `_is_duplicate_takeaway()` checking Jaccard token overlap (>55%) over significant content words. Eliminates near-duplicate consecutive takeaway bullets (e.g., Nandi et al. vs. MultiXC-QM9) across both backend synthesis and frontend display/exports.
- [x] **Defect E: arXiv E-Print Search Relaxation & HTTPS Redirection (`backend/agents/agent1_scraper.py`)**: Upgraded `_fetch_eprint_repository()` to use `https://export.arxiv.org/api/query` with `follow_redirects=True` (resolving 301 redirect silent drops) and relaxed strict `+AND+` constraints by filtering conversational stop words down to top 3 technical terms, restoring retrieval of landmark papers on Graph Transformers, LapPE, and over-squashing curvature.

