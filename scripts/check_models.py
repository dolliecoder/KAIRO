"""Calls each configured Gemini model once and prints the exact result or error."""
from google.genai import types

from echo import config, llm

for model in config.GEMINI_MODELS:
    for think in (True, False):
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0) if think else None)
        try:
            r = llm._client.models.generate_content(model=model, contents='Return {"ok": true}', config=cfg)
            print(model, "thinking_budget=0" if think else "default", "->", r.text.strip())
        except Exception as e:
            print(model, "thinking_budget=0" if think else "default", "-> ERROR", str(e)[:200])
