"""Memory -> Prisma word boosting and find-and-replace rules. KAIRO gets better at hearing *you*.

Verified with real audio (scripts/boost_ab_auto.py, scripts/probe_substitution.py):
- Boosting the CORRECT Devanagari spelling fixes many mishearings ("मैच" -> "मैथ्स"). Boosting a misheard
  spelling does not help, so raw transcripts are never used.
- Boosting cannot beat Prisma's strong prior for some real words ("viva" -> "विवाह"). For those, KAIRO learns a
  find-and-replace rule from the memories you approve ("विवाह" -> "वायवा"). Rules work on Devanagari, whole words.
- One invalid boost word makes Prisma reject the WHOLE list, so every word is checked here.
Limits: 100 boost words, 10 rules."""
import unicodedata

from . import memory
from .words import STOPWORDS

MAX_WORDS = 100
MAX_RULES = 10
MIN_LEN = 3



def valid_word(word: str) -> bool:
    """Letters (category L*) and combining vowel signs (M*) only: no digits, spaces, punctuation."""
    return len(word) >= MIN_LEN and all(unicodedata.category(c)[0] in ("L", "M") for c in word)


def bias_words(limit: int = MAX_WORDS) -> list[str]:
    """Correct spellings only: the cleaned Devanagari text, Latin keywords, and learned 'meant' words."""
    seen: dict[str, None] = {}
    for _, right in memory.corrections():
        seen.setdefault(right)  # learned words first: they are the ones Prisma struggles with
    for m in sorted(memory.all_memories(), key=lambda m: -m["created"]):  # newest first
        for text in (m["devanagari"], m["keywords"], m["latin"]):
            for w in memory.tokens(text or ""):
                if valid_word(w) and w not in STOPWORDS:
                    seen.setdefault(w)
    return list(seen)[:limit]


def substitution_rules() -> list[dict]:
    """Learned corrections in Prisma's rule format."""
    return [{"patterns": [wrong], "replacement": right} for wrong, right in memory.corrections(MAX_RULES)]


def learn(corrections: list[dict], transcript: str) -> list[tuple[str, str]]:
    """Validate the LLM's suggested corrections against the real transcript and store the good ones."""
    heard_words = memory.tokens(transcript)
    stored = []
    for c in corrections or []:
        wrong, right = (c.get("heard") or "").strip(), (c.get("meant") or "").strip()
        if (wrong in heard_words and wrong != right and valid_word(wrong) and valid_word(right)
                and wrong not in STOPWORDS and right not in STOPWORDS):
            memory.add_correction(wrong, right)
            stored.append((wrong, right))
    return stored
