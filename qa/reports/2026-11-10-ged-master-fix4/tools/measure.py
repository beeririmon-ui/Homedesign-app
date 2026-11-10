"""
qa-agent 2026-11-10: MB1 round 3 measurements: the warm-modern milk-tea lumbar's lit face (top 15 % L*) against the natural-linen duvet in
the same light (MB1's patches), as in MB1 (data/lumbar.json there: MB-A lumbar -3.2 L*, b* +2.1 against the duvet), and the Nordic white
lumbar likewise; plus the Nordic chair cloth's Lab (fix4) against the throw. Usage: ~/.venvs/motion/bin/python -I measure.py. Writes data/measure.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lit(a, b, q=85):
    v = lab(a[b[1]:b[3], b[0]:b[2]].reshape(-1, 3).astype(float))
    t = v[v[:, 0] >= np.percentile(v[:, 0], q)]
    m = np.median(t, 0)
    return [round(float(x), 1) for x in m]


def med(a, b):
    v = lab(a[b[1]:b[3], b[0]:b[2]].reshape(-1, 3).astype(float))
    m = np.median(v, 0)
    return [round(float(x), 1) for x in m] + [round(float(np.hypot(m[1], m[2])), 1), round(float(np.degrees(np.arctan2(m[2], m[1]))), 1)]


w = np.asarray(Image.open(os.path.join(B, "warm-modern/warm-modern-MB-A-fix3.png")).convert("RGB"))
n = np.asarray(Image.open(os.path.join(B, "nordic/nordic-MB-A-fix4.png")).convert("RGB"))
out = {"warm-modern": {"lumbar": lit(w, (1870, 830, 2190, 915)), "duvet": lit(w, (1200, 960, 1800, 1080))},
       "nordic": {"lumbar": lit(n, (1680, 770, 1975, 870)), "duvet": lit(n, (800, 1200, 1200, 1320)),
                  "chair cloth": med(n, (40, 800, 280, 1120)), "throw": med(n, (1400, 1280, 2200, 1440))}}
for k in ("warm-modern", "nordic"):
    out[k]["lumbar_minus_duvet"] = [round(out[k]["lumbar"][i] - out[k]["duvet"][i], 1) for i in range(3)]
out["mb_a_reference"] = {"warm-modern lumbar_minus_duvet": [-3.2, 0.0, 2.1], "nordic lumbar_minus_duvet": [-2.9, -1.2, -1.4]}
json.dump(out, open(os.path.join(OUT, "data", "measure.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
