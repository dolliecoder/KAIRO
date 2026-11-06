"""How well do Gemini embeddings match Hinglish across scripts and meaning? Prints the top match + cosine per query."""
import sys

from echo import embed

sys.stdout.reconfigure(encoding="utf-8")
MEMORIES = [
    "मैथ्स में इंटीग्रेशन हो गया, डिफरेंशियल इक्वेशंस बाकी हैं | maths mein integration ho gaya, differential equations baaki hain",
    "डेटाबेस का असाइनमेंट शुक्रवार तक जमा करना है | database ka assignment Friday tak jama karna hai",
    "राहुल से कॉलेज में नोट्स के बारे में पूछना है | Rahul se college mein notes ke baare mein poochna hai",
    "कैरो प्रोजेक्ट में साउंड वाली फीचर जोड़नी है | KAIRO project mein sound wali feature jodni hai",
    "फिजिक्स के न्यूमेरिकल्स चैप्टर पाँच रिवाइज करने हैं | physics ke numericals chapter paanch revise karne hain",
    "जिम में सोमवार को लेग डे है | gym mein Monday ko leg day hai",
]
QUERIES = [  # (query, index of the memory that should win)
    ("मैथ्स में क्या बचा है?", 0), ("database assignment kab jama karna hai?", 1), ("राहुल से क्या पूछना है?", 2),
    ("KAIRO project mein kya feature add karna hai?", 3), ("फिजिक्स में क्या revise करना है?", 4),
    ("gym mein monday ko kya hai?", 5),
    ("calculus ka kya status hai?", 0), ("workout kab hai aur kaunsa?", 5), ("submission ki deadline kya hai?", 1),
    ("mujhe Rahul se kya baat karni hai?", 2), ("ध्वनि ka kaam kab karna hai?", 3),
    ("पदार्थ विज्ञान mein kya baaki hai?", 4),
    # should match NOTHING confidently:
    ("aaj mausam kaisa hai?", None), ("मुझे बिरयानी की रेसिपी बताओ", None),
]
docs = embed.embed(MEMORIES)
ok = 0
for q, want in QUERIES:
    qv = embed.embed([q], query=True)[0]
    sims = sorted(((embed.cosine(qv, d), i) for i, d in enumerate(docs)), reverse=True)
    top, idx = sims[0]
    verdict = "" if want is None else ("OK " if idx == want else "BAD")
    ok += verdict == "OK "
    print(f"{verdict:3s} cos={top:.3f} (2nd {sims[1][0]:.3f}) -> #{idx}  {q}")
print(f"\ntop-1 correct: {ok}/{sum(w is not None for _, w in QUERIES)}")
