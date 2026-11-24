"""Kontroll-Render fuer neue/geaenderte Figuren.

  blender -b --factory-startup -P stickblend/lineup.py -- <out_dir> [preset] [figuren,...]

Erzeugt:
  lineup.png      alle Figuren nebeneinander (verschiedene Posen/Mimiken)
  turn_<id>.png   Drehung einer Figur: vorne, 3/4, Profil, hinten (je ein Bild)
"""
import sys, os, math, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
import stickblend
from stickblend import rig, character, stage, specs, mats

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.abspath("out_lineup"); PRESET = argv[1] if len(argv) > 1 else "preview"
IDS = argv[2].split(",") if len(argv) > 2 else list(specs.SPECS)
os.makedirs(OUT, exist_ok=True)

POSE_MOOD = [("idle", "neutral"), ("wave", "happy"), ("hips", "smug"), ("think", "suspicious"), ("salute", "proud"), ("shrug", "worry"), ("point", "determined"), ("handsUp", "shock"), ("read", "tired")]

# ---------- Lineup ----------
stage.reset(); stage.studio()
n = len(IDS); sp = 0.95
for i, sid in enumerate(IDS):
    spec = specs.SPECS[sid]; ch = character.build(spec, sid)
    pose, mood = POSE_MOOD[i % len(POSE_MOOD)]
    R = rig.to_world(rig.stick_rig(spec, rig.POSES[pose], t=0.4, phase=i), ((i - (n - 1) / 2) * sp, 0, 0), yaw=0.25 * math.sin(i * 1.7))
    character.pose_frame(ch, 1, R, mood=mood, blink=False, mouth=0.0)
w = (n - 1) * sp + 1.2
stage.camera((0, -(w * 0.5 / math.tan(math.radians(20))) * 0.62 - 1.0, 1.0), (0, 0, 0.85), lens=32)
sc = stage.render_setup(PRESET); sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.frame_set(1); sc.render.filepath = os.path.join(OUT, "lineup.png"); bpy.ops.render.render(write_still=True)

# ---------- Drehung (erste Figur bzw. alle angegebenen) ----------
for sid in IDS[:3]:
    stage.reset(); stage.studio()
    spec = specs.SPECS[sid]
    for k, yaw in enumerate((0.0, -0.75, -1.57, math.pi)):
        ch = character.build(spec, f"{sid}{k}")
        R = rig.to_world(rig.stick_rig(spec, rig.POSES["idle"], t=0.2), ((k - 1.5) * 0.9, 0, 0), yaw=yaw)
        character.pose_frame(ch, 1, R, mood="neutral")
    stage.camera((0, -5.2, 1.0), (0, 0, 0.85), lens=35)
    sc = stage.render_setup(PRESET); sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.frame_set(1); sc.render.filepath = os.path.join(OUT, f"turn_{sid}.png"); bpy.ops.render.render(write_still=True)
print("LINEUP_OK", OUT)
