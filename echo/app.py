"""Echo voice loop: hold the hotkey, speak, release. Echo acts and answers with Timbre.
When Echo asks to confirm, hold the hotkey again and say haan / nahi."""
import asyncio
import queue
import threading

from pynput import keyboard

from . import boost, brain, reminders, tts
from .audio import Recorder
from .log import log
from .stt import transcribe

HOTKEY = keyboard.Key.ctrl_r
LANG = "hi-IN"
CONFIRM_WAIT_SECONDS = 20

YES = {"haan", "han", "ha", "yes", "yeah", "kar", "karo", "theek", "ok", "okay", "sahi", "हाँ", "हां", "हा", "यस",
       "कर", "करो", "ठीक", "सही", "ओके"}
NO = {"nahi", "nahin", "no", "mat", "ruko", "cancel", "नहीं", "नही", "ना", "मत", "रुको", "नो"}

utterances: "queue.Queue[str]" = queue.Queue()
rec = Recorder()
held = False


def say(text: str) -> None:
    log("Echo", text)
    try:
        tts.speak(text, "hi-IN")  # Devanagari text: Timbre reads Hindi and transliterated English terms correctly
    except Exception as e:
        log("Timbre", f"unavailable: {e}")


def listen_once(q) -> None:
    """Runs in a thread per key press: transcribe, then hand the text to the worker."""
    try:
        words = boost.bias_words()
        text = asyncio.run(transcribe(q, LANG, bias_words=words, rules=boost.substitution_rules()))
    except Exception as e:
        log("Prisma", f"unavailable, try again: {e}")
        text = ""
    utterances.put(text)


def is_yes(text: str) -> bool:
    words = set(text.lower().replace(",", " ").replace("।", " ").split())
    if words & NO:
        return False
    return bool(words & YES)


def confirm(prompt: str) -> bool:
    say(f"{prompt} हाँ या नहीं?")
    for _ in range(2):  # an empty transcript (too short / not heard) gets one retry
        try:
            answer = utterances.get(timeout=CONFIRM_WAIT_SECONDS)
        except queue.Empty:
            return False
        if answer:
            return is_yes(answer)
        say("सुनाई नहीं दिया, फिर से बोलो, हाँ या नहीं?")
    return False


def worker() -> None:
    while True:
        text = utterances.get()
        if not text:
            say("सुनाई नहीं दिया, फिर से बोलो।")
            continue
        try:
            say(brain.handle(text, confirm))
        except Exception as e:
            log("Echo", f"error: {e}")
            say("कुछ गड़बड़ हो गई, फिर से कोशिश करो।")


def on_press(key):
    global held
    if key == HOTKEY and not held:
        held = True
        log("Echo", "listening...")
        rec.start()
        threading.Thread(target=listen_once, args=(rec.q,), daemon=True).start()


def on_release(key):
    global held
    if key == HOTKEY and held:
        held = False
        rec.stop()


def main() -> None:
    reminders.start()
    threading.Thread(target=worker, daemon=True).start()
    print("Echo is ready. Hold RIGHT CTRL, speak, release. Ctrl+C to quit.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
