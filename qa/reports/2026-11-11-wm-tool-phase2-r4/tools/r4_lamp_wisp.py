#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the pale wisp on the wall under the floor lamp's shade, left of the stem (rows ~740-790). Is it in the lamp layer
(alpha > 0) and how much lighter than the wall is it? r3 vs r4 (unchanged by R4?), and the raw step-2 render at the same place.
Writes data/floor-lamp-wisp.json and crops/floor-lamp-wisp-*.png.   ~/.venvs/motion/bin/python -I r4_lamp_wisp.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
m3 = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b3 = {l_["id"]: l_ for l_ in m3["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
L4 = np.asarray(Image.open(os.path.join(P2, "layers", b4["floor-lamp"]["file"])))
L3 = np.asarray(Image.open(os.path.join(P2, "layers", b3["floor-lamp"]["file"])))
base = np.asarray(Image.open(os.path.join(P2, "layers/base.png")).convert("RGB"))
S4 = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r4-set-B-graded-v3c.png")).convert("RGB"))
Lab = lambda im: cv2.cvtColor(im.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)  # noqa: E731
y0, y1, x0, x1 = 700, 800, 2380, 2470
a = L4[..., 3]
# the stem: the alpha-255 columns in rows 720-800 that are dark (walnut / brass), the wisp: alpha > 0, not the stem, lighter than the base
dL = Lab(S4)[..., 0] - Lab(base)[..., 0]
box = np.zeros(a.shape, bool)
box[y0:y1, x0:x1] = True
wisp = box & (a > 0) & (dL > 2)
ys, xs = np.nonzero(wisp)
res = dict(box=[x0, y0, x1, y1], wisp_px=int(wisp.sum()),
           wisp_box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if wisp.any() else None,
           dL_vs_base_p50_p95_max=[round(float(np.percentile(dL[wisp], q)), 2) for q in (50, 95, 100)] if wisp.any() else None,
           alpha_in_wisp_p50_max=[int(np.median(a[wisp])), int(a[wisp].max())] if wisp.any() else None,
           same_in_r3_layer=bool((L3[wisp] == L4[wisp]).all()))
json.dump(res, open(os.path.join(OUT, "data/floor-lamp-wisp.json"), "w"), indent=1)
print(res)
c = S4[y0:y1, x0:x1]
cb = base[y0:y1, x0:x1]
am = np.repeat(a[y0:y1, x0:x1, None], 3, 2)
strip = np.concatenate([c, np.full((c.shape[0], 4, 3), 30, np.uint8), cb, np.full((c.shape[0], 4, 3), 30, np.uint8), am], 1)
Image.fromarray(strip).resize((strip.shape[1] * 4, strip.shape[0] * 4), Image.NEAREST).save(os.path.join(OUT, "crops/floor-lamp-wisp-scene-base-alpha-x4.png"))
