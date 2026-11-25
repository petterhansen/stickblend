"""One-Take-Short: EIN durchgehender Kameraflug ueber globale Frames (Bild 1 = 0.0 s), gerendert in Sets.
Vorbilder mit voller Ausstattung: examples/aufzug (fahrende Kabine, Roentgen, Zaehler) und examples/wolkenkratzer.

Prinzipien (SHORTS-REGELN.md, STICKMAN-WORKFLOW.md §6):
- Set-Grenzen und alle Aktionen haengen an gesprochenen Woertern (wt("wort")) -> neue Stimme verschiebt alles automatisch.
- Jedes Set baut seine Welt selbst; die Zeitfunktionen sind global, damit die Kamera ueber Set-Grenzen stetig bleibt.
- Kamera: campath.path mit Keys; "stop" an Keys vor grossen Richtungswechseln. Nie durch Waende, Drehung <= ~90 deg/s.
- Figuren auf Zweiern (step=2). In fahrenden Objekten: after_flatten() -> flat.attach(root, ...).
- Gehaltene Requisiten mit flat.flat_pt in die 2.5D-Hand setzen.
Koordinaten: Blender-Achsen (x rechts, y Tiefe, z oben); Figuren-Rig in three-Achsen -> F() wandelt um.
"""
import bpy, json, math, os, re
from mathutils import Vector
from stickblend import rig, character, specs, mats, sets2, flat, campath
from stickblend.geo import tb

FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "src", "timeline.json"), encoding="utf8"))
WORDS = [dict(w=w["w"], s=w["s"], e=w["e"], line=l["id"]) for l in TL["lines"] for w in l["words"]]
END_T = WORDS[-1]["e"] + 0.22            # harter Schnitt kurz nach dem letzten Wort (Loop!)
NFR = round(END_T * FPS)
S = specs.SPECS; P = rig.POSES

def norm(s): return re.sub(r"[^\wäöüß0-9]", "", s.lower())
def wt(needle, nth=0, line=None, end=False):
    """Startzeit (oder Ende) eines Wortes. line= eingrenzen, wenn das Wort mehrfach vorkommt!"""
    m = [w for w in WORDS if norm(w["w"]).startswith(norm(needle)) and (line is None or w["line"] == line)]
    if len(m) <= nth: raise KeyError(f"Wort nicht in der Zeitachse: {needle!r} (line={line})")
    return m[nth]["e"] if end else m[nth]["s"]
def fr(t): return int(round(t * FPS)) + 1
def tf(f): return (f - 1) / FPS
def clamp(x, a, b): return max(a, min(b, x))
def ease(k): return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
def prog(t, a, b): return ease(clamp((t - a) / (b - a), 0, 1)) if b != a else float(t >= b)
def lerp(a, b, k): return a + (b - a) * k
def merge(*ps):
    out = {}
    for p in ps: out.update(p or {})
    return out
def F(x, y, z=0.0): return (x, z, -y)             # Blender-Punkt -> three (Figuren-Rig)
def B(p3): return Vector(tb(p3))                    # three -> Blender
def yaw_to(dx, dy): return math.atan2(dx, -dy)      # Figur schaut in Blender-Richtung (dx, dy)

# ---------------------------------------------------------------- Figuren
CHARS = []; STEP = [2]; SEG = [1, 1]
def R(spec, pose, t, pos3, yaw=0.0, walk=0.0, talk=0.0):
    return rig.to_world(rig.stick_rig(spec, pose, t, walk=walk, talk=talk), pos3, yaw)
def figure(key, name, fn, step=2):
    f0, f1 = SEG; t0 = tf(f0)
    ch = character.build(S[key], name); character.animate(ch, lambda t: fn(t + t0), f1 - f0 + 1, step, start=f0)
    CHARS.append(ch); STEP[0] = min(STEP[0], step); return ch
def hand(rg, side): return B(tuple(rg["arms"][side]["h"]))   # 0 = links, 1 = rechts
def blink(t, seed=0): return rig.blink_at(t, seed)
def grade(**kw): sets2.GRADE.clear(); sets2.GRADE.update(kw)

def mat(name, hexcol, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = mats.lin(hexcol)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal; return m
def box(name, center, size, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center); o = bpy.context.active_object; o.name = name
    o.scale = size; o.data.materials.append(m); return o

# ---------------------------------------------------------------- Zeitmarken (an Woerter gebunden)
T_B = wt("dann") - 0.1                  # Set A -> B: Kamera faehrt durch die offene Tuer (nie durch eine Wand)

# ---------------------------------------------------------------- Kamera (global, ein Flug)
KEYS = [
    (0.0, (-1.2, -4.2, 1.5), (0.0, 0.0, 1.1), 50),        # Hook: sofort mitten im Geschehen
    (T_B - 0.6, (0.6, -3.0, 1.6), (1.6, 0.0, 1.2), 46, "stop"),
    (T_B + 0.5, (2.6, -0.4, 1.6), (3.0, 4.0, 1.4), 54),    # durch die Tueroeffnung bei x = 3
    (END_T, (3.0, 3.0, 1.7), (3.0, 8.0, 1.3), 50),
]
def cam(t): return campath.path(t, KEYS)

def du_fn(t):
    p3, yw, wa = rig.walk_along(t, [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (T_B, 2.6, -0.8), (END_T, 3.0, -6.0)])   # erst zur Kamera schauen (Hook), dann los
    mood = "shock" if t < 1.0 else "determined"
    return dict(rig=R(S["du"], P["idle"], t, p3, yw, walk=wa), mood=mood, blink=blink(t, 1))

# ---------------------------------------------------------------- Sets
def room_a():
    floor = mat("floor", "c9a46a", 0.5); wall = mat("wall", "4f7fd0", 0.8)
    box("floor_a", (1.5, 0, -0.05), (10, 10, 0.1), floor)
    for x0, x1 in ((-3.5, 2.4), (3.6, 6.5)):    # Wand bei y = 2 mit Tueroeffnung x 2.4..3.6
        box(f"wall_a{x0}", ((x0 + x1) / 2, 2.0, 1.5), (x1 - x0, 0.2, 3.0), wall)
    box("lintel", (3.0, 2.0, 2.75), (1.2, 0.2, 0.5), wall)

def room_b():
    box("floor_b", (3.0, 6.0, -0.05), (8, 8, 0.1), mat("floor_b", "e05a3a", 0.5))
    box("back_b", (3.0, 10.0, 1.5), (8, 0.2, 3.0), mat("wall_b", "f2c14e", 0.8))

def light_setup():
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.0; sun.angle = 0.1
    o = bpy.data.objects.new("sun", sun); bpy.context.scene.collection.objects.link(o); o.rotation_euler = (math.radians(50), 0, math.radians(-30))
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.45, 0.7, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8

def shot_A():
    f0, f1 = SEG
    room_a(); room_b()   # Raum B ist durch die Tuer schon sichtbar
    light_setup(); mats.set_scene_light(tint=(1.0, 0.95, 0.88), rim_strength=0.0)
    grade(lift=(0.98, 0.99, 1.03), gain=(1.05, 1.0, 0.95), sat=1.15, contrast=0.1)
    figure("du", "du", du_fn).flat_bias = 0.2
    campath.camera(cam, f0, f1)

def shot_B():
    f0, f1 = SEG
    room_a(); room_b(); light_setup(); mats.set_scene_light(tint=(1.0, 0.95, 0.88), rim_strength=0.0)
    grade(lift=(0.98, 0.99, 1.03), gain=(1.05, 1.0, 0.95), sat=1.15, contrast=0.1)
    figure("du", "du", du_fn).flat_bias = 0.2
    campath.camera(cam, f0, f1)

SHOTS = {"A": (shot_A, 1, fr(T_B) - 1), "B": (shot_B, fr(T_B), NFR)}
RT = {}; MB = {}
