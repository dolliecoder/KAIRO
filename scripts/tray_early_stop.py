"""Does tray.stop() called BEFORE tray.run() make run() return? (A quit request can arrive during startup.)"""
import sys
import threading
import time

from echo.tray import Tray

t = Tray(on_quit=lambda: None)
t.stop()  # arrives before the tray loop exists
returned = {"at": None}
t0 = time.time()
threading.Timer(6, lambda: (returned["at"] is None) and (print("run() still blocking after 6 s: the early stop was LOST") or t.icon.stop())).start()
t.run()
returned["at"] = time.time() - t0
print(f"run() returned after {returned['at']:.1f} s")
sys.exit(0 if returned["at"] < 5 else 1)
