"""SQLite storage: contacts, conversations, visible messages, raw API transcript, escalations."""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

import config

_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    channel TEXT NOT NULL,              -- whatsapp | instagram | web
    external_id TEXT NOT NULL,          -- phone number / IG scoped id
    name TEXT,
    language TEXT,                      -- fr | ar | darija | en
    kind TEXT DEFAULT 'unknown',        -- prospect | student | parent | other | unknown
    lead_status TEXT DEFAULT 'new',     -- new | ready | undecided | general | not_fit | enrolled
    program_interest TEXT,
    level TEXT,                         -- e.g. "Bac 2026 Sciences Maths", "Bac+2 DUT"
    city TEXT,
    intake TEXT,
    notes TEXT,
    tags TEXT DEFAULT '[]',
    subscribed INTEGER DEFAULT 1,
    created_at REAL,
    updated_at REAL,
    UNIQUE(channel, external_id)
);
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    handler TEXT DEFAULT 'ai',          -- ai | human
    assignee TEXT,
    status TEXT DEFAULT 'open',         -- open | closed
    last_inbound_at REAL,
    last_outbound_at REAL,
    followups_sent INTEGER DEFAULT 0,
    pending_human_notes TEXT DEFAULT '[]',
    created_at REAL,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    direction TEXT NOT NULL,            -- in | out
    author TEXT NOT NULL,               -- contact | ai | <staff name> | system
    text TEXT NOT NULL,
    created_at REAL
);
-- Append-only Claude transcript (exact content blocks), replayed on every turn.
CREATE TABLE IF NOT EXISTS api_messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,              -- JSON
    created_at REAL
);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    category TEXT,                      -- admissions | finance | scolarite | urgent | knowledge_gap | other
    summary TEXT,
    resolved INTEGER DEFAULT 0,
    created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_msgs_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_api_conv ON api_messages(conversation_id);
"""


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = None


@contextmanager
def cursor():
    global _conn
    with _lock:
        if _conn is None:
            _conn = _connect()
            _conn.executescript(SCHEMA)
        cur = _conn.cursor()
        try:
            yield cur
            _conn.commit()
        except Exception:
            _conn.rollback()
            raise


def reset_for_tests(path: str):
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        config.DB_PATH = path
        _conn = None


def now() -> float:
    return time.time()


def row(r):
    return dict(r) if r is not None else None


# ---------- contacts / conversations ----------

def get_or_create_conversation(channel: str, external_id: str, name: str | None = None):
    """Return (contact, conversation) for an inbound sender; reuse the open conversation."""
    with cursor() as c:
        c.execute("SELECT * FROM contacts WHERE channel=? AND external_id=?", (channel, external_id))
        contact = c.fetchone()
        if contact is None:
            c.execute(
                "INSERT INTO contacts(channel, external_id, name, created_at, updated_at) VALUES(?,?,?,?,?)",
                (channel, external_id, name, now(), now()),
            )
            c.execute("SELECT * FROM contacts WHERE id=?", (c.lastrowid,))
            contact = c.fetchone()
        elif name and not contact["name"]:
            c.execute("UPDATE contacts SET name=?, updated_at=? WHERE id=?", (name, now(), contact["id"]))
        c.execute(
            "SELECT * FROM conversations WHERE contact_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (contact["id"],),
        )
        conv = c.fetchone()
        if conv is None:
            c.execute(
                "INSERT INTO conversations(contact_id, created_at, updated_at) VALUES(?,?,?)",
                (contact["id"], now(), now()),
            )
            c.execute("SELECT * FROM conversations WHERE id=?", (c.lastrowid,))
            conv = c.fetchone()
        return row(contact), row(conv)


def get_conversation(conv_id: int):
    with cursor() as c:
        c.execute("SELECT * FROM conversations WHERE id=?", (conv_id,))
        return row(c.fetchone())


def get_contact(contact_id: int):
    with cursor() as c:
        c.execute("SELECT * FROM contacts WHERE id=?", (contact_id,))
        return row(c.fetchone())


CONTACT_FIELDS = {"name", "language", "kind", "lead_status", "program_interest", "level",
                  "city", "intake", "notes", "tags", "subscribed"}
CONV_FIELDS = {"handler", "assignee", "status", "last_inbound_at", "last_outbound_at",
               "followups_sent", "pending_human_notes"}


def update_contact(contact_id: int, **fields):
    fields = {k: v for k, v in fields.items() if k in CONTACT_FIELDS and v is not None}
    if not fields:
        return
    if "tags" in fields and not isinstance(fields["tags"], str):
        fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
    sets = ", ".join(f"{k}=?" for k in fields)
    with cursor() as c:
        c.execute(f"UPDATE contacts SET {sets}, updated_at=? WHERE id=?", (*fields.values(), now(), contact_id))


def update_conversation(conv_id: int, **fields):
    fields = {k: v for k, v in fields.items() if k in CONV_FIELDS}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with cursor() as c:
        c.execute(f"UPDATE conversations SET {sets}, updated_at=? WHERE id=?", (*fields.values(), now(), conv_id))


# ---------- messages ----------

def add_message(conv_id: int, direction: str, author: str, text: str):
    with cursor() as c:
        c.execute(
            "INSERT INTO messages(conversation_id, direction, author, text, created_at) VALUES(?,?,?,?,?)",
            (conv_id, direction, author, text, now()),
        )
        col = "last_inbound_at" if direction == "in" else "last_outbound_at"
        c.execute(f"UPDATE conversations SET {col}=?, updated_at=? WHERE id=?", (now(), now(), conv_id))


def list_messages(conv_id: int):
    with cursor() as c:
        c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conv_id,))
        return [row(r) for r in c.fetchall()]


def append_api_message(conv_id: int, role: str, content):
    with cursor() as c:
        c.execute(
            "INSERT INTO api_messages(conversation_id, role, content, created_at) VALUES(?,?,?,?)",
            (conv_id, role, json.dumps(content, ensure_ascii=False), now()),
        )


def load_api_messages(conv_id: int):
    with cursor() as c:
        c.execute("SELECT role, content FROM api_messages WHERE conversation_id=? ORDER BY id", (conv_id,))
        return [{"role": r["role"], "content": json.loads(r["content"])} for r in c.fetchall()]


# ---------- escalations ----------

def add_escalation(conv_id: int, category: str, summary: str):
    with cursor() as c:
        c.execute(
            "INSERT INTO escalations(conversation_id, category, summary, created_at) VALUES(?,?,?,?)",
            (conv_id, category, summary, now()),
        )
        return c.lastrowid


def list_escalations(conv_id: int | None = None, unresolved_only=True):
    q = "SELECT * FROM escalations WHERE 1=1"
    args = []
    if conv_id is not None:
        q += " AND conversation_id=?"
        args.append(conv_id)
    if unresolved_only:
        q += " AND resolved=0"
    with cursor() as c:
        c.execute(q + " ORDER BY id DESC", args)
        return [row(r) for r in c.fetchall()]


# ---------- inbox queries ----------

def list_conversations(handler: str | None = None, q: str | None = None, lead_status: str | None = None):
    sql = """SELECT cv.*, ct.name, ct.channel, ct.external_id, ct.lead_status, ct.kind,
                    (SELECT text FROM messages m WHERE m.conversation_id=cv.id ORDER BY m.id DESC LIMIT 1) AS last_text,
                    (SELECT COUNT(*) FROM escalations e WHERE e.conversation_id=cv.id AND e.resolved=0) AS open_escalations
             FROM conversations cv JOIN contacts ct ON ct.id=cv.contact_id WHERE 1=1"""
    args = []
    if handler:
        sql += " AND cv.handler=?"
        args.append(handler)
    if lead_status:
        sql += " AND ct.lead_status=?"
        args.append(lead_status)
    if q:
        sql += " AND (ct.name LIKE ? OR ct.external_id LIKE ? OR EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id=cv.id AND m.text LIKE ?))"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY cv.updated_at DESC LIMIT 200"
    with cursor() as c:
        c.execute(sql, args)
        return [row(r) for r in c.fetchall()]


def list_contacts(filters: dict | None = None):
    filters = filters or {}
    sql = "SELECT * FROM contacts WHERE 1=1"
    args = []
    for key in ("channel", "kind", "lead_status", "language", "city"):
        if filters.get(key):
            sql += f" AND {key}=?"
            args.append(filters[key])
    if filters.get("program_contains"):
        sql += " AND program_interest LIKE ?"
        args.append(f"%{filters['program_contains']}%")
    if filters.get("text"):
        sql += " AND (name LIKE ? OR notes LIKE ? OR external_id LIKE ?)"
        args += [f"%{filters['text']}%"] * 3
    if filters.get("subscribed") is not None:
        sql += " AND subscribed=?"
        args.append(1 if filters["subscribed"] else 0)
    sql += " ORDER BY updated_at DESC LIMIT 500"
    with cursor() as c:
        c.execute(sql, args)
        return [row(r) for r in c.fetchall()]


def contact_stats():
    with cursor() as c:
        c.execute("""SELECT channel, COUNT(*) total, SUM(subscribed) subscribed,
                     SUM(CASE WHEN subscribed=0 THEN 1 ELSE 0 END) unsubscribed
                     FROM contacts GROUP BY channel""")
        by_channel = [row(r) for r in c.fetchall()]
        c.execute("SELECT lead_status, COUNT(*) n FROM contacts GROUP BY lead_status")
        by_status = {r["lead_status"]: r["n"] for r in c.fetchall()}
        c.execute("SELECT handler, COUNT(*) n FROM conversations WHERE status='open' GROUP BY handler")
        by_handler = {r["handler"]: r["n"] for r in c.fetchall()}
    return {"by_channel": by_channel, "by_lead_status": by_status, "open_by_handler": by_handler}


def followup_candidates(silent_since: float, max_followups: int):
    """Undecided prospects, AI-handled, whose last message was ours and who went quiet."""
    with cursor() as c:
        c.execute(
            """SELECT cv.*, ct.channel, ct.external_id, ct.name, ct.program_interest, ct.language
               FROM conversations cv JOIN contacts ct ON ct.id=cv.contact_id
               WHERE cv.handler='ai' AND cv.status='open' AND ct.subscribed=1
                 AND ct.lead_status IN ('undecided','new') AND ct.kind IN ('prospect','parent','unknown')
                 AND cv.followups_sent < ?
                 AND cv.last_outbound_at IS NOT NULL AND cv.last_outbound_at < ?
                 AND (cv.last_inbound_at IS NULL OR cv.last_inbound_at < cv.last_outbound_at)""",
            (max_followups, silent_since),
        )
        return [row(r) for r in c.fetchall()]
