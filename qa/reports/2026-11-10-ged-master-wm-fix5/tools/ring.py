"""
qa-agent 2026-11-10: deviation 2, the 12 px ring on the cream back pillows above the caramel pillowcases (fix5). Per column (every 4 px),
from the comp mask's top edge: L* and grain (high-pass SD, sigma 1.6, as in the fix5 gap check) of the back pillow 3-12 px ABOVE the mask
edge (fix4 = fix5 there) against the ring 3-10 px BELOW it (seedream's), and the step across the edge (L* 2 px below minus 2 px above).
Also the same for the gap band. Usage: ~/.venvs/motion/bin/python -I ring.py. Writes data/ring.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")


def lab(x8):
    c = x8 / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


f4 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix4.png")).convert("RGB")).astype(float)
f5 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix5.png")).convert("RGB")).astype(float)
comp = np.asarray(Image.open(os.path.join(B, "raw/P6b-comp-mask.png"))) > 127
L4, L5 = lab(f4)[..., 0], lab(f5)[..., 0]
hp5 = L5 - cv2.GaussianBlur(L5, (0, 0), 1.6)
hp4 = L4 - cv2.GaussianBlur(L4, (0, 0), 1.6)
out = {}
for name, xs in (("left pillowcase top", range(1560, 1960, 4)), ("right pillowcase top", range(2080, 2440, 4))):
    above, ring, step, g_above, g_ring, g4_old = [], [], [], [], [], []
    for x in xs:
        col = np.nonzero(comp[640:800, x])[0]
        if not col.size:
            continue
        t = 640 + int(col.min())
        above.append(L5[t - 12:t - 3, x].mean())
        ring.append(L5[t + 3:t + 10, x].mean())
        step.append(L5[t + 2, x] - L5[t - 2, x])
        g_above.append(hp5[t - 12:t - 3, x].std())
        g_ring.append(hp5[t + 3:t + 10, x].std())
        g4_old.append(hp4[t + 3:t + 10, x].std())
    out[name] = dict(columns=len(above), back_pillow_above_L=round(float(np.median(above)), 1), ring_L=round(float(np.median(ring)), 1),
                     ring_minus_above_L_p10_p50_p90=[round(float(np.percentile(np.subtract(ring, above), q)), 1) for q in (10, 50, 90)],
                     step_across_edge_L_p50_p90=[round(float(np.percentile(step, q)), 1) for q in (50, 90)],
                     grain_above=round(float(np.median(g_above)), 2), grain_ring=round(float(np.median(g_ring)), 2),
                     grain_same_px_fix4=round(float(np.median(g4_old)), 2))
json.dump(out, open(os.path.join(OUT, "data", "ring.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
