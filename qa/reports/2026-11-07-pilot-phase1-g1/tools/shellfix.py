"""
qa-agent 2026-11-07: the pilot's shell fixes (shell-fix.json) measured by QA. Usage: ~/.venvs/motion/bin/python -I shellfix.py <version>
(1) the wedge: moved to wedge_area.py (see the note in the code).
(2) L* at the plan's grading points (QA's projection, 7 x 7 px median) on the ungraded and the graded shell.
(3) the bench slab: a*, b* of the lit slab and the share of pore pixels (> 3.5 L* under the 7 px local median) inside the slab.
Writes data/shellfix-<version>.json.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
V = sys.argv[1] if len(sys.argv) > 1 else "v2"
FIXED, GRADED = f"shell-{V}.png", f"shell-{V}-graded.png"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def L_of(name):
    return lab(np.asarray(Image.open(os.path.join(P, name)).convert("RGB")).astype(float))


before, after = L_of("shell.png"), L_of(FIXED)
W, H = 2720, 1530
# (1) the wedge: see wedge_area.py (the designer's area condition). A first per-row measure here locked onto the corner's falloff at the
# box's left edge, not the wedge, and was dropped (QA, 2026-11-07).


def point(Lmap, X, Y, Z):
    u, v, _ = r1.project(r1.CAM["M0"], X, Y, Z)
    cu, cv_ = (116 + u * 3840) / 4072, (65 + v * 2160) / 2290
    x, y = int(cu * W), int(cv_ * H)
    return round(float(np.median(Lmap[y - 3:y + 4, x - 3:x + 4, 0])), 1)


PTS = {"back_wall_by_corner(-1.75,0,1.60)": (-1.75, 0, 1.60), "window_wall(-2.30,0.30,1.60)": (-2.30, 0.30, 1.60), "window_wall(-2.30,0.45,1.60)": (-2.30, 0.45, 1.60),
       "window_wall(-2.30,0.55,1.60)": (-2.30, 0.55, 1.60), "window_wall(-2.30,0.65,1.60)": (-2.30, 0.65, 1.60),
       "back_wall_centre(0.20,0,1.95)": (0.20, 0, 1.95), "back_wall_right(1.85,0,1.60)": (1.85, 0, 1.60)}
graded = L_of(GRADED)
points = {n: dict(ungraded=point(after, *p), graded=point(graded, *p)) for n, p in PTS.items()}
# the bench slab: its top between the bench's front edge and the wall, Y 1.1-2.7, lit (QA's projection of the slab polygon)
poly = []
for X, Y in ((-2.28, 1.1), (-2.28, 2.7), (-2.00, 2.7), (-2.00, 1.1)):
    u, v, _ = r1.project(r1.CAM["M0"], X, Y, 0.45)
    poly.append((int((116 + u * 3840) / 4072 * W), int((65 + v * 2160) / 2290 * H)))
m = np.zeros((H, W), np.uint8)
cv2.fillPoly(m, [np.array(poly, np.int32)], 1)
m = cv2.erode(m, np.ones((5, 5), np.uint8)) > 0
slab = {}
for name, Lm in (("step-2 shell", before), (FIXED, after), (GRADED, graded)):
    Lc = Lm[..., 0].astype(np.float32)
    pores = (cv2.medianBlur(np.clip(Lc * 2.55, 0, 255).astype(np.uint8), 7).astype(float) / 2.55 - Lc) > 3.5
    slab[name] = dict(L=round(float(np.median(Lm[m][:, 0])), 1), a=round(float(np.median(Lm[m][:, 1])), 2), b=round(float(np.median(Lm[m][:, 2])), 2),
                      pores_pct=round(float(pores[m].mean() * 100), 2))
slab["target #D8C8AE"] = [round(float(v), 2) for v in lab(np.array([[0xD8, 0xC8, 0xAE]], float))[0]]
slab["polygon_px"] = poly
out = dict(version=V, grading_points=points, bench_slab=slab)
json.dump(out, open(os.path.join(OUT, "data", f"shellfix-{V}.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
