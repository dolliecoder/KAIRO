"""Voice quiz: KAIRO asks questions made from your own notes, you answer out loud, and she checks each answer.
Prisma hears the answers, Timbre speaks the questions and the feedback, Gemini writes and judges them.

`ask(prompt) -> str` speaks a prompt and returns what the user said ("" if nothing was heard).
`say(text)` speaks a line without waiting for an answer."""
import random
from typing import Callable

from . import llm, memory
from .log import log
from .reminders import HI_NUM

MAX_QUESTIONS = 3
NEWEST_POOL = 10  # questions come from your most recent notes unless you name a topic

NO_NOTES = "अभी मेरे पास कोई नोट्स नहीं हैं, पहले कुछ याद रखवाओ।"
START = "ठीक है, क्विज़ शुरू करते हैं।"
NOT_READY = "अभी सवाल नहीं बना पाई, थोड़ी देर बाद कोशिश करो।"


def pick_notes(topic: str, count: int = MAX_QUESTIONS) -> list[dict]:
    """Notes about the topic (keyword + meaning search); if none match, or no topic, a random few of the newest."""
    pool: dict[int, dict] = {}
    if topic.strip():
        for _, m in [*memory.search([topic]), *memory.search_semantic(topic)]:
            pool.setdefault(m["id"], m)
    notes = list(pool.values()) or sorted(memory.all_memories(), key=lambda m: -m["created"])[:NEWEST_POOL]
    return random.sample(notes, min(count, len(notes)))


def _summary(score: int, asked: int) -> str:
    if asked == 0:
        return "ठीक है, क्विज़ यहीं रोकते हैं।"
    if score == asked:
        return f"शाबाश! {HI_NUM[asked]} में से {HI_NUM[score]} सही।"
    if score == 0:
        return "कोई बात नहीं! एक बार दोहराकर फिर से क्विज़ करते हैं।"
    return f"क्विज़ पूरा हुआ। {HI_NUM[asked]} में से {HI_NUM[score]} सही। थोड़ा और दोहराओ, फिर से क्विज़ कर सकते हैं।"


def run(topic: str, ask: Callable[[str], str], say: Callable[[str], None]) -> str:
    """Runs the whole quiz and returns the closing sentence for the caller to speak."""
    notes = pick_notes(topic or "")
    if not notes:
        return NO_NOTES
    say(START)
    try:
        items = llm.make_quiz([n["devanagari"] for n in notes])[:MAX_QUESTIONS]
    except Exception as e:  # Gemini down or out of quota: say so instead of crashing the voice loop
        log("Gemini", f"could not write quiz questions: {str(e)[:100]}")
        return NOT_READY
    if not items:
        return NOT_READY

    score = asked = 0
    for number, item in enumerate(items, 1):
        heard = ask(f"सवाल {HI_NUM[number]}। {item['question']}")
        if not heard.strip():  # nothing heard: treat as a skip, no Gemini call needed
            asked += 1
            say(f"कोई बात नहीं, सही जवाब है: {item['answer']}।")
            continue
        try:
            judged = llm.judge_answer(item["question"], item["answer"], heard)
        except Exception as e:
            log("Gemini", f"could not judge the answer: {str(e)[:100]}")
            judged = {"verdict": "wrong", "feedback": ""}
        verdict, feedback = judged["verdict"], judged["feedback"]
        log("Echo", f"quiz question {number}: {verdict}")
        if verdict == "stop":
            say(feedback or "ठीक है, क्विज़ यहीं रोकते हैं।")
            break
        asked += 1
        if verdict == "correct":
            score += 1
            say(feedback or "बिल्कुल सही!")
        else:
            say(feedback or f"सही जवाब है: {item['answer']}।")
    log("Echo", f"quiz finished: {score} of {asked}")
    return _summary(score, asked)
