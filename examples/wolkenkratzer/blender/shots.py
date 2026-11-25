"""Wolkenkratzer-Short: ein durchgehender Kameraflug, gerendert als Sets ueber GLOBALE Frames (1 = 0.0 s).
Sets/Kamera in Blender-Achsen; Figuren intern in three-Achsen (rig), Umrechnung: three (x, y, z) = blender (x, -z... ) -> F()/B().
"""
import bpy, json, math, os, re, sys, random
from mathutils import Vector, Quaternion, Matrix
from stickblend import rig, character, stage, specs, world, mats, sets, sets2, flat, ph
from stickblend.geo import tb
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wk

FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "src", "timeline.de.json"), encoding="utf8"))
WORDS = [dict(w=w["w"], s=w["s"], e=w["e"], line=l["id"]) for l in TL["lines"] for w in l["words"]]
END_T = WORDS[-1]["e"] + 0.22                     # harter Schnitt kurz nach dem letzten Wort
NFR = round(END_T * FPS)
S = specs.SPECS; P = rig.POSES

def norm(s): return re.sub(r"[^\wäöüß]", "", s.lower())
def wt(needle, nth=0, line=None, end=False):
    m = [w for w in WORDS if norm(w["w"]).startswith(norm(needle)) and (line is None or w["line"] == line)]
    return (m[nth]["e"] if end else m[nth]["s"]) if len(m) > nth else 0.0
def fr(t): return int(round(t * FPS)) + 1
def tf(f): return (f - 1) / FPS
def ease(k): return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
def clamp(x, a, b): return max(a, min(b, x))
def prog(t, a, b): return ease(clamp((t - a) / (b - a), 0, 1)) if b != a else (1.0 if t >= b else 0.0)
def lin_(t, a, b): return clamp((t - a) / (b - a), 0, 1) if b != a else float(t >= b)
def lerp(a, b, k): return a + (b - a) * k
def mixv(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(len(a)))
def merge(*ps):
    out = {}
    for p in ps: out.update(p or {})
    return out

# Blender <-> three
def F(x, y, z=0.0): return (x, z, -y)               # Blender-Punkt -> three
def B(p3): return Vector(tb(p3))                    # three -> Blender
def yaw_to(dx, dy): return math.atan2(dx, -dy)      # three-Yaw, damit die Figur in Blender-Richtung (dx, dy) schaut

# ---------------------------------------------------------------- Kamerapfad (Hermite durch Keys, ohne Stopps)
def path(t, keys):
    """keys: [(t, p, l, fov), ...] in Blender-Achsen. Weiche Kurve mit stetiger Geschwindigkeit."""
    if t <= keys[0][0]: k = keys[0]; return dict(p=k[1], l=k[2], fov=k[3])
    if t >= keys[-1][0]: k = keys[-1]; return dict(p=k[1], l=k[2], fov=k[3])
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    a, b = keys[i], keys[i + 1]; h = b[0] - a[0]; u = (t - a[0]) / h
    def tan(j, idx):
        k0 = keys[max(0, j - 1)]; k1 = keys[min(len(keys) - 1, j + 1)]
        if k1[0] == k0[0]: return tuple(0.0 for _ in keys[j][idx]) if idx < 3 else 0.0
        if idx < 3: return tuple((k1[idx][c] - k0[idx][c]) / (k1[0] - k0[0]) for c in range(3))
        return (k1[idx] - k0[idx]) / (k1[0] - k0[0])
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    out = {}
    for idx, nm in ((1, "p"), (2, "l")):
        ma, mb = tan(i, idx), tan(i + 1, idx)
        if len(a) > 4 and a[4] == "stop": ma = (0, 0, 0)
        if len(b) > 4 and b[4] == "stop": mb = (0, 0, 0)
        out[nm] = tuple(h00 * a[idx][c] + h10 * h * ma[c] + h01 * b[idx][c] + h11 * h * mb[c] for c in range(3))
    out["fov"] = a[3] + (b[3] - a[3]) * (3 * u * u - 2 * u ** 3)
    return out

def camera(fn, f0, f1, focus=None, fstop=None, clip=(0.02, 600)):
    cd = bpy.data.cameras.new("cam"); c = bpy.data.objects.new("cam", cd); bpy.context.scene.collection.objects.link(c); bpy.context.scene.camera = c
    cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24; cd.clip_start, cd.clip_end = clip; c.rotation_mode = "QUATERNION"
    cd.dof.use_dof = fstop is not None
    if fstop: cd.dof.aperture_fstop = fstop
    prev = None
    for f in range(f0, f1 + 1):
        t = tf(f); k = fn(t); p, l = Vector(k["p"]), Vector(k["l"])
        c.location = p; q = (l - p).to_track_quat("-Z", "Y")
        if k.get("roll"): q = q @ Quaternion((0, 0, 1), k["roll"])
        if prev is not None and prev.dot(q) < 0: q.negate()
        prev = q.copy(); c.rotation_quaternion = q; cd.lens = 12 / math.tan(math.radians(k["fov"]) / 2)
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
        if fstop:
            fo = Vector(focus(t)) if focus else l; cd.dof.focus_distance = max(0.05, (fo - p).length); cd.dof.keyframe_insert("focus_distance", frame=f)
    for fc in _fcurves(c) + _fcurves(cd):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
    return c

def _fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    try: return list(ad.action.fcurves)
    except AttributeError:   # Blender 5: geschichtete Actions
        out = []
        for ly in ad.action.layers:
            for st in ly.strips:
                for cb in st.channelbags: out += list(cb.fcurves)
        return out

# ---------------------------------------------------------------- Figuren (globale Zeit)
CHARS = []; STEP = [2]; SEG = [1, 1]
def R(spec, pose, t, pos3, yaw=0.0, walk=0.0, talk=0.0, phase=0.0):
    return rig.to_world(rig.stick_rig(spec, pose, t, walk=walk, talk=talk, phase=phase), pos3, yaw)
def figure(key, name, fn, step=2):
    f0, f1 = SEG; t0 = tf(f0)
    ch = character.build(S[key], name); character.animate(ch, lambda t: fn(t + t0), f1 - f0 + 1, step, start=f0)
    CHARS.append(ch); STEP[0] = min(STEP[0], step); return ch
def hand(rg, side):   # Hand-Weltposition (Blender) aus einem Welt-Rig; side 0 = links, 1 = rechts
    return B(tuple(rg["arms"][side]["h"]))
def blink(t, seed=0): return rig.blink_at(t, seed)

def prop_follow(o, f0, f1, fn, step=1):
    """fn(t) -> (loc Vector, rot Euler/Quaternion|None, visible)"""
    o.rotation_mode = "QUATERNION"
    for f in range(f0, f1 + 1, step):
        loc, rot, vis = fn(tf(f)); o.location = loc
        if rot is not None: o.rotation_quaternion = rot if isinstance(rot, Quaternion) else rot.to_quaternion()
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f)
        for oo in [o] + list(o.children_recursive):
            if oo.get("own_vis"): continue
            oo.hide_render = not vis; oo.keyframe_insert("hide_render", frame=f)

def toward_cam(loc, ch, t, camf, extra=0.0):
    """Requisit auf dieselbe Tiefe wie die 2.5D-Figur ziehen (flat_bias Richtung Kamera); extra = vor den Koerper."""
    b = (getattr(ch, "flat_bias", 0.0) or 0.0) + extra
    if not b: return loc
    cp = Vector(camf(t)["p"]); return loc + (cp - loc).normalized() * b

def flat_pt(p, rg, ch, t, camf, extra=0.0):
    """Punkt so verschieben, wie flat.flatten die Figur abbildet: orthografisch auf die Ebene durch den Torso
    (Normale zur Kamera), dann flat_bias (+extra) Richtung Kamera bei gleicher Bildposition."""
    a = B(tuple(rg["hipC"])); cp = Vector(camf(t)["p"]); n = (cp - a).normalized()
    q = p - n * n.dot(p - a)
    b = (getattr(ch, "flat_bias", 0.0) or 0.0) + extra; d = (cp - a).length
    return cp + (q - cp) * max(0.05, (d - b) / d) if b else q

def coffee_cup(name="cup", s=1.0):
    w = wk.principled("cup_white", "f6f2ea", 0.45); sl = wk.principled("cup_sleeve", "a8642e", 0.7); lid = wk.principled("cup_lid", "2a2a30", 0.4)
    c = wk.cyl(name, (0, 0, 0), 0.04 * s, 0.13 * s, w, r2=0.048 * s, n=24)
    wk.cyl(name + "_sleeve", (0, 0, 0.0), 0.0455 * s, 0.05 * s, sl, n=24).parent = c
    wk.cyl(name + "_lid", (0, 0, 0.07 * s), 0.05 * s, 0.018 * s, lid, n=24).parent = c
    return c

def visible(ch, frame, on):
    for o in list(ch.coll.all_objects):
        if "_face_" in o.name: continue
        o.hide_render = not on; o.keyframe_insert("hide_render", frame=frame)

def grade(**kw): sets2.GRADE.clear(); sets2.GRADE.update(kw)

# ================================================================= SHOT A: Lobby -> Aufzug -> Knoepfe -> Tueren zu
T_A1 = wt("lift") - 0.14
def shot_A():
    f0, f1 = SEG
    k_knoepf, k_drei, k_sechs, k_tueren, k_gleiten = wt("knöpfen"), wt("dreißig"), wt("sechsundvierzig"), wt("goldenen"), wt("gleiten")
    t_press = wt("sechsundvierzig") + 0.78
    door = lambda f: 1.0 - prog(tf(f), k_gleiten - 0.16, k_gleiten + 0.9)
    wk.world_color("3a2818", 1.0)
    wk.lobby(); wk.cabin()
    wk.doors(door, NFR)
    wk.glow_button("60", fr(t_press))
    flat.STICK_COLOR = None; flat.LIGHT_POS = None
    mats.set_scene_light(tint=(1.0, 0.92, 0.82), rim_strength=0.0)
    grade(lift=(1.0, 0.99, 1.01), gain=(1.06, 1.0, 0.92), sat=1.12, contrast=0.1)
    # Du: Lobby -> Kabine -> zum Tastenfeld, drueckt 60, tritt zurueck und schaut zur Tuer
    pos_end = (0.74, 6.95); back = (-0.55, 7.5)
    wp = [(0.0, 0.05, 2.6), (2.7, 0.2, -6.85), (3.3, pos_end[0], -pos_end[1]), (t_press + 0.45, pos_end[0], -pos_end[1]), (t_press + 1.1, back[0], -back[1])]
    def du(t):
        p3, yw, wa = rig.walk_along(t, wp)
        if 2.9 < t <= t_press + 0.45: yw = lerp(yw, math.pi / 2, prog(t, 2.9, 3.5))
        if t > t_press + 0.45: yw = lerp(math.pi / 2, 0.0, prog(t, t_press + 0.45, t_press + 1.1)); wa = min(wa, 0.6)
        press = prog(t, t_press - 0.45, t_press - 0.05) * (1 - prog(t, t_press + 0.25, t_press + 0.6))
        by, bz = wk.BTN["60"]
        fx = wk.PANEL["x"] - 0.03 - pos_end[0]; lx = by - pos_end[1] - 0.06; bz = bz + 0.09   # Figur schaut nach +x: links = +y (Korrektur ortho. Hand)
        hold = prog(t, 3.2, 3.9)   # erst seitlich haengend (Gehen), in der Kabine Becher vor den Bauch
        pose = merge(P["idle"], {"handL": (lerp(0.27, 0.16, hold), lerp(0.82, 0.98, hold), lerp(0.08, 0.24, hold))})
        if press > 0: pose = merge(pose, {"handR": (lerp(-0.22, lx, press), lerp(0.75, bz, press), lerp(0.05, fx, press)), "headPitch": -8 * press})
        mood = "puzzled" if t > k_knoepf - 0.2 else "neutral"
        return dict(rig=R(S["du"], pose, t, p3, yw, walk=wa), mood=mood, blink=blink(t, 1), look=(0.6, -0.3) if 3.4 < t < t_press + 0.5 else (0, 0))
    ch = figure("du", "du", du); ch.flat_bias = 0.3
    cup = coffee_cup()
    def cupf(t):
        rg = du(t)["rig"]; h = flat_pt(hand(rg, 0), rg, ch, t, lambda tt: path(tt, keys), 0.03); return (h + Vector((0, 0, -0.05)), None, True)
    # Kamera
    PX, PY = wk.PANEL["x"], wk.PANEL["y"]
    keys = [
        (0.0, (-0.3, -7.0, 0.85), (0.0, 4.0, 1.15), 44),
        (1.7, (-0.3, -1.4, 1.0), (0.05, 6.5, 1.25), 44),
        (3.1, (-0.1, 4.6, 1.25), (0.6, 7.2, 1.25), 46),
        (k_knoepf, (0.2, 6.2, 1.2), (PX, PY, 1.14), 44),
        (k_knoepf + 1.4, (0.42, 6.38, 1.1), (PX, PY, 1.1), 42),
        (k_drei, (0.5, 6.46, 0.78), (PX, PY, 0.72), 40),
        (k_sechs + 0.15, (0.5, 6.46, 1.14), (PX, PY, 1.14), 40),
        (t_press - 0.05, (-0.22, 6.14, 1.42), (1.0, 6.92, 1.34), 60),
        (t_press + 0.55, (-0.05, 5.6, 1.6), (0.1, 7.4, 1.45), 54),
        (k_gleiten - 0.15, (0.0, 3.9, 1.55), (-0.1, 7.2, 1.45), 50),
        (k_gleiten + 0.35, (0.0, 5.0, 1.85), (0.0, 7.4, 1.85), 52),
        (k_gleiten + 0.56, (0.05, 6.05, 2.02), (0.2, 8.0, 2.04), 56),
        (T_A1 + 0.04, (0.3, 7.965, 2.1), (0.3, 9.0, 2.1), 58),
    ]
    camera(lambda t: path(t, keys), f0, f1, focus=lambda t: (PX, PY, 1.0) if k_knoepf < t < t_press - 0.3 else path(t, keys)["l"], fstop=2.2)
    prop_follow(cup, f0, f1, cupf, 2)

# ================================================================= SHOT B: Schacht
T_B1 = wt("du", line="cavern") + 0.27
def shot_B():
    f0, f1 = SEG; t0 = T_A1
    k_lift, k_bremst, k_ab = wt("lift"), wt("bremst"), wt("ab", line="shaft")
    Z0 = wk.fz(25) + 0.4; GZ = 140.0; dur = T_B1 - t0
    def cab_z(t):   # Kabinenboden: beschleunigt, dann ~60 m/s
        u = max(0.0, t - (t0 + 0.1)); return Z0 + 24 * u * u if u < 1.6 else Z0 + 61.4 + 60 * (u - 1.6)
    def cam_z(t):   # Kamera faehrt mit (18 -> 25 -> 30), bleibt dann in der Luecke zurueck und bremst am Gitter
        u = max(0.0, t - t0); ua, a = 1.4, 14.0
        if u < ua: return Z0 + 2.1 + a * u * u
        za = Z0 + 2.1 + a * ua * ua; D = GZ + 0.05 - za; Tr = max(0.3, dur - ua); pw = max(1.5, 2 * a * ua * Tr / D)
        k = min(1.0, (u - ua) / Tr); return za + D * (1 - (1 - k) ** pw)
    wk.world_color("0e1830", 1.6)
    wk.shaft(cab_z, f1 - f0 + 1, f0, zmin=70, zmax=260, grille_z=GZ)
    wk.haze_box((0, 0.3, 150), (3.2, 3.4, 180), 0.03, (0.7, 0.8, 1.0), 0.6, name="sh_haze")
    grade(lift=(0.97, 0.98, 1.05), gain=(1.06, 1.0, 0.94), sat=1.15, contrast=0.12)
    gz = GZ
    def cam(t):
        z = cam_z(t)
        pan = prog(t, t0 + 0.05, t0 + 0.75); up = prog(t, t0 + 1.4, t0 + 2.4); turn = prog(t, T_B1 - 1.05, T_B1 - 0.4)
        p = Vector((lerp(0.0, 0.55, pan), lerp(0.95, 1.5, pan), z))
        l = Vector((lerp(0.0, -1.6, pan), lerp(3.0, 1.0, pan), z + lerp(0.0, 1.4, pan) + 4.0 * up))
        if turn > 0:
            p = p.lerp(Vector((lerp(0.55, 1.05, prog(t, T_B1 - 0.55, T_B1)), lerp(1.5, 0.95, turn), gz + 0.05)), turn)
            l = l.lerp(Vector((4.0, 0.95, gz)), turn)
        return dict(p=tuple(p), l=tuple(l), fov=lerp(64, 72, pan) - 10 * turn)
    camera(cam, f0, f1, None, None, clip=(0.02, 400))

# ================================================================= SHOT C: Betonhoehle + Bauprüfer
T_C1 = wt("klingt") - 0.18
def clipboard(name="clip"):
    b = wk.box(name, (0, 0, 0), (0.23, 0.31, 0.01), wk.principled("clip_board", "8a5a32", 0.6))
    wk.box(name + "_paper", (0, -0.015, 0.0065), (0.205, 0.26, 0.002), wk.principled("clip_paper", "f6f3ea", 0.8)).parent = b
    wk.box(name + "_clip", (0, 0.14, 0.012), (0.1, 0.04, 0.015), wk.principled("clip_metal", "b8bcc4", 0.3, 1.0)).parent = b
    for k in range(5): wk.box(f"{name}_line{k}", (-0.02, 0.06 - k * 0.035, 0.0078), (0.15, 0.006, 0.001), wk.principled("clip_ink", "8a8e98", 0.8)).parent = b
    t = wk.text(name + "_ok", "GENEHMIGT", (0.0, -0.04, 0.0105), 0.042, rot=(0, 0, 0.16), mat=wk.emit("stamp_green", "12b04e", 1.4), font=wk.FONT_I)
    t.parent = b; fr_ = wk.box(name + "_okframe", (0.0, -0.04, 0.0095), (0.21, 0.075, 0.0008), wk.emit("stamp_green", "12b04e", 1.4)); fr_.parent = b; fr_.rotation_euler = (0, 0, 0.16)
    hole = wk.box(name + "_okhole", (0.0, -0.04, 0.01), (0.196, 0.061, 0.0008), wk.principled("clip_paper", "f6f3ea", 0.8)); hole.parent = b; hole.rotation_euler = (0, 0, 0.16)
    return b, (t, fr_, hole)

def stamp(name="stamp"):
    b = wk.box(name, (0, 0, 0.0175), (0.1, 0.065, 0.035), wk.principled("stamp_rubber", "1d1d22", 0.7)); b.data.transform(Matrix.Translation((0, 0, 0.0175))); b.location = (0, 0, 0)
    wk.cyl(name + "_neck", (0, 0, 0.06), 0.02, 0.08, wk.principled("stamp_wood", "a8743e", 0.5), n=12).parent = b
    wk.cyl(name + "_knob", (0, 0, 0.12), 0.04, 0.06, wk.principled("stamp_wood", "a8743e", 0.5), n=16).parent = b
    return b

def shot_C():
    f0, f1 = SEG
    k_casino, k_doch, k_hoehle, k_zwei, k_wind, k_sonst = wt("casino"), wt("doch"), wt("höhle"), wt("zwei"), wt("pfeifender"), wt("sonst")
    k_stadt, k_baut, k_luft, k_ein = wt("stadt", line="cavern"), wt("baut"), wt("luft"), wt("ein", line="inspector")
    k_klopft, k_kurz, k_tech, k_sieht, k_aus, k_und, k_stempel, k_drauf = wt("klopft"), wt("kurz"), wt("technikraum"), wt("sieht"), wt("aus", line="inspector"), wt("und", line="inspector"), wt("stempel"), wt("drauf")
    wk.world_color("0a1226", 0.35)
    flat.STICK_COLOR = None; flat.LIGHT_POS = None
    mats.set_scene_light(tint=(0.86, 0.92, 1.05), rim_strength=0.0)
    grade(lift=(0.96, 0.98, 1.06), gain=(1.06, 1.0, 0.94), sat=1.2, contrast=0.14)
    # Kamera zuerst (Billboards brauchen das Ziel)
    keys = [
        (T_B1 - 0.05, (-16.6, 0.95 - 0.95, 32.05), (-10, 0.0, 31.6), 62),
        (T_B1 + 0.35, (-15.2, 0.0, 32.0), (-4, 1.0, 16.0), 64),
        (k_casino + 0.4, (-11.5, -3.5, 36), (0, 2, 16), 62),
        (k_hoehle, (-5.5, -11.5, 43), (2, 3, 8), 60),
        (k_zwei + 0.3, (-0.5, -11.0, 26), (2.4, 2, 7), 44),
        (k_wind + 0.2, (1.5, -5.0, 8.0), (wk.PIGEON["x"], wk.PIGEON["y"], 1.2), 44),
        (k_sonst + 0.25, (wk.PIGEON["x"] - 0.5, wk.PIGEON["y"] - 1.55, 0.62), (wk.PIGEON["x"] + 0.28, wk.PIGEON["y"], 0.2), 44),
        (k_stadt + 0.4, (1.0, -4.0, 8.0), (4.0, 4.0, 4.0), 58),
        (k_baut, (-5.0, -14.0, 45.0), (2.0, 2.0, 12.0), 66),
        (k_luft + 0.3, (-3.0, -11.0, 41.0), (1.8, 2.0, 3.0), 60),
        (k_ein + 0.1, (2.9, -2.2, 1.6), (2.3, 2.4, 1.2), 42, "stop"),
        (k_tech, (2.6, -1.6, 1.55), (2.3, 2.3, 1.2), 42),
        (k_stempel - 0.3, (2.25, -1.0, 1.45), (2.02, 2.1, 1.12), 42),
        (k_drauf + 0.45, (2.2, -0.85, 1.45), (2.0, 2.1, 1.12), 40, "stop"),
        (T_C1 - 0.3, (1.0, -9.5, 7.0), (1.6, 6.0, 4.0), 56),     # rueckwaerts raus, Blick bleibt auf den Rohren
        (T_C1 + 0.04, (1.2, -16.6, 9.9), (1.3, 6.0, 8.0), 56),
    ]
    def camf(t):
        k = path(t, keys)
        if k_stempel - 0.02 < t < k_stempel + 0.25:   # kleiner Ruck beim Stempelschlag
            a = (1 - (t - k_stempel) / 0.25) * 0.012; k["p"] = (k["p"][0], k["p"][1], k["p"][2] - a * math.sin(t * 90))
        return k
    cam = camera(camf, f0, f1, focus=lambda t: (2.0, 2.0, 1.2) if t > k_ein else path(t, keys)["l"], fstop=2.8 if False else None, clip=(0.02, 400))
    pig = wk.cavern(cam, f0, f1, light=0.3)
    t_toast0, t_toast1 = k_aus - 0.25, k_und + 0.7
    wk.key_vis(pig["tv"], f0, fr(t_toast0)); wk.key_vis(pig["toast"], fr(t_toast0), fr(t_toast1)); wk.key_vis(pig["tv"], fr(t_toast1)) if False else None
    tv2 = pig["remote"]; tv2.hide_render = True; tv2.keyframe_insert("hide_render", frame=1)
    pt = pig["tv"]; pt.hide_render = False; pt.keyframe_insert("hide_render", frame=fr(t_toast1))
    # Bauprüfer: links (kameraseitig) Stift -> Stempel, rechts durchgehend Klemmbrett
    pos = (1.95, 2.0); face_pipe = yaw_to(-1, 0); face_cam = yaw_to(2.7 - 1.95, -1.6 - 2.0)
    knocks = [k_klopft + 0.08, k_klopft + 0.36]
    k_rohr_end = k_klopft + 0.75; k_drueckt = wt("drückt")
    t_lift0, t_slam, t_rel = k_drueckt - 0.1, k_stempel, k_stempel + 0.3
    legs = {"legL": {"pitch": 9, "roll": 5}, "legR": {"pitch": -7, "roll": 5}}
    def insp(t):
        yw = lerp(face_pipe, face_cam, prog(t, k_rohr_end, k_tech))
        pose = {}; talk = 0.0; hp = 0; hy = 0
        clipR = (-0.3, 0.86, 0.12)
        if t < k_tech:
            knock = sum(max(0.0, 1 - abs(t - kn) / 0.09) for kn in knocks)
            reach = prog(t, k_klopft - 0.35, k_klopft) * (1 - prog(t, k_rohr_end - 0.2, k_rohr_end + 0.1))
            pose = {"handL": (lerp(0.26, 0.06, reach), lerp(0.8, 1.2, reach), lerp(0.06, 0.27 + 0.06 * knock, reach)), "handR": clipR}
        elif t < k_und:
            pose = merge(P["shrug"], {"headRoll": 6, "handR": (-0.36, 1.0, 0.24)}); talk = 1.0 if k_tech < t < k_aus + 0.2 else 0.0
            if t > k_aus - 0.05:   # nickt der Taube zu (nur Kopf)
                hy = 30 * prog(t, k_aus - 0.05, k_aus + 0.2); hp = 14 * max(0.0, 1 - abs(t - (k_aus + 0.35)) / 0.18)
        else:
            yw = face_cam; hy = 30 * (1 - prog(t, k_und, k_und + 0.35))
            up = prog(t, k_und, t_lift0 + 0.3); slam = prog(t, t_slam - 0.14, t_slam); rel = prog(t, t_rel, t_rel + 0.35)
            show = prog(t, t_rel, t_rel + 0.4)
            hl = mixv((0.1, 1.0, 0.32), (0.24, 1.42, 0.36), up)
            hl = mixv(hl, (-0.2, 1.06, 0.36), slam); hl = mixv(hl, (0.1, 1.0, 0.32), rel)
            pose = {"handL": hl, "handR": mixv((-0.24, 1.0, 0.3), (-0.2, 1.22, 0.36), show), "headPitch": 12 * (1 - show)}
        pose = merge(legs, pose, {"headPitch": pose.get("headPitch", 0) + hp, "headYaw": hy})
        return dict(rig=R(S["inspector"], pose, t, F(*pos), yw, talk=talk * 0.4), mood="bored", blink=blink(t, 3), mouth=(0.5 + 0.5 * math.sin(t * 22)) * talk * 0.6)
    ch = figure("inspector", "inspector", insp); ch.flat_bias = 0.25
    visible(ch, f0, False); visible(ch, fr(k_baut + 1.2), True)
    t_vis = k_baut + 1.2
    pen = wk.cyl("pen", (0, 0, 0), 0.007, 0.14, wk.principled("pen", "1c3a8a", 0.4), n=8)
    def penf(t):
        rg = insp(t)["rig"]; h = flat_pt(hand(rg, 0), rg, ch, t, camf, 0.02); vis = t_vis < t < k_tech
        d = Vector((-1, 0.1, -0.15)).normalized(); return (h + d * 0.05, Vector((0, 0, 1)).rotation_difference(d), vis)
    prop_follow(pen, f0, f1, penf, 1)
    clip, okparts = clipboard(); st = stamp()
    for o in okparts: o["own_vis"] = 1
    def clip_pose(t):
        rg = insp(t)["rig"]; h = flat_pt(hand(rg, 1), rg, ch, t, camf, 0.14); cp = Vector(camf(t)["p"]); d = (cp - h); d.z = 0; d.normalize()
        tilt = prog(t, k_und, t_lift0 + 0.3) * (1 - prog(t, t_rel, t_rel + 0.4))   # zum Stempeln flach, danach zur Kamera
        n = (d + Vector((0, 0, 0.25 + 1.6 * tilt))).normalized()
        loc = h + Vector((0, 0, 0.03))
        return loc, n
    def clipf(t):
        loc, n = clip_pose(t); q = Vector((0, 0, 1)).rotation_difference(n)
        return (loc, q, t > t_vis)
    prop_follow(clip, f0, f1, clipf, 1)
    def stampf(t):
        rg = insp(t)["rig"]; h = flat_pt(hand(rg, 0), rg, ch, t, camf, 0.16); vis = t > k_und - 0.05
        free = h - Vector((0, 0, 0.13))
        cl, n = clip_pose(t)
        contact = cl + n * 0.012
        k = prog(t, t_slam - 0.14, t_slam) * (1 - prog(t, t_rel, t_rel + 0.25))
        loc = free.lerp(contact, k)
        q = Vector((0, 0, 1)).rotation_difference(Vector((0, 0, 1)).lerp(n, k).normalized())
        return (loc, q, vis)
    prop_follow(st, f0, f1, stampf, 1)
    for o in okparts:
        o["own_vis"] = 1
        o.hide_render = True; o.keyframe_insert("hide_render", frame=f0); o.hide_render = False; o.keyframe_insert("hide_render", frame=fr(t_slam + 0.03))

# ================================================================= SHOT D: Skyline, Roentgen, Kisten-Hebebuehne
T_D1 = wt("die", line="penthouse") - 0.15
BLK_H, CR_H = 54.0, 9.0
def d_times():
    k_also, k_kisten, k_denn, k_heben, k_daecher = wt("also"), wt("kisten"), wt("denn"), wt("heben"), wt("dächer")
    t0 = k_also + 0.5
    return [t0 + i * 1.12 for i in range(6)]
def lift_n(t):
    return sum(prog(t, tk, tk + 0.62) for tk in d_times())

def shot_D():
    f0, f1 = SEG
    k_klingt, k_siehst, k_stadt, k_baue, k_starrst, k_nachbar, k_also, k_denn, k_daecher = wt("klingt"), wt("siehst"), wt("stadt", line="skyline"), wt("baue"), wt("starrst"), wt("nachbarwand"), wt("also"), wt("denn"), wt("dächer")
    TW = wk.TOWER["w"]; FH = wk.TOWER["fh"]
    ph.hdri("qwantani_dusk_2_puresky", 0.9, rot=1.2)
    wk.world_color  # (HDRI bleibt Lichtquelle)
    sets2._sky_gradient("27408f", "ff9a5a")
    world.sun((84, 0, -100), energy=3.2, color=(1.0, 0.62, 0.36))
    mats.set_scene_light(tint=(1.0, 0.86, 0.76), rim_strength=0.0)
    grade(lift=(0.97, 0.97, 1.04), gain=(1.08, 1.0, 0.9), sat=1.22, contrast=0.12)
    c = wk.coll("city")
    wk.ground_city(c); wk.park(c)
    wk.city(keep=lambda x, y: not (-130 < x < 60 and abs(y) < 60), near_max=50)
    # direkte Nachbarn (unter 70 m), Sued-Nachbar = graue Ziegelwand vor den Fenstern
    grey_brick = wk.pbr("rough_concrete", 0.1, (0.62, 0.64, 0.7), rough_mul=1.0, bump=1.0, name="grey_wall")
    wk.box("nb_S", (0, -32, 19), (44, 32, 38), grey_brick, c=c)   # Wandflaeche bei y = -16 (4 m Gasse)
    wk.box("plaza", (-70, -5, 0.05), (100, 110, 0.1), wk.pbr("concrete_floor_02", 0.08, (0.85, 0.8, 0.75), name="plaza"), c=c)
    for nm, cx, cy, sx, sy, h in (("nb_E", 34, 4, 20, 44, 46), ("nb_N", 2, 36, 40, 22, 48), ("nb_SE", 38, -36, 24, 26, 36), ("nb_NW", -38, 40, 24, 30, 42)):
        o = wk.box(nm, (cx, cy, h / 2), (sx, sy, h), wk.city_mat(), c=c)
        ca = o.data.color_attributes.new("tint", "BYTE_COLOR", "CORNER")
        for d_ in ca.data: d_.color = wk.lin(random.Random(cx).choice(["8a8d96", "9a8f84", "6f7686"]))
    # Turm (Phase 1): Sockel 1-29, Luecke 30-45 mit Lamellen + Kupferrohren, goldener Wohnblock 46-60
    tc = wk.coll("tower")
    pod = bpy.data.objects.new("podium", None); tc.objects.link(pod)
    z_void0, z_void1 = 29 * FH, 45 * FH
    for k in range(29):
        b = wk.box(f"pod{k}", (0, 0, k * FH + 1.8), (TW - 0.6, TW - 0.6, 3.2), wk.emit("pod_glow", "9fb8e8", 0.9), c=tc); b.parent = pod
        b = wk.box(f"podslab{k}", (0, 0, k * FH), (TW, TW, 0.4), wk.principled("pod_slab", "4a5466", 0.6, 0.3), c=tc); b.parent = pod
    void = bpy.data.objects.new("void", None); tc.objects.link(void)
    slat = wk.principled("louver", "2a3038", 0.5, 0.8)
    for k in range(int((z_void1 - z_void0) / 0.9)):
        for side in (-1, 1):
            b = wk.box(f"vlS{k}{side}", (0, side * TW / 2, z_void0 + 0.45 + k * 0.9), (TW, 0.3, 0.1), slat, c=tc); b.parent = void
            b = wk.box(f"vlE{k}{side}", (side * TW / 2, 0, z_void0 + 0.45 + k * 0.9), (0.3, TW, 0.1), slat, c=tc); b.parent = void
    for px_ in (-1.5, 1.5):
        b = wk.cyl(f"vpipe{px_}", (px_, 2, (z_void0 + z_void1) / 2), 0.35, z_void1 - z_void0, wk.copper(), c=tc); b.parent = void
    b = wk.box("void_dark", (0, 0, (z_void0 + z_void1) / 2), (TW - 1, TW - 1, z_void1 - z_void0), wk.principled("void_in", "0c1220", 0.9), c=tc); b.parent = void
    shell, salpha = wk.glass_shell("shell", TW, 60 * FH, c=tc)
    blk = wk.gold_block("blk", TW, BLK_H, c=tc)
    # Kisten (6 Ebenen x 3x3), steigen aus dem Boden
    crates = []
    for lv in range(6):
        for i in range(3):
            for j in range(3):
                faces = tuple(f_ for f_, cond in (("S", j == 0), ("E", i == 2), ("W", i == 0)) if cond)
                o = wk.crate(f"cr{lv}{i}{j}", (0, 0, 0), (7.9, 7.9, CR_H - 0.1), faces=faces, c=wk.coll("crates"))
                crates.append((lv, i, j, o))
    T = d_times()
    t_drop0, t_drop1 = k_stadt + 0.6, k_baue - 0.3
    for f in range(f0, f1 + 1):
        t = tf(f); n = lift_n(t)
        if t < t_drop0: bz = z_void1
        elif t < t_drop1: bz = z_void1 * (1 - prog(t, t_drop0, t_drop1))
        else: bz = CR_H * n
        blk.location = (0, 0, bz); blk.keyframe_insert("location", frame=f)
        sq = 1 - prog(t, t_drop0 - 0.5, t_drop0 + 0.3)
        pod.scale = (1, 1, max(0.001, sq)); pod.keyframe_insert("scale", frame=f)
        for grp in (void, pod):
            for oo in grp.children:
                oo.hide_render = sq < 0.02; oo.keyframe_insert("hide_render", frame=f)
        void.scale = (1, 1, max(0.001, sq)); void.location = (0, 0, z_void0 * (1 - sq)); void.keyframe_insert("scale", frame=f); void.keyframe_insert("location", frame=f)
        salpha.outputs[0].default_value = 0.85 * (1 - prog(t, k_siehst, t_drop0)); salpha.outputs[0].keyframe_insert("default_value", frame=f)
        for lv, i, j, o in crates:
            z = CR_H * (n - (lv + 1))
            o.location = ((i - 1) * 8, (j - 1) * 8, z + CR_H / 2); o.keyframe_insert("location", frame=f)
            vis = t > T[lv] - 0.05
            for oo in [o] + list(o.children_recursive): oo.hide_render = not vis; oo.keyframe_insert("hide_render", frame=f)
    # warmes Licht auf die Kisten
    wk.area("crate_key", (-60, -70, 40), (math.radians(70), 0, math.radians(-40)), 60000, 30, (1.0, 0.7, 0.42))
    # Du am Fenster (Wohnung unten, starrt auf die graue Wand)
    def blkz(t):
        if t < t_drop1: return -100.0
        return CR_H * lift_n(t)
    dpos = (-1.7, -12.45)
    def du(t):
        z = blkz(t) + FH + 0.25
        happy = t > T[3]
        pose = P["crossed"] if not happy else P["cheer"]
        return dict(rig=R(S["du"], pose, t, F(dpos[0], dpos[1], z), yaw_to(0, -1)), mood="angry" if not happy else "laugh", blink=blink(t, 2))
    ch = figure("du", "du_win", du); ch.flat_bias = 0.2
    visible(ch, f0, False); visible(ch, fr(t_drop1), True); visible(ch, fr(k_also), False)
    win = wk.box("win_in", (0, 0.2, 0), (2.3, 0.05, 2.8), wk.emit("win_room", "ffd9a0", 1.6), c=tc)
    fm = wk.principled("win_frame", "3a2a18", 0.5, 0.6)
    for nm, lc, sz in (("t", (0, 0, 1.45), (2.5, 0.16, 0.12)), ("b", (0, 0, -1.45), (2.5, 0.16, 0.12)), ("l", (-1.2, 0, 0), (0.12, 0.16, 2.9)), ("r", (1.2, 0, 0), (0.12, 0.16, 2.9))):
        b_ = wk.box("win_" + nm, lc, sz, fm, c=tc); b_.parent = win
    for f in range(f0, f1 + 1, 2):
        win.location = (dpos[0], -12.38, blkz(tf(f)) + FH + 1.45); win.keyframe_insert("location", frame=f)
    win.scale = (1, 1, 1)
    for oo in [win] + list(win.children):
        oo.hide_render = False; oo.keyframe_insert("hide_render", frame=f0); oo.hide_render = True; oo.keyframe_insert("hide_render", frame=fr(k_also))
    # Kamera
    zb_end = CR_H * 6
    keys = [
        (T_C1 - 0.05, (1.2, -12.2, 118.0), (1.3, 10.0, 116.4), 56),
        (T_C1 + 0.6, (-4.0, -32.0, 118.0), (0, 0, 114), 56),
        # ruhig rueckwaerts in die Totale (Abstand > 120 m, freie Zone westlich des Turms)
        (k_klingt + 1.3, (-40.0, -62.0, 110.0), (0, 0, 104), 52),
        (k_siehst + 0.2, (-110.0, -50.0, 92.0), (0, 0, 88), 52),
        # Wohnblock faellt: Kamera sinkt weit draussen mit
        (t_drop0, (-100.0, -40.0, 55.0), (0, -8, 35), 48),
        (t_drop1, (-40.0, -17.0, 14.0), (0, -13, 8), 40),
        # in der Gasse: Du am Fenster, dann Schwenk auf die graue Wand
        (k_starrst - 0.2, (-9.0, -15.3, 6.4), (dpos[0], -12.4, 5.4), 38),
        (k_nachbar - 0.2, (-8.0, -15.35, 6.3), (dpos[0], -12.4, 5.5), 38),
        (k_nachbar + 0.55, (-7.0, -15.4, 6.2), (6.0, -16.6, 7.5), 46),
        # zurueck und hoch: Kisten heben den Block
        (k_also + 0.35, (-30.0, -17.0, 10.0), (0, -8, 10), 40),
        (T[1], (-75.0, -38.0, 28.0), (0, 0, 24), 44),
        (T[3], (-92.0, -44.0, 48.0), (0, 0, 46), 52),
        (T[5] + 0.6, (-95.0, -45.0, 70.0), (0, 0, 62), 55),
        # Anflug aufs Penthouse-Fenster
        (k_daecher - 0.7, (-45.0, -38.0, 98.0), (-2, 0, 102), 52),
        (T_D1 - 0.5, (-12.0, -24.0, 106.0), (-2, 0, 106), 52),
        (T_D1 + 0.04, (-2.0, -12.9, 106.0), (-2.0, 0.0, 106.0), 52),
    ]
    camera(lambda t: path(t, keys), f0, f1, None, None, clip=(0.1, 4000))

# ================================================================= SHOT E: Penthouse -> durch den Glasboden zur Taube
def shot_E():
    f0, f1 = SEG; Z = wk.PH_Z
    k_oeffnet, k_vor, k_blick, k_ueber, k_getragen, k_nichts = wt("öffnet"), wt("vor", line="penthouse"), wt("fünfzig", line="penthouse"), wt("über", line="penthouse"), wt("getragen"), wt("nichts", line="penthouse")
    ph.hdri("qwantani_dusk_2_puresky", 0.9, rot=1.2)
    sets2._sky_gradient("27408f", "ff9a5a")
    world.sun((84, 0, -100), energy=3.2, color=(1.0, 0.62, 0.36))
    mats.set_scene_light(tint=(1.0, 0.88, 0.78), rim_strength=0.0)
    grade(lift=(0.97, 0.97, 1.03), gain=(1.08, 1.0, 0.9), sat=1.2, contrast=0.12)
    c = wk.coll("city"); wk.ground_city(c); wk.park(c)
    wk.city(keep=lambda x, y: not (-130 < x < 60 and abs(y) < 60), near_max=50)
    keys = [
        (T_D1 - 0.05, (-2.0, -0.95, Z + 1.6), (-1.0, 9.0, Z + 1.4), 52),
        (T_D1 + 0.4, (-1.6, 1.0, Z + 1.6), (0.0, 10.0, Z + 1.3), 52),
        (k_oeffnet + 0.5, (-0.9, 3.4, Z + 1.5), (0.0, 10.4, Z + 1.35), 44),
        (k_vor + 0.4, (-3.2, 1.4, Z + 1.5), (-0.8, 4.4, Z + 1.45), 46),
        (k_blick + 0.6, (-0.4, 5.4, Z + 1.75), (-2.4, -10.0, Z + 0.6), 50),
        (k_ueber + 0.9, (-1.7, 1.15, Z + 1.55), (-0.5, 3.2, Z + 1.45), 40),
        (k_getragen + 0.1, (-1.4, 1.3, Z + 1.55), (-0.5, 3.2, Z + 1.4), 40),
        (k_getragen + 0.75, (1.6, 1.9, Z + 0.9), (1.8, 2.6, Z - 5.0), 56),
        (k_getragen + 1.5, (1.2, 0.9, Z - 10.6), (1.9, 3.4, Z - 13.1), 46),
        (END_T + 0.05, (1.75, 0.55, Z - 12.45), (1.95, 3.4, Z - 13.75), 46),
    ]
    cam = camera(lambda t: path(t, keys), f0, f1, None, None, clip=(0.05, 4000))
    door = lambda f: prog(tf(f), k_oeffnet - 0.2, k_oeffnet + 0.5)
    wk.penthouse(door, NFR, cam)
    def du(t):
        p3, yw, wa = rig.walk_along(t, [(0.0, 0.0, -10.7), (k_oeffnet + 0.4, 0.0, -10.7), (k_vor + 0.9, -1.0, -3.2)])
        if t < k_oeffnet + 0.4 or t > k_vor + 0.9: yw = 0.0
        happy = t > k_blick
        pose = {"handL": (0.44, 1.18, 0.18), "handR": (-0.44, 1.18, 0.18)} if k_ueber < t < k_getragen + 0.6 else {}
        return dict(rig=R(S["du"], pose, t, (p3[0], Z, p3[2]), yw, walk=wa), mood="laugh" if happy else "puzzled", blink=blink(t, 1) and not happy)
    ch = figure("du", "du_ph", du); ch.flat_bias = 0.15

# ================================================================= Registry
SHOTS = {
    "A": (shot_A, 1, fr(T_A1)),
    "B": (shot_B, fr(T_A1) + 1, fr(T_B1)),
    "C": (shot_C, fr(T_B1) + 1, fr(T_C1)),
    "D": (shot_D, fr(T_C1) + 1, fr(T_D1)),
    "E": (shot_E, fr(T_D1) + 1, NFR),
}
RT = {"A": True, "E": True}; MB = {"B": True}
def nframes(): return NFR
