# Beispiel-Shorts (vollständig, reproduzierbar)

Zwei fertige One-Take-Shorts als Vorbilder für Szenencode, Kamera, Zähler, Ton und Untertitel.
Neue Shorts mit `.\stickblend-shorts\new_short.ps1 -Slug <name> -Template onetake` anlegen und sich hier abschauen, wie es fertig aussieht.

| Projekt | Länge | Zeigt |
|---|---|---|
| `aufzug/` | 47,7 s | What-If „mitten im Geschehen“, Zähler ab Frame 1, fahrende Kabine (`flat.attach`), Röntgen-Blende, Freeze + Rückspulen, Fliehkraftregler/Keile mit Funken, 1945-Nebelstadt mit Bomber, Lobby-Loop zum Anfang |
| `wolkenkratzer/` | 64 s | Lobby → Schacht → Betonhöhle → Skyline → Penthouse, Requisiten in 2.5D-Händen (`flat_pt`: Becher, Klemmbrett, Stempel), Billboard-Taube, Poly-Haven-Möbel |

`aufzug/blender/az.py` nutzt Bausteine aus `wolkenkratzer/blender/wk.py` (Kabine, Lobby, Materialien).

## Nachbauen
```powershell
.\setup.ps1                                   # einmalig: Remotion, Ton-Bibliothek, Poly-Haven-Assets (inkl. der Beispiel-Assets)
cd examples\aufzug
python scripts\audio.py                       # Effekte + Musik (deterministisch)
.\blender\render_all.ps1 -Preset preview -Spp 4   # schnelle Vorschau -> out\preview.mp4
.\blender\render_all.ps1                      # final -> public\bl\onetake.mp4 (fortsetzbar, ca. 10-35 min je nach GPU-Last)
npm install; npx remotion render src/index.ts Aufzug out\aufzug.mp4
```
Stimme und Wort-Zeitachse liegen bei (`public/audio/voice.wav`, `src/timeline.de.json`). Gemini-TTS ist nicht deterministisch:
`python scripts\voice_gemini.py` erzeugt eine neue Stimme, Sets und Kamera verschieben sich dann automatisch mit (alles hängt an Wörtern).

Wolkenkratzer: die Tauben-Sprites liegen in `blender/img/` (neu zeichnen: `python scripts\pigeon.py`).
Musik „Sneaky Snitch“ (Kevin MacLeod, CC BY 4.0) wird im Wolkenkratzer genutzt – Credit in die Videobeschreibung.
