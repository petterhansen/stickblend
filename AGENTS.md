# Regelbuch für Agents

Dieses Regelbuch gilt für **jeden** Agenten (Antigravity, Claude, Codex, Gemini …), der in diesem Repo Shorts produziert oder Code ändert.
Es ist allgemein gehalten: Es beschreibt, **wie** gearbeitet wird und **was** immer gelten muss, nicht wie ein bestimmter Short aussieht.

## 0. Rangfolge

1. **Dieses Regelbuch** (`AGENTS.md`): Arbeitsweise, Prüfpflicht, unverrückbare Grundsätze.
2. **`SHORTS-REGELN.md`**: messbare Vorgaben für Shorts (Safe-Zone, Länge, Hook, Lautheit, Untertitel, Labels). Zahlen stehen nur dort.
3. **`stickblend-shorts/SKILL.md`** und **`stickblend/STICKMAN-WORKFLOW.md`**: Befehle, Bibliothek, Techniken.
4. **Vorlagen und Beispiele** (`stickblend-shorts/templates/`, `examples/`): Ausgangspunkt und Qualitätsmaßstab.

Bei Widerspruch gilt das höhere Dokument. Einen gefundenen Widerspruch behebst du im niedrigeren Dokument, statt ihn zu umgehen.

## 1. Arbeitsweise: Phasen mit Abnahme

Jede Phase endet mit einer **Abnahme**. Die nächste Phase beginnt erst, wenn die Abnahme bestanden ist. Das Ergebnis jeder Abnahme schreibst du kurz in `STORY.md`.

| Phase | Ergebnis | Abnahme: fertig, wenn … |
|---|---|---|
| 1. Konzept | Idee, Fakten mit Quellen, Ablauf | Das Konzept ist eigenständig, der Hook liegt mitten im Geschehen, das Ende führt zum Anfang zurück, jede Tatsache hat eine Quelle und Zuspitzungen sind markiert. |
| 2. Text | `script.json` | Vorgelesen passt der Text in die Länge aus `SHORTS-REGELN.md`, ohne Beschleunigung. Jeder Satz lässt sich bebildern. |
| 3. Stimme | `voice.wav`, `timeline.json` | Das Transkript stimmt Wort für Wort mit dem Text überein: kein vorgelesener Stil, kein fehlendes Wort, nichts zu leise. Die Rohaufnahme ist unverändert (siehe §4). |
| 4. Blocking | Kamera und Sets mit Platzhaltern | Der Kontaktbogen zeigt in jeder Sekunde ein klares Motiv und die Kamera bewegt sich ohne Kollision. |
| 5. Szenen | Vorschau-Bilder je Set | Alle Grundsätze aus §3 sind an den Vorschau-Bildern geprüft und jeder Fund ist behoben. |
| 6. Final | `final.mp4` | Der Kontaktbogen alle 0,5–1 s, die Safe-Zone-Prüfung und die Lautheitsprüfung sind bestanden. |
| 7. Veröffentlichung | Titel, Beschreibung, Tags, Thumbnail | Sie stehen in `STORY.md`, mit Faktenhinweis und Credits. Das Thumbnail liegt in der Safe-Zone. |

Fertige Phasen fasst du nur an, wenn eine spätere Abnahme es verlangt. Dann wiederholst du alle Abnahmen ab dieser Phase.

## 2. Prüfpflicht: sehen, nicht annehmen

- **Nichts gilt als fertig, was du nicht selbst geprüft hast.** Gerendert ist nicht gleich geprüft.
- **Bild:** Prüfe Bilder als Kontaktbogen und sieh dir **jedes Bild** an. Notiere jeden Fehler als Liste, behebe ihn und prüfe erneut. Den Kontaktbogen nur zu erzeugen, ist keine Prüfung.
- **Ton:** Transkribiere jede Sprachaufnahme und vergleiche sie mit dem Text. Miss die Lautheit. Ist ein Anhören nicht möglich, prüfe Pegelverläufe und melde, dass es nicht angehört wurde.
- **Werkzeuge** (Befehle siehe `SKILL.md`): Vorschau-Bilder je Set, Kontaktbogen, `tools/safezone_check.py`, `ebur128`, Whisper-Transkript.
- **Bericht:** Melde ehrlich, was geprüft ist und was nicht. Bekannte Restmängel stehen im Bericht und in `STORY.md`.

## 3. Grundsätze für das Bild

1. **Jedes Bild ist lesbar.** Hauptmotiv und Figuren sind ganz im Bild, außer der Anschnitt ist gewollt. Kein Bild bleibt länger als in `SHORTS-REGELN.md` erlaubt ohne Motiv: nicht schwarz, nicht leer, keine kahle Wand.
2. **Die Kamera ist ein physischer Körper.** Sie steckt nie in Geometrie oder Figuren, fliegt nicht durch sie hindurch und hält Abstand. Sie dreht sich nicht schneller, als `SHORTS-REGELN.md` erlaubt. Prüfe auch die Bahn **zwischen** den Keyframes: Interpolation kann ausbrechen.
3. **Nichts verschwindet oder erscheint ohne Grund.** Ausblenden heißt: das ganze Objekt mit allen Anbauten, Gesichtern, Schatten und Konturen. Sicher ist, Figuren aus dem Bild zu bewegen, statt einzelne Teile unsichtbar zu schalten.
4. **Bewegung ist stetig.** Keine Sprünge durch Modulo, Neustarts oder Wiederholschleifen, außer die Wiederholung ist erzählerisch gewollt. Was einmal passiert (etwas fällt, fliegt, zerbricht), passiert einmal.
5. **Effekte sind physikalisch glaubwürdig.** Nebel, Rauch und Dunst sind Volumen und kein Geometrie-Ersatz. Begrenzte Effekt-Volumen enden nie sichtbar im Bild.
6. **An jedem Übergang passt alles zusammen.** Das letzte Bild eines Abschnitts und das erste des nächsten zeigen denselben Zustand: Objekte, Figuren, Licht, Tür offen oder zu. Ein Loop endet exakt im Bild 1.
7. **Bild und Ton sagen dasselbe.** Was gesagt wird, ist im selben Moment zu sehen. Zahlen im Bild (Zähler, Höhen, Zeiten) passen zu dem, was gesagt wird; eine Zeitangabe läuft in echter Zeit. Weicht eine Zahl bewusst ab, ist sie als Zuspitzung gekennzeichnet.
8. **Farben sind kräftig, Licht ist gerichtet.** Kein Grauschleier, nicht überbelichtet. Jede Welt ist eingerichtet und glaubwürdig.
9. **Figuren handeln.** Hauptfiguren zeigen das Gesicht, wenn ihre Emotion zählt. Nebenfiguren reagieren auf das Geschehen; Kulissen ohne Leben vermeiden.
10. **Texte und Grafiken liegen in der Safe-Zone** und folgen dem Label-Stil aus `SHORTS-REGELN.md`. Was im Bild schon klar ist, wird nicht zusätzlich beschriftet.

## 4. Grundsätze für den Ton

1. **Die Rohqualität der Stimme bleibt erhalten.** Keine Zeitdehnung und keine Ketten verfälschender Filter. Ist der Text zu lang, wird **der Text gekürzt**, nicht die Stimme beschleunigt.
2. **Anweisung und Text sind getrennt.** Stil- und Regieanweisungen gehen nie als vorzulesender Text an das TTS-Modell.
3. **Kein Wort geht unter.** Leise oder verschluckte Wörter, besonders am Satzende und im Loop-Satz, werden gezielt angehoben oder neu erzeugt.
4. **Geräusche bekommen einen Anlass.** Jeder Effekt gehört zu einem sichtbaren Ereignis oder einem Wendepunkt. Musik liegt unter der Stimme, die Stimme dominiert.
5. **Lautheit und Spitzen** entsprechen `SHORTS-REGELN.md` und werden am fertigen Video gemessen.

## 5. Grundsätze für die Erzählung

1. **Mitten ins Geschehen**, Du-Form, Präsens. Satz 1 beschreibt die Lage.
2. **Jede Behauptung ist belegt** (Quelle in `STORY.md`) oder als Zuspitzung gekennzeichnet. Keine erfundenen Zahlen als Tatsache.
3. **Jede Sekunde liefert etwas Neues.** Wechsel von Bild, Ort, Perspektive oder Ton im Takt aus `SHORTS-REGELN.md`.
4. **Das Ende führt zum Anfang zurück**, sprachlich und im Bild.
5. **Keine echten Marken, Logos oder Personen-Abbilder** als Dekoration; eigene, fiktive Gestaltung.

## 6. Grundsätze für Code und Repo

1. **Wiederverwenden vor Neubauen.** Erst Bibliothek, Vorlagen und Beispiele durchsuchen. Neues, das allgemein nützlich ist, kommt in die Bibliothek oder die Vorlage, nicht nur in ein Projekt.
2. **Fehler an der Quelle beheben.** Stammt ein Fehler aus Vorlage, Bibliothek oder Werkzeug, wird er dort behoben, damit er im nächsten Short nicht wiederkehrt.
3. **Zeiten hängen an gesprochenen Wörtern**, nicht an festen Sekunden. Ändert sich die Stimme, passt sich alles von selbst an.
4. **Keine absoluten, rechnerabhängigen Pfade.** Pfade sind relativ zum Repo oder werden gesucht.
5. **Rendern lässt sich fortsetzen und ist reproduzierbar.** Vorhandene Werkzeuge (`render_all.ps1`, Fingerabdruck, Resume) nutzen und nicht umgehen. Lange Läufe laufen im Hintergrund.
6. **Erst Vorschau, dann final.** Ein volles Final-Rendern beginnt erst nach bestandener Abnahme 5.
7. **Änderungen sind nachvollziehbar.** Was und warum, steht kurz in `STORY.md`; Commits beschreiben den Grund.

## 7. Assets und Lizenzen

- Nur eigene, CC0- oder klar freigegebene Assets. Prüfe die Lizenz vor der Nutzung und nenne sie in den Credits.
- Downloads kommen in einen eigenen Ordner und werden nicht ausgeführt.
- Ist die Freigabe unklar (z. B. von Dritten hochgeladen), wird der Nutzer informiert.

## 8. Rückfragen und Grenzen

- **Fragen**, bevor du Inhalte veröffentlichst, pushst, Kosten auslöst oder bei Geschmacksfragen ohne klare Vorgabe entscheidest (Stimme, Musikstil). Gib dann kurze Proben zur Auswahl.
- **Nicht fragen**, was dieses Regelbuch oder `SHORTS-REGELN.md` schon entscheidet.
- **Feedback des Nutzers wird zur Regel.** Kritik, die über einen Einzelfall hinausgeht, kommt verallgemeinert in dieses Regelbuch oder in `SHORTS-REGELN.md`.

## 9. Abnahme vor der Übergabe

- [ ] Alle Phasen-Abnahmen aus §1 bestanden und in `STORY.md` vermerkt
- [ ] Kontaktbogen des fertigen Videos Bild für Bild geprüft, keine Verstöße gegen §3
- [ ] Transkript gleich Text, Rohqualität der Stimme erhalten, Lautheit gemessen (§4)
- [ ] `SHORTS-REGELN.md`-Checkliste abgehakt
- [ ] Fehler aus Vorlagen oder Bibliothek an der Quelle behoben (§6.2)
- [ ] Bericht an den Nutzer: was fertig ist, was geprüft ist, was offen ist
