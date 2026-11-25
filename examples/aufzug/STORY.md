# Aufzug – Das Seil ist gerissen

9:16 · 30 fps · ca. 47,6 s (Stimme Fenrir, laut/klar/emotional, Tempo 1.3).
Format: What-If **mitten im Geschehen**: Du-Form, Präsens, Zähler ab Frame 1, Loop am Ende.
Ein durchgehender Kameraflug wie beim Wolkenkratzer; Kabine, Schacht und Tastenfeld werden aus `wolkenkratzer/blender/wk.py` übernommen.

## Hook-Frame (0,0 s)
Innenraum der Goldkabine, leicht schräg von oben. „Du“ hängt **schon** 10 cm über dem Boden, der Kaffeebecher schwebt vor dem Gesicht, ein Tropfen Kaffee löst sich als Kugel. Durch den Dachspalt fallen Funken, das Licht flackert rot.
- Etagenanzeige über der Tür rast: **80 → 79 → 78…**
- Zähler links oben (in der Safe-Zone): **⏱ 8,0 s**, rot, zählt sichtbar runter.
- Ton auf Frame 1: metallisches *TWANG*, Alarmglocke, Windheulen im Schacht.
Das ist zugleich das Thumbnail-Motiv (Text: „SPRINGEN?“).

## Ablauf
| Set | ca. Zeit (s) | Sprechtext | Bild |
|---|---|---|---|
| A | 0–4,5 | „Das Seil ist gerissen. Du bist im 80. Stock – und hast acht Sekunden.“ | Hook-Frame; Kamera dreht langsam um „Du“ (≤ 40°/s), Anzeige rast |
| A | 4,5–9 | „Dein Kaffee schwebt, deine Füße heben ab …“ | Nahaufnahme Becher, Kaffeekugel, Füße lösen sich; Zähler 6,x s |
| B | 9–19 | „Kurz vor dem Aufprall springen? …“ | Kamera gleitet durch die Kabinenwand in einen **Röntgen-Schnitt**: Schacht seitlich, Kabine als Glaskasten im Fall. „Du“ strampelt, findet keinen Halt. Tacho-Zähler **275 km/h**; Sprung-Pfeil zieht ihn auf **265** – rot durchgestrichen |
| B | 19–23 | „Flach hinlegen verteilt den Aufprall …“ | „Du“ liegt flach, Kraftpfeile verteilen sich über den Körper, Tacho bleibt rot; Grubenboden kommt näher (Zähler 0,8 s) |
| C | 23–34 | „**Aber:** Das passiert dir nicht. …“ | **Freeze**: Bild stoppt auf 0,4 s (Musik-Drop, Uhr-Ticken). Rückspul-Whoosh, Kamera fährt rückwärts am Seilbündel hoch: **7 Seile** intakt, eins lose. Ganz oben dreht der **Fliehkraftregler**, Gewichte klappen aus → Seil zieht die **Stahlkeile** an der Kabine in die Führungsschienen, Funkenregen, Stopp. Zähler: **1 m** (grün) |
| D | 34–47 | „Nur einmal versagte alles: 1945 …“ | Ortswechsel: Nacht, dichter Nebel, Art-déco-Turm in kräftigem Blau/Orange (keine Sepia – Farbregel). Schatten eines Bombers im Nebel, Einschlag im 79. Stock, Feuerball. Schnitt in den Schacht: Kabine fällt, Zähler **75 Stockwerke**. Luftkompression als blaue Druckwellen unter der Kabine; unten liegt das abgerissene Seil als Spirale. Aufschlag gedämpft, Staub; Einblendung „BETTY LOU OLIVER · 1945 · ÜBERLEBT“ (Guinness-Rekord) |
| L | 43,8–47,6 | „Also: keine Panik. Du steigst ein, drückst die Achtzig – und …“ | Lobby: Du kommt mit Kaffee herein, drückt 80, grinst in die Kamera, Türen schließen → harter Schnitt = **Loop** zum Hook-Frame („Das Seil ist gerissen.“) |

Pattern-Interrupts: Funken/Anzeige (0–4), Kaffeekugel (5), Durchflug Wand → Röntgen (9), Tacho-Sprung (15), Hinlegen (19), Freeze + Rückspulen (23), Regler (27), Keile + Funken (31), Ortswechsel 1945 (34), Einschlag (37), Schacht (40), Seilspirale (44), Einblendung (46), Loop (49).

## Zähler (Remotion-Overlay)
- Position links oben unter der Notch-Aussparung: x 60–300, y 220–320 (aus `stickblend/assets/safezone.json`).
- Modus je Set: Restzeit (A) → km/h (B) → Meter (C, grün) → Stockwerke (D).
- Jeder Moduswechsel mit kurzem Pop + Tick-SFX.

## Ton
- Musik: pulsierende Spannung (A–B), **harter Drop** auf „Aber“, ruhiger Synth bei C, ernstes Thema ab 1945, Stille vor dem Loop-TWANG.
- SFX: Seil-Twang, Alarmglocke, Schachtwind, Funken, Tick, Rückspul-Whoosh, Regler-Ratsche, Keil-Kreischen, Flugzeugdröhnen, Einschlag, gedämpfter Aufprall.

## Fakten und Zuspitzungen
- 80. Stock ≈ 300 m, freier Fall ohne Bremsung ≈ 7,8 s und ≈ 275 km/h (Luftwiderstand ignoriert). Ein guter Sprung schafft ≈ 3 m/s ≈ 10 km/h.
- Im freien Fall bist du schwerelos, du hast keinen Boden zum Abstoßen.
- Hochhausaufzüge hängen an mehreren Seilen; jedes ist für sich stark genug (zugespitzt als „jedes hält die Kabine allein“).
- Fangbremse nach Otis, 1854 im New Yorker Crystal Palace vorgeführt: Bei Übergeschwindigkeit löst der Geschwindigkeitsbegrenzer (Fliehkraftregler) aus und klemmt Keile an die Führungsschienen. „Einen Meter“ ist eine Zuspitzung für „wenige Meter“.
- 28. Juli 1945: Ein B-25-Bomber trifft im Nebel den 79. Stock des Empire State Building. Betty Lou Oliver (20, Liftführerin) stürzt etwa 75 Stockwerke und überlebt schwer verletzt; Guinness-Rekord für den längsten überlebten Aufzugsturz. Als Gründe werden das Luftpolster im engen Schacht und das am Boden aufgehäufte Seil genannt. Die Quellen nennen 75 oder 80 Stockwerke.
- Schluss ohne Betty-Behauptung: der Loop-Satz („Du steigst ein …“) ist reine Erzählung.

## Veröffentlichung
- Titel (≤ 60 Zeichen): „Aufzugseil reißt: Solltest du kurz vorm Aufprall springen?“
- Thumbnail: Hook-Frame + „SPRINGEN?“ (Impact, gelb) in der Safe-Zone.
- Quellen in die Beschreibung: Guinness World Records, Wikipedia „1945 Empire State Building B-25 crash“, Otis „High-rise safety systems“.

## Befehle
```
python scripts/voice_gemini.py [--skip-tts]   # Stimme + Wort-Timings (src/timeline.de.json)
python scripts/audio.py                       # Effekte + Musik (synthetisch, CC0)
bash blender/preview_all.sh                   # schnelle Bewegungs-Vorschau -> out/preview.mp4
bash blender/render_all.sh                    # final, Sets A C H L -> public/bl/onetake.mp4
blender -b --factory-startup -P aufzug/blender/run.py -- C preview still:700,800
npx remotion render src/index.ts Aufzug out/aufzug.mp4
```
Sets (globale Frames, Grenzen an Woerter gebunden): A = Fall + Roentgen bis „Aber“, C = Rueckspulen, Seile, Regler, Keile, H = 1945 (Nebel, Bomber, Sturz, Luftkissen), L = Lobby/Loop.
Szene: `blender/az.py` (Kabine, Schacht, Seile, Regler, Turm, Bomber), `blender/shots.py` (Zeitachse, Kamera, Figuren). Kabine/Lobby-Bausteine aus `wolkenkratzer/blender/wk.py`.
