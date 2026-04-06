from __future__ import annotations

import hashlib
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console

console = Console()

DB_PATH = Path(__file__).parent.parent / "data" / "agent.db"

# Lazy-load sentence transformer to avoid slow startup
_model: Any = None
_model_name = "all-MiniLM-L6-v2"


def _get_model() -> Any:
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            console.print(f"[dim]Loading embedding model: {_model_name}...[/dim]")
            _model = SentenceTransformer(_model_name)
            console.print("[dim]Embedding model loaded.[/dim]")
        except ImportError:
            console.print(
                "[yellow]sentence-transformers not installed. LLM cache disabled.[/yellow]"
            )
            return None
    return _model


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _embed(text: str) -> np.ndarray | None:
    """Get embedding for text. Returns None if model unavailable."""
    model = _get_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding
    except Exception as e:
        console.print(f"[yellow]Embedding failed: {e}[/yellow]")
        return None


def _serialize_embedding(embedding: np.ndarray) -> bytes:
    """Serialize numpy array to bytes for SQLite BLOB storage."""
    return embedding.astype(np.float32).tobytes()


def _deserialize_embedding(blob: bytes) -> np.ndarray:
    """Deserialize bytes from SQLite BLOB to numpy array."""
    n = len(blob) // 4  # float32 = 4 bytes
    return np.frombuffer(blob, dtype=np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two normalized vectors."""
    # Vectors are already normalized (normalize_embeddings=True)
    dot = float(np.dot(a, b))
    return min(1.0, max(-1.0, dot))


def _ensure_table() -> None:
    """Make sure llm_cache table exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                embedding BLOB,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON llm_cache(prompt_hash)")
        conn.commit()
    finally:
        conn.close()


_ensure_table()


def get_cached(prompt: str, threshold: float = 0.92) -> str | None:
    """
    Look up a semantically similar prompt in the cache.

    Returns cached response if similarity >= threshold, else None.
    Uses exact hash match first, then semantic similarity.
    """
    prompt_hash = _hash_prompt(prompt)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # Fast path: exact hash match
        row = conn.execute(
            "SELECT response FROM llm_cache WHERE prompt_hash=? LIMIT 1",
            (prompt_hash,),
        ).fetchone()
        if row:
            console.print("[dim]Cache HIT (exact match)[/dim]")
            return row["response"]

        # Semantic search
        query_embedding = _embed(prompt)
        if query_embedding is None:
            return None

        # Load all cached embeddings for comparison
        rows = conn.execute(
            "SELECT id, response, embedding FROM llm_cache WHERE embedding IS NOT NULL"
        ).fetchall()

        if not rows:
            return None

        best_sim = 0.0
        best_response: str | None = None

        for row in rows:
            if row["embedding"] is None:
                continue
            cached_emb = _deserialize_embedding(row["embedding"])
            if cached_emb.shape != query_embedding.shape:
                continue
            sim = _cosine_similarity(query_embedding, cached_emb)
            if sim > best_sim:
                best_sim = sim
                best_response = row["response"]

        if best_sim >= threshold and best_response:
            console.print(
                f"[dim]Cache HIT (semantic similarity: {best_sim:.3f} >= {threshold})[/dim]"
            )
            return best_response

        console.print(
            f"[dim]Cache MISS (best similarity: {best_sim:.3f} < {threshold})[/dim]"
        )
        return None

    finally:
        conn.close()


def store(prompt: str, response: str) -> None:
    """Store a prompt-response pair in the cache with its embedding."""
    prompt_hash = _hash_prompt(prompt)
    now = datetime.now(timezone.utc).isoformat()

    # Get embedding (may be None if model unavailable)
    embedding_bytes: bytes | None = None
    embedding = _embed(prompt)
    if embedding is not None:
        embedding_bytes = _serialize_embedding(embedding)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """INSERT OR REPLACE INTO llm_cache
               (prompt_hash, prompt, response, embedding, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (prompt_hash, prompt, response, embedding_bytes, now),
        )
        conn.commit()
        console.print("[dim]Cache stored.[/dim]")
    except Exception as e:
        console.print(f"[yellow]Cache store failed: {e}[/yellow]")
    finally:
        conn.close()


def clear_old_cache(days: int = 30) -> int:
    """Remove cache entries older than N days. Returns count removed."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.execute(
            "DELETE FROM llm_cache WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.commit()
        count: int = cursor.rowcount
        if count > 0:
            console.print(f"[dim]Cleared {count} old cache entries.[/dim]")
        return count
    finally:
        conn.close()


def cache_stats() -> dict[str, int]:
    """Return basic cache statistics."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT COUNT(*) as total FROM llm_cache").fetchone()
        total = row["total"] if row else 0
        row = conn.execute(
            "SELECT COUNT(*) as recent FROM llm_cache WHERE created_at >= datetime('now', '-7 days')"
        ).fetchone()
        recent = row["recent"] if row else 0
        return {"total": total, "recent_7d": recent}
    finally:
        conn.close()
