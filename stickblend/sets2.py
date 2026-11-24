"""Realistische Sets (Poly Haven + Quaternius-Kulisse) im Referenzstil. Gleiche Schnittstellen wie sets.py.
Positionen subjects/cam_path in three-Achsen (y oben, Kamera blickt nach -z), Umrechnung per tb().
"""
import bpy, math, random
from mathutils import Vector
from . import world, mats, ph, flat, sets
from .geo import tb

MOODS = {
    #           HDRI, Staerke, Sonne (Winkel, Energie, Farbe), Figuren-Tint, Strichfarbe, Grading (lift, gain)
    "day":    dict(hdri="kloofendal_48d_partly_cloudy_puresky", hs=0.9, sun=((55, 0, 150), 3.2, (1.0, 0.92, 0.8)), tint=(1.0, 0.98, 0.95), stick=None,
                   lift=(0.99, 0.99, 1.02), gain=(1.03, 1.0, 0.96), ground=(0.9, 0.9, 0.85), haze=0.004, hazec=(1.0, 0.95, 0.85)),
    "dusk":   dict(hdri="qwantani_dusk_2_puresky", hs=0.55, sun=((80, 0, 150), 3.8, (1.0, 0.6, 0.3)), tint=(1.0, 0.85, 0.72), stick=None,
                   lift=(1.0, 0.98, 0.99), gain=(1.08, 1.0, 0.9), ground=(0.9, 0.82, 0.7), haze=0.0015, hazec=(1.0, 0.7, 0.45), sky=("3c5fae", "ffae6a")),
    "sunset": dict(hdri="qwantani_sunset_puresky", hs=1.0, sun=((84, 0, 175), 3.0, (1.0, 0.6, 0.36)), tint=(1.0, 0.86, 0.76), stick=None,
                   lift=(0.98, 0.97, 1.03), gain=(1.07, 0.99, 0.92), ground=(1.0, 0.92, 0.85), haze=0.003, hazec=(1.0, 0.75, 0.6)),
    "night":  dict(hdri="rogland_clear_night", hs=0.55, sun=((40, 0, -130), 0.45, (0.55, 0.65, 1.0)), tint=(0.62, 0.68, 0.9), stick="5c5c80",
                   lift=(0.97, 0.98, 1.05), gain=(1.0, 1.0, 1.02), ground=(0.6, 0.62, 0.62), haze=0.006, hazec=(0.5, 0.6, 0.9)),
    "fire":   dict(hdri="rogland_clear_night", hs=0.5, sun=((40, 0, -130), 0.35, (0.55, 0.65, 1.0)), tint=(0.95, 0.78, 0.66), stick="7a5038",
                   lift=(0.98, 0.985, 1.03), gain=(1.05, 1.0, 0.95), ground=(0.75, 0.75, 0.7), haze=0.0, hazec=(1, 1, 1)),
}
GRADE = {}

def mood(name, light_pos=None):
    M = MOODS[name]
    ph.hdri(M["hdri"], M["hs"], rot=1.2)
    world.sun(M["sun"][0], energy=M["sun"][1], color=M["sun"][2])
    mats.set_scene_light(tint=M["tint"], rim_strength=0.0)
    flat.STICK_COLOR = M["stick"]; flat.LIGHT_POS = light_pos
    GRADE.clear(); GRADE.update(lift=M["lift"], gain=M["gain"], sat=M.get("sat", 1.18), contrast=0.12)
    if M["haze"]: _haze(M["haze"], M["hazec"])
    if M.get("sky"): _sky_gradient(*M["sky"])
    return M

def _haze(d, c):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 14, 5)); bx = bpy.context.active_object; bx.name = "haze"; bx.scale = (70, 70, 10); bx.visible_shadow = False
    m = bpy.data.materials.new("haze"); m.use_nodes = True; N = m.node_tree.nodes; N.remove(N["Principled BSDF"])
    vs = N.new("ShaderNodeVolumeScatter"); vs.inputs["Density"].default_value = d; vs.inputs["Color"].default_value = (*c, 1); vs.inputs["Anisotropy"].default_value = 0.5
    m.node_tree.links.new(vs.outputs[0], N["Material Output"].inputs["Volume"]); bx.data.materials.append(m)

def _env():
    c = bpy.data.collections.new("env"); bpy.context.scene.collection.children.link(c); return c

def _clear(subjects, cam_path, r=0.8, near=1.4):
    S = [tb(s) for s in subjects] or [Vector((0, 4, 1))]; C = [tb(c) for c in cam_path] or [Vector((0, -2, 1.3))]
    return S, C, world.keep_clear(C, S, radius=r, near=near), world.keep_clear(C, S, radius=2.6, near=3.0)

def _scatter_ph(aid, parts, n, area, avoid, scale, seed, env, rot=True):
    rnd = random.Random(seed); out = 0; tries = 0
    while out < n and tries < n * 30:
        tries += 1; x = rnd.uniform(area[0], area[1]); y = rnd.uniform(area[2], area[3])
        if avoid and avoid(x, y): continue
        ph.place(aid, (x, y, 0), rnd.uniform(0, 6.283) if rot else 0, rnd.uniform(*scale), part=rnd.choice(parts) if parts else None, coll=env); out += 1

# ---------------------------------------------------------------- Dschungel
def jungle(mode="day", seed=1, subjects=(), cam_path=(), clearing=2.6, dense=1.0, light_pos=None):
    M = mood(mode, light_pos); env = _env()
    S, C, avoid, avoid_tree = _clear(subjects, cam_path)
    cx = sum(s.x for s in S) / len(S); cy = sum(s.y for s in S) / len(S); ymin = min(c.y for c in C) - 3
    gt = tuple(M["ground"][i] * (0.8, 0.95, 0.6)[i] for i in range(3))   # Laubboden ins Gruen ziehen
    ph.textured_ground("forest_leaves_02", 70, 2.2, tint=gt)
    clear = lambda x, y: math.hypot(x - cx, y - cy) < clearing
    # Kulisse: dichte Wand aus Palmen/Baeumen (Quaternius) hinten und an den Seiten, davor Buschguertel
    world.scatter(["PalmTree_1", "PalmTree_2", "PalmTree_3", "PalmTree_4", "PalmTree_5"], int(48 * dense), (cx - 18, cx + 18, ymin, cy + 26), lambda x, y: clear(x, y) or avoid_tree(x, y), (1.5, 2.4), seed, env)
    world.scatter(["NormalTree_1", "NormalTree_2", "NormalTree_3", "NormalTree_4", "NormalTree_5"], int(22 * dense), (cx - 24, cx + 24, cy + 6, cy + 34), None, (1.8, 2.6), seed + 1, env)
    world.scatter(["Bush_Large", "Bush", "Bush_Large_Flowers", "Plant_1", "Plant_2"], int(60 * dense), (cx - 14, cx + 14, cy + 2.5, cy + 18), lambda x, y: clear(x, y) or avoid(x, y), (1.0, 1.8), seed + 2, env)
    world.scatter(["Plant_1", "Plant_2", "Grass_Large", "Bush_Small", "Bush_Flowers"], int(70 * dense), (cx - 10, cx + 10, ymin, cy + 10), lambda x, y: (clear(x, y) and math.hypot(x - cx, y - cy) < clearing * 0.75) or avoid(x, y), (0.7, 1.3), seed + 9, env)
    # Nahbereich: realistische Pflanzen und Bodenstuecke (Poly Haven)
    _scatter_ph("fern_02", [0, 1, 2, 3], int(60 * dense), (cx - 9, cx + 9, ymin, cy + 10), lambda x, y: clear(x, y) and abs(x - cx) < clearing * 0.7 or avoid(x, y), (1.0, 1.8), seed + 3, env)
    _scatter_ph("shrub_02", [0, 1, 2, 3], int(16 * dense), (cx - 10, cx + 10, cy + 1, cy + 12), lambda x, y: clear(x, y) or avoid(x, y), (0.9, 1.4), seed + 10, env)
    _scatter_ph("nettle_plant", None, int(14 * dense), (cx - 7, cx + 7, ymin, cy + 7), lambda x, y: clear(x, y) or avoid(x, y), (0.8, 1.3), seed + 4, env)
    _scatter_ph("rock_moss_set_01", [0, 1, 2, 3, 4, 5], 5, (cx - 9, cx + 9, ymin + 1, cy + 10), lambda x, y: clear(x, y) or avoid(x, y), (0.25, 0.5), seed + 5, env)
    _scatter_ph("tree_stump_01", None, 3, (cx - 8, cx + 8, ymin + 1, cy + 8), lambda x, y: clear(x, y) or avoid(x, y), (0.6, 0.9), seed + 6, env)
    _scatter_ph("root_cluster_01", None, 2, (cx - 9, cx + 9, cy + 1, cy + 9), lambda x, y: clear(x, y) or avoid(x, y), (0.6, 0.9), seed + 7, env)
    _scatter_ph("dry_branches_medium_01", [0, 1, 2], 8, (cx - 6, cx + 6, ymin, cy + 6), avoid, (0.6, 1.0), seed + 8, env)
    if mode in ("night", "fire"): sets.fireflies((cx, cy), 28, seed)
    return env

# ---------------------------------------------------------------- Strand
def _water(color):
    m = bpy.data.materials.new("sea"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = mats.lin(color); b.inputs["Roughness"].default_value = 0.08
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18; bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.25
    L.new(nz.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"]); return m

def beach(sunset=False, subjects=(), cam_path=()):
    M = mood("sunset" if sunset else "day"); env = _env()
    S, C, avoid, avoid_tree = _clear(subjects, cam_path, 0.9, 1.6)
    ph.textured_ground("coast_sand_01", 120, 3.0, tint=(1.0, 0.97, 0.9))
    sea = sets._prim("plane", (0, 220, 0.03), mat=_water("2a5f86" if not sunset else "3a4a78"), size=400); sea.visible_shadow = False
    foam = sets._prim("plane", (0, 20.3, 0.04), (60, 0.25, 1), mat=sets._emit("foam", "f4f8ff", 0.7), size=1); foam.visible_shadow = False
    for f in range(1, 400, 30): foam.location.y = 20.3 + 0.4 * math.sin(f / 30 * 1.2); foam.keyframe_insert("location", frame=f)
    for i, x in enumerate([-7, -4.8, 6, 8.5, -2.8, 3.6, -11, 12]):
        y = 3 + i * 1.7
        if not avoid_tree(x, y): world.place(["PalmTree_1", "PalmTree_3", "PalmTree_2", "PalmTree_4"][i % 4], (x, y, 0), i * 1.3, 1.6 + (i % 3) * 0.3, env)
    world.scatter(["Rock_1", "Rock_2", "Rock_4"], 7, (-10, 10, 2, 18), avoid_tree, (0.4, 0.8), 9, env)   # kleine Felsen; Poly-Haven-Kuestenfelsen sind zu gross
    _scatter_ph("nettle_plant", None, 5, (-9, 9, 1, 12), avoid, (0.7, 1.1), 12, env)
    _scatter_ph("dry_branches_medium_01", [0, 1, 2], 5, (-6, 6, -2, 8), avoid, (0.6, 1.0), 11, env)
    return env

# ---------------------------------------------------------------- Lager (Nacht, Feuer)
def camp(at=(0, 0, 0), years=None, frames=200, crates=True):
    """at in three-Achsen. years = [(frame_ab, "1946"), ...] -> Kerben im Rindenstamm."""
    p = tb(at); env = bpy.context.scene.collection
    ph.place("stone_fire_pit", p, 0.3, 0.75); ph.place("dry_branches_medium_01", p + Vector((0, 0, 0.05)), 1.0, 0.45, part=0)
    ph.fire(p + Vector((0, 0, 0.05)), frames, scale=0.8, light=150); ph.smoke(p + Vector((0, 0, 0.3)), frames, n=4)
    ph.place("pot_enamel_01", p + Vector((0.62, 0.35, 0)), 0.6, 1.0, part=0)
    if crates:
        ph.place("old_military_crate", p + tb((-1.6, 0, -1.4)), 0.5, 1.0, exclude=("cloth",)); ph.place("ammo_box", p + tb((-1.0, 0, -1.0)), 1.2, 1.4, part=0)
    # Rindenstamm mit Jahreskerben
    trunk = sets._prim("cylinder", p + tb((1.6, 2.5, -1.2)), mat=_bark(), radius=0.32, depth=5, vertices=24)
    if years:
        tm = sets._emit("carve", "e9d3a8", 0.9)
        for k, (fa, txt) in enumerate(years):
            bpy.ops.object.text_add(location=p + tb((1.6, 2.15 - k * 0.24, -0.86))); o = bpy.context.active_object
            o.data.body = txt; o.data.size = 0.16; o.data.align_x = "CENTER"; o.rotation_euler = (math.pi / 2, 0, 0); o.data.materials.append(tm)
            o.hide_render = True; o.keyframe_insert("hide_render", frame=1); o.hide_render = False; o.keyframe_insert("hide_render", frame=max(1, fa))
    return p + Vector((0, 0, 0.5))

def _bark():
    import os, glob
    if "bark" in bpy.data.materials: return bpy.data.materials["bark"]
    d = os.path.join(ph.PH, "textures", "bark_brown_02"); m = bpy.data.materials.new("bark"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(glob.glob(os.path.join(d, "*diff*"))[0], check_existing=True)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2, 2, 2); L.new(tc.outputs["UV"], mp.inputs[0]); L.new(mp.outputs[0], t.inputs[0])
    L.new(t.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9; return m

# ---------------------------------------------------------------- Mond
def _moon_h(x, y, craters):
    h = 0.35 * _nz.fractal(Vector((x / 18.0, y / 18.0, 0.4)), 0.6, 2.0, 4) + 0.04 * _nz.noise(Vector((x * 1.3, y * 1.3, 2.0)))
    for cx, cy, r, dp in craters:
        d = math.hypot(x - cx, y - cy) / r
        if d < 1.0: h -= dp * (1 - d * d)
        elif d < 1.6: h += dp * 0.35 * (1 - (d - 1) / 0.6) ** 2
    return h

def _space_sky():
    """Kamera: tiefes Indigo statt Schwarz, Sterne, blasses Milchstrassenband. Licht: dunkles Blau (Erdlicht)."""
    sc = bpy.context.scene; w = bpy.data.worlds.new("space"); sc.world = w; w.use_nodes = True
    N = w.node_tree.nodes; L = w.node_tree.links; out = N["World Output"]; amb = N["Background"]
    amb.inputs[0].default_value = (0.16, 0.2, 0.42, 1); amb.inputs[1].default_value = 0.35
    tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sp.inputs[0])
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (0.035, 0.03, 0.11, 1)
    rp.color_ramp.elements[1].position = 0.6; rp.color_ramp.elements[1].color = (0.004, 0.004, 0.02, 1); L.new(sp.outputs["Z"], rp.inputs[0])
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 420; L.new(tc.outputs["Generated"], vo.inputs["Vector"])
    st = N.new("ShaderNodeMapRange"); st.inputs[1].default_value = 0.06; st.inputs[2].default_value = 0.0; L.new(vo.outputs["Distance"], st.inputs[0])
    pw = N.new("ShaderNodeMath"); pw.operation = "POWER"; L.new(st.outputs[0], pw.inputs[0]); pw.inputs[1].default_value = 3
    br = N.new("ShaderNodeMath"); br.operation = "MULTIPLY"; L.new(pw.outputs[0], br.inputs[0]); L.new(vo.outputs["Color"], br.inputs[1])
    sb = N.new("ShaderNodeMath"); sb.operation = "MULTIPLY"; L.new(br.outputs[0], sb.inputs[0]); sb.inputs[1].default_value = 6.0
    # Milchstrasse: Rauschband entlang einer schraegen Ebene
    vm = N.new("ShaderNodeVectorMath"); vm.operation = "DOT_PRODUCT"; L.new(tc.outputs["Generated"], vm.inputs[0]); vm.inputs[1].default_value = (0.5, -0.35, 0.79)
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L.new(vm.outputs["Value"], ab.inputs[0])
    band = N.new("ShaderNodeMapRange"); band.inputs[1].default_value = 0.22; band.inputs[2].default_value = 0.0; L.new(ab.outputs[0], band.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 8; L.new(tc.outputs["Generated"], nz.inputs["Vector"])
    mb = N.new("ShaderNodeMath"); mb.operation = "MULTIPLY"; L.new(band.outputs[0], mb.inputs[0]); L.new(nz.outputs["Fac"], mb.inputs[1])
    mw = N.new("ShaderNodeMix"); mw.data_type = "RGBA"; mw.blend_type = "ADD"; L.new(mb.outputs[0], mw.inputs[0]); L.new(rp.outputs[0], mw.inputs[6]); mw.inputs[7].default_value = (0.09, 0.06, 0.2, 1)
    ad = N.new("ShaderNodeMix"); ad.data_type = "RGBA"; ad.blend_type = "ADD"; ad.inputs[0].default_value = 1; L.new(mw.outputs[2], ad.inputs[6])
    cs = N.new("ShaderNodeCombineXYZ"); L.new(sb.outputs[0], cs.inputs[0]); L.new(sb.outputs[0], cs.inputs[1]); L.new(sb.outputs[0], cs.inputs[2]); L.new(cs.outputs[0], ad.inputs[7])
    bg = N.new("ShaderNodeBackground"); L.new(ad.outputs[2], bg.inputs[0])
    lp = N.new("ShaderNodeLightPath"); mx = N.new("ShaderNodeMixShader"); L.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    L.new(amb.outputs[0], mx.inputs[1]); L.new(bg.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])

def _gold():
    m = bpy.data.materials.new("lm_gold"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 0.62, 0.16, 1); b.inputs["Metallic"].default_value = 0.7
    tc = N.new("ShaderNodeTexCoord"); vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 9; L.new(tc.outputs["Object"], vo.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4; nz.inputs["Detail"].default_value = 4; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs[3].default_value = 0.18; rr.inputs[4].default_value = 0.34; L.new(nz.outputs["Fac"], rr.inputs[0]); L.new(rr.outputs[0], b.inputs["Roughness"])
    vo.inputs["Scale"].default_value = 3.0; ad = N.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; L.new(vo.outputs["Distance"], ad.inputs[0]); ad.inputs[1].default_value = 0.4; L.new(nz.outputs["Fac"], ad.inputs[2])
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.22; bm.inputs["Distance"].default_value = 0.03; L.new(ad.outputs[0], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.9, 0.45, 0.06, 1); cr.color_ramp.elements[1].color = (1.0, 0.8, 0.3, 1)
    L.new(nz.outputs["Fac"], cr.inputs[0]); L.new(cr.outputs[0], b.inputs["Base Color"])
    return m

def _lander(at, yaw=0.4):
    """Mondfaehre (Apollo-LM-artig): Abstiegsstufe in Goldfolie, vier Beine, facettierte Aufstiegsstufe mit Fenstern, Antennen, Leiter."""
    import bmesh
    root = bpy.data.objects.new("lander", None); bpy.context.scene.collection.objects.link(root); root.location = at; root.rotation_euler = (0, 0, yaw)
    P = sets._pmat; gold = _gold(); sil = P("lm_silver", "c9ccd4", 0.35); beige = P("lm_beige", "a9a496", 0.6); dark = P("lm_dark", "24262c", 0.4); blk = P("lm_win", "0c0e14", 0.08)
    def add(o): o.parent = root; return o
    # Abstiegsstufe: Achteck
    add(sets._prim("cylinder", (0, 0, 1.75), (1, 1, 1), (0, 0, math.pi / 8), gold, radius=2.15, depth=1.6, vertices=8))
    add(sets._prim("cylinder", (0, 0, 0.82), (1, 1, 1), (0, 0, 0), dark, radius=0.55, depth=0.5, vertices=24))   # Triebwerksglocke
    for k in range(4):   # Beine
        a = math.pi / 4 + k * math.pi / 2; c, s_ = math.cos(a), math.sin(a)
        top = Vector((c * 1.6, s_ * 1.6, 2.2)); foot = Vector((c * 3.9, s_ * 3.9, 0.12)); mid = Vector((c * 2.3, s_ * 2.3, 1.05))
        for p0, p1, r in ((top, foot, 0.08), (mid, Vector((c * 1.7, s_ * 1.7, 1.2)), 0.045), (Vector((c * 2.9, s_ * 2.9, 0.7)), Vector((c * 1.6 + s_ * 0.9, s_ * 1.6 - c * 0.9, 1.1)), 0.035), (Vector((c * 2.9, s_ * 2.9, 0.7)), Vector((c * 1.6 - s_ * 0.9, s_ * 1.6 + c * 0.9, 1.1)), 0.035)):
            d = p1 - p0; o = add(sets._prim("cylinder", (p0 + p1) / 2, (1, 1, 1), (0, 0, 0), gold if r > 0.06 else sil, radius=r, depth=d.length, vertices=10))
            o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
        add(sets._prim("cylinder", foot, (1, 1, 1), (0, 0, 0), sil, radius=0.46, depth=0.14, vertices=24))
    # Leiter vor dem Vorderbein: um 0.24 m nach aussen-oben versetzt (nicht im Beinrohr), zwei Halter zum Bein
    a = math.pi / 4; c, s_ = math.cos(a), math.sin(a); nr, nz_ = 0.67 * 0.24, 0.74 * 0.24
    R2 = lambda r, z, side: Vector((c * (r + nr) - s_ * side, s_ * (r + nr) + c * side, z + nz_))
    for side in (-0.22, 0.22):
        p0 = R2(2.2, 1.75, side); p1 = R2(3.55, 0.45, side); d = p1 - p0
        o = add(sets._prim("cylinder", (p0 + p1) / 2, (1, 1, 1), (0, 0, 0), sil, radius=0.025, depth=d.length, vertices=8)); o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    for i in range(8):
        k = (i + 0.5) / 8; p = R2(2.2 + 1.35 * k, 1.75 - 1.3 * k, 0)
        add(sets._prim("cylinder", p, (1, 1, 1), (math.pi / 2, 0, a), sil, radius=0.018, depth=0.44, vertices=6))
    for k in (0.25, 0.8):   # Halter Leiter -> Bein
        r = 2.2 + 1.35 * k; z = 1.75 - 1.3 * k; p0 = R2(r, z, 0); p1 = Vector((c * r, s_ * r, z - 0.05)); d = p1 - p0
        o = add(sets._prim("cylinder", (p0 + p1) / 2, (1, 1, 1), (0, 0, 0), sil, radius=0.02, depth=d.length, vertices=6)); o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    add(sets._prim("cube", (c * 2.2, s_ * 2.2, 2.55), (0.45, 0.45, 0.04), (0, 0, a), sil))   # Plattform
    # Aufstiegsstufe: facettierter Rumpf
    bm = bmesh.new()
    prof = [(-1.25, -1.0), (1.25, -1.0), (1.55, -0.2), (1.25, 1.05), (-1.25, 1.05), (-1.55, -0.2)]
    for z in (2.55, 4.5):
        sh = 0.85 if z > 3 else 1.0
        for x, y in prof: bm.verts.new((x * sh, y * sh, z))
    bm.verts.ensure_lookup_table(); n = len(prof)
    bm.faces.new([bm.verts[i] for i in range(n)][::-1]); bm.faces.new([bm.verts[n + i] for i in range(n)])
    for i in range(n): j = (i + 1) % n; bm.faces.new([bm.verts[i], bm.verts[j], bm.verts[n + j], bm.verts[n + i]])
    me = bpy.data.meshes.new("ascent"); bm.to_mesh(me); asc = bpy.data.objects.new("ascent", me); bpy.context.scene.collection.objects.link(asc); add(asc); me.materials.append(beige)
    # Frontpartie zur Leiter (+x): Fenster (Dreiecke), Luke
    for sy in (-0.42, 0.42):
        add(sets._prim("cube", (1.36, sy, 3.85), (0.03, 0.22, 0.2), (0, -0.35, 0), blk))
    add(sets._prim("cube", (1.45, 0, 3.05), (0.03, 0.42, 0.42), (0, 0, 0), sil))
    add(sets._prim("cylinder", (0, 0, 4.75), (1, 1, 1), (0, 0, 0), sil, radius=0.55, depth=0.5, vertices=24))   # Andockstutzen
    for k in range(4):   # Steuerduesen-Quads
        a = math.pi / 4 + k * math.pi / 2; o = add(sets._prim("cube", (math.cos(a) * 1.55, math.sin(a) * 1.25, 4.1), (0.16, 0.16, 0.16), (0, 0, a), dark))
    pole = add(sets._prim("cylinder", (-0.7, -0.6, 5.2), (1, 1, 1), (0, 0, 0), sil, radius=0.03, depth=1.4, vertices=8))
    dish = add(sets._prim("cone", (-0.7, -0.6, 5.95), (1, 1, 1), (math.radians(130), 0, 0.6), sil, radius1=0.55, radius2=0.05, depth=0.25, vertices=24))
    add(sets._prim("cylinder", (0.6, 0.7, 5.0), (1, 1, 1), (0.3, 0.2, 0), sil, radius=0.015, depth=1.2, vertices=6))
    return root

def _flag(at, yaw):
    root = bpy.data.objects.new("flag", None); bpy.context.scene.collection.objects.link(root); root.location = at; root.rotation_euler = (0, 0, yaw)
    sil = sets._pmat("pole", "d8dbe2", 0.3)
    for loc, r, dp, rot in (((0, 0, 1.15), 0.02, 2.3, (0, 0, 0)), ((0.48, 0, 2.25), 0.012, 0.96, (0, math.pi / 2, 0))):
        o = sets._prim("cylinder", loc, (1, 1, 1), rot, sil, radius=r, depth=dp, vertices=8); o.parent = root
    me = bpy.data.meshes.new("flagcloth"); vs = []; fs = []; nx, ny = 16, 8
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny; vs.append((u * 0.95, 0.05 * math.sin(u * 7) * u, 2.24 - v * 0.6))
    for j in range(ny):
        for i in range(nx): a = j * (nx + 1) + i; fs.append((a, a + 1, a + nx + 2, a + nx + 1))
    me.from_pydata(vs, [], fs); uv = me.uv_layers.new(name="UV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; uv.data[li].uv = ((vi % (nx + 1)) / nx, 1 - (vi // (nx + 1)) / ny)
    m = bpy.data.materials.new("flag"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.8
    tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sp.inputs[0])
    st = N.new("ShaderNodeMath"); st.operation = "MULTIPLY"; L.new(sp.outputs["Y"], st.inputs[0]); st.inputs[1].default_value = 6.5
    fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; L.new(st.outputs[0], fr.inputs[0]); lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; L.new(fr.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = 0.5
    stripes = N.new("ShaderNodeMix"); stripes.data_type = "RGBA"; L.new(lt.outputs[0], stripes.inputs[0]); stripes.inputs[6].default_value = (0.95, 0.95, 0.95, 1); stripes.inputs[7].default_value = (0.62, 0.03, 0.05, 1)
    cx = N.new("ShaderNodeMath"); cx.operation = "LESS_THAN"; L.new(sp.outputs["X"], cx.inputs[0]); cx.inputs[1].default_value = 0.4
    cy = N.new("ShaderNodeMath"); cy.operation = "GREATER_THAN"; L.new(sp.outputs["Y"], cy.inputs[0]); cy.inputs[1].default_value = 0.46
    ca = N.new("ShaderNodeMath"); ca.operation = "MULTIPLY"; L.new(cx.outputs[0], ca.inputs[0]); L.new(cy.outputs[0], ca.inputs[1])
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 18; vo.inputs["Randomness"].default_value = 0.0; L.new(tc.outputs["UV"], vo.inputs["Vector"])
    stars = N.new("ShaderNodeMath"); stars.operation = "LESS_THAN"; L.new(vo.outputs["Distance"], stars.inputs[0]); stars.inputs[1].default_value = 0.16
    canton = N.new("ShaderNodeMix"); canton.data_type = "RGBA"; L.new(stars.outputs[0], canton.inputs[0]); canton.inputs[6].default_value = (0.03, 0.06, 0.3, 1); canton.inputs[7].default_value = (0.95, 0.95, 0.95, 1)
    fin = N.new("ShaderNodeMix"); fin.data_type = "RGBA"; L.new(ca.outputs[0], fin.inputs[0]); L.new(stripes.outputs[2], fin.inputs[6]); L.new(canton.outputs[2], fin.inputs[7]); L.new(fin.outputs[2], b.inputs["Base Color"])
    me.materials.append(m); o = bpy.data.objects.new("flagcloth", me); bpy.context.scene.collection.objects.link(o); o.parent = root
    for poly in me.polygons: poly.use_smooth = True
    return root

def _earth(at, r):
    m = bpy.data.materials.new("earth"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.6
    tc = N.new("ShaderNodeTexCoord"); land = N.new("ShaderNodeTexNoise"); land.inputs["Scale"].default_value = 0.22; land.inputs["Detail"].default_value = 3; L.new(tc.outputs["Object"], land.inputs["Vector"])
    lr = N.new("ShaderNodeValToRGB"); e = lr.color_ramp.elements; e[0].position = 0.5; e[0].color = (0.02, 0.12, 0.45, 1); e[1].position = 0.53; e[1].color = (0.18, 0.4, 0.1, 1)
    e2 = lr.color_ramp.elements.new(0.62); e2.color = (0.45, 0.35, 0.16, 1); L.new(land.outputs["Fac"], lr.inputs[0])
    cl = N.new("ShaderNodeTexNoise"); cl.inputs["Scale"].default_value = 0.5; cl.inputs["Detail"].default_value = 6; cl.inputs["Distortion"].default_value = 1.2; L.new(tc.outputs["Object"], cl.inputs["Vector"])
    cr = N.new("ShaderNodeMapRange"); cr.inputs[1].default_value = 0.52; cr.inputs[2].default_value = 0.62; L.new(cl.outputs["Fac"], cr.inputs[0])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(cr.outputs[0], mx.inputs[0]); L.new(lr.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (1, 1, 1, 1); L.new(mx.outputs[2], b.inputs["Base Color"])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.35; L.new(lw.outputs["Fresnel"], b.inputs["Emission Strength"]); b.inputs["Emission Color"].default_value = (0.3, 0.55, 1.0, 1)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=at, segments=64, ring_count=32); o = bpy.context.active_object; o.name = "earth"; o.data.materials.append(m); o.rotation_euler = (0.4, 0.2, 1.0)
    bpy.ops.object.shade_smooth(); o.visible_shadow = False
    return o

def moon(subjects=(), lander_at=(1.6, 0, -7.5), lander_yaw=-2.4):
    """Mondoberflaeche im Referenzstil: warmes Sonnenlicht, blaue Schatten (Erdlicht), Indigo-Himmel mit Sternen, goldene Faehre."""
    _space_sky(); world.sun((72, 0, -28), energy=5.0, color=(1.0, 0.93, 0.8), angle=0.01)
    mats.set_scene_light(tint=(1.0, 0.98, 0.96), rim_strength=0.0); flat.STICK_COLOR = None; flat.LIGHT_POS = None
    rnd = random.Random(11); S = [tb(s) for s in subjects] + [tb(lander_at)]
    cr = []
    while len(cr) < 70:
        x, y, r = rnd.uniform(-60, 60), rnd.uniform(-10, 110), rnd.choice([0.4, 0.6, 0.9, 1.3, 2.0, 3.5, 6.0])
        if any(math.hypot(x - p.x, y - p.y) < r * 1.7 + 1.2 for p in S): continue
        cr.append((x, y, r, r * 0.22))
    g = _grid("ground", -70, 70, -15, 130, 280, 290, lambda x, y: _moon_h(x, y, cr))
    d = __import__("os").path.join(ph.PH, "textures", "rock_ground"); import glob as _g
    m = bpy.data.materials.new("regolith"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.35, 0.35, 0.35); L.new(tc.outputs["Object"], mp.inputs[0])
    def img(key, nc=False):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(_g.glob(__import__("os").path.join(d, f"*{key}*"))[0], check_existing=True); t.projection = "BOX"; t.projection_blend = 0.3
        if nc: t.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs[0], t.inputs[0]); return t
    di = img("diff"); hsv = N.new("ShaderNodeHueSaturation"); hsv.inputs["Saturation"].default_value = 0.25; hsv.inputs["Value"].default_value = 1.25; L.new(di.outputs[0], hsv.inputs["Color"])
    tint = N.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"; tint.inputs[0].default_value = 1; L.new(hsv.outputs[0], tint.inputs[6]); tint.inputs[7].default_value = (0.98, 0.9, 0.8, 1)
    L.new(tint.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    nm = N.new("ShaderNodeNormalMap"); nt = img("nor_gl", True); L.new(nt.outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], b.inputs["Normal"])
    g.data.materials.append(m)
    for i in range(14):   # Brocken
        x, y = rnd.uniform(-12, 12), rnd.uniform(0, 40)
        if any(math.hypot(x - p.x, y - p.y) < 2.2 for p in S): continue
        ph.place(rnd.choice(["moon_rock_01", "moon_rock_03"]), (x, y, _moon_h(x, y, cr) - 0.05), rnd.uniform(0, 6.3), rnd.uniform(0.25, 0.9))
    for i, (x, y, sx, sz) in enumerate([(-120, 260, 120, 22), (90, 300, 140, 30), (-10, 420, 220, 45), (200, 200, 90, 18)]):   # ferne Huegel
        o = sets._prim("uv_sphere", (x, y, -sz * 0.35), (sx, sx * 0.6, sz), mat=m, segments=48, ring_count=24); bpy.ops.object.shade_smooth()
    _earth(tb((-8, 27, -95)), 6.5)
    _lander(tb(lander_at), lander_yaw)
    sc = bpy.context.scene
    GRADE.clear(); GRADE.update(lift=(0.96, 0.98, 1.08), gain=(1.06, 1.0, 0.93), sat=1.15, contrast=0.12)
    return cr

def grade():
    ph.grade(lift=GRADE.get("lift", (0.98, 0.985, 1.03)), gain=GRADE.get("gain", (1.04, 1.0, 0.96)), contrast=GRADE.get("contrast", 0.1), sat=GRADE.get("sat", 1.0))

# ---------------------------------------------------------------- Dorf: Kenney-Huetten mit Holz- und Strohmaterial
def _straw():
    if "straw" in bpy.data.materials: return bpy.data.materials["straw"]
    m = bpy.data.materials.new("straw"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (60, 3, 60); L.new(tc.outputs["Object"], mp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 8; L.new(mp.outputs[0], nz.inputs["Vector"])   # Halme: gestreckt
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].color = mats.lin("4a3016"); rp.color_ramp.elements[1].color = mats.lin("a87a38")
    L.new(nz.outputs["Fac"], rp.inputs[0]); L.new(rp.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.6; L.new(nz.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"])
    return m

def _weave():
    """Geflochtene Bambuswand (Sawali): Schachbrett aus Streifen, hell/dunkel."""
    if "weave" in bpy.data.materials: return bpy.data.materials["weave"]
    m = bpy.data.materials.new("weave"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); ch = N.new("ShaderNodeTexChecker"); ch.inputs["Scale"].default_value = 1.0
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (26, 26, 26); mp.inputs["Rotation"].default_value = (0, 0, 0); L.new(tc.outputs["Object"], mp.inputs[0]); L.new(mp.outputs[0], ch.inputs["Vector"])
    ch.inputs["Color1"].default_value = mats.lin("e3cfa0"); ch.inputs["Color2"].default_value = mats.lin("bfa071")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 30; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 0.3; L.new(ch.outputs["Color"], mx.inputs[6]); L.new(nz.outputs["Color"], mx.inputs[7])
    L.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.35; L.new(ch.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"])
    return m

def _hut(loc, rot, s=1.0):
    """Pfahlhuette (Bahay Kubo): Pfaehle, Boden, Flechtwaende, Tuer/Fenster, steiles Strohdach mit Ueberstand, Leiter."""
    import bmesh
    root = bpy.data.objects.new("hut", None); bpy.context.scene.collection.objects.link(root); root.location = loc; root.rotation_euler = (0, 0, rot); root.scale = (s, s, s)
    wood = _bark(); dark = sets._pmat("hut_dark", "1c120c", 0.9); pole = sets._pmat("bamboo", "a58a4a", 0.6)
    def add(o): o.parent = root; return o
    W, D, F, H = 3.0, 2.4, 0.9, 1.8
    for x in (-W / 2 + 0.1, 0, W / 2 - 0.1):
        for y in (-D / 2 + 0.1, D / 2 - 0.1): add(sets._prim("cylinder", (x, y, F / 2), (1, 1, 1), mat=pole, radius=0.07, depth=F + 0.05, vertices=10))
    add(sets._prim("cube", (0, 0, F), (W / 2 + 0.15, D / 2 + 0.15, 0.06), mat=wood))
    add(sets._prim("cube", (0, 0, F + H / 2), (W / 2, D / 2, H / 2), mat=_weave()))
    for x in (-W / 2, W / 2):
        for y in (-D / 2, D / 2): add(sets._prim("cylinder", (x, y, F + H / 2), (1, 1, 1), mat=pole, radius=0.06, depth=H + 0.1, vertices=8))
    add(sets._prim("cube", (0.5, -D / 2 - 0.01, F + 0.75), (0.38, 0.02, 0.7), mat=dark))      # Tuer
    add(sets._prim("cube", (-0.85, -D / 2 - 0.01, F + 1.15), (0.35, 0.02, 0.28), mat=dark))   # Fenster
    for i in range(5):   # Leiter
        add(sets._prim("cube", (0.5, -D / 2 - 0.35 - i * 0.05, F - 0.15 - i * 0.18), (0.4, 0.04, 0.025), mat=pole))
    for xs in (0.12, 0.88): add(sets._prim("cylinder", (xs, -D / 2 - 0.45, F / 2), (1, 1, 1), (0.25, 0, 0), pole, radius=0.03, depth=F + 0.2, vertices=6))
    # Dach: Satteldach, Traufe weit ueberstehend, First hoch
    bm = bmesh.new(); ox, oy, top, eave = W / 2 + 0.55, D / 2 + 0.6, F + H + 1.7, F + H - 0.15
    v = [bm.verts.new(c) for c in [(-ox, -oy, eave), (ox, -oy, eave), (ox * 0.85, 0, top), (-ox * 0.85, 0, top), (-ox, oy, eave), (ox, oy, eave)]]
    bm.faces.new([v[0], v[1], v[2], v[3]]); bm.faces.new([v[3], v[2], v[5], v[4]]); bm.faces.new([v[0], v[3], v[4]]); bm.faces.new([v[1], v[5], v[2]])
    me = bpy.data.meshes.new("roof"); bm.to_mesh(me); ro = bpy.data.objects.new("roof", me); bpy.context.scene.collection.objects.link(ro); add(ro)
    me.materials.append(_straw()); sd = ro.modifiers.new("solid", "SOLIDIFY"); sd.thickness = 0.18
    return root

def village():
    for x, z, r in ((-3.4, -8.5, 0.5), (3.3, -11.0, -0.45), (-0.3, -15.5, 0.1)): _hut(tb((x, 0, z)), r, 0.85)
    for name, pos, rot in (("old_military_crate", (-1.3, 0, -7.5), 0.3), ("pot_enamel_01", (1.3, 0, -9.2), 0)):
        ph.place(name, tb(pos), rot, 1.0, exclude=("cloth",))

# ---------------------------------------------------------------- Insel aus der Luft (Lubang): Gelaende, Flachwasser, Brandung, Wald, Wolken
from mathutils import noise as _nz

ISL_K, ISL_H = 4.5, 2.6   # Inselgroesse (~400 x 190 m) und Hoehenfaktor
def _isl_h(x, y):
    """Hoehe der Insel (m) in Blender-Koordinaten; < 0 = Meeresgrund."""
    return _isl_h0(x / ISL_K, y / ISL_K) * (ISL_H if _isl_h0(x / ISL_K, y / ISL_K) > 0 else 1.0)
def _isl_h0(x, y):
    w = Vector((x / 26.0, y / 26.0, 0.3)); wx = _nz.noise(w) * 9; wy = _nz.noise(w + Vector((5.2, 1.3, 0))) * 9
    xx, yy = x + wx, y + wy
    d = math.sqrt((xx / 44.0) ** 2 + (yy / 21.0) ** 2)
    land = 1.0 - d + 0.12 * _nz.fractal(Vector((x / 14.0, y / 14.0, 1.7)), 0.6, 2.0, 4)
    if land <= 0: return max(-7.0, land * 22.0)
    ridge = math.exp(-((yy + 0.18 * xx) / 9.0) ** 2) * 13 * min(1, land * 1.6)
    return 0.9 * min(1.0, land * 9) + ridge * min(1, land * 2.5) + 4.5 * land * (0.5 + 0.5 * _nz.fractal(Vector((x / 9.0, y / 9.0, 3.1)), 0.5, 2.0, 4))

def _grid(name, x0, x1, y0, y1, nx, ny, fz, cols=None):
    import bmesh
    me = bpy.data.meshes.new(name); verts = []; faces = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny; verts.append((x, y, fz(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me.from_pydata(verts, [], faces); me.update()
    for p in me.polygons: p.use_smooth = True
    if cols:
        for nm, fn in cols.items():
            at = me.color_attributes.new(nm, "FLOAT_COLOR", "POINT")
            for k, v in enumerate(verts): at.data[k].color = fn(v[0], v[1], v[2])
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def _attr_mat(name, attr, rough=0.85, extra=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    a = N.new("ShaderNodeAttribute"); a.attribute_name = attr; b.inputs["Roughness"].default_value = rough
    L.new(a.outputs["Color"], b.inputs["Base Color"])
    if extra: extra(m, N, L, b, a)
    return m

def _smooth(a, b, x): k = max(0.0, min(1.0, (x - a) / (b - a))); return k * k * (3 - 2 * k)
def _mixc(c1, c2, k): return tuple(c1[i] + (c2[i] - c1[i]) * k for i in range(3))

def island(frames=200, cam_path=()):
    """Lubang aus der Luft: kraeftige Farben (Tuerkis-Flachwasser, goldener Sand, sattes Gruen), Wolken auf Kamerahoehe."""
    ph.hdri("kloofendal_48d_partly_cloudy_puresky", 1.0, rot=2.2)
    world.sun((48, 0, 150), energy=4.2, color=(1.0, 0.9, 0.74))
    mats.set_scene_light(tint=(1, 1, 1), rim_strength=0.0); flat.STICK_COLOR = None; flat.LIGHT_POS = None
    lin = mats.lin
    SAND, SAND_W, GRASS, JUNG, ROCK = lin("f2d08a"), lin("c9a466"), lin("6fae3a"), lin("2f7a2c"), lin("8a7a5a")
    def land_col(x, y, z):
        if z < 0.8: c = _mixc(SAND_W, SAND, _smooth(-0.8, 0.5, z))
        else:
            n = 0.5 + 0.5 * _nz.noise(Vector((x / 22.0, y / 22.0, 0.7)))
            c = _mixc(SAND, _mixc(GRASS, JUNG, _smooth(0.25, 0.75, n)), _smooth(0.8, 2.4, z))
            c = _mixc(c, ROCK, 0.45 * _smooth(26, 40, z) * n)
        return (*c, 1)
    terr = _grid("island", -260, 260, -150, 150, 420, 240, _isl_h, {"col": land_col})
    def tex(m, N, L, b, a):   # Kronendach aus der Ferne: Voronoi-Buckel (je ~4 m eine Krone), dunkle Zwischenraeume; Sand bleibt glatt
        tc = N.new("ShaderNodeTexCoord"); vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 0.28; L.new(tc.outputs["Object"], vo.inputs["Vector"])
        vo.inputs["Randomness"].default_value = 1.0
        sq = N.new("ShaderNodeMapRange"); sq.inputs[1].default_value = 0.0; sq.inputs[2].default_value = 0.75; sq.inputs[3].default_value = 1.0; sq.inputs[4].default_value = 0.0
        L.new(vo.outputs["Distance"], sq.inputs[0])
        ga = N.new("ShaderNodeSeparateColor"); L.new(a.outputs["Color"], ga.inputs[0])   # Gruenanteil > Rot = Wald
        fo = N.new("ShaderNodeMath"); fo.operation = "SUBTRACT"; L.new(ga.outputs[1], fo.inputs[0]); L.new(ga.outputs[0], fo.inputs[1])
        fm = N.new("ShaderNodeMapRange"); fm.inputs[1].default_value = 0.0; fm.inputs[2].default_value = 0.08; L.new(fo.outputs[0], fm.inputs[0])
        dk = N.new("ShaderNodeMapRange"); dk.inputs[3].default_value = 0.45; dk.inputs[4].default_value = 1.15; L.new(sq.outputs[0], dk.inputs[0])
        one = N.new("ShaderNodeMix"); one.data_type = "FLOAT"; L.new(fm.outputs[0], one.inputs[0]); one.inputs[2].default_value = 1.0; L.new(dk.outputs[0], one.inputs[3])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 6; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        vm = N.new("ShaderNodeVectorMath"); vm.operation = "SCALE"; L.new(a.outputs["Color"], vm.inputs[0]); L.new(one.outputs[0], vm.inputs["Scale"])
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 0.25
        L.new(vm.outputs[0], mx.inputs[6]); L.new(nz.outputs["Color"], mx.inputs[7]); L.new(mx.outputs[2], b.inputs["Base Color"])
        h = N.new("ShaderNodeMath"); h.operation = "MULTIPLY"; L.new(sq.outputs[0], h.inputs[0]); L.new(fm.outputs[0], h.inputs[1])
        bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.8; bm.inputs["Distance"].default_value = 1.5; L.new(h.outputs[0], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"])
    terr.data.materials.append(_attr_mat("island_ground", "col", 0.9, tex))
    # Wasser: Farbe nach Tiefe (Tuerkis -> Tiefblau), Schaumkranz an der Kueste, bewegte Wellen
    SH, MID, DEEP = lin("52e3d2"), lin("1fb0d6"), lin("1468b8")
    def wcol(x, y, z):
        d = -_isl_h(x, y)
        c = _mixc(SH, MID, _smooth(0.0, 2.5, d)); c = _mixc(c, DEEP, _smooth(2.5, 7.0, d)); return (*c, 1)
    def wfoam(x, y, z):
        d = -_isl_h(x, y); f = max(0.0, 1 - abs(d - 0.35) / 0.55) + 0.55 * max(0.0, 1 - abs(d - 1.4) / 0.35); return (f, f, f, 1)
    def wmat(m, N, L, b, a):
        b.inputs["Roughness"].default_value = 0.05; b.inputs["Specular IOR Level"].default_value = 0.6
        fa = N.new("ShaderNodeAttribute"); fa.attribute_name = "foam"
        nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = 1.4; nz.inputs["Detail"].default_value = 6
        nz.inputs["W"].default_value = 0; nz.inputs["W"].keyframe_insert("default_value", frame=1); nz.inputs["W"].default_value = frames / 30 * 0.6; nz.inputs["W"].keyframe_insert("default_value", frame=frames)
        mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(fa.outputs["Fac"], mul.inputs[0]); L.new(nz.outputs["Fac"], mul.inputs[1])
        st = N.new("ShaderNodeMapRange"); st.inputs[1].default_value = 0.28; st.inputs[2].default_value = 0.42; L.new(mul.outputs[0], st.inputs[0])
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(st.outputs[0], mx.inputs[0]); L.new(a.outputs["Color"], mx.inputs[6]); mx.inputs[7].default_value = (0.95, 0.98, 1, 1)
        L.new(mx.outputs[2], b.inputs["Base Color"])
        rr = N.new("ShaderNodeMapRange"); L.new(st.outputs[0], rr.inputs[0]); rr.inputs[3].default_value = 0.05; rr.inputs[4].default_value = 0.8; L.new(rr.outputs[0], b.inputs["Roughness"])
        w2 = N.new("ShaderNodeTexNoise"); w2.noise_dimensions = "4D"; w2.inputs["Scale"].default_value = 9; w2.inputs["Detail"].default_value = 4
        w2.inputs["W"].default_value = 0; w2.inputs["W"].keyframe_insert("default_value", frame=1); w2.inputs["W"].default_value = frames / 30 * 0.8; w2.inputs["W"].keyframe_insert("default_value", frame=frames)
        bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.12; L.new(w2.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs[0], b.inputs["Normal"])
    sea = _grid("sea", -330, 330, -230, 230, 330, 230, lambda x, y: 0.0, {"col": wcol, "foam": wfoam})
    sea.data.materials.append(_attr_mat("sea_near", "col", 0.05, wmat)); sea.visible_shadow = False
    fm = _water("1468b8"); far = sets._prim("plane", (0, 0, -1.5), mat=fm, size=40000); far.visible_shadow = False
    N = fm.node_tree.nodes; L = fm.node_tree.links; cd = N.new("ShaderNodeCameraData"); hz = N.new("ShaderNodeMapRange"); hz.inputs[1].default_value = 350; hz.inputs[2].default_value = 5000; N["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.25
    L.new(cd.outputs["View Distance"], hz.inputs[0]); em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = mats.lin("bfe9ff"); mxs = N.new("ShaderNodeMixShader")
    out = N["Material Output"]; L.new(hz.outputs[0], mxs.inputs[0]); L.new(N["Principled BSDF"].outputs[0], mxs.inputs[1]); L.new(em.outputs[0], mxs.inputs[2]); L.new(mxs.outputs[0], out.inputs["Surface"])
    _sky_gradient("2b78dc", "bfe9ff")
    sc = bpy.context.scene; sc.eevee.volumetric_end = 1200; sc.eevee.volumetric_tile_size = "4"; sc.eevee.volumetric_samples = 96
    _boat(frames)
    # Wald: Palmen + Laubbaeume als Instanzen (Geometry Nodes), nur auf Land oberhalb des Strands
    rnd = random.Random(7); pts = []
    names = sorted(["PalmTree_1", "PalmTree_2", "PalmTree_3", "PalmTree_4", "PalmTree_5", "NormalTree_1", "NormalTree_2", "NormalTree_3", "NormalTree_4", "Bush_Large"])
    PALM = [i for i, n in enumerate(names) if n.startswith("Palm")]; LEAF = [i for i, n in enumerate(names) if not n.startswith("Palm")]   # Collection Info sortiert alphabetisch
    for _ in range(200000):   # Palmenguertel an der Kueste dicht, im Inneren lockere grosse Kronen (Kronendach-Textur fuellt den Rest)
        x, y = rnd.uniform(-240, 240), rnd.uniform(-130, 130); z = _isl_h(x, y)
        if z < 1.1: continue
        coast = z < 4.5
        if not coast and rnd.random() > 0.22: continue
        palm = coast or rnd.random() < 0.3; kind = rnd.choice(PALM if palm else LEAF)
        pts.append((x, y, z - 0.2, kind, rnd.uniform(0, 6.283), rnd.uniform(1.6, 2.4) if palm else rnd.uniform(2.6, 3.6)))
        if len(pts) >= 6500: break
    _instances("forest", pts, names)
    _clouds(frames)
    GRADE.clear(); GRADE.update(lift=(0.98, 0.99, 1.03), gain=(1.05, 1.02, 0.96), sat=1.12)

def _sky_gradient(top, horizon):
    """Kamera sieht einen kraeftigen Verlaufshimmel, Licht/Reflexe kommen weiter vom HDRI."""
    w = bpy.context.scene.world; N = w.node_tree.nodes; L = w.node_tree.links; out = N["World Output"]
    old = out.inputs["Surface"].links[0].from_socket
    tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sp.inputs[0])
    rp = N.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = tuple(mats.lin(horizon))[:3] + (1,)
    rp.color_ramp.elements[1].position = 0.45; rp.color_ramp.elements[1].color = tuple(mats.lin(top))[:3] + (1,); L.new(sp.outputs["Z"], rp.inputs[0])
    bg = N.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 1.0; L.new(rp.outputs[0], bg.inputs[0])
    lp = N.new("ShaderNodeLightPath"); mx = N.new("ShaderNodeMixShader"); L.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    L.new(old, mx.inputs[1]); L.new(bg.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])

def _boat(frames, a=(-6, -205), b=(10, -128)):
    """Graues Landungsboot (prozedural) mit V-foermigem Kielwasser faehrt auf die Kueste zu. a/b in Blender-xy."""
    import bmesh
    A, B = Vector((*a, 0)), Vector((*b, 0)); d = (B - A).normalized(); yaw = math.atan2(d.y, d.x) - math.pi / 2
    root = bpy.data.objects.new("boat", None); bpy.context.scene.collection.objects.link(root); root.rotation_euler = (0, 0, yaw)
    bm = bmesh.new()   # Rumpf: Kasten, Bug (lokal +y) verjuengt und angehoben
    for x, y, z in [(-2, -6, -0.6), (2, -6, -0.6), (2, 4, -0.6), (-2, 4, -0.6), (-2.3, -6.5, 1.2), (2.3, -6.5, 1.2), (2.2, 4.5, 1.3), (-2.2, 4.5, 1.3), (0, 7.5, 1.4), (0, 6.2, -0.3)]:
        bm.verts.new((x, y, z))
    bm.verts.ensure_lookup_table(); V = bm.verts
    for f in [(0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 6, 2), (3, 2, 9), (2, 6, 8, 9), (3, 9, 8, 7), (0, 3, 7, 4)]: bm.faces.new([V[i] for i in f])
    bm.normal_update(); me = bpy.data.meshes.new("hull"); bm.to_mesh(me); hull = bpy.data.objects.new("hull", me); bpy.context.scene.collection.objects.link(hull); hull.parent = root
    hm = bpy.data.materials.new("hull"); hm.use_nodes = True; hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mats.lin("6d7a73"); hm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    me.materials.append(hm)
    for loc, sc_, col in [((0, -4.0, 2.0), (1.4, 1.2, 0.8), "5a665f"), ((0, 1.2, 1.35), (1.9, 3.0, 0.08), "3e4a44"), ((0, -4.0, 3.0), (0.25, 0.25, 0.4), "2a2a2a")]:
        o = sets._prim("cube", loc, sc_, mat=sets._pmat("boat" + col, col)); o.parent = root
    # Kielwasser (Weltkoordinaten, nicht geparentet): V hinter dem Boot, Schaum an den Raendern, nach hinten auslaufend
    wm = bpy.data.materials.new("wake"); wm.use_nodes = True; N = wm.node_tree.nodes; L = wm.node_tree.links; N.remove(N["Principled BSDF"])
    em = N.new("ShaderNodeBsdfDiffuse"); em.inputs["Color"].default_value = (1, 1, 1, 1); tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
    tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 30; nz.inputs["Detail"].default_value = 8; nz.inputs["Roughness"].default_value = 0.7; L.new(tc.outputs["UV"], nz.inputs["Vector"])
    e = N.new("ShaderNodeMath"); e.operation = "SUBTRACT"; L.new(sp.outputs["X"], e.inputs[0]); e.inputs[1].default_value = 0.5
    wd = N.new("ShaderNodeMath"); wd.operation = "MULTIPLY_ADD"; L.new(sp.outputs["Y"], wd.inputs[0]); wd.inputs[1].default_value = 0.42; wd.inputs[2].default_value = 0.08
    dv = N.new("ShaderNodeMath"); dv.operation = "DIVIDE"; L.new(e.outputs[0], dv.inputs[0]); L.new(wd.outputs[0], dv.inputs[1])
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L.new(dv.outputs[0], ab.inputs[0])   # 0 = Mitte, 1 = Rand des V
    r1 = N.new("ShaderNodeFloatCurve"); cu = r1.mapping.curves[0]; cu.points[0].location = (0, 0.25); cu.points[1].location = (1, 0.0)
    cu.points.new(0.72, 0.05); cu.points.new(0.9, 1.0); r1.mapping.update(); L.new(ab.outputs[0], r1.inputs["Value"])   # schaumige Raender, lockere Mitte
    fv = N.new("ShaderNodeMapRange"); fv.inputs[3].default_value = 1; fv.inputs[4].default_value = 0; L.new(sp.outputs["Y"], fv.inputs[0])
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; L.new(r1.outputs[0], m1.inputs[0]); L.new(fv.outputs[0], m1.inputs[1])
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; L.new(m1.outputs[0], m2.inputs[0]); L.new(nz.outputs["Fac"], m2.inputs[1])
    m3 = N.new("ShaderNodeMapRange"); m3.inputs[1].default_value = 0.12; m3.inputs[2].default_value = 0.45; L.new(m2.outputs[0], m3.inputs[0])
    L.new(m3.outputs[0], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N["Material Output"].inputs["Surface"])
    if hasattr(wm, "surface_render_method"): wm.surface_render_method = "BLENDED"
    me = bpy.data.meshes.new("wake"); me.from_pydata([(-2.2, 5.5, 0), (2.2, 5.5, 0), (16, -80, 0), (-16, -80, 0)], [], [(3, 2, 1, 0)])
    uv = me.uv_layers.new(name="UV")
    for li, vi in enumerate(me.polygons[0].vertices): uv.data[li].uv = {0: (0.42, 0), 1: (0.58, 0), 2: (1, 1), 3: (0, 1)}[vi]
    wk = bpy.data.objects.new("wake", me); bpy.context.scene.collection.objects.link(wk); wk.parent = root; wk.location = (0, 0, 0.08)
    wk.data.materials.append(wm); wk.visible_shadow = False
    for f in (1, frames):
        root.location = A.lerp(B, (f - 1) / max(1, frames - 1)); root.keyframe_insert("location", frame=f)
    return root

def _instances(name, pts, names):
    """pts = [(x,y,z,kind,rotz,scale)] -> Punktwolke, per Geometry Nodes mit Quaternius-Objekten instanziert."""
    col = bpy.data.collections.new(name + "_src")
    for n in names:
        o = world.asset(n).copy(); o.location = (0, 0, 0); col.objects.link(o)
    me = bpy.data.meshes.new(name); me.from_pydata([p[:3] for p in pts], [], []); me.update()
    for an, typ, idx in (("kind", "INT", 3), ("rz", "FLOAT", 4), ("sc", "FLOAT", 5)):
        a = me.attributes.new(an, typ, "POINT")
        for k, p in enumerate(pts): a.data[k].value = p[idx]
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    g = bpy.data.node_groups.new(name + "_gn", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = g.nodes; L = g.links; gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    ci = N.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = col; ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True
    ip = N.new("GeometryNodeInstanceOnPoints"); ip.inputs["Pick Instance"].default_value = True
    def na(nm, dt):
        n = N.new("GeometryNodeInputNamedAttribute"); n.data_type = dt; n.inputs["Name"].default_value = nm; return n.outputs["Attribute"]
    L.new(gi.outputs[0], ip.inputs["Points"]); L.new(ci.outputs[0], ip.inputs["Instance"]); L.new(na("kind", "INT"), ip.inputs["Instance Index"])
    cx = N.new("ShaderNodeCombineXYZ"); L.new(na("rz", "FLOAT"), cx.inputs[2]); L.new(cx.outputs[0], ip.inputs["Rotation"]); L.new(na("sc", "FLOAT"), ip.inputs["Scale"])
    L.new(ip.outputs[0], go.inputs[0])
    m = o.modifiers.new("inst", "NODES"); m.node_group = g
    return o

def _clouds(frames):
    """Einige Volumenwolken in 38-55 m Hoehe; die Kamera sinkt an ihnen vorbei (Tiefe, Parallaxe)."""
    m = bpy.data.materials.new("cloud"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"])
    tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 6; nz.inputs["Roughness"].default_value = 0.6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    ln = N.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(tc.outputs["Object"], ln.inputs[0])
    fall = N.new("ShaderNodeMapRange"); fall.inputs[1].default_value = 0.55; fall.inputs[2].default_value = 1.0; fall.inputs[3].default_value = 1; fall.inputs[4].default_value = 0; L.new(ln.outputs["Value"], fall.inputs[0])
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; L.new(nz.outputs["Fac"], sub.inputs[0]); sub.inputs[1].default_value = 0.48
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(sub.outputs[0], mul.inputs[0]); L.new(fall.outputs[0], mul.inputs[1])
    den = N.new("ShaderNodeMath"); den.operation = "MULTIPLY"; den.use_clamp = False; L.new(mul.outputs[0], den.inputs[0]); den.inputs[1].default_value = 6.0
    pv = N.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (1, 1, 1, 1); pv.inputs["Anisotropy"].default_value = 0.3
    mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; L.new(den.outputs[0], mx.inputs[0]); mx.inputs[1].default_value = 0
    L.new(mx.outputs[0], pv.inputs["Density"]); L.new(pv.outputs[0], N["Material Output"].inputs["Volume"])
    rnd = random.Random(3)
    for k, (x, y, z, s) in enumerate([(-60, -250, 170, 45), (55, -280, 190, 50), (-70, -170, 120, 40), (70, -190, 135, 38), (-160, 40, 150, 70), (170, 80, 160, 70), (0, 300, 140, 90)]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x, y, z)); o = bpy.context.active_object; o.name = f"cloud{k}"
        o.scale = (s, s * 0.8, s * 0.42); o.data.materials.append(m); o.visible_shadow = True
        for f in (1, frames): o.location.x = x + (f - 1) / 30 * 2.5; o.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- Comic-"Poof": Wolkenbaellchen quellen auf und vergehen (Figur verschwindet)
def poof(at, frame, n=9, size=0.32, seed=1, color="eee6dc"):
    """at in Blender-Koordinaten (Koerpermitte). Ab frame quillt eine Wolke auf (~5 Bilder) und schrumpft weg (~14 Bilder)."""
    m = bpy.data.materials.get("poof_" + color) or sets._pmat("poof_" + color, color, 0.9, emit=0.35)
    rnd = random.Random(seed); out = []
    for i in range(n):
        a = i / n * 2 * math.pi + rnd.uniform(-0.3, 0.3); el = rnd.uniform(-0.6, 0.9)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el) * 1.3))
        r = size * rnd.uniform(0.7, 1.15)
        o = sets._prim("uv_sphere", at, mat=m, radius=1.0, segments=20, ring_count=12); o.visible_shadow = False; bpy.ops.object.shade_smooth()
        for f, k, sc_ in ((frame - 1, 0.0, 0.0), (frame, 0.15, 0.5), (frame + 4, 0.55, 1.0), (frame + 10, 0.85, 0.75), (frame + 18, 1.05, 0.0)):
            o.location = at + d * 0.45 * k + Vector((0, 0, 0.25 * k)); o.scale = (r * sc_,) * 3
            o.keyframe_insert("location", frame=max(1, f)); o.keyframe_insert("scale", frame=max(1, f))
        out.append(o)
    for i in range(6):   # kleine Funken/Sternchen
        a = rnd.uniform(0, 6.283); d = Vector((math.cos(a), math.sin(a), rnd.uniform(0.2, 1.0))).normalized()
        o = sets._prim("ico_sphere", at, mat=sets._pmat("poof_spark", "fff2b0", 0.5, emit=3.0), radius=1.0, subdivisions=1); o.visible_shadow = False
        for f, k, sc_ in ((frame - 1, 0.0, 0.0), (frame + 2, 0.4, 0.05), (frame + 12, 1.0, 0.03), (frame + 16, 1.1, 0.0)):
            o.location = at + d * 0.9 * k; o.scale = (sc_,) * 3; o.keyframe_insert("location", frame=max(1, f)); o.keyframe_insert("scale", frame=max(1, f))
    return out

def log_seat(pos3, yaw, length=0.8, r=0.17):
    """Liegender Rindenstamm als Sitz hinter einer sitzenden Figur (pos3 three-Achsen, yaw = Blickrichtung der Figur)."""
    fx, fz = math.sin(yaw), math.cos(yaw)
    c = tb((pos3[0] - fx * 0.12, 0, pos3[2] - fz * 0.12)) + Vector((0, 0, r))
    o = sets._prim("cylinder", c, mat=_bark(), radius=r, depth=length, vertices=20)
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector((math.cos(yaw), math.sin(yaw), 0)))
    return o
