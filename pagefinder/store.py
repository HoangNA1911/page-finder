import json
import sqlite3
import struct
from pathlib import Path
from typing import Any

from pagefinder import config
from pagefinder.utils import utc_now

try:
    import sqlite_vec
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    sqlite_vec = None


def _resolve_sqlite_module():
    """Pick a sqlite3 module that can load the sqlite-vec extension.

    CPython only exposes Connection.enable_load_extension when it was built with
    loadable-extension support (often disabled in macOS system Python). When it is
    missing we fall back to the pysqlite3 binary wheel if it happens to be present.
    """
    if hasattr(sqlite3.Connection, "enable_load_extension"):
        return sqlite3
    try:
        import pysqlite3

        return pysqlite3
    except ImportError:
        return sqlite3


_sqlite = _resolve_sqlite_module()


def _deserialize_float32(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class PagefinderStore:
    def __init__(self, db_path: Path, index_path: Path) -> None:
        self.db_path = db_path
        self.index_path = index_path
        self.embedding_dim = config.EMBEDDING_DIM
        self._init_db()

    def _connect(self):
        connection = _sqlite.connect(self.db_path)
        connection.row_factory = _sqlite.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        if sqlite_vec is None:
            raise RuntimeError(
                "sqlite-vec is not installed. Run `pip install -r requirements.txt`."
            )
        try:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            connection.enable_load_extension(False)
        except AttributeError as error:
            connection.close()
            raise RuntimeError(
                "This Python build cannot load SQLite extensions (enable_load_extension "
                "unavailable). Install `pysqlite3-binary` or use a Python built with "
                "--enable-loadable-sqlite-extensions."
            ) from error
        return connection

    def _init_db(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    page_title TEXT NOT NULL,
                    query TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

            stored_dim = connection.execute(
                "SELECT value FROM index_meta WHERE key = 'embedding_dim'"
            ).fetchone()
            if stored_dim is not None and int(stored_dim["value"]) != self.embedding_dim:
                # The embedding dimension changed; drop the index so it is rebuilt
                # cleanly on the next sync (vec0 tables have a fixed dimension).
                connection.execute("DROP TABLE IF EXISTS vec_chunks")
                connection.execute("DROP TABLE IF EXISTS chunks_fts")
                connection.execute("DROP TABLE IF EXISTS chunks")
                connection.execute("DROP TABLE IF EXISTS pages")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pages (
                    page_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT,
                    version INTEGER,
                    fetched_at TEXT,
                    source_mode TEXT,
                    index_schema_version INTEGER,
                    normalized_title TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT UNIQUE,
                    page_id TEXT NOT NULL,
                    heading TEXT,
                    text TEXT,
                    page_title TEXT,
                    page_url TEXT,
                    normalized_heading TEXT,
                    normalized_text TEXT,
                    tokens TEXT,
                    token_count INTEGER
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_page_id ON chunks(page_id)"
            )
            connection.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[{self.embedding_dim}])"
            )
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(heading, text, page_title)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO index_meta (key, value) VALUES ('embedding_dim', ?)",
                (str(self.embedding_dim),),
            )
            connection.commit()
        finally:
            connection.close()

    def _delete_page_chunks(self, connection, page_id: str) -> None:
        rows = connection.execute(
            "SELECT id FROM chunks WHERE page_id = ?", (page_id,)
        ).fetchall()
        for row in rows:
            connection.execute("DELETE FROM vec_chunks WHERE rowid = ?", (row["id"],))
            connection.execute("DELETE FROM chunks_fts WHERE rowid = ?", (row["id"],))
        connection.execute("DELETE FROM chunks WHERE page_id = ?", (page_id,))

    def _touch_last_sync(self, connection) -> None:
        connection.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES ('last_sync_at', ?)",
            (utc_now(),),
        )

    def upsert_page(self, page: dict[str, Any]) -> None:
        connection = self._connect()
        try:
            page_id = page["page_id"]
            self._delete_page_chunks(connection, page_id)
            connection.execute(
                """
                INSERT OR REPLACE INTO pages
                    (page_id, title, url, version, fetched_at, source_mode,
                     index_schema_version, normalized_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page_id,
                    page.get("title", ""),
                    page.get("url", ""),
                    page.get("version"),
                    page.get("fetched_at"),
                    page.get("source_mode"),
                    page.get("index_schema_version"),
                    page.get("normalized_title"),
                ),
            )
            for chunk in page.get("chunks", []):
                cursor = connection.execute(
                    """
                    INSERT INTO chunks
                        (chunk_id, page_id, heading, text, page_title, page_url,
                         normalized_heading, normalized_text, tokens, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk["chunk_id"],
                        page_id,
                        chunk.get("heading", ""),
                        chunk.get("text", ""),
                        chunk.get("page_title", ""),
                        chunk.get("page_url", ""),
                        chunk.get("normalized_heading", ""),
                        chunk.get("normalized_text", ""),
                        json.dumps(chunk.get("tokens", [])),
                        chunk.get("token_count", 0),
                    ),
                )
                rowid = cursor.lastrowid
                connection.execute(
                    "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
                    (rowid, sqlite_vec.serialize_float32(chunk["embedding"])),
                )
                connection.execute(
                    "INSERT INTO chunks_fts (rowid, heading, text, page_title) VALUES (?, ?, ?, ?)",
                    (rowid, chunk.get("heading", ""), chunk.get("text", ""), chunk.get("page_title", "")),
                )
            self._touch_last_sync(connection)
            connection.commit()
        finally:
            connection.close()

    def prune_pages(self, active_page_ids: set[str], source_mode: str) -> None:
        connection = self._connect()
        try:
            rows = connection.execute("SELECT page_id, source_mode FROM pages").fetchall()
            stale = [
                row["page_id"]
                for row in rows
                if row["page_id"] not in active_page_ids or row["source_mode"] != source_mode
            ]
            if not stale:
                return
            for page_id in stale:
                self._delete_page_chunks(connection, page_id)
                connection.execute("DELETE FROM pages WHERE page_id = ?", (page_id,))
            self._touch_last_sync(connection)
            connection.commit()
        finally:
            connection.close()

    def get_page(self, page_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            page_row = connection.execute(
                "SELECT * FROM pages WHERE page_id = ?", (page_id,)
            ).fetchone()
            if page_row is None:
                return None
            chunk_rows = connection.execute(
                """
                SELECT chunk_id, heading, text, page_title, page_url,
                       normalized_heading, normalized_text, tokens, token_count
                FROM chunks WHERE page_id = ? ORDER BY id
                """,
                (page_id,),
            ).fetchall()
            return self._page_row_to_dict(page_row, chunk_rows)
        finally:
            connection.close()

    @staticmethod
    def _page_row_to_dict(page_row, chunk_rows) -> dict[str, Any]:
        return {
            "page_id": page_row["page_id"],
            "title": page_row["title"],
            "url": page_row["url"],
            "version": page_row["version"],
            "fetched_at": page_row["fetched_at"],
            "source_mode": page_row["source_mode"],
            "index_schema_version": page_row["index_schema_version"],
            "normalized_title": page_row["normalized_title"],
            "chunks": [
                {
                    "chunk_id": row["chunk_id"],
                    "heading": row["heading"],
                    "text": row["text"],
                    "page_id": page_row["page_id"],
                    "page_title": row["page_title"],
                    "page_url": row["page_url"],
                    "normalized_heading": row["normalized_heading"],
                    "normalized_text": row["normalized_text"],
                    "tokens": json.loads(row["tokens"]) if row["tokens"] else [],
                    "token_count": row["token_count"],
                }
                for row in chunk_rows
            ],
        }

    def count_pages(self) -> int:
        connection = self._connect()
        try:
            return connection.execute("SELECT COUNT(*) AS total FROM pages").fetchone()["total"]
        finally:
            connection.close()

    def knn_chunk_rowids(self, query_vector: list[float], k: int) -> list[int]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT rowid FROM vec_chunks
                WHERE embedding MATCH ? AND k = ?
                ORDER BY distance
                """,
                (sqlite_vec.serialize_float32(query_vector), k),
            ).fetchall()
            return [row["rowid"] for row in rows]
        finally:
            connection.close()

    def fts_chunk_rowids(self, fts_query: str, limit: int) -> list[int]:
        if not fts_query:
            return []
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit),
            ).fetchall()
            return [row["rowid"] for row in rows]
        finally:
            connection.close()

    def get_chunks_for_rerank(self, rowids: list[int]) -> list[dict[str, Any]]:
        if not rowids:
            return []
        connection = self._connect()
        try:
            placeholders = ",".join("?" for _ in rowids)
            chunk_rows = connection.execute(
                f"""
                SELECT c.id, c.chunk_id, c.page_id, c.heading, c.text,
                       c.normalized_heading, c.normalized_text, c.tokens, c.token_count,
                       p.title AS page_title, p.url AS page_url, p.normalized_title
                FROM chunks c JOIN pages p ON c.page_id = p.page_id
                WHERE c.id IN ({placeholders})
                """,
                rowids,
            ).fetchall()
            vec_rows = connection.execute(
                f"SELECT rowid, embedding FROM vec_chunks WHERE rowid IN ({placeholders})",
                rowids,
            ).fetchall()
            embeddings = {row["rowid"]: _deserialize_float32(row["embedding"]) for row in vec_rows}
            results: list[dict[str, Any]] = []
            for row in chunk_rows:
                results.append(
                    {
                        "page_id": row["page_id"],
                        "title": row["page_title"],
                        "url": row["page_url"],
                        "normalized_title": row["normalized_title"],
                        "chunk_id": row["chunk_id"],
                        "heading": row["heading"],
                        "text": row["text"],
                        "normalized_heading": row["normalized_heading"],
                        "normalized_text": row["normalized_text"],
                        "tokens": json.loads(row["tokens"]) if row["tokens"] else [],
                        "token_count": row["token_count"],
                        "embedding": embeddings.get(row["id"], []),
                    }
                )
            return results
        finally:
            connection.close()

    def add_read(self, actor_id: str, page_id: str, page_title: str, query: str) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO reading_history (actor_id, page_id, page_title, query, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (actor_id, page_id, page_title, query, utc_now()),
            )
            connection.commit()
        finally:
            connection.close()

    def list_reads(self, actor_id: str, limit: int) -> list[sqlite3.Row]:
        connection = self._connect()
        try:
            return connection.execute(
                """
                SELECT page_id, page_title, query, created_at
                FROM reading_history
                WHERE actor_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (actor_id, limit),
            ).fetchall()
        finally:
            connection.close()
