"""Builds assets/kairo.ico (multi-size) and a preview PNG from the same K badge the tray uses. Run: python assets/make_icon.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from echo.tray import STATES, _image  # noqa: E402

out = Path(__file__).resolve().parent
big = _image((255, 31, 168), 256)  # KAIRO pink
big.save(out / "kairo.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
big.save(out / "kairo.png")
sheet = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if sheet:  # preview of every tray state at 64px next to the app icon
    from PIL import Image
    img = Image.new("RGBA", (64 * 5 + 60, 80), (30, 20, 60, 255))
    for i, (state, (_, color)) in enumerate(STATES.items()):
        img.paste(_image(color), (10 + i * 70, 8), _image(color))
    img.paste(big.resize((64, 64)), (10 + 4 * 70, 8), big.resize((64, 64)))
    img.save(sheet)
print("wrote", out / "kairo.ico")
