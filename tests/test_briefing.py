"""Today's plan and the daily schedule. Deterministic checks use a throwaway database and job store (no network);
add --live to also have real Gemini write a plan. Run: python -m tests.test_briefing [--live]"""
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from echo import briefing, llm, memory, reminders

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path(tempfile.mkdtemp(prefix="kairo_brief_"))
memory.DB_PATH = HOME / "brief.db"
reminders.JOBS_DB = HOME / "jobs.db"
memory._index = lambda *a, **k: None  # offline

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


now = datetime(2026, 11, 9, 8, 0, tzinfo=reminders.IST)

# --- the plain (no-Gemini) plan ---
text = briefing.fallback(now, [], [])
check("empty day: greets and says the day is free", "सुप्रभात" in text and "कोई रिमाइंडर नहीं" in text, text)
items = [(now.replace(hour=9), "गो असाइनमेंट जमा करना"), (now.replace(hour=18, minute=30), "जिम जाना")]
text = briefing.fallback(now, items, ["कल ओजेटी का वायवा है"])
check("with reminders: lists them in order with spoken times", text.index("गो असाइनमेंट") < text.index("जिम") and "सुबह नौ बजे" in text and "शाम छह बजकर तीस मिनट पर" in text, text)
check("with a recent note: mentions it", "वायवा" in text, text)
check("greeting changes with the time of day", briefing.greeting(now.replace(hour=7)) == "सुप्रभात!" and briefing.greeting(now.replace(hour=17)) == "शुभ संध्या!")

# --- Gemini failing must never silence the plan ---
def boom(*a, **k):
    raise RuntimeError("quota")


real_make = llm.make_briefing
llm.make_briefing = boom
check("Gemini down: falls back to the plain plan", "सुप्रभात" in briefing.compose(now, [], []))
llm.make_briefing = lambda *a, **k: ""
check("Gemini returns nothing: falls back to the plain plan", "सुप्रभात" in briefing.compose(now, [], []))
llm.make_briefing = real_make

# --- notes: only recent ones ---
memory.save("आज की बात", "aaj ki baat", ["aaj"])
memory.save("पुरानी बात", "purani baat", ["purani"])
db = sqlite3.connect(memory.DB_PATH)
db.execute("UPDATE memories SET created = ? WHERE latin = 'purani baat'", (time.time() - 10 * 86400,))
db.commit()
db.close()
memory._db = None
got = briefing.recent_notes(datetime.now(reminders.IST))
check("recent notes: today's included, 10-day-old excluded", got == ["आज की बात"], str(got))

# --- scheduling (real APScheduler, throwaway job store) ---
reminders._scheduler = None
check("no daily plan set at first", reminders.daily_briefing_time() is None)
reminders.set_daily_briefing(8, 0)
check("daily plan at 8:00 is stored", reminders.daily_briefing_time() == (8, 0), str(reminders.daily_briefing_time()))
reminders.set_daily_briefing(18, 30)
check("setting a new time replaces the old one (one job only)",
      reminders.daily_briefing_time() == (18, 30) and sum(j.id == reminders.BRIEFING_JOB_ID for j in reminders.start().get_jobs()) == 1)
job = reminders.start().get_job(reminders.BRIEFING_JOB_ID)
check("it repeats daily and its next run is in the future", job.next_run_time > datetime.now(reminders.IST), str(job.next_run_time))
check("it tolerates a late start of up to an hour, not a whole day", job.misfire_grace_time == 3600, str(job.misfire_grace_time))

when = datetime.now(reminders.IST) + timedelta(hours=2)
reminders.schedule("paani peena", "पानी पीना", when)
check("the daily plan is NOT listed as a one-time reminder", [t for _, t in reminders.pending()] == ["paani peena"], str(reminders.pending()))
check("pending_detail returns the Devanagari task", [t for _, t in reminders.pending_detail()] == ["पानी पीना"], str(reminders.pending_detail()))
check("todays_reminders picks only today's", [t for _, t in briefing.todays_reminders(when)] == ["पानी पीना"])
check("...and none for another day", briefing.todays_reminders(when + timedelta(days=3)) == [])
check("cancel removes the daily plan", reminders.cancel_daily_briefing() is True and reminders.daily_briefing_time() is None)
check("cancelling again says it was not set", reminders.cancel_daily_briefing() is False)
check("the one-time reminder is untouched by that", len(reminders.pending()) == 1)

# --- live Gemini (optional) ---
if "--live" in sys.argv:
    print("\nlive Gemini:")
    from echo.llm import has_devanagari
    text = llm.make_briefing("Monday 09 November 2026, 08:00 IST", ["सुबह नौ बजे - गो असाइनमेंट जमा करना", "शाम छह बजकर तीस मिनट पर - जिम जाना"],
                             ["कल ओजेटी का वायवा है"])
    print("   ", text)
    check("live: Devanagari, mentions both reminders", has_devanagari(text) and "असाइनमेंट" in text and "जिम" in text, text)
    check("live: short enough to listen to (under 400 characters)", 0 < len(text) < 400, str(len(text)))
    check("live: never feminine toward the user", "सकती हैं" not in text and "चाहती हैं" not in text, text)
    empty = llm.make_briefing("Monday 09 November 2026, 08:00 IST", [], [])
    check("live: an empty day is described as free, nothing invented", has_devanagari(empty) and len(empty) < 300, empty)

reminders.start().shutdown()
memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
