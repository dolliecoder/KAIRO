"""Study notes from a PDF: Gemini reads the document and writes short notes; you approve them; they become ordinary
KAIRO notes, so the quiz, recall and word hints all work on them. The PDF is sent to Google Gemini to be read."""
import string
from pathlib import Path

from . import boost, llm, memory
from .log import log
from .words import STOPWORDS

MAX_BYTES = 15 * 1024 * 1024  # inline upload limit for Gemini is ~20 MB per request; stay well under it
MAX_NOTES = 12
MAX_NOTE_CHARS = 300  # a note is spoken aloud; anything longer is not a note


class PdfError(Exception):
    """A problem with the PDF, worded for the person using KAIRO (shown in the import window)."""


def read_pdf(path: str) -> bytes:
    p = Path(path)
    if not p.is_file():
        raise PdfError("I could not find that file.")
    if p.suffix.lower() != ".pdf":
        raise PdfError("That is not a PDF file. Please choose a file that ends in .pdf.")
    size = p.stat().st_size
    if size == 0:
        raise PdfError("That PDF is empty.")
    if size > MAX_BYTES:
        raise PdfError(f"That PDF is too big ({size / 1048576:.0f} MB). Please choose one under {MAX_BYTES // 1048576} MB.")
    data = p.read_bytes()
    if not data.startswith(b"%PDF"):
        raise PdfError("That file does not look like a real PDF.")
    return data


def clean(notes: list[dict]) -> list[dict]:
    """Drop duplicates and anything too long to be spoken, and keep at most MAX_NOTES."""
    seen, out = set(), []
    for n in notes:
        dev = n["devanagari"].strip()
        if not dev or dev in seen or len(dev) > MAX_NOTE_CHARS or len(n["latin"]) > MAX_NOTE_CHARS:
            continue
        seen.add(dev)
        out.append(n)
    return out[:MAX_NOTES]


def extract(path: str) -> dict:
    """{"title": str, "notes": [...]} for the PDF at `path`. Raises PdfError with a readable message."""
    data = read_pdf(path)
    log("Gemini", f"reading PDF {Path(path).name} ({len(data) // 1024} KB)")
    try:
        result = llm.read_study_pdf(data)
    except Exception as e:
        log("Gemini", f"could not read the PDF: {str(e)[:120]}")
        raise PdfError("Gemini could not read this PDF right now. Please try again in a minute.") from e
    notes = clean(result["notes"])
    if not notes:
        raise PdfError("I could not find readable study notes in this PDF. Is it a scan that is too faint, or empty?")
    return {"title": result["title"] or Path(path).stem, "notes": notes}


def title_keywords(title: str) -> list[str]:
    """Words of the document title that help a topic quiz find these notes ('maths calculus chapter 3' -> maths, calculus)."""
    words = (w.strip(string.punctuation) for w in title.lower().replace("-", " ").split())  # in title order
    return list(dict.fromkeys(w for w in words if boost.valid_word(w) and w not in STOPWORDS))[:6]


def save(title: str, notes: list[dict]) -> int:
    """Save the approved notes (one embedding call). Returns how many were new; already-saved notes are skipped."""
    count = memory.save_many(notes, extra_keywords=title_keywords(title))
    log("Memory", f"imported {count} note(s) from the PDF '{title}'")
    return count


def make_minimal_pdf(lines: list[str]) -> bytes:
    """A tiny valid one-page PDF with the given lines of plain (Latin-1) text. Used by tests and the packaged self-test,
    so they need no PDF library."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = "BT /F1 12 Tf 50 780 Td 18 TL " + " T* ".join(f"({esc(line)}) Tj" for line in lines) + " ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode("latin-1"),
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out
