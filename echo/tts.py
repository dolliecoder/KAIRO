"""Timbre text-to-speech: text in, WAV bytes out, plus playback.
All playback goes through audio_lock: sd.play() is global, so two sounds at once cancel each other."""
import hashlib
import io
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
    for attempt in range(4):
        r = requests.post(config.TTS_URL, json=body, headers=headers, timeout=30)
        if r.status_code == 429:
            log("Timbre", "rate limited (429), backing off")
            time.sleep(1.5 * (attempt + 1))
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


# Fixed phrases Echo says often; synthesized once at startup so confirmations play instantly.
PHRASES = [
    "ठीक है, याद रख लिया।", "ठीक है, सेव नहीं किया।", "भूल गई।", "ठीक है, रहने दिया।",
    "ठीक है, रिमाइंडर नहीं लगाया।", "सुनाई नहीं दिया, फिर से बोलो।", "सुनाई नहीं दिया, फिर से बोलो, हाँ या नहीं?",
    "थोड़ा रुको, दूसरे तरीके से ढूँढ रही हूँ।", "मुझे इसके बारे में कुछ याद नहीं है।", "हाँ या नहीं?",
    "समझ नहीं आया, फिर से बोलो।", "कुछ गड़बड़ हो गई, फिर से कोशिश करो।",
]


def prewarm(language: str = "hi-IN") -> None:
    """Fill the cache for PHRASES in the background; stops quietly on any error (rate limit, offline)."""
    def work():
        for text in PHRASES:
            if _cache_path(text, language, 1.0).exists():
                continue
            try:
                synthesize(text, language)
                time.sleep(0.4)  # stay well under the ~5 rapid calls that trigger HTTP 429
            except Exception as e:
                log("Timbre", f"prewarm stopped: {str(e)[:80]}")
                return
    threading.Thread(target=work, daemon=True).start()
