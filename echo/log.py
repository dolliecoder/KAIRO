"""Console activity log: labels which model is doing what, so Gnani's role is visible on screen."""
import os
import sys

if sys.stdout is None:  # started with pythonw (tray only, no console): keep the log in a file instead
    from .paths import DATA_DIR
    sys.stdout = sys.stderr = open(DATA_DIR / "echo.log", "a", buffering=1, encoding="utf-8")
else:
    os.system("")  # enables ANSI colors in Windows terminals
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

COLORS = {"Prisma": "32", "Timbre": "35", "Gemini": "34", "Echo": "36", "Memory": "33"}
LABELS = {"Prisma": "Prisma (Gnani STT)", "Timbre": "Timbre (Gnani TTS)", "Echo": "KAIRO"}  # "Echo" is the internal tag


def log(tag: str, message: str) -> None:
    color = COLORS.get(tag, "37")
    label = LABELS.get(tag, tag)
    print(f"\033[{color}m[{label}]\033[0m {message}", flush=True)
