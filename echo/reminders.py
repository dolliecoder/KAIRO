"""Spoken reminders. APScheduler with a persistent SQLite job store, so reminders
survive restarts; ones missed while KAIRO was closed are spoken on the next start."""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from .paths import DATA_DIR

IST = ZoneInfo("Asia/Kolkata")
JOBS_DB = DATA_DIR / "jobs.db"
MISSED_GRACE_SECONDS = 24 * 3600

_scheduler: BackgroundScheduler | None = None

HI_NUM = ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
          "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस "
          "सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
          "इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ").split()
HI_MONTHS = ("जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर").split()


def fire(task_latin: str, task_devanagari: str = "") -> None:
    """Job target. Must be a top-level function so the job store can pickle a reference to it."""
    from . import sounds, tts  # lazy: keeps the job store import cheap
    from .log import log

    log("Echo", f"reminder due: {task_latin}")
    task = task_devanagari or task_latin
    try:  # Hindi words go to Timbre in Devanagari so they are pronounced correctly
        wav = tts.synthesize(f"याद दिलाना था: {task}। ध्यान दीजिए, {task}।", language="hi-IN")
    except Exception as e:
        log("Timbre", f"unavailable: {e}")
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


PERIOD_WORDS = {"सुबह", "सवेरे", "दोपहर", "शाम", "रात", "subah", "savere", "dopahar", "shaam", "raat",
                "am", "pm", "a.m.", "p.m.", "a.m", "p.m"}


def said_period(heard: str) -> bool:
    """True if the transcript really contains a day-part word or am/pm (the LLM must not invent one)."""
    return bool(set(heard.lower().replace(",", " ").replace("।", " ").split()) & PERIOD_WORDS)


def resolve(rem: dict, now: datetime | None = None, heard: str | None = None) -> datetime | None:
    """Turn what the user said (hour/minute/am-pm/day, as reported by the LLM) into the next matching time.
    No am/pm said -> both readings are tried and the earliest future one wins ("1:10" at 1:13 AM -> 1:10 PM)."""
    now = now or datetime.now(IST)
    if (rem.get("in_minutes") or 0) > 0:
        return (now + timedelta(minutes=rem["in_minutes"])).replace(second=0, microsecond=0)

    hour, minute = rem.get("hour", -1), rem.get("minute") or 0
    if not isinstance(hour, int) or not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None

    period = rem.get("period") or ""
    if heard is not None and not said_period(heard):
        period = ""  # the LLM guessed am/pm; the user never said it
    if hour == 0 or hour >= 13:
        hours = [hour]
    elif period == "am":
        hours = [hour % 12]
    elif period == "pm":
        hours = [hour % 12 + 12]
    else:
        hours = sorted({hour % 12, hour % 12 + 12})

    offsets = {"today": [0], "tomorrow": [1], "day_after": [2]}.get(rem.get("day") or "", [0, 1])
    if rem.get("date"):  # a weekday / calendar date: count days from today
        try:
            offsets = [(datetime.fromisoformat(rem["date"]).date() - now.date()).days]
        except ValueError:
            return None
    for off in offsets:
        for h in hours:
            when = (now + timedelta(days=off)).replace(hour=h, minute=minute, second=0, microsecond=0)
            if when > now:
                return when
    return None


def schedule(task_latin: str, task_devanagari: str, when: datetime) -> str:
    job = start().add_job(fire, "date", run_date=when, args=[task_latin, task_devanagari])
    return job.id


def pending() -> list[tuple[datetime, str]]:
    return sorted((j.next_run_time, j.args[0]) for j in start().get_jobs() if j.next_run_time)


def _day_part(h: int) -> str:
    return "subah" if 4 <= h < 12 else "dopahar" if 12 <= h < 16 else "shaam" if 16 <= h < 20 else "raat"


def describe(when: datetime) -> str:
    """Latin Hinglish for the console and typed tests: 'kal subah 9:00 baje'."""
    days = (when.date() - datetime.now(IST).date()).days
    day = {0: "aaj", 1: "kal", 2: "parso"}.get(days, f"{when.day} {when.strftime('%B')} ko")
    return f"{day} {_day_part(when.hour)} {when.hour % 12 or 12}:{when.minute:02d} baje"


def describe_hi(when: datetime) -> str:
    """Devanagari with the numbers spelled out, so Timbre reads the time unambiguously:
    'आज दोपहर एक बजकर दस मिनट पर'."""
    days = (when.date() - datetime.now(IST).date()).days
    day = {0: "आज", 1: "कल", 2: "परसों"}.get(days, f"{HI_NUM[when.day] if when.day < 60 else when.day} {HI_MONTHS[when.month - 1]} को")
    part = {"subah": "सुबह", "dopahar": "दोपहर", "shaam": "शाम", "raat": "रात"}[_day_part(when.hour)]
    hour = HI_NUM[when.hour % 12 or 12]
    clock = f"{hour} बजे" if when.minute == 0 else f"{hour} बजकर {HI_NUM[when.minute]} मिनट पर"
    return f"{day} {part} {clock}"
