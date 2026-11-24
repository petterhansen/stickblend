"""Blender shot definitions for a stickblend 2.5D short.

Coordinates use three.js axes (Y up, camera looks down -Z) and are converted to Blender (Z up) via tb().
Each scene returns a list of (build_fn, start_frame, end_frame) segments; frames are 1..N per scene, t = (f - 1) / 30.
"""
import json
import math
import pathlib
import re
import bpy
from mathutils import Quaternion
from stickblend import character, flat, mats, ph, rig, sets, sets2, specs, stage, world
from stickblend.geo import tb

FPS = 30
PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
TL_PATH = PROJECT_DIR / "timeline.json"
TL = json.loads(TL_PATH.read_text(encoding="utf-8")) if TL_PATH.exists() else {"fps": FPS, "lines": []}
LINES = {l["id"]: l for l in TL["lines"]}
S = specs.SPECS
Y = dict(front=0.0, back=math.pi, right=math.pi / 2, left=-math.pi / 2)
P = rig.POSES

# ---------------------------------------------------------------- Timing & math helpers
def norm(s): return re.sub(r"[^\w]", "", s.lower())
def words(sid):
    l = LINES[sid]
    return [dict(w=w["w"], s=w["s"] - l["start"], e=w["e"] - l["start"]) for w in l["words"]]
def wAt(W, needle, nth=0):
    m = [w for w in W if norm(w["w"]).startswith(norm(needle))]
    return m[nth]["s"] if len(m) > nth else 0.0
def nframes(sid):
    if sid not in LINES:
        return 90
    l = LINES[sid]
    return max(1, round(l["end"] * FPS) - round(l["start"] * FPS))
def ease(k): return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
def clamp(x, a, b): return max(a, min(b, x))
def prog(t, a, b): return ease(clamp((t - a) / (b - a), 0, 1)) if b != a else (1.0 if t >= b else 0.0)
def lerp(a, b, k): return a + (b - a) * k
def mixv(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
def cam3(t, ks):
    if t <= ks[0][0]:
        return dict(p=ks[0][1], l=ks[0][2], fov=ks[0][3])
    for a, b in zip(ks, ks[1:]):
        if t <= b[0]:
            k = ease((t - a[0]) / (b[0] - a[0]))
            return dict(p=mixv(a[1], b[1], k), l=mixv(a[2], b[2], k), fov=a[3] + (b[3] - a[3]) * k)
    z = ks[-1]
    return dict(p=z[1], l=z[2], fov=z[3])
def handheld(c, t, amt=1.0):
    p = c["p"]
    return dict(
        c,
        p=(p[0] + math.sin(t * 0.9) * 0.02 * amt, p[1] + math.sin(t * 1.3 + 1) * 0.015 * amt, p[2]),
        roll=math.sin(t * 0.7) * 0.006 * amt,
    )
def to_world(pos, yaw, l):
    return (
        pos[0] + l[0] * math.cos(yaw) + l[2] * math.sin(yaw),
        pos[1] + l[1],
        pos[2] - l[0] * math.sin(yaw) + l[2] * math.cos(yaw),
    )
def merge(*ps):
    out = {}
    for p in ps:
        out.update(p or {})
    return out
def blink(t, off=0.0, per=3.3): return ((t + off) % per) < 0.11

# ---------------------------------------------------------------- Scene building blocks
def camera(N, fn, focus=None, fstop=2.4):
    cd = bpy.data.cameras.new("cam")
    c = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(c)
    bpy.context.scene.camera = c
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1500
    c.rotation_mode = "QUATERNION"
    cd.dof.use_dof = fstop is not None
    if fstop:
        cd.dof.aperture_fstop = fstop
    for f in range(1, N + 1):
        t = (f - 1) / FPS
        k = fn(t)
        p, l = tb(k["p"]), tb(k["l"])
        c.location = p
        q = (l - p).to_track_quat("-Z", "Y")
        if k.get("roll"):
            q = q @ Quaternion((0, 0, 1), k["roll"])
        c.rotation_quaternion = q
        cd.lens = 12 / math.tan(math.radians(k["fov"]) / 2)
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_quaternion", frame=f)
        cd.keyframe_insert("lens", frame=f)
        if fstop:
            fo = tb(focus(t)) if focus else l
            cd.dof.focus_distance = (fo - p).length
            cd.dof.keyframe_insert("focus_distance", frame=f)
    return c

def cam_path(fn, N, n=6):
    return [fn((N - 1) / FPS * i / max(1, n - 1))["p"] for i in range(n)]

def R(spec, pose, t, pos, yaw=0.0, walk=0.0, talk=0.0, phase=0.0):
    return rig.to_world(rig.stick_rig(spec, pose, t, walk=walk, talk=talk, phase=phase), pos, yaw)

CHARS = []
STEP = [2]  # Characters animate on 2s (15 fps) by default; camera moves on 1s (30 fps)

def figure(key, name, fn, N, step=2):
    ch = character.build(S[key], name)
    character.animate(ch, fn, N, step)
    CHARS.append(ch)
    STEP[0] = min(STEP[0], step)
    return ch

def visible(ch, frame, on):
    for o in list(ch.coll.all_objects):
        if "_face_" in o.name:
            continue
        o.hide_render = not on
        o.keyframe_insert("hide_render", frame=frame)

# ================================================================= Scenes (replace with your story)
def hook(N):
    cf = lambda t: handheld(
        cam3(t, [(0, (0, 1.3, 2.8), (0, 1.15, -3.5), 44), ((N - 1) / FPS, (0.15, 1.3, -0.6), (0, 1.2, -3.5), 38)]),
        t,
    )
    sets2.jungle("day", seed=1, subjects=[(0, 1, -3.5)], cam_path=cam_path(cf, N), clearing=2.8)
    figure(
        "tourist",
        "hero",
        lambda t: dict(
            rig=R(S["tourist"], rig.poses_at(t, [(0, "idle"), (0.8, "wave")]), t, (0, 0, -3.5)),
            mood="happy",
            blink=blink(t),
        ),
        N,
    )
    camera(N, cf, lambda t: (0, 1.25, -3.5))

def cta(N):
    cf = lambda t: cam3(t, [(0, (0, 1.35, 1.6), (0, 1.15, -3.5), 42), ((N - 1) / FPS, (0, 1.35, 0.2), (0, 1.2, -3.5), 38)])
    sets2.jungle("dusk", seed=2, subjects=[(0, 1, -3.5)], cam_path=cam_path(cf, N), clearing=2.8)
    figure(
        "tourist",
        "hero",
        lambda t: dict(
            rig=R(S["tourist"], P["shrug"], t, (0, 0, -3.5)),
            mood="smug",
            blink=blink(t),
        ),
        N,
    )
    camera(N, cf, lambda t: (0, 1.25, -3.5))

def segments(sid):
    """Map scene id -> list of (build_fn, first_frame, last_frame). Split scenes return multiple segments."""
    N = nframes(sid)
    table = {
        "hook": [(hook, 1, N)],
        "cta": [(cta, 1, N)],
    }
    return table[sid]
