"""`Echo.exe --selftest`: checks that every component works inside the packaged app (no keys, no network).
Prints PASS/FAIL per check and exits non-zero on failure. Output goes to the log file when there is no console."""
import os
import sys
import tempfile
import time
from pathlib import Path


def run() -> int:
    results = []

    def check(name, fn):
        try:
            detail = fn()
            results.append((name, True, detail or ""))
        except Exception as e:  # report every failure, do not stop at the first
            results.append((name, False, f"{type(e).__name__}: {e}"))

    def sqlite_vec_loads():
        import sqlite3

        import sqlite_vec
        db = sqlite3.connect(":memory:")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        return "sqlite-vec " + db.execute("select vec_version()").fetchone()[0]

    def vector_roundtrip():
        import sqlite3

        import sqlite_vec
        db = sqlite3.connect(":memory:")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.execute("create virtual table v using vec0(embedding float[4])")
        db.execute("insert into v(rowid, embedding) values (1, ?)", (sqlite_vec.serialize_float32([1, 0, 0, 0]),))
        row = db.execute("select rowid from v where embedding match ? and k = 1",
                         (sqlite_vec.serialize_float32([1, 0, 0, 0]),)).fetchone()
        assert row[0] == 1
        return "vector insert + nearest-neighbour query"

    def audio_devices():
        import sounddevice as sd
        devs = sd.query_devices()
        ins = [d for d in devs if d["max_input_channels"] > 0]
        outs = [d for d in devs if d["max_output_channels"] > 0]
        assert ins and outs, f"{len(ins)} input / {len(outs)} output devices"
        return f"{len(ins)} input, {len(outs)} output devices"

    def hotkey_hook():
        from pynput import keyboard
        listener = keyboard.Listener(on_press=lambda k: None)
        listener.start()
        time.sleep(0.3)
        ok = listener.running
        listener.stop()
        assert ok, "listener did not start"
        return "global keyboard listener starts and stops"

    def tray_icon():
        from .tray import Tray
        Tray(on_quit=lambda: None)
        return "tray icon builds"

    def scheduler_jobstore():
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from apscheduler.schedulers.background import BackgroundScheduler
        from datetime import datetime, timedelta

        from . import reminders
        path = Path(tempfile.mkdtemp()) / "jobs.db"
        s = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{path}")}, timezone=reminders.IST)
        s.start()
        s.add_job(reminders.fire, "date", run_date=datetime.now(reminders.IST) + timedelta(days=1), args=["x", "x"])
        n = len(s.get_jobs())
        s.shutdown()
        assert n == 1
        return "persistent job store works"

    def timezone_data():
        from zoneinfo import ZoneInfo
        ZoneInfo("Asia/Kolkata")
        return "Asia/Kolkata time zone data present"

    def reminder_time_resolution():
        from datetime import datetime

        from .reminders import IST, resolve
        now = datetime(2026, 11, 7, 1, 13, tzinfo=IST)
        got = resolve({"day": "", "hour": 1, "minute": 10, "period": "", "in_minutes": 0}, now)
        assert got == datetime(2026, 11, 7, 13, 10, tzinfo=IST), got
        return "'1:10' at 01:13 -> 13:10"

    def window_toolkit():
        import tkinter
        tkinter.Tcl()
        return "tkinter available"

    def network_libs():
        import google.genai  # noqa: F401
        import requests  # noqa: F401
        import websockets  # noqa: F401
        return "google-genai, requests, websockets import"

    def data_folder_writable():
        from .paths import DATA_DIR
        probe = DATA_DIR / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return f"writable: {DATA_DIR}"

    check("sqlite-vec extension loads", sqlite_vec_loads)
    check("vector insert and search", vector_roundtrip)
    check("audio input and output devices", audio_devices)
    check("global hotkey hook", hotkey_hook)
    check("tray icon", tray_icon)
    check("reminder scheduler (persistent)", scheduler_jobstore)
    check("time zone data", timezone_data)
    check("reminder time logic", reminder_time_resolution)
    check("setup window toolkit (tkinter)", window_toolkit)
    check("network libraries", network_libs)
    check("data folder", data_folder_writable)

    failed = 0
    print(f"Echo self-test ({'packaged app' if getattr(sys, 'frozen', False) else 'source'})")
    for name, ok, detail in results:
        failed += not ok
        print(("PASS  " if ok else "FAIL  ") + name + (f"  -  {detail}" if detail else ""))
    print(f"\n{len(results) - failed}/{len(results)} passed", flush=True)
    return 1 if failed else 0


def run_live() -> int:
    """`Echo.exe --selftest-live`: the same checks against the REAL services (needs keys in the data folder).
    Proves HTTPS, WebSockets, Gemini, Timbre and Prisma all work from inside the packaged app."""
    import asyncio
    import queue
    import threading

    results = []

    def check(name, fn):
        t0 = time.time()
        try:
            detail = fn()
            results.append((name, True, f"{detail} ({time.time() - t0:.1f}s)"))
        except Exception as e:
            results.append((name, False, f"{type(e).__name__}: {e}"))

    from . import setup
    keys = setup.saved_keys()
    if not (keys["GNANI_API_KEY"] and keys["GEMINI_API_KEY"]):
        print("FAIL  no keys found in the data folder - run Echo once, or set ECHO_HOME to a folder with a .env")
        return 1

    def gnani_key():
        problem = setup.test_gnani(keys["GNANI_API_KEY"])
        assert problem is None, problem
        return "Prisma accepted the key (WebSocket + TLS)"

    def gemini_key():
        problem = setup.test_gemini(keys["GEMINI_API_KEY"])
        assert problem is None, problem
        return "Gemini accepted the key (HTTPS)"

    def intent():
        from . import llm
        out = llm.parse_intent("याद रखना कल जिम जाना है")
        assert out.get("intent") == "save", out  # "याद रखना" always means save, even with a day in the sentence
        return "understood a Hindi save request"

    def embeddings():
        from . import embed
        v = embed.embed(["नमस्ते"])[0]
        assert len(v) == embed.DIM
        return f"{len(v)}-number vector"

    wav_holder = {}

    def timbre():
        from . import tts
        wav = tts.synthesize("नमस्ते, मैं इको हूँ।", "hi-IN")
        assert wav[:4] == b"RIFF", wav[:8]
        wav_holder["wav"] = wav
        return f"{len(wav) // 1024} KB of audio"

    def prisma_on_timbre_audio():
        import io
        import wave

        import numpy as np

        from . import config
        from .stt import transcribe
        with wave.open(io.BytesIO(wav_holder["wav"])) as w:
            rate, pcm = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        n = int(len(pcm) * config.SAMPLE_RATE / rate)
        pcm16 = np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm).astype(np.int16).tobytes()
        pcm16 += bytes(-len(pcm16) % config.FRAME_BYTES)
        frames = [pcm16[k:k + config.FRAME_BYTES] for k in range(0, len(pcm16), config.FRAME_BYTES)]
        q: queue.Queue = queue.Queue()

        def feed():
            for f in frames:
                q.put(f)
                time.sleep(config.FRAME_SECONDS)
            q.put(None)
        threading.Thread(target=feed, daemon=True).start()
        text = asyncio.run(transcribe(q, "hi-IN"))
        assert text, "Prisma returned no text"
        return f"Prisma heard: {text}"

    def save_and_recall():
        from . import brain, memory, reminders
        tmp = Path(tempfile.mkdtemp())
        memory.DB_PATH = tmp / "selftest.db"
        reminders.JOBS_DB = tmp / "jobs.db"
        memory._db = None
        brain.handle("याद रखना कल ओजेटी का वायवा है", lambda p: True)
        reply = brain.handle("वायवा कब है", lambda p: True)
        assert "वायवा" in reply, reply
        memory._db.close()
        return f"saved, then recalled: {reply}"

    check("Gnani key (Prisma WebSocket)", gnani_key)
    check("Gemini key (HTTPS)", gemini_key)
    check("Gemini understands a Hindi sentence", intent)
    check("Gemini embeddings", embeddings)
    check("Timbre speaks (Gnani TTS)", timbre)
    check("Prisma transcribes that audio (Gnani STT)", prisma_on_timbre_audio)
    check("save then recall (whole brain)", save_and_recall)

    failed = sum(not ok for _, ok, _ in results)
    print(f"Echo LIVE self-test ({'packaged app' if getattr(sys, 'frozen', False) else 'source'})")
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name + (f"  -  {detail}" if detail else ""))
    print(f"\n{len(results) - failed}/{len(results)} passed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_live() if "--selftest-live" in sys.argv else run())
