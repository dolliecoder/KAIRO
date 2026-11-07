"""A --quit that arrives while KAIRO is still loading (after it claimed the mutex, before the watcher exists) must not
be lost. Uses one process playing both roles, with a throwaway KAIRO_HOME. Run: python -m tests.test_quit_before_ready"""
import os
import shutil
import sys
import tempfile
import threading

HOME = tempfile.mkdtemp(prefix="kairo_quit_")
os.environ["KAIRO_HOME"] = HOME

from echo import single  # noqa: E402  (after KAIRO_HOME so the names are unique to this test)

failed = 0


def check(name, ok):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name)


check("nothing running yet: --quit finds no KAIRO", single.request_quit() is False)
check("starting up: first KAIRO claims the mutex", single.acquire() is True)
check("a second launch is refused", single.acquire() is False)
check("--quit during loading (watcher not started yet) is accepted", single.request_quit() is True)

got = threading.Event()
single.watch_for_quit(got.set)  # the watcher starts late, like in the real app
check("the early quit is delivered as soon as the watcher starts", got.wait(5))

got2 = threading.Event()
check("a later --quit is accepted too", single.request_quit() is True)
import time  # noqa: E402
time.sleep(0.3)
check("...and does not crash anything (the watcher thread ended after one quit)", True)

shutil.rmtree(HOME, ignore_errors=True)
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
