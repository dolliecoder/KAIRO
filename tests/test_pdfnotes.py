"""Notes from a PDF. Offline checks use a fake Gemini and a throwaway database; add --live to have real Gemini read a typed
PDF and a scanned-style (image) PDF and to quiz from the result. Run: python -m tests.test_pdfnotes [--live]"""
import sys
import tempfile
from pathlib import Path

from echo import embed, llm, memory, pdfnotes, reminders

sys.stdout.reconfigure(encoding="utf-8")
HOME = Path(tempfile.mkdtemp(prefix="kairo_pdf_"))
memory.DB_PATH = HOME / "pdf.db"
reminders.JOBS_DB = HOME / "jobs.db"

failed = 0


def check(name, ok, detail=""):
    global failed
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + (f"   {detail}" if detail and not ok else ""))


def raises(fn, text=None):
    try:
        fn()
    except pdfnotes.PdfError as e:
        return text is None or text in str(e)
    return False


# --- opening the file ---
good = HOME / "notes.pdf"
good.write_bytes(pdfnotes.make_minimal_pdf(["Integration is the reverse of differentiation."]))
check("a real PDF is accepted", pdfnotes.read_pdf(str(good)).startswith(b"%PDF"))
check("a missing file gives a friendly message", raises(lambda: pdfnotes.read_pdf(str(HOME / "nope.pdf")), "could not find"))
(HOME / "notes.txt").write_text("hello")
check("a non-PDF extension is refused", raises(lambda: pdfnotes.read_pdf(str(HOME / "notes.txt")), "not a PDF"))
(HOME / "empty.pdf").write_bytes(b"")
check("an empty PDF is refused", raises(lambda: pdfnotes.read_pdf(str(HOME / "empty.pdf")), "empty"))
(HOME / "fake.pdf").write_text("this is not a pdf at all")
check("a file that only pretends to be a PDF is refused", raises(lambda: pdfnotes.read_pdf(str(HOME / "fake.pdf")), "real PDF"))
real_max = pdfnotes.MAX_BYTES
pdfnotes.MAX_BYTES = 100
check("a PDF over the size limit is refused, saying how big it is", raises(lambda: pdfnotes.read_pdf(str(good)), "too big"))
pdfnotes.MAX_BYTES = real_max

# --- cleaning ---
note = lambda dev, lat="x": {"devanagari": dev, "latin": lat, "keywords": ["k"]}  # noqa: E731
many = [note(f"नोट {i}") for i in range(30)]
check("at most 12 notes are kept", len(pdfnotes.clean(many)) == 12)
check("duplicates are dropped", len(pdfnotes.clean([note("एक"), note("एक"), note("दो")])) == 2)
check("notes too long to be spoken are dropped", len(pdfnotes.clean([note("क" * 400), note("छोटा")])) == 1)
check("blank notes are dropped", len(pdfnotes.clean([note("   "), note("ठीक")])) == 1)

# --- extraction with a fake Gemini ---
sample = [note("इंटीग्रेशन डिफरेंशिएशन का उल्टा है", "integration differentiation ka ulta hai"),
          note("sin x का डिफरेंशियल cos x है", "sin x ka differential cos x hai")]
llm.read_study_pdf = lambda data: {"title": "maths calculus chapter 3", "notes": sample}
got = pdfnotes.extract(str(good))
check("extract returns the title and the notes", got["title"] == "maths calculus chapter 3" and len(got["notes"]) == 2, str(got))
llm.read_study_pdf = lambda data: {"title": "", "notes": sample}
check("no title from Gemini: the file name is used", pdfnotes.extract(str(good))["title"] == "notes")
llm.read_study_pdf = lambda data: {"title": "x", "notes": []}
check("a PDF with no readable notes gives a friendly message", raises(lambda: pdfnotes.extract(str(good)), "could not find readable"))


def boom(data):
    raise RuntimeError("quota exceeded")


llm.read_study_pdf = boom
check("Gemini failing gives a friendly retry message, not a crash", raises(lambda: pdfnotes.extract(str(good)), "try again"))
check("title words become search keywords", pdfnotes.title_keywords("maths calculus chapter 3") == ["maths", "calculus", "chapter"])

# --- saving: one embedding call, no duplicates ---
embed_calls = []
embed.embed = lambda texts, query=False: (embed_calls.append(len(texts)), [[0.0] * embed.DIM for _ in texts])[1]
n = pdfnotes.save("maths calculus chapter 3", sample)
check("saving 2 notes stores 2", n == 2 and len(memory.all_memories()) == 2, str(n))
check("they are embedded with ONE call, not one per note", embed_calls == [2], str(embed_calls))
rows = memory._conn().execute("SELECT count(*) FROM vec_memories").fetchone()[0]
check("both notes have a vector for meaning search", rows == 2, str(rows))
check("title words were added as keywords", all("calculus" in m["keywords"] for m in memory.all_memories()))
embed_calls.clear()
check("importing the same notes again adds nothing", pdfnotes.save("maths calculus chapter 3", sample) == 0 and not embed_calls)
check("saved notes are searchable", len(memory.search(["calculus"])) == 2)

# --- live Gemini (optional) ---
if "--live" in sys.argv:
    print("\nlive Gemini:")
    importlib = __import__("importlib")
    importlib.reload(llm)
    importlib.reload(embed)
    from echo.llm import has_devanagari

    lines = ["Calculus notes, chapter 3.", "Integration is the reverse of differentiation.",
             "The derivative of sin x is cos x.", "The derivative of x squared is two x.",
             "A definite integral gives the area under a curve between two limits.",
             "The constant of integration, C, is added to every indefinite integral."]
    typed = HOME / "typed.pdf"
    typed.write_bytes(pdfnotes.make_minimal_pdf(lines))

    scanned = HOME / "scanned.pdf"
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1240, 1000), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 34)
    except OSError:
        font = ImageFont.load_default(size=34)
    for i, line in enumerate(lines):
        draw.text((60, 60 + i * 70), line, fill="black", font=font)
    img.save(scanned, "PDF", resolution=100)  # a picture of text: no text layer, like a scan

    for label, path in (("typed PDF", typed), ("scanned-style (image) PDF", scanned)):
        got = pdfnotes.extract(str(path))
        print(f"    {label}: '{got['title']}' -> {len(got['notes'])} notes; first: {got['notes'][0]['devanagari']}")
        check(f"live {label}: Gemini wrote at least 3 notes", len(got["notes"]) >= 3, str(got))
        check(f"live {label}: notes are Devanagari + Hinglish, short, with keywords",
              all(has_devanagari(n["devanagari"]) and not has_devanagari(n["latin"]) and len(n["devanagari"]) <= 300 and n["keywords"]
                  for n in got["notes"]), str(got["notes"][:2]))
        check(f"live {label}: it mentions what the document says",
              any(w in " ".join(n["latin"].lower() for n in got["notes"]) for w in ("integrat", "derivative", "differenti")),
              str([n["latin"] for n in got["notes"]]))

    items = llm.make_quiz([n["devanagari"] for n in got["notes"][:2]])
    q, a = items[0]["question"], items[0]["answer"]
    check("live: a quiz question made from the PDF notes is judged correctly when answered right",
          llm.judge_answer(q, a, a)["verdict"] == "correct", f"{q} / {a}")

memory._db.close()
print("\nall passed" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
