"""Step 3: type sentences (no mic) to test intent parsing + memory. Empty line quits."""
from echo import brain


def confirm(prompt: str) -> bool:
    return input(f"  KAIRO ASKS: {prompt} (y/n) ").strip().lower().startswith("y")


while True:
    text = input("\nYou: ").strip()
    if not text:
        break
    print("KAIRO:", brain.handle(text, confirm))
