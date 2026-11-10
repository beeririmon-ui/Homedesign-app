"""
qa-agent 2026-11-10: deviation 3, the lumbar's cast shadow on the right pillowcase, fix4 against fix5. Per row (y 820-925), from the
lumbar's right edge (QA's lumbar mask): the run of L* < 14 (render-agent's threshold) and of L* < 18, its outer x, and the box mean L*
over x 2210-2330 (shadow + the lit pillowcase beside it). Also the lumbar's own lit-face width per row, for the geometry.
Usage: ~/.venvs/motion/bin/python -I cast_shadow.py. Writes data/cast-shadow.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
lum = np.asarray(Image.open(os.path.join(OUT, "data/qa-lumbar-mask.png"))) > 127


def Lstar(p):
    c = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


out = {}
for k in ("fix4", "fix5"):
    L = Lstar(os.path.join(B, f"warm-modern-MB-A-{k}.png"))
    rows = {}
    for y in range(820, 926, 10):
        xe = int(np.nonzero(lum[y])[0].max()) + 1
        seg = L[y, xe:xe + 160]
        run14 = int(np.argmax(seg >= 14)) if (seg >= 14).any() else 160
        lt14 = int((seg < 14).sum())
        lt18 = int((seg < 18).sum())
        rows[y] = dict(lumbar_right_edge=xe, contiguous_lt14_from_edge=run14, px_lt14=lt14, px_lt18=lt18)
    out[k] = dict(rows=rows, box_mean_L_2210_2330_y820_925=round(float(L[820:925, 2210:2330].mean()), 1),
                  box_median_L=round(float(np.median(L[820:925, 2210:2330])), 1))
json.dump(out, open(os.path.join(OUT, "data", "cast-shadow.json"), "w"), indent=1)
for y in out["fix4"]["rows"]:
    a, b = out["fix4"]["rows"][y], out["fix5"]["rows"][y]
    print(y, "edge", a["lumbar_right_edge"], "lt14", a["px_lt14"], "->", b["px_lt14"], " lt18", a["px_lt18"], "->", b["px_lt18"])
print({k: (v["box_mean_L_2210_2330_y820_925"], v["box_median_L"]) for k, v in out.items()})
