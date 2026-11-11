#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): geometry of the re-rendered defaults and the variants, QA's own reading with QA's projection (house-plan
camera M0 via qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py project(), the canvas mapping of the checkpoint's
p2_geometry.py). Nothing from render-agent's code.

  vase (r5 default, v2; and r4 for reference)
    - the foot: its contact row (sub-pixel, on the foot column) and its centre; the stand point = where that contact meets the bench
      top (Z 0.45) on the camera ray, the axis half a foot further along the ray -> the offset from the plan point (-2.42, 1.35);
    - size: the card's cylinder (D x H, mouth) projected at that axis is the ruler: the widest 5-row mean of the alpha sum between the
      mouth and the foot, and the mouth-to-foot height;
    - lean: per body row, the midpoint of the alpha run through the axis minus the foot centre; a line fit over the body -> degrees
      off vertical, and the largest midpoint excursion in % of the width (a symmetric turned vase stays near 0);
    - F3: the nearest distance from the vase alpha (> 0.5) to the armchair (phase-1 fixed-furniture alpha > 0.5, the component left
      of x 1000), in camera-frame units (the frame is 3840 wide).
  planter (r5, and r4 for reference): the card's 42 belly / 35.5 opening / 35.5 tall pot at (-1.95, 0.42) projected: the rim row,
    the bottom row, the belly width, the opening width (the widest run in the first rows under the rim top, the left edge is free of
    the basket), against the layer's alpha.
  accent-sconces (default, v2, v3): the two pieces' alpha boxes (width x height px) and their centres against the default's.
Writes data/geometry.json.
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
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
FW = 3840 * 2720 / 4072
FHs = 2160 * 1530 / 2290
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
vfile = {v["id"]: v["file"] for vs in m5["variants"].values() for v in vs}


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * FHs, d


def alpha_file(f):
    return np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3].astype(np.float32) / 255


def on_plane(xp, yp, Z, X=-2.42, Y=1.35):
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


def cylinder(cx, cy, D, Hh, mouth, foot, z0=0.45, n=120):
    zs = np.linspace(z0, z0 + Hh, 9)
    xs = [px(cx + D / 2 * math.cos(t), cy + D / 2 * math.sin(t), z)[0] for t in np.linspace(0, 2 * math.pi, n) for z in zs[1:-1]]
    top = min(px(cx + mouth / 2 * math.cos(t), cy + mouth / 2 * math.sin(t), z0 + Hh)[1] for t in np.linspace(0, 2 * math.pi, n))
    bot = max(px(cx + foot / 2 * math.cos(t), cy + foot / 2 * math.sin(t), z0)[1] for t in np.linspace(0, 2 * math.pi, n))
    return dict(width_px=max(xs) - min(xs), height_px=bot - top)


ff = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3] > 127
n, lab, st, _ = cv2.connectedComponentsWithStats(ff.astype(np.uint8), connectivity=8)
arm_ids = [i for i in range(1, n) if st[i, 0] < 1000 and st[i, 4] > 2000]
arm = np.isin(lab, arm_ids)
arm_dt = cv2.distanceTransform((~arm).astype(np.uint8), cv2.DIST_L2, 5)

CARDS = {"vase r5": ("vase", b5["vase"]["file"], 0.16, 0.32, 0.09, 0.10), "vase r4": ("vase", b4["vase"]["file"], 0.16, 0.32, 0.09, 0.10),
         "vase-v2": ("vase", vfile["vase-v2"], 0.22, 0.32, 0.13, 0.14)}
res = {"vase": {}}
for name, (_, f, D, Hh, mouth, foot) in CARDS.items():
    a = alpha_file(f)
    M = a > 0.5
    ys = np.nonzero(M.any(1))[0]
    yb = int(ys.max())
    cols = np.nonzero(M[yb - 3:yb + 1].any(0))[0]
    xc = (cols.min() + cols.max() + 1) / 2.0
    col = a[:, int(round(xc))]
    yb_sub = yb + (float(col[yb]) - 0.5) / max(float(col[yb]) - float(col[min(yb + 1, a.shape[0] - 1)]), 1e-3)
    # the runs through the axis column, row by row
    runs = []
    for y in range(int(ys.min()), yb + 1):
        r = M[y]
        ix = int(round(xc))
        if not r[ix]:
            runs.append((y, 0, None, None))
            continue
        x0 = ix
        while x0 > 0 and r[x0 - 1]:
            x0 -= 1
        x1 = ix
        while x1 < r.size - 1 and r[x1 + 1]:
            x1 += 1
        runs.append((y, x1 - x0 + 1, x0, x1))
    wmax = max(w for _, w, _, _ in runs)
    # the mouth: walking up from the widest row, the first row where the run falls under 1.25x the narrowest neck run seen so far and
    # then widens again (the stems above are thin); simpler and robust here: the top of the body = the highest row whose run >= 0.45 x max
    body = [(y, w, x0, x1) for y, w, x0, x1 in runs if w >= 0.45 * wmax]
    top_body = body[0][0]
    # the mouth row: above top_body, the run stays >= 0.35 x max until the lip
    mouth_y = top_body
    for y, w, _, _ in reversed([r_ for r_ in runs if r_[0] < top_body]):
        if w >= 0.30 * wmax:
            mouth_y = y
        else:
            break
    rows = [r_ for r_ in runs if mouth_y + 6 <= r_[0] <= yb - 6 and r_[1] > 0]
    wv = np.array([r_[1] for r_ in rows], np.float64)
    w5 = np.convolve(wv, np.ones(5) / 5, mode="same")
    i = int(np.argmax(w5[2:-2])) + 2
    X, Y = on_plane(xc, yb_sub, 0.45)
    C = CAM["loc"]
    dx, dy = X - C[0], Y - C[1]
    nr = math.hypot(dx, dy)
    cx, cy = X + foot / 2 * dx / nr, Y + foot / 2 * dy / nr
    card = cylinder(cx, cy, D, Hh, mouth, foot)
    h_px = yb_sub - (mouth_y - 0.5)
    mids = np.array([(r_[2] + r_[3]) / 2.0 for r_ in rows])
    yy = np.array([r_[0] for r_ in rows], np.float64)
    k, b = np.polyfit(yy, mids, 1)
    exc = mids - xc
    gap = float(arm_dt[M].min()) * 3840 / FW / 3840     # canvas px -> frame px -> frame units
    res["vase"][name] = dict(foot_contact_y=round(yb_sub, 2), foot_centre_x=round(float(xc), 2), mouth_row=int(mouth_y),
                             stand_point_xy=[round(X, 3), round(Y, 3)], axis_xy=[round(cx, 3), round(cy, 3)],
                             offset_from_plan_point_m=round(math.hypot(cx + 2.42, cy - 1.35), 3),
                             width_px=round(float(w5[i]), 1), height_px=round(h_px, 1), card_px=dict(width=round(card["width_px"], 1), height=round(card["height_px"], 1)),
                             width_cm=round(D * 100 * w5[i] / card["width_px"], 1), height_cm=round(Hh * 100 * h_px / card["height_px"], 1),
                             lean_deg=round(math.degrees(math.atan(k)), 2), midline_excursion_max_pct_of_width=round(float(np.abs(exc).max() / w5[i] * 100), 1),
                             midline_excursion_p90_pct=round(float(np.percentile(np.abs(exc), 90) / w5[i] * 100), 1),
                             f3_gap_to_armchair_frame=round(gap, 4))
    print(name, res["vase"][name])
res["vase"]["default_vs_v2_foot"] = dict(dx_px=round(res["vase"]["vase-v2"]["foot_centre_x"] - res["vase"]["vase r5"]["foot_centre_x"], 2),
                                         dy_px=round(res["vase"]["vase-v2"]["foot_contact_y"] - res["vase"]["vase r5"]["foot_contact_y"], 2))

# planter
pl = {}
cx, cy = -1.95, 0.42
rim_top = min(px(cx + 0.1775 * math.cos(t), cy + 0.1775 * math.sin(t), 0.355)[1] for t in np.linspace(0, 2 * math.pi, 180))
rim_front = max(px(cx + 0.1775 * math.cos(t), cy + 0.1775 * math.sin(t), 0.355)[1] for t in np.linspace(0, 2 * math.pi, 180))
bot = max(px(cx + 0.21 * math.cos(t), cy + 0.21 * math.sin(t), 0.0)[1] for t in np.linspace(0, 2 * math.pi, 180))
belly_x = [px(cx + 0.21 * math.cos(t), cy + 0.21 * math.sin(t), z)[0] for t in np.linspace(0, 2 * math.pi, 180) for z in np.linspace(0.05, 0.30, 6)]
open_x = [px(cx + 0.1775 * math.cos(t), cy + 0.1775 * math.sin(t), 0.355)[0] for t in np.linspace(0, 2 * math.pi, 180)]
pl["projected"] = dict(rim_top_row=round(rim_top, 1), rim_front_row=round(rim_front, 1), bottom_row=round(bot, 1),
                       belly_left=round(min(belly_x), 1), belly_right=round(max(belly_x), 1), belly_width_px=round(max(belly_x) - min(belly_x), 1),
                       opening_left=round(min(open_x), 1), opening_right=round(max(open_x), 1), opening_width_px=round(max(open_x) - min(open_x), 1))
for t, man in (("r5", b5), ("r4", b4)):
    a = alpha_file(man["planter"]["file"]) > 0.5
    pot = a.copy()
    pot[:1000] = False                                    # the tree's crown and trunk above the rim are out (the rim is near row 1045)
    pot[:, :900] = False
    pot[:, 1150:] = False
    ys = np.nonzero(pot.any(1))[0]
    lefts = {int(y): int(np.nonzero(pot[y])[0].min()) for y in ys}
    rights = {int(y): int(np.nonzero(pot[y])[0].max()) for y in ys}
    # the rim top: the first row (from 1000 down) where the pot run is wider than 60 % of the projected opening (the trunk is narrow)
    rim = next(int(y) for y in ys if rights[y] - lefts[y] > 0.6 * pl["projected"]["opening_width_px"])
    rec = dict(rim_top_row=rim, bottom_row=int(ys.max()), left_edge_min=min(lefts.values()), left_edge_rows_min=int(min(lefts, key=lefts.get)),
               left_edge_at_rim_plus=[lefts.get(rim + d_) for d_ in (2, 5, 10, 20)],
               belly_left_vs_projected_px=round(min(lefts.values()) - pl["projected"]["belly_left"], 1),
               rim_vs_projected_px=round(rim - pl["projected"]["rim_top_row"], 1), bottom_vs_projected_px=round(int(ys.max()) - pl["projected"]["bottom_row"], 1))
    # the free left half: half-widths from the projected axis
    axis_x = (pl["projected"]["belly_left"] + pl["projected"]["belly_right"]) / 2
    cmpp = 0.42 * 100 / pl["projected"]["belly_width_px"]
    rec["belly_halfwidth_cm_left"] = round((axis_x - min(lefts.values())) * cmpp, 1)
    rec["opening_halfwidth_cm_left_at_rim_plus2"] = round((axis_x - lefts[rim + 2]) * cmpp, 1) if (rim + 2) in lefts else None
    rec["height_cm"] = round((int(ys.max()) - rim) / (pl["projected"]["bottom_row"] - pl["projected"]["rim_top_row"]) * 35.5, 1)
    pl[t] = rec
    print("planter", t, rec)
res["planter"] = pl

# sconces
sc = {}
for name, f in (("default", b5["accent-sconces"]["file"]), ("v2", vfile["accent-sconces-v2"]), ("v3", vfile["accent-sconces-v3"])):
    a = alpha_file(f) > 0.5
    n_, lab_, st_, cen = cv2.connectedComponentsWithStats(a.astype(np.uint8), connectivity=8)
    pieces = sorted([(int(st_[i, 0]), int(st_[i, 1]), int(st_[i, 2]), int(st_[i, 3]), int(st_[i, 4]), [round(float(c), 1) for c in cen[i]])
                     for i in range(1, n_) if st_[i, 4] > 50])
    sc[name] = [dict(x=p[0], y=p[1], w=p[2], h=p[3], px=p[4], centre=p[5]) for p in pieces]
    print("sconce", name, sc[name])
res["accent-sconces"] = sc
json.dump(res, open(os.path.join(OUT, "data/geometry.json"), "w"), indent=1)
