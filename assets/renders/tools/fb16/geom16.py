import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, numpy as np
from PIL import Image

def camera(cfg, canvas=(2720, 1530)):
    j = json.load(open(cfg["lock"]))
    cam = j.get("camera") or {}
    if isinstance(cam, list) or "loc" not in cam:
        cam = next((c for c in (j.get("cameras") or []) if isinstance(c, dict)), cam)
    fb = j.get("frame_box") or [77.49, 43.43, 2642.51, 1486.57]
    fbw, fbh = fb[2] - fb[0], fb[3] - fb[1]
    f = fbw / 36.0 * float(cam.get("lens", 24))
    u0, v0 = float(cam.get("u0", 0.5)), float(cam.get("v0", 0.5))
    return dict(f=f, cx=fb[0] + u0 * fbw, cy_top=fb[1] + v0 * fbh, cy_bot=fb[3] - v0 * fbh, z=float(cam["loc"][2]), fb=fb, cam=cam)

def depth(cfg):
    return np.asarray(Image.open(cfg["clay"] + "-depth.png")).astype(np.float64) / 5000.0

def backproject(Z, f, cx, cy, step=1):
    H, W = Z.shape
    v, u = np.mgrid[0:H:step, 0:W:step].astype(np.float64)
    Zs = Z[::step, ::step]
    X = (u + 0.5 - cx) / f * Zs
    Y = -(v + 0.5 - cy) / f * Zs
    return np.stack([X, Y, Zs], -1)
