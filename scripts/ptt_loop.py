"""Step 2: hold Right Ctrl, speak, release. Echo prints what Prisma heard and repeats it via Timbre."""
import asyncio
import threading

from pynput import keyboard

from echo import tts
from echo.audio import Recorder
from echo.stt import transcribe

HOTKEY = keyboard.Key.ctrl_r  # right Ctrl; laptop F-keys often need Fn
LANG = "hi-IN"  # hi-IN = Devanagari output; en-IN = Latin output

rec = Recorder()
held = False


def handle_utterance(q):
    try:
        text = asyncio.run(transcribe(q, LANG))
    except Exception as e:
        print(f"[Prisma unavailable, try again] {e}")
        return
    print(f"Heard: {text!r}")
    if text:
        tts.speak(f"Maine suna: {text}")


def on_press(key):
    global held
    if key == HOTKEY and not held:
        held = True
        print("Listening...")
        rec.start()
        threading.Thread(target=handle_utterance, args=(rec.q,), daemon=True).start()


def on_release(key):
    global held
    if key == HOTKEY and held:
        held = False
        rec.stop()


print("Hold RIGHT CTRL to talk. Ctrl+C to quit.")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
