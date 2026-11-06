# KAIRO

**Speak once. Remember forever. Get things done.**

KAIRO is a Hinglish voice memory for Indian students. Hold a key, speak in Hindi, Hinglish or English, and KAIRO
remembers what you approve, answers questions about it out loud, and rings spoken reminders when they are due.

Built solo for the Gnani AI Great Indian AI Internship Challenge 2026.

## Install (Windows 10 / 11)

1. Download **KAIROSetup.exe** from the [latest release](https://github.com/dolliecoder/KAIRO/releases/latest) and run it.
   Windows may show "Windows protected your PC" because the app is new and not code-signed:
   click **More info**, then **Run anyway**.
2. On first launch, paste two API keys. KAIRO tests them for you.
   - Gnani key (speech): <https://app.gnani.ai/voice>
   - Gemini key (understanding, free tier): <https://aistudio.google.com/apikey>
3. Look for the round pink **K** in the system tray (it may be under the **^** arrow). Hold **Right Ctrl**, speak, let go.

Try: "Yaad rakhna, maths mein integration ho gaya." then later "Maths mein kya bacha hai?" and
"Kal subah 9 baje Go assignment yaad dilana."

## Gnani models used

| Model | Used for |
|---|---|
| **Prisma** (real-time STT, `wss://api.vachana.ai/stt/v3/stream`) | Hinglish speech recognition, with word boosting and find-and-replace rules learned from your own memories |
| **Timbre** (TTS, `/api/v1/tts/inference`) | Every spoken answer, confirmation and reminder alarm |

Google Gemini is used only to understand what you meant and to write short answers from your own notes.

## What it does

- **Push-to-talk.** Hold Right Ctrl, speak, release. A tray icon shows what KAIRO is doing.
- **Approval-based memory.** "Yaad rakhna ..." saves (after a spoken haan/nahi), "bhool jao ..." deletes, and questions recall.
- **Cross-script and meaning search.** Every memory is stored in Devanagari and Latin and as a vector (sqlite-vec),
  so "maths" finds "मैथ्स", and "workout" finds "gym".
- **Self-healing recall.** If the first search is not confident, Gemini rewrites the question (synonyms, other script) and retries.
- **Reminders.** "Kal subah 9 baje ... yaad dilana" reads the time back, asks for confirmation, and rings a chime plus a
  spoken reminder. Reminders survive restarts; ones missed while KAIRO was closed are spoken on the next start.
- **Recognition that learns you.** Words from your memories go into Prisma word boosting, and corrections for words Prisma
  keeps mishearing (e.g. "viva" heard as "विवाह") are learned from memories you approve.

## What stays on your computer, and what doesn't

- **Stays local:** memories, reminders, keys, learned word list (in `%APPDATA%\KAIRO`).
- **Sent to Gnani:** your voice while you hold the key (Prisma) and the text KAIRO speaks (Timbre).
- **Sent to Google Gemini:** the text of what you said, plus the few matching notes, to understand and answer.

Synthetic data only is used in the demo.

## For developers

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env      # then fill in GNANI_API_KEY and GEMINI_API_KEY
.venv\Scripts\python -m echo.app
```

(The Python package is still called `echo`, which was the project's first name.)

Tests (no microphone needed; the ones marked * call the real services):

| Command | Checks |
|---|---|
| `python -m tests.test_resolve` | reminder time logic, 20 cases |
| `python -m tests.test_boost_rules` | boost words and learned corrections |
| `python -m tests.test_replies --live` | Devanagari, feminine, gender-neutral-to-user replies * |
| `python -m tests.test_intents` | save / remind / recall / forget routing * |
| `python -m tests.test_crossscript` | 12 cross-script and meaning recall cases * |
| `python -m tests.test_selfheal` | rewrite-and-retry recall * |
| `python -m echo.app --selftest-live` | whole pipeline against Gnani and Gemini * |

Build the Windows app and installer (Inno Setup 6 required for the installer):

```
build_app.bat                      # -> dist\KAIRO\KAIRO.exe
dist\KAIRO\KAIRO.exe --selftest    # checks every bundled component
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\kairo.iss   # -> release\KAIROSetup.exe
```

## Layout

```
echo/
  app.py        hotkey, tray and main voice loop
  setup.py      first-run key window
  stt.py        Prisma real-time WebSocket client
  tts.py        Timbre client, disk cache, serialized playback
  llm.py        Gemini (model fallback), intent parsing
  brain.py      transcript -> save / forget / recall / remind
  memory.py     SQLite + sqlite-vec, dual-script search
  recall.py     hybrid search + self-healing rewrite
  reminders.py  APScheduler with persistent job store
  boost.py      memory -> Prisma boost words and corrections
  tray.py  sounds.py  audio.py  paths.py  log.py  selftest.py
installer/      Inno Setup script
docs/           landing page (GitHub Pages)
scripts/        probes and experiments (latency, boost, TTS streaming, ...)
tests/          see above
```

## Notes from building it

- Prisma needs exactly 1,024-byte PCM frames and has no end-of-stream message, so after you release the key a short silence
  tail closes the segment. 300 ms silence is about 0.4 s faster than the 500 ms default with identical text.
- Prisma sometimes returns no transcript for a clear utterance (about 8% of synthetic runs), so an empty result is retried once.
- One invalid word makes Prisma reject the whole boost list, so every word is checked first.
- Boosting cannot beat Prisma's prior for some real words ("viva" vs "विवाह"); find-and-replace rules fix those. A learned
  rule rewrites that word everywhere, which is a deliberate trade-off.
- Timbre streaming (SSE) gave no faster first audio than the plain call, so KAIRO uses the plain call plus a phrase cache.
- Timbre with `container: "mp3"` plus bitrate or sample rate returns HTTP 500, so KAIRO uses WAV.
