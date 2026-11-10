"""
qa-agent 2026-11-10: G-ED.11 aid on warm-modern-MB-A-fix5: where the deepest 1 % sits (guardrails.py's quarter-size copy, L* <= p1),
by region of the frame, and the same for the living room's warm-modern-A-ed8 (final_test, the gate's Q-ED7 'information' ruling).
Writes data/shadow-floor.json and overlays/shadow-floor-map.jpg (the p1 pixels in red on the quarter-size frame).
Usage: ~/.venvs/motion/bin/python -I shadow_floor.py
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
FR = {"warm-modern-MB-A-fix5": "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix5.png",
      "warm-modern-A-ed8": "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed8.png"}


def lab_L(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


out = {}
for k, p in FR.items():
    im = Image.open(os.path.join(REPO, p)).convert("RGB")
    w, h = im.size
    q = np.asarray(im.resize((w // 4, h // 4), Image.BILINEAR)).astype(float)
    L = lab_L(q)
    p1, p05 = np.percentile(L, 1), np.percentile(L, 0.5)
    m = L <= p1
    ys, xs = np.nonzero(m)
    # share of the p1 pixels in thirds of the frame (columns x rows)
    grid = {}
    for gy in range(3):
        for gx in range(3):
            sel = (ys * 3 // L.shape[0] == gy) & (xs * 3 // L.shape[1] == gx)
            grid[f"r{gy}c{gx}"] = round(float(sel.mean() * 100), 1)
    out[k] = dict(p0_5=round(float(p05), 1), p1=round(float(p1), 1), p2=round(float(np.percentile(L, 2)), 1), p5=round(float(np.percentile(L, 5)), 1),
                  share_of_p1_px_by_third_pct=grid)
    if k.startswith("warm-modern-MB"):
        vis = q.astype(np.uint8).copy()
        vis[m] = (255, 0, 0)
        Image.fromarray(vis).save(os.path.join(OUT, "overlays", "shadow-floor-map.jpg"), quality=90)
json.dump(out, open(os.path.join(OUT, "data", "shadow-floor.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
