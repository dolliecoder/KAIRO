"""Microphone capture as 1,024-byte int16 mono frames."""
import queue

import sounddevice as sd

from . import config


class Recorder:
    def __init__(self):
        self.q: "queue.Queue[bytes | None]" = queue.Queue()
        self._stream = None

    def start(self):
        self.q = queue.Queue()

        def cb(indata, frames, time_info, status):
            self.q.put(bytes(indata))

        self._stream = sd.RawInputStream(samplerate=config.SAMPLE_RATE, channels=1,
                                         dtype="int16", blocksize=512, callback=cb)
        self._stream.start()

    def stop(self):
        self._stream.stop()
        self._stream.close()
        self.q.put(None)
