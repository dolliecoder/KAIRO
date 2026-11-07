"""'What KAIRO learned' window and its data. Uses a throwaway database; a window flashes for ~1 second.
Run: python -m tests.test_learned"""
import sys
import tempfile
from pathlib import Path

from echo import learned, memory

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(tempfile.mkdtemp(prefix="kairo_learned_")) / "learned.db"
memory._index = lambda *a, **k: None  # offline

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


data = learned.load()
check("a brand-new user: nothing learned, no crash", data == {"words": [], "corrections": [], "notes": 0}, str(data))

memory.save("कल ओजेटी का वायवा है", "kal OJT ka viva hai", ["ojt", "viva"])
memory.add_correction("विवाह", "वायवा")
memory.add_correction("मैच", "मैथ्स")
data = learned.load()
check("notes are counted", data["notes"] == 1)
check("corrections show Prisma's spelling and the intended one", set(data["corrections"]) == {("विवाह", "वायवा"), ("मैच", "मैथ्स")}, str(data["corrections"]))
check("the words KAIRO listens for include the learned fix", "वायवा" in data["words"] and "मैथ्स" in data["words"], str(data["words"]))
check("the word list never exceeds Prisma's limit of 100", len(data["words"]) <= 100)

learned.remove_correction("विवाह")
data = learned.load()
check("removing a wrong correction works", data["corrections"] == [("मैच", "मैथ्स")], str(data["corrections"]))
learned.remove_correction("विवाह")
check("removing it twice is harmless", len(learned.load()["corrections"]) == 1)

try:
    learned.show(auto_close_ms=1200)
    check("the window opens, fills in and closes without errors", True)
except Exception as e:
    check("the window opens, fills in and closes without errors", False, repr(e))

memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
