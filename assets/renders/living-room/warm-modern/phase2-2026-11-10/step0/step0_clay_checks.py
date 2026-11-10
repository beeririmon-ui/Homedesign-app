#!/usr/bin/env python3
"""
step0_clay_checks.py: step 0 of the warm-modern living-room tool, phase 2 (briefs/render-wm-tool-phase2-2026-11-10.md; plan
docs/proposals/warm-modern-tool-phase2-2026-11-07.md section 3 row 0). render-agent, 2026-11-10. Code only, 0 tokens, no var2.

What it does
  1. WMC9 / WMC10 on clay r4: re-reads assets/blockout/house/framing/warm-modern-r4/clay-checks-2026-11-07.json (resolved there).
  2. PLACE-HOLDERS FOR THE DEFAULTS ONLY: every step 1-3 default as a simple solid at its card's real size, at its slot position
     (data/slots/living-room.json 1.9.3 by_style.warm-modern, else the base slot; house plan 1.3.5), projected with the plan's M0 camera
     (house-plan.json cameras M0: loc (0.83, 4.64, 1.20), yaw 25, u0 0.47, v0 0.50; the projection of clay_checks_wm_r4.py). Each solid's
     full silhouette is the filled convex hull of its parts on the 4072 x 2290 overscan canvas; its VISIBLE part removes whatever stands in
     front of it (the r4 furniture index for items behind the sofa / armchair / table, nearer placeholders).
     The r4 clay has no proxy for framed-art and the floor lamp (hidden since round 5b) and its pendant (40), bowl (24 x 9) and candle
     proxies are not the defaults' sizes, so the placeholders are what the passes use. Where the r4 index has the same item, the IoU of
     the placeholder against it is reported (a check of the projection).
  3. F3 per slot (house plan section 12; the rule of framing_r2.py frame_selfcheck): for each pair of items whose 3D boxes are >= 0.03
     apart and whose silhouettes come near: a gap < 0.02 of the frame width fails ("kissing contours"); an overlap thinner than 0.03 that
     covers < 60 % of the item behind fails. Addition (documented): when the front item lies wholly inside the back item's silhouette, the
     pair is "contained" and the nearest distance between the two contours is checked against 0.02 instead. Edges: a visible box margin
     0 < m < 0.02 fails. Fixed furniture and the cushion sets A / B / C (the approved v3c cut, layers-v3c) are neighbours too.
Writes (this folder): placeholders.npz (label map at 4072 x 2290 and at the 2720 x 1530 work size), placeholders.json, f3-checks.json,
f3-overlay.jpg.   python3 step0_clay_checks.py
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
R4 = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r4")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
IDX_FULL = os.path.join(SCR, "wm-r4-idx/M0.npz")
IDX_FURN = os.path.join(SCR, "wm-r4-furn-idx/M0.npz")
CW, CH, CX, CY = 3840, 2160, 116, 65            # the 16:9 frame inside the 4072 x 2290 overscan canvas
GW, GH = 4072, 2290
WORK = (2720, 1530)
plan = json.load(open(os.path.join(REPO, "docs/house-plan.json")))
CAM = next(c for c in plan["cameras"] if c["id"] == "M0")
TABLE_TOP = 0.38


def P(X, Y, Z, cam=CAM):
    """clay_checks_wm_r4.py P(): the plan camera, frame u / v and the depth along the view"""
    C, Hc, yaw = cam["loc"][:2], cam["loc"][2], math.radians(cam["yaw_deg_left"])
    f, r = (-math.sin(yaw), -math.cos(yaw)), (math.cos(yaw), -math.sin(yaw))
    dx, dy = X - C[0], Y - C[1]
    d, x = f[0] * dx + f[1] * dy, r[0] * dx + r[1] * dy
    return cam["u0"] + 0.6667 * x / d, cam["v0"] + 1.1852 * (Hc - Z) / d, d


def circ(cx, cy, r, z, n=96):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]


def cyl(cx, cy, r, z0, z1, n=96):
    return circ(cx, cy, r, z0, n) + circ(cx, cy, r, z1, n)


def cone(cx, cy, r0, r1, z0, z1, n=96):
    return circ(cx, cy, r0, z0, n) + circ(cx, cy, r1, z1, n)


def ellip(cx, cy, r, z0, z1, n=48, m=16):
    zc, rz = (z0 + z1) / 2, (z1 - z0) / 2
    out = []
    for j in range(m + 1):
        ph = -math.pi / 2 + math.pi * j / m
        out += circ(cx, cy, r * math.cos(ph), zc + rz * math.sin(ph), n)
    return out


def box(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


# ------------------------------------------------------------------------------------------------- the defaults as solids
# (card sizes; positions from the slots file / house plan; every number here is in the record)
ART_X = (-0.36, 0.20, 0.76)          # house plan (framing_r3 living_vista): triptych 3 x 50 x 70, 6 cm gaps, centre X 0.20, Z 1.13-1.83
DEFAULTS = {
    "rug": dict(card="rug-cj-braided-wool-natural", option={"size": "230x330", "other": "square"}, step=1, z=20,
                where="house plan 1.2.2 rug centre (0.20, 1.92), long side along X; the card's nearest size 230 x 330 (slot envelope 330 x 240)",
                parts=[box(-1.45, 1.85, 0.77, 3.07, 0.0, 0.012)], r4_pidx=[519]),
    "curtains": dict(card="curtains-aliexpress-beige-linen-sheer-curtains-554205", option={"style": "hooks-top", "size": "150x270"}, step=2, z=10,
                     where="slots 1.9.2 WMC7: one front stack Y 2.65-2.95 on the recessed track (X -2.22, Z 2.86), drop to the floor "
                           "(the card's length is 'Customized'); a pair of panels",
                     parts=[box(-2.29, -2.15, 2.65, 2.95, 0.0, 2.86)], r4_pidx=[523]),
    "vase": dict(card="vase-cj-textured-white-stoneware", option={"size": "large"}, step=2, z=16,
                 where="slots 1.9.1: on the limestone bench, base (-2.42, 1.35, 0.45); Large D16 x H32; dry olive branch to Z 1.05 (filler)",
                 parts=[cyl(-2.42, 1.35, 0.08, 0.45, 0.77), cone(-2.42, 1.35, 0.02, 0.11, 0.77, 1.05, 24)], r4_pidx=[445]),
    "planter": dict(card="planter-cj-cement-ribbed-belly", option={"color": "beige", "size": "large"}, step=2, z=32,
                    where="slots 1.9.1 WMC2: pot centre (-1.95, 0.42), d 42 x 35.5; olive crown (filler) r 0.28, Z 0.70-1.65",
                    parts=[cyl(-1.95, 0.42, 0.21, 0.0, 0.355), cyl(-1.95, 0.42, 0.025, 0.355, 0.95, 12), ellip(-1.95, 0.42, 0.28, 0.70, 1.65)],
                    r4_pidx=[35, 60]),
    "basket": dict(card="basket-cj-jute-rope-cylinder", option={"other": "large"}, step=2, z=60,
                   where="slots 1.7 / 1.9: centre (-1.62, 0.78), Large d 35 x 39 (+ loop handles at the rim)",
                   parts=[cyl(-1.62, 0.78, 0.175, 0.0, 0.39)], r4_pidx=[524]),
    "magazine-holder": dict(card="magazine-holder-cj-gunmetal-leather-strap", option={"color": "black", "size": "small"}, step=2, z=60,
                            where="slots 1.9.3 WMC9: (-0.47, 2.57) on the rug, long side to the camera, small 35 x 19 x 27.5",
                            parts=[box(-0.645, -0.295, 2.475, 2.665, 0.012, 0.287)], r4_pidx=[525]),
    "floor-lamp": dict(card="floor-lamp-cj-pleated-walnut-stem-158", option={"other": "3color-floor-lamp"}, step=2, z=30,
                       where="slots 1.4: base centre (1.52, 0.20), right of the sofa; card: base 26 x 2.5, shade 37 x 23 (pleated cone), H 158",
                       parts=[cyl(1.52, 0.20, 0.13, 0.0, 0.025), cyl(1.52, 0.20, 0.0125, 0.025, 1.35, 16), cone(1.52, 0.20, 0.185, 0.12, 1.35, 1.58)],
                       r4_pidx=[]),
    "framed-art": dict(card="framed-art-aliexpress-frameless-minimalist-wall-art-631735", option={"color": "tl2356-3pcs", "size": "50x70-no-frame"},
                       step=3, z=12,
                       where="house plan (framing_r3 living_vista, the v4 spec art): triptych 3 x 50 x 70 at X -0.36 / 0.20 / 0.76, 6 cm gaps, "
                             "Z 1.13-1.83, on the back wall; sold unframed, rendered in a thin walnut frame (PR1)",
                       parts=[box(x - 0.25, x + 0.25, 0.0, 0.03, 1.13, 1.83) for x in ART_X], r4_pidx=[]),
    "accent-sconces": dict(card="accent-sconces-aliexpress-travertine-cylinder-walnut-choice", option={"style": "round-walnut"}, step=3, z=12,
                           where="slots: plates (-0.85, 0, 1.75) and (1.25, 0, 1.75); card: travertine cylinder D6.5 x H16 on a walnut "
                                 "block, 9 deep; a pair (2 units)",
                           parts=[p for x in (-0.85, 1.25) for p in (box(x - 0.04, x + 0.04, 0.0, 0.025, 1.67, 1.83),
                                                                      cyl(x, 0.0575, 0.0325, 1.67, 1.83, 32))],
                           r4_pidx=[514]),
    "pendant": dict(card="pendant-cj-tiered-fabric-drum", option={}, step=3, z=80,
                    where="slots 1.5 (V7Q7 b): hang point (0.20, 1.72, 3.00), shade bottom 1.90; card: Beige 50, tiered drum, height not stated "
                          "(~25-30 from photos): 28 used",
                    parts=[cyl(0.20, 1.72, 0.25, 1.90, 2.18), cyl(0.20, 1.72, 0.004, 2.18, 3.00, 12)], r4_pidx=[517, 518]),
    "bowl": dict(card="bowl-cj-matte-black-bowl-20", option={"other": "12style"}, step=3, z=65,
                 where="slots: coffee table, centre 'about (0.68, 1.92)'; placed at (0.72, 1.94) by step 0's F3 scan (0.045 from the slot's "
                       "approximate centre, ~8 cm inside the top's edge): at (0.68, 1.92) it kisses candle B (0.0107); card style 12 (the only "
                       "identified variant, addendum 1): D20 x H8",
                 parts=[cyl(0.72, 1.94, 0.10, TABLE_TOP, TABLE_TOP + 0.08)], r4_pidx=[446]),
    "candle-holders": dict(card="candle-holders-cj-travertine-pedestal", option={"size": "70x110mm"}, step=3, z=65,
                           where="coffee table, grouped with the bowl: two Small pedestals 7 x 11 (the set of 2 units) at (0.33, 1.74) and "
                                 "(0.48, 1.68), pillar candles (filler) 7.5 and 6 tall. Placed by step 0's F3 scan: the r4 / Nordic places "
                                 "(0.46, 1.64) and (0.50, 1.86) stack the two in one column and kiss the cushions (0.010-0.014); this pair "
                                 "passes against each other, the bowl and all three cushion sets. Candle A is 0.09 left of the Nordic X "
                                 "range 0.42-0.65 (designer to confirm)",
                           parts=[cyl(0.33, 1.74, 0.035, TABLE_TOP, TABLE_TOP + 0.11, 48), cyl(0.33, 1.74, 0.03, TABLE_TOP + 0.11, TABLE_TOP + 0.185, 48),
                                  cyl(0.48, 1.68, 0.035, TABLE_TOP, TABLE_TOP + 0.11, 48), cyl(0.48, 1.68, 0.03, TABLE_TOP + 0.11, TABLE_TOP + 0.17, 48)],
                           r4_pidx=[45]),
}
ORDER = list(DEFAULTS)
LABEL = {k: i + 1 for i, k in enumerate(ORDER)}
FURN = {"sofa": 1, "coffee-table": 2, "armchair": 3}


def raster(parts):
    """the filled convex hull of each part's projected vertices (all parts are convex solids), on the overscan canvas"""
    m = np.zeros((GH, GW), np.uint8)
    for pts in parts:
        uv = [P(*q) for q in pts]
        if any(d <= 0.05 for _, _, d in uv):
            continue
        xy = np.array([[CX + u * CW, CY + v * CH] for u, v, _ in uv], np.float32)
        hull = cv2.convexHull(xy)
        cv2.fillPoly(m, [np.round(hull * 4).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=2)
    return m.astype(bool)


def depth_of(parts):
    pts = [q for p in parts for q in p]
    return float(np.median([P(*q)[2] for q in pts]))


def aabb(parts):
    a = np.array([q for p in parts for q in p])
    return a.min(0), a.max(0)


def aabb_dist(A, B):
    (a0, a1), (b0, b1) = A, B
    d = np.maximum(0, np.maximum(a0 - b1, b0 - a1))
    return float(np.sqrt((d ** 2).sum()))


def thickness(m):
    if not m.any():
        return 0.0
    dt = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 5)
    return 2.0 * float(dt.max())


def boundary(m):
    return m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)


def contour_gap(a, b):
    """nearest distance between the two contours (px)"""
    ba, bb = boundary(a), boundary(b)
    if not ba.any() or not bb.any():
        return None
    dt = cv2.distanceTransform((~bb).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[ba].min())


def min_dist(a, b):
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[a].min())


def frame_box(m):
    ys, xs = np.nonzero(m)
    return [round((xs.min() - CX) / CW, 4), round((xs.max() + 1 - CX) / CW, 4), round((ys.min() - CY) / CH, 4), round((ys.max() + 1 - CY) / CH, 4)]


def main():
    r4 = json.load(open(os.path.join(R4, "clay-checks-2026-11-07.json")))
    idx = np.load(IDX_FULL, allow_pickle=True)["idx"]
    fidx = np.load(IDX_FURN, allow_pickle=True)["idx"]
    furn_vis = {k: fidx == v for k, v in FURN.items()}           # the furniture-only clay: furniture silhouettes without products
    # the cushion sets (the approved v3c cut at 2720 x 1530, scaled to the canvas)
    cush = {}
    for s in "ABC":
        a = np.asarray(Image.open(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png")))[..., 3]
        cush[s] = cv2.resize((a > 127).astype(np.uint8), (GW, GH), interpolation=cv2.INTER_NEAREST).astype(bool)

    sil = {k: raster(d["parts"]) for k, d in DEFAULTS.items()}
    dep = {k: depth_of(d["parts"]) for k, d in DEFAULTS.items()}
    box3 = {k: aabb(d["parts"]) for k, d in DEFAULTS.items()}
    # furniture 3D boxes (house plan; for the "in contact" skip and the depth order)
    fbox = {"sofa": (np.array([-0.90, 0.03, 0.0]), np.array([1.30, 0.95, 0.78])),
            "coffee-table": (np.array([-0.50, 1.37, 0.0]), np.array([0.90, 2.07, 0.38])),
            "armchair": (np.array([-1.62, 2.34, 0.0]), np.array([-0.84, 3.12, 0.70]))}
    fdep = {k: float(P(*(0.5 * (b[0] + b[1])))[2]) for k, b in fbox.items()}

    # visible parts: remove nearer placeholders and nearer furniture
    vis = {}
    for k in ORDER:
        v = sil[k].copy()
        for j in ORDER:
            if j != k and dep[j] < dep[k] and k != "rug":
                v &= ~sil[j]
        if k == "rug":                                            # the rug lies on the floor: everything standing on it is in front
            for j in ORDER:
                if j != k:
                    v &= ~sil[j]
        for fk, fm in furn_vis.items():
            if fdep[fk] < dep[k] or k in ("rug",):
                v &= ~fm
        if k in ("bowl", "candle-holders"):                       # standing on the table: the table never hides them
            v = sil[k].copy()
            for j in ("bowl", "candle-holders"):
                if j != k and dep[j] < dep[k]:
                    v &= ~sil[j]
        vis[k] = v

    # the placeholder label map (visible parts; drawn far to near so nearer items win)
    lab = np.zeros((GH, GW), np.uint8)
    for k in sorted(ORDER, key=lambda k: -dep[k]):
        lab[vis[k]] = LABEL[k]
    work = cv2.resize(lab, WORK, interpolation=cv2.INTER_NEAREST)
    np.savez_compressed(os.path.join(HERE, "placeholders.npz"), canvas=lab, work=work,
                        **{f"sil_{k}": sil[k] for k in ORDER})

    # per item: box, visible %, IoU with the r4 index item (where the r4 clay has it)
    items = {}
    for k, d in DEFAULTS.items():
        rec = dict(card=d["card"], option=d["option"], step=d["step"], z=d["z"], label=LABEL[k], where=d["where"],
                   depth_m=round(dep[k], 3), frame_box=frame_box(vis[k]) if vis[k].any() else None,
                   visible_px_3840=int(vis[k][CY:CY + CH, CX:CX + CW].sum()),
                   visible_pct_of_silhouette=round(100.0 * vis[k].sum() / max(1, sil[k].sum()), 1),
                   frame_pct=round(100.0 * vis[k][CY:CY + CH, CX:CX + CW].sum() / (CW * CH), 3))
        if d["r4_pidx"]:
            r4m = np.isin(idx, d["r4_pidx"])
            inter, uni = (r4m & vis[k]).sum(), (r4m | vis[k]).sum()
            rec["r4_clay"] = dict(pidx=d["r4_pidx"], frame_box=frame_box(r4m), iou_with_placeholder=round(float(inter / max(1, uni)), 3),
                                  note="r4 proxy at its own size; the placeholder is the default's card size")
        items[k] = rec

    # F3 (per cushion set: the cushions stand in front of the sofa and of the floor lamp)
    fbox = {"sofa": [(np.array([-0.90, 0.03, 0.0]), np.array([1.30, 0.95, 0.78]))],
            "coffee-table": [(np.array([-0.50, 1.37, 0.0]), np.array([0.90, 2.07, 0.38]))],
            "armchair": [(np.array([-1.62, 2.34, 0.0]), np.array([-0.84, 3.12, 0.70]))]}
    cbox = [(np.array([-0.95, 0.25, 0.44]), np.array([1.15, 0.65, 0.95])),       # cushions on the seat
            (np.array([1.08, 0.35, 0.02]), np.array([1.36, 0.97, 0.66]))]        # the throw over the right arm, down to the floor
    sofa_full = furn_vis["sofa"] | (raster([box(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)]) & furn_vis["coffee-table"])
    pboxes = {k: [aabb([p]) for p in DEFAULTS[k]["parts"]] for k in ORDER}
    near_ = lambda A, B: min(aabb_dist(x, y) for x in A for y in B)  # noqa: E731

    def f3_for(s):
        cm = cush[s]
        N = {}
        for k in ORDER:
            v = vis[k] & ~cm if k in ("floor-lamp", "rug") else vis[k]
            N[k] = dict(sil=sil[k], vis=v, boxes=pboxes[k], dep=dep[k])
        N["fixed:sofa"] = dict(sil=sofa_full, vis=furn_vis["sofa"] & ~cm, boxes=fbox["sofa"], dep=fdep["sofa"])
        N["fixed:coffee-table"] = dict(sil=furn_vis["coffee-table"], vis=furn_vis["coffee-table"], boxes=fbox["coffee-table"], dep=fdep["coffee-table"])
        N["fixed:armchair"] = dict(sil=furn_vis["armchair"], vis=furn_vis["armchair"], boxes=fbox["armchair"], dep=fdep["armchair"])
        N[f"cushions-set-{s}"] = dict(sil=cm, vis=cm, boxes=cbox, dep=fdep["sofa"] - 0.3)
        names = list(N)
        out = []
        pad = int(0.03 * CW)
        for i, k in enumerate(names):
            for j in names[i + 1:]:
                if k not in ORDER and j not in ORDER:
                    continue                                      # furniture / cushions among themselves: phase 1, approved
                A, B = N[k], N[j]
                ya, xa = np.nonzero(A["vis"])
                yb, xb = np.nonzero(B["vis"])
                if not len(xa) or not len(xb):
                    continue
                if xa.min() > xb.max() + pad or xb.min() > xa.max() + pad or ya.min() > yb.max() + pad or yb.min() > ya.max() + pad:
                    continue
                d3 = near_(A["boxes"], B["boxes"])
                rec = dict(a=k, b=j, dist3d_m=round(d3, 3))
                if d3 < 0.03:
                    rec.update(kind="contact", verdict="skip (physical contact / resting)")
                    out.append(rec)
                    continue
                inter = A["sil"] & B["sil"]
                if not inter.any():
                    g = min_dist(A["vis"], B["vis"])
                    rec.update(kind="gap", gap_px=round(g, 1), gap_frame=round(g / CW, 4),
                               verdict="FAIL (kissing, < 0.02)" if g / CW < 0.02 else "clear (>= 0.02)")
                    out.append(rec)
                    continue
                touching = (cv2.dilate(A["vis"].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & B["vis"]).any()
                if not touching:
                    rec.update(kind="overlap-hidden", verdict="skip (the silhouettes overlap only where a third item hides both)")
                    out.append(rec)
                    continue
                front, back, fn = (A, B, k) if A["dep"] < B["dep"] else (B, A, j)
                inside = float((front["sil"] & back["sil"]).sum()) / max(1, front["sil"].sum())
                th = thickness(inter) / CW
                cover = float(inter.sum()) / max(1, back["sil"].sum())
                rec.update(front=fn, overlap_thickness=round(th, 4), cover_of_back=round(cover, 3), front_inside_back_pct=round(100 * inside, 1))
                if inside >= 0.99:
                    seen = boundary(back["sil"]) & cv2.dilate(back["vis"].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                    dtb = cv2.distanceTransform((~seen).astype(np.uint8), cv2.DIST_L2, 5) if seen.any() else None
                    cg = None if dtb is None else float(dtb[boundary(front["vis"])].min())
                    rec.update(kind="contained", contour_gap_px=None if cg is None else round(cg, 1),
                               contour_gap_frame=None if cg is None else round(cg / CW, 4),
                               verdict="FAIL (contour < 0.02 from the visible contour behind)" if cg is not None and cg / CW < 0.02
                               else "clear (contained, contours >= 0.02 apart)")
                else:
                    rec.update(kind="overlap", verdict="FAIL (overlap < 0.03 and < 60 % of the back item)" if th < 0.03 and cover < 0.6
                               else "decisive overlap")
                out.append(rec)
        return out

    per_set = {s: f3_for(s) for s in "ABC"}
    pairs = []
    keyed = {}
    for s, lst in per_set.items():
        for p in lst:
            keyed.setdefault((p["a"].replace(f"cushions-set-{s}", "cushions-set-X"), p["b"].replace(f"cushions-set-{s}", "cushions-set-X")), {})[s] = p
    for (ka, kb), by in keyed.items():
        worst = next((by[s] for s in "BAC" if s in by and str(by[s]["verdict"]).startswith("FAIL")), by.get("B") or next(iter(by.values())))
        rec = dict(worst)
        rec["a"], rec["b"] = ka, kb
        rec["by_set"] = {s: {kk: vv for kk, vv in p.items() if kk not in ("a", "b")} for s, p in by.items()}
        rec["sets_failing"] = [s for s in "ABC" if s in by and str(by[s]["verdict"]).startswith("FAIL")]
        pairs.append(rec)

    # the floor lamp's levers (house plan authority of the designer: <= 0.10), projected only; nothing is moved here
    def lamp_at(c):
        L = raster([cyl(*c, 0.13, 0.0, 0.025), cyl(*c, 0.0125, 0.025, 1.35, 16), cone(*c, 0.185, 0.12, 1.35, 1.58)])
        S_ = raster([box(1.21, 1.29, 0.0, 0.025, 1.67, 1.83), cyl(1.25, 0.0575, 0.0325, 1.67, 1.83, 32)])
        bx_ = frame_box(L)
        r = dict(position=list(c), right_margin=round(1 - bx_[1], 4), sconce_gap=round(min_dist(L, S_) / CW, 4))
        for s in "ABC":
            Lc, Sc = L & ~furn_vis["sofa"] & ~cush[s], furn_vis["sofa"] & ~cush[s]
            touch = (cv2.dilate(Lc.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & Sc).any()
            r[f"set_{s}"] = dict(sofa=("touching, overlap %.4f" % (thickness(L & Sc) / CW)) if touch else "gap %.4f" % (min_dist(Lc, Sc) / CW),
                                 throw_overlap=round(thickness(L & cush[s]) / CW, 4))
        return r
    levers = [lamp_at(c) for c in [(1.52, 0.20), (1.56, 0.20), (1.60, 0.20), (1.58, 0.14), (1.52, 0.28), (1.47, 0.20), (1.42, 0.25)]]
    edges = {}
    for k in ORDER:
        b = items[k]["frame_box"]
        if b is None:
            continue
        m = dict(left=b[0], right=1 - b[1], top=b[2], bottom=1 - b[3])
        bad = {s: round(v, 4) for s, v in m.items() if 0 < v < 0.02}
        cut = [s for s, v in m.items() if v <= 0]
        edges[k] = dict(margins={s: round(v, 4) for s, v in m.items()}, cropped_by=cut,
                        verdict=("FAIL (edge tangent) " + json.dumps(bad)) if bad else "ok")

    fails = [p for p in pairs if p.get("sets_failing")] + [dict(edge=k, **v) for k, v in edges.items() if v["verdict"] != "ok"]
    out = dict(
        date="2026-11-10", step=0, tokens=0, author="render-agent", script=os.path.relpath(__file__, REPO),
        brief="briefs/render-wm-tool-phase2-2026-11-10.md", plan="docs/proposals/warm-modern-tool-phase2-2026-11-07.md section 3 row 0",
        clay="r4 (house plan 1.3.5, slots 1.9.3): assets/blockout/house/framing/warm-modern-r4/",
        wmc9=dict(resolved=r4["findings"]["WMC9_magazine_holder"]["resolved"], r4=r4["findings"]["WMC9_magazine_holder"]["r4"]["to_armchair"],
                  note="the r4 clay checks of 2026-11-07: (-0.47, 2.57), armchair gap 82 px = 0.0214 (>= 0.02)"),
        wmc10=dict(resolved=r4["findings"]["WMC10_floor_line"]["resolved"],
                   floor_line_offset_px_3840=r4["findings"]["WMC10_floor_line"]["r4"]["floor_line_offset_px_3840"]),
        r4_f3_m0=r4["f3_tangents"]["M0"],
        camera=dict(id="M0", loc=CAM["loc"], yaw_deg_left=CAM["yaw_deg_left"], u0=CAM["u0"], v0=CAM["v0"]),
        placeholders=items,
        f3=dict(rule="framing_r2.py frame_selfcheck: gap < 0.02 of the frame width fails; overlap thinner than 0.03 covering < 60 % of the back "
                     "item fails; 3D boxes < 0.03 apart are contact (skipped); + 'contained' (front item wholly inside the back item's silhouette: "
                     "the two contours must be >= 0.02 apart); edges: a visible margin 0 < m < 0.02 fails",
                pairs=pairs, edges=edges, fails=fails, pass_=not fails,
                floor_lamp_levers=dict(note="projected only, nothing moved: the plan position (1.52, 0.20) is binding; a nudge <= 0.10 is the "
                                            "designer's (house plan). The throw of every set covers the lamp's base by a thin overlap at all of them",
                                       positions=levers)),
        files=dict(placeholders="placeholders.npz (canvas 4072 x 2290 and work 2720 x 1530 label maps; full silhouettes sil_<slot>)",
                   overlay="f3-overlay.jpg"),
    )
    json.dump(out, open(os.path.join(HERE, "f3-checks.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(dict(labels=LABEL, order=ORDER, defaults={k: {kk: vv for kk, vv in d.items() if kk != "parts"} for k, d in DEFAULTS.items()}),
              open(os.path.join(HERE, "placeholders.json"), "w"), indent=1, ensure_ascii=False)

    # overlay: the v3c default scene (set B) with every placeholder outlined
    bg = Image.open(os.path.join(P1, "composite-set-B-v3-graded-v3c.png")).convert("RGB").resize((GW, GH), Image.LANCZOS)
    a = np.asarray(bg).astype(np.float32)
    cols = {"rug": (230, 160, 40), "curtains": (60, 160, 230), "vase": (40, 200, 120), "planter": (20, 140, 60), "basket": (200, 120, 40),
            "magazine-holder": (220, 60, 60), "floor-lamp": (240, 200, 30), "framed-art": (150, 60, 200), "accent-sconces": (230, 90, 170),
            "pendant": (250, 130, 30), "bowl": (40, 40, 40), "candle-holders": (90, 200, 220)}
    for k in ORDER:
        m = vis[k]
        a[m] = a[m] * 0.55 + np.array(cols[k]) * 0.45
        e = boundary(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool))
        a[cv2.dilate(e.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)] = cols[k]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).crop((CX, CY, CX + CW, CY + CH)).resize((1920, 1080), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    for k in ORDER:
        b = items[k]["frame_box"]
        if b:
            d.text((max(4, b[0] * 1920), max(4, b[2] * 1080 - 22)), k, fill=cols[k], font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((10, 1050), f"step 0: default placeholders at card size on v3c set B; F3 fails: {len(fails)}", fill=(255, 255, 255), font=f,
           stroke_width=2, stroke_fill=(0, 0, 0))
    im.save(os.path.join(HERE, "f3-overlay.jpg"), quality=90)
    for k in ORDER:
        print(f"{k:16s} box {items[k]['frame_box']} vis {items[k]['visible_pct_of_silhouette']}% iou_r4 {items[k].get('r4_clay', {}).get('iou_with_placeholder')}")
    for p in pairs:
        print(json.dumps({k: v for k, v in p.items() if k != "by_set"}))
    for l_ in levers:
        print(json.dumps(l_))
    print(json.dumps(edges))
    print("F3 fails:", len(fails))


if __name__ == "__main__":
    main()
