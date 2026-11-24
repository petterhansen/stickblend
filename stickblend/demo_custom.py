"""Animated 10-second demo showcasing all new stickblend figure customizations, poses, and animations.

Usage:
  blender -b --factory-startup -P stickblend/demo_custom.py
Output:
  stickblend/out/demo_custom/f####.jpg -> stickblend/out/demo_custom.mp4
"""
import math
import os
import pathlib
import sys
import time
import bpy
from mathutils import Vector

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stickblend import character, flat, mats, paths, ph, rig, stage, world
from stickblend.geo import tb

FPS = 30
FRAMES = 300  # 10 seconds
OUT_DIR = REPO_ROOT / "stickblend" / "out" / "demo_custom"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return k * k * (3.0 - 2.0 * k)


def mixv(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def cam_at(t: float):
    """Smooth wide-to-medium camera glide & orbit showing full characters head-to-toe with headroom."""
    keys = [
        (0.0, (-3.2, 1.55, 2.2), (-2.4, 1.05, -2.5), 42),
        (2.5, (-1.0, 1.55, 2.0), (-0.8, 1.05, -2.5), 42),
        (5.2, (1.4, 1.55, 2.0), (1.1, 1.05, -2.5), 42),
        (7.2, (4.2, 1.65, 0.8), (2.2, 1.05, -2.5), 44),
        (8.6, (2.6, 1.85, -6.4), (0.0, 1.05, -2.5), 46),   # Clean back orbit showing cape, ponytail, hats!
        (10.0, (0.0, 1.85, 4.4), (0.0, 1.05, -2.5), 46),   # Wide full-cast finale with headroom + shadows
    ]
    if t <= keys[0][0]:
        _, p, l, fov = keys[0]
        return dict(p=p, l=l, fov=fov)
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            k = ease((t - a[0]) / (b[0] - a[0]))
            return dict(p=mixv(a[1], b[1], k), l=mixv(a[2], b[2], k), fov=a[3] + (b[3] - a[3]) * k)
    _, p, l, fov = keys[-1]
    return dict(p=p, l=l, fov=fov)


def main():
    t0 = time.time()
    stage.reset()

    # HQ Environment (Poly Haven pure-sky HDRI, cobblestone, streetlamps, benches, optimized trees)
    ph.hdri("kloofendal_48d_partly_cloudy_puresky", strength=0.55, rot=0.8)
    world.sun(dir_deg=(48, 0, 130), energy=5.0, color=(1.0, 0.96, 0.88))
    mats.set_scene_light(tint=(1.0, 0.98, 0.95), rim_strength=0.18, rim_color=(1.0, 0.94, 0.82), rim_dir=(-0.4, 0.4, 0.7))
    ph.textured_ground("cobblestone_pavement", size=50, tile=2.4, tint=(0.90, 0.86, 0.80), bump=0.75)

    for sx in (-3.6, 3.6):
        ph.place("street_lamp_01", tb((sx, 0, -4.6)), rot_z=0.0 if sx > 0 else math.pi, scale=0.92)
        ph.place("painted_wooden_bench", tb((sx * 0.75, 0, -5.2)), rot_z=0.0, scale=0.92)
        ph.place("shrub_01", tb((sx * 1.15, 0, -4.2)), rot_z=sx, scale=0.85)

    opt_tree = paths.ASSETS3D / "optimized" / "jacaranda_tree_opt.blend"
    if opt_tree.exists():
        world.place("JacarandaOpt", tb((-4.8, 0, -6.5)), rot_z=0.4, scale=0.40, lib=str(opt_tree))
        world.place("JacarandaOpt", tb((4.8, 0, -6.5)), rot_z=2.1, scale=0.40, lib=str(opt_tree))

    # 6 Custom Characters showcasing new hats, hair, outfits, faces & animations
    specs_list = [
        ("detective", {"shoulderW": 0.165, "torso": {"color": "3c3844", "details": [{"type": "panel", "color": "f2efe8"}, {"type": "tie", "color": "8a2424"}, {"type": "scarf", "color": "c8a24a"}]}, "hat": {"type": "fedora", "color": "4a3a2c"}, "extras": ["monocle"], "face": {"mustache": True, "scar": True}}),
        ("chef",      {"shoulderW": 0.17,  "torso": {"color": "f0eee8", "details": [{"type": "apron", "color": "d8483c"}, {"type": "bowtie", "color": "2a2a2e"}]}, "hair": {"style": "curly", "color": "4a2c18"}, "face": {"beard": True, "blush": True}}),
        ("artist",    {"shoulderW": 0.15,  "torso": {"color": "2c3a4c", "pattern": "stripes", "pattern_color": "f0eee8", "details": [{"type": "scarf", "color": "d83838"}, {"type": "skirt", "color": "2a2430"}]}, "hat": {"type": "beret", "color": "9a242c"}, "hair": {"style": "ponytail", "color": "3a2416"}, "face": {"eyelashes": True, "freckles": True}}),
        ("king",      {"shoulderW": 0.18,  "torso": {"color": "6a1e34", "details": [{"type": "cape", "color": "8a223e"}, {"type": "belt", "color": "d8b44c", "buckle": "f0d86c"}, {"type": "medals"}]}, "hat": {"type": "crown", "color": "e8c048"}, "hair": {"style": "parted", "color": "5a4636"}, "face": {"beard": True, "mustache": True}}),
        ("banker",    {"shoulderW": 0.17,  "torso": {"color": "242834", "pattern": "pinstripe", "pattern_color": "4a5068", "details": [{"type": "suspenders", "color": "8a5428"}, {"type": "tie", "color": "2e6244"}]}, "hat": {"type": "tophat", "color": "1a1a20"}, "extras": ["glasses"], "face": {"goatee": True}}),
        ("punk",      {"shoulderW": 0.16,  "torso": {"color": "222228", "details": [{"type": "strap", "color": "c8c8d0"}, {"type": "belt", "color": "1a1a1a", "buckle": "d0d0d8"}]}, "hair": {"style": "mohawk", "color": "d4323c"}, "face": {"scar": True}}),
    ]

    xs = [-3.125, -1.875, -0.625, 0.625, 1.875, 3.125]
    built = []

    def make_fn(idx, sp):
        x0 = xs[idx]
        def fn(t):
            if idx == 0:  # Detective
                p = rig.poses_at(t, [(0.0, "facepalm"), (1.8, "present"), (7.5, "cheer")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t, talk=0.7 if 1.8 < t < 4.0 else 0.0), (x0, 0, -2.5), 0.15), mood="happy" if t > 1.8 else "worry", blink=rig.blink_at(t, 0))
            if idx == 1:  # Chef
                p = rig.poses_at(t, [(0.0, "present"), (3.0, "clap"), (7.5, "cheer")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t, talk=0.6 if t < 3.0 else 0.0), (x0, 0, -2.5), 0.08), mood="laugh" if t > 3.0 else "happy", blink=rig.blink_at(t, 1))
            if idx == 2:  # Artist
                p = rig.poses_at(t, [(0.0, "hips"), (2.8, "cheer"), (7.5, "wave")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t), (x0, 0, -2.5), 0.0), mood="laugh", blink=rig.blink_at(t, 2))
            if idx == 3:  # King
                p = rig.poses_at(t, [(0.0, "lean_back"), (3.5, "bow"), (6.0, "present"), (8.2, "cheer")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t), (x0, 0, -2.5), 0.0), mood="proud", blink=rig.blink_at(t, 3))
            if idx == 4:  # Banker
                p = rig.poses_at(t, [(0.0, "crossed"), (4.5, "whisper"), (7.5, "cheer")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t, talk=0.6 if 4.5 < t < 6.8 else 0.0), (x0, 0, -2.5), -0.08), mood="smug", blink=rig.blink_at(t, 4))
            # Punk: kick then run in a quick circle and cheer!
            if t < 5.0:
                p = rig.poses_at(t, [(0.0, "idle"), (1.5, "kick"), (3.5, "nervous")])
                return dict(rig=rig.to_world(rig.stick_rig(sp, p, t), (x0, 0, -2.5), -0.15), mood="angry" if t < 3.5 else "determined", blink=rig.blink_at(t, 5))
            pos, yaw, spd = rig.walk_along(t, [(5.0, x0, -2.5), (6.5, x0 + 0.6, -1.6), (8.0, x0, -2.5)])
            p = rig.poses_at(t, [(5.0, "idle"), (8.1, "cheer")])
            return dict(rig=rig.to_world(rig.stick_rig(sp, p, t, run=spd), pos, yaw), mood="laugh" if t > 8.0 else "determined", blink=rig.blink_at(t, 5))
        return fn

    for i, (nm, sp) in enumerate(specs_list):
        ch = character.build(sp, nm)
        character.animate(ch, make_fn(i, sp), FRAMES, step=2)
        built.append(ch)

    # Keyframe smooth camera on every frame (1..FRAMES)
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 500
    cam.rotation_mode = "QUATERNION"
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 3.2
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FPS
        k = cam_at(t)
        p, l = tb(k["p"]), tb(k["l"])
        cam.location = p
        cam.rotation_quaternion = (l - p).to_track_quat("-Z", "Y")
        cd.lens = 18.0 / math.tan(math.radians(k["fov"]) / 2.0)
        cd.dof.focus_distance = (l - p).length
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cd.keyframe_insert("lens", frame=f)
        cd.dof.keyframe_insert("focus_distance", frame=f)

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills = [int(x) for x in argv[0].split(",")] if argv else None

    if stills:
        sc = stage.render_setup("final")
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
        sc.render.resolution_percentage = 100
        sc.eevee.taa_render_samples = 6
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 95
        world.optimize_shadows(cam=(0, 0, 0), max_dist=18)
        for s_ in stills:
            if "flat" in bpy.data.collections:
                c_old = bpy.data.collections["flat"]
                for o in list(c_old.objects): bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.collections.remove(c_old)
            flat.flatten(built, cam, 1, step=1, start=s_)
            sc.frame_set(s_)
            sc.render.filepath = str(OUT_DIR / f"still_{s_:04d}")
            bpy.ops.render.render(write_still=True)
        print("STILLS_OK", len(stills), "in", round(time.time() - t0, 1), "s")
    else:
        flat.flatten(built, cam, FRAMES, step=2, start=1)
        sc = stage.render_setup("final")
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
        sc.render.resolution_percentage = 100
        sc.eevee.taa_render_samples = 6
        sc.frame_start, sc.frame_end = 1, FRAMES
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 95
        world.optimize_shadows(cam=(0, 0, 0), max_dist=18)
        sc.render.filepath = str(OUT_DIR / "f####")
        bpy.ops.render.render(animation=True)
        print("DEMO_OK", FRAMES, "frames in", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
