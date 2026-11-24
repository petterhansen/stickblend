"""Download reusable royalty-free storytelling music (Kevin MacLeod / Incompetech CC BY 4.0)
and CC0 SFX packs (OpenGameArt) into <repo_root>/assets_audio/.

Usage:
  python stickblend/tools/fetch_audio.py
"""
import pathlib
import re
import subprocess
import urllib.parse
import zipfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AUDIO_ROOT = REPO_ROOT / "assets_audio"
SFX_DIR = AUDIO_ROOT / "sfx"
MUSIC_DIR = AUDIO_ROOT / "music"
SFX_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

INCOMPETECH_TRACKS = [
    ("sneaky_snitch.mp3", "Sneaky Snitch.mp3"),
    ("scheming_weasel.mp3", "Scheming Weasel (faster version).mp3"),
    ("investigations.mp3", "Investigations.mp3"),
    ("jaunty_gumption.mp3", "Jaunty Gumption.mp3"),
    ("hidden_agenda.mp3", "Hidden Agenda.mp3"),
    ("marty_gots_a_plan.mp3", "Marty Gots a Plan.mp3"),
    ("fluffing_a_duck.mp3", "Fluffing a Duck.mp3"),
    ("mischief_maker.mp3", "Mischief Maker.mp3"),
    ("monkeys_spinning_monkeys.mp3", "Monkeys Spinning Monkeys.mp3"),
    ("run_amok.mp3", "Run Amok.mp3"),
    ("pixel_peeker_polka.mp3", "Pixel Peeker Polka - faster.mp3"),
    ("quirky_dog.mp3", "Quirky Dog.mp3"),
]

# Official CC0 SFX packs on OpenGameArt.org (public domain, no attribution required)
OGA_PAGES = [
    ("kenney_rpg_audio", "https://opengameart.org/content/50-rpg-sound-effects"),
    ("kenney_ui_audio", "https://opengameart.org/content/51-ui-sound-effects-buttons-switches-and-clicks"),
    ("kenney_casino_audio", "https://opengameart.org/content/54-casino-sound-effects-cards-dice-chips"),
    ("cc0_footsteps_impacts", "https://opengameart.org/content/100-cc0-sfx"),
]


def curl_fetch(url: str, dest: pathlib.Path) -> bool:
    r = subprocess.run(
        ["curl.exe", "-fsSL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "-o", str(dest), url],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 10000


def main() -> None:
    print("=== Downloading Kevin MacLeod (Incompetech CC BY 4.0) music ===")
    for local_name, remote_name in INCOMPETECH_TRACKS:
        dest = MUSIC_DIR / local_name
        if dest.exists() and dest.stat().st_size > 50000:
            print(f"  [skip] {local_name}")
            continue
        url = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + urllib.parse.quote(remote_name)
        if curl_fetch(url, dest):
            print(f"  [OK] {local_name} ({dest.stat().st_size // 1024} KB)")
        else:
            dest.unlink(missing_ok=True)
            print(f"  [FAIL] {local_name}")

    print("\n=== Downloading CC0 SFX packs (OpenGameArt) ===")
    for pack_name, page_url in OGA_PAGES:
        dest_dir = SFX_DIR / pack_name
        if dest_dir.exists() and (any(dest_dir.rglob("*.ogg")) or any(dest_dir.rglob("*.wav")) or any(dest_dir.rglob("*.mp3"))):
            print(f"  [skip] {pack_name}")
            continue
        r = subprocess.run(
            ["curl.exe", "-fsSL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", page_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        zips = re.findall(r'https://opengameart\.org/sites/default/files/[^"\']+\.zip', r.stdout)
        if not zips:
            print(f"  [FAIL] {pack_name}: no zip link found")
            continue
        tmp_zip = SFX_DIR / f"{pack_name}.zip"
        if curl_fetch(zips[0], tmp_zip):
            try:
                with zipfile.ZipFile(tmp_zip) as zf:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    zf.extractall(dest_dir)
                tmp_zip.unlink(missing_ok=True)
                n = len(list(dest_dir.rglob("*.ogg"))) + len(list(dest_dir.rglob("*.wav"))) + len(list(dest_dir.rglob("*.mp3")))
                print(f"  [OK] {pack_name} -> {n} sound files")
            except Exception as e:
                print(f"  [FAIL] {pack_name}: {e}")
        else:
            tmp_zip.unlink(missing_ok=True)
            print(f"  [FAIL] {pack_name}: download error")

    credits = """Audio Library Credits
=====================

SFX (sfx/*):
  Kenney & OpenGameArt CC0 Packs
  License: CC0 1.0 Universal (Public Domain, no attribution required)

Music (music/*.mp3):
  Kevin MacLeod (incompetech.com)
  Licensed under Creative Commons: By Attribution 4.0 License
  http://creativecommons.org/licenses/by/4.0/
"""
    (AUDIO_ROOT / "CREDITS.txt").write_text(credits, encoding="utf-8")
    print("\nLibrary ready at:", AUDIO_ROOT)


if __name__ == "__main__":
    main()
