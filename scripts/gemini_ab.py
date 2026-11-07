"""Fair A/B of Gemini thinking settings: the two settings alternate run by run, so network noise hits both equally.
Uses KAIRO's real intent prompt and answer prompt. Run: python -m scripts.gemini_ab [model]"""
import statistics
import sys
import time

from google.genai import types

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.5-flash-lite"
RUNS = 6  # 24 calls; free tier allows 15 requests/min/model, so calls are paced
CALLS = {
    "intent": (llm.INTENT_SYSTEM, "Current time: Saturday 2026-11-07 10:00\nTranscript: मैथ्स में क्या बचा है"),
    "answer": (llm.ANSWER_SYSTEM, "Question: मैथ्स में क्या बचा है\nMemories:\n- मैथ्स में इंटीग्रेशन हो गया, डिफरेंशियल इक्वेशंस बाकी हैं"),
}
SETTINGS = {"default": None, "MINIMAL": types.ThinkingConfig(thinking_level="MINIMAL")}

for name, (system, prompt) in CALLS.items():
    times = {k: [] for k in SETTINGS}
    for _ in range(RUNS):
        for label, think in SETTINGS.items():  # alternate: default, MINIMAL, default, MINIMAL, ...
            kwargs = {} if think is None else {"thinking_config": think}
            cfg = types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                              temperature=0.2, **kwargs)
            t0 = time.time()
            llm.client().models.generate_content(model=MODEL, contents=prompt, config=cfg)
            times[label].append(time.time() - t0)
            time.sleep(4.5)  # stay under 15 requests per minute
    for label, t in times.items():
        print(f"{MODEL} {name:6s} {label:8s} median {statistics.median(t):4.2f}s  mean {statistics.mean(t):4.2f}  "
              f"min {min(t):4.2f}  max {max(t):4.2f}  (n={len(t)})")
