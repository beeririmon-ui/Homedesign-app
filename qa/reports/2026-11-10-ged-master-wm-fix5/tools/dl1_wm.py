"""
qa-agent 2026-11-10: input for the designer's eye on warm-modern-MB-A-fix5 (G-ED.13 and DL1 of the warm-modern Bible 1.0.1: 'the living
room at 17:40 and the opening frame are the brightest in the house'; private rooms may be darker, docs/design-line-across-rooms-2026-11-07.md).
The same method as qa/reports/2026-11-10-ged-master-fix5/tools/dl1.py (Nordic): L* of the back wall's plaster above the furniture, boxes
by eye, the box's top 5 % dropped (sun patches), median and p75; and the whole frame's median and p90. Against the living room's
warm-modern-A-ed8 (final_test). Usage: ~/.venvs/motion/bin/python -I dl1_wm.py. Writes data/dl1-wm.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
FR = {"warm-modern-MB-A-fix5": ("assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix5.png",
                                [(1520, 80, 2560, 220)], "the plaster above the pill niche (1520-2560 x 80-220)"),
      "warm-modern-A-ed8": ("assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed8.png",
                            [(1120, 100, 1920, 220)], "the plaster above the triptych (1120-1920 x 100-220)")}


def Lstar(p):
    c = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


out = {}
for k, (p, boxes, note) in FR.items():
    L = Lstar(os.path.join(REPO, p))
    v = np.concatenate([L[y0:y1, x0:x1].ravel() for x0, y0, x1, y1 in boxes])
    v = v[v <= np.percentile(v, 95)]
    out[k] = dict(file=p, wall=dict(median=round(float(np.median(v)), 1), p75=round(float(np.percentile(v, 75)), 1), boxes=boxes, note=note),
                  frame_median=round(float(np.median(L)), 1), frame_p90=round(float(np.percentile(L, 90)), 1))
json.dump(out, open(os.path.join(OUT, "data", "dl1-wm.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
