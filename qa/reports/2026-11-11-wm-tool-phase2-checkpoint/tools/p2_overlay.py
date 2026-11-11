#!/usr/bin/env python3
"""
qa-agent 2026-11-11: plan-and-card wireframes (house plan 1.3.5 positions, card sizes, QA's projection) drawn on the r3 set-B scene, one
crop per product (overlays/plan-<slot>.jpg at 100% or x2), plus the measured / projected width ratio of the round products (the
projection of a real circle, so off-axis stretch is in the expected value). Writes data/geometry-ratios.json.
~/.venvs/motion/bin/python -I p2_overlay.py
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
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
S = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB")).copy()
FW = 3840 * 2720 / 4072


def px(X, Y, Z):
    u, v, _ = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * 2160 * 1530 / 2290


def circle(cx, cy, z, r, n=72):
    return [px(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, n)]


def alpha(k):
    return np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3]


def width_at_row(a, y):
    r = np.nonzero(a[int(round(y))] >= 128)[0]
    return (int(r.min()), int(r.max())) if r.size else None


img = S.copy()
col = (255, 0, 255)


def poly(pts, closed=True, c=col):
    cv2.polylines(img, [np.round(np.array(pts) * 4).astype(np.int32)], closed, c, 1, cv2.LINE_AA, shift=2)


def cyl(cx, cy, z0, z1, r0, r1_=None):
    r1_ = r0 if r1_ is None else r1_
    a_, b_ = circle(cx, cy, z0, r0), circle(cx, cy, z1, r1_)
    poly(a_)
    poly(b_)
    for i in (0, 18, 36, 54):
        poly([a_[i], b_[i]], False)
    return a_, b_


def box3(x0, x1, y0, y1, z0, z1):
    P = {(i, j, k): px((x0, x1)[i], (y0, y1)[j], (z0, z1)[k]) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    for a_ in P:
        for b_ in P:
            if sum(abs(a_[t] - b_[t]) for t in range(3)) == 1 and a_ < b_:
                poly([P[a_], P[b_]], False)


res = {}
# vase D16 x H32 base (-2.42, 1.35, 0.45)
lo, hi = cyl(-2.42, 1.35, 0.45, 0.77, 0.08)
a = alpha("vase")
mid_row = (max(p[1] for p in lo) + min(p[1] for p in hi)) / 2
exp_w = max(p[0] for p in lo) - min(p[0] for p in lo)
w = width_at_row(a, mid_row)
res["vase"] = dict(mid_row=round(mid_row, 1), measured_px=None if w is None else w[1] - w[0] + 1, expected_px_D16=round(exp_w, 1))
res["vase"]["ratio"] = round(res["vase"]["measured_px"] / exp_w, 3) if w else None
res["vase"]["layer_bottom_row"] = int(np.nonzero((a >= 128).any(1))[0].max())
res["vase"]["expected_bottom_row_front"] = round(max(p[1] for p in lo), 1)
res["vase"]["layer_top_body_row_est"] = None
# planter belly D42 (Z ~0.15) and opening D35.5 (Z 0.355), centre (-1.95, 0.42)
cyl(-1.95, 0.42, 0.0, 0.355, 0.21 * 0.85, 0.1775)
poly(circle(-1.95, 0.42, 0.16, 0.21))
# basket D35 H39 + handles 9
cyl(-1.62, 0.78, 0.0, 0.39, 0.175)
a = alpha("basket")
ring = circle(-1.62, 0.78, 0.20, 0.175)
yb = np.mean([p[1] for p in ring])
w = width_at_row(a, yb)
ew = max(p[0] for p in ring) - min(p[0] for p in ring)
res["basket"] = dict(row=round(yb, 1), measured_px=w[1] - w[0] + 1, expected_px_D35=round(ew, 1), ratio=round((w[1] - w[0] + 1) / ew, 3))
# magazine holder 35 x 19 x 27.5 at (-0.47, 2.57), long side along X
box3(-0.47 - 0.175, -0.47 + 0.175, 2.57 - 0.095, 2.57 + 0.095, 0.012, 0.287)
# floor lamp: base D26 x 2.5, stem, shade D37 bottom (Z 1.35) ~D20 top (Z 1.58)
cyl(1.52, 0.20, 0.0, 0.025, 0.13)
poly([px(1.52, 0.20, 0.025), px(1.52, 0.20, 1.35)], False)
lo, hi = cyl(1.52, 0.20, 1.35, 1.58, 0.185, 0.10)
a = alpha("floor-lamp")
yrow = max(p[1] for p in lo) - 4
w = width_at_row(a, yrow)
ew = max(p[0] for p in lo) - min(p[0] for p in lo)
rb = circle(1.52, 0.20, 0.0125, 0.13)
ybase = np.mean([p[1] for p in rb])
wb = width_at_row(a, ybase)
ewb = max(p[0] for p in rb) - min(p[0] for p in rb)
res["floor-lamp"] = dict(shade_row=round(yrow, 1), shade_measured_px=w[1] - w[0] + 1, shade_expected_px_D37=round(ew, 1),
                         shade_ratio=round((w[1] - w[0] + 1) / ew, 3), base_row=round(ybase, 1),
                         base_measured_px=None if wb is None else wb[1] - wb[0] + 1, base_expected_px_D26=round(ewb, 1),
                         base_ratio=None if wb is None else round((wb[1] - wb[0] + 1) / ewb, 3),
                         note="the base's left part is behind the throw in set B; the base ratio is read on set B's visible part if cut")
# pendant D50, bottom Z 1.90, height 28 (step 0), hang (0.20, 1.72)
lo, hi = cyl(0.20, 1.72, 1.90, 2.18, 0.15, 0.10)
poly(circle(0.20, 1.72, 2.05, 0.25))
poly([px(0.20, 1.72, 2.18), px(0.20, 1.72, 3.0)], False)
a = alpha("pendant")
wmax = int((a >= 128).sum(1).max())
ring = circle(0.20, 1.72, 2.05, 0.25)
ew = max(p[0] for p in ring) - min(p[0] for p in ring)
res["pendant"] = dict(widest_px=wmax, expected_px_D50=round(ew, 1), ratio=round(wmax / ew, 3))
# bowl D20 H8 at (0.72, 1.94, 0.38)
cyl(0.72, 1.94, 0.38, 0.46, 0.07, 0.10)
a = alpha("bowl")
ys = np.nonzero((a >= 128).any(1))[0]
wmax = int((a >= 128).sum(1).max())
ring = circle(0.72, 1.94, 0.46, 0.10)
ew = max(p[0] for p in ring) - min(p[0] for p in ring)
res["bowl"] = dict(widest_px=wmax, expected_px_D20=round(ew, 1), ratio=round(wmax / ew, 3))
# candle holders D7 x 11 + candles 7.5 / 6
for (X, Y, hc) in ((0.33, 1.74, 0.075), (0.48, 1.68, 0.06)):
    cyl(X, Y, 0.38, 0.49, 0.035)
    cyl(X, Y, 0.49, 0.49 + hc, 0.03)
# sconces: cylinder D6.5 x 16 standing off the wall on a block (Y 0.045 centre)
for X in (-0.85, 1.25):
    cyl(X, 0.06, 1.67, 1.83, 0.0325)
# framed art 3 x 50 x 70
for X in (-0.36, 0.20, 0.76):
    poly([px(X - 0.25, 0.0, 1.13), px(X + 0.25, 0.0, 1.13), px(X + 0.25, 0.0, 1.83), px(X - 0.25, 0.0, 1.83)])
# rug 330 x 230 centred (0.20, 1.92)
poly([px(-1.45, 0.77, 0), px(1.85, 0.77, 0), px(1.85, 3.07, 0), px(-1.45, 3.07, 0)])
# curtains stack X -2.29..-2.15, Y 2.65-2.95, Z 0-2.86
box3(-2.29, -2.15, 2.65, 2.95, 0.0, 2.86)

crops = {"vase": (580, 780, 780, 1120, 2), "planter-basket": (900, 720, 1220, 1260, 2), "magazine-holder": (880, 1330, 1260, 1530, 2),
         "floor-lamp": (2280, 540, 2600, 1380, 1), "pendant": (1480, 0, 1880, 420, 2), "table": (1680, 1100, 2120, 1380, 2),
         "sconces-art": (1380, 460, 2340, 830, 1), "rug": (0, 1100, 2720, 1530, 1), "curtains": (0, 0, 420, 1530, 1)}
for k, (x0, y0, x1, y1, s) in crops.items():
    c = Image.fromarray(img[y0:y1, x0:x1])
    if s != 1:
        c = c.resize((c.width * s, c.height * s), Image.LANCZOS)
    c.save(os.path.join(OUT, "overlays", f"plan-{k}.jpg"), quality=92)
json.dump(res, open(os.path.join(OUT, "data/geometry-ratios.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
