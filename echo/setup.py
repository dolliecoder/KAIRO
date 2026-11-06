"""First-run setup: a small window that asks for the two API keys, tests them and saves them.
Shown only when a key is missing. `python -m echo.setup --check` tests the saved keys without a window."""
import os
import sys
import webbrowser

from dotenv import dotenv_values

from .paths import ENV_FILE

STT_URL = "wss://api.vachana.ai/stt/v3/stream"
GNANI_LINK = "https://app.gnani.ai/voice"
GEMINI_LINK = "https://aistudio.google.com/apikey"


def saved_keys() -> dict:
    values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return {
        "GNANI_API_KEY": os.environ.get("GNANI_API_KEY") or values.get("GNANI_API_KEY") or "",
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY") or values.get("GEMINI_API_KEY") or "",
    }


def keys_present() -> bool:
    k = saved_keys()
    return bool(k["GNANI_API_KEY"].strip() and k["GEMINI_API_KEY"].strip())


def test_gnani(key: str) -> str | None:
    """None if the key works, else a short reason. Opens (and closes) a Prisma session: costs no credits."""
    from websockets.exceptions import InvalidStatus
    from websockets.sync.client import connect
    try:
        with connect(STT_URL, additional_headers={"x-api-key-id": key.strip(), "lang_code": "hi-IN",
                                                  "x-sample-rate": "16000"}, open_timeout=15):
            return None
    except InvalidStatus as e:
        return f"Gnani rejected this key (HTTP {e.response.status_code})"
    except Exception as e:
        return f"could not reach Gnani ({type(e).__name__}) - check your internet"


def test_gemini(key: str) -> str | None:
    from google import genai
    try:
        client = genai.Client(api_key=key.strip())  # keep a reference: a temporary client is closed on GC
        next(iter(client.models.list()))
        return None
    except Exception as e:
        text = str(e)
        if "API key" in text or "API_KEY" in text or "400" in text or "403" in text:
            return "Google rejected this Gemini key"
        return f"could not reach Google ({type(e).__name__}) - check your internet"


def save(gnani: str, gemini: str) -> None:
    """Write the keys to the env file (keeping any other lines the user already has)."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lines = [ln for ln in lines if not ln.startswith(("GNANI_API_KEY=", "GEMINI_API_KEY="))]
    lines += [f"GNANI_API_KEY={gnani.strip()}", f"GEMINI_API_KEY={gemini.strip()}"]
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["GNANI_API_KEY"], os.environ["GEMINI_API_KEY"] = gnani.strip(), gemini.strip()


def show_window(auto_close_ms: int | None = None) -> bool:
    """Returns True if keys were saved. `auto_close_ms` is for tests only."""
    import tkinter as tk
    from tkinter import ttk

    done = {"saved": False}
    root = tk.Tk()
    root.title("Echo - first-time setup")
    root.geometry("520x330")
    root.resizable(False, False)
    root.configure(bg="#1a0b3d")
    style = ttk.Style(root)
    style.configure("TLabel", background="#1a0b3d", foreground="white", font=("Segoe UI", 10))
    style.configure("Head.TLabel", font=("Segoe UI", 16, "bold"), foreground="#ff4fc3")
    style.configure("Link.TLabel", foreground="#9fb4ff", font=("Segoe UI", 9, "underline"))
    style.configure("Status.TLabel", font=("Segoe UI", 9))

    ttk.Label(root, text="Welcome to Echo", style="Head.TLabel").pack(anchor="w", padx=22, pady=(18, 2))
    ttk.Label(root, text="Echo needs two free keys. Paste them below once - they stay on this computer.",
              wraplength=470).pack(anchor="w", padx=22)

    fields = {}
    for label, link, url, name in (("Gnani key (speech)", "Get it at app.gnani.ai/voice", GNANI_LINK, "gnani"),
                                   ("Gemini key (understanding)", "Get a free key at aistudio.google.com/apikey",
                                    GEMINI_LINK, "gemini")):
        ttk.Label(root, text=label).pack(anchor="w", padx=22, pady=(12, 0))
        entry = ttk.Entry(root, width=64, show="•")
        entry.pack(anchor="w", padx=22)
        fields[name] = entry
        link_label = ttk.Label(root, text=link, style="Link.TLabel", cursor="hand2")
        link_label.pack(anchor="w", padx=22)
        link_label.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
    existing = saved_keys()
    fields["gnani"].insert(0, existing["GNANI_API_KEY"])
    fields["gemini"].insert(0, existing["GEMINI_API_KEY"])

    status = ttk.Label(root, text="", style="Status.TLabel", wraplength=470)
    status.pack(anchor="w", padx=22, pady=(10, 0))

    def on_save():
        g, m = fields["gnani"].get().strip(), fields["gemini"].get().strip()
        if not g or not m:
            status.config(text="Please paste both keys.", foreground="#ffb3b3")
            return
        status.config(text="Testing your keys...", foreground="white")
        root.update_idletasks()
        problem = test_gnani(g) or test_gemini(m)
        if problem:
            status.config(text=problem + ". Check the key and try again.", foreground="#ffb3b3")
            return
        save(g, m)
        done["saved"] = True
        root.destroy()

    ttk.Button(root, text="Test and save", command=on_save).pack(anchor="e", padx=22, pady=(8, 0))
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    if auto_close_ms:
        root.after(auto_close_ms, root.destroy)
    root.mainloop()
    return done["saved"]


def ensure_keys() -> None:
    """Call before importing the rest of Echo. Shows the window if a key is missing; quits if cancelled."""
    if any(a.startswith("--selftest") for a in sys.argv) or keys_present():
        return
    if not show_window():
        sys.exit(0)


if __name__ == "__main__":
    if "--check" in sys.argv:
        k = saved_keys()
        print("Gnani :", test_gnani(k["GNANI_API_KEY"]) or "OK")
        print("Gemini:", test_gemini(k["GEMINI_API_KEY"]) or "OK")
    elif "--demo" in sys.argv:
        show_window(auto_close_ms=1500)
        print("window opened and closed without errors")
    else:
        show_window()
