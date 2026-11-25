"""Zeichnet die Penthouse-Taube (2D, Tusche-Kontur) in drei Posen -> blender/img/pigeon_*.png"""
from PIL import Image, ImageDraw
import math, pathlib
OUT = pathlib.Path(__file__).resolve().parent.parent / "blender" / "img"; OUT.mkdir(parents=True, exist_ok=True)
S = 4; W, H = 640, 560
INK = (43, 29, 22, 255); LW = 7 * S
def P(pts, ox, oy, rot, sc=1.0):
    c, s = math.cos(rot), math.sin(rot)
    return [((x * c - y * s) * sc * S + ox * S, (x * s + y * c) * sc * S + oy * S) for x, y in pts]
def ell(cx, cy, rx, ry, n=48, a0=0, a1=2 * math.pi): return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
def shape(d, pts, fill, ink=True):
    d.polygon(pts, fill=fill)
    if ink: d.line(pts + [pts[0]], fill=INK, width=LW, joint="curve")
def line(d, pts, w=LW, col=INK): d.line(pts, fill=col, width=w, joint="curve")

def pigeon(pose):
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rot = {"tv": -0.05, "toast": -0.05, "remote": -0.38}[pose]; ox, oy = 300, 330
    T = lambda pts: P(pts, ox, oy, rot)
    # Schwanz
    shape(d, T([(-150, 10), (-250, 40), (-255, 75), (-140, 60)]), (88, 96, 116, 255))
    line(d, T([(-235, 48), (-238, 68)]), 5 * S)
    # Fuesse (bei remote hochgelegt)
    if pose == "remote":
        for dx in (0, 26): line(d, T([(40 + dx, 95), (120 + dx, 150), (150 + dx, 142)]), 8 * S, (232, 112, 104, 255))
    else:
        for dx in (-20, 20): line(d, T([(dx, 100), (dx + 6, 138), (dx + 30, 140)]), 8 * S, (232, 112, 104, 255))
    # Koerper
    shape(d, T(ell(-20, 20, 150, 95)), (138, 148, 170, 255))
    d.polygon(T(ell(-20, 20, 150, 95, a0=0.35, a1=2.2)), fill=(108, 116, 138, 255))   # Schattensichel unten
    d.polygon(T(ell(30, 30, 95, 62)), fill=(176, 184, 202, 255))                        # helle Brust
    line(d, T(ell(-20, 20, 150, 95)) , LW)
    # Fluegel
    wing = ell(-55, 5, 105, 55, a0=math.pi * 0.95, a1=math.pi * 2.05)
    shape(d, T(wing), (104, 114, 136, 255))
    for k in (0, 1): line(d, T([(-110 + k * 34, -10), (-70 + k * 34, 30)]), 9 * S)
    # Hals (schillernd) + Kopf
    shape(d, T([(70, -40), (120, -100), (160, -95), (150, -10), (95, 20)]), (88, 150, 128, 255), ink=False)
    d.polygon(T([(110, -60), (150, -70), (150, -30), (115, -20)]), fill=(132, 98, 160, 255))
    hx, hy = 150, -125
    shape(d, T(ell(hx, hy, 58, 52)), (150, 160, 182, 255))
    line(d, T([(70, -40), (98, -85)]), LW); line(d, T([(150, -10), (178, -78)]), LW)
    # Schnabel
    shape(d, T([(hx + 50, hy - 4), (hx + 92, hy + 10), (hx + 48, hy + 18)]), (70, 62, 66, 255))
    d.polygon(T(ell(hx + 56, hy - 2, 10, 7)), fill=(240, 236, 228, 255))
    # Sonnenbrille
    for gx in (hx + 12, hx + 44):
        shape(d, T(ell(gx, hy - 12, 19, 15)), (18, 18, 24, 255))
        d.polygon(T(ell(gx + 6, hy - 18, 6, 4)), fill=(255, 255, 255, 220))
    line(d, T([(hx + 30, hy - 14), (hx + 26, hy - 16)]), 6 * S); line(d, T([(hx - 8, hy - 14), (hx - 40, hy - 8)]), 6 * S)
    # Requisiten
    if pose == "toast":   # Fluegelspitze hebt Mini-Kaffeebecher
        line(d, T([(-10, -20), (70, -95), (100, -150)]), 22 * S, (104, 114, 136, 255)); line(d, T([(-10, -20), (70, -95), (100, -150)]), 4 * S)
        cup = [(80, -230), (128, -230), (120, -170), (88, -170)]
        shape(d, T(cup), (246, 242, 234, 255)); d.polygon(T([(82, -222), (126, -222), (125, -212), (83, -212)]), fill=(122, 78, 46, 255))
        line(d, T(ell(132, -205, 12, 14, a0=-1.4, a1=1.4)), 5 * S)
        for k in range(3): line(d, T([(92 + k * 12, -245), (98 + k * 12, -262), (92 + k * 12, -278)]), 4 * S, (255, 255, 255, 160))
    if pose == "remote":
        line(d, T([(20, -10), (120, -40), (190, -30)]), 22 * S, (104, 114, 136, 255)); line(d, T([(20, -10), (120, -40), (190, -30)]), 4 * S)
        shape(d, T([(178, -50), (250, -62), (254, -40), (182, -28)]), (34, 34, 40, 255)); d.polygon(T(ell(238, -50, 6, 5)), fill=(230, 50, 46, 255))
    return im.resize((W, H), Image.LANCZOS)

for p in ("tv", "toast", "remote"): pigeon(p).save(OUT / f"pigeon_{p}.png")
# Komposit zur Kontrolle
sheet = Image.new("RGBA", (W * 3, H), (200, 190, 175, 255))
for i, p in enumerate(("tv", "toast", "remote")): sheet.alpha_composite(Image.open(OUT / f"pigeon_{p}.png"), (i * W, 0))
sheet.save(OUT / "pigeon_sheet.png"); print("ok")
