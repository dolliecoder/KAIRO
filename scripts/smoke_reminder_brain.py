"""Runs reminder sentences through the brain with a throwaway job store (nothing real is scheduled)."""
import sys
from pathlib import Path

from echo import brain, reminders

reminders.JOBS_DB = Path(__file__).resolve().parent.parent / "data" / "smoke_jobs.db"
reminders.JOBS_DB.unlink(missing_ok=True)
sys.stdout.reconfigure(encoding="utf-8")

for t in ["kal subah 9 baje Go assignment yaad dilana",
          "आज रात 11 बजे दवाई याद दिलाना",
          "remind me on friday at 4 pm to submit the maths sheet",
          "yaad dilana"]:
    print("\nYou:", t)
    print("KAIRO:", brain.handle(t, lambda p: True))
print("\npending:", [(w.strftime("%a %d %b %H:%M"), task) for w, task in reminders.pending()])
reminders.start().shutdown()
