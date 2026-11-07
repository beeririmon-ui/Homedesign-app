"""
qa-agent 2026-11-07: boho-A-fin7 (render-agent's 0-token recolour of the planter's black-dipped base to natural seagrass, fin7-planter.json)
against fin6. (1) the change: pixels changed, bounding box; (2) Lab of the recoloured base (changed pixels) against the planter's body band
just above it (the 25 px above the change, inside the planter's columns), fin6 and fin7; the base/body L ratio; the weave's texture
(high-frequency L* sd, sigma 4) in the base and the body; (3) the seam: the L* and b* step across the old dip line (5 px above vs 5 px
below, per column); (4) crops: 100 % fin6 | fin7 | the card's cached gallery photo, and x4 of the seam and the base's bottom edge.
Usage: ~/.venvs/motion/bin/python -I check_fin7.py. Writes data/fin7.json and overlays/fin7-planter-100-x4.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r4")
CARD = os.path.join(REPO, "assets/renders/house-nordic-2026-10-25/refs/-com-products-83-7e-a75cb5e948b7b3280683b19ab275-import-webp.jpg")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


ra = np.asarray(Image.open(os.path.join(E, "boho-A-fin6.png")).convert("RGB"))
rb = np.asarray(Image.open(os.path.join(E, "boho-A-fin7.png")).convert("RGB"))
d = np.abs(ra.astype(int) - rb.astype(int)).max(2) > 0
ys, xs = np.nonzero(d)
a, b = lab(ra.astype(float)), lab(rb.astype(float))
top = np.full(d.shape[1], -1)
for x in range(xs.min(), xs.max() + 1):
    col = np.nonzero(d[:, x])[0]
    if len(col):
        top[x] = col.min()
body = np.zeros(d.shape, bool)
seam_L, seam_b = [], []
for x in range(xs.min() + 3, xs.max() - 2):
    t = top[x]
    if t < 0:
        continue
    body[max(0, t - 25):t - 2, x] = True
    seam_L.append(float(b[t + 2:t + 7, x, 0].mean() - b[t - 6:t - 1, x, 0].mean()))
    seam_b.append(float(b[t + 2:t + 7, x, 2].mean() - b[t - 6:t - 1, x, 2].mean()))
Lb = b[..., 0].astype(np.float32)
hf = Lb - cv2.GaussianBlur(Lb, (0, 0), 4)
out = dict(changed_px=int(d.sum()), bbox=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
           base_fin6=[round(float(v), 1) for v in np.median(a[d], 0)], base_fin7=[round(float(v), 1) for v in np.median(b[d], 0)],
           body_band_fin7=[round(float(v), 1) for v in np.median(b[body], 0)],
           base_over_body_L=round(float(np.median(b[d][:, 0]) / np.median(b[body][:, 0])), 2),
           hue_ab_base=round(float(np.degrees(np.arctan2(np.median(b[d][:, 2]), np.median(b[d][:, 1])))), 1),
           hue_ab_body=round(float(np.degrees(np.arctan2(np.median(b[body][:, 2]), np.median(b[body][:, 1])))), 1),
           texture_hf_sd_base=round(float(hf[cv2.erode(d.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0].std()), 2),
           texture_hf_sd_body=round(float(hf[body].std()), 2),
           seam_step_L_median=round(float(np.median(seam_L)), 2), seam_step_L_p90_abs=round(float(np.percentile(np.abs(seam_L), 90)), 2),
           seam_step_b_median=round(float(np.median(seam_b)), 2))
json.dump(out, open(os.path.join(OUT, "data", "fin7.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
x0, x1, y0, y1 = out["bbox"]
box = (x0 - 30, y0 - 150, x1 + 30, y1 + 30)
A = Image.fromarray(ra).crop(box)
B = Image.fromarray(rb).crop(box)
card = Image.open(CARD).convert("RGB")
card = card.resize((int(card.width * A.height / card.height), A.height))
xm = (x0 + x1) // 2
t = int(top[xm])
S1 = Image.fromarray(rb).crop((xm - 50, t - 30, xm + 50, t + 30)).resize((400, 240), Image.NEAREST)
S2 = Image.fromarray(rb).crop((xm - 50, y1 - 40, xm + 50, y1 + 20)).resize((400, 240), Image.NEAREST)
W = A.width * 2 + card.width + 400 + 40
o = Image.new("RGB", (W, max(A.height, 490)), (40, 40, 40))
o.paste(A, (0, 0))
o.paste(B, (A.width + 10, 0))
o.paste(card, (2 * A.width + 20, 0))
o.paste(S1, (2 * A.width + card.width + 30, 0))
o.paste(S2, (2 * A.width + card.width + 30, 250))
o.save(os.path.join(OUT, "overlays", "fin7-planter-100-x4.jpg"), quality=90)
