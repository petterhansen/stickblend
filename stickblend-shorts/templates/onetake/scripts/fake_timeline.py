"""Platzhalter-Zeitachse ohne TTS: verteilt die Woerter aus script.json gleichmaessig (2.6 Woerter/s).
Damit lassen sich Kamera und Sets schon blocken, bevor die echte Stimme existiert (danach voice_gemini.py)."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "script.json").read_text(encoding="utf-8"))
t, lines = 0.0, []
for l in cfg["lines"]:
    ws = []
    for w in l["text"].split():
        if not any(c.isalnum() for c in w): continue
        ws.append({"w": w, "s": round(t, 3), "e": round(t + 0.32, 3)}); t += 1 / 2.6 + (0.25 if w[-1] in ".:?!" else 0)
    lines.append({"id": l["id"], "text": l["text"], "words": ws})
for i, l in enumerate(lines):
    l["start"] = 0.0 if i == 0 else l["words"][0]["s"] - 0.08
for i, l in enumerate(lines):
    l["end"] = lines[i + 1]["start"] if i + 1 < len(lines) else round(t + 0.9, 3); l["dur"] = round(l["end"] - l["start"], 3)
(ROOT / "src").mkdir(exist_ok=True)
(ROOT / "src" / "timeline.json").write_text(json.dumps({"fps": 30, "total": lines[-1]["end"], "audio": "audio/voice.wav", "lines": lines, "fake": True}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Platzhalter-Zeitachse: {t:.1f} s")
