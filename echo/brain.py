"""Turns one transcript into an action and a spoken reply.
`confirm(prompt) -> bool` asks the user yes/no (voice in the real app, keyboard in tests)."""
from typing import Callable

from . import boost, llm, memory, recall, reminders
from .log import log


def handle(transcript: str, confirm: Callable[[str], bool], notify: Callable[[str], None] | None = None) -> str:
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
        hits = recall.retrieve(f'{q["devanagari"]} | {q["latin"]}', terms, notify)
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

    return intent.get("reply") or "समझ नहीं आया, फिर से बोलो।"
