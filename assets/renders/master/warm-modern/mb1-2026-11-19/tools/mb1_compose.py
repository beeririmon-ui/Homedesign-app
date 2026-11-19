#!/usr/bin/env python3
"""
mb1_compose.py: the MB1 layers from the four nano passes, and the MB1 frame (render-agent, 2026-11-19; 0 tokens beyond the passes).
Per pass (passes.json: the raw edit, its input, and the base the input was made from):
  1. lock: ECC affine of the edit onto its input, masked to the clay's architecture and fixed furniture outside the pass's zone;
  2. MP-I1: the gain field (sigma 60, the MB0 compositor's) against the base outside the zone;
  3. cut: what the edit changed on the base inside the zone (dE76 > 7 on a 1 px blur), GrabCut-refined, holes filled; each pixel
     goes to one product of the pass by the nearest clay region (and, for the bed textiles, by colour too);
  4. shadow: the edit's darkening of the base in a band round each product, never on a product (multiply, z - 1);
  5. light: for the lit lamps, the edit's brightening of the base outside every product, as a screen layer (z 90);
  6. MP-I2 / WM-G1: MB1's toe (plate-compose.json, step 3) on the new layers' L*, once.
Then the frame: plate.png, the layers in z order (each shadow, then the layer), the lights times (1 - every alpha): outside every alpha,
shadow and light nothing differs from plate.png (RND2).
  python3 mb1_compose.py <pass> ...     (each pass appends / replaces its layers in layers/manifest.json and recomposes)
  python3 mb1_compose.py compose        (recompose only)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
ARCH = (1, 2, 5, 9, 10, 12, 13, 14, 20, 21, 23, 24, 25, 28, 29, 30)
P = {   # clay id: (slot, product, z, pass, layer-name)
    51: ("pillowcases", "pillowcases-cj-pure-linen-envelope-pair-48x74-caramel-pairs", 50, "p1-bed", None),
    52: ("bedding", "bedding-cj-washed-linen-natural-set-natural-linen-1-8m", 52, "p1-bed", None),
    53: ("cushions", "cushions-cj-boucle-teddy-milk-tea-30x50", 55, "p1-bed", None),
    54: ("throw", "sofa-cover-cj-cotton-muslin-fringe-pecan-150x200", 58, "p1-bed", None),
    44: ("bedside-sconces", "wall-sconce-cj-travertine-cone-walnut", 14, "p2-right", "east"),
    49: ("candle-holders", "candle-holders-cj-travertine-pedestal-70x110", 46, "p2-right", None),
    55: ("floor-lamp", "floor-lamp-aliexpress-pleated-walnut-43x158-177278-master-a1-warm-light", 36, "p2-right", None),
    61: ("planter", "planter-cj-cement-ribbed-belly-beige-large-ficus-audrey", 30, "p2-right", None),
    63: ("magazine-holder", "magazine-holder-cj-gunmetal-leather-strap-orange", 38, "p2-right", None),
    64: ("bedside-carafe", "open-shelf-ceramics-cj-patina-clay-pitcher-c03d140", 46, "p2-right", None),
    40: ("curtains", "curtains-aliexpress-linen-blend-s-fold-180502", 10, "p3-wall", None),
    41: ("sill-vase", "sill-vase-cj-cream-fluted-column-25", 16, "p3-wall", None),
    43: ("bedside-sconces", "wall-sconce-cj-travertine-cone-walnut", 14, "p3-wall", "west"),
    45: ("nightstand-tray", "nightstand-tray-cj-black-walnut-rect-tray", 44, "p3-wall", None),
    46: ("nightstand-vase", "nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862-d", 46, "p3-wall", None),
    48: ("trinket-dish", "trinket-dish-cj-travertine-rough-edge-10x10", 46, "p3-wall", None),
    56: ("framed-art", "framed-art-aliexpress-japandi-bare-branch-70x100-776445-50x70-walnut-float", 12, "p3-wall", None),
    57: ("framed-art-2", "framed-art-aliexpress-misty-landscape-386242-work-05-30x40", 13, "p3-wall", None),
    59: ("shelf-vase-left", "vase-cj-charcoal-carved-style-b", 18, "p3-wall", None),
    60: ("shelf-vase-right", "vase-cj-white-plum-hand-thrown-m", 18, "p3-wall", None),
    65: ("bench-throw", "throw-cj-waffle-blanket-200x230-beige", 60, "p4-floor", None),
    66: ("bench-basket", "basket-cj-two-tone-rope-jute-white-30", 62, "p4-floor", None),
    67: ("rug", "rug-cj-braided-wool-natural-200x300", 20, "p4-floor", None),
}
FILLERS = {50: 49, 62: 61, 42: 41, 47: 46, 58: 56}       # filler / part id -> the product id it belongs to (candles, ficus, stems, canvases)
LAMPS = {"p2-right": [44, 55], "p3-wall": [43]}
ZONE_PAD = {55: 30, 61: 40, 62: 60, 54: 50, 52: 60, 40: 40, 65: 50, 67: 40, 51: 30, 53: 30}
BED_PROTO = {54: (45.0, 18.0, 28.0), 51: (60.0, 18.0, 30.0), 53: (82.0, 2.0, 9.0), 52: (78.0, 2.5, 9.0)}


def pass_ids(p):
    ids = [k for k, v in P.items() if v[3] == p]
    return ids + [f for f, k in FILLERS.items() if k in ids]


def owner(k):
    return FILLERS.get(k, k)


def toe_curve():
    s = json.load(open(os.path.join(ST, "plate-compose.json")))["steps"][2]
    return (s["xp"], s["fp"]) if s.get("applied") else None


def cut_pass(p, rec):
    J = json.load(open(os.path.join(ST, "passes.json")))[p]
    ids = M.ids("MB1")
    base = C.load(os.path.join(ST, J["base"]))
    pids = pass_ids(p)
    zone = np.zeros((H, W), bool)
    for k in pids:
        zone |= C.dil(ids == k, ZONE_PAD.get(k, 22))
    pl_ids = M.ids("MB1-plate")
    if p == "p4-floor":                               # the throw falls in front of the bench to the rug
        zone |= C.box_mask([(35, 1005, 600, 1480)])
    if p == "p1-bed":                                 # the duvet falls over the bed frame to the floor: the frame and the mattress are in;
        zone |= C.dil(np.isin(pl_ids, (21, 22, 23)), 12)       # the pillows stand taller than the clay's: up the headboard to its top
        hb = pl_ids == 20
        up = np.zeros((H, W), bool)
        for x in np.nonzero(np.isin(ids, (51, 53)).any(0))[0]:
            col = np.nonzero(np.isin(ids[:, x], (51, 53)))[0]
            up[max(0, col.min() - 140):col.min(), x] = True
        zone |= up & C.dil(hb, 2)
        zone &= ~C.dil(np.isin(pl_ids, (29, 30)), 2)   # never the bench (in front)
    stable = C.ero(np.isin(pl_ids, ARCH), 3) & ~C.dil(zone, 40)
    stable[1450:] = False
    e, rl = M.ecc_lock(os.path.join(ST, J["raw"]), os.path.join(ST, J["input"]), stable)
    keep = ~C.dil(zone, 40)
    lampenv = light_env(ids, p)
    keep &= ~lampenv                                   # the lamps' glow is light, not exposure: out of the gain field
    g = C.gain_field(e, base, keep)
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    d = np.linalg.norm(C.blur(C.to_lab(e), 1.0) - C.blur(C.to_lab(base), 1.0), axis=-1)
    out_d = d[keep & M.frame_mask()]
    rp = dict(lock=rl, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
              dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(out_d, [50, 95])])
    # the cut
    fg = (d > 7) & zone
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    sure = C.ero((d > 16) & zone, 2)
    hard = zone & ~C.ero(zone, 2)
    fg2 = C.gc_cut(e, sure, C.dil(fg, 2) & zone, zone, hard, iters=6) if sure.any() else fg
    fg = fill_holes(fg2 | (C.ero(fg, 1)), 900) & zone
    if p == "p1-bed":                                  # the mattress is covered everywhere (the duvet over it); closed, every hole filled
        fg |= C.ero(pl_ids == 23, 2)
        fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(6)).astype(bool) & zone
        fg = fill_holes(fg, 10 ** 7) & zone
        n_, lb_, st_, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
        fg = lb_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
        ns = np.isin(pl_ids, (24, 25, 26, 27)) & ~np.isin(ids, (51, 52, 53, 54))   # the nightstands where the clay's bedding does not reach
        fg &= ~C.ero(ns, 1)                                 # the bedding stays behind them
    # a change of brightness only, on the wall, the floor or the skirting, away from the products' own places: light or shadow, not object
    lab_e0, lab_b0 = C.blur(C.to_lab(e), 1.5), C.blur(C.to_lab(base), 1.5)
    ce_, cb_ = np.hypot(lab_e0[..., 1], lab_e0[..., 2]), np.hypot(lab_b0[..., 1], lab_b0[..., 2])
    he_, hb_ = np.degrees(np.arctan2(lab_e0[..., 2], lab_e0[..., 1])), np.degrees(np.arctan2(lab_b0[..., 2], lab_b0[..., 1]))
    dh_ = np.abs((he_ - hb_ + 180) % 360 - 180)
    same = ((np.abs(lab_e0[..., 1] - lab_b0[..., 1]) < 4) & (np.abs(lab_e0[..., 2] - lab_b0[..., 2]) < 5)) | ((dh_ < 12) & (np.abs(ce_ - cb_) < 8))
    same |= light_env(ids, p) & (dh_ < 25) & (np.abs(ce_ - cb_) < 14) & (lab_e0[..., 0] >= lab_b0[..., 0] - 3)   # a lamp's warm glow
    SURF = (1, 2, 5, 9, 10, 11)                                              # walls and floor; the fixed walnut only in a lamp's glow
    WAL = (20, 21, 22, 24, 25, 26, 27, 28, 29, 30)
    surf = (np.isin(pl_ids, SURF) & np.isin(ids, SURF)) | (np.isin(pl_ids, WAL) & np.isin(ids, WAL) & light_env(ids, p))
    light_coloured = [k for k in pids if k in (43, 44, 49, 50, 60, 41, 42, 56, 57, 58)]   # cream / white products on the wall: exempt
    exempt = np.isin(ids, light_coloured)
    if 55 in pids:                                     # the floor lamp: only its shade (the pole and the base are dark)
        lm = ids == 55
        ys_ = np.nonzero(lm.any(1))[0]
        lm[ys_.min() + int(0.32 * (ys_.max() - ys_.min())):] = False
        exempt |= lm
    fg &= ~(same & surf & ~C.dil(exempt, 8))
    if p == "p2-right":                                # the clay crown's sphere is wall in the edit: the leaves are green, the trunk pale
        sph = np.isin(ids, (62,)) & ~C.dil(np.isin(ids, (61, 55)), 4)
        lab_ab = np.hypot(lab_e0[..., 1] - lab_b0[..., 1], lab_e0[..., 2] - lab_b0[..., 2])
        fg &= ~(sph & (lab_ab < 5) & (np.abs(lab_e0[..., 0] - lab_b0[..., 0]) < 18))
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    lamps_lit = LAMPS.get(p, [])
    # brightening near lamps outside the objects is light, not object
    lab_e, lab_b = C.to_lab(e), C.to_lab(base)
    if lamps_lit:
        glow = (lab_e[..., 0] - lab_b[..., 0] > 2) & (np.abs(lab_e[..., 1] - lab_b[..., 1]) < 4) & ~np.isin(ids, pids)
        glow &= np.linalg.norm(C.blur(lab_e, 3)[..., 1:] - C.blur(lab_b, 3)[..., 1:], axis=-1) < 5
        lampm = np.zeros((H, W), bool)
        for k in lamps_lit:
            lampm |= C.dil(ids == k, 4)
        fg &= ~(glow & ~lampm)
    # assignment to products: the nearest clay region (filler ids count for their product); bed textiles also by colour
    prods = sorted({owner(k) for k in pids})
    dist = np.stack([cv2.distanceTransform((~np.isin(ids, [k] + [f for f, o in FILLERS.items() if o == k])).astype(np.uint8), cv2.DIST_L2, 5)
                     for k in prods])
    if p == "p1-bed":
        lab_i = bed_labels(lab_e, ids, fg, prods)
    else:
        lab_i = np.argmin(dist, 0)
        if p == "p4-floor":                            # over the bench (plate ids 29, 30) a change is the throw, unless the basket's
            onb = np.isin(pl_ids, (29, 30)) & ~C.dil(ids == 66, 25)
            lab_i[onb] = prods.index(65)
            fallx = C.box_mask([(35, 1005, 600, 1480)]) & ~C.dil(ids == 66, 25) & (lab_i == prods.index(67))
            lab_i[fallx & (dist[prods.index(65)] < 260) & ~C.ero(ids == 67, 3)] = prods.index(65)
        if p == "p2-right":
            lab_i, hold = right_labels(lab_e, fg, prods, lab_i, d)
            boxh = np.zeros((H, W), bool)
            boxh[1100:1470, 1940:2340] = True
            fg = (fg & ~(boxh & (lab_i == prods.index(63)) & ~hold)) | hold     # the holder and the pot: their hulls
            fg &= lab_i >= 0
            fg |= hold
    layers = {}
    for i, k in enumerate(prods):
        m = fg & (lab_i == i)
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        n, lb, stt, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        keepc = [j for j in range(1, n) if stt[j, cv2.CC_STAT_AREA] >= 40]
        m = np.isin(lb, keepc)
        if k in (41, 43, 44, 45, 46, 48, 49, 59, 60, 64):     # the small products sit where the clay has them: bounded to 20 px round it
            m &= C.dil(np.isin(ids, [k] + [f for f, o in FILLERS.items() if o == k]), 20)
        if k == 67:                                    # the rug: where the clay sees it (never over the bench, the bed or the basket)
            m &= C.dil(ids == 67, 6) & ~np.isin(pl_ids, (20, 21, 22, 23, 24, 25, 26, 27, 29, 30))
        if k == 65:                                    # the throw: on the bench's left half and its fall in front, down to the rug
            ys_, xs_ = np.nonzero(ids == 65)
            fall = C.box_mask([(int(xs_.min()) - 40, int(ys_.min()), int(xs_.max()) + 40, 1480)])
            m &= C.dil(ids == 65, 45) | fall
        if k == 66:
            m &= C.dil(ids == 66, 40)
        if k == 40:                                    # the sheer curtain stacks: low contrast on the plaster; closed solid in their place
            m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(7)).astype(bool)
            m = fill_holes(m, 20000) & C.dil(ids == 40, 25)
            n2, lb2, st2, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
            m = np.isin(lb2, [j for j in range(1, n2) if st2[j, cv2.CC_STAT_AREA] >= 3000])
        layers[k] = m
        rp[P[k][0] + (("-" + P[k][4]) if P[k][4] else "")] = dict(px=int(m.sum()), clay_px=int(np.isin(ids, [k]).sum()))
    # shadows: darkening round each product (band 40), the nearest product, never on any product
    allfg = np.zeros((H, W), bool)                      # the layers as kept (pixels the cut dropped are wall again: they take shadow / light)
    for k in prods:
        allfg |= layers[k]
    rat = np.clip(C.blur(C.luma(C.lin(e)), 2) / np.maximum(C.blur(C.luma(C.lin(base)), 2), 1e-4), 0, 1.5)
    dark = np.clip(1 - rat - 0.02, 0, 0.75)
    dk = np.stack([cv2.distanceTransform((~layers[k]).astype(np.uint8), cv2.DIST_L2, 5) for k in prods])
    near = np.argmin(dk, 0)
    du = dk.min(0)
    band = 45
    taper = np.clip(1 - du / band, 0, 1) ** 1.1
    shadows = {}
    shade_w = np.clip(C.blur(((dh_ < 15) & (np.abs(ce_ - cb_) < 10)).astype(np.float64), 4) * 1.4 - 0.2, 0, 1)   # a shadow or a glow changes the
    for i, k in enumerate(prods):                                                                                     # brightness, not the hue
        env = (du <= band) & (near == i) & ~allfg
        s = 1 - C.blur(dark * taper * env * shade_w, 1.0)
        s[~C.dil(env, 1) | allfg] = 1
        shadows[k] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
    # lights: the brightening outside every product, near the lit lamps, as screen
    light = None
    if lamps_lit:
        env = light_env(ids, p) & ~np.isin(pl_ids, (10, 11))          # the glow on the wall round the shade and the cones; not the floor
        L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.45)
        glow_ok = np.clip(C.blur(((dh_ < 30) & (ce_ - cb_ < 22)).astype(np.float64), 3) * 1.4 - 0.2, 0, 1)   # a warm glow may add chroma
        wgt = (env & ~C.dil(allfg, 2)).astype(np.float64) * glow_ok        # a smooth glow: a normalised blur over the clean wall only
        Ls = np.stack([C.blur(L8[..., c] * wgt, 10) / np.maximum(C.blur(wgt, 10), 1e-3) for c in range(3)], -1)
        Ls[C.blur(wgt, 10) < 0.02] = 0
        soft_env = C.blur(env.astype(np.float64), 25)
        L8 = Ls * (soft_env * ~allfg)[..., None]
        light = L8
        rp["light_px"] = int((L8.max(2) > 0.003).sum())
    rec[p] = rp
    return e, layers, shadows, light, prods


def bed_labels(lab, ids, fg, prods):
    """the bed textiles: the throw by its colour (rust: C* > 15, h 35-62, L* < 66; the duvet's warm shade is h 69-72) in its largest piece near the clay band; the pillows
    (caramel, C* > 16) and the cushion (light, low chroma) near the headboard; the rest is the duvet"""
    Lh, Ch = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    out = np.full((H, W), prods.index(52))
    head = C.dil(np.isin(ids, (51, 53)), 45)
    rust = fg & (Ch > 15) & (hh > 35) & (hh < 62) & (Lh < 66) & ~(head & (np.arange(H)[:, None] < 850))
    rust = cv2.morphologyEx(rust.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(4)).astype(bool)
    rust = fill_holes(rust, 4000) & fg
    n, lb, st, _ = cv2.connectedComponentsWithStats(rust.astype(np.uint8), connectivity=8)
    near = C.dil(ids == 54, 160)
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 3000 and (near & (lb == i)).any()]
    rust = np.isin(lb, keep)
    pil = fg & head & (Ch > 16) & (hh > 40) & (hh < 66)
    pil = fill_holes(cv2.morphologyEx(pil.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool), 3000) & fg
    tex = np.sqrt(np.maximum(C.blur(Lh * Lh, 2) - C.blur(Lh, 2) ** 2, 0))          # the boucle's texture (the duvet fold reads 0.6)
    cus = fg & C.dil(ids == 53, 130) & (tex > 1.4) & (((Ch < 24) & (hh > 64)) | (Ch < 12)) & (Lh > 35) & (np.arange(H)[:, None] < 830)
    cus = cv2.morphologyEx(cus.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
    cus = cv2.morphologyEx(cus.astype(np.uint8), cv2.MORPH_OPEN, C.disk(3)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cus.astype(np.uint8), connectivity=8)
    if n > 1:
        cus = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cus = fill_holes(cus, 6000) & fg
    over_head = fg & C.dil(M.ids("MB1-plate") == 20, 1) & ~cus & (Ch > 12) & (hh < 68)   # caramel (h 55-64; the oat duvet's shade is h 75) in front of the headboard: a pillow
    lim = np.full(W, -1.0)                                     # no pillow in front of the line (X, 18.25, 0.52): the duvet's fold is there
    for X in np.linspace(-1.70, 0.30, 400):
        x, y = M.proj(X, 18.25, 0.52)
        xi = int(round(x))
        if 0 <= xi < W:
            lim[max(0, xi - 3):xi + 4] = np.maximum(lim[max(0, xi - 3):xi + 4], y)
    lim[lim < 0] = H
    rows = np.arange(H)[:, None]
    pil = (pil | over_head) & ~cus & (rows < lim[None, :] + 6)
    pil &= ~rust
    out[pil] = prods.index(51)
    out[cus] = prods.index(53)
    out[rust] = prods.index(54)
    return out


def hull(m):
    pts = cv2.findNonZero(m.astype(np.uint8))
    out = np.zeros((H, W), np.uint8)
    if pts is not None:
        cv2.fillConvexPoly(out, cv2.convexHull(pts), 1)
    return out.astype(bool)


def light_env(ids, p):
    """where a lamp's glow may be: round the floor lamp's shade (its upper part) and round each wall cone"""
    env = np.zeros((H, W), bool)
    for k in LAMPS.get(p, []):
        m = ids == k
        if k == 55:
            ys = np.nonzero(m.any(1))[0]
            m = m.copy()
            m[ys.min() + int(0.32 * (ys.max() - ys.min())):] = False      # the shade, not the pole
            env |= C.dil(m, 230)
        else:
            env |= C.dil(m, 170)
    return env


def right_labels(lab, fg, prods, lab_i, D):
    """the magazine holder by its own colours (the black tube, the cognac straps, the white pages) in a box round it: the model drew it
    wider than the clay, and its right arch is nearer the clay pot"""
    Lh, Ch = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    box = np.zeros((H, W), bool)
    box[1100:1470, 1940:2340] = True
    cols = np.arange(W)[None, :] * np.ones((H, 1))
    hold = box & (D > 7) & ((Lh < 26) & (Ch < 6) | (Ch > 28) & (hh > 38) & (hh < 70) | (Lh > 78) & (Ch < 9) & (cols < 2235))
    hold = cv2.morphologyEx(hold.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(4)).astype(bool)
    hold = fill_holes(hold, 3000) & box
    floorish = (Ch > 11) & (Ch < 26) & (hh < 67) & (Lh < 60) & (Lh > 20)        # the oak between the tubes and straps
    hold &= ~floorish
    pot = fg & (lab_i == prods.index(61)) & ~hold
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(hold.astype(np.uint8), connectivity=8)
    if n_ > 1:                                          # the holder is one object: its hull, so the floor seen through it is the edit's
        big = [i for i in range(1, n_) if st_[i, cv2.CC_STAT_AREA] >= 0.05 * st_[1:, cv2.CC_STAT_AREA].max()]
        hold = hull(np.isin(lb_, big))
    # the pot: its greige body and its soil near the clay pot, as one hull (rows of the pot only)
    near_pot = C.dil(M.ids("MB1") == 61, 60)
    potc = near_pot & (D > 5) & ((((hh > 55) & (Ch < 24) & (Lh > 38)) | (Lh < 30)) & ~hold)
    potc[:int(np.nonzero((M.ids("MB1") == 61).any(1))[0].min()) - 25] = False
    n2, lb2, st2, _ = cv2.connectedComponentsWithStats(potc.astype(np.uint8), connectivity=8)
    potm = hull(lb2 == 1 + int(np.argmax(st2[1:, cv2.CC_STAT_AREA]))) if n2 > 1 else potc
    out = lab_i.copy()
    out[potm & ~hold] = prods.index(61)
    out[hold & ~(lab_i == prods.index(55))] = prods.index(63)
    floor = np.isin(M.ids("MB1-plate"), (10, 11))               # on the floor, the planter is only the pot's greige (h > 67, C* < 14) or soil
    notpot = floor & (out == prods.index(61)) & ~((((hh > 67) & (Ch < 14)) | ((Lh > 52) & (Ch < 22)) | (Lh < 25)) & C.dil(M.ids("MB1") == 61, 25))
    out[notpot] = -1
    out[(lab_i == prods.index(63)) & ~hold & ~box] = prods.index(61) if pot.any() else out[(lab_i == prods.index(63)) & ~hold & ~box]
    return out, hold | potm


def fill_holes(m, max_area):
    inv = (~m).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lb[0], lb[-1], lb[:, 0], lb[:, -1]])))
    return m | np.isin(lb, [i for i in range(1, n) if i not in border and st[i, cv2.CC_STAT_AREA] < max_area])


def write_pass(p, e, layers, shadows, light, prods, man, rec):
    tc = toe_curve()
    man["layers"] = [l for l in man["layers"] if l.get("pass") != p]
    for k in prods:
        slot, pid, z, _, side = P[k]
        a = C.soft(layers[k])
        rgb = C.defringe(e, layers[k])
        if tc:
            lab = C.to_lab(rgb)
            lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
            rgb = np.clip(C.from_lab(lab), 0, 1)
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        name = pid + (f"-{side}" if side else "")
        lp, sp = os.path.join(ST, "layers", slot, name + ".png"), os.path.join(ST, "shadows", slot, name + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        s8 = C.q(shadows[k])
        Image.fromarray(s8).save(sp)
        ys, xs = np.nonzero(a8 > 0)
        man["layers"].append(dict(slot=slot, product=pid, z=z, shadow_z=z - 1, default=True, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()),
                                  bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if xs.size else None,
                                  sold=True, pass_=p, source=f"MB1 {p} (nano-banana-2 edit), cut in code (tools/mb1_compose.py)", **({"side": side} if side else {}),
                                  pass_name=p))
        man["layers"][-1]["pass"] = p
    man["light"] = [li for li in man["light"] if li.get("pass") != p]
    if light is not None:
        lp = os.path.join(ST, "light", f"{p}-lamps.png")
        Image.fromarray(C.q(light)).save(lp)
        man["light"].append(dict(file=os.path.relpath(lp, ST), z=90, blend="screen", pass_=p, pass_name=p,
                                 lamps=[P[k][0] + ("-" + P[k][4] if P[k][4] else "") for k in LAMPS[p]]))
        man["light"][-1]["pass"] = p
    man["layers"].sort(key=lambda l: (l["z"], l["slot"]))


def compose(man, rec):
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    a_all = np.zeros((H, W))
    for l in man["layers"]:
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        region |= (rgba[..., 3] > 0) | (s8 < 255)
        a_all = 1 - (1 - a_all) * (1 - rgba[..., 3] / 255)
    for li in man["light"]:
        L8 = np.asarray(Image.open(os.path.join(ST, li["file"]))).astype(np.float64)
        L8 = np.clip(np.rint(L8 * (1 - a_all)[..., None]), 0, 255).astype(np.uint8)
        out = C.light_one(out, L8)
        region |= L8.max(2) > 0
    o8 = C.q(out)
    Image.fromarray(o8).save(os.path.join(ST, "mb1-defaults.png"))
    x0, y0, x1, y1 = (int(round(v)) for v in M.FRAME)
    Image.fromarray(o8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, "mb1-defaults-frame.png"))
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum()),
                       rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    lab = C.to_lab(o8.astype(np.float64) / 255)
    rec["black_point_p05"] = round(float(np.percentile(lab[..., 0][M.frame_mask()], 0.5)), 2)
    return o8


def main(args):
    mp = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(mp)) if os.path.exists(mp) else dict(
        id="wm-master-mb1-2026-11-19", room="master", style="warm-modern", frame="MB1", canvas=[W, H], frame_box=list(M.FRAME), base="plate.png",
        camera=dict(M.CAM), compose="plate.png; per layer in z order: shadow (multiply), then the layer (straight alpha); lights (screen, z 90) "
                                    "times (1 - every alpha)", layers=[], light=[])
    rp = os.path.join(ST, "mb1-compose.json")
    rec = json.load(open(rp)) if os.path.exists(rp) else {}
    for p in args:
        if p == "compose":
            continue
        e, layers, shadows, light, prods = cut_pass(p, rec)
        write_pass(p, e, layers, shadows, light, prods, man, rec)
        np.save(os.path.join(M.SCR, f"{p}-locked.npy"), e.astype(np.float32))
    compose(man, rec)
    json.dump(man, open(mp, "w"), indent=1)
    json.dump(rec, open(rp, "w"), indent=1, default=str)
    print(json.dumps(man["rnd2"]), rec.get("black_point_p05"), json.dumps({p: {k: v for k, v in rec[p].items() if k not in ("lock",)} for p in args if p in rec})[:1500])


if __name__ == "__main__":
    main(sys.argv[1:])
