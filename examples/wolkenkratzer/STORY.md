# Wolkenkratzer – 15 Stockwerke Nichts

9:16 · 30 fps · ca. 63 s · ein durchgehender Kameraflug (fünf Blender-Sets, Übergänge an Wänden, Gittern und Glas).

## Ablauf
9:16 · 30 fps · ca. 66 s. Die Set-Grenzen hängen an Wörtern (shots.py/Short.tsx), damit sich eine neue Sprachspur automatisch anpasst.

| Set | Zeit (s) | Inhalt |
|---|---|---|
| A | 0–11.9 | Marmor-Lobby → Goldkabine → Tastenfeld 22–30, verschraubte Blende, 46–60 → „Du“ drückt 60 → Türen schließen, Kamera durch den Spalt in die Rückwand |
| B | 11.9–16.0 | Schacht ab Etage 25: Zahlen rasen vorbei, ab 31 blanker Beton → Lüftungsgitter (z = 140 m = 32 m über Etage 31) |
| C | 16.0–38.9 | Drop ins Dunkel: 50-m-Betonhöhle nur mit Lichtstreifen; Taube auf Mini-Campingstuhl vor Mini-Röhren-TV; Bauprüfer klopft, „Technikraum? Sieht gut aus.“, Stempel GENEHMIGT auf dem Klemmbrett |
| D | 38.9–57.0 | Skyline, Röntgen-Turm, Wohnblock fällt in die Gasse („Du“ am Fenster, Schwenk auf die graue Nachbarwand), Kisten „TECHNIK = 0 m² WOHNFLÄCHE“ heben ihn hoch |
| E | 57.0–66.3 | Eingerichtetes Penthouse mit Glasfront, Aufzugtür öffnet (Akkord-Schlag), Blick, dann durch den Glasboden: Taube auf Kiste „ETAGE 31–45 · BESITZER: TAUBE“ → harter Schnitt |

Untertitel: 2–4 Wörter, Satzzeichen bleiben, Zahlen als Ziffern, ẞ in Großschrift.

## Befehle
```
python scripts/voice_gemini.py           # Stimme + Wort-Timings (src/timeline.de.json)
python scripts/pigeon.py                 # Tauben-Sprites
python scripts/audio.py                  # Effekte, Atmos, Musikteile
bash blender/render_all.sh               # alle Sets final -> public/bl/onetake.mp4
blender -b --factory-startup -P wolkenkratzer/blender/run.py -- C preview still:1000,1060   # Vorschau
npx remotion render src/index.ts Wolkenkratzer out/wolkenkratzer.mp4
```

## Hinweise
- Fakten: Die Grundidee stimmt (NYC zählt Technikgeschosse nicht zur Geschossfläche; Türme wie 432 Park Ave. und Central Park Tower nutzen hohe „mechanical voids“; die Stadt hat das 2019 begrenzt). Konkrete Zahlen im Skript (15 Etagen, 30 → 46, 50 m, 50 Mio. $) sind zugespitzt.
- Musik 36–55 s: „Sneaky Snitch“ von Kevin MacLeod (incompetech.com), CC BY 4.0. Gehört in die Videobeschreibung. Alle anderen Musikteile und Atmos sind synthetisch; die Effekte stammen aus CC0-Paketen (Kenney/OGA).
