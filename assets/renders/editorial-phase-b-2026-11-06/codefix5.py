#!/usr/bin/env python3
"""
codefix5.py: zero-token code fixes from QA (qa/reports/2026-11-07-ged-codefix-mc1-clay.md section 1), render-agent, 2026-11-07. No var2.
New files only; every fix inside its own mask, 0 px changed outside (counted in codefix5.json).
  boho     boho-A-fin4 -> boho-A-fin5:
             4. the door behind the basket rebuilt along its structure: the jamb and the stile continued down their columns, the panel's
                planks as a per-column colour times the light, the light (the reed curtain's diagonal stripes, ~46 deg) carried in along
                the stripes from the clean door, the bottom rail and the moulding along the leaf's perspective lines (VP ~(5446, 637)),
                the grain copied from the same column / line; the floor strip quilted from the floor beside it
             5. the basket's middle handle out (the card has two): not in the sprite any more, its two feet on the rim and the weave
                rebuilt from the same rows, the wall and the jamb behind it filled as the rest of the hole
           (the fin4 pipeline of codefix4 re-run from fin3 with these two changes; outside them fin5 equals fin4 pixel for pixel)
  mc       modern-country-A-mc1 -> modern-country-A-fix3:
             1. the tone seams at the MC1 table mask's side edges (x ~1120, ~1626): the low frequencies matched across each edge
             2. the bowl lowered (height x0.78 about its base, the rim's ellipse kept), the sofa behind rebuilt
             3. the clay vase slimmed (width x0.78 about its axis), the glass, the mullion and the sill behind rebuilt, the contact shadow
  crops    codefix5-before-after/, sheet codefix5-sheet.jpg
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01  # noqa: E402
from fin2_codefix import nblur, harmonic  # noqa: E402
from codefix3 import save8, lab_of, check, poly_mask  # noqa: E402
from codefix4 import BASKET_BODY, BASKET_HANDLES, quilt, poisson_refine  # noqa: E402

REC = os.path.join(HERE, "codefix5.json")
CROPS = os.path.join(HERE, "codefix5-before-after")


def rec_update(key, val):
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent", tokens=0,
                                                              source="qa/reports/2026-11-07-ged-codefix-mc1-clay.md section 1",
                                                              note="TEST, not for the site; new files only")
    R[key] = val
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)


# ==================================================================================================================================
# boho
# ==================================================================================================================================
VPX, VPY, XREF = 5446.0, 637.0, 2300.0       # the open leaf's horizontal lines (mid rail slope -0.03 at y 732, bottom rail -0.126 at 1035)
STREAK_DEG = 46.0                            # the reed curtain's light stripes on the leaf (line-variance minimum 42-50 deg, up to the right)


def leaf_line(xx, yy):
    """the leaf's perspective line through (x, y), as its y at x = 2300"""
    return VPY + (yy - VPY) * (VPX - XREF) / (VPX - xx)


def door_fill(lin, hole, need, xx, yy):
    """the door behind the basket (x >= 2157), rebuilt from its structure. Domains: J the shadowed jamb (2157-2200), S the leaf's
    stile (2200-2222), P the panel (x >= 2222 above the bottom moulding), R the bottom moulding and rail (to the rail's lower edge),
    F the floor. J: each column continued downwards (mirror-tiled from the rows above the hole). S, P: colour per column (its lit level)
    x the light ratio x the grain; R: the same per perspective line. The light ratio (the diagonal stripes) is carried into the hole along
    the stripes' direction from the nearest clean door pixel up to the right; the grain is copied from the same column (S, P) or the same
    line (R). F: quilted from the floor to the right, gradient-domain blended."""
    H, W = hole.shape
    ell = leaf_line(xx.astype(np.float64), yy.astype(np.float64))
    door_zone = (xx >= 2157) & (xx < 2345) & (yy >= 600) & (yy < 1100)
    J = door_zone & (xx < 2200) & (ell < 1038.5)
    S = door_zone & (xx >= 2200) & (xx < 2222) & (ell < 1038.5)
    P = door_zone & (xx >= 2222) & (ell < 976.5) & (yy >= 757)
    R = door_zone & (xx >= 2222) & (ell >= 976.5) & (ell < 1038.5)        # the moulding, the rail and the shadow line under the leaf
    F = door_zone & (ell >= 1038.5)
    known = ~hole & door_zone
    tgt = (need & door_zone).copy()
    out = lin.copy()
    Lum = (0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2])
    info = {}
    # --- J: straight down each column
    Lsm = cv2.GaussianBlur(np.log(Lum + 1e-3), (0, 0), 1.0)
    jwin = {}
    for x in range(2157, 2200):
        hc = np.nonzero(hole[:, x] & J[:, x])[0]
        if hc.size == 0:
            continue
        top = int(hc.min())
        # the whole column from the hole's top down (the old handle's loop inside included, so the jamb's lines run on unbroken),
        # where the new basket does not cover it
        col = J[:, x] & (yy[:, x] >= top) & ~(np.arange(H) > hc.max()) & (need[:, x] | ~hole[:, x])
        col &= ~((yy[:, x] > hc.max()))
        tgt[:, x] |= col
        # the window: the rows just above the hole, up to the nearest strong change in the column (the hinge gap's lit sliver, the
        # hardware above it), so that only the part that runs on into the hole is tiled
        ref = Lsm[top - 4:top - 1, x].mean()
        Msrc = 48
        for r in range(top - 5, top - 49, -1):
            if abs(Lsm[r, x] - ref) > 0.35:
                Msrc = top - r - 2
                break
        Msrc = max(Msrc, 8)
        jwin[x] = Msrc
        for y in np.nonzero(col)[0]:
            k = (y - top) % (2 * Msrc)
            ys = top - 1 - k if k < Msrc else top - Msrc + (k - Msrc)
            out[y, x] = lin[ys, x]
    info["J_px"] = int((tgt & J).sum())
    info["J_window_rows"] = [min(jwin.values()), max(jwin.values())] if jwin else None
    # --- the colour per column (S, P) and per line (R): the mean of the lit half of the known pixels
    A = np.zeros_like(lin)
    for dom, r0 in ((S, 692), (P, 757)):
        for x in range(2200 if dom is S else 2222, 2222 if dom is S else 2345):
            ok = known[:, x] & dom[:, x] & (yy[:, x] >= r0)
            if ok.sum() < 6:
                continue
            v = Lum[ok, x]
            lit = v >= np.percentile(v, 50)
            A[dom[:, x], x] = lin[ok, x][lit].mean(0)
    # R: the colour as a function of the line (0.25 px bins, each from the known rail pixels within +-0.5 px of it), read with linear
    # interpolation (a sloped thin line - the shadow under the leaf - would otherwise step every 8 px)
    BIN = 4.0
    fb = (ell - 976.5) * BIN
    rk = known & R & (xx >= 2286) & (xx < 2338)
    nb_ = int(np.ceil((1038.5 - 976.5) * BIN)) + 2
    tab = np.zeros((nb_, 3))
    okb = np.zeros(nb_, bool)
    rkf = fb[rk]
    rkv = lin[rk]
    rkl = Lum[rk]
    for b in range(nb_):
        sel = np.abs(rkf - b) <= 0.5 * BIN
        if sel.sum() < 4:
            continue
        v = rkl[sel]
        tab[b] = rkv[sel][v >= np.percentile(v, 50)].mean(0)
        okb[b] = True
    idx_ok = np.nonzero(okb)[0]
    for c in range(3):
        tab[:, c] = np.interp(np.arange(nb_), idx_ok, tab[idx_ok, c])
    rr = R & (fb >= 0)
    f = np.clip(fb[rr], 0, nb_ - 1.001)
    i0 = np.floor(f).astype(int)
    w1 = (f - i0)[:, None]
    A[rr] = tab[i0] * (1 - w1) + tab[np.minimum(i0 + 1, nb_ - 1)] * w1
    SPR = S | P | R
    haveA = (A.sum(2) > 0) & SPR
    Q = np.where(haveA[..., None], lin / np.maximum(A, 1e-4), 0)
    kq = (known & haveA).astype(np.float32)
    Qs, den = nblur(Q, kq, 2.0)
    Qs = np.where((den > 0.2)[..., None], Qs, 1.0)
    T = np.where((known & haveA)[..., None], Q / np.maximum(Qs, 1e-4), 1.0)
    T = np.clip(T, 0.6, 1.6)
    # --- the light carried along the stripes (up to the right) from the first clean door pixel (S, P or R)
    t_ = tgt & SPR & haveA
    ys, xs = np.nonzero(t_)
    d = (math.cos(math.radians(STREAK_DEG)), -math.sin(math.radians(STREAK_DEG)))
    kmask = known & SPR & haveA
    kmask = kmask & cv2.erode(kmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    found = np.full(ys.size, -1.0)
    for step in np.arange(1.0, 260.0, 0.7):
        px = np.round(xs + step * d[0]).astype(int)
        py = np.round(ys + step * d[1]).astype(int)
        inb = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        hit = np.zeros(ys.size, bool)
        hit[inb] = kmask[py[inb], px[inb]]
        newf = hit & (found < 0)
        found[newf] = step
        if (found >= 0).all():
            break
    acc = np.zeros((ys.size, 3))
    for k in range(4):
        st_ = np.where(found >= 0, found + 1.0 + 1.2 * k, 0)
        px = np.clip(np.round(xs + st_ * d[0]).astype(int), 0, W - 1)
        py = np.clip(np.round(ys + st_ * d[1]).astype(int), 0, H - 1)
        acc += Qs[py, px]
    Qf = acc / 4
    Qf[found < 0] = 1.0
    info["light_carried_px"] = int((found >= 0).sum())
    info["light_mean_march_px"] = round(float(found[found >= 0].mean()), 1) if (found >= 0).any() else None
    # --- the grain: S, P from the same column (mirror-tiled from the rows above the hole); R along its line from the clean right part
    Tf = np.ones((ys.size, 3))
    for i, (y, x) in enumerate(zip(ys, xs)):
        if R[y, x]:
            # along the perspective line, from x 2286 on (mirror-tiled), read with linear interpolation in y
            k = (x - 2222) % 80
            xsrc = 2286 + (k if k < 40 else 79 - k)
            yf = VPY + (ell[y, x] - VPY) * (VPX - xsrc) / (VPX - XREF)
            y0_ = int(np.floor(yf))
            wy = yf - y0_
            if known[y0_, xsrc] and known[y0_ + 1, xsrc] and R[y0_, xsrc] and R[y0_ + 1, xsrc]:
                Tf[i] = T[y0_, xsrc] * (1 - wy) + T[y0_ + 1, xsrc] * wy
        else:
            dom = S if S[y, x] else P
            colk = np.nonzero(known[:, x] & dom[:, x] & (yy[:, x] < y))[0]
            if colk.size < 4:
                continue
            top = int(colk.max()) + 1
            Ms = min(40, colk.size)
            k = (y - top) % (2 * Ms)
            ysrc = top - 1 - k if k < Ms else top - Ms + (k - Ms)
            Tf[i] = T[ysrc, x] if known[ysrc, x] else 1.0
    out[ys, xs] = np.clip(A[ys, xs] * Qf * Tf, 0, 1)
    info["S_P_R_px"] = int(ys.size)
    # --- F: the floor strip, quilted from the floor to the right (rows only), then blended in the gradient domain
    fneed = tgt & F
    if fneed.any():
        # one shift for the whole strip (no tile seams): the floor's light bands run along the rows; the shift whose source best matches
        # the known floor round the strip, then a gradient-domain blend (each pixel follows its source's gradients, the known floor fixed)
        fsrc = known & F
        ring = cv2.dilate(fneed.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & fsrc
        fy, fx = np.nonzero(fneed)
        ry, rx = np.nonzero(ring)
        best = None
        for dx in range(24, 160, 2):
            for dy in range(-6, 7):
                sy, sx = fy + dy, fx + dx
                if (sy >= H).any() or (sx >= W).any() or not fsrc[sy, sx].all():
                    continue
                e = ((lin[np.clip(ry + dy, 0, H - 1), np.clip(rx + dx, 0, W - 1)] - lin[ry, rx]) ** 2).sum(-1).mean()
                if best is None or e < best[0]:
                    best = (e, dx, dy)
        _, dx, dy = best
        out[fy, fx] = lin[fy + dy, fx + dx]
        offs = np.zeros((H, W, 2), np.int32)
        offs[fneed] = (dx, dy)
        out = poisson_refine(out, fneed, offs, ~hole, fsrc | fneed, iters=800)
        info["F_px"] = int(fneed.sum())
        info["F_shift"] = [int(dx), int(dy)]
    return out, info, dict(J=J, S=S, P=P, R=R, F=F, J_loop=tgt & J & ~hole)


def leg_repair(lin, body, leg):
    """the middle handle's feet on the rim and the weave (fin3 coordinates): each piece copied from the same rows of the basket a few
    weave units to the side (the shift whose source best matches the ring round the piece), feathered 1 px"""
    out = lin.copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats(leg.astype(np.uint8))
    picks = []
    other_legs = np.zeros_like(leg)
    for pts in (BASKET_HANDLES[0], BASKET_HANDLES[2]):
        h = np.zeros(leg.shape, np.uint8)
        cv2.polylines(h, [np.array(pts, np.int32)], False, 1, thickness=12)
        other_legs |= h.astype(bool)
    ok_src = body & ~leg & ~other_legs
    for i in range(1, n):
        m = lab == i
        ring = cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~m & body
        ys, xs = np.nonzero(m)
        ry, rx = np.nonzero(ring)
        best = None
        for dx in list(range(-44, -9)) + list(range(10, 45)):
            for dy in (-1, 0, 1):
                sy, sx = ys + dy, xs + dx
                if not ok_src[sy, sx].all():
                    continue
                e = ((lin[ry + dy, rx + dx] - lin[ry, rx]) ** 2).sum() / max(ry.size, 1)
                if best is None or e < best[0]:
                    best = (e, dx, dy)
        if best is None:
            continue
        _, dx, dy = best
        patch = np.zeros_like(lin)
        patch[ys, xs] = lin[ys + dy, xs + dx]
        ws = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7)
        ws = np.maximum(ws, m.astype(np.float32))
        mm = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & body
        yy2, xx2 = np.nonzero(mm)
        src = lin[yy2 + dy, xx2 + dx]
        out[yy2, xx2] = lin[yy2, xx2] * (1 - ws[yy2, xx2, None]) + src * ws[yy2, xx2, None]
        picks.append((int(dx), int(dy), int(m.sum())))
    return out, picks


def boho():
    src3 = os.path.join(HERE, "boho-A-fin3.png")
    src4 = os.path.join(HERE, "boho-A-fin4.png")
    a = load01(src3)
    f4 = load01(src4)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    AXc, AYc, K = 2153.0, 1069.0, 0.75
    lin = s2l(a)
    # ---- codefix4's masks (the old basket with its three handles: the hole)
    body = poly_mask(a.shape, BASKET_BODY)
    hands = []
    for pts in BASKET_HANDLES:
        h = np.zeros((H, W), np.uint8)
        cv2.polylines(h, [np.array(pts, np.int32)], False, 1, thickness=8)
        hands.append(h)
    hand_all = hands[0] | hands[1] | hands[2]
    sprite_old = body | hand_all.astype(bool)
    table = (xx < 2046) & (yy > 1050)
    hole = cv2.dilate(sprite_old.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~table
    hole |= cv2.dilate(hand_all, np.ones((15, 15), np.uint8)).astype(bool)
    # ---- 5: the middle handle out of the sprite; its feet on the rim / weave rebuilt (fin3 coordinates, before the scale)
    mid = np.zeros((H, W), np.uint8)
    cv2.polylines(mid, [np.array(BASKET_HANDLES[1], np.int32)], False, 1, thickness=12)
    leg = mid.astype(bool) & body
    lin_b, leg_picks = leg_repair(lin, body, leg)
    sprite = body | (hands[0] | hands[2]).astype(bool)
    alpha = cv2.GaussianBlur(sprite.astype(np.float32), (0, 0), 0.8)
    Am = np.float32([[K, 0, AXc * (1 - K)], [0, K, AYc * (1 - K)]])
    sc = cv2.warpAffine(lin_b * alpha[..., None], Am, (W, H), flags=cv2.INTER_AREA)
    sa = np.clip(cv2.warpAffine(alpha, Am, (W, H), flags=cv2.INTER_AREA), 0, 1)
    # the fin4 sprite (three handles), for the "unchanged elsewhere" check
    alpha4 = cv2.GaussianBlur(sprite_old.astype(np.float32), (0, 0), 0.8)
    sa4 = np.clip(cv2.warpAffine(alpha4, Am, (W, H), flags=cv2.INTER_AREA), 0, 1)
    planter = poly_mask(a.shape, [(1960, 820), (2026, 820), (2030, 925), (2026, 1036), (1960, 1036)])
    need = hole & ~(sa > 0.98)
    # ---- the wall (x < 2157): as codefix4 (harmonic + its grain, the same seed): the new pixels behind the middle handle included
    wallr = need & (xx < 2157) & (yy < 1038)
    sl = (slice(700, 1060), slice(1990, 2200))
    known = ~hole & ~planter & (xx < 2157) & (yy < 1038) & ~((A_ < 0) & (B_ > 10)) & (yy > 700)
    wl, den = nblur(lin, known.astype(np.float32), 3)
    kn = (known & (den > 0.3))[sl]
    hw_ = harmonic(np.where(kn[..., None], wl[sl], 0), kn, f=2, iters=3000)
    hp = (lin / np.maximum(cv2.GaussianBlur(lin, (0, 0), 2), 1e-5)).mean(2)
    kw = known & (xx > 2030) & (yy > 740) & (yy < 1000)
    kw &= cv2.erode(kw.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    sd = float(np.std(hp[kw])) if kw.any() else 0.03
    rng = np.random.default_rng(41)
    nz = cv2.GaussianBlur(rng.standard_normal(hw_.shape[:2]).astype(np.float32), (0, 0), 0.8)
    nz *= sd / max(float(nz.std()), 1e-6)
    tmp = lin.copy()
    tmp[sl] = hw_ * (1 + nz)[..., None]
    fill = np.where(wallr[..., None], tmp, lin)
    # ---- 4: the door, rebuilt along its structure
    fill_d, dinfo, doms = door_fill(lin, hole, need, xx, yy)
    door_jamb_loop = doms["J_loop"]
    door_need = need & (xx >= 2157)
    fill = np.where(door_need[..., None], fill_d, fill)
    # ---- composite as codefix4: the hole's edge feathered, the contact shadow, the basket
    oa = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.5)[..., None] * cv2.dilate(hole.astype(np.uint8), np.ones((5, 5), np.uint8))[..., None]
    out = lin * (1 - oa) + fill * oa
    out = np.where(door_jamb_loop[..., None], fill_d, out)                 # the jamb seen through the old handle's loop, re-run too
    # ---- the wall strip beside the jamb (x 2118-2157): its faint light band (fin3: +8-12 levels at x 2140-2157) and the old middle
    # handle's loose fibre and inner strand (left inside its loop in fin4). The band is a vertical structure: factored out as a gain
    # per column (read on the clean rows 720-760 above the old handle), the wall filled harmonically under it (the loop's inside now
    # unknown too), the band put back, the wall's grain as before; blended into the fin4 wall fill over x 2118-2126
    Wv = np.zeros((H, W), bool)
    for x in range(2118, 2157):
        hc = np.nonzero(hole[:, x] & (yy[:, x] < 900))[0]
        if hc.size:
            Wv[int(hc.min()):1000, x] = True
    Wv &= ~(sa > 0.98)
    Lw = (0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2])
    prof = np.array([np.median(Lw[720:760, x]) for x in range(2100, 2160)])
    trend = float(np.median(prof[12:36]))                                  # x 2112-2135: the plain wall
    G = np.ones(W, np.float32)
    g_ = np.clip(prof / trend, 0.9, 1.35)
    g_[:38] = 1.0                                                          # x < 2138: no band
    G[2100:2160] = np.convolve(np.r_[[g_[0]] * 2, g_, [g_[-1]] * 2], np.ones(5) / 5, mode="same")[2:-2]
    linn = lin / G[None, :, None]
    known2 = known & ~Wv
    wl2, den2 = nblur(linn, known2.astype(np.float32), 3)
    kn2 = (known2 & (den2 > 0.3))[sl]
    hw2 = harmonic(np.where(kn2[..., None], wl2[sl], 0), kn2, f=2, iters=3000)
    tmp2 = lin.copy()
    tmp2[sl] = hw2 * (1 + nz)[..., None] * G[None, sl[1], None]
    wr = np.clip((xx - 2118) / 8.0, 0, 1)[..., None]
    out = np.where(Wv[..., None], out * (1 - wr) + tmp2 * wr, out)
    Wtop = np.zeros((H, W), np.float32)
    for x in range(2118, 2157):
        ys_ = np.nonzero(Wv[:, x])[0]
        if ys_.size:
            t0 = int(ys_.min())
            Wtop[t0 - 8:t0, x] = (np.arange(8) + 1) / 9.0
    Wtop = Wtop[..., None] * wr
    out = out * (1 - Wtop) + tmp2 * Wtop
    fp = np.zeros((H, W), np.uint8)
    nb = np.nonzero(sa4[1060:1072] > 0.5)
    half = int((nb[1].max() - nb[1].min()) / 2) if nb[1].size else 55
    cx_ = int((nb[1].max() + nb[1].min()) / 2) if nb[1].size else int(AXc)
    cv2.ellipse(fp, (cx_, int(AYc) - 1), (half + 3, 4), 0, 0, 360, 1, -1)
    shadow = np.clip(0.5 * cv2.GaussianBlur(fp.astype(np.float32), (0, 0), 2.0)
                     + 0.2 * cv2.GaussianBlur(cv2.warpAffine(fp.astype(np.float32), np.float32([[1, 0, -6], [0, 1, 1]]), (W, H)), (0, 0), 6), 0, 0.6)
    shadow *= (yy >= 1058) * ~table
    out = out * (1 - shadow[..., None] * (1 - sa[..., None]))
    out = out * (1 - sa[..., None]) + np.clip(sc / np.maximum(sa[..., None], 1e-4), 0, 1) * sa[..., None]
    o8 = (np.clip(l2s(out), 0, 1) * 255 + 0.5).astype(np.uint8)
    # ---- outside the two fixes, fin5 = fin4 exactly: take fin4's pixels there
    f48 = (f4 * 255 + 0.5).astype(np.uint8)
    zone_door = cv2.dilate((door_need).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & hole
    mid_new = cv2.dilate(((sa4 > 0.002) & ~(sa > 0.98)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    mid_new &= (xx > 2100) & (xx < 2200) & (yy > 820) & (yy < 915)
    leg_new = cv2.warpAffine(cv2.dilate(leg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32), Am, (W, H)) > 0.01
    zone = zone_door | mid_new | leg_new | cv2.dilate(Wv.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) | (Wtop[..., 0] > 0)
    zone |= door_jamb_loop
    o8 = np.where(zone[..., None], o8, f48)
    Image.fromarray(o8).save(os.path.join(HERE, "boho-A-fin5.png"))
    # what the re-run alone would have changed outside the zones (should be ~0: the pipeline reproduces fin4)
    o8_all = (np.clip(l2s(out), 0, 1) * 255 + 0.5).astype(np.uint8)
    drift = np.abs(o8_all.astype(int) - f48.astype(int)).max(2)
    r = check(o8, f48, zone, "boho-A-fin5.png")
    r.update(base="boho-A-fin4.png (codefix4's fin4 pipeline re-run from boho-A-fin3.png)",
             fixes=dict(door=dict(px_zone=int(zone_door.sum()), **dinfo, streak_deg=STREAK_DEG, leaf_vp=[VPX, VPY]),
                        middle_handle=dict(px_zone=int((mid_new | leg_new).sum()), feet_repaired_px=int(leg.sum()), feet_shifts=leg_picks),
                        wall_strip=dict(px=int(Wv.sum()), band_gain_max=round(float(G[2100:2160].max()), 3),
                                       note="x 2118-2157: the faint light band beside the jamb continued down (a gain per column over the "
                                            "harmonic wall); the old middle handle's loose fibre and inner strand (left in fin4) gone")),
             rerun_drift_outside_zones=dict(px_over_0=int(((drift > 0) & ~zone).sum()), max_levels=int(drift[~zone].max())),
             method="see the docstring; fin4's pixels kept outside the door zone and the middle handle's zone")
    return r


# ==================================================================================================================================
if __name__ == "__main__":
    for k in sys.argv[1:]:
        r = globals()[k]()
        rec_update(k, r)
        print(k, json.dumps(r, default=str)[:1500])
