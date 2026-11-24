# Stickman-Workflow in Blender (`stickblend`)

So entstehen Strichmännchen für die Shorts: Jede Figur wird aus einem Steckbrief gebaut, mit Posen und Mimik animiert und in Blender (EEVEE) in einer 3D-Welt gerendert.
Untertitel, Ton und Effekte kommen danach wie bisher aus Remotion.

Getestet mit **Blender 5.2** (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`).

---

## 1. Stil (2.5D-Strichmännchen in 3D-Welt)

Grundregeln für den 2.5D-Ausschnitt-Look:

| Element | Regel |
|---|---|
| Kopf | groß und rund, etwa 29 % der Körperhöhe, hautfarben, flach gefüllt |
| Torso | abgerundete „Bohne“ in Kleidungsfarbe, darauf Details als Geometrie (Knöpfe, Gürtel, Riemen …) |
| Glieder | dünne dunkle Striche; Stoff (Ärmel, Hosen, Gamaschen) nur, wenn die Figur es braucht |
| Füllung | unbeleuchtet und flach, mit weicher, dunklerer Randzone |
| Kontur | dunkelbraun (`#2b1d16`), im Bild immer gleich breit, egal wie weit die Kamera weg ist |
| Gesicht | Striche auf der Kopfkugel: ovale Augen, kräftige Brauen, kleiner Mund |
| Umgebung | echtes, ausgeleuchtetes 3D **ohne** Konturlinien, mit Dunst, Glühen und starker Tiefenschärfe |
| Bewegung | Figuren auf Zweiern (12 Posen pro Sekunde), Kamera flüssig auf jedem Bild |

**Erweiterte Details für den 2.5D-Ausschnitt-Stil:**

| Element | Beobachtung |
|---|---|
| Figuren | echte **2.5D-Ausschnitte**: Der Kopf dreht sich (3/4 → vorne), Gesichtszüge rutschen über den Kopfkreis, Hutkrempe als Ellipse je nach Blickwinkel |
| Kontur | dunkles Pflaume-Braun, **dicker als bei uns** (~4–5 px bei 1080 px Breite) |
| Schattierung | flach, aber mit **weicher einseitiger Schattenzone** (lavendelgrau) auf der lichtabgewandten Seite von Kopf und Körper |
| Augen | je Figur: dunkle Ovale **oder** weiße Augen mit dunkler Pupille; dicke Brauen, Schnurrbart als Form |
| Kleidung | **Muster** in den Flächen: Karo, Nadelstreifen, Strick-Mütze |
| Requisiten | Zeitung, Geldscheine als flache Grafikkarten in der Hand; Eimer, Laterne, Goldpfanne als echte 3D-Objekte |
| Umgebung | **detailreich und realistisch texturiert** (Fels, Holzbalken, Schienen), Laternenlicht, Staub- und Funkenpartikel, Gold glüht |
| Kamera | viele Nahaufnahmen von Gesichtern und Requisiten mit starker Tiefenschärfe, dazu weite Etablierungsshots, langsame Fahrten und Kreisbewegungen |
| Schatten | Figuren werfen Schatten auf den Boden |

Die Figuren werfen echte Schatten in die Welt. Selbst bekommen sie nur eine weiche, gezeichnet wirkende Schattenzone, kein 3D-Licht. So bleiben sie 2D.
Szenenlicht wirkt auf sie über `mats.set_scene_light(tint, rim_strength, rim_color, rim_dir)`, also Farbstimmung und Lichtkante.

---

## 2. Aufbau

```
stickblend/
  specs.py        Steckbriefe aller Figuren          <- neue Figuren hier eintragen
  rig.py          Skelett, IK, Posen-Bibliothek (POSES), Überblendung, Laufzyklus
  face.py         Mimiken (16 Moods) als Strich-Primitive
  character.py    Figur bauen (build), animieren (animate / pose_frame), Haare, Hüte, Extras
  mats.py         Materialien: flache Füllung + Randzone, Tuschekontur, Szenenlicht
  geo.py          Geometrie-Helfer, Konturhülle (Geometry Nodes, kamera-abhängige Breite)
  stage.py        Testbühne, Kamera, Render-Presets
  lineup.py       Kontroll-Render: alle Figuren + Drehung (vorne/3/4/Profil/hinten)
  demo_shot.py    Vorlage für ein Shot-Skript
```

---

## 3. Neue Figur anlegen

1. **Steckbrief in `specs.py` eintragen.** Am einfachsten eine ähnliche Figur kopieren:
   ```python
   "polizist": {
       "name": "Polizist", "shoulderW": 0.16,
       "torso": {"color": "2a3a6a", "details": [
           {"type": "placket"}, {"type": "buttons", "color": "d8c070"},
           {"type": "belt", "color": "1a1a1a", "buckle": "c0c0c0"}, {"type": "pockets"}]},
       "hat": {"type": "officer", "color": "2a3a6a"},
       "face": {"nose": False},
   },
   ```

   | Feld | Bedeutung / Werte |
   |---|---|
   | `height` | Körpergröße in m (Standard 1,75 m; Kind 1,25 m) |
   | `prop` | Proportionen relativ zur Höhe: `head` 0.145, `torso` 0.30, `leg` 0.40, `arm` 0.34 |
   | `shoulderW` | halbe Schulterbreite in m (0.12–0.18) |
   | `torso` | `color`, `width` (Faktor), `depth`, `profile` (eigene Bohnenform), `details` |
   | `torso.details` | `placket`, `buttons`, `collar`, `tabs`, `belt`, `strap`, `pouches`, `pockets`, `patch`, `camera`, `bowtie`, `panel` (V-Ausschnitt/Hemd) |
   | `sleeves`, `pants` | `color`, `len` (Anteil 0..1), `r` (Radius) |
   | `puttees`, `shoes`, `skin`, `limbs` | Farben |
   | `hair` | `style`: `short`, `bowl`, `bob`, `long`, `sides` (Haarkranz), `none`; dazu `color`, `volume` |
   | `hat` | `type`: `fieldcap`, `officer`, `beanie`, `cap`; dazu `color`, `frayed` |
   | `extras` | `glasses`, `headband`, `backpack` |
   | `face` | `stubble`, `age` (Falten 0–3), `nose`, `blush`, `eye_highlight`, `eyes` (`dark` = dunkle Ovale, `white` = weiße Augen mit Pupille) |
   | `torso.pattern` | `plaid`, `pinstripe`, `stripes`, `knit`, dazu `pattern_color`. Das Muster wird flach auf den 2.5D-Ausschnitt gezeichnet. |

   **Stilregel:** Keine Ärmel, Hosenbeine oder Gamaschen. Arme und Beine sind nur Strichlinien, Kleidung sitzt am Torso. (`sleeves` und `pants` funktionieren technisch noch, sind aber aus allen Steckbriefen entfernt.)

   **2.5D-Ausschnitte** (`flat.flatten(chars, cam, frames)`): Nach dem Animieren und Setzen der Kamera aufrufen.
   - Die 3D-Figur wird zur unsichtbaren Vorlage und wirft nur noch Schatten.
   - Pro gezeichnetem Bild entsteht ein flacher Ausschnitt mit 4,4 px breiter Kontur und weicher Schattenzone.
   - Details liegen fest vor bzw. hinter ihrem Träger, Torso oder Kopf, in fester Stapelreihenfolge (`flat.LAYERS`).
   - Der Kopf liegt immer über dem Torso. Haare hinter dem Kopf bleiben dahinter.

2. **Kontrolle rendern** (etwa 10 s):
   ```
   blender -b --factory-startup -P stickblend/lineup.py -- stickblend/out preview polizist,tourist
   ```
   Das erzeugt `out/lineup.png` (alle Figuren in verschiedenen Posen) und `out/turn_<id>.png` (vorne, 3/4, Profil, hinten).

3. **Checkliste**
   - [ ] Haaransatz und Hut verdecken das Gesicht in keiner Ansicht.
   - [ ] Die Arme liegen außerhalb des Torsos (sonst `shoulderW` erhöhen oder `torso.width` senken).
   - [ ] Die Kontur ist überall geschlossen, auch an Hut, Haaren und Händen.
   - [ ] Die Figur ist in der Rückansicht ohne Gesicht erkennbar (Haare, Hut, Rucksack).
   - [ ] Die Farbe hebt sich vom geplanten Hintergrund ab.

**Neue Hut- oder Haarform:** Zuerst in `character.py` unter `_hat` bzw. `HAIR` ergänzen. Haare werden über drei Höhen des Haaransatzes beschrieben: `front` (Stirn), `side` und `back` (Nacken).

---

## 4. Posen, Mimik, Bewegung

- **Posen** (`rig.POSES`): `idle`, `salute`, `point`, `wave`, `handsUp`, `hips`, `think`, `offer`, `binoculars`, `read`, `stop`, `crouch`, `sneak`, `shrug`, `oil`.
  - Eine neue Pose ist ein Eintrag im Dictionary.
  - Hand-Ziele stehen im Figurenraum (`x` = linke Seite +, `y` oben, `z` vorne). Das IK erledigt den Rest.
- **Posenfolge:** `rig.poses_at(t, [(0, "idle"), (1.5, "wave"), (2.4, "idle")])` blendet weich über (0,3 s).
- **Laufen:** `stick_rig(spec, pose, t, walk=1.0)` (0..1 blendet zwischen Stehen und Laufen); dazu `pos` und `yaw` pro Bild selbst bewegen.
- **Sprechen:** `talk=1.0` erzeugt Mundbewegung, an `pose_frame(..., mouth=R["mouth"])` weiterreichen.
- **Mimik:** `neutral`, `happy`, `laugh`, `smug`, `sly`, `shock`, `scared`, `angry`, `sad`, `worry`, `tired`, `determined`, `suspicious`, `proud`, `cry`, `closed`. Dazu `blink=True`.
- **Platzieren:** `rig.to_world(stick_rig(...), pos=(x, 0, z), yaw)`.
  - Die Koordinaten sind three-Achsen (y oben). Blender-Position = `(x, -z, y)`.
  - `yaw = 0` blickt zur Kamera, wenn die Kamera auf der Blender-Achse −y steht.

---

## 5. Shot-Skript (Vorlage `demo_shot.py`)

```python
stage.reset()                                   # leere Szene, Keys halten (auf Zweiern)
# Welt aufbauen: eigene Assets / Kenney-Kits importieren, Lichter setzen
ch = character.build(specs.SPECS["tourist"], "tourist")
def f(t):                                       # Zustand der Figur zur Zeit t (s)
    pose = rig.poses_at(t, [(0, "idle"), (1.5, "wave")])
    R = rig.to_world(rig.stick_rig(spec, pose, t, walk=...), (x, 0, z), yaw)
    return dict(rig=R, mood="happy", blink=(t % 2.6) < 0.1, mouth=R["mouth"])
character.animate(ch, f, frames=90, step=2)     # Figur auf Zweiern
cam = stage.camera(loc, look, lens=28, dof=2.0) # Kamera auf jedem Bild keyen
sc = stage.render_setup("final"); bpy.ops.render.render(animation=True)
```

Danach geht die PNG-Folge per `ffmpeg` in ein MP4 und von dort als Clip in die Remotion-Komposition. Remotion legt Untertitel, Stimme, Musik und Effekte darüber.

---

## 5b. Welten bauen (`world.py`, Vorlage `testworld.py`)

| Funktion | Zweck |
|---|---|
| `world.asset(name, lib)` | lädt ein Objekt einmalig aus einer `.blend`-Bibliothek, Standard ist Quaternius `AllModels.blend` (Palmen, Bäume, Büsche, Pflanzen, Gras, Felsen, Blumen; Maße in Metern) |
| `world.place(name, loc, rot_z, scale)` | verlinkte Kopie: teilt Mesh und Material, kostet kaum Renderzeit |
| `world.scatter(names, n, area, avoid, scale, seed)` | streut zufällig, aber reproduzierbar |
| `world.keep_clear(cam_path, subjects)` | `avoid`-Funktion: hält die Sichtlinien Kamera→Figur und den Bereich direkt vor der Linse frei |
| `world.ground`, `world.sky(haze=…)`, `world.sun`, `world.glow` | Boden mit Farbvariation, Himmelsverlauf, Dunst-Volumen, Sonne, Glühen (Compositor) |

**Licht im Referenzstil**
- Tiefe Sonne als Gegenlicht (Schatten fallen zur Kamera), dazu schwaches kühles Fülllicht.
- Für die Figuren `mats.set_scene_light(tint, rim_strength, rim_color, rim_dir)`; `rim_dir` zeigt zur Sonne.

**Tiefe**
- Kamera mit `dof=2.0` (Blende) auf die Figuren fokussieren.
- 1–2 dunkle Büsche nah an der Kamera an den Bildrand stellen; sie werden weich und rahmen das Bild.

**Blender-5.2-Fallen**
- Ein Welt-Volumen (World → Volume) rendert in EEVEE alles schwarz. Für Dunst immer die Volumen-Box aus `world.sky` nehmen.
- Dunst sparsam dosieren: 0,006 reicht, 0,018 wäscht das Bild aus.

---

## 6. Rendern und Zeiten

Alle Presets rendern 1080×1920 in EEVEE (`stage.PRESETS`):

| Preset | Auflösung | Samples | gemessen |
|---|---|---|---|
| `preview` | 50 % (540×960) | 6 | Lineup mit 9 Figuren: 9 s inklusive Aufbau |
| `final` | 100 % | 16 | Demo-Shot: **0,39 s pro Bild**, also etwa 13 min für 69 s |
| `final_hq` | 100 % | 32 + Raytracing | für Hero-Shots |

**Testwelt Dschungel** (`testworld.py`): 370 Objekte, 2 Figuren, Gegenlichtsonne, Dunst, Tiefenschärfe, Glühen, 1080×1920. Jeder Wert ist der zweite Lauf, der erste kompiliert die Shader.

| Einstellung | pro Bild | 69-s-Short |
|---|---|---|
| ohne Optimierung, 16 Samples | 1,41 s | ~49 min |
| `world.optimize_shadows()`, 16 Samples | 0,68 s | ~23 min |
| `world.optimize_shadows()`, 8 Samples | 0,55 s | ~19 min |

- **Hauptkosten sind die Sonnenschatten** auf dichtem Laub. Dunst, Tiefenschärfe und Glühen kosten je nur wenige Hundertstel.
- `optimize_shadows()` macht die Schattenkarten gröber (Auflösung 0,5, Filterschritte 2), ohne sichtbaren Verlust bei flachen Figuren. Außerdem schaltet sie Schatten von Objekten jenseits von `max_dist` ab.
- **Immer aufrufen**, bevor gerendert wird.

**Was Zeit kostet** (gemessen an der Waffenöl-Szene, 1080×1920):
- **Grundkosten pro Bild:** etwa 0,25–0,35 s. Das liegt an vielen Einzelobjekten (die GLB-Umwandlung erzeugte über 1100), am Szenen-Update und am PNG-Schreiben.
- **Samples:** etwa 0,027 s pro Sample. 24 Samples ergeben etwa 0,65 s, 8 Samples etwa 0,2 s.
- **Line Art:** etwa +0,2 s pro Bild. Im Referenzstil entfällt sie, weil die Umgebung keine Linien hat.
- **Raytracing:** etwa +0,05 s.

**Tipps:**
- Welten in Blender aus wenigen, zusammengefügten Objekten bauen. Vegetation besser instanzieren statt als Einzelobjekte anlegen.
- 16 Samples reichen für flache Figuren. Mehr Samples braucht nur starke Tiefenschärfe.
- Länge rechnen: 69 s entsprechen 2070 Bildern. Bei 0,4 s pro Bild sind das etwa 14 min, bei 0,25 s etwa 9 min.

---

## 7. Bekannte Grenzen / nächste Schritte

- **Lichtkante:** `rim_*` ist global, ein Wert für alle Figuren einer Szene. Eine Lichtkante pro Figur je nach Lichtquelle fehlt noch.
- **Hände:** Sie sind Kugeln. Greifposen (Gewehr, Tasse) wirken über die Position, Finger gibt es keine.
- **Profil-Mimik:** Die Mimik ist in Seitenansicht nur halb sichtbar. Das ist physikalisch korrekt, aber bei Profil-Dialogen ist eine 3/4-Drehung besser.
- **Keine Umgebungen:** Das Paket enthält keine Welten. Kenney- und Quaternius-Kits (`assets3d/`) direkt in Blender importieren, ohne den Umweg über GLB aus three.js.
- **Laufzyklus:** stammt aus der three.js-Factory und wirkt etwas steif. Er lässt sich in `rig.stick_rig` nachjustieren.
