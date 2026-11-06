"""System tray icon: shows what Echo is doing (colour + tooltip) and lets you quit. Echo then runs in the
background without a console window (see start_echo.bat)."""
import pystray
from PIL import Image, ImageDraw

STATES = {  # state -> (label, colour)
    "idle": ("ready - hold Right Ctrl to talk", (0, 150, 136)),
    "listening": ("listening...", (229, 57, 53)),
    "thinking": ("thinking...", (255, 179, 0)),
    "speaking": ("speaking", (67, 160, 71)),
}


def _image(color: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=color)
    # a white "E" drawn from bars (no font files needed)
    d.rectangle((21, 16, 27, 48), fill="white")
    for y in (16, 29, 42):
        d.rectangle((21, y, 45, y + 6), fill="white")
    return img


class Tray:
    def __init__(self, on_quit):
        self.state = "idle"
        self._on_quit = on_quit
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: f"Echo: {STATES[self.state][0]}", None, enabled=False),
            pystray.MenuItem("Quit Echo", self._quit),
        )
        self.icon = pystray.Icon("echo", _image(STATES["idle"][1]), "Echo", menu)

    def set_state(self, state: str) -> None:
        if state == self.state:
            return
        self.state = state
        label, color = STATES[state]
        self.icon.icon = _image(color)
        self.icon.title = f"Echo - {label}"

    def _quit(self, icon, item) -> None:
        self._on_quit()
        icon.stop()

    def run(self) -> None:
        """Blocks (Windows needs the tray loop on the main thread) until Quit."""
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()
