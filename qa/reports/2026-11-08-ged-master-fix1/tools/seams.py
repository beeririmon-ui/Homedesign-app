"""
qa-agent 2026-11-08: G-ED.9 on every fix1 region: per region a crop at 100 %, the same at x3 (NEAREST), and a x4 contrast stretch
(percentiles 1-60 of the crop, the gate's method), MB-A beside fix1. Regions are the components of data/diff.json.
Usage: ~/.venvs/motion/bin/python -I seams.py <nordic|warm-modern> x0 y0 x1 y1 <name>. Writes overlays/seam-<name>.jpg.
"""
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1/overlays")
sub, x0, y0, x1, y1, name = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
base = "nordic-MB-A" if sub == "nordic" else "warm-modern-MB-A"
tiles = []
for f in (base + ".png", base + "-fix1.png"):
    c = np.asarray(Image.open(os.path.join(B, sub, f)).convert("RGB").crop((x0, y0, x1, y1))).astype(float)
    lo, hi = np.percentile(c, 1), np.percentile(c, 60)
    st = np.clip((c - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    s = max(1, min(4, 480 // max(x1 - x0, y1 - y0)))
    tiles.append(Image.fromarray(c.astype(np.uint8)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST))
    tiles.append(Image.fromarray(st).resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST))
W = sum(t.width for t in tiles) + 10 * len(tiles)
o = Image.new("RGB", (W, max(t.height for t in tiles)), (40, 40, 40))
x = 0
for t in tiles:
    o.paste(t, (x, 0))
    x += t.width + 10
o.save(os.path.join(OUT, f"seam-{name}.jpg"), quality=90)
