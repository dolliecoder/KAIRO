"""Non-interactive check of the hero flow, including cross-script recall. Uses a throwaway DB."""
import sys
from pathlib import Path

from echo import brain, memory, reminders

memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "smoke.db"
memory.DB_PATH.unlink(missing_ok=True)
reminders.JOBS_DB = memory.DB_PATH.parent / "smoke_jobs.db"  # never touch the real reminder store
reminders.JOBS_DB.unlink(missing_ok=True)


def confirm(prompt):
    print("  ASK:", prompt)
    return True


sys.stdout.reconfigure(encoding="utf-8")
for t in ["KAIRO, yaad rakhna maths mein integration ho gaya, differential equations baaki hai",
          "मैथ्स में क्या बचा है?",
          "Maths mein kya bacha hai?",
          "kal subah 9 baje Go assignment yaad dilana"]:
    print("\nYou:", t)
    print("KAIRO:", brain.handle(t, confirm))
