#!/usr/bin/env python3
"""extract.py: the layers of M0-W, split from ONE photograph (FB13 stage A step 6; proposal 3.2 items 5-6). Scratch -> out/stack/.

The base is the plate P (graded, registered to the hero): the empty room is one clean photograph in every state. Every product is
cut from the ONE hero H (graded; prep.py). What the products and the lamps do to the room is the hero over the plate:
  r = low-pass(H) / low-pass(P) outside every product (per channel, on the encoded values the engine blends; 2.5 px beside a product
      and in the leaf shadow's zone, 12 px elsewhere: the model re-drew the room's fine texture, so only the light is compared)
  d = min(r, 1): what the products take from the room (contact, cast shadow, occlusion)  -> each product's MULTIPLY layer
  g = max(r, 1): what the lamps give (wash, pool, glow)                                  -> each lamp's SCREEN layer
d is shared between the products by distance (each product's zone of influence; the olive's leaf shadow is the planter's), g between
the lamps by the clay's light maps. Outside every zone nothing is taken and nothing is given: the plate, pixel for pixel.
  each product = its pixels of H (straight alpha), with a feathered 4 px fringe of the hero's own room around it where it meets the
         room (its contact and its edge come with it), a solved anti-aliased edge where it meets another product, and what it hides
         of a lower product: the rug and the throw under the table from the hero rendered WITHOUT the table group (E2), the rug under
         the holder, the throw, the lamp and the pot from the rug's own rows, the table top under the bowl and the candle holders
         in-painted; a lower product's own pixels carry no shadow of a higher one (divided out, so the stack gives them back);
  the table's shadow on the rug and on the throw = low-pass(H) / low-pass(E2) (FB12-T: every table is a layer over the same rug).
Composed by the manifests' formula (base; per layer in z order: shadow multiply, then the layer; lights screen x (1 - every alpha)):
the products of the default stack are the hero's, pixel for pixel; the room between them is the plate in the hero's light."""
import json
import os

import cv2
import numpy as np
from PIL import Image

import hwlib as L

SP = L.SP
OUTP = os.path.join(L.OUT, "prep")
OUTS = os.path.join(L.OUT, "stack")
H_, W_ = L.H, L.W
ORDER = [("framed-art", 12), ("accent-sconces", 12), ("vase", 16), ("rug", 20), ("floor-lamp", 30), ("planter", 32), ("cushions", 55),
         ("coffee-table", 57), ("basket", 60), ("magazine-holder", 60), ("bowl", 65), ("candle-holders", 65), ("pendant", 80)]
PRODUCT = {"framed-art": "framed-art-aliexpress-frameless-minimalist-wall-art-631735", "accent-sconces": "accent-sconces-aliexpress-travertine-cylinder-walnut-choice",
           "vase": "vase-cj-textured-white-stoneware", "rug": "rug-cj-braided-wool-natural", "floor-lamp": "floor-lamp-cj-pleated-walnut-stem-158",
           "planter": "planter-cj-cement-ribbed-belly", "cushions": "set-B", "coffee-table": "coffee-table-idana-javorina-olia-natural",
           "basket": "basket-cj-jute-rope-cylinder", "magazine-holder": "magazine-holder-cj-gunmetal-leather-strap", "bowl": "bowl-cj-matte-black-bowl-20",
           "candle-holders": "candle-holders-cj-travertine-pedestal", "pendant": "pendant-cj-tiered-fabric-drum"}
RADIUS = {"framed-art": 34, "accent-sconces": 30, "vase": 70, "rug": 46, "floor-lamp": 80, "planter": 110, "cushions": 90, "coffee-table": 130,
          "basket": 70, "magazine-holder": 80, "bowl": 46, "candle-holders": 46, "pendant": 24}
LAMPS = ["accent-sconces", "floor-lamp", "pendant"]
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
ero = lambda m, r: cv2.erode(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def nblur(img, w, sigma):
    """normalised blur: the mean of img over w (0-1), -> (mean, weight); large sigmas on a 1/4 grid"""
    if sigma >= 12.0:
        f = 4
        hs, ws = img.shape[0] // f, img.shape[1] // f
        wi = cv2.resize(w, (ws, hs), interpolation=cv2.INTER_AREA)
        im = cv2.resize(img * (w[..., None] if img.ndim == 3 else w), (ws, hs), interpolation=cv2.INTER_AREA)
        num = cv2.GaussianBlur(im, (0, 0), sigma / f)
        den = cv2.GaussianBlur(wi, (0, 0), sigma / f)
        num = cv2.resize(num, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
        den = cv2.resize(den, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        num = cv2.GaussianBlur(img * (w[..., None] if img.ndim == 3 else w), (0, 0), sigma)
        den = cv2.GaussianBlur(w, (0, 0), sigma)
    return num / np.maximum(den[..., None] if img.ndim == 3 else den, 1e-5), den


def fill_scales(img, w, sigmas=(3.0, 10.0, 30.0, 90.0, 270.0)):
    """img where w says it is known; elsewhere the nearest known neighbourhood (growing scales)"""
    out = img.copy()
    done = w > 0.5
    for sg in sigmas:
        m, den = nblur(img, w, sg)
        take = (~done) & (den > 0.05)
        out[take] = m[take]
        done |= take
    return out


def ratio_field(A, B, w, near, s_small=2.5, s_large=12.0):
    """low-pass(A) / low-pass(B) over w; the small scale near the products (their contact shadows), the large one elsewhere"""
    As, d1 = nblur(A, w, s_small)
    Bs, _ = nblur(B, w, s_small)
    Al, d2 = nblur(A, w, s_large)
    Bl, _ = nblur(B, w, s_large)
    rs = np.clip(As / np.maximum(Bs, 0.012), 0.3, 2.0)
    rl = np.clip(Al / np.maximum(Bl, 0.012), 0.3, 2.0)
    r = np.exp(np.log(rl) * (1 - near[..., None]) + np.log(rs) * near[..., None])
    known = (w > 0.5).astype(np.float32)
    return fill_scales(r, known)


def main():
    os.makedirs(OUTS, exist_ok=True)
    P = L.rd(os.path.join(OUTP, "plate.png"))
    Hh = L.rd(os.path.join(OUTP, "hero.png"))
    NT = L.rd(os.path.join(OUTP, "notable.png"))
    mk = {k: v > 127 for k, v in np.load(os.path.join(OUTP, "masks.npz")).items()}
    v2 = np.load(os.path.join(OUTP, "paste-masks.npz"))["v2"] > 0
    maps = np.load(os.path.join(OUTP, "maps.npz"))
    idx_p = maps["idx_p"]
    hull = np.load(os.path.join(OUTP, "rug-hull.npy")) > 0
    log = dict(order=ORDER)
    names = [k for k, _ in ORDER]
    # ---- the hidden part of the rug: where a higher product stands on it or hangs before it
    tgrp = mk["coffee-table"] | mk["bowl"] | mk["candle-holders"]
    sofa_p = dil(idx_p == 1, 3)
    others_r = np.any(np.stack([mk[k] for k in names if k != 'rug']), 0)
    # the rug's far edge is where the HERO's sofa plinth hides it: one straight line, fitted to the top of the hero's visible rug along
    # the sofa (the plate's plinth stands a few px off the hero's: the hero's line is the rug's)
    rv0 = mk['rug']
    pts = []
    for x in range(1080, 2200, 2):
        ys_ = np.where(rv0[1300:1470, x])[0]
        if len(ys_) and not others_r[max(1300 + ys_.min() - 4, 0), x] and not mk['armchair'][1300 + ys_.min() - 4, x]:
            pts.append((x, 1300 + ys_.min()))
    pts = np.float64(pts)
    keep_ = np.ones(len(pts), bool)
    for _ in range(3):
        ca, cb = np.polyfit(pts[keep_, 0], pts[keep_, 1], 1)
        keep_ = np.abs(ca * pts[:, 0] + cb - pts[:, 1]) < 3.0
    yy_, xx_ = np.mgrid[0:H_, 0:W_]
    span = (xx_ >= pts[keep_, 0].min() - 30) & (xx_ <= pts[keep_, 0].max() + 30)
    below_line = yy_ >= (ca * xx_ + cb)
    log['rug_far_edge_line'] = dict(slope=round(float(ca), 5), y_at_x1500=round(float(ca * 1500 + cb), 1), points=int(keep_.sum()))
    over_rug = (tgrp | mk['magazine-holder'] | mk['throw'] | mk['floor-lamp'] | mk['planter']) & hull & ~mk['armchair'] & (below_line | ~span)
    over_rug &= ~(span & ~below_line)
    over_rug = cv2.morphologyEx(over_rug.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    rug_vis = mk['rug']
    rug_full = cv2.morphologyEx((rug_vis | over_rug).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    # the rug's own outline: the segment map's ragged edge made regular (closing then opening, 9 px); along the sofa it is the line
    el9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    reg = cv2.morphologyEx(cv2.morphologyEx(rug_full.astype(np.uint8), cv2.MORPH_CLOSE, el9), cv2.MORPH_OPEN, el9).astype(bool)
    rug_full = (reg & ~mk['armchair']) | (rug_full & others_r)
    rug_full = (rug_full | (hull & span & below_line & ~mk['armchair'] & dil(rug_full, 24))) & ~(span & ~below_line)
    rug_before = rug_full.copy()
    gap = np.zeros_like(rug_full)
    gap_under = np.zeros_like(rug_full)
    filled_to_line = rug_full & ~rv0 & ~others_r
    log['rug_filled_to_the_line_px'] = int(filled_to_line.sum())
    rug_vis = rug_full & ~others_r
    mk['rug'] = rug_vis
    # the throw's end and the cushions behind the table
    cush_vis = mk["cushions"]
    hard = dict(mk)
    hard["rug"] = rug_full
    # stray leaves and branch tips outside the segment map: what is not the room there (the hero against its own room around the
    # product, low-passed), connected to the product, up to 26 px from the olive's crown and 12 px from the vase's branch
    prod0 = np.any(np.stack([mk[k] for k in names]), 0)
    free0 = (~dil(prod0, 4)).astype(np.float32)
    room = fill_scales(nblur(Hh, free0, 5.0)[0], free0, (5.0, 15.0))
    resid = np.abs(cv2.GaussianBlur(Hh, (0, 0), 0.7) - room).max(2)
    for k, reach, cut in (("planter", 26, 230), ("vase", 12, 150)):
        ys_, xs_ = np.where(mk[k])
        top = np.zeros((H_, W_), bool)
        top[:ys_.max() - cut] = True
        cand = dil(mk[k] & top, reach) & top & ~prod0 & (resid > 0.085) & (idx_p != 3)
        n_, lb_ = cv2.connectedComponents((cand | (mk[k] & top)).astype(np.uint8), connectivity=8)
        keep_ids = np.unique(lb_[mk[k] & top])
        add = np.isin(lb_, keep_ids[keep_ids > 0]) & cand
        add = dil(add, 1) & ~prod0
        hard[k] = mk[k] | add
        mk[k] = hard[k]
        log.setdefault("mask_grown_px", {})[k] = int(add.sum())
    # ---- alphas (straight): the product, a feathered fringe of the hero's own room where it meets the room (4 px), and the hard
    # mask's anti-aliased edge where it meets another product
    FR = 4.0
    anyprod = np.any(np.stack([hard[k] for k in names]), 0)
    A = {}
    for k in names:
        aa = cv2.GaussianBlur(hard[k].astype(np.float32), (0, 0), 0.8)
        aa[~dil(hard[k], 2)] = 0
        dk = cv2.distanceTransform((~hard[k]).astype(np.uint8), cv2.DIST_L2, 5)
        fr = np.clip(1 - (dk - 0.5) / FR, 0, 1) ** 1.5
        others = anyprod & ~hard[k]
        fr_ok = ~dil(others, 1) & (idx_p != 3 if k in ("basket", "vase") else True)      # the armchair stands before the basket and the vase
        a = np.where(hard[k], 1.0, np.where(fr_ok, fr, np.minimum(aa, 0.999)))
        if k == "rug":
            a = np.where(hard[k], 1.0, np.minimum(aa, 0.999))                          # the rug lies flat: its own cut edge
        a[a < 0.02] = 0
        A[k] = a.astype(np.float32)
    U = np.max(np.stack([A[k] for k in names]), 0)
    Uvis = np.max(np.stack([cv2.GaussianBlur(mk[k].astype(np.float32), (0, 0), 0.8) for k in names]), 0)
    prod_hard = np.any(np.stack([mk[k] for k in names]), 0)
    free = (~dil(prod_hard, 2)).astype(np.float32)                  # the room, no product pixel
    dist_any = cv2.distanceTransform((~prod_hard).astype(np.uint8), cv2.DIST_L2, 5)
    near = np.exp(-dist_any / 10.0).astype(np.float32)
    # ---- the hero over the plate, outside the products
    ysp, xsp = np.where(mk["planter"])
    yy0, xx0 = np.mgrid[0:H_, 0:W_].astype(np.float32)
    leaf_zone = (np.clip((xx0 - (float(xsp.max()) - 60)) / 40, 0, 1) * np.clip((1310 - xx0) / 40, 0, 1) * np.clip((yy0 - 380) / 40, 0, 1)
                 * np.clip((1000 - yy0) / 60, 0, 1) * (idx_p == 5)).astype(np.float32)
    near = np.maximum(near, leaf_zone)
    r = ratio_field(Hh, np.maximum(P, 0.004), free, near)
    d = np.minimum(r, 1.0)
    g = np.maximum(r, 1.0)
    # the products' zones of influence
    Wk = {}
    for k in names:
        dk = cv2.distanceTransform((~mk[k]).astype(np.uint8), cv2.DIST_L2, 5)
        Wk[k] = np.clip(1 - dk / RADIUS[k], 0, 1).astype(np.float32) ** 1.5
    # the olive's leaf shadow on the plaster, between the tree and the first frame: the planter's (the sun comes from the left)
    zone = leaf_zone
    Wk["planter"] = np.maximum(Wk["planter"], zone.astype(np.float32))
    Wsum = np.sum(np.stack([Wk[k] for k in names]), 0)
    Wtot = np.clip(Wsum, 0, 1)
    d_eff = d ** Wtot[..., None]
    # the lamps' zones (the clay's light maps, each normalised to its 99.5th percentile), with the room's own registration
    q = {l: np.clip(maps["light-" + l], 0, 1).astype(np.float32) for l in LAMPS}
    qsum = np.sum(np.stack([q[l] for l in LAMPS]), 0)
    Q = np.clip((qsum - 0.01) / 0.05, 0, 1)
    Q = Q * Q * (3 - 2 * Q)
    g_eff = g ** Q[..., None]
    log["influence"] = dict(shadow_zone_px=int((Wtot > 0).sum()), light_zone_px=int((Q > 0).sum()), radius_px=RADIUS,
                            d_min=round(float(d_eff.min()), 3), g_max=round(float(g_eff.max()), 3))
    # ---- the base: the plate
    base8 = np.clip(np.rint(P * 255), 0, 255).astype(np.uint8)
    base = base8.astype(np.float32) / 255.0
    # ---- the table's shadow on the lower products (the rug, the throw): the hero over the hero without the table group
    zt = (v2 & dil(tgrp, 110)).astype(np.float32)
    zt = np.clip(cv2.GaussianBlur(cv2.erode(zt, np.ones((61, 61), np.uint8)), (0, 0), 14.0), 0, 1)
    lower = (rug_full | cush_vis) & ~tgrp
    wl = (lower & ~dil(tgrp, 2) & v2 & ~dil(mk["magazine-holder"] | mk["planter"] | mk["floor-lamp"], 2)).astype(np.float32)
    near_t = np.exp(-cv2.distanceTransform((~tgrp).astype(np.uint8), cv2.DIST_L2, 5) / 12.0).astype(np.float32)
    rt = ratio_field(Hh, np.maximum(NT, 0.004), wl, near_t, 3.0, 9.0)
    rtl = np.clip(nblur(Hh, wl, 9.0)[0] / np.maximum(nblur(NT, wl, 9.0)[0], 0.012), 0.2, 4.0)
    rtl = fill_scales(rtl, (wl > 0.5).astype(np.float32))
    gate = np.clip((1 - rtl.mean(2) - 0.05) / 0.06, 0, 1)                     # only where the table really darkens (5 % and more)
    gate = cv2.morphologyEx(gate.astype(np.float32), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    gate = cv2.GaussianBlur(gate.astype(np.float32), (0, 0), 3.0)
    S_table_low = np.minimum(rt, 1.0) ** (zt * gate)[..., None]
    # ---- the shadow (multiply) map of every product
    S = {}
    for k in names:
        share = Wk[k] / np.maximum(Wsum, 1e-4)
        S[k] = d_eff ** (share[..., None])
    lower_soft = cv2.GaussianBlur(lower.astype(np.float32), (0, 0), 1.0)[..., None]
    S["coffee-table"] = S["coffee-table"] * (1 - lower_soft) + S_table_low * lower_soft
    S8 = {k: np.clip(np.rint(S[k] * 255), 0, 255).astype(np.uint8) for k in names}
    for k in names:                                                    # no shadow where it would be under 1 level: 255
        S8[k][(S8[k] >= 254).all(2)] = 255
    # ---- the lamps' light (screen) on the plate in the products' shade: screen(P d, S) = P d g, per pixel (a dark surface takes
    # little, a light one much: the gain is the lamps', the pixel is the plate's)
    Bn = np.clip(base * d_eff, 0, 0.995)
    lit = np.clip(Bn * g_eff, 0, 0.999)
    St = np.clip(1 - (1 - lit) / np.maximum(1 - Bn, 5e-3), 0, 1)
    St = St * (Q[..., None] > 0)
    Lt, Lt8 = {}, {}
    for l in LAMPS:
        share = q[l] / np.maximum(qsum, 1e-4)
        Lt[l] = 1 - (1 - St) ** share[..., None]
        Lt8[l] = np.clip(np.rint(Lt[l] * 255), 0, 255).astype(np.uint8)
        Lt8[l][(Lt8[l] <= 1).all(2)] = 0
    # ---- the layers' colours, bottom up, so that the 8-bit stack gives the hero back
    keep = np.ones((H_, W_), np.float32)
    for k in names:
        keep *= (1 - A[k])
    lt_tot = 1 - np.prod(np.stack([1 - Lt8[l].astype(np.float32) / 255.0 * keep[..., None] for l in LAMPS]), 0)
    X = np.clip(1 - (1 - Hh) / np.maximum(1 - lt_tot, 5e-3), 0, 1)        # the stack before the lights
    comp = base.copy()
    layers = {}
    # what each product hides of a lower one
    rugC = Hh.copy()
    # the rug's own rows for what the holder, the throw, the lamp and the pot hide (the weave runs along the rows): reflect about the hole
    hole = rug_full & ~rug_vis & ~tgrp
    src_ok = rug_vis & ~dil(tgrp | mk["magazine-holder"] | mk["throw"] | mk["floor-lamp"] | mk["planter"], 6)
    # divide the table's shadow out of the visible rug first (the rug's own layer carries no table shadow)
    Stl = np.ones((H_, W_, 3), np.float32)
    for k in names[names.index("rug") + 1:]:
        Stl = Stl * np.clip(S8[k].astype(np.float32) / 255.0, 0.05, 1.0)
    rug_clean = np.clip(X / Stl, 0, 1)
    lab_r = L.to_lab(rug_clean)
    lo, _ = nblur(lab_r, src_ok.astype(np.float32), 18.0)
    lo = fill_scales(lo, src_ok.astype(np.float32), (18.0, 54.0, 160.0))
    det = np.where(src_ok[..., None], lab_r - lo, 0)
    filled = det.copy()
    for y in np.where(hole.any(1))[0]:
        hx = np.where(hole[y])[0]
        ok = np.where(src_ok[y])[0]
        if len(ok) < 40:
            continue
        runs = np.split(hx, np.where(np.diff(hx) > 1)[0] + 1)
        for run in runs:
            a0, b0 = run[0], run[-1]
            n_ = b0 - a0 + 1
            left = ok[ok < a0]
            right = ok[ok > b0]
            src = None
            if len(right) >= n_ and (right[:n_] == np.arange(b0 + 1, b0 + 1 + n_)).all():
                src = (b0 + 1 + n_ - 1) - np.arange(n_)                      # mirror of the run to its right
            elif len(left) >= n_ and (left[-n_:] == np.arange(a0 - n_, a0)).all():
                src = (a0 - 1) - np.arange(n_)
            elif len(right) >= 8:
                src = right[np.arange(n_) % len(right)]
            elif len(left) >= 8:
                src = left[::-1][np.arange(n_) % len(left)]
            if src is not None:
                filled[y, a0:b0 + 1] = det[y, src]
    rug_fill = L.from_lab(lo + filled)
    # under the table group: the hero without the table (E2), brought to the clean rug's level around it
    und = tgrp & rug_full
    lv = fill_scales(np.clip(nblur(rug_clean, (src_ok & v2).astype(np.float32), 14.0)[0] / np.maximum(nblur(NT, (src_ok & v2).astype(np.float32), 14.0)[0], 0.01), 0.7, 1.4),
                     (src_ok & v2).astype(np.float32), (14.0, 42.0, 120.0))
    NTl = np.clip(NT * lv, 0, 1)
    hid_rug = {"hole": hole, "und": und}
    after = {}
    acc = np.ones((H_, W_, 3), np.float32)
    for k in reversed(names):
        after[k] = acc.copy()
        acc = acc * np.clip(S8[k].astype(np.float32) / 255.0, 0.05, 1.0)
    for k in names:
        a = A[k]
        Sk = S8[k].astype(np.float32) / 255.0
        comp_s = np.rint(comp * 255 * Sk) / 255.0
        Tk = np.clip(X / after[k], 0, 1)                               # the stack at this layer: later shadows not yet on it
        rug_clean = Tk
        C = Tk.copy()
        sel = a > 0.02
        solve = np.clip((Tk - (1 - a[..., None]) * comp_s) / np.maximum(a[..., None], 0.02), 0, 1)
        # the fringe over the room keeps the hero's own pixels; the edge against another product is solved (the stack gives the hero)
        edge = sel & (a < 0.999) & dil(anyprod & ~hard[k], 1)
        strong = edge & (a >= 0.3)
        C[strong] = solve[strong]
        weak = edge & (a < 0.3)
        if weak.any():                                                 # a thin edge: the product's own colour beside it
            inner = (hard[k] & (a >= 0.999)).astype(np.float32)
            nb, den = nblur(Tk, inner, 2.0)
            C[weak] = np.where(den[weak][:, None] > 0.02, nb[weak], solve[weak])
        if k == "rug":
            C = np.where((rug_vis & ~dil(~rug_vis & rug_full, 1))[..., None], np.where(edge[..., None], C, rug_clean), C)
            C = np.where(hole[..., None], rug_fill, C)
            Cg = C.copy()
            todo = gap | gap_under
            for i_ in range(1, 17):
                below = np.zeros_like(rug_before)
                below[:-i_] = rug_before[i_:]
                hit = todo & below
                ys_, xs_ = np.where(hit)
                ysrc = np.clip(ys_ + 2 * i_ - 1, 0, H_ - 1)
                ysrc = np.where(rug_before[ysrc, xs_], ysrc, ys_ + i_)
                Cg[ys_, xs_] = np.where(hole[ysrc, xs_][:, None], rug_fill[ysrc, xs_], np.where(und[ysrc, xs_][:, None], NTl[ysrc, xs_], Tk[ysrc, xs_]))
                todo &= ~hit
            C = np.where((gap | gap_under)[..., None], Cg, C)
            C = np.where(und[..., None], NTl, C)
            # a soft seam between what the hero shows and what was filled
            seam = cv2.GaussianBlur((hole | und).astype(np.float32), (0, 0), 1.5)[..., None]
            Cf = np.where(und[..., None], NTl, rug_fill)
            C = np.where((rug_vis & ~edge)[..., None], rug_clean * (1 - seam) + Cf * seam, C)
        if k == "cushions":
            # the throw and the cushions where the table stands before them: the hero without the table; the table's shadow divided out
            hid = tgrp & dil(cush_vis, 40) & v2 & ~rug_full
            pass
        if k == "coffee-table":
            hidden = (mk["bowl"] | mk["candle-holders"])
            if hidden.any():
                src8 = np.clip(np.rint(C * 255), 0, 255).astype(np.uint8)
                C = np.where(dil(hidden, 2)[..., None], cv2.inpaint(src8, dil(hidden, 3).astype(np.uint8), 4, cv2.INPAINT_TELEA).astype(np.float32) / 255.0, C)
            a = np.maximum(a, cv2.GaussianBlur((hard[k] | dil(hidden, 1)).astype(np.float32), (0, 0), 0.8) * dil(hidden, 2))
            A[k] = a
        C8 = np.clip(np.rint(C * 255), 0, 255).astype(np.uint8)
        a8 = np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)
        C8[a8 == 0] = 0
        layers[k] = np.dstack([C8, a8])
        af = a8.astype(np.float32)[..., None] / 255.0
        comp = (np.rint(C8.astype(np.float32) * af) + np.rint(comp_s * 255) * (1 - af)) / 255.0
        comp = np.rint(comp * 255) / 255.0
    # the cushions' layer under the table: a second pass is not needed for the default frame (the table covers it); the hidden part of
    # the throw comes from E2 so that another table shows the throw's end
    hid = tgrp & v2 & ~rug_full & dil(mk["throw"], 60)
    throw_nt = hid & (np.abs(L.to_lab(NT)[..., 1] - float(np.median(L.to_lab(Hh)[..., 1][mk["throw"]]))) < 6) & (L.to_lab(NT)[..., 0] < 55)
    throw_nt = cv2.morphologyEx(throw_nt.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    throw_nt = cv2.morphologyEx(throw_nt, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(throw_nt, connectivity=8)
    throw_nt = (lb_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))) if n_ > 1 else throw_nt.astype(bool)
    if throw_nt.sum() > 200:
        lay = layers["cushions"].copy()
        a_new = np.clip(np.rint(cv2.GaussianBlur(throw_nt.astype(np.float32), (0, 0), 0.8) * 255), 0, 255).astype(np.uint8)
        put = a_new > lay[..., 3]
        lay[..., :3][put] = np.clip(np.rint(NT[put] * 255), 0, 255).astype(np.uint8)
        lay[..., 3][put] = a_new[put]
        layers["cushions"] = lay
        log["throw_under_table_px"] = int(throw_nt.sum())
    # ---- write
    Image.fromarray(base8).save(os.path.join(OUTS, "base.png"))
    np.savez_compressed(os.path.join(OUTS, "hard.npz"), **{k: hard[k] for k in names})
    for k in names:
        Image.fromarray(layers[k]).save(os.path.join(OUTS, f"layer-{k}.png"))
        Image.fromarray(S8[k]).save(os.path.join(OUTS, f"shadow-{k}.png"))
    for l in LAMPS:
        Image.fromarray(Lt8[l]).save(os.path.join(OUTS, f"light-{l}.png"))
    np.savez_compressed(os.path.join(OUTS, "zones.npz"), Wtot=(Wtot * 255).astype(np.uint8), Q=(Q * 255).astype(np.uint8),
                        rug_full=rug_full, zt=(zt * 255).astype(np.uint8))
    log["px"] = {k: dict(alpha=int((layers[k][..., 3] > 0).sum()), shadow=int((S8[k] < 255).any(2).sum())) for k in names}
    log["light_px"] = {l: int((Lt8[l] > 0).any(2).sum()) for l in LAMPS}
    log["rug"] = dict(visible_px=int(rug_vis.sum()), full_px=int(rug_full.sum()), under_table_from_E2_px=int(und.sum()), rows_filled_px=int(hole.sum()))
    json.dump(log, open(os.path.join(OUTS, "extract.json"), "w"), indent=1)
    print(json.dumps(log)[:2500])


if __name__ == "__main__":
    main()
