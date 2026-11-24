---
name: stickblend-shorts
description: Produce a ~55-70s vertical 2.5D stickman story short rendered in Blender 5.2 EEVEE (stickblend) and composited in Remotion (voiceover, ducked music, SFX, captions, SVG overlays). Use when asked to create a Blender 2.5D stickman short or to use the stickblend workflow.
---

# Stickblend 2.5D Short Workflow (Blender 5.2 + Remotion)

Hybrid pipeline for vertical animated story shorts:
- **HQ 3D worlds + 2.5D stickman actors:** rendered per scene in **Blender 5.2 EEVEE** via the reusable `stickblend/` Python library (flat 2.5D character cutouts casting real 3D shadows into realistic Poly Haven PBR environments with volumetric haze, DOF, and bloom).
- **Voice & word timings:** generated in one call via Gemini TTS (`scripts/voice_gemini.py`) and aligned to word timestamps with `faster-whisper` → `timeline.json`.
- **Sound:** reusable royalty-free music & CC0 SFX from `assets_audio/` (fetched via `python stickblend/tools/fetch_audio.py`), with `scripts/sfx.py` available for custom sounds.
- **Final compositing:** Remotion (`remotion/src/shared/StickblendShort.tsx`) stitches per-scene MP4 clips (`OffthreadVideo`), voiceover, ducked music, SFX cues, film grain, captions, and SVG overlays.

## Directory Layout

```text
<repo_root>/
  stickblend/                 # Reusable Blender 5.2 2.5D stickman & 3D world library
    paths.py                  # Resolves ASSETS3D_DIR (Poly Haven, Quaternius, Kenney)
    specs.py                  # Character specs (add new cast here)
    rig.py                    # Skeleton, IK, POSES library, pose blending, walk cycle
    face.py                   # 16 facial expressions + mustache/muttonchops/stubble
    character.py              # Build & animate 3D proxy rig
    flat.py                   # 2.5D cutout flattener (ink outline, shade zone, 3D shadows)
    mats.py / geo.py          # Flat fill + shade zone, Geometry Nodes ink, scene light tint/rim
    stage.py                  # Reset, camera, EEVEE render presets (preview / final / final_hq)
    world.py / ph.py          # Poly Haven PBR/glTF/HDRI + Quaternius loaders, ph.place_on()
    sets.py / sets2.py        # Reusable environment builders & color grading
    lineup.py                 # Cast turnaround verification render
    tools/polyhaven.py        # Fetch CC0 Poly Haven models, PBR textures, HDRIs
    tools/fetch_audio.py      # Fetch royalty-free storytelling music + CC0 SFX packs
  stickblend-shorts/
    SKILL.md                  # This workflow guide
    new_short.ps1             # Scaffolds a new short project from templates/short/
    templates/short/          # Starter STORY.md, script.json, scripts/, blender/
  remotion/
    src/shared/StickblendShort.tsx
    public/shorts/<slug>/     # Synced bl/*.mp4 + audio/* for Remotion
```

## Step-by-Step Pipeline

### 1. Scaffold a New Short
```powershell
.\stickblend-shorts\new_short.ps1 -Slug <slug>
```
Creates `<repo_root>\<slug>\` with `STORY.md`, `script.json`, `scripts/`, and `blender/`.

### 2. Story, Facts & Script
1. Write verified facts, beat table, cast, and asset notes in `<slug>\STORY.md`.
2. Fill `<slug>\script.json` with `voice` (e.g. `Charon`), `tempo` (e.g. `1.18`), `language`, `initial_prompt` (proper nouns for Whisper), and `lines: [{id, text}]`.
   - Target ~150–190 words (~55–65 s).

### 3. Generate Voiceover & Word Timings
Requires `GEMINI_API_KEY` (env var or `.env`), `ffmpeg`, and `faster-whisper`.
```powershell
python <slug>\scripts\voice_gemini.py
```
To tweak tempo or re-align without calling TTS again:
```powershell
python <slug>\scripts\voice_gemini.py --skip-tts
```

### 4. Cast & Assets
- **New characters:** Add entries to `stickblend\specs.py`.
- **Verify cast turnarounds** (~10 s):
  ```powershell
  & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -P stickblend\lineup.py -- <slug>\out\lineup preview <char1>,<char2>
  ```
- **Download CC0 Poly Haven 3D models, PBR textures, and HDRIs:**
  ```powershell
  python stickblend\tools\polyhaven.py --res 1k <asset_id_1> <asset_id_2>
  ```
- **Download reusable audio library (one-time):**
  ```powershell
  python stickblend\tools\fetch_audio.py
  ```

### 5. Author Blender Shots (`<slug>\blender\shots.py`)
- Coordinates use **three.js axes** (`Y` up, camera looks down `-Z`); `tb()` converts to Blender (`Z` up).
- Every scene id in `timeline.json` must be registered in `segments(sid)` returning `[(build_fn, first_frame, last_frame), ...]`.
- Use `words(sid)` and `wAt(W, "keyword")` to lock poses, cuts, and camera moves to spoken words.
- Characters animate on 2s (`step=2`, 15 fps) by default while cameras animate on 1s (30 fps).

### 6. Preview Stills & Visual QA
```powershell
.\<slug>\blender\stills_all.ps1
```
Inspect `<slug>\out\bl\<sid>\still_####.png` before full rendering. Check framing, grounded shadows, prop placement (zero floating/clipping), and lighting.

### 7. Render Final Scene Clips & Audio
```powershell
.\<slug>\blender\render_all.ps1 -Slug <slug> -Spp 6 -Pct 75 -Jobs 2
```
Renders scenes in parallel, encodes `H.264 CRF 16` MP4s at 1080×1920, and syncs clips + audio into `remotion\public\shorts\<slug>\`.

### 8. Composite & Export in Remotion
1. Create `remotion\src\videos\<slug>\<Slug>Short.tsx` importing `StickblendShort` from `../../shared/StickblendShort` and the project's `timeline.json`.
2. Register the `<Composition>` in `remotion\src\Root.tsx`.
3. Typecheck and render:
   ```powershell
   cd remotion
   npm run typecheck
   npx remotion render src/index.ts <CompId> out/<slug>/final.mp4 --codec h264 --crf 16
   ```

## Blender 5.2 Rules & Gotchas
- **Never use World → Volume for haze** in Blender 5.2 EEVEE (renders black). Always use the volume box from `world.sky(haze=...)` or `sets2._haze(...)` with low density (`~0.004–0.006`).
- **Always call `world.optimize_shadows()`** before rendering (handled automatically by `run.py`).
- **Copy object lists before keyframing `hide_render`** (`for o in list(ch.coll.all_objects): ...`).
- **No Line Art on environments** — ink outlines belong only on 2.5D characters (`flat.flatten`), keeping worlds photorealistic.
- **Avoid raw multi-million-poly photogrammetry trees** (e.g. raw `jacaranda_tree` is 3.86M polys). Pre-decimate to ~50k polys into a reusable `.blend` or use instanced Quaternius trees (`world.place("NormalTree_1..5", ...)`).
- **Zero floating or clipping props:** Always place tabletop/furniture props with `ph.place_on(aid, target_obj, offset_xy=...)` instead of guessing heights, and verify stills before full renders.
- **No baked-in background photos in HDRIs:** Use `*_puresky` HDRIs (`belfast_sunset_puresky`, `kloofendal_48d_partly_cloudy_puresky`) and place real 3D buildings/skyline geometry behind the camera's sightline.
- **Asset path override:** Set `STICKBLEND_ASSETS3D` (or `ASSETS3D_DIR`) to point to a custom `assets3d/` folder; otherwise `stickblend/paths.py` uses `<repo_root>/assets3d`.
