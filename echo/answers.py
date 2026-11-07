"""Understanding a spoken yes or no.

Prisma spells the same spoken word in several ways ("haan" comes back as हाँ, हां, हा, हान, हाँजी...), so matching a
fixed list of spellings breaks for some voices and accents. Words are normalised and matched by pattern, and an answer
that is neither yes nor no is reported as "unknown" so the caller can ask again instead of guessing "no"."""
import re

YES_WORDS = {
    "haan", "han", "haa", "ha", "yes", "yeah", "yep", "yup", "ok", "okay", "kar", "karo", "kardo", "theek", "thik",
    "sahi", "bilkul", "zaroor", "jaroor", "ji", "sure",
    "कर", "करो", "करदो", "ठीक", "सही", "ओके", "ओकै", "यस", "येस", "जी", "बिल्कुल", "बिलकुल", "जरूर", "हम्म",
}
NO_WORDS = {
    "nahi", "nahin", "nai", "no", "nope", "mat", "ruko", "cancel", "stop", "rehne",
    "नहीं", "नही", "नहि", "ना", "नो", "नॉ", "मत", "रुको", "रहने", "छोड़ो", "छोड़ दो", "बंद", "कैंसल",
}
# हाँ / हां / हा / हान / हाँन... and हाँ जी; नहीं / नही / नहि
_YES_PATTERN = re.compile(r"^(हा[ंँन]*|हां?जी|हाँजी|ह[ाा]ँ?)$")
_NO_PATTERN = re.compile(r"^(नह[ीि]ं?|ना|नो|नॉ)$")
_PUNCTUATION = re.compile(r"[।॥,.?!\"'“”‘’…\-]")


def _tokens(text: str) -> list[str]:
    clean = _PUNCTUATION.sub(" ", (text or "").lower()).replace("़", "")  # drop punctuation and the nukta dot
    return clean.split()


def answer_of(text: str) -> str:
    """"yes", "no" or "unknown". A "no" word anywhere wins ("haan nahi" is no; "nahi, rehne do" is no)."""
    tokens = _tokens(text)
    if any(t in NO_WORDS or _NO_PATTERN.match(t) for t in tokens):
        return "no"
    if any(t in YES_WORDS or _YES_PATTERN.match(t) for t in tokens):
        return "yes"
    return "unknown"


def is_yes(text: str) -> bool:
    return answer_of(text) == "yes"
