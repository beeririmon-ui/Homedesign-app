#!/usr/bin/env python3
"""
hc130.py: HC130, the bridge (route 12.4), seeded from its overlaps with HD and HC as HD was built from HDx (render-agent, 2026-11-18). 0 tokens.
  prep     the seeds: HD2 (hd.png with the bench strip; the bench is out of HC130) and HC, each turned by the pure rotation about HX onto
           HC130's 3:2 canvas, where its canvas has the ray (HD: u ~0.53-1.03, HC: u ~-0.03-0.35). Between them, the clay HC130:
           the back wall (Y 9.80) and the far wall (X 0.80) each take one gain per row that meets the nearer seed at its edge (a 40 px band
           each side, then a quadratic in the row through log gain, as prep_hd.py), and the seeds' median chroma.
  compose  the model's picture between the seeds; the seeds pasted back exactly, ramped 70 px inside their edges (as compose_hd.py), so
           that HD -> HC130 -> HC turn on the same pixels.
  python3 hc130.py prep <hd2.png> <hc.png> <work>      -> hc130-input.png, hc130-keep-hd.png, hc130-keep-hc.png, prep-hc130.json
  python3 hc130.py compose <model.png> <work> <out.png> <report.json>
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import normals  # noqa: E402

N = "HC130"


def seeds(hd2p, hcp):
    hd = K.to_lin(K.rgb(hd2p)).astype(np.float32)
    hc = K.to_lin(K.rgb(hcp)).astype(np.float32)
    a, ia = K.rot(hd, "HD", N)
    b, ib = K.rot(hc, "HC", N)
    k = np.ones((5, 5), np.uint8)
    ia = cv2.erode(ia.astype(np.uint8), k).astype(bool)          # 2 px off the source canvas edge (no border replicate)
    ib = cv2.erode(ib.astype(np.uint8), k).astype(bool)
    return a, ia, b, ib


def row_gain(clay_Y, seed_Y, surf, keep, side, H):
    """Per row: median(seed) / median(clay) in 40 px bands each side of the seed's edge, on surface `surf`; a quadratic in the row."""
    g = np.full(H, np.nan)
    W = keep.shape[1]
    for y in range(H):
        cols = np.nonzero(keep[y])[0]
        if not len(cols):
            continue
        x = cols.max() if side == "left" else cols.min()
        if side == "left":
            si, so = slice(max(x - 42, 0), x - 2), slice(x + 3, min(x + 43, W))
        else:
            si, so = slice(x + 3, min(x + 43, W)), slice(max(x - 42, 0), x - 2)
        mi, mo = surf[y, si] & keep[y, si], surf[y, so] & ~keep[y, so]
        if mi.sum() > 10 and mo.sum() > 10:
            g[y] = np.median(seed_Y[y, si][mi]) / np.median(clay_Y[y, so][mo])
    rows = np.arange(H)
    ok = np.isfinite(g)
    c2 = np.polyfit(rows[ok], np.log(g[ok]), 2)
    return np.exp(np.polyval(c2, rows)), int(ok.sum())


def prep(hd2p, hcp, work):
    a, ia, b, ib = seeds(hd2p, hcp)
    clay = K.to_lin(K.rgb(K.clay_png(N)))
    P, ok = K.world(N)
    n = normals(N)
    H, W = ia.shape
    U, V = K.canvas(N).uv()
    back = ok & (n[..., 1] < -0.7) & (np.abs(P[..., 1] - 9.80) < 0.02)
    far = ok & (n[..., 0] > 0.7) & (P[..., 0] < 0.85)
    Yc = clay @ K.W709
    gb, nb = row_gain(Yc, b @ K.W709, back, ib, "left", H)
    gf, nf = row_gain(Yc, a @ K.W709, far, ia, "right", H)
    res = clay.copy()
    res[back] = clay[back] * gb[:, None].repeat(W, 1)[back][:, None]
    res[far] = clay[far] * gf[:, None].repeat(W, 1)[far][:, None]
    rest = ~back & ~far
    res[rest] = clay[rest] * float(np.median(gb))
    lab = K.lab_from_lin(res)
    la, lb_ = K.lab_from_lin(a), K.lab_from_lin(b)
    for m, src, keep in ((far, la, ia), (back | rest, lb_, ib)):
        mm = m & ~(ia | ib)
        a0, b0 = float(np.median(src[keep & m][:, 1])) if (keep & m).any() else 1.0, float(np.median(src[keep & m][:, 2])) if (keep & m).any() else 5.0
        lab[mm, 1] = a0 + (lab[mm, 1] - lab[mm, 1].mean()) * 0.3
        lab[mm, 2] = b0 + (lab[mm, 2] - lab[mm, 2].mean()) * 0.3
    res = K.lin_from_lab(lab)
    res = np.where(ia[..., None], a, np.where(ib[..., None], b, res))
    K.save(os.path.join(work, "hc130-input.png"), K.to_srgb(res))
    K.save(os.path.join(work, "hc130-keep-hd.png"), np.where(ia, 255, 0).astype(np.uint8))
    K.save(os.path.join(work, "hc130-keep-hc.png"), np.where(ib, 255, 0).astype(np.uint8))
    rep = dict(seed_hd_px=int(ia.sum()), seed_hc_px=int(ib.sum()), new_px=int((~ia & ~ib).sum()),
               seed_hd_u=[round(float(U[ia].min()), 4), round(float(U[ia].max()), 4)], seed_hc_u=[round(float(U[ib].min()), 4), round(float(U[ib].max()), 4)],
               back_gain_rows=[round(float(gb.min()), 3), round(float(gb.max()), 3), nb], far_gain_rows=[round(float(gf.min()), 3), round(float(gf.max()), 3), nf])
    K.dump(os.path.join(work, "prep-hc130.json"), rep)
    print(rep)


def compose(model, work, outp, repp, ramp=70.0):  # noqa: C901
    cv = K.canvas(N)
    m8 = K.rgb8(model)
    r8 = K.resample_to(m8, cv.w, cv.h)
    r = K.to_lin(r8 / 255.0)
    i8 = K.rgb8(os.path.join(work, "hc130-input.png"))
    s = K.to_lin(i8 / 255.0)
    ia = K.rgb8(os.path.join(work, "hc130-keep-hd.png"))[..., 0] > 127
    ib = K.rgb8(os.path.join(work, "hc130-keep-hc.png"))[..., 0] > 127
    keep = ia | ib
    dx, dy, resp = K.shift_vs(i8 / 255.0, r8 / 255.0, keep.astype(np.float32))
    rep = dict(model_px=[int(m8.shape[1]), int(m8.shape[0])], shift_vs_seeds_px=dict(dx=round(dx, 2), dy=round(dy, 2), response=round(resp, 3)))
    if abs(dx) > 0.5 or abs(dy) > 0.5:
        M = np.array([[1, 0, -dx], [0, 1, -dy]], np.float32)
        r = cv2.warpAffine(r.astype(np.float32), M, (cv.w, cv.h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        rep["shift_corrected"] = True
    d = cv2.distanceTransform(keep.astype(np.uint8), cv2.DIST_L2, 5)
    rampmap = np.where(ib, 2.0 * ramp, ramp)          # HC's seed (r1's hall plaster, a little cooler) fades in over twice the ramp
    t = np.clip(d / rampmap, 0, 1)
    al = np.where(keep, t * t * (3 - 2 * t), 0.0)[..., None]
    out = r * (1 - al) + s * al
    K.save(outp, K.to_srgb(out))
    o8 = K.rgb8(outp)
    core = keep & (d >= rampmap)
    rep["seed_core_max_diff_levels"] = int(np.abs(o8.astype(int) - i8.astype(int))[core].max())
    for nm, m in (("hd", ia), ("hc", ib)):
        e = m & (d > 3) & (d < 12)
        Ys, Yr = (s @ K.W709)[e], (r @ K.W709)[e]
        rep[f"seam_{nm}_model_vs_seed_pct"] = dict(median=round(float(np.median(Yr / np.maximum(Ys, 1e-4) - 1)) * 100, 2),
                                                   p90_abs=round(float(np.percentile(np.abs(Yr / np.maximum(Ys, 1e-4) - 1), 90)) * 100, 2))
    K.dump(repp, rep)
    print(rep)


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(*sys.argv[2:5])
    else:
        compose(*sys.argv[2:6])
