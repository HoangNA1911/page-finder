import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from pagefinder.utils import utc_now


class PagefinderStore:
    def __init__(self, db_path: Path, index_path: Path) -> None:
        self.db_path = db_path
        self.index_path = index_path
        self.index_lock = Lock()
        self._init_db()
        self._init_index()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
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
            connection.commit()

    def _init_index(self) -> None:
        if self.index_path.exists():
            return
        self.save_index({"pages": {}, "last_sync_at": None})

    def load_index(self) -> dict[str, Any]:
        with self.index_lock:
            with self.index_path.open("r", encoding="utf-8") as file:
                return json.load(file)

    def save_index(self, payload: dict[str, Any]) -> None:
        with self.index_lock:
            with self.index_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)

    def upsert_page(self, page: dict[str, Any]) -> None:
        index_payload = self.load_index()
        index_payload.setdefault("pages", {})[page["page_id"]] = page
        index_payload["last_sync_at"] = utc_now()
        self.save_index(index_payload)

    def prune_pages(self, active_page_ids: set[str], source_mode: str) -> None:
        index_payload = self.load_index()
        pages = index_payload.get("pages", {})
        filtered_pages = {
            page_id: page
            for page_id, page in pages.items()
            if page_id in active_page_ids and page.get("source_mode") == source_mode
        }
        if filtered_pages == pages:
            return
        index_payload["pages"] = filtered_pages
        index_payload["last_sync_at"] = utc_now()
        self.save_index(index_payload)

    def get_page(self, page_id: str) -> dict[str, Any] | None:
        return self.load_index().get("pages", {}).get(page_id)

    def all_pages(self) -> list[dict[str, Any]]:
        return list(self.load_index().get("pages", {}).values())

    def add_note(self, actor_id: str, page_id: str, note: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO document_notes (actor_id, page_id, note, created_at) VALUES (?, ?, ?, ?)",
                (actor_id, page_id, note, utc_now()),
            )
            connection.commit()

    def list_notes(self, actor_id: str, page_id: str | None = None) -> list[sqlite3.Row]:
        with self._connect() as connection:
            if page_id:
                return connection.execute(
                    """
                    SELECT page_id, note, created_at
                    FROM document_notes
                    WHERE actor_id = ? AND page_id = ?
                    ORDER BY created_at DESC
                    """,
                    (actor_id, page_id),
                ).fetchall()
            return connection.execute(
                """
                SELECT page_id, note, created_at
                FROM document_notes
                WHERE actor_id = ?
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (actor_id,),
            ).fetchall()

    def add_read(self, actor_id: str, page_id: str, page_title: str, query: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reading_history (actor_id, page_id, page_title, query, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (actor_id, page_id, page_title, query, utc_now()),
            )
            connection.commit()

    def list_reads(self, actor_id: str, limit: int) -> list[sqlite3.Row]:
        with self._connect() as connection:
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
