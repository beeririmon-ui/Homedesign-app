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
    """the pendant 6 -> 5 rings: ring 5 (the second from the bottom) taken out and ring 6 lifted by the ring pitch (27 px, the same at
    every column: 26-29) so it hangs right behind ring 4's rim, as ring 5 did; where ring 5 and the old ring 6 showed and the lifted one
    does not, plain wall: a harmonic field from the wall round the pendant with the wall's own grain from below"""
    src = os.path.join(HERE, "warm-modern-A-ed4.png")
    a = load01(src)
    H, W = a.shape[:2]
    lin = s2l(a)
    # rim lines read per column on the frame (dark lines in L*): c4 = ring 4's bottom rim, c5 = ring 5's bottom rim, yb = the pendant's
    # bottom (ring 6's lower edge); outside ring 6 (x < 1372 or > 1548) only ring 5 hung below ring 4
    xs_m = np.array([1350, 1360, 1370, 1380, 1390, 1400, 1410, 1420, 1430, 1440, 1450, 1460, 1470, 1480, 1490, 1500, 1510, 1520, 1530, 1540, 1550, 1560, 1570])
    c4_m = np.array([198, 195, 192, 193, 189, 188, 186, 185, 185, 184, 183, 183, 183, 183, 183, 184, 185, 186, 187, 189, 191, 194, 197])
    yb_m = np.array([208, 212, 226, 230, 232, 234, 235, 236, 237, 237, 238, 238, 237, 237, 236, 235, 234, 232, 230, 228, 213, 209, 200])
    D = 27
    xs = np.arange(W)
    c4 = np.interp(xs, xs_m, c4_m)
    yb = np.interp(xs, xs_m, yb_m)
    X0, X1 = 1344, 1577
    yy = np.arange(H)[:, None]
    # the zone that changes: below ring 4's rim (+2, its dark rim line kept) down to the old bottom (+3 for its soft edge)
    zone = (yy > c4[None, :] + 2) & (yy <= yb[None, :] + 3)
    zone[:, :X0] = False
    zone[:, X1:] = False
    # the lifted ring 6: the pixels from c5 (= c4 + 27) to its bottom, moved up by 27, for x in ring 6's span
    r6 = np.zeros((H, W), bool)
    for x in range(1372, 1549):
        r6[int(c4[x]) + 2:int(yb[x]) + 2 - D, x] = True
    lifted = np.roll(lin, -D, axis=0)
    # its soft bottom edge: the last 3 rows fade into the wall
    r6f = cv2.GaussianBlur(r6.astype(np.float32), (0, 0), 0.9)
    # the plain wall behind: harmonic from the wall round the pendant (not the pendant, not the art below y 255)
    box = (slice(150, 262), slice(1300, 1620))
    pend = np.zeros((H, W), bool)
    for x in range(X0 - 2, X1 + 2):
        pend[:int(yb[x]) + 4, x] = True
    pend[:, :X0 - 2] = False
    pend[:, X1 + 2:] = False
    # the upper rings (ring 4 and above) are wider than the zone: keep them out of the wall estimate too (above c4 + 2 within x 1295-1625)
    upper = np.zeros((H, W), bool)
    for x in range(1295, 1625):
        upper[:int(np.interp(x, xs_m, c4_m)) + 3 if 1344 <= x <= 1577 else 200, x] = True
    wallk = ~(pend | upper)
    wl, den = nblur(lin, wallk.astype(np.float32), 4)
    kn = (wallk & (den > 0.3))[box]
    low = lin.copy()
    low[box] = harmonic(np.where(kn[..., None], wl[box], 0), kn, f=2, iters=3000)
    # grain: synthetic, matched to the plain wall beside the pendant (x 1180-1290, y 200-250; below lie the art frames)
    ref = lin[200:250, 1180:1290]
    hp = (ref / np.maximum(cv2.GaussianBlur(ref, (0, 0), 2.0), 1e-5)).mean(2)
    sd = float(np.std(hp))
    rng = np.random.default_rng(17)
    nz = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8)
    nz *= sd / max(float(nz.std()), 1e-6)
    wall = low * (1 + nz)[..., None]
    out = lin.copy()
    zf = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), 0.7) * zone
    out = out * (1 - zf[..., None]) + wall * zf[..., None]
    out = out * (1 - r6f[..., None]) + lifted * r6f[..., None]
    out = np.where(zone[..., None] | (r6f[..., None] > 0), out, lin)
    o8 = save8(l2s(out), os.path.join(HERE, "warm-modern-A-ed5.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    m = cv2.dilate((zone | (r6f > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
    rec = check(o8, a8, m, "warm-modern-A-ed5.png")
    rec.update(base="warm-modern-A-ed4.png", ring_pitch_px=D, rings_before=6, rings_after=5,
               rim_lines={"x": xs_m.tolist(), "ring4_bottom": c4_m.tolist(), "pendant_bottom": yb_m.tolist()},
               method="ring 5 taken out; ring 6 (from ring 5's rim line to the bottom) lifted 27 px behind ring 4's rim; the rest of the old "
                      "rings 5-6 area plain wall (harmonic from the wall round the pendant, grain matched to the plain wall beside it)")
    return rec


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent", qa="qa/reports/2026-11-07-editorial-fin2-ed4-country.md",
                                                              tokens=0, var2="none", note="TEST, not for the site; new files only")
    for k in sys.argv[1:]:
        fn = globals()[k]
        r = fn()
        if r is not None:
            R[k] = r
            print(k, json.dumps({kk: vv for kk, vv in r.items() if "px" in kk or kk == "file"}))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
