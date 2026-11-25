"""Ton fuer den Wolkenkratzer-Short: synthetische Atmos/Musikteile + CC0-Effekte (Kenney/OGA) -> public/sfx, public/audio"""
import numpy as np, wave, pathlib, subprocess
from scipy.signal import lfilter, butter
SR = 44100; ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT.parent.parent / "assets_audio"   # python stickblend/tools/fetch_audio.py
rng = np.random.default_rng(7)
T = lambda d: np.arange(int(SR * d)) / SR
def save(name, x, folder="sfx", peak=0.89):
    x = np.asarray(x, float); x = x / (np.max(np.abs(x)) + 1e-9) * peak
    p = ROOT / "public" / folder; p.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p / f"{name}.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
def bp(x, lo, hi): b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)
def lp(x, hi): b, a = butter(2, hi / (SR / 2)); return lfilter(b, a, x)
def hp(x, lo): b, a = butter(2, lo / (SR / 2), "high"); return lfilter(b, a, x)
noise = lambda d: rng.normal(0, 1, int(SR * d))
def fade(x, a=0.05, r=0.3):
    n = len(x); e = np.ones(n); ia, ir = int(SR * a), int(SR * r)
    if ia: e[:ia] = np.linspace(0, 1, ia)
    if ir: e[-ir:] = np.minimum(e[-ir:], np.linspace(1, 0, ir))
    return x * e
def place(buf, x, at):
    s = int(SR * at); buf[s:s + len(x)] += x[:max(0, len(buf) - s)]
def reverb(x, amt=0.35, tail=1.0):
    y = np.concatenate([x, np.zeros(int(SR * tail))])
    for d, g in [(0.031, 0.6), (0.047, 0.5), (0.071, 0.42), (0.097, 0.35), (0.143, 0.28), (0.211, 0.2), (0.33, 0.12)]:
        k = int(SR * d); y[k:k + len(x)] += x * g * amt
    return y
def ogg(src, name):
    out = ROOT / "public" / "sfx" / f"{name}.wav"; out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(SR), str(out)], check=True)

# --- Atmos
t = T(14); save("elevator_hum", fade(lp(noise(14), 180) * 0.6 + np.sin(2 * np.pi * 58 * t) * 0.25 + np.sin(2 * np.pi * 116 * t) * 0.08, 0.8, 1.0))
w = bp(noise(22), 300, 2200) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.17 * T(22)) ** 2); w += np.sin(2 * np.pi * np.cumsum(900 + 300 * np.sin(2 * np.pi * 0.11 * T(22))) / SR) * 0.06
save("cavern_wind", fade(w + lp(noise(22), 120) * 0.5, 1.0, 1.5))
save("city_distant", fade(lp(noise(20), 700) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * T(20))), 1.0, 1.5))
save("penthouse_breeze", fade(bp(noise(9), 150, 900) * 0.5, 0.8, 0.3))
# --- Schacht: Rauschen, das hochzieht
t = T(4); r = bp(noise(4), 200, 3000) * np.minimum(1, t / 1.0) * np.exp(-np.maximum(0, t - 2.6) * 2)
save("shaft_rush", r + np.sin(2 * np.pi * np.cumsum(60 + 140 * t / 4) / SR) * 0.3 * np.minimum(1, t))
# --- Whoosh
t = T(0.9); env = np.sin(np.pi * t / 0.9) ** 2
x = np.zeros(len(t)); seg = bp(noise(0.9), 300, 2500)
save("whoosh", seg * env)
# --- Stempel: dumpfer Schlag + Papier
t = T(0.6); thump = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-t * 12) + 55) / SR) * np.exp(-t * 14); save("stamp", reverb(thump + hp(noise(0.6), 1500) * np.exp(-t * 60) * 0.5, 0.3, 0.5))
# --- Rohrklopfen mit Hall (2x)
t = T(0.25); ping = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((420, 9), (1130, 14), (2210, 20))) + hp(noise(0.25), 3000) * np.exp(-t * 200)
x = np.zeros(int(SR * 0.6)); place(x, ping, 0.0); place(x, ping * 0.9, 0.28); save("pipe_tap", reverb(x, 0.8, 1.6))
# --- Kisten-Hebebuehne: Rattern + Hydraulik
t = T(1.0); hyd = lp(noise(1.0), 400) * 0.5 + np.sin(2 * np.pi * np.cumsum(70 + 40 * t) / SR) * 0.4
for k in range(9): place(hyd, hp(noise(0.03), 800) * np.exp(-T(0.03) * 120) * 0.8, 0.05 + k * 0.1)
save("crate_lift", fade(hyd, 0.05, 0.25))
# --- Musik A: Luxus-Puls (Klavier/Streicher-artig), 0-14 s
def note(f, d, a=0.3):
    tt = T(d); return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 2.2) * a
mA = np.zeros(int(SR * 15)); bpm = 92; beat = 60 / bpm
chords = [(220, 277.2, 329.6), (196, 246.9, 293.7), (174.6, 220, 261.6), (196, 246.9, 329.6)]
for i in range(int(14.5 / beat)):
    ch = chords[(i // 4) % 4]
    for k, f in enumerate(ch): place(mA, note(f * 2, beat * 1.6, 0.18), i * beat + k * 0.012)
    if i % 2 == 0: place(mA, note(ch[0] / 2, beat * 2.2, 0.35), i * beat)
pad = sum(np.sin(2 * np.pi * f * T(15)) for f in (220, 329.6, 440)) * 0.05
save("music_lux", reverb(fade(mA + pad, 0.3, 1.2), 0.4, 1.0), "audio", 0.7)
# --- Musik B: Sub-Bass-Puls + trockenes Ticken, 14-36 s
mB = np.zeros(int(SR * 22)); beat = 0.5
for i in range(int(21.5 / beat)):
    tt = T(0.45); place(mB, np.sin(2 * np.pi * 46 * tt) * np.exp(-tt * 6) * 0.8, i * beat)
    place(mB, hp(noise(0.01), 4000) * np.exp(-T(0.01) * 400) * 0.25, i * beat + 0.25)
mB += np.sin(2 * np.pi * 92.5 * T(22)) * 0.04 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * T(22)))
save("music_mystery", fade(mB, 0.6, 0.15), "audio", 0.75)
# --- Musik D: Schlussanschwellen (Dur-Pad), 55-63 s
t = T(8.5); env = np.minimum(1, t / 3.5)
sw = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((261.6, 0.4), (329.6, 0.3), (392, 0.3), (523.2, 0.2), (659.3, 0.12)))
sw += sum(note(f, 1.6, 0.15) for f in ()) if False else 0
save("music_swell", reverb(sw * env * (1 + 0.1 * np.sin(2 * np.pi * 5 * t)), 0.4, 0.5), "audio", 0.6)
# --- CC0-Effekte aus der Bibliothek
F = LIB / "sfx" / "cc0_footsteps_impacts"
ogg(LIB / "sfx" / "kenney_ui_audio" / "click3.wav", "button_click")
ogg(F / "bell_02.ogg", "ding")
ogg(F / "door_close_02.ogg", "doors_close")
ogg(F / "switch_01.ogg", "remote_click")
ogg(F / "wooden_02.ogg", "crate_knock")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(LIB / "music" / "sneaky_snitch.mp3"), "-ac", "2", "-ar", str(SR), str(ROOT / "public" / "audio" / "music_groove.wav")], check=True)
print("ok")
# --- Drop-Impact (Tuer ins Leere): tiefer Schlag + Rauschfahne
t = T(2.5); boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 5)) / SR) * np.exp(-t * 1.6)
save("impact", reverb(boom + lp(noise(2.5), 900) * np.exp(-t * 3) * 0.35, 0.35, 1.2))
# --- Penthouse-Reveal: heller Akkord-Schlag mit Becken-Schimmer
t = T(3.0); ch = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((130.8, 0.5), (261.6, 0.45), (329.6, 0.35), (392, 0.35), (523.2, 0.25), (784, 0.12)))
shim = hp(noise(3.0), 5000) * 0.25
save("reveal_hit", reverb((ch + shim) * np.exp(-t * 1.3) * np.minimum(1, t / 0.01), 0.45, 1.0))
# --- Pfeifender Windstoss
t = T(3.0); f = 700 + 500 * np.sin(np.pi * t / 3.0) + 80 * np.sin(2 * np.pi * 1.3 * t)
gust = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35 + bp(noise(3.0), 500, 3000) * 0.8
save("wind_gust", fade(gust * np.sin(np.pi * t / 3.0) ** 2, 0.05, 0.3))
# --- Knopf-Piep (Aufzug bestaetigt)
t = T(0.18); save("button_beep", fade(np.sin(2 * np.pi * 1318 * t) * 0.6 + np.sin(2 * np.pi * 2636 * t) * 0.15, 0.005, 0.06))
print("ok2")

