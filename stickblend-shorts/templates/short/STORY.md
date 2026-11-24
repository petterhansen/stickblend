# Story Title (Stickblend 2.5D Short)

- **Target Platform & Cut:** `YouTube Shorts (30–45 s loop)` | `TikTok Creator Rewards (62–75 s)`
- **Hook Formula (0–3 s):** `Result-First` | `Shock-to-Logic` | `Bizarre Rule` | `Contradiction`
- **Hook Line (0–2.5 s):** "One punchy, verifiable sentence starting *in medias res* — no greeting, no slow setup."
- **Open Loop:** What mystery/question keeps the viewer watching until the final 5 seconds?
- **Loop Bridge:** How does the final line/frame flow seamlessly back into the opening hook?

## Script & Retention Beat Plan
> **Rule:** New visual angle, POV switch (`rig.pov_pose`), expression shift, or SFX accent every **2–4 s**. Keep core visuals & text inside the cross-platform safe zone (`x 70–860, y 290–1240`).

| id | Time | Beat Type | Text (Voiceover) | Visual (Blender 3D + 2.5D Stickmen + SFX) |
|---|---|---|---|---|
| `hook` | 0–3 s | Climax / Contradiction | First beat text (open loop). | *In medias res* mid-action or dramatic close-up; sharp SFX on frame 1. |
| `setup` | 3–10 s | Context | Fast 1–2 sentence setup. | Wide 3D establishing shot (`ph.hdri` + `ph.place`), character walks/gestures. |
| `escalate` | 10–22 s | Pattern Interrupt (POV) | Raising the stakes / complication. | Switch to **1st-person POV** (`rig.pov_pose`) or fast 3/4 orbit; `puzzled`/`worry` mood. |
| `twist` | 22–34 s | Micro-Payoff / Reveal | The unexpected turn or proof. | Props/labels pop in safe zone; music drop + impact SFX. |
| `loop` | 34–42 s | Payoff + Seamless Loop | Final punchline linking back to `hook`. | Callback pose/frame matching `hook` composition for >100% AVD rewatch loop. |

## Fact Check
- **Fact 1:** Source / date / verified detail.
- **Fact 2:** Source / date / verified detail.

## Cast (`stickblend/specs.py` + `character.py`)
- `hero`: Preset from `specs.SPECS` or custom spec (`hat`, `hair`, `torso.details`, `face`, `extras`).
- `foil`: Secondary character for dialogue / POV counter-reaction.

## World & Assets (`stickblend/ph.py`, `world.py`, `sets2.py`)
- Poly Haven models/textures/HDRIs (`python stickblend/tools/polyhaven.py <id>`).
- Optimized trees (`jacaranda_tree_opt.blend`) or Quaternius/Kenney kits via `world.place(...)`.
- Check final MP4 with `python stickblend/tools/safezone_check.py <final.mp4> --step 2` and `ffmpeg -i <final.mp4> -af ebur128=peak=true -f null -` (target `−14 LUFS`, `≤ −1.0 dBTP`).
