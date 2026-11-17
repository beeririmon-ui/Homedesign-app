#!/usr/bin/env python3
"""
prep_hd.py: the model input of the HD still (render-agent, 2026-11-17). 0 tokens.
  the seed  = HDx (the accepted master) reprojected onto HD's 3:2 canvas (site/tools/transitions/seeds.py hd): u >= 0.717
  the input = the clay HD with the seed pasted, and:
    - the stone (94, 86) left of the seed: the gain that meets the seed's stone at its boundary (a 40 px band each side, per
      row, then a quadratic in the row through log gain) and the seed stone's median chroma, so HDx's wash and tone continue across the seam
    - the plaster (11, 82, 83): bone (a* 1.2, b* 6), the same vertical light profile as the stone's gain, and a level that puts the
      jib door (u 0.05-0.35, v 0.16-0.77, Z 0.80-1.65) at -0.52 vs base.png's back wall: inside 11.9.3's -0.60 +-1/6 and leaving
      the stone 0.25-0.6 darker than it (the seed's stone is at -0.82)
  python3 prep_hd.py <seed_dir> <out_input.png> <out_keep_mask.png>
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K  # noqa: E402
from prep_d0o import lab_from_lin, lin_from_lab, to_lin, to_srgb  # noqa: E402

W709 = np.array([0.2126, 0.7152, 0.0722])
JIB_TARGET = -0.52


def main(seed_dir, out, out_keep):
    clay = to_lin(np.asarray(Image.open(K.CLAY + "/HD.png").convert("RGB")).astype(np.float64) / 255)
    seed = to_lin(np.asarray(Image.open(seed_dir + "/hd-seed.png").convert("RGB")).astype(np.float64) / 255)
    keep = np.asarray(Image.open(seed_dir + "/hd-seed-mask.png")) > 127
    cls = K.clay_id("HD")
    H, W = cls.shape
    Yc, Ys = clay @ W709, seed @ W709
    stone = np.isin(cls, (94,))
    # the seed's left edge per row
    xb = np.array([np.argmax(keep[y]) if keep[y].any() else W for y in range(H)])
    g = np.full(H, np.nan)
    ab = np.full((H, 2), np.nan)
    labs = lab_from_lin(seed)
    for y in range(H):
        x = xb[y]
        if x >= W - 50 or x < 50:
            continue
        a_in = slice(x + 3, x + 43)
        a_out = slice(x - 43, x - 3)
        si, so = stone[y, a_in] & keep[y, a_in], stone[y, a_out] & ~keep[y, a_out]
        if si.sum() > 10 and so.sum() > 10:
            g[y] = np.median(Ys[y, a_in][si]) / np.median(Yc[y, a_out][so])
            ab[y] = np.median(labs[y, a_in][si][:, 1:], axis=0)
    rows = np.arange(H)
    ok = np.isfinite(g)
    g = np.interp(rows, rows[ok], g[ok])
    a_ = np.interp(rows, rows[ok], ab[ok, 0])
    b_ = np.interp(rows, rows[ok], ab[ok, 1])
    # a smooth profile: a quadratic in the row through log(gain) (the wash), not the stone-to-stone tone of single courses
    ws = ok.astype(float)
    c2 = np.polyfit(rows[ok], np.log(g[ok]), 2)
    g = np.exp(np.polyval(c2, rows))
    a_ = np.full(H, float(np.median(ab[ok, 0])))
    b_ = np.full(H, float(np.median(ab[ok, 1])))
    res = clay.copy()
    st = stone & ~keep | (np.isin(cls, (86,)) & ~keep)
    res[st] = clay[st] * g[:, None].repeat(W, 1)[st][:, None]
    lab = lab_from_lin(res)
    A = a_[:, None].repeat(W, 1)
    B = b_[:, None].repeat(W, 1)
    sm = stone & ~keep
    lab[sm, 1] = A[sm] + (lab[sm, 1] - lab[sm, 1].mean()) * 0.3
    lab[sm, 2] = B[sm] + (lab[sm, 2] - lab[sm, 2].mean()) * 0.3
    jm = np.isin(cls, (86,)) & ~keep
    lab[jm, 1] = A[jm] + 1.0
    lab[jm, 2] = B[jm] - 1.0
    res[sm | jm] = lin_from_lab(lab[sm | jm])
    # the plaster: the stone's vertical profile (normalised at the jib band's middle rows), bone tint, then the jib level
    pl = np.isin(cls, (11, 82, 83))
    jb = K.region("HD", (82,), 0.05, 0.35, 0.16, 0.77, cls=cls)
    jrows = np.nonzero(jb.any(1))[0]
    prof = g / np.median(g[jrows])
    res[pl] = clay[pl] * prof[:, None].repeat(W, 1)[pl][:, None]
    lab = lab_from_lin(res)
    lab[pl, 1] = 1.2 + (lab[pl, 1] - lab[pl, 1].mean()) * 0.3
    lab[pl, 2] = 6.0 + (lab[pl, 2] - lab[pl, 2].mean()) * 0.3
    res[pl] = lin_from_lab(lab[pl])
    Yr = res @ W709
    s0 = float(np.log2(np.median(Yr[jb]) / K.BASE_BACK_WALL))
    res[pl] = res[pl] * 2 ** (JIB_TARGET - s0)
    res = np.where(keep[..., None], seed, res)
    K.save_rgb(out, to_srgb(res))
    Image.fromarray(np.where(keep, 255, 0).astype(np.uint8)).save(out_keep)
    rep = dict(stone_gain_rows=[round(float(g.min()), 3), round(float(g.max()), 3)], plaster_profile=[round(float(prof.min()), 3), round(float(prof.max()), 3)],
               levels_of_input=K.levels("HD", np.asarray(Image.open(out).convert("RGB"))))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
