"""Prisma real-time STT over WebSocket.

The docs describe only server-side VAD: the server emits a final `transcript`
per speech segment. There is no end-of-stream frame, so after the key is
released we stream a little silence (so VAD closes the segment), wait for the
last transcript, then close the socket.

Measured with scripts/silence_experiment.py and scripts/tail_experiment.py:
- min-silence 300 ms is ~0.4 s faster than the 500 ms default with identical text; 200 ms or less is unreliable.
- Prisma sometimes returns no transcript at all for a clear utterance (~8% of synthetic runs), so an empty
  result is retried once on a fresh connection with the buffered audio.
"""
import asyncio
import json
import queue
import threading
import time

import websockets

from . import config
from .log import log

SILENCE_TAIL_FRAMES = 40  # max ~1.3 s of silence after release (stops early once text arrives)
FINAL_WAIT_SECONDS = 1.5  # max wait for a transcript after the tail
TAIL_FRAME_SECONDS = 0.008  # the silence tail is audio-time for the VAD, so it is sent faster than real time
EXTRA_SEGMENT_GRACE = 0.2  # after the first transcript post-release, wait briefly for another segment
CONNECT_ATTEMPTS = 2
RETRY_MIN_FRAMES = 20  # ~0.6 s of audio: shorter than this and an empty result is just silence
RETRY_PACE_SECONDS = 0.016  # replay speed for the retry (2x real time)


async def _connect(headers: dict):
    last = None
    for _ in range(CONNECT_ATTEMPTS):
        try:
            return await websockets.connect(config.STT_URL, additional_headers=headers,
                                            open_timeout=20)
        except (TimeoutError, OSError) as e:
            last = e
    raise ConnectionError(f"could not reach Prisma: {last!r}")


async def _session(headers: dict, rules: list[dict] | None, audio_q: "queue.Queue[bytes | None]",
                   sent: list[bytes]) -> str:
    parts: list[str] = []
    released = False
    got_text_after_release = asyncio.Event()

    ws = await _connect(headers)
    try:
        if rules:  # find-and-replace: documented update_settings frame (header spelling differs across docs)
            await ws.send(json.dumps({"type": "update_settings",
                                      "substitution": {"enabled": True, "map": rules[:10]}}))
            log("Prisma", "learned corrections: " + ", ".join(
                f"{r['patterns'][0]}->{r['replacement']}" for r in rules[:10]))

        async def receiver():
            async for msg in ws:
                data = json.loads(msg)
                if data["type"] == "transcript" and data.get("text"):
                    parts.append(data["text"])
                    log("Prisma", f"heard {data['text']!r}  ({data.get('latency', '?')} ms)")
                    if released:
                        got_text_after_release.set()
                elif data["type"] == "error":
                    log("Prisma", f"error: {data.get('message')}")

        recv_task = asyncio.create_task(receiver())

        loop = asyncio.get_running_loop()
        while True:
            chunk = await loop.run_in_executor(None, audio_q.get)
            if chunk is None:
                break
            sent.append(chunk)
            await ws.send(chunk)
        released = True

        silence = bytes(config.FRAME_BYTES)
        for _ in range(SILENCE_TAIL_FRAMES):
            if got_text_after_release.is_set():
                break
            await ws.send(silence)
            await asyncio.sleep(TAIL_FRAME_SECONDS)

        try:
            await asyncio.wait_for(got_text_after_release.wait(), FINAL_WAIT_SECONDS)
            await asyncio.sleep(EXTRA_SEGMENT_GRACE)
        except asyncio.TimeoutError:
            pass
        recv_task.cancel()
    finally:
        await ws.close()
    return " ".join(parts).strip()


def _replay(frames: list[bytes]) -> "queue.Queue[bytes | None]":
    q: "queue.Queue[bytes | None]" = queue.Queue()

    def feed():
        for f in frames:
            q.put(f)
            time.sleep(RETRY_PACE_SECONDS)
        q.put(None)

    threading.Thread(target=feed, daemon=True).start()
    return q


async def transcribe(audio_q: "queue.Queue[bytes | None]", lang: str = "hi-IN",
                     bias_words: list[str] | None = None, bias_score: str | None = None,
                     fmt: str | None = None, rules: list[dict] | None = None,
                     min_silence_ms: int | None = None) -> str:
    """Stream 1,024-byte PCM frames from audio_q (None = key released). Returns the text."""
    headers = {
        "x-api-key-id": config.API_KEY,
        "lang_code": lang,
        "x-sample-rate": str(config.SAMPLE_RATE),
        "x-min-silence-ms": str(min_silence_ms or config.MIN_SILENCE_MS),
    }
    if fmt:
        headers["x-format"] = fmt  # "transcribe" turns on number formatting (ITN)
    if bias_words:
        headers["x-bias-list"] = json.dumps(bias_words[:100])  # ascii-escaped, as the docs require
        headers["x-bias-score"] = bias_score or config.BIAS_SCORE
        log("Prisma", f"{lang} streaming, word boosting {min(len(bias_words), 100)} words "
                      f"(score {headers['x-bias-score']})")
    else:
        log("Prisma", f"{lang} streaming, no word boosting")

    sent: list[bytes] = []
    text = await _session(headers, rules, audio_q, sent)
    if not text and len(sent) >= RETRY_MIN_FRAMES:
        log("Prisma", "returned nothing for a real utterance, retrying once")
        text = await _session(headers, rules, _replay(sent), [])
    return text
