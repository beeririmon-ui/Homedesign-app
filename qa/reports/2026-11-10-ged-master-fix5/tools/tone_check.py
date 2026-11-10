"""
qa-agent 2026-11-10: G-ED.8 for fix6 when the exposure change is global: outside the candle boxes, is fix6 a function of fix5's own
luminance only (one tone curve for the whole frame, the same gain on R, G and B)? The gain Y6/Y5 binned by fix5's L* (0.5 L* bins, the
bin's median = the curve); per pixel the predicted fix6 = fix5 x curve(L*5) in linear light, back to sRGB; the residual > 3 levels inside and
outside the candle boxes; and the channel balance (the per-pixel spread of the R, G, B gains). Usage: ~/.venvs/motion/bin/python -I tone_check.py.
Writes data/tone-check.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/nordic")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix5")
BOXES = [(2575, 745, 2630, 910), (2652, 800, 2706, 912)]


def lin(a):
    c = a / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def srgb(l):
    return np.where(l > 0.0031308, 1.055 * np.power(np.clip(l, 0, None), 1 / 2.4) - 0.055, 12.92 * l) * 255


a = np.asarray(Image.open(os.path.join(B, "nordic-MB-A-fix5.png")).convert("RGB")).astype(float)
b = np.asarray(Image.open(os.path.join(B, "nordic-MB-A-fix6.png")).convert("RGB")).astype(float)
la, lb = lin(a), lin(b)
W = np.array([0.2126, 0.7152, 0.0722])
Ya, Yb = la @ W, lb @ W
La = np.where(Ya > 0.008856, 116 * np.cbrt(Ya) - 16, 903.3 * Ya)
inbox = np.zeros(Ya.shape, bool)
for x0, y0, x1, y1 in BOXES:
    inbox[y0:y1, x0:x1] = True
ok = (~inbox) & (Ya > 0.002)
bins = np.clip((La * 2).astype(int), 0, 200)
g = np.ones(201)
for k in range(201):
    s = ok & (bins == k)
    if s.sum() > 50:
        g[k] = np.median(Yb[s] / Ya[s])
pred = srgb(la * g[bins][..., None])
res = np.abs(pred - b).max(2)
ch = lb[ok] / np.maximum(la[ok], 1e-4)
spread = ch.max(1) - ch.min(1)
out = dict(curve_L_gain={str(k / 2): round(float(g[k]), 3) for k in range(0, 201, 20)},
           residual_gt3_outside_boxes=int(((res > 3) & ~inbox).sum()), residual_gt3_inside_boxes=int(((res > 3) & inbox).sum()),
           residual_p999_outside=round(float(np.percentile(res[~inbox], 99.9)), 2),
           channel_gain_spread_p99=round(float(np.percentile(spread[la[ok].min(1) > 0.01], 99)), 4))
json.dump(out, open(os.path.join(OUT, "data", "tone-check.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
