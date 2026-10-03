# Research Workbench: System Review & Strategic Improvements

## Overview
The Research Workbench was designed to compete directly against large monolithic LLM research workflows (like ChatGPT or Claude) while adhering to an exceptionally restrictive computing budget: **strictly 2 LLM calls per query** and an overall token consumption far lower than a single massive context window LLM request.

## Plus Points & Achievements
1. **Ultra-Efficient Architecture**: By shunting context-heavy retrieval matching to local CPU embeddings (`fastembed`), the system successfully bypasses the massive input-token costs associated with dumping 5-10 research papers into an LLM context.
2. **Aggressive Context Distillation**: Agent 3's context distillation (extracting only the top 15 most relevant sentences across all scraped papers) compresses 50,000+ words into ~500 tokens before it ever reaches the LLM.
3. **Multi-Tiered Verification System**: The UI and backend now clearly segregate claims into `Auto-Verified` (0 LLM tokens, 100% local embedding), `LLM-Verified` (Agent 4 semantic evaluation), and `Unverified`.
4. **Broad API Coverage (Zero ArXiv)**: By dropping ArXiv and adding CORE and BASE alongside Crossref, Semantic Scholar, OpenAlex, DOAJ, EuropePMC, and PubMed, the engine captures much broader, peer-reviewed open-access literature across multiple disciplines.
5. **Retractable & Persistent UI**: The sidebar remains fully operational in both compact and expanded forms, providing constant access to tools without sacrificing canvas space.

## Shortcomings & Bottlenecks

### 1. Zero-Shot Drafting Vulnerabilities (Agent 2)
**Issue**: Because the system is restricted to 2 LLM calls, Agent 2 is forced to perform initial synthesis, claim generation, and structuring entirely zero-shot based on the 15 distilled sentences.
**Consequence**: If the distillation phase missed a nuanced point in the literature, Agent 2 hallucinates or omits it. There is no feedback loop allowing Agent 2 to "request more context."

### 2. Over-Reliance on Sentence-Level Similarity
**Issue**: The `fastembed` local similarity metric is purely semantic at a sentence level. 
**Consequence**: Claims that require synthesizing multiple sentences (e.g., "Drug X lowers BP by 10%, but only in patients over 50") might fail local auto-verification because no single sentence has high cosine similarity to the complex claim, forcing it to fall back to the LLM or be marked Unverified.

### 3. Rigid LLM Parsing Constraints
**Issue**: Agent 4 processes bulk verification by outputting a strict JSON dictionary mapping claim IDs to `1` or `0`.
**Consequence**: If the LLM generates any markdown formatting, preamble text, or malformed JSON, the entire verification pipeline fails instantly. It relies heavily on instruction-tuned models not deviating from the format.

### 4. Limited Multi-Turn Capabilities
**Issue**: The hard constraint of 2 LLM calls per query prevents the system from doing multi-step agentic reflection (e.g., Draft -> Critique -> Revise).
**Consequence**: The final monograph quality is entirely dependent on the first draft's quality.

## Recommendations for Future Improvements (Within Budget)

To further improve the system while maintaining the strict <= 2 LLM call rule and minimal token count:

### 1. Implement Local TF-IDF + BM25 Keyword Hybrid Search
* **Improvement**: Cosine similarity (FastEmbed) struggles with exact entity matching (e.g., specific gene names or chemical IDs). Implement a local BM25 index alongside FastEmbed to do a hybrid search during distillation. 
* **Cost**: 0 LLM calls, 0 tokens. Purely local CPU processing.

### 2. Output Schema Enforcement via Structured Decoding
* **Improvement**: Use `response_schema` or structured outputs if the underlying LLM provider supports it. This guarantees the JSON dictionary output from Agent 4 without needing prompt engineering or risking format failures.
* **Cost**: 0 extra LLM calls. Often reduces token generation slightly as the model doesn't generate conversational filler.

### 3. Asynchronous Pre-Caching of Common Queries
* **Improvement**: Implement an offline background worker that pre-fetches and pre-embeds literature for trending or common topics. When the user makes a query, the context distillation happens instantly from the local SQLite cache without hitting external scrapers.
* **Cost**: Speeds up the system dramatically and reduces external API rate-limiting issues.

### 4. Dynamic Distillation Sizing
* **Improvement**: Instead of a hard-coded top 15 sentences, dynamically size the context based on a similarity threshold cliff. If the 16th sentence is still 0.85 similar, include it. If the 5th sentence drops to 0.4 similarity, stop at 4. 
* **Cost**: More efficient token usage for simple queries, preventing token waste on irrelevant sentences.

### 5. Multi-Claim Splitting Locally
* **Improvement**: Before Agent 4 verification, run a fast local NLP script (like `spacy` or `nltk`) to split compound claims into atomic claims. (e.g. splitting "X does Y and Z" into Claim 1: "X does Y", Claim 2: "X does Z").
* **Cost**: 0 LLM calls. Makes local `fastembed` auto-verification much more accurate, reducing the workload sent to Agent 4.
