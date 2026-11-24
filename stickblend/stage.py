"""Buehne, Kamera und Render-Presets."""
import bpy, math
from mathutils import Vector
from . import mats

PRESETS = {
    # Aufloesung immer 1080x1920 (9:16); percent skaliert fuer Vorschau
    "preview": dict(percent=50, spp=6, raytracing=False),
    "final": dict(percent=100, spp=16, raytracing=False),
    "final_hq": dict(percent=100, spp=32, raytracing=True),
}

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats._cache.clear()
    from . import world, ph
    world._cache.clear(); ph._models.clear()   # Objekt-Referenzen sind nach dem Reset ungueltig
    prefs = bpy.context.preferences.edit
    prefs.keyframe_new_interpolation_type = "CONSTANT"   # Figuren "auf Zweiern": Keys halten bis zum naechsten

def render_setup(preset="preview", fps=30, out=None):
    sc = bpy.context.scene; P = PRESETS[preset]
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 1080; sc.render.resolution_y = 1920
    sc.render.resolution_percentage = P["percent"]; sc.render.fps = fps
    ee = sc.eevee; ee.taa_render_samples = P["spp"]; ee.use_shadows = True; ee.use_raytracing = P["raytracing"]; ee.use_fast_gi = P["raytracing"]
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.compression = 15
    if out: sc.render.filepath = out
    return sc

def studio(floor="d9c9a8", wall="efe4cf", warm=True):
    """Neutrale Testbuehne: Boden, Hohlkehle, Key-Licht mit Schatten, Fuelllicht."""
    sc = bpy.context.scene
    def mat(h):
        m = bpy.data.materials.new("stage_" + h); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mats.lin(h)
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9; return m
    bpy.ops.mesh.primitive_plane_add(size=40); fl = bpy.context.active_object; fl.data.materials.append(mat(floor))
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 6, 20), rotation=(math.pi / 2, 0, 0)); w = bpy.context.active_object; w.data.materials.append(mat(wall))
    sun = bpy.data.lights.new("key", "SUN"); sun.energy = 3.2; sun.angle = 0.12; sun.color = (1.0, 0.93, 0.82) if warm else (1, 1, 1)
    so = bpy.data.objects.new("key", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(48), 0, math.radians(-32))
    fill = bpy.data.lights.new("fill", "AREA"); fill.energy = 300; fill.size = 6; fill.color = (0.8, 0.85, 1.0)
    fo = bpy.data.objects.new("fill", fill); sc.collection.objects.link(fo); fo.location = (4, -6, 4); fo.rotation_euler = (math.radians(60), 0, math.radians(35))
    wd = bpy.data.worlds.new("w"); sc.world = wd; wd.use_nodes = True; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.65, 1); wd.node_tree.nodes["Background"].inputs[1].default_value = 0.6

def camera(loc, look, lens=35, dof=None):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("cam"); c = bpy.data.objects.new("cam", cd); sc.collection.objects.link(c); sc.camera = c
    cd.lens = lens; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24; cd.clip_start = 0.05; cd.clip_end = 300
    c.location = Vector(loc); c.rotation_mode = "QUATERNION"; c.rotation_quaternion = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y")
    if dof:
        cd.dof.use_dof = True; cd.dof.focus_distance = (Vector(look) - Vector(loc)).length; cd.dof.aperture_fstop = dof
    return c
