"""
qa-agent 2026-11-10: deviation 1, the gap between the caramel pillowcases (fix5 = seedream's). Per row (y 700-812), the run across
x 1985-2075: the dark slit(s) (L* < 20) and the cream band (L* > 35) - widths and positions, to see one continuous slit + band + slit with
no doubled or stepped edge; the band's grain (L* high-pass SD, sigma 1.6) against the cream back pillow above the pillowcases; the
old spot box (x 2030-2060, y 770-812, the fix3/fix4 spot) L* median.
Usage: ~/.venvs/motion/bin/python -I gap.py. Writes data/gap.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")


def Lstar(p):
    c = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def runs(mask, x0):
    xs = np.nonzero(mask)[0]
    if not xs.size:
        return []
    out, s, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - p > 1:
            out.append([int(x0 + s), int(x0 + p)])
            s = x
        p = x
    out.append([int(x0 + s), int(x0 + p)])
    return [r for r in out if r[1] - r[0] >= 1]


res = {}
for k in ("fix4", "fix5"):
    L = Lstar(os.path.join(B, f"warm-modern-MB-A-{k}.png"))
    hp = L - cv2.GaussianBlur(L, (0, 0), 1.6)
    rows = {}
    for y in range(704, 813, 12):
        seg = L[y, 1985:2075]
        rows[y] = dict(dark_lt20=runs(seg < 20, 1985), cream_gt35=runs(seg > 35, 1985))
    band = (L[715:800, 1995:2060] > 35)
    res[k] = dict(rows=rows, spot_box_L_median=round(float(np.median(L[770:812, 2030:2060])), 1),
                  band_grain=round(float(hp[715:800, 1995:2060][band].std()), 2) if band.any() else None,
                  back_pillow_grain=round(float(hp[682:700, 1600:1760].std()), 2),
                  spot_box_grain=round(float(hp[770:812, 2030:2060].std()), 2),
                  spot_box_L_p10_p90=[round(float(np.percentile(L[770:812, 2030:2060], q)), 1) for q in (10, 90)])
json.dump(res, open(os.path.join(OUT, "data", "gap.json"), "w"), indent=1)
for y in res["fix5"]["rows"]:
    print(y, "fix4", res["fix4"]["rows"][y], "\n    fix5", res["fix5"]["rows"][y])
print({k: (v["spot_box_L_median"], v["spot_box_grain"], v["spot_box_L_p10_p90"], v["band_grain"], v["back_pillow_grain"]) for k, v in res.items()})
