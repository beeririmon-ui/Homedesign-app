"""
qa-agent 2026-11-07: where the halo-band statistic of swapdiff.py flags a light ring (ring 1-3 px inside the alpha edge brighter than both
the 4-8 px interior and the 1-3 px exterior by > 5 grey levels, 31 px windows), crop the 6 strongest spots per set at x4 for an eye check.
Usage: ~/.venvs/motion/bin/python -I halo_hotspots.py <version, default v2>
Writes overlays/halo-hotspots-<set>-<version>-x4.jpg and data/halo-hotspots-<version>.json.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
V = sys.argv[1] if len(sys.argv) > 1 else "v2"
res = {}
for S in "ABC":
    fn = os.path.join(P, f"composite-set-{S}-{V}.png")
    if not os.path.exists(fn):
        res[S] = "missing"
        continue
    im = np.asarray(Image.open(fn).convert("RGB"))
    g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(float)
    m = (np.asarray(Image.open(os.path.join(P, "layers/cushions", f"set-{S}.png")))[..., 3] > 127).astype(np.uint8)
    ring_in = (m > 0) & ~(cv2.erode(m, np.ones((7, 7), np.uint8)) > 0)
    deep = (cv2.erode(m, np.ones((9, 9), np.uint8)) > 0) & ~(cv2.erode(m, np.ones((17, 17), np.uint8)) > 0)
    ring_out = (cv2.dilate(m, np.ones((7, 7), np.uint8)) > 0) & (m == 0)
    blur = lambda x, mk: cv2.blur(x * mk, (31, 31)) / np.maximum(cv2.blur(mk.astype(float), (31, 31)), 1e-6)  # noqa: E731
    gi, gd, go = blur(g, ring_in.astype(float)), blur(g, deep.astype(float)), blur(g, ring_out.astype(float))
    above = np.where(ring_in, gi - np.maximum(gd, go), -999)
    # strongest spots, at least 60 px apart
    spots = []
    a = above.copy()
    for _ in range(6):
        y, x = np.unravel_index(np.argmax(a), a.shape)
        if a[y, x] <= 5:
            break
        spots.append(dict(x=int(x), y=int(y), ring_minus_max_neighbour=round(float(a[y, x]), 1), ring=round(float(gi[y, x]), 1), inside=round(float(gd[y, x]), 1), outside=round(float(go[y, x]), 1)))
        a[max(0, y - 60):y + 60, max(0, x - 60):x + 60] = -999
    res[S] = spots
    tiles = []
    for s in spots:
        x, y = s["x"], s["y"]
        tiles.append(Image.fromarray(im).crop((x - 40, y - 40, x + 40, y + 40)).resize((320, 320), Image.NEAREST))
    if tiles:
        o = Image.new("RGB", (len(tiles) * 330, 320), (40, 40, 40))
        for i, t in enumerate(tiles):
            o.paste(t, (i * 330, 0))
        o.save(os.path.join(OUT, "overlays", f"halo-hotspots-{S}-{V}-x4.jpg"), quality=90)
json.dump(res, open(os.path.join(OUT, "data", f"halo-hotspots-{V}.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
