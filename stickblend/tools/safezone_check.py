"""Safe-Zone-Pruefung: legt die Maske ueber Einzelbilder eines fertigen Shorts.
  python stickblend/tools/safezone_check.py <video.mp4> [--step 2] [--out sheet.png]
Rot = dort darf kein Text/wichtiges Detail liegen (Plattform-UI). Gruen = Untertitel-Box.
Zusaetzlich: automatische Warnung, wenn helle Untertitel-Pixel (reines Weiss mit schwarzer Kontur) im roten Bereich liegen."""
import sys, subprocess, json, pathlib, tempfile
import numpy as np
from PIL import Image, ImageDraw
A = pathlib.Path(__file__).resolve().parents[1] / "assets"
args = sys.argv[1:]; vid = args[0]
step = float(args[args.index("--step") + 1]) if "--step" in args else 2.0
out = args[args.index("--out") + 1] if "--out" in args else str(pathlib.Path(vid).with_name("safezone_sheet.png"))
SZ = json.load(open(A / "safezone.json")); mask = Image.open(A / "safezone_tiktok.png")
red = np.array(mask)[:, :, 3] > 0
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vid]))
tmp = pathlib.Path(tempfile.mkdtemp()); frames = []; bad = []
t = 0.5
while t < dur:
    p = tmp / f"{t:07.2f}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", vid, "-frames:v", "1", "-vf", "scale=1080:1920", str(p)], check=True)
    im = Image.open(p).convert("RGB"); a = np.array(im).astype(int)
    white = (a.min(axis=2) > 245)   # Untertitel-Weiss
    hits = int((white & red).sum())
    if hits > 400: bad.append((round(t, 1), hits))
    frames.append((t, Image.alpha_composite(im.convert("RGBA"), mask).convert("RGB")))
    t += step
W, H = 216, 384; cols = 8; rows = (len(frames) + cols - 1) // cols
sh = Image.new("RGB", (W * cols, H * rows))
for i, (t, im) in enumerate(frames):
    sh.paste(im.resize((W, H)), ((i % cols) * W, (i // cols) * H)); ImageDraw.Draw(sh).text(((i % cols) * W + 4, (i // cols) * H + 4), f"{t:.1f}s", fill="yellow")
sh.save(out)
print("Sheet:", out)
print("WARNUNG Text im Sperrbereich bei:", bad) if bad else print("OK: kein Untertitel-Weiss im Sperrbereich")
