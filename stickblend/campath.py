"""Kamerapfade fuer One-Take-Shorts (ein durchgehender Kameraflug ueber globale Frames).

Keys: [(t, pos, look, fov[, "stop"]), ...] in Blender-Achsen, t in Sekunden.
- `path` legt eine Hermite-Kurve durch die Keys (stetige Geschwindigkeit, keine Stopps an Zwischen-Keys).
  "stop" am Key setzt dort die Tangente auf 0: die Kamera bremst weich ab statt zu ueberschiessen.
  Faustregel: "stop" an jeden Key setzen, auf den ein grosser Richtungs- oder Hoehenwechsel folgt
  (sonst schiesst die Hermite-Kurve ueber das Ziel hinaus).
- `rel` macht Keys relativ zu einem bewegten Objekt (Kabine, Fahrzeug): z(t) wird addiert.
- `camera` keyt die Kamera jedes Bild (LINEAR), Brennweite aus vertikalem FOV, sensor_fit VERTICAL (9:16).
Regeln (SHORTS-REGELN.md): nie durch Waende fliegen, Drehung <= ~90 deg/s, keine 180-Grad-Schwenks.
"""
import math
import bpy
from mathutils import Vector, Quaternion


def path(t, keys):
    if t <= keys[0][0]: k = keys[0]; return dict(p=k[1], l=k[2], fov=k[3])
    if t >= keys[-1][0]: k = keys[-1]; return dict(p=k[1], l=k[2], fov=k[3])
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    a, b = keys[i], keys[i + 1]; h = b[0] - a[0]; u = (t - a[0]) / h

    def tan(j, idx):
        if len(keys[j]) > 4 and keys[j][4] == "stop": return (0.0, 0.0, 0.0)
        k0 = keys[max(0, j - 1)]; k1 = keys[min(len(keys) - 1, j + 1)]
        if k1[0] == k0[0]: return (0.0, 0.0, 0.0)
        return tuple((k1[idx][c] - k0[idx][c]) / (k1[0] - k0[0]) for c in range(3))

    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    out = {}
    for idx, nm in ((1, "p"), (2, "l")):
        ma, mb = tan(i, idx), tan(i + 1, idx)
        out[nm] = tuple(h00 * a[idx][c] + h10 * h * ma[c] + h01 * b[idx][c] + h11 * h * mb[c] for c in range(3))
    out["fov"] = a[3] + (b[3] - a[3]) * (3 * u * u - 2 * u ** 3)
    return out


def rel(k, z):
    """Kamera-Key relativ zu einem Objekt, das sich in z bewegt (z. B. Aufzugskabine)."""
    return dict(p=(k["p"][0], k["p"][1], k["p"][2] + z), l=(k["l"][0], k["l"][1], k["l"][2] + z), fov=k["fov"])


def shake(t, amp):
    """Deterministisches Wackeln (Erschuetterung, Handkamera). amp in Metern."""
    return Vector((math.sin(t * 37.1) * 0.6 + math.sin(t * 23.7 + 1), math.sin(t * 29.3 + 2) * 0.7,
                   math.sin(t * 41.9 + 3) * 0.8 + math.sin(t * 17.3))) * amp


def camera(fn, f0, f1, fps=30, clip=(0.02, 2000), name="cam"):
    """fn(t) -> dict(p, l, fov[, roll]). Keyt jedes Bild von f0 bis f1."""
    cd = bpy.data.cameras.new(name); c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c); bpy.context.scene.camera = c
    cd.sensor_fit = "VERTICAL"; cd.sensor_height = 24; cd.clip_start, cd.clip_end = clip; c.rotation_mode = "QUATERNION"
    prev = None
    for f in range(f0, f1 + 1):
        t = (f - 1) / fps; k = fn(t); p, l = Vector(k["p"]), Vector(k["l"])
        c.location = p; q = (l - p).to_track_quat("-Z", "Y")
        if k.get("roll"): q = q @ Quaternion((0, 0, 1), k["roll"])
        if prev is not None and prev.dot(q) < 0: q.negate()
        prev = q.copy(); c.rotation_quaternion = q; cd.lens = 12 / math.tan(math.radians(k["fov"]) / 2)
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
    return c


def key_every_frame(sock, fn, f0, f1, fps=30, attr="default_value"):
    """Material-/Licht-Werte, die ueber lange Strecken umschalten, JEDES Bild keyen:
    sonst interpoliert Bezier zwischen weit entfernten Keys (z. B. Roentgen-Blende blendet ueber 6 s statt hart)."""
    for f in range(f0, f1 + 1):
        setattr(sock, attr, fn((f - 1) / fps)); sock.keyframe_insert(attr, frame=f)
