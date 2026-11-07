"""KAIRO voice loop: hold the hotkey, speak, release. KAIRO acts and answers with Timbre.
When KAIRO asks to confirm, hold the hotkey again and say haan / nahi.
Runs with a tray icon (right-click -> Quit KAIRO); `--no-tray` runs in the console only."""
import asyncio
import queue
import signal
import sys
import threading

from . import setup as _setup

_setup.ensure_keys()  # first run: ask for the two keys before anything that needs them is imported

from pynput import keyboard  # noqa: E402

from . import boost, brain, reminders, sounds, tts
from .answers import answer_of, is_yes  # noqa: F401  (is_yes is also used by scripts)
from .audio import Recorder
from .log import log
from .stt import transcribe

HOTKEY = keyboard.Key.ctrl_r
LANG = "hi-IN"
CONFIRM_WAIT_SECONDS = 20
ANSWER_WAIT_SECONDS = 45  # a quiz answer can take longer than haan / nahi

utterances: "queue.Queue[str]" = queue.Queue()
rec = Recorder()
held = False
tray = None  # set in main(); None when running with --no-tray


def set_state(state: str) -> None:
    if tray:
        tray.set_state(state)


def say(text: str) -> None:
    log("Echo", text)
    set_state("speaking")
    try:
        tts.speak(text, "hi-IN")  # Devanagari text: Timbre reads Hindi and transliterated English terms correctly
    except Exception as e:
        log("Timbre", f"unavailable: {e}")
    finally:
        set_state("idle")


def listen_once(q) -> None:
    """Runs in a thread per key press: transcribe, then hand the text to the worker."""
    try:
        words = boost.bias_words()
        text = asyncio.run(transcribe(q, LANG, bias_words=words, rules=boost.substitution_rules()))
    except Exception as e:
        log("Prisma", f"unavailable, try again: {e}")
        text = ""
    utterances.put(text)


def confirm(prompt: str) -> bool:
    say(prompt)
    say("हाँ या नहीं?")  # cached phrase: plays instantly
    for _ in range(3):  # not heard, or neither yes nor no: ask again (up to twice) instead of guessing "no"
        try:
            answer = utterances.get(timeout=CONFIRM_WAIT_SECONDS)
        except queue.Empty:
            return False
        verdict = answer_of(answer) if answer else "unknown"
        if verdict != "unknown":
            return verdict == "yes"
        say("सुनाई नहीं दिया, फिर से बोलो, हाँ या नहीं?")  # cached phrase
    return False


def ask(prompt: str) -> str:
    """Speak a prompt, then wait for the user's next utterance (hold the hotkey and answer). "" if nothing was heard."""
    say(prompt)
    for _ in range(2):  # an empty transcript gets one retry
        try:
            answer = utterances.get(timeout=ANSWER_WAIT_SECONDS)
        except queue.Empty:
            return ""
        if answer:
            return answer
        say("सुनाई नहीं दिया, फिर से बोलो।")
    return ""


def worker() -> None:
    while True:
        text = utterances.get()
        if not text:
            say("सुनाई नहीं दिया, फिर से बोलो।")
            continue
        try:
            say(brain.handle(text, confirm, notify=say, ask=ask))
        except Exception as e:
            log("Echo", f"error: {e}")
            say("कुछ गड़बड़ हो गई, फिर से कोशिश करो।")


def on_press(key):
    global held
    if key == HOTKEY and not held:
        held = True
        log("Echo", "listening...")
        set_state("listening")
        rec.start()
        threading.Thread(target=listen_once, args=(rec.q,), daemon=True).start()


def on_release(key):
    global held
    if key == HOTKEY and held:
        held = False
        rec.stop()
        set_state("thinking")
        threading.Thread(target=sounds.tick, daemon=True).start()  # instant 'heard you' cue


def main() -> None:
    global tray
    if any(a.startswith("--selftest") for a in sys.argv):  # verify the packaged app: KAIRO.exe --selftest[-live]
        from .selftest import run, run_live
        sys.exit(run_live() if "--selftest-live" in sys.argv else run())
    if "--learned" in sys.argv:  # the tray's "What KAIRO learned" item runs this as its own window process
        from .learned import show
        show()
        return
    reminders.start()
    tts.prewarm()
    threading.Thread(target=worker, daemon=True).start()
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    if "--no-tray" in sys.argv:
        print("KAIRO is ready. Hold RIGHT CTRL, speak, release. Ctrl+C to quit.")
        from . import single
        single.watch_for_quit(listener.stop)  # `--quit` from another process ends listener.join() below
        listener.join()
        return

    from .tray import Tray  # imported here so --no-tray works even if pystray is missing
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Ctrl+C must still stop KAIRO while the tray loop blocks
    tray = Tray(on_quit=listener.stop)
    from . import single
    single.watch_for_quit(tray.stop)  # the Start-menu "Quit KAIRO" shortcut runs `KAIRO.exe --quit`
    log("Echo", "ready - tray icon is running. Hold RIGHT CTRL, speak, release. Right-click the tray icon to quit.")
    tray.run()  # blocks until "Quit KAIRO"
    listener.stop()
    reminders.start().shutdown()


if __name__ == "__main__":
    from . import single

    single.guard()
    main()
