"""Welten fuer die Shorts: Asset-Kits direkt in Blender laden, effizient platzieren, Licht/Dunst/Gluehen im Referenzstil.

Grundsaetze (Renderzeit!):
  - Asset einmal anhaengen (versteckte Sammlung "assets"), Platzierungen als verlinkte Kopien (teilen sich Mesh-Daten).
  - Keine Line Art in der Umgebung (Referenz: Linien nur an Figuren).
  - Tiefe ueber Tiefenschaerfe, Dunst und Vordergrund-Elemente.
"""
import bpy, math, random
from mathutils import Vector
from . import mats, paths

QUAT = paths.QUAT
KENNEY_NATURE = paths.KENNEY_NATURE

def _assets_coll():
    if "assets" in bpy.data.collections: return bpy.data.collections["assets"]
    c = bpy.data.collections.new("assets"); bpy.context.scene.collection.children.link(c)
    c.hide_render = True; c.hide_viewport = True
    return c

_cache = {}
def asset(name, lib=QUAT):
    """Objekt aus einer .blend-Bibliothek anhaengen (einmalig) und zurueckgeben."""
    if name in _cache: return _cache[name]
    with bpy.data.libraries.load(lib, link=False) as (src, dst): dst.objects = [name]
    o = dst.objects[0]; _assets_coll().objects.link(o)
    o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0)
    _cache[name] = o; return o

def place(name, loc, rot_z=0.0, scale=1.0, coll=None, lib=QUAT):
    src = asset(name, lib); o = src.copy()  # verlinkte Kopie: teilt Mesh + Materialien
    (coll or bpy.context.scene.collection).objects.link(o)
    o.location = Vector(loc); o.rotation_euler = (src.rotation_euler.x, src.rotation_euler.y, rot_z)
    s = src.scale; o.scale = (s.x * scale, s.y * scale, s.z * scale)
    return o

def scatter(names, n, area, avoid=None, scale=(0.8, 1.3), seed=1, coll=None):
    """n Objekte zufaellig in area=(x0,x1,y0,y1) (Blender-Koordinaten), avoid(x,y)->True = frei halten."""
    rnd = random.Random(seed); out = []
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        x = rnd.uniform(area[0], area[1]); y = rnd.uniform(area[2], area[3])
        if avoid and avoid(x, y): continue
        out.append(place(rnd.choice(names), (x, y, 0), rnd.uniform(0, 6.283), rnd.uniform(*scale), coll))
    return out

def keep_clear(cam_path, subjects, radius=0.6, near=1.8):
    """Sichtfreiheit (wie in three.js): Punkt frei halten, wenn er nahe an einer Sichtlinie Kamera->Figur oder direkt vor der Linse liegt."""
    segs = [(Vector(c), Vector(s)) for c in cam_path for s in subjects]
    def avoid(x, y):
        p = Vector((x, y, 0))
        for a, b in segs:
            a2, b2 = Vector((a.x, a.y, 0)), Vector((b.x, b.y, 0)); d = b2 - a2; L = d.length_squared or 1
            u = max(0, min(1, (p - a2).dot(d) / L))
            if (p - (a2 + d * u)).length < radius: return True
            if (p - a2).length < near: return True
        return False
    return avoid

def ground(color="5d7a3a", size=60, var="4a6630"):
    """Boden mit leichter Farbvariation (Noise), matt."""
    bpy.ops.mesh.primitive_plane_add(size=size); g = bpy.context.active_object; g.name = "ground"
    m = bpy.data.materials.new("ground"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.95
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 3
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = mats.lin(var); ramp.color_ramp.elements[1].color = mats.lin(color)
    L.new(nz.outputs["Fac"], ramp.inputs[0]); L.new(ramp.outputs[0], b.inputs["Base Color"])
    g.data.materials.append(m); return g

def sky(top="7fb6e6", horizon="f3e6c4", strength=1.0, haze=0.0, haze_color=(1.0, 0.95, 0.85)):
    """Himmelsverlauf als Welt + optionaler Volumen-Dunst (Lichtstrahlen durch die Sonne)."""
    sc = bpy.context.scene; w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    N = w.node_tree.nodes; L = w.node_tree.links; bg = N["Background"]; bg.inputs[1].default_value = strength
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = mats.lin(horizon)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = mats.lin(top)
    L.new(sep.outputs["Z"], ramp.inputs[0]); L.new(ramp.outputs[0], bg.inputs[0])
    if haze > 0:  # Dunst als Volumen-Box um das Set (Welt-Volumen rendert in EEVEE 5.2 schwarz)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 12, 6)); bx = bpy.context.active_object; bx.name = "haze"
        bx.scale = (70, 70, 12); bx.visible_shadow = False
        m = bpy.data.materials.new("haze"); m.use_nodes = True; Nm = m.node_tree.nodes; Nm.remove(Nm["Principled BSDF"])
        vs = Nm.new("ShaderNodeVolumeScatter"); vs.inputs["Density"].default_value = haze; vs.inputs["Color"].default_value = (*haze_color, 1)
        vs.inputs["Anisotropy"].default_value = 0.55
        m.node_tree.links.new(vs.outputs[0], Nm["Material Output"].inputs["Volume"]); bx.data.materials.append(m)
        ee = sc.eevee; ee.volumetric_tile_size = __import__("os").environ.get("VTILE", "8"); ee.volumetric_samples = int(__import__("os").environ.get("VSAMP", 48)); ee.volumetric_end = 45
        if hasattr(ee, "use_volumetric_shadows"): ee.use_volumetric_shadows = True
    return w

def sun(dir_deg=(50, 0, -35), energy=4.0, color=(1.0, 0.92, 0.78), angle=0.06):
    l = bpy.data.lights.new("sun", "SUN"); l.energy = energy; l.color = color; l.angle = angle
    o = bpy.data.objects.new("sun", l); bpy.context.scene.collection.objects.link(o); o.rotation_euler = [math.radians(a) for a in dir_deg]
    return o

def glow(threshold=0.85, strength=0.5, size=6):
    """Gluehen (Bloom) per Compositor, Blender 5.x: scene.compositing_node_group."""
    sc = bpy.context.scene
    try:
        g = bpy.data.node_groups.new("comp", "CompositorNodeTree")
        g.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        N = g.nodes; L = g.links; rl = N.new("CompositorNodeRLayers"); out = N.new("NodeGroupOutput")
        gl = N.new("CompositorNodeGlare")
        for k, v in (("glare_type", "BLOOM"), ("quality", "HIGH")):
            try: setattr(gl, k, v)
            except Exception: pass
        for k, v in (("Type", "Bloom"), ("Threshold", threshold), ("Strength", strength), ("Size", size), ("Quality", "High")):
            if k in gl.inputs:
                try: gl.inputs[k].default_value = v
                except Exception as e: print("glare", k, e)
        L.new(rl.outputs["Image"], gl.inputs["Image"]); L.new(gl.outputs["Image"], out.inputs[0])
        sc.compositing_node_group = g
        return True
    except Exception as e:
        print("GLOW_FAIL", e); return False

def optimize_shadows(max_dist=9.0, cam=(0, 0, 0), res_scale=0.5, max_res=0.008, steps=2):
    """Schatten sind der groesste Renderkostenpunkt: ferne Objekte werfen keine Schatten, Schattenkarten groeber.
    max_dist = Abstand (m) zur Kamera, ab dem Objekte keine Schatten mehr werfen (ihre Schatten liegen ausserhalb des Bildes/im Dunst)."""
    sc = bpy.context.scene; ee = sc.eevee; c = Vector(cam)
    if hasattr(ee, "shadow_resolution_scale"): ee.shadow_resolution_scale = res_scale
    if hasattr(ee, "shadow_step_count"): ee.shadow_step_count = steps
    for o in sc.objects:
        if o.type == "LIGHT" and hasattr(o.data, "shadow_maximum_resolution"): o.data.shadow_maximum_resolution = max_res
        if o.type == "MESH" and o.name not in ("ground", "haze") and (Vector((o.location.x, o.location.y, 0)) - Vector((c.x, c.y, 0))).length > max_dist:
            o.visible_shadow = False
