"""Aufzug-Short: ein Kameraflug ueber globale Frames (1 = 0.0 s). Sets: A (Fall + Roentgen), C (Seile, Regler, Keile), H (1945), L (Loop-Lobby).
Alle Sets bauen dieselbe Kabine/denselben Schacht; die Zeitfunktionen sind global."""
import bpy, json, math, os, re, sys, random
from mathutils import Vector, Quaternion
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "wolkenkratzer", "blender"))   # wk.py: Kabine, Lobby, Materialien
from stickblend import rig, character, specs, mats, sets2, flat
from stickblend.geo import tb
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wk, az

FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "src", "timeline.de.json"), encoding="utf8"))
WORDS = [dict(w=w["w"], s=w["s"], e=w["e"], line=l["id"]) for l in TL["lines"] for w in l["words"]]
END_T = WORDS[-1]["e"] + 0.22
NFR = round(END_T * FPS)
S = specs.SPECS; P = rig.POSES

def norm(s): return re.sub(r"[^\wäöüß0-9]", "", s.lower())
def wt(needle, nth=0, line=None, end=False):
    m = [w for w in WORDS if norm(w["w"]).startswith(norm(needle)) and (line is None or w["line"] == line)]
    return (m[nth]["e"] if end else m[nth]["s"]) if len(m) > nth else 0.0
def fr(t): return int(round(t * FPS)) + 1
def tf(f): return (f - 1) / FPS
def ease(k): return 4 * k ** 3 if k < 0.5 else 1 - (-2 * k + 2) ** 3 / 2
def ss(k): k = clamp(k, 0, 1); return k * k * (3 - 2 * k)
def clamp(x, a, b): return max(a, min(b, x))
def prog(t, a, b): return ease(clamp((t - a) / (b - a), 0, 1)) if b != a else float(t >= b)
def lin_(t, a, b): return clamp((t - a) / (b - a), 0, 1) if b != a else float(t >= b)
def lerp(a, b, k): return a + (b - a) * k
def mixv(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(len(a)))
def merge(*ps):
    out = {}
    for p in ps: out.update(p or {})
    return out
def F(x, y, z=0.0): return (x, z, -y)
def B(p3): return Vector(tb(p3))
def yaw_to(dx, dy): return math.atan2(dx, -dy)

# ---------------------------------------------------------------- Zeitmarken (an Woerter gebunden)
G = 9.81
T_FZ = wt("aber") - 0.05                    # Freeze
T_RW0 = wt("passiert") - 0.5                # Rueckspulen
T_RW1 = wt("über") - 0.12                   # Realitaet: Kabine haengt
T_X = wt("kurz") - 0.25                     # Roentgen an
K_REISS = wt("reißen")
T_DROP0 = K_REISS + 0.2
T_TRIP = wt("fliehkraftregler") + 0.65                 # Regler loest aus
T_WEDGE = wt("rammt") + 0.1
T_STOP = wt("schienen") + 0.3
T_H = wt("nur", line="history") - 0.12                      # Nebel -> 1945
K_RAST, K_BLD = wt("rast"), wt("building")
T_IMP = K_BLD + 0.05
K_STURZ = wt("stürzt")
T_LAND = wt("überlebt") + 0.05
T_L = wt("also", line="loop") - 0.22          # Loop: Lobby, Du steigt ein
T_PRESS = wt("drückst") + 0.25
ZP = az.PIT + 0.9 + 0.23                    # Kabinenboden auf den Puffern
Z_FZ = 0.4                                  # Kabinenboden beim Freeze (kurz vor der Grube)
TAU_END = math.sqrt(2 * (az.Z80 - Z_FZ) / G)

def tau(t): return TAU_END * clamp(t, 0, T_FZ) / T_FZ       # Erzaehlzeit im freien Fall (Zeitlupe ~2.4x)

def cz(t):
    """Kabinenboden-Hoehe (global)."""
    if t < T_FZ: return az.Z80 - 0.5 * G * tau(t) ** 2
    if t < T_RW0: return Z_FZ
    if t < T_RW1: return lerp(Z_FZ, az.Z80, prog(t, T_RW0, T_RW1))
    if t < T_H: return az.Z80 - 1.0 * ss(lin_(t, T_DROP0, T_STOP))
    if t < T_L:
        u = lin_(t, K_STURZ, T_LAND); return lerp(az.Z80, ZP, ss(u ** 1.6))
    return 0.0

def floor_no(z): return int(clamp(round(z / az.FH) + 1, 1, 80))

# ---------------------------------------------------------------- Kamera
def camera(fn, f0, f1, clip=(0.02, 2000)):
    cd = bpy.data.cameras.new("cam"); c = bpy.data.objects.new("cam", cd); bpy.context.scene.collection.objects.link(c); bpy.context.scene.camera = c
    cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24; cd.clip_start, cd.clip_end = clip; c.rotation_mode = "QUATERNION"
    prev = None
    for f in range(f0, f1 + 1):
        t = tf(f); k = fn(t); p, l = Vector(k["p"]), Vector(k["l"])
        c.location = p; q = (l - p).to_track_quat("-Z", "Y")
        if k.get("roll"): q = q @ Quaternion((0, 0, 1), k["roll"])
        if prev is not None and prev.dot(q) < 0: q.negate()
        prev = q.copy(); c.rotation_quaternion = q; cd.lens = 12 / math.tan(math.radians(k["fov"]) / 2)
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
    return c

def path(t, keys):
    """Hermite durch Keys [(t, p, l, fov[, 'stop'])]. p/l relativ zur Kabine, wenn rel=True im Key-Satz."""
    if t <= keys[0][0]: k = keys[0]; return dict(p=k[1], l=k[2], fov=k[3])
    if t >= keys[-1][0]: k = keys[-1]; return dict(p=k[1], l=k[2], fov=k[3])
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    a, b = keys[i], keys[i + 1]; h = b[0] - a[0]; u = (t - a[0]) / h
    def tan(j, idx):
        if len(keys[j]) > 4 and keys[j][4] == "stop": return (0.0, 0.0, 0.0)
        k0 = keys[max(0, j - 1)]; k1 = keys[min(len(keys) - 1, j + 1)]
        if k1[0] == k0[0]: return (0.0, 0.0, 0.0)
        return tuple((k1[idx][c] - k0[idx][c]) / (k1[0] - k0[0]) for c in range(3))
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    out = {}
    for idx, nm in ((1, "p"), (2, "l")):
        ma, mb = tan(i, idx), tan(i + 1, idx)
        out[nm] = tuple(h00 * a[idx][c] + h10 * h * ma[c] + h01 * b[idx][c] + h11 * h * mb[c] for c in range(3))
    out["fov"] = a[3] + (b[3] - a[3]) * (3 * u * u - 2 * u ** 3)
    return out

def rel(k, z):   # Kabinen-relative Kamera -> Welt
    return dict(p=(k["p"][0], k["p"][1], k["p"][2] + z), l=(k["l"][0], k["l"][1], k["l"][2] + z), fov=k["fov"])

def shake(t, amp):
    return Vector((math.sin(t * 37.1) * 0.6 + math.sin(t * 23.7 + 1), math.sin(t * 29.3 + 2) * 0.7, math.sin(t * 41.9 + 3) * 0.8 + math.sin(t * 17.3))) * amp

CAM_IN = ((-0.68, 7.88, 2.15), (0.2, 6.2, 1.5), 76)     # Loop-Bild (Anfang = Ende)
SIDE = lambda y=6.87: ((-5.6, y, 1.35), (0.0, y, 1.15), 50)

def cam_A():
    k_float, k_kaffee, k_kurz, k_schweb, k_sprung, k_265, k_flach = wt("dein"), wt("kaffee"), wt("kurz"), wt("schwebst"), wt("sprung"), wt("zweihundertfünfundsechzig"), wt("flach")
    sd = SIDE()
    keys = [
        (0.0, *CAM_IN),
        (k_float - 0.2, (-0.66, 7.88, 2.12), (0.05, 6.4, 1.45), 72),
        (k_kaffee + 0.4, (-0.64, 7.88, 2.1), (0.25, 6.4, 1.4), 70),
        (k_kurz - 0.5, (-0.64, 7.88, 2.05), (0.05, 6.5, 1.35), 74),
        (T_X + 2.1, sd[0], sd[1], sd[2]),
        (k_schweb + 0.5, (-4.2, 6.75, 1.45), (0.0, 6.62, 1.2), 40),
        (k_sprung - 0.2, (-4.6, 6.8, 1.3), (0.0, 6.66, 1.25), 44),
        (k_265 + 0.4, (-4.9, 6.85, 1.3), (0.0, 6.7, 1.2), 46),
        (k_flach + 0.6, (-5.6, 6.95, 1.1), (0.0, 7.0, 0.95), 50),
        (T_FZ - 0.1, (-6.2, 7.0, 0.6), (0.0, 7.0, 0.1), 54, "stop"),
    ]
    def fn(t):
        k = rel(path(t, keys), cz(t))
        if t < T_FZ:   # Erschuetterung im Fall (innen staerker)
            a = 0.012 * (1 - 0.6 * prog(t, T_X, T_X + 2)) + 0.004 * prog(t, 0, T_FZ)
            p = Vector(k["p"]) + shake(t, a); k["p"] = tuple(p)
        return k
    return fn

def cam_C():
    k_ueber, k_jedes, k_merkt, k_du, k_meter = wt("über"), wt("jedes"), wt("merkt"), wt("du", line="twist"), wt("meter")
    sd = SIDE()
    gx, gy, gz = az.GOV
    keys_rel = [
        (T_FZ, (-6.2, 7.0, 0.6), (0.0, 7.0, 0.1), 54),
        (T_RW0, (-6.2, 7.0, 0.6), (0.0, 7.0, 0.1), 54),
        (T_RW1, sd[0], sd[1], sd[2]),
        (k_jedes, (-4.6, 6.4, 3.4), (0.0, 7.0, 6.2), 52),
        (K_REISS - 0.1, (-4.3, 6.5, 4.6), (-0.2, 7.0, 7.0), 54),
    ]
    def fn(t):
        if t < K_REISS + 0.3: return rel(path(t, keys_rel), cz(t))
        # absolute Keys ab dem Reissen (Kabine bewegt sich nur noch 1 m)
        z0 = az.Z80
        keys = [
            (K_REISS - 0.1, (-4.3, 6.5, z0 + 4.6), (-0.2, 7.0, z0 + 7.0), 54),
            (K_REISS + 0.3, (-4.3, 6.5, z0 + 4.6), (-0.2, 7.0, z0 + 7.0), 54),
            (k_merkt + 0.25, (gx - 2.6, gy - 0.9, gz + 0.35), (gx, gy - 0.1, gz - 0.05), 40),
            (T_TRIP + 0.2, (gx - 2.2, gy - 0.8, gz + 0.25), (gx, gy - 0.1, gz - 0.05), 38, "stop"),
            (T_WEDGE + 0.35, (-3.1, 6.15, z0 - 0.45), (-1.36, 7.0, z0 - 1.05), 46, "stop"),
            (T_STOP + 0.2, (-2.9, 6.2, z0 - 0.5), (-1.36, 7.0, z0 - 1.12), 44, "stop"),
            (k_meter + 0.1, (-6.0, 6.9, z0 + 0.4), (0.0, 7.0, z0 - 0.1), 50),
            (T_H - 0.55, (-7.0, 6.9, z0 + 0.5), (0.0, 7.0, z0 - 0.1), 50),
            (T_H, (-40.0, 2.0, z0 + 1.6), (0.0, 7.0, z0 + 0.6), 44),
        ]
        return path(t, keys)
    return fn

PLANE_P1 = Vector((-6.0, -7.4, az.fz(79) + 1.5)); PLANE_P0 = Vector((-66.0, -74.0, az.fz(79) + 12.0)); PLANE_D = (PLANE_P1 - PLANE_P0).normalized()
def cam_H():
    k_die = wt("die", line="history"); k_luft = wt("luft")
    def fn(t):
        z = cz(t)
        far = [(T_H, (-40.0, 2.0, az.Z80 + 1.6), (0.0, 7.0, az.Z80 + 0.6), 44),
               (K_RAST - 0.1, (-118, -106, 286.0), (-6.0, 0.0, 279.0), 38),
               (T_IMP + 0.3, (-121, -109, 284.5), (-6.0, -2.0, 281.0), 38),
               (k_die - 0.1, (-108, -86, 285.5), (-5.0, 2.0, 283.0), 32),
               (K_STURZ - 0.15, (-42.0, 7.0, az.Z80 + 1.35), (0.0, 7.0, az.Z80 + 1.25), 11, "stop")]
        if t < K_STURZ - 0.15: return path(t, far)
        if t < T_LAND + 0.1:
            return dict(p=(-42.0, 7.0, z + 1.35 + 0.6 * math.sin(math.pi * lin_(t, K_STURZ, T_LAND))), l=(0.0, 7.0, z + 1.25), fov=11 + 2 * prog(t, K_STURZ, T_LAND))
        keys = [(T_LAND + 0.1, (-42.0, 7.0, ZP + 1.35), (0.0, 7.0, ZP + 1.25), 13),
                (T_LAND + 0.5, (-40.0, 7.0, ZP + 1.6), (0.0, 7.0, ZP + 0.8), 13),
                (k_luft, (-9.0, 6.65, 0.6), (0.0, 6.8, -0.35), 34),
                (T_L - 0.15, (-6.8, 6.6, 0.45), (0.0, 6.8, -0.4), 42)]
        return path(t, keys)
    return fn

def cam_L():
    def fn(t): return dict(p=CAM_IN[0], l=CAM_IN[1], fov=CAM_IN[2])
    return fn

def cam_all(t):
    if t < T_FZ: return CAMA(t)
    if t < T_H: return CAMC(t)
    if t < T_L: return CAMH(t)
    return CAML(t)
CAMA, CAMC, CAMH, CAML = cam_A(), cam_C(), cam_H(), cam_L()

# ---------------------------------------------------------------- Figuren
CHARS = []; STEP = [2]; SEG = [1, 1]
def R(spec, pose, t, pos3, yaw=0.0, walk=0.0, talk=0.0, phase=0.0):
    return rig.to_world(rig.stick_rig(spec, pose, t, walk=walk, talk=talk, phase=phase), pos3, yaw)
def figure(key, name, fn, step=2):
    f0, f1 = SEG; t0 = tf(f0)
    ch = character.build(S[key], name); character.animate(ch, lambda t: fn(t + t0), f1 - f0 + 1, step, start=f0)
    CHARS.append(ch); STEP[0] = min(STEP[0], step); return ch
def hand(rg, side): return B(tuple(rg["arms"][side]["h"]))
def blink(t, seed=0): return rig.blink_at(t, seed)

def flat_pt(p, rg, ch, t, camf, extra=0.0):
    a = B(tuple(rg["hipC"])); cp = Vector(camf(t)["p"]); n = (cp - a).normalized()
    q = p - n * n.dot(p - a)
    b = (getattr(ch, "flat_bias", 0.0) or 0.0) + extra; d = (cp - a).length
    return cp + (q - cp) * max(0.05, (d - b) / d) if b else q

def prop_follow(o, f0, f1, fn, step=1):
    o.rotation_mode = "QUATERNION"
    for f in range(f0, f1 + 1, step):
        loc, rot, vis = fn(tf(f)); o.location = loc
        if rot is not None: o.rotation_quaternion = rot if isinstance(rot, Quaternion) else rot.to_quaternion()
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f)
        for oo in [o] + list(o.children_recursive):
            oo.hide_render = not vis; oo.keyframe_insert("hide_render", frame=f)

FLOAT = {"legL": {"pitch": 28, "bend": 55, "roll": 6}, "legR": {"pitch": 8, "bend": 38, "roll": 4}}
LYING = {"lean": -84, "legL": {"pitch": 84, "bend": 6}, "legR": {"pitch": 80, "bend": 12}, "headPitch": -6}

def du_state(t):
    """Du in der Kabine: (x, y, Hoehe ueber Kabinenboden, yaw, pose, mood)."""
    k_kaffee, k_schweb, k_abst, k_sprung, k_265, k_flach = wt("kaffee"), wt("schwebst"), wt("abstoßen"), wt("sprung"), wt("zweihundertfünfundsechzig"), wt("flach")
    yw = lerp(yaw_to(0, 1), yaw_to(-1, 0), prog(t, T_X - 0.1, T_X + 1.6))
    fl = 0.08 + 0.12 * prog(t, 0.0, 4.5) + 0.03 * math.sin(t * 2.3)
    wob = math.sin(t * 3.1)
    pose = merge(FLOAT, {"handL": (0.36 + 0.05 * wob, 1.42 + 0.08 * math.sin(t * 2.6), 0.12), "handR": (-0.4, 1.3 + 0.08 * wob, 0.16), "headPitch": -6})
    mood = "shock" if t < 2.2 else "scared"
    if k_schweb - 0.3 < t < k_abst + 0.7:   # strampelt ins Leere
        kk = math.sin((t - k_schweb) * 11)
        pose = merge(pose, {"legL": {"pitch": 20 + 25 * kk, "bend": 40 + 25 * kk}, "legR": {"pitch": 20 - 25 * kk, "bend": 40 - 25 * kk},
                            "handL": (0.3, 1.0 + 0.2 * kk, 0.3), "handR": (-0.3, 1.0 - 0.2 * kk, 0.3), "headPitch": 14})
        mood = "worry"
    j0, j1 = k_sprung - 0.45, k_sprung + 0.35
    if j0 < t < k_265 + 0.3:   # Sprungversuch: zusammenkauern, strecken
        c_ = prog(t, j0, j0 + 0.3) * (1 - prog(t, j1 - 0.12, j1))
        pose = merge(pose, {"legL": {"pitch": lerp(10, 45, c_), "bend": lerp(4, 95, c_)}, "legR": {"pitch": lerp(6, 40, c_), "bend": lerp(4, 90, c_)},
                            "handL": (0.34, lerp(1.72, 1.1, c_), 0.06), "handR": (-0.34, lerp(1.72, 1.1, c_), 0.06), "headPitch": lerp(-12, 8, c_)})
        fl += 0.14 * prog(t, j1 - 0.12, j1 + 0.4); mood = "determined" if t < j1 else "shock"
    lie = prog(t, k_flach - 0.3, k_flach + 0.7)
    if lie > 0 and t < T_RW0 + 0.1:
        pose = rig.mix_pose(pose, merge(LYING, {"handL": (0.42, 1.05, -0.05), "handR": (-0.42, 1.05, -0.05)}), lie)
        fl = lerp(fl, -0.12, lie); mood = "scared"
        yw = lerp(yw, yaw_to(0, 1), lie)
    # Realitaet nach dem Rueckspulen: steht ruhig, Becher in der Hand
    rv = prog(t, T_RW0, T_RW1)
    if rv > 0:
        stand = merge(P["idle"], {"handL": (0.16, 0.98, 0.24), "headPitch": 0})
        if t > T_RW1:
            k_ueber = wt("über"); k_reiss = K_REISS
            up_ = prog(t, k_ueber, k_ueber + 0.6) * (1 - prog(t, k_reiss + 0.2, k_reiss + 0.6))
            stand = merge(stand, {"headPitch": -24 * up_})
        pose = rig.mix_pose(pose, stand, rv); fl = lerp(fl, 0.0, rv); yw = lerp(yw, yaw_to(-1, 0), rv)
        mood = "puzzled" if t < K_REISS else "neutral"
    if t > K_REISS:
        drop = prog(t, T_DROP0, T_DROP0 + 0.4) * (1 - prog(t, T_STOP - 0.1, T_STOP + 0.1))
        fl = 0.06 * drop
        bump = prog(t, T_STOP, T_STOP + 0.12) * (1 - prog(t, T_STOP + 0.15, T_STOP + 0.6))
        pose = merge(pose, {"crouch": 0.12 * bump, "handR": (-0.36, 1.2 + 0.2 * drop, 0.15)})
        mood = "shock" if t < T_STOP + 0.4 else ("happy" if t > wt("einen") - 0.1 else "worry")
    yy = lerp(az.DU_Y, 7.15, lie if t < T_RW0 + 0.1 else lie * (1 - prog(t, T_RW0, T_RW1)))
    return 0.05, yy, fl, yw, pose, mood

def du_lobby(t):
    """Loop-Ende: Du steigt mit Kaffee ein, drueckt 80, dreht sich zur Kamera (= Anfangsbild)."""
    t_in = wt("steigst") + 0.35; px, py = 0.4, 6.45
    p3, yw, wa = rig.walk_along(t, [(T_L, 0.1, -4.4), (t_in, px, -py)])
    if t > t_in - 0.3: yw = lerp(yw, yaw_to(1, 0), prog(t, t_in - 0.3, t_in + 0.15)); wa = min(wa, 0.4)
    turn = prog(t, T_PRESS + 0.25, T_PRESS + 0.6)
    if turn > 0: yw = lerp(yaw_to(1, 0), yaw_to(-1.08, 1.43), turn)
    press = prog(t, T_PRESS - 0.3, T_PRESS) * (1 - prog(t, T_PRESS + 0.2, T_PRESS + 0.45))
    by, bz = az.btn_pos("80")
    fx = az.PANEL["x"] - 0.03 - px; lx = by - py - 0.06; bz += 0.09
    pose = merge(P["idle"], {"handL": (0.16, 0.98, 0.24)})
    if press > 0: pose = merge(pose, {"handR": (lerp(-0.22, lx, press), lerp(0.75, bz, press), lerp(0.05, fx, press)), "headPitch": -6 * press})
    return p3, yw, wa, pose, "happy" if t > T_PRESS else "neutral"

def betty_state(t):
    """Betty im 1945-Set (H)."""
    yw = yaw_to(-1, 0); fl = 0.0; pose = merge(P["idle"], {"handR": (-0.2, 1.0, 0.28), "handL": (0.2, 1.0, 0.28)}); mood = "worry"
    if t > K_STURZ - 0.1:
        u = prog(t, K_STURZ - 0.1, K_STURZ + 0.6)
        pose = rig.mix_pose(pose, merge(FLOAT, {"handL": (0.38, 1.6, 0.05), "handR": (-0.38, 1.6, 0.05), "headPitch": -10}), u); fl = 0.35 * u; mood = "scared"
    if t > T_LAND - 0.08:
        u = prog(t, T_LAND - 0.08, T_LAND + 0.25)
        pose = rig.mix_pose(pose, merge(LYING, {"handL": (0.36, 1.0, 0.1), "handR": (-0.4, 1.02, -0.1)}), u); fl = lerp(fl, -0.55, u)
        mood = "closed"
        yw = lerp(yw, yaw_to(0, 1), u)
        if t > T_LAND + 0.6: mood = "tired"
        if t > wt("luft") - 0.2:
            r_ = prog(t, wt("luft") - 0.2, wt("luft") + 0.5)
            pose = merge(pose, {"handR": (-0.42, lerp(1.02, 1.5, r_), lerp(-0.1, 0.25, r_))}); mood = "happy" if r_ > 0.6 else "tired"
    yy = lerp(az.DU_Y, 7.15, prog(t, T_LAND - 0.08, T_LAND + 0.25))
    return F(-0.1, yy, cz(t) + fl), yw, 0.0, pose, mood

def after_flatten():
    """2.5D-Figuren (auf Zweiern) an die Kabine haengen: zwischen zwei Posen faehrt die flache Figur mit, statt zu ruckeln."""
    root = bpy.data.objects.get("cab_root")
    if root is None: return
    from mathutils import Matrix
    for o in bpy.data.objects:
        m = re.match(r"flat_.+_(\d{4})$", o.name)
        if not m or o.parent is not None: continue
        f = int(m.group(1)); o.parent = root; o.matrix_parent_inverse = Matrix.Translation((0, 0, -cz(tf(f))))

def visible(ch, frame, on):
    for o in list(ch.coll.all_objects):
        if "_face_" in o.name: continue
        o.hide_render = not on; o.keyframe_insert("hide_render", frame=frame)

def grade(**kw): sets2.GRADE.clear(); sets2.GRADE.update(kw)

# ---------------------------------------------------------------- gemeinsamer Aufbau
def build(sid):
    f0, f1 = SEG
    wk.world_color("16244a" if sid != "H" else "4a5a7a", 0.7 if sid != "H" else 0.9)
    root = bpy.data.objects.new("cab_root", None); bpy.context.scene.collection.objects.link(root)
    for f in range(f0, f1 + 1):
        root.location = (0, 0, cz(tf(f))); root.keyframe_insert("location", frame=f)
    cab = az.cabin(root)
    az.shaft(lobby=(sid == "L"))
    flat.STICK_COLOR = None; flat.LIGHT_POS = None
    mats.set_scene_light(tint=(1.0, 0.94, 0.86), rim_strength=0.0)
    # Tueren (nur in der Lobby offen)
    door_open = lambda t: (1.0 - prog(t, T_PRESS + 0.15, END_T - 0.04)) if t >= T_L else 0.0
    ds = wk.doors(lambda f: door_open(tf(f)), f1, y=6.08, c=wk.coll("cabin"))
    for _, d in ds: d.parent = root
    # Roentgen-Gruppen
    xr_main = lambda t: 0.0 if t >= T_L else (prog(t, T_X, T_X + 0.6) if t < T_H else prog(t, K_BLD + 0.45, K_BLD + 1.1))
    az.key_xr("xr", xr_main, f0, f1, tf)
    az.key_xr("xr_shaft", xr_main, f0, f1, tf)
    az.key_xr("xr_left", lambda t: xr_main(t) * (1 - prog(t, T_TRIP - 0.1, T_TRIP + 0.3) * (1 - prog(t, wt("meter") - 0.2, wt("meter") + 0.4))), f0, f1, tf)
    # Etagenanzeige
    for n, o in cab["nums"].items():
        az.key_hide(o, lambda t, n=n: floor_no(cz(t)) == n, f0, f1, tf)
    az.glow_button("80", 1 if sid != "L" else fr(T_PRESS))
    if sid == "L":
        m = bpy.data.materials.get("btn_glow_80"); e = m.node_tree.nodes["Emission"].inputs[1]; e.default_value = 0.0; e.keyframe_insert("default_value", frame=f0)
        e.default_value = 0.0; e.keyframe_insert("default_value", frame=fr(T_PRESS) - 1); e.default_value = 8.0; e.keyframe_insert("default_value", frame=fr(T_PRESS))
    # Alarm-Flackern im Fall
    L_ = cab["lights"]; rnd = random.Random(3)
    led = bpy.data.materials["cab_led"].node_tree.nodes["Emission"].inputs[1]
    for f in range(f0, f1 + 1, 2):
        t = tf(f); falling = t < T_RW0
        k = (0.35 + 0.65 * (rnd.random() > 0.25)) if falling else 1.0
        L_["cab_red"].data.energy = (14 + 6 * math.sin(t * 9)) if falling else 0.0; L_["cab_red"].data.keyframe_insert("energy", frame=f)
        L_["cab_top"].data.energy = 75 * k * (0.9 if falling else 1.0); L_["cab_top"].data.keyframe_insert("energy", frame=f)
        led.default_value = 3.0 * k * (0.85 if falling else 1.0); led.keyframe_insert("default_value", frame=f)
        L_["cab_key"].data.energy = 650 if T_X < t < T_L else 0.0; L_["cab_key"].data.keyframe_insert("energy", frame=f)
    return root, cab

# ---------------------------------------------------------------- Sets
def du_figure(root):
    def du(t):
        x, y, fl, yw, pose, mood = du_state(t)
        return dict(rig=R(S["du"], pose, t, F(x, y, cz(t) + fl), yw), mood=mood, blink=blink(t, 1), look=(0, 0))
    ch = figure("du", "du", du); ch.flat_bias = 0.25
    return ch, du

def cup_and_coffee(du, ch):
    cup = wk.cyl("cup", (0, 0, 0), 0.04, 0.13, wk.principled("cup_white", "f6f2ea", 0.45), r2=0.048, n=24)
    wk.cyl("cup_sleeve", (0, 0, 0.0), 0.0455, 0.05, wk.principled("cup_sleeve", "a8642e", 0.7), n=24).parent = cup
    wk.cyl("cup_lid", (0, 0, 0.07), 0.05, 0.018, wk.principled("cup_lid", "2a2a30", 0.4), n=24).parent = cup
    def cupf(t):
        rv = prog(t, T_RW0, T_RW1)
        zc = cz(t)
        fl = Vector((0.42 + 0.05 * math.sin(t * 1.3), 6.42, 1.28 + 0.06 * math.sin(t * 1.7) + 0.08 * prog(t, 0, 5))) + Vector((0, 0, zc))
        q = Quaternion((1, 0, 0), 0.6 * math.sin(t * 0.9)) @ Quaternion((0, 1, 0), 0.5 * t)
        if rv <= 0: return fl, q, True
        rg = du(t)["rig"]; h = flat_pt(hand(rg, 0), rg, ch, t, cam_all, 0.03) + Vector((0, 0, -0.05))
        return fl.lerp(h, rv), Quaternion().slerp(q, 1 - rv) if rv < 1 else Quaternion(), True
    f0, f1 = SEG
    prop_follow(cup, f0, f1, cupf, 1)
    # Kaffee-Kugeln, die aus dem Deckel schweben (nur im Fall)
    km = wk.principled("coffee", "5a2e14", 0.08, 0.0, coat=1.0)
    for i in range(3):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022 - i * 0.005, location=(0, 0, -999)); o = bpy.context.active_object; o.name = f"coffee{i}"; o.data.materials.append(km)
        for p_ in o.data.polygons: p_.use_smooth = True
        t_on = wt("kaffee") + 0.1 + i * 0.35
        def cf(t, i=i, t_on=t_on):
            if t < t_on or t > T_RW0: return Vector((0, 0, -999)), None, False
            base = cupf(t_on)[0]; a = t - t_on
            return base + Vector((-0.05 * a - 0.02 * i, -0.03 * a, 0.09 + 0.07 * a + 0.03 * math.sin(a * 2))) + Vector((0, 0, cz(t) - cz(t_on))), None, True
        prop_follow(o, f0, f1, cf, 1)

def ropes_keys(rp, cab_root, f0, f1):
    top = az.SHEAVE_Z - 0.72
    intact = lambda t, k: T_RW1 <= t < K_REISS + 0.15 and (k != 0) and t < T_H
    for k, o in enumerate(rp["ropes"]):
        for f in range(f0, f1 + 1):
            t = tf(f); a = cz(t) + 3.3; o.location.z = (a + top) / 2; o.scale.z = max(0.01, top - a)
            o.keyframe_insert("location", index=2, frame=f); o.keyframe_insert("scale", index=2, frame=f)
        az.key_hide(o, lambda t, k=k: intact(t, k), f0, f1, tf)
    az.key_hide(rp["up"], lambda t: T_RW1 <= t < T_H, f0, f1, tf)
    rp["sheave"].hide_render = False
    # Stummel auf dem Querhaupt: im Fall (A) einer, in der Realitaet einer, nach dem Reissen alle
    for k, y in enumerate(az.ROPE_Y):
        st = az.stub(f"stub{k}"); st.parent = cab_root; st.location = (0.0, y, 3.3); st.rotation_euler = (0, 0, 0.7 * k)
        az.key_hide(st, lambda t, k=k: (k == 0 and t < T_H) or (t >= K_REISS + 0.15 and t < T_H), f0, f1, tf)

def gov_keys(gv, f0, f1):
    ang = 0.0; hub = gv["hub"]
    for f in range(f0, f1 + 1):
        t = tf(f)
        w = (3.0 if T_RW1 < t < K_REISS else 0.0) + (lerp(3, 26, prog(t, K_REISS, T_TRIP)) if K_REISS <= t < T_TRIP + 0.08 else 0.0)
        ang += w / FPS; hub.rotation_euler = (ang, 0, 0); hub.keyframe_insert("rotation_euler", frame=f)
        out = prog(t, T_TRIP - 0.5, T_TRIP)
        for s, a in gv["arms"]: a.scale = (1, 1 + 0.7 * out, 1); a.keyframe_insert("scale", frame=f)
        gx, gy, gz = az.GOV; lo = cz(t) + 3.15; hi = gz
        gv["rope"].location = (gx, gy - 0.3, (lo + hi) / 2); gv["rope"].scale.z = max(0.01, hi - lo)
        gv["rope"].keyframe_insert("location", frame=f); gv["rope"].keyframe_insert("scale", index=2, frame=f)

def wedge_keys(cab, f0, f1):
    for (s, dy), w in cab["wedges"].items():
        for f in range(f0, f1 + 1, 1):
            u = prog(tf(f), T_WEDGE - 0.05, T_WEDGE + 0.25) if tf(f) < T_H else 0.0
            w.location = (s * lerp(1.36, 1.385, u), az.RAIL_Y + dy * lerp(0.055, 0.045, u), lerp(-0.14, -0.06, u))
            w.keyframe_insert("location", frame=f)

def shot_A():
    f0, f1 = SEG
    root, cab = build("A")
    grade(lift=(0.97, 0.98, 1.05), gain=(1.08, 1.0, 0.94), sat=1.18, contrast=0.14)
    ch, du = du_figure(root)
    cup_and_coffee(du, ch)
    rp = az.ropes(); ropes_keys(rp, root, f0, f1)
    sp = az.sparks("spk_rail", 36)
    az.key_sparks(sp, lambda t: Vector((-1.36 if int(t * 7) % 2 else 1.36, 7.0, cz(t) + 3.0)), lambda t: 1.0 if T_X < t < T_FZ else 0.0, f0, f1, tf, seed=2, spread=(0.6, 0.6, 1.0))
    camera(cam_all, f0, f1)

def shot_C():
    f0, f1 = SEG
    root, cab = build("C")
    grade(lift=(0.97, 0.98, 1.05), gain=(1.06, 1.0, 0.95), sat=1.16, contrast=0.12)
    ch, du = du_figure(root)
    cup_and_coffee(du, ch)
    rp = az.ropes(); ropes_keys(rp, root, f0, f1)
    gv = az.governor(); gov_keys(gv, f0, f1)
    wedge_keys(cab, f0, f1)
    sp = az.sparks("spk_wedge", 60)
    az.key_sparks(sp, lambda t: Vector((-1.40 if int(t * 23) % 3 else 1.40, 7.0, cz(t) - 0.08)), lambda t: 1.0 if T_WEDGE < t < T_STOP else 0.0, f0, f1, tf, seed=5, spread=(0.5, 1.2, 0.8))
    for nm in ("gov_light",): pass
    # Nebel zum Ende (Uebergang 1945)
    hz = wk.haze_box((-20, 5, az.Z80), (70, 60, 40), 0.0, (0.75, 0.82, 0.95), 0.3, name="c_fog")
    vs = hz.data.materials[0].node_tree.nodes["Volume Scatter"].inputs["Density"]
    for f in (f0, fr(T_H - 0.7), f1):
        vs.default_value = 0.0 if f < f1 else 0.06; vs.keyframe_insert("default_value", frame=f)
    bpy.context.scene.eevee.volumetric_end = 80
    camera(cam_all, f0, f1)

def shot_H():
    f0, f1 = SEG
    root, cab = build("H")
    grade(lift=(0.96, 0.98, 1.06), gain=(1.06, 1.0, 0.95), sat=1.2, contrast=0.12)
    tw = az.tower()
    az.key_xr("xr_tower", lambda t: prog(t, K_BLD + 0.35, K_BLD + 1.0), f0, f1, tf)
    wk.city(seed=5, extent=520, keep=lambda x, y: math.hypot(x, y - 7) > 80, near_max=150, cell=40)
    gm = wk.principled("asphalt", "2a2c34", 0.8)
    for cx_, cy_, sx_, sy_ in ((0, 7 - 522, 3000, 1000), (0, 7 + 522, 3000, 1000), (-530, 7, 1000, 44), (530, 7, 1000, 44)):
        wk.box(f"ground{cx_}{cy_}", (cx_, cy_, -0.5), (sx_, sy_, 1.0), gm)
    # Seil-Haufen in der Grube (abgerissenes Tragseil)
    cu_ = bpy.data.curves.new("coil", "CURVE"); cu_.dimensions = "3D"; sp_ = cu_.splines.new("POLY"); n = 140; sp_.points.add(n - 1)
    for i, p_ in enumerate(sp_.points):
        a = i * 0.45; r = 0.25 + 0.5 * (i / n); p_.co = (0.15 + r * math.cos(a), 7.0 + r * math.sin(a) * 0.9, az.PIT + 0.03 + 0.012 * i / 10 + 0.02 * math.sin(i), 1)
    cu_.bevel_depth = 0.016; co = bpy.data.objects.new("coil", cu_); wk.coll("shaft").objects.link(co); cu_.materials.append(wk.principled("rope", "8a909c", 0.35, 0.95))
    # Luftkissen unter der Kabine
    discs = []
    for k in range(3):
        d = wk.cyl(f"air{k}", (0, 7.0, 0), 1.35, 0.05, wk.emit(f"air_m{k}", "6fd8ff", 0.0), n=40); d.visible_shadow = False; discs.append(d)
        m = d.data.materials[0]; az.add_xray(m, "xr_air", alpha=0.0)
    for f in range(f0, f1 + 1):
        t = tf(f); z = cz(t); on = prog(t, T_LAND - 1.2, T_LAND - 0.2) * (1 - prog(t, T_L - 0.6, T_L))
        for k, d in enumerate(discs):
            ph_ = (t * 2.2 + k / 3) % 1.0
            d.location.z = max(az.PIT + 0.05, z - 0.25 - ph_ * max(0.4, z - az.PIT - 0.3)); d.scale = (1, 1, 1)
            d.keyframe_insert("location", index=2, frame=f)
            e = d.data.materials[0].node_tree.nodes["Emission"].inputs[1]; e.default_value = 3.0 * on * (1 - ph_); e.keyframe_insert("default_value", frame=f)
    az.key_xr("xr_air", lambda t: 0.7, f0, f1, tf)
    # Bomber
    pl, props = az.plane_b25()
    yaw = math.atan2(PLANE_D.y, PLANE_D.x); pitch = math.asin(-PLANE_D.z)
    def plf(t):
        u = lin_(t, K_RAST - 0.25, T_IMP)
        return PLANE_P0.lerp(PLANE_P1, u), None, K_RAST - 0.25 <= t < T_IMP
    pl.rotation_euler = (0, pitch, yaw)
    for f in range(f0, f1 + 1):
        t = tf(f); p_, _, v = plf(t); pl.location = p_; pl.keyframe_insert("location", frame=f)
        for o in [pl] + list(pl.children_recursive): o.hide_render = not v; o.keyframe_insert("hide_render", frame=f)
        for k, pr in enumerate(props): pr.rotation_euler = (t * 60 + k, 0, 0); pr.keyframe_insert("rotation_euler", frame=f)
    # Feuerball
    fb, fl_ = az.fireball(PLANE_P1 + Vector((0, -1.5, 0)))
    for f in range(f0, f1 + 1):
        t = tf(f); g = prog(t, T_IMP, T_IMP + 0.5); fade = 1 - prog(t, T_IMP + 0.5, T_IMP + 1.5)
        for o, s, m in fb:
            r = max(0.01, 3.0 * s * g * (1 + 0.15 * math.sin(t * 9 + s))); o.scale = (r, r, r); o.keyframe_insert("scale", frame=f)
            o.hide_render = not (T_IMP <= t < T_IMP + 1.6); o.keyframe_insert("hide_render", frame=f)
            e = m.node_tree.nodes["Emission"].inputs[1]; e.default_value = [40, 22, 10][fb.index((o, s, m))] * fade; e.keyframe_insert("default_value", frame=f)
        fl_.data.energy = 2.5e5 * g * (1 - prog(t, T_IMP + 0.3, T_IMP + 1.2)) if t >= T_IMP else 0.0; fl_.data.keyframe_insert("energy", frame=f)
    # Nebel + Mondlicht
    hz = wk.haze_box((0, 7, 220), (1300, 1300, 460), 0.004, (0.78, 0.84, 0.95), 0.3, name="h_fog")
    vs = hz.data.materials[0].node_tree.nodes["Volume Scatter"].inputs["Density"]
    vs.default_value = 0.05; vs.keyframe_insert("default_value", frame=f0)
    vs.default_value = 0.0045; vs.keyframe_insert("default_value", frame=fr(K_RAST - 0.4))
    vs.default_value = 0.0035; vs.keyframe_insert("default_value", frame=fr(K_STURZ))
    vs.default_value = 0.0006; vs.keyframe_insert("default_value", frame=fr(T_LAND))
    ee = bpy.context.scene.eevee; ee.volumetric_end = 400; ee.volumetric_tile_size = "8"
    sun = bpy.data.lights.new("moon", "SUN"); sun.energy = 2.5; sun.color = (0.7, 0.8, 1.0)
    so = bpy.data.objects.new("moon", sun); wk.coll("lights").objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(-30))
    # Betty
    def betty(t):
        p3, yw, wa, pose, mood = betty_state(t)
        return dict(rig=R(S["betty"], pose, t, p3, yw, walk=wa), mood=mood, blink=blink(t, 3), look=(0, 0))
    figure("betty", "betty", betty).flat_bias = 0.25
    # Staub beim Aufprall
    dz = wk.haze_box((0, 7.0, az.PIT + 1.2), (2.9, 2.5, 2.6), 0.0, (0.95, 0.85, 0.7), 0.2, name="dust")
    vd = dz.data.materials[0].node_tree.nodes["Volume Scatter"].inputs["Density"]
    for t_, v_ in ((T_LAND - 0.05, 0.0), (T_LAND + 0.15, 0.35), (T_LAND + 1.4, 0.03)):
        vd.default_value = v_; vd.keyframe_insert("default_value", frame=max(f0, fr(t_)))
    wk.point("pit_light", (-0.8, 6.4, az.PIT + 2.4), 140, (1.0, 0.85, 0.65), r=0.6)
    camera(cam_all, f0, f1, clip=(0.05, 3000))

def shot_L():
    f0, f1 = SEG
    root, cab = build("L")
    grade(lift=(1.0, 0.99, 1.01), gain=(1.06, 1.0, 0.92), sat=1.12, contrast=0.1)
    wk.lobby()
    def du(t):
        p3, yw, wa, pose, mood = du_lobby(t)
        return dict(rig=R(S["du"], pose, t, p3, yw, walk=wa), mood=mood, blink=blink(t, 1), look=(0, 0))
    ch = figure("du", "du", du); ch.flat_bias = 0.3
    cup = wk.cyl("cup", (0, 0, 0), 0.04, 0.13, wk.principled("cup_white", "f6f2ea", 0.45), r2=0.048, n=24)
    wk.cyl("cup_sleeve", (0, 0, 0.0), 0.0455, 0.05, wk.principled("cup_sleeve", "a8642e", 0.7), n=24).parent = cup
    wk.cyl("cup_lid", (0, 0, 0.07), 0.05, 0.018, wk.principled("cup_lid", "2a2a30", 0.4), n=24).parent = cup
    def cupf(t):
        rg = du(t)["rig"]; return flat_pt(hand(rg, 0), rg, ch, t, cam_all, 0.03) + Vector((0, 0, -0.05)), None, True
    camera(cam_all, f0, f1)
    prop_follow(cup, f0, f1, cupf, 1)

F_C, F_H, F_L = fr(T_FZ), fr(T_H), fr(T_L)
SHOTS = {"A": (shot_A, 1, F_C - 1), "C": (shot_C, F_C, F_H - 1), "H": (shot_H, F_H, F_L - 1), "L": (shot_L, F_L, NFR)}
RT = {}; MB = {}
