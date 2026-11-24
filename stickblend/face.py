"""Gesichter als Strich-Primitive (Port von onoda/src/stick/Face.ts).

Koordinaten: Gesichts-Canvas 512 x 512 (wie three.js), wird in draw.py auf die Kopfkugel gemappt.
Primitive:
  ("line", [(x, y), ...], breite_px, farbe, geschlossen)
  ("fill", [(x, y), ...], farbe, kontur_px)      kontur_px = 0 -> ohne Kontur
  ("dot",  (x, y), radius_px, farbe)
"""
import math

MOODS = ["neutral", "happy", "laugh", "smug", "sly", "shock", "scared", "angry", "sad", "worry", "tired", "determined", "suspicious", "proud", "cry", "closed"]
BROWS = {"neutral": (0, 0), "happy": (-8, -6), "laugh": (-10, -8), "smug": (6, -6), "sly": (10, -6), "shock": (-26, -20), "scared": (-22, 6), "angry": (22, -10), "sad": (-18, 10),
         "worry": (-18, 8), "tired": (-4, 8), "determined": (16, -6), "suspicious": (14, -2), "proud": (6, -8), "cry": (-20, 10), "closed": (0, 0)}

def q2(a, c, b, n=10):
    return [(a[0] * (1 - t) ** 2 + c[0] * 2 * t * (1 - t) + b[0] * t * t, a[1] * (1 - t) ** 2 + c[1] * 2 * t * (1 - t) + b[1] * t * t) for t in (i / n for i in range(n + 1))]
def ell(x, y, rx, ry, n=18): return [(x + rx * math.cos(2 * math.pi * i / n), y + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]

def face_prims(mood="neutral", blink=False, mouth=0.0, look=(0, 0), stubble=False, age=0, nose=True, blush=False, tears=False, sweat=False,
               ink="2b1d16", eye_highlight=False, mouth_dark="3a1218", eyes="dark",
               mustache=False, muttonchops=False, beard=False, goatee=False, freckles=False, scar=False, eyelashes=False, facial_hair_color="5e4c3a"):
    P = []; m = mood; closed = blink or m == "closed"
    lx, ly = look[0] * 14, look[1] * 10
    # Bartschatten + Stoppeln (unter allem anderen)
    if stubble:
        sh = q2((120, 300), (256, 520), (392, 300), 14) + q2((392, 300), (330, 345), (256, 340), 6)[1:] + q2((256, 340), (182, 345), (120, 300), 6)[1:]
        P.append(("fill", sh, ("8a8ca4", 0.42), 0))
        sd = [7]
        def R():
            sd[0] = (sd[0] * 16807) % 2147483647; return sd[0] / 2147483647
        for i in range(520):
            a = R() * math.pi; rr = 40 + R() * 105; x = 256 + math.cos(a) * rr * 1.2; y = 318 + math.sin(a) * rr * 0.8; r = 2 + R() * 1.6
            if y > 296 and math.hypot(x - 262, y - 362) > 34 and i % 2 == 0: P.append(("dot", (x, y), r * 1.3, "19191f"))
    if age:
        for k in range(age): P.append(("line", q2((200, 140 - k * 12), (256, 132 - k * 12), (312, 140 - k * 12), 8), 4, "6a5a52", False))
    if blush:
        for x, y in ((160, 300), (352, 300)): P.append(("fill", ell(x, y, 30, 16), ("ff6e78", 0.35), 0))
    if beard:
        bd = q2((146, 305), (256, 515), (366, 305), 14) + q2((366, 305), (312, 345), (256, 336), 6)[1:] + q2((256, 336), (200, 345), (146, 305), 6)[1:]
        P.append(("fill", bd, facial_hair_color, 7))
    if goatee:
        gt = q2((222, 375), (256, 468), (290, 375), 10) + [(256, 392)]
        P.append(("fill", gt, facial_hair_color, 6))
    # Augen
    for x, y in ((196, 236), (316, 236)):
        if closed: P.append(("line", q2((x - 22, y + 4), (x, y + 14), (x + 22, y + 4)), 11, ink, False)); continue
        if m in ("happy", "laugh"): P.append(("line", q2((x - 24, y + 8), (x, y - 22), (x + 24, y + 8)), 11, ink, False)); continue
        if m in ("shock", "scared"):
            P.append(("fill", ell(x, y, 30, 34), "ffffff", 8)); P.append(("dot", (x + lx * 0.6, y + ly * 0.6), 10, ink)); continue
        sq = 0.55 if m in ("suspicious", "sly", "smug") else 0.6 if m == "tired" else 0.8 if m in ("determined", "angry") else 1.0
        if eyes == "white":   # weisse Augen mit Pupille (zweite Referenz)
            P.append(("fill", ell(x, y, 27, 30 * max(0.55, sq)), "ffffff", 7)); P.append(("fill", ell(x + lx * 0.8, y + ly * 0.8 + 3, 11, 12 * max(0.6, sq)), ink, 0))
            if sq < 0.7: P.append(("fill", [(x - 30, y - 32), (x + 30, y - 32), (x + 30, y - 30 * sq + 6), (x - 30, y - 30 * sq + 6)], "f4efe6", 0)); P.append(("line", [(x - 28, y - 30 * sq + 6), (x + 28, y - 30 * sq + 6)], 7, ink, False))
            continue
        P.append(("fill", ell(x + lx, y + ly, 15, 21 * sq), ink, 0))
        if eye_highlight: P.append(("dot", (x + lx + 5, y + ly - 7 * sq), 4.5, "ffffff"))
        if m == "tired": P.append(("line", q2((x - 20, y + 26), (x, y + 34), (x + 20, y + 26)), 6, ink, False))
        if sq < 0.7: P.append(("line", [(x - 24, y - 12), (x + 24, y - 14)], 9, ink, False))
    bi, bo = BROWS.get(m, (0, 0))
    for x, l, r in ((196, bo, bi), (316, bi, bo)): P.append(("line", q2((x - 32, 188 + l), (x, 176 + (l + r) / 2), (x + 32, 188 + r)), 13, ink, False))
    if nose: P.append(("line", [(286, 252), (296, 312), (276, 316)], 8, ink, False))
    mo = max(0.0, min(1.0, mouth)); mx, my = 262, 362
    if m in ("shock", "scared"): P.append(("fill", ell(mx, my + 8, 22 + mo * 6, 30 + mo * 12), mouth_dark, 8))
    elif m == "laugh" or mo > 0.15:
        lip = q2((mx - 46, my - 6), (mx, my - 2), (mx + 44, my - 10), 8) + q2((mx + 44, my - 10), (mx + 6, my + 30 + mo * 30 + (20 if m == "laugh" else 0)), (mx - 46, my - 6), 10)[1:]
        P.append(("fill", lip, mouth_dark, 8)); P.append(("fill", ell(mx, my + 10 + mo * 14, 14, 5 + mo * 5), "d8606a", 0))
    elif m in ("happy", "proud"): P.append(("line", q2((mx - 44, my - 8), (mx, my + 32), (mx + 42, my - 10)), 10, ink, False))
    elif m in ("smug", "sly"): P.append(("line", q2((mx - 46, my - 10), (mx - 10, my + 16), (mx + 40, my - 6)), 10, ink, False))
    elif m in ("sad", "cry", "angry", "worry"): P.append(("line", q2((mx - 34, my + 12), (mx, my - 12), (mx + 34, my + 10)), 10, ink, False))
    elif m == "determined": P.append(("line", [(mx - 32, my), (mx + 32, my - 2)], 10, ink, False))
    else: P.append(("line", q2((mx - 30, my), (mx, my + 8), (mx + 30, my - 2)), 10, ink, False))
    if tears or m == "cry":
        for x, y in ((178, 270), (334, 270)): P.append(("fill", q2((x, y), (x + 14, y + 40), (x, y + 52), 6) + q2((x, y + 52), (x - 14, y + 40), (x, y), 6)[1:], "7cc6f2", 5))
    if sweat: P.append(("fill", q2((400, 160), (420, 200), (400, 214), 6) + q2((400, 214), (380, 200), (400, 160), 6)[1:], "9fd3f5", 5))
    if freckles:
        for sx in (-1, 1):
            for dx, dy in ((-18, 0), (0, -7), (16, 4)):
                P.append(("dot", (256 + sx * 100 + dx, 286 + dy), 3.6, "b87a56"))
    if scar:
        P.append(("line", [(328, 175), (366, 290)], 7, "a85652", False))
        for sy in (202, 232, 262):
            P.append(("line", [(328 + (sy - 175) * 0.33 - 8, sy + 2), (328 + (sy - 175) * 0.33 + 8, sy - 2)], 4, "a85652", False))
    if eyelashes:
        for sx, ex in ((-1, 172), (1, 340)):
            P.append(("line", [(ex, 224), (ex + sx * 18, 210)], 6, ink, False))
            P.append(("line", [(ex + sx * 4, 234), (ex + sx * 20, 226)], 5, ink, False))
    if muttonchops:
        for side in (-1, 1):
            cx = 256 + side * 136
            chop = q2((cx, 250), (cx + side * 26, 330), (cx - side * 18, 405), 8) + q2((cx - side * 18, 405), (cx - side * 46, 365), (cx - side * 22, 275), 8)[1:]
            P.append(("fill", chop, facial_hair_color, 6))
    if mustache:
        must = (
            q2((256, 318), (210, 312), (170, 352), 8)
            + q2((170, 352), (215, 366), (256, 346), 8)[1:]
            + q2((256, 346), (297, 366), (342, 352), 8)[1:]
            + q2((342, 352), (302, 312), (256, 318), 8)[1:]
        )
        P.append(("fill", must, facial_hair_color, 6))
    return P
