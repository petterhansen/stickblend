# <Titel> – One-Take-Short

9:16 · 30 fps · Ziel 30–55 s (max. 60). Ein durchgehender Kameraflug, gerendert in Sets über globale Frames.
Vollständige Vorbilder: `examples/aufzug` (What-If, Zähler, Röntgen, Freeze/Rückspulen, Loop) und `examples/wolkenkratzer`.

## Hook-Frame (0,0 s)
Was ist auf Bild 1 zu sehen, das schon *läuft* (Fall, Riss, Knall)? Welcher Ton liegt auf Frame 1? Welcher Zähler startet?
Satz 1 = Lage in Du-Form/Präsens, keine Frage. Das Thumbnail-Motiv steckt in diesem Bild.

## Ablauf
| Set | Zeit (s) | Sprechtext | Bild / Kamera | Übergang ins nächste Set |
|---|---|---|---|---|
| A | 0– | | | durch Tür/Gitter/Glas – **nie durch eine Wand** |
| B | | | | |
| … | | Schluss führt zurück zum Anfang (Loop) | letztes Bild ≈ erstes Bild | harter Schnitt |

Pattern-Interrupts alle 2–4 s (neue Perspektive, Ortswechsel, SFX, Text-Pop) hier mit Zeiten notieren.

## Fakten und Zuspitzungen
Belegt (mit Quelle) / zugespitzt / ungeprüft – Ungeprüftes vor dem Upload klären oder streichen.

## Befehle
```powershell
python scripts/fake_timeline.py              # Platzhalter-Zeitachse zum Blocken (ohne TTS)
python scripts/voice_gemini.py [--skip-tts]  # echte Stimme + Wort-Zeiten -> src/timeline.json
python scripts/audio.py                      # Effekte + Musik -> public/sfx, public/audio
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -P blender/run.py -- A preview still:1,60,120
.\blender\render_all.ps1 -Preset preview -Spp 4   # Bewegungs-Vorschau -> out/preview.mp4 (Kontaktbogen ansehen!)
.\blender\render_all.ps1                          # final -> public/bl/onetake.mp4 (fortsetzbar)
npm install; npx remotion render src/index.ts Short out/short.mp4
python ..\stickblend\tools\safezone_check.py out/short.mp4 --step 1.5
```
