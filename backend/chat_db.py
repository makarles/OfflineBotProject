from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("skyassist")

# Путь к базе
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chat.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT 'Новый чат',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON chat_messages (session_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON chat_sessions (updated_at DESC);
            """
        )
    logger.info("chat_db: схема проверена, путь %s", DB_PATH)


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


# Сессии

def create_session(title: str = "Новый чат") -> str:
    session_id = str(uuid.uuid4())
    now = _now_iso()
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, title, now, now),
        )
    logger.info("chat_db: создана сессия %s", session_id)
    return session_id


def list_sessions() -> list[dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions "
            "ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id: str) -> dict[str, Any] | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_session(session_id: str) -> bool:
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("chat_db: удалена сессия %s", session_id)
    return deleted


def rename_session(session_id: str, title: str) -> bool:
    with _get_connection() as conn:
        cursor = conn.execute(
            "UPDATE chat_sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )
        return cursor.rowcount > 0


def _touch_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
        (_now_iso(), session_id),
    )


# Сообщения
def add_message(session_id: str, role: str, content: str) -> int:
    if role not in ("user", "assistant"):
        raise ValueError(f"role должно быть 'user' или 'assistant', получено: {role!r}")

    now = _now_iso()
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        message_id = cursor.lastrowid
        _touch_session(conn, session_id)
    return message_id


def get_messages(session_id: str) -> list[dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def count_messages(session_id: str) -> int:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM chat_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return row["c"]


# CLI для отладки

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m backend.chat_db <init|list|create|messages SESSION_ID>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_db()
        print(f"База инициализирована: {DB_PATH}")

    elif command == "list":
        for s in list_sessions():
            print(f"  {s['id'][:8]}...  {s['title']:40}  updated: {s['updated_at']}")
        if not list_sessions():
            print("  (нет сессий)")

    elif command == "create":
        title = sys.argv[2] if len(sys.argv) > 2 else "Тестовая сессия"
        sid = create_session(title)
        print(f"Создана сессия: {sid}")

    elif command == "messages":
        if len(sys.argv) < 3:
            print("Usage: python -m backend.chat_db messages SESSION_ID")
            sys.exit(1)
        sid = sys.argv[2]
        messages = get_messages(sid)
        for m in messages:
            print(f"  [{m['role']:9}] {m['content'][:100]}")
        if not messages:
            print("  (нет сообщений)")

    else:
        print(f"Неизвестная команда: {command}")
        sys.exit(1)