"""Does sending the silence tail faster than real time (and a shorter grace) save time without losing text?"""
import asyncio
import sys

from echo import stt, tts
from scripts.silence_experiment import SENTENCES, run
from scripts.voice_probe import to_frames

sys.stdout.reconfigure(encoding="utf-8")
SETTINGS = [("baseline  tail 32ms grace 0.4", 0.032, 0.4), ("fast tail  tail  8ms grace 0.4", 0.008, 0.4),
            ("fast+grace tail  8ms grace 0.2", 0.008, 0.2), ("burst      tail  0ms grace 0.2", 0.0, 0.2)]
for s in SENTENCES:
    frames = to_frames(tts.synthesize(s, "hi-en"))
    print("\nSPOKEN:", s)
    for name, pace, grace in SETTINGS:
        stt.TAIL_FRAME_SECONDS, stt.EXTRA_SEGMENT_GRACE = pace, grace
        for _ in range(2):
            text, wait = asyncio.run(run(frames, 300))
            print(f"  {name}: {wait:4.2f} s | {text}")
