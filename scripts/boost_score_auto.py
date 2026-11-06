"""Does a stronger boost fix 'viva' -> 'विवाह', and does it cause false matches on unrelated speech?"""
import asyncio
import sys

from echo import tts
from echo.stt import transcribe
from scripts.voice_probe import replay, to_frames

sys.stdout.reconfigure(encoding="utf-8")
WORDS = ["वायवा", "ओजेटी", "मैथ्स", "इंटीग्रेशन", "डिफरेंशियल", "इक्वेशंस", "इंटर्नशिप"]
TESTS = [
    ("kal OJT ka viva hai", "should become वायवा"),
    ("aaj mausam bahut accha hai", "unrelated: must NOT contain boosted words"),
    ("meri shaadi ka vivah kal hai", "real वह word विवाह: ideally unchanged"),
    ("mujhe kal bazaar jaana hai", "unrelated"),
]
for text, note in TESTS:
    frames = to_frames(tts.synthesize(text, "hi-en"))
    print(f"\nSPOKEN: {text}   [{note}]")
    for score in (None, "1.5", "2.0"):
        out = asyncio.run(transcribe(replay(frames), "hi-IN", bias_words=WORDS if score else None, bias_score=score))
        print(f"  score {score or 'off':4s}: {out}")
