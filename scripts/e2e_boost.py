"""End to end, no mic: (1) save a memory from a MISHEARD transcript through the real brain (Gemini),
(2) check Echo learned the correction, (3) speak the sentence with Timbre into Prisma with Echo's own boost
words + rules and compare with no boost. Uses a throwaway database."""
import asyncio
import sys
from pathlib import Path

from echo import boost, brain, memory
from echo.stt import transcribe
from echo import tts
from scripts.voice_probe import replay, to_frames

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "e2e.db"
memory.DB_PATH.unlink(missing_ok=True)

MISHEARD = "कल ओजेटी का विवाह है याद रखना"  # what Prisma wrote for "kal OJT ka viva hai, yaad rakhna"
print("1) saving from the misheard transcript:", MISHEARD)
print("   Echo:", brain.handle(MISHEARD, lambda p: True))
print("2) learned rules:", boost.substitution_rules())
print("   boost words  :", boost.bias_words())

SPOKEN = "kal OJT ka viva hai"
frames = to_frames(tts.synthesize(SPOKEN, "hi-en"))
print("\n3) Timbre speaks:", SPOKEN)
print("   no boost, no rules :", asyncio.run(transcribe(replay(frames), "hi-IN")))
print("   Echo boost + rules :", asyncio.run(transcribe(replay(frames), "hi-IN", bias_words=boost.bias_words(),
                                                         rules=boost.substitution_rules())))
memory._db.close()
memory.DB_PATH.unlink(missing_ok=True)
