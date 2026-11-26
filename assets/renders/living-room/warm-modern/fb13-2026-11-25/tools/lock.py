#!/usr/bin/env python3
"""lock.py: does a returned frame keep the clay's camera? The clay's id boundaries (plate or full pass), by class, against the frame's
own edges: the median and p90 distance (px on the 2720 canvas) from each boundary pixel to the nearest strong edge of the frame, and
the global shift / scale found by ECC on the edge maps (the pilot's lock_v2 idea, in short).
  python3 lock.py <frame png> [hero]
"""
import json
import sys

import cv2
import numpy as np

import hwlib as L


def edges(rgb):
    g = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 1.6)
    return cv2.Canny(g, 12, 36) > 0


def boundary(idx, ids, other=None):
    m = np.isin(idx, ids)
    b = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    if other is not None:
        b &= cv2.dilate(np.isin(idx, other).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    b[:6] = b[-6:] = False
    b[:, :6] = b[:, -6:] = False
    return b


def check(rgb, hero=False):
    m = L.maps()
    idx = m["idx"] if hero else m["idx_p"]
    E = edges(rgb)
    dt = cv2.distanceTransform((~E).astype(np.uint8), cv2.DIST_L2, 5)
    classes = {"sofa outline (against the wall and the floor)": boundary(idx, [1], [5, 8, 11]),
               "armchair outline": boundary(idx, [3], [8, 520, 521, 6, 5, 11]),
               "floor line (skirting on the floor)": boundary(idx, [8], [11]),
               "glazing frame": boundary(idx, [4], [0, 732, 14, 6]),
               "window bench": boundary(idx, [520], [6, 521, 8, 14, 4]),
               "ceiling band": boundary(idx, [522, 9], [5, 521, 6])}
    if hero:
        for k in ("coffee-table", "pendant", "floor-lamp", "framed-art", "planter", "vase", "basket", "magazine-holder"):
            classes[k] = boundary(idx, [L.PI[k]])
    out = {}
    for k, b in classes.items():
        if b.sum() < 50:
            continue
        d = dt[b]
        out[k] = dict(px=int(b.sum()), median=round(float(np.median(d)), 1), p90=round(float(np.percentile(d, 90)), 1))
    # the global shift that best lays the clay's boundaries on the frame's edges (truncated chamfer, +-80 px, then +-6 px fine)
    B = np.zeros(idx.shape, bool)
    for b in classes.values():
        B |= b
    ys, xs = np.where(B)
    dtt = np.minimum(dt, 30.0)
    Hh, Ww = dt.shape

    def score(dx, dy):
        x, y = xs + dx, ys + dy
        ok = (x >= 0) & (x < Ww) & (y >= 0) & (y < Hh)
        return float(dtt[y[ok], x[ok]].mean()) if ok.sum() > 0.8 * len(xs) else 99.0

    best = min(((score(dx, dy), dx, dy) for dx in range(-80, 81, 8) for dy in range(-80, 81, 8)))
    best = min(((score(dx, dy), dx, dy) for dx in range(best[1] - 8, best[1] + 9, 1) for dy in range(best[2] - 8, best[2] + 9, 1)))
    out["shift"] = dict(px=[int(best[1]), int(best[2])], chamfer_at_shift=round(best[0], 2), chamfer_at_zero=round(score(0, 0), 2))
    # the overlay for the eye: the clay's boundaries in red on the frame
    ov = (np.clip(rgb, 0, 1) * 255).astype(np.uint8).copy()
    ov[cv2.dilate(B.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0] = (255, 30, 30)
    out["_overlay"] = ov
    return out


if __name__ == "__main__":
    im = L.rd(sys.argv[1])
    r = check(im, hero=len(sys.argv) > 2)
    ov = r.pop("_overlay")
    from PIL import Image
    Image.fromarray(ov).resize((1360, 765), Image.LANCZOS).save(sys.argv[1].rsplit(".", 1)[0] + "-lock.jpg", quality=88)
    print(json.dumps(r))
