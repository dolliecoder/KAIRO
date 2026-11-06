"""Spoken reminders. APScheduler with a persistent SQLite job store, so reminders
survive restarts; ones missed while Echo was closed are spoken on the next start."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

IST = ZoneInfo("Asia/Kolkata")
JOBS_DB = Path(__file__).resolve().parent.parent / "data" / "jobs.db"
MISSED_GRACE_SECONDS = 24 * 3600

_scheduler: BackgroundScheduler | None = None


def fire(task_latin: str, task_devanagari: str = "") -> None:
    """Job target. Must be a top-level function so the job store can pickle a reference to it."""
    from . import sounds, tts  # lazy: keeps the job store import cheap

    print(f"Reminder: {task_latin}")
    try:
        wav = tts.synthesize(f"Yaad dilana tha: {task_latin}. Dhyan dena, {task_latin}.")
    except Exception as e:
        print(f"[Timbre unavailable] {e}")
        wav = None
    with tts.audio_lock:  # the whole alarm plays uninterrupted
        sounds.chime()
        if wav:
            tts.play(wav)


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        JOBS_DB.parent.mkdir(exist_ok=True)
        _scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{JOBS_DB}")},
            timezone=IST,
            job_defaults={"misfire_grace_time": MISSED_GRACE_SECONDS, "coalesce": True},
        )
        _scheduler.start()
    return _scheduler


def parse_when(when_iso: str) -> datetime | None:
    """The LLM's ISO string -> aware datetime in IST, or None if unusable / in the past."""
    try:
        when = datetime.fromisoformat(when_iso)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=IST)
    when = when.astimezone(IST)
    return when if when > datetime.now(IST) else None


def schedule(task_latin: str, task_devanagari: str, when: datetime) -> str:
    job = start().add_job(fire, "date", run_date=when, args=[task_latin, task_devanagari])
    return job.id


def pending() -> list[tuple[datetime, str]]:
    return sorted((j.next_run_time, j.args[0]) for j in start().get_jobs() if j.next_run_time)


def describe(when: datetime) -> str:
    """Spoken-style time: 'kal subah 9:00 baje', 'aaj shaam 6:30 baje', '25 October ko raat 9:00 baje'."""
    today = datetime.now(IST).date()
    days = (when.date() - today).days
    day = {0: "aaj", 1: "kal", 2: "parso"}.get(days, f"{when.day} {when.strftime('%B')} ko")
    h = when.hour
    part = "subah" if 4 <= h < 12 else "dopahar" if 12 <= h < 16 else "shaam" if 16 <= h < 20 else "raat"
    h12 = h % 12 or 12
    return f"{day} {part} {h12}:{when.minute:02d} baje"
