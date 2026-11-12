#!/usr/bin/env python3
"""
fix_r8.py: R8, two 0-token code fixes on existing warm-modern tool layers (render-agent, 2026-11-12). Code only: 0 tokens, no var2,
no network. Source: docs/proposals/wm-r7-table-decisions-2026-11-12.md section 3 (3.3.1 and 3.2.4). NEW FILES ONLY: work-r8/ (ungraded
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

  python3 fix_r8.py holders | curtain3 | all
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


def curtain3():
    src = D(WR7, "layers", "curtains-v3.png")
    L8 = np.asarray(Image.open(src))
    a8 = L8[..., 3]
    rgb = L8[..., :3].astype(np.float32) / 255
    G8 = np.asarray(Image.open(GRADED_R7))
    lit_g, spk_g, _ = speck_masks(G8[..., :3].astype(np.float32) / 255, G8[..., 3])
    lit_u, spk_u, _ = speck_masks(rgb, a8)
    m1 = lit_g | spk_g | lit_u | spk_u
    out = neutralise(rgb, a8, m1)
    out8 = np.where(m1[..., None], np.clip(np.round(out * 255), 0, 255), L8[..., :3]).astype(np.uint8)
    lit2, spk2, _ = speck_masks(out8.astype(np.float32) / 255, a8)
    m2 = (lit2 | spk2) & ~m1
    if m2.any():
        out2 = neutralise(out8.astype(np.float32) / 255, a8, m2 | m1)
        out8 = np.where(m2[..., None], np.clip(np.round(out2 * 255), 0, 255), out8).astype(np.uint8)
    lit3, spk3, lb3 = speck_masks(out8.astype(np.float32) / 255, a8)
    lb0 = lab(rgb)
    changed = (out8 != L8[..., :3]).any(2)
    mm = m1 | m2
    body = a8 == 255
    dab = np.hypot(lb3[..., 1] - lb0[..., 1], lb3[..., 2] - lb0[..., 2])
    rec = dict(
        rules=dict(literal="the designer's: h 150-230 deg and C* > 6 (alpha > 0)",
                   specks="green side h 100-230, C* > 6, a* - median7(a*) <= -8 (alpha > 0); holds every literal pixel",
                   why_wider="the literal window misses the designer's own example points (x/y 108/610, 122/674, 127/707: h 117-142 there)",
                   fix="a*, b* -> the median of the radius-3 surroundings (not specks, not transparent); L* kept"),
        before=dict(graded_r7=dict(literal=int(lit_g.sum()), specks=int(spk_g.sum()), literal_not_in_specks=int((lit_g & ~spk_g).sum())),
                    ungraded_r7=dict(literal=int(lit_u.sum()), specks=int(spk_u.sum()))),
        fixed_px=dict(pass_1=int(m1.sum()), pass_2=int(m2.sum()), total=int(mm.sum()), of_layer_px=int((a8 > 0).sum()),
                      rows_lt_80=int((np.nonzero(mm)[0] < 80).sum()), soft_edge=int((mm & (a8 < 255)).sum())),
        after_ungraded=dict(literal=int(lit3.sum()), specks=int(spk3.sum())),
        changed_px=int(changed.sum()), changed_outside_specks=int((changed & ~mm).sum()),
        dL_max_on_specks=round(float(np.abs(lb3[..., 0] - lb0[..., 0])[mm].max()), 3) if mm.any() else 0.0,
        dab_on_specks=dict(median=round(float(np.median(dab[mm])), 2), max=round(float(dab[mm].max()), 2)) if mm.any() else None,
        body_median_lab_before=[round(float(v), 3) for v in np.median(lb0[body], 0)],
        body_median_lab_after=[round(float(v), 3) for v in np.median(lb3[body], 0)],
        alpha_unchanged=True,
        examples={f"{x}/{y}": dict(before=[round(float(v), 1) for v in lb0[y, x]], after=[round(float(v), 1) for v in lb3[y, x]], fixed=bool(mm[y, x]))
                  for x, y in ((107, 611), (108, 610), (122, 674), (124, 706), (126, 689), (143, 635), (148, 714), (160, 735))},
    )
    assert rec["changed_outside_specks"] == 0, rec
    pl = _new(D(WR8, "layers", "curtains-v3.png"))
    Image.fromarray(np.dstack([out8, a8]), "RGBA").save(pl)
    pf = _new(D(WR8, "layers", "curtains-v3-free-alpha.png"))
    shutil.copyfile(D(WR7, "layers", "curtains-v3-free-alpha.png"), pf)
    ps = _new(D(WR8, "shadows", "curtains-v3.png"))
    shutil.copyfile(D(WR7, "shadows", "curtains-v3.png"), ps)
    np.save(D(WR8, "curtain3-speck-mask.npy"), mm)
    rec["files"] = dict(layer=rel(pl), free_alpha=rel(pf) + " (byte copy)", shadow=rel(ps) + " (byte copy)", speck_mask=rel(D(WR8, "curtain3-speck-mask.npy")))
    rec["source"] = dict(layer=rel(src), graded_r7=rel(GRADED_R7))
    record("curtain3", rec)
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("holders", "all"):
        holders()
    if what in ("curtain3", "all"):
        curtain3()
