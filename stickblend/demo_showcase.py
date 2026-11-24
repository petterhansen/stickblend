"""Looping showcase animation of a single Stickblend figure cycling through 6 outfits & animations.

Designed to be encoded as a lightweight, high-impact GIF for the GitHub README.

Usage:
  blender -b --factory-startup -P stickblend/demo_showcase.py
  blender -b --factory-startup -P stickblend/demo_showcase.py -- 12,36,60,84,108,132
Output:
  stickblend/out/demo_showcase/f####.png
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

FPS = 15
SEG_FRAMES = 24       # 1.6 s per outfit/animation beat
NUM_SEGS = 6
FRAMES = SEG_FRAMES * NUM_SEGS  # 144 frames = 9.6 s seamless loop
OUT_DIR = REPO_ROOT / "stickblend" / "out" / "demo_showcase"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def spin_pop(local_f: int):
    """Quick 360-degree spin + tiny hop across segment boundaries for snappy wardrobe swaps."""
    # Incoming half-spin on frames 0..2, outgoing half-spin on frames SEG_FRAMES-2..SEG_FRAMES-1
    if local_f < 3:
        k = local_f / 3.0
        return -math.pi * (1.0 - k), math.sin(k * math.pi * 0.5) * 0.06
    if local_f >= SEG_FRAMES - 2:
        k = (local_f - (SEG_FRAMES - 2)) / 2.0
        return math.pi * k, math.sin((1.0 - k) * math.pi * 0.5) * 0.06
    return 0.0, 0.0


def cam_at(f: int):
    """Gentle seamless loop sway around center figure with generous head-to-toe headroom."""
    ang = 2.0 * math.pi * (f - 1) / FRAMES
    x = math.sin(ang) * 0.95
    z = 4.85 + math.cos(ang) * 0.18
    y = 1.28 + math.sin(ang * 2.0) * 0.04
    return dict(p=(x, y, z), l=(0.0, 1.00, 0.0), fov=42.0)


def main():
    t0 = time.time()
    stage.reset()

    # Clean, bright outdoor stage with warm sunlight, cobblestone, bench, streetlamp, and foliage
    ph.hdri("kloofendal_48d_partly_cloudy_puresky", strength=0.58, rot=0.85)
    world.sun(dir_deg=(46, 0, 132), energy=5.2, color=(1.0, 0.96, 0.88))
    mats.set_scene_light(tint=(1.0, 0.98, 0.95), rim_strength=0.18, rim_color=(1.0, 0.94, 0.82), rim_dir=(-0.4, 0.4, 0.7))
    ph.textured_ground("cobblestone_pavement", size=40, tile=2.2, tint=(0.91, 0.87, 0.81), bump=0.72)

    ph.place("street_lamp_01", tb((-2.1, 0, -2.4)), rot_z=math.pi * 0.85, scale=0.88)
    ph.place("painted_wooden_bench", tb((1.8, 0, -2.5)), rot_z=-0.28, scale=0.88)
    ph.place("shrub_01", tb((-2.5, 0, -2.0)), rot_z=0.5, scale=0.85)
    ph.place("shrub_01", tb((2.6, 0, -2.1)), rot_z=2.0, scale=0.80)

    specs_list = [
        ("detective", {"shoulderW": 0.165, "torso": {"color": "3c3844", "details": [{"type": "panel", "color": "f2efe8"}, {"type": "tie", "color": "8a2424"}, {"type": "scarf", "color": "c8a24a"}]}, "hat": {"type": "fedora", "color": "4a3a2c"}, "extras": ["monocle"], "face": {"mustache": True, "scar": True}}),
        ("chef",      {"shoulderW": 0.17,  "torso": {"color": "f0eee8", "details": [{"type": "apron", "color": "d8483c"}, {"type": "bowtie", "color": "2a2a2e"}]}, "hair": {"style": "curly", "color": "4a2c18"}, "face": {"beard": True, "blush": True}}),
        ("artist",    {"shoulderW": 0.15,  "torso": {"color": "2c3a4c", "pattern": "stripes", "pattern_color": "f0eee8", "details": [{"type": "scarf", "color": "d83838"}, {"type": "skirt", "color": "2a2430"}]}, "hat": {"type": "beret", "color": "9a242c"}, "hair": {"style": "ponytail", "color": "3a2416"}, "face": {"eyelashes": True, "freckles": True}}),
        ("king",      {"shoulderW": 0.18,  "torso": {"color": "6a1e34", "details": [{"type": "cape", "color": "8a223e"}, {"type": "belt", "color": "d8b44c", "buckle": "f0d86c"}, {"type": "medals"}]}, "hat": {"type": "crown", "color": "e8c048"}, "hair": {"style": "parted", "color": "5a4636"}, "face": {"beard": True, "mustache": True}}),
        ("banker",    {"shoulderW": 0.17,  "torso": {"color": "242834", "pattern": "pinstripe", "pattern_color": "4a5068", "details": [{"type": "suspenders", "color": "8a5428"}, {"type": "tie", "color": "2e6244"}]}, "hat": {"type": "tophat", "color": "1a1a20"}, "extras": ["glasses"], "face": {"goatee": True}}),
        ("punk",      {"shoulderW": 0.16,  "torso": {"color": "222228", "details": [{"type": "strap", "color": "c8c8d0"}, {"type": "belt", "color": "1a1a1a", "buckle": "d0d0d8"}]}, "hair": {"style": "mohawk", "color": "d4323c"}, "face": {"scar": True}}),
    ]

    built = []

    def make_fn(seg_idx, sp):
        def fn(lt):
            lf = max(0, min(SEG_FRAMES - 1, int(round(lt * FPS))))
            t_glob = (seg_idx * SEG_FRAMES + lf) / FPS
            ry_spin, hop = spin_pop(lf)

            if seg_idx == 0:    # Detective: facepalm -> present
                p = rig.poses_at(lt, [(0.0, "facepalm"), (0.75, "present")])
                mood = "worry" if lt < 0.72 else "happy"
                talk = 0.6 if lt > 0.78 else 0.0
                yaw = 0.12 + ry_spin
            elif seg_idx == 1:  # Chef: energetic clap
                p = rig.poses_at(lt, [(0.0, "present"), (0.25, "clap")])
                mood = "laugh"
                talk = 0.0
                yaw = 0.08 + ry_spin
            elif seg_idx == 2:  # Artist: hips -> cheerful wave
                p = rig.poses_at(lt, [(0.0, "hips"), (0.55, "wave")])
                mood = "laugh"
                talk = 0.0
                yaw = -0.05 + ry_spin
            elif seg_idx == 3:  # King: royal bow -> proud present
                p = rig.poses_at(lt, [(0.0, "bow"), (0.85, "present")])
                mood = "proud"
                talk = 0.0
                yaw = 0.05 + ry_spin
            elif seg_idx == 4:  # Banker: sly whisper -> arms crossed
                p = rig.poses_at(lt, [(0.0, "whisper"), (0.90, "crossed")])
                mood = "smug"
                talk = 0.55 if lt < 0.85 else 0.0
                yaw = -0.10 + ry_spin
            else:               # Punk: kick -> cheer!
                p = rig.poses_at(lt, [(0.0, "kick"), (0.80, "cheer")])
                mood = "angry" if lt < 0.78 else "laugh"
                talk = 0.0
                yaw = -0.14 + ry_spin

            r = rig.stick_rig(sp, p, t_glob, talk=talk)
            return dict(rig=rig.to_world(r, (0.0, hop, 0.0), yaw), mood=mood, blink=rig.blink_at(t_glob, seg_idx))
        return fn

    sc = bpy.context.scene
    sc.render.fps = FPS

    for i, (nm, sp) in enumerate(specs_list):
        ch = character.build(sp, nm)
        f0 = i * SEG_FRAMES + 1
        f1 = f0 + SEG_FRAMES - 1
        character.animate(ch, make_fn(i, sp), SEG_FRAMES, step=1, start=f0)
        # Hide 3D proxy meshes outside this character's segment so only the active character casts shadows
        for o in list(ch.coll.all_objects):
            if o is not None and o.type == "MESH":
                if f0 > 1:
                    o.hide_render = True
                    o.keyframe_insert("hide_render", frame=1)
                if "_face_" not in o.name:
                    o.hide_render = False
                    o.keyframe_insert("hide_render", frame=f0)
                if f1 < FRAMES:
                    o.hide_render = True
                    o.keyframe_insert("hide_render", frame=f1 + 1)
        built.append(ch)

    # Camera setup
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36
    cd.clip_start = 0.05
    cd.clip_end = 500
    cam.rotation_mode = "QUATERNION"
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 3.5

    for f in range(1, FRAMES + 1):
        k = cam_at(f)
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

    sc = stage.render_setup("final")
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = 800, 450
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = 6
    sc.render.image_settings.file_format = "PNG"
    world.optimize_shadows(cam=(0, 0, 0), max_dist=14)

    if stills:
        for s_ in stills:
            for c_old in [c for c in bpy.data.collections if c.name.startswith("flat")]:
                for o in list(c_old.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
                bpy.data.collections.remove(c_old)
            seg = min(NUM_SEGS - 1, (s_ - 1) // SEG_FRAMES)
            flat.flatten([built[seg]], cam, 1, step=1, start=s_)
            sc.frame_set(s_)
            sc.render.filepath = str(OUT_DIR / f"still_{s_:04d}")
            bpy.ops.render.render(write_still=True)
        print("STILLS_OK", len(stills), "in", round(time.time() - t0, 1), "s")
    else:
        for i in range(NUM_SEGS):
            f0 = i * SEG_FRAMES + 1
            coll = flat.flatten([built[i]], cam, SEG_FRAMES, step=1, start=f0)
            if f0 > 1:
                for o in coll.objects:
                    o.hide_render = True
                    o.keyframe_insert("hide_render", frame=1)
        sc.frame_start, sc.frame_end = 1, FRAMES
        sc.render.filepath = str(OUT_DIR / "f####")
        bpy.ops.render.render(animation=True)
        print("SHOWCASE_OK", FRAMES, "frames in", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
