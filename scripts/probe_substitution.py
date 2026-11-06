"""Verifies Prisma find-and-replace via update_settings: accepted? works on Devanagari? whole-word?"""
import asyncio
import json
import sys

import websockets

from echo import config, tts
from scripts.voice_probe import to_frames

sys.stdout.reconfigure(encoding="utf-8")
RULES = [{"patterns": ["विवाह"], "replacement": "वायवा"}]


async def run(sentence: str, rules):
    frames = to_frames(tts.synthesize(sentence, "hi-en"))
    headers = {"x-api-key-id": config.API_KEY, "lang_code": "hi-IN", "x-sample-rate": "16000"}
    async with websockets.connect(config.STT_URL, additional_headers=headers, open_timeout=20) as ws:
        await ws.recv()  # connected
        if rules:
            await ws.send(json.dumps({"type": "update_settings", "substitution": {"enabled": True, "map": rules}}))
            reply = json.loads(await asyncio.wait_for(ws.recv(), 10))
            print("   settings reply:", reply.get("type"), "substitution_enabled =", reply.get("config", {}).get("substitution_enabled"))
        texts = []

        async def rx():
            async for m in ws:
                d = json.loads(m)
                if d["type"] == "transcript" and d.get("text"):
                    texts.append(d["text"])

        t = asyncio.create_task(rx())
        for f in frames + [bytes(1024)] * 50:
            await ws.send(f)
            await asyncio.sleep(0.032)
        await asyncio.sleep(1.5)
        t.cancel()
    return " ".join(texts)


for s in ["kal OJT ka viva hai", "meri shaadi ka vivah kal hai"]:
    print("SPOKEN:", s)
    print("   no rules  ->", asyncio.run(run(s, None)))
    print("   with rule ->", asyncio.run(run(s, RULES)))
