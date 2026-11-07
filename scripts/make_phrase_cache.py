"""Generates assets/phrases/*.wav: KAIRO's fixed spoken phrases, synthesized once with the default Timbre model
and voice, then shipped inside the installer. Re-run after changing tts.PHRASES, TIMBRE_MODEL or TIMBRE_VOICE.
Run: python -m scripts.make_phrase_cache"""
import shutil
import sys
import time

from echo import config, tts

sys.stdout.reconfigure(encoding="utf-8")
out = tts.bundled_phrases_dir()
out.mkdir(parents=True, exist_ok=True)
print(f"model {config.TIMBRE_MODEL}, voice {config.TIMBRE_VOICE} -> {out}")
for text in tts.PHRASES:
    wav = tts.synthesize(text, "hi-IN")  # also lands in the normal cache
    shutil.copyfile(tts._cache_path(text, "hi-IN", 1.0), out / tts._cache_path(text, "hi-IN", 1.0).name)
    print(f"  {len(wav) // 1024:4d} KB  {text}")
    time.sleep(0.3)
print(f"{len(tts.PHRASES)} phrases, {sum(f.stat().st_size for f in out.glob('*.wav')) // 1024} KB total")
