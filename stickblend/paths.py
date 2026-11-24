"""Configurable asset path resolution for stickblend.

Resolution order for 3D asset kits (Poly Haven, Quaternius, Kenney):
  1. STICKBLEND_ASSETS3D or ASSETS3D_DIR environment variable
  2. <repo_root>/assets3d
"""
import os
import pathlib

PKG_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent


def _resolve_assets3d() -> pathlib.Path:
    for env_key in ("STICKBLEND_ASSETS3D", "ASSETS3D_DIR"):
        val = os.environ.get(env_key)
        if val:
            return pathlib.Path(val)
    return REPO_ROOT / "assets3d"


ASSETS3D = _resolve_assets3d()
POLYHAVEN = str(ASSETS3D / "polyhaven")
QUAT = str(ASSETS3D / "quaternius_usn" / "Ultimate Stylized Nature - May 2022" / "AllModels.blend")
KENNEY_NATURE = str(ASSETS3D / "kenney_nature" / "Models" / "GLTF format")
KENNEY_PIRATE = str(ASSETS3D / "kenney_pirate" / "Models" / "GLB format")
