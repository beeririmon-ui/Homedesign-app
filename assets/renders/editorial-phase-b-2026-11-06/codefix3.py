#!/usr/bin/env python3
"""
codefix3.py: QA's zero-token code fixes on the editorial frames (qa/reports/2026-11-07-editorial-fin2-ed4-country.md, sections 1 and 5),
render-agent, 2026-11-07. No var2, 0 tokens. New files only, next to the originals; each fix works inside its own mask and the record
counts the pixels changed inside and outside it (outside must be 0).
  boho     boho-A-fin2 -> boho-A-fin3: the seam at x ~400 (y 250-460) where the fill met the bamboo light's glow, softened over ~40 px
  med      mediterranean-A-ed4 -> mediterranean-A-ed5: (a) the old bowl rim's echo on the bench front right of the bowl rebuilt from the
           bench front round it; (b) the two generic back cushions of the bench to sand linen (hue / value only), so our white cushion
           (the right one) stands apart
  jar      japandi-A-ed4 -> japandi-A-ed5: the narrowed jar redone from the original frame with a clean fill: the old rim's wings,
           the two notches, the base (rounded, with a contact shadow, no light band, no grey patch)
  wm       warm-modern-A-ed4 -> warm-modern-A-ed5: the pendant 6 -> 5 rings (ring 5 taken out, ring 6 lifted behind ring 4's rim),
           the gap closed with the plain wall
  mc       modern-country-A -> modern-country-A-fix1: (a) the three cups plain glazed (no speckle, no tanned rim); (b) the fly-like mark on
           the right floral cushion; (c) both curtains lighter, toward #EDE7DB
  crops    before / after crops (100 % and x4) in codefix3-before-after/
  sheet    codefix3-sheet.jpg
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

REC = os.path.join(HERE, "codefix3.json")
CROPS = os.path.join(HERE, "codefix3-before-after")


def save8(a, p):
    o8 = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(p)
    return o8


def lab_of(a):
    """float Lab (L 0-100, a, b signed) of an sRGB float image"""
    lab = cv2.cvtColor((np.clip(a, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    return lab[..., 0] * 100 / 255, lab[..., 1] - 128, lab[..., 2] - 128


def lab_f(a):
    """float Lab via OpenCV's float path (no 8-bit rounding); input sRGB float 0-1"""
    return cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_f(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def check(out8, in8, mask, name):
    moved = np.abs(out8.astype(np.int16) - in8.astype(np.int16)).max(2) > 0
    allowed = mask.astype(bool)
    return dict(px_changed=int(moved.sum()), px_changed_outside_mask=int((moved & ~allowed).sum()), mask_px=int(allowed.sum()), file=name)


def poly_mask(shape, pts):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


# ----------------------------------------------------------------------------------------------------------------------------------
def boho():
    """the fin2 fill (right of x 399) met the original wall (left), which there still carries the old big sun's fringe shadow: an 8-14
    level step. Per row, the light across x 379-419 becomes a straight ramp between its two ends; the bamboo light is not touched"""
    src = os.path.join(HERE, "boho-A-fin2.png")
    a = load01(src)
    H, W = a.shape[:2]
    lin = s2l(a)
    L, _, _ = lab_of(a)
    y0, y1, X, HALF = 238, 474, 399, 20
    # the bamboo light, set by hand on the frame: its ball (ellipse c (326, 395), r (66, 72)) and its arm and wood cap (x 290-352, y 250-330),
    # grown 3 px; kept out
    lamp = np.zeros((H, W), np.uint8)
    cv2.ellipse(lamp, (326, 395), (66, 72), 0, 0, 360, 1, -1)
    lamp[250:330, 290:352] = 1
    lamp = cv2.dilate(lamp, np.ones((7, 7), np.uint8)).astype(bool)
    # per row: the light's low frequencies across the band replaced by a straight ramp between the wall at the band's left end (x 379, or
    # just right of the light's ball where it reaches into the band) and the fill at its right end (x 419); the fine grain (sigma 2) kept
    wallm = ~lamp
    lowc, den = nblur(lin, wallm.astype(np.float32), 2.0)
    xs = np.arange(W)
    gain = np.ones((H, W, 3), np.float32)
    mask = np.zeros((H, W), bool)
    xl_used = []
    for y in range(y0, y1):
        xl = X - HALF
        while xl < X - 1 and lamp[y, xl]:
            xl += 1
        if lamp[y, xl]:
            continue
        xr = X + HALF
        vr = np.median(lin[max(y - 2, 0):y + 3, xr - 3:xr + 1].reshape(-1, 3), axis=0)
        # beside the ball no clean wall is left of the seam: there the fill's own level (eased in by how far the ball reaches)
        sub = lin[max(y - 2, 0):y + 3, xl:xl + 4][~lamp[max(y - 2, 0):y + 3, xl:xl + 4]]
        vw = np.median(sub, axis=0) if sub.size else vr
        wb = float(np.clip((xl - (X - HALF)) / 10.0, 0, 1))
        vl = vw * (1 - wb) + vr * wb
        t = ((xs[xl:xr] - xl) / float(xr - xl))[:, None]
        tgt = vl[None, :] * (1 - t) + vr[None, :] * t
        gain[y, xl:xr] = tgt / np.maximum(lowc[y, xl:xr], 1e-5)
        mask[y, xl:xr] = ~lamp[y, xl:xr]
        xl_used.append(xl)
    # the gain itself smoothed a little along y (rows are independent), eased in and out at the band's top and bottom
    gain = cv2.GaussianBlur(gain, (0, 0), sigmaX=0.6, sigmaY=4.0)
    rows = np.arange(H)
    ease = np.clip(np.minimum(rows - y0, y1 - rows) / 12.0, 0, 1)[:, None, None]
    gain = 1 + (gain - 1) * ease
    wm = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.8) * mask
    # right at the seam (x 395-403) the fine grain still holds the step: there it is the fill's own grain from 8 px to the right
    G = lin / np.maximum(lowc, 1e-5)
    seam = np.zeros((H, W), bool)
    seam[y0:y1, X - 4:X + 5] = True
    seam &= mask
    lin2 = lin.copy()
    lin2[seam] = (lowc * np.roll(G, -8, axis=1))[seam]
    k = 1 + (gain - 1) * wm[..., None]
    out = l2s(lin2 * k)
    o8 = save8(out, os.path.join(HERE, "boho-A-fin3.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    rec = check(o8, a8, mask, "boho-A-fin3.png")
    rec.update(base="boho-A-fin2.png", seam_x=X, rows=[y0, y1], band_px=2 * HALF, left_anchor_x=[int(min(xl_used)), int(max(xl_used))],
               method="per row, the low frequencies (sigma 2) across x 379-419 replaced by a straight ramp from the wall at the band's left end "
                      "(beside the bamboo light's ball, where no clean wall is left, the fill's own level) to the fill at its right end; fine grain kept, "
                      "at the seam itself (x 395-403) the fill's grain from 8 px right; the light's pixels kept out")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
def med():
    src = os.path.join(HERE, "mediterranean-A-ed4.png")
    a = load01(src)
    H, W = a.shape[:2]
    out = a.copy()
    L, A_, B_ = lab_of(a)
    rec = {}
    # (a) the echo of the old bowl rim on the bench front, right of / above the new bowl: a faint light + dark double line ~4-16 px above
    # the new bowl's tanned rim. Per column (x 1398-1482): the rim = the first row below y 1145 that is tan (b* >= 19.5, L* < 55); the band
    # rim-20 .. rim-4 (the bowl's own lip highlight right above its rim is kept) is rebuilt as the bench front: a straight fit in y on the
    # clean rows above it (y 1146 .. rim-17), plus those rows' own grain
    lin = s2l(a)
    mask_a = np.zeros((H, W), bool)
    fill_a = lin.copy()
    cols = {}
    for x in range(1392, 1483):
        rim = None
        for y in range(1146, 1215):
            if B_[y, x] >= 19.5 and L[y, x] < 55:
                rim = y
                break
        if (rim is None or rim > 1200) and 1460 <= x <= 1482:
            rim = 1190                                                    # where the bowl's rim turns down (x 1460-1482): above its lip
        if rim is None:
            continue
        b0, b1 = max(rim - 20, 1150), rim - 4
        c0, c1 = 1146, max(b0 - 1, 1150)
        ys = np.arange(c0, c1)
        if b1 <= b0 or ys.size < 3:
            continue
        A2 = np.stack([ys, np.ones_like(ys)], 1).astype(np.float32)
        coef = np.linalg.lstsq(A2, lin[c0:c1, x], rcond=None)[0]          # (2, 3): slope and offset per channel
        cols[x] = (rim, b0, b1, c0, c1, coef)
    xs_ = sorted(cols)
    # the fits smoothed across columns (sigma 4 columns), so the band has no column-to-column streaks
    C = np.stack([cols[x][5] for x in xs_])                               # (n, 2, 3)
    Cs = cv2.GaussianBlur(C.reshape(len(xs_), 6).astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=4).reshape(len(xs_), 2, 3)
    for n, x in enumerate(xs_):
        rim, b0, b1, c0, c1, coef = cols[x]
        ys = np.arange(c0, c1)
        A2 = np.stack([ys, np.ones_like(ys)], 1).astype(np.float32)
        yb = np.arange(b0, b1 + 1)
        model = np.stack([yb, np.ones_like(yb)], 1).astype(np.float32) @ Cs[n]
        gr = lin[c0:c1, x] / np.maximum(A2 @ Cs[n], 1e-5)
        wx = float(np.clip((x - 1392) / 6.0, 0, 1) * np.clip((1482 - x) / 4.0, 0, 1))
        new_ = model * gr[np.arange(yb.size) % ys.size]
        fill_a[b0:b1 + 1, x] = lin[b0:b1 + 1, x] * (1 - wx) + new_ * wx
        mask_a[b0:b1 + 1, x] = True
    ma = cv2.GaussianBlur(mask_a.astype(np.float32), (0, 0), 0.8) * cv2.dilate(mask_a.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = l2s(lin * (1 - ma[..., None]) + fill_a * ma[..., None])
    mask_a = ma > 0
    rec["a_rim_echo"] = dict(columns=[1392, 1482], px=int(mask_a.sum()),
                             method="per column, the band 4-20 px above the new bowl's tanned rim (the bowl and its lip highlight kept) rebuilt "
                                    "as a straight fit in y of the clean bench front above it (from y 1146; fits smoothed over 4 columns), "
                                    "with those rows' own grain")
    # (b) the two generic back cushions (left, middle) to sand linen; the right one stays white (our cushions-cj-washed-cotton-frayed White)
    left = poly_mask(a.shape, [(208, 713), (232, 716), (256, 725), (290, 730), (340, 736), (390, 739), (440, 738), (490, 734), (540, 727),
                               (604, 722), (604, 1000), (470, 1000), (420, 1012), (264, 1012), (258, 960), (252, 900), (240, 834),
                               (232, 786), (226, 772), (217, 752), (209, 717)])
    mid = poly_mask(a.shape, [(906, 726), (922, 725), (967, 732), (1033, 740), (1067, 742), (1100, 739), (1133, 737), (1167, 734), (1200, 727),
                              (1208, 724), (1209, 765), (1212, 815), (1216, 890), (1223, 966),
                              (1206, 966), (1192, 895), (1182, 826), (1140, 828), (1000, 834), (906, 842)])
    L2, A2, B2 = lab_of(out)
    excl = (A2 > 9.5) | (B2 > 21.5) | (L2 < 22)                         # terracotta, straw hat (and its band), deep gaps
    olive = (L2 < 38) & (B2 > 17) & (A2 < 7)                              # the moss lumbar (L 26-33, b 20) and its dark ruffle
    excl = cv2.dilate((excl | olive).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    cm = (left | mid) & ~excl
    cm = cv2.morphologyEx(cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    # inside the outline by 2 px, feathered 2 px: the very tips of the ruffles keep a little of their light
    cm_in = cv2.erode(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    wgt = cv2.GaussianBlur(cm_in, (0, 0), 1.3) * cm
    lab = lab_f(out)
    # sand linen: a little darker and warmer, the texture and shading kept (L scaled about the cushion's own mean, a/b shifted)
    Lm = float(lab[..., 0][cm].mean())
    tgt = dict(dL=-6.0, da=1.5, db=6.0)
    newlab = lab.copy()
    newlab[..., 0] = lab[..., 0] + tgt["dL"]
    newlab[..., 1] = lab[..., 1] + tgt["da"]
    newlab[..., 2] = lab[..., 2] + tgt["db"]
    rec_rgb = rgb_f(newlab)
    out = out * (1 - wgt[..., None]) + rec_rgb * wgt[..., None]
    rec["b_bench_cushions"] = dict(cushions="left (x 208-604, y 713-1012) and middle (x 906-1223, y 724-966), outlines along their frayed tops; the right one stays white (ours)",
                                   px=int((wgt > 0).sum()), mean_L_before=round(Lm, 1), shift_Lab=tgt,
                                   target="sand linen ~ L 61 a 6 b 19 against the white cushion's L 71 a 4 b 12",
                                   method="hand outlines along the frayed flange (feathered 2 px), terracotta / hat / moss / gaps cut out by colour; Lab shift only, "
                                          "so the crinkle texture and the shading stay")
    o8 = save8(out, os.path.join(HERE, "mediterranean-A-ed5.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    allm = cv2.dilate((mask_a | (wgt > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
    rec.update(check(o8, a8, allm, "mediterranean-A-ed5.png"))
    rec["px_changed_a"] = int((np.abs(o8.astype(np.int16) - a8.astype(np.int16)).max(2) > 0)[mask_a].sum())
    rec["px_changed_b"] = int((np.abs(o8.astype(np.int16) - a8.astype(np.int16)).max(2) > 0)[wgt > 0].sum())
    rec["base"] = "mediterranean-A-ed4.png"
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
def mc():
    src = os.path.join(HERE, "modern-country-A.png")
    a = load01(src)
    H, W = a.shape[:2]
    out = a.copy()
    rec = {}
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    # (a) the three cups: a plain glaze, no speckle and no tanned rim. Outlines by hand (the sofa behind is the same cream), 2 px inside.
    # Lightness: the dots and the rim's dark tan line lifted to a 7 px closing of L* (the form's shading kept). Colour: a/b replaced by their
    # own 11 px median (spatter and the tan rim gone), then 3 b* cooler, so the glaze reads plain off-white next to the ivory bowl
    cup_polys = [
        [(1561, 1104), (1575, 1099), (1612, 1097), (1648, 1099), (1663, 1105), (1662, 1115), (1658, 1140), (1654, 1160), (1647, 1180),
         (1640, 1193), (1630, 1196), (1600, 1197), (1588, 1194), (1581, 1182), (1572, 1160), (1566, 1135), (1562, 1115)],
        [(1668, 1121), (1690, 1115), (1730, 1116), (1757, 1122), (1756, 1132), (1752, 1153), (1745, 1175), (1737, 1190), (1727, 1197),
         (1690, 1197), (1683, 1190), (1675, 1170), (1671, 1150), (1669, 1133)],
        [(1756, 1146), (1770, 1142), (1800, 1142), (1818, 1146), (1818, 1160), (1815, 1180), (1808, 1197), (1801, 1204), (1765, 1205),
         (1758, 1199), (1754, 1180), (1755, 1160)]]
    cups = np.zeros((H, W), bool)
    for pts in cup_polys:
        cups |= poly_mask(a.shape, pts)
    cups_raw = cups.copy()
    cups = cv2.erode(cups.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    # the rims' outer lip (the tanned line runs along each cup's top contour, partly outside the inset outline): in a band of the top
    # 16 rows of each cup grown 4 px, the tan pixels (b* > 16) join the cup; and the orange dot at cup 2's right edge
    lip = np.zeros((H, W), bool)
    for pts in cup_polys:
        top = min(p_[1] for p_ in pts)
        pm = poly_mask(a.shape, pts)
        pm[top + 16:] = False
        lip |= cv2.dilate(pm.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    dot = np.zeros((H, W), bool)
    dot[1138:1162, 1745:1762] = True
    lip = (lip & (B_ > 16)) | (dot & ((A_ > 8) | (B_ > 22)))
    lip = cv2.dilate(lip.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (cv2.dilate(cups_raw.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) | dot)
    cups = cups | lip
    lab = lab_f(out)
    Lc = lab[..., 0]
    clo = cv2.morphologyEx(Lc, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    clo = cv2.GaussianBlur(clo, (0, 0), 0.8)
    newL = np.where(cups & ((clo - Lc) > 1.5), clo, Lc)
    def cmed(ch):
        v = np.where(cups, ch, np.nan)
        # an 11 px median of a/b over the cup only (via a normalized blur of the median-filtered, cup-filled channel)
        fill_v = np.where(cups, ch, float(np.nanmedian(v)))
        q = cv2.medianBlur(np.clip((fill_v + 128), 0, 255).astype(np.uint8), 11).astype(np.float32) - 128
        return cv2.GaussianBlur(q, (0, 0), 2.0)
    sa, sb = cmed(lab[..., 1]), cmed(lab[..., 2])
    newlab = lab.copy()
    newlab[..., 0] = newL
    newlab[..., 1] = np.where(cups, sa - 0.5, lab[..., 1])
    newlab[..., 2] = np.where(cups, sb - 3.0, lab[..., 2])
    cw = cv2.GaussianBlur(cups.astype(np.float32), (0, 0), 1.2) * cv2.dilate(cups.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = out * (1 - cw[..., None]) + rgb_f(newlab) * cw[..., None]
    rec["a_cups"] = dict(outlines="three hand outlines (see cup_polys in the script), 2 px inside", px=int((cw > 0).sum()),
                         glaze="plain off-white: the cups' own a/b median, 3 b* cooler; the bowl keeps its speckle and tanned rim",
                         method="dots and the tanned rim line lifted to a 7 px closing of L*; a/b replaced by their 11 px median over the cup, "
                                "b* -3; the form's shading kept")
    # (b) the fly-like mark on the right floral cushion
    fm = np.zeros((H, W), bool)
    fm[861:882, 1591:1611] = True
    dk = fm & (L < (np.median(L[fm]) - 6))
    dk = cv2.dilate(dk.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & fm
    o8t = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    inp = cv2.inpaint(o8t, dk.astype(np.uint8), 4, cv2.INPAINT_TELEA).astype(np.float32) / 255
    ring = cv2.dilate(dk.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~dk
    hp = out - cv2.GaussianBlur(out, (0, 0), 1.2)
    sd = float(np.std(hp[ring].mean(1)))
    rng = np.random.default_rng(3)
    nz = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7)
    nz *= sd / max(float(nz.std()), 1e-6)
    fw = cv2.GaussianBlur(dk.astype(np.float32), (0, 0), 0.8) * cv2.dilate(dk.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = out * (1 - fw[..., None]) + np.clip(inp + nz[..., None], 0, 1) * fw[..., None]
    rec["b_fly"] = dict(box=[1591, 861, 1611, 882], px=int((fw > 0).sum()), method="the dark glyph (L 6 below the cushion ground, grown 2 px) "
                                                                                  "inpainted from the ground round it (Telea r 4) with its grain")
    # (c) both curtains lighter toward #EDE7DB (L 91.8 a 0.6 b 5.6): the curtain pixels in each curtain's box by colour (oat linen: warmer
    # and darker than the plaster and the window), then L lifted and a/b eased toward the card, the folds' shading kept
    # the plaster has the same colour as the oat linen and the window frames carry texture too: both curtains traced by hand on the frame
    # (their outer edges hang nearly straight; the floral cushion and the armchair's throw cut their bottoms)
    left_c = poly_mask(a.shape, [(1610, 79), (1771, 77), (1771, 706), (1745, 711), (1700, 724), (1660, 736), (1640, 745), (1599, 758),
                                 (1599, 650), (1602, 450), (1604, 300), (1607, 200), (1609, 160), (1611, 100)])
    right_c = poly_mask(a.shape, [(2362, 69), (2540, 69), (2545, 108), (2549, 400), (2555, 520), (2559, 600), (2559, 928), (2540, 927),
                                  (2480, 931), (2403, 944), (2380, 956), (2351, 959), (2351, 600), (2356, 500), (2360, 300)])
    curt = (left_c | right_c)
    lab = lab_f(out)
    cm = curt
    Lm, am, bm = [float(lab[..., i][cm].mean()) for i in range(3)]
    t = np.array([91.8, 0.6, 5.6])
    kL, kab = 0.6, 0.6                                                   # "toward": 60 % of the way, folds kept
    newlab = lab.copy()
    newlab[..., 0] = lab[..., 0] + kL * (t[0] - Lm)
    newlab[..., 1] = lab[..., 1] + kab * (t[1] - am)
    newlab[..., 2] = lab[..., 2] + kab * (t[2] - bm)
    cw2 = cv2.GaussianBlur(cv2.erode(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2) * cm
    out = out * (1 - cw2[..., None]) + rgb_f(newlab) * cw2[..., None]
    rec["c_curtains"] = dict(px=int((cw2 > 0).sum()), mean_Lab_before=[round(Lm, 1), round(am, 1), round(bm, 1)], target="#EDE7DB (91.8, 0.6, 5.6)",
                             share_of_the_way=kL, method="both curtains traced by hand (the plaster is the same colour as the linen); Lab "
                                                         "shift of the mean 60 % toward the card, the folds' own L variation kept")
    o8 = save8(out, os.path.join(HERE, "modern-country-A-fix1.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    allm = cv2.dilate(((cw > 0) | (fw > 0) | (cw2 > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
    rec.update(check(o8, a8, allm, "modern-country-A-fix1.png"))
    mv = np.abs(o8.astype(np.int16) - a8.astype(np.int16)).max(2) > 0
    rec["px_changed_a"], rec["px_changed_b"], rec["px_changed_c"] = int(mv[cw > 0].sum()), int(mv[fw > 0].sum()), int(mv[cw2 > 0].sum())
    rec["base"] = "modern-country-A.png"
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
def wm():
    """the pendant 6 -> 5 rings. Rings 5 and 6 are replaced by ring 6 (the bottom ring: its side band and its open, glowing bottom)
    scaled to ring 5's size (x1.25 about the pendant's axis, also in height) and hung right under ring 4's rim, as ring 5 hung; so ring 6
    keeps its look and the stack steps 4 -> 5 as the card does. The pendant ends ~20 px higher; that gap is plain wall (a harmonic field
    from the wall round the pendant, with grain matched to the plain wall beside it)."""
    src = os.path.join(HERE, "warm-modern-A-ed4.png")
    a = load01(src)
    H, W = a.shape[:2]
    lin = s2l(a)
    # rim lines read per column on the frame (dark lines in L*): c4 = ring 4's bottom rim, c5 = ring 5's (where ring 6 starts),
    # yb = the bottom; widths read on rows: ring 5 x 1347-1566, ring 6 x 1368-1548
    x4 = np.array([1344, 1350, 1360, 1370, 1380, 1390, 1400, 1410, 1420, 1430, 1440, 1450, 1460, 1470, 1480, 1490, 1500, 1510, 1520,
                   1530, 1540, 1550, 1560, 1570, 1577])
    c4_m = np.array([200, 198, 195, 192, 193, 189, 188, 186, 185, 185, 184, 183, 183, 183, 183, 183, 184, 185, 186, 187, 189, 191, 194,
                     197, 199])
    x6 = np.array([1368, 1380, 1390, 1400, 1410, 1420, 1430, 1440, 1450, 1460, 1470, 1480, 1490, 1500, 1510, 1520, 1530, 1540, 1548])
    c5_m = np.array([224, 219, 216, 214, 213, 212, 211, 210, 210, 210, 210, 210, 210, 211, 211, 213, 215, 218, 223])
    yb_m = np.array([226, 230, 232, 234, 235, 236, 237, 237, 238, 238, 237, 237, 236, 235, 234, 232, 230, 228, 225])
    AXc, K = 1458.0, 1.25
    # the rim lines as smooth curves (quadratic fits; the reads are whole pixels)
    p4 = np.polyfit(x4, c4_m, 2)
    p5 = np.polyfit(x6, c5_m, 2)
    pb = np.polyfit(x6, yb_m, 2)
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    c4t = np.polyval(p4, X).astype(np.float32)
    Xs = (AXc + (X - AXc) / K).astype(np.float32)
    c5s = (np.polyval(p5, Xs) - 2.0).astype(np.float32)                 # from 2 px above ring 5's rim line (its shadow comes along)
    ybs = np.polyval(pb, Xs).astype(np.float32)
    Ys = (c5s + (Y - c4t) / K).astype(np.float32)
    inzone_x = (X >= 1344) & (X <= 1577)
    below4 = Y > c4t + 0.5
    valid = (Xs >= 1368) & (Xs <= 1548) & (Ys >= c5s - 0.5) & (Ys <= ybs + 2.0) & below4 & inzone_x
    spr = cv2.remap(lin, Xs, Ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # the old rings 5-6 area (to wall where the new bottom ring does not cover it): below ring 4's rim, down to the old bottom + 3
    ybo = np.interp(X, x6, yb_m, left=0, right=0)
    old56 = inzone_x & below4 & (Y <= np.maximum(ybo, np.interp(X, [1344, 1350, 1360, 1368, 1548, 1560, 1570, 1577], [205, 208, 212, 226, 225, 210, 206, 201])) + 3)
    # plain wall: harmonic from the wall round the pendant (the pendant and the art below y 252 kept out)
    pend = np.zeros((H, W), bool)
    for x in range(1290, 1630):
        ylim = 175 if 1295 <= x <= 1620 else 0
        if 1344 <= x <= 1577:
            ylim = max(ylim, int(np.interp(x, [1344, 1350, 1360, 1368, 1548, 1560, 1570, 1577], [205, 208, 212, 226, 225, 210, 206, 201])))
        if 1368 <= x <= 1548:
            ylim = max(ylim, int(np.interp(x, x6, yb_m)))
        pend[:ylim + 4, x] = True
    wallk = ~pend
    box = (slice(150, 252), slice(1300, 1620))
    wl, den = nblur(lin, wallk.astype(np.float32), 4)
    kn = (wallk & (den > 0.3))[box]
    low = lin.copy()
    low[box] = harmonic(np.where(kn[..., None], wl[box], 0), kn, f=2, iters=3000)
    ref = lin[200:250, 1180:1290]
    hp = (ref / np.maximum(cv2.GaussianBlur(ref, (0, 0), 2.0), 1e-5)).mean(2)
    sd = float(np.std(hp))
    rng = np.random.default_rng(17)
    nz = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8)
    nz *= sd / max(float(nz.std()), 1e-6)
    wall = low * (1 + nz)[..., None]
    wf = cv2.GaussianBlur(old56.astype(np.float32), (0, 0), 0.7) * old56
    out = lin * (1 - wf[..., None]) + wall * wf[..., None]
    sa = cv2.GaussianBlur(valid.astype(np.float32), (0, 0), 0.7) * below4 * inzone_x
    out = out * (1 - sa[..., None]) + spr * sa[..., None]
    o8 = save8(l2s(out), os.path.join(HERE, "warm-modern-A-ed5.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    m = cv2.dilate((old56 | (sa > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
    rec = check(o8, a8, m, "warm-modern-A-ed5.png")
    rec.update(base="warm-modern-A-ed4.png", rings_before=6, rings_after=5, scale=K, axis_x=AXc,
               rim_lines={"x_ring4": x4.tolist(), "ring4_bottom": c4_m.tolist(), "x_ring6": x6.tolist(), "ring5_bottom": c5_m.tolist(),
                          "old_bottom": yb_m.tolist()},
               method="rings 5 and 6 replaced by ring 6 (side band and open bottom) scaled x1.25 about the axis to ring 5's size and hung "
                      "under ring 4's rim; the ~20 px gap below and the leftover old ring pixels plain wall (harmonic + matched grain)")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
JAR_SCALE_X = 0.76


def jar():
    """Japandi A: the jar narrowed x0.76 about its axis (as ED4) redone from the original frame with a clean fill. Its outline: the
    right edge (a strong gradient on every row) mirrored about the axis x 666, the rim (x 621-711, y 922-937) as measured, the base
    rounded (y 1117-1129). The strips it leaves: the background shifted in along each structure's own slope, measured on its edges:
    the top rail and glass horizontally (34 px), the garden and the upper rails at 0.41 / 0.44 px per px (34 px), the lower rails and
    the sill's front edge at 0.53-0.55 (22-40 px). The branch stems in front of the rim are the original's. The old contact shadow is
    taken out with the old base and a new one laid under the narrower base."""
    base = load01(os.path.join(HERE, "japandi-A.png"))
    ed4 = load01(os.path.join(HERE, "japandi-A-ed4.png"))
    H, W = base.shape[:2]
    L, A_, B_ = lab_of(base)
    gx = cv2.Sobel(cv2.GaussianBlur(L, (0, 0), 1.2), cv2.CV_32F, 1, 0, ksize=3)
    AX = 666.0
    ytop, ybot = 922, 1128
    # the right edge tracked row by row (within 3 px of the row before; a free search caught the window rail's edge at y ~1060),
    # from y 1000 up and down, then a smooth 4th-degree fit over the body
    hw = np.zeros(H)
    r0 = 680 + int(np.argmax(gx[1000, 680:760]))
    edge = {1000: r0}
    for rng_ in (range(1001, 1117), range(999, 937, -1)):
        prev = r0
        for y in rng_:
            lo_, hi_ = prev - 3, prev + 4
            prev = lo_ + int(np.argmax(gx[y, lo_:hi_]))
            edge[y] = prev
    ys_ = np.array(sorted(edge))
    pf = np.polyfit(ys_, np.array([edge[y] for y in ys_]) - AX, 4)
    hw[938:1117] = np.polyval(pf, np.arange(938, 1117))
    hw[ytop:938] = 46.0                                                   # the rim, x 621-711
    for y in range(1117, ybot):
        hw[y] = hw[1116] * np.sqrt(max(1 - ((y - 1116) / 11.5) ** 2, 0))  # the base's rounded front
    xx = np.arange(W, dtype=np.float32)[None, :]
    yy = np.arange(H)[:, None]
    rows = (yy >= ytop) & (yy < ybot)
    old = rows & (np.abs(xx - AX) <= hw[:, None] + 3)
    new_a = np.clip(hw[:, None] * JAR_SCALE_X + 0.5 - np.abs(xx - AX), 0, 1) * rows
    # the old contact shadow (under the base and to its right, on the sill top above the sill's front edge)
    sill_edge = 1100 + (770 - xx) * 0.55
    oldsh = (yy >= 1112) & (yy <= 1137) & (xx >= 612) & (xx <= 738) & (yy < sill_edge - 1)
    old = old | oldsh
    # the new jar: each row of the old one sampled narrower about the axis
    jar_px = base.copy()
    for y in range(ytop, ybot):
        xs = np.arange(int(AX - hw[y] - 3), int(AX + hw[y] + 4))
        src = AX + (xs - AX) / JAR_SCALE_X
        for c in range(3):
            jar_px[y, xs, c] = np.interp(src, np.arange(W), base[y, :, c])
    # the strips: background shifted in from beside the jar along each structure's slope (per row band, cross-faded over 8 rows)
    def sh(dx, dy):
        return cv2.warpAffine(base, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    yv = np.arange(H, dtype=np.float32)
    def band(y0, y1):
        return (np.clip((yv - y0 + 4) / 8.0, 0, 1) * np.clip((y1 - yv + 4) / 8.0, 0, 1))[:, None, None]
    bands_L = [(0, 945, 34, 0.0), (945, 1030, 34, 0.41), (1030, 9999, 22, 0.41)]
    bands_R = [(0, 945, 34, 0.0), (945, 1030, 34, 0.44), (1030, 1078, 22, 0.44), (1078, 1110, 22, 0.53), (1110, 9999, 40, 0.55)]
    bgL = np.zeros_like(base)
    wl = np.zeros((H, 1, 1), np.float32)
    for y0, y1, sx, sl in bands_L:
        w_ = band(y0, y1)
        bgL += sh(sx, -sl * sx) * w_                                     # out(x, y) = base(x - sx, y + sl * sx)
        wl += w_
    bgL /= np.maximum(wl, 1e-6)
    bgR = np.zeros_like(base)
    wr = np.zeros((H, 1, 1), np.float32)
    for y0, y1, sx, sl in bands_R:
        w_ = band(y0, y1)
        bgR += sh(-sx, sl * sx) * w_                                     # out(x, y) = base(x + sx, y - sl * sx)
        wr += w_
    bgR /= np.maximum(wr, 1e-6)
    bg = np.where((xx < AX)[..., None], bgL, bgR)
    oa = cv2.GaussianBlur(old.astype(np.float32), (0, 0), 1.5)[..., None] * cv2.dilate(old.astype(np.uint8), np.ones((5, 5), np.uint8))[..., None]
    out = base * (1 - oa) + bg * oa
    # under and right of the base (y 1118 on, x 628-745, grown 3 px; left of it the shifted rails are right) the shifted sources would reach into the old jar: there the sill top is a
    # smooth field, solved on the composite so far (the strip fill round it is its boundary; the new jar, the rails and the sill's
    # front face left out), with the sill's own grain (sd 0.10), feathered 3 px
    U = old & (yy >= 1118) & (xx >= 628) & (xx <= 745) & (yy < sill_edge - 1)
    U = cv2.dilate(U.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & (yy < sill_edge - 1) & (new_a <= 0) & (yy >= 1116) & (xx >= 625)
    Lo, _, _ = lab_of(out)
    lin_o = s2l(out)
    sb = (slice(1096, 1152), slice(590, 772))
    newj = new_a > 0
    kn = (~U & ~newj & (Lo > 40) & (yy < sill_edge - 2))[sb]
    wl_, den_ = nblur(lin_o[sb], kn.astype(np.float32), 2)
    kn &= den_ > 0.3
    hl = harmonic(np.where(kn[..., None], wl_, 0), kn, f=1, iters=4000)
    rng = np.random.default_rng(29)
    nz = cv2.GaussianBlur(rng.standard_normal(hl.shape[:2]).astype(np.float32), (0, 0), 0.7)
    nz *= 0.10 / max(float(nz.std()), 1e-6)
    sill = out.copy()
    sill[sb] = l2s(np.clip(hl * (1 + nz)[..., None], 0, 1))
    Ui = cv2.erode(U.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    ua = np.maximum(cv2.GaussianBlur(Ui, (0, 0), 1.5), (old & U).astype(np.float32))[..., None] * U[..., None]
    out = out * (1 - ua) + sill * ua
    # a new contact shadow under the narrower base: a tight core and a soft spread, a little to the right (the lantern is on the left)
    fp = np.zeros((H, W), np.uint8)
    cv2.ellipse(fp, (int(AX) + 1, 1125), (int(hw[1116] * JAR_SCALE_X) + 1, 3), 0, 0, 360, 1, -1)
    core = cv2.GaussianBlur(fp.astype(np.float32), (0, 0), 1.8)
    spread = cv2.GaussianBlur(cv2.warpAffine(fp.astype(np.float32), np.float32([[1, 0, 6], [0, 1, -1]]), (W, H)), (0, 0), 5.0)
    shadow = np.clip(0.6 * core + 0.25 * spread, 0, 0.7) * (yy >= 1110) * (yy < sill_edge)
    out = out * (1 - shadow[..., None] * (1 - new_a[..., None]))
    na = new_a[..., None].astype(np.float32)
    out = out * (1 - na) + jar_px * na
    # the branch stems in front of the rim (rows 918-937): the original's
    stems = np.zeros((H, W), bool)
    stems[918:938, 660:706] = (L[918:938, 660:706] > 45)
    stems = cv2.dilate(stems.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    stems = cv2.GaussianBlur(stems, (0, 0), 0.5)[..., None]
    out = out * (1 - stems) + base * stems
    o8 = save8(out, os.path.join(HERE, "japandi-A-ed5.png"))
    e8 = (ed4 * 255 + 0.5).astype(np.uint8)
    b8 = (base * 255 + 0.5).astype(np.uint8)
    zone = cv2.dilate((old | (new_a > 0) | (shadow > 0.002)).astype(np.uint8), np.ones((9, 9), np.uint8))
    ed4_changed = np.abs(e8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    rec = check(o8, e8, zone.astype(bool) | ed4_changed, "japandi-A-ed5.png")
    mv0 = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    rows_ = [y for y in range(938, 1118)]
    wmax = 2 * float(hw[938:1118].max())
    rec.update(base="japandi-A.png (the original; ED4's jar redone)", compared_with="japandi-A-ed4.png", scale_x=JAR_SCALE_X, axis_x=AX,
               size_px_before=[round(wmax, 1), ybot - ytop], size_px_after=[round(wmax * JAR_SCALE_X, 1), ybot - ytop],
               h_over_w_after=round((ybot - ytop) / (wmax * JAR_SCALE_X), 2), px_changed_vs_original=int(mv0.sum()),
               px_changed_vs_original_outside_zone=int((mv0 & ~zone.astype(bool)).sum()),
               strips={"left": bands_L, "right": bands_R}, method=jar.__doc__.strip().replace("\n", " "))
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
CROP_SETS = [
    ("boho-seam", "boho-A-fin2.png", "boho-A-fin3.png", [((330, 220, 470, 500), 1), ((370, 300, 430, 420), 4)]),
    ("med-rim-echo", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", [((1340, 1090, 1540, 1240), 1), ((1380, 1110, 1510, 1225), 4)]),
    ("med-bench-cushions", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", [((150, 650, 1650, 1060), 1), ((190, 690, 330, 800), 4),
                                                                                  ((900, 690, 1060, 770), 4)]),
    ("japandi-jar", "japandi-A-ed4.png", "japandi-A-ed5.png", [((540, 880, 800, 1160), 1), ((600, 905, 735, 960), 4), ((595, 1040, 735, 1100), 4),
                                                              ((600, 1095, 760, 1150), 4)]),
    ("warm-modern-pendant", "warm-modern-A-ed4.png", "warm-modern-A-ed5.png", [((1230, 0, 1700, 330), 1), ((1330, 165, 1600, 250), 4)]),
    ("mc-cups", "modern-country-A.png", "modern-country-A-fix1.png", [((1540, 1080, 1840, 1215), 1), ((1550, 1090, 1700, 1205), 4)]),
    ("mc-fly", "modern-country-A.png", "modern-country-A-fix1.png", [((1540, 820, 1660, 920), 1), ((1585, 855, 1620, 890), 4)]),
    ("mc-curtains", "modern-country-A.png", "modern-country-A-fix1.png", [((1500, 40, 2700, 1000), 1), ((1585, 60, 1645, 200), 4),
                                                                          ((2520, 50, 2600, 220), 4)]),
]


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    outl = []
    for name, b, a_, boxes in CROP_SETS:
        B = Image.open(os.path.join(HERE, b)).convert("RGB")
        A = Image.open(os.path.join(HERE, a_)).convert("RGB")
        panels = []
        for box, sc in boxes:
            w, h = box[2] - box[0], box[3] - box[1]
            rs = Image.NEAREST if sc > 1 else Image.LANCZOS
            pb = B.crop(box).resize((w * sc, h * sc), rs)
            pa = A.crop(box).resize((w * sc, h * sc), rs)
            panels.append((pb, pa, sc, box))
        Wd = max(max(p[0].width for p in panels) * 2 + 30, 700)
        Ht = sum(p[0].height + 30 for p in panels) + 40
        im = Image.new("RGB", (Wd, Ht), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: {b} -> {a_}", fill=(0, 0, 0), font=f)
        y = 35
        for pb, pa, sc, box in panels:
            tag = "100 %" if sc == 1 else f"x{sc}"
            d.text((10, y), f"before {tag}", fill=(0, 0, 0), font=f)
            d.text((20 + pb.width, y), f"after {tag}", fill=(0, 0, 0), font=f)
            im.paste(pb, (10, y + 24))
            im.paste(pa, (20 + pb.width, y + 24))
            y += pb.height + 30
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    return outl


def sheet():
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    R = json.load(open(REC))
    rows = [("Boho: the seam at x~400 softened", "boho-A-fin2.png", "boho-A-fin3.png", (250, 150, 700, 560)),
            ("Mediterranean: rim echo cleaned; bench back cushions to sand (the right one, ours, stays white)", "mediterranean-A-ed4.png",
             "mediterranean-A-ed5.png", (150, 640, 1650, 1240)),
            ("Japandi: the fill round the narrowed jar rebuilt (rim wings, notches, base and contact shadow)", "japandi-A-ed4.png",
             "japandi-A-ed5.png", (500, 820, 840, 1180)),
            ("Warm modern: the pendant 6 -> 5 rings, the gap closed with plain wall", "warm-modern-A-ed4.png", "warm-modern-A-ed5.png",
             (1200, 0, 1730, 340)),
            ("Modern country: plain cups, the fly mark gone, both curtains lighter toward #EDE7DB", "modern-country-A.png",
             "modern-country-A-fix1.png", (1450, 30, 2730, 1230))]
    TH = 520
    tiles = []
    for title, b, a_, box in rows:
        B = Image.open(os.path.join(HERE, b)).convert("RGB").crop(box)
        A = Image.open(os.path.join(HERE, a_)).convert("RGB").crop(box)
        sc = TH / B.height
        tiles.append((title, B.resize((int(B.width * sc), TH), Image.LANCZOS), A.resize((int(A.width * sc), TH), Image.LANCZOS)))
    W = max(t[1].width for t in tiles) * 2 + 60
    H = 70 + len(tiles) * (TH + 60)
    out = Image.new("RGB", (W, H), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((20, 18), "Code fixes, round 3 (2026-11-07): 0 tokens, no var2. TEST, not for the site. Before (left) / after (right).", fill=(0, 0, 0), font=fb)
    y = 70
    for title, B, A in tiles:
        d.text((20, y), title, fill=(0, 0, 0), font=f)
        out.paste(B, (20, y + 30))
        out.paste(A, (40 + B.width, y + 30))
        y += TH + 60
    p = os.path.join(HERE, "codefix3-sheet.jpg")
    out.save(p, quality=90)
    return os.path.relpath(p, HERE)


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent", qa="qa/reports/2026-11-07-editorial-fin2-ed4-country.md",
                                                              tokens=0, var2="none", note="TEST, not for the site; new files only")
    for k in sys.argv[1:]:
        fn = globals()[k]
        if k in ("crops", "sheet"):
            R[k] = fn()
            print(k, R[k])
            continue
        r = fn()
        if r is not None:
            R[k] = r
            print(k, json.dumps({kk: vv for kk, vv in r.items() if "px" in kk or kk == "file"}))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
