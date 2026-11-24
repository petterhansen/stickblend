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
    prompt_text = f"{style}: {full_text}" if style else full_text

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
        model = cfg.get("model", "gemini-2.5-flash-preview-tts")
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

    tempo = float(cfg.get("tempo", 1.0))
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(raw_wav), "-af", f"atempo={tempo}", str(wav)],
        check=True,
    )

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
