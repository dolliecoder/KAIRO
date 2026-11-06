"""Calls each candidate Gemini model once with the real intent prompt and reports OK / the exact error."""
import json
import sys
import time

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
CANDIDATES = sys.argv[1:] or ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
                              "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-flash-lite-latest"]
for model in CANDIDATES:
    started = time.time()
    try:
        r = llm._client.models.generate_content(
            model=model, contents="Current time: Saturday\nTranscript: याद रखना कल जिम जाना है",
            config=llm._config(model, llm.INTENT_SYSTEM, True))
        json.loads(r.text)
        print(f"OK    {model:28s} {int((time.time() - started) * 1000)} ms")
    except Exception as e:
        print(f"FAIL  {model:28s} {str(e)[:110]}")
