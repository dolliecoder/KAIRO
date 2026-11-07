"""Turns one transcript into an action and a spoken reply.
`confirm(prompt) -> bool` asks the user yes/no; `ask(prompt) -> str` asks a question and returns the spoken answer
(used by the quiz). Both are voice in the real app and keyboard or scripted in tests."""
from typing import Callable

from . import boost, briefing, llm, memory, quiz, recall, reminders
from .log import log

NOT_A_QUESTION = ("याद रख", "yaad rakh", "भूल जा", "bhool jao", "याद दिला", "yaad dila", "remind")


def handle(transcript: str, confirm: Callable[[str], bool], notify: Callable[[str], None] | None = None,
           ask: Callable[[str], str] | None = None) -> str:
    # Embed the question while Gemini works out the intent, but not for saves / deletes / reminders (wasted call)
    early = None if any(t in transcript.lower() for t in NOT_A_QUESTION) else memory.embed_async(transcript)
    intent = llm.parse_intent(transcript)
    kind = intent.get("intent", "other")

    if kind == "save":
        m = intent["memory"]
        if confirm(f"सेव कर दूँ? {m['devanagari']}"):
            memory.save(m["devanagari"], m["latin"], m.get("keywords", []), raw=transcript)
            log("Memory", f"saved locally in SQLite: {m['devanagari']} | {m['latin']}")
            for wrong, right in boost.learn(m.get("corrections"), transcript):
                log("Memory", f"learned: Prisma writes '{wrong}', you mean '{right}'")
            return "ठीक है, याद रख लिया।"
        return "ठीक है, सेव नहीं किया।"

    if kind in ("recall", "forget"):
        q = intent["query"]
        terms = [q["devanagari"], q["latin"], *q.get("keywords", [])]
        hits = recall.retrieve(f'{q["devanagari"]} | {q["latin"]}', terms, notify, early)
        log("Memory", f"searched Devanagari + Latin terms: {len(hits)} match(es)")
        if not hits:
            return "मुझे इसके बारे में कुछ याद नहीं है।"
        if kind == "recall":
            return llm.answer(q["devanagari"], [h[1]["devanagari"] for h in hits])
        best = hits[0][1]
        if confirm(f"ये भूल जाऊँ? {best['devanagari']}"):
            memory.delete(best["id"])
            return "भूल गई।"
        return "ठीक है, रहने दिया।"

    if kind == "remind":
        r = intent["reminder"]
        when = reminders.resolve(r, heard=transcript)
        if when is None:
            return "ये समय समझ नहीं आया या निकल चुका है, फिर से बोलो, जैसे 'कल सुबह नौ बजे'।"
        log("Echo", f"reminder: {reminders.describe(when)} -> {r['task_latin']}")
        task = r.get("task_devanagari") or r["task_latin"]
        if not confirm(f"{reminders.describe_hi(when)} {task} याद दिलाऊँ?"):
            return "ठीक है, रिमाइंडर नहीं लगाया।"
        reminders.schedule(r["task_latin"], r.get("task_devanagari", ""), when)
        return f"ठीक है, {reminders.describe_hi(when)} {task} याद दिलाऊँगी।"

    if kind == "quiz":
        if ask is None:
            return "क्विज़ सिर्फ आवाज़ वाले मोड में चलता है।"
        return quiz.run((intent.get("quiz") or {}).get("topic", ""), ask, notify or (lambda text: None))

    if kind == "briefing":
        b = intent.get("briefing") or {}
        action = b.get("action", "now")
        if action == "daily_off":
            return "ठीक है, रोज़ का प्लान बंद कर दिया।" if reminders.cancel_daily_briefing() else "रोज़ का प्लान चालू ही नहीं था।"
        if action == "daily_on":
            hour, minute = b.get("hour", 8), b.get("minute", 0)
            if not (isinstance(hour, int) and 0 <= hour <= 23 and isinstance(minute, int) and 0 <= minute <= 59):
                hour, minute = 8, 0
            when = reminders.clock_hi(hour, minute)
            if not confirm(f"रोज़ {when} आज का प्लान सुनाऊँ?"):
                return "ठीक है, रोज़ का प्लान नहीं लगाया।"
            reminders.set_daily_briefing(hour, minute)
            return f"ठीक है, रोज़ {when} आज का प्लान सुनाऊँगी।"
        return briefing.compose_now()

    return intent.get("reply") or "समझ नहीं आया, फिर से बोलो।"
