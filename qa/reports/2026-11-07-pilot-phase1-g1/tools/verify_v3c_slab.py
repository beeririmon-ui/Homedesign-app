"""
qa-agent 2026-11-07: verify_v3c.py's slab counts, split by what the pixel shows in the composites: the visible slab (fixed-furniture alpha 0),
the armchair's antialiased edge over the slab (0 < alpha < 255) and the armchair itself (alpha 255, not stone; the wide mask runs under it).
Per class: px, HSV H < 25 with chroma > 3, b* > 15, b* max. Usage: ~/.venvs/motion/bin/python -I verify_v3c_slab.py. Writes data/verify-v3c-slab.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


wide = np.asarray(Image.open(os.path.join(P, "masks/stone-wide.png")).convert("L")) > 127
fa = np.asarray(Image.open(os.path.join(P, "fixed-furniture.png")))[..., 3]
out = {}
for n in ("shell-furniture-v3-graded-v3c.png", "composite-set-C-v3-graded-v3c.png"):
    rgb = np.asarray(Image.open(os.path.join(P, n)).convert("RGB"))
    L = lab(rgb.astype(float))
    H = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV_FULL)[..., 0].astype(float) * 360 / 256
    C = np.hypot(L[..., 1], L[..., 2])
    rec = {}
    for cls, sel in (("visible_slab", wide & (fa == 0)), ("armchair_edge_over_slab", wide & (fa > 0) & (fa < 255)), ("armchair_itself", wide & (fa == 255))):
        b = L[..., 2][sel]
        rec[cls] = dict(px=int(sel.sum()), H_below_25_C_gt3=int(((H < 25) & (C > 3) & sel).sum()), b_over_15=int((b > 15).sum()), b_over_12_5=int((b > 12.5).sum()),
                        b_max=round(float(b.max()), 2) if b.size else None, b_median=round(float(np.median(b)), 2) if b.size else None)
    vs = wide & (fa == 0)
    ys, xs = np.nonzero(vs & (L[..., 2] > 12.5))
    rec["visible_slab_b_over_12_5_bbox"] = [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())] if len(xs) else None
    out[n] = rec
json.dump(out, open(os.path.join(OUT, "data", "verify-v3c-slab.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
