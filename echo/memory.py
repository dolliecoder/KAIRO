"""Local SQLite memory. Every memory is stored in both scripts plus latin keywords,
so a Devanagari memory is found by a Latin query and vice versa."""
import sqlite3
import string
import time
from difflib import SequenceMatcher
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "echo.db"

_db = None


def _conn() -> sqlite3.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
        _db.execute("""CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY, devanagari TEXT, latin TEXT, keywords TEXT, created REAL)""")
        try:  # raw = Prisma's own transcript of the approved utterance (its spelling, used for boosting)
            _db.execute("ALTER TABLE memories ADD COLUMN raw TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
    return _db


_EDGE_PUNCT = string.punctuation + "।॥‘’“”…"


def tokens(text: str) -> set[str]:
    """Whitespace split, not \\w+: \\w does not match Devanagari vowel signs and would cut words apart."""
    words = (w.strip(_EDGE_PUNCT) for w in text.lower().replace("-", " ").split())
    return {w for w in words if w}


def save(devanagari: str, latin: str, keywords: list[str], raw: str = "") -> int:
    c = _conn()
    cur = c.execute("INSERT INTO memories(devanagari, latin, keywords, created, raw) VALUES(?,?,?,?,?)",
                    (devanagari, latin, " ".join(k.lower() for k in keywords), time.time(), raw))
    c.commit()
    return cur.lastrowid


def all_memories() -> list[dict]:
    rows = _conn().execute("SELECT id, devanagari, latin, keywords, created, raw FROM memories").fetchall()
    return [dict(id=r[0], devanagari=r[1], latin=r[2], keywords=r[3], created=r[4], raw=r[5] or "")
            for r in rows]


def _similar(a: str, b: str) -> bool:
    return a == b or (len(a) > 3 and len(b) > 3 and SequenceMatcher(None, a, b).ratio() >= 0.8)


def search(query_terms: list[str], limit: int = 5) -> list[tuple[float, dict]]:
    """Score = share of query terms (either script) that match a memory's tokens, exactly or fuzzily."""
    q = set()
    for t in query_terms:
        q |= tokens(t)
    hits = []
    for m in all_memories():
        mt = tokens(f"{m['devanagari']} {m['latin']} {m['keywords']}")
        score = sum(1.0 for w in q if any(_similar(w, x) for x in mt))
        if score:
            hits.append((score / max(len(q), 1), m))
    hits.sort(key=lambda h: -h[0])
    return hits[:limit]


def delete(memory_id: int) -> None:
    _conn().execute("DELETE FROM memories WHERE id=?", (memory_id,))
    _conn().commit()
