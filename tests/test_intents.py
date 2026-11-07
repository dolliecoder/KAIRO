"""Intent routing for ambiguous Hindi/Hinglish sentences (uses real Gemini). Each sentence runs 3 times because
the model is not deterministic. Free tier allows 15 requests/min/model, so runs are paced.
Run: python -m tests.test_intents"""
import sys
import time

from echo import llm

sys.stdout.reconfigure(encoding="utf-8")
CASES = [
    ("याद रखना कल जिम जाना है", "save"),                       # yaad rakhna + a day: still a save
    ("yaad rakhna kal subah 9 baje meeting hai", "save"),        # yaad rakhna + a day AND a time: still a save
    ("याद रखना शुक्रवार को असाइनमेंट जमा करना है", "save"),
    ("कल जिम जाना याद दिलाना", "remind"),
    ("kal subah 9 baje Go assignment yaad dilana", "remind"),
    ("remind me at 5 pm to call mom", "remind"),
    ("मैथ्स में क्या बचा है", "recall"),
    ("bhool jao maths wali baat", "forget"),
    # --- 1.1.0: quiz and the day's plan, and they must not steal sentences from the older intents ---
    ("मैथ्स में क्विज़ करो", "quiz"),
    ("mujhe quiz karo", "quiz"),
    ("physics ke sawal poochho", "quiz"),
    ("आज का प्लान बताओ", "briefing"),
    ("morning briefing do", "briefing"),
    ("roz subah 8 baje mujhe aaj ka plan sunana", "briefing"),
    ("plan band karo", "briefing"),
    ("कल शाम 6 बजे मीटिंग की याद दिलाना", "remind"),           # a reminder for ONE task, not a briefing
    ("याद रखना कल क्विज़ है", "save"),                          # a note that mentions a quiz is still a save
]
# (sentence, which field to check, expected value) for the quiz and briefing details
DETAILS = [
    ("aaj ka plan batao", ("briefing", "action"), "now"),
    ("plan band karo", ("briefing", "action"), "daily_off"),
    ("roz subah 8 baje mujhe aaj ka plan sunana", ("briefing", "action"), "daily_on"),
    ("roz subah 8 baje mujhe aaj ka plan sunana", ("briefing", "hour"), 8),
    ("roz shaam 6 baje plan sunana", ("briefing", "hour"), 18),
    ("roz subah saade saat baje plan sunana", ("briefing", "minute"), 30),
]
PAUSE = 3.3  # seconds after every call: ~13 requests/min, under the free-tier limit of 15 per model


def intent_of(text):
    out = llm.parse_intent(text)
    time.sleep(PAUSE)
    return out


failed = 0
for text, want in CASES:
    got = [intent_of(text).get("intent") for _ in range(3)]
    ok = all(g == want for g in got)
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"want {want:9s} got {got}  {text}")

print()
for text, (group, field), want in DETAILS:
    got = [(intent_of(text).get(group) or {}).get(field) for _ in range(3)]
    ok = all(g == want for g in got)
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"{group}.{field} want {want!r:11} got {got}  {text}")

topic = [(intent_of("maths mein quiz karo").get("quiz") or {}).get("topic", "") for _ in range(3)]
ok = all(t and any(w in t.lower() for w in ("math", "मैथ", "गणित", "ganit")) for t in topic)
failed += not ok
print(("PASS " if ok else "FAIL ") + f"quiz.topic for 'maths mein quiz karo' = {topic}")

print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
