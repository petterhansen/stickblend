"""2.5D-Ausschnitte: die 3D-Figur dient nur als unsichtbare Vorlage (Pose, Drehung, Schatten).
Pro gezeichnetem Bild wird jede Figur orthografisch auf eine kamerazugewandte Ebene projiziert:
flache Fuellungen mit weicher einseitiger Schattenzone, gleich breite Tuschelinien im Bildraum,
Teile als feste Ebenen hintereinander (Cut-out). Details sitzen immer auf ihrem Traeger (Torso/Kopf) -> kein Aufploppen.
"""
import bpy, math
from mathutils import Vector
from . import mats

LW_PX = 4.4              # Linienbreite in Pixeln (bei 1080x1920), Referenz ~4-5 px
LIGHT = (-0.55, 0.6, 0.6) # Lichtrichtung relativ zur Kamera (rechts, oben, zur Kamera) fuer die Schattenzone
SOFT = (-0.15, 0.25)
HAND_FRONT = 0.12         # Haende so weit vor ihre tatsaechliche Tiefe (m), damit sie Gehaltenes ueberdecken
STICK_COLOR = None        # optional: hellere Strichfarbe fuer Arme/Beine (Nachtszenen, sonst verschwinden sie vor dunklem Hintergrund)
LIGHT_POS = None          # optional: Weltposition einer Lichtquelle (z. B. Feuer) -> Schattenzone auf der abgewandten Seite       # weicher Uebergang (dot-Bereich)

def _src(mat):
    if mat is None: return dict(hex="888888", alpha=1.0, pattern=None, pcol=None)
    return dict(hex=mat.get("sb_hex", "888888"), alpha=mat.get("sb_alpha", 1.0), pattern=mat.get("sb_pattern"), pcol=mat.get("sb_pcol"))

def _cam_basis(cam, anchor):
    cp = cam.matrix_world.translation; n = (cp - anchor).normalized()
    cr = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    R = (cr - n * cr.dot(n)).normalized(); U = n.cross(R).normalized()
    return cp, n, R, U

def _px_to_world(cam, dist):
    h = bpy.context.scene.render.resolution_y
    return dist / (cam.data.lens / cam.data.sensor_height * h)

def make_proxy(ch):
    """Vorlage unsichtbar fuer die Kamera, wirft aber weiter Schatten."""
    for o in ch.coll.all_objects:
        o.visible_camera = False; o.lineart.usage = "EXCLUDE"

def _smooth(a, b, x):
    k = max(0.0, min(1.0, (x - a) / (b - a))); return k * k * (3 - 2 * k)

# Feste Stapelreihenfolge der Details auf ihrem Traeger (wie Ebenen einer Cut-out-Puppe).
# Nie nach Tiefe sortieren: Teile auf gleicher Hoehe (Guertel/Taschen/Schnalle) tauschen sonst von Bild zu Bild die Reihenfolge.
LAYERS = {"cape": -2, "skirt": 0, "panel": 0, "pack": 0, "bedroll": 1, "lapel": 1, "patch": 1, "pocket": 1, "apron": 2, "apronbelt": 3, "apronpocket": 4, "apronstrap": 4, "placket": 2, "susp": 3, "belt": 3, "tieknot": 4, "tiebody": 4, "button": 4, "buckle": 5, "pouch": 5,
          "ribbon": 5, "star": 5, "strap": 6, "camstrap": 6, "packstrap": 6, "tab": 7, "collar": 7, "ep": 7, "capeclasp": 8, "scarf": 8, "scarftail": 8, "camera": 8, "bow": 8, "lens": 9,
          "hair": 1, "hairlong": 1, "hairbun": 1, "curl": 2, "mohawk": 2, "flap": 2, "crown": 2, "beanie": 2, "capdome": 2, "tophatcrown": 3, "fedoracrown": 3, "bowlerdome": 3, "beret": 3, "crownbase": 3, "crownpt": 3, "crownjewel": 5, "helm_dome": 3, "helm_spike": 3,
          "band": 4, "tophatbrim": 4, "fedorabrim": 4, "bowlerbrim": 4, "beretstem": 4, "headband": 4, "visor": 4, "capvisor": 4, "badge": 5, "bridge": 6, "monocle": 6, "helmring": 6, "helmet": 8, "glint": 9}
def _base(o): return o.name.split(".")[0]   # Blender haengt ".001" an, wenn der Name schon vergeben ist (Empty "x_torso" vs. Mesh "x_torso")
def _layer(o, ch):
    key = _base(o)[len(ch.name) + 1:].rstrip("0123456789-")
    return LAYERS.get(key, 3)

def _closed(me):
    cnt = {}
    for e in me.edges: cnt[e.key] = 0
    for p in me.polygons:
        for k in p.edge_keys: cnt[k] = cnt.get(k, 0) + 1
    return all(c == 2 for c in cnt.values())

def _classify(o, ch):
    if "_face_" in o.name: return "face"
    if "_arm" in o.name and "_stick" in o.name: return "armstick"   # Arme kommen mit den Haenden nach vorne
    if "_stick" in o.name: return "stick"
    if _base(o) == ch.name + "_head": return "head"
    if _base(o) == ch.name + "_torso": return "torso"
    if o.parent == ch.E_head: return "headpart"
    if o.parent == ch.E_torso: return "torsopart"
    if "_hand" in o.name: return "hand"
    return "body"

def flatten(chars, cam, frames, step=2, start=1, lw_px=LW_PX):
    sc = bpy.context.scene; ink = mats.STYLE["ink"]
    coll = bpy.data.collections.new("flat"); sc.collection.children.link(coll)
    for ch in chars: make_proxy(ch)
    for f in range(start, start + frames, step):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        for ch in chars:
            anchor = ch.E_torso.matrix_world.translation.copy()
            cp, n, R, U = _cam_basis(cam, anchor)
            Lw = (Vector(LIGHT_POS) - anchor).normalized() if LIGHT_POS is not None else (R * LIGHT[0] + U * LIGHT[1] + n * LIGHT[2]).normalized()
            lw = lw_px * _px_to_world(cam, (cp - anchor).length) / 2
            proj = lambda v: (R.dot(v - anchor), U.dot(v - anchor), n.dot(v - anchor))
            hc = ch.E_head.matrix_world.translation
            tc = ch.E_torso.matrix_world @ Vector((0, 0, ch.pr["torsoH"] * 0.5)); ax = (ch.E_torso.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
            parts = []; base = {}
            for o in ch.coll.all_objects:
                if o.type != "MESH" or o.name.endswith("_ink") or o.hide_render: continue
                kind = _classify(o, ch)
                eo = o.evaluated_get(dg); me = eo.to_mesh(); M = eo.matrix_world; N3 = M.to_3x3().inverted_safe().transposed()
                P = [proj(M @ v.co) for v in me.vertices]
                VN = [(N3 @ v.normal).normalized() for v in me.vertices]
                if kind == "face":   # Baender auf der Kopfkugel: sichtbar, wenn die Kugelstelle zur Kamera zeigt
                    sel = [p for p in me.polygons if ((M @ p.center) - hc).normalized().dot(n) > 0.12]
                elif kind == "torsopart":   # Kontur ueber Normalen; offene Ringe (Guertel) haben nach innen zeigende Normalen -> beidseitig zulassen, Seite entscheidet unten
                    sel = [p for p in me.polygons if (N3 @ p.normal).dot(n) > 0.0] if _closed(me) else list(me.polygons)
                else:
                    sel = [p for p in me.polygons if (N3 @ p.normal).dot(n) > 0.0]
                if not sel: eo.to_mesh_clear(); continue
                groups = [(kind, sel)]
                if kind in ("headpart", "torsopart"):   # vor / hinter dem Traeger trennen
                    if kind == "headpart":   # Kopf = Kugel: Richtung vom Mittelpunkt
                        side = lambda q: (q - hc).dot(n)
                    else:                    # Torso = stehender Koerper: Richtung von der Hochachse (Hoehe darf nicht mitzaehlen)
                        side = lambda q: ((q - tc) - ax * (q - tc).dot(ax)).dot(n)
                    fr = [p for p in sel if side(M @ p.center) >= 0]; bk = [p for p in sel if side(M @ p.center) < 0]
                    if kind == "headpart":   # Teile, die in 3D hinter der Kopfkugel liegen (Nackenschutz neben dem Gesicht), nach hinten
                        rH = ch.pr["headR"] * 1.01
                        def hidden_by_head(q):
                            d = q - hc; al = d.dot(n); pp = (d - n * al).length
                            return pp < rH and al < math.sqrt(max(0.0, rH * rH - pp * pp))
                        hid = [p for p in fr if hidden_by_head(M @ p.center)]
                        if hid: fr = [p for p in fr if p not in hid]; bk = bk + hid
                    groups = [g for g in ((kind, fr), (kind + "_back", bk)) if g[1]]
                for gk, polys in groups:
                    fills = {}; ecount = {}
                    shade = gk not in ("face", "stick", "armstick")
                    for p in polys:
                        src = _src(me.materials[p.material_index] if me.materials else None)
                        k = (src["hex"], src["alpha"], src["pattern"], src["pcol"])
                        if STICK_COLOR and gk in ("stick", "armstick"): k = (STICK_COLOR, 1.0, None, None)
                        corners = [(P[i], _smooth(SOFT[0], SOFT[1], VN[i].dot(Lw)) if shade else 1.0) for i in p.vertices]
                        fills.setdefault(k, []).append(corners)
                        vs = list(p.vertices)
                        for a_, b_ in zip(vs, vs[1:] + vs[:1]): kk = (min(a_, b_), max(a_, b_)); ecount[kk] = ecount.get(kk, 0) + 1
                    depth = sum(P[i][2] for p in polys for i in p.vertices) / sum(len(p.vertices) for p in polys)
                    bound = [(P[a_], P[b_]) for (a_, b_), c in ecount.items() if c == 1] if gk not in ("face", "stick", "armstick") else []
                    parts.append(dict(kind=gk, depth=depth, fills=fills, bound=bound, layer=_layer(o, ch)))
                    if gk in ("head", "torso"): base[gk] = depth
                eo.to_mesh_clear()
            # feste Ebenen relativ zum Traeger: Gesicht auf Kopf, Kopfteile davor/dahinter, Torso-Details davor/dahinter
            hd, td = base.get("head"), base.get("torso")
            for p in parts:
                if hd is not None:
                    if p["kind"] == "face": p["depth"] = hd + 0.002
                    elif p["kind"] == "headpart": p["depth"] = hd + 0.004 + p["layer"] * 6e-4
                    elif p["kind"] == "headpart_back": p["depth"] = hd - 0.004 - p["layer"] * 6e-4
                if td is not None:
                    if p["kind"] == "torsopart": p["depth"] = td + 0.003 + p["layer"] * 6e-4
                    elif p["kind"] == "torsopart_back": p["depth"] = td - 0.003 - p["layer"] * 6e-4
            # Kopf liegt immer ueber dem Torso (wie gezeichnet: der Kopfkreis ueberdeckt Kragen/Schultern)
            tgrp = [p["depth"] for p in parts if p["kind"] in ("torso", "torsopart")]
            if hd is not None and tgrp and hd <= max(tgrp) + 0.003:
                dlt = max(tgrp) + 0.004 - hd
                for p in parts:
                    if p["kind"] in ("head", "face", "headpart"): p["depth"] += dlt
            for p in parts:   # Haende liegen immer vor dem, was sie halten (Gewehr, Tasse ...)
                if p["kind"] in ("hand", "armstick"): p["depth"] += HAND_FRONT
            parts.sort(key=lambda p: p["depth"])
            verts, faces, fmat, fshade, mlist = [], [], [], [], []
            def mid(k, shaded=True):
                m = mats.flat2d(k[0], k[1], k[2], k[3], shaded)
                if m not in mlist: mlist.append(m)
                return mlist.index(m)
            def W(x, y, d): return anchor + R * x + U * y + n * d
            def poly(pts, layer, mi, shades=None):
                i0 = len(verts); verts.extend(W(q[0], q[1], layer) for q in pts); faces.append(list(range(i0, len(verts)))); fmat.append(mi)
                fshade.append(shades or [1.0] * len(pts))
            for li, p in enumerate(parts):
                Lr = p["depth"]; shaded = p["kind"] not in ("face", "stick", "armstick")
                for k, polys in p["fills"].items():
                    mi = mid(k, shaded)
                    for cs in polys: poly([c[0] for c in cs], Lr, mi, [c[1] for c in cs])
                if p["bound"]:
                    mi = mid((ink, 1.0, None, None), False); pts = set()
                    for a, b in p["bound"]:
                        A, B = Vector((a[0], a[1])), Vector((b[0], b[1])); d = B - A
                        if d.length < 1e-7: continue
                        s = Vector((-d.y, d.x)).normalized() * lw
                        poly([(v.x, v.y) for v in (A + s, A - s, B - s, B + s)], Lr + 0.0003, mi)
                        pts.add((round(a[0], 5), round(a[1], 5))); pts.add((round(b[0], 5), round(b[1], 5)))
                    for x, y in pts:
                        poly([(x + math.cos(2 * math.pi * k / 8) * lw, y + math.sin(2 * math.pi * k / 8) * lw) for k in range(8)], Lr + 0.0003, mi)
            me = bpy.data.meshes.new(f"flat_{ch.name}_{f:04d}"); me.from_pydata([tuple(v) for v in verts], [], faces)
            for m in mlist: me.materials.append(m)
            ca = me.color_attributes.new("shade", "BYTE_COLOR", "CORNER"); uvl = me.uv_layers.new(name="puppet")
            sh = mats.SHADE
            for poly_, mi, shs in zip(me.polygons, fmat, fshade):
                poly_.material_index = mi
                for li_, s_ in zip(poly_.loop_indices, shs):
                    ca.data[li_].color = (sh[0] + (1 - sh[0]) * s_, sh[1] + (1 - sh[1]) * s_, sh[2] + (1 - sh[2]) * s_, 1.0)
                    v = Vector(verts[me.loops[li_].vertex_index]) - anchor; uvl.data[li_].uv = (R.dot(v), U.dot(v))
            ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob); ob.visible_shadow = False; ob.lineart.usage = "EXCLUDE"
            keys = ([(start, True)] if f > start else []) + [(f, False), (f + step, True)]
            for kf, hide in keys: ob.hide_render = hide; ob.keyframe_insert("hide_render", frame=kf)
    sc.frame_set(start)
    return coll
