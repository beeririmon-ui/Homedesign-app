#!/usr/bin/env python3
"""
codefix4.py: two zero-token code fixes from master-designer (docs/proposals/tool-shells-and-qa-items-2026-11-07.md, rows 46-47),
render-agent, 2026-11-07. No var2. New files only; each fix inside its own mask, 0 px changed outside (counted in codefix4.json).
  rug      modern-country-A-fix1 -> modern-country-A-fix2: inside the rug only, the pattern's contrast ~60 % lower and its saturation
           ~40 % lower (a faded rug in close tones); the shadows and the light on it kept (an edge-preserving base carries them)
  basket   boho-A-fin3 -> boho-A-fin4: the seagrass basket alone x0.75 about its floor contact point (the planter and plant untouched),
           the wall, the door and the floor behind it rebuilt, a contact shadow for the new size; basket / planter ~0.84 as the cards
  crops    codefix4-before-after/
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01  # noqa: E402
from fin2_codefix import nblur, harmonic  # noqa: E402
from codefix3 import save8, lab_of, lab_f, rgb_f, check, poly_mask  # noqa: E402

REC = os.path.join(HERE, "codefix4.json")
CROPS = os.path.join(HERE, "codefix4-before-after")


# ----------------------------------------------------------------------------------------------------------------------------------
def rug():
    src = os.path.join(HERE, "modern-country-A-fix1.png")
    a = load01(src)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    # the rug: from its back edge (read per column, the strongest step in y 1393-1440, smoothed) to the frame's bottom, x 300 on
    Lb = cv2.GaussianBlur(L, (0, 0), 1.5)
    top = np.full(W, 1412.0)
    for x in range(300, W):
        g = np.abs(np.diff(Lb[1393:1440, x]))
        top[x] = 1393 + int(np.argmax(g)) + 1
    top[300:] = np.convolve(np.r_[[top[300]] * 25, top[300:], [top[-1]] * 25], np.ones(51) / 51, mode="same")[25:-25]
    rugm = (xx >= 300) & (yy >= top[None, :] + 2)
    # out: the runner and its tassels, the table and armchair legs (warm dark wood), the doorway on the left
    # kept out (and blended through a soft matte, so their edges carry no ring of old rug): the runner's body (down to its scalloped
    # bottom, y 1451), its 13 tassels (hand outlines: the knot at y 1449 widening to the bottom span at y 1516) and the legs
    runner = poly_mask(a.shape, [(1122, 1250), (1613, 1250), (1613, 1451), (1122, 1451)])
    knots = [1151, 1193, 1230, 1266, 1301, 1342, 1376, 1412, 1445, 1482, 1522, 1555, 1595]
    spans = [(1129, 1162), (1172, 1204), (1206, 1241), (1246, 1275), (1285, 1315), (1326, 1347), (1360, 1387), (1397, 1421), (1430, 1452),
             (1471, 1499), (1510, 1540), (1550, 1580), (1585, 1610)]
    tassels = np.zeros((H, W), bool)
    for kx, (bl, br) in zip(knots, spans):
        tassels |= poly_mask(a.shape, [(kx - 6, 1447), (kx + 6, 1447), (br + 1, 1510), (br - 2, 1518), (bl + 2, 1518), (bl - 1, 1510)])
    # the legs (two table legs to the frame's bottom, one ending at y ~1490, the armchair's): in each leg's box the warm wood, each row
    # filled between its first and last wood pixel
    legs = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in [(820, 1380, 915, 1536), (1712, 1380, 1792, 1500), (1810, 1380, 1902, 1536), (2355, 1380, 2430, 1455)]:
        sub = (L < 46) & (A_ > 8.5) & (B_ > 10)                            # the turned wood (its shade keeps a* > 9; the rug's shade a* < 8)
        sub = cv2.morphologyEx(sub[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab_, st, _ = cv2.connectedComponentsWithStats(sub)
        if n < 2:
            continue
        kk = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        comp = lab_ == kk
        lo_ = np.full(comp.shape[0], -1.0)
        hi_ = np.full(comp.shape[0], -1.0)
        for r in range(comp.shape[0]):
            xs_ = np.nonzero(comp[r])[0]
            if xs_.size > 3:
                lo_[r], hi_[r] = xs_.min(), xs_.max()
        ok = lo_ >= 0
        if ok.sum() > 5:                                                    # the outline's two sides, median over 5 rows (no single-row spurs)
            rr = np.nonzero(ok)[0]
            lo_s = cv2.medianBlur(lo_[ok].astype(np.float32).reshape(-1, 1), 5).ravel()
            hi_s = cv2.medianBlur(hi_[ok].astype(np.float32).reshape(-1, 1), 5).ravel()
            for r, l_, h_ in zip(rr, lo_s, hi_s):
                legs[y0 + r, x0 + int(l_):x0 + int(h_) + 1] = True
    # the legs' specular highlights at their lit edges (bright, low chroma, within 4 px of the wood): part of the leg
    hl = (L > 62) & (np.hypot(A_, B_) < 14) & cv2.dilate(legs.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & (yy >= 1380)
    hl = cv2.morphologyEx(hl.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    legs = cv2.morphologyEx((legs | hl).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    # the outline refined by GrabCut per leg box (the lit edges reflect the rug and fail the colour rule): sure leg = the rule eroded 2 px,
    # maybe = within 5 px of it, sure rug = the rest of the box
    refined = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in [(810, 1380, 925, 1536), (1702, 1380, 1802, 1505), (1800, 1380, 1912, 1536), (2345, 1380, 2440, 1460)]:
        lg = legs[y0:y1, x0:x1].astype(np.uint8)
        if lg.sum() < 50:
            continue
        gm = np.full(lg.shape, cv2.GC_BGD, np.uint8)
        gm[cv2.dilate(lg, np.ones((11, 11), np.uint8)) > 0] = cv2.GC_PR_BGD
        gm[lg > 0] = cv2.GC_PR_FGD
        gm[cv2.erode(lg, np.ones((5, 5), np.uint8)) > 0] = cv2.GC_FGD
        img8 = (a[y0:y1, x0:x1] * 255).astype(np.uint8)
        bgdM, fgdM = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(np.ascontiguousarray(img8), gm, None, bgdM, fgdM, 5, cv2.GC_INIT_WITH_MASK)
        fg = ((gm == cv2.GC_FGD) | (gm == cv2.GC_PR_FGD)).astype(np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n_, lb_, st_, _ = cv2.connectedComponentsWithStats(fg)
        if n_ > 1:
            kk = 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
            refined[y0:y1, x0:x1] |= lb_ == kk
    legs = legs | refined
    excl = runner | tassels | legs
    m = rugm
    pure = rugm & ~cv2.dilate(excl.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    lab = lab_f(a)
    Lf = lab[..., 0].astype(np.float32)
    wp = pure.astype(np.float32)
    # L*: the light and the shadows on the rug are broad (the table's shadow, the legs' soft shadows): a sigma-8 base over the rug only
    # carries them; the motifs (2-15 px marks) are the detail
    baseL, _ = nblur(Lf, wp, 8)
    baseA, _ = nblur(lab[..., 1], wp, 10)
    baseB, _ = nblur(lab[..., 2], wp, 10)
    PC, SAT = 0.40, 0.60                                                   # pattern contrast x0.4 (-60 %), saturation x0.6 (-40 %)
    newlab = np.stack([baseL + PC * (Lf - baseL), (baseA + PC * (lab[..., 1] - baseA)) * SAT, (baseB + PC * (lab[..., 2] - baseB)) * SAT], -1)
    D = rgb_f(newlab) - a                                                  # the change, measured on the rug
    Dext, _ = nblur(D, wp, 3)                                              # carried under the kept-out things (their edge pixels)
    D = np.where(pure[..., None], D, Dext)
    alpha = np.clip(cv2.GaussianBlur(excl.astype(np.float32), (0, 0), 0.7), 0, 1) * cv2.dilate(excl.astype(np.uint8), np.ones((3, 3), np.uint8))
    w = cv2.GaussianBlur(cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2) * m * (1 - alpha)
    out = np.clip(a + D * w[..., None], 0, 1)
    o8 = save8(out, os.path.join(HERE, "modern-country-A-fix2.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    rec = check(o8, a8, m, "modern-country-A-fix2.png")
    Ls, As, Bs = lab_of(out)
    def pstats(Lx, Ax, Bx):
        d = (Lx - cv2.GaussianBlur(Lx, (0, 0), 10))[m]
        return dict(L_detail_std=round(float(d.std()), 2), chroma_median=round(float(np.median(np.hypot(Ax, Bx)[m])), 1))
    rec.update(base="modern-country-A-fix1.png", rug_top_edge="read per column (y 1393-1440), smoothed over 51 columns", pattern_contrast=PC,
               saturation=SAT, before=pstats(L, A_, B_), after=pstats(Ls, As, Bs),
               method="rug only (the runner, its 13 tassels by hand and the legs kept out through a soft matte); L*: a sigma-8 base over "
                      "the rug keeps the broad shadows and the light, the motifs' detail x0.4; a/b: detail about a sigma-10 base x0.4, then chroma x0.6")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
BASKET_BODY = [(2060, 832), (2240, 832), (2242, 840), (2245, 870), (2250, 890), (2253, 900), (2268, 920), (2281, 937), (2280, 945),
               (2275, 952), (2268, 975), (2263, 1000), (2258, 1025), (2253, 1040), (2240, 1060), (2225, 1069), (2150, 1072), (2085, 1069),
               (2067, 1060), (2050, 1040), (2043, 1020), (2037, 1000), (2027, 975), (2018, 952), (2014, 945), (2015, 938), (2023, 925),
               (2040, 908), (2047, 900), (2050, 880), (2055, 850)]
BASKET_HANDLES = [[(2058, 834), (2048, 815), (2043, 800), (2047, 793), (2056, 795), (2066, 808), (2076, 822), (2082, 832)],
                  [(2110, 834), (2112, 815), (2116, 795), (2126, 781), (2140, 773), (2155, 774), (2166, 780), (2176, 795), (2180, 812),
                   (2181, 830), (2181, 848)],
                  [(2213, 834), (2222, 820), (2233, 807), (2245, 799), (2254, 800), (2256, 808), (2251, 822), (2244, 838)]]


def best_offset(img, hole, region, valid_src, cands):
    """the one shift (dx, dy) whose source best continues the known pixels round the region's part of the hole (median abs difference
    on a 6 px ring), among the candidates whose sources are all valid"""
    H, W = hole.shape
    tgt = hole & region
    ys, xs = np.nonzero(tgt)
    ring = cv2.dilate(tgt.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool) & ~hole & region
    ry, rx = np.nonzero(ring)
    best = None
    for dx, dy in cands:
        sy, sx = ys + dy, xs + dx
        if sy.min() < 0 or sx.min() < 0 or sy.max() >= H or sx.max() >= W:
            continue
        if not valid_src[sy, sx].all():
            continue
        qy, qx = np.clip(ry + dy, 0, H - 1), np.clip(rx + dx, 0, W - 1)
        sc_ = float(np.median(np.abs(img[ry, rx] - img[qy, qx]).mean(1))) + 0.0002 * (abs(dx) + abs(dy))
        if best is None or sc_ < best[0]:
            best = (sc_, dx, dy)
    return best


def quilt(img, need, valid_src, care, cands, tile=20, margin=6, seed=0):
    """block fill (image quilting with structured shifts): tiles of the needed area, nearest the known pixels first; for each tile the
    shift whose source patch best matches the known or already filled pixels in the tile's margin (sum of squared differences), among
    shifts whose sources are all valid; pasted with a feather over the margin. care = pixels that count for the score."""
    H, W = need.shape
    out = img.copy()
    filled = ~need
    dist = cv2.distanceTransform(need.astype(np.uint8), cv2.DIST_L2, 5)
    ys, xs = np.nonzero(need)
    tiles = {}
    for y, x in zip(ys, xs):
        k = (y // tile, x // tile)
        tiles[k] = min(tiles.get(k, 1e9), dist[y, x])
    order = sorted(tiles, key=lambda k: tiles[k])
    C = np.array(cands, np.int32)
    picks = []
    for ty, tx in order:
        y0, x0 = ty * tile, tx * tile
        Y0, X0, Y1, X1 = max(y0 - margin, 0), max(x0 - margin, 0), min(y0 + tile + margin, H), min(x0 + tile + margin, W)
        gy, gx = np.mgrid[Y0:Y1, X0:X1]
        inner = need[Y0:Y1, X0:X1] & ~filled[Y0:Y1, X0:X1] & (gy >= y0) & (gy < y0 + tile) & (gx >= x0) & (gx < x0 + tile)
        if not inner.any():
            continue
        sc_mask = filled[Y0:Y1, X0:X1] & care[Y0:Y1, X0:X1]
        sy = gy[None] + C[:, 1, None, None]
        sx = gx[None] + C[:, 0, None, None]
        okb = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
        syc, sxc = np.clip(sy, 0, H - 1), np.clip(sx, 0, W - 1)
        vs = (valid_src | (filled & ~need))[syc, sxc] & okb
        good = (vs | ~inner[None]).reshape(len(C), -1).all(1)
        if not good.any():
            continue
        Cg = C[good]
        P = out[syc[good], sxc[good]]                                          # (n, h, w, 3)
        T = out[Y0:Y1, X0:X1][None]
        if sc_mask.any():
            d = ((P - T) ** 2).sum(-1)
            e = (d * sc_mask[None]).sum((1, 2)) / sc_mask.sum()
        else:
            e = np.zeros(len(Cg))
        e = e + 1e-6 * np.abs(Cg).sum(1)
        b = int(np.argmin(e))
        patch = P[b]
        # feather: inside the tile weight 1, in the margin (where already filled) a ramp
        wgt = np.zeros(inner.shape, np.float32)
        wgt[inner] = 1
        ring = need[Y0:Y1, X0:X1] & filled[Y0:Y1, X0:X1] & ~inner
        dd = cv2.distanceTransform((~inner).astype(np.uint8), cv2.DIST_L2, 3)
        wgt = np.where(ring, np.clip(1 - dd / margin, 0, 1) * 0.5, wgt)
        reg = out[Y0:Y1, X0:X1]
        out[Y0:Y1, X0:X1] = reg * (1 - wgt[..., None]) + patch * wgt[..., None]
        filled[Y0:Y1, X0:X1] |= inner
        picks.append((int(Cg[b][0]), int(Cg[b][1])))
    return out, picks


def basket():
    src = os.path.join(HERE, "boho-A-fin3.png")
    a = load01(src)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    AXc, AYc, K = 2153.0, 1069.0, 0.75
    # the basket: its body and three handles traced by hand on the frame (x3 crops); the planter, the plant and the table are not in it
    body = poly_mask(a.shape, BASKET_BODY)
    hand = np.zeros((H, W), np.uint8)
    for pts in BASKET_HANDLES:
        cv2.polylines(hand, [np.array(pts, np.int32)], False, 1, thickness=6, lineType=cv2.LINE_AA)
    sprite = body | hand.astype(bool)
    alpha = cv2.GaussianBlur(sprite.astype(np.float32), (0, 0), 0.8)
    lin = s2l(a)
    Am = np.float32([[K, 0, AXc * (1 - K)], [0, K, AYc * (1 - K)]])
    sc = cv2.warpAffine(lin * alpha[..., None], Am, (W, H), flags=cv2.INTER_AREA)
    sa = np.clip(cv2.warpAffine(alpha, Am, (W, H), flags=cv2.INTER_AREA), 0, 1)
    # the hole: the old basket grown 4 px, not the table's corner in front (x < 2046, y > 1050)
    table = (xx < 2046) & (yy > 1050)
    hole = cv2.dilate(sprite.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~table
    # what lies behind, by structure (read on the frame): the plaster wall (x < 2157), the door's shadowed jamb (2157-2185), its lit
    # stile (2185-2222), the panel (x >= 2222, above its bottom rail at y 985), the bottom rail (985-1038), the floor (y >= 1038)
    planter = poly_mask(a.shape, [(1960, 820), (2026, 820), (2030, 925), (2026, 1036), (1960, 1036)])
    valid = ~hole & ~planter & ~table
    # where the new basket will not cover it (alpha < 0.98), the background is needed
    need = hole & ~(sa > 0.98)
    # the wall (x < 2157): harmonic from the wall round it (the planter, the plant and the basket kept out), with the wall's own grain
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
    used = {"wall": "harmonic + grain (sd %.3f)" % sd}
    # the door (jamb, stile, panel, bottom rail) and the floor: quilted from the door and the floor round them with structured shifts
    rest = need & ~wallr
    cands = [(dx, dy) for dx in range(-96, 100, 4) for dy in range(-140, 60, 4) if (dx, dy) != (0, 0)]
    care = ~hole | wallr
    fill, picks = quilt(fill, rest, valid & (xx >= 2150), care, cands, tile=16, margin=6)
    used["door_floor"] = dict(tiles=len(picks), shifts_used=sorted(set(picks))[:40])
    hole_fill = need
    # seams between regions inside the hole softened (2 px), the hole's edge feathered (1.5 px)
    oa = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.5)[..., None] * cv2.dilate(hole.astype(np.uint8), np.ones((5, 5), np.uint8))[..., None]
    out = lin * (1 - oa) + fill * oa
    # a contact shadow for the new size, then the basket
    fp = np.zeros((H, W), np.uint8)
    nb = np.nonzero(sa[1060:1072] > 0.5)
    half = int((nb[1].max() - nb[1].min()) / 2) if nb[1].size else 55
    cx_ = int((nb[1].max() + nb[1].min()) / 2) if nb[1].size else int(AXc)
    cv2.ellipse(fp, (cx_, int(AYc) - 1), (half + 3, 4), 0, 0, 360, 1, -1)
    shadow = np.clip(0.5 * cv2.GaussianBlur(fp.astype(np.float32), (0, 0), 2.0)
                     + 0.2 * cv2.GaussianBlur(cv2.warpAffine(fp.astype(np.float32), np.float32([[1, 0, -6], [0, 1, 1]]), (W, H)), (0, 0), 6), 0, 0.6)
    shadow *= (yy >= 1058) * ~table
    out = out * (1 - shadow[..., None] * (1 - sa[..., None]))
    out = out * (1 - sa[..., None]) + np.clip(sc / np.maximum(sa[..., None], 1e-4), 0, 1) * sa[..., None]
    o8 = save8(l2s(out), os.path.join(HERE, "boho-A-fin4.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    zone = cv2.dilate((hole | (sa > 0) | (shadow > 0.002)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~table
    rec = check(o8, a8, zone, "boho-A-fin4.png")
    by, bx = np.nonzero(body)
    hb, wb = int(by.max() - by.min()), int(bx.max() - bx.min())
    rec.update(base="boho-A-fin3.png", anchor_floor_contact=[AXc, AYc], scale=K, basket_body_px_before=[wb, hb],
               basket_body_px_after=[round(wb * K, 1), round(hb * K, 1)], planter_body_px=[199, 216],
               ratio_height_after=round(hb * K / 216, 2), ratio_width_after=round(wb * K / 199, 2), card_ratio=round(38 / 45, 2),
               fills=used,
               method="the basket's body and three handles traced by hand; x0.75 about its floor contact; behind it, where the new basket "
                      "does not cover: the plaster wall harmonic + its grain, the door (jamb, stile, panel, rail) and the floor quilted in 16 px "
                      "tiles from the door and floor round them (structured shifts scored on the tiles' margins); a contact shadow for the new "
                      "base; the planter, the plant and the table untouched")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
CROP_SETS = [
    ("mc-rug", "modern-country-A-fix1.png", "modern-country-A-fix2.png", [((300, 1390, 2736, 1536), 1), ((1950, 1420, 2150, 1536), 4),
                                                                        ((500, 1420, 700, 1536), 4)]),
    ("boho-basket", "boho-A-fin3.png", "boho-A-fin4.png", [((1780, 700, 2420, 1120), 1), ((2010, 760, 2300, 1080), 2)]),
]


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    outl = []
    for name, b, a_, boxes in CROP_SETS:
        Bm = Image.open(os.path.join(HERE, b)).convert("RGB")
        Am = Image.open(os.path.join(HERE, a_)).convert("RGB")
        panels = []
        for box, sc in boxes:
            w, h = box[2] - box[0], box[3] - box[1]
            rs = Image.NEAREST if sc > 1 else Image.LANCZOS
            panels.append((Bm.crop(box).resize((w * sc, h * sc), rs), Am.crop(box).resize((w * sc, h * sc), rs), sc))
        wide = any(p[0].width > 1400 for p in panels)
        if wide:   # stack before above after
            Wd = max(p[0].width for p in panels) + 20
            Ht = sum(2 * p[0].height + 60 for p in panels) + 40
        else:
            Wd = max(max(p[0].width for p in panels) * 2 + 30, 700)
            Ht = sum(p[0].height + 30 for p in panels) + 40
        im = Image.new("RGB", (Wd, Ht), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: {b} -> {a_}", fill=(0, 0, 0), font=f)
        y = 35
        for pb, pa, sc in panels:
            tag = "100 %" if sc == 1 else f"x{sc}"
            if wide:
                d.text((10, y), f"before {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, y + 24))
                d.text((10, y + 30 + pb.height), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pa, (10, y + 54 + pb.height))
                y += 2 * pb.height + 60
            else:
                d.text((10, y), f"before {tag}", fill=(0, 0, 0), font=f)
                d.text((20 + pb.width, y), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, y + 24))
                im.paste(pa, (20 + pb.width, y + 24))
                y += pb.height + 30
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    return outl


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent",
                                                              source="docs/proposals/tool-shells-and-qa-items-2026-11-07.md rows 46-47",
                                                              tokens=0, var2="none", note="TEST, not for the site; new files only")
    for k in sys.argv[1:]:
        r = globals()[k]()
        R[k] = r
        print(k, r if isinstance(r, list) else json.dumps({kk: vv for kk, vv in r.items() if "px" in kk or kk in ("file", "ratio_width_after", "before", "after")}))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
