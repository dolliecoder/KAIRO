"""Memory -> Prisma word boosting. Words you have told Echo are fed back into recognition,
so Echo gets better at hearing *you*.

Prisma rules (verified with scripts/probe_bias.py): single words, letters (and Devanagari vowel signs) only,
max 100. One invalid word makes Prisma reject the WHOLE list, so every word is checked here."""
import unicodedata

from . import memory

MAX_WORDS = 100
MIN_LEN = 3

STOPWORDS = {
    # Devanagari function words
    "में", "है", "हैं", "हो", "गया", "गई", "गए", "की", "का", "के", "को", "से", "पर", "और", "ये", "वो", "तो",
    "भी", "ही", "कि", "मैं", "मुझे", "मेरा", "मेरी", "मेरे", "कल", "आज", "रखो", "रखना", "करना", "करो", "बाकी",
    "नहीं", "था", "थी", "थे", "रहा", "रही", "लिए", "बहुत", "अब", "फिर", "यह", "इसे", "उसे", "हम", "आप",
    # Latin Hinglish function words
    "mein", "hai", "hain", "ho", "gaya", "gayi", "gaye", "ki", "ka", "ke", "ko", "se", "par", "aur", "ye", "wo",
    "to", "bhi", "hi", "ki", "mujhe", "mera", "meri", "mere", "kal", "aaj", "rakho", "rakhna", "karna", "karo",
    "baaki", "nahi", "tha", "thi", "the", "raha", "rahi", "liye", "bahut", "ab", "phir", "yeh", "isse", "hum",
    "aap", "the", "and", "for", "with", "that", "this", "have", "will",
}


def valid_word(word: str) -> bool:
    """Letters (category L*) and combining vowel signs (M*) only: no digits, spaces, punctuation."""
    return len(word) >= MIN_LEN and all(unicodedata.category(c)[0] in ("L", "M") for c in word)


def bias_words(limit: int = MAX_WORDS) -> list[str]:
    seen: dict[str, None] = {}
    for m in sorted(memory.all_memories(), key=lambda m: -m["created"]):  # newest first
        for text in (m["raw"], m["devanagari"], m["keywords"], m["latin"]):  # raw = Prisma's own spelling
            for w in memory.tokens(text or ""):
                if valid_word(w) and w not in STOPWORDS:
                    seen.setdefault(w)
    return list(seen)[:limit]
