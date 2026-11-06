"""Lists Gemini models your key can call."""
from echo import config
from google import genai

c = genai.Client(api_key=config.GEMINI_API_KEY)
print("key set:", bool(config.GEMINI_API_KEY))
for m in c.models.list():
    if "generateContent" in (m.supported_actions or []) and "gemini" in m.name:
        print(m.name)
