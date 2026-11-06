"""Gemini wrapper (free tier). Tries each model in GEMINI_MODELS in order."""
import json
import time
from datetime import datetime, timedelta, timezone

from google import genai
from google.genai import types

from . import config

IST = timezone(timedelta(hours=5, minutes=30))
_client = genai.Client(api_key=config.GEMINI_API_KEY)


def _config(model: str, system: str, as_json: bool) -> types.GenerateContentConfig:
    kwargs = {}
    if "2.5" in model:  # only 2.5 models accept thinking_budget; others return 400
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if as_json else "text/plain",
        temperature=0.2, **kwargs)


def generate(prompt: str, system: str, as_json: bool = True):
    errors = []
    for model in config.GEMINI_MODELS:
        for attempt in range(2):
            try:
                r = _client.models.generate_content(
                    model=model, contents=prompt, config=_config(model, system, as_json))
                return json.loads(r.text) if as_json else r.text.strip()
            except Exception as e:  # 429 / 503 / bad JSON: back off, then fall to next model
                errors.append(f"{model}: {str(e)[:160]}")
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError("all Gemini models failed: " + " | ".join(errors))


INTENT_SYSTEM = """You are the intent parser for Echo, a Hinglish voice memory assistant for Indian students.
The input is a speech transcript (Hindi/Hinglish/English, usually Devanagari, may contain recognition errors).
Return ONE JSON object:
{
 "intent": "save" | "forget" | "recall" | "remind" | "other",
 "memory":   {"devanagari": str, "latin": str, "keywords": [str]},   // intent=save
 "query":    {"devanagari": str, "latin": str, "keywords": [str]},   // intent=forget or recall
 "reminder": {"task_devanagari": str, "task_latin": str, "when_iso": str},  // intent=remind
 "reply": str   // intent=other: a short friendly Hinglish reply
}
Rules:
- save: triggers like "yaad rakhna", "remember", "note kar lo". Strip the trigger; keep the fact. Write the fact in BOTH scripts.
- SCRIPTS ARE STRICT: every "devanagari" field must be written in Devanagari script (English words transliterated, e.g. "maths" -> "मैथ्स", "integration" -> "इंटीग्रेशन"), even when the input is Latin. Every "latin" field must be Latin letters only (Hinglish romanization). Never copy the same text into both.
- forget: "bhool jao", "delete", "hata do". query = what to forget.
- recall: any question about something the user told Echo before ("maths mein kya bacha hai?").
- remind: "yaad dilana", "remind me". when_iso is an ISO-8601 time WITH +05:30 offset, resolved from the current time given below. "subah"=09:00 unless a time is said, "shaam"=18:00, "raat"=21:00, "kal"=tomorrow.
- keywords: 3-8 LATIN lowercase words, with common spelling variants (e.g. maths, math, mathematics, ganit). Subjects, names, projects, topics only.
- Fill only the field for the chosen intent; omit the others.
"""


def has_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


def _transliterate(text: str, to: str) -> str:
    if to == "devanagari":
        system = "Transliterate the text, keeping words and meaning, into DEVANAGARI script (English words too)."
    else:
        system = "Transliterate the text into Latin letters only (natural Hinglish romanization)."
    return generate(text, system + ' Return JSON: {"text": str}')["text"]


def _fix_scripts(d: dict, dev_key: str, lat_key: str) -> None:
    """The model can copy one script into both fields; enforce each field's script in code."""
    if d.get(dev_key) and not has_devanagari(d[dev_key]):
        d[dev_key] = _transliterate(d.get(lat_key) or d[dev_key], "devanagari")
    if d.get(lat_key) and has_devanagari(d[lat_key]):
        d[lat_key] = _transliterate(d[lat_key], "latin")


def parse_intent(transcript: str) -> dict:
    now = datetime.now(IST).strftime("%A %Y-%m-%d %H:%M (IST, +05:30)")
    intent = generate(f"Current time: {now}\nTranscript: {transcript}", INTENT_SYSTEM)
    if intent.get("intent") == "save":
        _fix_scripts(intent["memory"], "devanagari", "latin")
    elif intent.get("intent") in ("recall", "forget"):
        _fix_scripts(intent["query"], "devanagari", "latin")
    elif intent.get("intent") == "remind":
        _fix_scripts(intent["reminder"], "task_devanagari", "task_latin")
    return intent


ANSWER_SYSTEM = """You are Echo, a warm Hinglish voice assistant. Answer the user's question using ONLY the memories given.
Reply in 1-2 short spoken sentences, natural Hinglish in Latin script (like "Maths mein integration ho gaya hai, differential equations baaki hain.").
If the memories don't contain the answer, say so briefly. Return JSON: {"reply": str}"""


def answer(question: str, memories: list[str]) -> str:
    mem = "\n".join(f"- {m}" for m in memories) or "(none)"
    return generate(f"Question: {question}\nMemories:\n{mem}", ANSWER_SYSTEM)["reply"]
