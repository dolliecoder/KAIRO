"""Speak test sentences with Timbre, feed the audio to Prisma, print what Prisma writes.
Lets us test number/time recognition without a microphone."""
import asyncio
import io
import queue
import sys
import time
import wave

import numpy as np

from echo import config, tts
from echo.stt import transcribe

sys.stdout.reconfigure(encoding="utf-8")

SENTENCES = [
    "aaj dopahar ek bajkar das minute par paani peena yaad dilana",
    "kal subah saade nau baje Go assignment yaad dilana",
    "aaj shaam paanch baje gym jaana yaad dilana",
]


def to_frames(wav_bytes: bytes) -> list[bytes]:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate, pcm = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    n = int(len(pcm) * config.SAMPLE_RATE / rate)  # linear resample to 16 kHz
    pcm16 = np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm).astype(np.int16).tobytes()
    pcm16 += bytes(-len(pcm16) % config.FRAME_BYTES)
    return [pcm16[i:i + config.FRAME_BYTES] for i in range(0, len(pcm16), config.FRAME_BYTES)]


def replay(frames):
    import threading
    q = queue.Queue()

    def feed():
        for f in frames:
            q.put(f)
            time.sleep(config.FRAME_SECONDS)
        q.put(None)

    threading.Thread(target=feed, daemon=True).start()
    return q


def main():
    for sentence in SENTENCES:
        frames = to_frames(tts.synthesize(sentence, "hi-en"))
        print("\nSPOKEN :", sentence)
        for fmt in (None, "transcribe"):
            text = asyncio.run(transcribe(replay(frames), "hi-IN", fmt=fmt))
            print(f"PRISMA {fmt or 'verbatim':10s}: {text}")


if __name__ == "__main__":
    main()
