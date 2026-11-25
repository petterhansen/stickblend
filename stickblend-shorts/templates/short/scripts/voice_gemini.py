"""Generate voiceover via Gemini TTS and align word timestamps via faster-whisper.

Usage:
  python scripts/voice_gemini.py [--skip-tts] [--script script.json] [--whisper-model small]

Outputs:
  audio/voice.raw.wav   (normalized 44.1 kHz before tempo)
  audio/voice.wav       (tempo-adjusted final voiceover)
  timeline.json         (scene start/end/dur + per-word timestamps)
"""
import argparse
import base64
import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent


def get_api_key() -> str:
    env_val = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_val:
        return env_val
    candidates = [
        ROOT / ".env",
        ROOT.parent / ".env",
        ROOT.parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.+)", line)
                if m:
                    return m.group(1).strip().strip("\"'")
    sys.exit("GEMINI_API_KEY not found in environment or .env")


# ---- Pausen-Werkzeuge (Gemini haengt manchmal ~1 s Stille mitten in Saetze, Pausen nur in echte Stille setzen)
def _read_wav(p):
    import numpy as np, wave
    with wave.open(str(p)) as w:
        prm = w.getparams(); x = np.frombuffer(w.readframes(prm.nframes), np.int16).reshape(-1, prm.nchannels)
    return prm, x


def _write_wav(p, prm, y):
    import wave
    with wave.open(str(p), "wb") as w:
        w.setparams(prm); w.writeframes(y.astype("int16").tobytes())


def _env_db(x, sr, win=0.02):
    import numpy as np
    n = int(sr * win); m = x.astype(np.float32).mean(axis=1); k = len(m) // n
    return 20 * np.log10(np.sqrt((m[: k * n].reshape(k, n) ** 2).mean(axis=1)) / 32768 + 1e-9), n


def trim_long_silences(wav, max_keep=0.4, longer_than=0.5, thr=-40):
    """Stille > longer_than s (unter thr dB) in der Mitte auf max_keep s kuerzen. Rueckgabe: gekuerzte Sekunden."""
    import numpy as np
    prm, x = _read_wav(wav); sr = prm.framerate; db, hop = _env_db(x, sr)
    quiet = db < thr; keep = np.ones(len(x), bool); i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            dur = (j - i) * hop / sr
            if dur > longer_than and i > 0 and j < len(quiet):
                cut = int((dur - max_keep) * sr); a = i * hop + (int((j - i) * hop) - cut) // 2; keep[a: a + cut] = False
            i = j
        else:
            i += 1
    _write_wav(wav, prm, x[keep]); return (~keep).sum() / sr


def insert_pauses(wav, pauses, times, script_words, lines, thr=-40):
    """pauses: [{"line": id, "after": wortanfang, "sec": 0.4}] -> Gesamtpause nach dem Wort.
    Sucht im Fenster +-0.35 s die laengste echte Stille und ergaenzt nur die fehlende Dauer (nie mitten im Wort).
    Gibt verschobene times zurueck."""
    import numpy as np
    pz = []
    for p in pauses:
        li = [i for i, l in enumerate(lines) if l["id"] == p["line"]][0]
        ks = [k for k, (l_, w) in enumerate(script_words) if l_ == li and norm(w).startswith(norm(p["after"]))]
        if not ks: print("Pause: Wort nicht gefunden", p); continue
        k = ks[0]; c0 = (times[k][1] + times[k + 1][0]) / 2 if k + 1 < len(times) else times[k][1]
        prm, x = _read_wav(wav); db, hop = _env_db(x, prm.framerate, 0.01)
        lo, hi = int((c0 - 0.35) * prm.framerate / hop), int((c0 + 0.35) * prm.framerate / hop)
        q = db[max(0, lo): hi] < thr; best, bl, i = None, 0, 0
        while i < len(q):
            if q[i]:
                j = i
                while j < len(q) and q[j]: j += 1
                if j - i > bl: best, bl = (i + j) // 2, j - i
                i = j
            else:
                i += 1
        if best is None: print("Pause: keine Stille nach", p["after"]); continue
        add = p["sec"] - bl * hop / prm.framerate
        if add > 0.03: pz.append(((max(0, lo) + best) * hop / prm.framerate, add))
    if not pz: return times, 0.0
    prm, x = _read_wav(wav); out, last = [], 0
    for cut, sec in sorted(pz):
        c = int(cut * prm.framerate); out += [x[last:c], np.zeros((int(sec * prm.framerate), prm.nchannels), np.int16)]; last = c
    out.append(x[last:]); _write_wav(wav, prm, np.concatenate(out))
    sh = lambda t_: t_ + sum(sec for cut, sec in pz if t_ >= cut)
    return [(sh(a_), sh(b_)) for a_, b_ in times], sum(s_ for _, s_ in pz)


def norm(s: str) -> str:
    return re.sub(r"[^\w]", "", s.lower())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tts", action="store_true", help="Reuse audio/voice.raw.wav and re-run tempo + alignment")
    ap.add_argument("--script", default="script.json", help="Script JSON relative to project root")
    ap.add_argument("--whisper-model", default="small", help="faster-whisper model size")
    args = ap.parse_args()

    cfg = json.loads((ROOT / args.script).read_text(encoding="utf-8"))
    audio_dir = ROOT / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav = audio_dir / "voice.wav"
    raw_wav = audio_dir / "voice.raw.wav"

    full_text = " ".join(line["text"] for line in cfg["lines"])
    style = cfg.get("style", "").strip()
    # Neuere TTS-Modelle lesen eine vorangestellte Stilanweisung sonst mit vor -> Regie und Transkript trennen
    prompt_text = (f"### DIRECTOR'S NOTES\n{style}\n\n"
                   "Read ONLY the transcript below, word for word. Do not read the director's notes aloud.\n\n"
                   f"#### TRANSCRIPT\n{full_text}") if style else full_text

    if not args.skip_tts:
        api_key = get_api_key()
        body = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": cfg.get("voice", "Charon")}
                    }
                },
            },
        }
        model = cfg.get("model", "gemini-3.8-flash-tts")
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", errors="replace")
                if e.code in (429, 400) and attempt < 3 and "PerDay" not in msg:
                    print(f"TTS {e.code}, retrying in 65s...")
                    time.sleep(65)
                    continue
                sys.exit(f"TTS error {e.code}: {msg[:400]}")

        if "content" not in data["candidates"][0]:   # sporadisch kein Audio (finishReason OTHER): einmal neu anfragen
            print("No audio:", data["candidates"][0].get("finishReason"), "- retrying")
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
        part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
        raw_bytes = base64.b64decode(part["data"])
        if "wav" in part["mimeType"]:
            src_file = wav.with_suffix(".src.wav")
            src_file.write_bytes(raw_bytes)
            src_args = ["-i", str(src_file)]
        else:
            src_file = wav.with_suffix(".pcm")
            src_file.write_bytes(raw_bytes)
            src_args = ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(src_file)]

        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", *src_args,
                "-af",
                "silenceremove=start_periods=1:start_threshold=-45dB,"
                "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                "loudnorm=I=-14:TP=-1.5",
                "-ar", "44100", str(raw_wav),
            ],
            check=True,
        )

    # Tempo: am besten 1.0 (Rohaufnahme unveraendert, kein Roboterklang). Zeitdehnung nur minimal per Rubberband.
    tempo = float(cfg.get("tempo", 1.0))
    if abs(tempo - 1.0) < 1e-3:
        import shutil
        shutil.copyfile(raw_wav, wav)
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(raw_wav), "-af",
             f"rubberband=tempo={tempo}:pitchq=quality:formant=preserved:transients=smooth:window=long", str(wav)],
            check=True,
        )

    print(f"Long silences trimmed: {trim_long_silences(wav):.2f}s")

    from faster_whisper import WhisperModel

    m = WhisperModel(args.whisper_model, device="cpu", compute_type="int8")
    lang = cfg.get("language", "en")
    init_prompt = cfg.get("initial_prompt", "") or None
    segs, _ = m.transcribe(str(wav), language=lang, word_timestamps=True, initial_prompt=init_prompt)
    heard = [w for s in segs for w in s.words]

    script_words = []
    for i, line in enumerate(cfg["lines"]):
        for w in line["text"].split():
            script_words.append((i, w))

    a = [norm(w) for _, w in script_words]
    b = [norm(w.word) for w in heard]
    times = [None] * len(a)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (heard[blk.b + k].start, heard[blk.b + k].end)

    total = float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)]
        ).strip()
    )
    known = [i for i, t in enumerate(times) if t is not None]
    for i, t in enumerate(times):
        if t is not None:
            continue
        prv = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        s = times[prv][1] if prv is not None else 0.0
        e = times[nxt][0] if nxt is not None else total
        gap = [k for k in range(len(a)) if (prv is None or k > prv) and (nxt is None or k < nxt)]
        j = gap.index(i)
        step = (e - s) / max(1, len(gap))
        times[i] = (s + j * step, s + (j + 1) * step)

    times, added = insert_pauses(wav, cfg.get("pauses", []), times, script_words, cfg["lines"])
    total += added
    print(f"Matched {len(known)}/{len(a)} words, duration {total:.2f}s")

    lines_out = []
    for i, line in enumerate(cfg["lines"]):
        idx = [k for k, (li, _) in enumerate(script_words) if li == i]
        words_out = [
            {"w": script_words[k][1], "s": round(times[k][0], 3), "e": round(times[k][1], 3)}
            for k in idx
        ]
        lines_out.append({"id": line["id"], "text": line["text"], "words": words_out})

    for i, line in enumerate(lines_out):
        line["start"] = 0.0 if i == 0 else round(max(0.0, line["words"][0]["s"] - 0.08), 3)
    for i, line in enumerate(lines_out):
        line["end"] = lines_out[i + 1]["start"] if i + 1 < len(lines_out) else round(total + 0.9, 3)
        line["dur"] = round(line["end"] - line["start"], 3)

    tl = {"fps": 30, "total": lines_out[-1]["end"], "audio": "audio/voice.wav", "lines": lines_out}
    (ROOT / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")
    for line in lines_out:
        print(f"{line['id']:12} {line['start']:6.2f} {line['dur']:5.2f}  {line['text'][:55]}")


if __name__ == "__main__":
    main()
