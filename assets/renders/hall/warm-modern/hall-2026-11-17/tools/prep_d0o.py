#!/usr/bin/env python3
"""
prep_d0o.py: the model input of the D0o still (render-agent, 2026-11-17). 0 tokens.
  outside the mask: the approved D0 (assets/renders/hall/warm-modern/door-2026-11-16/d0.png), byte for byte
  inside the mask: the lit clay D0-none (wm-door-2026-11-16), through its id pass:
    - the whole interior scaled in linear light so that the jib door (id 82, u 0.28-0.36, v 0.40-0.55, Z 0.80-1.65) sits
      at the 11.9.3 target, -0.60 stops vs base.png's back wall
    - the hall floor (10) to smoked oak: chroma of #8B6F55, median L* 42 (base.png's oak, about 0.6 stop down), its
      plank shading kept as a ratio
    - plaster (11, 14, 15, 64, 82, 83) to bone (a* 1, b* 5), stone (85, 86, 94) to the honed limestone (a* 2, b* 12),
      the slot (95) to a warm white; lightness kept
The mask = the leaf rectangle of motion-agent's section 2 (u 0.2441-0.4224, v 0.0997-0.8603), plus the one column
(x 1161) where D0's leaf runs 1.17 px past it (d0-lock.json): without it a 1 px walnut line stays on the right jamb.

  python3 prep_d0o.py <out_input.png> <out_mask.png>
"""
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K  # noqa: E402

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])


def to_lin(rgb):
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def lab_from_lin(l):
    xyz = l @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lin_from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    return np.clip(xyz @ np.linalg.inv(M).T, 0, 1)


def mask_d0o():
    cv = K.canvas("D0o")
    m = np.zeros((cv.h, cv.w), bool)
    m[187:1285, 704:1162] = True          # pixel centres inside u 0.2441-0.4224, v 0.0997-0.8603, plus column 1161
    return m


def main(out, out_mask):
    d0 = np.asarray(Image.open(K.D0).convert("RGB")).astype(np.float64) / 255
    clay = np.asarray(Image.open(K.CLAY + "/D0-none.png").convert("RGB")).astype(np.float64) / 255
    cls = K.clay_id("D0o")
    m = mask_d0o()
    lin = to_lin(clay)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    jb = K.region("D0o", (82,), 0.28, 0.36, 0.40, 0.55, cls=cls)
    s0 = float(np.log2(np.median(Y[jb]) / K.BASE_BACK_WALL))
    k = 2 ** (-0.60 - s0)
    lin = lin * k
    lab = lab_from_lin(lin)
    rep = dict(jib_clay_stops=round(s0, 3), interior_gain=round(k, 4))

    def tint(ids, a, b, keep=0.3):
        mm = m & np.isin(cls, ids)
        if mm.any():
            lab[mm, 1] = a + (lab[mm, 1] - lab[mm, 1].mean()) * keep
            lab[mm, 2] = b + (lab[mm, 2] - lab[mm, 2].mean()) * keep
        return int(mm.sum())
    rep["plaster_px"] = tint((11, 14, 15, 64, 82, 83), 1.0, 5.0)
    rep["stone_px"] = tint((85, 94), 2.0, 12.0)
    rep["joint_px"] = tint((86,), 3.0, 11.0)
    rep["slot_px"] = tint((95,), 0.0, 3.0)
    res = lin_from_lab(lab)
    # the floor: a gain in linear light to median L* 42, then oak chroma
    fl = m & (cls == 10)
    Yf = res @ np.array([0.2126, 0.7152, 0.0722])
    Yt = ((42 + 16) / 116) ** 3
    res[fl] *= Yt / float(np.median(Yf[fl]))
    labf = lab_from_lin(res)
    labf[fl, 1] = 6.0 + (labf[fl, 1] - labf[fl, 1].mean()) * 0.3
    labf[fl, 2] = 15.0 + (labf[fl, 2] - labf[fl, 2].mean()) * 0.3
    res[fl] = lin_from_lab(labf[fl])
    rep["floor_px"] = int(fl.sum())
    inside = to_srgb(res)
    outimg = np.where(m[..., None], inside, d0)
    K.save_rgb(out, outimg)
    Image.fromarray(np.where(m, 255, 0).astype(np.uint8)).save(out_mask)
    o = np.asarray(Image.open(out).convert("RGB")).astype(int)
    d0i = np.asarray(Image.open(K.D0).convert("RGB")).astype(int)
    rep["outside_mask_max_diff_levels"] = int(np.abs(o - d0i)[~m].max())
    rep["mask_px"] = int(m.sum())
    rep["jib_after_stops"] = round(K.levels("D0o", o)["stops_vs_base"], 3)
    print(rep)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
