"""Deterministic checks for reminder time resolution (no network). Run: python -m tests.test_resolve"""
import sys
from datetime import datetime

from echo.reminders import IST, describe_hi, resolve

sys.stdout.reconfigure(encoding="utf-8")


def at(day, h, m):
    return datetime(2026, 11, day, h, m, tzinfo=IST)


def r(**kw):
    return {"day": "", "hour": -1, "minute": 0, "period": "", "in_minutes": 0, **kw}


CASES = [
    # (description, now, reminder fields, expected)
    ("1:10, no am/pm, at 01:13 -> next 1:10 is 13:10 today", at(7, 1, 13), r(hour=1, minute=10), at(7, 13, 10)),
    ("1:10, no am/pm, at 00:50 -> 01:10 today", at(7, 0, 50), r(hour=1, minute=10), at(7, 1, 10)),
    ("1:10, no am/pm, at 14:00 -> 01:10 tomorrow", at(7, 14, 0), r(hour=1, minute=10), at(8, 1, 10)),
    ("dopahar 1:10 (pm)", at(7, 1, 13), r(hour=1, minute=10, period="pm"), at(7, 13, 10)),
    ("raat 1:10 (am), at 23:00 -> 01:10 tomorrow", at(7, 23, 0), r(hour=1, minute=10, period="am"), at(8, 1, 10)),
    ("kal subah 9 (am)", at(7, 12, 0), r(day="tomorrow", hour=9, period="am"), at(8, 9, 0)),
    ("kal 9, no am/pm -> earliest = 9 AM", at(7, 12, 0), r(day="tomorrow", hour=9), at(8, 9, 0)),
    ("aaj shaam 5 (pm), at 10:00", at(7, 10, 0), r(day="today", hour=5, period="pm"), at(7, 17, 0)),
    ("aaj 5 pm but it is already 18:00 -> None", at(7, 18, 0), r(day="today", hour=5, period="pm"), None),
    ("17:30 (24h)", at(7, 10, 0), r(hour=17, minute=30), at(7, 17, 30)),
    ("in 5 minutes", at(7, 1, 13), r(in_minutes=5), at(7, 1, 18)),
    ("12 noon, no am/pm, at 09:00 -> 12:00 today", at(7, 9, 0), r(hour=12), at(7, 12, 0)),
    ("parso 7 am", at(7, 9, 0), r(day="day_after", hour=7, period="am"), at(9, 7, 0)),
    ("no clock time -> None", at(7, 9, 0), r(), None),
    ("date given (friday 13 Nov) 4 pm", at(7, 9, 0), {**r(hour=4, period="pm"), "date": "2026-11-13"}, at(13, 16, 0)),
    ("bad date string -> None", at(7, 9, 0), {**r(hour=4, period="pm"), "date": "friday"}, None),
]

# The LLM sometimes invents am/pm. If the transcript has no day-part word, the period must be ignored.
HEARD_CASES = [
    ("LLM invented 'am' for 'आज 1:10 बजे' at 01:13 -> ignored, 13:10", at(7, 1, 13),
     r(day="today", hour=1, minute=10, period="am"), "आज 1:10 बजे पानी पीना याद दिलाना", at(7, 13, 10)),
    ("'आज रात 1:10' keeps am (raat said) but it's past -> None", at(7, 1, 13),
     r(day="today", hour=1, minute=10, period="am"), "आज रात 1:10 बजे पानी पीना याद दिलाना", None),
    ("'कल सुबह 9' keeps am", at(7, 12, 0),
     r(day="tomorrow", hour=9, period="am"), "कल सुबह 9 बजे", at(8, 9, 0)),
    ("'शाम 5' keeps pm", at(7, 10, 0),
     r(day="today", hour=5, period="pm"), "आज शाम 5 बजे जिम", at(7, 17, 0)),
]

failed = 0
for name, now, fields, want in CASES:
    got = resolve(fields, now)
    ok = got == want
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got}, want {want}"))

for name, now, fields, heard, want in HEARD_CASES:
    got = resolve(fields, now, heard=heard)
    ok = got == want
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got}, want {want}"))

print("\nspoken Hindi:", describe_hi(at(7, 13, 10)), "|", describe_hi(at(7, 9, 0)), "|", describe_hi(at(7, 21, 45)))
total = len(CASES) + len(HEARD_CASES)
print(f"\n{total - failed}/{total} passed")
sys.exit(1 if failed else 0)
