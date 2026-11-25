"""Ton fuer den Aufzug-Short: synthetische Effekte/Musik + CC0-Effekte (Kenney/OGA) -> public/sfx, public/audio"""
import numpy as np, wave, pathlib, subprocess
from scipy.signal import lfilter, butter
SR = 44100; ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT.parent.parent / "assets_audio"   # python stickblend/tools/fetch_audio.py
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

# --- Seil-Twang: gespanntes Stahlseil reisst (metallischer Knall + absteigender Saitenton + Peitschen-Rauschen)
t = T(1.6)
twang = sum(np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t * 9))) / SR) * a * np.exp(-t * d) for f, a, d in ((180, 0.6, 3), (371, 0.4, 4), (743, 0.25, 6), (1490, 0.15, 9)))
crack = hp(noise(1.6), 2500) * np.exp(-t * 60) * 1.4 + bp(noise(1.6), 600, 4000) * np.exp(-t * 7) * 0.4
save("twang", reverb(twang + crack, 0.5, 1.2))
# --- Alarmglocke (elektrische Klingel, ratternd)
t = T(4.0); bell = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1180, 0.5), (2950, 0.25), (4100, 0.1)))
save("alarm", fade(bell * (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 22 * t))) * 0.6, 0.01, 0.4))
# --- Fall-Rauschen im Schacht (steigend)
t = T(19); fall = bp(noise(19), 250, 3500) * np.minimum(1, t / 3.0) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.6 * t))
fall += lp(noise(19), 140) * 0.8 + np.sin(2 * np.pi * np.cumsum(55 + 30 * t / 19) / SR) * 0.15
save("fall_rush", fade(fall, 0.02, 1.0))
# --- Funken (knisternde Einzelimpulse)
spk = np.zeros(int(SR * 3.0))
for k in range(70): place(spk, hp(noise(0.012), 3000) * np.exp(-T(0.012) * 300) * rng.uniform(0.3, 1.0), rng.uniform(0, 2.9))
save("sparks", spk)
# --- Uhr-Ticken (Freeze)
tk = np.zeros(int(SR * 2.0))
for k in range(4): place(tk, (hp(noise(0.02), 2000) * 0.6 + np.sin(2 * np.pi * 3200 * T(0.02)) * 0.4) * np.exp(-T(0.02) * 250), k * 0.5)
save("tick", tk)
# --- Rueckspul-Whoosh (rueckwaerts angeschwollenes Rauschen + absteigendes Pitch-Zirpen)
t = T(1.1); env = (t / 1.1) ** 2.5
rw = bp(noise(1.1), 400, 5000) * env + np.sin(2 * np.pi * np.cumsum(2400 - 1800 * t / 1.1) / SR) * 0.25 * env
save("rewind", fade(rw, 0.0, 0.03))
# --- Whoosh
t = T(0.9); save("whoosh", bp(noise(0.9), 300, 2500) * np.sin(np.pi * t / 0.9) ** 2)
# --- Fliehkraftregler: Ratsche, schneller werdend, dann Klack
rat = np.zeros(int(SR * 1.4)); tt, k = 0.0, 0
while tt < 1.15:
    place(rat, hp(noise(0.015), 1500) * np.exp(-T(0.015) * 220) * 0.7 + np.sin(2 * np.pi * 900 * T(0.015)) * np.exp(-T(0.015) * 200) * 0.3, tt); tt += max(0.03, 0.12 - k * 0.006); k += 1
place(rat, (bp(noise(0.12), 300, 2500) + np.sin(2 * np.pi * 220 * T(0.12))) * np.exp(-T(0.12) * 30), 1.2)
save("ratchet", rat)
# --- Keile in den Schienen: Kreischen + Stopp-Schlag
t = T(1.6); f = 2100 - 700 * t / 1.6 + 60 * np.sin(2 * np.pi * 13 * t)
scr = (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + np.sin(2 * np.pi * np.cumsum(f * 1.51) / SR) * 0.2 + bp(noise(1.6), 1500, 7000) * 0.5) * np.minimum(1, t / 0.03) * np.exp(-np.maximum(0, t - 1.0) * 6)
stop = np.zeros(len(t)); place(stop, np.sin(2 * np.pi * np.cumsum(90 * np.exp(-T(0.5) * 5) + 40) / SR) * np.exp(-T(0.5) * 7) * 1.4 + lp(noise(0.5), 1200) * np.exp(-T(0.5) * 12), 1.05)
save("brake_screech", reverb(scr + stop, 0.3, 0.6))
# --- Flugzeug im Nebel (tiefes Propeller-Droehnen, naeherkommend)
t = T(4.0); amp = np.minimum(1, (t / 3.6) ** 2)
prop = (np.sin(2 * np.pi * 72 * t) * 0.5 + np.sin(2 * np.pi * 144 * t) * 0.3 + lp(noise(4), 500) * 0.6) * (0.75 + 0.25 * np.sin(2 * np.pi * 18 * t))
save("plane", fade(prop * amp, 0.2, 0.05))
# --- Einschlag (tiefer Boom + Rauschfahne)
t = T(3.0); boom = np.sin(2 * np.pi * np.cumsum(34 + 80 * np.exp(-t * 4)) / SR) * np.exp(-t * 1.3)
save("impact", reverb(boom + lp(noise(3.0), 1400) * np.exp(-t * 2.2) * 0.6 + hp(noise(3.0), 2000) * np.exp(-t * 18) * 0.5, 0.4, 1.4))
# --- Gedaempfter Aufprall (Luftkissen): tiefer Plumps + Staub
t = T(1.8); save("thud", reverb(np.sin(2 * np.pi * np.cumsum(60 * np.exp(-t * 3) + 30) / SR) * np.exp(-t * 3.5) + lp(noise(1.8), 600) * np.exp(-t * 4) * 0.5, 0.3, 0.8))
# --- Luftdruck-Heulen unter der Kabine (Kompression)
t = T(4.0); f = 140 + 260 * (t / 4) ** 2
save("air_press", fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35 + bp(noise(4), 120, 900) * 0.9 * (t / 4), 0.3, 0.15))
# --- Pop fuer Zaehler-Wechsel
t = T(0.12); save("pop", np.sin(2 * np.pi * np.cumsum(500 + 900 * t / 0.12) / SR) * np.exp(-t * 35))
# --- Kabinen-Brummen
t = T(6); save("hum", fade(lp(noise(6), 180) * 0.6 + np.sin(2 * np.pi * 58 * t) * 0.25, 0.3, 0.5))

# --- Musik 1: Spannungs-Puls (A-B), 140 bpm, Sub + Ostinato + steigende Streicher-Flaeche
dur = 20; m1 = np.zeros(int(SR * dur)); beat = 60 / 140
for i in range(int(dur / beat)):
    tt = T(0.3); place(m1, np.sin(2 * np.pi * 49 * tt) * np.exp(-tt * 9) * 0.9, i * beat)
    place(m1, tone([392, 466.2, 392, 587.3][i % 4] * (1 if i < 16 else 2 ** (1 / 12) if i < 32 else 2 ** (2 / 12)), beat * 0.9, 0.16, 6), i * beat)
    if i % 2: place(m1, hp(noise(0.03), 5000) * np.exp(-T(0.03) * 120) * 0.25, i * beat)
t = T(dur); m1 += sum(np.sin(2 * np.pi * f * t * (1 + 0.06 * t / dur)) for f in (196, 233.1, 293.7)) * 0.05 * (t / dur)
save("music_tension", fade(m1, 0.02, 0.3), "audio", 0.75)
# --- Musik 2: ruhig-ueberlegen (C), Dur-Arpeggio
dur = 12; m2 = np.zeros(int(SR * dur)); beat = 60 / 100 / 2
arp = [261.6, 329.6, 392, 523.2, 392, 329.6]
for i in range(int(dur / beat)): place(m2, tone(arp[i % 6] * (1 if (i // 12) % 2 == 0 else 1.122), beat * 2.5, 0.14, 3.5), i * beat)
t = T(dur); m2 += sum(np.sin(2 * np.pi * f * t) for f in (130.8, 196)) * 0.06
save("music_calm", reverb(fade(m2, 0.4, 0.6), 0.35, 0.8), "audio", 0.65)
# --- Musik 3: ernstes Thema (D), Moll-Pad + tiefe Glocke
dur = 13; t = T(dur); m3 = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((110, 0.35), (130.8, 0.25), (164.8, 0.25), (220, 0.12))) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t))
for k in range(0, dur, 3): place(m3, tone(55, 3, 0.6, 1.2) + tone(220, 3, 0.15, 1.6), k)
save("music_serious", reverb(fade(m3, 1.0, 1.0), 0.4, 1.0), "audio", 0.65)

# --- CC0
F = LIB / "sfx" / "cc0_footsteps_impacts"
ogg(LIB / "sfx" / "kenney_ui_audio" / "click3.wav", "button_click")
ogg(F / "bell_02.ogg", "ding")
ogg(F / "door_close_02.ogg", "doors_close")
ogg(F / "explosion.ogg", "explosion")
ogg(F / "metal_04.ogg", "metal_hit")
print("ok")
