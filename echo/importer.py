"""'Add notes from a PDF': pick a PDF, Gemini reads it and writes short notes, you tick the ones to keep, and they become
ordinary KAIRO notes (so "maths mein quiz karo" works on them). Opened from the tray menu as its own window process, or
with `--import-pdf [file.pdf]`. The PDF is sent to Google Gemini to be read; nothing else leaves the computer."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from . import pdfnotes

BG, FG, PINK, MUTED, CARD = "#1a0b3d", "#ffffff", "#ff4fc3", "#c9bbe8", "#2a1460"


class ImportWindow:
    def __init__(self, root: tk.Tk, path: str | None = None):
        self.root = root
        self.path = ""
        self.result: dict = {}
        self.checks: list[tk.BooleanVar] = []
        self._outcome = None  # set by the reading thread: ("ok", result) or ("error", message)

        root.title("KAIRO - add notes from a PDF")
        root.geometry("720x640")
        root.minsize(600, 480)
        root.configure(bg=BG)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Head.TLabel", font=("Segoe UI", 16, "bold"), foreground=PINK)
        style.configure("Sub.TLabel", foreground=MUTED)
        style.configure("Dev.TLabel", font=("Segoe UI", 11), background=CARD)
        style.configure("Lat.TLabel", foreground=MUTED, background=CARD, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("TCheckbutton", background=CARD, foreground=FG)
        style.configure("Horizontal.TProgressbar", troughcolor=CARD, background=PINK)

        self.body = ttk.Frame(root, padding=18)
        self.body.pack(fill="both", expand=True)
        self.start(path) if path else self.choose()

    # ---- stages -------------------------------------------------------------------------------------------
    def _clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        ttk.Label(self.body, text="Add notes from a PDF", style="Head.TLabel").pack(anchor="w")

    def choose(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Choose your notes (PDF)",
                                          filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            self.root.destroy()
            return
        self.start(path)

    def start(self, path: str) -> None:
        self.path = path
        self._outcome = None
        self._clear()
        ttk.Label(self.body, text=f"Reading {os.path.basename(path)} ...", font=("Segoe UI", 11)).pack(anchor="w", pady=(14, 6))
        bar = ttk.Progressbar(self.body, mode="indeterminate", length=420)
        bar.pack(anchor="w")
        bar.start(12)
        ttk.Label(self.body, style="Sub.TLabel", wraplength=640,
                  text="This takes 10 to 30 seconds. The PDF is sent to Google Gemini to be read; nothing else leaves "
                       "your computer.").pack(anchor="w", pady=(10, 0))
        threading.Thread(target=self._read, daemon=True).start()
        self.root.after(250, self._poll)

    def _read(self) -> None:
        try:
            self._outcome = ("ok", pdfnotes.extract(self.path))
        except pdfnotes.PdfError as e:
            self._outcome = ("error", str(e))
        except Exception as e:  # never leave the window stuck on the progress bar
            self._outcome = ("error", f"Something went wrong: {str(e)[:120]}")

    def _poll(self) -> None:
        if self._outcome is None:
            self.root.after(250, self._poll)
        elif self._outcome[0] == "ok":
            self.show_notes(self._outcome[1])
        else:
            self.show_error(self._outcome[1])

    def show_error(self, message: str) -> None:
        self._clear()
        ttk.Label(self.body, text=message, wraplength=640, font=("Segoe UI", 11)).pack(anchor="w", pady=(16, 14))
        row = ttk.Frame(self.body)
        row.pack(anchor="w")
        ttk.Button(row, text="Choose another PDF", command=self.choose).pack(side="left")
        ttk.Button(row, text="Close", command=self.root.destroy).pack(side="left", padx=8)

    def show_notes(self, result: dict) -> None:
        self.result = result
        self._clear()
        notes = result["notes"]
        ttk.Label(self.body, text=f"{result['title']}  -  {len(notes)} notes", font=("Segoe UI", 11, "bold")
                  ).pack(anchor="w", pady=(10, 0))
        ttk.Label(self.body, style="Sub.TLabel", wraplength=660,
                  text="Untick any note you do not want. Only the ticked notes are saved.").pack(anchor="w", pady=(0, 8))

        holder = ttk.Frame(self.body)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(holder, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=640)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.checks = []
        for note in notes:
            var = tk.BooleanVar(value=True)
            self.checks.append(var)
            card = tk.Frame(inner, bg=CARD, padx=10, pady=8)
            card.pack(fill="x", pady=3)
            # a plain tk checkbox (white box, black tick): the themed one draws an "x" that reads as "removed"
            tk.Checkbutton(card, variable=var, command=self._refresh_save, bg=CARD, activebackground=CARD, selectcolor="white",
                           highlightthickness=0, bd=0).pack(side="left", anchor="n")
            text = tk.Frame(card, bg=CARD)
            text.pack(side="left", fill="x", expand=True, padx=(6, 0))
            ttk.Label(text, text=note["devanagari"], style="Dev.TLabel", wraplength=560, justify="left").pack(anchor="w")
            ttk.Label(text, text=note["latin"], style="Lat.TLabel", wraplength=560, justify="left").pack(anchor="w")

        row = ttk.Frame(self.body)
        row.pack(fill="x", pady=(10, 0))
        self.save_button = ttk.Button(row, text="Save selected notes", command=self.save)
        self.save_button.pack(side="left")
        ttk.Button(row, text="Select all", command=lambda: self._set_all(True)).pack(side="left", padx=8)
        ttk.Button(row, text="Select none", command=lambda: self._set_all(False)).pack(side="left")
        ttk.Button(row, text="Cancel", command=self.root.destroy).pack(side="right")
        self._refresh_save()

    def _set_all(self, value: bool) -> None:
        for var in self.checks:
            var.set(value)
        self._refresh_save()

    def _refresh_save(self) -> None:
        chosen = sum(v.get() for v in self.checks)
        self.save_button.config(text=f"Save {chosen} selected notes", state="normal" if chosen else "disabled")

    def save(self) -> None:
        chosen = [n for n, v in zip(self.result["notes"], self.checks) if v.get()]
        count = pdfnotes.save(self.result["title"], chosen)
        self.show_done(count, len(chosen))

    def show_done(self, saved: int, chosen: int) -> None:
        self._clear()
        if saved:
            line = f"Saved {saved} notes."
            if saved < chosen:
                line += f" ({chosen - saved} were already saved.)"
            hint = "Now hold Right Ctrl and say:  \"Maths mein quiz karo\"  (or the subject of your PDF) - or ask any question about them."
        else:
            line, hint = "Those notes were all saved already.", "Nothing new was added."
        ttk.Label(self.body, text=line, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(16, 6))
        ttk.Label(self.body, text=hint, style="Sub.TLabel", wraplength=640).pack(anchor="w")
        ttk.Button(self.body, text="Close", command=self.root.destroy).pack(anchor="w", pady=16)
        self._speak(saved)

    @staticmethod
    def _speak(saved: int) -> None:
        """A spoken confirmation, best effort: the window must work without audio or a network."""
        if os.environ.get("KAIRO_NO_DIALOGS") or not saved:
            return

        def go() -> None:
            try:
                from . import tts
                from .reminders import HI_NUM
                count = HI_NUM[saved] if saved < len(HI_NUM) else str(saved)
                tts.speak(f"मैंने {count} नोट्स याद कर लिए हैं। अब बोलिए, क्विज़ करो।", "hi-IN")
            except Exception:
                pass

        threading.Thread(target=go, daemon=True).start()


def run(path: str | None = None, auto_close_ms: int | None = None) -> None:
    """Opens the window and blocks until it is closed. `auto_close_ms` is for tests only."""
    root = tk.Tk()
    ImportWindow(root, path)
    if auto_close_ms:
        root.after(auto_close_ms, root.destroy)
    try:
        root.mainloop()
    except tk.TclError:  # the window was destroyed while a callback was pending (cancelled file dialog)
        pass
