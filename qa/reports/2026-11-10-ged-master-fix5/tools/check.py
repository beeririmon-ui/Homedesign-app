"""
qa-agent 2026-11-10: G-ED.8 and G-ED.9 on render-agent's two 0-token fixes (mb1-fix5.json): nordic-MB-A-fix5.png against fix4 and
warm-modern-MB-A-fix4.png against fix3. (1) changed pixels (> 0 and > 2 levels) and their bounding box against the declared region;
(2) the repaired patch against its surroundings: L* median and grain (high-pass sd, sigma 1.6) inside vs a 12 px ring outside;
(3) sheets: before | after at 100 %, x4 NEAREST and a x4 contrast stretch (percentiles 1-60).
Usage: ~/.venvs/motion/bin/python -I check.py. Writes data/check.json and overlays/{nordic-wedge,wm-gap}-x4.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix5")


def Lstar(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


out = {}
for name, sub, a, b, box in (("nordic-wedge", "nordic", "nordic-MB-A-fix4.png", "nordic-MB-A-fix5.png", (1540, 750, 1700, 890)),
                             ("wm-gap", "warm-modern", "warm-modern-MB-A-fix3.png", "warm-modern-MB-A-fix4.png", (1980, 730, 2110, 850))):
    x = np.asarray(Image.open(os.path.join(B, sub, a)).convert("RGB")).astype(int)
    y = np.asarray(Image.open(os.path.join(B, sub, b)).convert("RGB")).astype(int)
    d0 = np.abs(x - y).max(2) > 0
    d2 = np.abs(x - y).max(2) > 2
    ys, xs = np.nonzero(d0)
    m = d0.astype(np.uint8)
    ring = (cv2.dilate(m, np.ones((25, 25), np.uint8)) > 0) & ~d0
    L = Lstar(y.astype(float)).astype(np.float32)
    hp = L - cv2.GaussianBlur(L, (0, 0), 1.6)
    out[name] = dict(changed_px=int(d0.sum()), changed_gt2=int(d2.sum()), bbox=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
                     L_patch=round(float(np.median(L[d0])), 1), L_ring=round(float(np.median(L[ring])), 1),
                     grain_patch=round(float(hp[d0].std()), 2), grain_ring=round(float(hp[ring].std()), 2))
    tiles = []
    for arr in (x, y):
        c = arr[box[1]:box[3], box[0]:box[2]].astype(float)
        lo, hi = np.percentile(c, 1), np.percentile(c, 60)
        st = np.clip((c - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
        w, h = box[2] - box[0], box[3] - box[1]
        tiles += [Image.fromarray(c.astype(np.uint8)).resize((w * 4, h * 4), Image.NEAREST), Image.fromarray(st).resize((w * 4, h * 4), Image.NEAREST)]
    o = Image.new("RGB", (sum(t.width for t in tiles) + 30, tiles[0].height), (40, 40, 40))
    xx = 0
    for t in tiles:
        o.paste(t, (xx, 0))
        xx += t.width + 10
    o.save(os.path.join(OUT, "overlays", f"{name}-x4.jpg"), quality=90)
    ctx = (box[0] - 300, box[1] - 150, box[2] + 300, box[3] + 120)
    Image.fromarray(y.astype(np.uint8)[ctx[1]:ctx[3], ctx[0]:ctx[2]]).save(os.path.join(OUT, "overlays", f"{name}-context-100.jpg"), quality=90)
json.dump(out, open(os.path.join(OUT, "data", "check.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
