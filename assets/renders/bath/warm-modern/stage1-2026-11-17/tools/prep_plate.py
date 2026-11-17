#!/usr/bin/env python3
"""
prep_plate.py: the model input of the B2 empty plate (output 1), render-agent, 2026-11-17. 0 tokens.
The lit clay B2-plate (assets/blockout/house/framing/wm-bath-2026-11-17/B2-plate.png), recoloured through its id pass so the model sees
the house's own materials (chroma only, the clay's lightness and shading kept):
  plaster (ids 1-4, 6)         a* 0.5, b* 4.0    base.png's back wall (median of x 1300-2200, y 300-800)
  limestone (5, 9, 11, 12, 14) a* 2.5, b* 13.5, L* -4: between the albedo #D8C8AE (a* 1.4, b* 15.0) and hdx.png's stone in shade
                               (a* 3.3, b* 16.5); 4 L* down so the stone reads as the darker material next to the plaster
  joints (10, 13)              the stone's chroma, L* 10 below the clay (6 below the recoloured stone)
  walnut (20, 21, 22)          a* 11.4, b* 17.6  base.png's coffee-table top
  bronze (15, 18, 25)          a* 2.4, b* 5.1    #3A322C
  basin (24)                   a* 0.5, b* 5.0    warm white
Nothing else changes (mirror 17, slot and gaps 7 / 8, the downlight 16).

  python3 prep_plate.py <clay.png> <clay-id.png> <out.png>
"""
import sys

import numpy as np
from PIL import Image

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
TARGET = {"plaster": ((1, 2, 3, 4, 6), 0.5, 4.0), "stone": ((5, 9, 11, 12, 14), 2.5, 13.5), "walnut": ((20, 21, 22), 11.4, 17.6),
          "bronze": ((15, 18, 25), 2.4, 5.1), "basin": ((24,), 0.5, 5.0)}


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


def main(clay, idp, out):
    a = np.asarray(Image.open(clay).convert("RGB")).astype(np.float64) / 255
    ids = np.asarray(Image.open(idp))
    L = lab(a)
    rep = {}
    for name, (gids, ta, tb) in TARGET.items():
        m = np.isin(ids, gids)
        if not m.any():
            continue
        before = np.median(L[m][:, 1:], 0)
        L[m, 1] = ta + (L[m, 1] - before[0]) * 0.5            # keep half the local chroma variation (light colour, bounce)
        L[m, 2] = tb + (L[m, 2] - before[1]) * 0.5
        if name == "stone":
            L[m, 0] = np.clip(L[m, 0] - 4.0, 0, 100)
        rep[name] = dict(px=int(m.sum()), before_ab=[round(float(x), 1) for x in before], after_ab=[ta, tb])
    j = np.isin(ids, (10, 13))
    if j.any():
        L[j, 1], L[j, 2] = 2.5, 13.5
        L[j, 0] = np.clip(L[j, 0] - 10, 0, 100)
    res = rgb_from_lab(L)
    Image.fromarray(np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)).save(out)
    print(rep)


if __name__ == "__main__":
    main(*sys.argv[1:4])
