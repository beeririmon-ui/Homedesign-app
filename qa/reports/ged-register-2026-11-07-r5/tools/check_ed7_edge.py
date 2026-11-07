"""
qa-agent 2026-11-07: ed7's cushion edge (G-ED.9, no seam or halo): inside the ed5->ed6 cushion mask, the 1-3 px ring at its edge against
the 4-8 px band inside it, median C* and hue, ed6 and ed7 (a chroma ring would show as a step); and a x4 crop of the top edge against
the wall and of the left edge by the olive leaves. Usage: ~/.venvs/motion/bin/python -I check_ed7_edge.py. Writes data/ed7-edge.json and
overlays/ed7-edge-x4.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r5")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


raw = {k: np.asarray(Image.open(os.path.join(E, f"warm-modern-A-{k}.png")).convert("RGB")) for k in ("ed5", "ed6", "ed7")}
m = (np.abs(raw["ed5"].astype(int) - raw["ed6"].astype(int)).max(2) > 0).astype(np.uint8)
ring = (m > 0) & ~(cv2.erode(m, np.ones((7, 7), np.uint8)) > 0)
band = (cv2.erode(m, np.ones((9, 9), np.uint8)) > 0) & ~(cv2.erode(m, np.ones((17, 17), np.uint8)) > 0)
out = {}
for k in ("ed6", "ed7"):
    L = lab(raw[k].astype(float))
    C = np.hypot(L[..., 1], L[..., 2])
    h = np.degrees(np.arctan2(L[..., 2], L[..., 1]))
    out[k] = dict(ring_C=round(float(np.median(C[ring])), 2), band_C=round(float(np.median(C[band])), 2),
                  ring_h=round(float(np.median(h[ring])), 1), band_h=round(float(np.median(h[band])), 1),
                  ring_L=round(float(np.median(L[..., 0][ring])), 1), band_L=round(float(np.median(L[..., 0][band])), 1))
json.dump(out, open(os.path.join(OUT, "data", "ed7-edge.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
ys, xs = np.nonzero(m)
top_x = int(np.median(xs))
top_y = int(ys[xs == top_x].min())
left_y = int(np.median(ys))
left_x = int(xs[ys == left_y].min())
im = Image.fromarray(raw["ed7"])
t1 = im.crop((top_x - 50, top_y - 30, top_x + 50, top_y + 30)).resize((400, 240), Image.NEAREST)
t2 = im.crop((left_x - 30, left_y - 50, left_x + 30, left_y + 50)).resize((240, 400), Image.NEAREST)
o = Image.new("RGB", (650, 400), (40, 40, 40))
o.paste(t1, (0, 0))
o.paste(t2, (410, 0))
o.save(os.path.join(OUT, "overlays", "ed7-edge-x4.jpg"), quality=90)
