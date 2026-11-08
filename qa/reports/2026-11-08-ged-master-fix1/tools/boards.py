"""
qa-agent 2026-11-08: the Nordic headboard wall's own perspective scale, from its vertical boards (equal widths by construction): the board
grooves (dark minima of the column profile of a band just below the cap rail, rows y0-y1, on the fix1 frame), the local pitch in px as a
function of x, and the pitch's ratio between the nightstand's x and the right pillowcase's x. The ratio is the nightstand plane's px/cm
against the pillowcase basis (6.08 px/cm at x 2165), both measured on the same wall plane.
Usage: ~/.venvs/motion/bin/python -I boards.py. Writes data/boards.json and overlays/boards-grooves.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A-fix1.png")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1")
im = np.asarray(Image.open(B).convert("L")).astype(float)
res = {}
for name, (y0, y1, x0, x1) in {"band_545_575": (545, 575, 1330, 2736), "band_520_545": (520, 545, 1330, 2736)}.items():
    prof = im[y0:y1, x0:x1].mean(0)
    hp = prof - cv2.GaussianBlur(prof.reshape(1, -1), (0, 0), 12).ravel()
    # minima: local min over +-12 px and at least 2.5 levels below the smooth profile
    mins = [i for i in range(12, len(hp) - 12) if hp[i] == hp[i - 12:i + 13].min() and hp[i] < -2.5]
    xs = np.array(mins) + x0
    pitch = np.diff(xs)
    mid = (xs[:-1] + xs[1:]) / 2
    keep = (pitch > 25) & (pitch < 120)
    res[name] = dict(grooves=xs.tolist(), pitches=[[float(m), int(p)] for m, p in zip(mid[keep], pitch[keep])])
    if keep.sum() >= 4:
        A = np.vstack([mid[keep], np.ones(keep.sum())]).T
        k, c = np.linalg.lstsq(A, pitch[keep], rcond=None)[0]
        res[name]["fit_pitch_vs_x"] = [round(float(k), 5), round(float(c), 2)]
        p = lambda x: k * x + c  # noqa: E731
        res[name]["pitch_at_pillow_2165"] = round(float(p(2165)), 1)
        res[name]["pitch_at_bottle_2505"] = round(float(p(2505)), 1)
        res[name]["pitch_at_holders_2630"] = round(float(p(2630)), 1)
        res[name]["scale_ratio_bottle_vs_pillow"] = round(float(p(2505) / p(2165)), 3)
        res[name]["scale_ratio_holders_vs_pillow"] = round(float(p(2630) / p(2165)), 3)
json.dump(res, open(os.path.join(OUT, "data", "boards.json"), "w"), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("grooves",)} for k, v in res.items()}, indent=1)[:3000])
o = Image.open(B).convert("RGB").crop((1300, 380, 2736, 720))
d = ImageDraw.Draw(o)
for x in res["band_545_575"]["grooves"]:
    d.line([(x - 1300, 545 - 380), (x - 1300, 575 - 380)], fill=(255, 0, 0), width=2)
o.save(os.path.join(OUT, "overlays", "boards-grooves.jpg"), quality=88)
