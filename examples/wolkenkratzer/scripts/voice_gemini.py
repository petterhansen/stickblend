"""Ein Gemini-TTS-Aufruf fuer den ganzen Text -> public/audio/voice.wav
Danach Whisper-Ausrichtung -> src/timeline.json (Zeilen + Wort-Timings).
Aufruf: python scripts/voice_gemini.py [--skip-tts]"""
import sys, json, base64, urllib.request, urllib.error, subprocess, pathlib, re, difflib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gkey import key

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "script.de.json").read_text(encoding="utf-8"))
WAV = ROOT / "public" / "audio" / "voice.wav"
RAW = ROOT / "public" / "audio" / "voice.raw.wav"
WAV.parent.mkdir(parents=True, exist_ok=True)
full = " ".join(l["text"] for l in cfg["lines"])

if "--skip-tts" not in sys.argv:
    body = {"contents": [{"parts": [{"text": f"{cfg['style']}: {full}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": cfg["voice"]}}}}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key()})
    import time
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: d = json.loads(r.read()); break
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            # 429 = Minutenlimit im Free Tier, 400 = Modell wollte Text erzeugen (sporadisch): kurz warten, nochmal
            if e.code in (429, 400) and attempt < 3 and "PerDay" not in msg:
                print(f"TTS {e.code}, neuer Versuch in 65 s"); time.sleep(65); continue
            sys.exit(f"TTS-Fehler {e.code}: {msg[:400]}")
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    raw = base64.b64decode(part["data"])
    if "wav" in part["mimeType"]:
        (WAV.with_suffix(".src.wav")).write_bytes(raw); src = ["-i", str(WAV.with_suffix(".src.wav"))]
    else:
        (WAV.with_suffix(".pcm")).write_bytes(raw); src = ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(WAV.with_suffix(".pcm"))]
    # Stille am Anfang/Ende kappen, leicht lauter
    subprocess.run(["ffmpeg", "-y", "-v", "error", *src, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-14:TP=-1.5",
                    "-ar", "44100", str(RAW)], check=True)
# Tempo anheben (Tonhoehe bleibt)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(RAW), "-af", f"atempo={cfg.get('tempo', 1.0)}", str(WAV)], check=True)

# ---- lange natuerliche Pausen kuerzen (Gemini haengt manchmal ~1 s Stille mitten in Saetze)
import numpy as np, wave
def _read(p):
    with wave.open(str(p)) as w_: prm = w_.getparams(); x = np.frombuffer(w_.readframes(prm.nframes), np.int16).reshape(-1, prm.nchannels)
    return prm, x
def _write(p, prm, y):
    with wave.open(str(p), "wb") as w_: w_.setparams(prm); w_.writeframes(y.astype(np.int16).tobytes())
def _env(x, sr, win=0.02):
    n = int(sr * win); m = x.astype(np.float32).mean(axis=1); k = len(m) // n
    return 20 * np.log10(np.sqrt((m[:k * n].reshape(k, n) ** 2).mean(axis=1)) / 32768 + 1e-9), n
prm, x = _read(WAV); sr = prm.framerate; db, hop = _env(x, sr)
quiet = db < -40; keep = np.ones(len(x), bool); i = 0; MAXS = 0.4
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]: j += 1
        dur = (j - i) * hop / sr
        if dur > 0.5 and i > 0 and j < len(quiet):   # Mitte der Stille herausschneiden
            cut = int((dur - MAXS) * sr); a = i * hop + (int((j - i) * hop) - cut) // 2; keep[a:a + cut] = False
        i = j
    else: i += 1
_write(WAV, prm, x[keep]); print(f"Stille gekuerzt: {(~keep).sum() / sr:.2f}s")

# ---- Whisper-Ausrichtung ----
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(str(WAV), language="de", word_timestamps=True, initial_prompt=cfg.get("initial_prompt", ""))
heard = [w for s in segs for w in s.words]
norm = lambda s: re.sub(r"[^\wäöüß]", "", s.lower())
script_words = []  # (line_idx, word)
for i, l in enumerate(cfg["lines"]):
    for w in l["text"].split():
        if norm(w): script_words.append((i, w))
a = [norm(w) for _, w in script_words]; b = [norm(w.word) for w in heard]
times = [None] * len(a)
for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
    for k in range(blk.size): times[blk.a + k] = (heard[blk.b + k].start, heard[blk.b + k].end)
# Luecken interpolieren
total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(WAV)]).strip())
known = [i for i, t in enumerate(times) if t]
for i, t in enumerate(times):
    if t: continue
    prv = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
    s = times[prv][1] if prv is not None else 0.0
    e = times[nxt][0] if nxt is not None else total
    gp = [k for k in range(len(a)) if (prv is None or k > prv) and (nxt is None or k < nxt)]
    j = gp.index(i); step = (e - s) / len(gp)
    times[i] = (s + j * step, s + (j + 1) * step)
pz = []
for p in cfg.get("pauses", []):
    li = [i for i, l in enumerate(cfg["lines"]) if l["id"] == p["line"]][0]
    k = [k for k, (l_, w) in enumerate(script_words) if l_ == li and norm(w).startswith(p["after"])][0]
    c0 = (times[k][1] + times[k + 1][0]) / 2 if k + 1 < len(times) else times[k][1]
    prm_, x_ = _read(WAV); db_, hop_ = _env(x_, prm_.framerate, 0.01)
    lo, hi = int((c0 - 0.35) * prm_.framerate / hop_), int((c0 + 0.35) * prm_.framerate / hop_)
    seg = db_[max(0, lo):hi]; q = seg < -40
    # laengsten stillen Abschnitt im Fenster suchen; dessen Laenge zaehlt schon als Pause
    best, bl, i = None, 0, 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]: j += 1
            if j - i > bl: best, bl = (i + j) // 2, j - i
            i = j
        else: i += 1
    if best is None: print("keine Stille fuer Pause nach", p["after"]); continue
    have = bl * hop_ / prm_.framerate; add = p["sec"] - have
    if add > 0.03: pz.append(((max(0, lo) + best) * hop_ / prm_.framerate, add))
if pz:
    with wave.open(str(WAV)) as w_: prm = w_.getparams(); x = np.frombuffer(w_.readframes(prm.nframes), np.int16).reshape(-1, prm.nchannels)
    out, last = [], 0
    for cut, sec in sorted(pz):
        c = int(cut * prm.framerate); out += [x[last:c], np.zeros((int(sec * prm.framerate), prm.nchannels), np.int16)]; last = c
    out.append(x[last:]); y = np.concatenate(out)
    with wave.open(str(WAV), "wb") as w_: w_.setparams(prm); w_.writeframes(y.tobytes())
    sh = lambda t_: t_ + sum(sec for cut, sec in pz if t_ >= cut)
    times = [(sh(a_), sh(b_)) for a_, b_ in times]; total += sum(s for _, s in pz)
print(f"gematcht: {len(known)}/{len(a)} Woerter, Dauer {total:.2f}s")

lines = []
for i, l in enumerate(cfg["lines"]):
    idx = [k for k, (li, _) in enumerate(script_words) if li == i]
    words = [{"w": script_words[k][1], "s": round(times[k][0], 3), "e": round(times[k][1], 3)} for k in idx]
    lines.append({"id": l["id"], "text": l["text"], "words": words})
for i, l in enumerate(lines):
    l["start"] = 0.0 if i == 0 else round(l["words"][0]["s"] - 0.08, 3)
for i, l in enumerate(lines):
    l["end"] = lines[i + 1]["start"] if i + 1 < len(lines) else round(total + 0.9, 3)
    l["dur"] = round(l["end"] - l["start"], 3)
(ROOT / "src" / "timeline.de.json").write_text(json.dumps({"fps": 30, "total": lines[-1]["end"], "audio": "audio/voice.wav", "lines": lines}, ensure_ascii=False, indent=1), encoding="utf-8")
for l in lines: print(f"{l['id']:8} {l['start']:6.2f} {l['dur']:5.2f}  {l['text'][:50]}")
