import os

from dotenv import load_dotenv

from .paths import ENV_FILE

load_dotenv(ENV_FILE)

API_KEY = os.environ.get("GNANI_API_KEY", "")
TIMBRE_MODEL = os.environ.get("TIMBRE_MODEL", "timbre-v3.0")
TIMBRE_VOICE = os.environ.get("TIMBRE_VOICE", "Shivani")

STT_URL = "wss://api.vachana.ai/stt/v3/stream"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

SAMPLE_RATE = 16000
FRAME_BYTES = 1024  # Prisma needs exactly 1,024-byte frames (512 samples @ 16 kHz = 32 ms)
FRAME_SECONDS = 0.032

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.5-flash,gemini-2.5-flash").split(",")]

# Prisma accepts 0.0, 0.5, 1.0, 1.5, 2.0 (0.0 disables boosting)
BIAS_SCORE = os.environ.get("BIAS_SCORE", "2.0")

# How long Prisma waits in silence before closing a speech segment (100-2000, docs default 500)
MIN_SILENCE_MS = int(os.environ.get("MIN_SILENCE_MS", "300"))
