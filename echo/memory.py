"""Local SQLite memory. Every memory is stored in both scripts plus latin keywords, and as a vector in sqlite-vec,
so a Devanagari memory is found by a Latin query (keywords) and by meaning (embeddings), and vice versa."""
import sqlite3
import string
import time
from concurrent.futures import Future, ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import sqlite_vec

from .log import log
from . import embed
from .embed import DIM
from .words import STOPWORDS

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "echo.db"

_db = None
VEC_OK = False  # False if the sqlite-vec extension could not load: then only keyword search is used
MIN_COSINE = 0.62  # measured: true matches 0.67-0.87, unrelated questions about 0.55


def _load_vec(db: sqlite3.Connection) -> None:
    global VEC_OK
    try:
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(embedding float[{DIM}])")
        VEC_OK = True
    except Exception as e:
        VEC_OK = False
        log("Memory", f"sqlite-vec unavailable, keyword search only: {e}")


def _conn() -> sqlite3.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
        _db.execute("""CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY, devanagari TEXT, latin TEXT, keywords TEXT, created REAL)""")
        _db.execute("""CREATE TABLE IF NOT EXISTS corrections(
            wrong TEXT PRIMARY KEY, right TEXT, created REAL)""")
        _load_vec(_db)
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
    _index(cur.lastrowid, devanagari, latin, keywords)
    return cur.lastrowid


def _doc_text(devanagari: str, latin: str, keywords) -> str:
    kw = " ".join(keywords) if isinstance(keywords, list) else keywords
    return f"{devanagari} | {latin} | {kw}"


def _index(memory_id: int, devanagari: str, latin: str, keywords) -> None:
    """Embed one memory. A failed embedding (quota, network) must never lose the memory itself."""
    if not VEC_OK:
        return
    try:
        vec = embed.embed([_doc_text(devanagari, latin, keywords)])[0]
        _conn().execute("INSERT OR REPLACE INTO vec_memories(rowid, embedding) VALUES(?, ?)",
                        (memory_id, sqlite_vec.serialize_float32(vec)))
        _conn().commit()
    except Exception as e:
        log("Memory", f"could not embed memory {memory_id} (keyword search still works): {str(e)[:80]}")


def backfill_vectors() -> int:
    """Embed memories that have no vector yet (older saves, or an earlier embedding failure)."""
    if not VEC_OK:
        return 0
    have = {r[0] for r in _conn().execute("SELECT rowid FROM vec_memories")}
    missing = [m for m in all_memories() if m["id"] not in have]
    for m in missing:
        _index(m["id"], m["devanagari"], m["latin"], m["keywords"])
    return len(missing)


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
        q |= tokens(t) - STOPWORDS  # 'kya', 'hai', 'क्या' would otherwise match unrelated memories
    hits = []
    for m in all_memories():
        mt = tokens(f"{m['devanagari']} {m['latin']} {m['keywords']}")
        score = sum(1.0 for w in q if any(_similar(w, x) for x in mt))
        if score:
            hits.append((score / max(len(q), 1), m))
    hits.sort(key=lambda h: -h[0])
    return hits[:limit]


_pool = ThreadPoolExecutor(max_workers=2)


def embed_async(text: str) -> Future | None:
    """Start embedding `text` now, so the vector is ready when the search needs it (None if nothing to search)."""
    if not VEC_OK or not text.strip() or not _conn().execute("SELECT 1 FROM memories LIMIT 1").fetchone():
        return None
    return _pool.submit(lambda: embed.embed([text], query=True)[0])


def search_semantic(query: str, limit: int = 5, vec: list[float] | None = None) -> list[tuple[float, dict]]:
    """Meaning-based search: (cosine similarity, memory) for memories above MIN_COSINE, best first.
    `vec` is a ready query vector (from embed_async); otherwise `query` is embedded here."""
    if not VEC_OK:
        return []
    try:
        backfill_vectors()
        qv = vec if vec is not None else embed.embed([query], query=True)[0]
        rows = _conn().execute(
            "SELECT rowid, distance FROM vec_memories WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (sqlite_vec.serialize_float32(qv), limit)).fetchall()
    except Exception as e:
        log("Memory", f"semantic search unavailable, keyword only: {str(e)[:80]}")
        return []
    by_id = {m["id"]: m for m in all_memories()}
    hits = []
    for rowid, dist in rows:
        cos = 1 - dist * dist / 2  # vectors are unit length, so L2 distance maps to cosine
        if cos >= MIN_COSINE and rowid in by_id:
            hits.append((cos, by_id[rowid]))
    return hits


def delete(memory_id: int) -> None:
    _conn().execute("DELETE FROM memories WHERE id=?", (memory_id,))
    if VEC_OK:
        _conn().execute("DELETE FROM vec_memories WHERE rowid=?", (memory_id,))
    _conn().commit()


def add_correction(wrong: str, right: str) -> None:
    """Remember 'Prisma writes <wrong> but I mean <right>' (replaces an older rule for the same word)."""
    _conn().execute("INSERT OR REPLACE INTO corrections(wrong, right, created) VALUES(?,?,?)",
                    (wrong, right, time.time()))
    _conn().commit()


def corrections(limit: int = 10) -> list[tuple[str, str]]:
    rows = _conn().execute("SELECT wrong, right FROM corrections ORDER BY created DESC LIMIT ?", (limit,))
    return list(rows.fetchall())
