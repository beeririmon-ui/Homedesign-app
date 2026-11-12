#!/usr/bin/env python3
"""
fix_r8.py: R8, 0-token code fixes on existing warm-modern tool layers (render-agent, 2026-11-12). Code only: 0 tokens, no var2,
no network. Sources: docs/proposals/wm-r7-table-decisions-2026-11-12.md section 3 (3.3.1 and 3.2.4) and QA's combined R6/R7 report
(the coordinator's additions, below). On the travertine marks QA proposed filling the 3 px gap inside the field; the designer's 3.3.1
rule (whatever lies between the feet goes) is what is applied: the fill, computed for comparison only, would join the dashes into one
patch up to 36 % dark between the feet (fix-r8.json holders_qa_fill_alternative). NEW FILES ONLY: work-r8/ (ungraded
per-product layers and shadows, the same form as work-r7/) and work-r8/fix-r8.json; grade_cut_r8.py grades and cuts them with the ONE
v3c grade. The R7 files are read, never written.

  holders   3.3.1, the travertine pair (default): the dark marks on the table between A and B (x ~1711-1746, y ~1251-1265 at 2720;
            they came with the pair from R6, so they sit in the pair's SHADOW file, the frozen recipe's field: checked, the layer's alpha
            is 0 there). The designer's rule: the contact shadow is one soft ellipse under each foot; whatever lies between the feet
            goes. Row by row between the two feet (pixels the pair's alpha leaves free, alpha < 0.5):
              - from A's side (its shadow side, the light comes from the left): the anchor is A's own blob next to its foot (the darkest
                pixel between the foot's centre and 12 px beyond its right edge); from B's side (its lit side): B's edge, or, below
                B's alpha, B's own ellipse (the darkest pixel between B's left edge and its centre);
              - each foot's field is kept AS IT IS while it falls away from the foot (within 1.5 / 255); where it rises again (a mark),
                the foot's field fades out from its last value, exp(-x / 4 px); the result is the larger of the two feet's fields;
              - what is left of a mark under 1.5 / 255 is set to none.
            Nothing is added and no foot's own field changes before the first rise; the pair's layer (RGBA) is the R7 file, byte copy.
  curtain3  3.2.4, curtains-v3 (Linen 200 x 260, the 7' render): the few green-turquoise specks in the fabric. Counted on the graded R7
            layer and on its ungraded source: (literal) the designer's rule, h 150-230 deg and C* > 6; (the specks) every pixel on the
            green side, h 100-230 and C* > 6, whose a* lies >= 8 below the median a* of its 7 x 7 surroundings. The literal rule misses
            the designer's own example points (108/610, 122/674, 127/707 read h 117-142 there), so the specks set is the one fixed; it
            holds every literal pixel. Each speck pixel's a* and b* -> the median a* and b* of the pixels within radius 3 that are
            neither specks nor transparent; L* kept; alpha, the free alpha and the shadow are the R7 files, byte copies. Two passes
            (the second catches a pixel the first one's medians uncover). Nothing else changes (checked: RGB differs only on the specks).

  + QA's combined R6/R7 report (qa/reports/2026-11-12-wm-tool-phase2-r6-r7.md sections 5, 7, 8, 10; the coordinator's additions to R8):
  curtains  180502 (default) and 554205 (curtains-v2): the break over the bench (graded L* -3..-5; QA read -0.1 / -0.7) and the stone
            contact (multiply 0.90-0.95; QA read 0.973), solved on the graded layer with QA's own formulas (targets -4.0 and 0.925)
  curtain3  + its L* relative to 180502 by the card ratio (linear Y; target ~72.9, QA ~72.7): one luminance factor, a* b* kept; PENDING
            THE DESIGNER'S EYE; + the light fringe on the free part's edge at the bench corner; + the break and the contact as above
  The order on curtain 3: specks, L*, fringe, break / contact.

  python3 fix_r8.py holders | curtains | curtain3 | all
"""
import json
import math
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join
WR7, WR8 = D(HERE, "work-r7"), D(HERE, "work-r8")
LAY = D(HERE, "layers")
REC = D(WR8, "fix-r8.json")
REPO = os.path.abspath(D(HERE, *[".."] * 5))


def rel(p):
    return os.path.relpath(p, REPO)


def record(key, val):
    os.makedirs(WR8, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-12", author="render-agent", tokens=0, source="docs/proposals/wm-r7-table-decisions-2026-11-12.md section 3 (3.3.1, 3.2.4)",
        note="ungraded per-product layers (RGBA, straight alpha) and shadows (grey RGB, multiply) in work-r8/; grade_cut_r8.py grades and cuts "
             "them with the ONE v3c grade; only the two fixed products have R8 sources, every other slot reads its R7 source")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_of(L, A, B):
    return np.clip(cv2.cvtColor(np.dstack([L, A, B]).astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


# ================================================================================================= 3.3.1 the marks between the feet
TOL, TAU, FLOOR = 1.5 / 255, 4.0, 1.5 / 255
MARK_BOX = (1704, 1240, 1752, 1292)          # x0, y0, x1, y1 (2720): the designer's 1711-1746 x 1251-1265, grown to the marks' full extent


def _keep(seg):
    """a foot's field along a row, from the foot outward: as it is while it falls (within TOL); faded from its last value where it rises"""
    k = seg.copy()
    m, fading, i0, e0 = seg[0], False, 0, 0.0
    for i in range(len(seg)):
        if not fading:
            if seg[i] > m + TOL:
                fading, i0, e0 = True, i - 1, m
            else:
                m = min(m, seg[i])
        if fading:
            k[i] = min(seg[i], e0 * math.exp(-(i - i0) / TAU))
    return k


def holders_between_feet(d, a):
    """d: the shadow's darkening (1 - shadow), a: the pair's alpha; returns the new d and a record"""
    n, lab_, st, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
    ids = sorted([i for i in range(1, n) if st[i, 4] >= 200], key=lambda i: st[i, 0])
    assert len(ids) == 2, "the pair: two pieces expected"
    A, B = lab_ == ids[0], lab_ == ids[1]

    def foot_centre(m):
        ys, xs = np.nonzero(m)
        return int(round(xs[ys >= ys.max() - 2].mean()))
    cA, cB = foot_centre(A), foot_centre(B)
    ax1, bx0 = int(st[ids[0], 0] + st[ids[0], 2]), int(st[ids[1], 0])
    y0 = int(st[ids[0], 1])
    y1 = min(int(max(st[ids[0], 1] + st[ids[0], 3], st[ids[1], 1] + st[ids[1], 3])) + 40, d.shape[0])
    free = a < 0.5
    out = d.copy()
    rows = 0
    for y in range(y0, y1):
        wa = np.arange(cA, ax1 + 13)
        wa = wa[free[y, wa]]
        xsB = np.nonzero(B[y])[0]
        lo = int(xsB.min()) - 1 if len(xsB) else bx0 - 2
        wb = np.arange(lo, cB + 1)
        wb = wb[free[y, wb]]
        if not len(wa) or not len(wb):
            continue
        xa, xb = int(wa[np.argmax(d[y, wa])]), int(wb[np.argmax(d[y, wb])])
        if xb - xa < 2:
            continue
        seg = d[y, xa:xb + 1]
        new = np.maximum(_keep(seg), _keep(seg[::-1])[::-1])
        new = np.where(free[y, xa:xb + 1], new, seg)
        ch = new < seg - 1e-6
        new = np.where(ch & (new < FLOOR), 0.0, new)
        if ch.any():
            rows += 1
        out[y, xa:xb + 1] = new
    return out, dict(pieces=dict(A=dict(box=[int(v) for v in st[ids[0], :4]], foot_centre_x=cA), B=dict(box=[int(v) for v in st[ids[1], :4]], foot_centre_x=cB)),
                     rows_changed=rows, rule=dict(tolerance_255=TOL * 255, fade_px=TAU, floor_255=FLOOR * 255))


def holders():
    src_l, src_s = D(WR7, "layers", "candle-holders.png"), D(WR7, "shadows", "candle-holders.png")
    L8 = np.asarray(Image.open(src_l))
    S8 = np.asarray(Image.open(src_s).convert("RGB"))
    assert (S8[..., 0] == S8[..., 1]).all() and (S8[..., 0] == S8[..., 2]).all()
    a = L8[..., 3].astype(np.float32) / 255
    d = 1 - S8[..., 0].astype(np.float32) / 255
    d2, rec = holders_between_feet(d, a)
    new8 = np.where(d2 < d - 1e-6, np.clip(np.round((1 - d2) * 255), 0, 255), S8[..., 0]).astype(np.uint8)
    changed = new8 != S8[..., 0]
    x0, y0, x1, y1 = MARK_BOX
    inbox = np.zeros(changed.shape, bool)
    inbox[y0:y1, x0:x1] = True
    rec.update(px_changed=int(changed.sum()), px_changed_outside_mark_box=int((changed & ~inbox).sum()),
               alpha_at_changed_px_max=int(L8[..., 3][changed].max()) if changed.any() else None,
               darkening_removed_255=dict(max=int((new8.astype(int) - S8[..., 0].astype(int)).max()), sum=int((new8.astype(int) - S8[..., 0].astype(int)).sum())),
               mark_box_before=dict(max_darkening_255=int(255 - S8[..., 0][y0:y1, x0:x1][L8[..., 3][y0:y1, x0:x1] == 0].min())),
               nothing_added=bool((new8 >= S8[..., 0]).all()))
    # what is left between the feet, beyond A's own blob (x >= 1718, where A's field has faded): the darkest remaining pixel
    zone = np.zeros(changed.shape, bool)
    zone[y0:y1, 1718:x1] = True
    zone &= L8[..., 3] == 0
    rec["between_feet_after"] = dict(zone="x 1718-1752, y 1240-1292, alpha 0", max_darkening_255=int(255 - new8[zone].min()),
                                     before_max_darkening_255=int(255 - S8[..., 0][zone].min()))
    assert rec["px_changed_outside_mark_box"] == 0, rec
    pl = _new(D(WR8, "layers", "candle-holders.png"))
    shutil.copyfile(src_l, pl)
    ps = _new(D(WR8, "shadows", "candle-holders.png"))
    Image.fromarray(np.dstack([new8] * 3), "RGB").save(ps)
    rec.update(files=dict(layer=rel(pl) + " (byte copy of " + rel(src_l) + ")", shadow=rel(ps)), source=dict(layer=rel(src_l), shadow=rel(src_s)),
               recipe="the frozen recipe's field (extract.shadow_one, carried in R7 with each piece) unchanged on each foot; only what lies "
                      "between the feet is taken out (the designer's 3.3.1 rule); the WM-T3 move, if approved, starts from this file")
    record("holders", rec)
    print(json.dumps(rec, indent=1))


# ================================================================================================= 3.2.4 the specks in curtain 3
GRADED_R7 = D(LAY, "curtains", "curtains-cj-japanese-linen-half-shade-r7.png")


def speck_masks(rgb01, a8):
    lb = lab(rgb01)
    A_, B_ = lb[..., 1], lb[..., 2]
    C = np.hypot(A_, B_)
    h = np.degrees(np.arctan2(B_, A_)) % 360
    on = a8 > 0
    literal = on & (h >= 150) & (h <= 230) & (C > 6)
    med_a = cv2.medianBlur(np.clip(np.round(A_ + 128), 0, 255).astype(np.uint8), 7).astype(np.float32) - 128
    specks = on & (h >= 100) & (h <= 230) & (C > 6) & (A_ - med_a <= -8)
    return literal, specks, lb


def neutralise(rgb01, a8, m):
    """each pixel of m: a*, b* -> the median a*, b* of the pixels within radius 3 that are not in m and not transparent; L* kept"""
    lb = lab(rgb01)
    out = lb.copy()
    ok = (a8 > 0) & ~m
    yy, xx = np.mgrid[-3:4, -3:4]
    disk = (yy ** 2 + xx ** 2) <= 9
    H, W = m.shape
    for y, x in zip(*np.nonzero(m)):
        y0, y1, x0, x1 = max(0, y - 3), min(H, y + 4), max(0, x - 3), min(W, x + 4)
        dk = disk[y0 - y + 3:y1 - y + 3, x0 - x + 3:x1 - x + 3] & ok[y0:y1, x0:x1]
        if dk.sum() < 5:
            continue
        out[y, x, 1] = np.median(lb[y0:y1, x0:x1, 1][dk])
        out[y, x, 2] = np.median(lb[y0:y1, x0:x1, 2][dk])
    new = rgb_of(out[..., 0], out[..., 1], out[..., 2])
    return np.where(m[..., None], new, rgb01)


# ================================================================================================= QA R6/R7: the curtains on the bench
# (qa/reports/2026-11-12-wm-tool-phase2-r6-r7.md section 5 and 10; the coordinator's additions to R8): the break over the bench and the
# stone contact to the designer's section 6.3 numbers AS QA MEASURES THEM on the graded files; curtain 3: its L* relative to 180502 by the
# card ratio, and the light fringe at the bench corner. The measures below are QA's formulas (tools/r67_curtains.py, r67_halo.py), copied.
QA_CON = [(129.3, 1209.9), (244.7, 1183.6)]          # QA's contact line (data/curtains.json lines_canvas_px.contact), canvas px
BREAK_TARGET, BREAK_FULL, BREAK_END = -4.0, 5.0, 7.0  # graded dL; full step up to 5 px above the contact (7.5 at 3840), gone by 7 (10.5)
CONTACT_TARGET = 0.925
CARD_HEX = {"180502": "#EDE7DB", "linen": "#D9CDB8"}  # the cards' colours (QA: "Linen #D9CDB8 against #EDE7DB")
P1 = os.path.abspath(D(HERE, "..", "pilot-phase1-2026-11-07"))
_G, _F7 = [], []


def grade():
    if not _G:
        sys.path.insert(0, HERE)
        import stack
        _G.append(stack.Grade())
    return _G[0]


def f7():
    if not _F7:
        sys.path.insert(0, HERE)
        sys.path.insert(0, D(HERE, "step0"))
        import fix_r7
        _F7.append(fix_r7)
    return _F7[0]


def furn8():
    return np.asarray(Image.open(D(P1, "fixed-furniture.png")))[..., 3]


def qa_yline(P, x):
    (x0, y0), (x1, y1) = P
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def qa_break(Lt, fa):
    """QA r67_curtains.py break_dL: per column x 200-244 clear of furniture, median L* of the 5 rows above b0 = round(yp) - 1 minus the
    10 rows above those; the median over the columns"""
    brk, abv = [], []
    for x in range(200, 245):
        yp = qa_yline(QA_CON, x)
        if fa[int(yp) - 20:int(yp) + 2, x].max() > 0:
            continue
        b0 = int(round(yp)) - 1
        brk.append(np.median(Lt[b0 - 5:b0, x]))
        abv.append(np.median(Lt[b0 - 15:b0 - 5, x]))
    return round(float(np.median(np.array(brk) - np.array(abv))), 2), len(brk)


def qa_contact(S8, fa):
    """QA r67_curtains.py stone_contact_multiply: per visible column x 131-244, the min of the shadow file in rows yp .. yp + 5; the median"""
    cm = []
    for x in range(131, 245):
        yp = qa_yline(QA_CON, x)
        if fa[int(yp) - 6:int(yp) + 8, x].max() > 0:
            continue
        cm.append(float(S8[int(yp):int(yp) + 6, x].min()) / 255)
    return round(float(np.median(cm)), 4), len(cm)


def qa_hem_band(Lt, hem_z):
    """QA's hem band: per column x 80-125, the 15 rows above (hem - 3) against the 20 above those (median of the differences)"""
    F7 = f7()
    hem = [F7.wpt(-2.15, 2.95, hem_z), F7.wpt(-2.15, 2.85, hem_z)]
    band, above = [], []
    for x in range(80, 126):
        yp = qa_yline(hem, x)
        b0 = int(round(yp)) - 3
        band.append(np.median(Lt[b0 - 15:b0, x]))
        above.append(np.median(Lt[b0 - 35:b0 - 15, x]))
    return round(float(np.median(np.array(band) - np.array(above))), 2)


def graded_L(rgb, a_eff):
    """the graded L* of the layer's own pixels (the v3c grade is per pixel: where the layer is opaque this IS the scene, checked: 0 px
    differ from the R7 truth of curtains-v3 at full alpha)"""
    g8 = grade()(rgb, a_eff)
    return cv2.cvtColor(g8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0], g8


def qa_colour_mask():
    """QA's same mask: alpha 255 eroded 5 x 5 in all three R7 curtain layers, rows 100-1149"""
    m7 = json.load(open(D(LAY, "manifest-r7.json")))
    files = [next(l_["file"] for l_ in m7["layers"] if l_["id"] == "curtains")] + [v["file"] for v in m7["variants"]["curtains"]]
    same = np.ones((1530, 2720), bool)
    for f in files:
        A = np.asarray(Image.open(D(LAY, f)))[..., 3]
        m = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        m[:100] = False
        m[1400:] = False
        same &= m
    same[1150:] = False
    return same


def stats_lab(g8, m):
    lb = cv2.cvtColor(g8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[m].astype(np.float64)
    L_, a_, b_ = np.median(lb, 0)
    Lmap = cv2.cvtColor(g8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    lo = cv2.GaussianBlur(Lmap, (0, 0), 3)
    return dict(L=round(float(L_), 2), C=round(float(math.hypot(a_, b_)), 2), h=round(float(math.degrees(math.atan2(b_, a_)) % 360), 1),
                L_p99=round(float(np.percentile(lb[:, 0], 99)), 2), highpass_L_std=round(float(np.std((Lmap - lo)[m])), 3))


def card_target(L180):
    def lin(c):
        c = np.array(c) / 255.0
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

    def Y(h):
        l_ = lin([int(h[i:i + 2], 16) for i in (1, 3, 5)])
        return 0.2126 * l_[0] + 0.7152 * l_[1] + 0.0722 * l_[2]
    r = Y(CARD_HEX["linen"]) / Y(CARD_HEX["180502"])
    fy = (L180 + 16) / 116
    return round(float(116 * np.cbrt(fy ** 3 * r) - 16), 2), round(float(r), 4)


def luminance_factor(rgb, f, m):
    """L* from Y x f (CIE), a* and b* kept (hue and chroma unchanged), on the pixels m"""
    lb = lab(rgb)
    fy = (lb[..., 0] + 16) / 116
    Y = np.where(fy > 6 / 29, fy ** 3, (fy - 16 / 116) * 3 * (6 / 29) ** 2)
    Y2 = Y * f
    L2 = np.where(Y2 > (6 / 29) ** 3, 116 * np.cbrt(Y2) - 16, 903.3 * Y2)
    out = rgb_of(L2, lb[..., 1], lb[..., 2])
    return np.where(m[..., None], out, rgb).astype(np.float32)


def corner_fringe(rgb, af, xh, y_top, y_bot):
    """curtain 3's free-part edge at the bench end (x ~ the bench end, rows from the spill down to the hem): per row, the last 4 fabric
    columns may not be lighter than the fabric 4-9 px inside them + 2 L* (the cut runs through a fold's lit flank there); a* b* kept"""
    lb = lab(rgb)
    L_ = lb[..., 0].copy()
    n = 0
    for y in range(int(y_top), int(y_bot) + 1):
        x0 = int(xh) - 10
        w = af[y, x0:int(xh) + 10] >= 0.5
        edges = np.nonzero(w[:-1] & ~w[1:])[0]                    # a real edge: fabric, then no fabric to its right
        if not len(edges):
            continue
        e = x0 + int(edges.max())
        ref = float(np.median(L_[y, e - 9:e - 3]))
        for x in range(e - 3, e + 2):
            if af[y, x] > 0 and L_[y, x] > ref + 2.0:
                L_[y, x] = ref + 2.0
                n += 1
    out = rgb_of(L_, lb[..., 1], lb[..., 2])
    ch = np.abs(L_ - lb[..., 0]) > 1e-6
    return np.where(ch[..., None], out, rgb).astype(np.float32), n, ch


def break_and_contact(name, rgb, af, sh, fa8):
    """the break: an extra L* step on the fabric just above the stone contact (x beyond the bench end), its size solved so that QA's graded
    break_dL reads -4.0; the contact: R7's contact profile on the stone (section 6.3 item 6, the same width and blur), its darkening raised
    so that QA's stone_contact_multiply reads 0.925 (the shadow under the fabric keeps its alpha lift)"""
    F7 = f7()
    H, Wd = af.shape
    hem, con = F7.lines(F7.HEM_Z[name])
    xh = con[0][0]
    xs = np.arange(Wd, dtype=np.float32)
    con_y = F7._interp_line(con, xs)
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    fa = fa8.astype(np.float32) / 255
    a_eff = af * (1 - fa)
    t = con_y[None, :] - yy
    s_ = np.clip((BREAK_END - t) / (BREAK_END - BREAK_FULL), 0, 1)
    prof = np.where(t <= BREAK_FULL, 1.0, s_ * s_ * (3 - 2 * s_)) * (t > -1) * (xx > xh + 1) * (af > 0)
    # R7's own break (fix_r7.curtain_cut: L* -4 x smoothstep, peaking AT the contact) is taken back out, so the band is ONE flat step
    # (a peak at the contact line stacked on the step reads as a dark contour: QA's halo metric)
    sr = np.clip(1 - t / F7.BREAK_PX, 0, 1)
    brk7 = (sr * sr * (3 - 2 * sr)) * (t > -2) * (xx > xh) * (af > 0)
    touch = (prof > 0) | (brk7 > 0)
    lb0 = lab(rgb)
    L0, _ = graded_L(rgb, a_eff)
    before_break = qa_break(L0, fa8)

    def apply(A):
        L_ = lb0[..., 0] + 4.0 * brk7 - A * prof
        return np.where(touch[..., None], rgb_of(L_, lb0[..., 1], lb0[..., 2]), rgb).astype(np.float32)
    lo, hi, hist = 0.0, 25.0, []
    for _ in range(18):
        A = (lo + hi) / 2
        Lg, _ = graded_L(apply(A), a_eff)
        v, n = qa_break(Lg, fa8)
        hist.append((round(A, 3), v))
        if abs(v - BREAK_TARGET) <= 0.05:
            break
        if v > BREAK_TARGET:
            lo = A
        else:
            hi = A
    rgb2 = apply(A)
    Lg2, _ = graded_L(rgb2, a_eff)
    after_break = qa_break(Lg2, fa8)
    # the contact: the same profile as R7 (fix_r7.curtain_cut), one more darkening D on top of it
    v_ = np.clip((yy - con_y[None, :]) / F7.CONTACT_W, 0, 1)
    base_c = (1 - v_) * (yy >= con_y[None, :] - 0.5) * (xx > xh - 1) * (xx < F7.wpt(F7.X_FACE, F7.Y_BACK, F7.CONTACT_Z)[0] + 6)
    base_c = cv2.GaussianBlur(base_c.astype(np.float32), (0, 0), F7.CONTACT_BLUR)
    before_contact = qa_contact(graded_shadow_r(rgb2, af, sh, fa8), fa8)
    before_contact_ungraded = qa_contact(np.round(sh * 255).astype(np.uint8), fa8)
    under = np.clip((sh - af) / np.maximum(1 - af, 1e-6), 0, 1)

    def sh_with(Dd):
        s2 = under * (1 - Dd * base_c)
        return np.where(af < 0.999, np.clip(s2 * (1 - af) + af, 0.45, 1.0), sh).astype(np.float32)
    lo, hi, chist = 0.0, 0.4, []
    for _ in range(20):
        Dd = (lo + hi) / 2
        v, n2 = qa_contact(graded_shadow_r(rgb2, af, sh_with(Dd), fa8), fa8)
        chist.append((round(Dd, 4), v))
        if abs(v - CONTACT_TARGET) <= 0.002:
            break
        if v > CONTACT_TARGET:
            lo = Dd
        else:
            hi = Dd
    sh2 = sh_with(Dd)
    after_contact = qa_contact(graded_shadow_r(rgb2, af, sh2, fa8), fa8)
    after_contact_ungraded = qa_contact(np.round(sh2 * 255).astype(np.uint8), fa8)
    halo = dict(before=qa_halo_model(rgb, af, sh, fa8), after=qa_halo_model(rgb2, af, sh2, fa8))
    rec = dict(break_=dict(qa_measure_graded=dict(before=before_break[0], after=after_break[0], columns=after_break[1]), target=BREAK_TARGET,
                           flat_step_L_ungraded=round(A, 3), extra_step_L_ungraded=round(A, 3),
                           profile=f"ONE flat step (R7's smoothstep peak at the contact taken back out): full up to {BREAK_FULL} px above the "
                                   f"contact (x > the bench end), smoothstep to 0 at {BREAK_END} px (10.5 at 3840)", bisection=hist,
                           why="R7's -4 was applied before the grade; the v3c highlight shoulder (the fabric at L* 93-95) eats it"),
               contact=dict(qa_measure=dict(before=before_contact[0], after=after_contact[0], columns=after_contact[1]), target=CONTACT_TARGET,
                            on_the_graded_shadow="modelled as grade_cut's cut() solves it (graded_shadow_r); the build's file is checked in verify",
                            ungraded_source=dict(before=before_contact_ungraded[0], after=after_contact_ungraded[0],
                                                 why="the bright stone sits in the v3c shoulder: the graded file reads lighter than its source"),
                            extra_darkening=round(Dd, 4), bisection=chist,
                            profile="fix_r7.curtain_cut's contact profile (width 5 px at 3840, linear, blur sigma CONTACT_BLUR), on top of R7's"),
               qa_hem_halo_model=halo,
               rgb_px_changed=int(((rgb2 != rgb).any(2)).sum()), shadow_px_changed=int((np.round(sh2 * 255) != np.round(sh * 255)).sum()))
    return rgb2, sh2, rec


_HALO = []


def qa_halo_model(rgb, af, sh, fa8):
    """QA's hem-halo metric (r67_halo.analyse, loaded read-only as r67_hem_halo.py does) on the modelled set-B scene of this curtain:
    the curtain composed first behind the furniture on the base, graded (stack.py); box x 0-260, y 1180-1445"""
    if not _HALO:
        qad = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
        src = open(os.path.join(qad, "tools/r67_halo.py")).read()
        ns = {}
        exec(src[src.index("def Lof"):src.index("def alphas_of")], {"np": np, "cv2": cv2, "Image": Image, "os": os, "OUT": qad}, ns)
        _HALO.append(ns)
    ns = _HALO[0]
    P = base_parts()
    fa = fa8.astype(np.float32) / 255
    Uw = (P["behind0"] * sh[..., None] * (1 - af[..., None]) + rgb * af[..., None]) * (1 - fa[..., None]) + P["F"] * fa[..., None]
    a_eff = af * (1 - fa)
    T = grade()(Uw, a_eff)
    A8 = np.clip(np.floor(a_eff * 255 + 0.5), 0, 255).astype(np.uint8)
    above = cv2.dilate((fa8 > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    h = ns["analyse"](ns["Lof"](T), A8, "model", T, above, box=(0, 1180, 260, 1445), save=False)
    return {k: v for k, v in h.items() if k.startswith(("dark", "bright"))}


_P = []


def base_parts():
    if not _P:
        sys.path.insert(0, HERE)
        import stack
        _P.append(stack.base_parts())
    return _P[0]


def graded_shadow_r(rgb, af, sh, fa8):
    """the red channel of the GRADED shadow file as grade_cut's cut() solves it (GC.cut, per channel: the value nearest the ungraded shadow
    inside the interval that reproduces the graded composite), for the curtain composed first behind the furniture on the base (stack.py):
    with it U = (behind0 sh (1 - a) + rgb a)(1 - fa) + F fa, without it U0; QA reads this file"""
    P = base_parts()
    fa = fa8.astype(np.float32) / 255
    Uw = (P["behind0"] * sh[..., None] * (1 - af[..., None]) + rgb * af[..., None]) * (1 - fa[..., None]) + P["F"] * fa[..., None]
    a_eff = af * (1 - fa)
    t = grade()(Uw, a_eff)[..., 0].astype(np.float64)
    bb = grade()(P["U0"], np.zeros_like(a_eff))[..., 0].astype(np.float64)
    r0 = np.round(sh * 255).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lo = np.ceil((t - 0.5) * 255.0 / bb)
        hi = np.ceil((t + 0.5) * 255.0 / bb) - 1
    reach = np.where(bb > 0, lo <= 255, t == 0)
    lo, hi = np.clip(np.nan_to_num(lo, nan=0), 0, 255), np.clip(np.nan_to_num(hi, nan=255), 0, 255)
    wide = (hi - lo) >= 2
    lo2, hi2 = np.where(wide, lo + 1, lo), np.where(wide, hi - 1, hi)
    S = np.where(bb > 0, np.clip(r0, lo2, hi2), r0)
    S = np.where(reach, S, 255.0)
    a8 = np.clip(np.floor(a_eff * 255 + 0.5), 0, 255)
    sho = (a8 == 0) & (t != bb)                       # the cut solves the shadow only where the product has no alpha
    S = np.where(sho, S, 255.0)
    S = np.where((a8 > 0) & (a8 < 255), r0, S)        # its soft edge keeps the ungraded shadow (cut(): S[part] = r0)
    return np.clip(S, 0, 255).astype(np.uint8)


def load_src(name, ld=WR7, sd=WR7):
    L8 = np.asarray(Image.open(D(ld, "layers", f"{name}.png")))
    af = np.asarray(Image.open(D(ld, "layers", f"{name}-free-alpha.png")).convert("L")).astype(np.float32) / 255
    sh = np.asarray(Image.open(D(sd, "shadows", f"{name}.png")).convert("L")).astype(np.float32) / 255
    return L8, af, sh


def save_curtain(name, L8, rgb, sh):
    out8 = np.where((np.abs(rgb - L8[..., :3].astype(np.float32) / 255) > 1e-7).any(2)[..., None],
                    np.clip(np.round(rgb * 255), 0, 255), L8[..., :3]).astype(np.uint8)
    pl = _new(D(WR8, "layers", f"{name}.png"))
    Image.fromarray(np.dstack([out8, L8[..., 3]]), "RGBA").save(pl)
    pf = _new(D(WR8, "layers", f"{name}-free-alpha.png"))
    shutil.copyfile(D(WR7, "layers", f"{name}-free-alpha.png"), pf)
    s0 = np.asarray(Image.open(D(WR7, "shadows", f"{name}.png")).convert("L"))
    s8 = np.where(np.abs(sh - s0.astype(np.float32) / 255) > 1e-7, np.clip(np.round(sh * 255), 0, 255), s0).astype(np.uint8)
    ps = _new(D(WR8, "shadows", f"{name}.png"))
    Image.fromarray(np.dstack([s8] * 3), "RGB").save(ps)
    return dict(layer=rel(pl), free_alpha=rel(pf) + " (byte copy of the R7 source)", shadow=rel(ps)), out8, s8


def curtains_bench():
    """180502 (default) and 554205 (curtains-v2): the break and the contact"""
    fa8 = furn8()
    out = {}
    for name in ("curtains", "curtains-v2"):
        L8, af, sh = load_src(name)
        rgb = L8[..., :3].astype(np.float32) / 255
        rgb2, sh2, rec = break_and_contact(name, rgb, af, sh, fa8)
        files, out8, s8 = save_curtain(name, L8, rgb2, sh2)
        Lg, _ = graded_L(out8.astype(np.float32) / 255, af * (1 - fa8.astype(np.float32) / 255))
        rec["hem_band_dL_qa"] = dict(after=qa_hem_band(Lg, f7().HEM_Z[name]), rule="-2 +-1")
        rec["alpha_unchanged"] = True
        rec["files"] = files
        rec["source"] = dict(layer=rel(D(WR7, "layers", f"{name}.png")), shadow=rel(D(WR7, "shadows", f"{name}.png")))
        out[name] = rec
        print(name, json.dumps({k: v for k, v in rec.items() if k in ("break_", "contact")}, default=float)[:600], flush=True)
    record("curtains_bench", dict(what="QA R6/R7 section 5 (the coordinator's R8 addition 2): the break over the bench and the stone contact "
                                       "to the designer's section 6.3 numbers, measured as QA measures them", **out))


def curtain3():
    """curtain 3 (Linen): (1) the specks (designer 3.2.4); (2) its L* relative to 180502 by the card ratio (QA / the coordinator: ~72.7;
    one factor on the luminance in linear light, a* b* kept: hue and chroma unchanged; PENDING THE DESIGNER'S EYE); (3) the light fringe
    on the free part's edge at the bench corner (QA: an 18 px run); (4) the break and the contact as the other two curtains"""
    name = "curtains-v3"
    L8, af, sh = load_src(name)
    a8 = L8[..., 3]
    fa8 = furn8()
    a_eff = af * (1 - fa8.astype(np.float32) / 255)
    rgb = L8[..., :3].astype(np.float32) / 255
    # (1) the specks
    G8 = np.asarray(Image.open(GRADED_R7))
    lit_g, spk_g, _ = speck_masks(G8[..., :3].astype(np.float32) / 255, G8[..., 3])
    lit_u, spk_u, _ = speck_masks(rgb, a8)
    m1 = lit_g | spk_g | lit_u | spk_u
    s1 = neutralise(rgb, a8, m1)
    s1 = np.where(m1[..., None], np.round(s1 * 255) / 255, rgb).astype(np.float32)
    lit2, spk2, _ = speck_masks(s1, a8)
    m2 = (lit2 | spk2) & ~m1
    if m2.any():
        s2 = neutralise(s1, a8, m2 | m1)
        s1 = np.where(m2[..., None], np.round(s2 * 255) / 255, s1).astype(np.float32)
    mm = m1 | m2
    lit3, spk3, _ = speck_masks(s1, a8)
    lb0, lbs = lab(rgb), lab(s1)
    dab = np.hypot(lbs[..., 1] - lb0[..., 1], lbs[..., 2] - lb0[..., 2])
    specks = dict(
        rules=dict(literal="the designer's: h 150-230 deg and C* > 6 (alpha > 0)",
                   specks="green side h 100-230, C* > 6, a* - median7(a*) <= -8 (alpha > 0); holds every literal pixel",
                   why_wider="the literal window misses the designer's own example points (x/y 108/610, 122/674, 127/707: h 117-142 there)",
                   fix="a*, b* -> the median of the radius-3 surroundings (not specks, not transparent); L* kept"),
        before=dict(graded_r7=dict(literal=int(lit_g.sum()), specks=int(spk_g.sum()), literal_not_in_specks=int((lit_g & ~spk_g).sum())),
                    ungraded_r7=dict(literal=int(lit_u.sum()), specks=int(spk_u.sum()))),
        fixed_px=dict(pass_1=int(m1.sum()), pass_2=int(m2.sum()), total=int(mm.sum()), of_layer_px=int((a8 > 0).sum()), soft_edge=int((mm & (a8 < 255)).sum())),
        after_ungraded=dict(literal=int(lit3.sum()), specks=int(spk3.sum())),
        changed_outside_specks=int(((np.round(s1 * 255) != L8[..., :3]).any(2) & ~mm).sum()),
        dL_max_on_specks=round(float(np.abs(lbs[..., 0] - lb0[..., 0])[mm].max()), 3),
        dab_on_specks=dict(median=round(float(np.median(dab[mm])), 2), max=round(float(dab[mm].max()), 2)),
        examples={f"{x}/{y}": dict(before=[round(float(v), 1) for v in lb0[y, x]], after=[round(float(v), 1) for v in lbs[y, x]], fixed=bool(mm[y, x]))
                  for x, y in ((107, 611), (108, 610), (122, 674), (124, 706), (126, 689), (143, 635), (148, 714), (160, 735))})
    assert specks["changed_outside_specks"] == 0
    np.save(_new(D(WR8, "curtain3-speck-mask.npy")), mm)
    # (2) the L* target relative to 180502 (QA's same mask, graded; 180502's value read on its R7 layer = the R8 one there)
    mask = qa_colour_mask()
    L180 = np.asarray(Image.open(D(WR7, "layers", "curtains.png")))
    af180 = np.asarray(Image.open(D(WR7, "layers", "curtains-free-alpha.png"))).astype(np.float32) / 255
    _, g180 = graded_L(L180[..., :3].astype(np.float32) / 255, af180 * (1 - fa8.astype(np.float32) / 255))
    ref = stats_lab(g180, mask)
    target, ratio = card_target(ref["L"])
    _, gb = graded_L(s1, a_eff)
    before = stats_lab(gb, mask)
    on = af > 0
    lo, hi, hist = 0.3, 1.0, []
    for _ in range(25):
        f = (lo + hi) / 2
        _, gf = graded_L(luminance_factor(s1, f, on), a_eff)
        st = stats_lab(gf, mask)
        hist.append((round(f, 5), st["L"]))
        if abs(st["L"] - target) <= 0.05:
            break
        if st["L"] > target:
            hi = f
        else:
            lo = f
    s2 = luminance_factor(s1, f, on)
    _, ga = graded_L(s2, a_eff)
    after = stats_lab(ga, mask)
    lstar = dict(status="PENDING THE DESIGNER'S EYE (the coordinator, 2026-11-12)", reference_180502=ref,
                 card_ratio_linear_Y=ratio, cards=CARD_HEX, target_L=target, qa_said="about 72.7 (card ratio); the photo ratio ~62 is a soft lower bound",
                 method="one factor f on the luminance Y in linear light (L* from Y x f), a* and b* kept: hue and chroma unchanged; f solved on "
                        "the graded layer in QA's same mask (alpha 255 eroded 5 x 5 in all three curtain layers, rows 100-1149)",
                 factor_Y=round(f, 5), bisection=hist, before=before, after=after,
                 not_the_r5_method="L* is not locked to the render (the method the designer retired in R5): it is set by the card ratio to 180502")
    # (3) the corner fringe
    F7 = f7()
    hem, con = F7.lines(F7.HEM_Z[name])
    xh, yv = con[0]
    y_hem = float(F7._interp_line(hem, np.array([xh], np.float32))[0])
    s3, nfr, chf = corner_fringe(s2, af, xh, yv - 1, y_hem)
    fringe = dict(rule="the last 4 fabric columns of the free part's edge at the bench end (rows %d-%d; the spill's diagonal included) no lighter "
                       "than the fabric 4-9 px inside + 2 L*; a* b* kept" % (int(yv - 1), int(y_hem)), px_changed=int(nfr), dL_max=round(float(np.abs(lab(s3)[..., 0] - lab(s2)[..., 0]).max()), 2))
    # (4) the break and the contact
    s4, sh2, bc = break_and_contact(name, s3, af, sh, fa8)
    # the final speck pass: after the L* factor the 8-bit round trip nudges a few borderline pixels past the rule (dark folds)
    # detected on the ungraded file AND on the graded model (exact where the fabric is opaque: what QA and the verify read)
    s4 = (np.round(s4 * 255) / 255).astype(np.float32)
    full = a8 == 255
    m5 = np.zeros(a8.shape, bool)
    for _ in range(4):
        lit5, spk5, _ = speck_masks(s4, a8)
        _, g5 = graded_L(s4, a_eff)
        litg, spkg, _ = speck_masks(g5.astype(np.float32) / 255, a8)
        new = (lit5 | spk5 | ((litg | spkg) & full)) & ~m5
        if not new.any():
            break
        m5 |= new
        n5 = neutralise(s4, a8, m5)
        s4 = np.where(m5[..., None], np.round(n5 * 255) / 255, s4).astype(np.float32)
    lit6, spk6, _ = speck_masks(s4, a8)
    _, g6 = graded_L(s4, a_eff)
    litg6, spkg6, _ = speck_masks(g6.astype(np.float32) / 255, a8)
    specks["final_pass"] = dict(px=int(m5.sum()), after_ungraded=dict(literal=int(lit6.sum()), specks=int(spk6.sum())),
                                after_graded_model_opaque=dict(literal=int((litg6 & full).sum()), specks=int((spkg6 & full).sum())),
                                why="after the L* factor, the 8-bit round trip and the grade nudge borderline dark-fold pixels (L* ~18-60) "
                                    "past the rule; detected on the ungraded file and on the graded model")
    files, out8, s8 = save_curtain(name, L8, s4, sh2)
    Lg, g8 = graded_L(out8.astype(np.float32) / 255, a_eff)
    bc["hem_band_dL_qa"] = dict(after=qa_hem_band(Lg, F7.HEM_Z[name]), before=qa_hem_band(graded_L(rgb, a_eff)[0], F7.HEM_Z[name]), rule="-2 +-1")
    final = stats_lab(g8, mask)
    rec = dict(specks=specks, lstar=lstar, corner_fringe=fringe, bench=bc, final_same_mask=final, alpha_unchanged=True, files=files,
               source=dict(layer=rel(D(WR7, "layers", f"{name}.png")), graded_r7=rel(GRADED_R7)))
    record("curtain3", rec)
    print(json.dumps(dict(specks=specks["fixed_px"], lstar=dict(target=target, f=f, before=before, after=after), fringe=fringe,
                          bench={k: v for k, v in bc.items() if k in ("break_", "contact")}), default=float)[:2500])


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("holders", "all"):
        holders()
    if what in ("curtains", "all"):
        curtains_bench()
    if what in ("curtain3", "all"):
        curtain3()
