#!/usr/bin/env python3
"""
qa-agent 2026-11-11: geometry of three R4 fixes, QA's own reading.
  vase     the size after the scale, measured on the r4 layer alpha and turned into cm with QA's projection (house-plan camera M0,
           qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py project(), the same canvas mapping as the checkpoint's
           p2_geometry.py): the foot's contact row and centre; the stand point = where that contact meets the bench top (Z 0.45) on the
           camera ray, the vase's axis 5 cm (the foot's radius) further along the ray; the mouth = the neck's narrowest alpha row (the
           dry stems are thinner than the neck's run only above the mouth), + the collar; the width = the widest 5-row mean of the alpha
           sum between mouth and foot. The card's 16 x 32 cylinder projected at that axis is the ruler. Before (r3) and after (r4).
           Also: the anchor (foot row and centre x, r3 vs r4) and the contact shadow (its darkest row, its extent).
  pendant  the alpha above row 62: connected pieces (alpha > 0.5, 8-connected), r3 vs r4, and whether canopy, cord and shade are one piece.
  planter  the crescent left of the mouth (rows 1030-1056, left of the pot's edge line fitted on rows 1056-1075 of the r4 alpha):
           alpha mass r3 vs r4.
Writes data/geometry.json.   ~/.venvs/motion/bin/python -I r4_geometry.py
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
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
FW = 3840 * 2720 / 4072
FHs = 2160 * 1530 / 2290
m = {t: json.load(open(os.path.join(P2, f"layers/manifest-{t}.json"))) for t in ("r3", "r4")}
by = {t: {l_["id"]: l_ for l_ in m[t]["layers"]} for t in m}


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * FHs, d


def alpha(t, k):
    return np.asarray(Image.open(os.path.join(P2, "layers", by[t][k]["file"])))[..., 3].astype(np.float32) / 255


def on_bench(xp, yp, Z=0.45):
    """the point on the plane Z whose projection is (xp, yp): a 2-D Newton solve from the plan point"""
    X, Y = -2.42, 1.35
    for _ in range(40):
        x0, y0, _ = px(X, Y, Z)
        e = np.array([xp - x0, yp - y0])
        if np.hypot(*e) < 1e-4:
            break
        h = 1e-4
        J = np.array([[(px(X + h, Y, Z)[0] - x0) / h, (px(X, Y + h, Z)[0] - x0) / h],
                      [(px(X + h, Y, Z)[1] - y0) / h, (px(X, Y + h, Z)[1] - y0) / h]])
        dX, dY = np.linalg.solve(J, e)
        X, Y = X + dX, Y + dY
    return X, Y


def cylinder(cx, cy, D=0.16, Hh=0.32, mouth=0.09, z0=0.45, n=120):
    zs = np.linspace(z0, z0 + Hh, 9)
    pts = [px(cx + D / 2 * math.cos(t), cy + D / 2 * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, n) for z in zs[1:-1]]
    xs = [p[0] for p in pts]
    top = min(px(cx + mouth / 2 * math.cos(t), cy + mouth / 2 * math.sin(t), z0 + Hh)[1] for t in np.linspace(0, 2 * math.pi, n))
    bot = max(px(cx + 0.05 * math.cos(t), cy + 0.05 * math.sin(t), z0)[1] for t in np.linspace(0, 2 * math.pi, n))
    return dict(width_px=max(xs) - min(xs), height_px=bot - top, top=top, bottom=bot, depth=px(cx, cy, z0 + Hh / 2)[2])


res = {}
vase = {}
for t in ("r3", "r4"):
    a = alpha(t, "vase")
    M = a > 0.5
    ys = np.nonzero(M.any(1))[0]
    yb = int(ys.max())
    cols = np.nonzero(M[yb - 3:yb + 1].any(0))[0]
    xc = (cols.min() + cols.max() + 1) / 2.0
    col = a[:, int(round(xc))]
    yb_sub = yb + (float(col[yb]) - 0.5) / max(float(col[yb]) - float(col[yb + 1]), 1e-3)
    wsum = a.sum(1)
    # the neck: the narrowest run through the foot's column in the upper half of the body (the stems above are separate thin pieces)
    runw = []
    for y in range(int(ys.min()), yb):
        r = M[y]
        ix = int(round(xc))
        if not r[ix]:
            runw.append((y, 0))
            continue
        x0 = ix
        while x0 > 0 and r[x0 - 1]:
            x0 -= 1
        x1 = ix
        while x1 < r.size - 1 and r[x1 + 1]:
            x1 += 1
        runw.append((y, x1 - x0 + 1))
    span = yb - int(ys.min())
    cand = [(w, y) for y, w in runw if int(ys.min()) + 0.15 * span < y < int(ys.min()) + 0.55 * span and w > 0]
    neck_w, neck_y = min(cand)
    # the mouth's top: the first row above the neck where the run widens again by > 25 % (the collar's lip), else the neck row
    mouth_y = neck_y
    for y, w in reversed(runw):
        if y < neck_y and w > 1.25 * neck_w:
            break
        if y < neck_y:
            mouth_y = y
    rows = np.arange(mouth_y + 8, yb - 8)
    w5 = np.convolve(wsum[rows], np.ones(5) / 5, mode="same")
    i = int(np.argmax(w5[2:-2])) + 2
    X, Y = on_bench(xc, yb_sub)
    C = CAM["loc"]
    dx, dy = X - C[0], Y - C[1]
    nr = math.hypot(dx, dy)
    cx, cy = X + 0.05 * dx / nr, Y + 0.05 * dy / nr
    card = cylinder(cx, cy)
    h_px = yb_sub - (mouth_y - 0.5)
    vase[t] = dict(foot_contact_y=round(yb_sub, 2), foot_centre_x=round(float(xc), 2), neck_row=neck_y, neck_width_px=neck_w,
                   mouth_row=mouth_y, height_px=round(h_px, 2), widest_row=int(rows[i]), width_px=round(float(w5[i]), 2),
                   stand_point_xy=[round(X, 3), round(Y, 3)], axis_xy=[round(cx, 3), round(cy, 3)],
                   card_at_axis_px=dict(width=round(card["width_px"], 2), height=round(card["height_px"], 2), depth_m=round(card["depth"], 3)),
                   height_cm=round(32 * h_px / card["height_px"], 1), width_cm=round(16 * w5[i] / card["width_px"], 1),
                   h_to_w=round(h_px / w5[i], 3), card_h_to_w_px=round(card["height_px"] / card["width_px"], 3),
                   offset_from_plan_point_m=round(math.hypot(cx + 2.42, cy - 1.35), 3))
    sh = np.asarray(Image.open(os.path.join(P2, "layers", by[t]["vase-shadow"]["file"])))[..., :3].min(2).astype(np.float32) / 255
    dk = sh < 0.99
    if dk.any():
        sy, sx = np.nonzero(dk)
        vase[t]["shadow"] = dict(px_below_0_99=int(dk.sum()), box=[int(sx.min()), int(sy.min()), int(sx.max()) + 1, int(sy.max()) + 1],
                                 min=round(float(sh.min()), 3), darkest_at=[int(v) for v in np.unravel_index(int(sh.argmin()), sh.shape)[::-1]],
                                 centroid_x_minus_foot_x=round(float(((1 - sh) * dk * np.arange(sh.shape[1])[None, :]).sum() / ((1 - sh) * dk).sum() - xc), 1))
vase["anchor_shift_px"] = dict(foot_row=round(vase["r4"]["foot_contact_y"] - vase["r3"]["foot_contact_y"], 2),
                               foot_centre_x=round(vase["r4"]["foot_centre_x"] - vase["r3"]["foot_centre_x"], 2))
res["vase"] = vase
print(json.dumps(vase, indent=1))

pend = {}
for t in ("r3", "r4"):
    a = alpha(t, "pendant")
    top = (a[:62] > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(top, connectivity=8)
    pieces = sorted([int(s) for s in st[1:, 4]], reverse=True)
    whole = (a > 0.5).astype(np.uint8)
    n2, _, st2, _ = cv2.connectedComponentsWithStats(whole, connectivity=8)
    pend[t] = dict(pieces_above_row_62=pieces, pieces_ge5px=[p for p in pieces if p >= 5], whole_layer_pieces_ge20px=sorted([int(s) for s in st2[1:, 4] if s >= 20], reverse=True),
                   alpha_mass_above_row_62=round(float(a[:62].sum()), 1))
res["pendant"] = pend
print(json.dumps(pend, indent=1))

pl = {}
a4 = alpha("r4", "planter")
ys = np.arange(1056, 1076)
xe = []
for y in ys:
    r = a4[y]
    x = int(np.nonzero(r > 0.5)[0].min())
    xe.append(x - 0.5 + (0.5 - r[x - 1]) / max(r[x] - r[x - 1], 1e-3))
k, b = np.polyfit(ys, np.array(xe), 1)
for t in ("r3", "r4"):
    a = alpha(t, "planter")
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    zone = (yy >= 1030) & (yy < 1056) & (xx < k * yy + b - 1.0) & (xx > 900)
    pl[t] = dict(alpha_mass_left_of_edge=round(float(a[zone].sum()), 1), px_alpha_gt_0_1=int((a[zone] > 0.1).sum()))
pl["edge_line"] = f"x = {k:.4f} y + {b:.2f} (r4 alpha, rows 1056-1075), the zone: rows 1030-1055, more than 1 px left of it"
res["planter_crescent"] = pl
print(json.dumps(pl, indent=1))
json.dump(res, open(os.path.join(OUT, "data/geometry.json"), "w"), indent=1)
