"""Timbre synthesis time by text length, sample rate and model. Bypasses the disk cache."""
import statistics
import sys
import time

from echo import config, tts

sys.stdout.reconfigure(encoding="utf-8")
TEXTS = {"short (22 chars)": "ठीक है, याद रख लिया।", "medium (45 chars)": "मैथ्स में डिफरेंशियल इक्वेशंस बाकी हैं, इंटीग्रेशन हो गया।",
         "long (95 chars)": "कल सुबह नौ बजे गो असाइनमेंट याद दिलाऊँगी, और शुक्रवार तक डेटाबेस का असाइनमेंट जमा करना है, याद रखना।"}


def timed(text, rate):
    t0 = time.time()
    body_rate = {"sample_rate": rate, "container": "wav"}
    import requests
    r = requests.post(config.TTS_URL, json={"text": text, "voice": config.TIMBRE_VOICE, "model": config.TIMBRE_MODEL,
                                            "language": "hi-IN", "speed": 1.0, "audio_config": body_rate},
                      headers={"X-API-Key-ID": config.API_KEY, "Content-Type": "application/json"}, timeout=40)
    r.raise_for_status()
    return time.time() - t0, len(r.content)


for name, text in TEXTS.items():
    for rate in (24000, 16000):
        runs = [timed(text + " " * i, rate) for i in range(4)]  # trailing spaces: same speech, not a cache hit
        t = [x[0] for x in runs]
        print(f"{name:18s} {rate} Hz: median {statistics.median(t):4.2f} s  min {min(t):4.2f}  max {max(t):4.2f}  ({runs[0][1] // 1024} KB)")
