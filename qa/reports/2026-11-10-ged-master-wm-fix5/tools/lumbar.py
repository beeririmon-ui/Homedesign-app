"""
qa-agent 2026-11-10: the bouclé lumbar on fix4 -> fix5, with QA's own mask (not render-agent's protect): the cream bouclé by its brightness
and hue inside the lumbar's box (left edge x ~1860-1869, right edge ~2210-2228, top ~805, the contact with the duvet ~928, read from
fix4's edge profiles), holes filled. Counts the changed px inside it and in rings 1-8 px round it, and the lumbar's lit-face Lab before
and after. Usage: ~/.venvs/motion/bin/python -I lumbar.py. Writes data/lumbar.json.
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
H, W = f4.shape[:2]
d = np.abs(f5 - f4).max(2)
Y = f4.mean(2)
r, g, b = f4[..., 0], f4[..., 1], f4[..., 2]
box = np.zeros((H, W), bool)
box[798:929, 1850:2236] = True
# cream: bright, and red not far above green (the caramel is r - g > 45 at these levels)
m = box & (Y > 72) & ((r - g) < 0.28 * Y + 8)
m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, lbl, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
m = (lbl == k).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
ff = m.copy()
cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
lum = (m | (1 - ff)).astype(bool) & box
ys, xs = np.nonzero(lum)
out = dict(px=int(lum.sum()), box=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], changed_gt0_inside=int(((d > 0) & lum).sum()),
           max_change_inside=int(d[lum].max()))
for rr in (1, 2, 3, 5, 8):
    ring = cv2.dilate(lum.astype(np.uint8), np.ones((2 * rr + 1, 2 * rr + 1), np.uint8)).astype(bool) & ~lum
    out[f"ring_{rr}px"] = dict(px=int(ring.sum()), changed_gt0=int(((d > 0) & ring).sum()), changed_gt2=int(((d > 2) & ring).sum()))
# which side of the lumbar the ring changes sit on
ring3 = cv2.dilate(lum.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~lum & (d > 2)
yy, xx = np.nonzero(ring3)
out["ring_3px_changed_by_side"] = dict(left=int((xx < 1880).sum()), right=int((xx > 2200).sum()),
                                       top=int(((xx >= 1880) & (xx <= 2200) & (yy < 860)).sum()), bottom=int(((xx >= 1880) & (xx <= 2200) & (yy >= 860)).sum()))
Image.fromarray(lum.astype(np.uint8) * 255).save(os.path.join(OUT, "data", "qa-lumbar-mask.png"))
json.dump(out, open(os.path.join(OUT, "data", "lumbar.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
