"""Automatic boost A/B using Timbre-spoken audio (no mic). Same audio, different boost lists.
Run:  python -m scripts.boost_ab_auto"""
import asyncio
import sys

from echo import tts
from scripts.voice_probe import replay, to_frames
from echo.stt import transcribe

sys.stdout.reconfigure(encoding="utf-8")

SENTENCES = [
    "kal OJT ka viva hai",
    "Gnani ke internship challenge ke liye project submit karna hai",
    "maths mein integration ho gaya differential equations baaki hai",
]
LISTS = {
    "none": None,
    "raw-from-memory (current)": ["ओजीटी", "वैवाह", "वायवा", "viva", "ogt"],
    "clean correct forms": ["वायवा", "ओजेटी", "ज्ञानी", "इंटर्नशिप", "इंटीग्रेशन", "डिफरेंशियल", "इक्वेशंस", "मैथ्स"],
}

for s in SENTENCES:
    frames = to_frames(tts.synthesize(s, "hi-en"))
    print("\nSPOKEN:", s)
    for name, words in LISTS.items():
        for score in (("1.5",) if words else (None,)):
            out = asyncio.run(transcribe(replay(frames), "hi-IN", bias_words=words, bias_score=score))
            print(f"  {name:28s}: {out}")
