# Echo

**Speak once. Remember forever. Get things done.**

Echo is a Hinglish voice memory for Indian students. Hold a hotkey, speak in Hindi, Hinglish or English, and Echo
remembers what you approve, answers questions about it out loud, and speaks reminders when they are due.

Built for the Gnani AI Great Indian AI Internship Challenge 2026.

## Gnani models used

| Model | Used for |
|---|---|
| **Prisma** (real-time STT, `wss://api.vachana.ai/stt/v3/stream`) | Hinglish speech recognition, with word boosting fed from your own memories |
| **Timbre** (TTS, `/api/v1/tts/inference`) | Spoken replies, confirmations and reminder alarms |

## What it does

- **Push-to-talk.** Hold Right Ctrl, speak, release.
- **Approval-based memory.** "Yaad rakhna ..." saves (after a spoken haan/nahi), "bhool jao ..." deletes, and questions
  like "maths mein kya bacha hai?" recall.
- **Cross-script recall.** Every memory is stored in Devanagari and Latin, so a Devanagari memory is found by a Latin
  query and the other way round.
- **Reminders.** "Kal subah 9 baje Go assignment yaad dilana" plays a chime and speaks the reminder. Reminders survive
  restarts, and ones missed while Echo was closed are spoken on the next start.
- **Recognition that learns you.** Words from approved memories (in Prisma's own spelling) go into Prisma word boosting.
- **Local-first.** Memories and reminders live in SQLite on your laptop.

## Setup

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env      # then fill in GNANI_API_KEY and GEMINI_API_KEY
.venv\Scripts\python -m echo.app
```

Keys: Gnani at https://app.gnani.ai/voice, Gemini (free tier) at https://aistudio.google.com/apikey.

## Layout

```
echo/
  app.py        hotkey + main voice loop
  audio.py      microphone capture (1,024-byte PCM frames)
  stt.py        Prisma real-time WebSocket client
  tts.py        Timbre client and serialized playback
  sounds.py     synthesized alarm chime
  llm.py        Gemini intent parsing (with model fallback)
  brain.py      transcript -> save / forget / recall / remind
  memory.py     SQLite store, dual-script search
  reminders.py  APScheduler with persistent job store
  boost.py      memory -> Prisma word-boost list
scripts/        test and probe scripts (test_tts, ptt_loop, test_brain, test_boost, ...)
```

## Notes from building it

- Prisma needs exactly 1,024-byte PCM frames at real-time pace and has no end-of-stream message, so after you release
  the key Echo streams a short silence tail to close the VAD segment.
- One invalid word makes Prisma reject the whole word-boost list, so every word is sanitized first.
- Timbre with `container: "mp3"` plus bitrate or sample rate returns HTTP 500, so Echo uses WAV.

## Data

Synthetic data only. No real phone numbers, IDs or recorded calls are used.
