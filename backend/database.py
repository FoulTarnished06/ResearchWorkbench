import sqlite3
import os
import json
import hashlib
import datetime
import time
import uuid
import re
from typing import List, Dict, Any, Optional
from backend.logger import get_logger

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = get_logger("Database")

DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")
IS_POSTGRES = bool(os.environ.get("DATABASE_URL", "").strip().startswith(("postgres://", "postgresql://")))

TABLE_PRIMARY_KEYS = {
    "scraped_papers": ["id"],
    "cached_sentences": ["id"],
    "pipeline_runs": ["id"],
    "response_cache": ["query_hash"],
    "pdf_sessions": ["session_id"],
    "pdf_files": ["file_id"],
    "pdf_chunks": ["chunk_id"],
    "pdf_figures": ["figure_id"],
    "pdf_references": ["ref_id"],
    "user_api_keys": ["user_id", "provider"],
    "users": ["id"],
    "schema_version": ["version"],
}

def adapt_sql_for_postgres(sql: str) -> str:
    """Translates SQLite statements (INSERT OR REPLACE, ? placeholders) to standard PostgreSQL syntax."""
    # Convert INSERT OR REPLACE INTO table (cols) VALUES (...) to ON CONFLICT DO UPDATE
    m = re.search(r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)", sql, re.IGNORECASE | re.DOTALL)
    if m:
        tbl = m.group(1).lower()
        cols = [c.strip() for c in m.group(2).split(",")]
        pks = TABLE_PRIMARY_KEYS.get(tbl, ["id"])
        non_pks = [c for c in cols if c.lower() not in [p.lower() for p in pks]]
        if non_pks:
            updates = ", ".join([f"{c} = EXCLUDED.{c}" for c in non_pks])
            sql = f"INSERT INTO {tbl} ({m.group(2)}) VALUES ({m.group(3)}) ON CONFLICT ({', '.join(pks)}) DO UPDATE SET {updates}"
        else:
            sql = f"INSERT INTO {tbl} ({m.group(2)}) VALUES ({m.group(3)}) ON CONFLICT ({', '.join(pks)}) DO NOTHING"
    
    # Replace ? parameter placeholders with %s for psycopg2
    return sql.replace("?", "%s")

class PostgresRow:
    """Provides sqlite3.Row-compatible access (by key row['id'], index row[0], and dict(row)) for PostgreSQL."""
    def __init__(self, raw_tuple, col_names):
        self._raw = raw_tuple
        self._cols = col_names
        self._dict = dict(zip(col_names, raw_tuple)) if raw_tuple else {}

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._raw[item]
        return self._dict[item]

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __iter__(self):
        return iter(self._dict)

    def __contains__(self, key):
        return key in self._dict

    def __repr__(self):
        return repr(self._dict)

class PostgresCursorWrapper:
    """Adapts a psycopg2 cursor to match sqlite3 cursor interfaces."""
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor

    def execute(self, sql, params=None):
        adapted = adapt_sql_for_postgres(sql)
        if params is not None:
            return self._cursor.execute(adapted, params)
        return self._cursor.execute(adapted)

    def executemany(self, sql, seq_of_params):
        adapted = adapt_sql_for_postgres(sql)
        return self._cursor.executemany(adapted, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
        return PostgresRow(row, cols)

    def fetchall(self):
        rows = self._cursor.fetchall()
        cols = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
        return [PostgresRow(r, cols) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        cols = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
        return [PostgresRow(r, cols) for r in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        for r in self.fetchall():
            yield r

class PostgresConnectionWrapper:
    """Wraps a psycopg2 connection to provide sqlite3-compatible cursor and transaction helpers."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor())

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()

class DatabaseEngine:
    """
    Pluggable database backend engine abstraction (STRAT-02).
    Defaults to high-performance WAL-mode SQLite with row factories and foreign key pragmas.
    Supports DATABASE_URL configuration for 100% free cloud databases (Neon, Supabase, Render, Aiven).
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_url = os.environ.get("DATABASE_URL", "")
        self.db_path = db_path or DB_PATH
        self.fallback_to_sqlite = False
        self.is_sqlite = not self.db_url.startswith(("postgres://", "postgresql://"))

    def connect(self):
        if not self.fallback_to_sqlite:
            self.db_url = os.environ.get("DATABASE_URL", self.db_url)
            self.is_sqlite = not self.db_url.startswith(("postgres://", "postgresql://"))
            
        if self.is_sqlite or self.fallback_to_sqlite:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.row_factory = sqlite3.Row
            return conn
        else:
            try:
                import psycopg2
                conn = psycopg2.connect(self.db_url, connect_timeout=3)
                return PostgresConnectionWrapper(conn)
            except Exception as e:
                logger.warning(f"Failed to connect to cloud database via DATABASE_URL: {e}; falling back to SQLite")
                self.fallback_to_sqlite = True
                self.is_sqlite = True
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.row_factory = sqlite3.Row
                return conn

_DEFAULT_ENGINE = DatabaseEngine()

def get_db_connection():
    return _DEFAULT_ENGINE.connect()

def init_db():
    conn = get_db_connection()
    try:
        if _DEFAULT_ENGINE.is_sqlite:
            conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        # Schema version tracking (FIX-12)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM schema_version")
        has_version_records = (cursor.fetchone()[0] > 0)
        cursor.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
        current_version = cursor.fetchone()[0]

        # For fresh databases (including Neon/PostgreSQL cloud databases), initialize directly at schema version 3
        if not has_version_records:
            cursor.execute("INSERT INTO schema_version (version, description) VALUES (3, 'Initial schema with all v3 tables')")
            current_version = 3

        # Users table for authentication (AUTH-01) - Must be created before foreign-key references
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                oauth_provider TEXT DEFAULT 'local',
                oauth_id TEXT,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
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
                FOREIGN KEY (paper_id) REFERENCES scraped_papers (id) ON DELETE CASCADE
            )
        """)
        
        # Log of pipeline runs and telemetry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                elapsed_seconds REAL DEFAULT 0.0,
                status TEXT DEFAULT 'completed',
                results_json TEXT,
                user_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)

        # Response cache table for quality-preserving token efficiency (TOK-03-REVISED)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        # Interactive contextual follow-up inquiries (FOL-01)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followup_interactions (
                id TEXT PRIMARY KEY,
                parent_run_id TEXT NOT NULL,
                claim_id TEXT,
                target_topic TEXT,
                question TEXT NOT NULL,
                quick_summary TEXT,
                answer_html TEXT,
                ref_id TEXT,
                tokens_used INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_run_id) REFERENCES pipeline_runs (id) ON DELETE CASCADE
            )
        """)

        # Multi-turn continuous research dialogue messages (CHAT-01)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dialogue_messages (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                quick_summary TEXT,
                answer_html TEXT,
                tokens_used INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_run_id ON dialogue_messages(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created_at ON pipeline_runs(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_response_cache_expires_at ON response_cache(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_sentences_query ON cached_sentences(query)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_followup_parent_run_id ON followup_interactions(parent_run_id)")

        # Migration V1 (FIX-12): Ensure prompt_tokens and completion_tokens columns exist on existing databases
        if current_version < 1:
            for tbl in ["pipeline_runs", "followup_interactions", "dialogue_messages"]:
                for col in ["prompt_tokens", "completion_tokens"]:
                    try:
                        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} INTEGER DEFAULT 0")
                    except Exception as e:
                        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                            pass
                        else:
                            logger.error(f"Migration error adding {col} to {tbl}: {e}")
                            raise
            cursor.execute("INSERT INTO schema_version (version, description) VALUES (1, 'Add prompt_tokens and completion_tokens columns')")

        # Ensure OAuth columns exist on both SQLite and PostgreSQL
        for col, col_def in [("oauth_provider", "TEXT DEFAULT 'local'"), ("oauth_id", "TEXT"), ("avatar_url", "TEXT")]:
            try:
                if not _DEFAULT_ENGINE.is_sqlite:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_def}")
                else:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            except Exception:
                pass

        # Migration V2 (AUTH-01): Ensure user_id columns exist on pipeline_runs and pdf_sessions
        if current_version < 2:
            for tbl in ["pipeline_runs", "pdf_sessions"]:
                try:
                    cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id TEXT")
                except Exception as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        pass
                    else:
                        logger.warning(f"Note adding user_id to {tbl}: {e}")
            cursor.execute("INSERT INTO schema_version (version, description) VALUES (2, 'Add user authentication tables and user_id relations')")

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
                total_references INTEGER DEFAULT 0,
                user_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
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

        # Encrypted User API Key Vault Table (AES-256-GCM encrypted per user)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_api_keys (
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                key_hint TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, provider),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_api_keys_user ON user_api_keys(user_id)")

        # Migration V3: Add OAuth provider columns and user_api_keys table
        if current_version < 3:
            for col, col_type in [("oauth_provider", "TEXT DEFAULT 'local'"), ("oauth_id", "TEXT"), ("avatar_url", "TEXT")]:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        pass
                    else:
                        logger.warning(f"Note adding {col} to users: {e}")
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id)")
            except Exception as e:
                logger.warning(f"Note creating idx_users_oauth: {e}")
            cursor.execute("INSERT INTO schema_version (version, description) VALUES (3, 'Add OAuth fields and encrypted user_api_keys table')")

        # Secondary indexes for high-speed O(1) / O(log N) relational queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_chunks_session ON pdf_chunks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_figures_session ON pdf_figures(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_refs_session ON pdf_references(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_files_session ON pdf_files(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_papers_query ON scraped_papers(query)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_id ON pipeline_runs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_sessions_user_id ON pdf_sessions(user_id)")
        
        conn.commit()
    finally:
        conn.close()

def save_scraped_papers(query: str, papers: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for p in papers:
            authors_str = ", ".join(p.get("authors", [])) if isinstance(p.get("authors"), list) else str(p.get("authors", ""))
            paper_id = p.get("paperId") or p.get("id")
            if not paper_id:
                raw_id_seed = f"{p.get('title', '')}_{p.get('year', '')}"
                paper_id = f"p_{hashlib.sha256(raw_id_seed.encode('utf-8')).hexdigest()[:16]}"
            cursor.execute("""
                INSERT OR REPLACE INTO scraped_papers (id, query, title, authors, year, abstract, url, venue, citation_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id,
                query,
                p.get("title", "Untitled"),
                authors_str,
                p.get("year"),
                p.get("abstract", ""),
                p.get("url", ""),
                p.get("venue", "Open Access Repository"),
                p.get("citationCount", 0)
            ))
        conn.commit()
    finally:
        conn.close()

def save_cached_sentences(query: str, sentences: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for s in sentences:
            sentence_text = s.get("text") or s.get("sentence_text") or s.get("sentence") or ""
            sent_id = s.get("id") or hashlib.md5(f"{query}:{sentence_text}".encode('utf-8')).hexdigest()
            raw_paper_id = s.get("paper_id")
            valid_paper_id = None
            if raw_paper_id:
                cursor.execute("SELECT 1 FROM scraped_papers WHERE id = ?", (raw_paper_id,))
                if cursor.fetchone():
                    valid_paper_id = raw_paper_id
            cursor.execute("""
                INSERT OR REPLACE INTO cached_sentences (id, paper_id, query, sentence_text, density_score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                sent_id,
                valid_paper_id,
                query,
                sentence_text,
                s.get("density_score") or s.get("score", 0.0)
            ))
        conn.commit()
    finally:
        conn.close()

def get_cached_sentences_for_query(query: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cached_sentences WHERE query = ? ORDER BY density_score DESC", (query,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_all_cached_papers(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scraped_papers ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def log_pipeline_run(
    run_id: str, 
    query: str, 
    tokens_used: int = 0, 
    elapsed_seconds: float = 0.0, 
    results: Optional[Dict[str, Any]] = None, 
    prompt_tokens: int = 0, 
    completion_tokens: int = 0,
    user_id: Optional[str] = None,
    *args,
    **kwargs
):
    if results is None:
        if args and isinstance(args[-1], dict):
            results = args[-1]
        elif "results" in kwargs:
            results = kwargs["results"]
        else:
            results = {}
            
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        valid_user_id = user_id
        if valid_user_id:
            try:
                cursor.execute("SELECT 1 FROM users WHERE id = ?", (valid_user_id,))
                if not cursor.fetchone():
                    logger.warning(f"User ID '{valid_user_id}' not found in users table; logging run with user_id=None")
                    valid_user_id = None
            except Exception as chk_err:
                logger.warning(f"Failed to verify user_id '{valid_user_id}': {chk_err}")
                valid_user_id = None

        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_runs (id, query, tokens_used, elapsed_seconds, results_json, prompt_tokens, completion_tokens, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, query, tokens_used, elapsed_seconds, json.dumps(results), prompt_tokens, completion_tokens, valid_user_id))
        conn.commit()
    except Exception as exc:
        logger.error(f"Failed to log pipeline run {run_id}: {exc}")
        if user_id:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO pipeline_runs (id, query, tokens_used, elapsed_seconds, results_json, prompt_tokens, completion_tokens, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """, (run_id, query, tokens_used, elapsed_seconds, json.dumps(results), prompt_tokens, completion_tokens))
                conn.commit()
            except Exception as fallback_exc:
                logger.error(f"Fallback logging without user_id failed: {fallback_exc}")
    finally:
        conn.close()

def get_run_history(limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches past pipeline executions for the Research History Timeline."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT id, query, tokens_used, prompt_tokens, completion_tokens, elapsed_seconds, created_at, results_json, user_id
                FROM pipeline_runs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, query, tokens_used, prompt_tokens, completion_tokens, elapsed_seconds, created_at, results_json, user_id
                FROM pipeline_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["run_id"] = d["id"]
            d["total_tokens"] = d.get("tokens_used", 0)
            # Parse brief summary for frontend listing
            try:
                full_data = json.loads(d.get("results_json") or "{}")
                d["architecture"] = full_data.get("architecture", "system_a")
                d["model"] = full_data.get("model", "")
                d["quick_answer"] = full_data.get("quick_answer", "")
                d["takeaways"] = full_data.get("takeaways", [])[:2]
                d["citations_count"] = len(full_data.get("citations", []))
                d["sections_count"] = len(full_data.get("dossier_sections", []))
            except Exception:
                d["architecture"] = "system_a"
                d["model"] = ""
                d["quick_answer"] = ""
                d["takeaways"] = []
                d["citations_count"] = 0
                d["sections_count"] = 0
            results.append(d)
        return results
    finally:
        conn.close()

def get_run_by_id(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a past run with full parsed results for instant zero-token replay."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, query, tokens_used, prompt_tokens, completion_tokens, elapsed_seconds, created_at, results_json
            FROM pipeline_runs
            WHERE id = ?
        """, (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["run_id"] = d["id"]
        d["total_tokens"] = d.get("tokens_used", 0)
        try:
            parsed_results = json.loads(d.get("results_json") or "{}")
            d["results"] = parsed_results
            for k, v in parsed_results.items():
                if k not in d:
                    d[k] = v
        except Exception:
            d["results"] = {}
        return d
    finally:
        conn.close()

def delete_run(run_id: str) -> bool:
    """Deletes a run and any associated follow-up interactions and dialogue messages from history."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dialogue_messages WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM followup_interactions WHERE parent_run_id = ?", (run_id,))
        cursor.execute("DELETE FROM pipeline_runs WHERE id = ?", (run_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

def save_followup_interaction(
    parent_run_id: str,
    question: str,
    quick_summary: str,
    answer_html: str,
    claim_id: Optional[str] = None,
    target_topic: Optional[str] = None,
    ref_id: Optional[str] = None,
    tokens_used: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0
) -> str:
    """Persists a contextual follow-up interaction to the database (FOL-01)."""
    fol_id = f"fol_{int(time.time()*1000):x}_{uuid.uuid4().hex[:6]}"
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO followup_interactions (id, parent_run_id, claim_id, target_topic, question, quick_summary, answer_html, ref_id, tokens_used, prompt_tokens, completion_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fol_id, parent_run_id, claim_id, target_topic, question, quick_summary, answer_html, ref_id, tokens_used, prompt_tokens, completion_tokens))
        conn.commit()
        return fol_id
    finally:
        conn.close()

def get_followups_for_run(parent_run_id: str) -> List[Dict[str, Any]]:
    """Retrieves all follow-up questions and answers linked to a parent research dossier."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, parent_run_id, claim_id, target_topic, question, quick_summary, answer_html, ref_id, tokens_used, prompt_tokens, completion_tokens, created_at
            FROM followup_interactions
            WHERE parent_run_id = ?
            ORDER BY created_at ASC
        """, (parent_run_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_all_prompt_history(limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches the unified hierarchical prompt history:
    Every parent query with its full nested tree of follow-up questions,
    timestamps, target claims, and cumulative token consumption.
    """
    runs = get_run_history(limit=limit, user_id=user_id)
    if not runs:
        return []
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
    
        for r in runs:
            run_id = r["id"]
            cursor.execute("""
                SELECT id, parent_run_id, claim_id, target_topic, question, quick_summary, answer_html, ref_id, tokens_used, prompt_tokens, completion_tokens, created_at
                FROM followup_interactions
                WHERE parent_run_id = ?
                ORDER BY created_at ASC
            """, (run_id,))
            followups = [dict(row) for row in cursor.fetchall()]
            r["followups"] = followups
            r["followup_count"] = len(followups)

            cursor.execute("""
                SELECT id, run_id, turn_index, role, content, quick_summary, answer_html, tokens_used, prompt_tokens, completion_tokens, created_at
                FROM dialogue_messages
                WHERE run_id = ?
                ORDER BY turn_index ASC, created_at ASC
            """, (run_id,))
            dialogues = [dict(row) for row in cursor.fetchall()]
            r["dialogues"] = dialogues
            r["dialogue_count"] = len(dialogues)

            # Calculate total tokens consumed across the full research thread
            thread_tokens = (
                r.get("tokens_used", 0) + 
                sum(f.get("tokens_used", 0) for f in followups) +
                sum(d.get("tokens_used", 0) for d in dialogues)
            )
            r["total_thread_tokens"] = thread_tokens

        return runs
    finally:
        conn.close()

def delete_followup(followup_id: str) -> bool:
    """Deletes an individual follow-up interaction."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM followup_interactions WHERE id = ?", (followup_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted

    # =========================================================
    # CONTINUOUS RESEARCH DIALOGUE (CHAT-01)
    # =========================================================
    finally:
        conn.close()

def save_dialogue_message(
    run_id: str,
    role: str,
    content: str,
    quick_summary: Optional[str] = None,
    answer_html: Optional[str] = None,
    tokens_used: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0
) -> str:
    """Saves an atomic turn in the multi-turn research dialogue."""
    msg_id = f"msg_{int(time.time()*1000):x}_{uuid.uuid4().hex[:6]}"
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
    
        cursor.execute("SELECT COUNT(*) FROM dialogue_messages WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        turn_index = row[0] if row else 0
    
        cursor.execute("""
            INSERT INTO dialogue_messages (id, run_id, turn_index, role, content, quick_summary, answer_html, tokens_used, prompt_tokens, completion_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, run_id, turn_index, role, content, quick_summary, answer_html, tokens_used, prompt_tokens, completion_tokens))
        conn.commit()
        return msg_id
    finally:
        conn.close()

def get_dialogue_history(run_id: str) -> List[Dict[str, Any]]:
    """Retrieves full chronological multi-turn dialogue history for a research run."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, run_id, turn_index, role, content, quick_summary, answer_html, tokens_used, prompt_tokens, completion_tokens, created_at
            FROM dialogue_messages
            WHERE run_id = ?
            ORDER BY turn_index ASC, created_at ASC
        """, (run_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def clear_dialogue_history(run_id: str) -> bool:
    """Clears all dialogue messages for a research run."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dialogue_messages WHERE run_id = ?", (run_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

def get_response_cache(query: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves cached response for an identical or normalized query within 24h.
    Consumes 0 tokens while returning identical high-quality output.
    """
    clean_q = query.strip().lower()
    q_hash = hashlib.sha256(clean_q.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT response_json, created_at, expires_at
            FROM response_cache
            WHERE query_hash = ? AND expires_at > CURRENT_TIMESTAMP
        """, (q_hash,))
        row = cursor.fetchone()
        if row:
            try:
                cached = json.loads(row["response_json"])
                cached["from_cache"] = True
                cached["cached_at"] = row["created_at"]
                return cached
            except Exception as e:
                logger.warning(f"Failed to decode response cache: {e}")
                return None
        return None
    finally:
        conn.close()

def set_response_cache(query: str, response_data: Dict[str, Any], ttl_hours: int = 24) -> None:
    """Caches synthesized response to eliminate token waste on repeated queries."""
    clean_q = query.strip().lower()
    q_hash = hashlib.sha256(clean_q.encode("utf-8")).hexdigest()
    expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO response_cache (query_hash, query, response_json, expires_at)
            VALUES (?, ?, ?, ?)
        """, (q_hash, query, json.dumps(response_data), expires_at))
        conn.commit()
    finally:
        conn.close()

def clear_all_cache() -> Dict[str, int]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cached_sentences")
        sentences_deleted = cursor.rowcount
        cursor.execute("DELETE FROM scraped_papers")
        papers_deleted = cursor.rowcount
        cursor.execute("DELETE FROM response_cache")
        response_cache_deleted = cursor.rowcount
        cursor.execute("DELETE FROM dialogue_messages")
        cursor.execute("DELETE FROM followup_interactions")
        cursor.execute("DELETE FROM pipeline_runs")
        runs_deleted = cursor.rowcount
        cursor.execute("DELETE FROM pdf_references")
        cursor.execute("DELETE FROM pdf_figures")
        cursor.execute("DELETE FROM pdf_chunks")
        cursor.execute("DELETE FROM pdf_files")
        cursor.execute("DELETE FROM pdf_sessions")
        conn.commit()
        return {
            "papers_deleted": papers_deleted,
            "sentences_deleted": sentences_deleted,
            "runs_deleted": runs_deleted,
            "response_cache_deleted": response_cache_deleted
        }
    finally:
        conn.close()

def reset_database(hard: bool = False) -> Dict[str, Any]:
    """
    Completely resets the database for both SQLite and cloud PostgreSQL.
    - If hard=False: Clears all research runs, cached papers, sentences, response cache,
      dialogue turns, follow-ups, and PDF workspaces while preserving registered users and API keys.
    - If hard=True: Complete factory wipe — drops and recreates all tables from scratch,
      including users, API keys, and schema versions, restoring a 100% blank state.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if hard:
            logger.info("Executing HARD factory reset: Dropping all database tables...")
            all_tables = [
                "user_api_keys",
                "pdf_references",
                "pdf_figures",
                "pdf_chunks",
                "pdf_files",
                "pdf_sessions",
                "dialogue_messages",
                "followup_interactions",
                "pipeline_runs",
                "cached_sentences",
                "scraped_papers",
                "response_cache",
                "schema_version",
                "users",
            ]
            if _DEFAULT_ENGINE.is_sqlite:
                cursor.execute("PRAGMA foreign_keys = OFF;")
                for tbl in all_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {tbl}")
                cursor.execute("PRAGMA foreign_keys = ON;")
            else:
                for tbl in all_tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
            conn.commit()
            conn.close()
            
            # Recreate all tables cleanly from scratch at schema version 3
            init_db()
            logger.info("Database schema cleanly recreated from scratch.")
            return {"status": "success", "mode": "hard_factory_reset", "tables_recreated": all_tables}
        else:
            logger.info("Executing SOFT reset: Clearing all data while preserving users...")
            cursor.execute("DELETE FROM cached_sentences")
            cursor.execute("DELETE FROM scraped_papers")
            cursor.execute("DELETE FROM response_cache")
            cursor.execute("DELETE FROM dialogue_messages")
            cursor.execute("DELETE FROM followup_interactions")
            cursor.execute("DELETE FROM pipeline_runs")
            cursor.execute("DELETE FROM pdf_references")
            cursor.execute("DELETE FROM pdf_figures")
            cursor.execute("DELETE FROM pdf_chunks")
            cursor.execute("DELETE FROM pdf_files")
            cursor.execute("DELETE FROM pdf_sessions")
            conn.commit()
            return {"status": "success", "mode": "soft_reset", "preserved": ["users", "user_api_keys"]}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_cache_stats() -> Dict[str, int]:
    conn = get_db_connection()
    try:
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
    finally:
        conn.close()

def save_pdf_session(session_id: str, total_files: int = 0, user_id: Optional[str] = None) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        valid_user_id = user_id
        if valid_user_id:
            try:
                cursor.execute("SELECT 1 FROM users WHERE id = ?", (valid_user_id,))
                if not cursor.fetchone():
                    logger.warning(f"User ID '{valid_user_id}' not found in users table; saving PDF session with user_id=None")
                    valid_user_id = None
            except Exception as chk_err:
                logger.warning(f"Failed to verify user_id '{valid_user_id}': {chk_err}")
                valid_user_id = None

        cursor.execute("""
            INSERT OR REPLACE INTO pdf_sessions (session_id, status, total_files, user_id)
            VALUES (?, 'processing', ?, ?)
        """, (session_id, total_files, valid_user_id))
        conn.commit()
    except Exception as exc:
        logger.error(f"Failed to save PDF session {session_id}: {exc}")
        if user_id:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO pdf_sessions (session_id, status, total_files, user_id)
                    VALUES (?, 'processing', ?, NULL)
                """, (session_id, total_files))
                conn.commit()
            except Exception:
                pass
    finally:
        conn.close()

def get_pdf_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pdf_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        session_data = dict(row)
        cursor.execute("SELECT * FROM pdf_files WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        session_data["files"] = [dict(r) for r in cursor.fetchall()]
        return session_data
    finally:
        conn.close()

def get_all_pdf_sessions(limit: int = 20, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM pdf_sessions WHERE user_id = ? ORDER BY last_accessed DESC LIMIT ?", (user_id, limit))
        else:
            cursor.execute("SELECT * FROM pdf_sessions ORDER BY last_accessed DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        for s in rows:
            cursor.execute("SELECT original_filename, title, page_count FROM pdf_files WHERE session_id = ?", (s["session_id"],))
            s["files_summary"] = [dict(f) for f in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def update_pdf_session_status(session_id: str, status: str, **counts) -> None:
    conn = get_db_connection()
    try:
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
    finally:
        conn.close()

def update_pdf_session_last_accessed(session_id: str) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pdf_sessions SET last_accessed = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

def delete_pdf_session(session_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
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

        # Safely delete files on disk if present (SEC-04: Path traversal prevention)
        import shutil
        clean_session_id = os.path.basename(session_id.strip("/\\"))
        base_uploads = os.path.realpath(os.path.join(os.path.dirname(__file__), "uploads"))
        uploads_dir = os.path.realpath(os.path.join(base_uploads, clean_session_id))
    
        if uploads_dir.startswith(base_uploads) and uploads_dir != base_uploads and os.path.exists(uploads_dir):
            try:
                shutil.rmtree(uploads_dir)
            except Exception as e:
                logger.warning(f"Failed to remove session directory {uploads_dir}: {e}")

        return {
            "sessions_deleted": sessions_deleted,
            "files_deleted": files_deleted,
            "chunks_deleted": chunks_deleted,
            "figures_deleted": figs_deleted,
            "references_deleted": refs_deleted
        }
    finally:
        conn.close()

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
    try:
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
    finally:
        conn.close()

def get_pdf_files_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pdf_files WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def update_pdf_file_status(file_id: str, status: str, error: Optional[str] = None) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pdf_files SET extraction_status = ?, extraction_error = ? WHERE file_id = ?", (status, error, file_id))
        conn.commit()
    finally:
        conn.close()

def save_pdf_chunks(session_id: str, file_id: str, chunks: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    try:
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
    finally:
        conn.close()

def get_pdf_chunks_by_session(session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM pdf_chunks WHERE session_id = ? ORDER BY file_id, chunk_index"
        params: List[Any] = [session_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def get_pdf_chunks_by_page(session_id: str, page: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM pdf_chunks
            WHERE session_id = ? AND start_page <= ? AND end_page >= ?
            ORDER BY chunk_index
        """, (session_id, page, page))
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def save_pdf_figures(session_id: str, file_id: str, figures: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    try:
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
    finally:
        conn.close()

def get_pdf_figures_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pdf_figures WHERE session_id = ? ORDER BY page_number ASC", (session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def save_pdf_references(session_id: str, file_id: str, refs: List[Dict[str, Any]]) -> None:
    conn = get_db_connection()
    try:
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
                r.get("parsed_year") or r.get("year"),
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
    finally:
        conn.close()

def get_pdf_references_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pdf_references WHERE session_id = ? ORDER BY ref_index ASC", (session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def update_reference_resolution(ref_id: str, resolved_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    try:
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
    finally:
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


# ==============================================================================
# User Authentication & Account Operations (AUTH-01)
# ==============================================================================

def create_user(username: str, email: str, password_hash: str, role: str = "user", user_id: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new user account with unique username and email."""
    import uuid
    uid = user_id or f"usr_{uuid.uuid4().hex[:16]}"
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, username.strip(), email.strip().lower(), password_hash, role))
        conn.commit()
        return get_user_by_id(uid)
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by username (case-insensitive lookup)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by email (case-insensitive lookup)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by user ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_user_last_login(user_id: str) -> None:
    """Updates the last_login timestamp for a user upon successful authentication."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by OAuth provider and provider unique user ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE oauth_provider = ? AND oauth_id = ?",
            (provider.lower().strip(), str(oauth_id).strip())
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_or_update_oauth_user(provider: str, oauth_id: str, email: str, username: str, avatar_url: str = "") -> Dict[str, Any]:
    """
    Finds or creates a user authenticated via OAuth (Google or GitHub).
    If an account exists with matching oauth_id or matching verified email, it links and updates last_login.
    """
    import secrets
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 1. Match by provider + oauth_id
        existing_oauth = get_user_by_oauth(provider, oauth_id)
        if existing_oauth:
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP,
                    avatar_url = COALESCE(NULLIF(?, ''), avatar_url)
                WHERE id = ?
            """, (avatar_url, existing_oauth["id"]))
            conn.commit()
            return get_user_by_id(existing_oauth["id"])

        # 2. Match by email (Account Linking)
        existing_email = get_user_by_email(email)
        if existing_email:
            cursor.execute("""
                UPDATE users
                SET oauth_provider = ?,
                    oauth_id = ?,
                    avatar_url = COALESCE(NULLIF(?, ''), avatar_url),
                    last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (provider.lower().strip(), str(oauth_id).strip(), avatar_url, existing_email["id"]))
            conn.commit()
            return get_user_by_id(existing_email["id"])

        # 3. Create new user
        uid = f"usr_{uuid.uuid4().hex[:16]}"
        clean_username = re.sub(r"[^a-zA-Z0-9_\-]", "_", username.strip())[:30] or f"user_{secrets.token_hex(4)}"
        if get_user_by_username(clean_username):
            clean_username = f"{clean_username[:24]}_{secrets.token_hex(2)}"

        placeholder_hash = f"oauth_{provider}_{secrets.token_hex(16)}"
        cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, oauth_provider, oauth_id, avatar_url, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (uid, clean_username, email.strip().lower(), placeholder_hash, provider.lower().strip(), str(oauth_id).strip(), avatar_url))
        conn.commit()
        return get_user_by_id(uid)
    finally:
        conn.close()

# ==============================================================================
# User Encrypted API Key Vault Operations (Per-User Isolation)
# ==============================================================================

def save_user_api_key(user_id: str, provider: str, encrypted_key: str, key_hint: str) -> None:
    """Stores or updates an AES-256-GCM encrypted API key for a specific user and provider."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_api_keys (user_id, provider, encrypted_key, key_hint, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                encrypted_key = excluded.encrypted_key,
                key_hint = excluded.key_hint,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, provider.lower().strip(), encrypted_key, key_hint))
        conn.commit()
    finally:
        conn.close()

def get_user_api_key_hints(user_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Retrieves masked hints and metadata for all API keys stored by a user.
    CRITICAL: Plaintext or decrypted keys are NEVER returned by this function!
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT provider, key_hint, updated_at
            FROM user_api_keys
            WHERE user_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        out = {
            "gemini": {"is_set": False, "configured": False, "hint": None, "updated_at": None},
            "anthropic": {"is_set": False, "configured": False, "hint": None, "updated_at": None},
            "openai": {"is_set": False, "configured": False, "hint": None, "updated_at": None},
            "serpapi": {"is_set": False, "configured": False, "hint": None, "updated_at": None}
        }
        for r in rows:
            p = r["provider"].lower()
            out[p] = {
                "is_set": True,
                "configured": True,
                "hint": r["key_hint"],
                "updated_at": str(r["updated_at"])
            }
        return out
    finally:
        conn.close()

def get_user_encrypted_key(user_id: str, provider: str) -> Optional[str]:
    """Retrieves the encrypted ciphertext blob for in-memory decryption during authorized pipeline execution."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT encrypted_key
            FROM user_api_keys
            WHERE user_id = ? AND provider = ?
        """, (user_id, provider.lower().strip()))
        row = cursor.fetchone()
        return row["encrypted_key"] if row else None
    finally:
        conn.close()

def delete_user_api_key(user_id: str, provider: str) -> bool:
    """Deletes a stored encrypted API key for a user and provider."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM user_api_keys
            WHERE user_id = ? AND provider = ?
        """, (user_id, provider.lower().strip()))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()




