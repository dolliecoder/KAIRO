"""Hybrid, self-healing recall.
1. Keyword search (both scripts) and meaning search (sqlite-vec + Gemini embeddings) run together.
2. If neither is confident, Gemini rewrites the query (synonyms, broader/narrower topics, the other script)
   and KAIRO retries. Adapted from the self-healing retrieval in ragx."""
from concurrent.futures import Future
from typing import Callable

from . import llm, memory
from .log import log

CONFIDENT = 0.5  # keyword score: share of the query's content words that a memory matches
MAX_REWRITES = 2


def _merge(keyword_hits, semantic_hits) -> list[tuple[float, dict]]:
    """Best score per memory (keyword share and cosine similarity are both 0..1), best first."""
    best: dict[int, tuple[float, dict]] = {}
    for score, m in [*keyword_hits, *semantic_hits]:
        if m["id"] not in best or score > best[m["id"]][0]:
            best[m["id"]] = (score, m)
    return sorted(best.values(), key=lambda h: -h[0])


def _confident(keyword_hits, semantic_hits) -> bool:
    return bool(semantic_hits) or (bool(keyword_hits) and keyword_hits[0][0] >= CONFIDENT)


def _early_semantic(early: Future | None):
    """Meaning search with the vector that was computed in parallel with Gemini's intent call."""
    try:
        vec = early.result(timeout=10) if early else None
    except Exception:
        return None
    return memory.search_semantic("", vec=vec) if vec is not None else None


def retrieve(question: str, terms: list[str], notify: Callable[[str], None] | None = None,
             early: Future | None = None) -> list[tuple[float, dict]]:
    kw = memory.search(terms)
    sem = _early_semantic(early)
    if not sem:  # not found with the raw-transcript vector: search again with the cleaned-up question
        sem = memory.search_semantic(question)
    if _confident(kw, sem):
        log("Memory", f"keyword {len(kw)} + meaning {len(sem)} match(es)")
        return _merge(kw, sem)

    log("Echo", "low confidence - rewriting the query and retrying")
    if notify:
        notify("थोड़ा रुको, दूसरे तरीके से ढूँढ रही हूँ।")
    tried = list(terms)
    for attempt in range(1, MAX_REWRITES + 1):
        try:
            new_terms = llm.rewrite_query(question, tried)
        except Exception as e:  # a failed rewrite must not break recall: fall back to the first result
            log("Echo", f"query rewrite failed: {e}")
            break
        log("Echo", f"rewrite {attempt}: {', '.join(new_terms)}")
        kw2, sem2 = memory.search(new_terms), memory.search_semantic(" ".join(new_terms))
        if kw2 or sem2:
            log("Memory", f"self-healed after rewrite {attempt}: keyword {len(kw2)} + meaning {len(sem2)}")
            return _merge(kw2, sem2)
        tried += new_terms
    return _merge(kw, sem)
