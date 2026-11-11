#!/usr/bin/env python3
"""
qa-agent 2026-11-11: is the light on the R3 products (planter, basket, pendant) the room's light?
  1. Shadow direction on the floor: every shadow pixel of a floor product (its *-shadow.png, weight 1 - min channel / 255) is unprojected
     to the floor (Z 0, QA's projection, inverse); pixels that land behind a wall (Y < 0.02 or X < -2.29) are wall shadow and dropped.
     The weighted centroid minus the product's plan point = the shadow's direction in plan (degrees: 0 = +X, away from the window;
     90 = +Y, toward the camera). Same for the approved phase-1 fixed-furniture shadow around the coffee table and the armchair, the
     room's reference, and for the other floor products.
  2. The window-side gradient: L* of the left quarter vs the right quarter of each R3 product's opaque body (the window is on the
     left), against the same measure on neighbours from earlier passes (vase, floor-lamp pole, candle holders) and on the fixed
     furniture (the armchair cushion, the coffee-table drums), on the r3 set-B scene.
  3. Grain and sharpness: high-pass std (sigma 1.5) and the 10-90 % edge width of the alpha on the R3 products against the neighbours.
Writes data/light.json.   ~/.venvs/motion/bin/python -I p2_light.py
"""
import importlib.util
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CAM = r1.CAM["M0"]
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
FW = 3840 * 2720 / 4072
FH = 2160 * 1530 / 2290
a_ = math.radians(CAM["yaw_deg_left"])
fwd = np.array([-math.sin(a_), -math.cos(a_), 0.0])
right = np.array([math.cos(a_), -math.sin(a_), 0.0])
fx = CAM.get("lens", 24) / 36.0
fy = fx * 16 / 9
C = np.array(CAM["loc"], float)


def unproject_floor(xp, yp):
    u = (xp - 77.49) / FW
    v = (yp - 43.43) / FH
    with np.errstate(divide="ignore", invalid="ignore"):
        d = fy * C[2] / (v - CAM["v0"])
    xr = (u - CAM["u0"]) * d / fx
    P = C[None, :2] + d[:, None] * fwd[None, :2] + xr[:, None] * right[None, :2]
    return P, d


def shadow_dir(sh, centre, radius=1.2, keep=None):
    w = 1 - sh.min(2).astype(np.float64) / 255
    if keep is not None:
        w = w * keep
    ys, xs = np.nonzero(w > 0.01)
    P, d = unproject_floor(xs.astype(float), ys.astype(float))
    ok = (d > 0) & (P[:, 1] > 0.02) & (P[:, 0] > -2.29) & (np.hypot(P[:, 0] - centre[0], P[:, 1] - centre[1]) < radius)
    if ok.sum() < 20:
        return dict(px=int(ok.sum()))
    ww = w[ys[ok], xs[ok]]
    c = (P[ok] * ww[:, None]).sum(0) / ww.sum()
    dv = c - np.array(centre)
    return dict(px=int(ok.sum()), centroid=[round(float(c[0]), 3), round(float(c[1]), 3)], offset_m=[round(float(dv[0]), 3), round(float(dv[1]), 3)],
                angle_deg=round(math.degrees(math.atan2(dv[1], dv[0])), 1), length_m=round(float(np.hypot(*dv)), 3))


res = {"shadow_direction": {}}
for k, c in (("planter", (-1.95, 0.42)), ("basket", (-1.62, 0.78)), ("floor-lamp", (1.52, 0.20)), ("magazine-holder", (-0.47, 2.57))):
    sh = np.asarray(Image.open(os.path.join(P2, "layers", byid[k + "-shadow"]["file"])).convert("RGB"))
    res["shadow_direction"][k] = shadow_dir(sh, c)
fsh = np.asarray(Image.open(os.path.join(P1, "fixed-furniture-shadow.png")).convert("RGB"))
res["shadow_direction"]["coffee-table (phase 1, approved)"] = shadow_dir(fsh, (0.20, 1.92), radius=1.0)
res["shadow_direction"]["armchair (phase 1, approved; centre est. from its floor shadow)"] = shadow_dir(fsh, (-1.55, 3.45), radius=0.8)
res["shadow_direction_note"] = ("angles in plan: 0 = +X (away from the window wall), 90 = +Y (toward the camera), -90 = toward the back wall; "
                                "the window is the left wall X -2.30, Y 0.75-2.85; the armchair's centre is an estimate")

S = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
L = cv2.cvtColor(S.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
hp = L - cv2.GaussianBlur(L, (0, 0), 1.5)


def body(k, rows=None, cols=None):
    a = np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3]
    m = cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if rows:
        mm = np.zeros_like(m)
        mm[rows[0]:rows[1]] = True
        m &= mm
    if cols:
        mm = np.zeros_like(m)
        mm[:, cols[0]:cols[1]] = True
        m &= mm
    return m, a


def lr(m):
    xs = np.nonzero(m.any(0))[0]
    x0, x1 = xs.min(), xs.max()
    q = (x1 - x0) / 4
    cols = np.arange(m.shape[1])[None, :]
    lm, rm = m & (cols < x0 + q), m & (cols > x1 - q)
    return round(float(np.median(L[lm]) - np.median(L[rm])), 1)


def edge_width(a):
    af = a.astype(np.float32) / 255
    soft = (af > 0.1) & (af < 0.9)
    edge = (cv2.dilate((a == 255).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & (a < 255)
    return round(float(soft.sum() / max(1, edge.sum())), 2)


g = {}
for k, rows, cols in (("planter", (1050, 1180), (940, 1000)), ("basket", (1070, 1225), None), ("pendant", (180, 375), None),
                      ("vase", (930, 1075), None), ("candle-holders", None, None), ("bowl", None, None), ("floor-lamp", (585, 700), None),
                      ("magazine-holder", None, None)):
    m, a = body(k, rows, cols)
    g[k] = dict(left_minus_right_quarter_L=lr(m), body_L_median=round(float(np.median(L[m])), 1), highpass_std=round(float(hp[m].std()), 2),
                soft_to_edge_ratio=edge_width(a))
fa = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3]
for name, box in (("armchair seat cushion (approved)", (300, 1180, 700, 1330)), ("coffee-table left drum (approved)", (1330, 1330, 1470, 1480)),
                  ("sofa left arm front (approved)", (1370, 1100, 1450, 1300))):
    m = np.zeros(fa.shape, bool)
    m[box[1]:box[3], box[0]:box[2]] = True
    m &= fa == 255
    g[name] = dict(left_minus_right_quarter_L=lr(m) if m.any() else None, body_L_median=round(float(np.median(L[m])), 1) if m.any() else None,
                   highpass_std=round(float(hp[m].std()), 2) if m.any() else None)
bg = np.zeros(L.shape, bool)
bg[700:1000, 1150:1300] = True
g["back wall near the corner (base)"] = dict(highpass_std=round(float(hp[bg].std()), 2), L_median=round(float(np.median(L[bg])), 1))
res["window_gradient_and_grain"] = g
json.dump(res, open(os.path.join(OUT, "data/light.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
