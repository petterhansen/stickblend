"""Perspective-switch demo: 3rd-person <-> 1st-person figure POV in stickblend.

Beats (240 frames @ 30 fps = 8.0 s):
  1..60   : 3rd-person establishing shot (Detective, Artist, King)
  61..132 : Detective's 1st-person POV (looking at Artist & King, gesturing with own hand)
  133..196: Artist's 1st-person POV (looking at Detective & King)
  197..240: 3rd-person wide finale (all cheering)

Usage:
  blender -b --factory-startup -P stickblend/demo_pov.py
  blender -b --factory-startup -P stickblend/demo_pov.py -- 30,85,155,220
"""
import math
import pathlib
import sys
import time
import bpy

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stickblend import character, flat, mats, paths, ph, rig, stage, world
from stickblend.geo import tb

FPS = 30
FRAMES = 240
OUT_DIR = REPO_ROOT / "stickblend" / "out" / "demo_pov"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def third_person_cam(f: int):
    t = (f - 1) / FPS
    if f <= 60:
        k = (f - 1) / 59.0
        p = (-0.25 + 0.50 * k, 1.32, 3.15)
        l = (0.0, 0.96, -0.70)
        return tb(p), (tb(l) - tb(p)).to_track_quat("-Z", "Y"), 38.0
    k = max(0.0, min(1.0, (f - 197) / 43.0))
    p = (0.0, 1.42 + 0.08 * k, 3.35 + 0.35 * k)
    l = (0.0, 0.96, -0.75)
    return tb(p), (tb(l) - tb(p)).to_track_quat("-Z", "Y"), 35.0


def main():
    t0 = time.time()
    stage.reset()

    ph.hdri("kloofendal_48d_partly_cloudy_puresky", strength=0.58, rot=0.85)
    world.sun(dir_deg=(46, 0, 132), energy=5.2, color=(1.0, 0.96, 0.88))
    mats.set_scene_light(tint=(1.0, 0.98, 0.95), rim_strength=0.18, rim_color=(1.0, 0.94, 0.82), rim_dir=(-0.4, 0.4, 0.7))
    ph.textured_ground("cobblestone_pavement", size=40, tile=2.2, tint=(0.91, 0.87, 0.81), bump=0.72)

    ph.place("street_lamp_01", tb((-2.5, 0, -2.2)), rot_z=math.pi * 0.85, scale=0.90)
    ph.place("painted_wooden_bench", tb((2.3, 0, -2.3)), rot_z=-0.55, scale=0.90)
    ph.place("painted_wooden_bench", tb((-2.4, 0, -0.4)), rot_z=math.pi * 0.45, scale=0.88)
    ph.place("street_lamp_01", tb((2.5, 0, -0.2)), rot_z=-math.pi * 0.4, scale=0.90)
    ph.place("shrub_01", tb((-2.8, 0, -1.8)), rot_z=0.5, scale=0.85)
    ph.place("shrub_01", tb((2.8, 0, -1.8)), rot_z=2.0, scale=0.80)

    opt_tree = paths.ASSETS3D / "optimized" / "jacaranda_tree_opt.blend"
    if opt_tree.exists():
        world.place("JacarandaOpt", tb((-4.2, 0, -4.8)), rot_z=0.4, scale=0.40, lib=str(opt_tree))
        world.place("JacarandaOpt", tb((4.2, 0, -4.8)), rot_z=2.2, scale=0.40, lib=str(opt_tree))

    sp_det = {"shoulderW": 0.165, "torso": {"color": "3c3844", "details": [{"type": "panel", "color": "f2efe8"}, {"type": "tie", "color": "8a2424"}, {"type": "scarf", "color": "c8a24a"}]}, "hat": {"type": "fedora", "color": "4a3a2c"}, "extras": ["monocle"], "face": {"mustache": True, "scar": True}}
    sp_art = {"shoulderW": 0.15,  "torso": {"color": "2c3a4c", "pattern": "stripes", "pattern_color": "f0eee8", "details": [{"type": "scarf", "color": "d83838"}, {"type": "skirt", "color": "2a2430"}]}, "hat": {"type": "beret", "color": "9a242c"}, "hair": {"style": "ponytail", "color": "3a2416"}, "face": {"eyelashes": True, "freckles": True}}
    sp_kng = {"shoulderW": 0.18,  "torso": {"color": "6a1e34", "details": [{"type": "cape", "color": "8a223e"}, {"type": "belt", "color": "d8b44c", "buckle": "f0d86c"}, {"type": "medals"}]}, "hat": {"type": "crown", "color": "e8c048"}, "hair": {"style": "parted", "color": "5a4636"}, "face": {"beard": True, "mustache": True}}

    det = character.build(sp_det, "detective")
    art = character.build(sp_art, "artist")
    kng = character.build(sp_kng, "king")

    def fn_det(t):
        p = rig.poses_at(t, [(0.0, "present"), (2.0, "wave"), (3.1, "point"), (4.4, "facepalm"), (5.5, "shrug"), (6.6, "cheer")])
        if 2.0 <= t < 4.4:
            # Detective POV: bring waving/pointing hand forward into 1st-person view & look at Artist + King
            if t < 3.1:
                p["handL"] = (0.14 + 0.04 * math.sin((t - 2.0) * 10.0), 1.50, 0.46)
            p["headYaw"] = -8.0 * math.sin((t - 2.0) * 1.4)
            p["headPitch"] = 2.0 + 2.0 * math.cos((t - 2.0) * 2.0)
            yaw = 1.78
        elif 4.4 <= t < 6.5:
            # Being looked at by Artist: face toward Artist
            yaw = 1.50
        else:
            yaw = 0.18
        mood = "worry" if 4.4 <= t < 5.6 else ("laugh" if t >= 6.6 else "happy")
        return dict(rig=rig.to_world(rig.stick_rig(sp_det, p, t, talk=0.5 if t < 2.0 else 0.0), (-0.95, 0, -0.35), yaw), mood=mood, blink=rig.blink_at(t, 0))

    def fn_art(t):
        p = rig.poses_at(t, [(0.0, "hips"), (1.8, "wave"), (3.2, "clap"), (4.4, "present"), (6.6, "cheer")])
        if 4.4 <= t < 6.5:
            # Artist POV: reach hand into 1st-person view & look across at Detective + King
            p["handL"] = (0.15, 1.48 + 0.03 * math.sin((t - 4.4) * 6.0), 0.46)
            p["headYaw"] = 10.0 * math.sin((t - 4.4) * 1.5)
            p["headPitch"] = 2.0 + 2.0 * math.cos((t - 4.4) * 2.0)
            yaw = -1.82
        elif 2.0 <= t < 4.4:
            # Being looked at by Detective: face toward Detective
            yaw = -1.48
        else:
            yaw = -0.18
        return dict(rig=rig.to_world(rig.stick_rig(sp_art, p, t), (0.95, 0, -0.35), yaw), mood="laugh", blink=rig.blink_at(t, 2))

    def fn_kng(t):
        p = rig.poses_at(t, [(0.0, "idle"), (2.2, "bow"), (3.4, "present"), (4.6, "clap"), (6.6, "cheer")])
        return dict(rig=rig.to_world(rig.stick_rig(sp_kng, p, t), (0.0, 0, -1.35), 0.0), mood="proud" if t < 6.5 else "laugh", blink=rig.blink_at(t, 3))

    sc = bpy.context.scene
    sc.render.fps = FPS

    character.animate(det, fn_det, FRAMES, step=2)
    character.animate(art, fn_art, FRAMES, step=2)
    character.animate(kng, fn_kng, FRAMES, step=2)

    # Setup camera & keyframe 3rd-person <-> POV switches
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36
    cd.clip_start = 0.03
    cd.clip_end = 500
    cam.rotation_mode = "QUATERNION"
    cd.dof.use_dof = False

    def pov_at(f: int):
        if 61 <= f <= 132:
            return det
        if 133 <= f <= 196:
            return art
        return None

    for f in range(1, FRAMES + 1, 2):
        sc.frame_set(f)
        p_ch = pov_at(f)
        if p_ch is not None:
            loc, quat, _ = rig.pov_pose(p_ch, eye_fwd=0.02, eye_up=0.05, roll_keep=0.28)
            lens = 24.0
        else:
            loc, quat, lens = third_person_cam(f)
        cam.location = loc
        cam.rotation_quaternion = quat
        cd.lens = lens
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cd.keyframe_insert("lens", frame=f)

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    stills = [int(x) for x in argv[0].split(",")] if argv else None

    sc = stage.render_setup("final")
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = 6
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 94
    world.optimize_shadows(cam=(0, 0, 0), max_dist=16)

    chars = [det, art, kng]
    if stills:
        for s_ in stills:
            for c_old in [c for c in bpy.data.collections if c.name.startswith("flat")]:
                for o in list(c_old.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.collections.remove(c_old)
            flat.flatten(chars, cam, 1, step=1, start=s_, pov=pov_at, pov_hands=True)
            sc.frame_set(s_)
            sc.render.filepath = str(OUT_DIR / f"still_{s_:04d}")
            bpy.ops.render.render(write_still=True)
        print("STILLS_OK", len(stills), "in", round(time.time() - t0, 1), "s")
    else:
        flat.flatten(chars, cam, FRAMES, step=2, start=1, pov=pov_at, pov_hands=True)
        sc.frame_start, sc.frame_end = 1, FRAMES
        sc.render.filepath = str(OUT_DIR / "f####")
        bpy.ops.render.render(animation=True)
        print("POV_OK", FRAMES, "frames in", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
