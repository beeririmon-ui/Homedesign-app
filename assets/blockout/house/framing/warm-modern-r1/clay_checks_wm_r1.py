#!/usr/bin/env python3
"""
Clay checks of the warm-modern living-room clay r1 (house plan 1.3.1 section 0א, slots 1.9 by_style.warm-modern, Bible warm-modern 1.0;
render-agent, 2026-11-07; briefs/render-warm-modern-clay-2026-11-07.md; 0 var2 tokens). The same named lines as round 5b
(clay_checks_r5b.py: the slot boxes, the armchair, the rug, the coffee table / sofa, the F3 tangents) plus the new ones: the glazing head and
jambs, the bench edge, the rounded corner and the curtain track; and the designer's two checks: (1) the vase on the bench against the top
of the armchair's back at M0 1.2 (gap in px and in % of the frame), (2) whether the curtain stacks and the planter clear the new glazing.
Reads framing/warm-modern-r1/selfcheck-render-A.json and the index passes the render kept in the scratchpad (wm-r1-idx/<frame>.npz);
writes clay-checks-2026-11-07.json, overlays/<frame>-lines.png and the sheet nordic-r5b-vs-warm-modern-r1.jpg.

  python3 -I clay_checks_wm_r1.py
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
R5B = os.path.join(HERE, "..", "round5b")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r1-idx"
plan = json.load(open(os.path.join(REPO, "docs", "house-plan.json")))
slots = json.load(open(os.path.join(REPO, "data", "slots", "living-room.json")))
wm_slots = slots["by_style"]["warm-modern"]
sc = json.load(open(os.path.join(HERE, "selfcheck-render-A.json")))["frames"]
CAMS = {c["id"]: c for c in plan["cameras"] if c["id"] in ("M0", "M0p", "M0x")}
CX, CY, CW, CH = 116, 65, 3840, 2160          # the 3 % overscan canvas 4072 x 2290 -> the 16:9 frame


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


def cyl(cx, cy, r, z0, z1, n=96):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z) for k in range(n) for z in (z0, z1)]


def rrect(cx, cy, w, dp, deg, z0, z1):
    a, out = math.radians(deg), []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = sx * w / 2, sy * dp / 2
            out += [(cx + lx * math.cos(a) - ly * math.sin(a), cy + lx * math.sin(a) + ly * math.cos(a), z) for z in (z0, z1)]
    return out


M0 = CAMS["M0"]
S = {s["id"]: s for s in slots["slots"]}
WS = wm_slots["slots"]


def slot_box(slot, part=None):
    m = (WS.get(slot, {}) or {}).get("m0_1_2") or S.get(slot, {}).get("m0_1_2", {})
    if part:
        return (m.get("parts") or {}).get(part)
    return m.get("box")


rows = []


def row(slot, label, proj, clay, part=None, note=""):
    sb = slot_box(slot, part)
    cl = lambda b: None if b is None else [min(max(x, 0.0), 1.0) for x in b]  # noqa: E731
    dp = None if (sb is None or proj is None) else round(max(abs(a - b) for a, b in zip(cl(sb), cl(proj))), 3)
    dc = None if (sb is None or clay is None) else round(max(abs(a - b) for a, b in zip(cl(sb), cl(clay))), 3)
    w = max([x for x in (dp, dc) if x is not None] or [0])
    clay = None if clay is None else [round(float(x), 4) for x in clay]
    rows.append(dict(slot=slot, item=label, slots_1_9=sb, projection=proj, clay=clay, max_diff_projection=dp, max_diff_clay=dc,
                     verdict=("not comparable" if (dp is None and dc is None) else "agrees (<= 0.02)" if w <= 0.02 else
                              "estimate off (0.02-0.05)" if w <= 0.05 else "CONTRADICTION (> 0.05)"), note=note))


ARM = (-1.23, 2.73)
row("sofa", "sofa 220 x 92 x 78", box(M0, corners(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)), clay_box("M0", "sofa 220x92x78 (fixed-product)"))
row("coffee-table", "coffee table 140 x 70 h 38", box(M0, corners(-0.50, 0.90, 1.37, 2.07, 0.0, 0.38)), clay_box("M0", "coffee table 140x70 h38 (fixed-product)"))
row("armchair", "armchair 72 x 78 h 70 (-1.23, 2.73) 25 deg, Nordic geometry (WM-F1)", box(M0, rrect(*ARM, 0.72, 0.78, 25, 0.0, 0.70)),
    clay_box("M0", "armchair 72x78 h70 (fixed-product)"))
row("pendant", "pendant shade 40 x 28, bottom 1.90", box(M0, cyl(0.20, 1.72, 0.20, 1.90, 2.18)), clay_box("M0", "living/pendant"))
row("vase", "vase on the bench, base (-2.42, 1.35, 0.45), body to 0.76, branches to 1.05", box(M0, cyl(-2.42, 1.35, 0.08, 0.45, 1.05)), clay_box("M0", "living/vase"),
    note="slots 1.9 box = the plan projection; the clay box includes the stems")
row("basket", "basket (-1.62, 0.78) d 35 h 39", box(M0, cyl(-1.62, 0.78, 0.175, 0.0, 0.39)), clay_box("M0", "living/basket"))
row("magazine-holder", "magazine holder (-0.54, 2.52) 32 x 22 x 40", box(M0, corners(-0.70, -0.38, 2.41, 2.63, 0.0, 0.40)), clay_box("M0", "living/magazine-holder"))
row("planter", "planter (-2.00, 0.47) d 38 + crown", None, clay_box("M0", "living/planter"))
row("curtains", "front stack Y 2.85-3.00", box(M0, corners(-2.28, -2.16, 2.85, 3.00, 0.0, 2.82)), None, part="front_stack",
    note="the clay box of living/curtains is both stacks: " + str(clay_box("M0", "living/curtains")))
row("curtains", "back stack Y 0.60-0.75", box(M0, corners(-2.28, -2.16, 0.60, 0.75, 0.0, 2.82)), None, part="back_stack")
row("rug", "rug 330 x 240", None, clay_box("M0", "living/rug"))
row("bowl", "bowl d 24 h 9 (0.68, 1.92)", box(M0, cyl(0.68, 1.92, 0.12, 0.38, 0.47)), clay_box("M0", "living/bowl"))
row("candle-holders", "candle holders", box(M0, corners(0.42, 0.65, 1.55, 1.75, 0.38, 0.63)), clay_box("M0", "living/candle-holders"))

# --- the named lines (projected through each camera; the clay boxes of the architecture items where they exist)
LINES = {
    "glazing_head": ((-2.30, 0.75, 2.70), (-2.30, 2.85, 2.70)),
    "glazing_sill_line": ((-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45)),
    "glazing_jamb_back_Y0.75": ((-2.30, 0.75, 0.45), (-2.30, 0.75, 2.70)),
    "glazing_jamb_front_Y2.85": ((-2.30, 2.85, 0.45), (-2.30, 2.85, 2.70)),
    "mullion_Y1.45_frame_plane": ((-2.65, 1.45, 0.45), (-2.65, 1.45, 2.70)),
    "mullion_Y2.15_frame_plane": ((-2.65, 2.15, 0.45), (-2.65, 2.15, 2.70)),
    "bench_front_top_edge_X-1.90": ((-1.90, 0.75, 0.45), (-1.90, 2.85, 0.45)),
    "bench_end_front_Y2.85": ((-1.90, 2.85, 0.0), (-1.90, 2.85, 0.45)),
    "bench_end_back_Y0.75": ((-1.90, 0.75, 0.0), (-1.90, 0.75, 0.45)),
    "rounded_corner_tangent_left_wall_Y0.15": ((-2.30, 0.15, 0.0), (-2.30, 0.15, 3.0)),
    "rounded_corner_tangent_back_wall_X-2.15": ((-2.15, 0.0, 0.0), (-2.15, 0.0, 3.0)),
    "curtain_track_band_edge_X-2.05_Z2.82": ((-2.05, 0.0, 2.82), (-2.05, 5.0, 2.82)),
    "curtain_track_slot_X-2.22_Z2.82": ((-2.22, 0.55, 2.82), (-2.22, 3.05, 2.82)),
}


def line_summary(cam, a, b):
    pts = [(u, v) for u, v in seg(cam, a, b, 2000) if -0.2 <= u <= 1.2 and -0.2 <= v <= 1.2]
    if not pts:
        return dict(in_frame=False)
    inn = [(u, v) for u, v in pts if 0 <= u <= 1 and 0 <= v <= 1]
    out = dict(in_frame=bool(inn), start_uv=[round(pts[0][0], 4), round(pts[0][1], 4)], end_uv=[round(pts[-1][0], 4), round(pts[-1][1], 4)])
    if inn:
        # F3 against the frame: the longest run of the line that stays within 0.01 of one edge (a line crossing an edge has a run ~0)
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
# lines that sit within 0.02 of a frame edge (F3, architecture)
f3_lines = {fid: [dict(line=k, **v["longest_run_within_0_01_of_an_edge"]) for k, v in L.items() if v.get("runs_along_an_edge")]
            for fid, L in lines.items()}


# --- the designer's check 1: the vase on the bench against the armchair back's top (M0)
import cv2  # noqa: E402

PLANTER_POT, PLANTER_CROWN = 35, 60      # build_alts: the pot keeps its slot pidx, the crown envelope is CROWN_IDX (r 0.40, Z 0.60-1.65)


def load_idx(fid):
    p = os.path.join(IDX, f"{fid}.npz")
    if not os.path.exists(p):
        return None, None
    z = np.load(p, allow_pickle=True)
    nm = json.load(open(os.path.join(IDX, f"{fid}-names.json")))
    return z["idx"], {int(k): v for k, v in nm["names"].items()}


def pidx_of(names, key):
    return [k for k, v in names.items() if v[0] == key]


def mask_of(idx, names, key):
    if key == "planter-pot":
        return idx == PLANTER_POT
    if key == "planter-crown":
        return idx == PLANTER_CROWN
    if key == "armchair":
        return idx == 3
    return np.isin(idx, pidx_of(names, key))


def min_dist(a, b):
    """the smallest Euclidean distance in px between two pixel sets (0 = they touch or overlap)"""
    if not a.any() or not b.any():
        return None
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[a].min())


def fpct(px):
    return None if px is None else round(100 * px / CH, 2)


check1 = {}
idx, names = load_idx("M0")
if idx is not None:
    vase = mask_of(idx, names, "living/vase")
    arm = mask_of(idx, names, "armchair")
    per = []
    for c in np.nonzero(vase.any(0))[0]:
        vb = int(np.nonzero(vase[:, c])[0].max())
        ar = np.nonzero(arm[:, c])[0]
        if ar.size:
            per.append((int(ar.min()) - vb - 1, int(c), vb, int(ar.min())))
    dmin = min_dist(vase, arm)
    ys, xs = np.nonzero(vase)
    ay, ax = np.nonzero(arm)
    # the armchair back (the upper part of the chair left of the arm rail): its top-right corner
    check1 = dict(vase_px=int(vase.sum()), vase_bbox_frame=[round((xs.min() - CX) / CW, 4), round((xs.max() + 1 - CX) / CW, 4), round((ys.min() - CY) / CH, 4), round((ys.max() + 1 - CY) / CH, 4)],
                  armchair_top_v_frame=round((ay.min() - CY) / CH, 4),
                  min_euclidean_gap_px=None if dmin is None else round(dmin, 1), min_euclidean_gap_frame_pct=fpct(dmin))
    if per:
        g = min(per)
        check1.update(columns_with_both=len(per), min_vertical_gap_px=g[0], at_frame_u=round((g[1] - CX) / CW, 4),
                      vase_foot_v=round((g[2] + 1 - CY) / CH, 4), armchair_top_below_v=round((g[3] - CY) / CH, 4), min_vertical_gap_frame_pct=fpct(g[0]))
    check1["reads"] = ("touching / overlapping" if (dmin is not None and dmin <= 1) else
                       "tangent (< 1 % of the frame)" if (dmin is not None and dmin < 0.01 * CH) else
                       "clear (>= 1 % of the frame)" if dmin is not None else "not both visible")
    check1["note"] = ("px of the 3840 x 2160 frame (the 3 % overscan canvas keeps the frame's pixel scale); vertical gap per column where both show "
                      "(the armchair's top pixel minus the vase's lowest pixel); Euclidean = the nearest pair of pixels of the two silhouettes")

# --- the designer's check 2: the stacks and the planter against the new glazing
CROWN_R, CROWN_Z = 0.40, (0.60, 1.65)
pc = (-2.00, 0.47)
stack_back = dict(x=(-2.28, -2.16), y=(0.60, 0.75))


def box_circle_gap(bx, by, c, r):
    nx = min(max(c[0], bx[0]), bx[1])
    ny = min(max(c[1], by[0]), by[1])
    return round(math.hypot(c[0] - nx, c[1] - ny) - r, 3)


plan_clear = dict(
    back_stack=dict(y=[0.60, 0.75], x=[-2.28, -2.16], to_opening_y=0.0, reads="flush with the back jamb (Y 0.75): beside the glazing, not over it"),
    front_stack=dict(y=[2.85, 3.00], x=[-2.28, -2.16], to_opening_y=0.0, reads="flush with the front jamb (Y 2.85)"),
    planter_pot=dict(c=list(pc), r=0.19, y_max=0.66, to_opening_y=0.09, to_bench_end_y=0.09, to_back_stack_m=box_circle_gap(stack_back["x"], stack_back["y"], pc, 0.19),
                     reads="clear"),
    planter_crown_envelope=dict(c=list(pc), r=CROWN_R, z=list(CROWN_Z), y_max=round(pc[1] + CROWN_R, 2), x_min=round(pc[0] - CROWN_R, 2),
                                over_the_opening_y=round(pc[1] + CROWN_R - 0.75, 2),
                                x_min_at_jamb_y_0_75=round(pc[0] - math.sqrt(CROWN_R ** 2 - (0.75 - pc[1]) ** 2), 3),
                                to_back_stack_m=box_circle_gap(stack_back["x"], stack_back["y"], pc, CROWN_R),
                                reads="NOT clear: the clay envelope (r 0.40, the Nordic planter's) reaches Y 0.87, 0.12 past the back jamb in front of the first "
                                      "glazing field (to 1.4 cm from the glass at Y 0.75), contains the whole back stack and passes 0.10 through the wall plane (X -2.40)"),
    sconce_plate=dict(y=3.17, to_glazing_edge=0.32, to_front_stack=0.17, rule=">= 0.10", reads="clear"))
check2 = dict(plan=plan_clear, frames={})


def opening_poly(cam):
    q = [(-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45), (-2.30, 2.85, 2.70), (-2.30, 0.75, 2.70)]
    return [P(cam, *p)[:2] for p in q]


for fid in CAMS:
    idx, names = load_idx(fid)
    if idx is None:
        continue
    Hc, Wc = idx.shape
    q3 = [(-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45), (-2.30, 2.85, 2.70), (-2.30, 0.75, 2.70)]
    behind = any(P(CAMS[fid], *q)[2] <= 0.05 for q in q3)     # a corner behind the camera: the opening is not in this view
    poly = [((u * CW + CX), (v * CH + CY)) for u, v in opening_poly(CAMS[fid])]
    m = Image.new("L", (Wc, Hc), 0)
    if not behind:
        ImageDraw.Draw(m).polygon(poly, fill=1)
    op = np.asarray(m).astype(bool)
    glaz = np.isin(idx, [0, 4, 14])                       # the glass / sky, the frames and the reveal lining (shell idx window 4, lining 14)
    cur = mask_of(idx, names, "living/curtains")
    n, lab, st, _ = cv2.connectedComponentsWithStats(cur.astype(np.uint8))
    comps = sorted([i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 500], key=lambda i: st[i, cv2.CC_STAT_LEFT])
    parts = {}
    if not op.any():
        parts["curtains"] = cur        # the glazing is out of frame here: the curtain pixels are not split into stacks
    elif len(comps) >= 2:
        parts["front-stack"] = lab == comps[0]
        parts["back-stack"] = np.isin(lab, comps[1:])
    elif len(comps) == 1:
        # one stack in view: the front stack sits at the far left (Y 2.85-3.00 is nearer the camera)
        parts["front-stack" if st[comps[0], cv2.CC_STAT_LEFT] < 0.15 * Wc else "back-stack"] = lab == comps[0]
    parts["planter-pot"] = mask_of(idx, names, "planter-pot")
    parts["planter-crown"] = mask_of(idx, names, "planter-crown")
    parts["basket"] = mask_of(idx, names, "living/basket")
    parts["vase"] = mask_of(idx, names, "living/vase")
    res = dict(opening_polygon_px=int(op.sum()), glazing_px_visible=int((glaz & op).sum()))
    if not op.any():
        res["note"] = "the glazing (X -2.30, Y 0.75-2.85) is outside this frame: nothing in it can cover the glazing; only the F3 gaps below apply"
    for k, msk in parts.items():
        if not msk.any():
            res[k] = dict(px=0)
            continue
        ys, xs = np.nonzero(msk)
        res[k] = dict(px=int(msk.sum()), bbox_frame=[round((xs.min() - CX) / CW, 4), round((xs.max() + 1 - CX) / CW, 4), round((ys.min() - CY) / CH, 4), round((ys.max() + 1 - CY) / CH, 4)],
                      over_the_opening_px=int((msk & op).sum()), over_the_opening_pct_of_opening=round(100 * (msk & op).sum() / max(op.sum(), 1), 2),
                      gap_to_visible_glazing_px=(None if min_dist(msk, glaz) is None else round(min_dist(msk, glaz), 1)))
    if ("back-stack" in parts or "curtains" in parts) and parts["planter-pot"].any():
        bs_, pt, cr = parts.get("back-stack", parts.get("curtains")), parts["planter-pot"], parts["planter-crown"]
        g = min_dist(pt, bs_)
        res["pot_vs_back_stack_gap_px"] = None if g is None else round(g, 1)
        res["pot_vs_back_stack_gap_frame_u"] = None if g is None else round(g / CW, 4)
        # the crown's outline against the stack's outline, row by row (a shared edge = an F3 tangent)
        rows_ = [r for r in range(Hc) if cr[r].any() and bs_[r].any()]
        if rows_:
            dl = [int(np.nonzero(cr[r])[0].min()) - int(np.nonzero(bs_[r])[0].min()) for r in rows_]
            res["crown_left_edge_minus_back_stack_left_edge_px"] = dict(rows=len(rows_), min=int(min(dl)), median=float(np.median(dl)), max=int(max(dl)),
                                                                        rows_within_4px=int(sum(abs(x) <= 4 for x in dl)))
        # the crown and the stack overlap in the frame? (the nearer one occludes; measure the shared outline span)
        res["crown_and_back_stack_touch"] = bool(min_dist(cr, bs_) is not None and min_dist(cr, bs_) <= 1.5)
    check2["frames"][fid] = res

# the slot rows the selfcheck boxes cannot give: the planter with its crown, and each curtain stack, from the M0 index pass
_m0 = check2["frames"].get("M0", {})


def _union(*bb):
    bb = [b for b in bb if b]
    return None if not bb else [min(b[0] for b in bb), max(b[1] for b in bb), min(b[2] for b in bb), max(b[3] for b in bb)]


rows[:] = [r for r in rows if r["slot"] not in ("planter", "curtains")]
row("planter", "planter (-2.00, 0.47): pot d 38 + crown envelope r 0.40 (Z 0.60-1.65)", None,
    _union(_m0.get("planter-pot", {}).get("bbox_frame"), _m0.get("planter-crown", {}).get("bbox_frame")),
    note="clay = the index pass (pot pidx 35 + crown pidx 60); the selfcheck box of living/planter is the pot alone: " + str(clay_box("M0", "living/planter")))
row("curtains", "front stack Y 2.85-3.00", box(M0, corners(-2.28, -2.16, 2.85, 3.00, 0.0, 2.82)), _m0.get("front-stack", {}).get("bbox_frame"), part="front_stack",
    note="clay = the index pass; the stack runs off the frame's left edge")
row("curtains", "back stack Y 0.60-0.75", box(M0, corners(-2.28, -2.16, 0.60, 0.75, 0.0, 2.82)), _m0.get("back-stack", {}).get("bbox_frame"), part="back_stack",
    note="clay = the visible part: the bench end (Y 0.75) hides it below the bench top, so its bottom is not compared")
_r = rows[-1]
if _r["clay"]:
    _r["max_diff_clay"] = round(max(abs(a - b) for a, b in zip(_r["slots_1_9"][:3], _r["clay"][:3])), 3)
    _w = max(_r["max_diff_clay"], _r["max_diff_projection"] or 0)
    _r["verdict"] = ("agrees (<= 0.02)" if _w <= 0.02 else "estimate off (0.02-0.05)" if _w <= 0.05 else "CONTRADICTION (> 0.05)") + " (left, right, top; the bottom is hidden)"

# --- F3 of the clays (as reported by the render's own tangents)
f3 = {fid: sc.get(fid, {}).get("F3_tangents") for fid in CAMS}
f3_new = {fid: [t for t in (sc.get(fid, {}).get("F3_tangents", {}) or {}).get("object_object_tangents", [])
                if any(w in (t.get("a", "") + t.get("b", "")) for w in ("bench", "corner", "track", "vase", "basket", "planter", "curtains", "magazine"))]
          for fid in CAMS}

out = dict(date="2026-11-07", tokens=0, script="assets/blockout/house/framing/warm-modern-r1/clay_checks_wm_r1.py",
           inputs=dict(plan=plan["version"][:60], slots=slots["version"], selfcheck="assets/blockout/house/framing/warm-modern-r1/selfcheck-render-A.json"),
           cameras={k: dict(loc=v["loc"], yaw=v["yaw_deg_left"], u0=v["u0"], v0=v["v0"]) for k, v in CAMS.items()},
           slot_boxes=rows, named_lines=lines, architecture_clay_boxes=arch_clay, f3_lines_near_edges=f3_lines,
           check1_vase_vs_armchair_back_M0=check1, check2_stacks_planter_vs_glazing=check2, f3_tangents=f3, f3_new_items=f3_new,
           contradictions=[f"{r['slot']}: {r['item']}" for r in rows if r["verdict"].startswith("CONTRADICTION")])
json.dump(out, open(os.path.join(HERE, "clay-checks-2026-11-07.json"), "w"), indent=1, ensure_ascii=False)

# --- overlays: the named lines on the warm-modern clays
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
        pts = [(u * CW + CX, v * CH + CY) for u, v in seg(CAMS[fid], a, b)]
        pts = [q for q in pts if -500 < q[0] < im.width + 500 and -500 < q[1] < im.height + 500]
        if len(pts) > 1:
            d.line(pts, fill=col, width=4)
            inside = [q for q in pts if 20 < q[0] < im.width - 700 and 40 < q[1] < im.height - 40]
            if inside:
                q = inside[int(len(inside) * (0.12 + 0.76 * ((li * 5) % 13) / 12))]   # spread the labels along their lines
                d.text((q[0] + 6, q[1] + 4), k, fill=col, font=font, stroke_width=3, stroke_fill=(255, 255, 255))
    d.rectangle((CX, CY, CX + CW, CY + CH), outline=(0, 0, 0), width=3)
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(os.path.join(HERE, "overlays", f"{fid}-lines.png"))

# --- the sheet: Nordic round 5b against warm modern r1, per camera
fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
TW = 1280
tiles = []
for fid, rel in paths.items():
    a_ = os.path.join(R5B, rel)
    b_ = os.path.join(HERE, rel)
    if not (os.path.exists(a_) and os.path.exists(b_)):
        continue
    A = Image.open(a_).convert("RGB")
    B = Image.open(b_).convert("RGB")
    A = A.resize((TW, int(A.height * TW / A.width)), Image.LANCZOS)
    B = B.resize((TW, int(B.height * TW / B.width)), Image.LANCZOS)
    tiles.append((fid, A, B))
if tiles:
    th = tiles[0][1].height
    sheet = Image.new("RGB", (2 * TW + 60, 80 + len(tiles) * (th + 60)), (250, 249, 247))
    d = ImageDraw.Draw(sheet)
    d.text((20, 20), "Living-room clay per camera: Nordic round 5b (left) against warm modern r1 (right). 0 tokens, clay only.", fill=(0, 0, 0), font=fb)
    y = 80
    for fid, A, B in tiles:
        d.text((20, y), f"{fid}  Nordic r5b", fill=(0, 0, 0), font=font)
        d.text((40 + TW, y), f"{fid}  warm modern r1", fill=(0, 0, 0), font=font)
        sheet.paste(A, (20, y + 34))
        sheet.paste(B, (40 + TW, y + 34))
        y += th + 60
    sheet.save(os.path.join(HERE, "nordic-r5b-vs-warm-modern-r1.jpg"), quality=90)
print(json.dumps(dict(check1=check1, check2=check2, f3_lines=f3_lines, contradictions=out["contradictions"]), indent=1)[:4000])
for r in rows:
    print(f"{r['slot']:15s} {r['item'][:40]:40s} slots {r['slots_1_9']} proj {r['projection']} clay {r['clay']} -> {r['verdict']}")
