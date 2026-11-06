"""Echo speaks as a woman, in Devanagari. Deterministic checks use a fake LLM (no network).
Run: python -m tests.test_replies   |   add --live to also check real Gemini replies."""
import re
import sys
from pathlib import Path

from echo import brain, llm, memory, reminders

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_replies.db"
memory.DB_PATH.unlink(missing_ok=True)
reminders.JOBS_DB = memory.DB_PATH.parent / "test_replies_jobs.db"
reminders.JOBS_DB.unlink(missing_ok=True)

MASCULINE = re.compile(r"(ूँगा|ऊँगा|ूंगा|ता हूँ|ता हूं|रहा हूँ|रहा हूं|गया हूँ|गया हूं|मैं गया|मैं भूल गया)")
LATIN = re.compile(r"[A-Za-z]{2,}")
failed = 0
spoken = []


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def ask(prompt):
    spoken.append(prompt)
    return True


def run(intent, text="x", confirm=ask):
    llm.parse_intent = lambda t: intent
    reply = brain.handle(text, confirm)
    spoken.append(reply)
    return reply


SAVE = {"intent": "save", "memory": {"devanagari": "कल ओजेटी का वायवा है", "latin": "kal OJT ka viva hai",
                                      "keywords": ["ojt", "viva"], "corrections": []}}
run(SAVE)
run({"intent": "save", "memory": SAVE["memory"]}, confirm=lambda p: (spoken.append(p), False)[1])
run({"intent": "recall", "query": {"devanagari": "वायवा कब है", "latin": "viva kab hai", "keywords": ["viva"]}})
run({"intent": "recall", "query": {"devanagari": "जिम", "latin": "gym", "keywords": ["gym"]}})
run({"intent": "forget", "query": {"devanagari": "वायवा", "latin": "viva", "keywords": ["viva"]}})
run({"intent": "remind", "reminder": {"task_devanagari": "पानी पीना", "task_latin": "paani peena", "day": "tomorrow",
                                      "date": "", "hour": 9, "minute": 0, "period": "am", "in_minutes": 0}},
    text="कल सुबह 9 बजे पानी पीना याद दिलाना")
run({"intent": "remind", "reminder": {"task_devanagari": "पानी पीना", "task_latin": "paani peena", "day": "",
                                      "date": "", "hour": -1, "minute": 0, "period": "", "in_minutes": 0}})
run({"intent": "other"})

print()
for line in spoken:
    print("  Echo says:", line)
print()
check("every spoken line is Devanagari (no Latin words)", not any(LATIN.search(s) for s in spoken),
      str([s for s in spoken if LATIN.search(s)]))
check("no masculine self-references", not any(MASCULINE.search(s) for s in spoken),
      str([s for s in spoken if MASCULINE.search(s)]))
check("feminine reminder confirmation 'दिलाऊँगी'", any("दिलाऊँगी" in s for s in spoken))
check("forget says feminine 'भूल गई'", any("भूल गई" in s for s in spoken))

if "--live" in sys.argv:
    print("\nLive Gemini replies:")
    for text in ["तुम कौन हो?", "थैंक यू", "तुम मेरी क्या मदद कर सकती हो?"]:
        llm.parse_intent = llm.__dict__.get("_orig_parse", llm.parse_intent)
    import importlib
    importlib.reload(llm)
    live = []
    for text in ["तुम कौन हो?", "थैंक यू", "तुम मेरी क्या मदद कर सकती हो?"]:
        reply = llm.parse_intent(text).get("reply", "")
        live.append(reply)
        print("  you:", text, "->", reply)
    live.append(llm.answer("वायवा कब है", ["कल ओजेटी का वायवा है"]))
    print("  recall ->", live[-1])
    check("live replies: Devanagari only", not any(LATIN.search(s) for s in live))
    check("live replies: no masculine self-references", not any(MASCULINE.search(s) for s in live),
          str([s for s in live if MASCULINE.search(s)]))

memory._db.close()
memory.DB_PATH.unlink(missing_ok=True)
reminders.start().shutdown()
try:
    reminders.JOBS_DB.unlink(missing_ok=True)
except PermissionError:
    pass  # Windows keeps the scheduler's SQLite file locked until exit; data/ is git-ignored
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
