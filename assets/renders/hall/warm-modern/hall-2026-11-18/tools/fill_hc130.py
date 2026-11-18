#!/usr/bin/env python3
"""
fill_hc130.py: HC130's gap between its two seeds, in code (render-agent, 2026-11-18). 0 tokens.
Why: the one HC130 render (nano-banana-2, r1) drew a doorway into a lit room (a window, an oak floor: the living room of the reference
plate hdx.png) where the clay has the hall's back wall, the inside corner and the far wall (route 12.4, rejection items 3 and 5). The
seeds came back intact, and the budget is spent (2,650 of 2,658). The gap is two plain plaster planes, so it is built from what is there:
  - the light: the clay HC130, carried to the seeds' level row by row at their edges (hc130.py prep: the model input outside the seeds)
  - the plaster's grain: each plane's own grain from the seed on the SAME plane, mirrored across the seed's edge in world coordinates (the
    far wall X 0.80 from HD's seed, about Y = its edge; the back wall Y 9.80 from HC's seed, about X = its edge), as a multiplicative
    high-pass (the seed over its own 12 px blur), so the light stays the clay's and the trowel marks continue across the edges
  - the skirting and the floor sliver at the canvas bottom (under the 16:9 frame): the clay fill as it is
Then hc130.py compose with this picture in place of the model's.
  python3 fill_hc130.py <work> <out_fill.png> <report.json>
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import normals  # noqa: E402

N = "HC130"


def main(work, outp, repp):
    inp = K.to_lin(K.rgb(os.path.join(work, "hc130-input.png"))).astype(np.float32)
    ia = K.rgb8(os.path.join(work, "hc130-keep-hd.png"))[..., 0] > 127
    ib = K.rgb8(os.path.join(work, "hc130-keep-hc.png"))[..., 0] > 127
    P, ok = K.world(N)
    n = normals(N)
    gap = ~(ia | ib)
    far = ok & (n[..., 0] > 0.7) & (P[..., 0] < 0.83)
    back = ok & (n[..., 1] < -0.7) & (np.abs(P[..., 1] - 9.80) < 0.02)
    Ylum = inp @ K.W709
    low = cv2.GaussianBlur(Ylum, (0, 0), 12.0)
    hp = np.clip(Ylum / np.maximum(low, 1e-4), 0.85, 1.15).astype(np.float32)
    # no line is carried by the mirror: the jib door's seam (clay id 83) and the walnut reveal's edges are flattened in the grain
    cls = K.clay_id(N)
    lines = cv2.dilate(np.isin(cls, (83, 23)).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    hp[lines] = 1.0
    cam, cv = K.CAMS[N], K.canvas(N)
    out = inp.copy()
    rep = dict(gap_px=int(gap.sum()))
    for nm, plane, seed, axis in (("far wall X 0.80", far, ia, 1), ("back wall Y 9.80", back, ib, 0)):
        edge_px = plane & seed & ~cv2.erode(seed.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        if not edge_px.any():
            continue
        c_edge = float(np.median(P[..., axis][edge_px]))
        tgt = plane & gap
        Pm = P[tgt].copy()
        Pm[:, axis] = 2 * c_edge - Pm[:, axis]
        us, vs, _ = cam.project(Pm)
        mx, my = cv.px(us, vs)
        m_ = len(mx)
        w_ = 1024
        h_ = (m_ + w_ - 1) // w_
        MX = np.zeros(h_ * w_, np.float32)
        MY = np.zeros(h_ * w_, np.float32)
        MX[:m_], MY[:m_] = mx, my
        smp = cv2.remap(hp, MX.reshape(h_, w_), MY.reshape(h_, w_), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).reshape(-1)[:m_]
        inside = seed[np.clip(np.rint(my).astype(int), 0, cv.h - 1), np.clip(np.rint(mx).astype(int), 0, cv.w - 1)]
        smp = np.where(inside, smp, 1.0)
        out[tgt] = inp[tgt] * smp[:, None]
        rep[nm] = dict(px=int(tgt.sum()), mirror_about=round(c_edge, 4), sampled_inside_seed_pct=round(float(inside.mean()) * 100, 1))
    # the tone at each seed's edge, row by row and per channel (the seeds' plaster is a little cooler than the clay's): the fill takes the
    # seed's colour there, fading over 250 px into the gap; ratios clipped to 0.8-1.25 (rows where the edge meets the reveal or the floor)
    H, W = gap.shape
    rows = np.arange(H)
    for nm, seed in (("hc", ib), ("hd", ia)):
        dist = cv2.distanceTransform((~seed).astype(np.uint8), cv2.DIST_L2, 5)
        din = cv2.distanceTransform(seed.astype(np.uint8), cv2.DIST_L2, 5)
        r = np.full((H, 3), np.nan)
        for y in range(H):
            a_ = seed[y] & (din[y] > 4) & (din[y] < 40)
            b_ = gap[y] & (dist[y] > 4) & (dist[y] < 40) & (far[y] | back[y])
            if a_.sum() > 8 and b_.sum() > 8:
                r[y] = np.median(out[y, a_], 0) / np.maximum(np.median(out[y, b_], 0), 1e-4)
        okr = np.isfinite(r[:, 0])
        if okr.sum() < 10:
            continue
        r = np.stack([np.interp(rows, rows[okr], r[okr, c]) for c in range(3)], -1)
        r = np.clip(cv2.GaussianBlur(r.astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=15), 0.8, 1.25)
        w = (np.exp(-dist / 250.0) * gap)[..., None]
        out = out * (1 + (r[:, None, :] - 1) * w)
        rep[f"edge_colour_{nm}"] = dict(rows=int(okr.sum()), ratio_min=[round(float(v), 3) for v in r.min(0)], ratio_max=[round(float(v), 3) for v in r.max(0)])
    K.save(outp, K.to_srgb(out))
    K.dump(repp, rep)
    print(rep)


if __name__ == "__main__":
    main(*sys.argv[1:4])
