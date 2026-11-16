#!/usr/bin/env python3
"""
prep_input.py: the input of the final D0 still = the lit clay D0-closed.png (wm-door-2026-11-16) with two colour edits through its id pass,
as for the 2026-11-14 still (README there): the leaf (ids 70, 71) to oiled-walnut Lab (L* 44, a* 14, b* 24; the clay's AgX render makes the
#6B4A33 leaf look orange, L* ~51) and the fluted glass (id 76) from near-black to a soft bone grey (L* 62). The shading inside each mask (the
flutes, the glass reeding) is kept; nothing else changes. render-agent, 2026-11-16. 0 tokens.

  python3 prep_input.py <out.png>
"""
import sys

import numpy as np
from PIL import Image

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-door-2026-11-16/D0-closed"
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])


def to_lab(rgb):
    l = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = l @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    l = np.clip(xyz @ np.linalg.inv(M).T, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def recolour(lab, m, L, a, b, keep):
    mu = lab[m, 0].mean()
    lab[m, 0] = L + (lab[m, 0] - mu) * keep
    lab[m, 1] = a + (lab[m, 1] - lab[m, 1].mean()) * 0.3
    lab[m, 2] = b + (lab[m, 2] - lab[m, 2].mean()) * 0.3
    return dict(mean_L_before=round(float(mu), 1))


def main(out):
    rgb = np.asarray(Image.open(CLAY + ".png").convert("RGB")).astype(np.float64) / 255
    cls = np.asarray(Image.open(CLAY + "-id.png"))
    lab = to_lab(rgb)
    rep = {}
    leaf = np.isin(cls, (70, 71))
    rep["leaf"] = recolour(lab, leaf, 44.0, 14.0, 24.0, 1.0)
    glass = cls == 76
    rep["glass"] = recolour(lab, glass, 62.0, 0.0, 3.0, 0.6)
    res = rgb.copy()
    m = leaf | glass
    res[m] = from_lab(lab[m])
    Image.fromarray(np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)).save(out)
    d = np.abs(res - rgb).max(-1) * 255
    rep["changed_px"] = int((d > 0.5).sum())
    rep["outside_the_two_masks_max_diff_levels"] = float(d[~m].max())
    print(rep)


if __name__ == "__main__":
    main(sys.argv[1])
