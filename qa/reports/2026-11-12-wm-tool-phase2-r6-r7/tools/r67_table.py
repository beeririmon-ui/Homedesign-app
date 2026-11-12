#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R7): the table group (WM-T2, slots 1.9.4), QA's own clay check and the real layers.
Projection: QA's clay_wm_r1.project (house-plan camera M0 1.2), the canvas of the checkpoint's p2_geometry.py; table top Z 0.38.
  1. Placement: each piece's connected component (alpha >= 128, pieces merged by a 3 px dilation) against the projected card cylinder
     at its 1.9.4 point (travertine D7 x H11 + candle D6 x 7.5 / 6; ceramic tray D13.3 (17 with the handles) x H7.2 + candle D6 x 7.5 / 6;
     bowls D20 x H8 / D21.2 x H6.4): centre-x offset in cm, the foot (bottom) offset in px, the width in cm.
  2. QA's clay: the card cylinders as filled projected silhouettes (convex hull of the projected rims) at the 1.9.4 points, every bowl
     (D20 x 8, D21.2 x 6.4, D21.3 x 5.2) x every holder pair (travertine 0.205 / 0.355 as the slots say, and 0.195 as the lever moved it;
     ceramic 0.055 / 0.305; iron D10.5 + candles D7 x 15 / 18 at 0.15 / 0.34), against the REAL cushion sets A / B / C (their layer alpha
     >= 128), A vs B, B vs bowl. Gap = the nearest distance between the silhouettes / the frame width (2565.0 canvas px). F3 >= 0.02.
  3. The real layers: the same gaps on the rendered silhouettes (alpha >= 128) of the moved defaults and the 6' variants.
  4. The sofa: every holder piece inside the sofa's silhouette (fixed furniture), its contour distance.
Writes data/table.json.
"""
import importlib.util
import itertools
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
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
m7 = json.load(open(os.path.join(P2, "layers/manifest-r7.json")))
b7 = {l_["id"]: l_ for l_ in m7["layers"]}
V = {v["id"]: v for vs in m7["variants"].values() for v in vs}
FW = 3840 * 2720 / 4072
H, W = 1530, 2720
TOP = 0.38


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * 2160 * 1530 / 2290, d


def cm_per_px(d):
    return 100 * d / ((CAM.get("lens", 24) / 36) * FW)


def cyl_pts(cx, cy, z0, z1, r, n=72):
    return [px(cx + r * math.cos(t), cy + r * math.sin(t), z)[:2] for t in np.linspace(0, 2 * math.pi, n, endpoint=False) for z in (z0, z1)]


def sil(parts):
    """filled silhouette of the union of convex parts (each a list of cylinders), rasterised at 4x"""
    big = np.zeros((H * 4, W * 4), np.uint8)
    for part in parts:
        P = np.array(part, np.float32) * 4
        hull = cv2.convexHull(P).astype(np.int32)
        cv2.fillConvexPoly(big, hull, 255)
    return cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA) >= 128


def gap(a, b):
    if (a & b).any():
        return 0.0
    d = cv2.distanceTransform((~a).astype(np.uint8), cv2.DIST_L2, 5)
    return round(float(d[b].min()) / FW, 4)


def alpha(f, thr=128):
    return np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3] >= thr


sets = {s: alpha(m7["slot_cushions"]["sets"][s]["layer"]) for s in "ABC"}
ff = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3] >= 128

# the clay bodies
HOLD = {
    "travertine (slots 0.205)": [((0.205, 1.74), 0.035, 0.11, 0.03, 0.075), ((0.355, 1.68), 0.035, 0.11, 0.03, 0.06)],
    "travertine (lever 0.195)": [((0.195, 1.74), 0.035, 0.11, 0.03, 0.075), ((0.355, 1.68), 0.035, 0.11, 0.03, 0.06)],
    "ceramic trays": [((0.055, 1.74), 0.085, 0.072, 0.03, 0.075), ((0.305, 1.68), 0.085, 0.072, 0.03, 0.06)],
    "iron plates (15 / 18)": [((0.15, 1.74), 0.0525, 0.02, 0.035, 0.15), ((0.34, 1.68), 0.0525, 0.02, 0.035, 0.18)],
    "iron plates (15 / 16 lever)": [((0.15, 1.74), 0.0525, 0.02, 0.035, 0.15), ((0.34, 1.68), 0.0525, 0.02, 0.035, 0.16)],
}
BOWLS = {"black D20 x 8": (0.10, 0.08), "white belly D21.2 x 6.4": (0.106, 0.064), "speckled D21.3 x 5.2": (0.1065, 0.052)}


def holder_parts(spec_):
    (x, y), r, h, rc, hc = spec_
    return [cyl_pts(x, y, TOP, TOP + h, r), cyl_pts(x, y, TOP + h - 0.01, TOP + h + hc, rc)]


res = dict(frame_width_px=round(FW, 2), table_top_z=TOP)
clay = {}
for hn, pair in HOLD.items():
    A = sil(holder_parts(pair[0]))
    B = sil(holder_parts(pair[1]))
    rec = {"A x B": gap(A, B)}
    for s in "ABC":
        rec[f"holders x cushions {s}"] = min(gap(A, sets[s]), gap(B, sets[s]))
    rec["holders inside the sofa silhouette"] = bool((ff[A | B]).mean() > 0.95)
    for bn, (r, h) in BOWLS.items():
        bowl = sil([cyl_pts(0.62, 1.94, TOP, TOP + h, r)])
        rec[f"B x bowl {bn}"] = gap(B, bowl)
    clay[hn] = rec
for bn, (r, h) in BOWLS.items():
    bowl = sil([cyl_pts(0.62, 1.94, TOP, TOP + h, r)])
    clay[f"bowl {bn}"] = {f"x cushions {s}": gap(bowl, sets[s]) for s in "ABC"}
    bowl64 = sil([cyl_pts(0.64, 1.94, TOP, TOP + h, r)])
    clay[f"bowl {bn} at X 0.64 (the lever)"] = {f"x cushions {s}": gap(bowl64, sets[s]) for s in "ABC"}
res["clay"] = clay
print(json.dumps(clay, indent=1))


# the real layers
def pieces(m, k=2):
    mm = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(mm, 8)
    idx = sorted(range(1, n), key=lambda i: -st[i, 4])[:k]
    idx = sorted(idx, key=lambda i: st[i, 0])
    return [(lab == i) & m for i in idx]


real = {}
H_DEF = alpha(b7["candle-holders"]["file"])
H_V2 = alpha(V["candle-holders-v2"]["file"])
B_DEF = alpha(b7["bowl"]["file"])
B_V2 = alpha(V["bowl-v2"]["file"])
for hn, hm in (("travertine (default)", H_DEF), ("ceramic trays (v2)", H_V2)):
    A, B = pieces(hm)
    rec = {"A x B": gap(A, B)}
    for s in "ABC":
        rec[f"holders x cushions {s}"] = min(gap(A, sets[s]), gap(B, sets[s]))
    rec["B x black bowl (default)"] = gap(B, B_DEF)
    rec["B x white bowl (v2)"] = gap(B, B_V2)
    # inside the sofa's silhouette? (share of the holders' pixels over fixed furniture) and the contour distance to the sofa's outline
    rec["share_over_fixed_furniture"] = round(float(ff[A | B].mean()), 3)
    real[hn] = rec
for bn, bm in (("black bowl (default)", B_DEF), ("white bowl (v2)", B_V2)):
    real[bn] = {f"x cushions {s}": gap(bm, sets[s]) for s in "ABC"}
res["real_layers"] = real
print(json.dumps(real, indent=1))

# placement against the card cylinders at the 1.9.4 points
pl = {}
for name, m, specs in (("travertine (default)", H_DEF, HOLD["travertine (lever 0.195)"]), ("ceramic trays (v2)", H_V2, HOLD["ceramic trays"])):
    out = []
    for p, (sp) in zip(pieces(m), specs):
        (x, y), r, h, rc, hc = sp
        P = np.array(cyl_pts(x, y, TOP, TOP + h, r) + cyl_pts(x, y, TOP + h, TOP + h + hc, rc))
        eb = [P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()]
        foot = np.array(cyl_pts(x, y, TOP, TOP, r))
        ys, xs = np.nonzero(p)
        d = px(x, y, TOP)[2]
        lb = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        out.append(dict(point=[x, y], expected_box=[round(float(v), 1) for v in eb], layer_box=lb,
                        centre_x_offset_cm=round(((lb[0] + lb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(d), 1),
                        foot_bottom_offset_px=round(lb[3] - float(foot[:, 1].max()), 1), top_offset_px=round(lb[1] - eb[1], 1),
                        width_cm_layer=round((lb[2] - lb[0] + 1) * cm_per_px(d), 1), width_cm_expected=round((eb[2] - eb[0]) * cm_per_px(d), 1),
                        height_cm_layer_incl_candle=round((lb[3] - lb[1] + 1) * cm_per_px(d), 1)))
    pl[name] = out
for name, m, (r, h) in (("black bowl (default)", B_DEF, BOWLS["black D20 x 8"]), ("white bowl (v2)", B_V2, BOWLS["white belly D21.2 x 6.4"])):
    P = np.array(cyl_pts(0.62, 1.94, TOP, TOP + h, r))
    eb = [P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()]
    ys, xs = np.nonzero(m)
    lb = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    d = px(0.62, 1.94, TOP)[2]
    # the widest row (the rim): its width in cm
    w = m.sum(1)
    pl[name] = dict(point=[0.62, 1.94], expected_box=[round(float(v), 1) for v in eb], layer_box=lb,
                    centre_x_offset_cm=round(((lb[0] + lb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(d), 1),
                    bottom_offset_px=round(lb[3] - eb[3], 1), rim_width_cm=round(float(w.max()) * cm_per_px(d), 1), card_cm=round(2 * r * 100, 1),
                    height_px_layer=lb[3] - lb[1] + 1, height_px_expected=round(eb[3] - eb[1], 1))
res["placement"] = pl
print(json.dumps(pl, indent=1))
json.dump(res, open(os.path.join(OUT, "data/table.json"), "w"), indent=1)
