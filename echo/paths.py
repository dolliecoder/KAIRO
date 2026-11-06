"""Where Echo keeps its files.

Running from source: the project's own data/ folder and .env (unchanged).
Installed app (PyInstaller): %APPDATA%\\Echo, so updates never touch memories, reminders or keys.
ECHO_HOME overrides both (used by tests)."""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
_PROJECT = Path(__file__).resolve().parent.parent

if os.environ.get("ECHO_HOME"):
    DATA_DIR = Path(os.environ["ECHO_HOME"])
    ENV_FILE = DATA_DIR / ".env"
elif FROZEN:
    DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "Echo"
    ENV_FILE = DATA_DIR / ".env"
else:
    DATA_DIR = _PROJECT / "data"
    ENV_FILE = _PROJECT / ".env"

DATA_DIR.mkdir(parents=True, exist_ok=True)
