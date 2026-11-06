"""Release-to-transcript time and accuracy for different Prisma silence settings, on identical audio."""
import asyncio
import queue
import sys
import threading
import time

from echo import config, tts
from echo.stt import transcribe
from scripts.voice_probe import to_frames

sys.stdout.reconfigure(encoding="utf-8")
SENTENCES = ["maths mein kya bacha hai", "kal subah nau baje Go assignment yaad dilana",
             "yaad rakhna physics ke numericals chapter paanch revise karne hain"]


async def run(frames, min_silence):
    q: "queue.Queue[bytes | None]" = queue.Queue()
    mark = {}

    def feed():
        for f in frames:
            q.put(f)
            time.sleep(config.FRAME_SECONDS)
        mark["t"] = time.time()
        q.put(None)

    threading.Thread(target=feed, daemon=True).start()
    text = await transcribe(q, "hi-IN", min_silence_ms=min_silence)
    return text, time.time() - mark["t"]


def _main():
  for s in SENTENCES:
      frames = to_frames(tts.synthesize(s, "hi-en"))
      print("\nSPOKEN:", s)
      for ms in (500, 300, 200, 120):
          text, wait = asyncio.run(run(frames, ms))
          print(f"  min-silence {ms:3d} ms: {wait:4.2f} s after release | {text}")



if __name__ == "__main__":
    _main()
