"""Cross-script recall test set (uses real Gemini, throwaway database, no mic).
Facts are SAVED in one script/wording and RECALLED in the other. 'easy' = shares words with the memory,
'hard' = different words for the same meaning (needs query rewriting / semantic search).
Run: python -m tests.test_crossscript"""
import sys
import time
from pathlib import Path

from echo import brain, memory, reminders

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_cross.db"
memory.DB_PATH.unlink(missing_ok=True)
reminders.JOBS_DB = memory.DB_PATH.parent / "test_cross_jobs.db"

SAVES = [
    "KAIRO yaad rakhna maths mein integration ho gaya differential equations baaki hai",
    "याद रखना डेटाबेस का असाइनमेंट शुक्रवार तक जमा करना है",
    "yaad rakhna Rahul se college mein notes ke baare mein poochna hai",
    "याद रखना कैरो प्रोजेक्ट में साउंड वाली फीचर जोड़नी है",
    "yaad rakhna physics ke numericals chapter paanch revise karne hain",
    "याद रखना जिम में सोमवार को लेग डे है",
]
# (level, question, acceptable substrings in the Devanagari reply)
QUERIES = [
    ("easy", "मैथ्स में क्या बचा है?", ["डिफरेंशियल", "डिफरेंशल"]),
    ("easy", "database assignment kab jama karna hai?", ["शुक्रवार"]),
    ("easy", "राहुल से क्या पूछना है?", ["नोट्स", "नोट"]),
    ("easy", "KAIRO project mein kya feature add karna hai?", ["साउंड", "आवाज़", "आवाज"]),
    ("easy", "फिजिक्स में क्या revise करना है?", ["न्यूमेरिकल", "नुमेरिकल", "न्यूमेरिक"]),
    ("easy", "gym mein monday ko kya hai?", ["लेग"]),
    ("hard", "calculus ka kya status hai?", ["डिफरेंशियल", "इंटीग्रेशन", "इंटीग्रल"]),
    ("hard", "workout kab hai aur kaunsa?", ["सोमवार", "लेग"]),
    ("hard", "submission ki deadline kya hai?", ["शुक्रवार"]),
    ("hard", "mujhe Rahul se kya baat karni hai?", ["नोट्स", "नोट"]),
    ("hard", "ध्वनि ka kaam kab karna hai?", ["साउंड"]),
    ("hard", "पदार्थ विज्ञान mein kya baaki hai?", ["न्यूमेरिकल", "नुमेरिकल", "न्यूमेरिक", "चैप्टर", "अध्याय"]),
]

for t in SAVES:
    brain.handle(t, lambda p: True)
    time.sleep(0.5)
print(f"saved {len(SAVES)} memories\n")

results = {"easy": [0, 0], "hard": [0, 0]}
for level, q, accept in QUERIES:
    reply = brain.handle(q, lambda p: True)
    ok = any(a in reply for a in accept)
    results[level][0] += ok
    results[level][1] += 1
    print(("PASS " if ok else "FAIL ") + f"[{level}] {q}\n       -> {reply}")

e, h = results["easy"], results["hard"]
total_ok, total = e[0] + h[0], e[1] + h[1]
print(f"\neasy {e[0]}/{e[1]}   hard {h[0]}/{h[1]}   overall {total_ok}/{total} = {100 * total_ok // total}%")
memory._db.close()
memory.DB_PATH.unlink(missing_ok=True)
sys.exit(0 if total_ok / total >= 0.9 else 1)
