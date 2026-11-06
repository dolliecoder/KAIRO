"""Timbre SSE streaming: time to first audio chunk vs the REST call, and is the raw PCM sane?"""
import base64
import io
import json
import sys
import time
import wave

import numpy as np
import requests

from echo import config

sys.stdout.reconfigure(encoding="utf-8")
URL = "https://api.vachana.ai/api/v1/tts/sse"
TEXTS = ["ठीक है, कल सुबह नौ बजे गो असाइनमेंट याद दिलाऊँगी।", "मैथ्स में डिफरेंशियल इक्वेशंस बाकी हैं, इंटीग्रेशन हो गया।"]
HEAD = {"X-API-Key-ID": config.API_KEY, "Content-Type": "application/json"}


def body(text, container):
    return {"text": text, "voice": config.TIMBRE_VOICE, "model": config.TIMBRE_MODEL, "language": "hi-IN", "speed": 1.0,
            "audio_config": {"sample_rate": 24000, "container": container}}


def sse(text):
    t0 = time.time()
    r = requests.post(URL, json=body(text, "raw"), headers=HEAD, stream=True, timeout=40)
    r.raise_for_status()
    first, chunks, event = None, [], None
    for line in r.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:].strip())
            if event == "chunk" and data.get("audio"):
                if first is None:
                    first = time.time() - t0
                chunks.append(base64.b64decode(data["audio"]))
            elif event == "error" or data.get("type") == "error":
                raise RuntimeError(data)
    return first, time.time() - t0, chunks


def rest(text):
    t0 = time.time()
    r = requests.post(config.TTS_URL, json=body(text, "wav"), headers=HEAD, timeout=40)
    r.raise_for_status()
    return time.time() - t0, r.content


for text in TEXTS:
    print("\nTEXT:", text)
    wall, wav = rest(text)
    with wave.open(io.BytesIO(wav)) as w:
        ref = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    print(f"  REST  total {wall:4.2f} s | {len(ref) / 24000:.2f} s of audio | rms {np.sqrt(np.mean(ref.astype(float) ** 2)):.0f}")
    for i in range(2):
        first, total, chunks = sse(text)
        pcm = np.frombuffer(b"".join(chunks), dtype=np.int16)
        print(f"  SSE#{i + 1} first chunk {first:4.2f} s, total {total:4.2f} s | {len(chunks)} chunks | "
              f"{len(pcm) / 24000:.2f} s of audio | rms {np.sqrt(np.mean(pcm.astype(float) ** 2)):.0f} | "
              f"first chunk size {len(chunks[0])} B starts {chunks[0][:4]!r}")
