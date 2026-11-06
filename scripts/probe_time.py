"""Shows how Gemini resolves reminder times. Prints the clock, then each sentence's resolved time + task."""
import sys
from datetime import datetime

from echo import llm, reminders

sys.stdout.reconfigure(encoding="utf-8")
CASES = [
    "आज दोपहर 01:10 बजे पर पानी पीना याद दिलाना",
    "आज 1:10 बजे पानी पीना याद दिलाना",
    "मुझे 1:10 पर पानी पीने का याद दिलाना",
    "आज रात 1:10 बजे पानी पीना याद दिलाना",
    "कल सुबह 09:30 बजे गो असाइनमेंट याद दिलाना",
    "5 मिनट बाद पानी पीना याद दिलाना",
    "आज शाम 05:00 बजे जिम जाना याद दिलाना",
    "पनी पीने का याद दिलाना 2 बजे",
]
print("NOW:", datetime.now(llm.IST).strftime("%a %d %b %H:%M"))
for c in CASES:
    r = llm.parse_intent(c)
    rem = r.get("reminder") or {}
    when = reminders.resolve(rem, heard=c)
    said = {k: rem.get(k) for k in ("day", "hour", "minute", "period", "in_minutes")}
    print(f"{c}\n   said {said}\n   -> {reminders.describe_hi(when) if when else None} | "
          f"{rem.get('task_devanagari')} | {rem.get('task_latin')}")
