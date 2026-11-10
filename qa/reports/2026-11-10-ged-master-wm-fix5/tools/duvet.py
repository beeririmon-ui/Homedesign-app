"""
qa-agent 2026-11-10: the duvet under the bed head, fix4 -> fix5. The contact line per column on fix4: the lowest caramel pixel (the
pillowcases), or the lumbar's lowest pixel in QA's lumbar mask (data/qa-lumbar-mask.png, from lumbar.py) where the lumbar sits in front.
Counts the changed px more than 2 / 4 px below that line (the duvet proper), their levels, and the Lab of the speck pixels against
their neighbours. Usage: ~/.venvs/motion/bin/python -I duvet.py. Writes data/duvet.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
f4 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix4.png")).convert("RGB")).astype(np.int16)
f5 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix5.png")).convert("RGB")).astype(np.int16)
comp = np.asarray(Image.open(os.path.join(B, "raw/P6b-comp-mask.png"))) > 127
lum = np.asarray(Image.open(os.path.join(OUT, "data/qa-lumbar-mask.png"))) > 127
H, W = f4.shape[:2]
d = np.abs(f5 - f4).max(2)
r, g, b = f4[..., 0], f4[..., 1], f4[..., 2]
Y = f4.mean(2)
car = ((r - g) > 0.28 * Y + 8) & (Y < 150)          # caramel / its shadow: red well above green
line = np.full(W, -1)
for x in range(1460, 2680):
    cl = np.nonzero(car[860:1000, x])[0]
    ll = np.nonzero(lum[860:1000, x])[0]
    c = [860 + int(cl.max())] if cl.size else []
    c += [860 + int(ll.max())] if ll.size else []
    if c:
        line[x] = max(c)
out = {}
for off in (2, 4, 8):
    duv = np.zeros((H, W), bool)
    for x in np.nonzero(line >= 0)[0]:
        duv[line[x] + off + 1:1086, x] = True
    ch = (d > 0) & duv
    out[f"below_contact_plus_{off}px"] = dict(changed_gt0=int(ch.sum()), changed_gt2=int(((d > 2) & duv).sum()), changed_gt6=int(((d > 6) & duv).sum()),
                                             max_level=int(d[duv].max()), p99_level_of_changed=(round(float(np.percentile(d[ch], 99)), 1) if ch.any() else 0))
    if ch.any():
        ys, xs = np.nonzero(ch)
        out[f"below_contact_plus_{off}px"]["box"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
# the comp mask's islands on the duvet: components of the mask fully below the contact line + 2
duv2 = np.zeros((H, W), bool)
for x in np.nonzero(line >= 0)[0]:
    duv2[line[x] + 3:1086, x] = True
isl = comp & duv2
n, lbl, st, _ = cv2.connectedComponentsWithStats(isl.astype(np.uint8), connectivity=8)
out["mask_islands_on_duvet"] = dict(count=int(n - 1), px=int(isl.sum()), largest_px=int(st[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0,
                                    mean_abs_level_change=round(float(np.abs(f5 - f4)[isl].mean()), 2) if isl.any() else 0,
                                    max_level_change=int(d[isl].max()) if isl.any() else 0)
out["contact_line_samples"] = {str(x): int(line[x]) for x in range(1500, 2680, 100)}
json.dump(out, open(os.path.join(OUT, "data", "duvet.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
