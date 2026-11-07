"""Timbre safety checks, no network: (1) the shipped phrases seed a fresh cache with zero API calls,
(2) Timbre requests never overlap, even from several threads (Timbre allows one active request).
Run: python -m tests.test_tts_cache"""
import sys
import tempfile
import threading
import time
from pathlib import Path

from echo import tts

sys.stdout.reconfigure(encoding="utf-8")
failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


# --- 1. seeding a brand-new user's cache -------------------------------------------------------------
calls = []
real_post = tts.requests.post
tts.requests.post = lambda *a, **k: calls.append(1) or (_ for _ in ()).throw(AssertionError("no API call expected"))
tts.CACHE_DIR = Path(tempfile.mkdtemp()) / "tts_cache"

check("all fixed phrases are shipped", all((tts.bundled_phrases_dir() / tts._cache_path(t, "hi-IN", 1.0).name).exists()
                                            for t in tts.PHRASES))
n = tts.seed_cache()
check(f"seeding a fresh cache copies all {len(tts.PHRASES)} phrases", n == len(tts.PHRASES), f"copied {n}")
check("seeding twice copies nothing more", tts.seed_cache() == 0)
wav = tts.synthesize(tts.PHRASES[0], "hi-IN")
check("a seeded phrase plays from cache with ZERO Timbre calls", wav[:4] == b"RIFF" and not calls, f"calls={len(calls)}")

# --- 2. requests never overlap -----------------------------------------------------------------------
active = {"now": 0, "max": 0}
guard = threading.Lock()


class FakeResponse:
    status_code = 200
    content = b"RIFF" + bytes(100)

    def raise_for_status(self):
        pass


def fake_post(*a, **k):
    with guard:
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
    time.sleep(0.15)
    with guard:
        active["now"] -= 1
    return FakeResponse()


tts.requests.post = fake_post
threads = [threading.Thread(target=tts.synthesize, args=(f"नया वाक्य {i}", "hi-IN")) for i in range(6)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check("6 simultaneous synthesize() calls never overlap at Timbre", active["max"] == 1, f"max concurrent = {active['max']}")

tts.requests.post = real_post
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
