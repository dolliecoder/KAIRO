"""Asks Prisma how many boost words it accepted (settings_updated.bias_word_count)."""
import asyncio
import json
import sys

import websockets

from echo import config

sys.stdout.reconfigure(encoding="utf-8")

TESTS = {
    "latin": ["maths", "integration", "Dolly"],
    "devanagari": ["मैथ्स", "इंटीग्रेशन", "डिफरेंशियल", "डॉली"],
    "mixed junk": ["maths", "two words", "abc123", "मैथ्स", "x.y"],
}


async def probe(words):
    headers = {"x-api-key-id": config.API_KEY, "lang_code": "hi-IN", "x-sample-rate": "16000"}
    async with websockets.connect(config.STT_URL, additional_headers=headers, open_timeout=20) as ws:
        await ws.recv()  # connected
        await ws.send(json.dumps({"type": "update_settings", "bias": {"list": words, "score": 1.0}}))
        for _ in range(3):
            data = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if data["type"] in ("settings_updated", "error"):
                return data
    return None


for name, words in TESTS.items():
    r = asyncio.run(probe(words))
    print(name, len(words), "sent ->", json.dumps(r.get("config", r), ensure_ascii=False) if r else None)
