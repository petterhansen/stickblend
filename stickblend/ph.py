"""Realistische Umgebung mit Poly-Haven-Assets (CC0): Modelle, Bodentexturen, HDRI, Feuer, Funken, Rauch, Farbgebung.
Assets laden: python stickblend/tools/polyhaven.py <id> ...  -> assets3d/polyhaven/<typ>/<id>/
"""
import bpy, os, glob, math, random
from mathutils import Vector, Euler
from . import mats, world, paths

PH = paths.POLYHAVEN
_models = {}

def _hidden():
    if "ph_assets" in bpy.data.collections: return bpy.data.collections["ph_assets"]
    c = bpy.data.collections.new("ph_assets"); bpy.context.scene.collection.children.link(c); c.hide_render = True; c.hide_viewport = True
    return c

def model(aid):
    """glTF einmal importieren -> Liste der Mesh-Objekte (versteckt). Transformationen werden eingebacken,
    die Teile behalten ihre Lage zueinander (Verschluss/Abzug bleiben am Gewehr)."""
    if aid in _models: return _models[aid]
    f = glob.glob(os.path.join(PH, "models", aid, "*.gltf"))[0]
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]; hc = _hidden()
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        hc.objects.link(o)
    meshes = [o for o in new if o.type == "MESH"]
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None
        o.data = o.data.copy(); o.data.transform(mw); o.matrix_world.identity()
    _models[aid] = meshes; return meshes

def _bbox(objs):
    vs = [v.co for o in objs for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return lo, hi

def place(aid, loc, rot_z=0.0, scale=1.0, part=None, coll=None, rot=None, exclude=(), keep_origin=False):
    """Kopie (teilt Meshes) eines Modells bzw. eines Teils (Index oder Namensteil) platzieren. loc in Blender-Koordinaten.
    Standard: Ursprung = Unterkante-Mitte der gewaehlten Teile (steht auf dem Boden). keep_origin=True: Original-Ursprung des Modells."""
    ms = model(aid)
    if part is not None: ms = [m for i, m in enumerate(ms) if (i == part if isinstance(part, int) else part in m.name)]
    ms = [m for m in ms if not any(x in m.name for x in exclude)]
    if keep_origin: off = Vector((0, 0, 0))
    else:
        lo, hi = _bbox(ms); off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    C = coll or bpy.context.scene.collection
    root = bpy.data.objects.new(f"{aid}_inst", None); C.objects.link(root)
    root.location = Vector(loc); root.rotation_mode = "XYZ"; root.rotation_euler = rot or (0, 0, rot_z); root.scale = (scale,) * 3
    for m in ms:
        o = m.copy(); C.objects.link(o); o.parent = root; o.location = -off
    return root

def world_bounds(obj):
    """Return (min_vec, max_vec) in Blender world space for obj and all mesh descendants."""
    bpy.context.view_layer.update()
    objs = ([obj] if obj.type == "MESH" else []) + [c for c in obj.children_recursive if c.type == "MESH"]
    pts = [o.matrix_world @ Vector(b) for o in objs for b in o.bound_box]
    if not pts:
        return obj.location.copy(), obj.location.copy()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

def top_z(obj):
    """Exact world-space top surface Z of a placed table/console/desk/box."""
    return world_bounds(obj)[1].z

def place_on(aid, target_obj, offset_xy=(0.0, 0.0), rot_z=0.0, scale=1.0, part=None, coll=None):
    """Place a Poly Haven model flush on top of target_obj (zero floating or sinking)."""
    lo, hi = world_bounds(target_obj)
    cx, cy = (lo.x + hi.x) / 2.0 + offset_xy[0], (lo.y + hi.y) / 2.0 + offset_xy[1]
    return place(aid, (cx, cy, hi.z), rot_z=rot_z, scale=scale, part=part, coll=coll)

def textured_ground(tid="forest_leaves_02", size=40, tile=2.5, tint=(1, 1, 1), bump=0.6):
    d = os.path.join(PH, "textures", tid); fs = {k: (glob.glob(os.path.join(d, f"*{k}*")) or [None])[0] for k in ("diff", "nor_gl", "rough", "ao")}
    bpy.ops.mesh.primitive_plane_add(size=size); g = bpy.context.active_object; g.name = "ground"
    m = bpy.data.materials.new("ground_" + tid); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (size / tile,) * 3; L.new(tc.outputs["UV"], mp.inputs[0])
    def img(path, non_color=False):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
        if non_color: t.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs[0], t.inputs[0]); return t
    if fs["diff"]:
        dt = img(fs["diff"]); mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L.new(dt.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (*tint, 1); L.new(mul.outputs[2], b.inputs["Base Color"])
    if fs["rough"]: L.new(img(fs["rough"], True).outputs[0], b.inputs["Roughness"])
    if fs["nor_gl"]:
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump; L.new(img(fs["nor_gl"], True).outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], b.inputs["Normal"])
    g.data.materials.append(m); return g

def pbr(tid, scale=1.0, tint=(1, 1, 1), bump=0.7, metallic=0.0):
    """Box-projected Poly Haven PBR material (Diffuse + Roughness + Normal) for any 3D mesh."""
    key = f"pbr_{tid}_{scale:.2f}_{tint}"
    if key in bpy.data.materials: return bpy.data.materials[key]
    d = os.path.join(PH, "textures", tid)
    fs = {k: (glob.glob(os.path.join(d, f"*{k}*")) or [None])[0] for k in ("diff", "nor_gl", "rough")}
    m = bpy.data.materials.new(key); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    b.inputs["Metallic"].default_value = metallic
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale,) * 3; L.new(tc.outputs["Object"], mp.inputs[0])
    def img(path, non_color=False):
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.projection = "BOX"; t.projection_blend = 0.2
        if non_color: t.image.colorspace_settings.name = "Non-Color"
        L.new(mp.outputs[0], t.inputs[0]); return t
    if fs["diff"]:
        dt = img(fs["diff"]); mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L.new(dt.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (*tint, 1); L.new(mul.outputs[2], b.inputs["Base Color"])
    if fs["rough"]: L.new(img(fs["rough"], True).outputs[0], b.inputs["Roughness"])
    if fs["nor_gl"]:
        nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump; L.new(img(fs["nor_gl"], True).outputs[0], nm.inputs["Color"]); L.new(nm.outputs[0], b.inputs["Normal"])
    return m

def hdri(hid="rogland_clear_night", strength=0.35, rot=0.0):
    f = glob.glob(os.path.join(PH, "hdris", hid, "*.hdr"))[0]
    sc = bpy.context.scene; w = bpy.data.worlds.new("hdri"); sc.world = w; w.use_nodes = True; N = w.node_tree.nodes; L = w.node_tree.links
    env = N.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(f, check_existing=True)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, rot)
    L.new(tc.outputs["Generated"], mp.inputs[0]); L.new(mp.outputs[0], env.inputs[0])
    L.new(env.outputs[0], N["Background"].inputs[0]); N["Background"].inputs[1].default_value = strength
    return w

# ---------------------------------------------------------------- Feuer
def _flame_mat():
    if "flame" in bpy.data.materials: return bpy.data.materials["flame"]
    m = bpy.data.materials.new("flame"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"])
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    # Flammenform: unten breit, oben spitz, mit animiertem Rauschen
    nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = 4.0; nz.inputs["Detail"].default_value = 3
    tm = N.new("ShaderNodeValue"); tm.name = "time"; L.new(tm.outputs[0], nz.inputs["W"])
    mp = N.new("ShaderNodeMapping"); L.new(tc.outputs["UV"], mp.inputs[0]); L.new(mp.outputs[0], nz.inputs["Vector"])
    cx = N.new("ShaderNodeMath"); cx.operation = "SUBTRACT"; L.new(sep.outputs["X"], cx.inputs[0]); cx.inputs[1].default_value = 0.5
    ax = N.new("ShaderNodeMath"); ax.operation = "ABSOLUTE"; L.new(cx.outputs[0], ax.inputs[0])
    wd = N.new("ShaderNodeMath"); wd.operation = "MULTIPLY_ADD"; L.new(sep.outputs["Y"], wd.inputs[0]); wd.inputs[1].default_value = -0.42; wd.inputs[2].default_value = 0.46   # Breite nimmt nach oben ab
    nn = N.new("ShaderNodeMath"); nn.operation = "MULTIPLY_ADD"; L.new(nz.outputs["Fac"], nn.inputs[0]); nn.inputs[1].default_value = 0.25; nn.inputs[2].default_value = -0.12
    wd2 = N.new("ShaderNodeMath"); wd2.operation = "ADD"; L.new(wd.outputs[0], wd2.inputs[0]); L.new(nn.outputs[0], wd2.inputs[1])
    msk = N.new("ShaderNodeMath"); msk.operation = "SUBTRACT"; L.new(wd2.outputs[0], msk.inputs[0]); L.new(ax.outputs[0], msk.inputs[1])
    sm = N.new("ShaderNodeMapRange"); sm.inputs["From Min"].default_value = 0.0; sm.inputs["From Max"].default_value = 0.08; L.new(msk.outputs[0], sm.inputs["Value"])
    ramp = N.new("ShaderNodeValToRGB"); el = ramp.color_ramp.elements
    el[0].position = 0.0; el[0].color = (1.0, 0.18, 0.02, 1); el[1].position = 1.0; el[1].color = (1.0, 0.95, 0.6, 1)
    mid = el.new(0.55); mid.color = (1.0, 0.55, 0.08, 1)
    hy = N.new("ShaderNodeMath"); hy.operation = "SUBTRACT"; hy.inputs[0].default_value = 1.0; L.new(sep.outputs["Y"], hy.inputs[1])
    cm = N.new("ShaderNodeMath"); cm.operation = "MULTIPLY"; L.new(sm.outputs[0], cm.inputs[0]); L.new(hy.outputs[0], cm.inputs[1])
    L.new(cm.outputs[0], ramp.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 6.0; L.new(ramp.outputs[0], em.inputs[0])
    tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader"); L.new(sm.outputs[0], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], N["Material Output"].inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    return m

def fire(at, frames, scale=1.0, light=220.0, seed=3):
    """Feuer: gekreuzte Flammenkarten mit animiertem Rauschen, flackerndes Punktlicht (Schatten), Glut, aufsteigende Funken."""
    sc = bpy.context.scene; p = Vector(at); rnd = random.Random(seed); fm = _flame_mat()
    for k in range(3):
        bpy.ops.mesh.primitive_plane_add(size=1, location=p + Vector((0, 0, 0.42 * scale)), rotation=(math.pi / 2, 0, k * math.pi / 3))
        o = bpy.context.active_object; o.scale = (0.7 * scale, 0.85 * scale, 1); o.data.materials.append(fm); o.visible_shadow = False; o.name = "flame%d" % k
    tm = fm.node_tree.nodes["time"]
    for f in range(1, frames + 1, 1):
        tm.outputs[0].default_value = f / 30 * 1.6; tm.outputs[0].keyframe_insert("default_value", frame=f)
    L = bpy.data.lights.new("fire", "POINT"); L.color = (1.0, 0.5, 0.2); L.shadow_soft_size = 0.25 * scale
    lo = bpy.data.objects.new("fire", L); sc.collection.objects.link(lo); lo.location = p + Vector((0, 0, 0.5 * scale))
    for f in range(1, frames + 1, 2):
        t = f / 30; fl = 0.82 + 0.18 * math.sin(t * 17) * math.sin(t * 7.3 + 1) + 0.05 * math.sin(t * 31)
        L.energy = light * fl; L.keyframe_insert("energy", frame=f)
    glow = bpy.data.materials.new("ember"); glow.use_nodes = True; Nn = glow.node_tree.nodes; Nn.remove(Nn["Principled BSDF"])
    e = Nn.new("ShaderNodeEmission"); e.inputs[0].default_value = (1.0, 0.45, 0.08, 1); e.inputs[1].default_value = 18
    glow.node_tree.links.new(e.outputs[0], Nn["Material Output"].inputs[0])
    for i in range(40):   # Funken: steigen spiralig auf, verglimmen
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.008 * scale, location=p); s = bpy.context.active_object; s.data.materials.append(glow); s.visible_shadow = False
        ph0 = rnd.random() * 2.0; sp = 0.6 + rnd.random() * 0.6; ang = rnd.random() * 6.28; rr = 0.08 + rnd.random() * 0.15
        for f in range(1, frames + 1, 2):
            tt = (f / 30 + ph0) % 2.0; h = tt * sp
            s.location = p + Vector((math.cos(ang + tt * 2) * rr * (1 + tt), math.sin(ang + tt * 2) * rr * (1 + tt), 0.3 * scale + h))
            k = max(0.0, 1 - tt / 2.0); s.scale = (k,) * 3
            s.keyframe_insert("location", frame=f); s.keyframe_insert("scale", frame=f)
    return lo

def smoke(at, frames, n=5, color=(0.35, 0.36, 0.4), seed=5):
    """Duenne Rauchschwaden: weiche Rauschkarten, steigen langsam und blenden aus."""
    m = bpy.data.materials.new("smoke"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"])
    tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.5; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    gr = N.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"; L.new(tc.outputs["Object"], gr.inputs["Vector"])
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L.new(nz.outputs["Fac"], mul.inputs[0]); L.new(gr.outputs["Fac"], mul.inputs[1])
    a = N.new("ShaderNodeMath"); a.operation = "MULTIPLY"; L.new(mul.outputs[0], a.inputs[0]); a.inputs[1].default_value = 0.55
    em = N.new("ShaderNodeBsdfDiffuse"); em.inputs[0].default_value = (*color, 1); tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
    L.new(a.outputs[0], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], N["Material Output"].inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    rnd = random.Random(seed); p = Vector(at)
    for i in range(n):
        bpy.ops.mesh.primitive_plane_add(size=1.2, location=p, rotation=(math.pi / 2, 0, rnd.random() * 0.6 - 0.3)); o = bpy.context.active_object; o.data.materials.append(m); o.visible_shadow = False
        ph0 = rnd.random() * 4
        for f in range(1, frames + 1, 3):
            tt = (f / 30 + ph0) % 4.0; o.location = p + Vector((math.sin(tt + i) * 0.15, 0, 0.9 + tt * 0.45)); s = 0.6 + tt * 0.35; o.scale = (s, s, s)
            o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)

def grade(contrast=0.12, lift=(0.96, 0.98, 1.06), gain=(1.06, 1.0, 0.94), vignette=0.35, bloom=(0.85, 0.45, 7), sat=1.0):
    """Farbgebung im Compositor: Gluehen, Lift/Gain (kuehle Schatten, warme Lichter), Kontrast, Vignette."""
    sc = bpy.context.scene
    g = bpy.data.node_groups.new("grade", "CompositorNodeTree"); g.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N = g.nodes; L = g.links; rl = N.new("CompositorNodeRLayers"); out = N.new("NodeGroupOutput"); cur = rl.outputs["Image"]
    def setin(node, name, val):
        if name in node.inputs:
            try: node.inputs[name].default_value = val
            except Exception as e: print("grade", name, e)
    gl = N.new("CompositorNodeGlare")
    for k, v in (("glare_type", "BLOOM"),):
        try: setattr(gl, k, v)
        except Exception: pass
    setin(gl, "Type", "Bloom"); setin(gl, "Threshold", bloom[0]); setin(gl, "Strength", bloom[1]); setin(gl, "Size", bloom[2])
    L.new(cur, gl.inputs["Image"]); cur = gl.outputs["Image"]
    cb = N.new("CompositorNodeColorBalance")   # 5.x: Lift/Gain gibt es als Wert- und als Farb-Eingang -> den Farb-Eingang nehmen
    for nm, v in (("Lift", (*lift, 1)), ("Gain", (*gain, 1))):
        for sck in cb.inputs:
            if sck.name == nm and sck.type == "RGBA": sck.default_value = v
    L.new(cur, cb.inputs["Image"]); cur = cb.outputs["Image"]
    if sat != 1.0:   # Saettigung (Referenz: kraeftige Farben, nichts Graues)
        hs = N.new("CompositorNodeHueSat"); setin(hs, "Saturation", sat)
        L.new(cur, hs.inputs["Image"]); cur = hs.outputs["Image"]
    bc = N.new("CompositorNodeBrightContrast"); setin(bc, "Contrast", contrast * 100 if "Contrast" in bc.inputs and bc.inputs["Contrast"].default_value > 1 else contrast)
    L.new(cur, bc.inputs["Image"]); cur = bc.outputs["Image"]
    if vignette:
        em = N.new("CompositorNodeEllipseMask"); setin(em, "Size", (0.95, 0.75))
        try: em.width, em.height = 0.95, 0.75
        except Exception: pass
        bl = N.new("CompositorNodeBlur"); setin(bl, "Size", (200, 200))
        try: bl.size_x = bl.size_y = 200
        except Exception: pass
        L.new(em.outputs[0], bl.inputs["Image"])
        mr = N.new("CompositorNodeMapRange") if hasattr(bpy.types, "CompositorNodeMapRange") else None
        mx = N.new("CompositorNodeMixRGB") if hasattr(bpy.types, "CompositorNodeMixRGB") else N.new("ShaderNodeMix")
        try:
            mx.blend_type = "MULTIPLY"
            fac_in, a_in, b_in = mx.inputs[0], mx.inputs[1], mx.inputs[2]
            if mx.bl_idname == "ShaderNodeMix": mx.data_type = "RGBA"; fac_in, a_in, b_in = mx.inputs[0], mx.inputs[6], mx.inputs[7]
            fac_in.default_value = vignette; L.new(cur, a_in); L.new(bl.outputs[0], b_in); cur = mx.outputs[0] if mx.bl_idname != "ShaderNodeMix" else mx.outputs[2]
        except Exception as e: print("vignette", e)
    L.new(cur, out.inputs[0]); sc.compositing_node_group = g
