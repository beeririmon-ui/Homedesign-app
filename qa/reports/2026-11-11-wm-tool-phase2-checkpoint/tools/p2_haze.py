#!/usr/bin/env python3
"""
qa-agent 2026-11-11: haze test. A layer's soft edge should only blend the product into the room; it must not lay a lighter (or darker)
veil over the room beyond the product's own edge. For each layer, its low-alpha fringe (0 < alpha < 255, farther than 2 px from the
alpha-255 core): composite (that layer over everything below it in set B, without the layers above) against the same stack without it,
dL* per pixel; counts of px lighter / darker by > 3 L*, how far they reach from the core (p95 px), and the mean dL* there.
A product's whole-edge AA is 1-2 px; a veil reaching 5+ px with dL* > 3 is a halo the eye reads as "pasted".
Writes data/haze.json and overlays/haze-<layer>.jpg (red = lighter, blue = darker, on the scene).
~/.venvs/motion/bin/python -I p2_haze.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
order = [i for i in man["compose"]["order"] if i != "base" and not i.endswith("-shadow")]


def rd(p):
    return np.asarray(Image.open(p)).astype(np.float64)


base = rd(os.path.join(P2, "layers/base.png"))
L_, S_ = {}, {}
for k in order:
    if k == "cushions":
        L_[k] = rd(os.path.join(P2, "layers", man["slot_cushions"]["sets"]["B"]["layer"]))
        S_[k] = rd(os.path.join(P2, "layers", man["slot_cushions"]["sets"]["B"]["shadow"]))
    else:
        L_[k] = rd(os.path.join(P2, "layers", byid[k]["file"]))
        S_[k] = rd(os.path.join(P2, "layers", byid[k + "-shadow"]["file"]))


def lab(x):
    return cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]


res = {}
below = base.copy()
for k in order:
    a = L_[k][..., 3:4] / 255
    with_sh = below * S_[k] / 255
    over = with_sh * (1 - a) + L_[k][..., :3] * a
    A = L_[k][..., 3]
    core = (A == 255).astype(np.uint8)
    dist = cv2.distanceTransform(1 - core, cv2.DIST_L2, 5)
    fringe = (A > 0) & (A < 255) & (dist > 2)
    dL = lab(over) - lab(with_sh)          # the product's own pixels vs the room under it (shadow kept on both sides)
    li, dk = fringe & (dL > 3), fringe & (dL < -3)
    rec = dict(fringe_px=int(fringe.sum()), lighter_px=int(li.sum()), darker_px=int(dk.sum()),
               lighter_reach_p95_px=round(float(np.percentile(dist[li], 95)), 1) if li.any() else 0,
               darker_reach_p95_px=round(float(np.percentile(dist[dk], 95)), 1) if dk.any() else 0,
               lighter_mean_dL=round(float(dL[li].mean()), 1) if li.any() else 0, darker_mean_dL=round(float(dL[dk].mean()), 1) if dk.any() else 0,
               lighter_beyond_4px=int((li & (dist > 4)).sum()), darker_beyond_4px=int((dk & (dist > 4)).sum()),
               fringe_reach_max_px=round(float(dist[A > 0].max()), 1))
    res[k] = rec
    print(k, rec)
    if li.sum() + dk.sum() > 50:
        ys, xs = np.nonzero(A > 0)
        x0, x1, y0, y1 = max(0, xs.min() - 20), min(2720, xs.max() + 20), max(0, ys.min() - 20), min(1530, ys.max() + 20)
        v = over[y0:y1, x0:x1].copy()
        v[li[y0:y1, x0:x1]] = (255, 0, 0)
        v[dk[y0:y1, x0:x1]] = (0, 80, 255)
        im = Image.fromarray(v.astype(np.uint8))
        if im.width > 1400:
            im = im.resize((1400, int(im.height * 1400 / im.width)))
        im.save(os.path.join(OUT, "overlays", f"haze-{k}.jpg"), quality=92)
    below = over
json.dump(res, open(os.path.join(OUT, "data/haze.json"), "w"), indent=1)
