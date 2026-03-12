import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "sessions.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id               TEXT PRIMARY KEY,
                email            TEXT,
                business_type    TEXT,
                process_name     TEXT,
                transcript       TEXT,
                diagram_asis     TEXT,
                diagram_improved TEXT,
                report           TEXT,
                created_at       TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id         TEXT PRIMARY KEY,
                name       TEXT,
                email      TEXT,
                subject    TEXT,
                message    TEXT,
                created_at TEXT
            )
        """)
        conn.commit()


def list_sessions() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT id, email, business_type, process_name, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()


def get_session(session_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()


def save_session(data: dict) -> str:
    session_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO sessions
               (id, email, business_type, process_name,
                transcript, diagram_asis, diagram_improved, report, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                data.get("email", ""),
                data.get("business_type", ""),
                data.get("process_name", ""),
                data.get("transcript", ""),
                data.get("diagram_asis", ""),
                data.get("diagram_improved", ""),
                data.get("report", ""),
                created_at,
            ),
        )
        conn.commit()
    return session_id


def save_contact(data: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO contact_messages (id, name, email, subject, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                data.get("name", ""),
                data.get("email", ""),
                data.get("subject", ""),
                data.get("message", ""),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
