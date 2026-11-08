"""Gemini model racing and fallback, with fake models (no network). Run: python -m tests.test_llm_hedge"""
import sys
import time

from echo import config, llm

sys.stdout.reconfigure(encoding="utf-8")
failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


calls = []


def fake(behaviours):
    """behaviours: model -> (seconds to take, 'ok' | error text)."""
    def attempt(model, prompt, system, as_json, slow=False):
        calls.append(model)
        seconds, result = behaviours[model]
        time.sleep(seconds)
        if result != "ok":
            raise RuntimeError(result)
        return {"answer_from": model}, int(seconds * 1000)
    return attempt


def run(behaviours, models=("A", "B", "C")):
    calls.clear()
    llm._cooldown.clear()
    config.GEMINI_MODELS = list(models)
    llm._attempt = fake(behaviours)
    t0 = time.time()
    try:
        out = llm.generate("p", "s")
    except RuntimeError as e:
        out = str(e)
    return out, time.time() - t0


llm.HEDGE_AFTER_SECONDS = 0.3

out, took = run({"A": (0.05, "ok"), "B": (0.05, "ok"), "C": (0.05, "ok")})
check("fast first model answers alone, nobody else is asked", out == {"answer_from": "A"} and calls == ["A"], f"{out} {calls}")

out, took = run({"A": (1.5, "ok"), "B": (0.05, "ok"), "C": (0.05, "ok")})
check("slow first model is raced: the fast second one wins", out == {"answer_from": "B"} and took < 1.0, f"{out} {took:.2f}s {calls}")

out, took = run({"A": (0.9, "ok"), "B": (1.5, "ok"), "C": (0.05, "ok")})
check("two slow models: the third one (started at 0.6 s) beats both", out == {"answer_from": "C"} and took < 0.9, f"{out} {took:.2f}s {calls}")

out, took = run({"A": (0.05, "boom 500"), "B": (0.05, "ok"), "C": (0.05, "ok")})
check("failing first model: the next one answers at once", out == {"answer_from": "B"} and took < 0.25, f"{out} {took:.2f}s {calls}")

out, took = run({"A": (0.05, "429 RESOURCE_EXHAUSTED Please retry in 30s."), "B": (0.05, "ok"), "C": (0.05, "ok")})
check("quota error: falls back and puts model A on a ~31 s cooldown",
      out == {"answer_from": "B"} and 30 <= llm._cooldown["A"] - time.time() <= 32, f"{out} {llm._cooldown}")

llm._cooldown["A"] = time.time() + 100
calls.clear()
config.GEMINI_MODELS = ["A", "B"]
llm._attempt = fake({"A": (0.05, "ok"), "B": (0.05, "ok")})
out = llm.generate("p", "s")
check("a model in cooldown is skipped", out == {"answer_from": "B"} and calls == ["B"], f"{out} {calls}")

out, took = run({"A": (0.05, "bad A"), "B": (0.05, "bad B"), "C": (0.05, "bad C")})
check("all models failing gives one clear error naming each", isinstance(out, str) and "bad A" in out and "bad C" in out, out)

print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
