import sqlite3
import hashlib
import uuid
from datetime import datetime

STORE_DB = "chat_store.db"


def init_db():
    conn = sqlite3.connect(STORE_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        csv_filename TEXT,
        csv_db_path TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        charts_json TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Auth ──────────────────────────────────────────────────────────────────────

def create_user(username: str, password: str) -> bool:
    try:
        conn = sqlite3.connect(STORE_DB)
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (str(uuid.uuid4()), username, _hash(password), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # username taken


def verify_user(username: str, password: str):
    conn = sqlite3.connect(STORE_DB)
    row = conn.execute(
        "SELECT id FROM users WHERE username=? AND password_hash=?",
        (username, _hash(password))
    ).fetchone()
    conn.close()
    return row[0] if row else None


# ── Chats ─────────────────────────────────────────────────────────────────────

def create_chat(user_id: str, title: str = "New Chat") -> str:
    chat_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = sqlite3.connect(STORE_DB)
    conn.execute(
        "INSERT INTO chats VALUES (?,?,?,?,?,?,?)",
        (chat_id, user_id, title, None, None, now, now)
    )
    conn.commit()
    conn.close()
    return chat_id


def get_user_chats(user_id: str) -> list:
    conn = sqlite3.connect(STORE_DB)
    rows = conn.execute(
        "SELECT id, title, csv_filename FROM chats WHERE user_id=? ORDER BY updated_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "csv_filename": r[2]} for r in rows]


def get_chat(chat_id: str) -> dict | None:
    conn = sqlite3.connect(STORE_DB)
    row = conn.execute(
        "SELECT id, user_id, title, csv_filename, csv_db_path FROM chats WHERE id=?",
        (chat_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"id": row[0], "user_id": row[1], "title": row[2],
                "csv_filename": row[3], "csv_db_path": row[4]}
    return None


def update_chat_title(chat_id: str, title: str):
    conn = sqlite3.connect(STORE_DB)
    conn.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))
    conn.commit()
    conn.close()


def update_chat_csv(chat_id: str, filename: str, db_path: str):
    conn = sqlite3.connect(STORE_DB)
    conn.execute(
        "UPDATE chats SET csv_filename=?, csv_db_path=? WHERE id=?",
        (filename, db_path, chat_id)
    )
    conn.commit()
    conn.close()


def delete_chat(chat_id: str):
    conn = sqlite3.connect(STORE_DB)
    conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(chat_id: str, role: str, content: str, charts_json: str = None):
    now = datetime.now().isoformat()
    conn = sqlite3.connect(STORE_DB)
    conn.execute(
        "INSERT INTO messages VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), chat_id, role, content, charts_json, now)
    )
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))
    conn.commit()
    conn.close()


def get_chat_messages(chat_id: str) -> list:
    conn = sqlite3.connect(STORE_DB)
    rows = conn.execute(
        "SELECT role, content, charts_json FROM messages WHERE chat_id=? ORDER BY created_at",
        (chat_id,)
    ).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "charts_json": r[2]} for r in rows]