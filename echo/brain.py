"""Turns one transcript into an action and a spoken reply.
`confirm(prompt) -> bool` asks the user yes/no (voice in the real app, keyboard in tests)."""
from typing import Callable

from . import llm, memory, reminders


def handle(transcript: str, confirm: Callable[[str], bool]) -> str:
    intent = llm.parse_intent(transcript)
    kind = intent.get("intent", "other")

    if kind == "save":
        m = intent["memory"]
        if confirm(f"Save kar doon? {m['latin']}"):
            memory.save(m["devanagari"], m["latin"], m.get("keywords", []), raw=transcript)
            return "Theek hai, yaad rakh liya."
        return "Okay, save nahi kiya."

    if kind in ("recall", "forget"):
        q = intent["query"]
        terms = [q["devanagari"], q["latin"], *q.get("keywords", [])]
        hits = memory.search(terms)
        if not hits:
            return "Mujhe iske baare mein kuch yaad nahi hai."
        if kind == "recall":
            return llm.answer(q["latin"], [h[1]["latin"] for h in hits])
        best = hits[0][1]
        if confirm(f"Ye bhool jaoon? {best['latin']}"):
            memory.delete(best["id"])
            return "Bhool gaya."
        return "Okay, rehne diya."

    if kind == "remind":
        r = intent["reminder"]
        when = reminders.parse_when(r.get("when_iso", ""))
        if when is None:
            return "Reminder ka time samajh nahi aaya, phir se bolo, jaise 'kal subah 9 baje'."
        reminders.schedule(r["task_latin"], r.get("task_devanagari", ""), when)
        return f"Theek hai, {reminders.describe(when)} yaad dilaunga: {r['task_latin']}."

    return intent.get("reply", "Samajh nahi aaya, phir se bolo.")
