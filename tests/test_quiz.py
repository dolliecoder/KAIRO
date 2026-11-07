"""Voice quiz. Deterministic checks use a fake Gemini and a throwaway database (no network);
add --live to also check that real Gemini writes and judges questions sensibly. Run: python -m tests.test_quiz [--live]"""
import sys
import tempfile
from pathlib import Path

from echo import llm, memory, quiz, reminders

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(tempfile.mkdtemp(prefix="kairo_quiz_")) / "quiz.db"
reminders.JOBS_DB = memory.DB_PATH.parent / "jobs.db"
memory._index = lambda *a, **k: None          # no embeddings: keep this test offline
memory.search_semantic = lambda *a, **k: []

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def play(topic, answers, verdicts=None, items=None, make_fails=False, judge_fails=False):
    """Runs a quiz with scripted answers and fake Gemini; returns (closing sentence, prompts asked, lines said, judged)."""
    asked, said, judged = [], [], []
    answers = list(answers)

    def ask(prompt):
        asked.append(prompt)
        return answers.pop(0) if answers else ""

    def fake_make(notes):
        if make_fails:
            raise RuntimeError("quota")
        return items if items is not None else [{"question": f"प्रश्न {i}?", "answer": f"उत्तर {i}"} for i in range(1, len(notes) + 1)]

    verdict_iter = iter(verdicts or [])

    def fake_judge(question, expected, heard):
        if judge_fails:
            raise RuntimeError("quota")
        judged.append((question, expected, heard))
        v = next(verdict_iter)
        return {"verdict": v, "feedback": {"correct": "बहुत बढ़िया!", "wrong": "सही जवाब कुछ और है।",
                                           "stop": "ठीक है, फिर मिलते हैं।", "skip": "कोई बात नहीं।"}[v]}

    llm.make_quiz, llm.judge_answer = fake_make, fake_judge
    closing = quiz.run(topic, ask, said.append)
    return closing, asked, said, judged


# --- no notes ---
closing, asked, said, _ = play("", [])
check("no notes: says so and asks nothing", closing == quiz.NO_NOTES and not asked and not said)

memory.save("मैथ्स में इंटीग्रेशन हो गया", "maths mein integration ho gaya", ["maths", "integration"])
memory.save("जिम में सोमवार को लेग डे है", "gym mein somvaar ko leg day hai", ["gym", "leg"])
memory.save("कल ओजेटी का वायवा है", "kal OJT ka viva hai", ["ojt", "viva"])

closing, asked, said, judged = play("", ["a", "b", "c"], ["correct", "correct", "correct"])
check("3 notes, all correct: asks 3 questions numbered in Hindi", len(asked) == 3 and asked[0].startswith("सवाल एक।") and asked[2].startswith("सवाल तीन।"), str(asked))
check("all correct: cheers with the score", closing == "शाबाश! तीन में से तीन सही।", closing)
check("the quiz announces itself first", said[0] == quiz.START and len(said) == 4, str(said))

closing, asked, said, judged = play("", ["a", "b", "c"], ["correct", "wrong", "correct"])
check("one wrong: score two of three", "तीन में से दो सही" in closing, closing)
check("a wrong answer gets corrective feedback spoken", "सही जवाब कुछ और है।" in said, str(said))

closing, asked, said, judged = play("", ["a", "", "c"], ["correct", "correct"])
check("silence counts as a skip and the correct answer is spoken, with no Gemini call",
      len(judged) == 2 and any("सही जवाब है: उत्तर 2" in s for s in said), f"{judged} {said}")
check("silence still counts toward the total (two of three)", "तीन में से दो सही" in closing, closing)

closing, asked, said, judged = play("", ["a", "बस"], ["correct", "stop"])
check("'stop' ends the quiz early with a goodbye", len(asked) == 2 and "ठीक है, फिर मिलते हैं।" in said, f"{asked} {said}")
check("a stopped question is not counted", closing == "शाबाश! एक में से एक सही।", closing)

closing, asked, said, judged = play("", ["a", "b", "c"], ["wrong", "wrong", "wrong"])
check("all wrong: kind message, not a harsh score", closing.startswith("कोई बात नहीं"), closing)

closing, asked, said, judged = play("", ["a", "b", "c"], judge_fails=True)
check("Gemini failing while judging: quiz carries on, speaks the correct answers",
      len(asked) == 3 and sum("सही जवाब है" in s for s in said) == 3, f"{asked} {said}")

closing, asked, said, judged = play("", ["a"], make_fails=True)
check("Gemini failing while writing questions: polite message, no crash", closing == quiz.NOT_READY and not asked, closing)

closing, asked, said, judged = play("", ["a"], items=[])
check("Gemini returning no questions: polite message", closing == quiz.NOT_READY, closing)

# --- topic selection uses the real keyword search ---
picked = quiz.pick_notes("maths")
check("a topic picks only matching notes", len(picked) == 1 and "मैथ्स" in picked[0]["devanagari"], str(picked))
picked = quiz.pick_notes("chemistry")
check("an unknown topic falls back to your newest notes", len(picked) == 3, str(len(picked)))
check("never more than 3 questions", len(quiz.pick_notes("")) <= quiz.MAX_QUESTIONS)

# --- live Gemini (optional) ---
if "--live" in sys.argv:
    print("\nlive Gemini:")
    from echo.llm import has_devanagari  # noqa: E402
    import importlib
    importlib.reload(llm)  # undo the fakes
    notes = ["मैथ्स में इंटीग्रेशन हो गया, डिफरेंशियल इक्वेशंस बाकी हैं", "कल ओजेटी का वायवा है"]
    items = llm.make_quiz(notes)
    check("live: one question per note", len(items) == 2, str(items))
    check("live: questions and answers are in Devanagari", all(has_devanagari(i["question"]) and has_devanagari(i["answer"]) for i in items), str(items))
    q, a = items[0]["question"], items[0]["answer"]
    check("live: the right answer is judged correct", llm.judge_answer(q, a, a)["verdict"] == "correct")
    check("live: a clearly wrong answer is judged wrong", llm.judge_answer(q, a, "बिरयानी बनाने की विधि")["verdict"] == "wrong")
    check("live: 'pata nahi' is a skip", llm.judge_answer(q, a, "पता नहीं")["verdict"] == "skip")
    check("live: 'bas karo' stops the quiz", llm.judge_answer(q, a, "बस अब बंद करो")["verdict"] == "stop")
    fb = llm.judge_answer(q, a, "बिरयानी बनाने की विधि")["feedback"]
    check("live: feedback is Devanagari and never feminine toward the user", has_devanagari(fb) and "सकती हैं" not in fb, fb)

memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
