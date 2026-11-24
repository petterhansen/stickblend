"""Skelett/Posen der Stickman-Factory (Port von onoda/src/stick/Stickman.tsx + Poses.ts).

Figurenraum wie in three.js: x = linke Koerperseite (+), y = oben, z = vorne. Fuss bei y = 0.
Die Umrechnung nach Blender (z oben) passiert erst beim Zeichnen (draw.py: tb()).
"""
import math
from mathutils import Vector, Quaternion, Euler

D = math.pi / 180

# ---------------- Posen (Grad; Hand-Ziele im Figurenraum) ----------------
POSES = {
    "idle": {},
    "salute": {"handR": (-0.07, 1.55, 0.2), "headPitch": -3, "lean": -2},
    "point": {"armR": {"pitch": 80, "roll": 10, "bend": 5}, "headYaw": -10},
    "wave": {"handL": (0.32, 1.55, 0.12)},
    "handsUp": {"handL": (0.3, 1.8, 0.05), "handR": (-0.3, 1.8, 0.05), "headPitch": -8},
    "hips": {"handL": (0.26, 0.8, 0.02), "handR": (-0.26, 0.8, 0.02)},
    "think": {"handR": (-0.04, 1.25, 0.24), "handL": (0.12, 0.98, 0.2), "headRoll": 8, "headPitch": 6},
    "offer": {"handL": (0.1, 0.98, 0.42), "handR": (-0.1, 0.98, 0.42), "lean": 12, "headPitch": 10},
    "binoculars": {"handL": (0.06, 1.38, 0.28), "handR": (-0.06, 1.38, 0.28)},
    "read": {"handL": (0.09, 1.02, 0.32), "handR": (-0.09, 1.02, 0.32), "headPitch": 18},
    "stop": {"handR": (-0.12, 1.25, 0.45), "headPitch": -2},
    "crouch": {"crouch": 0.4, "lean": 18, "handL": (0.15, 0.55, 0.35), "handR": (-0.15, 0.55, 0.35), "headPitch": 8},
    "sneak": {"crouch": 0.16, "lean": 22, "armL": {"pitch": 30, "bend": 40}, "armR": {"pitch": 20, "bend": 50}},
    "shrug": {"handL": (0.36, 1.1, 0.2), "handR": (-0.36, 1.1, 0.2), "headRoll": 10},
    "sit": {"sit": 0.46, "lean": 8},
    "oil": {"crouch": 0.4, "lean": 18, "handL": (0.22, 0.6, 0.36), "handR": (-0.05, 0.62, 0.38), "headPitch": 16},
    "cheer": {"handL": (0.34, 1.72, 0.14), "handR": (-0.34, 1.72, 0.14), "lean": -5, "headPitch": -10},
    "facepalm": {"handR": (-0.06, 1.32, 0.30), "handL": (0.24, 0.72, 0.04), "headPitch": 14, "lean": 5},
    "crossed": {"handL": (-0.10, 0.96, 0.28), "handR": (0.10, 0.94, 0.26), "lean": -2},
    "kneel": {"crouch": 0.38, "lean": 10, "handL": (0.14, 0.66, 0.32), "handR": (-0.14, 0.66, 0.32), "headPitch": 10},
    "nervous": {"handL": (0.05, 0.90, 0.28), "handR": (-0.05, 0.90, 0.28), "lean": 8, "headPitch": 10},
    "clap": {"handL": (0.02, 1.02, 0.32), "handR": (-0.02, 1.02, 0.32), "headPitch": -3},
    "whisper": {"handR": (-0.08, 1.24, 0.30), "handL": (0.24, 0.74, 0.04), "lean": 10, "headYaw": 12},
    "bow": {"lean": 28, "headPitch": 14, "handL": (0.22, 0.62, 0.26), "handR": (-0.22, 0.62, 0.26)},
    "present": {"armL": {"pitch": 62, "roll": 28, "bend": 12}, "handR": (-0.24, 0.72, 0.06), "headYaw": 10, "lean": 4},
    "kick": {"legR": {"pitch": -70, "bend": 12}, "armL": {"pitch": 35, "bend": 25}, "lean": -10},
    "lean_back": {"lean": -12, "headPitch": -8, "handL": (0.26, 0.80, 0.02), "handR": (-0.26, 0.80, 0.02)},
}
REST = {"L": (0.24, 0.7, 0.04), "R": (-0.24, 0.7, 0.04)}

def _n(a, b, k): return (a or 0) + ((b or 0) - (a or 0)) * k
def _limb(a, b, k):
    a = a or {}; b = b or {}
    return {"pitch": _n(a.get("pitch"), b.get("pitch"), k), "roll": _n(a.get("roll", 6), b.get("roll", 6), k), "bend": _n(a.get("bend", 8), b.get("bend", 8), k)}
def _hand(a, b, rest, k):
    if a is None and b is None: return None
    a = a or rest; b = b or rest
    return tuple(_n(a[i], b[i], k) for i in range(3))

def mix_pose(a, b, k):
    kk = max(0.0, min(1.0, k)); e = 4 * kk ** 3 if kk < 0.5 else 1 - (-2 * kk + 2) ** 3 / 2
    out = {key: _n(a.get(key), b.get(key), e) for key in ("lean", "twist", "side", "crouch", "headYaw", "headPitch", "headRoll")}
    for l in ("armL", "armR", "legL", "legR"): out[l] = _limb(a.get(l), b.get(l), e)
    out["handL"] = _hand(a.get("handL"), b.get("handL"), REST["L"], e)
    out["handR"] = _hand(a.get("handR"), b.get("handR"), REST["R"], e)
    return out

def poses_at(t, seq, blend=0.3):
    """seq = [(t0, "idle"), (t1, "salute"), ...] -> weich ueberblendete Pose."""
    i = 0
    while i < len(seq) - 1 and t >= seq[i + 1][0]: i += 1
    cur = POSES[seq[i][1]]; prev = POSES[seq[i - 1][1]] if i > 0 else cur
    return mix_pose(prev, cur, (t - seq[i][0]) / blend)

# ---------------- Geometrie ----------------
def limb_dir(pitch, roll, side):
    sx = math.sin(roll * D) * side; sy = -math.cos(roll * D)
    return Vector((sx, sy * math.cos(pitch * D), -sy * math.sin(pitch * D))).normalized()

def ik2(s, t, a, b, pole):
    d = t - s; ln = min(d.length, (a + b) * 0.999); dr = d.normalized()
    x = (a * a - b * b + ln * ln) / (2 * ln); h = math.sqrt(max(0.0, a * a - x * x))
    pv = (pole - dr * pole.dot(dr)).normalized()
    return s + dr * x + pv * h, s + dr * ln

def proportions(spec):
    H = spec.get("height", 1.75); P = spec.get("prop", {})
    return dict(H=H, legLen=H * P.get("leg", 0.40), armLen=H * P.get("arm", 0.34), torsoH=H * P.get("torso", 0.30),
                headR=H * P.get("head", 0.145), shW=spec.get("shoulderW", 0.17), hipW=0.075)

def stick_rig(spec, pose=None, t=0.0, walk=0.0, talk=0.0, phase=0.0, run=0.0):
    """Gelenke im Figurenraum. Rueckgabe: dict mit legs/arms (je [L, R]), hipC, tq, neck, hq, mouth."""
    P = dict(pose or {}); pr = proportions(spec)
    legLen, armLen, torsoH, headR, shW, hipW = pr["legLen"], pr["armLen"], pr["torsoH"], pr["headR"], pr["shW"], pr["hipW"]
    stride = max(walk, run)
    freq = 13.5 if run > 0.2 else 8.5
    ph = t * freq + phase; w = stride
    legL = dict(P.get("legL") or {}); legR = dict(P.get("legR") or {})
    armL = {"pitch": 0, "roll": 6, "bend": 8, **(P.get("armL") or {})}; armR = {"pitch": 0, "roll": 6, "bend": 8, **(P.get("armR") or {})}
    bob = 0.0
    if w:
        amp_l = (30 + 22 * run) * w; amp_b = (45 + 35 * run) * w; amp_a = (28 + 26 * run) * w
        legL["pitch"] = legL.get("pitch", 0) + math.sin(ph) * amp_l; legL["bend"] = legL.get("bend", 0) + max(0, -math.cos(ph)) * amp_b
        legR["pitch"] = legR.get("pitch", 0) + math.sin(ph + math.pi) * amp_l; legR["bend"] = legR.get("bend", 0) + max(0, -math.cos(ph + math.pi)) * amp_b
        if not P.get("handL"): armL["pitch"] = armL.get("pitch", 0) - math.sin(ph) * amp_a; armL["bend"] = armL.get("bend", 8) + 35 * run
        if not P.get("handR"): armR["pitch"] = armR.get("pitch", 0) - math.sin(ph + math.pi) * amp_a; armR["bend"] = armR.get("bend", 8) + 35 * run
        bob = abs(math.cos(ph)) * (0.035 + 0.035 * run) * w
    # Organic talking hand gesticulation when hands are not locked to an IK target
    if talk and not w:
        if not P.get("handL") and not P.get("armL"):
            armL["pitch"] += (14 + 10 * math.sin(t * 7.2 + phase)) * talk; armL["bend"] += 26 * talk
        if not P.get("handR") and not P.get("armR"):
            armR["pitch"] += (14 + 10 * math.cos(t * 6.5 + phase)) * talk; armR["bend"] += 26 * talk
    crouch = P.get("crouch") or 0.0; sit = P.get("sit")   # sit = Sitzhoehe in m (Huefte auf Sitz, Fuesse vorne am Boden)
    hipY = sit if sit else legLen + bob - crouch
    def leg(side, l):
        hip = Vector((side * hipW, hipY, 0))
        if sit:
            k, a = ik2(hip, Vector((side * (hipW + 0.03), 0.06, P.get("feet", 0.4))), legLen / 2, legLen / 2, Vector((side * 0.15, 0.3, 1)))
            return {"hip": hip, "knee": k, "ankle": a}
        if crouch > 0 and not w:
            k, a = ik2(hip, Vector((side * (hipW + 0.04), 0.06, 0.05 + crouch * 0.3)), legLen / 2, legLen / 2, Vector((side * 0.3, 0.2, 1)))
            return {"hip": hip, "knee": k, "ankle": a}
        th = limb_dir(l.get("pitch", 0), l.get("roll", 2), side); knee = hip + th * (legLen / 2)
        sh = limb_dir(l.get("pitch", 0) - l.get("bend", 0), l.get("roll", 2), side)
        return {"hip": hip, "knee": knee, "ankle": knee + sh * (legLen / 2)}
    LL, LR = leg(1, legL), leg(-1, legR)
    run_lean = 14 * run
    tq = Euler(((P.get("lean") or 0) * D + run_lean * D + math.sin(t * 1.1 + phase) * 0.012, (P.get("twist") or 0) * D, (P.get("side") or 0) * D + (math.sin(ph) * 0.04 * w if w else 0)), "ZYX").to_quaternion()  # three "XYZ" = Rx*Ry*Rz
    hipC = Vector((0, hipY, 0)); T = lambda p: tq @ Vector(p) + hipC
    shL, shR = T((shW, torsoH * 0.86, 0)), T((-shW, torsoH * 0.86, 0))
    neck = T((0, torsoH + headR * 0.82, 0))
    def arm(side, sh, l, target):
        if target:
            # Elbow pole points outward and forward-down so arms never fold backward through head/torso
            pole = Vector((side * 0.9, -0.55, 0.35))
            e, h = ik2(sh, Vector(target), armLen / 2, armLen / 2, pole); return {"sh": sh, "e": e, "h": h}
        ua = tq @ limb_dir(l.get("pitch", 0), l.get("roll", 0), side); e = sh + ua * (armLen / 2)
        fa = tq @ limb_dir(l.get("pitch", 0) + l.get("bend", 0), l.get("roll", 0) * 0.6, side)
        return {"sh": sh, "e": e, "h": e + fa * (armLen / 2)}
    AL, AR = arm(1, shL, armL, P.get("handL")), arm(-1, shR, armR, P.get("handR"))
    hp = ((P.get("headPitch") or 0) + math.sin(t * 1.7 + phase) * 1.5 + (math.sin(t * 7) * 2 if talk else 0)) * D
    hy = ((P.get("headYaw") or 0) + math.sin(t * 0.9 + phase) * 2) * D; hr = (P.get("headRoll") or 0) * D
    hq = tq @ Euler((hp, hy, hr), "ZXY").to_quaternion()  # three "YXZ" = Ry*Rx*Rz
    mouth = 0.3 + 0.7 * abs(math.sin(t * 13)) * talk if talk else 0.0
    return dict(pr=pr, legs=[LL, LR], arms=[AL, AR], hipC=hipC, tq=tq, neck=neck, hq=hq, mouth=mouth)

def to_world(rig, pos=(0, 0, 0), yaw=0.0):
    """Figurenraum -> Weltraum (three-Achsen: y oben). Gibt eine neue Rig-Struktur zurueck."""
    yq = Quaternion((0, 1, 0), yaw); p0 = Vector(pos)
    W = lambda v: yq @ v + p0
    out = dict(rig); out["yq"] = yq
    out["legs"] = [{k: W(v) for k, v in l.items()} for l in rig["legs"]]
    out["arms"] = [{k: W(v) for k, v in a.items()} for a in rig["arms"]]
    out["hipC"] = W(rig["hipC"]); out["neck"] = W(rig["neck"]); out["tq"] = yq @ rig["tq"]; out["hq"] = yq @ rig["hq"]
    return out

def blink_at(t, seed=0):
    """Natural irregular human-like blink timing (with occasional double-blinks)."""
    u = t + seed * 1.73
    cyc = u % 3.4
    if cyc < 0.11:
        return True
    if (u % 11.3) > 10.75 and (u % 0.38) < 0.10:
        return True
    return False

def walk_along(t, waypoints):
    """Smoothly interpolate (pos3, yaw, walk_amount) along waypoints=[(t0, x0, z0), (t1, x1, z1), ...]."""
    if len(waypoints) == 1 or t <= waypoints[0][0]:
        _, x, z = waypoints[0]
        yaw = math.atan2(waypoints[1][1] - x, waypoints[1][2] - z) if len(waypoints) > 1 else 0.0
        return (x, 0.0, z), yaw, 0.0
    for (t0, x0, z0), (t1, x1, z1) in zip(waypoints, waypoints[1:]):
        if t <= t1:
            k = max(0.0, min(1.0, (t - t0) / max(1e-4, t1 - t0)))
            e = k * k * (3 - 2 * k)
            x, z = x0 + (x1 - x0) * e, z0 + (z1 - z0) * e
            dx, dz = x1 - x0, z1 - z0
            moving = math.hypot(dx, dz) > 0.05
            yaw = math.atan2(dx, dz) if moving else 0.0
            fade = min(1.0, min(k, 1.0 - k) * 6.0) if moving else 0.0
            return (x, 0.0, z), yaw, fade
    _, x, z = waypoints[-1]
    px, pz = waypoints[-2][1], waypoints[-2][2]
    yaw = math.atan2(x - px, z - pz) if math.hypot(x - px, z - pz) > 0.05 else 0.0
    return (x, 0.0, z), yaw, 0.0
