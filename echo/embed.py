"""Gemini embeddings (free tier) for meaning-based memory search across Devanagari, Latin and English."""
import math

from google.genai import types

from . import llm
from .log import log

MODEL = "gemini-embedding-001"
DIM = 768  # gemini-embedding-001 supports reduced output sizes; 768 keeps the local database small


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed(texts: list[str], query: bool = False) -> list[list[float]]:
    """Unit-length vectors (so L2 distance maps to cosine similarity). Raises on API failure."""
    r = llm._client.models.embed_content(
        model=MODEL, contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT", output_dimensionality=DIM))
    log("Gemini", f"{MODEL} embedded {len(texts)} text(s)")
    return [_normalize(list(e.values)) for e in r.embeddings]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
