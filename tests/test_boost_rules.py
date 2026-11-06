"""Deterministic checks for boost-word and correction handling (no network). Run: python -m tests.test_boost_rules"""
import sys
from pathlib import Path

from echo import boost, memory

sys.stdout.reconfigure(encoding="utf-8")
memory.DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_boost.db"
memory.DB_PATH.unlink(missing_ok=True)

failed = 0


def check(name, ok):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name)


check("valid Devanagari word with vowel signs", boost.valid_word("वायवा"))
check("rejects two words", not boost.valid_word("two words"))
check("rejects digits", not boost.valid_word("abc123"))
check("rejects too short", not boost.valid_word("ab"))

memory.save("कल ओजेटी का वायवा है", "kal OJT ka viva hai", ["ojt", "viva"], raw="हाँ कल ओजीटी का वैवाह है")
stored = boost.learn(
    [{"heard": "वैवाह", "meant": "वायवा"},      # good
     {"heard": "है", "meant": "हैं"},           # stopword -> rejected
     {"heard": "नहींथा", "meant": "वायवा"},      # heard word not in transcript -> rejected
     {"heard": "वैवाह", "meant": "वैवाह"}],     # same word -> rejected
    "हाँ कल ओजीटी का वैवाह है")
check("learns only the valid correction", stored == [("वैवाह", "वायवा")])
check("rule format", boost.substitution_rules() == [{"patterns": ["वैवाह"], "replacement": "वायवा"}])

words = boost.bias_words()
check("boost list has the correct spelling", "वायवा" in words)
check("boost list never has the misheard raw spelling", "वैवाह" not in words)
check("boost list drops the 'हाँ' answer word", "हाँ" not in words)
check("learned word comes first", words[0] == "वायवा")
check("every boost word is valid", all(boost.valid_word(w) for w in words))

for i in range(15):
    memory.add_correction(f"ग़लत{'ा' * (i % 3 + 1)}{chr(0x0915 + i)}", "सहीशब्द")
check("rules capped at 10", len(boost.substitution_rules()) <= 10)

memory._db.close()  # Windows cannot delete an open SQLite file
memory.DB_PATH.unlink(missing_ok=True)
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
