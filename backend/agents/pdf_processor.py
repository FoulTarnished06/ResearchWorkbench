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

    doc = pymupdf.open(file_path)
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
    doc.close()

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
    doc = pymupdf.open(file_path)
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
            image_ext = base_image.get("ext", "png")
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            if width < 60 or height < 60:
                continue

            img_hash = hashlib.md5(image_bytes).hexdigest()
            if img_hash in seen_hashes:
                continue
            seen_hashes.add(img_hash)

            fig_filename = f"{file_id}_fig_{fig_idx:03d}.{image_ext}"
            fig_rel_path = f"{session_id}/figures/{fig_filename}"
            fig_abs_path = os.path.join(output_dir, fig_filename)

            with open(fig_abs_path, "wb") as f_out:
                f_out.write(image_bytes)

            caption = f"Figure on page {page_num + 1}"
            caption_matches = re.findall(
                rf"(?:Fig(?:ure|\.)\s*{fig_idx}[:.\s][^\n\.\?]{{10,140}}[\.\n])",
                page_text,
                re.IGNORECASE
            )
            if caption_matches:
                caption = caption_matches[0].strip().replace("\n", " ")
            else:
                generic_matches = re.findall(r"(?:Fig(?:ure|\.)\s*\d+[:.\s][^\n]{10,120})", page_text, re.IGNORECASE)
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

    doc.close()
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

            if len(current_chunk_words) + len(para_words) > chunk_size and current_chunk_words:
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
                current_chunk_words = overlap_words + para_words
                current_chunk_has_table = has_table
                current_chunk_has_eq = has_eq
            else:
                current_chunk_words.extend(para_words)
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
    ref_heading_match = re.search(
        r"(?:#{1,4}\s*|\*{1,3}|_|\b)(?:References|Bibliography|Works Cited)(?:\*{1,3}|_)?[:\s\n][\s\S]*$",
        full_text,
        re.IGNORECASE
    )
    if not ref_heading_match:
        ref_block_match = re.search(r"\n(?:\[1\]|1\.)\s+[A-Z][\s\S]{100,}$", full_text)
        if ref_block_match:
            ref_section_text = ref_block_match.group(0)
        else:
            return refs
    else:
        ref_section_text = ref_heading_match.group(0)

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
        year = int(year_match.group(1)) if year_match else 2024

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
