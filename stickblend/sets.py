"""Wiederverwendbare Sets und Requisiten. Positionen in three-Achsen (x rechts, y oben, z zur Kamera), Umrechnung per tb()."""
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, Quaternion, Euler
from . import world, mats, geo, character
from .geo import tb

def _pmat(name, hexc, rough=0.85, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = mats.lin(hexc); b.inputs["Roughness"].default_value = rough
    if emit: b.inputs["Emission Color"].default_value = mats.lin(hexc); b.inputs["Emission Strength"].default_value = emit
    return m

def _emit(name, hexc, strength=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; N.remove(N["Principled BSDF"])
    e = N.new("ShaderNodeEmission"); e.inputs[0].default_value = mats.lin(hexc); e.inputs[1].default_value = strength
    m.node_tree.links.new(e.outputs[0], N["Material Output"].inputs[0]); return m

def _prim(kind, loc, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, name=None, **kw):
    getattr(bpy.ops.mesh, "primitive_" + kind + "_add")(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object; o.scale = scale
    if name: o.name = name
    if mat: o.data.materials.append(mat)
    return o

# ---------------------------------------------------------------- Stimmungen
MOODS = {
    "day": dict(top="8fc3ea", horizon="f6e3b8", sky=1.1, sun=((58, 0, 162), 4.5, (1.0, 0.88, 0.7)), fill=0.6, haze=0.006, hazec=(1.0, 0.9, 0.75),
                ground=("5f7d3c", "47622c"), tint=(1.0, 0.97, 0.92), rim=(0.85, (1.0, 0.86, 0.62), (-0.3, 0.75, 0.6))),
    "dusk": dict(top="5a5a8a", horizon="f29a6a", sky=0.9, sun=((80, 0, 150), 3.2, (1.0, 0.55, 0.32)), fill=0.35, haze=0.01, hazec=(1.0, 0.7, 0.55),
                 ground=("5a5a34", "40442a"), tint=(1.0, 0.8, 0.72), rim=(1.0, (1.0, 0.6, 0.35), (-0.2, 0.85, 0.3))),
    "night": dict(top="0a1230", horizon="1e2c4c", sky=0.55, sun=((45, 0, -40), 0.45, (0.6, 0.7, 1.0)), fill=0.0, haze=0.008, hazec=(0.5, 0.6, 0.9),
                  ground=("2c3e2a", "1e2c20"), tint=(0.55, 0.62, 0.85), rim=(0.6, (0.6, 0.75, 1.0), (0.4, 0.5, 0.75))),
}

def mood(name):
    M = MOODS[name]
    world.sky(top=M["top"], horizon=M["horizon"], strength=M["sky"], haze=M["haze"], haze_color=M["hazec"])
    world.sun(M["sun"][0], energy=M["sun"][1], color=M["sun"][2])
    if M["fill"]:
        f = bpy.data.lights.new("fill", "SUN"); f.energy = M["fill"]; f.color = (0.75, 0.85, 1.0)
        fo = bpy.data.objects.new("fill", f); bpy.context.scene.collection.objects.link(fo); fo.rotation_euler = (math.radians(60), 0, math.radians(-20))
    mats.set_scene_light(tint=M["tint"], rim_strength=M["rim"][0], rim_color=M["rim"][1], rim_dir=M["rim"][2])
    return M

# ---------------------------------------------------------------- Dschungel
def jungle(mode="day", seed=1, subjects=(), cam_path=(), clearing=2.6, dense=1.0):
    """subjects / cam_path in three-Achsen. Lichtung um die Figuren, Sichtlinien frei."""
    M = mood(mode); world.ground(M["ground"][0], 90, M["ground"][1])
    S = [tb(s) for s in subjects] or [Vector((0, 4, 1))]; C = [tb(c) for c in cam_path] or [Vector((0, -2, 1.3))]
    avoid = world.keep_clear(C, S, radius=0.8, near=1.4)
    avoid_tree = world.keep_clear(C, S, radius=2.6, near=3.0)   # Palmkronen sind ~2.5 m breit
    cx = sum(s.x for s in S) / len(S); cy = sum(s.y for s in S) / len(S)
    clear = lambda x, y: math.hypot(x - cx, y - cy) < clearing
    env = bpy.data.collections.new("env"); bpy.context.scene.collection.children.link(env)
    ymin = min(c.y for c in C) - 3
    world.scatter(["PalmTree_1", "PalmTree_2", "PalmTree_3", "PalmTree_4", "PalmTree_5"], int(30 * dense), (cx - 16, cx + 16, ymin, cy + 24), lambda x, y: clear(x, y) or avoid_tree(x, y), (1.5, 2.3), seed, env)
    world.scatter(["NormalTree_1", "NormalTree_3", "NormalTree_5"], int(8 * dense), (cx - 20, cx + 20, cy + 8, cy + 30), None, (1.6, 2.2), seed + 1, env)
    world.scatter(["Bush_Large", "Bush", "Bush_Small", "Bush_Flowers"], int(36 * dense), (cx - 10, cx + 10, ymin, cy + 16), lambda x, y: clear(x, y) and abs(x - cx) < clearing * 0.8 or avoid(x, y), (0.8, 1.5), seed + 2, env)
    world.scatter(["Plant_1", "Plant_2", "Grass_Large", "Grass_Small", "Flower_3_Clump", "Plant_Flowers"], int(130 * dense), (cx - 9, cx + 9, ymin, cy + 12), avoid, (0.7, 1.4), seed + 3, env)
    world.scatter(["Rock_1", "Rock_2", "Rock_4"], 8, (cx - 8, cx + 8, ymin + 2, cy + 12), lambda x, y: clear(x, y) or avoid(x, y), (0.5, 1.0), seed + 4, env)
    if mode == "night": fireflies((cx, cy), 30, seed)
    return env

def fireflies(center, n=30, seed=1):
    rnd = random.Random(seed); m = _emit("firefly", "eaff9a", 6.0)
    for i in range(n):
        o = _prim("uv_sphere", (center[0] + rnd.uniform(-5, 5), center[1] + rnd.uniform(-1, 9), rnd.uniform(0.4, 2.6)), (0.025,) * 3, mat=m, segments=8, ring_count=6)
        o.visible_shadow = False
        for f in range(1, 400, 20):
            o.location.z += rnd.uniform(-0.08, 0.08); o.location.x += rnd.uniform(-0.08, 0.08); o.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- Strand
def beach(sunset=False, subjects=(), cam_path=()):
    if sunset:
        world.sky(top="3d4f8a", horizon="f6a070", strength=1.0, haze=0.004, haze_color=(1.0, 0.75, 0.6)); world.sun((84, 0, 175), 3.0, (1.0, 0.62, 0.38))
        mats.set_scene_light(tint=(1.0, 0.86, 0.78), rim_strength=1.0, rim_color=(1.0, 0.62, 0.35), rim_dir=(0, 0.9, 0.3))
    else:
        world.sky(top="3f86d6", horizon="a9d4f2", strength=1.0, haze=0.002, haze_color=(0.9, 0.95, 1.0)); world.sun((45, 0, 150), 4.5, (1.0, 0.95, 0.85))
        mats.set_scene_light(tint=(1.0, 0.98, 0.95), rim_strength=0.6, rim_color=(1.0, 0.95, 0.8), rim_dir=(-0.3, 0.7, 0.6))
    world.ground("e6cf95", 120, "d8bb7c")
    sea = _prim("plane", (0, 220, 0.02), (1, 1, 1), mat=_pmat("sea", "4a6aa8" if sunset else "2f9fd0", 0.15), size=400); sea.visible_shadow = False  # beginnt bei y=20 (Wasserlinie)
    foam = _prim("plane", (0, 20.3, 0.03), (60, 0.25, 1), mat=_emit("foam", "ffffff", 0.9), size=1); foam.visible_shadow = False
    for f in range(1, 400, 30):
        foam.location.y = 20.3 + 0.4 * math.sin(f / 30 * 1.2); foam.keyframe_insert("location", frame=f)
    S = [tb(s) for s in subjects] or [Vector((0, 3, 1))]; C = [tb(c) for c in cam_path] or [Vector((0, -2, 1.3))]
    avoid = world.keep_clear(C, S, radius=0.9, near=1.6); avoid_tree = world.keep_clear(C, S, radius=2.6, near=3.0)
    env = bpy.data.collections.new("env"); bpy.context.scene.collection.children.link(env)
    for i, x in enumerate([-7, -4.8, 6, 8.5, -2.8, 3.6, -11, 12]):
        y = 3 + i * 1.7
        if not avoid_tree(x, y): world.place(["PalmTree_1", "PalmTree_3", "PalmTree_2", "PalmTree_4"][i % 4], (x, y, 0), i * 1.3, 1.6 + (i % 3) * 0.3, env)
    world.scatter(["Rock_1", "Rock_2", "Grass_Large", "Bush_Small"], 14, (-9, 9, 0, 16), avoid, (0.5, 1.0), 9, env)
    return env

# ---------------------------------------------------------------- Insel aus der Luft
def island():
    world.sky(top="3a7fd0", horizon="e9f7ff", strength=1.2); world.sun((40, 0, 30), 4.0, (1, 0.96, 0.88))
    _prim("plane", (0, 0, 0), mat=_pmat("ocean", "2f8fc9", 0.2), size=900)
    sand = _prim("cylinder", (0, 0, 0.3), (30, 16.5, 0.3), mat=_pmat("sand", "e9d39a"), vertices=64)
    rnd = random.Random(4); g = [_pmat("isl%d" % k, c) for k, c in enumerate(("2f7a3a", "3d8f45", "2a6a3a"))]
    for i in range(16):
        _prim("uv_sphere", (rnd.uniform(-20, 20), rnd.uniform(-10, 10), 1.5), (1, 1, 0.55), mat=g[i % 3], radius=rnd.uniform(5, 10))
    for k in range(3):
        r = _prim("torus", (0, 0, 0.05 + k * 0.01), (1, 0.55, 1), mat=_emit("surf%d" % k, "e8f6ff", 0.8), major_radius=31 + k * 3, minor_radius=0.4, major_segments=96)
    for i in range(10):
        c = Vector((rnd.uniform(-60, 60), rnd.uniform(-60, 60), 32 + rnd.uniform(0, 10)))
        for k in range(3): _prim("uv_sphere", c + Vector((k * 4 - 4, 0, math.sin(k) * 1.5)), mat=_pmat("cloud", "ffffff", 1.0), radius=4 - abs(k - 1))

# ---------------------------------------------------------------- Mond
def moon():
    sc = bpy.context.scene; w = bpy.data.worlds.new("space"); sc.world = w; w.use_nodes = True
    N = w.node_tree.nodes; L = w.node_tree.links; bg = N["Background"]
    vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 180; ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (1, 1, 1, 1); ramp.color_ramp.elements[1].position = 0.025; ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    L.new(vor.outputs["Distance"], ramp.inputs[0]); L.new(ramp.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.5
    world.sun((60, 0, -70), 4.5, (1, 1, 1))
    mats.set_scene_light(tint=(1, 1, 1), rim_strength=0.0)
    world.ground("9a9aa0", 300, "7a7a80")
    rnd = random.Random(5); dm = _pmat("crater", "6a6a70")
    for i in range(14):
        _prim("cylinder", tb(((rnd.random() - 0.5) * 30, 0.01, -2 - rnd.random() * 30)), (1, 1, 0.01), mat=dm, radius=0.6 + rnd.random() * 1.8, depth=1, vertices=32)
    _prim("uv_sphere", tb((-14, 18, -70)), mat=_pmat("earth", "3a7fd0", 0.6, 0.3), radius=7)
    _prim("uv_sphere", tb((-12.5, 19.5, -64)), mat=_pmat("land", "4aa65a", 0.6, 0.3), radius=2.5)
    # Landefaehre (stilisiert)
    root = bpy.data.objects.new("lander", None); sc.collection.objects.link(root); root.location = tb((1.2, 0, -5)); root.rotation_euler = (0, 0, 0.5)
    gold, sil = _pmat("gold", "e0b043", 0.35), _pmat("silver", "c9ccd6", 0.4)
    parts = [("cube", (0, 0, 1.2), (0.8, 0.8, 0.4), gold), ("cube", (0, 0, 2.0), (0.6, 0.55, 0.45), sil), ("cube", (0.3, -0.56, 2.1), (0.15, 0.01, 0.12), _pmat("win", "1a2230", 0.2))]
    for k, (kind, loc, s, m) in enumerate(parts):
        o = _prim(kind, loc, s, mat=m); o.parent = root
    for a, b in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        o = _prim("cylinder", (a * 0.9, -b * 0.9, 0.6), (1, 1, 1), (b * 0.35, a * 0.35, 0), sil, radius=0.05, depth=1.4); o.parent = root

# ---------------------------------------------------------------- Lager mit Feuer und Jahreskerben
def campfire(at=(0, 0, 0), years=None, frames=200):
    """years = [(frame_ab, "1946"), ...] erscheinen nacheinander auf dem Baumstamm."""
    p = tb(at); sc = bpy.context.scene
    L = bpy.data.lights.new("fire", "POINT"); L.color = (1.0, 0.55, 0.25); L.shadow_soft_size = 0.15
    lo = bpy.data.objects.new("fire", L); sc.collection.objects.link(lo); lo.location = p + Vector((0, 0, 0.6))
    for f in range(1, frames + 1, 2):
        t = f / 30; fl = 0.85 + 0.15 * math.sin(t * 17) * math.sin(t * 7.3); L.energy = 160 * fl; L.keyframe_insert("energy", frame=f)
    wood = _pmat("log", "5a3a24")
    for k in range(3): _prim("cylinder", p + Vector((0, 0, 0.08)), (1, 1, 1), (math.pi / 2, 0, k * 1.05), wood, radius=0.07, depth=0.9)
    flames = []
    for k, c in enumerate(("ff5a1e", "ff8a2e", "ffc23d", "fff0a0")):
        o = _prim("cone", p + Vector((math.sin(k * 1.6) * 0.08, math.cos(k * 1.6) * 0.08, 0.3 + k * 0.03)), mat=_emit("flame%d" % k, c, 4.0 + k), radius1=0.18 - k * 0.03, depth=0.6, vertices=8)
        o.visible_shadow = False; flames.append(o)
        for f in range(1, frames + 1, 2):
            t = f / 30; fl = 0.85 + 0.15 * math.sin(t * 17 + k) * math.sin(t * 7.3 + k); o.scale = (1, 1, fl * (1 - k * 0.15)); o.keyframe_insert("scale", frame=f)
    # Stamm mit Kerben + Plane, Kisten
    trunk = _prim("cylinder", p + tb((1.6, 2.5, -1.2)) - tb((0, 0, 0)), (1, 1, 1), mat=_pmat("trunk", "6b4a32"), radius=0.32, depth=5)
    tarp = _prim("plane", p + tb((-1.2, 1.1, -1.0)), (1.2, 0.8, 1), (math.radians(73), 0.1, 0.6), _pmat("tarp", "5f6b3a"), size=2)
    world.place("Rock_2", p + tb((-1.7, 0, -1.6)), 0.4, 0.5); world.place("Rock_1", p + tb((-2.3, 0, -1.0)), 1.2, 0.45)
    if years:
        tm = _emit("carve", "e9d3a8", 0.9)
        for k, (fa, txt) in enumerate(years):
            bpy.ops.object.text_add(location=p + tb((1.6, 2.15 - k * 0.24, -0.86))); o = bpy.context.active_object
            o.data.body = txt; o.data.size = 0.16; o.data.align_x = "CENTER"; o.rotation_euler = (math.pi / 2, 0, 0); o.data.materials.append(tm)
            o.hide_render = True; o.keyframe_insert("hide_render", frame=1); o.hide_render = False; o.keyframe_insert("hide_render", frame=max(1, fa))
    return lo

# ---------------------------------------------------------------- Dorf (Kenney Pirate-Huetten), Rauch
def village(models=None):
    if models is None:
        from . import paths
        models = os.environ.get("STICKBLEND_MODELS_DIR", paths.KENNEY_PIRATE)
    def imp(name, loc, rot, s):
        bpy.ops.import_scene.gltf(filepath=os.path.join(models, name + ".glb"))
        for o in bpy.context.selected_objects:
            if o.parent is None: o.location = loc; o.rotation_euler = (0, 0, rot); o.scale = (s, s, s)
    for x, z, r in ((-2.8, -8.5, 0.6), (2.6, -10.5, -0.5), (-0.3, -14, 0.1)):
        imp("p_structure", tb((x, 0, z)), r, 1.36); imp("p_structure-roof", tb((x, 0, z)), r, 1.36)
    for name, pos, rot in (("p_crate", (-1.3, 0, -7.5), 0), ("p_barrel", (1.3, 0, -9.2), 0), ("p_crate-bottles", (0.5, 0, -12), 0.7)):
        imp(name, tb(pos), rot, 0.66)
    sm = _pmat("smoke", "9a9a9a", 1.0)
    for k in range(5):
        o = _prim("uv_sphere", tb((2.6, 2.8, -10.5)), mat=sm, radius=1.0); o.visible_shadow = False
        for f in range(1, 300, 6):
            tt = (f / 30 * 0.25 + k / 5) % 1; o.location = tb((2.6 + math.sin(tt * 5) * 0.3, 2.8 + tt * 3, -10.5)); r = 0.3 + tt * 0.5; o.scale = (r, r, r)
            o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)

# ---------------------------------------------------------------- Bild-Requisiten (flache Ausschnitte wie in 2D)
IMG = os.environ.get("STICKBLEND_IMG_DIR", "")
def image_prop(name, width, unlit=True, img_dir=None):
    base_dir = img_dir or IMG
    path = name if os.path.isabs(name) else os.path.join(base_dir, name if name.endswith(".png") else name + ".png")
    img = bpy.data.images.load(path, check_existing=True); asp = img.size[1] / max(1, img.size[0])
    bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.active_object; o.name = "prop_" + name
    o.data.transform(Matrix.Diagonal((width, width * asp, 1, 1))); o.rotation_mode = "QUATERNION"
    m = bpy.data.materials.new("prop_" + name); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links; N.remove(N["Principled BSDF"])
    tx = N.new("ShaderNodeTexImage"); tx.image = img; em = N.new("ShaderNodeEmission"); grp = N.new("ShaderNodeGroup"); grp.node_tree = mats._globals_group()
    Lk.new(tx.outputs[0], grp.inputs[0]); Lk.new(grp.outputs[0], em.inputs[0])
    tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader"); Lk.new(tx.outputs[1], ms.inputs[0]); Lk.new(tr.outputs[0], ms.inputs[1]); Lk.new(em.outputs[0], ms.inputs[2])
    Lk.new(ms.outputs[0], N["Material Output"].inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    o.data.materials.append(m); return o

def key_prop(o, frame, pos3, rot3=(0, 0, 0), visible=True, scale=1.0):
    """Position/Rotation in three-Achsen (Euler wie three.js XYZ) setzen und keyen."""
    q = Euler(rot3, "ZYX").to_quaternion()   # three "XYZ"
    o.location = tb(pos3); o.rotation_quaternion = Quaternion((q.w, q.x, -q.z, q.y)) @ Quaternion((1, 0, 0), math.pi / 2)
    o.scale = (scale, scale, scale); o.hide_render = not visible
    o.keyframe_insert("location", frame=frame); o.keyframe_insert("rotation_quaternion", frame=frame); o.keyframe_insert("scale", frame=frame); o.keyframe_insert("hide_render", frame=frame)

def leaflets(frames, t_of_frame, t0=0.0, n=120, area=(-6, 6, -16, 2), top=9.0, seed=11, step=2):
    """Fallende Flugblaetter (Port von World.tsx Leaflets)."""
    rnd = random.Random(seed); src = image_prop("leaflet", 0.22); src.hide_render = True
    out = []
    for i in range(n):
        a, b, c, d = rnd.random(), rnd.random(), rnd.random(), rnd.random()
        o = src.copy(); bpy.context.scene.collection.objects.link(o); out.append(o)
        for f in range(1, frames + 1, step):
            tt = t_of_frame(f) - t0 - d * 2.2
            y = top + 5 if tt < 0 else max(0.02, top - tt * 1.1 + math.sin(tt * 2.5 + c * 6) * 0.25); landed = y <= 0.02
            x = area[0] + a * (area[1] - area[0]) + (0 if landed else math.sin(tt * 1.6 + c * 9) * 0.6); z = area[2] + b * (area[3] - area[2])
            rot = (-math.pi / 2, tt * 1.5 + c * 6, c) if landed else (math.sin(tt * 3 + c * 5) * 1.2, tt * 1.5 + c * 6, math.cos(tt * 2.7 + d * 4) * 0.8)
            key_prop(o, f, (x, y, z), rot)
    return out

def books(pos3):
    rnd = random.Random(2)
    for k, c in enumerate(("c8352f", "2a6fc9", "3fae5a", "e0b043", "7a3fa8")):
        _prim("cube", tb((pos3[0] + (rnd.random() - 0.5) * 0.06, 0.05 + k * 0.09, pos3[2])), (0.18, 0.13, 0.04), (0, 0, (rnd.random() - 0.5) * 0.4), mats.flat(c))

# ---------------------------------------------------------------- Hubschrauber (Huey-Stil)
def heli(name="heli"):
    sc = bpy.context.scene; root = bpy.data.objects.new(name, None); sc.collection.objects.link(root)
    OD, OD2 = _pmat("od", "5c6a3e", 0.6), _pmat("od2", "4e5a34", 0.6); glass = _pmat("glass", "9fd0e8", 0.1); dark = _pmat("dark", "2a2a2e", 0.5)
    def P(kind, loc, s, rot=(0, 0, 0), m=OD, **kw):
        o = _prim(kind, loc, s, rot, m, **kw); o.parent = root; return o
    P("uv_sphere", (0.2, 0, 1.25), (1.55, 0.72, 0.78)); P("cube", (-0.35, 0, 1.2), (0.85, 0.65, 0.48))
    P("uv_sphere", (1.05, 0, 1.32), (0.6, 0.66, 0.62), m=glass)
    P("cylinder", (-2.75, 0, 1.42), (1, 1, 1), (0, math.pi / 2 - 0.04, 0), OD2, radius1=0.3, radius2=0.11, depth=3.4) if False else P("cone", (-2.75, 0, 1.42), (1, 1, 1), (0, -math.pi / 2 + 0.04, 0), OD2, radius1=0.3, radius2=0.11, depth=3.4)
    P("cube", (-4.35, 0, 1.85), (0.25, 0.035, 0.48), (0, 0.35, 0)); P("cube", (-3.3, 0, 1.42), (0.27, 0.4, 0.03))
    for y in (-0.69, 0.69):
        P("cylinder", (0, y, 0.08), (1, 1, 1), (0, math.pi / 2, 0), dark, radius=0.045, depth=2.6)
        for x in (-0.6, 0.55): P("cylinder", (x, y * 0.76, 0.5), (1, 1, 1), (math.copysign(0.35, y), 0, 0), dark, radius=0.04, depth=0.85)
    P("cylinder", (0, 0, 1.85), (1, 1, 1), m=dark, radius=0.06, depth=0.5)
    rotor = bpy.data.objects.new(name + "_rotor", None); sc.collection.objects.link(rotor); rotor.parent = root; rotor.location = (0, 0, 2.05)
    for k in (0, 1):
        b = _prim("cube", (0, 0, 0), (1.75, 0.11, 0.015), (0, 0, k * math.pi), dark); b.parent = rotor; b.location = (math.cos(k * math.pi) * 1.75, math.sin(k * math.pi) * 1.75, 0)
    tail = bpy.data.objects.new(name + "_tail", None); sc.collection.objects.link(tail); tail.parent = root; tail.location = (-4.45, 0.1, 2.05)
    b = _prim("cube", (0, 0, 0), (0.025, 0.04, 0.45), mat=dark); b.parent = tail
    return root, rotor, tail

# ---------------------------------------------------------------- Panda / Yeti (im Figurenstil: flach + Kontur)
def creature(kind, name):
    ch = character.Char(); ch.name = name; ch.coll = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(ch.coll)
    root = bpy.data.objects.new(name, None); ch.coll.objects.link(root)
    def part(nm, center, r, scale, col, thick=0.006):
        bm = geo.uvsphere(bmesh.new(), r, scale, center, 32, 20)
        return character._obj(ch, nm, bm, mats.flat(col), root, thick=thick)
    if kind == "panda":
        part("body", (0, 0.55, 0), 0.38, (1, 1.15, 0.9), "f4f2ee"); part("belt", (0, 0.72, 0), 0.4, (1.02, 0.3, 0.92), "1c1c20")
        for s in (-1, 1):
            part("leg%d" % s, (s * 0.2, 0.15, 0), 0.15, (1, 1.2, 1), "1c1c20"); part("arm%d" % s, (s * 0.38, 0.75, 0.08), 0.12, (1, 1.6, 1), "1c1c20")
            part("ear%d" % s, (s * 0.24, 1.55, -0.02), 0.11, (1, 1, 0.6), "1c1c20"); part("patch%d" % s, (s * 0.12, 1.3, 0.27), 0.08, (0.9, 1.2, 0.4), "1c1c20", 0.003)
            part("eye%d" % s, (s * 0.12, 1.31, 0.3), 0.025, (1, 1, 0.5), "ffffff", 0.0015)
        part("head", (0, 1.28, 0), 0.32, (1.1, 0.95, 0.95), "f4f2ee"); part("nose", (0, 1.2, 0.3), 0.045, (1.3, 0.8, 0.6), "1c1c20", 0.002)
    else:  # Yeti
        part("body", (0, 0.75, 0), 0.5, (1, 1.3, 0.85), "eef2f6")
        for s in (-1, 1):
            part("leg%d" % s, (s * 0.22, 0.18, 0), 0.18, (1, 1.3, 1), "e2e8ee"); part("arm%d" % s, (s * 0.55, 0.85, 0.05), 0.15, (1, 2.2, 1), "e2e8ee")
        part("head", (0, 1.55, 0.02), 0.3, (1.05, 1, 0.95), "eef2f6"); part("face", (0, 1.5, 0.2), 0.2, (1.1, 0.9, 0.5), "8fb4d8", 0.003)
        for s in (-1, 1): part("eye%d" % s, (s * 0.07, 1.56, 0.29), 0.03, (1, 1.2, 0.5), "1c1c20", 0.0015)
        part("mouth", (0, 1.44, 0.29), 0.05, (1.5, 0.5, 0.4), "3a1218", 0.002)
    # Fuer die 2.5D-Projektion wie eine Figur behandeln: Anker-Empties (Teile bleiben "body" -> je eigene Ebene)
    for nm, z in (("E_torso", 0.8), ("E_head", 1.4)):
        e = bpy.data.objects.new(f"{name}_{nm}", None); ch.coll.objects.link(e); e.parent = root; e.location = (0, 0, z); setattr(ch, nm, e)
    ch.pr = {"headR": 0.3, "torsoH": 0.6}; ch.root = root
    return ch
