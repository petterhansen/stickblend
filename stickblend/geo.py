"""Geometrie-Helfer. Alles wird im three-Figurenraum gebaut (y oben, z vorne) und mit CM nach Blender (z oben) gedreht."""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion

CM = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
tb = lambda v: Vector((v[0], -v[2], v[1]))
tq = lambda q: Quaternion((q.w, q.x, -q.z, q.y))  # three-Quaternion (mathutils, three-Achsen) -> Blender

def mesh_obj(name, bm, mats, coll, parent=None, mtx=CM, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.transform(mtx)
    for p in me.polygons: p.use_smooth = smooth
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]): me.materials.append(m)
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    if parent: o.parent = parent
    return o

def lathe(bm, pts, segs=36, phi0=0.0, phil=2 * math.pi):
    """three.js-LatheGeometry: x = r sin(phi), z = r cos(phi). pts = [(r, y), ...] von unten nach oben."""
    full = abs(phil - 2 * math.pi) < 1e-6; ring = []
    for i in range(segs + 1):
        if full and i == segs: ring.append(ring[0]); continue
        ph = phi0 + phil * i / segs
        ring.append([bm.verts.new((r * math.sin(ph), y, r * math.cos(ph))) for (r, y) in pts])
    for i in range(segs):
        for j in range(len(pts) - 1):
            vs = [ring[i][j], ring[i][j + 1], ring[i + 1][j + 1], ring[i + 1][j]]
            try: bm.faces.new(vs)
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def uvsphere(bm, r, scale=(1, 1, 1), center=(0, 0, 0), seg=32, rings=20, rot=None):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    for v in res["verts"]:
        p = Vector((v.co.x * scale[0], v.co.z * scale[1], v.co.y * scale[2]))
        if rot: p = rot @ p
        v.co = p + Vector(center)
    return bm

def box(bm, size, center=(0, 0, 0), rot=None, bevel=0.2):
    res = bmesh.ops.create_cube(bm, size=1); vs = res["verts"]
    for v in vs:
        p = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        if rot: p = rot @ p
        v.co = p + Vector(center)
    if bevel: bmesh.ops.bevel(bm, geom=[e for e in bm.edges if all(v in vs for v in e.verts)], offset=min(size) * bevel, segments=2, affect="EDGES")
    return bm

def cyl(bm, r1, r2, h, center=(0, 0, 0), rot=None, segs=24):
    """Zylinder entlang y (wie three.js cylinderGeometry), geschlossen."""
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r2, radius2=r1, depth=h)
    for v in res["verts"]:
        p = Vector((v.co.x, v.co.z, v.co.y))
        if rot: p = rot @ p
        v.co = p + Vector(center)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def tube(bm, path, r, segs=10, caps=True):
    """Roehre entlang eines Polygonzugs (fuer Riemen, Guertel, Reissverschluss)."""
    path = [Vector(p) for p in path]; rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r) for k in range(segs)])
    for i in range(len(rings) - 1):
        for k in range(segs): bm.faces.new([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
    if caps:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

HULL_K = 0.0021   # Konturbreite pro Meter Kameraabstand (~2.5 px bei 1080x1920, 35 mm)

def _hull_group():
    """Geometry Nodes: Flaechen drehen + entlang Normalen versetzen, Versatz waechst mit Abstand zur aktiven Kamera
    -> Kontur bleibt im Bild gleich breit (wie gezeichnet)."""
    if "SB_Hull" in bpy.data.node_groups: return bpy.data.node_groups["SB_Hull"]
    g = bpy.data.node_groups.new("SB_Hull", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    w = g.interface.new_socket("Width", in_out="INPUT", socket_type="NodeSocketFloat"); w.default_value = 1.0
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = g.nodes; L = g.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    flip = N.new("GeometryNodeFlipFaces"); L.new(gi.outputs[0], flip.inputs[0])
    cam = N.new("GeometryNodeInputActiveCamera"); oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = "RELATIVE"
    L.new(cam.outputs[0], oi.inputs["Object"])
    pos = N.new("GeometryNodeInputPosition"); nrm = N.new("GeometryNodeInputNormal")
    dist = N.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"; L.new(pos.outputs[0], dist.inputs[0]); L.new(oi.outputs["Location"], dist.inputs[1])
    k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY"; L.new(dist.outputs["Value"], k.inputs[0]); k.inputs[1].default_value = -HULL_K
    k2 = N.new("ShaderNodeMath"); k2.operation = "MULTIPLY"; L.new(k.outputs[0], k2.inputs[0]); L.new(gi.outputs[1], k2.inputs[1])
    sc = N.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; L.new(nrm.outputs[0], sc.inputs[0]); L.new(k2.outputs[0], sc.inputs["Scale"])
    sp = N.new("GeometryNodeSetPosition"); L.new(flip.outputs[0], sp.inputs["Geometry"]); L.new(sc.outputs[0], sp.inputs["Offset"])
    L.new(sp.outputs[0], go.inputs[0])
    return g

def add_hull(o, coll, thick, ink_mat):
    """Inverted-Hull-Kontur als eigenes Objekt; thick = relative Breite (0.0055 = Standard)."""
    d = o.copy(); d.data = o.data.copy(); d.name = o.name + "_ink"; coll.objects.link(d)
    d.data.materials.clear(); d.data.materials.append(ink_mat)
    for p in d.data.polygons: p.material_index = 0
    m = d.modifiers.new("hull", "NODES"); m.node_group = _hull_group()
    sock = [it for it in m.node_group.interface.items_tree if getattr(it, "name", "") == "Width"][0]
    v = thick / 0.0055
    try: getattr(m.properties.inputs, sock.identifier).value = v   # Blender 5.x
    except AttributeError: m[sock.identifier] = v                   # Blender 4.x
    d.visible_shadow = False
    return d
