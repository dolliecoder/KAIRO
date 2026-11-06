"""Speaks the same reminder three ways so you can hear which script Timbre pronounces best."""
import time

from echo import tts

VARIANTS = [
    ("1  Latin Hinglish, language hi-en", "Yaad dilana tha: pani pine ka.", "hi-en"),
    ("2  Devanagari,     language hi-IN", "याद दिलाना था: पानी पीना।", "hi-IN"),
    ("3  Devanagari,     language hi-en", "याद दिलाना था: पानी पीना।", "hi-en"),
    ("4  Mixed script,   language hi-en", "मैथ्स में integration हो गया है, differential equations बाकी हैं।", "hi-en"),
    ("5  Latin Hinglish, language hi-en", "Maths mein integration ho gaya hai, differential equations baaki hain.", "hi-en"),
]
for label, text, lang in VARIANTS:
    print(label, "->", text)
    tts.speak(text, lang)
    time.sleep(1)
