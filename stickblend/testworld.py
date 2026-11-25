"""Testwelt: Dschungellichtung im Gegenlicht mit Dunst, Tiefenschaerfe und Vordergrund-Pflanzen; Onoda kommt rein, Suzuki erschrickt.
  blender -b --factory-startup -P stickblend/testworld.py -- <out_dir> [preset] [still|anim]
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
from mathutils import Vector
from stickblend import rig, character, stage, specs, world, mats

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.abspath("out_world"); PRESET = argv[1] if len(argv) > 1 else "preview"; MODE = argv[2] if len(argv) > 2 else "still"
FR = int(os.environ.get("FR", 90)); T0 = time.time()
stage.reset()

# ---------- Kamera (zuerst, damit die Sichtfreiheit den Pfad kennt) ----------
CAM_A, CAM_B, LOOK = (0.3, -6.4, 0.75), (0.12, -5.3, 0.8), (0.0, 0.0, 1.0)
SUBJ = [(-0.5, 0.2, 1.0), (0.5, 0.0, 1.0), (2.4, 0.4, 1.0)]

# ---------- Welt ----------
world.ground("5f7d3c", 80, "47622c")
world.sky(top="8fc3ea", horizon="f6e3b8", strength=1.1, haze=float(os.environ.get("HAZE", 0.006)), haze_color=(1.0, 0.9, 0.75))
world.sun((58, 0, 162), energy=4.5, color=(1.0, 0.88, 0.7), angle=0.05)          # Gegenlicht, tief
fill = bpy.data.lights.new("fill", "SUN"); fill.energy = 0.6; fill.color = (0.75, 0.85, 1.0)
fo = bpy.data.objects.new("fill", fill); bpy.context.scene.collection.objects.link(fo); fo.rotation_euler = (math.radians(60), 0, math.radians(-20))
avoid = world.keep_clear([CAM_A, CAM_B], SUBJ, radius=0.75, near=1.6)
clearing = lambda x, y: (x * x + (y - 0.5) ** 2) < 3.2 ** 2   # Lichtung um die Figuren
env = bpy.data.collections.new("env"); bpy.context.scene.collection.children.link(env)
PALMS = ["PalmTree_1", "PalmTree_2", "PalmTree_3", "PalmTree_4", "PalmTree_5"]
for o in world.scatter(PALMS, 26, (-16, 16, 1, 26), lambda x, y: clearing(x, y) or avoid(x, y), (1.5, 2.3), 3, env): pass
for o in world.scatter(["NormalTree_1", "NormalTree_3", "NormalTree_5"], 8, (-20, 20, 12, 30), None, (1.6, 2.2), 4, env): pass
for o in world.scatter(["Bush_Large", "Bush", "Bush_Small", "Bush_Flowers"], 34, (-10, 10, -2, 16), lambda x, y: clearing(x, y) and abs(x) < 2.6 or avoid(x, y), (0.8, 1.5), 5, env): pass
for o in world.scatter(["Plant_1", "Plant_2", "Grass_Large", "Grass_Small", "Flower_3_Clump", "Plant_Flowers"], 120, (-9, 9, -3, 12), avoid, (0.7, 1.4), 6, env): pass
for o in world.scatter(["Rock_1", "Rock_2", "Rock_4"], 8, (-8, 8, 0, 12), lambda x, y: clearing(x, y) or avoid(x, y), (0.5, 1.0), 7, env): pass
# Vordergrund am Bildrand (wird durch die Tiefenschaerfe weich, rahmt das Bild wie in der Referenz)
world.place("Bush_Large", (-1.05, -4.5, -0.35), 0.4, 0.75, env); world.place("Bush", (1.1, -4.2, -0.3), 1.2, 0.7, env)

# ---------- Figuren ----------
mats.set_scene_light(tint=(1.0, 0.97, 0.92), rim_strength=0.85, rim_color=(1.0, 0.86, 0.62), rim_dir=(-0.3, 0.75, 0.6))
S_on, S_su = specs.SPECS["onodaOld"], specs.SPECS["suzuki"]
on = character.build(S_on, "onoda"); su = character.build(S_su, "suzuki")
def f_on(t):
    x = max(0.5, 2.4 - t * 1.4); w = 1.0 if x > 0.51 else max(0.0, 1 - (t - 1.3) * 4)
    pose = rig.poses_at(t, [(0, "idle"), (1.5, "stop")])
    R = rig.to_world(rig.stick_rig(S_on, pose, t, walk=w), (x, 0, 0.0), yaw=-math.pi / 2 * w + (-0.6) * (1 - w))
    return dict(rig=R, mood="suspicious" if t < 1.6 else "determined", blink=(t % 2.9) < 0.1)
def f_su(t):
    pose = rig.poses_at(t, [(0, "idle"), (0.9, "handsUp")], blend=0.18)
    R = rig.to_world(rig.stick_rig(S_su, pose, t, phase=2.0), (-0.5, 0, -0.2), yaw=0.55)
    return dict(rig=R, mood="neutral" if t < 0.9 else "shock", blink=((t + 0.7) % 3.1) < 0.1)
character.animate(on, f_on, FR); character.animate(su, f_su, FR)

# ---------- Kamera, Tiefenschaerfe, Gluehen ----------
cam = stage.camera(CAM_A, LOOK, lens=28, dof=None if os.environ.get("DOF", "1") == "0" else 2.0)
cam.keyframe_insert("location", frame=1); cam.location = CAM_B; cam.keyframe_insert("location", frame=FR)
if cam.data.dof.use_dof: cam.data.dof.focus_distance = (Vector(CAM_A) - Vector((0, 0, 1))).length
sc = stage.render_setup(PRESET); sc.frame_start, sc.frame_end = 1, FR
if os.environ.get("SPP"): sc.eevee.taa_render_samples = int(os.environ["SPP"])
if os.environ.get("SHADOW", "1") == "0": sc.eevee.use_shadows = False
if os.environ.get("SHOPT", "1") == "1": world.optimize_shadows(max_dist=float(os.environ.get("SHDIST", 9)), cam=CAM_A)
if os.environ.get("GLOW", "1") == "1": world.glow(0.9, 0.35, 7)
os.makedirs(OUT, exist_ok=True)
print("BUILD_S", round(time.time() - T0, 1), "OBJ", len(bpy.data.objects))
T1 = time.time()
if MODE == "anim":
    sc.render.filepath = os.path.join(OUT, "f####"); bpy.ops.render.render(animation=True)
    print("RENDER_S", round(time.time() - T1, 1), "PER_FRAME", round((time.time() - T1) / FR, 3))
else:
    for f in (1, 45, 80):
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"still_{f}.png"); bpy.ops.render.render(write_still=True)
    print("STILLS_S", round(time.time() - T1, 1))
