"""Gemini wrapper (free tier). Tries each model in GEMINI_MODELS in order."""
import json
import time
from datetime import datetime, timedelta, timezone

from google import genai
from google.genai import types

from . import config
from .log import log

IST = timezone(timedelta(hours=5, minutes=30))
_client_obj = None


def client() -> genai.Client:
    """Created on first use, not at import: importing KAIRO must work before the user has entered a key."""
    global _client_obj
    if _client_obj is None:
        _client_obj = genai.Client(api_key=config.GEMINI_API_KEY,
                                   http_options=types.HttpOptions(timeout=20000))  # ms: never hang the voice loop
    return _client_obj


def _config(model: str, system: str, as_json: bool) -> types.GenerateContentConfig:
    kwargs = {}
    if "2.5" in model:  # only 2.5 models accept thinking_budget; others return 400
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if as_json else "text/plain",
        temperature=0.2, **kwargs)


def _parse_json(text: str):
    """First JSON object in the text; tolerates code fences and trailing junk some models add."""
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    obj, _ = json.JSONDecoder().raw_decode(text[text.index("{"):])
    return obj


_cooldown: dict[str, float] = {}  # model -> time before which it is skipped (quota / not found)
COOLDOWN_SECONDS = 600


def generate(prompt: str, system: str, as_json: bool = True):
    errors = []
    now = time.time()
    models = [m for m in config.GEMINI_MODELS if _cooldown.get(m, 0) <= now] or config.GEMINI_MODELS
    for model in models:
        for attempt in range(2):
            started = time.time()
            try:
                r = client().models.generate_content(
                    model=model, contents=prompt, config=_config(model, system, as_json))
                out = _parse_json(r.text) if as_json else r.text.strip()
                log("Gemini", f"{model} replied  ({int((time.time() - started) * 1000)} ms)")
                return out
            except Exception as e:  # bad JSON / 5xx: retry once; quota (429) or missing model: skip it for a while
                msg = str(e)
                errors.append(f"{model}: {msg[:120]}")
                log("Gemini", f"{model} failed ({msg[:60]}), trying next")
                if "RESOURCE_EXHAUSTED" in msg or "NOT_FOUND" in msg:
                    _cooldown[model] = time.time() + COOLDOWN_SECONDS
                    break
                time.sleep(0.5)
    raise RuntimeError("all Gemini models failed: " + " | ".join(errors))


INTENT_SYSTEM = """You are the intent parser for KAIRO, a Hinglish voice memory assistant for Indian students.
The input is a speech transcript (Hindi/Hinglish/English, usually Devanagari, may contain recognition errors).
Return ONE JSON object:
{
 "intent": "save" | "forget" | "recall" | "remind" | "other",
 "memory":   {"devanagari": str, "latin": str, "keywords": [str], "corrections": [{"heard": str, "meant": str}]},   // intent=save
 "query":    {"devanagari": str, "latin": str, "keywords": [str]},   // intent=forget or recall
 "reminder": {"task_devanagari": str, "task_latin": str, "day": "today"|"tomorrow"|"day_after"|"", "date": "YYYY-MM-DD"|"", "hour": int,
              "minute": int, "period": "am"|"pm"|"", "in_minutes": int},  // intent=remind
 "reply": str   // intent=other: a short friendly reply (rules below)
}
Rules:
- save: triggers like "yaad rakhna" / "याद रखना", "remember", "note kar lo". These ALWAYS mean save, even if the sentence mentions a day or a time ("याद रखना कल जिम जाना है" is a save, not a reminder). Strip the trigger; keep the fact. Write the fact in BOTH scripts.
- corrections (save only): words in the transcript that speech recognition clearly got wrong, as single Devanagari words exactly as they appear in the transcript ("heard") and the correct Devanagari spelling ("meant"). Only subjects, names, technical or project terms (e.g. heard "वैवाह", meant "वायवा" for "viva"). Never grammar words, never rewording. Usually empty [].
- SCRIPTS ARE STRICT: every "devanagari" field must be written in Devanagari script (English words transliterated, e.g. "maths" -> "मैथ्स", "integration" -> "इंटीग्रेशन"), even when the input is Latin. Every "latin" field must be Latin letters only (Hinglish romanization). Never copy the same text into both.
- forget: "bhool jao", "delete", "hata do". query = what to forget.
- recall: any question about something the user told KAIRO before ("maths mein kya bacha hai?").
- remind: ONLY when the user asks to be reminded or alarmed: "yaad dilana" / "याद दिलाना", "remind me", "alarm". Report ONLY what the user said; do not compute the final time (code does that).
  day: "today" (aaj), "tomorrow" (kal), "day_after" (parso), or "" if no day was said.
  date: ONLY if a weekday or calendar date was said ("friday", "somvar", "15 november"): the next such date as YYYY-MM-DD, computed from the current date/weekday given below; else "".
  hour/minute: the clock time as spoken ("1:10", "01:10" -> hour 1, minute 10; "saade nau" -> 9:30; "sawa do" -> 2:15; "paune teen" -> 2:45). hour=-1 if no clock time was said.
  period: "am" or "pm" ONLY if a day-part word or am/pm was said: subah=am, dopahar=pm, shaam=pm, raat=pm for hours 6-11 but am for 12-4 ("raat 1:10" = am). Otherwise "". Never guess a period.
  in_minutes: for "5 minute baad" / "aadhe ghante mein" (30) / "ek ghante baad" (60); else 0.
  task_devanagari: the thing to be reminded, with obvious speech-recognition errors fixed, short noun phrase (e.g. "पनी पीने का" -> "पानी पीना"). task_latin: its correct Hinglish romanization (e.g. "paani peena").
- keywords: 3-8 LATIN lowercase words, with common spelling variants (e.g. maths, math, mathematics, ganit). Subjects, names, projects, topics only.
- reply (intent=other): 1-2 short spoken sentences in DEVANAGARI script only. Your name is KAIRO; write it as कैरो. You are a woman: always use FEMININE forms for yourself ("मैं याद रखूँगी", "मैं बताती हूँ"), never masculine ("रखूँगा"). Never assume the user's gender: address them politely with "आप" and avoid gendered verb endings for them.
- Fill only the field for the chosen intent; omit the others.
"""


# KAIRO is a woman, but the user's gender is unknown: forms aimed at the user must not be feminine.
# Prompts alone are not reliable for this, so it is enforced here ("सकती हूँ" about herself is left alone).
_USER_FEMININE = (("सकती हैं", "सकते हैं"), ("सकती हो", "सकते हो"), ("चाहती हैं", "चाहते हैं"),
                  ("चाहती हो", "चाहते हो"), ("करती हैं", "करते हैं"), ("करती हो", "करते हो"))


def neutral_user(text: str) -> str:
    for fem, neutral in _USER_FEMININE:
        text = text.replace(fem, neutral)
    return text


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
    log("Gemini", f"intent = {intent.get('intent')}")
    if isinstance(intent.get("reply"), str):
        intent["reply"] = neutral_user(intent["reply"])
    if intent.get("intent") == "save":
        _fix_scripts(intent["memory"], "devanagari", "latin")
    elif intent.get("intent") in ("recall", "forget"):
        _fix_scripts(intent["query"], "devanagari", "latin")
    elif intent.get("intent") == "remind":
        _fix_scripts(intent["reminder"], "task_devanagari", "task_latin")
    return intent


ANSWER_SYSTEM = """You are KAIRO (written कैरो in Devanagari), a warm assistant with a FEMALE voice. Answer the user's question using ONLY the memories given.
Write the reply in DEVANAGARI script only (English terms transliterated, e.g. वायवा, इंटीग्रेशन), 1-2 short sentences of natural spoken Hindi.
Answer directly and briefly, like "कल ओजेटी का वायवा है।" with no filler such as "मैं आपको बताती हूँ".
If you refer to yourself you are a woman: use FEMININE forms ("याद रखूँगी"), never masculine ("रखूँगा"). Never assume the user's gender: avoid gendered verb endings for the user.
The memories were found by a search that works across scripts and synonyms, so the question may use different words than the memory (e.g. "पदार्थ विज्ञान" = physics, "calculus" = integration/differential equations, "workout" = gym). If a memory is plausibly about the same topic, answer from it.
Only if no memory is about the topic, say briefly that you don't remember it. Return JSON: {"reply": str}"""


def answer(question: str, memories: list[str]) -> str:
    mem = "\n".join(f"- {m}" for m in memories) or "(none)"
    return neutral_user(generate(f"Question: {question}\nMemories:\n{mem}", ANSWER_SYSTEM)["reply"])


REWRITE_SYSTEM = """A keyword search over the user's saved notes (Hinglish, both Devanagari and Latin) found no confident match.
Produce alternative search words that could appear in the note that answers the question: synonyms, narrower topics
under a broad word (calculus -> integration, differentiation, differential equations, maths), broader topics, the
English or Hindi equivalent, and BOTH scripts (Latin and Devanagari) for each idea. Single words only, 10-16 words.
If a list of already-tried words is given, do not repeat them and go broader or more different.
Return JSON: {"terms": [str]}"""


def rewrite_query(question: str, tried: list[str]) -> list[str]:
    out = generate(f"Question: {question}\nAlready tried: {', '.join(tried)}", REWRITE_SYSTEM)
    terms = out.get("terms", [])
    return [t for t in terms if isinstance(t, str) and t.strip()]
