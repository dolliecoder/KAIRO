"""Brain wiring for the quiz and the day's plan, with scripted voice answers and a fake Gemini (no network).
Run: python -m tests.test_brain_new"""
import sys
import tempfile
from pathlib import Path

from echo import brain, briefing, llm, memory, quiz, reminders

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path(tempfile.mkdtemp(prefix="kairo_brain_"))
memory.DB_PATH = HOME / "brain.db"
reminders.JOBS_DB = HOME / "jobs.db"
memory._index = lambda *a, **k: None
memory.search_semantic = lambda *a, **k: []
memory.embed_async = lambda *a, **k: None
reminders._scheduler = None

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def route(intent):
    llm.parse_intent = lambda transcript: intent


yes, no = (lambda p: True), (lambda p: False)

# --- quiz ---
route({"intent": "quiz", "quiz": {"topic": ""}})
check("quiz without a voice channel explains itself", "आवाज़" in brain.handle("quiz karo", yes))

memory.save("मैथ्स में इंटीग्रेशन हो गया, डिफरेंशियल इक्वेशंस बाकी हैं", "maths integration done", ["maths"])
llm.make_quiz = lambda notes: [{"question": "मैथ्स में कौन सा टॉपिक बाकी है?", "answer": "डिफरेंशियल इक्वेशंस"}]
llm.judge_answer = lambda q, a, heard: {"verdict": "correct" if "डिफरेंशियल" in heard else "wrong", "feedback": "बहुत बढ़िया!"}
asked, said = [], []
reply = brain.handle("maths mein quiz karo", yes, notify=said.append, ask=lambda p: (asked.append(p), "डिफरेंशियल इक्वेशंस")[1])
check("quiz through the brain: question asked, answered, scored", len(asked) == 1 and reply == "शाबाश! एक में से एक सही।", f"{asked} {reply}")
check("quiz through the brain: feedback is spoken via notify", "बहुत बढ़िया!" in said, str(said))

# --- today's plan, on demand ---
route({"intent": "briefing", "briefing": {"action": "now", "hour": 8, "minute": 0}})
briefing.compose_now = lambda: "सुप्रभात! आज का दिन खाली है।"
check("'aaj ka plan' speaks the composed plan", brain.handle("aaj ka plan batao", yes) == "सुप्रभात! आज का दिन खाली है।")

# --- the daily plan: on, change, off ---
route({"intent": "briefing", "briefing": {"action": "daily_on", "hour": 8, "minute": 0}})
asks = []
reply = brain.handle("roz subah 8 baje plan sunana", lambda p: (asks.append(p), True)[1])
check("daily plan: asks to confirm with the time in words", len(asks) == 1 and "सुबह आठ बजे" in asks[0], str(asks))
check("daily plan: confirmed -> scheduled for 8:00", reminders.daily_briefing_time() == (8, 0) and "सुबह आठ बजे" in reply, f"{reminders.daily_briefing_time()} {reply}")

route({"intent": "briefing", "briefing": {"action": "daily_on", "hour": 18, "minute": 30}})
brain.handle("roz shaam saade chhe baje plan sunana", yes)
check("daily plan: a new time replaces the old one", reminders.daily_briefing_time() == (18, 30), str(reminders.daily_briefing_time()))

route({"intent": "briefing", "briefing": {"action": "daily_on", "hour": 7, "minute": 0}})
reply = brain.handle("roz subah 7 baje plan sunana", no)
check("daily plan: declined -> nothing changes", reminders.daily_briefing_time() == (18, 30) and "नहीं लगाया" in reply, reply)

route({"intent": "briefing", "briefing": {"action": "daily_on", "hour": 99, "minute": 0}})
asks.clear()
brain.handle("roz plan", lambda p: (asks.append(p), False)[1])
check("an impossible hour falls back to 8:00 instead of crashing", "सुबह आठ बजे" in asks[0], str(asks))

route({"intent": "briefing", "briefing": {"action": "daily_off", "hour": 0, "minute": 0}})
check("'plan band karo' cancels it", "बंद कर दिया" in brain.handle("plan band karo", yes) and reminders.daily_briefing_time() is None)
check("...and says so when it was not on", "चालू ही नहीं" in brain.handle("plan band karo", yes))

# --- the older features still route as before ---
route({"intent": "other", "reply": "नमस्ते!"})
check("other still works", brain.handle("hello", yes) == "नमस्ते!")

reminders.start().shutdown()
memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
