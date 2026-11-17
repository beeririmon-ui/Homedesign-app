#!/usr/bin/env python3
"""
lock_mb0.py: an MB0 still against its clay (render-agent, 2026-11-17; 0 tokens).
The clay's named lines (assets/blockout/house/framing/wm-master-2026-11-17/lock-target.json: analytic projections, samples kept where the
clay's depth pass sees the line) are found in the still: at each seen sample, the luminance gradient profile across the line (+-R px)
is registered to the same profile in the lit clay; the offset is the shift that maximises the correlation. Per line: the median offset,
p90 |offset|, the number of samples and the mean correlation; and the tilt of the line in the still against the clay.

  python3 lock_mb0.py <still.png> <clay.png> <out.json> [line-name-filter ...]
(Copied from the bath's tools/lock_b2.py; only the lock-target path changes.)
"""
import json
import math
import sys

import numpy as np
from PIL import Image

LT = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/lock-target.json"
R = 14


def gray(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    return a @ [0.2126, 0.7152, 0.0722]


def profile(g, x, y, vertical):
    H, W = g.shape
    x, y = int(round(x)), int(round(y))
    if vertical:
        if not (R + 2 <= x < W - R - 2 and 0 <= y < H):
            return None
        row = g[max(0, y - 2):y + 3, x - R - 1:x + R + 2].mean(0)
    else:
        if not (R + 2 <= y < H - R - 2 and 0 <= x < W):
            return None
        row = g[y - R - 1:y + R + 2, max(0, x - 2):x + 3].mean(1)
    d = np.diff(row)
    d = d - d.mean()
    n = np.linalg.norm(d)
    return None if n < 1e-6 else d / n


def offset(pc, ps):
    best, bk = -2, 0
    for k in range(-8, 9):
        a = pc[max(0, k):len(pc) + min(0, k)]
        b = ps[max(0, -k):len(ps) + min(0, -k)]
        c = float((a * b).sum())
        if c > best:
            best, bk = c, k
    return -bk, best


def main(still, clay, out, *filt):
    lt = json.load(open(LT))
    gs, gc = gray(still), gray(clay)
    res = {}
    worst = 0.0
    for name, L in lt["lines"].items():
        if filt and not any(f in name for f in filt):
            continue
        (x0, y0), (x1, y1) = L["px_ends"]
        vertical = abs(x1 - x0) < abs(y1 - y0)
        offs, cors, pts = [], [], []
        for x, y, seen in L["samples"]:
            if not seen:
                continue
            pc, ps = profile(gc, x, y, vertical), profile(gs, x, y, vertical)
            if pc is None or ps is None:
                continue
            o, c = offset(pc, ps)
            if c < 0.5:
                continue
            offs.append(o)
            cors.append(c)
            pts.append((y if vertical else x, o))
        if len(offs) < 4:
            res[name] = dict(n=len(offs), note="too few confident samples (flat or covered)")
            continue
        offs = np.array(offs, float)
        t = np.array(pts, float)
        k = np.polyfit(t[:, 0], t[:, 1], 1)[0] if len(t) > 3 else 0.0
        res[name] = dict(kind="vertical" if vertical else "horizontal", n=len(offs), median_offset_px=round(float(np.median(offs)), 2),
                         p90_abs_px=round(float(np.percentile(np.abs(offs), 90)), 2), mean_corr=round(float(np.mean(cors)), 3),
                         tilt_deg_vs_clay=round(math.degrees(math.atan(k)), 3))
        worst = max(worst, abs(float(np.median(offs))))
    rep = dict(still=still, clay=clay, method=__doc__.strip().split("\n")[1], worst_median_px=round(worst, 2), lines=res)
    json.dump(rep, open(out, "w"), indent=1)
    for k, v in res.items():
        print(f"{k:55s} {v}")
    print("worst median", round(worst, 2))


if __name__ == "__main__":
    main(*sys.argv[1:])
