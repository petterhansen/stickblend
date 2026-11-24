"""Render one scene (or segment / stills) of a stickblend short in Blender 5.2.

Usage:
  blender -b --factory-startup -P blender/run.py -- <scene_id> <preset> [all|still:f1,f2,...]

Environment overrides:
  SPP=6              Override EEVEE sample count
  PCT=75             Override resolution percentage (75 = 810x1440, 100 = 1080x1920)
  FMT=JPEG           Output format for animation frames: JPEG (fast, q=95) or PNG (compression=0)
  SHADOW_DIST=18     Max shadow-casting distance from origin (cuts distant foliage shadow cost)
  STICKBLEND_ROOT    Path to repo containing stickblend/
"""
import os
import pathlib
import sys
import time

BLENDER_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_DIR = BLENDER_DIR.parent
REPO_ROOT = pathlib.Path(os.environ.get("STICKBLEND_ROOT", PROJECT_DIR.parent))

for p in (str(REPO_ROOT), str(BLENDER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy
from stickblend import flat, sets2, stage, world
import shots

argv = sys.argv[sys.argv.index("--") + 1 :]
SID, PRESET = argv[0], argv[1]
MODE = argv[2] if len(argv) > 2 else "all"

OUT = PROJECT_DIR / "out" / "bl" / SID
OUT.mkdir(parents=True, exist_ok=True)

N = shots.nframes(SID)
T0 = time.time()
stills = [int(x) for x in MODE.split(":")[1].split(",")] if MODE.startswith("still") else None
fmt = os.environ.get("FMT", "JPEG" if stills is None else "PNG").upper()
shadow_dist = float(os.environ.get("SHADOW_DIST", "18"))

for fn, f0, f1 in shots.segments(SID):
    if stills is not None and not any(f0 <= s <= f1 for s in stills):
        continue
    stage.reset()
    shots.CHARS.clear()
    shots.STEP[0] = 2
    fn(N)
    if shots.CHARS:
        if stills is not None:
            for s_ in stills:
                if f0 <= s_ <= f1:
                    flat.flatten(shots.CHARS, bpy.context.scene.camera, 1, step=1, start=s_)
        else:
            flat.flatten(shots.CHARS, bpy.context.scene.camera, f1 - f0 + 1, step=shots.STEP[0], start=f0)
    sc = stage.render_setup(PRESET)
    sc.frame_start, sc.frame_end = f0, f1
    if os.environ.get("SPP"):
        sc.eevee.taa_render_samples = int(os.environ["SPP"])
    if os.environ.get("PCT"):
        sc.render.resolution_percentage = int(os.environ["PCT"])
    world.optimize_shadows(cam=(0, 0, 0), max_dist=shadow_dist)
    sets2.grade()
    if stills is not None:
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.compression = 0
        for s in stills:
            if f0 <= s <= f1:
                sc.frame_set(s)
                sc.render.filepath = str(OUT / f"still_{s:04d}.png")
                bpy.ops.render.render(write_still=True)
    else:
        if fmt == "JPEG":
            sc.render.image_settings.file_format = "JPEG"
            sc.render.image_settings.quality = 95
        else:
            sc.render.image_settings.file_format = "PNG"
            sc.render.image_settings.compression = 0
        sc.render.filepath = str(OUT / "f####")
        bpy.ops.render.render(animation=True)

print("SCENE_OK", SID, N, "frames", round(time.time() - T0, 1), "s")
