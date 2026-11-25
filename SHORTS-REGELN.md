# Shorts-Regeln (verbindlich für jeden Short)

Ziel: maximale Zuschauerbindung (Retention) und Algorithmus-Attraktivität auf YouTube Shorts, TikTok und Instagram Reels.
Jede Regel ist prüfbar. Vor dem Export die Checkliste unten abarbeiten.

## 1. Safe-Zone (Plattform-UI, 1080×1920)
Quelle: TikTok-Maske (`stickblend/assets/safezone.json`, Overlay: `stickblend/assets/safezone_tiktok.png`).

| Bereich (1080×1920) | Regel |
|---|---|
| y < 120 | kein Text (Statusleiste, Tabs) |
| x 307–760, y 120–212 | kein Text (Suchfeld/Tabs-Notch) |
| x < 45 oder x > 1031 | kein Text |
| x > 885 ab y 957 | kein Text (Like/Kommentar/Teilen-Leiste) |
| y > 1540 | kein Text (Name, Beschreibung, Sound) |
| **TikTok-Untertitel-Box** | **x 70–860, Mitte y ≈ 1290, Unterkante ≤ 1500** |

### Plattformübergreifende Safe-Zone (YouTube Shorts + Reels + TikTok)
YouTube Shorts und Instagram Reels verdecken unten und oben deutlich mehr Fläche als TikTok-Organic:
- **YouTube Shorts / Reels:** Top-UI bis ca. **y ≈ 288**, Bottom-UI (Kanal, Abo-Button, Titel, Audioleiste) ab ca. **y ≈ 1248** (~672 px vom unteren Rand), rechte Button-Leiste ab **x ≈ 888** (~192 px).
- **Universelle Cross-Platform-Zone (für einen gemeinsamen Export):** Wichtige Motive, Gesichter, Text-Overlays und Schilder in **x 70–860, y 290–1240** halten. Bei reinen TikTok-Untertiteln darf die `caption_box` bis `y ≤ 1500` genutzt werden.
- **Prüfung:** `python stickblend/tools/safezone_check.py <video.mp4> --step 2` erzeugt einen Kontaktbogen mit Maske (`safezone_sheet.png`) und warnt bei hellem Untertitel-Weiß im Sperrbereich (Fehlalarme durch helle Szenen immer visuell im Bogen gegenprüfen).

## 2. Hook (0–3 s)
- **Swipe-Away-Rate minimieren:** In den ersten 3 Sekunden entscheiden 30–50 % der Zuschauer, ob sie weiterschauen. Kein Schwarzbild, kein Logo, keine Begrüßung („Hallo Leute…“), kein langsamer Aufbau.
- **Show, Don't Tell:** Direkt mitten in der Bewegung, mit starkem visuellem Kontrast oder dem zentralen Rätsel-/Ergebnismotiv starten („3-Sekunden-Thumbnail“-Prinzip).
- Im ersten Satz steckt sofort die Frage, der Konflikt oder der Widerspruch („…fehlen einfach 15 Stockwerke“).
- Das Thumbnail-Motiv taucht in den ersten 3 s sichtbar auf.
- **Mitten ins Geschehen:** Frame 1 zeigt die Situation, die schon läuft (Fall, Riss, Knall), keine Einleitung. Du-Form und Präsens, Satz 1 schildert die Lage statt eine Frage zu stellen („Das Seil ist gerissen.“). Auf Frame 1 liegt ein Ton-Treffer.
- **Zähler im Bild** (Restzeit, Höhe, Tempo) ab 0,0 s erzeugt Druck und gibt den Takt. Er steht in der Safe-Zone und überdeckt nie die Untertitel-Box.
- **Einzigartiges Konzept:** kein Thema, das große Kanäle schon so gemacht haben, ohne eigenen Dreh.

## 3. Länge, Tempo und Loop
- **Sweet Spot:** **21–50 s** (maximal **60 s** für straffes Shorts-Tempo). Jede Sekunde muss visuell oder inhaltlich etwas Neues liefern.
- **Pattern-Interrupts:** Alle **2–4 s** (spätestens alle 5 s) ein neuer Reiz: Kameraperspektive (inkl. POV-Wechsel), Ortswechsel, SFX-Akzent oder Text-Pop.
- Kein Bild länger als **0,5 s** fast schwarz oder ohne erkennbares Motiv (auch nicht „stimmungsvoll dunkel“).
- **Auflösung & Cut:** Pointe/Auflösung vor dem Ende, danach höchstens 1–2 s Nachklang (Easter-Egg), dann harter Schnitt.
- **Nahtloser Loop (APV > 100 %):** Das letzte Bild oder der letzte Satz führt gedanklich/visuell direkt zurück zum Anfang, damit Rewatches die durchschnittliche Wiedergabedauer über 100 % treiben.

## 4. Kamera (One-Take / 3D / POV)
- Nie durch Wände, Gebäude oder Figuren fliegen; Mindestabstand zu Flächen ≈ 1 m (bei Totalen ≫ 10 m).
- Keine Drehung über ~90° pro Sekunde. 180°-Wenden vermeiden: lieber rückwärts aus einem Raum fahren.
- Totalen weit genug wählen (Hochformat ist schmal: horizontaler Bildwinkel ≈ 0,56 × vertikaler).
- **Perspektivwechsel (POV):** Mit `rig.pov_pose(ch)` + `flat.flatten(..., pov=..., pov_hands=True)` lässt sich mitten in der Szene in die Ego-Perspektive einer Figur schneiden (Kopf/Hut wird ausgeblendet, eigener Schatten und optional eigene Gesten-Hände bleiben sichtbar).
- **Wand-/Objekt-Abstand (`flat_bias`):** Steht eine Figur nah vor einer Wand oder einem Requisit, `ch.flat_bias` setzen, damit die 2.5D-Cutout-Ebene nicht in die 3D-Geometrie schneidet.
- Zu jeder Zeit ist klar, wo wir sind und was das Motiv ist. Prüfen: Kontaktbogen alle 0,5 s.

## 5. Untertitel
- 2–4 Wörter pro Einblendung, Satzzeichen bleiben, Zahlen als Ziffern, ß → ẞ in Großschrift.
- Keine Trennung von Zusammengehörigem („NEW | YORK“, „1 | MILLION“). Kurze Satzenden an die vorige Gruppe hängen.
- Weiß, fette geometrische Sans, dicke schwarze Kontur, nur in der Untertitel-Box (Abschnitt 1 — bei Multi-Plattform-Upload idealerweise im oberen Bereich der Box `y ≈ 1050–1220`).


### Zähler und Bauchbinden
- **Zähler:** kein Kasten, kein Rahmen. Dieselbe fette Schrift wie die Untertitel: oben klein weiß (Label), darunter groß in Rot/Weiß (Wert), nur schwarze Kontur + harter Schlagschatten.
- **Doku-Bauchbinden** (Datum, Ort, Person): scharfkantiger gelber Vollton-Balken mit schwarzer Schrift, darunter leicht versetzt ein weißer Balken. Eigener Look, nie wie der Zähler (Vorlage: `LowerThird` in `templates/onetake/src/Short.tsx`).

## 6. Ton und Lautheit (LUFS)
- **Ziel-Lautheit:** Finalen Mix auf **−14 LUFS integriert** (Arbeitsbereich **−16 bis −14 LUFS**) mastern. YouTube und TikTok normalisieren automatisch auf ca. −14 LUFS — zu laute Mixe werden heruntergeregelt, zu leise klingen im Feed schwach.
- **True Peak:** Strikt **≤ −1,0 dBTP**, damit beim mobilen Re-Encoding (AAC/Opus) kein digitales Clipping entsteht.
- **Sprachverständlichkeit:** Stimme dominiert (Loudness Range **LRA 5–10 LU**); Musik **15–20 dB** darunter, SFX klar hörbar (Klick, Klopfen, Stempel …).
- Musik-Drops und SFX-Akzente an den Wendepunkten der Story (Enthüllung, Pointe, Reveal).
- Pausen nur an echten Satzgrenzen, maximal ca. 0,5–0,6 s, nie mitten im Wort oder Satz (`voice_gemini.py` setzt Pausen in echte Stille und kürzt Lücken über 0,5 s).
- **Stimme ohne Roboter-/Metallklang:** Modell `gemini-3.8-flash-tts` (die alte `2.5-flash-preview` klingt metallisch) und **Tempo 1,0**: Die Rohaufnahme bleibt unverändert, nur lange Pausen werden gekürzt. Jede Zeitdehnung (`atempo`, auch Rubberband) klingt nach Roboter; ist der Text zu lang, wird er gekürzt, nicht beschleunigt. Stil steht als Regieanweisung getrennt vom Transkript, sonst liest das Modell ihn vor; nach dem Erzeugen per Transkript prüfen. Leise Schlussworte (z. B. „doch …“) gezielt anheben.
- **Lautheit prüfen:** `ffmpeg -i final.mp4 -af ebur128=peak=true -f null -` (Integrated ≈ −14 LUFS, True Peak ≤ −1,0 dBTP) und einmal komplett auf Handy-Lautsprechern anhören.

## 7. Inhalt und Logik
- Was gesagt wird, ist im selben Moment zu sehen (sagt die Stimme „46“, sieht man 46; sagt sie „stockdunkel“, ist es dunkel).
- Beschriftungen im Bild sind eindeutig und passen zur Story (z. B. „0 m² WOHNFLÄCHE“ statt „0 m²“).
- Räume sind eingerichtet und glaubwürdig (Glas vor Abgründen, Möbel im Penthouse …).
- Figuren: beide Beine sichtbar, Requisiten sitzen an der gezeichneten Hand (`flat_pt`), nichts schwebt oder steckt im Körper.
- Fakten, die zugespitzt sind, in der Beschreibung kennzeichnen.

## 8. Veröffentlichung
- Titel ≤ 60 Zeichen, erzeugt Neugier und verspricht die Auflösung („Warum …?“). Keine erfundene Zahl als Tatsache.
- Beschreibung: 2–3 Sätze Kontext, Faktenhinweis, Credits (CC-BY-Musik ist Pflicht), 3–6 Hashtags inkl. `#Shorts`.
- Thumbnail: Rätsel-Motiv aus dem Video plus max. 4 Wörter Text, in der universellen Safe-Zone (`x 70–860, y 290–1240`).
- Kategorie „Bildung“ für Erklär-Shorts, einheitlich pro Reihe.

## Checkliste vor dem Export
- [ ] Hook (0–3 s): Frame 1 mitten im Geschehen, Satz 1 schildert die Lage, Ton-Treffer auf Frame 1 (kein langsamer Einstieg)
- [ ] Länge 21–50 s (max. 60 s), Pattern-Interrupts alle 2–4 s, kein Schwarzbild > 0,5 s, Loop am Ende
- [ ] Kamera: Kontaktbogen alle 0,5 s ohne Wand-Durchflüge, Ruck-Drehungen oder `flat_bias`-Clipping
- [ ] `safezone_check.py` angesehen: Untertitel und Kernmotive sicher (Cross-Platform: `y 290–1240` für Kernmotive)
- [ ] Audio: ≈ −14 LUFS integriert, True Peak ≤ −1,0 dBTP, Musik −15 bis −20 dB unter Stimme, SFX hörbar
- [ ] Bild passt zum gesprochenen Wort, Schilder eindeutig, Requisiten/Schatten korrekt
- [ ] Titel, Beschreibung mit Credits, Thumbnail
