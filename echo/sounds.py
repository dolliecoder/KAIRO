"""Synthesized alert sounds (no audio files needed)."""
import numpy as np

from . import tts

RATE = 24000


def _bell(freq: float, seconds: float = 0.45) -> np.ndarray:
    t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
    tone = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2 * t)
    return tone * np.exp(-5 * t)  # fast decay = bell-like


def chime(repeats: int = 2) -> None:
    """Rising three-note alarm chime, played `repeats` times."""
    phrase = np.concatenate([_bell(f) for f in (880.0, 1108.7, 1318.5)] + [np.zeros(int(RATE * 0.25))])
    audio = np.tile(phrase, repeats)
    pcm = (audio / np.max(np.abs(audio)) * 0.6 * 32767).astype(np.int16)
    tts.play_pcm(pcm, RATE)
