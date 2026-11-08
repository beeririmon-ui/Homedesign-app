"""
qa-agent 2026-11-08: MB1 fix1 measurements.
(1) G-ED.3 colour on the changed products (Lab median and lit face, top 15 % L*, on patches by eye) against the same-light neutral
    (Nordic: the white panelling in shade; warm modern: the plaster by the bed) and the SKU photos (scratchpad master-refs/, view only):
    the Nordic throw, the chair cloth (G-ED.6: is it now too close to the throw?), the planter, the sill vase, the bottle, the holders.
(2) the warm-modern wall's perspective: the pill niche's height near its left and right ends (column profiles of the niche's top and bottom
    edges), so the scale at the nightstand's x is read on the wall itself.
Usage: ~/.venvs/motion/bin/python -I measure.py. Writes data/measure.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/master-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def stat(v):
    m = np.median(v, 0)
    t = np.median(v[v[:, 0] >= np.percentile(v[:, 0], 85)], 0)
    f = lambda q: [round(float(q[0]), 1), round(float(q[1]), 1), round(float(q[2]), 1), round(float(np.hypot(q[1], q[2])), 1), round(float(np.degrees(np.arctan2(q[2], q[1]))), 1)]  # noqa: E731
    return dict(median=f(m), lit=f(t))


def patch(arr, b):
    return stat(lab(arr[b[1]:b[3], b[0]:b[2]].reshape(-1, 3).astype(float)))


def ref(n):
    a = lab(np.asarray(Image.open(REF + n).convert("RGB")).astype(float))
    H, W = a.shape[:2]
    return stat(a[H // 3:2 * H // 3, W // 3:2 * W // 3].reshape(-1, 3))


n = np.asarray(Image.open(os.path.join(B, "nordic/nordic-MB-A-fix1.png")).convert("RGB"))
w = np.asarray(Image.open(os.path.join(B, "warm-modern/warm-modern-MB-A-fix1.png")).convert("RGB"))
out = {"nordic": {"neutral: white panelling (shade)": patch(n, (1800, 340, 2000, 560)), "throw (P1)": patch(n, (1400, 1280, 2200, 1440)),
                  "throw (P1), unlit fold": patch(n, (1000, 1380, 1400, 1520)), "chair cloth (code)": patch(n, (40, 800, 280, 1120)),
                  "planter (code)": patch(n, (800, 770, 920, 900)), "jute basket": patch(n, (670, 830, 800, 960)), "sill vase (P3)": patch(n, (345, 600, 405, 720)),
                  "bottle (P2)": patch(n, (2470, 800, 2545, 930)), "candle holder (P2)": patch(n, (2575, 905, 2620, 975))},
       "warm-modern": {"neutral: plaster by the bed": patch(w, (1600, 580, 1800, 640)), "bottle (P4)": patch(w, (1235, 820, 1300, 930)),
                       "candle holder (P4)": patch(w, (1095, 870, 1130, 930))},
       "refs": {k: ref(v) for k, v in {"throw light grey": "crop_throw_lightgray.png", "planter seagrass": "crop_planter_seagrass.png", "clay vase": "crop_claysvase.png",
                                       "bottle D": "crop_vaseD.png", "candle holders": "crop_candles.png"}.items()}}
c, t = out["nordic"]["chair cloth (code)"]["median"], out["nordic"]["throw (P1)"]["median"]
out["nordic"]["chair_cloth_vs_throw"] = dict(dL=round(c[0] - t[0], 1), dC=round(c[3] - t[3], 1), dh=round(c[4] - t[4], 1),
                                            dE76=round(float(np.linalg.norm(np.array(c[:3]) - np.array(t[:3]))), 1))
# the niche: its top and bottom edges (strongest vertical gradients) per column, near both ends of the straight part
g = cv2.GaussianBlur(lab(w.astype(float))[..., 0].astype(np.float32), (0, 0), 2)
gy = np.diff(g, axis=0)
hts = {}
for x in (1560, 1600, 1640, 2360, 2400, 2440):
    col = gy[200:560, x]
    top = 200 + int(np.argmax(np.abs(col[:120])))           # the top edge in rows 200-320
    bot = 200 + 200 + int(np.argmax(np.abs(col[200:])))     # the bottom edge in rows 400-560
    hts[x] = [top, bot, bot - top]
out["warm-modern"]["niche_heights_px"] = hts
L = np.mean([hts[x][2] for x in (1560, 1600, 1640)])
R = np.mean([hts[x][2] for x in (2360, 2400, 2440)])
slope = (R / L - 1) / (2400 - 1600)
s = lambda x: 1 + slope * (x - 1600)  # noqa: E731
out["warm-modern"]["niche_scale"] = dict(left_mean=round(float(L), 1), right_mean=round(float(R), 1), ratio_right_left=round(float(R / L), 3),
                                         scale_at_nightstand_1240_vs_pillowcase_1745=round(float(s(1240) / s(1745)), 3),
                                         scale_at_sconce_1267_vs_pillowcase_1745=round(float(s(1267) / s(1745)), 3))
json.dump(out, open(os.path.join(OUT, "data", "measure.json"), "w"), indent=1, ensure_ascii=False)
for k in ("nordic", "warm-modern"):
    for kk, vv in out[k].items():
        print(k, kk, vv)
for kk, vv in out["refs"].items():
    print("ref", kk, vv)
