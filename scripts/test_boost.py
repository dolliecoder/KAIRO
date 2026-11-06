"""A/B test of word boosting: record ONE utterance, then transcribe the same audio
without and with boost words. Usage:  python -m scripts.test_boost "maths" "integration" ...
(Words default to the ones derived from your saved memories.)"""
import asyncio
import queue
import sys
import threading
import time

from echo import boost, config
from echo.audio import Recorder
from echo.stt import transcribe

sys.stdout.reconfigure(encoding="utf-8")
SECONDS = 6
words = sys.argv[1:] or boost.bias_words()
print("boost words:", words)

input(f"Press Enter, then speak for {SECONDS} seconds...")
rec = Recorder()
rec.start()
time.sleep(SECONDS)
rec.stop()
frames = []
while (f := rec.q.get()) is not None:
    frames.append(f)


def replay() -> "queue.Queue[bytes | None]":
    q: "queue.Queue[bytes | None]" = queue.Queue()

    def feed():
        for f in frames:
            q.put(f)
            time.sleep(config.FRAME_SECONDS)  # real-time pacing; Prisma wants no bursts
        q.put(None)

    threading.Thread(target=feed, daemon=True).start()
    return q


for label, bias, score in (("no boost   ", None, None), ("boost 1.0  ", words, "1.0"), ("boost 2.0  ", words, "2.0")):
    print(label, "->", repr(asyncio.run(transcribe(replay(), "hi-IN", bias_words=bias, bias_score=score))))
