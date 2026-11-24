"""Poly-Haven-Assets (CC0) laden: python stickblend/tools/polyhaven.py <id> [<id> ...] [--res 2k]
Modelle -> glTF (+bin/Texturen), Texturen -> JPG-Maps (Diffuse/Normal GL/Roughness/AO), HDRIs -> .hdr.
Ablage: assets3d/polyhaven/<typ>/<id>/   (keine .blend-Dateien: kein eingebetteter Code)
"""
import importlib.util, json, os, pathlib, sys, urllib.request

_spec = importlib.util.spec_from_file_location("sb_paths", pathlib.Path(__file__).resolve().parents[1] / "paths.py")
_paths = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_paths)
ROOT = _paths.POLYHAVEN
UA = {"User-Agent": "stickblend-asset-fetch"}

def get(url): return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "wb").write(get(url))

def fetch(aid, res="2k"):
    info = json.loads(get(f"https://api.polyhaven.com/info/{aid}")); typ = {0: "hdris", 1: "textures", 2: "models"}[info["type"]]
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}")); out = os.path.join(ROOT, typ, aid)
    if typ == "hdris":
        f = files["hdri"][res]["hdr"]; save(f["url"], os.path.join(out, os.path.basename(f["url"])))
    elif typ == "textures":
        for key in ("Diffuse", "nor_gl", "Rough", "AO", "Displacement"):
            if key in files and res in files[key]:
                f = files[key][res].get("jpg") or files[key][res].get("png"); save(f["url"], os.path.join(out, os.path.basename(f["url"])))
    else:
        g = files["gltf"][res]["gltf"]; save(g["url"], os.path.join(out, os.path.basename(g["url"])))
        for rel, inc in g.get("include", {}).items(): save(inc["url"], os.path.join(out, rel))
    print("OK", typ, aid)

if __name__ == "__main__":
    args = sys.argv[1:]; res = "2k"
    if "--res" in args: i = args.index("--res"); res = args[i + 1]; del args[i:i + 2]
    for a in args:
        try: fetch(a, res)
        except Exception as e: print("FAIL", a, e)
