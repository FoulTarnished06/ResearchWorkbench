# AI Research Workbench

> **Autonomous Multi-Agent Academic Literature Synthesis & Multimodal PDF Document Workstation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-003B57.svg)](https://www.postgresql.org/)
[![FastEmbed ONNX](https://img.shields.io/badge/embeddings-FastEmbed%20ONNX-blueviolet.svg)](https://github.com/qdrant/fastembed)
[![PyMuPDF](https://img.shields.io/badge/pdf-PyMuPDF4LLM-FF6F00.svg)](https://pymupdf.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An academic research workstation engineered to minimize hallucinations, prevent runaway API token costs, and provide verifiable literature citations. Operates across two complementary workflows:

1. **Mode A (Fact-Checked Multi-Agent Web Synthesis):** Enforces a **strict 2-call LLM ceiling** using a sequential 4-agent pipeline with deterministic open-access scraping (**Crossref, DOAJ, OpenAlex, Semantic Scholar, Europe PMC, PubMed**) and local neural FastEmbed ONNX sentence vector pre-filtering (auto-verifying claims $\ge 0.80$ cosine similarity against retrieved literature with zero LLM tokens).
2. **Mode B (Multimodal PDF Document Analysis):** Provides zero-token local PDF text extraction, layout preservation via Markdown, high-resolution diagram/figure extraction, automated bibliography parsing with force-directed citation network graphs, and grounded multi-turn Q&A with display KaTeX math and inline page citations (`[p.X]`).

---

## Architecture Overview

```
[User Query / Papers]
         │
         ├──► MODE A: FACT-CHECKED WEB RESEARCH SYNTHESIS
         │    ├── Agent 1: Academic Scraper (0 Tokens) ──► Crossref, DOAJ, OpenAlex, PubMed, S2, Europe PMC
         │    ├── Agent 2: Synthesis Drafter (LLM Call 1) ──► Monograph + Atomic Claims
         │    ├── Agent 3: Neural Context Cacher (0 Tokens) ──► FastEmbed ONNX Cosine Sim (>=0.80 Auto-Verify)
         │    └── Agent 4: Fact-Checker & Auditor (LLM Call 2) ──► Evidence Scoring & Finalized Dossier
         │
         └──► MODE B: MULTIMODAL PDF DOCUMENT ANALYSIS
              ├── Agent P1: PDF Processor (0 Tokens) ──► PyMuPDF4LLM, Suffix Stemmer, Semantic Chunks
              ├── Figure Extractor (0 Tokens) ──► High-Res PNG Diagrams & Captions
              ├── Citation Network Builder (0 Tokens) ──► OpenAlex & Semantic Scholar Physics Graph
              └── Agent P3: Document Synthesizer (1 Call) ──► Grounded Q&A + KaTeX Math & Page Anchors
```

---

## Key Features

- **Strict Two-Call LLM Ceiling:** Hard cap of at most 2 LLM calls per web research inquiry, keeping API token consumption predictable and contained.
- **FastEmbed ONNX Dense Vector Caching:** Automatically deconstructs scraped literature into individual sentences and indexes dense neural embeddings (`BAAI/bge-small-en-v1.5`) locally on CPU.
- **Automated Claim Cross-Examination:** Every factual assertion generated in Agent 2's initial draft is isolated into an atomic claim tag and independently audited against scraped open-access evidence before final compilation.
- **Multi-Provider LLM Integration:** Full native support for **Google Gemini** (Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash, 3.1 Pro), **Anthropic Claude** (Claude 3.7 Sonnet, 3.5 Sonnet, Haiku, Opus), and **OpenAI** (GPT-6, GPT-5, GPT-4o) via asynchronous HTTP streaming.
- **Dual-Engine Persistence:** High-performance WAL-mode SQLite for local development, seamlessly upgradable to serverless **PostgreSQL (Neon, Supabase, Render, Aiven)** via standard `DATABASE_URL`.
- **Multimodal Figure Extraction:** Automatically extracts diagrams, charts, and plots from PDFs and displays them in an interactive Figure Gallery.
- **Interactive Citation Network:** Resolves bibliography citations against Semantic Scholar and OpenAlex to render a Verlet force-directed physics graph.
- **Dual Aesthetic Themes:** One-click switching between Midnight Obsidian (dark) and Warm Beige (light editorial) palettes.
- **Multi-Format Export:** Export complete research dossiers to publication-ready **DOCX**, **Markdown**, or academic **LaTeX**.

---

## Project Structure

```
ResearchWorkbench/
├── backend/
│   ├── agents/
│   │   ├── agent1_scraper.py          # Deterministic HTTP scraper (6 academic sources)
│   │   ├── agent2_drafter.py          # Monograph drafting & claim generation (LLM Call 1)
│   │   ├── agent3_cacher.py           # ONNX FastEmbed neural cacher & MMR distiller
│   │   ├── agent4_synthesizer.py      # Fact-checker & evidence auditor (LLM Call 2)
│   │   ├── pdf_processor.py           # PyMuPDF text & diagram/figure extractor
│   │   ├── pdf_synthesizer.py         # Grounded PDF Q&A & deep document synthesis
│   │   ├── dialogue_synthesizer.py    # Multi-turn conversational research synthesis
│   │   ├── followup_synthesizer.py    # Per-claim deep dive follow-up inquiries
│   │   └── citation_graph_builder.py  # Force-directed citation graph network resolver
│   ├── app.py                         # FastAPI server core & SSE streaming endpoints
│   ├── auth.py                        # PBKDF2 hashing, JWT sessions & user isolation
│   ├── database.py                    # Dual-engine PostgreSQL (Neon) & SQLite persistence
│   ├── export.py                      # Multi-format export (DOCX, Markdown, LaTeX)
│   ├── logger.py                      # Structured console and file logging
│   ├── pdf_pipeline.py                # PDF analysis pipeline & streaming router
│   ├── pipeline.py                    # Web literature synthesis pipeline router
│   ├── post_processor.py              # Math normalization, citations, XSS sanitization
│   ├── retry.py                       # Exponential backoff retry engine
│   └── requirements.txt               # Python package dependencies
├── frontend/
│   ├── js/
│   │   ├── modules/
│   │   │   ├── auth.js                # Auth modals, token storage & session handling
│   │   │   ├── canvas.js              # Pipeline node visualization & activity logger
│   │   │   ├── dialogue.js            # Multi-turn researcher dialogue interface
│   │   │   ├── dossier.js             # Synthesis viewer, KaTeX math & export controls
│   │   │   ├── pdf_workspace.js       # PDF viewer, figure gallery & chat dock
│   │   │   ├── pipeline.js            # Live SSE streaming & architecture controllers
│   │   │   ├── scenarios.js           # Secure POST SSE event-stream transport
│   │   │   ├── state.js               # Reactive UI state & API credential storage
│   │   │   ├── study.js               # Comparative evaluation study modal UI
│   │   │   └── utils.js               # DOM sanitization, timers & clipboard helpers
│   │   └── main.js                    # ES6 modular application entrypoint
│   ├── app.js                         # Bundled standalone client application
│   ├── index.html                     # Semantic HTML5 workstation layout
│   ├── login.html                     # Authentication login & registration interface
│   ├── styles.css                     # Editorial Obsidian & Warm Beige CSS design system
│   ├── favicon.ico / favicon.svg      # Workstation branding icons
├── evals/                             # Comparative empirical benchmark study suite
│   ├── build_study_docx.py            # Formatted publication-grade Word docx builder
│   ├── Comparative_Study_Protocol_and_Workbook.docx # Benchmark study workbook
│   ├── conventional_rag_system.py     # System B baseline implementation
│   ├── direct_api_system.py           # System C baseline implementation
│   ├── prompts.py                     # 5 standardized rigorous evaluation prompts
│   ├── run_study.py                   # Automated CLI study benchmark runner
│   ├── STUDY_TEMPLATE.md              # Markdown scoring protocol template
│   ├── test_evals.py                  # Evaluation framework unit tests
│   ├── ui_server.py                   # Standalone evaluation UI server
│   └── workbench_system.py            # System A benchmark adapter
├── scripts/
│   └── build_frontend.js              # Frontend syntax & landmark accessibility auditor
├── LICENSE                            # MIT License
├── render.yaml                        # Render.com infrastructure blueprint
├── run_server.py                      # Multi-worker Uvicorn startup script
├── run_tests.py                       # Behavioral test suite runner
├── .env.example                       # Environment configuration template
└── README.md                          # Platform documentation
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/FoulTarnished06/ResearchWorkbench.git
cd ResearchWorkbench
```

### 3. Install Dependencies
```bash
python -m pip install -r backend/requirements.txt
```

### 4. Configure Environment & API Keys (Optional)
The workbench operates with all 6 public academic scrapers (**Crossref, DOAJ, OpenAlex, Semantic Scholar, Europe PMC, PubMed**) and local neural **ONNX BAAI/bge-small-en-v1.5 embeddings** running free locally.

To run live AI generation, configure your keys in the in-app **Agent & Model Configuration** drawer, or create a `.env` file in the root folder (see `.env.example`):

```ini
# Google Gemini (Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash, 3.1 Pro)
GEMINI_API_KEY=your_gemini_api_key_here

# Anthropic Claude (Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3.5 Haiku)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# OpenAI (GPT-6, GPT-5, GPT-4o)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (Optional: Defaults to local SQLite cache.db if omitted)
# Supports serverless PostgreSQL: Neon, Supabase, Render, Aiven
DATABASE_URL=postgresql://user:password@ep-sample-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require

# Authentication Secret (Minimum 32 characters)
JWT_SECRET=your_secret_key_minimum_32_characters
```

### 5. Launch Locally
```bash
python run_server.py
```
Open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🚀 Production Web Deployment Guide

### Option 1: Render.com Native Web Service (Recommended)
ResearchWorkbench includes a native [render.yaml](render.yaml) blueprint:

1. Push your repository to GitHub.
2. Sign up or log into [render.com](https://render.com).
3. Click **New +** $\rightarrow$ **Blueprint** $\rightarrow$ Connect your `ResearchWorkbench` repository.
4. Render automatically configures:
   - **Environment:** Python
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
5. Under Environment Variables in the Render dashboard, supply:
   - `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, and/or `OPENAI_API_KEY`
   - `DATABASE_URL` (e.g. from your free Neon PostgreSQL database)
   - `JWT_SECRET`
6. Click **Apply**. Your workbench is live with automatic free SSL/TLS.

### Option 2: Linux VPS / Reverse Proxy (Nginx + Let's Encrypt)
When deploying behind Nginx, configure the proxy to disable SSE buffering for real-time streaming:

```nginx
server {
    server_name research.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Critical for Server-Sent Events (SSE) streaming:
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}
```

---

## 🔒 User Authentication & Security

- **PBKDF2-HMAC-SHA256:** Password hashing with 100,000 iterations and unique cryptographic salts (zero external binary dependencies).
- **Encrypted JWT Sessions:** Standard HMAC-SHA256 JSON Web Tokens with 7-day expiration and automatic cookie/header synchronization.
- **Multi-User Isolation:** Each researcher's pipeline syntheses, history timeline, and uploaded PDF document libraries are partitioned by `user_id`.
- **Zero Query String Credential Leakage:** All API keys and sensitive tokens are transmitted strictly via encrypted HTTP POST bodies or headers, keeping them out of URL query parameters and server access logs.

---

## 🧪 Verification Test Suites

The codebase includes an exhaustive automated verification test suite:

```bash
# 1. Behavioral smoke tests (ReDoS, claim splitting, retry guard, nh3, DB schema)
python run_tests.py

# 2. Comprehensive integration test suite (32 unit & integration tests)
python -m unittest backend.test_audit_fixes

# 3. User authentication & multi-user isolation test suite (16 tests)
python -m unittest backend.test_auth

# 4. Multi-turn dialogue (DHS-RCC) and claim follow-up test suites (15 tests)
python -m unittest backend.test_dialogue backend.test_followup

# 5. Provenance validation & academic scraper upstream gatekeeper tests (9 tests)
python -m unittest backend.test_provenance_validation

# 6. Comparative evaluation baseline test suite (9 tests)
python -m unittest evals.test_evals

# 7. Frontend ES6 module architecture & landmark accessibility audit
node scripts/build_frontend.js
```

---

## 📊 Comparative Empirical Study: Multi-Agent vs. Conventional RAG vs. Direct API

ResearchWorkbench includes a built-in scientific evaluation harness located in `evals/` designed to empirically compare:
1. **System A: ResearchWorkbench (4-Agent Architecture):** Scraper $\rightarrow$ Drafter $\rightarrow$ FastEmbed ONNX Cacher & MMR Distiller $\rightarrow$ Cross-Verification & Synthesizer.
2. **System B: Conventional RAG (Single Call):** Dense vector embedding search (top-$k$ chunks) injected into a single augmented LLM prompt.
3. **System C: Direct Single API Call (Zero-Shot):** Single LLM call relying strictly on pre-trained parametric weights.

All 3 systems share identical system prompt directives, model selections, and token ceilings.

### Interactive Pipeline Selection in the Workbench UI
You can switch architectures directly in the primary user interface without restarting the server:
- **Settings Drawer (Tab 1):** Choose between *System A: 4-Agent ResearchWorkbench*, *System B: Conventional RAG Baseline*, or *System C: Direct Single API Baseline*. When System B is selected, a context depth slider allows selecting Top-3, Top-5, Top-8, or Top-10 vector retrieval chunks.
- **Floating Canvas Architecture Bar:** Click the architecture pills floating above the Pipeline Canvas to instantly change topology. Unused nodes (e.g. Scraper, Cacher, or Fact-Checker) are dynamically dimmed and labeled as *Bypassed*.
- **Bottom Prompt Bar Quick Toggle:** Click the quick toggle pill next to the prompt input to cycle between System A, B, and C.
- **Independent API Credentials Per System:** In the Settings Drawer, expand *Advanced: Independent API Keys Per System* to enter distinct Gemini, Claude, or OpenAI API keys for System A, System B, and System C.

### Running the Comparative Study via CLI:
```bash
# Run benchmark for Prompt 1 using Claude Sonnet
python evals/run_study.py --prompt 1 --model claude-sonnet-5.5

# Run benchmark for all 5 prompts across all 3 systems
python evals/run_study.py --prompt all --model claude-sonnet-5.5

# Run benchmark on Gemini 3.8 Flash
python evals/run_study.py --prompt 1 --model gemini-3.8-flash
```

Outputs are automatically saved in `evals/results/prompt_<id>_<slug>/`:
- `system_a_research_workbench.md`
- `system_b_conventional_rag.md`
- `system_c_direct_api.md`
- `telemetry_comparison.json`
- `side_by_side_summary.md`

Use **`evals/STUDY_TEMPLATE.md`** or the formatted Word workbook **`evals/Comparative_Study_Protocol_and_Workbook.docx`** (Times New Roman 12pt, 1.5 line spacing) to enter your evaluation scores and compute the **Composite Research Integrity Score (CRIS)**.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
