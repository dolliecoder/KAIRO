"""Reminder persistence test.
  python -m scripts.test_reminders schedule   -> schedules a reminder 5 s ahead, then exits immediately
  python -m scripts.test_reminders run        -> starts the scheduler; a missed reminder should be spoken
"""
import sys
import time
from datetime import datetime, timedelta

from echo import reminders

mode = sys.argv[1] if len(sys.argv) > 1 else "run"
sched = reminders.start()

if mode == "schedule":
    when = datetime.now(reminders.IST) + timedelta(seconds=5)
    reminders.schedule("Go assignment submit karna hai", "", when)
    print("scheduled for", when.strftime("%H:%M:%S"), "-", reminders.describe(when))
    print("pending:", reminders.pending())
    sched.shutdown()  # exit before it fires
else:
    print("pending at start:", reminders.pending())
    time.sleep(12)  # long enough for a missed job to fire and be spoken
    sched.shutdown()
    print("pending after:", reminders.pending())
