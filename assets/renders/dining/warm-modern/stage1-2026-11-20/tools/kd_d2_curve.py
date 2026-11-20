#!/usr/bin/env python3
"""
kd_d2_curve.py: the plaster-light curve of D2 (render-agent, 2026-11-20; 0 tokens). One camera point, one house: D2's locked still is
matched to the finished D1 plate on the plaster both frames see (D1 warped into D2 by the rotation homography): the quantiles (2-98) of
the plaster's smoothed L* (sigma 25, as kd_plate.plaster_light) in D2 mapped onto D1's, made monotonic. Prints the curve as json (for
KD_D2_CURVE) and writes it to d2-plaster-curve.json.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
import kd_plate as P  # noqa: E402

C = K.C
ids = K.ids("D2-plate")
e, _ = K.ecc_lock(os.path.join(K.ST, "raw/plate-D2-r1.png"), os.path.join(K.ST, "inputs/plate-D2-input.png"),
                  C.ero(np.isin(ids, P.ARCH), 3) & K.frame_mask())
p1 = C.load(os.path.join(K.ST, "plate-D1.png"))
maps = K.map_between("D1", "D2")
w1 = np.clip(K.warp(p1, "D1", "D2", maps=maps), 0, 1)
ov = C.ero(K.warp(K.frame_mask(), "D1", "D2", maps=maps) & K.frame_mask(), 12)
core = C.ero(np.isin(ids, P.PLASTER_ALL), 2)


def smoothL(img):
    L = C.to_lab(img)[..., 0]
    w = C.blur(core.astype(np.float64), 25)
    return C.blur(L * core, 25) / np.maximum(w, 1e-6)


m = core & ov
a, b = smoothL(e)[m], smoothL(w1)[m]
qs = np.linspace(2, 98, 13)
xa, xb = np.percentile(a, qs), np.percentile(b, qs)
xp = [0.0] + [round(float(v), 2) for v in xa] + [100.0]
fp = [0.0] + [round(float(v), 2) for v in xb] + [100.0]
for i in range(1, len(fp)):
    fp[i] = max(fp[i], fp[i - 1])
    xp[i] = max(xp[i], xp[i - 1] + 0.01)
cur = dict(xp=xp, fp=fp, how="quantiles 2-98 of the plaster's smoothed L* on the D1 / D2 overlap, D2 (raw, locked) onto D1 (final)", px=int(m.sum()))
json.dump(cur, open(os.path.join(K.ST, "d2-plaster-curve.json"), "w"), indent=1)
print(json.dumps(dict(xp=xp, fp=fp)))
