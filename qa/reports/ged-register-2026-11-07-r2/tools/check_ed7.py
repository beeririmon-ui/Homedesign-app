"""qa-agent 2026-11-07: G-ED on mediterranean-A ed6 -> ed7 (grade-med.json, the regional shade grade).
(1) the sun patches untouched: QA's own sun mask from ed6 (L* > 78 and b* > 18, the window box out; the spec of grade-med) and the
    pixels that changed inside it; (2) the product colours in the shade before / after (G-ED.3 under the new light); (3) crops at the
    sun-mask edges for halos (G-ED.9). G-ED.11 / G-ED.12: qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py (run separately).
Writes data/ed7.json and overlays/ed7-*.jpg. Usage: ~/.venvs/motion/bin/python -I check_ed7.py"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r2")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


a8 = np.asarray(Image.open(os.path.join(R, "mediterranean-A-ed6.png")).convert("RGB"))
b8 = np.asarray(Image.open(os.path.join(R, "mediterranean-A-ed7.png")).convert("RGB"))
A, B = lab(a8.astype(float)), lab(b8.astype(float))
H, W = A.shape[:2]
win = np.zeros((H, W), bool)
win[170:915, 2392:2730] = True
sun = (A[..., 0] > 78) & (A[..., 2] > 18) & ~win
sun = cv2.morphologyEx(sun.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
d = np.abs(a8.astype(int) - b8.astype(int)).max(2)
out = dict(changed_px=int((d > 2).sum()), changed_pct=round(float((d > 2).mean() * 100), 1),
           sun_px=int(sun.sum()), sun_changed_px_over_0=int((d[sun] > 0).sum()), sun_changed_px_over_2=int((d[sun] > 2).sum()),
           window_changed_px_over_2=int((d[win] > 2).sum()))
P = {"white cushion, right (ours)": (1640, 760, 1760, 860), "white cushion, left (bench)": (300, 760, 440, 880), "terracotta cushion": (700, 760, 820, 880),
     "moss lumbar": (1000, 860, 1180, 940), "sofa throw (muslin)": (520, 1080, 700, 1180), "speckled bowl, rim": (1080, 1160, 1180, 1200),
     "seagrass basket": (1960, 1000, 2060, 1100), "travertine candle holder": (1380, 1100, 1420, 1180), "limewash back wall (shade)": (1520, 320, 1700, 520)}
prod = {}
for k, (x0, y0, x1, y1) in P.items():
    prod[k] = dict(ed6=[round(float(v), 1) for v in A[y0:y1, x0:x1].reshape(-1, 3).mean(0)], ed7=[round(float(v), 1) for v in B[y0:y1, x0:x1].reshape(-1, 3).mean(0)])
    prod[k]["d"] = [round(prod[k]["ed7"][i] - prod[k]["ed6"][i], 1) for i in range(3)]
out["products_Lab"] = prod
# the sun patches' edges: the steepest change of the grade weight is where a halo would show; sample |d| in a ring 4-24 px outside the sun
ring = cv2.dilate(sun.astype(np.uint8), np.ones((49, 49), np.uint8)) > 0
ring &= ~(cv2.dilate(sun.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
far = ~(cv2.dilate(sun.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0) & ~win
out["delta_L_ring_4_24px"] = round(float((B[..., 0] - A[..., 0])[ring].mean()), 2)
out["delta_L_far_shade"] = round(float((B[..., 0] - A[..., 0])[far].mean()), 2)
json.dump(out, open(os.path.join(OUT, "data", "ed7.json"), "w"), indent=1)
ia, ib = Image.fromarray(a8), Image.fromarray(b8)
for tag, box, s in (("ed7-full", (0, 0, W, H), 0), ("ed7-floor-blade", (1700, 1200, 2736, 1536), 1), ("ed7-sill-x2", (2200, 820, 2736, 1000), 2),
                    ("ed7-bench", (150, 620, 1900, 1150), 1), ("ed7-blade-edge-x3", (2000, 1240, 2200, 1360), 3)):
    ca, cb = ia.crop(box), ib.crop(box)
    if s == 0:
        ca, cb = ca.resize((1368, 768), Image.LANCZOS), cb.resize((1368, 768), Image.LANCZOS)
    elif s > 1:
        ca, cb = ca.resize((ca.width * s, ca.height * s), Image.NEAREST), cb.resize((cb.width * s, cb.height * s), Image.NEAREST)
    o = Image.new("RGB", (ca.width, 2 * ca.height + 6), (40, 40, 40))
    o.paste(ca, (0, 0))
    o.paste(cb, (0, ca.height + 6))
    o.save(os.path.join(OUT, "overlays", tag + ".jpg"), quality=88)
print(json.dumps(out, indent=0))
