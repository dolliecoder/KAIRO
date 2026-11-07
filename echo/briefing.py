"""Today's plan: your reminders for today plus your recent notes, spoken as a short briefing.
On demand ("aaj ka plan batao") or every day at a time you choose ("roz subah 8 baje plan sunana")."""
from datetime import datetime

from . import llm, memory, reminders
from .log import log
from .reminders import IST, clock_hi

RECENT_DAYS = 3  # notes saved in the last 3 days count as "recent"
MAX_NOTES = 3


def todays_reminders(now: datetime) -> list[tuple[datetime, str]]:
    """One-time reminders that are due today, earliest first."""
    return [(w, task) for w, task in reminders.pending_detail() if w.astimezone(IST).date() == now.date()]


def recent_notes(now: datetime, days: int = RECENT_DAYS, limit: int = MAX_NOTES) -> list[str]:
    cutoff = now.timestamp() - days * 86400
    fresh = sorted((m for m in memory.all_memories() if m["created"] >= cutoff), key=lambda m: -m["created"])
    return [m["devanagari"] for m in fresh[:limit]]


def greeting(now: datetime) -> str:
    h = now.hour
    return "सुप्रभात!" if 4 <= h < 12 else "नमस्ते!" if h < 16 or h >= 20 else "शुभ संध्या!"


def fallback(now: datetime, items: list[tuple[datetime, str]], notes: list[str]) -> str:
    """The plan without Gemini, so a quota hiccup never silences the daily briefing."""
    if items:
        listed = "; ".join(f"{clock_hi(w.hour, w.minute)} {task}" for w, task in items)
        text = f"{greeting(now)} आज के रिमाइंडर हैं: {listed}।"
    else:
        text = f"{greeting(now)} आज कोई रिमाइंडर नहीं है, दिन आपका है।"
    if notes:
        text += f" हाल का नोट: {notes[0]}।"
    return text


def compose(now: datetime, items: list[tuple[datetime, str]], notes: list[str]) -> str:
    lines = [f"{clock_hi(w.hour, w.minute)} - {task}" for w, task in items]
    try:
        text = llm.make_briefing(now.strftime("%A %d %B %Y, %H:%M IST"), lines, notes)
        if text:
            return text
    except Exception as e:
        log("Gemini", f"could not write the plan, using the plain version: {str(e)[:100]}")
    return fallback(now, items, notes)


def compose_now() -> str:
    now = datetime.now(IST)
    return compose(now, todays_reminders(now), recent_notes(now))
