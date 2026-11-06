"""System tray icon: shows what KAIRO is doing (colour + tooltip) and lets you quit. KAIRO then runs in the
background without a console window (see start_echo.bat)."""
import pystray
from PIL import Image, ImageDraw

STATES = {  # state -> (label, colour)
    "idle": ("ready - hold Right Ctrl to talk", (0, 150, 136)),
    "listening": ("listening...", (229, 57, 53)),
    "thinking": ("thinking...", (255, 179, 0)),
    "speaking": ("speaking", (67, 160, 71)),
}


def _image(color: tuple[int, int, int], size: int = 64) -> Image.Image:
    """Round badge with a white K, drawn from shapes (no font files). Also used for the app and installer icon."""
    k = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((1 * k, 1 * k, 63 * k, 63 * k), fill=color)
    d.rectangle((19 * k, 14 * k, 27 * k, 50 * k), fill="white")  # the spine of the K
    d.polygon([(27 * k, 33 * k), (27 * k, 26 * k), (43 * k, 14 * k), (53 * k, 14 * k)], fill="white")  # upper arm
    d.polygon([(27 * k, 33 * k), (34 * k, 28 * k), (54 * k, 50 * k), (44 * k, 50 * k)], fill="white")  # lower arm
    return img


class Tray:
    def __init__(self, on_quit):
        self.state = "idle"
        self._on_quit = on_quit
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: f"KAIRO: {STATES[self.state][0]}", None, enabled=False),
            pystray.MenuItem("Quit KAIRO", self._quit),
        )
        self.icon = pystray.Icon("kairo", _image(STATES["idle"][1]), "KAIRO", menu)

    def set_state(self, state: str) -> None:
        if state == self.state:
            return
        self.state = state
        label, color = STATES[state]
        self.icon.icon = _image(color)
        self.icon.title = f"KAIRO - {label}"

    def _quit(self, icon, item) -> None:
        self._on_quit()
        icon.stop()

    def run(self) -> None:
        """Blocks (Windows needs the tray loop on the main thread) until Quit."""
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()
