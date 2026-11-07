"""A broken Gemini connection is rebuilt and the call retried once (no network).
Run: python -m tests.test_llm_connection"""
import sys

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


check("each model gets its own connection pool", llm.client("m1") is not llm.client("m2"))
check("the same name reuses one connection pool", llm.client("m1") is llm.client("m1"))

first = llm.client("flaky")
state = {"calls": 0}


def flaky(c):
    state["calls"] += 1
    if state["calls"] == 1:
        raise RuntimeError("Cannot send a request, as the client has been closed.")
    return "answer"


out = llm.with_client("flaky", flaky)
check("closed connection: rebuilt and retried once", out == "answer" and state["calls"] == 2, f"{out} {state}")
check("the broken pool was replaced by a new one", llm.client("flaky") is not first)

state["calls"] = 0


def winerror(c):
    state["calls"] += 1
    if state["calls"] == 1:
        raise OSError("[WinError 10038] An operation was attempted on something that is not a socket")
    return "ok"


check("WinError 10038: rebuilt and retried once", llm.with_client("w", winerror) == "ok" and state["calls"] == 2)

state["calls"] = 0


def always_closed(c):
    state["calls"] += 1
    raise RuntimeError("client has been closed")


try:
    llm.with_client("x", always_closed)
    check("a connection that stays broken raises after one retry", False)
except RuntimeError:
    check("a connection that stays broken raises after one retry", state["calls"] == 2, f"calls={state['calls']}")

state["calls"] = 0


def quota(c):
    state["calls"] += 1
    raise RuntimeError("429 RESOURCE_EXHAUSTED")


try:
    llm.with_client("q", quota)
except RuntimeError:
    pass
check("other errors (quota etc.) are NOT retried here", state["calls"] == 1, f"calls={state['calls']}")

print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
