"""Beispiel-Einstellung (Vorlage fuer Shot-Skripte): Tourist laeuft rein, bleibt stehen, winkt; Verkaeuferin antwortet.
  blender -b --factory-startup -P stickblend/demo_shot.py -- <out_dir> [preset]
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
from mathutils import Vector
from stickblend import rig, character, stage, specs

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.abspath("out_demo"); PRESET = argv[1] if len(argv) > 1 else "final"
FR = 90
stage.reset(); stage.studio()
tour = character.build(specs.SPECS["tourist"], "tourist"); clerk = character.build(specs.SPECS["clerk"], "clerk")
S1, S2 = specs.SPECS["tourist"], specs.SPECS["clerk"]

def f_tourist(t):
    x = min(-0.45, -2.2 + t * 1.4); walking = 1.0 if x < -0.46 else max(0.0, 1 - (t - 1.25) * 4)
    pose = rig.poses_at(t, [(0, "idle"), (1.5, "wave"), (2.4, "idle")])
    R = rig.to_world(rig.stick_rig(S1, pose, t, walk=walking), (x, 0, 0), yaw=math.pi / 2 * walking + 0.5 * (1 - walking))
    return dict(rig=R, mood="happy" if t > 1.4 else "neutral", blink=(t % 2.6) < 0.1)
def f_clerk(t):
    pose = rig.poses_at(t, [(0, "idle"), (2.1, "offer")])
    R = rig.to_world(rig.stick_rig(S2, pose, t, talk=1.0 if 2.1 < t < 2.9 else 0.0, phase=1.3), (0.55, 0, 0.1), yaw=-0.55)
    return dict(rig=R, mood="happy" if t > 2.0 else "neutral", mouth=R["mouth"], blink=((t + 1.1) % 3.1) < 0.1)

T0 = time.time()
character.animate(tour, f_tourist, FR); character.animate(clerk, f_clerk, FR)
cam = stage.camera((0.0, -4.4, 1.15), (0.05, 0, 0.9), lens=28)
cam.keyframe_insert("location", frame=1); cam.location = (0.05, -3.7, 1.05); cam.keyframe_insert("location", frame=FR)  # langsame Fahrt (jedes Bild)
sc = stage.render_setup(PRESET); sc.frame_start, sc.frame_end = 1, FR
os.makedirs(OUT, exist_ok=True); sc.render.filepath = os.path.join(OUT, "f####")
print("BUILD_S", round(time.time() - T0, 1)); T1 = time.time()
bpy.ops.render.render(animation=True)
print("RENDER_S", round(time.time() - T1, 1), "PER_FRAME", round((time.time() - T1) / FR, 3))
