"""Sets fuer den Aufzug-Short (Blender-Achsen: x rechts, y Tiefe, z oben).
Kabine innen wie wolkenkratzer/wk.CAB: x -1.1..1.1, y 6..8 (Tuer bei y = 6), Hoehe 2.6. Alles Kabinen-Zeug haengt an einem Root-Empty (z = Kabinenboden).
Schacht: x -1.5..1.5, y 5.75..8.35, Etage n bei z = (n-1)*3.6, Grube bis z = -1.8.
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "wolkenkratzer", "blender"))   # wk.py: Kabine, Lobby, Materialien
import wk
from wk import box, cyl, text, principled, emit, gold, pbr, area, point, spot, coll, lin, FONT_I, FONT_B

FH = 3.6
def fz(n): return (n - 1) * FH
Z80 = fz(80)
TOP = Z80 + 9.5                        # Schachtdecke (Maschinenraum darueber)
PIT = -1.8
SX0, SX1, SY0, SY1 = -1.5, 1.5, 5.75, 8.35
RAIL_X = 1.40; RAIL_Y = 7.0
DU_Y = 6.62                            # Figuren vor dem Kabinen-Stil (y = 7.0), damit nichts ueber dem Koerper liegt

# ---------------------------------------------------------------- Roentgen-Material (keyframebarer Mix)
XR = {}   # gruppe -> [Value-Nodes]
def add_xray(mat, group="xr", alpha=0.08, col="7fe8ff"):
    """Mischt die vorhandene Oberflaeche mit einem Geister-Shader (transparent + Fresnel-Kanten). Wert 1 = Roentgen."""
    N = mat.node_tree.nodes; L = mat.node_tree.links
    out = [n for n in N if n.type == "OUTPUT_MATERIAL"][0]
    if not out.inputs["Surface"].links: return
    src = out.inputs["Surface"].links[0].from_socket; L.remove(out.inputs["Surface"].links[0])
    tr = N.new("ShaderNodeBsdfTransparent")
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    ma = N.new("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; ma.inputs[1].default_value = 1.1; ma.inputs[2].default_value = 0.06
    L.new(lw.outputs["Facing"], ma.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = lin(col); L.new(ma.outputs[0], em.inputs[1])
    gh = N.new("ShaderNodeMixShader"); gh.inputs[0].default_value = alpha; L.new(tr.outputs[0], gh.inputs[1]); L.new(em.outputs[0], gh.inputs[2])
    mx = N.new("ShaderNodeMixShader"); v = N.new("ShaderNodeValue"); v.name = "xr"; v.outputs[0].default_value = 0.0
    L.new(v.outputs[0], mx.inputs[0]); L.new(src, mx.inputs[1]); L.new(gh.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"): mat.surface_render_method = "BLENDED"
    try: mat.use_transparency_overlap = True
    except Exception: pass
    XR.setdefault(group, []).append(v)

def xray_obj(o, group="xr"):
    """Eigene Materialkopie fuer das Objekt, damit andere Nutzer des Materials undurchsichtig bleiben."""
    if o.type not in ("MESH", "CURVE", "FONT") or not o.data.materials: return
    for i, m in enumerate(o.data.materials):
        if m is None: continue
        k = f"{m.name}__{group}"
        mm = bpy.data.materials.get(k)
        if mm is None:
            mm = m.copy(); mm.name = k; add_xray(mm, group)
        o.data.materials[i] = mm

def key_xr(group, fn, f0, f1, tf):
    """Jedes Bild keyen (sonst interpoliert Bezier zwischen weit entfernten Keys)."""
    for f in range(f0, f1 + 1):
        v = round(fn(tf(f)), 3)
        for n in XR.get(group, []): n.outputs[0].default_value = v; n.outputs[0].keyframe_insert("default_value", frame=f)

def key_hide(o, vis_fn, f0, f1, tf):
    last = None
    for f in range(f0, f1 + 1):
        v = bool(vis_fn(tf(f)))
        if v != last or f == f0:
            for oo in [o] + list(o.children_recursive): oo.hide_render = not v; oo.keyframe_insert("hide_render", frame=f)
            last = v

# ---------------------------------------------------------------- Kabine
CAB = wk.CAB
PANEL = dict(x=1.07, y=6.45, z=1.15)
LABELS = ["80", "79", "70", "60", "50", "40", "30", "20", "10", "1"]
def btn_pos(lab):
    k = LABELS.index(lab); return (PANEL["y"] + 0.04 - 0.08 * (k % 2), PANEL["z"] + 0.3 - 0.13 * (k // 2))

def cabin(root):
    """Goldkabine (innen), Aussenrahmen (Stile, Querhaupt, Fanggeraete), Tastenfeld 1-80, Etagenanzeige. Alles an root."""
    c = coll("cabin"); g = gold("cab_gold", "a8742e", 0.34); g2 = gold("cab_gold_dark", "8a5a24", 0.32)
    x0, x1, y0, y1, h = CAB["x0"], CAB["x1"], CAB["y0"], CAB["y1"], CAB["h"]
    P = []
    P.append(box("cab_floor", (0, (y0 + y1) / 2, -0.03), (x1 - x0, y1 - y0, 0.06), wk._marble(0.5, (0.95, 0.9, 0.85), 0.3, "cab_marble"), c=c))
    P.append(box("cab_ceil", (0, (y0 + y1) / 2, h + 0.03), (x1 - x0 + 0.1, y1 - y0, 0.06), g2, c=c))
    P.append(box("cab_light", (0, (y0 + y1) / 2, h - 0.005), (x1 - x0 - 0.5, y1 - y0 - 0.5, 0.01), emit("cab_led", "fff1d6", 3.0), c=c))
    walls = []
    for nm, cx in (("cab_wl", x0 - 0.03), ("cab_wr", x1 + 0.03)):
        walls.append(box(nm, (cx, (y0 + y1) / 2, h / 2), (0.06, y1 - y0, h), g, c=c))
    P += walls
    P.append(box("cab_wb", (0, y1 + 0.03, h / 2), (x1 - x0 + 0.12, 0.06, h), principled("cab_back", "9a6a30", 0.62, 0.6), c=c))
    strips = []
    for z in (0.95, 2.1):
        for nm, cx in (("l", x0 + 0.01), ("r", x1 - 0.01)): strips.append(box(f"cab_strip_{nm}{z}", (cx, (y0 + y1) / 2, z), (0.03, y1 - y0, 0.03), g2, c=c))
        P.append(box(f"cab_strip_b{z}", (0, y1 - 0.01, z), (x1 - x0, 0.03, 0.03), g2, c=c))
    P += strips
    P.append(cyl("cab_rail", (0, y1 - 0.08, 0.92), 0.025, x1 - x0 - 0.3, gold("rail_gold", "ffd27a", 0.15), axis="X", c=c))
    for s in (-1, 1): P.append(box(f"cab_front{s}", (s * 0.85, y0 + 0.025, h / 2), (0.5, 0.05, h), g2, c=c))
    P.append(box("cab_front_top", (0, y0 + 0.025, 2.45), (2.2, 0.05, 0.3), g2, c=c))
    P.append(box("cab_disp", (0, y0 + 0.065, 2.43), (0.36, 0.03, 0.14), principled("disp_black", "0a0a0c", 0.3), c=c))
    # Tastenfeld
    brass = principled("panel_bronze", "3a2a1c", 0.32, 0.85)
    P.append(box("panel_plate", (PANEL["x"], PANEL["y"], PANEL["z"]), (0.02, 0.24, 0.8), brass, bevel=0.006, c=c))
    P.append(box("panel_frame", (PANEL["x"] + 0.002, PANEL["y"], PANEL["z"]), (0.018, 0.27, 0.83), gold("frame_gold", "f2c060", 0.2), bevel=0.004, c=c))
    ink = principled("btn_txt", "120c08", 0.7)
    for lab in LABELS:
        by, bz = btn_pos(lab)
        P.append(cyl(f"btn_{lab}", (PANEL["x"] - 0.016, by, bz), 0.03, 0.014, principled("btn_gold", "e0b25e", 0.3, 0.7), axis="X", n=32, c=c))
        P.append(cyl(f"btn_ring_{lab}", (PANEL["x"] - 0.011, by, bz), 0.037, 0.008, emit(f"btn_glow_{lab}", "ffb347", 0.0), axis="X", n=32, c=c))
        P.append(text(f"btn_txt_{lab}", lab, (PANEL["x"] - 0.0235, by, bz - 0.001), 0.034, rot=(math.pi / 2, 0, -math.pi / 2), mat=ink, font=FONT_I, c=c))
    P.append(cyl("btn_alarm", (PANEL["x"] - 0.016, PANEL["y"], PANEL["z"] - 0.34), 0.026, 0.014, principled("alarm", "c0281e", 0.3), axis="X", c=c))
    # Etagenanzeige (eine Zahl je Etage, Sichtbarkeit wird pro Set gekeyt)
    nums = {}
    red = emit("disp_num", "ff5a2a", 6.0)
    for n in range(1, 81):
        nums[n] = text(f"disp_{n}", str(n), (0, y0 + 0.083, 2.425), 0.1, rot=(math.pi / 2, 0, math.pi), mat=red, font=FONT_I, c=c); P.append(nums[n])
    # Aussenrahmen: Stile an den Schienen (x = +-1.25, y = 7.0), Querhaupt, Bodenrahmen, Fanggeraete mit Keilen
    st = principled("frame_steel", "2c3240", 0.45, 0.85); yel = principled("wedge_yel", "f2c014", 0.35, 0.3)
    left, right = [], []
    for s, L_ in ((-1, left), (1, right)):
        L_.append(box(f"stile{s}", (s * 1.24, RAIL_Y, 1.4), (0.07, 0.1, 3.4), st, c=c))
        L_.append(box(f"sgear{s}", (s * 1.3, RAIL_Y, -0.12), (0.16, 0.24, 0.22), st, c=c))
        L_.append(box(f"shoe{s}", (s * 1.3, RAIL_Y, 3.0), (0.14, 0.2, 0.14), st, c=c))
    P += left + right
    P.append(box("crosshead", (0, RAIL_Y, 3.1), (2.6, 0.16, 0.18), st, c=c))
    P.append(box("plank", (0, RAIL_Y, -0.15), (2.6, 0.5, 0.16), st, c=c))
    P.append(box("hitch", (0, RAIL_Y, 3.25), (0.25, 0.85, 0.1), st, c=c))
    wedges = {}
    for s in (-1, 1):
        for dy in (-1, 1):
            w = box(f"wedge{s}{dy}", (s * 1.36, RAIL_Y + dy * 0.055, -0.14), (0.05, 0.035, 0.16), yel, c=c); wedges[(s, dy)] = w; P.append(w)
            (left if s < 0 else right).append(w)
    lev = box("gov_lever", (-1.24, 7.7, 3.0), (0.04, 0.04, 0.3), yel, c=c); P.append(lev); left.append(lev)
    # Licht innen (warm) + Aussen-Key fuer die Roentgen-Seitenansicht
    lights = [area("cab_top", (0, (y0 + y1) / 2, h - 0.03), (0, 0, 0), 55, 1.4, (1, 0.9, 0.74), sy=1.2),
              point("cab_fill", (0, 7.2, 2.2), 25, (1, 0.88, 0.7), r=0.5),
              point("cab_red", (0, 7.4, 2.4), 0.0, (1.0, 0.12, 0.06), r=0.6),
              area("cab_key", (-4.5, 6.8, 2.4), (0, -math.pi / 2, 0), 650, 3.0, (0.85, 0.92, 1.0)),
              area("cab_rim", (3.0, 6.4, 3.6), (0, math.radians(60), 0), 0.0, 2.0, (0.5, 0.8, 1.0)),
              point("cab_under_l", (0, 7.0, -0.6), 120, (1.0, 0.75, 0.45), r=0.5),
              point("cab_over_l", (0, 7.0, 3.8), 120, (0.7, 0.85, 1.0), r=0.5)]
    for o in P + lights: o.parent = root   # keine mitfahrende Licht-Sonde (wird sonst jedes Bild neu aufgenommen: +0.3 s/Bild)
    for w_ in walls + strips: xray_obj(w_, "xr")
    for o in left: xray_obj(o, "xr_left")
    return dict(nums=nums, walls=walls, wedges=wedges, lights={l.name: l for l in lights})

def glow_button(lab, f_on, strength=8.0):
    m = bpy.data.materials.get(f"btn_glow_{lab}")
    if not m: return
    e = m.node_tree.nodes["Emission"].inputs[1]
    if f_on <= 1: e.default_value = strength; e.keyframe_insert("default_value", frame=1); return
    e.default_value = 0.0; e.keyframe_insert("default_value", frame=f_on - 1)
    e.default_value = strength; e.keyframe_insert("default_value", frame=f_on)

# ---------------------------------------------------------------- Schacht
def shaft(zmin=PIT, zmax=TOP, lobby=False):
    c = coll("shaft")
    con = pbr("concrete_wall_008", 0.35, (0.82, 0.86, 0.95), rough_mul=1.0, bump=0.8, name="shaft_con")
    H = zmax - zmin; zc = (zmin + zmax) / 2
    ya = 5.96 if lobby else SY0 - 0.25; yb = SY1 + 0.25
    wl = box("sh_wl", (SX0 - 0.12, (ya + yb) / 2, zc), (0.24, yb - ya, H), con, c=c); xray_obj(wl, "xr_shaft")
    box("sh_wr", (SX1 + 0.12, (ya + yb) / 2, zc), (0.24, yb - ya, H), con, c=c)
    box("sh_wb", (0, SY1 + 0.12, zc), (SX1 - SX0 + 0.5, 0.24, H), con, c=c)
    zf = 6.0 if lobby else zmin
    box("sh_wf", (0, SY0 - 0.12, (zf + zmax) / 2), (SX1 - SX0 + 0.5, 0.24, zmax - zf), con, c=c)   # in der Lobby uebernimmt deren Aufzugswand
    box("sh_pit", (0, (SY0 + SY1) / 2, zmin - 0.15), (SX1 - SX0 + 0.5, SY1 - SY0 + 0.5, 0.3), principled("pit", "3a3d46", 0.8), c=c)
    box("sh_top", (0, (SY0 + SY1) / 2, zmax + 0.15), (SX1 - SX0 + 0.5, SY1 - SY0 + 0.5, 0.3), con, c=c)
    steel = principled("sh_steel", "7a8494", 0.35, 0.95); dark = principled("sh_dark", "1a1d24", 0.6, 0.6)
    for sx in (-RAIL_X, RAIL_X):
        r_ = box(f"rail{sx}", (sx, RAIL_Y, zc), (0.05, 0.12, H), steel, c=c)
        if sx < 0: xray_obj(r_, "xr_shaft")
        for k in range(int(zmin), int(zmax), 3):
            b_ = box(f"rbr{sx}_{k}", (sx + 0.07 * (1 if sx > 0 else -1), RAIL_Y, k), (0.1, 0.3, 0.08), dark, c=c)
            if sx < 0: xray_obj(b_, "xr_shaft")
    for sy in (SY0 + 0.25, SY1 - 0.25): box(f"cwrail{sy}", (SX1 - 0.2, sy, zc), (0.06, 0.06, H), steel, c=c)
    yel = principled("sh_yellow", "ffc61a", 0.5); paint = emit("sh_paint", "f4f6fa", 1.4); lamp = emit("sh_lamp", "d4e6ff", 7.0)
    for fl in range(1, 81):
        z = fz(fl)
        if z < zmin - 1 or z > zmax: continue
        box(f"beam{fl}", (SX1 - 0.03, (SY0 + SY1) / 2, z + 0.15), (0.06, SY1 - SY0, 0.3), principled("sh_slab", "4a4e5a", 0.8), c=c)
        box(f"stripe{fl}", (SX1 - 0.004, 7.95, z + 0.75), (0.01, 0.7, 0.12), yel, c=c)
        text(f"num{fl}", str(fl), (SX1 - 0.006, 7.65, z + 1.7), 0.95, rot=(math.pi / 2, 0, -math.pi / 2), mat=paint, font=FONT_I, c=c)
        box(f"lamp{fl}", (SX1 - 0.05, 5.95, z + 2.7), (0.08, 0.14, 0.26), lamp, c=c)
        box(f"sill{fl}", (0, SY0 + 0.06, z), (1.3, 0.12, 0.06), principled("sill", "9aa0aa", 0.4, 0.8), c=c)
    # Puffer in der Grube
    for sx in (-0.55, 0.55):
        cyl(f"buffer{sx}", (sx, RAIL_Y, zmin + 0.45), 0.16, 0.9, yel, c=c)
    return c

# ---------------------------------------------------------------- Seile, Treibscheibe, Fliehkraftregler
ROPE_Y = [6.68 + k * 0.09 for k in range(8)]
SHEAVE_Z = TOP - 0.9
def ropes(c=None):
    c = c or coll("ropes"); steel = principled("rope", "8a909c", 0.35, 0.95)
    sh = cyl("sheave", (0, 7.0, SHEAVE_Z), 0.75, 1.0, principled("sheave", "9aa4b4", 0.3, 0.95), axis="Y", n=48, c=c)
    point("sheave_light", (-1.0, 6.2, SHEAVE_Z - 1.2), 160, (1.0, 0.92, 0.8), r=0.4)
    cyl("sheave_hub", (0, 7.0, SHEAVE_Z), 0.18, 1.1, principled("hub", "d8262c", 0.4, 0.4), axis="Y", n=24, c=c)
    R = []
    for k, y in enumerate(ROPE_Y):
        R.append(cyl(f"rope{k}", (-0.02 * (k % 2), y, 0), 0.014, 1.0, steel, n=8, c=c))   # Hoehe/Lage wird gekeyt
    # gerissenes Seil: oberer Stummel haengt von der Scheibe, unterer krumm auf dem Querhaupt
    up = cyl("rope_snap_up", (0, ROPE_Y[0], SHEAVE_Z - 3.0), 0.014, 6.0, steel, n=8, c=c)
    return dict(ropes=R, up=up, sheave=sh)

def stub(name, c=None):
    """Krummer Seilstummel (3 Segmente) als Kind eines Empties."""
    c = c or coll("ropes"); steel = principled("rope", "8a909c", 0.35, 0.95)
    root = bpy.data.objects.new(name, None); c.objects.link(root)
    pts = [Vector((0, 0, 0)), Vector((0.05, 0.1, 0.6)), Vector((0.25, 0.0, 1.0)), Vector((0.5, -0.15, 1.15))]
    for i in range(3):
        a, b = pts[i], pts[i + 1]; d = b - a
        o = cyl(f"{name}_{i}", (a + b) / 2, 0.014, d.length, steel, n=8, c=c); o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d); o.parent = root
    return root

GOV = (-1.15, 8.0, TOP - 1.4)
def governor(c=None):
    """Geschwindigkeitsbegrenzer: Scheibe (zeigt zur Kamera, -x), zwei Fliehgewichte an Armen, roter Rahmen."""
    c = c or coll("gov"); red = principled("gov_red", "d8262c", 0.4, 0.4); st = principled("gov_steel", "aab2c0", 0.3, 0.95); yel = principled("wedge_yel", "f2c014", 0.35, 0.3)
    gx, gy, gz = GOV
    box("gov_base", (gx + 0.1, gy, gz - 0.45), (0.3, 0.5, 0.12), red, c=c)
    for s in (-1, 1): box(f"gov_post{s}", (gx + 0.1, gy + s * 0.2, gz - 0.2), (0.08, 0.06, 0.5), red, c=c)
    hub = bpy.data.objects.new("gov_hub", None); c.objects.link(hub); hub.location = (gx, gy, gz); hub.rotation_mode = "XYZ"
    wheel = cyl("gov_wheel", (0, 0, 0), 0.32, 0.06, principled("gov_wheel", "c8d0dc", 0.25, 0.95), axis="X", n=48, c=c); wheel.parent = hub
    cyl("gov_groove", (0, 0, 0), 0.27, 0.07, principled("gov_dark", "22262e", 0.5, 0.8), axis="X", n=48, c=c).parent = hub
    arms = []
    for s in (-1, 1):
        a = bpy.data.objects.new(f"gov_arm{s}", None); c.objects.link(a); a.parent = hub; a.location = (-0.06, 0, 0); a.rotation_mode = "XYZ"
        bar = box(f"gov_bar{s}", (0, s * 0.1, 0), (0.03, 0.2, 0.03), st, c=c); bar.parent = a
        wt_ = box(f"gov_wt{s}", (0, s * 0.2, 0), (0.06, 0.09, 0.12), yel, c=c); wt_.parent = a
        arms.append((s, a))
    rope = cyl("gov_rope", (gx, gy - 0.3, 0), 0.008, 1.0, principled("rope", "8a909c", 0.35, 0.95), n=6, c=c)
    point("gov_light", (gx - 1.2, gy - 0.6, gz + 0.6), 220, (1.0, 0.9, 0.8), r=0.3)
    return dict(hub=hub, arms=arms, rope=rope)

# ---------------------------------------------------------------- Funken
def sparks(name, n=40, c=None):
    c = c or coll("fx"); m = emit("spark", "ffb347", 40.0); out = []
    for k in range(n):
        o = box(f"{name}{k}", (0, 0, -999), (0.008, 0.008, 0.09), m, c=c); o.visible_shadow = False; out.append(o)
    return out

def key_sparks(objs, origin_fn, active_fn, f0, f1, tf, seed=1, spread=(1.0, 1.0, 1.0)):
    """origin_fn(t) -> Vector, active_fn(t) -> Intensitaet 0..1. Jeder Funke lebt 0.35 s, ballistisch."""
    rnd = random.Random(seed)
    life = 0.35
    births = [rnd.uniform(0, life) for _ in objs]
    vel = [Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1], rnd.uniform(0.3, 1.6) * spread[2])) * rnd.uniform(1.5, 3.5) for _ in objs]
    for f in range(f0, f1 + 1):
        t = tf(f)
        for i, o in enumerate(objs):
            age = (t - births[i]) % life; tb_ = t - age
            on = active_fn(tb_) > rnd.random() * 0.0 + (i / len(objs)) * 0.999
            if on:
                p = origin_fn(tb_) + vel[i] * age + Vector((0, 0, -4.9 * age * age))
                o.location = p; d = vel[i] + Vector((0, 0, -9.8 * age))
                o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
                o.scale = (1, 1, max(0.3, 1 - age / life))
            else:
                o.location = (0, 0, -999)
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f); o.keyframe_insert("scale", frame=f)

# ---------------------------------------------------------------- 1945: Turm (Art deco), Stadt im Nebel, Bomber, Feuerball
TW_SECT = [(0, 25, 60, 44), (25, 90, 50, 36), (90, 300, 40, 28), (300, 330, 30, 22), (330, 362, 18, 14), (362, 380, 10, 8)]
def tower(c=None):
    c = c or coll("tower"); bm = bmesh.new()
    for z0, z1, w, d in TW_SECT:
        g = bmesh.ops.create_cube(bm, size=1.0)
        for v in g["verts"]: v.co = Vector((v.co.x * w, 7 + v.co.y * d, z0 + (v.co.z + 0.5) * (z1 - z0)))
    me = bpy.data.meshes.new("tower"); bm.to_mesh(me); bm.free()
    ca = me.color_attributes.new("tint", "BYTE_COLOR", "CORNER")
    for d_ in ca.data: d_.color = lin("c9b48e")
    o = bpy.data.objects.new("tower", me); c.objects.link(o)
    m = wk.city_mat("tower_mat", haze="7c90b8").copy(); m.name = "tower_mat_x"; me.materials.append(m); add_xray(m, "xr_tower", alpha=0.05, col="8fe0ff")
    # Mast + Krone
    sp = cyl("spire", (0, 7, 380 + 30), 2.6, 60, principled("spire", "c8ccd4", 0.3, 0.9), r2=0.4, c=c); xray_obj(sp, "xr_tower")
    for k, (z, r) in enumerate(((381, 6), (386, 4.5), (391, 3.4))):
        o_ = cyl(f"crown{k}", (0, 7, z), r, 1.2, emit("crown", "fff0c8", 5.0), n=32, c=c); xray_obj(o_, "xr_tower")
    return o

def plane_b25(c=None):
    """Zweimotoriger Bomber, Nase zeigt nach +x (Ursprung = Nase)."""
    c = c or coll("plane"); root = bpy.data.objects.new("plane", None); c.objects.link(root); root.rotation_mode = "XYZ"
    ol = principled("b25", "5c6a3e", 0.55, 0.2); gl = principled("b25_glass", "9fc8e8", 0.1, 0.0, emit="3a5a80", es=0.5); dk = principled("b25_dark", "2a2e26", 0.6)
    P = [cyl("pl_fus", (-7.5, 0, 0), 1.0, 15, ol, axis="X", r2=0.75, c=c), cyl("pl_nose", (-0.4, 0, 0), 0.75, 0.8, gl, axis="X", r2=0.2, c=c),
         box("pl_wing", (-6.5, 0, 0.4), (3.0, 20.5, 0.35), ol, bevel=0.1, c=c), box("pl_stab", (-14.4, 0, 0.9), (1.6, 7.4, 0.2), ol, c=c)]
    for s in (-1, 1):
        P += [cyl(f"pl_eng{s}", (-5.0, s * 3.4, 0.25), 0.75, 3.6, dk, axis="X", r2=0.6, c=c), box(f"pl_fin{s}", (-14.6, s * 3.7, 2.0), (1.6, 0.2, 2.6), ol, c=c),
              box(f"pl_prop{s}", (-3.15, s * 3.4, 0.25), (0.08, 0.25, 3.4), dk, c=c)]
        P.append(box(f"pl_nav{s}", (-6.5, s * 10.3, 0.4), (0.2, 0.2, 0.2), emit(f"nav{s}", "ff2a2a" if s < 0 else "2aff5a", 30.0), c=c))
    for o in P: o.parent = root
    return root, [o for o in P if o.name.startswith("pl_prop")]

def fireball(loc, c=None):
    c = c or coll("fx")
    out = []
    for k, (col, s, es) in enumerate((("fff1a8", 1.0, 40.0), ("ffa020", 1.5, 22.0), ("ff7a1a", 2.1, 12.0))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=loc); o = bpy.context.active_object; o.name = f"fire{k}"
        for cc in o.users_collection: cc.objects.unlink(o)
        c.objects.link(o)
        m = emit(f"fire_m{k}", col, es); o.data.materials.append(m); o.visible_shadow = False
        d = o.modifiers.new("disp", "DISPLACE"); tx = bpy.data.textures.new(f"fire_tx{k}", "CLOUDS"); tx.noise_scale = 0.45; d.texture = tx; d.strength = 0.5
        out.append((o, s, m))
    l = point("fire_light", loc + Vector((0, -6, 0)), 0.0, (1.0, 0.55, 0.2), r=4.0)
    return out, l
