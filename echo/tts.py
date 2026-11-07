"""Timbre text-to-speech: text in, WAV bytes out, plus playback.
All playback goes through audio_lock: sd.play() is global, so two sounds at once cancel each other."""
import hashlib
import io
import shutil
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd

from . import config
from .log import log
from .paths import DATA_DIR

audio_lock = threading.RLock()
_timbre_lock = threading.Lock()  # Timbre allows one active request: never let KAIRO collide with itself
CACHE_DIR = DATA_DIR / "tts_cache"


def _cache_path(text: str, language: str, speed: float) -> Path:
    key = f"{config.TIMBRE_MODEL}|{config.TIMBRE_VOICE}|{language}|{speed}|{text}"
    return CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".wav")


def synthesize(text: str, language: str = "hi-en", speed: float = 1.0) -> bytes:
    """Timbre audio for `text`. Repeated phrases come from a disk cache (keyed by model, voice, language, text)."""
    path = _cache_path(text, language, speed)
    if path.exists():
        log("Timbre", f"cached audio for {len(text)} chars (0 ms)")
        return path.read_bytes()
    wav = _synthesize(text, language, speed)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(wav)
    return wav


def _synthesize(text: str, language: str, speed: float) -> bytes:
    body = {
        "text": text,
        "voice": config.TIMBRE_VOICE,
        "model": config.TIMBRE_MODEL,
        "language": language,
        "speed": speed,
        # wav only: mp3 + bitrate/sample_rate is a known HTTP 500
        "audio_config": {"sample_rate": 24000, "container": "wav"},
    }
    headers = {"X-API-Key-ID": config.API_KEY, "Content-Type": "application/json"}
    started = time.time()
    with _timbre_lock:
        for attempt in range(4):
            r = requests.post(config.TTS_URL, json=body, headers=headers, timeout=30)
            if r.status_code == 429:
                log("Timbre", "rate limited (429), backing off")
                time.sleep(1.0 * (attempt + 1))
                continue
            r.raise_for_status()
            log("Timbre", f"{config.TIMBRE_MODEL} voice {config.TIMBRE_VOICE} ({language}) "
                          f"spoke {len(text)} chars  ({int((time.time() - started) * 1000)} ms)")
            return r.content
    raise RuntimeError("Timbre rate-limited (429) after retries")


def play_pcm(pcm: np.ndarray, rate: int) -> None:
    with audio_lock:
        sd.play(pcm, rate)
        sd.wait()


def play(wav_bytes: bytes) -> None:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    play_pcm(pcm, rate)


def speak(text: str, language: str = "hi-en") -> None:
    wav = synthesize(text, language)  # network call happens outside the lock
    play(wav)


# Fixed phrases KAIRO says often; synthesized once at startup so confirmations play instantly.
PHRASES = [
    "ठीक है, याद रख लिया।", "ठीक है, सेव नहीं किया।", "भूल गई।", "ठीक है, रहने दिया।",
    "ठीक है, रिमाइंडर नहीं लगाया।", "सुनाई नहीं दिया, फिर से बोलो।", "सुनाई नहीं दिया, फिर से बोलो, हाँ या नहीं?",
    "थोड़ा रुको, दूसरे तरीके से ढूँढ रही हूँ।", "मुझे इसके बारे में कुछ याद नहीं है।", "हाँ या नहीं?",
    "समझ नहीं आया, फिर से बोलो।", "कुछ गड़बड़ हो गई, फिर से कोशिश करो।",
    "ठीक है, क्विज़ शुरू करते हैं।", "अभी मेरे पास कोई नोट्स नहीं हैं, पहले कुछ याद रखवाओ।",
    "ठीक है, रोज़ का प्लान बंद कर दिया।",
]


def bundled_phrases_dir() -> Path:
    """Phrase audio generated at build time (scripts/make_phrase_cache.py) and shipped inside the app."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "phrases"
    return Path(__file__).resolve().parent.parent / "assets" / "phrases"


def seed_cache(language: str = "hi-IN") -> int:
    """Copy the shipped phrase audio into the user's cache, so a new install never has to synthesize them
    (and never makes a burst of Timbre calls on first launch). Returns how many files were copied."""
    src, copied = bundled_phrases_dir(), 0
    if not src.is_dir():
        return 0
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for text in PHRASES:
        dest = _cache_path(text, language, 1.0)
        shipped = src / dest.name  # same file name = same model, voice, language, speed and text
        if not dest.exists() and shipped.exists():
            shutil.copyfile(shipped, dest)
            copied += 1
    return copied


def prewarm(language: str = "hi-IN") -> None:
    """Seed the cache from the shipped phrases; anything still missing (e.g. a different voice) is
    synthesized in the background. Stops quietly on any error (rate limit, offline)."""
    seed_cache(language)

    def work():
        for text in PHRASES:
            if _cache_path(text, language, 1.0).exists():
                continue
            try:
                synthesize(text, language)
            except Exception as e:
                log("Timbre", f"prewarm stopped: {str(e)[:80]}")
                return
    threading.Thread(target=work, daemon=True).start()
