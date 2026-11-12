#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): the WM-T3 clay check (designer docs/proposals/wm-r7-table-decisions-2026-11-12.md 1.4 / 1.6), QA's own clay:
the method of qa/reports/2026-11-12-wm-tool-phase2-r6-r7/tools/r67_table.py (QA's projection clay_wm_r1, camera M0 1.2; card cylinders
as filled projected silhouettes = convex hull of the projected rims, rasterised at 4x; table top Z 0.38), only the points changed:
  - bowls at (0.46, 1.94): black D20 x 8, white belly D21.2 x 6.4 (in the tool), speckled D21.3 x 5.2 (information);
  - holders 18 cm left of 1.9.4 (B's right edge X 0.21): travertine A/B 0.025 / 0.175 (D7 x 11, candles D6 x 7.5 / 6), also the R7 layer's
    pre-approved 9 cm lever (A 0.015); ceramic trays -0.125 / 0.125 (17 with handles x 13.3, H 7.2); iron plates -0.03 / 0.16 (D10.5,
    candles D7 x 15 / 18, and the 16 lever) (information);
  - against: the REAL cushion sets A / B / C (alpha >= 128 of the R8 set layers: the throw is the set's right piece), the real rug, floor lamp
    and the three curtain options (R8), the sofa (fixed furniture), A vs B, B vs bowl;
  - in plan: the bowl >= 2 cm inside the straight front edge Y 2.07, every footprint >= 2 cm inside the top X -0.50..0.90, Y 1.37..2.07
    (the clay's box of step0_clay_checks.py), and the 18 cm / 16 cm moves against 1.9.4.
Gap = the nearest distance between the silhouettes / the frame width (2565.0 canvas px). F3 >= 0.02.
Also: the bowl vs the throw measured vertically (the gap below the throw's lower edge in the bowl's columns), as the designer's 1.1 says.
Writes data/wmt3.json and overlays/wmt3-qa-clay.png.     ~/.venvs/motion/bin/python3.12 -I r8_wmt3.py
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
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
m8 = json.load(open(os.path.join(P2, "layers/manifest-r8.json")))
b8 = {l_["id"]: l_ for l_ in m8["layers"]}
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
FW = 3840 * 2720 / 4072
H, W = 1530, 2720
TOP = 0.38
TABLE = dict(x=(-0.50, 0.90), y=(1.37, 2.07))


def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * 2160 * 1530 / 2290, d


def cyl_pts(cx, cy, z0, z1, r, n=72):
    return [px(cx + r * math.cos(t), cy + r * math.sin(t), z)[:2] for t in np.linspace(0, 2 * math.pi, n, endpoint=False) for z in (z0, z1)]


def box_pts(cx, cy, z0, z1, hx, hy):
    return [px(cx + sx * hx, cy + sy * hy, z)[:2] for sx in (-1, 1) for sy in (-1, 1) for z in (z0, z1)]


def sil(parts):
    big = np.zeros((H * 4, W * 4), np.uint8)
    for part in parts:
        P = np.array(part, np.float32) * 4
        cv2.fillConvexPoly(big, cv2.convexHull(P).astype(np.int32), 255)
    return cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA) >= 128


def gap(a, b):
    if (a & b).any():
        return 0.0
    d = cv2.distanceTransform((~a).astype(np.uint8), cv2.DIST_L2, 5)
    return round(float(d[b].min()) / FW, 4)


def alpha(f, thr=128):
    return np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3] >= thr


sets = {s: alpha(m8["slot_cushions"]["sets"][s]["layer"]) for s in "ABC"}
ff = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3] >= 128
rug = alpha(b8["rug"]["file"])
lamp = alpha(b8["floor-lamp"]["file"])
curt = {"180502": alpha(b8["curtains"]["file"]), "554205": alpha(V8["curtains-v2"]["file"]), "linen": alpha(V8["curtains-v3"]["file"])}


def throw_of(m):
    """the set's rightmost large piece (the throw on the right arm)"""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    idx = [i for i in range(1, n) if st[i, 4] > 2000]
    i = max(idx, key=lambda i: st[i, 0] + st[i, 2])
    return lab == i


throws = {s: throw_of(sets[s]) for s in "ABC"}
BOWL_PT = (0.46, 1.94)
BOWLS = {"black D20 x 8 (default, in tool)": (0.10, 0.08), "white belly D21.2 x 6.4 (v2, in tool)": (0.106, 0.064),
         "speckled D21.3 x 5.2 (info, held)": (0.1065, 0.052)}
# holder pieces: (point, base parts, footprint half-extents for the plan check)
HOLD = {
    "travertine (in tool)": [((0.025, 1.74), "cyl", 0.035, 0.11, 0.03, 0.075), ((0.175, 1.68), "cyl", 0.035, 0.11, 0.03, 0.06)],
    "travertine, R7 layer's 9 cm lever (A 0.015)": [((0.015, 1.74), "cyl", 0.035, 0.11, 0.03, 0.075), ((0.175, 1.68), "cyl", 0.035, 0.11, 0.03, 0.06)],
    "ceramic trays (in tool)": [((-0.125, 1.74), "cyl", 0.085, 0.072, 0.03, 0.075), ((0.125, 1.68), "cyl", 0.085, 0.072, 0.03, 0.06)],
    "ceramic trays, disc D13.3 + ball handles (info, a tighter model)": [((-0.125, 1.74), "tray", 0.085, 0.072, 0.03, 0.075), ((0.125, 1.68), "tray", 0.085, 0.072, 0.03, 0.06)],
    "iron plates 15 / 18 (info, held)": [((-0.03, 1.74), "cyl", 0.0525, 0.02, 0.035, 0.15), ((0.16, 1.68), "cyl", 0.0525, 0.02, 0.035, 0.18)],
    "iron plates 15 / 16 lever (info, held)": [((-0.03, 1.74), "cyl", 0.0525, 0.02, 0.035, 0.15), ((0.16, 1.68), "cyl", 0.0525, 0.02, 0.035, 0.16)],
}


def holder_parts(sp):
    (x, y), kind, r, h, rc, hc = sp
    if kind == "cyl":       # the R7 model (r67_table.py): one cylinder of the full width (the trays: D17 with the handles), conservative
        return [cyl_pts(x, y, TOP, TOP + h, r), cyl_pts(x, y, TOP + h - 0.01, TOP + h + hc, rc)]
    # the tray as the card draws it: a disc D13.3 and two ball handles (D3) on the X axis at +-0.07, at the rim's height
    return [cyl_pts(x, y, TOP, TOP + h, 0.0665), cyl_pts(x - 0.07, y, TOP + h - 0.03, TOP + h, 0.015), cyl_pts(x + 0.07, y, TOP + h - 0.03, TOP + h, 0.015),
            cyl_pts(x, y, TOP + h - 0.01, TOP + h + hc, rc)]


def footprint(sp):
    (x, y), kind, r = sp[0], sp[1], sp[2]
    return (x - r, x + r, y - (r if kind == "cyl" else 0.0665), y + (r if kind == "cyl" else 0.0665))


res = dict(frame_width_px=round(FW, 2), table_top_z=TOP, table_box=TABLE, bowl_point=BOWL_PT)
# the moves against 1.9.4
SL = {"travertine": (0.205, 0.355, 0.035), "ceramic": (0.055, 0.305, 0.085), "iron": (0.15, 0.34, 0.0525)}
NEW = {"travertine": (0.025, 0.175), "ceramic": (-0.125, 0.125), "iron": (-0.03, 0.16)}
res["moves_vs_1_9_4"] = {k: dict(dA=round(NEW[k][0] - SL[k][0], 3), dB=round(NEW[k][1] - SL[k][1], 3), B_right_edge=round(NEW[k][1] + SL[k][2], 4))
                         for k in SL}
res["bowl_move_vs_1_9_4"] = round(0.46 - 0.62, 3)
clay = {}
bowl_sil = {bn: sil([cyl_pts(*BOWL_PT, TOP, TOP + h, r)]) for bn, (r, h) in BOWLS.items()}
for hn, pair in HOLD.items():
    A = sil(holder_parts(pair[0]))
    B = sil(holder_parts(pair[1]))
    rec = {"A x B": gap(A, B)}
    for s in "ABC":
        rec[f"holders x cushion set {s}"] = min(gap(A, sets[s]), gap(B, sets[s]))
    rec["holders x rug"] = min(gap(A, rug), gap(B, rug))
    rec["holders x floor lamp"] = min(gap(A, lamp), gap(B, lamp))
    rec["holders x curtains (worst option)"] = min(min(gap(A, c), gap(B, c)) for c in curt.values())
    rec["holders inside the sofa silhouette (share)"] = round(float(ff[A | B].mean()), 3)
    for bn, bs in bowl_sil.items():
        rec[f"B x bowl {bn}"] = gap(B, bs)
        rec[f"A x bowl {bn}"] = gap(A, bs)
    fps = [footprint(sp) for sp in pair]
    rec["footprints_min_inside_table_m"] = round(min(min(f[0] - TABLE["x"][0], TABLE["x"][1] - f[1], f[2] - TABLE["y"][0], TABLE["y"][1] - f[3]) for f in fps), 3)
    clay[hn] = rec
for bn, (r, h) in BOWLS.items():
    bs = bowl_sil[bn]
    rec = {f"bowl x cushion set {s}": gap(bs, sets[s]) for s in "ABC"}
    rec.update({f"bowl x throw {s}": gap(bs, throws[s]) for s in "ABC"})
    # vertical: in the bowl's columns, the bowl's top vs the throw's lowest pixel
    cols = np.nonzero(bs.any(0))[0]
    for s in "ABC":
        v = []
        for x in cols:
            ty = np.nonzero(throws[s][:, x])[0]
            by = np.nonzero(bs[:, x])[0]
            if len(ty) and len(by):
                v.append((by.min() - ty.max()) / FW)
        rec[f"bowl top below throw, vertical {s}"] = round(float(min(v)), 4) if v else None
    rec["bowl x rug"] = gap(bs, rug)
    rec["bowl x floor lamp"] = gap(bs, lamp)
    rec["bowl x curtains (worst option)"] = min(gap(bs, c) for c in curt.values())
    rec["bowl inside the front edge Y 2.07 (m)"] = round(TABLE["y"][1] - (BOWL_PT[1] + r), 4)
    clay[bn] = rec
res["clay"] = clay
# the bowl vs the rug at the 1.9.4 point too (the slots file: "bowl-sofa and bowl-rug: hidden overlap, as in step 0")
res["bowl_x_rug_at_1_9_4_point"] = {bn: gap(sil([cyl_pts(0.62, 1.94, TOP, TOP + h, r)]), rug) for bn, (r, h) in BOWLS.items()}
in_tool_h = [k for k in HOLD if "in tool" in k]
in_tool_b = [k for k in BOWLS if "in tool" in k]
worst = {}
for hn in in_tool_h:
    for k, v in clay[hn].items():
        if isinstance(v, float) and "share" not in k and "footprints" not in k and ("bowl" not in k or any(b in k for b in in_tool_b)):
            worst[f"{hn}: {k}"] = v
for bn in in_tool_b:
    for k, v in clay[bn].items():
        if isinstance(v, float) and "(m)" not in k and "x rug" not in k:
            worst[f"{bn}: {k}"] = v
res["in_tool_min"] = min(worst.values())
res["in_tool_min_at"] = min(worst, key=worst.get)
res["in_tool_below_0_02"] = {k: v for k, v in worst.items() if v < 0.02}
info = {}
for hn in HOLD:
    if "info, held" in hn:
        for k, v in clay[hn].items():
            if isinstance(v, float) and "share" not in k and "footprints" not in k and v < 0.02:
                info[f"{hn}: {k}"] = v
res["info_below_0_02"] = info
# render-agent's numbers for the same pairs (table-group-wm-t3.json, summary_in_tool 0.21)
ra = json.load(open(os.path.join(P2, "step0/wm-t3/table-group-wm-t3.json")))["summary_in_tool"]["0.21"]["worst"]
res["render_agent_in_tool_worst"] = {k: v["min"] for k, v in ra.items()}
json.dump(res, open(os.path.join(OUT, "data/wmt3.json"), "w"), indent=1)
print(json.dumps(res, indent=1))

# overlay: the clay silhouettes over the R8 default scene (set C, the tightest), cropped on the table
G = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r8-set-C-graded-v3c.png")).convert("RGB")).copy()
ov = G.astype(np.float32)
for m, c in ((sil(holder_parts(HOLD["travertine (in tool)"][0])) | sil(holder_parts(HOLD["travertine (in tool)"][1])), (80, 200, 255)),
             (bowl_sil["black D20 x 8 (default, in tool)"], (255, 120, 60)), (throws["C"], (120, 255, 120))):  # blue: travertine; orange: black bowl; green: set C's throw; yellow: the rug's visible edge; magenta: the D17 tray outlines
    ov[m] = ov[m] * 0.45 + np.array(c) * 0.55
edge = (cv2.dilate(rug.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~rug
ov[edge] = np.array((255, 230, 0))
tr = sil(holder_parts(HOLD["ceramic trays (in tool)"][0])) | sil(holder_parts(HOLD["ceramic trays (in tool)"][1]))
tedge = (cv2.dilate(tr.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~tr
ov[tedge] = np.array((255, 60, 200))
crop = ov[1050:1420, 1400:2250].astype(np.uint8)
Image.fromarray(crop).resize((crop.shape[1] * 2, crop.shape[0] * 2), Image.LANCZOS).save(os.path.join(OUT, "overlays/wmt3-qa-clay-set-C-x2.png"))
