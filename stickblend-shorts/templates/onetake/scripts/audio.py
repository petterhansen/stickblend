"""Ton fuer einen One-Take-Short: synthetische Effekte/Musik + CC0-Effekte (Kenney/OGA) -> public/sfx, public/audio.
Weitere fertige Klaenge (Seil-Twang, Alarm, Funken, Rueckspulen, Flugzeug ...): examples/aufzug/scripts/audio.py"""
import numpy as np, wave, pathlib, subprocess
from scipy.signal import lfilter, butter
SR = 44100; ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = pathlib.Path(r"C:\AI\agy-shorts\assets_audio")
rng = np.random.default_rng(11)
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
def tone(f, d, a=0.3, dec=2.2):
    tt = T(d); return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * dec) * a


# --- Whoosh (Kamera-Schwenk, Uebergang)
t = T(0.9); save("whoosh", bp(noise(0.9), 300, 2500) * np.sin(np.pi * t / 0.9) ** 2)
# --- Einschlag / Drop (tiefer Boom + Rauschfahne)
t = T(2.5); boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t * 5)) / SR) * np.exp(-t * 1.6)
save("impact", reverb(boom + lp(noise(2.5), 900) * np.exp(-t * 3) * 0.35, 0.35, 1.2))
# --- Pop (Zaehler-/Text-Wechsel)
t = T(0.12); save("pop", np.sin(2 * np.pi * np.cumsum(500 + 900 * t / 0.12) / SR) * np.exp(-t * 35))
# --- Musik: Spannungs-Puls (bis zum Twist), harter Stopp im Short.tsx
dur = 20; m1 = np.zeros(int(SR * dur)); beat = 60 / 140
for i in range(int(dur / beat)):
    tt = T(0.3); place(m1, np.sin(2 * np.pi * 49 * tt) * np.exp(-tt * 9) * 0.9, i * beat)
    place(m1, tone([392, 466.2, 392, 587.3][i % 4], beat * 0.9, 0.16, 6), i * beat)
save("music_tension", fade(m1, 0.02, 0.3), "audio", 0.75)
# --- Musik: ruhig-ueberlegen (nach dem Twist)
dur = 12; m2 = np.zeros(int(SR * dur)); beat = 0.3
for i in range(int(dur / beat)): place(m2, tone([261.6, 329.6, 392, 523.2, 392, 329.6][i % 6], beat * 2.5, 0.14, 3.5), i * beat)
save("music_calm", reverb(fade(m2, 0.4, 0.6), 0.35, 0.8), "audio", 0.65)
# --- CC0 aus der Bibliothek (falls geladen)
F = LIB / "sfx" / "cc0_footsteps_impacts"
for src_, name in ((LIB / "sfx" / "kenney_ui_audio" / "click3.wav", "click"), (F / "bell_02.ogg", "ding"), (F / "door_close_02.ogg", "door")):
    if src_.exists(): ogg(src_, name)
    else: print("fehlt (fetch_audio.py):", src_)
print("ok")
