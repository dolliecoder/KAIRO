"""Forces the self-healing path: meaning search is switched off and the question shares no words with the memory,
so only Gemini's query rewrite + retry can find it. Uses real Gemini, throwaway database.
Run: python -m tests.test_selfheal"""
import sys
from pathlib import Path

from echo import brain, memory, reminders

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_heal.db"
memory.DB_PATH.unlink(missing_ok=True)
reminders.JOBS_DB = memory.DB_PATH.parent / "test_heal_jobs.db"

brain.handle("याद रखना मैथ्स में इंटीग्रेशन हो गया डिफरेंशियल इक्वेशंस बाकी हैं", lambda p: True)
brain.handle("याद रखना जिम में सोमवार को लेग डे है", lambda p: True)
memory.search_semantic = lambda *a, **k: []  # simulate: embeddings unavailable / not confident

said = []
CASES = [
    ("calculus ka kya status hai?", ["डिफरेंशियल", "इंटीग्रेशन"]),          # English word, memory has Hindi-script terms
    ("workout kab hai?", ["सोमवार", "लेग"]),                               # different word for the same idea
    ("ganit mein kya baaki hai?", ["डिफरेंशियल", "इक्वेशंस", "इक्वेशन"]),   # Hindi word for maths
]
failed = 0
healed_any = False
for q, accept in CASES:
    said.clear()
    reply = brain.handle(q, lambda p: True, notify=said.append)
    healed = bool(said)
    healed_any |= healed
    ok = any(a in reply for a in accept)  # a confident first search needs no rewrite; the answer must still be right
    failed += not ok
    print(("PASS " if ok else "FAIL ") + q + f"\n       rewrite needed: {healed}\n       -> {reply}")

print(("PASS " if healed_any else "FAIL ") + "at least one question forced a rewrite-and-retry")
failed += not healed_any

memory._db.close()
memory.DB_PATH.unlink(missing_ok=True)
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
