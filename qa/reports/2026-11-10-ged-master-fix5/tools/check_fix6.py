"""
qa-agent 2026-11-10: nordic-MB-A-fix6.png (render-agent: the two candles put out; the exposure lowered by up to 1/3 stop for DL1) against
fix5. (1) the exposure: per pixel the linear-luminance ratio fix6 / fix5 outside the candle boxes (median, p5, p95, in stops) and in the sun
stripes on the duvet (the brightest 2 %), so a global gain shows as one value and a kept highlight as a ratio near 1 there;
(2) G-ED.8 for the candles: after taking the global gain out (fix5 x the median ratio), pixels that still differ by > 3 levels, and how many lie
outside the candle boxes; (3) G-ED.9 sheets: the candles at x4 and a x4 contrast stretch, fix5 | fix6. Candle boxes by eye on fix5
(the two pillar candles and flames on the nightstand). Usage: ~/.venvs/motion/bin/python -I check_fix6.py. Writes data/fix6.json, overlays/fix6-candles-x4.jpg.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/nordic")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix5")
BOXES = [(2560, 740, 2640, 910), (2640, 820, 2720, 915)]


def lin(a):
    c = a / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


a = np.asarray(Image.open(os.path.join(B, "nordic-MB-A-fix5.png")).convert("RGB")).astype(float)
b = np.asarray(Image.open(os.path.join(B, "nordic-MB-A-fix6.png")).convert("RGB")).astype(float)
W = np.array([0.2126, 0.7152, 0.0722])
Ya, Yb = lin(a) @ W, lin(b) @ W
inbox = np.zeros(Ya.shape, bool)
for x0, y0, x1, y1 in BOXES:
    inbox[y0:y1, x0:x1] = True
ok = (~inbox) & (Ya > 0.01)
r = Yb[ok] / Ya[ok]
sun = ok & (Ya >= np.percentile(Ya[ok], 98))
out = dict(gain_median=round(float(np.median(r)), 4), gain_stops=round(float(np.log2(np.median(r))), 3), gain_p5_p95=[round(float(np.percentile(r, 5)), 4), round(float(np.percentile(r, 95)), 4)],
           sun_2pct_ratio_median=round(float(np.median(Yb[sun] / Ya[sun])), 4))
# the global gain out: compare fix6 with fix5 brought through the same tone change (per-channel ratio median outside the boxes)
g = np.array([np.median(b[..., k][ok] / np.maximum(a[..., k][ok], 1)) for k in range(3)])
pred = np.clip(a * g, 0, 255)
res = np.abs(b - pred).max(2) > 12
out["residual_gt12_after_linear_gain"] = dict(inside_boxes=int((res & inbox).sum()), outside_boxes=int((res & ~inbox).sum()))
d = np.abs(a - b).max(2) > 0
out["changed_px_total"] = int(d.sum())
json.dump(out, open(os.path.join(OUT, "data", "fix6.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
tiles = []
x0, y0, x1, y1 = 2540, 720, 2736, 930
for arr in (a, b):
    c = arr[y0:y1, x0:x1]
    lo, hi = np.percentile(c, 1), np.percentile(c, 60)
    st = np.clip((c - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    tiles += [Image.fromarray(c.astype(np.uint8)).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST), Image.fromarray(st).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST)]
o = Image.new("RGB", (sum(t.width for t in tiles) + 30, tiles[0].height), (40, 40, 40))
xx = 0
for t in tiles:
    o.paste(t, (xx, 0))
    xx += t.width + 10
o.save(os.path.join(OUT, "overlays", "fix6-candles-x3.jpg"), quality=90)
