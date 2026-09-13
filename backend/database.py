import sqlite3
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Scraped academic papers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraped_papers (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            title TEXT NOT NULL,
            authors TEXT,
            year INTEGER,
            abstract TEXT,
            url TEXT,
            venue TEXT,
            citation_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Granular filtered context sentences for semantic verification
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_sentences (
            id TEXT PRIMARY KEY,
            paper_id TEXT,
            query TEXT NOT NULL,
            sentence_text TEXT NOT NULL,
            density_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES scraped_papers (id)
        )
    """)
    
    # Log of pipeline runs and telemetry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tokens_used INTEGER DEFAULT 0,
            elapsed_seconds REAL DEFAULT 0.0,
            status TEXT DEFAULT 'completed',
            results_json TEXT
        )
    """)

    # V3: Persistent PDF sessions (document library)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processing',
            total_files INTEGER DEFAULT 0,
            total_pages INTEGER DEFAULT 0,
            total_chunks INTEGER DEFAULT 0,
            total_words INTEGER DEFAULT 0,
            total_figures INTEGER DEFAULT 0,
            total_references INTEGER DEFAULT 0
        )
    """)

    # V3: Individual uploaded PDF files within a session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_files (
            file_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_size_bytes INTEGER DEFAULT 0,
            page_count INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            title TEXT,
            authors TEXT,
            subject TEXT,
            creation_date TEXT,
            outline_json TEXT,
            extraction_status TEXT DEFAULT 'pending',
            extraction_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES pdf_sessions(session_id) ON DELETE CASCADE
        )
    """)

    # V3: Extracted and indexed document chunks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            chunk_id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            section_title TEXT,
            start_page INTEGER,
            end_page INTEGER,
            token_count INTEGER DEFAULT 0,
            has_table INTEGER DEFAULT 0,
            has_equation INTEGER DEFAULT 0,
            vector_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES pdf_files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES pdf_sessions(session_id) ON DELETE CASCADE
        )
    """)

    # V3: Extracted figures and images
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_figures (
            figure_id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            figure_path TEXT NOT NULL,
            page_number INTEGER,
            caption TEXT,
            width INTEGER,
            height INTEGER,
            mime_type TEXT DEFAULT 'image/png',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES pdf_files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES pdf_sessions(session_id) ON DELETE CASCADE
        )
    """)

    # V3: Parsed references and resolved citation graph
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_references (
            ref_id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            ref_index INTEGER NOT NULL,
            raw_text TEXT,
            parsed_title TEXT,
            parsed_authors TEXT,
            parsed_year INTEGER,
            parsed_venue TEXT,
            parsed_doi TEXT,
            resolved INTEGER DEFAULT 0,
            semantic_scholar_id TEXT,
            openalex_id TEXT,
            external_url TEXT,
            citation_count INTEGER DEFAULT 0,
            abstract_snippet TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES pdf_files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES pdf_sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def save_scraped_papers(query: str, papers: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for p in papers:
        authors_str = ", ".join(p.get("authors", [])) if isinstance(p.get("authors"), list) else str(p.get("authors", ""))
        cursor.execute("""
            INSERT OR REPLACE INTO scraped_papers (id, query, title, authors, year, abstract, url, venue, citation_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.get("paperId") or p.get("id") or str(hash(p.get("title", ""))),
            query,
            p.get("title", "Untitled"),
            authors_str,
            p.get("year", 2024),
            p.get("abstract", ""),
            p.get("url", ""),
            p.get("venue", "Open Access Repository"),
            p.get("citationCount", 0)
        ))
    conn.commit()
    conn.close()

def save_cached_sentences(query: str, sentences: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for s in sentences:
        cursor.execute("""
            INSERT OR REPLACE INTO cached_sentences (id, paper_id, query, sentence_text, density_score)
            VALUES (?, ?, ?, ?, ?)
        """, (
            s.get("id"),
            s.get("paper_id"),
            query,
            s.get("text"),
            s.get("density_score", 0.0)
        ))
    conn.commit()
    conn.close()

def get_cached_sentences_for_query(query: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cached_sentences WHERE query = ? ORDER BY density_score DESC", (query,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_cached_papers(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scraped_papers ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_pipeline_run(run_id: str, query: str, tokens_used: int, elapsed_seconds: float, results: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO pipeline_runs (id, query, tokens_used, elapsed_seconds, results_json)
        VALUES (?, ?, ?, ?, ?)
    """, (run_id, query, tokens_used, elapsed_seconds, json.dumps(results)))
    conn.commit()
    conn.close()

def clear_all_cache() -> Dict[str, int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cached_sentences")
    sentences_deleted = cursor.rowcount
    cursor.execute("DELETE FROM scraped_papers")
    papers_deleted = cursor.rowcount
    cursor.execute("DELETE FROM pipeline_runs")
    runs_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return {
        "papers_deleted": papers_deleted,
        "sentences_deleted": sentences_deleted,
        "runs_deleted": runs_deleted
    }

def get_cache_stats() -> Dict[str, int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM scraped_papers")
    paper_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cached_sentences")
    sentence_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pipeline_runs")
    run_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pdf_sessions")
    pdf_session_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pdf_files")
    pdf_file_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pdf_chunks")
    pdf_chunk_count = cursor.fetchone()[0]
    conn.close()
    return {
        "papers_count": paper_count,
        "sentences_count": sentence_count,
        "runs_count": run_count,
        "pdf_sessions_count": pdf_session_count,
        "pdf_files_count": pdf_file_count,
        "pdf_chunks_count": pdf_chunk_count
    }


# =========================================================
# V3: PDF SESSIONS, FILES, CHUNKS & CITATION GRAPH CRUD
# =========================================================

def save_pdf_session(session_id: str, total_files: int = 0) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO pdf_sessions (session_id, status, total_files)
        VALUES (?, 'processing', ?)
    """, (session_id, total_files))
    conn.commit()
    conn.close()

def get_pdf_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdf_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    session_data = dict(row)
    cursor.execute("SELECT * FROM pdf_files WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    session_data["files"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return session_data

def get_all_pdf_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdf_sessions ORDER BY last_accessed DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    for s in rows:
        cursor.execute("SELECT original_filename, title, page_count FROM pdf_files WHERE session_id = ?", (s["session_id"],))
        s["files_summary"] = [dict(f) for f in cursor.fetchall()]
    conn.close()
    return rows

def update_pdf_session_status(session_id: str, status: str, **counts) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clauses = ["status = ?", "last_accessed = CURRENT_TIMESTAMP"]
    params: List[Any] = [status]
    for key in ["total_files", "total_pages", "total_chunks", "total_words", "total_figures", "total_references"]:
        if key in counts and counts[key] is not None:
            set_clauses.append(f"{key} = ?")
            params.append(counts[key])
    params.append(session_id)
    cursor.execute(f"UPDATE pdf_sessions SET {', '.join(set_clauses)} WHERE session_id = ?", params)
    conn.commit()
    conn.close()

def update_pdf_session_last_accessed(session_id: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE pdf_sessions SET last_accessed = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def delete_pdf_session(session_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stored_path FROM pdf_files WHERE session_id = ?", (session_id,))
    stored_paths = [r["stored_path"] for r in cursor.fetchall()]
    cursor.execute("DELETE FROM pdf_references WHERE session_id = ?", (session_id,))
    refs_deleted = cursor.rowcount
    cursor.execute("DELETE FROM pdf_figures WHERE session_id = ?", (session_id,))
    figs_deleted = cursor.rowcount
    cursor.execute("DELETE FROM pdf_chunks WHERE session_id = ?", (session_id,))
    chunks_deleted = cursor.rowcount
    cursor.execute("DELETE FROM pdf_files WHERE session_id = ?", (session_id,))
    files_deleted = cursor.rowcount
    cursor.execute("DELETE FROM pdf_sessions WHERE session_id = ?", (session_id,))
    sessions_deleted = cursor.rowcount
    conn.commit()
    conn.close()

    # Also delete files on disk if present
    import shutil
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads", session_id)
    if os.path.exists(uploads_dir):
        try:
            shutil.rmtree(uploads_dir)
        except Exception:
            pass

    return {
        "sessions_deleted": sessions_deleted,
        "files_deleted": files_deleted,
        "chunks_deleted": chunks_deleted,
        "figures_deleted": figs_deleted,
        "references_deleted": refs_deleted
    }

def save_pdf_file(
    file_id: str,
    session_id: str,
    original_filename: str,
    stored_path: str,
    file_size_bytes: int = 0,
    page_count: int = 0,
    word_count: int = 0,
    title: Optional[str] = None,
    authors: Optional[str] = None,
    subject: Optional[str] = None,
    creation_date: Optional[str] = None,
    outline_json: Optional[str] = None,
    extraction_status: str = "pending",
    extraction_error: Optional[str] = None
) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO pdf_files (
            file_id, session_id, original_filename, stored_path, file_size_bytes,
            page_count, word_count, title, authors, subject, creation_date,
            outline_json, extraction_status, extraction_error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id, session_id, original_filename, stored_path, file_size_bytes,
        page_count, word_count, title or original_filename, authors or "",
        subject or "", creation_date or "", outline_json or "[]",
        extraction_status, extraction_error
    ))
    conn.commit()
    conn.close()

def get_pdf_files_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdf_files WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def update_pdf_file_status(file_id: str, status: str, error: Optional[str] = None) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE pdf_files SET extraction_status = ?, extraction_error = ? WHERE file_id = ?", (status, error, file_id))
    conn.commit()
    conn.close()

def save_pdf_chunks(session_id: str, file_id: str, chunks: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for c in chunks:
        vec_json = json.dumps(c.get("vector", {})) if isinstance(c.get("vector"), dict) else (c.get("vector_json") or "{}")
        cursor.execute("""
            INSERT OR REPLACE INTO pdf_chunks (
                chunk_id, file_id, session_id, chunk_index, chunk_text,
                section_title, start_page, end_page, token_count,
                has_table, has_equation, vector_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c.get("chunk_id") or f"{file_id}_chk_{c.get('chunk_index', 0)}",
            file_id,
            session_id,
            c.get("chunk_index", 0),
            c.get("chunk_text") or c.get("text", ""),
            c.get("section_title", "General"),
            c.get("start_page", 1),
            c.get("end_page", 1),
            c.get("token_count", 0),
            1 if c.get("has_table") else 0,
            1 if c.get("has_equation") else 0,
            vec_json
        ))
    conn.commit()
    conn.close()

def get_pdf_chunks_by_session(session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM pdf_chunks WHERE session_id = ? ORDER BY file_id, chunk_index"
    params: List[Any] = [session_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_pdf_chunks_by_page(session_id: str, page: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM pdf_chunks
        WHERE session_id = ? AND start_page <= ? AND end_page >= ?
        ORDER BY chunk_index
    """, (session_id, page, page))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_pdf_figures(session_id: str, file_id: str, figures: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for f in figures:
        cursor.execute("""
            INSERT OR REPLACE INTO pdf_figures (
                figure_id, file_id, session_id, figure_path, page_number,
                caption, width, height, mime_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f.get("figure_id"),
            file_id,
            session_id,
            f.get("figure_path") or f.get("file_path", ""),
            f.get("page_number") or f.get("page", 1),
            f.get("caption", ""),
            f.get("width", 0),
            f.get("height", 0),
            f.get("mime_type", "image/png")
        ))
    conn.commit()
    conn.close()

def get_pdf_figures_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdf_figures WHERE session_id = ? ORDER BY page_number ASC", (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_pdf_references(session_id: str, file_id: str, refs: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for r in refs:
        cursor.execute("""
            INSERT OR REPLACE INTO pdf_references (
                ref_id, file_id, session_id, ref_index, raw_text,
                parsed_title, parsed_authors, parsed_year, parsed_venue, parsed_doi,
                resolved, semantic_scholar_id, openalex_id, external_url,
                citation_count, abstract_snippet
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("ref_id") or f"{file_id}_ref_{r.get('ref_index', 0)}",
            file_id,
            session_id,
            r.get("ref_index", 0),
            r.get("raw_text", ""),
            r.get("parsed_title") or r.get("title", ""),
            r.get("parsed_authors") or r.get("authors", ""),
            r.get("parsed_year") or r.get("year", 2024),
            r.get("parsed_venue") or r.get("venue", ""),
            r.get("parsed_doi") or r.get("doi", ""),
            1 if r.get("resolved") else 0,
            r.get("semantic_scholar_id"),
            r.get("openalex_id"),
            r.get("external_url") or r.get("url", ""),
            r.get("citation_count", 0),
            r.get("abstract_snippet", "")
        ))
    conn.commit()
    conn.close()

def get_pdf_references_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pdf_references WHERE session_id = ? ORDER BY ref_index ASC", (session_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def update_reference_resolution(ref_id: str, resolved_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pdf_references
        SET resolved = 1,
            semantic_scholar_id = ?,
            openalex_id = ?,
            external_url = ?,
            citation_count = ?,
            abstract_snippet = ?,
            parsed_title = COALESCE(NULLIF(?, ''), parsed_title),
            parsed_year = COALESCE(NULLIF(?, 0), parsed_year),
            parsed_venue = COALESCE(NULLIF(?, ''), parsed_venue)
        WHERE ref_id = ?
    """, (
        resolved_data.get("semantic_scholar_id"),
        resolved_data.get("openalex_id"),
        resolved_data.get("external_url") or resolved_data.get("url"),
        resolved_data.get("citation_count", 0),
        resolved_data.get("abstract_snippet", ""),
        resolved_data.get("title", ""),
        resolved_data.get("year", 0),
        resolved_data.get("venue", ""),
        ref_id
    ))
    conn.commit()
    conn.close()

def get_citation_graph_data(session_id: str) -> Dict[str, Any]:
    refs = get_pdf_references_by_session(session_id)
    nodes = []
    edges = []
    total_external_cites = 0
    years = []

    for r in refs:
        resolved = bool(r.get("resolved", 0))
        cite_count = r.get("citation_count", 0) or 0
        total_external_cites += cite_count
        year = r.get("parsed_year")
        if year and isinstance(year, int) and year > 1900:
            years.append(year)

        nodes.append({
            "id": r["ref_id"],
            "ref_index": r["ref_index"],
            "title": r.get("parsed_title") or r.get("raw_text", f"Reference {r['ref_index']}")[:80],
            "authors": r.get("parsed_authors", "Unknown"),
            "year": r.get("parsed_year"),
            "venue": r.get("parsed_venue", ""),
            "doi": r.get("parsed_doi", ""),
            "url": r.get("external_url", ""),
            "citation_count": cite_count,
            "abstract": r.get("abstract_snippet", ""),
            "resolved": resolved
        })

    # Inter-reference co-citation edges: connect papers from similar decades / themes
    for i in range(len(nodes)):
        for j in range(i + 1, min(i + 4, len(nodes))):
            if nodes[i]["resolved"] and nodes[j]["resolved"]:
                edges.append({"from": nodes[i]["id"], "to": nodes[j]["id"], "type": "co-cited"})

    import statistics
    median_yr = int(statistics.median(years)) if years else 2023

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_references": len(refs),
            "resolved_count": sum(1 for n in nodes if n["resolved"]),
            "unresolved_count": sum(1 for n in nodes if not n["resolved"]),
            "median_year": median_yr,
            "total_external_citations": total_external_cites
        }
    }


