#!/usr/bin/env python3
"""
prep_plate.py: the model input of the MB0 empty plate, render-agent, 2026-11-17. 0 tokens.
The lit clay MB0-plate (assets/blockout/house/framing/wm-master-2026-11-17/MB0-plate.png), recoloured through its id pass so the model
sees the house's own materials (chroma per material; the clay's lightness and shading kept unless noted):
  plaster (ids 1-6, 9, 12)       a* 0.5, b* 4.0     base.png's back wall (median of x 1300-2200, y 300-800)
  smoked oak floor (10)          a* 7.6, b* 16.3    base.png's floor (median of three clean patches)
  floor joints (11)              the oak's chroma, L* 12 below the clay
  walnut (20, 21, 24, 25)        a* 11.4, b* 17.6   base.png's coffee-table top (as the bath)
  plinths, grooves (22, 26, 27)  a* 7.0, b* 9.0, L* capped at 24 (the dark walnut in shade, #3A2A1F)
  mattress (23)                  a* 0.7, b* 4.6     #E6DFD3; L* capped 2 below the bed wall's median right above the headboard
  bronze frame (13)              a* 2.4, b* 5.1, L* 24   #3A322C (the clay's frame is lit grey)
  limestone slab (14)            a* 2.5, b* 13.5, L* -4 (as the bath)
Nothing else changes (the sky and the ground outside, ids 0 / 15).

  python3 prep_plate.py <clay.png> <clay-id.png> <out.png> <out.json>
"""
import json
import sys

import numpy as np
from PIL import Image

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
TARGET = {"plaster": ((1, 2, 3, 4, 5, 6, 9, 12), 0.5, 4.0), "oak": ((10,), 7.6, 16.3), "walnut": ((20, 21, 24, 25), 11.4, 17.6),
          "dark walnut": ((22, 26, 27), 7.0, 9.0), "mattress": ((23,), 0.7, 4.6), "bronze": ((13,), 2.4, 5.1), "stone": ((14,), 2.5, 13.5)}


def to_lin(rgb):
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def lab(rgb):
    xyz = to_lin(rgb) @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def rgb_from_lab(L):
    fy = (L[..., 0] + 16) / 116
    fx, fz = fy + L[..., 1] / 500, fy - L[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    return to_srgb(xyz @ np.linalg.inv(M).T)


def main(clay, idp, out, rec):
    a = np.asarray(Image.open(clay).convert("RGB")).astype(np.float64) / 255
    ids = np.asarray(Image.open(idp))
    L = lab(a)
    rep = {}
    H, W = ids.shape
    wall_above = (ids == 1)
    wall_above[: int(0.40 * H)] = False
    wall_above[int(0.47 * H):] = False
    wall_ref = float(np.median(L[wall_above][:, 0])) if wall_above.any() else 85.0
    for name, (gids, ta, tb) in TARGET.items():
        m = np.isin(ids, gids)
        if not m.any():
            continue
        before = np.median(L[m], 0)
        L[m, 1] = ta + (L[m, 1] - before[1]) * 0.5
        L[m, 2] = tb + (L[m, 2] - before[2]) * 0.5
        if name == "stone":
            L[m, 0] = np.clip(L[m, 0] - 4.0, 0, 100)
        if name == "bronze":
            L[m, 0] = 24.0 + (L[m, 0] - before[0]) * 0.3
        if name == "dark walnut":
            L[m, 0] = np.minimum(L[m, 0], 24.0)
        if name == "mattress":
            L[m, 0] = np.minimum(L[m, 0], wall_ref - 2.0 + (L[m, 0] - before[0]))
        rep[name] = dict(px=int(m.sum()), before_Lab=[round(float(x), 1) for x in before], after_ab=[ta, tb],
                         after_median_L=round(float(np.median(L[m, 0])), 1))
    j = ids == 11
    if j.any():
        L[j, 1], L[j, 2] = 7.6, 16.3
        L[j, 0] = np.clip(L[j, 0] - 12, 0, 100)
    rep["bed_wall_L_above_headboard"] = round(wall_ref, 1)
    res = rgb_from_lab(L)
    Image.fromarray(np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)).save(out)
    json.dump(rep, open(rec, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
