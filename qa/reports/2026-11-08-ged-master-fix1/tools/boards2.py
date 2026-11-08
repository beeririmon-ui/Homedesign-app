"""
qa-agent 2026-11-08: boards.py again, on clean original boards: the MB-A frame (the wall's geometry is the same in fix1; MB-A's boards
under the sconces were never filled), band y 505-560 (below MB-A's right sconce, above the dried stem and the pillows), x 1560-2736 (right
of MB-A's left sconce). Pitches 22-50 px only (a missed groove doubles the pitch), Theil-Sen fit of pitch against x.
The board pitch is proportional to px per cm on the wall plane, so pitch(x_object) / pitch(x_pillowcase) scales QA's pillowcase basis
(6.08 px/cm at the right pillowcase, x 1940-2390, centre 2165) to the objects' x on the same wall.
Usage: ~/.venvs/motion/bin/python -I boards2.py. Writes data/boards2.json and overlays/boards2-grooves.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A.png")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1")
im = np.asarray(Image.open(B).convert("L")).astype(float)
y0, y1, x0, x1 = 505, 560, 1560, 2736
prof = im[y0:y1, x0:x1].mean(0)
hp = prof - cv2.GaussianBlur(prof.reshape(1, -1), (0, 0), 12).ravel()
mins = [i for i in range(10, len(hp) - 10) if hp[i] == hp[i - 10:i + 11].min() and hp[i] < -2.0]
xs = np.array(mins) + x0
pitch = np.diff(xs).astype(float)
mid = (xs[:-1] + xs[1:]) / 2
k = (pitch >= 22) & (pitch <= 50)
m, p = mid[k], pitch[k]
sl = [(p[j] - p[i]) / (m[j] - m[i]) for i in range(len(m)) for j in range(i + 1, len(m)) if m[j] - m[i] > 60]
slope = float(np.median(sl))
icpt = float(np.median(p - slope * m))
f = lambda x: slope * x + icpt  # noqa: E731
out = dict(band=[y0, y1, x0, x1], grooves=xs.tolist(), pitches=[[float(a), float(b)] for a, b in zip(m, p)], theil_sen=[round(slope, 5), round(icpt, 2)],
           pitch_at={"pillowcase_2165": round(f(2165), 1), "bottle_2505": round(f(2505), 1), "holders_2630": round(f(2630), 1), "sconce_right_2566": round(f(2566), 1)},
           ratio_vs_pillowcase={"bottle": round(f(2505) / f(2165), 3), "holders": round(f(2630) / f(2165), 3), "sconce_right": round(f(2566) / f(2165), 3)},
           local_medians={"x 2050-2280": float(np.median(p[(m > 2050) & (m < 2280)])), "x 2420-2736": float(np.median(p[(m > 2420)]))})
json.dump(out, open(os.path.join(OUT, "data", "boards2.json"), "w"), indent=1)
print(json.dumps({kk: vv for kk, vv in out.items() if kk not in ("grooves",)}, indent=1))
o = Image.open(B).convert("RGB").crop((1540, 420, 2736, 640))
d = ImageDraw.Draw(o)
for x in xs:
    d.line([(x - 1540, y0 - 420), (x - 1540, y1 - 420)], fill=(255, 0, 0), width=2)
o.save(os.path.join(OUT, "overlays", "boards2-grooves.jpg"), quality=88)
