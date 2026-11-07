"""Fires parallel generate() calls through the real hedged code path and reports any failed attempt.
Free tier allows 15 requests/min/model, so keep the numbers small. Run: python -m scripts.gemini_stress"""
import sys
import threading
import time

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
PROMPT = "Current time: Saturday 2026-11-07 10:00\nTranscript: मैथ्स में क्या बचा है"
results, lock = [], threading.Lock()


def one(i):
    t0 = time.time()
    try:
        out = llm.generate(PROMPT, llm.INTENT_SYSTEM)
        res = ("ok", out.get("intent"))
    except Exception as e:
        res = ("ERROR", str(e)[:150])
    with lock:
        results.append((i, res, time.time() - t0))


for round_no in range(2):
    threads = [threading.Thread(target=one, args=(i,)) for i in range(4)]  # 4 at once, like embed + intent + reminders
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    time.sleep(35)  # let the per-minute quota recover between rounds
for i, res, took in sorted(results):
    print(f"call {i}: {res} in {took:.1f}s")
