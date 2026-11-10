"""
qa-agent 2026-11-10: G-ED.9 sheets for MB1 round 3: a region of fix1 and of the current frame (Nordic fix4, warm modern fix3), each at
NEAREST zoom and as a x4 contrast stretch (percentiles 1-60). Usage: ~/.venvs/motion/bin/python -I seams.py <nordic|warm-modern> x0 y0 x1 y1 <name> [zoom].
Writes overlays/seam-<name>.jpg.
"""
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4/overlays")
sub, x0, y0, x1, y1, name = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
z = int(sys.argv[7]) if len(sys.argv) > 7 else max(1, min(4, 480 // max(x1 - x0, y1 - y0)))
files = ("nordic-MB-A-fix1.png", "nordic-MB-A-fix4.png") if sub == "nordic" else ("warm-modern-MB-A-fix1.png", "warm-modern-MB-A-fix3.png")
tiles = []
for f in files:
    c = np.asarray(Image.open(os.path.join(B, sub, f)).convert("RGB").crop((x0, y0, x1, y1))).astype(float)
    lo, hi = np.percentile(c, 1), np.percentile(c, 60)
    st = np.clip((c - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    tiles += [Image.fromarray(c.astype(np.uint8)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST),
              Image.fromarray(st).resize(((x1 - x0) * z, (y1 - y0) * z), Image.NEAREST)]
o = Image.new("RGB", (sum(t.width for t in tiles) + 10 * len(tiles), tiles[0].height), (40, 40, 40))
x = 0
for t in tiles:
    o.paste(t, (x, 0))
    x += t.width + 10
o.save(os.path.join(OUT, f"seam-{name}.jpg"), quality=90)
