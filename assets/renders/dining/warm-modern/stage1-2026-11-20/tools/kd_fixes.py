#!/usr/bin/env python3
"""
kd_fixes.py: the code fixes of stage one, applied inside the cut (render-agent, 2026-11-20; 0 tokens). Only what shows at x1-x2 or does
not match the product (EFF1), as in B1 / MB1:
  - the pendant (A-table and the variants): the edit drew the shade about 17 % wider than the card's 50 cm, rounder than its 50 x 19 and 5 cm low. The shade
    (the convex hull of its cut, so a lit edge the cut lost comes back) is scaled to the clay's 50 x 19 shade, its bottom on the clay's
    bottom (Z 1.50) and centred on it; the rod / cord above it is rebuilt from the edit's own rod columns, from the frame's top down to
    the new shade top (FIX_PENDANT);
  - the runner: its edges smoothed (close 3 px, then a 1 px blur), so the hem reads as one line (the cut left a dashed edge at x2);
    kept to the table top (no drape);
  - the olive sprigs: the model drew a few out-of-focus leaves behind the sprigs (7.5: everything sharp); pixels of the filler whose local
    sharpness is under a third of the sprigs' median are dropped (and they never become shadow);
  - shadows only on each product's support surfaces (SUPPORT, clay ids of the plate): the table top for the table products, the
    worktop / splash for the worktop products, the shelf and the wall behind it for the shelf products; none for the pendant and the sconce.
"""
import cv2
import numpy as np

import kd_common as K

C = K.C
H, W = K.H, K.W
SUPPORT = {50: (), 52: (20,), 53: (20,), 55: (20,), 57: (1, 5, 9, 10, 12, 14), 58: (1, 2, 5, 9, 10), 60: (24,), 61: (32, 33), 62: (32, 33),
           63: (32, 33), 65: (38, 2), 66: (38, 2), 67: (38, 2), 69: (38, 2), 70: (), 71: (32, 33), 72: (32, 33), 73: (32, 33), 74: (32, 33, 40),
           76: (42,), 77: (40, 43, 44),
           78: (32, 33, 40), 79: (32, 33)}                  # 10.9: the vessel with its branches, the serving boards
BAND = {57: 30, 58: 40, 60: 30, 65: 20, 66: 20, 67: 20, 69: 24, 73: 20, 78: 30, 79: 16}


def hull(m):
    pts = cv2.findNonZero(m.astype(np.uint8))
    out = np.zeros((H, W), np.uint8)
    if pts is not None:
        cv2.fillConvexPoly(out, cv2.convexHull(pts), 1)
    return out.astype(bool)


def shade_rows(m, min_w=40):
    w = m.sum(1)
    rows = np.nonzero(w >= min_w)[0]
    return rows.min(), rows.max()


def fix_pendant(e, m, ids, rec, frame="D1"):
    """m: the cut pendant mask on the locked edit e; returns (e', m') with the shade at the clay's size and place"""
    clay = ids == 50
    cy0, cy1 = shade_rows(clay)
    cxs = np.nonzero(clay[cy0:cy1 + 1].any(0))[0]
    cx0, cx1 = cxs.min(), cxs.max()
    ey0, ey1 = shade_rows(m)
    sh = m.copy()
    sh[:ey0] = False
    sh = hull(sh) & C.dil(sh, 1)                         # the hull fills what the cut lost inside, never the wall beside it
    exs = np.nonzero(sh.any(0))[0]
    ex0, ex1 = exs.min(), exs.max()
    s = (cx1 - cx0 + 1) / (ex1 - ex0 + 1)
    sy_ = (cy1 - cy0 + 1) / (ey1 - ey0 + 1)        # the card's 50 x 19 (the clay's silhouette), not the edit's rounder shade
    # uniform scale about the edit's shade bottom-centre, then moved so the bottom sits on the clay's and the centre on the clay's
    ecx, ecy = (ex0 + ex1) / 2, ey1
    tcx, tcy = (cx0 + cx1) / 2, cy1
    A = np.array([[s, 0, tcx - s * ecx], [0, sy_, tcy - sy_ * ecy]], np.float32)
    rgb_s = cv2.warpAffine(e.astype(np.float32), A, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    sh_s = cv2.warpAffine(sh.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5
    new_top = shade_rows(sh_s)[0]
    # the rod: the edit's rod rows (above its shade), its centre per row; rebuilt from the frame top down to the new shade top
    rod = m.copy()
    rod[ey0:] = False
    rows = np.nonzero(rod.any(1))[0]
    out = e.copy()
    rodm = np.zeros((H, W), bool)
    if rows.size:
        prof = []
        for y in rows[-40:]:
            xs = np.nonzero(rod[y])[0]
            prof.append((xs.min(), xs.max(), y))
        rx0 = int(np.median([p[0] for p in prof]))
        rx1 = int(np.median([p[1] for p in prof]))
        dx = int(round(tcx - (rx0 + rx1) / 2))
        src_rows = [p[2] for p in prof]
        old_top_y = rows.min()
        for y in range(0, new_top + 2):
            sy = y if (y in set(rows) and y < ey0 - 2) else src_rows[(y - old_top_y) % len(src_rows)]
            xs = np.arange(rx0 - 2, rx1 + 3)
            out[y, xs + dx] = e[sy, xs]
            rodm[y, rx0 + dx:rx1 + dx + 1] = True
        # the plate behind the old rod's place shows where the rod moved (the layer only carries the new rod)
    out = np.where(sh_s[..., None], rgb_s, out)
    m2 = sh_s | rodm
    rec["pendant_fix"] = dict(scale_x=round(float(s), 4), scale_y=round(float(sy_), 4), edit_shade_px=[int(ex0), int(ey0), int(ex1), int(ey1)],
                              clay_shade_px=[int(cx0), int(cy0), int(cx1), int(cy1)], new_shade_top_row=int(new_top),
                              rule="scaled to the clay's 50 x 19 shade (the SKU drawing), bottom on the clay's (Z 1.50), centred; the rod rebuilt from the edit's rod columns")
    return out, m2


def fix_runner(m, pl_ids):
    m2 = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
    m2 = C.blur(m2.astype(np.float64), 1.0) > 0.5
    return m2 & C.dil(pl_ids == 20, 2)


def sharp_filter(e, m, ids, filler_id, rec):
    """drop the out-of-focus pixels of a filler (the olive sprigs): local Laplacian energy against the sprigs' own"""
    fz = C.dil(ids == filler_id, 40) & m & ~C.dil(np.isin(ids, (53,)), 2)
    if fz.sum() < 50:
        return m
    y = C.luma(e).astype(np.float32)
    lap = np.abs(cv2.Laplacian(cv2.GaussianBlur(y, (0, 0), 0.7), cv2.CV_32F, ksize=3))
    en = C.blur(lap.astype(np.float64), 3)
    thr = np.median(en[fz]) / 3.0
    blurry = fz & (en < thr)
    blurry = cv2.morphologyEx(blurry.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    rec["olive_blur_dropped_px"] = int(blurry.sum())
    return m & ~blurry


def support_env(k, pl_ids, band_default=45):
    sup = SUPPORT.get(k)
    if sup is None:
        return None, band_default
    if not sup:
        return np.zeros((H, W), bool), 0
    return np.isin(pl_ids, sup), BAND.get(k, band_default)
