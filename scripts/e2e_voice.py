"""End-to-end run of KAIRO's whole flow with a SYNTHESIZED user voice, no microphone and nothing played aloud.
A different Timbre voice speaks the user's sentences -> real Prisma transcribes them (with KAIRO's boost words and rules)
-> real Gemini + memory + quiz + plan -> KAIRO's replies are captured as text. Uses a throwaway database and job store.
Run: python -m scripts.e2e_voice"""
import asyncio
import queue
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

from echo import boost, brain, config, memory, reminders, sounds, tts
from echo.answers import answer_of
from echo.stt import transcribe
from scripts.voice_probe import to_frames

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path(tempfile.mkdtemp(prefix="kairo_e2e_"))
memory.DB_PATH = HOME / "e2e.db"
reminders.JOBS_DB = HOME / "jobs.db"

played = []  # (seconds of audio) for everything KAIRO would have said aloud via a scheduled job
tts.play = lambda wav: played.append(len(wav))
sounds.chime = lambda *a, **k: None
USER_VOICE, KAIRO_VOICE = "Avinash", config.TIMBRE_VOICE

results = []
spoken: list[str] = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("  PASS " if ok else "  FAIL ") + name + (f"   -> {detail}" if detail and not ok else ""))


def user_says(sentence: str) -> str:
    """The user speaks `sentence`; returns what Prisma wrote."""
    config.TIMBRE_VOICE = USER_VOICE
    try:
        frames = to_frames(tts.synthesize(sentence, "hi-en"))
    finally:
        config.TIMBRE_VOICE = KAIRO_VOICE
    q: "queue.Queue[bytes | None]" = queue.Queue()

    def feed():
        for f in frames:
            q.put(f)
            time.sleep(config.FRAME_SECONDS)
        q.put(None)

    threading.Thread(target=feed, daemon=True).start()
    text = asyncio.run(transcribe(q, "hi-IN", bias_words=boost.bias_words(), rules=boost.substitution_rules()))
    print(f"    you said : {sentence}\n    Prisma   : {text}")
    return text


def say(text: str) -> None:
    spoken.append(text)
    print(f"    KAIRO    : {text}")


def session(sentence: str, replies: list[str], smart=None) -> str:
    """One turn exactly like the app: the user speaks, brain.handle runs, KAIRO's final line is returned.
    `replies` are what the user says to each question KAIRO asks (confirmations and quiz answers), in order."""
    replies = list(replies)

    def confirm(prompt):
        say(prompt + " हाँ या नहीं?")
        if not replies:
            return False
        reply = replies.pop(0)
        for _ in range(3):  # like the app: not heard or unclear -> KAIRO asks again and the user repeats
            verdict = answer_of(user_says(reply))
            if verdict != "unknown":
                return verdict == "yes"
            say("सुनाई नहीं दिया, फिर से बोलो, हाँ या नहीं?")
        return False

    def ask(prompt):
        say(prompt)
        if smart:  # a student who answers according to the question that was actually asked
            return user_says(smart(prompt))
        return user_says(replies.pop(0)) if replies else ""

    heard = user_says(sentence)
    if not heard.strip():  # like the app: nothing heard -> KAIRO says so and the user repeats once
        say("सुनाई नहीं दिया, फिर से बोलो।")
        heard = user_says(sentence)
    final = brain.handle(heard, confirm, notify=say, ask=ask)
    say(final)
    time.sleep(2)
    return final


t_start = time.time()
now = datetime.now(reminders.IST)
print(f"started {now:%H:%M} IST; throwaway data in {HOME}\n")

print("1. Save two notes by voice")
session("Yaad rakhna, maths mein integration ho gaya, differential equations baaki hai", ["haan"])
session("Yaad rakhna, physics ke numericals chapter paanch revise karne hain", ["haan"])
check("both notes were saved", len(memory.all_memories()) == 2, str(len(memory.all_memories())))

print("\n2. Voice quiz, answered correctly")
# the topic may be misheard ("maths" -> "मार्च"), so any note can come first: answer whichever question is asked
final = session("maths mein quiz karo", [], smart=lambda q: "differential equations" if "मैथ्स" in q or "टॉपिक" in q else "chapter paanch")
check("KAIRO asked questions and scored the answers", any(s.startswith("सवाल एक।") for s in spoken), str(spoken[-4:]))
check("correct spoken answers earn the cheer", final == "शाबाश! दो में से दो सही।", final)

print("\n3. Voice quiz, answered wrongly")
spoken.clear()
final = session("physics ka quiz karo", ["chapter teen"])
check("a wrong spoken answer is corrected kindly with the right answer", any("पाँच" in s or "5" in s for s in spoken[2:]), str(spoken))
check("all wrong: no harsh score", final.startswith("कोई बात नहीं"), final)

print("\n4. Quiz stopped by voice")
spoken.clear()
final = session("maths ka quiz karo", ["bas ab band karo"])
check("saying 'bas' ends the quiz politely", "रोकते" in final or any("मिलते" in s or "ठीक है" in s for s in spoken), str(spoken))

print("\n5. Today's plan, with a reminder due soon")
if now.hour == 23 and now.minute > 50:
    print("  (skipped: too close to midnight for a 'today' reminder)")
else:
    session("5 minute baad paani peena yaad dilana", ["haan"])
    spoken.clear()
    final = session("aaj ka plan batao", [])
    check("the plan mentions today's reminder", "पानी" in final, final)
    check("the plan is short enough to listen to", 0 < len(final) < 400, str(len(final)))

print("\n6. Daily plan on, then off")
final = session("roz subah 8 baje mujhe aaj ka plan sunana", ["haan"])
check("daily plan scheduled for 8:00", reminders.daily_briefing_time() == (8, 0), str(reminders.daily_briefing_time()))
final = session("plan band karo", [])
check("daily plan switched off by voice", reminders.daily_briefing_time() is None, final)

print("\n7. The scheduled plan really fires and speaks")
fire_at = datetime.now(reminders.IST).replace(second=0, microsecond=0)
fire_at = fire_at.replace(minute=(fire_at.minute + 1) % 60, hour=fire_at.hour + (1 if fire_at.minute == 59 else 0)) if fire_at.hour < 23 or fire_at.minute < 59 else fire_at
reminders.set_daily_briefing(fire_at.hour, fire_at.minute)
print(f"    daily plan set for {fire_at:%H:%M}; waiting up to 100 s for it to fire...")
t0 = time.time()
while not played and time.time() - t0 < 100:
    time.sleep(1)
check("the scheduler fired the plan, Gemini wrote it and Timbre voiced it", bool(played), "nothing was spoken in 100 s")
if played:
    check("the voiced plan is a real audio clip", played[0] > 20_000, f"{played[0]} bytes")
reminders.cancel_daily_briefing()

reminders.start().shutdown()
memory._db.close()
print(f"\n{sum(results)}/{len(results)} checks passed in {time.time() - t_start:.0f} s")
sys.exit(0 if all(results) else 1)
