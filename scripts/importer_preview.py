"""Opens the 'Add notes from a PDF' window on the sample PDF (real Gemini) and saves a picture of just that window once the notes
are shown. Run: python -m scripts.importer_preview <output.png>"""
import ctypes
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path

os.environ["KAIRO_NO_DIALOGS"] = "1"
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # make Tk and the screen grab use the same pixels on scaled displays
except Exception:
    pass

from PIL import ImageGrab  # noqa: E402

from echo import importer, memory  # noqa: E402

out = Path(sys.argv[1])
memory.DB_PATH = Path(tempfile.mkdtemp(prefix="kairo_prev_")) / "preview.db"
pdf = Path(__file__).resolve().parent.parent / "assets" / "demo" / "sample_maths_notes.pdf"

root = tk.Tk()
win = importer.ImportWindow(root, str(pdf))


def wait_then_snap():
    if not win.result:
        root.after(400, wait_then_snap)
        return
    root.update()
    root.lift()
    root.attributes("-topmost", True)
    root.after(800, snap)


def snap():
    root.update()
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(out)
    root.destroy()


root.after(400, wait_then_snap)
root.mainloop()
if memory._db:
    memory._db.close()
print("saved", out)
