"""Opens the 'what KAIRO learned' window on a throwaway database with sample data and saves a picture of just that window.
Run: python -m scripts.learned_preview <output.png>"""
import sys
import tempfile
from pathlib import Path

from PIL import ImageGrab

from echo import learned, memory

out = Path(sys.argv[1])
memory.DB_PATH = Path(tempfile.mkdtemp(prefix="kairo_prev_")) / "preview.db"
memory._index = lambda *a, **k: None
for dev, lat, kw in [("मैथ्स में इंटीग्रेशन हो गया, डिफरेंशियल इक्वेशंस बाकी हैं", "maths integration done", ["maths", "integration"]),
                     ("कल ओजेटी का वायवा है", "kal OJT ka viva hai", ["ojt", "viva"]),
                     ("फिजिक्स के न्यूमेरिकल्स चैप्टर पाँच रिवाइज करने हैं", "physics numericals chapter 5", ["physics", "numericals"]),
                     ("जिम में सोमवार को लेग डे है", "gym leg day monday", ["gym"])]:
    memory.save(dev, lat, kw)
memory.add_correction("विवाह", "वायवा")
memory.add_correction("मैच", "मैथ्स")
memory.add_correction("ओजेपी", "ओजेटी")

import tkinter as tk  # noqa: E402

_real_mainloop = tk.Tk.mainloop


def mainloop_with_photo(self, n=0):
    def snap():
        self.update_idletasks()
        self.lift()
        self.attributes("-topmost", True)
        self.update()
        x, y, w, h = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height()
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(out)
        self.destroy()
    self.after(1500, snap)
    _real_mainloop(self, n)


tk.Tk.mainloop = mainloop_with_photo
learned.show()
memory._db.close()
print("saved", out)
