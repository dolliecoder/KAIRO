# KAIRO

**Listens. Speaks. Remembers.**
*Speak once. Remember forever. Get things done.*

KAIRO is a Hinglish voice memory for Indian students, built on Gnani AI's **Prisma** (speech recognition) and **Timbre**
(speech). Hold a key and talk the way you normally talk, in Hindi, English or a mix of both. KAIRO remembers what you
approve, answers questions about it out loud, quizzes you on your own notes, and rings spoken reminders.

**[Landing page](https://dolliecoder.github.io/KAIRO/)** | **[Download for Windows](https://github.com/dolliecoder/KAIRO/releases/latest)**

Built solo for the Great Indian AI Internship Challenge 2026 by Gnani AI.

---

## Try it in two minutes (Windows 10 / 11)

1. Download **KAIROSetup.exe** from the [latest release](https://github.com/dolliecoder/KAIRO/releases/latest) and run it.
   Your browser may say the file "isn't commonly downloaded", and Windows may show "Windows protected your PC", because the
   app is new and not code-signed. Choose **Keep**, then **More info**, then **Run anyway**.
2. On first launch, paste two API keys. KAIRO tests them for you.
   - Gnani key (speech): <https://app.gnani.ai/voice>
   - Gemini key (understanding, free tier): <https://aistudio.google.com/apikey>
3. Find the round **K** icon in the system tray, near the clock (it may be under the **^** arrow). It is **teal** when KAIRO is
   ready, **red** while it listens, **amber** while it thinks and **green** while it speaks.
4. Hold **Right Ctrl**, speak, let go, and wait about five seconds.

| Say this | What happens |
|---|---|
| "Yaad rakhna, maths mein integration ho gaya, differential equations baaki hai" | KAIRO asks "सेव कर दूँ?"; say "haan" and it is saved |
| "Maths mein kya bacha hai?" | KAIRO answers out loud from your notes |
| "Kal subah 9 baje Go assignment yaad dilana" | KAIRO reads the time back, asks to confirm, then rings a chime and speaks the reminder at 9 |
| "Maths mein quiz karo" | KAIRO asks questions from your notes, listens to your answers, and scores you |
| "Aaj ka plan batao" | KAIRO speaks today's reminders and your recent notes |
| "Bhool jao maths wali baat" | KAIRO asks, then forgets that note |

---

## What makes it different

- **Hinglish first, across scripts.** Every note is stored in Devanagari *and* Latin, and as a meaning vector, so a note saved
  as "मैथ्स" is found by saying "maths", and "workout" finds your "gym" note.
- **It learns how *you* sound.** Words from your own notes are fed back into Prisma's word boosting, and when Prisma keeps
  mishearing one of your words ("viva" written as "विवाह"), KAIRO learns a find-and-replace fix from the notes you approve.
  You can see and remove what it learned from the tray menu.
- **Self-healing recall.** If a search is not confident, KAIRO rewrites your question (synonyms, the other script) and tries
  again before giving up.
- **Your notes live on your laptop.** Notes, reminders and keys are stored locally. Speech goes to Gnani and understanding goes to
  Gemini (see [Privacy](#privacy)).

## Features

| Feature | Details |
|---|---|
| **Push-to-talk** | Global hotkey (Right Ctrl), live streaming recognition, spoken replies, a tray icon showing what KAIRO is doing |
| **Approval-based memory** | Nothing is saved or deleted until you say "haan". An unclear answer is asked again, never guessed as "no" |
| **Reminders** | Natural Hinglish times ("1:10", "saade nau", "5 minute baad", "friday 4 pm"), time read back for confirmation, chime plus spoken alarm, survives restarts |
| **Voice quiz** | Up to three questions written from your notes, spoken answers judged by meaning (different words are fine), "bas" to stop |
| **Day's plan** | On demand, or every day at a time you choose; falls back to a plain version if Gemini is down |
| **Notes from a PDF** | Tray menu, then **Add notes from a PDF...**. Typed or scanned, Hindi or English, up to 15 MB. You tick the notes to keep. A sample PDF is in `assets/demo/` |
| **What KAIRO learned** | Tray menu window listing the word hints and learned corrections, with a button to remove a wrong one |
| **Stop and start** | Right-click the K, **Quit KAIRO**, or use the Start-menu shortcuts. One copy runs at a time |

---

## How Gnani's models are used

| Model | How KAIRO uses it |
|---|---|
| **Prisma** real-time STT (`wss://api.vachana.ai/stt/v3/stream`) | Streams your voice as 16 kHz mono PCM in 1,024-byte frames while you hold the key. 300 ms silence detection. Up to 100 **word-boost** words built from your own notes. Up to 10 **find-and-replace rules** learned from mishearings. An empty result is retried once. |
| **Timbre** TTS (`/api/v1/tts/inference`, `timbre-v3.0`, voice Shivani, `hi-IN`) | Speaks every answer, confirmation, quiz question, plan and reminder alarm in Devanagari. Fixed phrases ship pre-generated inside the installer, and all Timbre calls go through one lock because Timbre allows one active request. |

**Google Gemini** (free tier, not a Gnani model) is used to understand what you meant, write short answers from your notes,
write and judge quiz questions, compose the day's plan, and read PDFs. It is called through a chain of models: if one is slow
a second is asked in parallel, and if one runs out of its per-minute quota the next takes over.

## How it works

```
 hold Right Ctrl ──> microphone ──> Prisma (Gnani) ──> your words as text
                                        ^                      |
              word hints + learned fixes |                      v
              (built from your notes)    |      Gemini: what did you mean?
                                         |      save | ask | remind | quiz | plan
                                         |                      |
                     SQLite + sqlite-vec (notes, meaning search) + APScheduler (reminders)   <- all on your laptop
                                                                |
                                                                v
                                            Timbre (Gnani) ──> your speakers
```

## Privacy

- **Stays on your computer:** your notes, reminders, keys and the learned word list, in `%APPDATA%\KAIRO`. KAIRO has no server.
- **Sent to Gnani:** your voice while you hold the key (Prisma), and the text KAIRO speaks (Timbre).
- **Sent to Google Gemini:** the text of what you said, plus the few matching notes, to understand and answer. The quiz and the
  day's plan also send your notes and reminders for that purpose, and a PDF you choose to import is sent to be read.

The demo uses made-up data only.

## Stop and start again

- **Stop:** right-click the round **K** in the system tray and choose **Quit KAIRO**, or click **Quit KAIRO** in the Start menu.
- **Start again:** Start menu, **KAIRO** (or the desktop shortcut). Your keys, notes and reminders are kept; you never install it again.
- To change a key: delete `%APPDATA%\KAIRO\.env` and start KAIRO; the key window comes back.

## Known limits

- **Windows only**, and it needs two API keys of your own. The installer is not code-signed, so Windows shows a warning.
- **A reply takes about 5 to 7 seconds** (recognition, understanding, then speech). Gemini's free tier allows 15 requests per
  minute per model, so very heavy use can slow down.
- **Recognition is not perfect.** Prisma sometimes mishears a word or returns nothing; KAIRO retries, asks again on unclear
  yes/no answers, and learns fixes, but it cannot remove every miss.
- **The quiz asks at most three questions** at a time, and a PDF becomes at most 12 notes. Formulas are described in words, not symbols.
- **Not tested on other machines yet,** and it is not designed for noisy rooms.

---

## For developers

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env      # then fill in GNANI_API_KEY and GEMINI_API_KEY
.venv\Scripts\python -m echo.app
```

(The Python package is still called `echo`, which was the project's first name.)

Tests need no microphone. Those marked * call the real services.

| Command | Checks |
|---|---|
| `python -m tests.test_resolve` | reminder time logic, 20 cases |
| `python -m tests.test_answers` | every spelling of a spoken yes or no, and the confirmation flow |
| `python -m tests.test_intents` | save / remind / recall / forget / quiz / plan routing, 3 runs each * |
| `python -m tests.test_crossscript` | 12 cross-script and meaning recall cases * |
| `python -m tests.test_selfheal` | rewrite-and-retry recall * |
| `python -m tests.test_quiz --live` | quiz flow (17 checks) and real Gemini questions and judging * |
| `python -m tests.test_briefing --live` | day's plan, daily schedule, and a real Gemini plan * |
| `python -m tests.test_pdfnotes --live`, `test_importer` | notes from a PDF: checks, saving, the window; real Gemini reading typed and scanned PDFs * |
| `python -m tests.test_brain_new`, `test_learned`, `test_replies --live` | brain wiring, the learned window, reply wording and gender-neutral address * |
| `python -m tests.test_single_instance`, `test_quit_before_ready`, `test_tray` | one copy at a time, `--quit`, tray menu |
| `python -m tests.test_tts_cache`, `test_llm_hedge`, `test_llm_connection`, `test_llm_cooldown`, `test_boost_rules` | voice cache, Gemini racing and recovery, word-boost rules |
| `python -m scripts.e2e_voice` | the whole flow with a synthesized "user" voice through real Prisma, Gemini and Timbre * |
| `python -m echo.app --selftest-live` | the installed app checking every component against Gnani and Gemini * |

Build the Windows app and installer (Inno Setup 6 is needed for the installer):

```
build_app.bat                      # -> dist\KAIRO\KAIRO.exe
dist\KAIRO\KAIRO.exe --selftest    # checks every bundled component
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\kairo.iss   # -> release\KAIROSetup.exe
```

### Layout

```
echo/
  app.py        hotkey, tray and main voice loop         answers.py   spoken yes / no, every spelling
  setup.py      first-run key window                     stt.py       Prisma real-time WebSocket client
  tts.py        Timbre client, cache, one-at-a-time      llm.py       Gemini (racing, fallback), intent parsing
  brain.py      transcript -> save / forget / recall / remind / quiz / plan
  memory.py     SQLite + sqlite-vec, dual-script search  recall.py    hybrid search + self-healing rewrite
  reminders.py  APScheduler, persistent job store        boost.py     notes -> Prisma boost words and fixes
  quiz.py  briefing.py  learned.py                       voice quiz, the day's plan, the "learned" window
  pdfnotes.py  importer.py                               notes from a PDF, and its window
  single.py     one copy at a time, --quit               tray.py  sounds.py  audio.py  paths.py  log.py  selftest.py
installer/      Inno Setup script          docs/      landing page (GitHub Pages)
scripts/        probes, experiments, end-to-end run      tests/     see above
assets/         icon, pre-generated voice phrases, demo PDF
```

### Notes from building it

- Prisma needs exactly 1,024-byte PCM frames and has no end-of-stream message, so after you release the key a short silence
  tail closes the segment. 300 ms silence detection is about 0.4 s faster than the 500 ms default with identical text.
- Prisma writes the same spoken "haan" several ways (हाँ, हां, हान...). Matching a fixed list broke confirmations for some
  voices, found by the end-to-end run with a synthesized voice, so yes/no is matched by pattern and unclear answers are asked again.
- One invalid word makes Prisma reject the whole boost list, so every word is checked first.
- Boosting cannot beat Prisma's prior for some real words ("viva" vs "विवाह"); find-and-replace rules fix those. A learned
  rule rewrites that word everywhere, which is a deliberate trade-off.
- Timbre allows one active request, so a burst of first-launch calls collided with the user's first question; the fixed phrases
  now ship pre-generated and all calls are serialized.
- Timbre streaming (SSE) gave no faster first audio than the plain call, so KAIRO uses the plain call plus a phrase cache.
- Gemini's free tier allows 15 requests per minute per model and sometimes takes 3 to 8 seconds, so slow calls are raced against
  the next model and a quota hit puts a model on a cooldown that follows Google's own retry time.
- Timbre with `container: "mp3"` plus bitrate or sample rate returns HTTP 500, so KAIRO uses WAV.

## Credits

Speech recognition and speech by [Gnani AI](https://gnani.ai) (Prisma, Timbre). Built for the Great Indian AI Internship Challenge 2026.
