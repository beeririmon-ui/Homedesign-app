#!/usr/bin/env python3
"""
kd_cut2.py: the cut of the mask-edit passes, second version (render-agent, resumed session, 2026-11-20; 0 tokens).
Why a second version: at x2 the first cut (compose_edits.cut_pass) left a pale halo round the olive sprigs, chopped the rims of the iron
candle dishes (a pixel claimed by the runner and a dish went to the nearer clay region, often the runner) and gave the runner a ragged
end where the edit had draped it over the table end. The lock, the gain field (MP-I1), the first masks and the light layer are the
first version's; what changes:
  1. overlaps: a pixel claimed by two products goes to the one on top (the higher z; STACK: the candles and the vase stand on the
     runner, the dispenser on the tray), only then to the nearer clay region;
  2. edges: known-background matting. Per product, the edit's own background is inpainted under it (Bk); the foreground colour F is the
     product's inner colour, spread outward; in a 2 px band the alpha is the projection of (e - Bk) on (F - Bk), and the colour is
     unmixed, (e - (1 - a) Bk) / a. Over the plate this gives the edit back at the edge, with no halo and no fringe. Where F and Bk are
     too close to separate (a white vase on pale plaster), the first version's soft alpha stays;
  3. thin fillers (the olive, the eucalyptus): the same matte over the whole filler, from the leaves' own colour;
  4. a parent under a child (the runner under the candles and the vase, the tray under the dispenser) is filled under and round the
     child from its own pixels further out, so the child's contact shadow is its own shadow layer and is not baked twice;
  5. shadows: per product, the edit's background against what lies under it (the plate, or the plate with the parent), on the
     product's support surfaces only (kd_fixes.SUPPORT), in a band, to the nearest product;
  6. the product-specific fixes (kd_fixes2): the runner's footprint from the clay (140 x 40, straight hems, never draped), the
     pendant's shade at the card's size and its 30 cm rod with the thin suspension line above (the SKU drawing), the olive scaled
     about the vase mouth to Z 1.20 at most (7.5).
  python3 kd_cut2.py cut <pass> ...      (then: python3 compose_edits.py project)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
import compose_edits as CE  # noqa: E402
from kd_passes import PASSES, PRODUCTS, FILLERS, VARIANTS, owner  # noqa: E402
import kd_fixes as FX  # noqa: E402
import kd_fixes2 as FX2  # noqa: E402

C = K.C
H, W = K.H, K.W
ST = K.ST
STACK = {55: 52, 53: 52, 72: 71}          # child: parent
SUB = {72: 1}                              # within one slot and z, the child is composed after the parent
THIN = {54: 53, 59: 58}                    # thin fillers: filler id -> owner
NO_GROW = {50, 52, 57, 60, 53, 76, 70}             # their geometry comes from the clay or a fix (pendant, runner, curtain box, bench pad, vase)
GROW = {71: 70, 72: 70, 74: 50, 73: 50}
# a colour cut where the edit relit the ground under the product (the niche's walnut came back lighter): the pale canisters and their
# bamboo lids against the walnut, inside the niche
# WM-G1 on the layers: after the plate's toe (MP-I2), a soft floor so no product pixel is under L* 11, and no shadow takes the plate
# under it (the sRGB multiply of the compositor: 0.12 is about L* 11 on a grey)
BP_FLOOR = ([0.0, 11.0, 16.0, 100.0], [11.0, 12.5, 16.0, 100.0])
SHADOW_FLOOR_SRGB = 0.12
COLOUR_CUT = {76: dict(box=(1725, 560, 1960, 760), L_min=54.0)}
# the sink set of E-left r1: the model drew the tray and the dispenser about 1.7x their size and off the placeholders, sand on sand;
# the group is the edit's strong change in the box (shading excluded), split by rows and colour: the tray is the dark band at the
# bottom, the dispenser everything above it and its sand base on the tray (then kd_fixes2.size_fix puts the group on the clay)
SINK_BOX = (480, 590, 690, 756)


def nconv_small(v, w, s):
    """normalised convolution at a small sigma, channel-wise"""
    nb = cv2.GaussianBlur(w.astype(np.float32), (0, 0), s)
    if v.ndim == 3:
        out = np.stack([cv2.GaussianBlur((v[..., c] * w).astype(np.float32), (0, 0), s) for c in range(3)], -1) / np.maximum(nb[..., None], 1e-6)
    else:
        out = cv2.GaussianBlur((v * w).astype(np.float32), (0, 0), s) / np.maximum(nb, 1e-6)
    return out.astype(np.float64), nb.astype(np.float64)


def spread(v, w, sigmas=(2.0, 5.0, 12.0, 30.0)):
    """the colour of the weighted pixels, spread outward (finest scale first)"""
    out = np.zeros_like(v, dtype=np.float64)
    have = np.zeros(v.shape[:2])
    for s in sigmas:
        val, nb = nconv_small(v, w, s)
        a = np.clip(nb / 0.2, 0, 1)
        out = out + (val * (a * (1 - have))[..., None] if v.ndim == 3 else val * a * (1 - have))
        have = have + a * (1 - have)
    return out / np.maximum(have, 1e-6)[..., None] if v.ndim == 3 else out / np.maximum(have, 1e-6)


def inpaint(img, region, radius=6):
    """img (float 0-1, HxWx3) with the region filled from round it (Telea, per channel, on the region's box)"""
    ys, xs = np.nonzero(region)
    if not ys.size:
        return img.copy()
    y0, y1, x0, x1 = max(0, ys.min() - 30), min(H, ys.max() + 31), max(0, xs.min() - 30), min(W, xs.max() + 31)
    out = img.copy()
    m = region[y0:y1, x0:x1].astype(np.uint8)
    for c in range(3):                                       # 16-bit (OpenCV's float path returns garbage here)
        ch = np.clip(np.rint(img[y0:y1, x0:x1, c] * 65535), 0, 65535).astype(np.uint16)
        out[y0:y1, x0:x1, c] = cv2.inpaint(ch, m, radius, cv2.INPAINT_TELEA).astype(np.float64) / 65535
    return out


def matte(e, fg, Bk, r_in=2, r_out=2, sure=None, f_sig=(2.0, 5.0, 12.0)):
    """known-background matte of fg on the edit e over the background Bk: alpha, colour"""
    sure = C.ero(fg, r_in) if sure is None else sure
    if sure.sum() < 12:
        sure = fg.copy()
    outer = C.dil(fg, r_out)
    band = outer & ~sure
    F = spread(e, sure.astype(np.float64), f_sig)
    dFB = F - Bk
    den = (dFB ** 2).sum(-1)
    a = np.clip(((e - Bk) * dFB).sum(-1) / np.maximum(den, 1e-6), 0, 1)
    sep = np.sqrt(den)
    t = np.clip((sep - 0.04) / 0.06, 0, 1)                   # 0.04-0.10 in sRGB distance: from the soft binary alpha to the matte
    a_bin = C.soft(fg)
    a = t * a + (1 - t) * a_bin
    a = np.where(sure, 1.0, np.where(band, a, 0.0))
    a = np.where(a < 0.04, 0.0, a)
    col = (e - (1 - a[..., None]) * Bk) / np.maximum(a[..., None], 1e-3)
    col = np.where((a > 0.3)[..., None], np.clip(col, 0, 1), F)
    col = np.where(sure[..., None], e, col)
    return a, np.clip(col, 0, 1)


def first_masks(p, J, rec):
    """the first version's lock, gain field and masks (compose_edits.cut_pass up to the overlap rule), with the overlap rule of 1."""
    P = PASSES[p]
    fr = P["frame"]
    ids = K.ids(fr)
    pl_ids = K.ids(f"{fr}-plate")
    base = C.load(os.path.join(ST, J["base"]))
    variant = P.get("variant", False)
    prods = sorted({owner(k) for k in P["ids"]})
    zones = {}
    for k in prods:
        z = np.zeros((H, W), bool)
        for j in CE.product_ids(k):
            z |= C.dil(ids == j, CE.FILLER_PAD.get(j, CE.PAD.get(k, 14)))
        if k == 50:
            z |= C.box_mask([J.get("pendant_box", (640, 0, 1190, 480))])
        if k == 57:                                   # the curtain: the edit drew the panel wider than the clay's stack (kept, flagged)
            z |= C.box_mask([J.get("curtain_box", (340, 0, 700, 1110))])
        zones[k] = z
    zone = np.zeros((H, W), bool)
    for z in zones.values():
        zone |= z
    stable = C.ero(np.isin(pl_ids, CE.ARCH), 3) & ~C.dil(zone, 40) & K.frame_mask()
    e, rl = K.ecc_lock(os.path.join(ST, J["raw"]), os.path.join(ST, J["input"]), stable)
    lampenv = CE.light_env(ids, P["lamps"])
    keep = ~C.dil(zone, 40) & ~lampenv
    g = C.gain_field(e, base, keep)
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    diff_base = base
    if variant:                                   # a variant against the plate with the lamps' light (not against the default lamp)
        diff_base = C.load(os.path.join(ST, f"plate-{fr}.png"))
        for li in J.get("lights", []):
            diff_base = C.light_one(diff_base, np.asarray(Image.open(os.path.join(ST, li))))
    lab_e, lab_b = C.to_lab(e), C.to_lab(diff_base)
    d = np.linalg.norm(C.blur(lab_e, 1.0) - C.blur(lab_b, 1.0), axis=-1)
    out_d = d[keep & K.frame_mask()]
    rp = dict(lock=rl, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
              dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(out_d, [50, 95])], products={}, cut="kd_cut2")
    lab_e0, lab_b0 = C.blur(lab_e, 1.5), C.blur(lab_b, 1.5)
    ce_, cb_ = np.hypot(lab_e0[..., 1], lab_e0[..., 2]), np.hypot(lab_b0[..., 1], lab_b0[..., 2])
    he_, hb_ = np.degrees(np.arctan2(lab_e0[..., 2], lab_e0[..., 1])), np.degrees(np.arctan2(lab_b0[..., 2], lab_b0[..., 1]))
    dh_ = np.abs((he_ - hb_ + 180) % 360 - 180)
    same = ((np.abs(lab_e0[..., 1] - lab_b0[..., 1]) < 4) & (np.abs(lab_e0[..., 2] - lab_b0[..., 2]) < 5)) | ((dh_ < 12) & (np.abs(ce_ - cb_) < 8))
    # grow: where the model drew a product off its placeholder or larger, the zone follows the edit's own change that touches it
    allclay = {k: np.isin(ids, CE.product_ids(k)) for k in prods}
    for k in prods:
        if variant or k in NO_GROW:
            continue
        others = np.zeros((H, W), bool)
        for j in prods:
            if j != k:
                others |= C.dil(allclay[j], 4)
        reach = C.dil(allclay[k], GROW.get(k, 60)) & ~others & K.frame_mask()
        thr_g = 5.0 if k in CE.PALE else 6.0
        big = (d > thr_g) & reach & ~(same & (lab_e0[..., 0] < lab_b0[..., 0]))
        big = cv2.morphologyEx(big.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        n_, lb_ = cv2.connectedComponents(big.astype(np.uint8), connectivity=8)
        hit = set(np.unique(lb_[big & zones[k]])) - {0}
        grown = np.isin(lb_, list(hit))
        zones[k] |= C.dil(grown, 6) & reach
        rp.setdefault("grown_px", {})[str(k)] = int((grown & ~zones[k]).sum() + grown.sum())
    if 57 in zones:                                   # the curtain never takes the chairs or the table
        zones[57] &= ~C.dil(np.isin(pl_ids, (20, 21, 22, 23, 24)), 2)
    layers = {}
    if 71 in prods and 72 in prods and p == "E-left":
        bx = C.box_mask([SINK_BOX])
        U = bx & (d > 8) & ~(same & (lab_e0[..., 0] < lab_b0[..., 0]))
        U = cv2.morphologyEx(U.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        n_, lb_, st_, _ = cv2.connectedComponentsWithStats(U.astype(np.uint8), connectivity=8)
        big_ = [i for i in range(1, n_) if st_[i, cv2.CC_STAT_AREA] > 150]
        U = CE.fill_holes(np.isin(lb_, big_), 4000)
        dark = U & (lab_e[..., 0] < 45)
        rows = dark.sum(1)
        ys_ = np.nonzero(U.any(1))[0]
        yb = ys_.max()
        r_ = np.nonzero(rows[: yb + 1] > 0.5 * rows.max())[0]
        top = r_.min() if r_.size else yb - 15
        tray = U & (np.arange(H)[:, None] >= top) & ~(U & (lab_e[..., 0] > 52) & (np.arange(H)[:, None] < yb - 4))
        tray = cv2.morphologyEx(tray.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        layers[71] = tray
        layers[72] = U & ~tray
        rp["sink_cut"] = dict(box=list(SINK_BOX), group_px=int(U.sum()), tray_top_row=int(top), bottom_row=int(yb),
                              tray_px=int(tray.sum()), dispenser_px=int((U & ~tray).sum()))
    for k in prods:
        if k in layers:
            continue
        z = zones[k]
        core_src = np.isin(ids, CE.product_ids(k))
        if variant:                                   # the new shade's core: the middle of the pendant box, below the rod
            core_src = C.box_mask([J["variant_core"]])
        core = C.ero(core_src, 3 if core_src.sum() > 600 else 1)
        thr = 5.0 if k in CE.PALE else 7.0
        cand = (d > thr) & z
        if k not in CE.PALE:
            cand &= ~(same & ~C.dil(core_src, 4))
        else:
            cand &= ~(same & ~C.dil(core_src, 10) & (lab_e0[..., 0] < lab_b0[..., 0]))
        if P["lamps"]:
            glow = (lab_e[..., 0] - lab_b[..., 0] > 2) & same & ~C.dil(core_src, 6)
            cand &= ~glow
        cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        if k in COLOUR_CUT:
            cc = COLOUR_CUT[k]
            bx = C.box_mask([cc["box"]])
            pale = bx & (lab_e[..., 0] > cc["L_min"])
            pale = cv2.morphologyEx(pale.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            n_, lb_ = cv2.connectedComponents(pale.astype(np.uint8), connectivity=8)
            st_ = set(np.unique(lb_[pale & C.dil(core_src, 6)])) - {0}
            m = CE.fill_holes(np.isin(lb_, list(st_)), 3000)
            m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool) & bx
            layers[k], rp["canister_geom"] = FX2.canister_geom(lab_e, m)
            continue
        sure = (core & (d > 2.5)) | C.ero((d > 16) & z & C.dil(core_src, 6), 2)
        hard = z & ~C.ero(z, 2)
        try:
            m = C.gc_cut(e, sure, C.dil(cand, 2) & z, z, hard, iters=6) if sure.sum() > 20 else cand
        except Exception:                             # noqa: BLE001
            m = cand
        m = (m | (cand & C.dil(m, 1))) & z
        m = CE.keep_touching(m, sure | core)
        m = CE.fill_holes(m, 1500) & z
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        layers[k] = m
    # overlaps: the product on top keeps the pixel (STACK, then z), then the nearer clay region
    if len(prods) > 1:
        dist = {k: cv2.distanceTransform((~np.isin(ids, CE.product_ids(k))).astype(np.uint8), cv2.DIST_L2, 5) for k in prods}
        for i, k in enumerate(prods):
            for j in prods[i + 1:]:
                both = layers[k] & layers[j]
                if not both.any():
                    continue
                if STACK.get(k) == j:
                    win_k = np.ones((H, W), bool)
                elif STACK.get(j) == k:
                    win_k = np.zeros((H, W), bool)
                elif PRODUCTS[k][2] != PRODUCTS[j][2]:
                    win_k = np.full((H, W), PRODUCTS[k][2] > PRODUCTS[j][2])
                else:
                    win_k = dist[k] <= dist[j]
                layers[k] &= ~(both & ~win_k)
                layers[j] &= ~(both & win_k)
    return dict(P=P, fr=fr, ids=ids, pl_ids=pl_ids, base=base, e=e, d=d, same=same, prods=prods, layers=layers, rp=rp, variant=variant,
                lab_e=lab_e, lab_b=lab_b, dh=dh_, ce=ce_, cb=cb_, diff_base=diff_base)


def light_of(S, pre_fix):
    """the first version's light layer (screen) for a lit lamp, outside every product"""
    P, ids, pl_ids, e, base = S["P"], S["ids"], S["pl_ids"], S["e"], S["base"]
    allfg = np.zeros((H, W), bool)
    for m in S["layers"].values():
        allfg |= m
    env = CE.light_env(ids, P["lamps"])
    L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.5)
    glow_ok = np.clip(C.blur(((S["dh"] < 30) & (S["ce"] - S["cb"] < 22)).astype(np.float64), 3) * 1.4 - 0.2, 0, 1)
    wgt = (env & ~C.dil(allfg | pre_fix, 3) & (pl_ids != 0) & (pl_ids != 15)).astype(np.float64) * glow_ok
    Ls = np.stack([C.blur(L8[..., c] * wgt, 8) / np.maximum(C.blur(wgt, 8), 1e-3) for c in range(3)], -1)
    Ls[C.blur(wgt, 8) < 0.02] = 0
    soft_env = C.blur(env.astype(np.float64), 25)
    return Ls * soft_env[..., None]


def cut2(p, rec, J):
    S = first_masks(p, J, rec)
    P, fr, ids, pl_ids, base, e, prods, layers, rp = S["P"], S["fr"], S["ids"], S["pl_ids"], S["base"], S["e"], S["prods"], S["layers"], S["rp"]
    variant = S["variant"]
    pre_fix = np.zeros((H, W), bool)
    for k in prods:
        pre_fix |= layers[k]
    # product-specific geometry (kd_fixes2)
    if 52 in prods:
        runner_edit = layers[52].copy()
        layers[52], rp["runner"] = FX2.runner_footprint(ids, pl_ids, layers[52])
    if 53 in prods:
        layers[53] = FX.sharp_filter(e, layers[53], ids, 54, rp)
    if 50 in prods:
        e, layers[50], rp["pendant"] = FX2.pendant(e, layers[50], ids, J.get("pendant_card", "V1"), S["diff_base"])
    light0 = light_of(S, pre_fix) if (P["lamps"] and not variant) else None
    e, layers, rp["size_fix"] = FX2.size_fix(p, e, layers, ids, base)
    # per product: its background in the edit, its matte, its colour
    out = {}
    order = sorted(prods, key=lambda k: (PRODUCTS[k][2], SUB.get(k, 0)))
    below = base.copy()                              # what lies under the next product (the plate, then the parents' layers)
    under = {}
    for k in order:
        fg = layers[k]
        if not fg.any():
            continue
        Bk = inpaint(e, C.dil(fg, 3))
        thin = [f for f, o in THIN.items() if o == k]
        if k == 52:                                  # the runner: one colour family, filled under and round its children
            a, col = FX2.runner_matte(e, runner_edit, fg, inpaint(e, C.dil(runner_edit | fg, 3)),
                                      [layers[c] for c, par in STACK.items() if par == 52 and c in layers])
            col, rp["runner_colour"] = FX2.runner_colour(a, col)
        elif k == 50:
            a, col = matte(e, fg, S["diff_base"], r_in=1, r_out=1)
        elif k in COLOUR_CUT:                        # clean geometric outlines: an anti-aliased edge, the colour pulled in from inside
            a = FX2.aa_alpha(fg, sigma=1.2, width=1.0)
            col = C.defringe(e, fg, r=2)
        elif k == 57:                                # a sheer: the exact difference matte on the plate (the window shows through)
            near_furn = C.dil(np.isin(pl_ids, (20, 21, 22, 23, 24)), 80)
            ch_e = np.hypot(S["lab_e"][..., 1], S["lab_e"][..., 2])
            not_sheer = near_furn & (S["lab_e"][..., 0] < 60) & (ch_e > 16)   # the edit's own walnut chair back is not curtain
            not_sheer = C.dil(cv2.morphologyEx(not_sheer.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool), 2)
            fgc = CE.fill_holes(fg, 60000)                                # no hole in a sheer panel
            reg = C.dil(fgc, 3) & ~C.dil(np.isin(pl_ids, (20, 21, 22, 23, 24)), 1) & ~not_sheer
            a, col = FX2.diff_matte(e, base, reg.astype(np.float64))
            a_open = cv2.morphologyEx(a.astype(np.float32), cv2.MORPH_OPEN, C.disk(3)).astype(np.float64)
            a = np.where(near_furn, np.minimum(a, a_open), a)               # no flecks of sheer along the chair backs
            a = np.where(a < 0.05, 0.0, a)
            rp["curtain_not_sheer_px"] = int((not_sheer & C.dil(fg, 1)).sum())
        else:                                        # a solid product: a smoothed outline, anti-aliased, its colour pulled in from inside
            fg_s = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2))
            fg_s = cv2.morphologyEx(fg_s, cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            fg_s = CE.fill_holes(C.blur(fg_s.astype(np.float64), 1.0) > 0.5, 400)
            a = FX2.aa_alpha(fg_s, sigma=1.0, width=1.0)
            col = C.defringe(e, fg_s, r=2)
        for f in thin:                               # thin fillers: the matte over the whole filler, from the leaves' colour
            fz = fg & C.dil(ids == f, CE.FILLER_PAD.get(f, 40)) & ~C.dil(ids == k, 2)
            body_like = fg & (S["lab_e"][..., 0] > 70) & (S["lab_e"][..., 1] > -1.5)      # the vessel itself (pale, not green)
            n_, lb_ = cv2.connectedComponents(body_like.astype(np.uint8), connectivity=8)
            core_lb = set(np.unique(lb_[C.ero(ids == k, 3) & body_like])) - {0}
            vessel = np.isin(lb_, list(core_lb))
            fz &= ~C.dil(vessel, 1)
            if fz.sum() < 30:
                continue
            Bf = S["diff_base"] if light0 is None else C.light_one(S["diff_base"], C.q(light0))
            leaf = C.ero(fz, 1) & (S["d"] > 14)
            a_est, _ = matte(e, fz, Bf, sure=leaf, r_out=1, f_sig=(1.5, 4.0, 10.0))
            up = np.where(e > Bf, (e - Bf) / np.maximum(1 - Bf, 1e-3), (Bf - e) / np.maximum(Bf, 1e-3)).max(-1)
            strong = fz & (S["d"] > 14)
            reg = C.dil(fz, 1) & (C.dil(strong, 2) | (up > 0.35))      # no pale ghost leaves far from a crisp one (7.5: all sharp)
            af, cf = FX2.diff_matte(e, Bf, reg.astype(np.float64), a_est)
            if f == 54:
                af, cf, rp["olive_scale"] = FX2.olive_to_z120(af, cf, fz)
                fz = fz | (af > 0)
            body = fg & ~fz
            ab, cb = (a * body, col)
            a = np.where(fz | (C.dil(fz, 1) & ~body), af, ab)
            col = np.where((fz | (C.dil(fz, 1) & ~body))[..., None], cf, cb)
            rp.setdefault("thin_fillers", {})[str(f)] = dict(px=int(fz.sum()), leaf_px=int(leaf.sum()))
        under[k] = below.copy()
        out[k] = (a, col)
        below = below * (1 - a[..., None]) + col * a[..., None]
        rp["products"][str(k)] = dict(slot=PRODUCTS[k][0], px=int((a > 0).sum()), clay_px=int(np.isin(ids, CE.product_ids(k)).sum()),
                                      alpha_mean_edge=round(float(a[(a > 0) & (a < 1)].mean()), 3) if ((a > 0) & (a < 1)).any() else None)
    # shadows: the edit's background against what lies under each product, in a band, on its support, to the nearest product
    allfg = np.zeros((H, W), bool)
    for k, (a, _) in out.items():
        allfg |= a > 0
    dk = np.stack([cv2.distanceTransform((~(out[k][0] > 0)).astype(np.uint8), cv2.DIST_L2, 5) for k in out])
    keys = list(out)
    near = np.argmin(dk, 0)
    du = dk.min(0)
    shade_w = np.clip(C.blur(((S["dh"] < 15) & (np.abs(S["ce"] - S["cb"]) < 10)).astype(np.float64), 4) * 1.4 - 0.2, 0, 1)
    shadows = {}
    for i, k in enumerate(keys):
        a, col = out[k]
        sup, bk = FX.support_env(k, pl_ids, 45)
        if k == 52:
            bk = 8                                     # a flat runner: a seam of contact only
        Bk = inpaint(e, C.dil(a > 0, 3))
        ref = under[k]
        if k in STACK and STACK[k] in out:            # over the parent: the parent's filled colour is the reference
            pa, pc = out[STACK[k]]
            ref = ref * (1 - pa[..., None]) + pc * pa[..., None]
        rat = np.clip(C.blur(C.luma(C.lin(Bk)), 1.5) / np.maximum(C.blur(C.luma(C.lin(ref)), 1.5), 1e-4), 0, 1.5)
        dark = np.clip(1 - rat - 0.015, 0, 0.75)
        env = (du <= bk) & (near == i) & (pl_ids != 0) & (pl_ids != 15)
        if sup is not None:
            env &= sup | (C.dil(out[STACK[k]][0] > 0, 1) if k in STACK and STACK[k] in out else False)
        if k == 57:                                  # a sheer: no shadow layer (it would show through the panel); the diff matte
            shadows[k] = np.ones((H, W))              # already gives the edit's own shading over the plate
            continue
        if k == 50 or k == 70 or variant:
            env &= False
        if k in COLOUR_CUT:                          # synthetic contact: a soft band under each canister on the niche floor
            fgk = a > 0.5
            bottom = fgk & ~np.roll(fgk, -1, axis=0)
            band_ = np.zeros((H, W), np.float32)
            ys_, xs_ = np.nonzero(bottom)
            for y_, x_ in zip(ys_, xs_):
                band_[y_ - 2:y_ + 4, x_ - 3:x_ + 4] = 1.0
            sh_ = 1 - 0.38 * np.clip(C.blur(band_.astype(np.float64), 2.5) * 1.6, 0, 1)
            sh_ = np.where(fgk, 1.0, sh_)
            shadows[k] = np.where(sh_ > 0.996, 1.0, sh_)
            continue
        tk = np.clip(1 - du / max(bk, 1), 0, 1) ** 1.1
        inside = a > 0
        s = 1 - C.blur(dark * tk * (env | inside) * np.where(inside, 1.0, shade_w), 1.0)
        s[~C.dil(env | inside, 1)] = 1
        s = np.maximum(s, SHADOW_FLOOR_SRGB / np.maximum(ref.mean(-1), 1e-3))
        shadows[k] = np.where(s > 0.996, 1.0, np.clip(s, 0.25, 1))
    light = light0
    if light is not None:
        rp["light_px"] = int((light.max(2) > 0.003).sum())
    rec[p] = rp
    return e, out, shadows, light, keys


def write2(p, e, out, shadows, light, keys, man):
    P = PASSES[p]
    fr = P["frame"]
    tc = CE.toe(fr)
    variant = P.get("variant", False)
    man["layers"] = [l for l in man["layers"] if not (l.get("pass_") == p and l["frame"] == fr and not l.get("projected_from"))]
    for k in keys:
        a, col = out[k]
        slot, pid, z = PRODUCTS[k]
        if variant:
            slot, pid = VARIANTS[p]
        rgb = col
        if tc:
            lab = C.to_lab(rgb)
            lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
            lab[..., 0] = np.interp(lab[..., 0], BP_FLOOR[0], BP_FLOOR[1])     # WM-G1: nothing in a layer under L* 11
            rgb = np.clip(C.from_lab(lab), 0, 1)
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        lp = os.path.join(ST, "layers", fr, slot, pid + ".png")
        sp = os.path.join(ST, "shadows", fr, slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        s8 = C.q(shadows[k]) if not variant else np.full((H, W), 255, np.uint8)
        Image.fromarray(s8).save(sp, optimize=True)
        ys, xs = np.nonzero(a8 > 0)
        man["layers"].append(dict(frame=fr, slot=slot, product=pid, clay_id=k, z=z, sub=SUB.get(k, 0), shadow_z=z - 1, default=not variant,
                                  layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()),
                                  bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if xs.size else None,
                                  sold=True, source=f"{fr} pass {p} (nano-banana-2 mask edit), cut in code (tools/kd_cut2.py)", pass_=p,
                                  toned=bool(tc)))
    if light is not None:
        lp = os.path.join(ST, "light", fr, f"{p}-lamps.png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        Image.fromarray(C.q(light)).save(lp, optimize=True)
        man["light"] = [li for li in man["light"] if not (li.get("pass_") == p and li["frame"] == fr)]
        man["light"].append(dict(frame=fr, file=os.path.relpath(lp, ST), z=90, blend="screen", lamps=[PRODUCTS[k][0] for k in P["lamps"]], pass_=p))
    man["layers"].sort(key=lambda l: (l["frame"], l["z"], l.get("sub", 0), l["slot"]))


def retone(man):
    """once, for the layers cut before the toe was read right: the toe and the floor on their colour (write2 does it on a new cut)"""
    n = 0
    for l in man["layers"]:
        if l.get("projected_from") or l.get("toned"):
            continue
        tc = CE.toe(l["frame"])
        if not tc:
            continue
        lp = os.path.join(ST, l["layer"])
        rgba = np.asarray(Image.open(lp)).copy()
        m = rgba[..., 3] > 0
        lab = C.to_lab(rgba[..., :3][m][None].astype(np.float64) / 255)
        lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
        lab[..., 0] = np.interp(lab[..., 0], BP_FLOOR[0], BP_FLOOR[1])
        rgba[..., :3][m] = C.q(np.clip(C.from_lab(lab), 0, 1))[0]
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        l["toned"] = True
        n += 1
    return n


def main(args):
    man = CE.load_man()
    rp = os.path.join(ST, "compose.json")
    rec = json.load(open(rp)) if os.path.exists(rp) else {}
    J = json.load(open(os.path.join(ST, "passes.json")))
    if args[0] == "retone":
        print("retoned", retone(man))
        json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
        return
    for p in args[1:]:
        e, out, shadows, light, keys = cut2(p, rec, J[p])
        write2(p, e, out, shadows, light, keys, man)
        np.save(os.path.join(K.SCR, f"{p}-locked.npy"), e.astype(np.float16))
        print(p, json.dumps({k: v for k, v in rec[p].items() if k != "lock"})[:1500], json.dumps(rec[p]["lock"]["ecc"]))
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    json.dump(rec, open(rp, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1:])
