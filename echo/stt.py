"""Prisma real-time STT over WebSocket.

The docs describe only server-side VAD: the server emits a final `transcript`
per speech segment. There is no end-of-stream frame, so after the key is
released we stream a little silence (so VAD closes the segment), wait for the
last transcript, then close the socket.
"""
import asyncio
import json
import queue

import websockets

from . import config
from .log import log

SILENCE_TAIL_FRAMES = 40  # max ~1.3 s of silence after release (stops early once text arrives)
FINAL_WAIT_SECONDS = 1.5  # max wait for a transcript after the tail
EXTRA_SEGMENT_GRACE = 0.4  # after the first transcript post-release, wait briefly for another segment
CONNECT_ATTEMPTS = 2


async def _connect(headers: dict):
    last = None
    for _ in range(CONNECT_ATTEMPTS):
        try:
            return await websockets.connect(config.STT_URL, additional_headers=headers,
                                            open_timeout=20)
        except (TimeoutError, OSError) as e:
            last = e
    raise ConnectionError(f"could not reach Prisma: {last!r}")


async def transcribe(audio_q: "queue.Queue[bytes | None]", lang: str = "hi-IN",
                     bias_words: list[str] | None = None, bias_score: str | None = None,
                     fmt: str | None = None, rules: list[dict] | None = None) -> str:
    """Stream 1,024-byte PCM frames from audio_q (None = key released). Returns the text."""
    headers = {
        "x-api-key-id": config.API_KEY,
        "lang_code": lang,
        "x-sample-rate": str(config.SAMPLE_RATE),
        "x-min-silence-ms": "500",
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
            await ws.send(chunk)
        released = True

        silence = bytes(config.FRAME_BYTES)
        for _ in range(SILENCE_TAIL_FRAMES):
            if got_text_after_release.is_set():
                break
            await ws.send(silence)
            await asyncio.sleep(config.FRAME_SECONDS)  # real-time cadence, no bursting

        try:
            await asyncio.wait_for(got_text_after_release.wait(), FINAL_WAIT_SECONDS)
            await asyncio.sleep(EXTRA_SEGMENT_GRACE)
        except asyncio.TimeoutError:
            pass
        recv_task.cancel()
    finally:
        await ws.close()
    return " ".join(parts).strip()
