# Stickblend Shorts — Viral Hook & Pacing Playbook

Use these templates when planning a new short in `STORY.md` and `script.json`.

---

## 1. Proven 0–3 Second Hook Formulas
Pick one formula and pair it with **immediate motion + an SFX hit on frame 1** (never start with "Hey guys", a logo, or "In the year…"):

1. **Result-First (*In Medias Res*)**
   - *Pattern:* `"This [tiny/absurd mistake] cost [person/city] [huge consequence]—and nobody noticed for [time]."`
   - *Visual:* Start at the climax (character doing `facepalm`, `shock`, or mid-fall) before cutting back to how it happened.
2. **Contradiction / Impossible Claim**
   - *Pattern:* `"[Famous thing] is missing [impossible detail]—and the reason is even weirder."`
   - *Visual:* Close-up on the object/prop with a bold 2–4 word label inside `x 70–860, y 290–1240`.
3. **Shock-to-Logic**
   - *Pattern:* `"Stop [common intuition]. It's actually doing [the exact opposite]."`
   - *Visual:* Stickman aggressively doing the counter-intuitive action (`kick`, `lean_back`).
4. **Bizarre Rule / Scenario ("What If")**
   - *Pattern:* `"In this [place/experiment], if you [simple action], [extreme consequence] happens."`
   - *Visual:* **1st-person POV** (`rig.pov_pose`) facing a `suspicious` or `smug` character.

---

## 2. Two Winning Runtime Cuts

### A. YouTube Shorts Loop Cut (30–42 s, ~95–125 words @ 1.08× tempo)
- **0–3 s (`hook`):** Mid-action frame + open loop question.
- **3–10 s (`setup`):** Wide 3D scene + characters entering (`walk_along`).
- **10–20 s (`escalate`):** **POV switch** (`rig.pov_pose`) or dynamic orbit; complication hits.
- **20–32 s (`twist`):** Reveal / proof + music drop + SFX hit.
- **32–38 s (`loop`):** Final punchline whose last clause flows directly back into `hook` (aim for >100% average view duration).

### B. TikTok Creator Rewards Cut (62–72 s, ~180–215 words @ 1.06× tempo)
- Same 5-beat spine, adding **2 micro-escalations** (`escalate_2`, `false_victory`) so a **pattern interrupt** (POV switch, location cut, prop reveal, or SFX hit) still lands every **2–4 seconds**.
- Must exceed **60 seconds** to qualify for TikTok Creator Rewards original-content monetization.

---

## 3. Pre-Export Technical Checks
- **Safe-Zone:** `python stickblend/tools/safezone_check.py <final.mp4> --step 2` (keep core visuals & text inside `x 70–860, y 290–1240` for cross-platform safety).
- **Loudness:** `ffmpeg -i <final.mp4> -af ebur128=peak=true -f null -` → target **−14 LUFS integrated** (`−16` to `−14`), **True Peak ≤ −1.0 dBTP**.
