"""Materialien im Referenzstil: flache 2D-Fuellung mit weicher Randschattierung + Lichtkante, braune Tuschekontur."""
import bpy
from mathutils import Color

STYLE = {
    "ink": "2a1822",          # Konturfarbe (dunkles Pflaume-Braun wie in der Referenz)
    "edge_dark": 0.72,        # Helligkeit der Randzone (Layer Weight Facing)
    "edge_width": 0.45,       # Breite der Randzone
    "rim_color": (1.0, 0.85, 0.6),
    "rim_strength": 0.0,      # 0 = aus; pro Szene setzen (z. B. Fensterlicht)
    "rim_dir": (-0.5, -0.4, 0.75),  # Weltrichtung, aus der das Kantenlicht kommt (Blender-Achsen)
    "tint": (1.0, 1.0, 1.0),  # Szenenfarbe (Nacht/Daemmerung)
}

def lin(h, a=1.0):
    h = h.lstrip("#"); c = Color([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]).from_srgb_to_scene_linear()
    return (c.r, c.g, c.b, a)

_cache = {}
def _globals_group():
    """Gemeinsame Node-Group: Tint + Kantenlicht, damit eine Szene alle Figuren auf einmal umstimmen kann."""
    if "SB_Scene" in bpy.data.node_groups: return bpy.data.node_groups["SB_Scene"]
    g = bpy.data.node_groups.new("SB_Scene", "ShaderNodeTree")
    io = g.interface
    io.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    io.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    N = g.nodes; L = g.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    tint = N.new("ShaderNodeRGB"); tint.name = "tint"; tint.outputs[0].default_value = (*STYLE["tint"], 1)
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
    L.new(gi.outputs[0], mul.inputs[6]); L.new(tint.outputs[0], mul.inputs[7])
    # Kantenlicht: Normal . Richtung, nur am Rand (Facing)
    geo = N.new("ShaderNodeNewGeometry"); dirn = N.new("ShaderNodeCombineXYZ"); dirn.name = "rim_dir"
    for i, v in enumerate(STYLE["rim_dir"]): dirn.inputs[i].default_value = v
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], dot.inputs[0]); L.new(dirn.outputs[0], dot.inputs[1])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.3
    m1 = N.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; L.new(dot.outputs["Value"], m1.inputs[0]); L.new(lw.outputs["Facing"], m1.inputs[1])
    st = N.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = 0.22; L.new(m1.outputs[0], st.inputs[0])
    rs = N.new("ShaderNodeValue"); rs.name = "rim_strength"; rs.outputs[0].default_value = STYLE["rim_strength"]
    m2 = N.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; L.new(st.outputs[0], m2.inputs[0]); L.new(rs.outputs[0], m2.inputs[1])
    rc = N.new("ShaderNodeRGB"); rc.name = "rim_color"; rc.outputs[0].default_value = (*STYLE["rim_color"], 1)
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "SCREEN"
    L.new(m2.outputs[0], mix.inputs[0]); L.new(mul.outputs[2], mix.inputs[6]); L.new(rc.outputs[0], mix.inputs[7])
    L.new(mix.outputs[2], go.inputs[0])
    return g

def set_scene_light(tint=(1, 1, 1), rim_strength=0.0, rim_color=(1, 0.85, 0.6), rim_dir=(-0.5, -0.4, 0.75)):
    g = _globals_group(); N = g.nodes
    N["tint"].outputs[0].default_value = (*tint, 1); N["rim_strength"].outputs[0].default_value = rim_strength
    N["rim_color"].outputs[0].default_value = (*rim_color, 1)
    for i, v in enumerate(rim_dir): N["rim_dir"].inputs[i].default_value = v

def flat(hexc, edge=True, name=None, pattern=None, pcol=None):
    """Flache Fuellung; Rand weich abgedunkelt (wie die Referenz), unbeleuchtet -> 2D-Look.
    pattern/pcol werden nur vom 2.5D-Ausschnitt (flat2d) genutzt."""
    key = ("flat", hexc, edge, pattern, pcol)
    if key in _cache: return _cache[key]
    m = bpy.data.materials.new(name or "sb_" + hexc); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"]); out = N["Material Output"]
    base = N.new("ShaderNodeRGB"); base.outputs[0].default_value = lin(hexc)
    col = base.outputs[0]
    if edge:
        lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = STYLE["edge_width"]
        ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "EASE"
        ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        d = STYLE["edge_dark"]; ramp.color_ramp.elements[1].position = 0.9; ramp.color_ramp.elements[1].color = (d, d * 0.96, d * 1.02, 1)
        L.new(lw.outputs["Facing"], ramp.inputs[0])
        mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L.new(col, mul.inputs[6]); L.new(ramp.outputs[0], mul.inputs[7]); col = mul.outputs[2]
    grp = N.new("ShaderNodeGroup"); grp.node_tree = _globals_group(); L.new(col, grp.inputs[0])
    em = N.new("ShaderNodeEmission"); L.new(grp.outputs[0], em.inputs[0]); L.new(em.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    m["sb_hex"] = hexc
    if pattern: m["sb_pattern"] = pattern; m["sb_pcol"] = pcol or "000000"
    _cache[key] = m; return m

def ink_hull():
    """Konturmaterial fuer die Inverted-Hull: nur Rueckseiten sichtbar."""
    if "sb_ink_hull" in bpy.data.materials: return bpy.data.materials["sb_ink_hull"]
    m = bpy.data.materials.new("sb_ink_hull"); m.use_nodes = True; m.use_backface_culling = True
    N = m.node_tree.nodes; N.remove(N["Principled BSDF"]); em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = lin(STYLE["ink"])
    m.node_tree.links.new(em.outputs[0], N["Material Output"].inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    return m

def ink_line(hexc=None, alpha=1.0):
    """Material fuer Gesichtsstriche/Punkte (unbeleuchtet, keine Randschattierung)."""
    hexc = hexc or STYLE["ink"]; key = ("line", hexc, alpha)
    if key in _cache: return _cache[key]
    m = bpy.data.materials.new("sb_line_" + hexc); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"]); out = N["Material Output"]
    em = N.new("ShaderNodeEmission"); em.inputs[0].default_value = lin(hexc)
    grp = N.new("ShaderNodeGroup"); grp.node_tree = _globals_group(); rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = lin(hexc)
    L.new(rgb.outputs[0], grp.inputs[0]); L.new(grp.outputs[0], em.inputs[0])
    if alpha < 1:
        tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader"); ms.inputs[0].default_value = alpha
        L.new(tr.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2]); L.new(ms.outputs[0], out.inputs[0])
    else: L.new(em.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    m["sb_hex"] = hexc; m["sb_alpha"] = alpha
    _cache[key] = m; return m

SHADE = (0.7, 0.66, 0.84)   # Farbe der weichen Schattenzone (lavendelgrau, multipliziert)

def flat2d(hexc, alpha=1.0, pattern=None, pcol=None, shaded=True):
    """Material fuer 2.5D-Ausschnitte: Grundfarbe x Schattenzone (Farbattribut 'shade') x Muster (UV 'puppet' in Metern)."""
    key = ("flat2d", hexc, alpha, pattern, pcol, shaded)
    if key in _cache: return _cache[key]
    m = bpy.data.materials.new("sb2d_" + hexc); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; N.remove(N["Principled BSDF"]); out = N["Material Output"]
    base = N.new("ShaderNodeRGB"); base.outputs[0].default_value = lin(hexc); col = base.outputs[0]
    if pattern:
        uv = N.new("ShaderNodeUVMap"); uv.uv_map = "puppet"; sep = N.new("ShaderNodeSeparateXYZ"); L.new(uv.outputs[0], sep.inputs[0])
        def band(axis, period, width):
            mul = N.new("ShaderNodeMath"); mul.operation = "DIVIDE"; L.new(sep.outputs[axis], mul.inputs[0]); mul.inputs[1].default_value = period
            fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; L.new(mul.outputs[0], fr.inputs[0])
            lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; L.new(fr.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = width
            return lt.outputs[0]
        if pattern == "pinstripe": fac = band(0, 0.035, 0.14); strength = 0.75
        elif pattern == "stripes": fac = band(1, 0.07, 0.45); strength = 0.9
        elif pattern == "knit": fac = band(0, 0.022, 0.35); strength = 0.35
        else:  # plaid: Kreuzungen dunkler
            a = band(0, 0.09, 0.32); b = band(1, 0.09, 0.32)
            ad = N.new("ShaderNodeMath"); ad.operation = "ADD"; L.new(a, ad.inputs[0]); L.new(b, ad.inputs[1])
            sc = N.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; L.new(ad.outputs[0], sc.inputs[0]); sc.inputs[1].default_value = 0.5
            fac = sc.outputs[0]; strength = 1.0
        k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY"; L.new(fac, k.inputs[0]); k.inputs[1].default_value = strength
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; L.new(k.outputs[0], mx.inputs[0]); L.new(col, mx.inputs[6]); mx.inputs[7].default_value = lin(pcol or "000000")
        col = mx.outputs[2]
    if shaded:
        ca = N.new("ShaderNodeVertexColor"); ca.layer_name = "shade"
        mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L.new(col, mul.inputs[6]); L.new(ca.outputs[0], mul.inputs[7]); col = mul.outputs[2]
    grp = N.new("ShaderNodeGroup"); grp.node_tree = _globals_group(); L.new(col, grp.inputs[0])
    em = N.new("ShaderNodeEmission"); L.new(grp.outputs[0], em.inputs[0])
    if alpha < 1:
        tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader"); ms.inputs[0].default_value = alpha
        L.new(tr.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2]); L.new(ms.outputs[0], out.inputs[0])
    else: L.new(em.outputs[0], out.inputs[0])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    _cache[key] = m; return m
