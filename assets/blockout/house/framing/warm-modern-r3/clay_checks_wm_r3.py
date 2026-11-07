#!/usr/bin/env python3
"""
Clay checks of the warm-modern living-room clay r3 (house plan 1.3.3 section 0א WMC6-WMC8, slots 1.9.2 by_style.warm-modern;
render-agent, 2026-11-07; 0 var2 tokens). The same shape as r2 (clay_checks_wm_r2.py), with the r3 numbers, and the designer's checks,
each r2 -> r3 in px:
  WMC6 the bench from Y 1.00: its end corner in M0 (expected u ~0.320, ~0.024 from the pot) and in M0p (expected out of the frame);
  WMC7 the front stack at Y 2.65-2.95: its overlap with the armchair (expected ~0.038), the sconce plate 0.22 from it;
  WMC8 the magazine holder (-0.47, 2.59) at the gunmetal leather strap's size 35 x 19 x 27.5: gaps to the armchair (~0.021), the basket
       (~0.024) and the coffee table's front-left corner (~0.023);
  accepted as they are (numbers only): the arc's start next to the pot, the pot rim against the basket top.
Reads framing/warm-modern-r3/selfcheck-render-A.json and the index passes in the scratchpad (wm-r3-idx/, and wm-r2-idx/ for r2);
writes clay-checks-2026-11-07.json, overlays/<frame>-lines.png and the sheet warm-modern-r2-vs-r3.jpg.

  python3 -P clay_checks_wm_r3.py
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
R1 = os.path.join(HERE, "..", "warm-modern-r2")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IDX = {"r3": os.path.join(SCR, "wm-r3-idx"), "r2": os.path.join(SCR, "wm-r2-idx")}
plan = json.load(open(os.path.join(REPO, "docs", "house-plan.json")))
slots = json.load(open(os.path.join(REPO, "data", "slots", "living-room.json")))
wm_slots = slots["by_style"]["warm-modern"]
sc = json.load(open(os.path.join(HERE, "selfcheck-render-A.json")))["frames"]
r2_checks = json.load(open(os.path.join(R1, "clay-checks-2026-11-07.json")))
CAMS = {c["id"]: c for c in plan["cameras"] if c["id"] in ("M0", "M0p", "M0x")}
CX, CY, CW, CH = 116, 65, 3840, 2160          # the 3 % overscan canvas 4072 x 2290 -> the 16:9 frame
PLANTER_POT, PLANTER_CROWN, ARMCHAIR = 35, 60, 3

# r2 geometry (house plan 1.3.2 / slots 1.9.1)
GEO = dict(r2=dict(pot_c=(-1.95, 0.42), pot_r=0.21, pot_h=0.355, crown_r=0.28, crown_z=(0.70, 1.65), bench_x1=-1.98, bench_y0=0.75,
                   corner_r=0.30, stack_y=(2.70, 3.00), holder=dict(c=(-0.54, 2.52), w=0.32, d=0.22, h=0.40)),
           r3=dict(pot_c=(-1.95, 0.42), pot_r=0.21, pot_h=0.355, crown_r=0.28, crown_z=(0.70, 1.65), bench_x1=-1.98, bench_y0=1.00,
                   corner_r=0.30, stack_y=(2.65, 2.95), holder=dict(c=(-0.47, 2.59), w=0.35, d=0.19, h=0.275)))
G = GEO["r3"]
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


MK = {(run, fid): masks(run, fid) for run in ("r2", "r3") for fid in CAMS}


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


m2 = MK[("r3", "M0")]
ARM = (-1.23, 2.73)
row("sofa", "sofa 220 x 92 x 78", box(M0, corners(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)), clay_box("M0", "sofa 220x92x78 (fixed-product)"))
row("coffee-table", "coffee table 140 x 70 h 38", box(M0, corners(-0.50, 0.90, 1.37, 2.07, 0.0, 0.38)), clay_box("M0", "coffee table 140x70 h38 (fixed-product)"))
row("armchair", "armchair 72 x 78 h 70 (-1.23, 2.73) 25 deg, Nordic geometry (WM-F1)", box(M0, rrect(*ARM, 0.72, 0.78, 25, 0.0, 0.70)),
    clay_box("M0", "armchair 72x78 h70 (fixed-product)"))
row("pendant", "pendant shade 40 x 28, bottom 1.90", box(M0, cyl(0.20, 1.72, 0.20, 1.90, 2.18)), clay_box("M0", "living/pendant"))
row("vase", "vase on the bench, base (-2.42, 1.35, 0.45), body to 0.76, branches to 1.05", box(M0, cyl(-2.42, 1.35, 0.08, 0.45, 1.05)), clay_box("M0", "living/vase"))
row("basket", "basket (-1.62, 0.78) d 35 h 39 (unchanged; lever not applied)", box(M0, cyl(*BASKET["c"], BASKET["r"], 0.0, BASKET["h"])), clay_box("M0", "living/basket"))
row("magazine-holder", "magazine holder (-0.47, 2.59) 35 x 19 x 27.5 (gunmetal leather strap, WMC8)", box(M0, corners(-0.645, -0.295, 2.495, 2.685, 0.0, 0.275)),
    clay_box("M0", "living/magazine-holder"))
row("planter", "planter (-1.95, 0.42): pot d 42 x 35.5 + olive crown r 0.28 Z 0.70-1.65 (WMC2)",
    box(M0, cyl(*G["pot_c"], G["pot_r"], 0.0, G["pot_h"]) + ellip(*G["pot_c"], G["crown_r"], *G["crown_z"])), bbox_frame(m2["planter"]) if m2 else None,
    note="clay = the index pass (pot + trunk pidx 35, crown pidx 60)")
row("planter", "the pot alone, d 42 x 35.5", box(M0, cyl(*G["pot_c"], G["pot_r"], 0.0, G["pot_h"])), bbox_frame(m2["pot"]) if m2 else None, part="pot",
    note="clay = the visible pot (the basket in front hides most of it, so its left / right are the visible part)")
row("curtains", "one front stack Y 2.65-2.95 (WMC7)", box(M0, corners(-2.28, -2.16, 2.65, 2.95, 0.005, 2.86)), bbox_frame(m2["curtains"]) if m2 else None,
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
    "bench_front_top_edge_X-1.98": ((-1.98, 1.00, 0.45), (-1.98, 2.85, 0.45)),
    "bench_end_front_Y2.85": ((-1.98, 2.85, 0.0), (-1.98, 2.85, 0.45)),
    "bench_end_back_Y1.00": ((-1.98, 1.00, 0.0), (-1.98, 1.00, 0.45)),
    "bench_end_back_top_edge_Y1.00": ((-2.30, 1.00, 0.45), (-1.98, 1.00, 0.45)),
    "rounded_corner_tangent_left_wall_Y0.30": ((-2.30, 0.30, 0.0), (-2.30, 0.30, 2.82)),
    "rounded_corner_tangent_back_wall_X-2.00": ((-2.00, 0.0, 0.0), (-2.00, 0.0, 3.0)),
    "curtain_band_edge_X-2.05_Z2.82": ((-2.05, 0.0, 2.82), (-2.05, YF, 2.82)),
    "curtain_slot_edge_X-2.26_Z2.82": ((-2.26, 0.15, 2.82), (-2.26, YF, 2.82)),
    "curtain_slot_edge_X-2.18_Z2.82": ((-2.18, 0.06, 2.82), (-2.18, YF, 2.82)),
    "curtain_track_X-2.22_Z2.86": ((-2.22, 0.70, 2.86), (-2.22, 3.00, 2.86)),
    "curtain_stack_back_edge_Y2.65": ((-2.16, 2.65, 0.005), (-2.16, 2.65, 2.82)),
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

# ------------------------------------------------------------------------------------------------- the vase against the armchair (as r2)
check_vase = {}
if m2:
    dmin = min_dist(m2["vase"], m2["armchair"])
    check_vase = dict(min_euclidean_gap_px=dmin, min_euclidean_gap_frame_pct=fpct(dmin),
                      reads="clear (>= 1 % of the frame)" if dmin and dmin >= 0.01 * CH else "tangent / touching",
                      r2=r2_checks.get("vase_vs_armchair_M0", {}).get("min_euclidean_gap_px"))


def vline_u(cam, X, Y):
    return P(cam, X, Y, 1.0)[0]


def gap_pair(run, fid, ka, kb):
    m = MK[(run, fid)]
    if not m or not m[ka].any() or not m[kb].any():
        return None
    d = min_dist(m[ka], m[kb])
    return dict(px=d, frame_u=None if d is None else round(d / CW, 4))


def holder_mask(run, fid):
    m = MK[(run, fid)]
    return None if not m else np.isin(m["idx"], pidx_of(m["names"], "living/magazine-holder"))


for run in ("r2", "r3"):
    for fid in CAMS:
        m = MK[(run, fid)]
        if m:
            m["holder"] = holder_mask(run, fid)
            m["table"] = m["idx"] == 2


# WMC6: the bench's end corner against the pot
def bench_vs_pot(run, fid):
    g = GEO[run]
    cam = CAMS[fid]
    m = MK[(run, fid)]
    edge_u = P(cam, g["bench_x1"], g["bench_y0"], 0.2)[0]
    pu = min(P(cam, *q)[0] for q in circ(*g["pot_c"], g["pot_r"], 0.2))
    out = dict(bench_end_corner=dict(xy=[g["bench_x1"], g["bench_y0"]], u=round(edge_u, 4), px_from_left_edge=round(edge_u * CW, 1)),
               pot_left_u=round(pu, 4), pot_left_minus_bench_corner_projection=dict(px=round((pu - edge_u) * CW, 1), frame_u=round(pu - edge_u, 4)))
    if m is not None:
        out["bench_px_in_frame"] = int(m["bench"][:, CX:CX + CW].sum())
        if m["pot"].any() and m["bench"].any():
            rows_ = [r for r in range(m["idx"].shape[0]) if m["pot"][r].any() and m["bench"][r].any()]
            dl = []
            for r in rows_:
                pl = int(np.nonzero(m["pot"][r])[0].min())
                br = np.nonzero(m["bench"][r, :pl])[0]
                if br.size:
                    dl.append(pl - int(br.max()) - 1)
            out["clay_pot_left_minus_bench_right_px"] = dict(rows=len(dl), min=int(min(dl)), median=float(np.median(dl))) if dl else None
            out["clay_min_euclidean_px"] = min_dist(m["pot"], m["bench"])
    return out


wmc6 = dict(M0=dict(r2=bench_vs_pot("r2", "M0"), r3=bench_vs_pot("r3", "M0")), M0p=dict(r2=bench_vs_pot("r2", "M0p"), r3=bench_vs_pot("r3", "M0p")),
            expected=dict(M0_corner_u=0.320, M0_gap_to_pot_u=0.024, M0p_corner_u=-0.045))
_w = wmc6["M0"]["r3"]
_g = (_w.get("clay_pot_left_minus_bench_right_px") or {}).get("median")
wmc6["resolved"] = bool(_g is not None and _g >= 0.02 * CW and wmc6["M0p"]["r3"]["bench_end_corner"]["u"] < 0)

# WMC7: the front stack against the armchair; the sconce plate; the glazing the stack covers
def stack_info(run):
    m = MK[(run, "M0")]
    t = [x for x in ((json.load(open(os.path.join(HERE if run == "r3" else R1, "selfcheck-render-A.json")))["frames"]["M0"].get("F3_tangents", {}) or {})
                     .get("object_object_tangents", [])) if "curtains" in x.get("a", "") + x.get("b", "")]
    g = GEO[run]
    op = opening_mask("M0", m["idx"].shape) if m else None
    return dict(stack_y=list(g["stack_y"]), stack_back_edge_u=round(P(M0, -2.16, g["stack_y"][0], 1.0)[0], 4),
                render_selfcheck=t, overlap_frame_u=[x.get("overlap_thickness") for x in t if x.get("kind") == "overlap"],
                overlap_px=[round(x.get("overlap_thickness", 0) * CW, 1) for x in t if x.get("kind") == "overlap"],
                armchair_left_u=bbox_frame(m["armchair"])[0] if m else None,
                stack_right_u_clay=bbox_frame(m["curtains"])[1] if m else None,
                stack_over_the_opening_pct=None if not m else round(100 * (m["curtains"] & op).sum() / max(op.sum(), 1), 2),
                sconce_plate_to_stack_m=round(3.17 - g["stack_y"][1], 2))
wmc7 = dict(r2=stack_info("r2"), r3=stack_info("r3"), expected=dict(overlap=0.038, sconce_plate_to_stack_m=0.22))
wmc7["resolved"] = bool(wmc7["r3"]["overlap_frame_u"] and min(wmc7["r3"]["overlap_frame_u"]) >= 0.03) or bool(
    wmc7["r3"]["armchair_left_u"] is not None and wmc7["r3"]["stack_right_u_clay"] is not None and
    wmc7["r3"]["stack_right_u_clay"] - wmc7["r3"]["armchair_left_u"] >= 0.03)

# WMC8: the magazine holder
def holder_info(run):
    sc_ = json.load(open(os.path.join(HERE if run == "r3" else R1, "selfcheck-render-A.json")))["frames"]["M0"]
    t = [x for x in (sc_.get("F3_tangents", {}) or {}).get("object_object_tangents", []) if "magazine" in x.get("a", "") + x.get("b", "")]
    return dict(holder=GEO[run]["holder"], to_armchair=gap_pair(run, "M0", "holder", "armchair"), to_basket=gap_pair(run, "M0", "holder", "basket"),
                to_coffee_table=gap_pair(run, "M0", "holder", "table"), holder_bbox_frame=bbox_frame(MK[(run, "M0")]["holder"]) if MK[(run, "M0")] else None,
                render_selfcheck=t)
wmc8 = dict(r2=holder_info("r2"), r3=holder_info("r3"), expected=dict(armchair=0.021, basket=0.024, coffee_table_corner=0.023),
            size_source="data/products/magazine-holder/magazine-holder-cj-gunmetal-leather-strap.json: small 35 x 19 x 27.5 cm "
                        "(data/selections/living-room.warm-modern.json default); the clay box is its envelope, the rack itself is open tubes")
_h = wmc8["r3"]
wmc8["resolved"] = bool(all(x is not None and x["frame_u"] is not None and x["frame_u"] >= 0.02 for x in (_h["to_armchair"], _h["to_basket"], _h["to_coffee_table"])))


# accepted: the arc's start next to the pot; the pot rim against the basket top
def basket_vs_pot(run, fid):
    m = MK[(run, fid)]
    if not m or not m["basket"].any() or not m["pot"].any():
        return None
    bt = int(np.nonzero(m["basket"].any(1))[0].min())
    ptop = int(np.nonzero(m["pot"].any(1))[0].min())
    return dict(basket_top_minus_pot_rim_px=bt - ptop, frame_pct=fpct(abs(bt - ptop)))


accepted = dict(arc_start_next_to_pot=dict(arc_left_tangent_u=round(vline_u(M0, -2.30, G["corner_r"]), 4),
                                           pot_left_u=round(min(P(M0, *q)[0] for q in circ(*G["pot_c"], G["pot_r"], 0.2)), 4),
                                           px=round((min(P(M0, *q)[0] for q in circ(*G["pot_c"], G["pot_r"], 0.2)) - vline_u(M0, -2.30, G["corner_r"])) * CW, 1),
                                           note="accepted (designer, 1.3.3): a continuous curve, no edge"),
                pot_rim_vs_basket_top=dict(r2=basket_vs_pot("r2", "M0"), r3=basket_vs_pot("r3", "M0"), note="accepted (designer, 1.3.3): above the 1 % line"))

plan_clear = dict(sconce_plate_to_stack_m=round(3.17 - G["stack_y"][1], 2), sconce_plate_to_glazing_edge_m=round(3.17 - 2.85, 2), rule=">= 0.10",
                  armchair_to_bench_m=round(min(p[0] for p in rrect(*ARM, 0.72, 0.78, 25, 0, 0)) - G["bench_x1"], 3),
                  pot_to_bench_end_y_m=round(G["bench_y0"] - (G["pot_c"][1] + G["pot_r"]), 3),
                  basket_to_bench_end_y_m=round(G["bench_y0"] - (BASKET["c"][1] + BASKET["r"]), 3),
                  vase_on_bench=dict(base=[-2.42, 1.35, 0.45], bench_y=[G["bench_y0"], 2.85], note="the vase stands on the slab in the reveal; unaffected"))
f3 = {fid: sc.get(fid, {}).get("F3_tangents") for fid in CAMS}
out = dict(date="2026-11-07", tokens=0, script="assets/blockout/house/framing/warm-modern-r3/clay_checks_wm_r3.py",
           inputs=dict(plan=plan["version"][:60], slots=slots["version"], selfcheck="assets/blockout/house/framing/warm-modern-r3/selfcheck-render-A.json",
                       r2="assets/blockout/house/framing/warm-modern-r2/clay-checks-2026-11-07.json"),
           decisions="WMC6-WMC8 on WMC1-WMC5 (house plan 1.3.3 section 0א; slots 1.9.2)",
           cameras={k: dict(loc=v["loc"], yaw=v["yaw_deg_left"], u0=v["u0"], v0=v["v0"]) for k, v in CAMS.items()},
           findings=dict(WMC6_bench_vs_pot=wmc6, WMC7_stack_vs_armchair=wmc7, WMC8_magazine_holder=wmc8, accepted=accepted),
           plan_clearances=plan_clear, vase_vs_armchair_M0=check_vase,
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
        for g_, b_, col, lab in ((G, BASKET, (0, 0, 0), "basket top"),):
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
    d.text((20, 20), "Warm-modern living-room clay per camera: r2 (left) against r3 with WMC6-WMC8 (right). 0 tokens, clay only.", fill=(0, 0, 0), font=fbold)
    y = 80
    for fid, A, B in tiles:
        d.text((20, y), f"{fid}  warm modern r2", fill=(0, 0, 0), font=font)
        d.text((40 + TW, y), f"{fid}  warm modern r3", fill=(0, 0, 0), font=font)
        sheet.paste(A, (20, y + 34))
        sheet.paste(B, (40 + TW, y + 34))
        y += th + 60
    sheet.save(os.path.join(HERE, "warm-modern-r2-vs-r3.jpg"), quality=90)

print(json.dumps(dict(findings=out["findings"], vase=check_vase, f3_lines=f3_lines, contradictions=out["contradictions"]),
                 indent=1, ensure_ascii=False, default=str)[:9000])
for r in rows:
    print(f"{r['slot']:18s} {r['item'][:40]:40s} slots {r['slots_1_9_1']} proj {r['projection']} clay {r['clay']} -> {r['verdict']}")
