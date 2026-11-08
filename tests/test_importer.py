"""The 'Add notes from a PDF' window, driven in code with a fake Gemini and a throwaway database (a window flashes for a
few seconds, nothing is spoken). Run: python -m tests.test_importer"""
import os
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

os.environ["KAIRO_NO_DIALOGS"] = "1"  # no spoken confirmation in tests

from echo import embed, importer, memory, pdfnotes  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path(tempfile.mkdtemp(prefix="kairo_imp_"))
memory.DB_PATH = HOME / "imp.db"
embed.embed = lambda texts, query=False: [[0.0] * embed.DIM for _ in texts]  # offline

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def pump(root, until, seconds=8.0):
    end = time.time() + seconds
    while time.time() < end and not until():
        root.update()
        time.sleep(0.05)
    root.update()
    return until()


def texts(widget):
    """All label and button texts inside a widget tree."""
    out = []
    for w in widget.winfo_children():
        try:
            out.append(str(w.cget("text")))
        except tk.TclError:
            pass
        out += texts(w)
    return out


NOTES = [{"devanagari": f"नोट संख्या {n}", "latin": f"note number {n}", "keywords": ["maths"]} for n in range(1, 4)]
pdf = HOME / "sample.pdf"
pdf.write_bytes(pdfnotes.make_minimal_pdf(["Integration is the reverse of differentiation."]))

# --- the happy path: read, tick, save ---
pdfnotes.extract = lambda path: {"title": "maths calculus chapter 3", "notes": NOTES}
root = tk.Tk()
win = importer.ImportWindow(root, str(pdf))
check("the window reads the PDF and shows the notes", pump(root, lambda: bool(win.result)))
check("all three notes start ticked", len(win.checks) == 3 and all(v.get() for v in win.checks))
check("the save button says how many will be saved", win.save_button.cget("text") == "Save 3 selected notes", win.save_button.cget("text"))
win.checks[1].set(False)
win._refresh_save()
check("unticking one updates the button", win.save_button.cget("text") == "Save 2 selected notes", win.save_button.cget("text"))
win._set_all(False)
check("with nothing ticked the save button is disabled", str(win.save_button.cget("state")) == "disabled")
win._set_all(True)
win.checks[2].set(False)
win._refresh_save()
win.save()
saved = [m["devanagari"] for m in memory.all_memories()]
check("only the ticked notes were saved", saved == ["नोट संख्या 1", "नोट संख्या 2"], str(saved))
check("the confirmation says how many were saved", any("Saved 2 notes" in t for t in texts(win.body)), str(texts(win.body)))
check("saved notes carry the title words as keywords", all("calculus" in m["keywords"] for m in memory.all_memories()))
root.destroy()

# --- the same PDF again: nothing is duplicated, and the window says so ---
root = tk.Tk()
win = importer.ImportWindow(root, str(pdf))
pump(root, lambda: bool(win.result))
win.save()
check("importing again does not duplicate notes", len(memory.all_memories()) == 3, str(len(memory.all_memories())))  # the 3rd note is new
check("the window says some were already saved", any("already saved" in t for t in texts(win.body)), str(texts(win.body)))
root.destroy()

# --- errors are shown in the window, not crashes ---
def fail(path):
    raise pdfnotes.PdfError("That PDF is empty.")


pdfnotes.extract = fail
root = tk.Tk()
win = importer.ImportWindow(root, str(pdf))
check("a PDF problem is shown as a friendly message with a way forward",
      pump(root, lambda: any("empty" in t for t in texts(win.body))) and any("Choose another PDF" in t for t in texts(win.body)), str(texts(win.body)))
root.destroy()


def crash(path):
    raise RuntimeError("something unexpected")


pdfnotes.extract = crash
root = tk.Tk()
win = importer.ImportWindow(root, str(pdf))
check("an unexpected error never leaves the window stuck on the progress bar",
      pump(root, lambda: any("Something went wrong" in t for t in texts(win.body))), str(texts(win.body)))
root.destroy()

# --- cancelling the file dialog just closes the window ---
importer.filedialog.askopenfilename = lambda **k: ""
root = tk.Tk()
importer.ImportWindow(root, None)
closed = False
try:
    root.winfo_exists()  # raises once the window has been destroyed (root.update() does not, in this Python)
except tk.TclError:
    closed = True
check("cancelling the file picker closes the window quietly", closed)

# --- the whole run() entry point opens and closes ---
pdfnotes.extract = lambda path: {"title": "t", "notes": NOTES}
try:
    importer.run(str(pdf), auto_close_ms=1500)
    check("run() opens, shows the notes and closes without errors", True)
except Exception as e:
    check("run() opens, shows the notes and closes without errors", False, repr(e))

memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
