import os
import re
import math
import hashlib
from typing import List, Dict, Any, Tuple, Optional
import pymupdf
import pymupdf4llm

def extract_pdf_metadata_and_text(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    with pymupdf.open(file_path) as doc:
        page_count = len(doc)
        raw_meta = doc.metadata or {}

        meta = {
            "title": raw_meta.get("title") or os.path.basename(file_path).replace(".pdf", ""),
            "authors": raw_meta.get("author") or "",
            "subject": raw_meta.get("subject") or "",
            "creation_date": raw_meta.get("creationDate") or ""
        }

        try:
            markdown_text = pymupdf4llm.to_markdown(file_path, page_chunks=False)
        except Exception as e:
            print(f"[PDF Processor] pymupdf4llm failed ({e}), falling back to fitz get_text")
            pages = []
            for page in doc:
                pages.append(page.get_text("text"))
            markdown_text = "\n\n".join(pages)

        words = re.findall(r"\b\w+\b", markdown_text)
        word_count = len(words)

    return {
        "full_text": markdown_text,
        "page_count": page_count,
        "metadata": meta,
        "word_count": word_count
    }

def extract_pdf_figures(file_path: str, output_dir: str, session_id: str, file_id: str) -> List[Dict[str, Any]]:
    figures: List[Dict[str, Any]] = []
    if not os.path.exists(file_path):
        return figures

    os.makedirs(output_dir, exist_ok=True)
    with pymupdf.open(file_path) as doc:
        seen_hashes = set()
        fig_idx = 1

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            page_text = page.get_text("text")

            for img_info in image_list:
                if fig_idx > 50:
                    break

                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image.get("image")
                image_ext = base_image.get("ext", "png").lower()
                if image_ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
                    image_ext = "png"
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                if width < 60 or height < 60:
                    continue

                img_hash = hashlib.sha256(image_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                seen_hashes.add(img_hash)

                safe_file_id = os.path.basename(file_id.strip("/\\"))
                fig_filename = f"{safe_file_id}_fig_{fig_idx:03d}.{image_ext}"
                fig_rel_path = f"{session_id}/figures/{fig_filename}"
                base_output_dir = os.path.realpath(output_dir)
                fig_abs_path = os.path.realpath(os.path.join(output_dir, fig_filename))

                if not fig_abs_path.startswith(base_output_dir):
                    continue

                with open(fig_abs_path, "wb") as f_out:
                    f_out.write(image_bytes)

                caption = f"Figure on page {page_num + 1}"
                caption_matches = re.findall(
                    rf"(?:Fig(?:ure|\.)\s*{fig_idx}[:.\s][^\n.]{{5,140}}(?:\.|\n|$))",
                    page_text,
                    re.IGNORECASE
                )
                if caption_matches:
                    caption = caption_matches[0].strip().replace("\n", " ")
                else:
                    generic_matches = re.findall(
                        r"(?:Fig(?:ure|\.)\s*\d+[:.\s][^\n.]{{5,120}}(?:\.|\n|$))",
                        page_text,
                        re.IGNORECASE
                    )
                    if generic_matches:
                        caption = generic_matches[min(len(generic_matches)-1, fig_idx-1)].strip()

                figures.append({
                    "figure_id": f"{file_id}_fig_{fig_idx}",
                    "file_path": fig_rel_path,
                    "page": page_num + 1,
                    "caption": caption[:200],
                    "width": width,
                    "height": height,
                    "mime_type": f"image/{image_ext}"
                })
                fig_idx += 1

    return figures

def chunk_document(
    full_text: str,
    file_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
    page_count: int = 1
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    if not full_text.strip():
        return chunks

    raw_sections = re.split(r"\n(?=#{1,4}\s+)", full_text)
    total_text_len = len(full_text)
    current_char_offset = 0
    chunk_index = 0

    for sec in raw_sections:
        sec = sec.strip()
        if not sec:
            continue

        title_match = re.match(r"^(#{1,4}\s+)([^\n]+)", sec)
        section_title = title_match.group(2).strip() if title_match else "General Content"

        paragraphs = re.split(r"\n\s*\n", sec)
        current_chunk_words: List[str] = []
        current_chunk_has_table = False
        current_chunk_has_eq = False

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_words = para.split()
            has_table = "|" in para and "---" in para
            has_eq = bool(re.search(r"\$[^\$]+\$|\\\[|\\\(", para))

            # BUG-08 fix: If a single paragraph is longer than chunk_size, split into sub-segments
            segments = []
            if len(para_words) > chunk_size:
                step = max(1, chunk_size - overlap)
                for start_idx in range(0, len(para_words), step):
                    sub_words = para_words[start_idx:start_idx + chunk_size]
                    if sub_words:
                        segments.append(sub_words)
            else:
                segments.append(para_words)

            for seg_words in segments:
                if len(current_chunk_words) + len(seg_words) > chunk_size and current_chunk_words:
                    chunk_text = " ".join(current_chunk_words)
                    approx_start_page = max(1, min(page_count, int((current_char_offset / max(1, total_text_len)) * page_count) + 1))
                    approx_end_page = max(1, min(page_count, int(((current_char_offset + len(chunk_text)) / max(1, total_text_len)) * page_count) + 1))

                    chunks.append({
                        "chunk_id": f"{file_id}_chk_{chunk_index}",
                        "file_id": file_id,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk_text,
                        "section_title": section_title,
                        "start_page": approx_start_page,
                        "end_page": approx_end_page,
                        "token_count": len(current_chunk_words),
                        "has_table": current_chunk_has_table,
                        "has_equation": current_chunk_has_eq
                    })
                    chunk_index += 1
                    current_char_offset += len(chunk_text)

                    overlap_words = current_chunk_words[-overlap:] if overlap > 0 else []
                    current_chunk_words = overlap_words + seg_words
                    current_chunk_has_table = has_table
                    current_chunk_has_eq = has_eq
                else:
                    current_chunk_words.extend(seg_words)
                    current_chunk_has_table = current_chunk_has_table or has_table
                    current_chunk_has_eq = current_chunk_has_eq or has_eq

        if current_chunk_words:
            chunk_text = " ".join(current_chunk_words)
            approx_start_page = max(1, min(page_count, int((current_char_offset / max(1, total_text_len)) * page_count) + 1))
            approx_end_page = max(1, min(page_count, int(((current_char_offset + len(chunk_text)) / max(1, total_text_len)) * page_count) + 1))

            lower_text = chunk_text.lower()
            is_bp = any(bp in lower_text for bp in [
                "proper attribution is provided",
                "grants permission to reproduce",
                "for use in journalistic or scholarly",
                "permission to make digital or hard copies",
                "all rights reserved"
            ])

            chunks.append({
                "chunk_id": f"{file_id}_chk_{chunk_index}",
                "file_id": file_id,
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "section_title": section_title,
                "start_page": approx_start_page,
                "end_page": approx_end_page,
                "token_count": len(current_chunk_words),
                "has_table": current_chunk_has_table,
                "has_equation": current_chunk_has_eq,
                "is_boilerplate": is_bp
            })
            chunk_index += 1
            current_char_offset += len(chunk_text)

    return chunks

def _stem(word: str) -> str:
    w = word.lower()
    for suffix in ("ations", "ation", "ions", "ion", "ings", "ing", "ments", "ment", "ers", "er", "ies", "ied", "ed", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[:-len(suffix)]
    return w

def compute_chunk_vector(text: str) -> Dict[str, float]:
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    if not words:
        return {}

    tf: Dict[str, float] = {}
    for w in words:
        tf[w] = tf.get(w, 0.0) + 1.0
        stem = _stem(w)
        if stem != w:
            tf[f"stem_{stem}"] = tf.get(f"stem_{stem}", 0.0) + 1.2

    for i in range(len(words) - 1):
        bg = f"{words[i]}_{words[i+1]}"
        tf[bg] = tf.get(bg, 0.0) + 1.5

    norm = math.sqrt(sum(v * v for v in tf.values()))
    if norm > 0:
        return {k: round(v / norm, 4) for k, v in tf.items()}
    return tf

def compute_chunk_vectors(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for c in chunks:
        vec = compute_chunk_vector(c.get("chunk_text", ""))
        c["vector"] = vec
    return chunks

def extract_references(full_text: str, file_id: str) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    # BUG-02 fix: Match heading directly without catastrophic backtracking regex
    ref_heading_match = re.search(
        r"(?:#{1,4}\s*|\*{1,3}|_|\b)(?:References|Bibliography|Works Cited)(?:\*{1,3}|_)?[:\s\n]",
        full_text,
        re.IGNORECASE
    )
    if ref_heading_match:
        ref_section_text = full_text[ref_heading_match.end():]
    else:
        ref_block_match = re.search(r"\n(?:\[1\]|1\.)\s+[A-Z]", full_text)
        if ref_block_match:
            ref_section_text = full_text[ref_block_match.start():]
        else:
            return refs

    entries = re.split(r"(?:\n+|\s+)(?:-\s*)?\[\d+\]\s*|(?:\n\d+\.\s+)|(?:\n(?=[A-Z][a-z]+,\s+[A-Z]\.))", ref_section_text)
    ref_idx = 1

    for entry in entries:
        entry = entry.strip()
        if not entry or len(entry) < 20:
            continue
        if re.match(r"^#{1,4}\s*(?:References|Bibliography)", entry, re.I):
            continue

        raw = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", entry).strip()

        year_match = re.search(r"\b(19\d\d|20[0-2]\d)\b", raw)
        year = int(year_match.group(1)) if year_match else None

        doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", raw, re.IGNORECASE)
        doi = doi_match.group(0) if doi_match else ""

        url_match = re.search(r"https?://[^\s\)]+", raw)
        url = url_match.group(0) if url_match else (f"https://doi.org/{doi}" if doi else "")

        title = ""
        quote_title = re.search(r'["\u201c\u201d]([^"\u201c\u201d]{15,180})["\u201c\u201d]', raw)
        if quote_title:
            title = quote_title.group(1).strip()
        else:
            parts = re.split(r"[\.\?\!]\s+", raw)
            if len(parts) >= 2:
                title = parts[1].strip()
            else:
                title = raw[:90].strip()

        authors = ""
        first_part = raw.split(".")[0]
        if len(first_part) < 60:
            authors = first_part.strip()
        else:
            authors = raw[:40].strip()

        refs.append({
            "ref_id": f"{file_id}_ref_{ref_idx}",
            "ref_index": ref_idx,
            "raw_text": raw[:300],
            "title": title,
            "authors": authors,
            "year": year,
            "venue": "Academic Publication",
            "doi": doi,
            "url": url,
            "resolved": False,
            "citation_count": 0,
            "abstract_snippet": ""
        })
        ref_idx += 1
        if ref_idx > 80:
            break

    return refs

def build_document_outline(full_text: str) -> List[Dict[str, Any]]:
    outline: List[Dict[str, Any]] = []
    header_matches = re.finditer(r"^(#{1,4})\s+([^\n]+)", full_text, re.MULTILINE)
    idx = 1
    for m in header_matches:
        level = len(m.group(1))
        title = m.group(2).strip()
        if len(title) > 2 and not title.lower().startswith("fig"):
            outline.append({
                "id": f"sec_{idx}",
                "level": level,
                "title": title
            })
            idx += 1
    return outline

def extractive_summarize_chunks(chunks: List[Dict[str, Any]], query: str = "", top_k: int = 12) -> List[Dict[str, Any]]:
    """
    Zero-token extractive pre-summarizer for PDF context chunks (QUAL-04).
    Scores chunks based on query term overlap, information density, and section prominence.
    Ensures high-signal methodology and empirical findings are prioritized over boilerplate.
    """
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return chunks

    q_words = set(re.findall(r'\b\w{3,}\b', query.lower())) if query else set()
    scored_chunks = []

    for idx, c in enumerate(chunks):
        text = c.get("chunk_text", "")
        words = re.findall(r'\b\w{3,}\b', text.lower())
        if not words or c.get("is_boilerplate"):
            continue

        overlap_score = sum(1 for w in words if w in q_words) if q_words else 0

        sec_title = (c.get("section_title") or "").lower()
        structural_bonus = 0.0
        if any(h in sec_title for h in ["result", "method", "finding", "experiment", "benchmark", "discussion", "conclusion"]):
            structural_bonus += 2.5
        if c.get("has_equation"):
            structural_bonus += 1.0
        if c.get("has_table"):
            structural_bonus += 1.0

        unique_words = len(set(words))
        density = unique_words / max(1, len(words))

        total_score = overlap_score * 2.0 + structural_bonus + density * 1.5
        if idx < 3:
            total_score += 1.0

        scored_chunks.append((total_score, c))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored_chunks[:top_k]]
