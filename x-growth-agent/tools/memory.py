from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

DB_PATH = Path(__file__).parent.parent / "data" / "agent.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Initialize all database tables."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tweet_id TEXT UNIQUE,
                type TEXT CHECK(type IN ('thread', 'single', 'quote')) DEFAULT 'single',
                posted_at TEXT,
                impressions INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                bookmarks INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                topic TEXT,
                content_type TEXT,
                hook_style TEXT
            );

            CREATE TABLE IF NOT EXISTS reply_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_account TEXT NOT NULL,
                vip_tweet_id TEXT NOT NULL,
                vip_tweet_content TEXT NOT NULL,
                suggested_reply TEXT NOT NULL,
                strategy TEXT CHECK(strategy IN ('insight', 'disagree', 'question', 'humor')) DEFAULT 'insight',
                status TEXT CHECK(status IN ('pending', 'posted', 'skipped')) DEFAULT 'pending',
                created_at TEXT NOT NULL,
                posted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS engagement_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT NOT NULL,
                account TEXT NOT NULL,
                content TEXT NOT NULL,
                suggestion_type TEXT CHECK(suggestion_type IN ('like', 'quote')) DEFAULT 'like',
                created_at TEXT NOT NULL,
                status TEXT CHECK(status IN ('pending', 'done', 'skipped')) DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS follow_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                follower_count INTEGER DEFAULT 0,
                reason TEXT,
                status TEXT CHECK(status IN ('pending', 'followed', 'skipped')) DEFAULT 'pending',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                tweet_count INTEGER DEFAULT 0,
                sample_tweet TEXT,
                detected_at TEXT NOT NULL,
                acted_on INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT NOT NULL UNIQUE,
                from_user TEXT NOT NULL,
                follower_count INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                flagged_high_value INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                reviewed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS recent_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                posted_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                embedding BLOB,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
        console.print("[green]Database initialized successfully.[/green]")
    finally:
        conn.close()


def insert_tweet(
    content: str,
    tweet_id: str | None = None,
    tweet_type: str = "single",
    posted_at: str | None = None,
    topic: str | None = None,
    content_type: str | None = None,
    hook_style: str | None = None,
) -> int:
    """Insert a tweet record. Returns the new row id."""
    now = posted_at or datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO tweets
               (content, tweet_id, type, posted_at, topic, content_type, hook_style)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (content, tweet_id, tweet_type, now, topic, content_type, hook_style),
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
        return row_id
    finally:
        conn.close()


def update_tweet_metrics(
    tweet_id: str,
    impressions: int = 0,
    likes: int = 0,
    retweets: int = 0,
    replies: int = 0,
    bookmarks: int = 0,
) -> None:
    """Update engagement metrics for a tweet."""
    engagement_rate = 0.0
    if impressions > 0:
        engagement_rate = (likes + retweets + replies + bookmarks) / impressions
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE tweets
               SET impressions=?, likes=?, retweets=?, replies=?, bookmarks=?,
                   engagement_rate=?
               WHERE tweet_id=?""",
            (impressions, likes, retweets, replies, bookmarks, engagement_rate, tweet_id),
        )
        conn.commit()
    finally:
        conn.close()


def insert_reply_suggestion(
    vip_account: str,
    vip_tweet_id: str,
    vip_tweet_content: str,
    suggested_reply: str,
    strategy: str = "insight",
) -> int:
    """Save a reply suggestion. Returns new row id."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO reply_suggestions
               (vip_account, vip_tweet_id, vip_tweet_content, suggested_reply, strategy, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vip_account, vip_tweet_id, vip_tweet_content, suggested_reply, strategy, now),
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
        return row_id
    finally:
        conn.close()


def get_pending_replies(limit: int = 50) -> list[dict[str, Any]]:
    """Return pending reply suggestions ordered by creation time."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM reply_suggestions
               WHERE status='pending'
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_reply_status(suggestion_id: int, status: str, posted_at: str | None = None) -> None:
    """Update reply suggestion status."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE reply_suggestions SET status=?, posted_at=? WHERE id=?",
            (status, posted_at, suggestion_id),
        )
        conn.commit()
    finally:
        conn.close()


def insert_trend(
    keyword: str,
    tweet_count: int = 0,
    sample_tweet: str | None = None,
) -> int:
    """Save a detected trend. Returns new row id."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO trends (keyword, tweet_count, sample_tweet, detected_at) VALUES (?, ?, ?, ?)",
            (keyword, tweet_count, sample_tweet, now),
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
        return row_id
    finally:
        conn.close()


def get_recent_topics(days: int = 14) -> list[str]:
    """Return topics posted in the last N days for dedup check."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT topic FROM recent_topics
               WHERE posted_at >= datetime('now', ?)
               ORDER BY posted_at DESC""",
            (f"-{days} days",),
        ).fetchall()
        return [r["topic"] for r in rows]
    finally:
        conn.close()


def insert_recent_topic(topic: str) -> None:
    """Record a posted topic."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO recent_topics (topic, posted_at) VALUES (?, ?)",
            (topic, now),
        )
        conn.commit()
    finally:
        conn.close()


def insert_mention(
    tweet_id: str,
    from_user: str,
    follower_count: int = 0,
    content: str = "",
    flagged_high_value: bool = False,
) -> None:
    """Save a mention. Ignores duplicate tweet_ids."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO mentions
               (tweet_id, from_user, follower_count, content, flagged_high_value, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tweet_id, from_user, follower_count, content, int(flagged_high_value), now),
        )
        conn.commit()
    finally:
        conn.close()


def get_high_value_mentions(min_followers: int = 1000) -> list[dict[str, Any]]:
    """Return high-value unreviewed mentions."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM mentions
               WHERE follower_count >= ? AND reviewed = 0
               ORDER BY follower_count DESC""",
            (min_followers,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_unreviewed_mentions() -> list[dict[str, Any]]:
    """Return all unreviewed mentions ordered by follower count."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM mentions
               WHERE reviewed = 0
               ORDER BY follower_count DESC""",
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_engagement_suggestion(
    tweet_id: str,
    account: str,
    content: str,
    suggestion_type: str = "like",
) -> int:
    """Save an engagement suggestion."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO engagement_suggestions
               (tweet_id, account, content, suggestion_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (tweet_id, account, content, suggestion_type, now),
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
        return row_id
    finally:
        conn.close()


def get_engagement_suggestions(
    status: str = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return engagement suggestions."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM engagement_suggestions
               WHERE status=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_engagement_suggestions_today(suggestion_type: str) -> int:
    """Count engagement suggestions created today for rate-limiting."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM engagement_suggestions
               WHERE suggestion_type=?
               AND date(created_at) = date('now')""",
            (suggestion_type,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def insert_follow_suggestion(
    username: str,
    follower_count: int = 0,
    reason: str = "",
) -> int:
    """Save a follow suggestion. Returns new row id."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        # Don't insert duplicates for pending suggestions
        existing = conn.execute(
            "SELECT id FROM follow_suggestions WHERE username=? AND status='pending'",
            (username,),
        ).fetchone()
        if existing:
            return existing["id"]
        cursor = conn.execute(
            """INSERT INTO follow_suggestions
               (username, follower_count, reason, created_at)
               VALUES (?, ?, ?, ?)""",
            (username, follower_count, reason, now),
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
        return row_id
    finally:
        conn.close()


def get_follow_suggestions(
    status: str = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return follow suggestions."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM follow_suggestions
               WHERE status=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_follow_suggestions_today() -> int:
    """Count follow suggestions generated today."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM follow_suggestions
               WHERE date(created_at) = date('now')""",
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_agent_state(key: str) -> str | None:
    """Get a persisted agent state value."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM agent_state WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_agent_state(key: str, value: str) -> None:
    """Persist an agent state value."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO agent_state (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_tweets_last_n_days(days: int = 7) -> list[dict[str, Any]]:
    """Return all tweets posted in the last N days."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM tweets
               WHERE posted_at >= datetime('now', ?)
               ORDER BY posted_at DESC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trends_last_n_hours(hours: int = 4) -> list[dict[str, Any]]:
    """Return trends detected in the last N hours."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM trends
               WHERE detected_at >= datetime('now', ?)
               AND acted_on = 0
               ORDER BY tweet_count DESC""",
            (f"-{hours} hours",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_trend_acted_on(trend_id: int) -> None:
    """Mark a trend as acted on."""
    conn = _get_conn()
    try:
        conn.execute("UPDATE trends SET acted_on=1 WHERE id=?", (trend_id,))
        conn.commit()
    finally:
        conn.close()


def get_reply_stats() -> dict[str, int]:
    """Return reply suggestion statistics."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT
               COUNT(CASE WHEN status='pending' THEN 1 END) as pending,
               COUNT(CASE WHEN status='posted' THEN 1 END) as posted,
               COUNT(CASE WHEN status='skipped' THEN 1 END) as skipped
               FROM reply_suggestions
               WHERE created_at >= datetime('now', '-7 days')"""
        ).fetchone()
        return dict(row) if row else {"pending": 0, "posted": 0, "skipped": 0}
    finally:
        conn.close()


def vip_tweet_already_saved(vip_tweet_id: str) -> bool:
    """Check if a VIP tweet already has a reply suggestion."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM reply_suggestions WHERE vip_tweet_id=?",
            (vip_tweet_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
