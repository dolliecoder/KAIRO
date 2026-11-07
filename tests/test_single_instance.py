"""One KAIRO at a time, and stopping it from outside. Starts real processes (a tray icon flashes for a few seconds)
with dummy keys in a throwaway folder - no network, no secrets. Run: python -m tests.test_single_instance"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
HOME = Path(tempfile.mkdtemp(prefix="kairo_single_"))
ENV = {**os.environ, "KAIRO_HOME": str(HOME), "GNANI_API_KEY": "dummy", "GEMINI_API_KEY": "dummy",
       "KAIRO_NO_DIALOGS": "1", "PYTHONIOENCODING": "utf-8"}
CMD = [sys.executable, "-m", "echo.app"]
failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def start():
    p = subprocess.Popen(CMD, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8")
    lines = []
    threading.Thread(target=lambda: [lines.append(ln) for ln in p.stdout], daemon=True).start()
    return p, lines


def wait_for(pred, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.25)
    return False


def run(*args, timeout=60):
    return subprocess.run(CMD + list(args), cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8",
                          timeout=timeout)


a, a_out = start()
check("first KAIRO starts and reaches 'ready'", wait_for(lambda: any("ready" in ln for ln in a_out), 60), "".join(a_out)[-300:])

b = run()
check("a second launch exits at once with 'already running'", b.returncode == 0 and "already running" in b.stdout, b.stdout + b.stderr)
check("the first KAIRO is still running after that", a.poll() is None)

st = run("--selftest", timeout=120)
check("--selftest still works while KAIRO is running (exempt from the guard)", st.returncode == 0, st.stdout[-300:])

q = run("--quit")
check("--quit exits cleanly", q.returncode == 0, q.stdout + q.stderr)
check("--quit stops the running KAIRO", wait_for(lambda: a.poll() is not None, 20), "still running after 20 s")

q2 = run("--quit")
check("--quit with nothing running says 'not running'", q2.returncode == 0 and "not running" in q2.stdout, q2.stdout)

c, c_out = start()
check("after quitting, KAIRO can be started again", wait_for(lambda: any("ready" in ln for ln in c_out), 60), "".join(c_out)[-300:])
run("--quit")
wait_for(lambda: c.poll() is not None, 20)
if c.poll() is None:
    c.kill()
if a.poll() is None:
    a.kill()
time.sleep(1)
shutil.rmtree(HOME, ignore_errors=True)
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
