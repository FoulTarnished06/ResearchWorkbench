import io
import re
from typing import Dict, Any, List, Optional

_XML_ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff]')

def sanitize_xml(text: Any) -> str:
    """Removes XML 1.0 illegal characters (NULL bytes, control characters, invalid surrogates)."""
    if text is None:
        return ""
    return _XML_ILLEGAL_CHARS_RE.sub('', str(text))

def strip_html_tags(text: Any) -> str:
    """Removes HTML tags, cleans up whitespace, and strips XML-incompatible control characters."""
    if not text:
        return ""
    clean = sanitize_xml(text)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def _normalize_comparison_table(table_data: Any) -> tuple[List[str], List[List[str]]]:
    """Extracts column headers and rows from comparison table data structures."""
    if not table_data:
        return [], []
    if isinstance(table_data, dict) and "columns" in table_data and "rows" in table_data:
        return [sanitize_xml(c) for c in table_data["columns"]], [[sanitize_xml(cell) for cell in row] for row in table_data["rows"]]
    if isinstance(table_data, list) and table_data and isinstance(table_data[0], dict):
        cols = ["Technique / Paradigm", "Governing Metric", "Measured Benchmark", "Baseline Comparison", "Empirical Limitations"]
        rows = []
        for item in table_data:
            rows.append([
                sanitize_xml(item.get("technique") or item.get("name") or "Method"),
                sanitize_xml(item.get("governing_metric") or item.get("metric") or "Metric"),
                sanitize_xml(item.get("measured_value") or item.get("value") or "Value"),
                sanitize_xml(item.get("baseline") or "N/A"),
                sanitize_xml(item.get("limitations") or item.get("notes") or "N/A")
            ])
        return cols, rows
    return [], []

def _normalize_dialectical_friction(friction_data: Any) -> List[tuple[str, str]]:
    """Normalizes dialectical disputes and trade-offs into structured (label, description) tuples."""
    if not friction_data:
        return []
    if isinstance(friction_data, dict):
        items = []
        if friction_data.get("disagreements"):
            items.append(("Core Methodological Dispute", sanitize_xml(friction_data["disagreements"])))
        if friction_data.get("pareto_tradeoffs"):
            items.append(("Pareto Frontier Trade-offs", sanitize_xml(friction_data["pareto_tradeoffs"])))
        return items
    if isinstance(friction_data, list):
        items = []
        for item in friction_data:
            if isinstance(item, dict):
                dispute = sanitize_xml(item.get("disagreement") or item.get("disagreements") or item.get("topic") or "Dispute")
                detail = sanitize_xml(item.get("details") or item.get("evidence") or item.get("pareto_tradeoffs") or item)
                items.append((dispute, detail))
            elif isinstance(item, str):
                items.append(("Methodological Debate", sanitize_xml(item)))
        return items
    return []

def _normalize_epistemic_limitations(limitations_data: Any) -> List[str]:
    """Normalizes epistemic boundaries into a clean string list."""
    if not limitations_data:
        return []
    if isinstance(limitations_data, list):
        return [sanitize_xml(x) for x in limitations_data if x]
    if isinstance(limitations_data, str):
        return [sanitize_xml(limitations_data)]
    return []

def export_to_docx(dossier_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a professionally formatted Word document (.docx) from research dossier.
    Includes Quick Answer, Key Takeaways, Executive Monograph, Benchmark Tables,
    Dialectical Friction, Thematic Sections, and Cited References.
    Fully sanitizes XML incompatible control characters and NULL bytes.
    """
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise RuntimeError("python-docx is not installed.")

    doc = Document()
    
    # Title
    raw_query = dossier_data.get("query", "Academic Research Dossier")
    title = doc.add_heading(level=0)
    title_run = title.add_run(strip_html_tags(raw_query))
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    
    # Subtitle / Metadata
    arch = dossier_data.get("architecture") or "system_a"
    arch_label = {
        "system_a": "AI Research Workbench v3.0 | Multi-Agent Fact-Checked Synthesis",
        "system_b": "Conventional RAG Baseline | FastEmbed ONNX Vector Retrieval",
        "system_c": "Direct Single API Baseline | Zero-Shot Parametric Memory"
    }.get(arch, "AI Research Workbench v3.0")
    
    meta_p = doc.add_paragraph()
    meta_run = meta_p.add_run(sanitize_xml(arch_label))
    meta_run.font.italic = True
    meta_run.font.size = Pt(9.5)
    meta_run.font.color.rgb = RGBColor(100, 116, 139)

    sec_num = 1

    # 1. Quick Answer (Basic TL;DR)
    quick_answer = str(dossier_data.get("quick_answer", "") or "").strip()
    if quick_answer:
        doc.add_heading(f"{sec_num}. Executive Quick Answer (Plain-English TL;DR)", level=2)
        sec_num += 1
        qa_p = doc.add_paragraph()
        qa_p.style = 'Intense Quote'
        qa_run = qa_p.add_run(strip_html_tags(quick_answer))
        qa_run.font.size = Pt(11)

    # 2. Key Takeaways
    takeaways = dossier_data.get("takeaways", [])
    if takeaways:
        doc.add_heading(f"{sec_num}. Core Empirical Findings & Takeaways", level=2)
        sec_num += 1
        for t in takeaways:
            doc.add_paragraph(strip_html_tags(t), style='List Bullet')

    # 3. Quantitative Comparative Benchmarks (Table)
    cols, rows = _normalize_comparison_table(dossier_data.get("comparison_table"))
    if cols and rows:
        doc.add_heading(f"{sec_num}. Quantitative Comparative Benchmarks", level=2)
        sec_num += 1
        table = doc.add_table(rows=1, cols=len(cols))
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(cols):
            hdr_cells[i].text = strip_html_tags(col_name)
            for p in hdr_cells[i].paragraphs:
                for r in p.runs:
                    r.font.bold = True
                    r.font.size = Pt(9.5)
        for row_vals in rows:
            row_cells = table.add_row().cells
            for i, val in enumerate(row_vals):
                if i < len(row_cells):
                    row_cells[i].text = strip_html_tags(str(val))
                    for p in row_cells[i].paragraphs:
                        for r in p.runs:
                            r.font.size = Pt(9)
        doc.add_paragraph()

    # 4. Dialectical Friction & Disagreements
    friction_items = _normalize_dialectical_friction(dossier_data.get("dialectical_friction"))
    if friction_items:
        doc.add_heading(f"{sec_num}. Dialectical Friction & Methodological Disagreements", level=2)
        sec_num += 1
        for f_label, f_body in friction_items:
            p = doc.add_paragraph()
            p.add_run(f"• {strip_html_tags(f_label)}: ").bold = True
            p.add_run(strip_html_tags(f_body))

    # 5. Executive Monograph Summary
    exec_summary = str(dossier_data.get("executive_summary", "") or "").strip()
    if exec_summary:
        doc.add_heading(f"{sec_num}. Comprehensive Academic Monograph", level=2)
        sec_num += 1
        doc.add_paragraph(strip_html_tags(exec_summary))

    # 6. Detailed Thematic Sections or Monograph Output (System B & C support)
    sections = dossier_data.get("dossier_sections", dossier_data.get("sections", []))
    if sections:
        t_num = sec_num
        doc.add_heading(f"{sec_num}. Thematic Literature Synthesis & Analysis", level=2)
        sec_num += 1
        for idx, sec in enumerate(sections):
            sub_q = sec.get("sub_question", f"Section {idx+1}")
            clean_title = re.sub(r'^(?:Subtopic\s*\d+[:.-]?|\d+[\.\):]|\d+\s+[-–:]\s*)\s*', '', str(sub_q), flags=re.IGNORECASE)
            doc.add_heading(f"{t_num}.{idx+1} {strip_html_tags(clean_title)}", level=3)
            doc.add_paragraph(strip_html_tags(sec.get("answer_html", sec.get("content_html", ""))))
    elif dossier_data.get("output_text"):
        # For System B or System C baseline runs where sections are stored as markdown in output_text
        doc.add_heading(f"{sec_num}. Monograph Output", level=2)
        sec_num += 1
        paragraphs = str(dossier_data.get("output_text", "")).split("\n\n")
        for p_chunk in paragraphs:
            cleaned_chunk = strip_html_tags(p_chunk.strip())
            if cleaned_chunk:
                if cleaned_chunk.startswith("#"):
                    header_text = cleaned_chunk.lstrip("#").strip()
                    doc.add_heading(header_text, level=3)
                else:
                    doc.add_paragraph(cleaned_chunk)

    # 7. Epistemic Horizons & Limitations
    epistemic_items = _normalize_epistemic_limitations(dossier_data.get("epistemic_limitations"))
    if epistemic_items:
        doc.add_heading(f"{sec_num}. Epistemic Horizons & Unresolved Frontiers", level=2)
        sec_num += 1
        for item in epistemic_items:
            doc.add_paragraph(strip_html_tags(item), style='List Bullet')

    # 8. References & Bibliography
    citations = dossier_data.get("citations", [])
    if citations:
        doc.add_heading(f"{sec_num}. Grounded Citations & Bibliographic Evidence", level=2)
        sec_num += 1
        for cit in citations:
            ref_id = strip_html_tags(cit.get("ref_id", "REF"))
            raw_authors = cit.get("authors", "Unknown Authors")
            authors = ", ".join(str(a) for a in raw_authors) if isinstance(raw_authors, list) else str(raw_authors)
            authors = strip_html_tags(authors)
            year = strip_html_tags(str(cit.get("year", "n.d.")))
            p_title = strip_html_tags(cit.get("title", "Untitled"))
            venue = strip_html_tags(cit.get("venue", "Academic Publication"))
            url = sanitize_xml(cit.get("url", ""))
            
            prov_label = cit.get("provenance_label") or ("Unrefereed Preprint" if cit.get("provenance_tier") == "preprint" else "Peer-Reviewed Literature")
            prov_label = strip_html_tags(prov_label)
            
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"[{ref_id}] {authors} ({year}). ").bold = True
            p.add_run(f"{p_title}. ").italic = True
            p.add_run(f"{venue}. [{prov_label}] ")
            if url:
                p.add_run(f"Available: {url}")
            
            evidence = cit.get("evidence", "")
            if evidence:
                ev_p = doc.add_paragraph()
                ev_p.paragraph_format.left_indent = Inches(0.4)
                ev_run = ev_p.add_run(f'Matched Evidence: "{strip_html_tags(evidence)}"')
                ev_run.font.size = Pt(9)
                ev_run.font.italic = True
                ev_run.font.color.rgb = RGBColor(71, 85, 105)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

LATEX_ESCAPE_MAP = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    '\\': r'\textbackslash{}',
}
LATEX_ESCAPE_REGEX = re.compile(r'([&%\$#_{}~^\\])')

def escape_latex(text: Any) -> str:
    """
    Escapes special LaTeX characters in text to prevent compilation syntax errors.
    Preserves inline math blocks ($ ... $) while escaping %, &, _, #, {, }, ~, ^ in surrounding text.
    Strips illegal XML/control characters.
    """
    if not text:
        return ""
    clean = strip_html_tags(str(text))
    parts = re.split(r'(\$[^\$]+\$)', clean)
    res = []
    for part in parts:
        if part.startswith('$') and part.endswith('$') and len(part) >= 2:
            res.append(part)
        else:
            res.append(LATEX_ESCAPE_REGEX.sub(lambda m: LATEX_ESCAPE_MAP[m.group(1)], part))
    return ''.join(res)

def export_to_latex(dossier_data: Dict[str, Any]) -> str:
    """
    Generates a publication-grade LaTeX article document from research dossier.
    Includes benchmark tables, dialectical friction, epistemic horizons, and bibliography.
    Supports structured sections as well as monolithic monograph outputs (System B/C).
    """
    query = escape_latex(dossier_data.get("query", "Academic Synthesis"))
    arch = dossier_data.get("architecture") or "system_a"
    arch_subtitle = {
        "system_a": "Synthesized by AI Research Workbench v3.0 | Multi-Agent Fact-Checked Synthesis",
        "system_b": "Synthesized via Conventional RAG Baseline | FastEmbed ONNX Vector Retrieval",
        "system_c": "Synthesized via Direct Single API Baseline | Zero-Shot Parametric Memory"
    }.get(arch, "Synthesized by AI Research Workbench v3.0")

    latex = [
        "\\documentclass[11pt,a4paper]{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{hyperref}",
        "\\usepackage{booktabs}",
        "\\usepackage{geometry}",
        "\\geometry{margin=1in}",
        "",
        f"\\title{{{query}}}",
        f"\\author{{{escape_latex(arch_subtitle)}}}",
        "\\date{\\today}",
        "",
        "\\begin{document}",
        "\\maketitle",
        ""
    ]

    # Quick answer
    quick = str(dossier_data.get("quick_answer", "") or "").strip()
    if quick:
        latex.append("\\begin{abstract}")
        latex.append(escape_latex(quick))
        latex.append("\\end{abstract}\n")

    # Takeaways
    takeaways = dossier_data.get("takeaways", [])
    if takeaways:
        latex.append("\\section*{Key Findings}")
        latex.append("\\begin{itemize}")
        for t in takeaways:
            latex.append(f"  \\item {escape_latex(t)}")
        latex.append("\\end{itemize}\n")

    # Benchmark Table
    cols, rows = _normalize_comparison_table(dossier_data.get("comparison_table"))
    if cols and rows:
        latex.append("\\section{Quantitative Comparative Benchmarks}")
        col_align = "l" * len(cols)
        latex.append("\\begin{table}[htbp]")
        latex.append("\\centering")
        latex.append("\\small")
        latex.append(f"\\begin{{tabular}}{{{col_align}}}")
        latex.append("\\toprule")
        latex.append(" & ".join([escape_latex(c) for c in cols]) + " \\\\")
        latex.append("\\midrule")
        for row in rows:
            latex.append(" & ".join([escape_latex(cell) for cell in row]) + " \\\\")
        latex.append("\\bottomrule")
        latex.append("\\end{tabular}")
        latex.append("\\caption{Comparative literature benchmark evaluations.}")
        latex.append("\\end{table}\n")

    # Dialectical Friction
    friction_items = _normalize_dialectical_friction(dossier_data.get("dialectical_friction"))
    if friction_items:
        latex.append("\\section{Dialectical Friction \\& Methodological Disagreements}")
        latex.append("\\begin{itemize}")
        for f_label, f_body in friction_items:
            latex.append(f"  \\item \\textbf{{{escape_latex(f_label)}}}: {escape_latex(f_body)}")
        latex.append("\\end{itemize}\n")

    # Executive Summary
    exec_summary = str(dossier_data.get("executive_summary", "") or "").strip()
    if exec_summary:
        latex.append("\\section{Executive Monograph}")
        latex.append(escape_latex(exec_summary) + "\n")

    # Sections or Monograph Output (System B/C)
    sections = dossier_data.get("dossier_sections", dossier_data.get("sections", []))
    if sections:
        for idx, sec in enumerate(sections):
            sub_q = sec.get("sub_question", f"Section {idx+1}")
            clean_title = re.sub(r'^(?:Subtopic\s*\d+[:.-]?|\d+[\.\):]|\d+\s+[-–:]\s*)\s*', '', str(sub_q), flags=re.IGNORECASE)
            latex.append(f"\\section{{{escape_latex(clean_title)}}}")
            latex.append(escape_latex(sec.get("answer_html", sec.get("content_html", ""))) + "\n")
    elif dossier_data.get("output_text"):
        latex.append("\\section{Monograph Output}")
        paragraphs = str(dossier_data.get("output_text", "")).split("\n\n")
        for p_chunk in paragraphs:
            cleaned_p = p_chunk.strip()
            if cleaned_p:
                if cleaned_p.startswith("#"):
                    hdr = cleaned_p.lstrip("#").strip()
                    latex.append(f"\\subsection{{{escape_latex(hdr)}}}")
                else:
                    latex.append(escape_latex(cleaned_p) + "\n")

    # Epistemic Limitations
    epistemic_items = _normalize_epistemic_limitations(dossier_data.get("epistemic_limitations"))
    if epistemic_items:
        latex.append("\\section{Epistemic Horizons \\& Unresolved Frontiers}")
        latex.append("\\begin{itemize}")
        for item in epistemic_items:
            latex.append(f"  \\item {escape_latex(item)}")
        latex.append("\\end{itemize}\n")

    # Citations
    citations = dossier_data.get("citations", [])
    if citations:
        latex.append("\\section*{References}")
        latex.append("\\begin{enumerate}")
        for cit in citations:
            raw_authors = cit.get("authors", "Unknown")
            authors_str = ", ".join(str(a) for a in raw_authors) if isinstance(raw_authors, list) else str(raw_authors)
            authors = escape_latex(authors_str)
            year = escape_latex(str(cit.get("year") or "n.d."))
            title = escape_latex(cit.get("title", "Untitled"))
            venue = escape_latex(cit.get("venue", ""))
            url = escape_latex(cit.get("url", ""))
            prov_label = cit.get("provenance_label") or ("Unrefereed Preprint" if cit.get("provenance_tier") == "preprint" else "Peer-Reviewed Literature")
            prov_str = f" [{escape_latex(prov_label)}]"
            latex.append(f"  \\item \\textbf{{{authors}}} ({year}). \\textit{{{title}}}. {venue}.{prov_str} \\url{{{url}}}")
        latex.append("\\end{enumerate}\n")

    latex.append("\\end{document}")
    return "\n".join(latex)

def export_to_markdown(dossier_data: Dict[str, Any]) -> str:
    """
    Generates a publication-grade GitHub Flavored Markdown document from research dossier.
    Includes Markdown tables, blockquotes, KaTeX formulas, and full references.
    """
    query = strip_html_tags(dossier_data.get("query", "Academic Research Dossier"))
    arch = dossier_data.get("architecture") or "system_a"
    arch_subtitle = {
        "system_a": "*Synthesized via AI Research Workbench v3.0 | Multi-Agent Fact-Checked Synthesis*",
        "system_b": "*Synthesized via Conventional RAG Baseline | FastEmbed ONNX Vector Retrieval*",
        "system_c": "*Synthesized via Direct Single API Baseline | Zero-Shot Parametric Memory*"
    }.get(arch, "*Synthesized via AI Research Workbench v3.0*")

    md = [
        f"# {query}",
        "",
        arch_subtitle,
        ""
    ]

    sec_num = 1

    # Quick answer
    quick = str(dossier_data.get("quick_answer", "") or "").strip()
    if quick:
        md.append(f"## {sec_num}. Executive Quick Answer (TL;DR)")
        sec_num += 1
        md.append(f"> {strip_html_tags(quick)}\n")

    # Takeaways
    takeaways = dossier_data.get("takeaways", [])
    if takeaways:
        md.append(f"## {sec_num}. Core Empirical Findings & Takeaways")
        sec_num += 1
        for t in takeaways:
            md.append(f"- {strip_html_tags(t)}")
        md.append("")

    # Benchmark Table
    cols, rows = _normalize_comparison_table(dossier_data.get("comparison_table"))
    if cols and rows:
        md.append(f"## {sec_num}. Quantitative Comparative Benchmarks\n")
        sec_num += 1
        header_line = "| " + " | ".join(cols) + " |"
        sep_line = "| " + " | ".join([":---"] * len(cols)) + " |"
        md.append(header_line)
        md.append(sep_line)
        for row in rows:
            md.append("| " + " | ".join([strip_html_tags(cell) for cell in row]) + " |")
        md.append("")

    # Dialectical Friction
    friction_items = _normalize_dialectical_friction(dossier_data.get("dialectical_friction"))
    if friction_items:
        md.append(f"## {sec_num}. Dialectical Friction & Methodological Disagreements\n")
        sec_num += 1
        for f_label, f_body in friction_items:
            md.append(f"- **{strip_html_tags(f_label)}:** {strip_html_tags(f_body)}")
        md.append("")

    # Executive Monograph
    exec_summary = str(dossier_data.get("executive_summary", "") or "").strip()
    if exec_summary:
        md.append(f"## {sec_num}. Comprehensive Academic Monograph\n")
        sec_num += 1
        md.append(strip_html_tags(exec_summary) + "\n")

    # Thematic Sections or Monograph Output (System B/C)
    sections = dossier_data.get("dossier_sections", dossier_data.get("sections", []))
    if sections:
        t_num = sec_num
        md.append(f"## {sec_num}. Thematic Literature Synthesis & Analysis\n")
        sec_num += 1
        for idx, sec in enumerate(sections):
            sub_q = sec.get("sub_question", f"Section {idx+1}")
            clean_title = re.sub(r'^(?:Subtopic\s*\d+[:.-]?|\d+[\.\):]|\d+\s+[-–:]\s*)\s*', '', str(sub_q), flags=re.IGNORECASE)
            md.append(f"### {t_num}.{idx+1} {strip_html_tags(clean_title)}\n")
            md.append(strip_html_tags(sec.get("answer_html", sec.get("content_html", ""))) + "\n")
    elif dossier_data.get("output_text"):
        md.append(f"## {sec_num}. Monograph Output\n")
        sec_num += 1
        md.append(sanitize_xml(dossier_data["output_text"]) + "\n")

    # Epistemic Limitations
    epistemic_items = _normalize_epistemic_limitations(dossier_data.get("epistemic_limitations"))
    if epistemic_items:
        md.append(f"## {sec_num}. Epistemic Horizons & Unresolved Frontiers\n")
        sec_num += 1
        for item in epistemic_items:
            md.append(f"- {strip_html_tags(item)}")
        md.append("")

    # Citations
    citations = dossier_data.get("citations", [])
    if citations:
        md.append(f"## {sec_num}. Grounded Citations & Bibliographic Evidence\n")
        sec_num += 1
        for cit in citations:
            ref_id = strip_html_tags(cit.get("ref_id", "REF"))
            raw_authors = cit.get("authors", "Unknown Authors")
            authors = ", ".join(str(a) for a in raw_authors) if isinstance(raw_authors, list) else str(raw_authors)
            authors = strip_html_tags(authors)
            year = strip_html_tags(str(cit.get("year", "n.d.")))
            p_title = strip_html_tags(cit.get("title", "Untitled"))
            venue = strip_html_tags(cit.get("venue", "Academic Publication"))
            url = sanitize_xml(cit.get("url", ""))
            
            prov_label = cit.get("provenance_label") or ("Unrefereed Preprint" if cit.get("provenance_tier") == "preprint" else "Peer-Reviewed Literature")
            prov_label = strip_html_tags(prov_label)
            prov_tag = f" [{prov_label}]"
            md.append(f"- **[{ref_id}]** {authors} ({year}). *{p_title}*. {venue}.{prov_tag}" + (f" [{url}]({url})" if url else ""))
            evidence = cit.get("evidence", "")
            if evidence:
                md.append(f"  > *Matched Evidence:* \"{strip_html_tags(evidence)}\"")
        md.append("")

    return "\n".join(md)

def export_dialogue_to_markdown(query: str, dialogue_messages: List[Dict[str, Any]], initial_dossier: Optional[Dict[str, Any]] = None) -> str:
    """Exports multi-turn continuous research dialogue to Markdown."""
    clean_q = strip_html_tags(query)
    lines = [
        f"# Continuous Research Dialogue: {clean_q}",
        "",
        f"*Session Recorded via AI Research Workbench v3.0 | Total Turns: {len(dialogue_messages)}*",
        ""
    ]
    if initial_dossier:
        quick = initial_dossier.get("quick_answer", "")
        if quick:
            lines.append("## Initial Literature Synthesis (Turn 0)")
            lines.append(f"> {strip_html_tags(quick)}\n")

    lines.append("## Dialogue Transcript\n")
    for msg in dialogue_messages:
        role = strip_html_tags(msg.get("role", "user")).upper()
        content = strip_html_tags(msg.get("content") or msg.get("answer_html") or "")
        lines.append(f"### [{role}]")
        lines.append(f"{content}\n")

    return "\n".join(lines)

def export_dialogue_to_latex(query: str, dialogue_messages: List[Dict[str, Any]], initial_dossier: Optional[Dict[str, Any]] = None) -> str:
    """Exports multi-turn continuous research dialogue to LaTeX."""
    clean_q = escape_latex(query)
    latex = [
        "\\documentclass[11pt,a4paper]{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{geometry}",
        "\\geometry{margin=1in}",
        f"\\title{{Research Dialogue: {clean_q}}}",
        "\\author{AI Research Workbench v3.0}",
        "\\date{\\today}",
        "\\begin{document}",
        "\\maketitle",
        ""
    ]
    for msg in dialogue_messages:
        role = escape_latex(str(msg.get("role", "user")).upper())
        content = escape_latex(msg.get("content") or msg.get("answer_html") or "")
        latex.append(f"\\subsection*{{{role}}}")
        latex.append(content + "\n")
    latex.append("\\end{document}")
    return "\n".join(latex)
