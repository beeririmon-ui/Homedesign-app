#!/usr/bin/env python3
"""
Clay checks of the warm-modern living-room clay r2 (house plan 1.3.2 section 0א WMC1-WMC5, slots 1.9.1 by_style.warm-modern;
render-agent, 2026-11-07; 0 var2 tokens). The same shape as r1 (clay_checks_wm_r1.py): the slot boxes, the named lines (with the r2
numbers: bench edge X -1.98, corner tangents Y 0.30 / X -2.00, the band edge, the slot edges, the track at 2.86, the stack's edge Y 2.70),
the F3 lines along the frame edges, the vase against the armchair, plus the r1 findings, each r1 -> r2 in px:
  (a) the planter against the curtain stack (r1: pot 9 px from the back stack in M0, the crown over the stack);
  (b) the crown (r1: the r 0.40 envelope past the back jamb, 7 px from the glazing in M0);
  (c) the M0p left edge: the rounded corner's tangent line and the bench's back end (r1: along the edge, u 0.005 and 0.002);
  (d) the planter against the basket: does the pot rim and the basket top read as one line (M0); the designer's lever basket (-1.55, 0.80)
      is projected only, not applied.
Reads framing/warm-modern-r2/selfcheck-render-A.json and the index passes in the scratchpad (wm-r2-idx/, and wm-r1-idx/ for r1);
writes clay-checks-2026-11-07.json, overlays/<frame>-lines.png and the sheet warm-modern-r1-vs-r2.jpg.

  python3 -P clay_checks_wm_r2.py
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
R1 = os.path.join(HERE, "..", "warm-modern-r1")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IDX = {"r2": os.path.join(SCR, "wm-r2-idx"), "r1": os.path.join(SCR, "wm-r1-idx")}
plan = json.load(open(os.path.join(REPO, "docs", "house-plan.json")))
slots = json.load(open(os.path.join(REPO, "data", "slots", "living-room.json")))
wm_slots = slots["by_style"]["warm-modern"]
sc = json.load(open(os.path.join(HERE, "selfcheck-render-A.json")))["frames"]
r1_checks = json.load(open(os.path.join(R1, "clay-checks-2026-11-07.json")))
CAMS = {c["id"]: c for c in plan["cameras"] if c["id"] in ("M0", "M0p", "M0x")}
CX, CY, CW, CH = 116, 65, 3840, 2160          # the 3 % overscan canvas 4072 x 2290 -> the 16:9 frame
PLANTER_POT, PLANTER_CROWN, ARMCHAIR = 35, 60, 3

# r2 geometry (house plan 1.3.2 / slots 1.9.1)
GEO = dict(r1=dict(pot_c=(-2.00, 0.47), pot_r=0.19, pot_h=0.45, crown_r=0.40, crown_z=(0.60, 1.65), bench_x1=-1.90, corner_r=0.15),
           r2=dict(pot_c=(-1.95, 0.42), pot_r=0.21, pot_h=0.355, crown_r=0.28, crown_z=(0.70, 1.65), bench_x1=-1.98, corner_r=0.30))
G = GEO["r2"]
BASKET = dict(c=(-1.62, 0.78), r=0.175, h=0.39)
LEVER = dict(c=(-1.55, 0.80), r=0.175, h=0.39)


def P(cam, X, Y, Z):
    C, Hc, yaw = cam["loc"][:2], cam["loc"][2], math.radians(cam["yaw_deg_left"])
    f, r = (-math.sin(yaw), -math.cos(yaw)), (math.cos(yaw), -math.sin(yaw))
    dx, dy = X - C[0], Y - C[1]
    d, x = f[0] * dx + f[1] * dy, r[0] * dx + r[1] * dy
    return cam["u0"] + 0.6667 * x / d, cam["v0"] + 1.1852 * (Hc - Z) / d, d


def seg(cam, a, b, n=400):
    pts = []
    for k in range(n + 1):
        t = k / n
        q = [a[i] + (b[i] - a[i]) * t for i in range(3)]
        u, v, d = P(cam, *q)
        if d > 0.05:
            pts.append((u, v))
    return pts


def to_frame(b):
    return [round((b[0] * 4072 - CX) / CW, 4), round((b[1] * 4072 - CX) / CW, 4), round((b[2] * 2290 - CY) / CH, 4), round((b[3] * 2290 - CY) / CH, 4)]


def clay_box(fid, key):
    b = sc.get(fid, {}).get("boxes", {}).get(key)
    return None if b is None else to_frame(b["box"])


def box(cam, pts):
    uv = [P(cam, *p) for p in pts]
    return [round(min(a[0] for a in uv), 3), round(max(a[0] for a in uv), 3), round(min(a[1] for a in uv), 3), round(max(a[1] for a in uv), 3)]


def corners(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def circ(cx, cy, r, z, n=180):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]


def cyl(cx, cy, r, z0, z1, n=96):
    return circ(cx, cy, r, z0, n) + circ(cx, cy, r, z1, n)


def ellip(cx, cy, r, z0, z1, n=48, m=24):
    zc, rz = (z0 + z1) / 2, (z1 - z0) / 2
    out = []
    for j in range(m + 1):
        ph = -math.pi / 2 + math.pi * j / m
        out += circ(cx, cy, r * math.cos(ph), zc + rz * math.sin(ph), n)
    return out


def rrect(cx, cy, w, dp, deg, z0, z1):
    a, out = math.radians(deg), []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = sx * w / 2, sy * dp / 2
            out += [(cx + lx * math.cos(a) - ly * math.sin(a), cy + lx * math.sin(a) + ly * math.cos(a), z) for z in (z0, z1)]
    return out


def px_u(u):
    return u * CW + CX


def px_v(v):
    return v * CH + CY


M0 = CAMS["M0"]
S = {s["id"]: s for s in slots["slots"]}
WS = wm_slots["slots"]


def slot_box(slot, part=None):
    m = (WS.get(slot, {}) or {}).get("m0_1_2") or S.get(slot, {}).get("m0_1_2", {})
    if part:
        return (m.get("parts") or {}).get(part) or m.get(part)
    return m.get("box")


# ------------------------------------------------------------------------------------------------- index passes
def load_idx(run, fid):
    p = os.path.join(IDX[run], f"{fid}.npz")
    if not os.path.exists(p):
        return None, None
    z = np.load(p, allow_pickle=True)
    nm = json.load(open(os.path.join(IDX[run], f"{fid}-names.json")))
    return z["idx"], {int(k): v for k, v in nm["names"].items()}


def pidx_of(names, key):
    return [k for k, v in names.items() if v[0] == key]


def min_dist(a, b):
    """the smallest Euclidean distance in px between two pixel sets (0 = they touch or overlap)"""
    if a is None or b is None or not a.any() or not b.any():
        return None
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return round(float(dt[a].min()), 1)


def fpct(px):
    return None if px is None else round(100 * px / CH, 2)


def bbox_frame(m):
    if m is None or not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [round((xs.min() - CX) / CW, 4), round((xs.max() + 1 - CX) / CW, 4), round((ys.min() - CY) / CH, 4), round((ys.max() + 1 - CY) / CH, 4)]


def pot_rim_top_v(cam, g):
    """the far edge of the pot's rim ellipse (its silhouette top) in frame v"""
    return min(P(cam, *q)[1] for q in circ(*g["pot_c"], g["pot_r"], g["pot_h"]))


def masks(run, fid):
    idx, names = load_idx(run, fid)
    if idx is None:
        return None
    g = GEO[run]
    pot_all = idx == PLANTER_POT
    # pidx 35 also carries the trunk (build_alts 'extra'): the pot alone = its pixels from 3 px above the projected rim's far edge down
    rim_row = int(round(px_v(pot_rim_top_v(CAMS[fid], g)))) - 3 if P(CAMS[fid], *g["pot_c"], 0.2)[2] > 0.05 else 0
    pot = pot_all.copy()
    pot[:max(rim_row, 0)] = False
    trunk = pot_all & ~pot
    return dict(idx=idx, names=names, pot=pot, trunk=trunk, crown=idx == PLANTER_CROWN, planter=pot_all | (idx == PLANTER_CROWN),
                curtains=np.isin(idx, pidx_of(names, "living/curtains")), basket=np.isin(idx, pidx_of(names, "living/basket")),
                vase=np.isin(idx, pidx_of(names, "living/vase")), armchair=idx == ARMCHAIR, bench=np.isin(idx, pidx_of(names, "living/window-bench")),
                corner=np.isin(idx, pidx_of(names, "living/rounded-corner")),
                glazing=np.isin(idx, [0, 4, 14]))     # the glass / sky, the steel frames, the reveal lining


MK = {(run, fid): masks(run, fid) for run in ("r1", "r2") for fid in CAMS}


def opening_mask(fid, shape):
    q3 = [(-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45), (-2.30, 2.85, 2.70), (-2.30, 0.75, 2.70)]
    m = Image.new("L", (shape[1], shape[0]), 0)
    if not any(P(CAMS[fid], *q)[2] <= 0.05 for q in q3):
        ImageDraw.Draw(m).polygon([(px_u(P(CAMS[fid], *q)[0]), px_v(P(CAMS[fid], *q)[1])) for q in q3], fill=1)
    return np.asarray(m).astype(bool)


# ------------------------------------------------------------------------------------------------- slot boxes
rows = []


def row(slot, label, proj, clay, part=None, note=""):
    sb = slot_box(slot, part)
    cl = lambda b: None if b is None else [min(max(x, 0.0), 1.0) for x in b]  # noqa: E731
    dp = None if (sb is None or proj is None) else round(max(abs(a - b) for a, b in zip(cl(sb), cl(proj))), 3)
    dc = None if (sb is None or clay is None) else round(max(abs(a - b) for a, b in zip(cl(sb), cl(clay))), 3)
    w = max([x for x in (dp, dc) if x is not None] or [0])
    clay = None if clay is None else [round(float(x), 4) for x in clay]
    rows.append(dict(slot=slot + (f" ({part})" if part else ""), item=label, slots_1_9_1=sb, projection=proj, clay=clay, max_diff_projection=dp,
                     max_diff_clay=dc, verdict=("not comparable" if (dp is None and dc is None) else "agrees (<= 0.02)" if w <= 0.02 else
                                                "estimate off (0.02-0.05)" if w <= 0.05 else "CONTRADICTION (> 0.05)"), note=note))


m2 = MK[("r2", "M0")]
ARM = (-1.23, 2.73)
row("sofa", "sofa 220 x 92 x 78", box(M0, corners(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)), clay_box("M0", "sofa 220x92x78 (fixed-product)"))
row("coffee-table", "coffee table 140 x 70 h 38", box(M0, corners(-0.50, 0.90, 1.37, 2.07, 0.0, 0.38)), clay_box("M0", "coffee table 140x70 h38 (fixed-product)"))
row("armchair", "armchair 72 x 78 h 70 (-1.23, 2.73) 25 deg, Nordic geometry (WM-F1)", box(M0, rrect(*ARM, 0.72, 0.78, 25, 0.0, 0.70)),
    clay_box("M0", "armchair 72x78 h70 (fixed-product)"))
row("pendant", "pendant shade 40 x 28, bottom 1.90", box(M0, cyl(0.20, 1.72, 0.20, 1.90, 2.18)), clay_box("M0", "living/pendant"))
row("vase", "vase on the bench, base (-2.42, 1.35, 0.45), body to 0.76, branches to 1.05", box(M0, cyl(-2.42, 1.35, 0.08, 0.45, 1.05)), clay_box("M0", "living/vase"))
row("basket", "basket (-1.62, 0.78) d 35 h 39 (unchanged; lever not applied)", box(M0, cyl(*BASKET["c"], BASKET["r"], 0.0, BASKET["h"])), clay_box("M0", "living/basket"))
row("magazine-holder", "magazine holder (-0.54, 2.52) 32 x 22 x 40", box(M0, corners(-0.70, -0.38, 2.41, 2.63, 0.0, 0.40)), clay_box("M0", "living/magazine-holder"))
row("planter", "planter (-1.95, 0.42): pot d 42 x 35.5 + olive crown r 0.28 Z 0.70-1.65 (WMC2)",
    box(M0, cyl(*G["pot_c"], G["pot_r"], 0.0, G["pot_h"]) + ellip(*G["pot_c"], G["crown_r"], *G["crown_z"])), bbox_frame(m2["planter"]) if m2 else None,
    note="clay = the index pass (pot + trunk pidx 35, crown pidx 60)")
row("planter", "the pot alone, d 42 x 35.5", box(M0, cyl(*G["pot_c"], G["pot_r"], 0.0, G["pot_h"])), bbox_frame(m2["pot"]) if m2 else None, part="pot",
    note="clay = the visible pot (the basket in front hides most of it, so its left / right are the visible part)")
row("curtains", "one front stack Y 2.70-3.00 (WMC1)", box(M0, corners(-2.28, -2.16, 2.70, 3.00, 0.005, 2.86)), bbox_frame(m2["curtains"]) if m2 else None,
    part="front_stack", note="clay = the index pass; the stack runs off the frame's left edge")
row("rug", "rug 330 x 240", None, clay_box("M0", "living/rug"))
row("bowl", "bowl d 24 h 9 (0.68, 1.92)", box(M0, cyl(0.68, 1.92, 0.12, 0.38, 0.47)), clay_box("M0", "living/bowl"))
row("candle-holders", "candle holders", box(M0, corners(0.42, 0.65, 1.55, 1.75, 0.38, 0.63)), clay_box("M0", "living/candle-holders"))

# ------------------------------------------------------------------------------------------------- named lines
YF = 6.2   # the living room's front wall (v4-spec room.y_front)
LINES = {
    "glazing_head": ((-2.30, 0.75, 2.70), (-2.30, 2.85, 2.70)),
    "glazing_sill_line": ((-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45)),
    "glazing_jamb_back_Y0.75": ((-2.30, 0.75, 0.45), (-2.30, 0.75, 2.70)),
    "glazing_jamb_front_Y2.85": ((-2.30, 2.85, 0.45), (-2.30, 2.85, 2.70)),
    "mullion_Y1.45_frame_plane": ((-2.65, 1.45, 0.45), (-2.65, 1.45, 2.70)),
    "mullion_Y2.15_frame_plane": ((-2.65, 2.15, 0.45), (-2.65, 2.15, 2.70)),
    "bench_front_top_edge_X-1.98": ((-1.98, 0.75, 0.45), (-1.98, 2.85, 0.45)),
    "bench_end_front_Y2.85": ((-1.98, 2.85, 0.0), (-1.98, 2.85, 0.45)),
    "bench_end_back_Y0.75": ((-1.98, 0.75, 0.0), (-1.98, 0.75, 0.45)),
    "rounded_corner_tangent_left_wall_Y0.30": ((-2.30, 0.30, 0.0), (-2.30, 0.30, 2.82)),
    "rounded_corner_tangent_back_wall_X-2.00": ((-2.00, 0.0, 0.0), (-2.00, 0.0, 3.0)),
    "curtain_band_edge_X-2.05_Z2.82": ((-2.05, 0.0, 2.82), (-2.05, YF, 2.82)),
    "curtain_slot_edge_X-2.26_Z2.82": ((-2.26, 0.15, 2.82), (-2.26, YF, 2.82)),
    "curtain_slot_edge_X-2.18_Z2.82": ((-2.18, 0.06, 2.82), (-2.18, YF, 2.82)),
    "curtain_track_X-2.22_Z2.86": ((-2.22, 0.70, 2.86), (-2.22, 3.00, 2.86)),
    "curtain_stack_back_edge_Y2.70": ((-2.16, 2.70, 0.005), (-2.16, 2.70, 2.82)),
}


def line_summary(cam, a, b):
    pts = [(u, v) for u, v in seg(cam, a, b, 2000) if -0.2 <= u <= 1.2 and -0.2 <= v <= 1.2]
    if not pts:
        return dict(in_frame=False)
    inn = [(u, v) for u, v in pts if 0 <= u <= 1 and 0 <= v <= 1]
    out = dict(in_frame=bool(inn), start_uv=[round(pts[0][0], 4), round(pts[0][1], 4)], end_uv=[round(pts[-1][0], 4), round(pts[-1][1], 4)])
    if inn:
        best = (0.0, None)
        for ename, fn in (("left", lambda q: q[0]), ("right", lambda q: 1 - q[0]), ("top", lambda q: q[1]), ("bottom", lambda q: 1 - q[1])):
            run, prev = 0.0, None
            for q in inn:
                if fn(q) < 0.01:
                    if prev is not None:
                        run += math.hypot(q[0] - prev[0], q[1] - prev[1])
                    prev = q
                    best = max(best, (run, ename), key=lambda t: t[0])
                else:
                    run, prev = 0.0, None
        out["longest_run_within_0_01_of_an_edge"] = dict(length=round(best[0], 4), edge=best[1])
        out["runs_along_an_edge"] = bool(best[0] > 0.05)
    return out


lines = {fid: {k: line_summary(CAMS[fid], *ab) for k, ab in LINES.items()} for fid in CAMS}
arch_clay = {fid: {k: clay_box(fid, k) for k in ("living/window-bench", "living/rounded-corner", "living/curtain-track")} for fid in CAMS}
f3_lines = {fid: [dict(line=k, **v["longest_run_within_0_01_of_an_edge"]) for k, v in L.items() if v.get("runs_along_an_edge")]
            for fid, L in lines.items()}

# ------------------------------------------------------------------------------------------------- the vase against the armchair (as r1)
check_vase = {}
if m2:
    vase, arm = m2["vase"], m2["armchair"]
    per = []
    for c in np.nonzero(vase.any(0))[0]:
        vb = int(np.nonzero(vase[:, c])[0].max())
        ar = np.nonzero(arm[:, c])[0]
        if ar.size:
            per.append((int(ar.min()) - vb - 1, int(c)))
    dmin = min_dist(vase, arm)
    check_vase = dict(min_euclidean_gap_px=dmin, min_euclidean_gap_frame_pct=fpct(dmin), min_vertical_gap_px=min(per)[0] if per else None,
                      reads="clear (>= 1 % of the frame)" if dmin and dmin >= 0.01 * CH else "tangent / touching",
                      r1=dict(min_euclidean_gap_px=r1_checks["check1_vase_vs_armchair_back_M0"].get("min_euclidean_gap_px")))


# ------------------------------------------------------------------------------------------------- (a) planter vs the curtain stack
def back_jamb_u(fid):
    return P(CAMS[fid], -2.30, 0.75, 1.575)[0]


fa = {}
for fid in CAMS:
    m = MK[("r2", fid)]
    if not m:
        continue
    e = dict(curtain_px=int(m["curtains"].sum()), planter_px=int(m["planter"].sum()))
    if m["curtains"].any() and m["planter"].any():
        e.update(pot_to_curtains_px=min_dist(m["pot"], m["curtains"]), crown_to_curtains_px=min_dist(m["crown"], m["curtains"]),
                 planter_to_curtains_px=min_dist(m["planter"], m["curtains"]))
        e["planter_to_curtains_frame_u"] = None if e["planter_to_curtains_px"] is None else round(e["planter_to_curtains_px"] / CW, 4)
    else:
        e["note"] = "the planter and the curtains are not both in this frame"
    fa[fid] = e
r1f = r1_checks["check2_stacks_planter_vs_glazing"]["frames"]
finding_a = dict(
    r1=dict(M0=dict(pot_to_back_stack_px=r1f["M0"].get("pot_vs_back_stack_gap_px"), crown_and_back_stack_touch=r1f["M0"].get("crown_and_back_stack_touch")),
            M0p=dict(pot_to_curtains_px=r1f.get("M0p", {}).get("pot_vs_back_stack_gap_px"))),
    r2=fa,
    plan=dict(back_stack="none (WMC1, one-way draw)", front_stack_y=[2.70, 3.00], planter_y_max_pot=round(G["pot_c"][1] + G["pot_r"], 3),
              planter_to_front_stack_y_m=round(2.70 - (G["pot_c"][1] + G["crown_r"]), 2)),
)
finding_a["resolved"] = bool(fa.get("M0", {}).get("planter_to_curtains_px") is not None and fa["M0"]["planter_to_curtains_px"] >= 0.02 * CW)


# ------------------------------------------------------------------------------------------------- (b) the crown
def boundary_clearance(c, r):
    """3D clearance of a horizontal circle (centre c, radius r) to the room's back-left corner: the left wall X -2.30 (Y 0.30-0.75; the
    glazing plane beyond), the back wall Y 0 (X >= -2.00), and the rounded corner (arc centre (-2.00, 0.30), R 0.30)"""
    R = G["corner_r"]
    ac = (-2.30 + R, 0.0 + R)
    cl = dict(left_wall=round(c[0] - r - (-2.30), 3), back_wall=round(c[1] - r - 0.0, 3))
    # the arc: points on it, distance to the circle
    arc = [(ac[0] - R * math.cos(t), ac[1] - R * math.sin(t)) for t in np.linspace(0, math.pi / 2, 200)]
    cl["rounded_corner"] = round(min(math.hypot(p[0] - c[0], p[1] - c[1]) for p in arc) - r, 3)
    cl["back_jamb_Y0.75"] = round(0.75 - (c[1] + r), 3)
    return cl


fb = {}
for fid in CAMS:
    m = MK[("r2", fid)]
    if not m or not m["crown"].any():
        continue
    op = opening_mask(fid, m["idx"].shape)
    cr = m["crown"]
    ys, xs = np.nonzero(cr)
    e = dict(crown_bbox_frame=bbox_frame(cr), over_the_opening_px=int((cr & op).sum()),
             crown_to_visible_glazing_px=min_dist(cr, m["glazing"]), pot_to_visible_glazing_px=min_dist(m["pot"], m["glazing"]))
    if op.any():
        ju = back_jamb_u(fid)
        e["back_jamb_line_u"] = round(ju, 4)
        e["crown_left_u_minus_back_jamb_u"] = round((xs.min() - CX) / CW - ju, 4)
        e["crown_left_minus_back_jamb_px"] = int(xs.min() - round(px_u(ju)))
    e["crown_to_corner_silhouette_px"] = min_dist(cr, m["corner"])
    fb[fid] = e
finding_b = dict(
    r1=dict(plan="envelope r 0.40 at (-2.00, 0.47): Y to 0.87 (0.12 past the back jamb), X to -2.40 (0.10 through the wall), contained the back stack",
            M0=dict(crown_to_visible_glazing_px=r1f["M0"]["planter-crown"]["gap_to_visible_glazing_px"],
                    crown_left_edge_minus_back_stack_left_edge_px=r1f["M0"].get("crown_left_edge_minus_back_stack_left_edge_px"))),
    r2=dict(plan=dict(centre=list(G["pot_c"]), r=G["crown_r"], z=list(G["crown_z"]), x_min=round(G["pot_c"][0] - G["crown_r"], 3),
                      y_max=round(G["pot_c"][1] + G["crown_r"], 3), clearances_m=boundary_clearance(G["pot_c"], G["crown_r"]),
                      pot_clearances_m=boundary_clearance(G["pot_c"], G["pot_r"])), frames=fb),
)
pb = finding_b["r2"]["plan"]["clearances_m"]
finding_b["resolved"] = bool(min(pb.values()) > 0.0 and fb.get("M0", {}).get("over_the_opening_px", 1) == 0)


# ------------------------------------------------------------------------------------------------- (c) the M0p left edge
def vline_u(cam, X, Y):
    return P(cam, X, Y, 1.0)[0]


fc = {}
for run in ("r1", "r2"):
    g = GEO[run]
    cam = CAMS["M0p"]
    m = MK[(run, "M0p")]
    tan_y = g["corner_r"]
    e = dict(corner_tangent_line=dict(xy=[-2.30, tan_y], u=round(vline_u(cam, -2.30, tan_y), 4)),
             bench_back_end_line=dict(xy=[g["bench_x1"], 0.75], u=round(vline_u(cam, g["bench_x1"], 0.75), 4)))
    # the rounded corner's silhouette (the arc seen from the camera): its u span
    R = g["corner_r"]
    arc_u = [vline_u(cam, -2.30 + R - R * math.cos(t), R - R * math.sin(t)) for t in np.linspace(0, math.pi / 2, 200)]
    e["corner_arc_u_span"] = [round(min(arc_u), 4), round(max(arc_u), 4)]
    for k in ("corner_tangent_line", "bench_back_end_line"):
        u = e[k]["u"]
        e[k]["px_from_left_edge"] = round(u * CW, 1)
        e[k]["reads"] = ("outside the frame" if u < 0 else "along the left edge (F3: within 0.01)" if u < 0.01 else "clear of the edge (>= 0.01)")
    if m is not None:
        for key, mk in (("bench", m["bench"]), ("corner", m["corner"])):
            if mk.any():
                ys, xs = np.nonzero(mk)
                inside = xs[(xs >= CX) & (xs < CX + CW)]
                e[f"{key}_pixels"] = dict(px_in_frame=int(((mk[:, CX:CX + CW]).sum())), u_span_in_frame=None if inside.size == 0 else
                                         [round((inside.min() - CX) / CW, 4), round((inside.max() + 1 - CX) / CW, 4)])
            else:
                e[f"{key}_pixels"] = dict(px_in_frame=0)
    fc[run] = e
fc["f3_lines_M0p_r1"] = r1_checks["f3_lines_near_edges"].get("M0p")
fc["f3_lines_M0p_r2"] = f3_lines.get("M0p")
finding_c = dict(fc, resolved=bool(not f3_lines.get("M0p")))


# ------------------------------------------------------------------------------------------------- (d) the planter against the basket
def basket_vs_pot(run, fid):
    m = MK[(run, fid)]
    if not m or not m["basket"].any() or not m["pot"].any():
        return None
    bk, pt = m["basket"], m["pot"]
    cols = np.nonzero(bk.any(0) & pt.any(0))[0]
    bt = int(np.nonzero(bk.any(1))[0].min())               # the basket's top silhouette row
    ptop = int(np.nonzero(pt.any(1))[0].min())             # the pot's top silhouette row (the rim's far edge)
    pcols = np.nonzero(pt.any(0))[0]
    bcols = np.nonzero(bk.any(0))[0]
    # the pot's full width (projected) and how much of it the basket covers
    g = GEO[run]
    pu = [P(CAMS[fid], *q)[0] for q in circ(*g["pot_c"], g["pot_r"], g["pot_h"])]
    pot_u0, pot_u1 = px_u(min(pu)), px_u(max(pu))
    cover = max(0.0, min(pot_u1, bcols.max() + 1) - max(pot_u0, bcols.min())) / max(pot_u1 - pot_u0, 1)
    dv = bt - ptop
    return dict(basket_top_v=round((bt - CY) / CH, 4), pot_rim_top_v=round((ptop - CY) / CH, 4), basket_top_minus_pot_rim_px=dv,
                basket_top_minus_pot_rim_frame_pct=fpct(abs(dv)), pot_rim_visible_above_basket_rows=max(0, dv),
                basket_covers_pot_width=round(cover, 3), pot_visible_px=int(pt.sum()), shared_columns=int(cols.size),
                pot_u_span=[round((pot_u0 - CX) / CW, 4), round((pot_u1 - CX) / CW, 4)],
                basket_u_span=[round((bcols.min() - CX) / CW, 4), round((bcols.max() + 1 - CX) / CW, 4)],
                reads=("ONE LINE: the pot rim and the basket top within 0.5 % of the frame (<= 11 px)" if abs(dv) <= 0.005 * CH else
                       "near one line (0.5-1 % of the frame): a tangent by the F-rules" if abs(dv) < 0.01 * CH else
                       "two lines (>= 1 % apart)"))


def proj_basket_vs_pot(fid, g, b):
    cam = CAMS[fid]
    bt = min(P(cam, *q)[1] for q in circ(*b["c"], b["r"], b["h"]))
    pt = pot_rim_top_v(cam, g)
    bu = [P(cam, *q)[0] for q in circ(*b["c"], b["r"], b["h"]) + circ(*b["c"], b["r"], 0.0)]
    pu = [P(cam, *q)[0] for q in circ(*g["pot_c"], g["pot_r"], g["pot_h"])]
    cover = max(0.0, min(max(pu), max(bu)) - max(min(pu), min(bu))) / (max(pu) - min(pu))
    dv = (bt - pt) * CH
    return dict(basket_top_v=round(bt, 4), pot_rim_top_v=round(pt, 4), basket_top_minus_pot_rim_px=round(dv, 1),
                basket_u_span=[round(min(bu), 4), round(max(bu), 4)], pot_u_span=[round(min(pu), 4), round(max(pu), 4)],
                basket_covers_pot_width=round(cover, 3),
                reads=("ONE LINE (<= 0.5 %)" if abs(dv) <= 0.005 * CH else "near one line (0.5-1 %)" if abs(dv) < 0.01 * CH else "two lines (>= 1 % apart)"))


finding_d = dict(M0=dict(r1_clay=basket_vs_pot("r1", "M0"), r2_clay=basket_vs_pot("r2", "M0"),
                         r2_projection=proj_basket_vs_pot("M0", G, BASKET),
                         lever_basket_minus155_080_projection_not_applied=proj_basket_vs_pot("M0", G, LEVER)),
                 M0p=dict(r2_clay=basket_vs_pot("r2", "M0p"), r2_projection=proj_basket_vs_pot("M0p", G, BASKET),
                          lever_projection_not_applied=proj_basket_vs_pot("M0p", G, LEVER)),
                 lever_plan=dict(basket=list(LEVER["c"]), to_bench_front_x_m=round((LEVER["c"][0] - LEVER["r"]) - G["bench_x1"], 3),
                                 to_pot_m=round(math.hypot(LEVER["c"][0] - G["pot_c"][0], LEVER["c"][1] - G["pot_c"][1]) - LEVER["r"] - G["pot_r"], 3),
                                 to_armchair_note="the armchair's nearest corner is near X -1.72, Y ~2.2-3.2: far in Y"),
                 note="the lever is projected only (render-agent does not apply it); the projection's error is r2_projection against r2_clay")
_d = finding_d["M0"]["r2_clay"]
finding_d["reads_as_one_line_in_M0"] = None if _d is None else _d["reads"].startswith("ONE LINE")

# ------------------------------------------------------------------------------------------------- (e) new: the pot against the bench's end
def pot_vs_bench_end(run, fid):
    m = MK[(run, fid)]
    g = GEO[run]
    cam = CAMS[fid]
    edge_u = P(cam, g["bench_x1"], 0.75, 0.2)[0]
    pu = min(P(cam, *q)[0] for q in circ(*g["pot_c"], g["pot_r"], 0.2))
    out = dict(bench_end_edge=dict(xy=[g["bench_x1"], 0.75], u=round(edge_u, 4)), pot_left_u_projection=round(pu, 4),
               pot_left_minus_bench_edge_px_projection=round((pu - edge_u) * CW, 1))
    if m is not None and m["pot"].any() and m["bench"].any():
        rows_ = [r for r in range(m["idx"].shape[0]) if m["pot"][r].any() and m["bench"][r].any()]
        dl = []
        for r in rows_:
            pl = int(np.nonzero(m["pot"][r])[0].min())
            br = np.nonzero(m["bench"][r, :pl])[0]
            if br.size:
                dl.append(pl - int(br.max()) - 1)
        if dl:
            out["clay_rows"] = len(dl)
            out["clay_pot_left_minus_bench_right_px"] = dict(min=int(min(dl)), median=float(np.median(dl)), max=int(max(dl)))
    d = out["pot_left_minus_bench_edge_px_projection"]
    out["reads"] = ("thin overlap (the bench hides < 0.03 of the frame of the pot)" if -0.03 * CW < d < 0 else
                    "kissing contours (< 0.02 apart)" if 0 <= d < 0.02 * CW else "clear (>= 0.02)" if d >= 0.02 * CW else "decisive overlap")
    return out


def pot_shift_for(fid, target):
    """the +X shift of the pot (r2) that puts its left silhouette `target` (frame u) right of the bench end's edge"""
    cam = CAMS[fid]
    edge_u = P(cam, G["bench_x1"], 0.75, 0.2)[0]
    for k in range(0, 301):
        dx = k / 1000
        pu = min(P(cam, *q)[0] for q in circ(G["pot_c"][0] + dx, G["pot_c"][1], G["pot_r"], 0.2))
        if pu - edge_u >= target:
            return round(dx, 3)
    return None


def pot_shift_overlap(fid, frac):
    """the -X shift of the pot (r2) that hides `frac` of its width behind the bench end"""
    cam = CAMS[fid]
    edge_u = P(cam, G["bench_x1"], 0.75, 0.2)[0]
    for k in range(0, 301):
        dx = -k / 1000
        us = [P(cam, *q)[0] for q in circ(G["pot_c"][0] + dx, G["pot_c"][1], G["pot_r"], 0.2)]
        if (edge_u - min(us)) / (max(us) - min(us)) >= frac:
            return round(dx, 3)
    return None


finding_e = dict(M0=dict(r1=pot_vs_bench_end("r1", "M0"), r2=pot_vs_bench_end("r2", "M0")),
                 levers_for_the_designer_not_applied=dict(
                     pot_plus_x_for_a_0_02_gap_m=pot_shift_for("M0", 0.02),
                     pot_minus_x_for_one_third_hidden_by_the_bench_m=pot_shift_overlap("M0", 1 / 3),
                     note="WMC4 (bench to -1.98) and WMC2 (pot to -1.95, 0.42) together put the pot's left silhouette on the bench end's edge in M0; "
                          "the basket in front hides the pot's right part, so the visible pot is the sliver between the bench end and the basket"))


def lever_search():
    """pot moves within the designer's 0.10 m (keeping the WMC2 crown limits X >= -2.23, Y <= 0.70), and the bench edge alone"""
    cam = CAMS["M0"]
    edge = P(cam, G["bench_x1"], 0.75, 0.2)[0]
    best = None
    for i in range(-10, 11):
        for j in range(-10, 11):
            dx, dy = i / 100, j / 100
            c = (G["pot_c"][0] + dx, G["pot_c"][1] + dy)
            if math.hypot(dx, dy) > 0.10 + 1e-9 or c[0] - G["crown_r"] < -2.23 - 1e-9 or c[1] + G["crown_r"] > 0.70 + 1e-9:
                continue
            us = [P(cam, *q)[0] for q in circ(*c, G["pot_r"], 0.2)]
            gap = (min(us) - edge) * CW
            hid = (edge - min(us)) / (max(us) - min(us))
            if best is None or max(gap / (0.02 * CW), hid * 3) > max(best[2] / (0.02 * CW), best[3] * 3):
                best = (dx, dy, round(gap, 1), round(hid, 3))
    us = [P(cam, *q)[0] for q in circ(*G["pot_c"], G["pot_r"], 0.2)]
    bench = {}
    for k in range(-220, -179):
        xb = k / 100
        e = P(cam, xb, 0.75, 0.2)[0]
        bench[str(xb)] = dict(gap_px=round((min(us) - e) * CW, 1), hidden=round((e - min(us)) / (max(us) - min(us)), 3))
    need_gap = max([float(x) for x, v in bench.items() if v["gap_px"] >= 0.02 * CW], default=None)
    need_hide = min([float(x) for x, v in bench.items() if v["hidden"] >= 1 / 3], default=None)
    return dict(best_pot_move_within_0_10=dict(dx=best[0], dy=best[1], gap_px=best[2], hidden=best[3],
                                                reads="does not reach a 0.02 gap or a third hidden" if best[2] < 0.02 * CW and best[3] < 1 / 3 else "solves it"),
                bench_edge_alone=dict(x_for_a_0_02_gap=need_gap, x_for_a_third_hidden=need_hide))


finding_e["levers_for_the_designer_not_applied"].update(lever_search())
finding_e["M0"]["third_line"] = dict(
    rounded_corner_left_tangent_u=round(P(M0, -2.30, G["corner_r"], 1.0)[0], 4),
    note="the start of the R 0.30 curve on the window wall (Y 0.30) projects onto the same vertical as the bench end's edge and the pot's left side "
         "(all within ~0.001 u, ~4 px): three edges on one line in M0 (the curve's start is a soft shading edge in the clay)")
_t = [t for t in (sc.get("M0", {}).get("F3_tangents", {}) or {}).get("object_object_tangents", []) if "curtains" in t.get("a", "") + t.get("b", "")]
finding_f = dict(M0=dict(render_selfcheck=_t, overlap_px=[round(t.get("overlap_thickness", 0) * CW, 1) for t in _t],
                         note="new in r2: WMC1 widens the front stack from 0.15 to 0.30 (its edge u 0.019 -> 0.053), so the armchair's left contour "
                              "now overlaps the stack thinly (< 0.03, 5 % of the stack); in r1 the stack's edge was at u 0.019 against the armchair's left 0.023"))

# ------------------------------------------------------------------------------------------------- the glazing and the stack (WMC1)
fg = {}
for fid in CAMS:
    m = MK[("r2", fid)]
    if not m:
        continue
    op = opening_mask(fid, m["idx"].shape)
    if not op.any():
        fg[fid] = dict(note="the glazing is outside this frame")
        continue
    fg[fid] = dict(opening_polygon_px=int(op.sum()), front_stack_over_the_opening_px=int((m["curtains"] & op).sum()),
                   front_stack_over_the_opening_pct=round(100 * (m["curtains"] & op).sum() / op.sum(), 2),
                   r1_front_stack_over_the_opening_pct=r1f.get(fid, {}).get("front-stack", {}).get("over_the_opening_pct_of_opening"),
                   back_jamb_line_u=round(back_jamb_u(fid), 4))
plan_clear = dict(sconce_plate_to_stack_m=round(3.17 - 3.00, 2), sconce_plate_to_glazing_edge_m=round(3.17 - 2.85, 2), rule=">= 0.10",
                  armchair_to_bench_m=round(min(p[0] for p in rrect(*ARM, 0.72, 0.78, 25, 0, 0)) - G["bench_x1"], 3),
                  pot_to_bench_end_y_m=round(0.75 - (G["pot_c"][1] + G["pot_r"]), 3),
                  basket_to_bench_front_x_m=round((BASKET["c"][0] - BASKET["r"]) - G["bench_x1"], 3),
                  vase_on_bench=dict(base=[-2.42, 1.35, 0.45], bench_x=[-2.30, G["bench_x1"]], note="the vase stands on the slab in the reveal (X -2.50..-2.34); unaffected"))

f3 = {fid: sc.get(fid, {}).get("F3_tangents") for fid in CAMS}
out = dict(date="2026-11-07", tokens=0, script="assets/blockout/house/framing/warm-modern-r2/clay_checks_wm_r2.py",
           inputs=dict(plan=plan["version"][:60], slots=slots["version"], selfcheck="assets/blockout/house/framing/warm-modern-r2/selfcheck-render-A.json",
                       r1="assets/blockout/house/framing/warm-modern-r1/clay-checks-2026-11-07.json"),
           decisions="WMC1-WMC5 (house plan 1.3.2 section 0א; slots 1.9.1)",
           cameras={k: dict(loc=v["loc"], yaw=v["yaw_deg_left"], u0=v["u0"], v0=v["v0"]) for k, v in CAMS.items()},
           findings=dict(a_planter_vs_curtain_stack=finding_a, b_crown=finding_b, c_M0p_left_edge=finding_c, d_planter_vs_basket=finding_d,
                         e_new_pot_vs_bench_end=finding_e, f_new_armchair_vs_front_stack=finding_f),
           glazing_and_stack=fg, plan_clearances=plan_clear, vase_vs_armchair_M0=check_vase,
           slot_boxes=rows, named_lines=lines, architecture_clay_boxes=arch_clay, f3_lines_near_edges=f3_lines, f3_tangents=f3,
           contradictions=[f"{r['slot']}: {r['item']}" for r in rows if r["verdict"].startswith("CONTRADICTION")])
json.dump(out, open(os.path.join(HERE, "clay-checks-2026-11-07.json"), "w"), indent=1, ensure_ascii=False)

# ------------------------------------------------------------------------------------------------- overlays
os.makedirs(os.path.join(HERE, "overlays"), exist_ok=True)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
COL = {"glazing": (220, 40, 40), "mullion": (220, 120, 40), "bench": (40, 120, 220), "rounded": (40, 170, 90), "curtain": (160, 60, 200)}
paths = {"M0": "M0.png", "M0p": "poses/M0p.png", "M0x": "poses/M0x.png"}
for fid, rel in paths.items():
    p = os.path.join(HERE, rel)
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(im)
    for li, (k, (a, b)) in enumerate(LINES.items()):
        col = next((c for w, c in COL.items() if k.startswith(w)), (0, 0, 0))
        pts = [(px_u(u), px_v(v)) for u, v in seg(CAMS[fid], a, b)]
        pts = [q for q in pts if -500 < q[0] < im.width + 500 and -500 < q[1] < im.height + 500]
        if len(pts) > 1:
            d.line(pts, fill=col, width=4)
            inside = [q for q in pts if 20 < q[0] < im.width - 700 and 40 < q[1] < im.height - 40]
            if inside:
                q = inside[int(len(inside) * (0.12 + 0.76 * ((li * 5) % 13) / 12))]
                d.text((q[0] + 6, q[1] + 4), k, fill=col, font=font, stroke_width=3, stroke_fill=(255, 255, 255))
    if fid in ("M0", "M0p"):
        # the pot rim's far edge and the basket's top (finding d), and the lever's basket outline (projected, not applied)
        for g_, b_, col, lab in ((G, BASKET, (0, 0, 0), "basket top"), (G, LEVER, (0, 140, 160), "lever basket (-1.55, 0.80), not applied")):
            pts = [(px_u(P(CAMS[fid], *q)[0]), px_v(P(CAMS[fid], *q)[1])) for q in circ(*b_["c"], b_["r"], b_["h"])]
            d.line(pts + pts[:1], fill=col, width=3)
            d.text((max(q[0] for q in pts) + 8, min(q[1] for q in pts) - 30), lab, fill=col, font=font, stroke_width=3, stroke_fill=(255, 255, 255))
        pts = [(px_u(P(CAMS[fid], *q)[0]), px_v(P(CAMS[fid], *q)[1])) for q in circ(*G["pot_c"], G["pot_r"], G["pot_h"])]
        d.line(pts + pts[:1], fill=(200, 0, 120), width=3)
    d.rectangle((CX, CY, CX + CW, CY + CH), outline=(0, 0, 0), width=3)
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(os.path.join(HERE, "overlays", f"{fid}-lines.png"))

# ------------------------------------------------------------------------------------------------- the sheet: r1 against r2, per camera
fbold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
TW = 1280
tiles = []
for fid, rel in paths.items():
    a_, b_ = os.path.join(R1, rel), os.path.join(HERE, rel)
    if not (os.path.exists(a_) and os.path.exists(b_)):
        continue
    A = Image.open(a_).convert("RGB")
    B = Image.open(b_).convert("RGB")
    tiles.append((fid, A.resize((TW, int(A.height * TW / A.width)), Image.LANCZOS), B.resize((TW, int(B.height * TW / B.width)), Image.LANCZOS)))
if tiles:
    th = tiles[0][1].height
    sheet = Image.new("RGB", (2 * TW + 60, 80 + len(tiles) * (th + 60)), (250, 249, 247))
    d = ImageDraw.Draw(sheet)
    d.text((20, 20), "Warm-modern living-room clay per camera: r1 (left) against r2 with WMC1-WMC5 (right). 0 tokens, clay only.", fill=(0, 0, 0), font=fbold)
    y = 80
    for fid, A, B in tiles:
        d.text((20, y), f"{fid}  warm modern r1", fill=(0, 0, 0), font=font)
        d.text((40 + TW, y), f"{fid}  warm modern r2", fill=(0, 0, 0), font=font)
        sheet.paste(A, (20, y + 34))
        sheet.paste(B, (40 + TW, y + 34))
        y += th + 60
    sheet.save(os.path.join(HERE, "warm-modern-r1-vs-r2.jpg"), quality=90)

print(json.dumps(dict(findings=out["findings"], glazing_and_stack=fg, vase=check_vase, f3_lines=f3_lines, contradictions=out["contradictions"]),
                 indent=1, ensure_ascii=False, default=str)[:9000])
for r in rows:
    print(f"{r['slot']:18s} {r['item'][:40]:40s} slots {r['slots_1_9_1']} proj {r['projection']} clay {r['clay']} -> {r['verdict']}")
