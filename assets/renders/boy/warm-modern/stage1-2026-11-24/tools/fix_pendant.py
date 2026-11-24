#!/usr/bin/env python3
"""
fix_pendant.py: the silk pumpkin 30 of pass PB3, rebuilt in code (render-agent, 2026-11-24; 0 tokens). Three findings on the edit:
  1. the generic cut took a strip of the wall's glow round the cord and a halo round the shade into the lamp's layer;
  2. the model drew the shade about 1.25 x the card's 30 cm (178 px wide against the clay's 143) and about 16 px high;
  3. a grey ring and a bright disc show in the opening at the bottom (the rejection list, ד.8: "a silver or shiny ring at the opening:
     matte, in the shade's colour").
What is done:
  - the shade: the largest bright component (L* above the midpoint of the silk and the wall round it) that holds the clay's shade, holes
    filled; its edge matted against the edit's own glowing wall (kd_cut2.matte);
  - the opening: the shade's bottom fifth across its middle third repainted from the silk round it (inpaint), so no ring and no bulb;
  - the size: the shade scaled about its own centre to the clay's width (the card's 30 cm) and its centre put on the clay's (Z 1.45-1.61);
  - the cord: the edit's thin white line, traced row by row and fitted as a straight line, redrawn 2 px wide from the new shade's top to
    the top of the canvas (the SKU's suspension wire: no rod, no canopy in frame);
  - the light: screen, 1 - (1 - e) / (1 - base) on the wall round the lamp outside the drawn shade, the cord and the blind, smoothed, and
    the hole where the drawn shade was filled from round it (normalised convolution), so the smaller shade sits in an even glow.
  python3 fix_pendant.py <kid>            (boy: from the PB3 edit; the girl takes the boy's layers by girl_from_boy.py)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402
from kids_passes import PRODUCTS  # noqa: E402

C = K.C
H, W = K.H, K.W


def main(kid="boy"):
    S = KC.edit_canvas("PB3-window")
    e, base, ids, env, st = S["e"], S["base"], S["ids"], S["env"], S["st"]
    lab = C.to_lab(e)
    L = lab[..., 0]
    clay = ids == 41
    rows = clay.sum(1)
    sr = np.nonzero(rows > 20)[0]
    cy0, cy1 = int(sr.min()), int(sr.max())
    cols = np.nonzero(clay[cy0:cy1 + 1].any(0))[0]
    cx0, cx1 = int(cols.min()), int(cols.max())
    clay_w, clay_h = cx1 - cx0 + 1, cy1 - cy0 + 1
    ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    win = np.zeros((H, W), bool)
    win[max(0, cy0 - 90):cy1 + 90, max(0, cx0 - 110):cx1 + 110] = True
    core = C.ero(clay & (np.arange(H)[:, None] >= cy0), 6)
    ring = win & ~C.dil(clay, 80)
    T = 0.5 * (np.median(L[core]) + np.median(L[ring]))
    bright = (L > T) & win
    n, lb, stt, _ = cv2.connectedComponentsWithStats(bright.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lb[bright & core])) - {0}
    shade = np.isin(lb, list(keep))
    shade = KC.fill_holes(shade, 4000)
    shade = cv2.morphologyEx(shade.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
    shade = cv2.morphologyEx(shade.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    cnt, _ = cv2.findContours(shade.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(cnt, key=cv2.contourArea))
    hm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(hm, [hull], 1)
    shade = hm.astype(bool)                    # the lantern's outline is convex: the ring's notch at the bottom is filled
    ys, xs = np.nonzero(shade)
    sy0, sy1, sx0, sx1 = ys.min(), ys.max(), xs.min(), xs.max()
    dw, dh = sx1 - sx0 + 1, sy1 - sy0 + 1
    dcx, dcy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    # the opening: the bottom fifth, middle third, repainted from the silk round it
    open_ = shade & (np.arange(H)[:, None] > sy1 - 0.22 * dh) & (np.abs(np.arange(W)[None, :] - dcx) < 0.2 * dw)
    open_ = C.dil(open_, 1) & shade
    Bk = KC.KC.inpaint(e, C.dil(shade, 3), radius=6)
    a, col = KC.KC.matte(e, shade, Bk)
    col = KC.KC.inpaint(col, open_, radius=5)
    a = np.where(C.ero(shade, 2), 1.0, a)
    # the size: about the shade's centre, to the clay's width; the centre to the clay's
    s = clay_w / dw
    M = np.float32([[s, 0, ccx - s * dcx], [0, s, ccy - s * dcy]])
    a2 = cv2.warpAffine(a.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
    col2 = cv2.warpAffine(col.astype(np.float32), M, (W, H), flags=cv2.INTER_LANCZOS4).astype(np.float64)
    a2 = np.clip(a2, 0, 1)
    new_top = ccy - s * dh / 2
    # the cord: a thin bright line above the drawn shade, traced and fitted
    pts = []
    for y in range(0, int(sy0) - 4):
        lo, hi = int(dcx - 18), int(dcx + 18)
        seg = L[y, lo:hi]
        loc = seg - np.median(seg)
        j = int(np.argmax(loc))
        if loc[j] > 2.0:
            pts.append((y, lo + j))
    pts = np.array(pts, float)
    A = np.stack([pts[:, 0], np.ones(len(pts))], 1)
    coef, *_ = np.linalg.lstsq(A, pts[:, 1], rcond=None)
    res = np.abs(A @ coef - pts[:, 1])
    good = res < 2.5
    coef, *_ = np.linalg.lstsq(A[good], pts[good, 1], rcond=None)
    yy, xx = np.mgrid[0:H, 0:W]
    xline = coef[0] * yy + coef[1]
    dist = np.abs(xx - xline)
    cord_a = np.clip(1.6 - dist, 0, 1) * (yy <= new_top + 3)
    cord_col = np.clip(np.median(e[np.clip(np.rint(pts[good, 0]).astype(int), 0, H - 1), np.clip(np.rint(pts[good, 1]).astype(int), 0, W - 1)], 0), 0, 1)
    # the cord at the new shade's centre line: shift the fitted line so it meets the scaled shade's top centre
    shift = ccx - (coef[0] * new_top + coef[1])
    cord_a = np.clip(1.6 - np.abs(xx - (xline + shift)), 0, 1) * (yy <= new_top + 3)
    alpha = 1 - (1 - a2) * (1 - cord_a)
    rgb = np.where((a2 > 0)[..., None], col2, cord_col[None, None, :] * np.ones((H, W, 3)))
    rgb = np.where(((a2 <= 0) & (cord_a <= 0))[..., None], 0, rgb)
    rgb = KC.floor_lab(np.clip(rgb, 0, 1), alpha > 0)
    alpha[alpha < 0.04] = 0
    # the light: round the lamp, outside the drawn shade, the cord and the blind; the hole filled from round it
    blind = np.asarray(Image.open(os.path.join(st, "layers", "roman-blind", PRODUCTS[kid]["roman-blind"][1] + ".png")))[..., 3] > 0
    drawn = C.dil(shade, 4) | C.dil(np.abs(xx - xline) < 2.5, 2) & (yy < sy0)
    L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.6)
    w = (env & ~drawn & ~C.dil(blind, 4) & (ids != 0) & (ids != 15)).astype(np.float64)
    Ls = np.stack([C.nconv(L8[..., c], w, sigmas=(10, 40, 120)) for c in range(3)], -1)
    soft_env = C.blur(env.astype(np.float64), 25)[..., None]
    light = np.clip(Ls, 0, 0.6) * soft_env
    light[~S["box"]] = 0
    # write
    slot, pid = PRODUCTS[kid]["pendant"][0], PRODUCTS[kid]["pendant"][1]
    rgba = np.dstack([C.q(rgb), C.q(alpha)])
    rgba[..., :3][rgba[..., 3] == 0] = 0
    lp = os.path.join(st, "layers", slot, pid + ".png")
    Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
    Image.fromarray(np.full((H, W), 255, np.uint8)).save(os.path.join(st, "shadows", slot, pid + ".png"), optimize=True)
    Image.fromarray(C.q(light)).save(os.path.join(st, "light", "PB3-window-lamps.png"), optimize=True)
    man = KC.load_man(kid)
    yy2, xx2 = np.nonzero(rgba[..., 3] > 0)
    for l in man["layers"]:
        if l["key"] == "pendant":
            l.update(alpha_px=int((rgba[..., 3] > 0).sum()), shadow_px=0, bbox_px=[int(xx2.min()), int(yy2.min()), int(xx2.max()) + 1, int(yy2.max()) + 1],
                     source=l["source"] + "; rebuilt by tools/fix_pendant.py (size, opening, cord, light)")
    rec = dict(threshold_L=round(float(T), 1), drawn_shade_px=[int(dw), int(dh)], clay_shade_px=[int(clay_w), int(clay_h)], scale=round(float(s), 3),
               scaled_shade_px=[round(float(dw * s), 1), round(float(dh * s), 1)], centre_moved_px=[round(float(ccx - dcx), 1), round(float(ccy - dcy), 1)],
               opening_px=int(open_.sum()), cord_line=dict(points=int(good.sum()), x_at_top=round(float(coef[1] + shift), 1), slope=round(float(coef[0]), 5)),
               light_max=round(float(light.max()), 3))
    man.setdefault("code_fixes", {})["pendant"] = dict(rec, why=__doc__.split("What is done:")[0].split("edit:")[1].strip())
    KC.save_man(kid, man)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["boy"]))
