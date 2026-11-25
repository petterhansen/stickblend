"""Sets fuer den Wolkenkratzer-Short. Alle Koordinaten hier in BLENDER-Achsen (x rechts, y in die Tiefe, z oben).
Figuren/Kamera-Helfer in shots.py rechnen ggf. um (three: (x, z, -y)).
"""
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, Euler
from stickblend import mats, ph, world, sets, sets2, flat

IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
FONT_B = r"C:\Windows\Fonts\bahnschrift.ttf"
FONT_I = r"C:\Windows\Fonts\impact.ttf"
lin = lambda h: tuple(mats.lin(h))[:3] + (1,)

# ---------------------------------------------------------------- Grundbausteine
def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    return c

def box(name, center, size, mat=None, bevel=0.0, c=None):
    """Quader: center/size in Blender-Achsen."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); (c or coll("set")).objects.link(o); o.location = center
    if mat: me.materials.append(mat)
    if bevel:
        m = o.modifiers.new("bev", "BEVEL"); m.width = bevel; m.segments = 2; m.limit_method = "ANGLE"
    return o

def cyl(name, center, r, h, mat=None, axis="Z", n=32, c=None, r2=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); (c or coll("set")).objects.link(o); o.location = center
    if axis == "X": o.rotation_euler = (0, math.pi / 2, 0)
    if axis == "Y": o.rotation_euler = (math.pi / 2, 0, 0)
    if mat: me.materials.append(mat)
    return o

def plane(name, center, size, rot=(0, 0, 0), mat=None, c=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=center, rotation=rot); o = bpy.context.active_object; o.name = name
    o.scale = (size[0], size[1], 1)
    for cc in o.users_collection: cc.objects.unlink(o)
    (c or coll("set")).objects.link(o)
    if mat: o.data.materials.append(mat)
    return o

def text(name, s, loc, size, rot=(math.pi / 2, 0, 0), mat=None, font=FONT_B, extrude=0.0, align="CENTER", c=None):
    cu = bpy.data.curves.new(name, "FONT"); cu.body = s; cu.size = size; cu.align_x = align; cu.align_y = "CENTER"; cu.extrude = extrude
    try: cu.font = bpy.data.fonts.load(font, check_existing=True)
    except Exception: pass
    o = bpy.data.objects.new(name, cu); (c or coll("set")).objects.link(o); o.location = loc; o.rotation_euler = rot
    if mat: cu.materials.append(mat)
    return o

# ---------------------------------------------------------------- Materialien
_M = {}
def principled(name, col, rough=0.5, metal=0.0, emit=None, es=0.0, alpha=1.0, coat=0.0):
    if name in _M and name in bpy.data.materials: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(col) if isinstance(col, str) else col
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat
    if emit: b.inputs["Emission Color"].default_value = lin(emit); b.inputs["Emission Strength"].default_value = es
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    _M[name] = m; return m

def emit(name, col, strength=4.0):
    if name in _M and name in bpy.data.materials: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; N.remove(N["Principled BSDF"])
    e = N.new("ShaderNodeEmission"); e.inputs[0].default_value = lin(col); e.inputs[1].default_value = strength
    m.node_tree.links.new(e.outputs[0], N["Material Output"].inputs[0]); _M[name] = m; return m

def gold(name="gold", col="f2b84a", rough=0.22, brushed=True):
    """Poliertes Messing/Gold mit feinen Schliffspuren."""
    if name in _M and name in bpy.data.materials: return _M[name]
    m = principled(name, col, rough, 1.0); N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    if brushed:
        tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 60)
        L.new(tc.outputs["Object"], mp.inputs[0]); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 30; nz.inputs["Detail"].default_value = 6
        L.new(mp.outputs[0], nz.inputs[0]); mr = N.new("ShaderNodeMapRange"); mr.inputs[3].default_value = rough * 0.6; mr.inputs[4].default_value = rough * 1.5
        L.new(nz.outputs[0], mr.inputs[0]); L.new(mr.outputs[0], b.inputs["Roughness"])
    return m

def pbr(tid, scale=1.0, tint=(1, 1, 1), rough_mul=1.0, bump=0.6, metallic=0.0, rough_add=0.0, name=None):
    """Poly-Haven-Textur, Box-Projektion in Objektkoordinaten; rough_mul < 1 = poliert."""
    key = name or f"pbr_{tid}_{scale}_{tint}_{rough_mul}"
    if key in _M and key in bpy.data.materials: return _M[key]
    import glob
    d = os.path.join(ph.PH, "textures", tid)
    fs = {k: (glob.glob(os.path.join(d, f"*{k}*")) or [None])[0] for k in ("diff", "nor_gl", "rough")}
    m = bpy.data.materials.new(key); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    b.inputs["Metallic"].default_value = metallic
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale,) * 3; L.new(tc.outputs["Object"], mp.inputs[0])
    def img(path, nc=False):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.projection = "BOX"; t.projection_blend = 0.25
        if nc: t.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs[0], t.inputs[0]); return t
    if fs["diff"]:
        dt = img(fs["diff"]); mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L.new(dt.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (*tint, 1); L.new(mul.outputs[2], b.inputs["Base Color"])
    if fs["rough"]:
        mr = N.new("ShaderNodeMath"); mr.operation = "MULTIPLY_ADD"; mr.inputs[1].default_value = rough_mul; mr.inputs[2].default_value = rough_add
        L.new(img(fs["rough"], True).outputs[0], mr.inputs[0]); L.new(mr.outputs[0], b.inputs["Roughness"])
    if fs["nor_gl"] and bump:
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump; L.new(img(fs["nor_gl"], True).outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], b.inputs["Normal"])
    _M[key] = m; return m

def area(name, loc, rot, energy, size, col=(1, 0.85, 0.65), shape="RECTANGLE", sy=None, shadow=True):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = col; l.shape = shape; l.size = size
    if sy: l.size_y = sy
    l.use_shadow = shadow
    o = bpy.data.objects.new(name, l); coll("lights").objects.link(o); o.location = loc; o.rotation_euler = rot; return o

def point(name, loc, energy, col=(1, 0.8, 0.55), r=0.1, shadow=True):
    l = bpy.data.lights.new(name, "POINT"); l.energy = energy; l.color = col; l.shadow_soft_size = r; l.use_shadow = shadow
    o = bpy.data.objects.new(name, l); coll("lights").objects.link(o); o.location = loc; return o

def spot(name, loc, rot, energy, angle, col=(1, 1, 1), blend=0.3, r=0.1):
    l = bpy.data.lights.new(name, "SPOT"); l.energy = energy; l.color = col; l.spot_size = angle; l.spot_blend = blend; l.shadow_soft_size = r
    o = bpy.data.objects.new(name, l); coll("lights").objects.link(o); o.location = loc; o.rotation_euler = rot; return o

def probe(name, loc, r):
    try:
        bpy.ops.object.lightprobe_add(type="SPHERE", location=loc); o = bpy.context.active_object; o.name = name
        o.data.influence_distance = r; return o
    except Exception as e: print("probe", e)

def world_color(col, strength=1.0):
    sc = bpy.context.scene; w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = lin(col); bg.inputs[1].default_value = strength; return w

def haze_box(center, size, density, col=(1, 1, 1), aniso=0.5, name="haze", noise=0.0):
    o = box(name, center, size, c=coll("fx")); o.visible_shadow = False
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"])
    vs = N.new("ShaderNodeVolumeScatter"); vs.inputs["Color"].default_value = (*col, 1); vs.inputs["Anisotropy"].default_value = aniso
    if noise:
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = noise; nz.inputs["Detail"].default_value = 3
        mr = N.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.35; mr.inputs[2].default_value = 0.75; mr.inputs[3].default_value = density * 0.25; mr.inputs[4].default_value = density * 1.8
        L.new(nz.outputs[0], mr.inputs[0]); L.new(mr.outputs[0], vs.inputs["Density"])
    else: vs.inputs["Density"].default_value = density
    L.new(vs.outputs[0], N["Material Output"].inputs["Volume"]); o.data.materials.append(m)
    ee = bpy.context.scene.eevee; ee.volumetric_tile_size = os.environ.get("VTILE", "4"); ee.volumetric_samples = int(os.environ.get("VSAMP", 64))
    if hasattr(ee, "use_volumetric_shadows"): ee.use_volumetric_shadows = True
    return o

# ================================================================= SET A: Lobby + Aufzugkabine
# Kabine: x -1.1..1.1, y 6.0..8.0 (Tuer bei y = 6.0), z 0..2.6. Lobby: y -14..6.
CAB = dict(x0=-1.1, x1=1.1, y0=6.0, y1=8.0, h=2.6)
PANEL = dict(x=1.07, y=6.7, z=1.12)    # Tastenfeld an der rechten Kabinenwand (zeigt nach -x)
# Tastenfeld: 3 Spalten. Unten 22-30, dann verschraubte Blende (31-45), oben 46-60 lueckenlos.
BTN_DY, BTN_R = 0.075, 0.03
def _btn_layout():
    out = {}
    lo = [str(n) for n in range(22, 31)]; hi = [str(n) for n in range(46, 61)]
    for k, lab in enumerate(lo): out[lab] = (PANEL["y"] + BTN_DY - BTN_DY * (k % 3), 0.58 + 0.08 * (k // 3))
    for k, lab in enumerate(hi): out[lab] = (PANEL["y"] + BTN_DY - BTN_DY * (k % 3), 1.1 + 0.08 * (k // 3))
    return out
BTN = _btn_layout()
GAP_Z = (0.83, 1.05)
BUTTONS = [(lab, z) for lab, (y, z) in BTN.items()]   # Kompatibilitaet

def _marble(scale=0.35, tint=(1.0, 0.97, 0.93), rough=0.35, name=None):
    return pbr("marble_01", scale, tint, rough_mul=rough, bump=0.15, name=name)

def cabin(door_fn=None, frames=1, gold_back=True, c=None):
    """Goldene Kabine mit Tastenfeld. door_fn(f) -> Oeffnung 0..1 (1 = offen)."""
    c = c or coll("cabin"); g = gold("cab_gold", "a8742e", 0.34); g2 = gold("cab_gold_dark", "8a5a24", 0.32)
    x0, x1, y0, y1, h = CAB["x0"], CAB["x1"], CAB["y0"], CAB["y1"], CAB["h"]
    box("cab_floor", (0, (y0 + y1) / 2, -0.03), (x1 - x0, y1 - y0, 0.06), _marble(0.5, (0.95, 0.9, 0.85), 0.3, "cab_marble"), c=c)
    box("cab_ceil", (0, (y0 + y1) / 2, h + 0.03), (x1 - x0 + 0.1, y1 - y0, 0.06), g2, c=c)
    box("cab_light", (0, (y0 + y1) / 2, h - 0.005), (x1 - x0 - 0.5, y1 - y0 - 0.5, 0.01), emit("cab_led", "fff1d6", 3.0), c=c)
    area("cab_top", (0, (y0 + y1) / 2, h - 0.03), (0, 0, 0), 55, 1.4, (1, 0.9, 0.74), sy=1.2)
    for nm, cx, sx in (("cab_wl", x0 - 0.03, 0.06), ("cab_wr", x1 + 0.03, 0.06)):
        box(nm, (cx, (y0 + y1) / 2, h / 2), (sx, y1 - y0, h), g, c=c)
    box("cab_wb", (0, y1 + 0.03, h / 2), (x1 - x0 + 0.12, 0.06, h), principled("cab_back", "9a6a30", 0.62, 0.6), c=c)
    # Zierleisten + Handlauf
    for z in (0.95, 2.1):
        for nm, cx in (("l", x0 + 0.01), ("r", x1 - 0.01)): box(f"cab_strip_{nm}{z}", (cx, (y0 + y1) / 2, z), (0.03, y1 - y0, 0.03), g2, c=c)
        box(f"cab_strip_b{z}", (0, y1 - 0.01, z), (x1 - x0, 0.03, 0.03), g2, c=c)
    cyl("cab_rail", (0, y1 - 0.08, 0.92), 0.025, x1 - x0 - 0.3, gold("rail_gold", "ffd27a", 0.15), axis="X", c=c)
    # Front (Tuerseite) mit Rahmen
    for s in (-1, 1): box(f"cab_front{s}", (s * 0.85, y0 + 0.025, h / 2), (0.5, 0.05, h), g2, c=c)
    box("cab_front_top", (0, y0 + 0.025, 2.45), (2.2, 0.05, 0.3), g2, c=c)
    # Etagenanzeige ueber der Tuer (innen)
    box("cab_disp", (0, y0 + 0.01, 2.43), (0.36, 0.03, 0.14), principled("disp_black", "0a0a0c", 0.3), c=c)
    _buttons(c)
    probe("cab_probe", (0, 7.0, 1.4), 1.6)
    point("cab_fill", (0, 7.2, 2.2), 25, (1, 0.88, 0.7), r=0.5)
    return c

def _buttons(c):
    x, y = PANEL["x"], PANEL["y"]
    brass = principled("panel_bronze", "3a2a1c", 0.32, 0.85)
    z0, z1 = 0.44, 1.55
    box("panel_plate", (x, y, (z0 + z1) / 2), (0.02, 0.27, z1 - z0), brass, bevel=0.006, c=c)
    box("panel_frame", (x + 0.002, y, (z0 + z1) / 2), (0.018, 0.30, z1 - z0 + 0.03), gold("frame_gold", "f2c060", 0.2), bevel=0.004, c=c)
    blank = principled("panel_blank", "5a4430", 0.5, 0.7)
    ga, gb = GAP_Z; gm = (ga + gb) / 2
    box("panel_gap", (x - 0.012, y, gm), (0.006, 0.22, gb - ga), blank, bevel=0.003, c=c)   # Luecke 31-45: zugeschraubte Blende
    for dz in (-1, 1):
        for dy in (-0.085, 0.085): cyl(f"screw{dz}{dy}", (x - 0.016, y + dy, gm + dz * (gb - ga) * 0.36), 0.007, 0.006, principled("screw", "6a5a3a", 0.4, 1.0), axis="X", n=12, c=c)
    ink = principled("btn_txt", "120c08", 0.7)
    for lab, (by, bz) in BTN.items():
        cyl(f"btn_{lab}", (x - 0.016, by, bz), BTN_R, 0.014, principled("btn_gold", "e0b25e", 0.3, 0.7), axis="X", n=32, c=c)
        cyl(f"btn_ring_{lab}", (x - 0.011, by, bz), BTN_R + 0.007, 0.008, emit(f"btn_glow_{lab}", "ffb347", 0.0), axis="X", n=32, c=c)
        text(f"btn_txt_{lab}", lab, (x - 0.0235, by, bz - 0.001), 0.034, rot=(math.pi / 2, 0, -math.pi / 2), mat=ink, font=FONT_I, c=c)
    cyl("btn_alarm", (x - 0.016, y, 0.49), 0.024, 0.014, principled("alarm", "c0281e", 0.3), axis="X", c=c)

def glow_button(lab, f_on, strength=8.0):
    m = bpy.data.materials.get(f"btn_glow_{lab}")
    if not m: return
    e = m.node_tree.nodes["Emission"].inputs[1]
    e.default_value = 0.0; e.keyframe_insert("default_value", frame=f_on - 1)
    e.default_value = strength; e.keyframe_insert("default_value", frame=f_on)

def doors(door_fn, frames, y=6.08, c=None, name="door", w=1.2, h=2.3):
    """Zwei goldene Schiebetueren; door_fn(f) -> 0 zu .. 1 offen."""
    c = c or coll("set"); g = gold("door_gold", "d9a048", 0.2)
    L_ = []
    for s in (-1, 1):
        d = box(f"{name}{s}", (s * w / 4, y, h / 2), (w / 2, 0.04, h), g, bevel=0.004, c=c)
        # Zierfuge
        box(f"{name}{s}_line", (s * w / 4, y - 0.022, h / 2), (0.006, 0.004, h * 0.9), gold("door_line", "a8742a", 0.3), c=c).parent = d
        L_.append((s, d))
    for f in range(1, frames + 1):
        k = door_fn(f)
        for s, d in L_:
            d.location.x = s * (w / 4 + k * w / 2 * 0.98); d.keyframe_insert("location", index=0, frame=f)
    return L_

def lobby():
    c = coll("lobby")
    mar = _marble(0.12, (1.0, 0.97, 0.92), 0.12, "lobby_marble")
    dark = pbr("marble_tiles", 0.5, (0.42, 0.36, 0.32), rough_mul=0.35, bump=0.2, name="lobby_tiles")
    g = gold("lobby_gold", "e0a040", 0.25)
    # Boden (Marmor, Mittelbahn dunkler), Decke, Waende
    box("lobby_floor", (0, -4, -0.05), (14, 20, 0.1), mar, c=c)
    box("lobby_runner", (0, -3, 0.002), (2.6, 17, 0.004), dark, c=c)
    box("lobby_ceil", (0, -4, 6.05), (14, 20, 0.1), principled("ceil", "2a1e18", 0.6), c=c)
    wallm = _marble(0.2, (0.92, 0.86, 0.8), 0.4, "lobby_wallmarble")
    # Aufzugswand bei y = 6 mit drei Tueroeffnungen (x = -3, 0, 3)
    for cx, sx in ((-5.6, 3.6), (-1.6, 0.8 + 1.0), (1.6, 1.8), (5.6, 3.6)):
        pass
    segs = [(-7, -3.62), (-2.38, -0.62), (0.62, 2.38), (3.62, 7)]
    for i, (a, b) in enumerate(segs): box(f"lobby_ewall{i}", ((a + b) / 2, 5.95, 3), (b - a, 0.1, 6), wallm, c=c)
    for cx in (-3, 0, 3):
        box(f"lobby_lintel{cx}", (cx, 5.95, 4.15), (1.24, 0.1, 3.7), wallm, c=c)
        for s in (-1, 1): box(f"lobby_jamb{cx}{s}", (cx + s * 0.64, 5.98, 1.2), (0.06, 0.12, 2.4), g, bevel=0.01, c=c)
        box(f"lobby_head{cx}", (cx, 5.98, 2.36), (1.34, 0.12, 0.1), g, bevel=0.01, c=c)
        box(f"lobby_disp{cx}", (cx, 5.98, 2.62), (0.5, 0.04, 0.16), principled("disp_black", "0a0a0c", 0.3), c=c)
        if cx != 0:   # Nachbar-Aufzuege: geschlossene Goldtueren + Kabinenrueckwand
            for s in (-1, 1): box(f"lobby_door{cx}{s}", (cx + s * 0.3, 6.04, 1.15), (0.6, 0.04, 2.3), gold("door_gold", "d9a048", 0.2), bevel=0.004, c=c)
    for side in (-1, 1):
        box(f"lobby_side{side}", (side * 7.1, -4, 3), (0.2, 20, 6), wallm, c=c)
        # Saeulen
        for y in (-10, -5, 0, 4):
            col = cyl(f"lobby_col{side}{y}", (side * 5.3, y, 3), 0.42, 6, _marble(0.25, (0.95, 0.92, 0.88), 0.2, "col_marble"), c=c)
            for z in (0.12, 5.88): cyl(f"lobby_colring{side}{y}{z}", (side * 5.3, y, z), 0.5, 0.24, g, c=c)
        # Wandleuchten (warm, Bokeh)
        for y in (-12, -7.5, -2.5, 2):
            box(f"lobby_sconce{side}{y}", (side * 6.95, y, 2.8), (0.1, 0.3, 0.6), emit("sconce", "ffcf8a", 9.0), c=c)
            point(f"sconce_l{side}{y}", (side * 6.6, y, 2.8), 60, (1, 0.72, 0.42), r=0.2)
    box("lobby_back", (0, -14.1, 3), (14, 0.2, 6), wallm, c=c)
    # Kronleuchter
    for y in (-8, -2):
        try:
            ch = ph.place("Chandelier_01", (0, y, 4.0), 0, 1.6)
        except Exception as e: print("chandelier", e)
        point(f"chand_l{y}", (0, y, 4.6), 260, (1, 0.75, 0.45), r=0.4)
    # Goldene Deckenleisten
    for x in (-3.5, 3.5): box(f"lobby_ceilstrip{x}", (x, -4, 5.98), (0.12, 20, 0.04), emit("ceil_led", "ffc878", 5.0), c=c)
    # Grosse Pflanzen-Kuebel als Bokeh-Vordergrund
    for x, y in ((-4.2, 3.6), (4.2, 3.6)):
        cyl(f"pot{x}", (x, y, 0.45), 0.4, 0.9, principled("pot", "1c1a1e", 0.3), c=c)
        try: world.place("Bush_Large", (x, y, 0.9), 0.3 * x, 0.9)
        except Exception as e: print("bush", e)
    # Kabinenlicht faellt in die Lobby
    area("cab_spill", (0, 5.6, 2.3), (0, 0, 0), 140, 1.2, (1, 0.86, 0.62))
    area("lobby_key", (0, -5, 5.85), (0, 0, 0), 4200, 9, (1, 0.84, 0.64), sy=16)
    area("lobby_fill", (0, -12, 3), (math.radians(80), 0, 0), 900, 10, (1, 0.9, 0.78), sy=4)
    for y in (-11, -6, -1, 3.5):   # Deckenkassetten (leuchtend, warm)
        box(f"coffer{y}", (0, y, 5.97), (4.4, 2.6, 0.02), emit("coffer", "fff0d8", 2.2), c=c)
    probe("lobby_probe", (0, -2, 2.5), 9)
    return c

# ================================================================= SET B: Aufzugsschacht
FLOOR_H = 3.6
def fz(floor): return (floor - 1) * FLOOR_H          # Hoehe der Etage (Schacht-Koordinaten)
SHAFT = dict(x0=-1.6, x1=1.6, y0=-1.4, y1=2.0)

def shaft(cab_z, frames, f0=1, zmin=30, zmax=230, grille_z=118.0):
    """Schacht mit Beton, Fuehrungsschienen, Traegern pro Etage, Etagennummern (ohne 31-45), Lueftungsgitter.
    cab_z(t) -> Kabinenboden-Hoehe."""
    c = coll("shaft"); x0, x1, y0, y1 = SHAFT["x0"], SHAFT["x1"], SHAFT["y0"], SHAFT["y1"]
    con = pbr("concrete_wall_008", 0.35, (0.75, 0.8, 0.9), rough_mul=1.0, bump=0.8, name="shaft_con")
    H = zmax - zmin; zc = (zmin + zmax) / 2
    box("sh_wl", (x0 - 0.15, (y0 + y1) / 2, zc), (0.3, y1 - y0 + 0.6, H), con, c=c)
    box("sh_wb", (0, y1 + 0.15, zc), (x1 - x0 + 0.6, 0.3, H), con, c=c)
    box("sh_wf", (0, y0 - 0.15, zc), (x1 - x0 + 0.6, 0.3, H), con, c=c)
    # rechte Wand mit Gitteroeffnung
    gh = 1.3
    box("sh_wr_lo", (x1 + 0.15, (y0 + y1) / 2, (zmin + grille_z - gh / 2) / 2), (0.3, y1 - y0 + 0.6, grille_z - gh / 2 - zmin), con, c=c)
    box("sh_wr_hi", (x1 + 0.15, (y0 + y1) / 2, (grille_z + gh / 2 + zmax) / 2), (0.3, y1 - y0 + 0.6, zmax - grille_z - gh / 2), con, c=c)
    gy = 0.95
    box("sh_wr_a", (x1 + 0.15, (y0 + gy - gh / 2) / 2 - 0.15, grille_z), (0.3, (gy - gh / 2) - y0 + 0.3, gh), con, c=c)
    box("sh_wr_b", (x1 + 0.15, (gy + gh / 2 + y1) / 2 + 0.15, grille_z), (0.3, y1 - (gy + gh / 2) + 0.3, gh), con, c=c)
    steel = principled("sh_steel", "4a5260", 0.45, 0.9); dark = principled("sh_dark", "1a1d24", 0.6, 0.6)
    for k in range(7):   # Lamellen des Gitters (schraeg)
        b = box(f"grille{k}", (x1 + 0.12, gy, grille_z - gh / 2 + 0.1 + k * 0.18), (0.22, gh, 0.03), steel, c=c); b.rotation_euler = (0.0, -0.6, 0)
    box("grille_frame_t", (x1 + 0.02, gy, grille_z + gh / 2), (0.08, gh + 0.1, 0.06), steel, c=c)
    area("grille_light", (x1 + 2.5, gy, grille_z + 0.6), (0, math.radians(-75), 0), 900, 2.0, (0.65, 0.78, 1.0))
    box("grille_beyond", (x1 + 6, gy, grille_z), (0.1, 8, 8), emit("beyond", "7f9cc8", 1.2), c=c)
    box("grille_frame_b", (x1 + 0.02, gy, grille_z - gh / 2), (0.08, gh + 0.1, 0.06), steel, c=c)
    # Fuehrungsschienen (Kabine an x-Waenden), Gegengewicht-Schienen hinten
    for sx in (x0 + 0.08, x1 - 0.08):
        box(f"rail{sx}", (sx, -0.25, zc), (0.06, 0.12, H), steel, c=c)
    for sx in (-0.5, 0.5): box(f"cwrail{sx}", (sx, y1 - 0.12, zc), (0.08, 0.08, H), steel, c=c)
    yel = principled("sh_yellow", "e8b818", 0.5); white = emit("sh_paint", "f2f4f8", 1.2)
    for fl in range(1, 70):
        z = fz(fl)
        if z < zmin or z > zmax: continue
        box(f"beam{fl}", (0, y1 - 0.05, z + 0.2), (x1 - x0, 0.1, 0.25), dark, c=c)                       # Traeger hinten
        box(f"slab{fl}", (x0 + 0.02, (y0 + y1) / 2, z), (0.04, y1 - y0, 0.3), principled("sh_slab", "3a3e48", 0.8), c=c)
        void = 31 <= fl <= 45
        if void and fl % 2 == 0:
            box(f"vlamp{fl}", (x0 + 0.05, -0.9, z + 2.6), (0.08, 0.14, 0.24), emit("sh_lamp", "cfe2ff", 6.0), c=c)
            point(f"vlampl{fl}", (x0 + 0.3, 1.0, z + 2.4), 45, (0.55, 0.68, 1.0), r=0.3, shadow=False)
        if not void:
            box(f"stripe{fl}", (x0 + 0.005, 1.45, z + 0.9), (0.01, 1.0, 0.1), yel, c=c)
            t = text(f"num{fl}", str(fl), (x0 + 0.006, 1.45, z + 1.6), 0.95, rot=(math.pi / 2, 0, math.pi / 2), mat=white, font=FONT_I, c=c)
            # Arbeitsleuchte
            box(f"lamp{fl}", (x0 + 0.05, -0.9, z + 2.6), (0.08, 0.14, 0.24), emit("sh_lamp", "cfe2ff", 6.0), c=c)
            point(f"lampl{fl}", (x0 + 0.3, 1.0, z + 2.4), 60, (0.62, 0.75, 1.0), r=0.3, shadow=False)
    # "46" etwas groesser/heller (Ziel)
    # Kabine
    cab = coll("cab_ext"); root = bpy.data.objects.new("cab_root", None); cab.objects.link(root)
    ext = principled("cab_ext", "8a8f98", 0.35, 0.85)
    parts = [box("cab_body", (0, -0.25, 1.3), (2.6, 2.1, 2.8), ext, c=cab), box("cab_roof", (0, -0.25, 2.78), (2.7, 2.2, 0.08), dark, c=cab),
             box("cab_frame_l", (-1.32, -0.25, 1.6), (0.08, 0.16, 3.6), dark, c=cab), box("cab_frame_r", (1.32, -0.25, 1.6), (0.08, 0.16, 3.6), dark, c=cab),
             box("cab_cross", (0, -0.25, 3.4), (2.7, 0.18, 0.16), dark, c=cab), box("cab_sheave", (0, -0.25, 3.62), (0.7, 0.3, 0.3), steel, c=cab),
             box("cab_glow", (0, 0.86, 1.3), (2.3, 0.01, 0.05), emit("cab_seam", "ffc070", 30.0), c=cab),
             box("cab_glow2", (0, 0.86, 0.15), (2.3, 0.01, 0.04), emit("cab_seam", "ffc070", 30.0), c=cab)]
    for k in range(4): parts.append(cyl(f"cable{k}", (-0.3 + k * 0.2, -0.25, 3.7 + 60), 0.012, 120, dark, n=8, c=cab))
    for p_ in parts: p_.parent = root
    l1 = spot("cab_uplight", (0, -0.25, 3.0), (0, 0, 0), 900, math.radians(70), (1.0, 0.75, 0.45), r=0.3); l1.parent = root
    l2 = point("cab_back_glow", (0, 0.95, 1.3), 160, (1.0, 0.7, 0.4), r=0.4); l2.parent = root
    l3 = spot("cab_downlight", (0, -0.25, -0.1), (math.pi, 0, 0), 1200, math.radians(110), (1.0, 0.72, 0.42), r=0.4); l3.parent = root
    parts.append(box("cab_under", (0, -0.25, -0.02), (2.4, 1.9, 0.04), emit("cab_under", "ffb860", 8.0), c=cab)); parts[-1].parent = root
    for f in range(f0, f0 + frames):
        root.location = (0, 0, cab_z((f - 1) / 30)); root.keyframe_insert("location", frame=f)
    return c

# ================================================================= SET C: Betonhoehle (Technikgeschoss 31-45)
HALL = dict(x0=-16, x1=16, y0=-16, y1=16, h=50)
PIPES = [(1.2, 2.0), (3.4, 2.0)]
PIGEON = dict(x=3.2, y=5.7)

def copper():
    m = principled("copper", "d0763e", 0.32, 0.65); N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 5
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = lin("b05a2c"); rp.color_ramp.elements[1].color = lin("e89058")
    L.new(nz.outputs[0], rp.inputs[0]); L.new(rp.outputs[0], b.inputs["Base Color"]); return m

def billboard(name, img, width, loc, cam, c=None):
    """Vertikale Bildkarte, dreht sich um die Hochachse zur Kamera (2.5D-Requisit)."""
    o = sets.image_prop(img, width, img_dir=IMG); o.name = name; o.rotation_mode = "XYZ"; o.rotation_euler = (math.pi / 2, 0, 0)
    for cc in o.users_collection: cc.objects.unlink(o)
    (c or coll("set")).objects.link(o)
    bpy.context.view_layer.update(); o.data.transform(Matrix.Translation((0, o.dimensions.y / 2, 0)))   # Fuss am Ursprung
    o.location = loc
    con = o.constraints.new("LOCKED_TRACK"); con.target = cam; con.track_axis = "TRACK_Z"; con.lock_axis = "LOCK_Y"
    return o

def key_vis(o, f_on, f_off=None):
    o.hide_render = True; o.keyframe_insert("hide_render", frame=1)
    o.hide_render = False; o.keyframe_insert("hide_render", frame=f_on)
    if f_off: o.hide_render = True; o.keyframe_insert("hide_render", frame=f_off)

PIG_W, CHAIR_SEAT = 0.36, 0.17
def camp_chair(name, loc, yaw=0.0, c=None, s=1.0):
    """Tauben-Campingstuhl (Puppengroesse): Alu-Kreuzbeine, rot-weiss gestreifter Stoff, Lehne."""
    root = bpy.data.objects.new(name, None); (c or coll("set")).objects.link(root); root.location = loc; root.rotation_euler = (0, 0, yaw)
    alu = principled("alu", "c8ccd4", 0.3, 1.0); red = principled("chair_red", "e8352a", 0.7); wht = principled("chair_wht", "f4f1ea", 0.7)
    w, d, h = 0.2 * s, 0.17 * s, CHAIR_SEAT * s
    parts = []
    for k in range(4):   # Sitz: Streifen
        parts.append(box(f"{name}_seat{k}", (-w / 2 + w / 8 + k * w / 4, 0, h), (w / 4, d, 0.008), red if k % 2 == 0 else wht, c=c))
    for k in range(4):   # Lehne
        b = box(f"{name}_back{k}", (-w / 2 + w / 8 + k * w / 4, d / 2, h + 0.09 * s), (w / 4, 0.008, 0.16 * s), red if k % 2 == 0 else wht, c=c); b.rotation_euler = (-0.18, 0, 0); parts.append(b)
    for sx in (-1, 1):   # Kreuzbeine je Seite
        for a in (-1, 1):
            A, B_ = Vector((sx * w / 2, -a * d / 2, 0.0)), Vector((sx * w / 2, a * d / 2, h)); dv = B_ - A
            o = cyl(f"{name}_leg{sx}{a}", (A + B_) / 2, 0.006 * s, dv.length, alu, n=8, c=c); o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(dv); parts.append(o)
        o = cyl(f"{name}_up{sx}", (sx * w / 2, d / 2, h + 0.09 * s), 0.006 * s, 0.18 * s, alu, n=8, c=c); o.rotation_euler = (-0.18, 0, 0); parts.append(o)
        parts.append(cyl(f"{name}_arm{sx}", (sx * w / 2, 0, h + 0.06 * s), 0.006 * s, d, alu, axis="Y", n=8, c=c))
    for p_ in parts: p_.parent = root
    return root

def mini_tv(name, loc, yaw=0.0, c=None, s=1.0):
    """Winziger Roehrenfernseher (ca. 20 cm) mit Antenne; Bildschirm zeigt nach lokal -y."""
    root = bpy.data.objects.new(name, None); (c or coll("set")).objects.link(root); root.location = loc; root.rotation_euler = (0, 0, yaw)
    shell = principled("tv_shell", "d8c49a", 0.5); dark = principled("tv_dark", "1a1a1e", 0.4)
    parts = [box(f"{name}_body", (0, 0, 0.1 * s), (0.22 * s, 0.2 * s, 0.17 * s), shell, bevel=0.012 * s, c=c),
             box(f"{name}_back", (0, 0.13 * s, 0.1 * s), (0.15 * s, 0.08 * s, 0.12 * s), shell, bevel=0.01 * s, c=c),
             box(f"{name}_bezel", (-0.02 * s, -0.101 * s, 0.1 * s), (0.15 * s, 0.004, 0.12 * s), dark, c=c),
             box("tv_screen", (-0.02 * s, -0.104 * s, 0.1 * s), (0.13 * s, 0.004, 0.1 * s), emit("tv_scr", "9fd8ff", 6.0), c=c)]
    for k in range(2): parts.append(cyl(f"{name}_knob{k}", (0.075 * s, -0.103 * s, (0.13 - k * 0.05) * s), 0.012 * s, 0.01, dark, axis="Y", n=12, c=c))
    for a in (-1, 1):
        o = cyl(f"{name}_ant{a}", (a * 0.04 * s, 0.0, 0.25 * s), 0.003, 0.17 * s, principled("alu", "c8ccd4", 0.3, 1.0), n=6, c=c); o.rotation_euler = (0, a * 0.5, 0); parts.append(o)
    for p_ in parts: p_.parent = root
    return root

def cavern(cam, f0, f1, light=1.0):
    c = coll("cavern"); x0, x1, y0, y1, H = HALL["x0"], HALL["x1"], HALL["y0"], HALL["y1"], HALL["h"]
    floor = pbr("concrete_floor_02", 0.25, (0.7, 0.74, 0.82), rough_mul=1.0, bump=0.6, name="cav_floor")
    wallm = pbr("concrete_wall_008", 0.12, (0.6, 0.66, 0.78), rough_mul=1.0, bump=1.0, name="cav_wall")
    box("cav_floor", (0, 0, -0.15), (x1 - x0 + 2, y1 - y0 + 2, 0.3), floor, c=c)
    box("cav_ceil", (0, 0, H + 0.3), (x1 - x0 + 2, y1 - y0 + 2, 0.6), wallm, c=c)
    # Westwand mit Gitter (Kamera kommt aus dem Schacht)
    gz, gy, gh = 32.0, 0.0, 1.3
    box("cav_w_lo", (x0 - 0.3, 0, (gz - gh / 2) / 2), (0.6, y1 - y0, gz - gh / 2), wallm, c=c)
    box("cav_w_hi", (x0 - 0.3, 0, (gz + gh / 2 + H) / 2), (0.6, y1 - y0, H - gz - gh / 2), wallm, c=c)
    box("cav_w_a", (x0 - 0.3, (y0 + gy - gh / 2) / 2, gz), (0.6, (gy - gh / 2) - y0, gh), wallm, c=c)
    box("cav_w_b", (x0 - 0.3, (gy + gh / 2 + y1) / 2, gz), (0.6, y1 - gy - gh / 2, gh), wallm, c=c)
    steel = principled("cav_steel", "3c4350", 0.5, 0.9)
    for k in range(7):
        b = box(f"cgrille{k}", (x0 - 0.05, gy, gz - gh / 2 + 0.1 + k * 0.18), (0.22, gh, 0.03), steel, c=c); b.rotation_euler = (0, 0.6, 0)
    box("cgf_t", (x0 + 0.02, gy, gz + gh / 2), (0.1, gh + 0.12, 0.08), steel, c=c); box("cgf_b", (x0 + 0.02, gy, gz - gh / 2), (0.1, gh + 0.12, 0.08), steel, c=c)
    box("cav_n", (0, y1 + 0.3, H / 2), (x1 - x0 + 1.2, 0.6, H), wallm, c=c)
    # Ost- und Suedfassade: Lamellenbaender (offen) zwischen Betonbruestungen
    bands = [(6, 18), (24, 46)]
    slat = principled("louver", "2a3038", 0.5, 0.8)
    for side in ("E", "S"):
        zs = [0] + [z for b_ in bands for z in b_] + [H]
        for i in range(0, len(zs), 2):
            za, zb = zs[i], zs[i + 1]
            if side == "E": box(f"cav_E{i}", (x1 + 0.3, 0, (za + zb) / 2), (0.6, y1 - y0 + 1.2, zb - za), wallm, c=c)
            else: box(f"cav_S{i}", (0, y0 - 0.3, (za + zb) / 2), (x1 - x0 + 1.2, 0.6, zb - za), wallm, c=c)
        for (za, zb) in bands:
            n = int((zb - za) / 0.55)
            for k in range(n):
                z = za + 0.3 + k * 0.55
                if side == "E": s_ = box(f"lv_E{za}_{k}", (x1 + 0.1, 0, z), (0.4, y1 - y0, 0.05), slat, c=c); s_.rotation_euler = (0, -0.3, 0)
                else: s_ = box(f"lv_S{za}_{k}", (0, y0 - 0.1, z), (x1 - x0, 0.4, 0.05), slat, c=c); s_.rotation_euler = (0.3, 0, 0)
            # Pfosten
            for q in range(-16, 17, 4):
                if side == "E": box(f"post_E{za}{q}", (x1 + 0.1, q, (za + zb) / 2), (0.4, 0.3, zb - za), wallm, c=c)
                else: box(f"post_S{za}{q}", (q, y0 - 0.1, (za + zb) / 2), (0.3, 0.4, zb - za), wallm, c=c)
    # Himmel/Nachbarhaeuser hinter den Lamellen (hell -> Gegenlicht)
    for o in (box("sky_E", (x1 + 9, 0, 25), (0.2, 80, 70), emit("sky_card", "8fb4ff", 2.2), c=c), box("sky_S", (0, y0 - 9, 25), (80, 0.2, 70), emit("sky_card", "8fb4ff", 2.2), c=c)):
        o.visible_shadow = False
    # Wandpfeiler + Stahl-Diagonalen (Massstab)
    for q in (-8, 0, 8):
        box(f"pil_N{q}", (q, y1 - 0.4, H / 2), (1.2, 0.8, H), wallm, c=c)
        box(f"pil_W{q}", (x0 + 0.4, q, H / 2), (0.8, 1.2, H), wallm, c=c)
    beam = principled("cav_beam", "2c323c", 0.55, 0.85)
    for (a, b_) in (((-14, y1 - 1.0, 4), (-2, y1 - 1.0, 44)), ((-2, y1 - 1.0, 4), (-14, y1 - 1.0, 44)), ((2, y1 - 1.0, 4), (14, y1 - 1.0, 44)), ((14, y1 - 1.0, 4), (2, y1 - 1.0, 44))):
        A, B_ = Vector(a), Vector(b_); d = B_ - A
        o = box("brace", (A + B_) / 2, (0.7, 0.5, d.length), beam, c=c); o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    # Zwei Kupferrohre mit Flanschen + Ventil
    cu = copper()
    for i, (px, py) in enumerate(PIPES):
        cyl(f"pipe{i}", (px, py, H / 2), 0.34, H, cu, n=40, c=c)
        for z in range(2, int(H), 6): cyl(f"flange{i}_{z}", (px, py, z), 0.42, 0.12, cu, n=40, c=c)
        cyl(f"pipefoot{i}", (px, py, 0.15), 0.55, 0.3, principled("cav_foot", "2a2e36", 0.6, 0.6), n=32, c=c)
    cyl("valve_stem", (PIPES[0][0] + 0.4, PIPES[0][1], 1.1), 0.05, 0.4, principled("valve", "b82a22", 0.4, 0.6), axis="X", c=c)
    cyl("valve_wheel", (PIPES[0][0] + 0.62, PIPES[0][1], 1.1), 0.16, 0.04, principled("valve", "b82a22", 0.4, 0.6), axis="X", c=c)
    # Licht: kalter Mond-/Himmelsstrahl durch die Lamellen + warme Arbeitsleuchte an den Rohren
    sun = bpy.data.lights.new("cav_sun", "SUN"); sun.energy = 16.0 * light; sun.color = (0.6, 0.8, 1.0); sun.angle = 0.008
    so = bpy.data.objects.new("cav_sun", sun); coll("lights").objects.link(so); so.rotation_euler = (math.radians(55), 0, math.radians(50))
    for (x, y, z) in ((2.3, 0.2, 6.5), (-6, -4, 8), (7, 7, 8)):
        cyl(f"wlamp{x}", (x, y, z), 0.18, 0.25, emit("wlamp", "ffb15e", 12.0), n=16, c=c)
        cyl(f"wlamp_cable{x}", (x, y, z + 21.5), 0.01, 43, principled("cable_blk", "111111", 0.6), n=6, c=c)
        point(f"wlampl{x}", (x, y, z - 0.25), 1100 if x == 2.3 else 1400 * light, (1.0, 0.66, 0.34), r=0.2)
    area("cav_fill", (0, 0, 30), (0, 0, 0), 900 * light, 30, (0.45, 0.6, 1.0), shadow=False)
    point("grille_in", (x0 + 1.5, 0, 32), 400, (0.6, 0.75, 1.0), r=1.0, shadow=False)
    haze_box((0, 0, 25), (32, 32, 50), 0.022, (0.8, 0.9, 1.0), 0.6, name="cav_haze", noise=0.12)
    ee = bpy.context.scene.eevee; ee.volumetric_end = 120
    # Easter Egg: Taube auf Klappstuhl vor Mini-Roehrenfernseher, 50-m-Verlaengerungskabel
    px_, py_ = PIGEON["x"], PIGEON["y"]
    camp_chair("pchair", (px_, py_, 0), c=c)
    tvx, tvy = px_ + 0.55, py_ - 0.05
    mini_tv("ptv", (tvx, tvy, 0), -math.pi / 2, c=c)
    tvl = point("tv_light", (tvx - 0.3, tvy, 0.25), 18, (0.55, 0.8, 1.0), r=0.05)
    rnd = random.Random(4)
    for f in range(f0, f1 + 1, 2):   # Flackern
        k = 0.6 + 0.4 * rnd.random(); tvl.data.energy = 25 * k; tvl.data.keyframe_insert("energy", frame=f)
        e_ = bpy.data.materials["tv_scr"].node_tree.nodes["Emission"].inputs[1]; e_.default_value = 6 * k; e_.keyframe_insert("default_value", frame=f)
    pts = [(tvx + 0.1, tvy, 0.03), (tvx + 2, tvy - 1.5, 0.03), (tvx + 5, tvy + 1.5, 0.03), (tvx + 6.5, tvy - 4, 0.03), (tvx + 3, tvy - 9, 0.03),
           (tvx + 7, tvy - 13, 0.03), (x1 - 0.2, y0 + 3, 0.03), (x1 - 0.05, y0 + 3, 0.4)]
    cu_ = bpy.data.curves.new("cable", "CURVE"); cu_.dimensions = "3D"; sp = cu_.splines.new("BEZIER"); sp.bezier_points.add(len(pts) - 1)
    for bp, p_ in zip(sp.bezier_points, pts): bp.co = p_; bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu_.bevel_depth = 0.022; cu_.bevel_resolution = 3
    co = bpy.data.objects.new("cable", cu_); c.objects.link(co); cu_.materials.append(principled("cable_orange", "ff7a12", 0.45))
    box("socket", (x1 - 0.03, y0 + 3, 0.4), (0.06, 0.16, 0.2), principled("socket", "e8e4da", 0.4), c=c)
    pig = {}
    for k in ("tv", "toast", "remote"):
        pig[k] = billboard(f"pigeon_{k}", f"pigeon_{k}.png", PIG_W, (px_ - 0.03, py_, CHAIR_SEAT - 0.045), cam, c=c)
    return pig

# ================================================================= SET D: Skyline (Daemmerung), Roentgen-Turm, Kisten-Hebebuehne
TOWER = dict(w=24.0, fh=3.6)
def city_mat(name="city", haze="9fb2e0"):
    """Fassaden mit Fenstergitter (Brick-Textur), zufaellig erleuchtet, Luftperspektive ueber die Sichtweite."""
    if name in _M and name in bpy.data.materials: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    out = N["Material Output"]
    geo_ = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo_.outputs["Position"], sep.inputs[0])
    nsep = N.new("ShaderNodeSeparateXYZ"); L.new(geo_.outputs["Normal"], nsep.inputs[0])
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L.new(nsep.outputs[0], ab.inputs[0])
    gt = N.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5; L.new(ab.outputs[0], gt.inputs[0])
    mixu = N.new("ShaderNodeMix"); mixu.data_type = "FLOAT"; L.new(gt.outputs[0], mixu.inputs[0]); L.new(sep.outputs[0], mixu.inputs[2]); L.new(sep.outputs[1], mixu.inputs[3])
    cmb = N.new("ShaderNodeCombineXYZ"); L.new(mixu.outputs[0], cmb.inputs[0]); L.new(sep.outputs[2], cmb.inputs[1])
    br = N.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.9; br.inputs["Brick Width"].default_value = 2.6
    br.inputs["Row Height"].default_value = 3.6; br.offset = 0.0; br.squash = 1.0
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.3, 0.3, 0.3, 1); br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    L.new(cmb.outputs[0], br.inputs["Vector"])
    ca = N.new("ShaderNodeVertexColor"); ca.layer_name = "tint"
    win = N.new("ShaderNodeMath"); win.operation = "GREATER_THAN"; win.inputs[1].default_value = 0.05; L.new(br.outputs["Fac"], win.inputs[0])   # Mortar=0 -> Wand
    # Fenster leuchten zufaellig (Brick Color1/Color2-Variation)
    lit = N.new("ShaderNodeMath"); lit.operation = "GREATER_THAN"; lit.inputs[1].default_value = 0.62; L.new(br.outputs["Color"], lit.inputs[0])
    wl = N.new("ShaderNodeMath"); wl.operation = "MULTIPLY"; L.new(win.outputs[0], wl.inputs[0]); L.new(lit.outputs[0], wl.inputs[1])
    wall_col = N.new("ShaderNodeMix"); wall_col.data_type = "RGBA"; L.new(win.outputs[0], wall_col.inputs[0]); L.new(ca.outputs["Color"], wall_col.inputs[6]); wall_col.inputs[7].default_value = lin("1a2236")
    L.new(wall_col.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = lin("ffc27a"); em.inputs[1].default_value = 3.5
    add = N.new("ShaderNodeMixShader"); L.new(wl.outputs[0], add.inputs[0]); L.new(b.outputs[0], add.inputs[1]); L.new(em.outputs[0], add.inputs[2])
    cam = N.new("ShaderNodeCameraData"); mr = N.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 250; mr.inputs[2].default_value = 1600; mr.inputs[4].default_value = 0.85
    L.new(cam.outputs["View Distance"], mr.inputs[0])
    hz = N.new("ShaderNodeEmission"); hz.inputs[0].default_value = lin(haze); hz.inputs[1].default_value = 1.0
    fin = N.new("ShaderNodeMixShader"); L.new(mr.outputs[0], fin.inputs[0]); L.new(add.outputs[0], fin.inputs[1]); L.new(hz.outputs[0], fin.inputs[2])
    L.new(fin.outputs[0], out.inputs[0]); _M[name] = m; return m

def city(seed=3, extent=700, keep=None, near_max=62.0, cell=34, name="city"):
    """Viele Quader in EINEM Mesh. keep(x, y) -> False = Zelle freilassen. Nahe Bebauung <= near_max (unter dem gehobenen Wohnblock)."""
    rnd = random.Random(seed); bm = bmesh.new(); tints = []
    pal = ["8a8d96", "9a8f84", "6f7686", "a39a8c", "7c6f66", "8c96a8", "b0a690", "5f6676"]
    n = int(extent / cell)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            cx, cy = i * cell, j * cell
            if keep and not keep(cx, cy): continue
            if cy > 140 and abs(cx) < 260: continue          # Central Park (Norden)
            d = math.hypot(cx, cy)
            for k in range(rnd.choice((1, 2, 2, 3))):
                w = rnd.uniform(10, 22); dpt = rnd.uniform(10, 22)
                ox = rnd.uniform(-(cell - w) / 2 + 3, (cell - w) / 2 - 3); oy = rnd.uniform(-(cell - dpt) / 2 + 3, (cell - dpt) / 2 - 3)
                hmax = near_max if d < 160 else (95 if d < 360 else 190)
                h = rnd.uniform(18, hmax) * (1.0 if rnd.random() > 0.08 or d < 160 else 1.6)
                g = bmesh.ops.create_cube(bm, size=1.0)
                for v in g["verts"]: v.co = Vector((cx + ox + v.co.x * w, cy + oy + v.co.y * dpt, (v.co.z + 0.5) * h))
                tints.append((len(bm.faces), lin(rnd.choice(pal))))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ca = me.color_attributes.new("tint", "BYTE_COLOR", "CORNER")
    import bisect
    starts = [st_ for st_, _ in tints]
    for p in me.polygons:
        tcol = tints[max(0, bisect.bisect_right(starts, p.index) - 1)][1]
        for li in p.loop_indices: ca.data[li].color = tcol
    o = bpy.data.objects.new(name, me); coll("city").objects.link(o); me.materials.append(city_mat()); return o

def park(c=None):
    """Central Park: gruene Flaeche mit Baumkronen-Struktur + See."""
    m = principled("park", "2f6a2a", 0.9); N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.35
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = lin("1c4a1e"); rp.color_ramp.elements[1].color = lin("5f9a3a"); L.new(vo.outputs["Distance"], rp.inputs[0]); L.new(rp.outputs[0], b.inputs["Base Color"])
    bu = N.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = 0.8; L.new(vo.outputs["Distance"], bu.inputs["Height"]); L.new(bu.outputs[0], b.inputs["Normal"])
    box("park", (0, 520, 0.6), (520, 760, 1.2), m, c=c)
    box("lake", (-40, 420, 1.25), (160, 110, 0.1), principled("lake", "6c90c8", 0.08), c=c)

def ground_city(c=None):
    box("streets", (0, 0, -0.5), (3000, 3000, 1.0), principled("asphalt", "2a2c34", 0.8), c=c)

def crate_mat():
    return pbr("plywood", 0.12, (1.05, 0.82, 0.58), rough_mul=1.0, bump=0.5, name="crate_wood")

def crate(name, center, size, label="TECHNIK\n= 0 m² WOHNFLÄCHE", faces=("S", "E", "W"), c=None, label_size=None):
    o = box(name, center, size, crate_mat(), bevel=size[0] * 0.02, c=c)
    fr = principled("crate_frame", "6a4424", 0.7)
    sx, sy, sz = size; e = min(sx, sz) * 0.07
    for zz in (-sz / 2 + e / 2, sz / 2 - e / 2):   # Rahmenbretter
        box(name + f"_fh{zz:.1f}", (0, 0, zz), (sx * 1.01, sy * 1.01, e), fr, c=c).parent = o
    for xx in (-sx / 2 + e / 2, sx / 2 - e / 2):
        for yy in (-sy / 2 + e / 2, sy / 2 - e / 2):
            box(name + f"_fv{xx:.1f}{yy:.1f}", (xx, yy, 0), (e * 1.02, e * 1.02, sz * 1.01), fr, c=c).parent = o
    ink = principled("stencil", "151210", 0.9)
    ls = label_size or sx * 0.092
    for f_ in faces:
        if f_ == "S": t = text(name + "_lblS", label, (0, -sy / 2 - 0.02, 0), ls, rot=(math.pi / 2, 0, 0), mat=ink, font=FONT_B, c=c)
        elif f_ == "E": t = text(name + "_lblE", label, (sx / 2 + 0.02, 0, 0), ls, rot=(math.pi / 2, 0, math.pi / 2), mat=ink, font=FONT_B, c=c)
        elif f_ == "W": t = text(name + "_lblW", label, (-sx / 2 - 0.02, 0, 0), ls, rot=(math.pi / 2, 0, -math.pi / 2), mat=ink, font=FONT_B, c=c)
        t.parent = o
    return o

def gold_block(name, w, h, c=None, fh=3.6):
    """Goldener Wohnblock: warm leuchtende Fensterbaender + Goldrahmen."""
    c = c or coll("tower"); root = bpy.data.objects.new(name, None); c.objects.link(root)
    g = gold("blk_gold", "c88a2e", 0.3)
    core = box(name + "_core", (0, 0, h / 2), (w - 0.6, w - 0.6, h), emit("blk_glow", "ffb35c", 1.15), c=c); core.parent = root
    n = int(round(h / fh))
    for k in range(n + 1):
        b = box(name + f"_slab{k}", (0, 0, k * fh), (w, w, 0.5), g, c=c); b.parent = root
    for xx in (-w / 2, w / 2):
        for yy in (-w / 2, w / 2):
            b = box(name + f"_col{xx}{yy}", (xx, yy, h / 2), (0.8, 0.8, h), g, c=c); b.parent = root
    for k in range(-3, 4):   # Fassadenpfosten
        for side in (-1, 1):
            b = box(name + f"_mx{k}{side}", (k * w / 7, side * w / 2, h / 2), (0.25, 0.25, h), g, c=c); b.parent = root
            b = box(name + f"_my{k}{side}", (side * w / 2, k * w / 7, h / 2), (0.25, 0.25, h), g, c=c); b.parent = root
    return root

def glass_shell(name, w, h, c=None):
    c = c or coll("tower")
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.25
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = lin("8fd4ff"); em.inputs[1].default_value = 1.6
    tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader"); L.new(lw.outputs["Facing"], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
    val = N.new("ShaderNodeValue"); val.name = "alpha"; val.outputs[0].default_value = 1.0
    tr2 = N.new("ShaderNodeBsdfTransparent"); mx2 = N.new("ShaderNodeMixShader"); L.new(val.outputs[0], mx2.inputs[0]); L.new(tr2.outputs[0], mx2.inputs[1]); L.new(mx.outputs[0], mx2.inputs[2])
    L.new(mx2.outputs[0], N["Material Output"].inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    o = box(name, (0, 0, h / 2), (w + 0.4, w + 0.4, h), m, c=c); o.visible_shadow = False
    return o, val


# ================================================================= SET E: Penthouse + Hoehle darunter
PH_Z = 106.0
def penthouse(door_fn, frames, cam):
    c = coll("penthouse"); z0 = PH_Z
    mar = _marble(0.15, (1.0, 0.97, 0.93), 0.12, "ph_marble")
    # Boden mit Glasfeld (x 0.2..3.2, y 0.8..3.4)
    gx0, gx1, gy0, gy1 = 0.2, 3.2, 0.8, 3.4
    for nm, cx, cy, sx, sy in (("a", -3.4, 5, 7.2, 10), ("b", 4.6, 5, 2.8, 10), ("c", 1.7, 0.4, 3.0, 0.8), ("d", 1.7, 6.7, 3.0, 6.6)):
        box("ph_floor_" + nm, (cx, cy, z0 - 0.15), (sx, sy, 0.3), mar, c=c)
    glass = principled("ph_glassfloor", "cfe8ff", 0.05, 0.0, alpha=0.18)
    box("ph_glassfloor", ((gx0 + gx1) / 2, (gy0 + gy1) / 2, z0 - 0.02), (gx1 - gx0, gy1 - gy0, 0.04), glass, c=c).visible_shadow = False
    g = gold("ph_gold", "d9a048", 0.25)
    for nm, lc, sz in (("n", ((gx0 + gx1) / 2, gy1, z0), (gx1 - gx0 + 0.08, 0.04, 0.02)), ("s", ((gx0 + gx1) / 2, gy0, z0), (gx1 - gx0 + 0.08, 0.04, 0.02)),
                       ("w", (gx0, (gy0 + gy1) / 2, z0), (0.04, gy1 - gy0, 0.02)), ("e", (gx1, (gy0 + gy1) / 2, z0), (0.04, gy1 - gy0, 0.02))):
        box("ph_gf_" + nm, lc, sz, g, c=c)
    box("ph_ceil", (0, 5, z0 + 3.6), (12, 10, 0.2), principled("ph_ceil", "f2ede4", 0.8), c=c)
    wallm = principled("ph_wall", "c9b8a2", 0.7)
    # Nordwand mit Aufzugsoeffnung (x -0.7..0.7, Hoehe 2.4)
    for nm, cx, sx in (("w", -3.375, 5.25), ("e", 3.375, 5.25)): box("ph_wall_n" + nm, (cx, 10.1, z0 + 1.8), (sx, 0.2, 3.6), wallm, c=c)
    box("ph_wall_nt", (0, 10.1, z0 + 3.0), (1.5, 0.2, 1.2), wallm, c=c)
    box("ph_wall_e", (6.1, 5, z0 + 1.8), (0.2, 10, 3.6), wallm, c=c)
    # Glasfront Sued + West: Scheiben, Goldpfosten, Handlauf
    pane = principled("ph_pane", "dfeeff", 0.02, 0.0, alpha=0.1)
    o = box("ph_glass_s", (0, -0.02, z0 + 1.8), (12, 0.02, 3.6), pane, c=c); o.visible_shadow = False
    o = box("ph_glass_w", (-6.02, 5, z0 + 1.8), (0.02, 10, 3.6), pane, c=c); o.visible_shadow = False
    for x in range(-6, 7, 2): box(f"ph_mul_s{x}", (x, 0, z0 + 1.8), (0.06, 0.08, 3.6), g, c=c)
    for y in range(0, 11, 2): box(f"ph_mul_w{y}", (-6, y, z0 + 1.8), (0.08, 0.06, 3.6), g, c=c)
    cyl("ph_rail_s", (0, 0.08, z0 + 1.0), 0.02, 12, g, axis="X", n=12, c=c)
    cyl("ph_rail_w", (-5.92, 5, z0 + 1.0), 0.02, 10, g, axis="Y", n=12, c=c)
    box("ph_sill_s", (0, 0.05, z0 + 0.04), (12, 0.12, 0.08), g, c=c); box("ph_sill_w", (-5.95, 5, z0 + 0.04), (0.12, 10, 0.08), g, c=c)
    # Aufzug: Goldrahmen, Kabine dahinter, Schiebetueren in der Wandoeffnung
    for nm, lc, sz in (("l", (-0.74, 9.98, z0 + 1.22), (0.08, 0.06, 2.44)), ("r", (0.74, 9.98, z0 + 1.22), (0.08, 0.06, 2.44)), ("t", (0, 9.98, z0 + 2.44), (1.56, 0.06, 0.08))):
        box("ph_jamb_" + nm, lc, sz, g, c=c)
    cg = gold("cab_gold", "a8742e", 0.34)
    for s_ in (-1, 1): box(f"ph_lift_in{s_}", (s_ * 0.73, 10.9, z0 + 1.3), (0.06, 1.4, 2.6), cg, c=c)
    box("ph_lift_back", (0, 11.6, z0 + 1.3), (1.5, 0.06, 2.6), cg, c=c)
    box("ph_lift_floor", (0, 10.9, z0 - 0.02), (1.5, 1.4, 0.04), mar, c=c)
    box("ph_lift_ceil", (0, 10.9, z0 + 2.45), (1.5, 1.4, 0.04), gold("cab_gold_dark", "8a5a24", 0.32), c=c)
    box("ph_lift_light", (0, 10.9, z0 + 2.42), (1.0, 1.0, 0.01), emit("cab_led", "fff1d6", 3.0), c=c)
    point("ph_lift_l", (0, 10.9, z0 + 2.1), 60, (1, 0.85, 0.6))
    dl = []
    for s_ in (-1, 1):
        d = box(f"ph_door{s_}", (s_ * 0.35, 10.1, z0 + 1.2), (0.7, 0.04, 2.4), gold("door_gold", "d9a048", 0.2), c=c); dl.append((s_, d))
    for f in range(1, frames + 1):
        k = door_fn(f)
        for s_, d in dl: d.location.x = s_ * (0.35 + k * 0.7 * 0.98); d.keyframe_insert("location", index=0, frame=f)
    # Einrichtung (Poly Haven, CC0)
    box("ph_rug", (3.3, 5.6, z0 + 0.008), (3.0, 4.0, 0.016), principled("rug", "d9c7a4", 0.95), c=c)
    def put(aid, loc, rz=0.0, sc=1.0):
        try: return ph.place(aid, loc, rz, sc, coll=c)
        except Exception as e: print("ph", aid, e)
    put("sofa_03", (5.2, 5.6, z0), -math.pi / 2)
    put("throw_pillows_01", (5.25, 5.6, z0 + 0.45), -math.pi / 2)
    put("modern_coffee_table_01", (3.6, 5.6, z0), 0.0)
    put("modern_arm_chair_01", (2.4, 8.0, z0), math.radians(-140))
    put("dining_table", (-3.6, 6.4, z0), 0.0)
    for dx, rz in ((-0.55, 0.0), (0.55, 0.0)):
        put("dining_chair_02", (-3.6 + dx, 5.55, z0), rz); put("dining_chair_02", (-3.6 + dx, 7.25, z0), math.pi)
    put("Chandelier_03", (-3.6, 6.4, z0 + 2.4), 0.0, 1.0)
    put("side_table_tall_01", (-2.1, 9.55, z0)); put("marble_bust_01", (-2.1, 9.55, z0 + 0.8), math.pi, 1.0)
    put("potted_plant_04", (1.5, 9.45, z0), 0.6, 1.5); put("potted_plant_02", (5.4, 9.3, z0), 0.0, 1.4); put("potted_plant_04", (-5.3, 9.3, z0), 0.0, 1.5); put("potted_plant_02", (5.3, 0.7, z0), 1.0, 1.3)
    o = put("hanging_picture_frame_02", (3.4, 9.98, z0 + 1.2), math.pi, 1.6)
    point("ph_warm", (0, 5, z0 + 3.2), 140, (1.0, 0.78, 0.55), r=1.0)
    point("ph_lamp_din", (-3.6, 6.4, z0 + 1.9), 60, (1.0, 0.72, 0.45), r=0.3)
    # Hoehle darunter (Technikgeschoss): Beton, Kiste, Taube, TV
    hz0 = z0 - 14
    con = pbr("concrete_wall_008", 0.15, (0.55, 0.58, 0.64), name="ph_cav_wall")
    box("cav2_floor", (0, 5, hz0 - 0.2), (12, 10, 0.4), pbr("concrete_floor_02", 0.25, (0.6, 0.62, 0.68), name="ph_cav_floor"), c=c)
    box("cav2_wall_n", (0, 9.8, hz0 + 6.9), (11.6, 0.3, 13.8), con, c=c); box("cav2_wall_e", (5.8, 5, hz0 + 6.9), (0.3, 9.6, 13.8), con, c=c)
    box("cav2_wall_w", (-5.8, 5, hz0 + 6.9), (0.3, 9.6, 13.8), con, c=c); box("cav2_wall_s", (0, 0.25, hz0 + 6.9), (11.6, 0.3, 13.8), con, c=c)
    crate("cav2_crate", (1.9, 3.4, hz0 + 0.55), (1.5, 1.1, 1.1), label="ETAGE 31–45\nBESITZER: TAUBE", faces=("S",), c=c, label_size=0.11)
    mini_tv("cav2_tv", (2.35, 3.35, hz0 + 1.1), -math.pi / 4, c=c)
    point("cav2_tv", (2.1, 3.0, hz0 + 1.3), 12, (0.55, 0.8, 1.0), r=0.05)
    area("cav2_grey", (1.5, 0, hz0 + 10), (0, 0, 0), 300, 6, (0.75, 0.8, 0.9))
    pig = billboard("pigeon_end", "pigeon_remote.png", 0.5, (1.55, 3.4, hz0 + 1.1 - 0.06), cam, c=c)
    return c
