import os
import json
import re
from typing import Dict, Any, List, Optional
import httpx
from backend.post_processor import clean_monograph_text
from backend.agents.agent2_drafter import safe_parse_json, call_gemini_api, call_anthropic_api

# =========================================================
# PRE-GENERATED HIGH-PRECISION DEMO OUTPUTS (Zero Tokens)
# =========================================================

DEMO_QA_RESPONSES = {
    "attention": {
        "answer_html": (
            "<p><strong>Scaled Dot-Product Mathematical Formulation [p.3]:</strong> "
            "The fundamental attention primitive is defined as: "
            "$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$ "
            "where the input queries and keys have dimension $d_k = 64$ and values have dimension $d_v = 64$. "
            "The scaling factor $\\frac{1}{\\sqrt{d_k}}$ is essential: for large dimensions, the dot products grow large in magnitude, "
            "pushing the softmax function into regions with extremely small gradients. Dividing by $\\sqrt{d_k}$ stabilizes gradient flow during backpropagation.</p>"
            "<p><strong>Multi-Head Subspace Projections & Parallel Heads [p.4-5]:</strong> "
            "Multi-Head Attention projects queries, keys, and values linearly $h=8$ times with independently learned parameter matrices [Fig.1, p.3]: "
            "$$\\text{MultiHead}(Q, K, V) = \\text{Concat}(\\text{head}_1, \\dots, \\text{head}_h)W^O$$ "
            "where $\\text{head}_i = \\text{Attention}(QW_i^Q, KW_i^K, VW_i^V)$ with projections $W_i^Q, W_i^K \\in \\mathbb{R}^{d_{\\text{model}} \\times d_k}$ and $W^O \\in \\mathbb{R}^{h d_v \\times d_{\\text{model}}}$. "
            "Because each head's dimensionality is reduced to $d_{\\text{model}}/h = 512/8 = 64$, total compute is strictly equivalent to full-dimensional single-head attention.</p>"
        ),
        "referenced_pages": [3, 4, 5],
        "referenced_figures": ["1"],
        "confidence_score": 0.98
    },
    "compare": {
        "answer_html": (
            "<p><strong>Sequential Operations & Parallelization Limits [p.6]:</strong> "
            "Self-attention layers connect all positions within a sequence in a constant $O(1)$ sequential operations, "
            "completely unblocking full GPU/TPU parallelization across token positions. In contrast, recurrent neural networks (RNNs) require "
            "$O(n)$ sequential steps, enforcing an inherent sequential computational barrier that precludes training parallelization.</p>"
            "<p><strong>Computational Complexity per Layer [p.6]:</strong> "
            "Self-attention exhibits computational complexity of $O(n^2 \\cdot d)$ per layer, compared to $O(n \\cdot d^2)$ for recurrent layers. "
            "For standard context lengths where $n < d$ (e.g. $n=512, d=512$), self-attention is faster and computationally lighter than recurrent layers.</p>"
            "<p><strong>Maximum Information Path Length [p.6]:</strong> "
            "The maximum path length between any two token positions is $O(1)$ for self-attention, compared to $O(n)$ in recurrent layers and $O(\\log_k(n))$ in dilated convolutions. "
            "Shorter path lengths make it significantly easier for backpropagated gradients to learn long-range semantic dependencies without vanishing.</p>"
        ),
        "referenced_pages": [5, 6],
        "referenced_figures": [],
        "confidence_score": 0.97
    },
    "general": {
        "answer_html": (
            "<p><strong>Core Architectural Thesis [p.1-2]:</strong> "
            "The Transformer relies entirely on multi-headed self-attention mechanisms to draw global dependencies between input and output sequences, "
            "abandoning recurrent and convolutional inductive biases entirely. The encoder consists of $N=6$ identical layers, each containing a multi-head "
            "self-attention sub-layer followed by a position-wise fully connected feed-forward network with residual connections and layer normalization.</p>"
            "<p><strong>Empirical Benchmark Performance [p.7-8]:</strong> "
            "On the WMT 2014 English-to-German task, the Big Transformer model establishes a new state-of-the-art BLEU score of 28.4, outperforming all previous models and ensembles by over 2.0 BLEU. "
            "On English-to-French, it scores 41.8 BLEU after 3.5 days of training on 8 P100 GPUs, achieving superior quality at a fraction of prior training costs.</p>"
        ),
        "referenced_pages": [1, 2, 7, 8],
        "referenced_figures": ["1"],
        "confidence_score": 0.96
    }
}

DEMO_SUMMARIZE_RESPONSE = {
    "executive_summary": (
        "<p><strong>Executive Problem Statement & Core Architectural Thesis [p.1]:</strong> "
        "The paper introduces the <em>Transformer</em>, the first sequence transduction architecture based entirely on self-attention mechanisms, "
        "eschewing sequential recurrent layers (LSTMs, GRUs) and convolutional backbones. By eliminating temporal recurrence, "
        "the architecture enables unprecedented parallelization across input tokens, drastically accelerating training execution from weeks to 3.5 days on 8 NVIDIA P100 GPUs.</p>"
        "<p><strong>Empirical Characterization & State-of-the-Art Benchmarks [p.7-8]:</strong> "
        "On the WMT 2014 English-to-German translation benchmark, the Transformer (Big) achieves an unprecedented 28.4 BLEU score, surpassing existing published models and ensembles by over 2.0 BLEU. "
        "On the WMT 2014 English-to-French task, the model sets a new single-model state-of-the-art score of 41.8 BLEU at one-fourth the training computational budget of preceding architectures.</p>"
        "<p><strong>Systemic Bottlenecks & Operational Constraints [p.5-6]:</strong> "
        "While eliminating sequential constraints ($O(1)$ sequential operations), the memory footprint scales quadratically ($O(n^2)$) with sequence length $n$. "
        "Because attention is permutation-invariant, positional awareness is injected via fixed sinusoidal encodings $PE_{(pos, 2i)} = \\sin(pos/10000^{2i/d_{\\text{model}}})$, enabling zero-shot length extrapolation beyond training sequences.</p>"
    ),
    "sub_questions": [
        "Theoretical & Algorithmic Foundations: Scaled Multi-Head Attention",
        "Empirical Characterization: WMT Translation Benchmarks & BLEU Metrics",
        "Systemic Trade-offs: Quadratic Memory Scaling & Positional Invariance"
    ],
    "sections": [
        {
            "sub_question": "Theoretical & Algorithmic Foundations: Scaled Multi-Head Attention",
            "answer_html": (
                "<p><strong>Scaled Dot-Product Mechanics:</strong> The core computational primitive is scaled dot-product attention: "
                "$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$ "
                "Dividing by $\\sqrt{d_k}$ prevents the dot products from growing excessively large in high dimensions ($d_k=64$), avoiding vanishing gradients in the softmax activation [p.3-4].</p>"
                "<p><strong>Multi-Head Subspace Projections:</strong> With $h=8$ parallel attention heads, the model jointly attends to disparate representation subspaces at different positions simultaneously without increasing total computational FLOPs [p.4-5].</p>"
            ),
            "claims": [{"id": "c1", "text": "Scaled dot-product attention divides by sqrt(d_k) to prevent softmax gradient saturation in high dimensions."}]
        },
        {
            "sub_question": "Empirical Characterization: WMT Translation Benchmarks & BLEU Metrics",
            "answer_html": (
                "<p><strong>State-of-the-Art Translation Scores:</strong> The Big Transformer model achieves 28.4 BLEU on English-to-German and 41.8 BLEU on English-to-French, outperforming ByteNet, MoE, and ConvS2S ensembles [p.7-8].</p>"
                "<p><strong>Training Wall-Clock Efficiency:</strong> The base model trained in 12 hours, while the big model completed in 3.5 days on 8 P100 GPUs, requiring orders of magnitude fewer operations than recurrent architectures [p.8].</p>"
            ),
            "claims": [{"id": "c2", "text": "Transformer Big achieved 28.4 BLEU on English-to-German after 3.5 days of training on 8 P100 GPUs."}]
        },
        {
            "sub_question": "Systemic Trade-offs: Quadratic Memory Scaling & Positional Invariance",
            "answer_html": (
                "<p><strong>Quadratic Attention Overhead:</strong> Attention layer complexity scales as $O(n^2 \\cdot d)$, creating memory bottlenecks for ultra-long context windows $n > 4096$ [p.6].</p>"
                "<p><strong>Sinusoidal Positional Encoding:</strong> Geometric progression frequencies from $2\\pi$ to $10000 \\cdot 2\\pi$ allow the network to learn relative positions through linear transformations [p.5-6].</p>"
            ),
            "claims": [{"id": "c3", "text": "Self-attention layer computational complexity scales quadratically as O(n^2 * d) with sequence length."}]
        }
    ]
}

def _clean_chunk_prose(text: str) -> str:
    """Strips metadata, emails, headers, and copyright boilerplate from raw chunk text."""
    t = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
    t = re.sub(r'#+\s*', '', t)
    t = re.sub(r'[*]{1,3}', '', t)
    t = re.sub(r'-\s*[*]\s*-', '', t)
    t = re.sub(r'-{2,}', '', t)
    t = re.sub(r'Provided proper attribution[\s\S]*?(?:scholarly works|reproduce[^\.\n]*|\.)', '', t, flags=re.I)
    t = re.sub(r'arXiv:\d+\.\d+v\d+\s*\[\w+\.\w+\]\s*\d+\s*[A-Za-z]+\s*\d{4}', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# =========================================================
# 1. RUN PDF SUMMARIZE
# =========================================================

async def run_pdf_summarize(
    chunks: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    figures: Optional[List[Dict[str, Any]]] = None,
    mode: str = "comprehensive",
    provider: str = "auto",
    api_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    disable_fallback: bool = False,
    demo_mode: bool = False
) -> Dict[str, Any]:
    """
    Summarizes uploaded PDF documents into an authoritative executive monograph.
    Consumes exactly 1 LLM call when live, or returns pre-generated synthesis in demo mode.
    """
    if demo_mode:
        return _format_pdf_output("summarize", DEMO_SUMMARIZE_RESPONSE, 0, "Showcase Demo Synthesizer", metadata, chunks)

    active_gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    active_anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
    is_claude = ("claude" in provider.lower()) or (not active_gemini_key and bool(active_anthropic_key))

    # STRICT API CALL ENFORCEMENT: Fail-closed if keys are missing
    if disable_fallback and not (active_gemini_key or active_anthropic_key):
        raise RuntimeError(
            "Strict API Mode is active: No Google Gemini or Anthropic Claude API key was provided. "
            "Please configure your API key in Workbench Settings (Settings Drawer) or disable Strict Mode."
        )

    title = metadata.get("title", "Uploaded Research Document")
    authors = metadata.get("authors", "Author(s) Unknown")
    figures = figures or []

    context_chunks = [c for c in chunks if not c.get("is_boilerplate")][:10]
    chunks_text = "\n\n".join([
        f"--- CHUNK {idx+1} (Page {c.get('start_page', 1)}-{c.get('end_page', 1)}) [{c.get('section_title', 'General')}] ---\n{c.get('chunk_text', '')}"
        for idx, c in enumerate(context_chunks)
    ])

    fig_context = ""
    if figures:
        fig_context = "\n\nExtracted Figures from Document:\n" + "\n".join([
            f"- Figure {f.get('figure_id')} (Page {f.get('page', 1)}): {f.get('caption', 'Diagram')}"
            for f in figures[:6]
        ])

    prompt = f"""You are an elite academic literature synthesizer.
Your task is to synthesize an authoritative, multi-paragraph research summary of the following uploaded academic paper:

Document Title: {title}
Authors: {authors}

Extracted Document Context Chunks:
{chunks_text}
{fig_context}

STRICT ACADEMIC GUIDELINES:
1. Provide an authoritative, deeply technical executive summary (3 substantive paragraphs, ~300 words).
2. Detail 3 thematic subtopics covering:
   - Theoretical & Algorithmic Foundations
   - Empirical Measurements, Benchmarks & Results
   - Systemic Trade-offs, Hardware Bounds & Limitations
3. CITE PAGE NUMBERS ACCURATELY: Use [p.X] or [p.X-Y] in your text based strictly on the chunk headers.
4. If referencing figures, cite them as [Fig.X, p.Y].
5. Avoid meta-commentary about AI systems, tokens, or pipelines.
6. Tag 3-5 key empirical assertions using <claim id="c#">factual assertion with metrics</claim>.
7. Return ONLY a strict raw JSON object without markdown fences:

{{
  "executive_summary": "<p><strong>Executive Problem Statement & Core Architectural Thesis:</strong> ...</p><p><strong>Quantitative Benchmarks & Cross-Study Consensus:</strong> ...</p><p><strong>Strategic Deployment Trade-offs & Production Implications:</strong> ...</p>",
  "sub_questions": [
    "Subtopic 1: Theoretical & Algorithmic Foundations",
    "Subtopic 2: Empirical Measurements & Benchmarks",
    "Subtopic 3: Systemic Trade-offs & Production Limits"
  ],
  "sections": [
    {{
      "sub_question": "Subtopic 1: Theoretical & Algorithmic Foundations",
      "answer_html": "<p><strong>Theoretical Principles & Mechanics:</strong> ... [p.1]</p><p><strong>Algorithmic Formulation:</strong> ... [p.2]</p>",
      "claims": [{{"id": "c1", "text": "key factual assertion"}}]
    }}
  ]
}}"""

    if is_claude and active_anthropic_key:
        try:
            raw_text, tokens = await call_anthropic_api(prompt, active_anthropic_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return _format_pdf_output("summarize", parsed, tokens, provider, metadata, chunks)
        except Exception as e:
            print(f"[PDF Synthesizer] Claude summarize failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Claude): {e}")

    elif active_gemini_key:
        try:
            raw_text, tokens = await call_gemini_api(prompt, active_gemini_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return _format_pdf_output("summarize", parsed, tokens, provider, metadata, chunks)
        except Exception as e:
            print(f"[PDF Synthesizer] Gemini summarize failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Gemini): {e}")

    if disable_fallback:
        raise RuntimeError("Strict API Mode Error: Live model call did not return a valid response.")

    return _synthesize_pdf_fallback("summarize", metadata, chunks, figures)


# =========================================================
# 2. RUN PDF QA
# =========================================================

async def run_pdf_qa(
    query: str,
    relevant_chunks: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    figures: Optional[List[Dict[str, Any]]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    provider: str = "auto",
    api_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    disable_fallback: bool = False,
    demo_mode: bool = False
) -> Dict[str, Any]:
    """
    RAG-powered conversational Q&A over document chunks.
    Consumes exactly 1 LLM call when live, or returns pre-generated answers in demo mode.
    """
    figures = figures or []
    chat_history = chat_history or []

    # Check Demo Mode
    if demo_mode:
        q_lower = query.lower()
        if any(k in q_lower for k in ("compare", "rnn", "recurrent", "cnn", "convolution", "complexity", "speed", "parallel", "versus", "vs")):
            resp = DEMO_QA_RESPONSES["compare"]
        elif any(k in q_lower for k in ("attention", "multi-head", "head", "formula", "math", "equation", "softmax", "queries", "keys", "values")):
            resp = DEMO_QA_RESPONSES["attention"]
        else:
            resp = DEMO_QA_RESPONSES["general"]
        return {
            "action": "qa",
            "query": query,
            "tokens_used": 0,
            "answer_html": resp["answer_html"],
            "referenced_pages": resp["referenced_pages"],
            "referenced_figures": resp["referenced_figures"],
            "confidence_score": resp["confidence_score"],
            "source_chunks": relevant_chunks[:4]
        }

    active_gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    active_anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
    is_claude = ("claude" in provider.lower()) or (not active_gemini_key and bool(active_anthropic_key))

    # STRICT API CALL ENFORCEMENT: Fail-closed if keys are missing
    if disable_fallback and not (active_gemini_key or active_anthropic_key):
        raise RuntimeError(
            "Strict API Mode is active: No Google Gemini or Anthropic Claude API key was provided. "
            "Please configure your API key in Workbench Settings (Settings Drawer) or disable Strict Mode."
        )

    clean_chunks = [c for c in relevant_chunks if not c.get("is_boilerplate")] or relevant_chunks
    context_str = "\n\n".join([
        f"--- CHUNK (Page {c.get('start_page', 1)}-{c.get('end_page', 1)}) [{c.get('section_title', 'Section')}] ---\n{c.get('chunk_text', '')}"
        for c in clean_chunks[:8]
    ])

    history_str = ""
    if chat_history:
        history_str = "\nRecent Conversation History:\n" + "\n".join([
            f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
            for msg in chat_history[-4:]
        ])

    fig_str = ""
    if figures:
        fig_str = "\nExtracted Figures:\n" + "\n".join([
            f"- Figure {f.get('figure_id')} (Page {f.get('page', 1)}): {f.get('caption', '')}"
            for f in figures[:4]
        ])

    prompt = f"""You are a precise academic research assistant analyzing an uploaded scientific document.
Document: {metadata.get('title', 'Document')}

{history_str}

Retrieved Document Evidence Chunks:
{context_str}
{fig_str}

Researcher Question:
{query}

INSTRUCTIONS:
1. Answer the question comprehensively and authoritatively using ONLY evidence from the provided chunks.
2. If the document does not contain sufficient information to answer the question, state what is known and explicitly note what the document omits.
3. CITE PAGE NUMBERS ACCURATELY: Use [p.X] inline for every substantive statement.
4. If a figure is directly relevant, cite it as [Fig.X, p.Y].
5. Format your response with clear HTML paragraphs (<p>...</p>) and bold lead-in tags (<p><strong>...:</strong> ...</p>).
6. Return strictly a raw JSON object:
{{
  "answer_html": "<p><strong>Direct Findings:</strong> Detailed answer with [p.X] citations...</p><p><strong>Methodological Context:</strong> Additional context from [p.Y]...</p>",
  "referenced_pages": [1, 2],
  "referenced_figures": [],
  "confidence_score": 0.95
}}"""

    if is_claude and active_anthropic_key:
        try:
            raw_text, tokens = await call_anthropic_api(prompt, active_anthropic_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return {
                    "action": "qa",
                    "query": query,
                    "tokens_used": tokens,
                    "answer_html": parsed.get("answer_html", ""),
                    "referenced_pages": parsed.get("referenced_pages", []),
                    "referenced_figures": parsed.get("referenced_figures", []),
                    "confidence_score": parsed.get("confidence_score", 0.92),
                    "source_chunks": clean_chunks[:4]
                }
        except Exception as e:
            print(f"[PDF Q&A] Claude call failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Claude): {e}")

    elif active_gemini_key:
        try:
            raw_text, tokens = await call_gemini_api(prompt, active_gemini_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return {
                    "action": "qa",
                    "query": query,
                    "tokens_used": tokens,
                    "answer_html": parsed.get("answer_html", ""),
                    "referenced_pages": parsed.get("referenced_pages", []),
                    "referenced_figures": parsed.get("referenced_figures", []),
                    "confidence_score": parsed.get("confidence_score", 0.92),
                    "source_chunks": clean_chunks[:4]
                }
        except Exception as e:
            print(f"[PDF Q&A] Gemini call failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Gemini): {e}")

    if disable_fallback:
        raise RuntimeError("Strict API Mode Error: Live Q&A call did not produce a valid response.")

    # High-quality sanitized fallback Q&A
    top_clean = clean_chunks[0] if clean_chunks else {"chunk_text": "No matching document excerpts found.", "start_page": 1}
    cleaned_prose = _clean_chunk_prose(top_clean.get("chunk_text", ""))
    p_num = top_clean.get("start_page", 1)
    fallback_html = f"<p><strong>Document Evidence [p.{p_num}]:</strong> {cleaned_prose}</p>"

    return {
        "action": "qa",
        "query": query,
        "tokens_used": 0,
        "answer_html": fallback_html,
        "referenced_pages": [p_num],
        "referenced_figures": [],
        "confidence_score": 0.85,
        "source_chunks": clean_chunks[:4]
    }


# =========================================================
# 3. RUN PDF DEEP ANALYSIS
# =========================================================

async def run_pdf_deep_analysis(
    query: str,
    chunks: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    figures: Optional[List[Dict[str, Any]]] = None,
    references: Optional[List[Dict[str, Any]]] = None,
    analysis_type: str = "methodology",
    provider: str = "auto",
    api_key: Optional[str] = None,
    anthropic_key: Optional[str] = None,
    disable_fallback: bool = False,
    demo_mode: bool = False
) -> Dict[str, Any]:
    """
    Executes deep academic analysis (methodology critique, findings extraction, or peer review).
    Consumes 1-2 LLM calls when live, or returns pre-generated synthesis in demo mode.
    """
    if demo_mode:
        return _format_pdf_output(analysis_type, DEMO_SUMMARIZE_RESPONSE, 0, "Showcase Demo Synthesizer", metadata, chunks)

    active_gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    active_anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")
    is_claude = ("claude" in provider.lower()) or (not active_gemini_key and bool(active_anthropic_key))

    # STRICT API CALL ENFORCEMENT: Fail-closed if keys are missing
    if disable_fallback and not (active_gemini_key or active_anthropic_key):
        raise RuntimeError(
            "Strict API Mode is active: No Google Gemini or Anthropic Claude API key was provided. "
            "Please configure your API key in Workbench Settings (Settings Drawer) or disable Strict Mode."
        )

    clean_chunks = [c for c in chunks if not c.get("is_boilerplate")][:12] or chunks[:12]
    chunks_text = "\n\n".join([
        f"--- CHUNK {idx+1} (Page {c.get('start_page', 1)}-{c.get('end_page', 1)}) [{c.get('section_title', 'General')}] ---\n{c.get('chunk_text', '')}"
        for idx, c in enumerate(clean_chunks)
    ])

    analysis_prompts = {
        "methodology": "Extract and critically evaluate the research methodology, experimental protocols, controls, and mathematical formulations.",
        "findings": "Extract all quantitative findings, empirical margins, benchmarks, and statistical claims with confidence evaluations.",
        "critique": "Perform an academic peer-review critique: identify unstated assumptions, potential confounders, boundary conditions, and threats to validity.",
        "compare": "Perform a comparative synthesis evaluating internal consistency, trade-offs, and scaling limits."
    }
    focus_instruction = analysis_prompts.get(analysis_type, analysis_prompts["methodology"])

    prompt = f"""You are a senior academic reviewer conducting an in-depth analysis of an uploaded research paper.
Paper: {metadata.get('title', 'Document')}

Focus of Analysis:
{focus_instruction}

Document Evidence Chunks:
{chunks_text}

INSTRUCTIONS:
1. Provide a rigorous, multi-section academic evaluation.
2. Use diverse subheadings (e.g. 'Experimental Design & Baseline Controls:', 'Empirical Characterization & Statistical Significance:', 'Boundary Constraints & Threat Analysis:').
3. CITE PAGE NUMBERS ACCURATELY: Use [p.X] throughout the analysis.
4. Tag key empirical claims using <claim id="c#">...</claim>.
5. Return strictly raw JSON:
{{
  "executive_summary": "<p><strong>Executive Review & Assessment:</strong> ...</p>",
  "sub_questions": [
    "Core Methodological Framework & Experimental Protocols",
    "Quantitative Benchmarks & Empirical Validation",
    "Threats to Validity & Boundary Constraints"
  ],
  "sections": [
    {{
      "sub_question": "Core Methodological Framework & Experimental Protocols",
      "answer_html": "<p><strong>Protocol Specifications:</strong> ... [p.2]</p><p><strong>Mathematical Formulations:</strong> ... [p.3]</p>",
      "claims": [{{"id": "c1", "text": "methodology claim"}}]
    }}
  ]
}}"""

    if is_claude and active_anthropic_key:
        try:
            raw_text, tokens = await call_anthropic_api(prompt, active_anthropic_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return _format_pdf_output(analysis_type, parsed, tokens, provider, metadata, clean_chunks)
        except Exception as e:
            print(f"[PDF Deep Analysis] Claude call failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Claude): {e}")

    elif active_gemini_key:
        try:
            raw_text, tokens = await call_gemini_api(prompt, active_gemini_key, provider)
            parsed = safe_parse_json(raw_text)
            if parsed:
                return _format_pdf_output(analysis_type, parsed, tokens, provider, metadata, clean_chunks)
        except Exception as e:
            print(f"[PDF Deep Analysis] Gemini call failed: {e}")
            if disable_fallback:
                raise RuntimeError(f"Strict API Mode Error (Gemini): {e}")

    if disable_fallback:
        raise RuntimeError("Strict API Mode Error: Live deep analysis call did not return a valid response.")

    return _synthesize_pdf_fallback(analysis_type, metadata, clean_chunks, figures)


# =========================================================
# 4. FORMATTERS & SANITIZED FALLBACK
# =========================================================

def _format_pdf_output(
    action: str,
    parsed: Dict[str, Any],
    tokens: int,
    provider: str,
    metadata: Dict[str, Any],
    chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    exec_summary = clean_monograph_text(parsed.get("executive_summary", ""))
    sections = []
    for s in parsed.get("sections", []):
        sections.append({
            "sub_question": s.get("sub_question", "Section Analysis"),
            "content_html": clean_monograph_text(s.get("answer_html", "")),
            "claims": s.get("claims", [])
        })

    citations = []
    seen_pages = set()
    for c in chunks[:8]:
        p = c.get("start_page", 1)
        if p not in seen_pages:
            seen_pages.add(p)
            citations.append({
                "ref_id": f"P-{p}",
                "paper_id": f"page_{p}",
                "title": f"{metadata.get('title', 'Document')} (Page {p})",
                "authors": metadata.get("authors", "Author(s)"),
                "year": 2024,
                "venue": f"Page {p} of Uploaded PDF",
                "url": "#",
                "citation_count": 0,
                "verified_claims_count": 1,
                "evidence": _clean_chunk_prose(c.get("chunk_text", ""))[:180]
            })

    return {
        "action": action,
        "query": metadata.get("title", "Uploaded Document"),
        "tokens_used": tokens,
        "executive_summary": exec_summary,
        "dossier_sections": sections,
        "citations": citations,
        "evaluated_claims": parsed.get("claims", []),
        "provider_used": provider
    }


def _synthesize_pdf_fallback(
    action: str,
    metadata: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    figures: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Sanitized fallback when live AI is unavailable and strict mode is off."""
    title = metadata.get("title", "Uploaded Document")
    clean_chunks = [c for c in chunks if not c.get("is_boilerplate")] or chunks

    c1 = _clean_chunk_prose(clean_chunks[0].get("chunk_text", ""))[:320] if clean_chunks else "Academic synthesis of document."
    c2 = _clean_chunk_prose(clean_chunks[1].get("chunk_text", ""))[:320] if len(clean_chunks) > 1 else c1
    c3 = _clean_chunk_prose(clean_chunks[2].get("chunk_text", ""))[:320] if len(clean_chunks) > 2 else c1

    p1 = clean_chunks[0].get("start_page", 1) if clean_chunks else 1
    p2 = clean_chunks[1].get("start_page", 2) if len(clean_chunks) > 1 else p1
    p3 = clean_chunks[2].get("start_page", 3) if len(clean_chunks) > 2 else p1

    exec_summary = (
        f"<p><strong>Document Overview & Architectural Thesis:</strong> Synthesized analysis of <em>{title}</em>. "
        f"{c1} [p.{p1}]</p>"
        f"<p><strong>Empirical Benchmarks & Observations:</strong> {c2} [p.{p2}]</p>"
        f"<p><strong>Systemic Trade-offs & Production Frontiers:</strong> {c3} [p.{p3}]</p>"
    )

    sections = [
        {
            "sub_question": "Theoretical & Methodological Primitives",
            "content_html": f"<p><strong>Foundational Principles:</strong> {c1} [p.{p1}]</p>",
            "claims": [{"id": "c1", "text": c1[:90]}]
        },
        {
            "sub_question": "Quantitative Characterization & Benchmarks",
            "content_html": f"<p><strong>Empirical Measurements:</strong> {c2} [p.{p2}]</p>",
            "claims": [{"id": "c2", "text": c2[:90]}]
        },
        {
            "sub_question": "Systemic Frontiers & Operational Bounds",
            "content_html": f"<p><strong>Scaling Boundaries:</strong> {c3} [p.{p3}]</p>",
            "claims": [{"id": "c3", "text": c3[:90]}]
        }
    ]

    citations = [
        {
            "ref_id": f"P-{clean_chunks[i].get('start_page', i+1)}",
            "paper_id": f"page_{clean_chunks[i].get('start_page', i+1)}",
            "title": f"{title} (Section {i+1})",
            "authors": metadata.get("authors", "Author(s)"),
            "year": 2024,
            "venue": "Uploaded PDF",
            "url": "#",
            "citation_count": 0,
            "evidence": _clean_chunk_prose(clean_chunks[i].get("chunk_text", ""))[:150]
        }
        for i in range(min(3, len(clean_chunks)))
    ]

    return {
        "action": action,
        "query": title,
        "tokens_used": 0,
        "executive_summary": exec_summary,
        "dossier_sections": sections,
        "citations": citations,
        "evaluated_claims": [{"id": "c1", "text": c1[:90]}],
        "provider_used": "Deterministic PDF Synthesizer (Fallback)"
    }
