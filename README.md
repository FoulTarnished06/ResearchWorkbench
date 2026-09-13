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

### 4. Configure API Keys (Optional)
The workbench includes an offline **Showcase Demo Mode** that requires zero API keys. To run live LLM synthesis, you can either enter keys in the in-app **Model Settings** drawer, or create a `.env` file in the root folder:

```ini
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SERPAPI_API_KEY=your_serpapi_key_here
```

### 5. Launch the Application
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

## Running Automated Tests

Run the verification test suites:
```bash
# Test 1: Full 4-agent web research pipeline
python -m backend.test_pipeline

# Test 2: Tone, takeaway extraction, and diversified headings
python scratch/test_tone_and_takeaways.py

# Test 3: Strict API mode, Demo mode, stemming, and boilerplate sanitization
python scratch/test_v3_strict_and_demo.py
```

---

## Project Documentation & Exhibition Report
For the complete technical breakdown including UML diagrams, ER schemas, design rationale, and benchmarks, view:
- **PDF Report:** [`PROJECT_REPORT_AI_RESEARCH_WORKBENCH.pdf`](PROJECT_REPORT_AI_RESEARCH_WORKBENCH.pdf)
- **Markdown Report:** [`PROJECT_REPORT.md`](PROJECT_REPORT.md)

---

## License
Distributed under the MIT License. See `LICENSE` for more information.
