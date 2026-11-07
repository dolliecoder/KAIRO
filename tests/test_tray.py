"""Tray smoke test: builds the real tray icon, cycles through every state, then quits it from a timer thread.
A tray icon appears for ~3 seconds. Run: python -m tests.test_tray"""
import sys
import threading
import time

from echo.tray import STATES, Tray, _image

failed = 0


def check(name, ok):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name)


quit_called = []
tray = Tray(on_quit=lambda: quit_called.append(True))
check("every state has a label and a colour", all(len(v) == 2 and len(v[1]) == 3 for v in STATES.values()))
check("icon image is 64x64", _image((1, 2, 3)).size == (64, 64))
seen = []


def drive():
    time.sleep(1.0)
    for state in ("listening", "thinking", "speaking", "idle"):
        tray.set_state(state)
        seen.append(tray.state)
        time.sleep(0.3)
    tray.stop()


threading.Thread(target=drive, daemon=True).start()
tray.run()  # blocks until tray.stop() above
check("tray went through every state", seen == ["listening", "thinking", "speaking", "idle"])
check("tray.run() returned after stop()", True)
# a stop request that arrives BEFORE the tray loop starts (e.g. Quit clicked during startup) must not be lost
early = Tray(on_quit=lambda: None)
early.stop()
t0 = time.time()
watchdog = threading.Timer(6, lambda: early.icon.stop())  # only fires if the early stop was lost
watchdog.start()
early.run()
watchdog.cancel()
check("an early stop() is honoured: run() returns at once", time.time() - t0 < 3)

# stop() while the tray loop is already running (the normal case)
normal = Tray(on_quit=lambda: None)
threading.Timer(1.0, normal.stop).start()
t0 = time.time()
normal.run()
check("a normal stop() while running ends run()", time.time() - t0 < 5)

print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
