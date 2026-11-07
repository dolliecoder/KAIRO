"""How long KAIRO skips a Gemini model after an error (no network). Run: python -m tests.test_llm_cooldown"""
import sys

from echo.llm import cooldown_seconds

failed = 0


def check(name, got, want):
    global failed
    ok = got == want
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got}, want {want}"))


per_minute = ("429 RESOURCE_EXHAUSTED ... Generate content requests per minute limit exceeded on Free Tier. "
              "Please retry in 57.908238943s. 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'")
per_day = "429 RESOURCE_EXHAUSTED ... 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'"
check("per-minute limit follows Google's retry time (+1 s)", round(cooldown_seconds(per_minute), 1), 58.9)
check("per-day limit skips the model for an hour", cooldown_seconds(per_day), 3600.0)
check("model not found skips it for an hour", cooldown_seconds("404 NOT_FOUND models/x is no longer available"), 3600.0)
check("unknown quota error defaults to 60 s", cooldown_seconds("429 RESOURCE_EXHAUSTED something"), 60.0)
check("absurdly long retry time is capped at 15 minutes", cooldown_seconds("retry in 99999.0s"), 900.0)
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
