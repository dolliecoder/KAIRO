"""Spoken yes / no, and the confirmation flow around it (no network, nothing played aloud).
Run: python -m tests.test_answers"""
import sys

import echo.app as app
from echo.answers import answer_of

sys.stdout.reconfigure(encoding="utf-8")
failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


YES = ["हाँ", "हां", "हा", "हान", "हाँन", "हाँ।", "हां जी", "हाँजी", "जी हाँ", "haan", "Haan.", "han", "yes", "yeah", "okay", "ओके",
       "ठीक है", "बिल्कुल", "ज़रूर", "जरूर", "हाँ कर दो", "हाँ, सेव कर दो", "हान हान", "सही है", "हम्म"]
NO = ["नहीं", "नही", "नहि", "ना", "नो", "नहीं नहीं", "मत करो", "nahi", "no", "रुको", "cancel", "नहीं, रहने दो", "हाँ नहीं", "नहीं हाँ"]
UNKNOWN = ["", "   ", "मौसम कैसा है", "हाल", "हानि", "बताना", "kya", "आज बहुत गर्मी है", "।"]

bad = [t for t in YES if answer_of(t) != "yes"]
check(f"{len(YES)} ways of saying yes are understood", not bad, f"missed: {bad}")
bad = [t for t in NO if answer_of(t) != "no"]
check(f"{len(NO)} ways of saying no are understood (a 'no' word always wins)", not bad, f"missed: {bad}")
bad = [t for t in UNKNOWN if answer_of(t) != "unknown"]
check("unrelated words are 'unknown', not yes or no (हाल, हानि, बताना...)", not bad, f"wrongly matched: {bad}")
check("'हान' - what Prisma wrote for a spoken 'haan' - is a yes (the bug the end-to-end run found)", app.is_yes("हान"))

# --- the confirmation flow: the user's next utterances arrive on app.utterances ---
said = []
app.say = said.append
app.CONFIRM_WAIT_SECONDS = 0.3


def confirm_with(*answers):
    said.clear()
    while not app.utterances.empty():
        app.utterances.get()
    for a in answers:
        app.utterances.put(a)
    return app.confirm("सेव कर दूँ?")


check("confirm: 'हान' -> yes", confirm_with("हान") is True)
check("confirm: 'नहीं' -> no", confirm_with("नहीं") is False)
r = confirm_with("", "हाँ")
check("confirm: not heard, then 'हाँ' -> yes, after one polite retry", r is True and sum("सुनाई नहीं दिया" in s for s in said) == 1, str(said))
r = confirm_with("मौसम कैसा है", "हाँ")
check("confirm: unclear answer is asked again, not treated as 'no'", r is True and sum("हाँ या नहीं" in s for s in said) >= 2, str(said))
check("confirm: three unclear answers in a row -> no (nothing is saved by accident)", confirm_with("क्या", "क्या", "क्या") is False)
check("confirm: silence -> no", confirm_with() is False)

print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
