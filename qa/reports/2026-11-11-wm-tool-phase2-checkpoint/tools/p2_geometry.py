#!/usr/bin/env python3
"""
qa-agent 2026-11-11: size and position of the 12 defaults against house plan 1.3.5 / slots 1.9.3 and the cards, with QA's own projection
(qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py project(): house-plan camera M0, X right, Y toward the viewer, Z up),
measured on the layer alphas of manifest-r3.json. Each product is measured where it is visible (no occlusion guessing): the named edges
below are projected and compared with the alpha's edge on the same rows / columns; offsets in px (2720 canvas) and in cm at the
product's depth. Writes data/geometry.json.   ~/.venvs/motion/bin/python -I p2_geometry.py
"""
import importlib.util
import json
import math
import os

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
FW = 3840 * 2720 / 4072          # camera-frame width in canvas px


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * 2160 * 1530 / 2290, d


def cm_per_px(d):
    return 100 * d / ((CAM.get("lens", 24) / 36) * FW)


def alpha(k, thr=128):
    return np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3] >= thr


def box_of(m):
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def cyl_box(cx, cy, z0, z1, r, n=36):
    pts = [px(cx + r * math.cos(t), cy + r * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, n) for z in (z0, z1)]
    xs, ys, ds = zip(*pts)
    return [min(xs), min(ys), max(xs), max(ys)], float(np.mean(ds))


res = {}

# vase: body only (rows below the branches), D16 x H32 on the bench top (Z 0.45) at (-2.42, 1.35)
m = alpha("vase")
eb, d = cyl_box(-2.42, 1.35, 0.45, 0.77, 0.08)
w = m.sum(1)
body_rows = np.nonzero(w >= 0.6 * w.max())[0]
body = m.copy()
body[: body_rows.min()] = False
bb = box_of(body)
res["vase"] = dict(expected_body_box=[round(v, 1) for v in eb], layer_body_box=bb, depth_m=round(d, 2), cm_per_px=round(cm_per_px(d), 3),
                   width_cm=round((bb[2] - bb[0] + 1) * cm_per_px(d), 1), expected_width_cm=16,
                   bottom_offset_px=round(bb[3] - eb[3], 1), centre_x_offset_cm=round(((bb[0] + bb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(d), 1),
                   body_height_cm_from_rows=round((bb[3] - bb[1]) * cm_per_px(d), 1))

# basket: D35 x H39 at (-1.62, 0.78), handles +9
m = alpha("basket")
eb, d = cyl_box(-1.62, 0.78, 0.0, 0.39, 0.175)
bb = box_of(m)
w = m.sum(1)
body_rows = np.nonzero(w >= 0.8 * w.max())[0]
res["basket"] = dict(expected_body_box=[round(v, 1) for v in eb], layer_box_with_handles=bb, depth_m=round(d, 2), cm_per_px=round(cm_per_px(d), 3),
                     body_width_px=int(w.max()), body_width_cm=round(w.max() * cm_per_px(d), 1), expected_width_cm=35,
                     body_top_row=int(body_rows.min()), expected_rim_row=round(px(-1.62, 0.78 + 0.175, 0.39)[1], 1),
                     bottom_row=bb[3], expected_bottom_row_front=round(eb[3], 1),
                     handle_top_row=bb[1], expected_handle_top_row=round(px(-1.62, 0.78, 0.48)[1], 1),
                     centre_x_offset_cm=round(((bb[0] + bb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(d), 1))

# planter: pot centre (-1.95, 0.42), belly D42, opening 35.5, H35.5; visible: the left belly edge, the rim top, the base
m = alpha("planter")
pot_rows = range(1040, 1195)
eb, d = cyl_box(-1.95, 0.42, 0.0, 0.355, 0.21)
eo, _ = cyl_box(-1.95, 0.42, 0.355, 0.355, 0.1775)
left_edge = [int(np.nonzero(m[y])[0].min()) for y in pot_rows if m[y].any()]
res["planter"] = dict(expected_belly_box=[round(v, 1) for v in eb], expected_opening_box=[round(v, 1) for v in eo], depth_m=round(d, 2),
                      cm_per_px=round(cm_per_px(d), 3), layer_left_edge_min=int(min(left_edge)), expected_belly_left=round(eb[0], 1),
                      layer_left_edge_at_rim_rows=[int(np.nonzero(m[y])[0].min()) for y in (1046, 1050, 1055) if m[y].any()],
                      expected_opening_left=round(eo[0], 1),
                      opening_halfwidth_render_cm=round(((eo[0] + eo[2]) / 2 - min(int(np.nonzero(m[y])[0].min()) for y in (1046, 1050, 1055))) * cm_per_px(d), 1),
                      opening_halfwidth_card_cm=17.75, belly_halfwidth_card_cm=21.0)

# magazine holder: (-0.47, 2.57), 35 x 19 x 27.5, long side to the camera -> its top row
m = alpha("magazine-holder")
bb = box_of(m)
_, _, d = px(-0.47, 2.57, 0.2)
top_exp = min(px(-0.47 + sx, 2.57 + sy, 0.287)[1] for sx in (-0.175, 0.175) for sy in (-0.095, 0.095))
xs_exp = [px(-0.47 + sx, 2.57 + sy, 0.287)[0] for sx in (-0.175, 0.175) for sy in (-0.095, 0.095)]
res["magazine-holder"] = dict(layer_box=bb, expected_top_row=round(top_exp, 1), top_offset_px=round(bb[1] - top_exp, 1),
                              expected_x_range=[round(min(xs_exp), 1), round(max(xs_exp), 1)], depth_m=round(d, 2), cm_per_px=round(cm_per_px(d), 3),
                              width_px=bb[2] - bb[0], expected_width_px=round(max(xs_exp) - min(xs_exp), 1))

# floor lamp: base (1.52, 0.20) D26, shade D37 (bottom) x 23, top 1.58
m = alpha("floor-lamp")
bb = box_of(m)
_, _, d = px(1.52, 0.20, 1.0)
w = m.sum(1)
shade_rows = np.nonzero(w >= 40)[0]
shade_rows = shade_rows[shade_rows < bb[1] + 200]
shade_bot = int(shade_rows.max())
eshade, _ = cyl_box(1.52, 0.20, 1.35, 1.58, 0.185)
ebase, _ = cyl_box(1.52, 0.20, 0.0, 0.025, 0.13)
res["floor-lamp"] = dict(layer_box=bb, depth_m=round(d, 2), cm_per_px=round(cm_per_px(d), 3),
                         shade_width_px=int(w[shade_rows].max()), shade_width_cm=round(w[shade_rows].max() * cm_per_px(d), 1), card_shade_cm=37,
                         layer_top_row=bb[1], expected_top_row=round(eshade[1], 1), shade_bottom_row=shade_bot, expected_shade_bottom_row=round(eshade[3], 1),
                         base_width_px=int(w[bb[3] - 30:bb[3]].max()), base_width_cm=round(w[bb[3] - 30:bb[3]].max() * cm_per_px(d), 1), card_base_cm=26,
                         bottom_row=bb[3], expected_base_bottom_row=round(ebase[3], 1),
                         stem_x=float(np.mean(np.nonzero(m[bb[1] + 300])[0])), expected_stem_x=round(px(1.52, 0.20, 0.9)[0], 1))

# framed art: 3 x 50 x 70 at X -0.36 / 0.20 / 0.76, Z 1.13-1.83, Y 0 (frames add a few mm)
import cv2  # noqa: E402
m = alpha("framed-art").astype(np.uint8)
n, lab_, st, _ = cv2.connectedComponentsWithStats(m, 8)
isl = sorted([st[i] for i in range(1, n) if st[i, 4] > 1000], key=lambda s: s[0])
panels = []
for (xc, s) in zip((-0.36, 0.20, 0.76), isl):
    e = [px(xc - 0.25, 0.0, 1.83), px(xc + 0.25, 0.0, 1.13)]
    lb = [int(s[0]), int(s[1]), int(s[0] + s[2] - 1), int(s[1] + s[3] - 1)]
    dd = e[0][2]
    panels.append(dict(X=xc, expected_box=[round(e[0][0], 1), round(e[0][1], 1), round(e[1][0], 1), round(e[1][1], 1)], layer_box=lb,
                       width_cm=round((lb[2] - lb[0] + 1) * cm_per_px(dd), 1), height_cm=round((lb[3] - lb[1] + 1) * cm_per_px(dd), 1),
                       centre_offset_cm=[round(((lb[0] + lb[2]) / 2 - (e[0][0] + e[1][0]) / 2) * cm_per_px(dd), 1),
                                         round(((lb[1] + lb[3]) / 2 - (e[0][1] + e[1][1]) / 2) * cm_per_px(dd), 1)]))
res["framed-art"] = dict(panels=panels, card="3 x 50 x 70, sold unframed, rendered in a thin walnut frame (PR1)")

# sconces: plates (-0.85, 0, 1.75), (1.25, 0, 1.75); travertine cylinder D6.5 x H16 on a walnut block
m = alpha("accent-sconces").astype(np.uint8)
n, lab_, st, cen = cv2.connectedComponentsWithStats(m, 8)
isl = sorted([(st[i], cen[i]) for i in range(1, n) if st[i, 4] > 200], key=lambda s: s[0][0])
sc = []
for X, (s, c) in zip((-0.85, 1.25), isl):
    ex, ey, dd = px(X, 0.05, 1.75)
    sc.append(dict(X=X, expected_centre=[round(ex, 1), round(ey, 1)], layer_centre=[round(float(c[0]), 1), round(float(c[1]), 1)],
                   offset_cm=[round((c[0] - ex) * cm_per_px(dd), 1), round((c[1] - ey) * cm_per_px(dd), 1)],
                   width_cm=round(s[2] * cm_per_px(dd), 1), height_cm=round(s[3] * cm_per_px(dd), 1)))
res["accent-sconces"] = dict(units=sc, card="travertine cylinder D6.5 x H16 on a walnut block 9 deep; plate centre Z 1.75 assumed as the unit centre")

# pendant: hang (0.20, 1.72, 3.00), shade bottom Z 1.90, D50
m = alpha("pendant")
w = m.sum(1)
shade_rows = np.nonzero(w >= 120)[0]
bot = int(shade_rows.max())
# lowest image point of a bottom ring of radius r_b at Z: the front of the ring; fit Z by matching the row (the bottom tier ~ D30)
best = None
for Z in np.arange(1.70, 2.10, 0.0025):
    yb = max(px(0.20 + 0.15 * math.cos(t), 1.72 + 0.15 * math.sin(t), Z)[1] for t in np.linspace(0, 2 * math.pi, 72))
    if best is None or abs(yb - bot) < best[1]:
        best = (Z, abs(yb - bot))
_, _, d = px(0.20, 1.72, 2.05)
wide = int(w.max())
res["pendant"] = dict(shade_bottom_row=bot, shade_bottom_Z_fit_m=round(float(best[0]), 3), plan_Z=1.90, tolerance_cm=1.5,
                      bottom_tier_radius_assumed_m=0.15, widest_px=wide, widest_cm=round(wide * cm_per_px(d), 1), card_cm=50,
                      depth_m=round(d, 2), centre_x=float(np.mean(np.nonzero(m[int(np.argmax(w))])[0])),
                      expected_centre_x=round(px(0.20, 1.72, 2.05)[0], 1))
for rb in (0.12, 0.18):
    bz = None
    for Z in np.arange(1.70, 2.10, 0.0025):
        yb = max(px(0.20 + rb * math.cos(t), 1.72 + rb * math.sin(t), Z)[1] for t in np.linspace(0, 2 * math.pi, 72))
        if bz is None or abs(yb - bot) < bz[1]:
            bz = (Z, abs(yb - bot))
    res["pendant"][f"Z_fit_if_bottom_tier_r_{rb}"] = round(float(bz[0]), 3)

# bowl: (0.72, 1.94) on the table top Z 0.38, D20 x H8
m = alpha("bowl")
bb = box_of(m)
eb, d = cyl_box(0.72, 1.94, 0.38, 0.46, 0.10)
res["bowl"] = dict(expected_box=[round(v, 1) for v in eb], layer_box=bb, depth_m=round(d, 2), width_cm=round((bb[2] - bb[0] + 1) * cm_per_px(d), 1),
                   card_cm=20, centre_x_offset_cm=round(((bb[0] + bb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(d), 1),
                   bottom_offset_px=round(bb[3] - eb[3], 1), position_status="provisional (WM-T2)")

# candle holders: (0.33, 1.74) and (0.48, 1.68), D7 x H11 on Z 0.38, candles 7.5 / 6
m = alpha("candle-holders").astype(np.uint8)
n, lab_, st, cen = cv2.connectedComponentsWithStats(m, 8)
isl = sorted([(st[i], cen[i]) for i in range(1, n) if st[i, 4] > 200], key=lambda s: s[0][0])
ch = []
for (X, Y, hc), (s, c) in zip(((0.33, 1.74, 0.075), (0.48, 1.68, 0.06)), isl):
    eb, dd = cyl_box(X, Y, 0.38, 0.49 + hc, 0.035)
    lb = [int(s[0]), int(s[1]), int(s[0] + s[2] - 1), int(s[1] + s[3] - 1)]
    ch.append(dict(at=[X, Y], expected_box_with_candle=[round(v, 1) for v in eb], layer_box=lb,
                   centre_x_offset_cm=round(((lb[0] + lb[2]) / 2 - (eb[0] + eb[2]) / 2) * cm_per_px(dd), 1),
                   bottom_offset_px=round(lb[3] - eb[3], 1), top_offset_px=round(lb[1] - eb[1], 1),
                   width_cm=round(s[2] * cm_per_px(dd), 1)))
res["candle-holders"] = dict(units=ch)

# rug: 330 (X) x 230 (Y) centred (0.20, 1.92) -> X -1.45..1.85, Y 0.805..3.035; the back edge and the back-left corner are visible
m = alpha("rug", 1) | (np.asarray(Image.open(os.path.join(P2, "layers", byid["rug"]["file"])))[..., 3] > 0)
X0, X1, Y0 = 0.20 - 1.65, 0.20 + 1.65, 1.92 - 1.15
samples = []
for X in np.linspace(X0 + 0.3, X1 - 0.3, 12):
    ex, ey, dd = px(X, Y0, 0.0)
    xi = int(round(ex))
    if 0 <= xi < m.shape[1]:
        col = np.nonzero(m[:, xi])[0]
        if col.size:
            samples.append(dict(X=round(float(X), 2), expected_row=round(ey, 1), layer_top_row=int(col.min()), d=round(dd, 2),
                                offset_cm_along_Y=None))
res["rug"] = dict(back_edge=samples, back_left_corner_expected=[round(v, 1) for v in px(X0, Y0, 0.0)[:2]],
                  note="the back edge is hidden behind the sofa over most of its length; columns where the rug top row is the sofa's occlusion line read low")

# curtains: front stack X -2.29..-2.15 (room-side edge X -2.15), Y 2.65-2.95, to the floor
m = alpha("curtains")
rows = {}
for Z in (2.6, 2.0, 1.5, 1.0, 0.5):
    ex, ey, dd = px(-2.15, 2.65, Z)
    yi = int(round(ey))
    xr = int(np.nonzero(m[yi])[0].max()) if m[yi].any() else None
    rows[str(Z)] = dict(row=yi, expected_inner_edge_x=round(ex, 1), layer_inner_edge_x=xr,
                        offset_cm=None if xr is None else round((xr - ex) * cm_per_px(dd), 1))
res["curtains"] = dict(inner_edge=rows, note="room-side edge of the stack at the near (Y 2.65) end; the stack's left part runs off the canvas")
json.dump(res, open(os.path.join(OUT, "data/geometry.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
