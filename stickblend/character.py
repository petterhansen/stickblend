"""Stickman-Factory fuer Blender: Figur aus Steckbrief bauen und aus Rig-Daten animieren.

Stil: flache 2D-Fuellungen (unbeleuchtet, weiche Randschattierung) + braune Inverted-Hull-Kontur,
Glieder als duenne Tuschestriche, Gesicht als Striche auf der Kopfkugel. Wirft echte Schatten in die 3D-Welt.
"""
import bpy, bmesh, math
from mathutils import Vector, Quaternion, Matrix
from . import geo, mats, face as facemod, rig as rigmod
from .geo import tb, tq, CM

OUT = 0.0055                         # Konturdicke (m)
FS = (math.pi / 2 - 0.95, 1.9, math.pi / 2 - 0.8, 1.6)   # Gesichtssegment wie three.js FACE_SEG
BEAN = [(0.0, 0.0), (0.62, 0.0), (0.93, 0.07), (1.0, 0.3), (0.98, 0.62), (0.86, 0.86), (0.55, 0.985), (0.0, 1.02)]

def _dark(h, k=0.75):
    h = h.lstrip("#"); return "".join("%02x" % int(int(h[i:i + 2], 16) * k) for i in (0, 2, 4))

class Char:
    pass

def face_pt(r, px, py, lift=1.0):
    ph = FS[0] + px / 512 * FS[1]; th = FS[2] + py / 512 * FS[3]
    return Vector((-math.cos(ph) * math.sin(th), math.cos(th), math.sin(ph) * math.sin(th))) * r * lift

# ------------------------------------------------------------------ Teile
def _obj(ch, name, bm, mat, parent, hull=True, thick=OUT, mtx=CM, solid=0.0):
    o = geo.mesh_obj(ch.name + "_" + name, bm, mat, ch.coll, parent, mtx)
    if solid:
        m = o.modifiers.new("solid", "SOLIDIFY"); m.thickness = solid; m.offset = 0; m.use_even_offset = True
    if hull: geo.add_hull(o, ch.coll, thick, mats.ink_hull())
    return o

def _torso(ch, spec):
    T = spec["torso"]; pr = ch.pr; tH = pr["torsoH"]; W = pr["shW"] * 1.08 * T.get("width", 1.0); depth = T.get("depth", 0.78)
    prof = T.get("profile") or BEAN
    pts = [(r * W, y * tH) for r, y in prof]
    _obj(ch, "torso", geo.lathe(bmesh.new(), pts, 40, math.pi, 2 * math.pi), mats.flat(T["color"], pattern=T.get("pattern"), pcol=T.get("pattern_color")), ch.E_torso)
    # Oberflaechenpunkt (phi = 0 vorne, y in Torsohoehe 0..1)
    def R(yn):
        for (r0, y0), (r1, y1) in zip(prof, prof[1:]):
            if y0 <= yn <= y1: return (r0 + (r1 - r0) * (yn - y0) / max(1e-6, y1 - y0)) * W
        return prof[-1][0] * W
    def S(phi, yn, lift=1.0):
        r = R(yn) * lift; return Vector((r * math.sin(phi), yn * tH, r * math.cos(phi) * depth))
    def nrm_rot(phi): return Quaternion((0, 1, 0), phi)
    base = T["color"]
    for d in T.get("details", []):
        t = d["type"]; col = d.get("color", _dark(base, 0.6))
        if t == "placket":
            _obj(ch, "placket", geo.tube(bmesh.new(), [S(0, y / 10, 1.01) for y in range(1, 10)], 0.0035, 8), mats.flat(col, edge=False), ch.E_torso, hull=False)
        elif t == "buttons":
            y0, y1 = d.get("y0", 0.3), d.get("y1", 0.75)
            for k in range(3):
                bm = geo.uvsphere(bmesh.new(), 0.011, (1, 1, 0.45), S(0.07, y0 + (y1 - y0) * k / 2, 1.0), 12, 8, nrm_rot(0.07))
                _obj(ch, "button%d" % k, bm, mats.flat(col, edge=False), ch.E_torso, thick=0.002)
        elif t == "collar":
            _obj(ch, "collar", geo.tube(bmesh.new(), [S(2 * math.pi * k / 24, 0.93, 1.0) for k in range(25)], 0.013, 8, caps=False), mats.flat(col), ch.E_torso, thick=0.003)
        elif t == "tabs":
            for s in (-1, 1): _obj(ch, "tab%d" % s, geo.box(bmesh.new(), (0.045, 0.03, 0.01), S(s * 0.42, 0.9, 1.02), nrm_rot(s * 0.42), 0.1), mats.flat(col, edge=False), ch.E_torso, thick=0.002)
        elif t == "belt":
            _obj(ch, "belt", geo.lathe(bmesh.new(), [(R(0.08) * 1.025, 0.08 * tH), (R(0.16) * 1.025, 0.16 * tH)], 40), mats.flat(col), ch.E_torso, thick=0.003)
            ch.parts_belt = True
            if d.get("buckle"): _obj(ch, "buckle", geo.box(bmesh.new(), (0.05, 0.05, 0.012), S(0, 0.12, 1.04), None, 0.15), mats.flat(d["buckle"], edge=False), ch.E_torso, thick=0.002)
        elif t == "strap":
            path = [S(0.8 - 1.6 * k / 14, 0.95 - 0.83 * k / 14, 1.025) for k in range(15)]
            _obj(ch, "strap", geo.tube(bmesh.new(), path, 0.009, 8), mats.flat(col), ch.E_torso, thick=0.002)
        elif t == "pouches":
            n = d.get("n", 3)
            for i in range(n):
                a = (i - (n - 1) / 2) * 0.55
                _obj(ch, "pouch%d" % i, geo.box(bmesh.new(), (0.06, 0.055, 0.035), S(a, 0.1, 1.08), nrm_rot(a), 0.2), mats.flat(col), ch.E_torso, thick=0.003)
        elif t == "pockets":
            for s in (-1, 1): _obj(ch, "pocket%d" % s, geo.box(bmesh.new(), (0.07, 0.06, 0.008), S(s * 0.42, 0.62, 1.01), nrm_rot(s * 0.42), 0.1), mats.flat(col, edge=False), ch.E_torso, thick=0.0025)
        elif t == "patch":
            w, h = d.get("size", (0.07, 0.06))
            _obj(ch, "patch", geo.box(bmesh.new(), (w, h, 0.006), S(d["phi"], d["y"], 1.01), nrm_rot(d["phi"]), 0.1), mats.flat(col, edge=False), ch.E_torso, thick=0.002)
        elif t == "camera":
            c = S(0, 0.5, 1.12)
            _obj(ch, "camera", geo.box(bmesh.new(), (0.1, 0.07, 0.045), c, None, 0.2), mats.flat(col), ch.E_torso, thick=0.0035)
            _obj(ch, "lens", geo.cyl(bmesh.new(), 0.022, 0.022, 0.03, c + Vector((0.0, 0, 0.035)), Matrix.Rotation(math.pi / 2, 3, "X"), 16), mats.flat("444448"), ch.E_torso, thick=0.003)
            for s in (-1, 1):
                _obj(ch, "camstrap%d" % s, geo.tube(bmesh.new(), [c + Vector((s * 0.04, 0.02, -0.01)), S(s * 0.35, 0.8, 1.06), S(s * 0.5, 0.99, 1.0)], 0.006, 6), mats.flat("1a1a1e", edge=False), ch.E_torso, hull=False)
        elif t == "bowtie":
            c = S(0, 0.93, 1.04)
            for s in (-1, 1): _obj(ch, "bow%d" % s, geo.cyl(bmesh.new(), 0.004, 0.024, 0.045, c + Vector((s * 0.022, 0, 0)), Matrix.Rotation(-s * math.pi / 2, 3, "Z"), 12), mats.flat(col), ch.E_torso, thick=0.002)
        elif t == "epaulettes":
            for s in (-1, 1):
                c = S(s * 1.15, 0.96, 1.08) + Vector((s * 0.035, 0.02, 0))
                _obj(ch, "ep%d" % s, geo.box(bmesh.new(), (0.11, 0.055, 0.085), c, None, 0.35), mats.flat(col), ch.E_torso, thick=0.003)
        elif t == "medals":
            _obj(ch, "ribbon", geo.box(bmesh.new(), (0.095, 0.035, 0.012), S(0.28, 0.72, 1.03), nrm_rot(0.28), 0.1), mats.flat("c8352f"), ch.E_torso, thick=0.002)
            for idx, (phi, yn) in enumerate(((0.52, 0.54), (0.48, 0.38))):
                _obj(ch, "star%d" % idx, geo.cyl(bmesh.new(), 0.028, 0.028, 0.012, S(phi, yn, 1.035), nrm_rot(phi).to_matrix() @ Matrix.Rotation(math.pi / 2, 3, "X"), 8), mats.flat("e8d278"), ch.E_torso, thick=0.002)
        elif t == "tie":
            c = S(0, 0.90, 1.03)
            _obj(ch, "tieknot", geo.box(bmesh.new(), (0.036, 0.032, 0.018), c, None, 0.2), mats.flat(col), ch.E_torso, thick=0.002)
            path = [S(0, 0.88 - 0.54 * k / 6, 1.028) for k in range(7)]
            _obj(ch, "tiebody", geo.tube(bmesh.new(), path, 0.022, 6), mats.flat(col), ch.E_torso, thick=0.002)
        elif t == "scarf":
            pts = [S(a, 0.96, 1.04) for a in (2 * math.pi * k / 24 for k in range(25))]
            _obj(ch, "scarf", geo.tube(bmesh.new(), pts, 0.034, 8, caps=False), mats.flat(col), ch.E_torso, thick=0.003)
            tail = [S(0.28, 0.94 - 0.44 * k / 6, 1.06 + 0.01 * k) for k in range(7)]
            _obj(ch, "scarftail", geo.tube(bmesh.new(), tail, 0.028, 6), mats.flat(col), ch.E_torso, thick=0.0025)
        elif t == "apron":
            bm = bmesh.new(); rows = []
            for j in range(9):
                yn = 0.04 + 0.78 * j / 8; w = 0.65
                rows.append([bm.verts.new(S(-w + 2 * w * i / 8, yn, 1.025)) for i in range(9)])
            for j in range(8):
                for i in range(8): bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            _obj(ch, "apron", bm, mats.flat(col, edge=False), ch.E_torso, solid=0.008, thick=0.0025)
        elif t == "suspenders":
            for s in (-1, 1):
                path = [S(s * 0.34, 0.14 + 0.82 * k / 8, 1.02) for k in range(9)]
                _obj(ch, "susp%d" % s, geo.tube(bmesh.new(), path, 0.012, 6), mats.flat(col), ch.E_torso, thick=0.002)
        elif t == "cape":
            bm = bmesh.new(); rows = []
            for j in range(8):
                yn = -0.35 + 1.32 * j / 7; w = 0.95 - 0.35 * (j / 7)
                rows.append([bm.verts.new(S(math.pi - w + 2 * w * i / 8, yn, 1.04 + (1 - j / 7) * 0.18)) for i in range(9)])
            for j in range(7):
                for i in range(8): bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            _obj(ch, "cape", bm, mats.flat(col), ch.E_torso, solid=0.010, thick=0.003)
        elif t == "skirt":
            rw = R(0.05) * 1.05
            bm = geo.lathe(bmesh.new(), [(rw * (1.32 - 0.32 * k / 6), tH * (0.28 * k / 6 - 0.16)) for k in range(7)], 32)
            _obj(ch, "skirt", bm, mats.flat(col), ch.E_torso, thick=0.004)
        elif t == "panel":  # V-Ausschnitt / Hemd unter Jacke
            a = d.get("width", 0.4); y0 = d.get("y0", 0.5); bm = bmesh.new(); rows = []
            for j in range(9):
                yn = y0 + (0.99 - y0) * j / 8; w = a * (j / 8)
                rows.append([bm.verts.new(S(-w + 2 * w * i / 6, yn, 1.006)) for i in range(7)])
            for j in range(8):
                for i in range(6):
                    try: bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
                    except ValueError: pass
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
            _obj(ch, "panel", bm, mats.flat(col, edge=False), ch.E_torso, hull=False)
            for s in (-1, 1): _obj(ch, "lapel%d" % s, geo.tube(bmesh.new(), [S(0, y0, 1.012), S(s * a, 0.99, 1.012)], 0.004, 6), mats.ink_line(), ch.E_torso, hull=False)
    if "lifepack" in spec.get("extras", []):   # Lebenserhaltungs-Tornister (Raumanzug)
        c = S(math.pi, 0.6, 1.0) + Vector((0, 0, -0.1))
        _obj(ch, "pack", geo.box(bmesh.new(), (0.36, 0.46, 0.2), c, None, 0.15), mats.flat("dcdde2"), ch.E_torso, thick=0.004)
    if "backpack" in spec.get("extras", []):
        c = S(math.pi, 0.55, 1.0) + Vector((0, 0, -0.08))
        _obj(ch, "pack", geo.box(bmesh.new(), (0.26, 0.32, 0.15), c, None, 0.2), mats.flat("8a6a43"), ch.E_torso, thick=0.004)
        _obj(ch, "bedroll", geo.cyl(bmesh.new(), 0.055, 0.055, 0.34, c + Vector((0, 0.2, 0)), Matrix.Rotation(math.pi / 2, 3, "Z"), 16), mats.flat("5f7a4a"), ch.E_torso, thick=0.003)
        for s in (-1, 1): _obj(ch, "packstrap%d" % s, geo.tube(bmesh.new(), [S(s * 0.35, 0.98, 1.03), S(s * 0.45, 0.6, 1.04), S(s * 0.4, 0.3, 1.03)], 0.008, 6), mats.flat("6b4a2a", edge=False), ch.E_torso, hull=False)

HAIR = {  # Haaransatz-Hoehe (Einheitskugel, y oben): vorne (Stirn), Seite, hinten (Nacken); fringe = Wellen im Pony
    "short": dict(front=0.52, side=0.05, back=-0.38, fringe=0.0),
    "parted": dict(front=0.42, side=0.02, back=-0.42, fringe=0.06),
    "bowl": dict(front=0.36, side=-0.18, back=-0.5, fringe=0.05),
    "bob": dict(front=0.4, side=-0.6, back=-0.72, fringe=0.0),
    "long": dict(front=0.42, side=-0.62, back=-0.75, fringe=0.03),
    "ponytail": dict(front=0.46, side=0.02, back=-0.45, fringe=0.02),
    "bun": dict(front=0.46, side=0.0, back=-0.42, fringe=0.0),
    "afro": dict(front=0.48, side=0.0, back=-0.48, fringe=0.04),
}
def _smooth(e0, e1, x):
    k = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return k * k * (3 - 2 * k)

def _hair(ch, H):
    """Haarkappe mit glattem Haaransatz: pro Laengengrad eine Spalte vom Scheitel bis zur Ansatzlinie."""
    style = H.get("style", "none")
    if style == "none": return
    r = ch.pr["headR"]; vol = H.get("volume", 1.0); col = H["color"]; bm = bmesh.new()
    NP, NR = 64, 18
    if style == "sides":   # Haarkranz (Glatze): nur Seiten + Hinterkopf
        ph0, ph1 = math.radians(70), math.radians(290); y0, y1 = 0.12, -0.55
        cols = []
        for i in range(NP + 1):
            ph = ph0 + (ph1 - ph0) * i / NP; edge = min(_smooth(0, 6, i), _smooth(NP, NP - 6, i))
            ytop = y1 + (y0 - y1) * (0.35 + 0.65 * edge)
            cols.append([bm.verts.new(Vector((math.sin(ph) * math.sqrt(1 - y * y), y, math.cos(ph) * math.sqrt(1 - y * y))) * r * (1.07 + 0.08 * math.sin(math.pi * j / NR)))
                         for j, y in enumerate([ytop + (y1 - ytop) * j / NR for j in range(NR + 1)])])
        for i in range(NP):
            for j in range(NR): bm.faces.new([cols[i][j], cols[i + 1][j], cols[i + 1][j + 1], cols[i][j + 1]])
    elif style == "spiky":
        bm = geo.uvsphere(bmesh.new(), r * 1.07, (1, 0.85, 1), (0, r * 0.25, -r * 0.05), 32, 18)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < r * 0.3], context="FACES")
        for k in range(7):
            a = -0.9 + 0.3 * k
            cone = geo.lathe(bmesh.new(), [(r * 0.22, 0), (0.001, r * 0.48)], 10)
            M = Matrix.Translation((math.sin(a) * r * 0.55, r * 0.82, math.cos(a) * r * 0.25 - r * 0.1)) @ Matrix.Rotation(-a * 0.7, 4, "Z")
            for v in cone.verts: bm.verts.new(M @ v.co)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        _obj(ch, "hair", bm, mats.flat(col), ch.E_head, thick=0.006, solid=-0.01)
        return
    elif style == "mohawk":
        for k in range(7):
            a = -0.35 + 0.24 * k
            _obj(ch, "mohawk%d" % k, geo.box(bmesh.new(), (r * 0.14, r * 0.42, r * 0.22), (0, math.cos(a) * r * 1.08, math.sin(a) * r * 0.95), Matrix.Rotation(a, 3, "X"), 0.3), mats.flat(col), ch.E_head, thick=0.005)
        return
    elif style == "curly":
        for k in range(18):
            ph = 2 * math.pi * k / 18; th = 0.45 + 0.52 * (k % 3) / 2
            c = Vector((math.sin(th) * math.sin(ph), math.cos(th), math.sin(th) * math.cos(ph))) * r * 1.02
            if c.z > r * 0.25 and c.y < r * 0.45: continue
            _obj(ch, "curl%d" % k, geo.uvsphere(bmesh.new(), r * 0.24 * vol, (1, 1, 1), c, 14, 10), mats.flat(col), ch.E_head, thick=0.0045)
        return
    else:
        P = HAIR[style]
        vol = vol * (1.28 if style == "afro" else 1.0)
        def hairline(ph):
            x, z = math.sin(ph), math.cos(ph)
            back = P["side"] + (P["back"] - P["side"]) * _smooth(0.1, -0.9, z)
            wf = _smooth(0.15, 0.5, z) * _smooth(0.9, 0.65, abs(x))
            return back + (P["front"] + P["fringe"] * math.cos(x * 9) - back) * wf
        top = bm.verts.new(Vector((0, 1, 0)) * r * 1.07 * vol); rings = []
        for i in range(NP):
            ph = 2 * math.pi * i / NP; th_h = math.acos(max(-0.99, min(0.99, hairline(ph))))
            col_ = []
            for j in range(1, NR + 1):
                th = th_h * j / NR; y = math.cos(th); s_ = 1.07 * (vol if y > 0.2 else 1 + (vol - 1) * max(0.0, y + 0.2) / 0.4)
                col_.append(bm.verts.new(Vector((math.sin(th) * math.sin(ph), y, math.sin(th) * math.cos(ph))) * r * s_))
            rings.append(col_)
        for i in range(NP):
            a_, b_ = rings[i], rings[(i + 1) % NP]
            bm.faces.new([top, a_[0], b_[0]])
            for j in range(NR - 1): bm.faces.new([a_[j], a_[j + 1], b_[j + 1], b_[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _obj(ch, "hair", bm, mats.flat(col), ch.E_head, thick=0.0065, solid=-0.012)
    if style == "long":
        prof = [(r * (0.97 - 0.08 * k / 6), -r * (0.3 + 1.5 * k / 6)) for k in range(7)][::-1]
        bm = geo.lathe(bmesh.new(), prof, 28, math.pi * 0.42, math.pi * 1.16)
        _obj(ch, "hairlong", bm, mats.flat(col), ch.E_head, thick=0.0065, solid=-0.014)
    elif style == "ponytail":
        tail = [Vector((0, r * (0.15 - 0.25 * k), -r * (0.98 + 0.12 * k))) for k in range(5)]
        _obj(ch, "hairlong", geo.tube(bmesh.new(), tail, r * 0.18, 12), mats.flat(col), ch.E_head, thick=0.0055)
    elif style == "bun":
        _obj(ch, "hairbun", geo.uvsphere(bmesh.new(), r * 0.34, (1, 1, 1), (0, r * 0.55, -r * 0.88), 20, 14), mats.flat(col), ch.E_head, thick=0.0055)

def _hat(ch, Hd):
    t = Hd["type"]; col = Hd.get("color", "7d7a48"); r = ch.pr["headR"]; dk = _dark(col, 0.8)
    if t == "fieldcap":   # lift: Muetze sitzt hoeher (Augen frei); Schirm weniger steil
        R = Matrix.Rotation(0.07, 4, "X"); mt = CM @ R @ Matrix.Translation((0, r * Hd.get("lift", 0.12), 0))
        _obj(ch, "crown", geo.lathe(bmesh.new(), [(0, r * 0.32), (r * 0.99, r * 0.32), (r * 0.78, r * 0.88), (r * 0.6, r * 0.99), (0, r * 1.03)], 40), mats.flat(col), ch.E_head, mtx=mt)
        bm = geo.lathe(bmesh.new(), [(0, 0), (r * 0.55, 0)], 28, -math.pi / 2, math.pi)
        M = Matrix.Translation((0, r * 0.36, r * 0.8)) @ Matrix.Rotation(0.1, 4, "X") @ Matrix.Diagonal((1.2, 1, 0.8, 1))
        for v in bm.verts: v.co = M @ v.co
        _obj(ch, "visor", bm, mats.flat(dk), ch.E_head, mtx=mt, solid=r * 0.05)
        fp = [(r * (math.sqrt(1 - y * y) + 0.045 + max(0, -y - 0.05) * (0.5 if Hd.get("frayed") else 0.35)), r * y) for y in [-0.42 + i / 11 * 1.04 for i in range(12)]]
        bm = geo.lathe(bmesh.new(), fp, 32, math.pi * 0.25, math.pi * 1.5)
        _obj(ch, "flap", bm, mats.flat(dk), ch.E_head, mtx=mt, solid=r * 0.03)
        _obj(ch, "badge", geo.box(bmesh.new(), (r * 0.16, r * 0.12, r * 0.04), (0, r * 0.66, r * 0.9), None, 0.15), mats.flat("c9a650", edge=False), ch.E_head, mtx=mt, thick=0.002)
    elif t == "officer":
        R = Matrix.Rotation(-0.15, 4, "X"); mt = CM @ R
        _obj(ch, "crown", geo.lathe(bmesh.new(), [(0, r * 0.62), (r * 0.94, r * 0.62), (r * 1.1, r * 1.04), (0, r * 1.04)], 40), mats.flat(col), ch.E_head, mtx=mt)
        _obj(ch, "band", geo.lathe(bmesh.new(), [(r * 0.955, r * 0.6), (r * 0.975, r * 0.74)], 40), mats.flat("b8322c"), ch.E_head, mtx=mt, thick=0.003)
        bm = geo.lathe(bmesh.new(), [(0, 0), (r * 0.6, 0)], 28, -math.pi / 2, math.pi)
        M = Matrix.Translation((0, r * 0.55, r * 0.62)) @ Matrix.Rotation(0.32, 4, "X") @ Matrix.Diagonal((1.1, 1, 0.7, 1))
        for v in bm.verts: v.co = M @ v.co
        _obj(ch, "visor", bm, mats.flat("1f1a16"), ch.E_head, mtx=mt, solid=r * 0.05)
    elif t == "helmet":   # Glaskugel-Helm (2.5D: halbtransparent ueber dem Gesicht) + Halsring + Glanzlicht
        R = r * 1.38; cy = r * 0.08
        bm = geo.uvsphere(bmesh.new(), R, (1, 1, 1), (0, cy, 0), 48, 28)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < cy - R * 0.8], context="FACES")
        gm = mats.flat("e2f0ff", edge=False); gm["sb_alpha"] = 0.22
        _obj(ch, "helmet", bm, gm, ch.E_head, hull=False)
        ring = [Vector((math.sin(a) * R * 0.62, cy - R * 0.8, math.cos(a) * R * 0.62)) for a in (2 * math.pi * k / 40 for k in range(41))]
        _obj(ch, "helmring", geo.tube(bmesh.new(), ring, r * 0.09, 10, caps=False), mats.flat("b8bcc6"), ch.E_head, thick=0.003)
        arc = [Vector((math.sin(a) * R * 0.97, cy + math.cos(a) * R * 0.97 * 0.9, R * 0.25)) for a in (-0.95 + 0.5 * k / 10 for k in range(11))]
        _obj(ch, "glint", geo.tube(bmesh.new(), arc, r * 0.05, 6), mats.flat("ffffff", edge=False), ch.E_head, hull=False)
    elif t == "beanie":
        bm = geo.uvsphere(bmesh.new(), r * 1.08, (1, 0.85, 1), (0, r * 0.3, -r * 0.02), 40, 24)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < r * 0.32], context="FACES")
        _obj(ch, "beanie", bm, mats.flat(col), ch.E_head, solid=-0.01)
    elif t == "cap":
        bm = geo.uvsphere(bmesh.new(), r * 1.05, (1, 0.8, 1), (0, r * 0.28, 0), 40, 24)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < r * 0.3], context="FACES")
        _obj(ch, "capdome", bm, mats.flat(col), ch.E_head, solid=-0.01)
        bm = geo.lathe(bmesh.new(), [(0, 0), (r * 0.6, 0)], 28, -math.pi / 2, math.pi)
        M = Matrix.Translation((0, r * 0.34, r * 0.8)) @ Matrix.Rotation(0.12, 4, "X") @ Matrix.Diagonal((1.0, 1, 1.0, 1))
        for v in bm.verts: v.co = M @ v.co
        _obj(ch, "capvisor", bm, mats.flat(dk), ch.E_head, solid=r * 0.04)
    elif t == "tophat":
        _obj(ch, "tophatbrim", geo.cyl(bmesh.new(), r * 1.38, r * 1.38, r * 0.08, (0, r * 0.62, 0), None, 32), mats.flat(dk), ch.E_head)
        _obj(ch, "tophatcrown", geo.cyl(bmesh.new(), r * 0.86, r * 0.94, r * 0.95, (0, r * 1.10, 0), None, 32), mats.flat(col), ch.E_head)
        _obj(ch, "band", geo.cyl(bmesh.new(), r * 0.88, r * 0.89, r * 0.16, (0, r * 0.72, 0), None, 32), mats.flat(Hd.get("band", "8a2424")), ch.E_head, thick=0.003)
    elif t == "fedora":
        R = Matrix.Rotation(-0.14, 4, "X"); mt = CM @ R
        _obj(ch, "fedorabrim", geo.cyl(bmesh.new(), r * 1.42, r * 1.42, r * 0.07, (0, r * 0.56, 0), None, 32), mats.flat(dk), ch.E_head, mtx=mt)
        _obj(ch, "fedoracrown", geo.cyl(bmesh.new(), r * 0.80, r * 0.96, r * 0.58, (0, r * 0.85, 0), None, 32), mats.flat(col), ch.E_head, mtx=mt)
        _obj(ch, "band", geo.cyl(bmesh.new(), r * 0.92, r * 0.95, r * 0.14, (0, r * 0.65, 0), None, 32), mats.flat(Hd.get("band", "222026")), ch.E_head, mtx=mt, thick=0.003)
    elif t == "bowler":
        _obj(ch, "bowlerbrim", geo.cyl(bmesh.new(), r * 1.32, r * 1.32, r * 0.07, (0, r * 0.56, 0), None, 32), mats.flat(dk), ch.E_head)
        bm = geo.uvsphere(bmesh.new(), r * 0.96, (1, 0.92, 1), (0, r * 0.58, 0), 32, 20)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < r * 0.56], context="FACES")
        _obj(ch, "bowlerdome", bm, mats.flat(col), ch.E_head, solid=-0.01)
    elif t == "beret":
        R = Matrix.Rotation(0.18, 4, "Z"); mt = CM @ R
        _obj(ch, "beret", geo.uvsphere(bmesh.new(), r * 1.15, (1.1, 0.34, 1.1), (0, r * 0.72, -r * 0.05), 32, 16), mats.flat(col), ch.E_head, mtx=mt)
        _obj(ch, "beretstem", geo.cyl(bmesh.new(), r * 0.04, r * 0.04, r * 0.16, (0, r * 1.08, -r * 0.05), None, 8), mats.flat(dk), ch.E_head, mtx=mt)
    elif t == "crown":
        _obj(ch, "crownbase", geo.cyl(bmesh.new(), r * 0.96, r * 0.90, r * 0.24, (0, r * 0.85, 0), None, 24), mats.flat(Hd.get("color", "e0b844")), ch.E_head)
        for k in range(6):
            a = 2 * math.pi * k / 6
            _obj(ch, "crownpt%d" % k, geo.lathe(bmesh.new(), [(r * 0.14, r * 0.95), (0.001, r * 1.25)], 8), mats.flat(Hd.get("color", "e0b844")), ch.E_head, mtx=CM @ Matrix.Translation((math.sin(a) * r * 0.88, 0, math.cos(a) * r * 0.88)))
    elif t == "pickelhaube":
        bm = geo.uvsphere(bmesh.new(), r * 1.04, (1, 0.9, 1), (0, r * 0.35, 0), 32, 20)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < r * 0.35], context="FACES")
        _obj(ch, "helm_dome", bm, mats.flat(col), ch.E_head, solid=-0.01)
        _obj(ch, "helm_spike", geo.lathe(bmesh.new(), [(r * 0.12, r * 1.15), (0.001, r * 1.62)], 12), mats.flat("d8b84c"), ch.E_head)

def _extras(ch, spec):
    r = ch.pr["headR"]; ex = spec.get("extras", [])
    if "glasses" in ex:
        for px in (196, 316):
            c = face_pt(r, px, 236, 1.06); n = c.normalized(); q = Vector((0, 0, 1)).rotation_difference(n)
            ring = [c + q @ Vector((math.cos(a) * r * 0.17, math.sin(a) * r * 0.17, 0)) for a in (2 * math.pi * k / 24 for k in range(25))]
            _obj(ch, "lens%d" % px, geo.tube(bmesh.new(), ring, r * 0.022, 6, caps=False), mats.ink_line(), ch.E_head, hull=False)
        _obj(ch, "bridge", geo.tube(bmesh.new(), [face_pt(r, 240, 232, 1.07), face_pt(r, 256, 226, 1.09), face_pt(r, 272, 232, 1.07)], r * 0.02, 6), mats.ink_line(), ch.E_head, hull=False)
    if "monocle" in ex:
        c = face_pt(r, 316, 236, 1.06); n = c.normalized(); q = Vector((0, 0, 1)).rotation_difference(n)
        ring = [c + q @ Vector((math.cos(a) * r * 0.17, math.sin(a) * r * 0.17, 0)) for a in (2 * math.pi * k / 24 for k in range(25))]
        _obj(ch, "monocle", geo.tube(bmesh.new(), ring, r * 0.022, 6, caps=False), mats.flat("d8b44c", edge=False), ch.E_head, hull=False)
    if "headband" in ex:
        R = Matrix.Rotation(-0.12, 4, "X")
        bm = geo.tube(bmesh.new(), [R @ Vector((math.sin(a) * r * 1.09, r * 0.5, math.cos(a) * r * 1.09)) for a in (2 * math.pi * k / 40 for k in range(41))], r * 0.085, 10, caps=False)
        _obj(ch, "headband", bm, mats.flat("d4322c"), ch.E_head, thick=0.003)

def _limbs(ch, spec):
    pr = ch.pr; arm = bpy.data.armatures.new(ch.name + "_rig"); ch.rig = bpy.data.objects.new(ch.name + "_rig", arm); ch.coll.objects.link(ch.rig)
    bpy.context.view_layer.objects.active = ch.rig
    L = []
    for side, nm in ((0, "L"), (1, "R")):
        L.append(("leg" + nm, pr["legLen"] / 2, "legs", side, ("hip", "knee", "ankle")))
        L.append(("arm" + nm, pr["armLen"] / 2, "arms", side, ("sh", "e", "h")))
    bpy.ops.object.mode_set(mode="EDIT")
    for n, a, *_ in L:
        A = arm.edit_bones.new(n + "_A"); A.head = (0, 0, 0); A.tail = (0, 0, -a)
        B = arm.edit_bones.new(n + "_B"); B.head = (0, 0, -a); B.tail = (0, 0, -2 * a); B.parent = A; B.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    ch.joints = {}
    for n, a, grp, side, keys in L:
        es = []
        for k in keys:
            e = bpy.data.objects.new(f"{ch.name}_{n}_{k}", None); e.empty_display_size = 0.02; ch.coll.objects.link(e); es.append(e)
        ch.joints[n] = (grp, side, keys, es)
        pa, pb = ch.rig.pose.bones[n + "_A"], ch.rig.pose.bones[n + "_B"]
        c = pa.constraints.new("COPY_LOCATION"); c.target = es[0]
        c = pa.constraints.new("DAMPED_TRACK"); c.target = es[1]; c.track_axis = "TRACK_Y"
        c = pb.constraints.new("DAMPED_TRACK"); c.target = es[2]; c.track_axis = "TRACK_Y"
    def skin_tube(name, n, a, s0, s1, r0, r1, mat, hull):
        bm = bmesh.new(); segs = 16; rings = max(6, int((s1 - s0) / 0.012)); rows = []
        for j in range(rings + 1):
            s = s0 + (s1 - s0) * j / rings; rr = r0 + (r1 - r0) * j / rings
            rows.append([bm.verts.new((rr * math.cos(2 * math.pi * i / segs), rr * math.sin(2 * math.pi * i / segs), -s)) for i in range(segs)])
        for j in range(rings):
            for i in range(segs): bm.faces.new([rows[j][i], rows[j][(i + 1) % segs], rows[j + 1][(i + 1) % segs], rows[j + 1][i]])
        bm.faces.new(rows[0][::-1]); bm.faces.new(rows[-1]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        o = geo.mesh_obj(f"{ch.name}_{name}", bm, mat, ch.coll, None, Matrix.Identity(4))
        gA = o.vertex_groups.new(name=n + "_A"); gB = o.vertex_groups.new(name=n + "_B")
        for v in o.data.vertices:
            s = -v.co.z; k = min(1, max(0, (s - (a - 0.04)) / 0.08)); k = k * k * (3 - 2 * k)
            gA.add([v.index], 1 - k, "REPLACE"); gB.add([v.index], k, "REPLACE")
        md = o.modifiers.new("arm", "ARMATURE"); md.object = ch.rig
        if hull: geo.add_hull(o, ch.coll, OUT * 0.9, mats.ink_hull())
        return o
    limbc = spec.get("limbs", mats.STYLE["ink"]); SL = spec.get("sleeves"); PA = spec.get("pants")
    for n, a, grp, side, keys in L:
        skin_tube(n + "_stick", n, a, 0, 2 * a, 0.011, 0.011, mats.flat(limbc, edge=False), False)
        if grp == "arms" and SL:
            skin_tube(n + "_sleeve", n, a, 0, 2 * a * SL.get("len", 0.9), SL["r"] * 1.1, SL["r"] * 0.9, mats.flat(SL["color"]), True)
        if grp == "legs" and PA:
            skin_tube(n + "_pants", n, a, 0, 2 * a * PA.get("len", 1.0), PA["r"], PA["r"] * 0.85, mats.flat(PA["color"]), True)
        if grp == "legs" and spec.get("puttees"):
            skin_tube(n + "_putt", n, a, 2 * a * 0.6, 2 * a * 0.97, 0.03, 0.034, mats.flat(spec["puttees"]), True)
        es = ch.joints[n][3]
        if grp == "arms":
            bm = geo.uvsphere(bmesh.new(), 0.032, (1, 1.15, 0.85), (0, 0, 0), 16, 12)
            _obj(ch, n + "_hand", bm, mats.flat(spec.get("skin", "f4efe6")), es[2], mtx=Matrix.Identity(4), thick=0.004)
        if grp == "legs":
            sh = bpy.data.objects.new(f"{ch.name}_{n}_shoe", None); ch.coll.objects.link(sh); sh.rotation_mode = "QUATERNION"
            bm = geo.uvsphere(bmesh.new(), 0.05, (0.8, 0.6, 1.6), (0, 0, 0), 16, 12)
            _obj(ch, n + "_shoebox", bm, mats.flat(spec.get("shoes", "2b1d16")), sh, thick=0.004)
            ch.joints[n] = ch.joints[n] + (sh,)

def _face_variant(ch, key, prims):
    """Ein Gesichtsausdruck als Mesh aus Baendern/Flaechen auf der Kopfkugel (Kopf-lokal)."""
    r = ch.pr["headR"]; px2m = FS[1] * r / 512; bm = bmesh.new(); mlist = []; midx = []
    def matid(c):
        m = mats.ink_line(c[0], c[1]) if isinstance(c, tuple) else mats.ink_line(c)
        if m not in mlist: mlist.append(m)
        return mlist.index(m)
    def disc(c, rad, mi, n=10):
        nn = c.normalized(); a = nn.orthogonal().normalized(); b = nn.cross(a)
        vs = [bm.verts.new(c + (a * math.cos(2 * math.pi * k / n) + b * math.sin(2 * math.pi * k / n)) * rad) for k in range(n)]
        f = bm.faces.new(vs); midx.append((f, mi))
    def line(pts2, wpx, col, closed, lift=1.012):
        P = [face_pt(r, x, y, lift) for x, y in pts2]; mi = matid(col); hw = wpx / 2 * px2m
        if closed: P = P + [P[0]]
        for a_, b_ in zip(P, P[1:]):
            t = b_ - a_
            if t.length < 1e-7: continue
            s = a_.normalized().cross(t.normalized()) * hw
            f = bm.faces.new([bm.verts.new(a_ - s), bm.verts.new(b_ - s), bm.verts.new(b_ + s), bm.verts.new(a_ + s)]); midx.append((f, mi))
        for p in (P[:-1] if closed else P): disc(p * 1.0005, hw, mi)
    for pr_ in prims:
        if pr_[0] == "line": line(pr_[1], pr_[2], pr_[3], pr_[4])
        elif pr_[0] == "fill":
            lift = 1.006 if isinstance(pr_[2], tuple) else 1.009
            P = [face_pt(r, x, y, lift) for x, y in pr_[1]]; mi = matid(pr_[2])
            f = bm.faces.new([bm.verts.new(p) for p in P]); midx.append((f, mi))
            if pr_[3]: line(pr_[1], pr_[3], mats.STYLE["ink"], True)
        elif pr_[0] == "dot": disc(face_pt(r, pr_[1][0], pr_[1][1], 1.013), pr_[2] * px2m, matid(pr_[3]))
    for f, mi in midx: f.material_index = mi
    for f in bm.faces: f.normal_update()
    me = bpy.data.meshes.new(f"{ch.name}_face_{key}"); bm.to_mesh(me); bm.free(); me.transform(CM)
    for m in mlist: me.materials.append(m)
    o = bpy.data.objects.new(me.name, me); ch.coll.objects.link(o); o.parent = ch.E_head; o.visible_shadow = False
    ch.faces[key] = o; return o

# ------------------------------------------------------------------ Bauen / Animieren
def build(spec, name, parent_coll=None):
    ch = Char(); ch.spec = spec; ch.name = name; ch.pr = rigmod.proportions(spec); ch.faces = {}
    ch.coll = bpy.data.collections.new(name); (parent_coll or bpy.context.scene.collection).children.link(ch.coll)
    for nm in ("torso", "head"):
        e = bpy.data.objects.new(f"{name}_{nm}", None); e.rotation_mode = "QUATERNION"; e.empty_display_size = 0.05; ch.coll.objects.link(e); setattr(ch, "E_" + nm, e)
    _torso(ch, spec)
    _obj(ch, "head", geo.uvsphere(bmesh.new(), ch.pr["headR"], seg=48, rings=32), mats.flat(spec.get("skin", "f4efe6")), ch.E_head, thick=0.0065)
    _hair(ch, spec.get("hair", {"style": "none"}))
    if spec.get("hat"): _hat(ch, spec["hat"])
    _extras(ch, spec)
    _limbs(ch, spec)
    return ch

def animate(ch, fn, frames, step=2, start=1):
    """fn(t) -> dict(rig=..., mood=..., blink=..., mouth=...). Figur wird nur jedes `step`-te Bild gesetzt (auf Zweiern)."""
    for f in range(start, start + frames, step):
        st = fn((f - start) / bpy.context.scene.render.fps)
        pose_frame(ch, f, st["rig"], st.get("mood", "neutral"), st.get("blink", False), st.get("mouth", 0.0), st.get("look", (0, 0)), st.get("hidden", False))

def face_key(spec, mood, blink, mouth):
    return f"{mood}_{int(blink)}_{round(mouth * 4)}"

def pose_frame(ch, frame, rigw, mood="neutral", blink=False, mouth=0.0, look=(0, 0), hidden=False):
    """Setzt alle Keys fuer ein Bild. rigw = rig.to_world(stick_rig(...), pos, yaw) (three-Achsen)."""
    ch.E_torso.location = tb(rigw["hipC"]); ch.E_torso.rotation_quaternion = tq(rigw["tq"])
    ch.E_head.location = tb(rigw["neck"]); ch.E_head.rotation_quaternion = tq(rigw["hq"])
    for e in (ch.E_torso, ch.E_head): e.keyframe_insert("location", frame=frame); e.keyframe_insert("rotation_quaternion", frame=frame)
    fwd = rigw["yq"] @ Vector((0, 0, 1))
    for n, (grp, side, keys, es, *rest) in ch.joints.items():
        J = rigw[grp][side]
        for k, e in zip(keys, es): e.location = tb(J[k]); e.keyframe_insert("location", frame=frame)
        if rest:
            a = J["ankle"]; s = rest[0]
            s.location = tb(Vector((a.x, max(0.032, a.y - 0.01), a.z)) + fwd * 0.045); s.rotation_quaternion = tq(rigw["yq"])
            s.keyframe_insert("location", frame=frame); s.keyframe_insert("rotation_quaternion", frame=frame)
    F = ch.spec.get("face", {})
    key = face_key(ch.spec, mood, blink, mouth)
    if key not in ch.faces:
        new = True
        _face_variant(ch, key, facemod.face_prims(mood, blink, round(mouth * 4) / 4, look, F.get("stubble", False), F.get("age", 0), F.get("nose", True),
                                                   F.get("blush", False), eye_highlight=F.get("eye_highlight", False), ink=mats.STYLE["ink"], eyes=F.get("eyes", "dark"),
                                                   mustache=F.get("mustache", False), muttonchops=F.get("muttonchops", False),
                                                   beard=F.get("beard", False), goatee=F.get("goatee", False), freckles=F.get("freckles", False),
                                                   scar=F.get("scar", False), eyelashes=F.get("eyelashes", False),
                                                   facial_hair_color=F.get("facial_hair_color", "5e4c3a")))
        if frame > 1: o = ch.faces[key]; o.hide_render = True; o.keyframe_insert("hide_render", frame=1)  # vorher unsichtbar
    for k, o in ch.faces.items():
        o.hide_render = hidden or k != key; o.keyframe_insert("hide_render", frame=frame)  # kein hide_viewport: sonst wertet Blender die Animation nicht aus
