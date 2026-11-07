"""Does a lower thinking level make Gemini 3.x models faster for KAIRO's intent call? 4 runs per setting.
Run: python -m scripts.gemini_speed [model ...]"""
import statistics
import sys
import time

from google.genai import types

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
MODELS = sys.argv[1:] or ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
PROMPT = "Current time: Saturday 2026-11-07 10:00\nTranscript: मैथ्स में क्या बचा है"


def run(model, level):
    kwargs = {} if level is None else {"thinking_config": types.ThinkingConfig(thinking_level=level)}
    cfg = types.GenerateContentConfig(system_instruction=llm.INTENT_SYSTEM, response_mime_type="application/json",
                                      temperature=0.2, **kwargs)
    t0 = time.time()
    r = llm.client().models.generate_content(model=model, contents=PROMPT, config=cfg)
    out = llm._parse_json(r.text)
    return time.time() - t0, out.get("intent")


for model in MODELS:
    for level in (None, "MINIMAL", "LOW"):
        try:
            runs = [run(model, level) for _ in range(4)]
            t = [x[0] for x in runs]
            ok = all(x[1] == "recall" for x in runs)
            print(f"{model:24s} thinking={str(level):8s} median {statistics.median(t):4.2f}s  min {min(t):4.2f}  max {max(t):4.2f}  intent ok: {ok}")
        except Exception as e:
            print(f"{model:24s} thinking={str(level):8s} ERROR {str(e)[:100]}")
