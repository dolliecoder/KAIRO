"""Where does the time go between releasing the key and Echo speaking? No mic: Timbre speaks the question,
Prisma transcribes it in real time, then the real brain and Timbre run. Throwaway database.
Run: python -m scripts.latency"""
import asyncio
import queue
import sys
import threading
import time
from pathlib import Path

from echo import boost, brain, config, llm, memory, recall, reminders, tts
from echo.stt import transcribe
from scripts.voice_probe import to_frames

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "latency.db"
memory.DB_PATH.unlink(missing_ok=True)
reminders.JOBS_DB = memory.DB_PATH.parent / "latency_jobs.db"

for t in ["याद रखना मैथ्स में इंटीग्रेशन हो गया डिफरेंशियल इक्वेशंस बाकी हैं", "याद रखना जिम में सोमवार को लेग डे है",
          "याद रखना डेटाबेस का असाइनमेंट शुक्रवार तक जमा करना है"]:
    brain.handle(t, lambda p: True)

timings: dict[str, float] = {}


def timed(module, name, label):
    orig = getattr(module, name)

    def wrapper(*a, **k):
        t0 = time.time()
        try:
            return orig(*a, **k)
        finally:
            timings[label] = timings.get(label, 0) + time.time() - t0
    setattr(module, name, wrapper)


timed(llm, "parse_intent", "Gemini: understand intent")
timed(recall, "retrieve", "Memory: search (keyword + meaning)")
timed(llm, "answer", "Gemini: write answer")
timed(tts, "synthesize", "Timbre: synthesize reply")
brain.recall.retrieve = recall.retrieve  # brain imported the module, wrapper is picked up via attribute

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "maths mein kya bacha hai"
frames = to_frames(tts.synthesize(QUESTION, "hi-en"))
timings.clear()

q: "queue.Queue[bytes | None]" = queue.Queue()
release = {}


def feed():
    for f in frames:
        q.put(f)
        time.sleep(config.FRAME_SECONDS)
    release["t"] = time.time()  # the moment the key is released
    q.put(None)


threading.Thread(target=feed, daemon=True).start()
text = asyncio.run(transcribe(q, "hi-IN", bias_words=boost.bias_words(), rules=boost.substitution_rules()))
t_text = time.time()
timings["Prisma: transcript after release"] = t_text - release["t"]
reply = brain.handle(text, lambda p: True)
t_reply = time.time()
tts.synthesize(reply, "hi-IN")  # Echo's spoken reply (not cached the first time)
t_speak = time.time()
print(f"\nQuestion: {QUESTION}\nPrisma  : {text}\nEcho    : {reply}\n")
order = ["Prisma: transcript after release", "Gemini: understand intent", "Memory: search (keyword + meaning)",
         "Gemini: write answer", "Timbre: synthesize reply"]
for k in order:
    print(f"  {k:38s} {timings.get(k, 0):5.2f} s")
print(f"  {'TOTAL until Echo starts speaking':38s} {t_speak - release['t']:5.2f} s")
memory._db.close()
memory.DB_PATH.unlink(missing_ok=True)
