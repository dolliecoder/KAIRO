"""Timbre text-to-speech: text in, WAV bytes out, plus playback.
All playback goes through audio_lock: sd.play() is global, so two sounds at once cancel each other."""
import io
import threading
import time
import wave

import numpy as np
import requests
import sounddevice as sd

from . import config
from .log import log

audio_lock = threading.RLock()


def synthesize(text: str, language: str = "hi-en", speed: float = 1.0) -> bytes:
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
