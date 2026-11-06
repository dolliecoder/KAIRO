"""Intent routing for ambiguous Hindi/Hinglish sentences (uses real Gemini). Each sentence runs 3 times because
the model is not deterministic. Run: python -m tests.test_intents"""
import sys

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
]
failed = 0
for text, want in CASES:
    got = [llm.parse_intent(text).get("intent") for _ in range(3)]
    ok = all(g == want for g in got)
    failed += not ok
    print(("PASS " if ok else "FAIL ") + f"want {want:7s} got {got}  {text}")
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
