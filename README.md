---
title: AI Research Workbench
emoji: 🔬
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AI Research Workbench v3.0

> **Autonomous Multi-Agent Academic Literature Synthesis & Multimodal PDF Document Workstation**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite3](https://img.shields.io/badge/cache-SQLite3%20TF--IDF-003B57.svg)](https://www.sqlite.org/)
[![PyMuPDF](https://img.shields.io/badge/pdf-PyMuPDF4LLM-FF6F00.svg)](https://pymupdf.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An academic research workstation engineered to eliminate hallucinations, runaway API token costs, and missing citations. Operates in two complementary modes:

1. **Mode A (Multi-Agent Web Literature Synthesis):** Enforces a **strict 2-call LLM budget** using a sequential 4-agent pipeline with deterministic open-access scraping (arXiv, Semantic Scholar, OpenAlex, PubMed) and local SQLite sentence vector pre-filtering (auto-verifying claims >= 0.80 similarity with zero tokens).
2. **Mode B (Multimodal PDF Document Analysis):** Provides zero-token local PDF text extraction, layout preservation via Markdown, high-resolution diagram/figure extraction, automated bibliography parsing with force-directed citation network graphs, and grounded multi-turn Q&A with display KaTeX math and inline page citations (`[p.X]`).

---

## Architecture Overview

```
[User Query / Papers]
         │
         ├──► MODE A: WEB RESEARCH SYNTHESIS
         │    ├── Agent 1: Academic Scraper (0 Tokens) ──► arXiv, Semantic Scholar, OpenAlex
         │    ├── Agent 2: Synthesis Drafter (LLM Call 1) ──► Monograph + Atomic Claims
         │    ├── Agent 3: SQLite Context Cacher (0 Tokens) ──► Cosine Similarity (>=0.80 Auto-Verify)
         │    └── Agent 4: Fact-Checker & Auditor (LLM Call 2) ──► Evidence Scoring & Dossier
         │
         └──► MODE B: MULTIMODAL PDF DOCUMENT ANALYSIS
              ├── Agent P1: PDF Processor (0 Tokens) ──► PyMuPDF4LLM, Suffix Stemmer, Chunks
              ├── Figure Extractor (0 Tokens) ──► High-Res PNG Diagrams & Captions
              ├── Citation Network Builder (0 Tokens) ──► OpenAlex & Semantic Scholar Graph
              └── Agent P3: Document Synthesizer (1 Call or Demo) ──► Grounded Q&A + KaTeX Math
```

---

## Key Features

- **Strict Two-Call LLM Budget:** Hard ceiling of at most 2 LLM calls per web research inquiry, keeping API costs low and predictable.
- **Sentence-Level SQLite Vector Caching:** Automatically deconstructs scraped literature into individual sentences and indexes unigram/bigram TF-IDF vectors.
- **Fail-Closed Strict API Mode:** Toggleable mode that refuses to emit dummy placeholder data if an API key is missing or an error occurs.
- **Showcase Demo Mode:** Zero-token simulation mode with peer-reviewed pre-computed mathematical attention formulations and computational complexity comparisons.
- **Multimodal Figure Extraction:** Automatically extracts diagrams, charts, and plots from PDFs and displays them in a dedicated Figure Gallery.
- **Interactive Citation Network:** Resolves bibliography citations against Semantic Scholar and OpenAlex to render a Verlet force-directed physics graph.
- **Dual Aesthetic Themes:** One-click switching between Midnight Obsidian (dark) and Warm Beige (light editorial) palettes.

---

## Project Structure

```
PROJECT_EXHIBITION/
├── backend/
│   ├── agents/
│   │   ├── agent1_scraper.py          # Deterministic HTTP scraper (arXiv, S2, OpenAlex)
│   │   ├── agent2_drafter.py          # Monograph drafting & claim generation (LLM 1)
│   │   ├── agent3_cacher.py           # SQLite sentence vectorizer & cosine matcher
│   │   ├── agent4_synthesizer.py      # Claim auditor & evidence verification (LLM 2)
│   │   ├── pdf_processor.py           # PyMuPDF extraction, stemmer, figures, references
│   │   ├── pdf_synthesizer.py         # Grounded PDF Q&A, monographs, demo math
│   │   └── citation_graph_builder.py  # Asynchronous citation graph network resolver
│   ├── app.py                         # FastAPI server core & REST/SSE endpoints
│   ├── database.py                    # SQLite schema management & CRUD operations
│   ├── pipeline.py                    # Web synthesis pipeline orchestrator
│   ├── pdf_pipeline.py                # PDF analysis pipeline & streaming controller
│   ├── post_processor.py              # LaTeX normalization & citation badges
│   └── requirements.txt               # Python package dependencies
├── frontend/
│   ├── app.js                         # Reactive SPA client & canvas renderer
│   ├── index.html                     # Semantic HTML5 layout & workspace views
│   └── styles.css                     # Modern CSS custom properties (Obsidian & Beige)
├── run_server.py                      # Multi-worker Uvicorn startup script
├── run.bat                            # One-click Windows startup batch script
├── PROJECT_REPORT_AI_RESEARCH_WORKBENCH.pdf # Detailed 17-page Project Exhibition Report
├── PROJECT_REPORT.md                  # Comprehensive Project Report source document
├── README.md                          # Repository documentation
└── .gitignore                         # Git exclusion rules
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/<your-username>/ai-research-workbench.git
cd ai-research-workbench
```

### 3. Install Dependencies
```bash
python -m pip install -r backend/requirements.txt
```

### 4. Configure API Keys & Authentication (Optional)
The workbench operates out-of-the-box with **Showcase Demo Mode** requiring $0 and zero API keys. 
All 6 public academic scrapers (**Crossref, DOAJ, OpenAlex, Semantic Scholar, Europe PMC, PubMed**) and local neural **ONNX BAAI/bge-small-en-v1.5 embeddings** run completely free locally.

To run live AI generation, you can enter your keys in the in-app **Agent & Model Configuration** drawer, or create a `.env` file in the root folder:

```ini
# Google Gemini (Gemini 3.8 Flash, 3.6 Flash, 3.5 Flash, 3.1 Pro)
GEMINI_API_KEY=your_gemini_api_key_here

# Anthropic Claude (Claude Opus 5.5, Claude Sonnet 5.5, Claude Haiku)
# Enforces strict 4096 token ceiling for Opus and 8192 for Sonnet/Haiku
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: JWT Secret for User Authentication Sessions
JWT_SECRET=your_secret_key_minimum_32_characters
```

### 5. Launch Locally
Run via the Windows batch script:
```cmd
run.bat
```
Or run directly with Python:
```bash
python run_server.py
```
Open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🚀 Free Production Cloud Deployment Guide

The workbench is 100% containerized and configured for zero-cost cloud hosting with no credit card required.

### Option 1: Hugging Face Spaces (100% Free — Recommended)
Hugging Face Spaces provides a permanent free tier with **2 vCPUs, 16 GB RAM, 50 GB storage, and free HTTPS**:

1. Create a free account at [huggingface.co](https://huggingface.co).
2. Click **New Space** → Set Space Name (e.g. `research-workbench`).
3. Select **Docker** as the Space SDK and choose the **Blank** template.
4. Set Space Hardware to **CPU basic · 2 vCPU · 16 GB RAM · Free**.
5. Push your repository to the Hugging Face Space git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/research-workbench
   git push space main
   ```
6. In your Space's **Settings** → **Variables and secrets**, add:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `JWT_SECRET`: Random 32-character string
7. Your workbench is immediately live with a public HTTPS URL (e.g. `https://<your-username>-research-workbench.hf.space`)!

---

### Option 2: Render.com (100% Free Web Service)
Render offers a free Docker web service tier:

1. Sign up at [render.com](https://render.com) using GitHub.
2. Click **New +** → **Web Service** → Connect your GitHub repository.
3. Select **Docker** environment (it automatically detects the included `Dockerfile`).
4. Choose the **Free** instance type.
5. In **Environment Variables**, add:
   - `PORT`: `10000`
   - `GEMINI_API_KEY`: Your Gemini API key
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `JWT_SECRET`: Random 32-character string
6. Click **Deploy Web Service**.

---

### Option 3: Local Docker & Docker Compose
To run in an isolated production container locally:
```bash
# Build and start the container in the background
docker compose up -d --build

# Verify container health
docker compose ps

# View real-time logs
docker compose logs -f
```
Open **[http://localhost:8000](http://localhost:8000)**.

---

## 🔒 User Authentication & Security

- **PBKDF2-HMAC-SHA256:** Password hashing with 100,000 iterations and unique cryptographic salts (zero external binary dependencies).
- **Encrypted JWT Sessions:** Standard HMAC-SHA256 JSON Web Tokens with 7-day expiration and automatic cookie/header synchronization.
- **Multi-User Isolation:** Each researcher's pipeline syntheses, history timeline, and uploaded PDF document libraries are partitioned by `user_id`.
- **Zero-Token Guest Mode:** Guests can explore demo syntheses and test offline features without creating an account.

---

## 🧪 Running Verification Test Suites

The codebase includes an exhaustive test suite with 100% pass rate:

```bash
# 1. Behavioral smoke tests (ReDoS, claim splitting, retry 400 guard, nh3, DB migration)
python run_tests.py

# 2. Comprehensive integration test suite (32 unit & integration tests)
python backend/test_audit_fixes.py

# 3. User authentication & multi-user isolation test suite (6 tests)
python backend/test_auth.py

# 4. Multi-turn dialogue (DHS-RCC) and claim follow-up test suites (15 tests)
python -m unittest backend/test_dialogue.py
python -m unittest backend/test_followup.py

# 5. Frontend ES6 module architecture & landmark accessibility audit
node scripts/build_frontend.js
```

---

## License
Distributed under the MIT License. See `LICENSE` for more information.

