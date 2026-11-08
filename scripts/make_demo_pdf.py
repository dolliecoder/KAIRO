"""Makes assets/demo/sample_maths_notes.pdf: a clean, made-up one-page study sheet for the demo video (no real personal data),
then reads it with KAIRO's PDF reader and prints the notes and how long it took.
Run: python -m scripts.make_demo_pdf"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from echo import pdfnotes

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent.parent / "assets" / "demo" / "sample_maths_notes.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

TITLE = "Calculus - Chapter 3: Integration"
POINTS = [
    "Integration is the reverse process of differentiation.",
    "The integral of x raised to n is x raised to n plus one, divided by n plus one, plus a constant C.",
    "The derivative of sin x is cos x, so the integral of cos x is sin x plus C.",
    "A definite integral gives the area under a curve between two limits a and b.",
    "Every indefinite integral needs the constant of integration, C.",
    "A differential equation is an equation that contains a derivative of an unknown function.",
    "To solve a first order differential equation by separation of variables, put all y terms on one side and all x terms on the other, then integrate both sides.",
    "The order of a differential equation is the order of its highest derivative.",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf" if bold else "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


page = Image.new("RGB", (1240, 1754), "white")  # A4 at 150 dpi
d = ImageDraw.Draw(page)
d.rectangle((0, 0, 1240, 150), fill="#3b1796")
d.text((70, 48), TITLE, fill="white", font=font(54, True))
d.text((70, 190), "Class notes (made-up sample for the KAIRO demo)", fill="#555555", font=font(30))
y = 270
for i, point in enumerate(POINTS, 1):
    d.ellipse((70, y + 8, 98, y + 36), fill="#ff1fa8")
    d.text((80, y + 6), str(i), fill="white", font=font(22, True))
    for line in wrap(d, point, font(36), 1000):
        d.text((130, y), line, fill="#111111", font=font(36))
        y += 52
    y += 34
page.save(OUT, "PDF", resolution=150)
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")

started = time.time()
result = pdfnotes.extract(str(OUT))
print(f"\nKAIRO read it in {time.time() - started:.0f} s -> '{result['title']}', {len(result['notes'])} notes:")
for n in result["notes"]:
    print(f"  - {n['devanagari']}\n    {n['latin']}   [{', '.join(n['keywords'])}]")
