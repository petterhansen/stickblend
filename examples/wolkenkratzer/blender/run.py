"""Rendert ein Set eines One-Take-Shorts ueber GLOBALE Frames (Bild 1 = 0.0 s).
  blender -b --factory-startup -P blender/run.py -- <set> <preset> [all|still:f1,f2,...|range:a,b]
  blender -b --factory-startup -P blender/run.py -- --list            (Set-Namen ausgeben)
Ausgabe: out/bl/<set>/f####.png (globale Nummer) bzw. still_####.png
Umgebung: SPP, PCT (Aufloesung %), RT=1 (Raytracing), MB=1 (Bewegungsunschaerfe),
          RESUME=1 (Standard: vorhandene Bilder ueberspringen, flatten erst ab dem ersten fehlenden Bild)
Vertrag mit shots.py: SHOTS = {set: (build_fn, f0, f1)}, CHARS, STEP, SEG, optional after_flatten(), RT, MB.
"""
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("STICKBLEND_ROOT") or next(
    (d for d in [os.path.abspath(os.path.join(HERE, *[".."] * k)) for k in range(1, 6)] if os.path.exists(os.path.join(d, "stickblend", "__init__.py"))), None)
if ROOT is None: raise SystemExit("stickblend nicht gefunden: STICKBLEND_ROOT setzen")
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import bpy
from stickblend import stage, world, flat, sets2
import shots

argv = sys.argv[sys.argv.index("--") + 1:]
if argv and argv[0] == "--list": print("SETS", " ".join(shots.SHOTS)); sys.exit(0)
SID, PRESET = argv[0], argv[1]; MODE = argv[2] if len(argv) > 2 else "all"
OUT = os.path.join(os.path.dirname(HERE), "out", "bl", SID); os.makedirs(OUT, exist_ok=True)
T0 = time.time()
fn, f0, f1 = shots.SHOTS[SID]
stills = [int(x) for x in MODE.split(":")[1].split(",")] if MODE.startswith("still") else None
if MODE.startswith("range"): f0, f1 = [int(x) for x in MODE.split(":")[1].split(",")]
RS = f0
resume = MODE == "all" and os.environ.get("RESUME", "1") == "1"
if resume:
    have = {int(n[1:5]) for n in os.listdir(OUT) if n.startswith("f") and n.endswith(".png") and n[1:5].isdigit() and os.path.getsize(os.path.join(OUT, n)) > 0}
    miss = [f for f in range(f0, f1 + 1) if f not in have]
    if not miss: print("SET_OK", SID, f0, f1, "schon fertig"); sys.exit(0)
    RS = f0 + ((miss[0] - f0) // 2) * 2   # 2er-Rhythmus der Figuren beibehalten
    print("RESUME", SID, "ab", RS, "fehlend", len(miss))
stage.reset(); bpy.context.scene.render.fps = 30; shots.CHARS.clear(); shots.STEP[0] = 2; shots.SEG[:] = [f0, f1]
fn()
cam = bpy.context.scene.camera
if shots.CHARS:
    if stills is not None:
        for s in stills: flat.flatten(shots.CHARS, cam, 1, step=1, start=s)
    else: flat.flatten(shots.CHARS, cam, f1 - RS + 1, step=shots.STEP[0], start=RS)
    if hasattr(shots, "after_flatten"): shots.after_flatten()   # z. B. flat.attach(...) in fahrenden Objekten
for o in bpy.context.scene.objects:   # 2.5D-Ausschnitte nicht in Spiegelungen (sonst 'zweite Figur' in Gold/Glas)
    if o.name.startswith(("flat", "cut")) or "_flat" in o.name:
        try: o.visible_glossy = False
        except Exception: pass
sc = stage.render_setup(PRESET); sc.frame_start, sc.frame_end = RS, f1
sc.render.use_persistent_data = True    # Szene zwischen Bildern behalten (~40 % schneller)
sc.render.use_overwrite = not resume
if os.environ.get("SPP"): sc.eevee.taa_render_samples = int(os.environ["SPP"])
if os.environ.get("PCT"): sc.render.resolution_percentage = int(os.environ["PCT"])
if os.environ.get("RT") == "1" or getattr(shots, "RT", {}).get(SID):
    sc.eevee.use_raytracing = True
if os.environ.get("MB") == "1" or getattr(shots, "MB", {}).get(SID):
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
world.optimize_shadows(cam=(0, 0, 0), max_dist=1e9)
sets2.grade()
if PRESET == "preview":   # Vorschau: Volumen grob
    sc.eevee.volumetric_tile_size = "16"; sc.eevee.volumetric_samples = 24
if stills is not None:
    for s in stills:
        sc.frame_set(s); sc.render.filepath = os.path.join(OUT, f"still_{s:04d}.png"); bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(OUT, "f####"); bpy.ops.render.render(animation=True)
print("SET_OK", SID, f0, f1, round(time.time() - T0, 1), "s")
