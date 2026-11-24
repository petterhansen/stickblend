"""Procedural royalty-free SFX and background music generator -> audio/sfx/*.wav, audio/music.wav.

Usage:
  python scripts/sfx.py
"""
import pathlib
import wave
import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
ROOT = pathlib.Path(__file__).resolve().parent.parent
rng = np.random.default_rng(7)
T = lambda d: np.arange(int(SR * d)) / SR


def save(name: str, x: np.ndarray, folder: str = "audio/sfx") -> None:
    out_dir = ROOT / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    x = np.asarray(x, float)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    with wave.open(str(out_dir / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
    return lfilter(b, a, x)


def lp(x, hi):
    b, a = butter(2, hi / (SR / 2))
    return lfilter(b, a, x)


def hp(x, lo):
    b, a = butter(2, lo / (SR / 2), "high")
    return lfilter(b, a, x)


noise = lambda d: rng.normal(0, 1, int(SR * d))


def fade(x, a=0.05, r=0.3):
    n = len(x)
    e = np.ones(n)
    ia, ir = int(SR * a), int(SR * r)
    if ia:
        e[:ia] = np.linspace(0, 1, ia)
    if ir:
        e[-ir:] = np.minimum(e[-ir:], np.linspace(1, 0, ir))
    return x * e


def place(buf, x, at):
    s = int(SR * at)
    buf[s : s + len(x)] += x[: max(0, len(buf) - s)]


def reverb(x, amt=0.3):
    y = x.copy()
    for d, g in [(0.029, 0.5), (0.043, 0.4), (0.067, 0.33), (0.089, 0.26), (0.131, 0.2)]:
        k = int(SR * d)
        y[k:] += x[:-k] * g * amt * 2
    return y


if __name__ == "__main__":
    # Starter SFX cues
    t = T(0.5)
    save("whoosh", bp(noise(0.5), 400, 3000) * np.sin(np.pi * t / 0.5) ** 2)
    t = T(0.12)
    save("pop", np.sin(2 * np.pi * (500 + 900 * t / 0.12) * t) * np.exp(-t * 40))
    t = T(1.2)
    save("impact", reverb(np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t * 20)) / SR) * np.exp(-t * 5) + lp(noise(1.2), 400) * np.exp(-t * 30) * 0.6, 0.5))
    t = T(1.4)
    save("ding", (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 4))
    save("wind", fade(lp(noise(5.0), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * T(5.0))), 0.8, 1.2))

    # Starter ambient music bed (customize per story)
    dur = 65.0
    pad_t = T(dur)
    pad = np.zeros_like(pad_t)
    for f, g in [(55, 0.25), (82.4, 0.15), (110, 0.12), (164.8, 0.06)]:
        pad += np.sin(2 * np.pi * f * pad_t + np.sin(2 * np.pi * 0.07 * pad_t) * 2) * g
    save("music", fade(reverb(lp(pad, 900), 0.35), 1.5, 3.0), folder="audio")
    print("SFX + music generated in audio/")
