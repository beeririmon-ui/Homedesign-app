"""
qa-agent 2026-11-07: G2.1 / G2.3 (swap-diff, studio rule ו.5) on the pilot's cushion sets. For every pair of the base
(shell-furniture-v2.png) and composite-set-{A,B,C}-v2.png: pixels that changed by more than 0 and by more than 2 levels outside the union of
both sets' layer alphas (layers/cushions/set-<S>.png, alpha > 0) and shadows (shadows/cushions/set-<S>.png, any channel < 255).
Halo band (G2.3): the 1-3 px ring just inside each alpha edge, its luminance against the layer 4-8 px inside and the base just outside.
Writes data/swapdiff.json and overlays/swap-edges-x4.jpg. Usage: ~/.venvs/motion/bin/python -I swapdiff.py
"""
import itertools
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
img = {"base": np.asarray(Image.open(os.path.join(P, "shell-furniture-v2.png")).convert("RGB")).astype(int)}
alpha, shadow = {"base": None}, {"base": None}
for S in "ABC":
    img[S] = np.asarray(Image.open(os.path.join(P, f"composite-set-{S}-v2.png")).convert("RGB")).astype(int)
    alpha[S] = np.asarray(Image.open(os.path.join(P, "layers/cushions", f"set-{S}.png")))[..., 3]
    shadow[S] = np.asarray(Image.open(os.path.join(P, "shadows/cushions", f"set-{S}.png")).convert("RGB")).min(2) < 255
out = {}
for a, b in [("base", "A"), ("base", "B"), ("base", "C"), ("A", "B"), ("A", "C"), ("B", "C")]:
    d = np.abs(img[a] - img[b]).max(2)
    allowed = np.zeros(d.shape, bool)
    for k in (a, b):
        if alpha[k] is not None:
            allowed |= alpha[k] > 0
            allowed |= shadow[k]
    out[f"{a}->{b}"] = dict(changed_gt0=int((d > 0).sum()), changed_gt2=int((d > 2).sum()), outside_gt0=int(((d > 0) & ~allowed).sum()),
                            outside_gt2=int(((d > 2) & ~allowed).sum()), allowed_px=int(allowed.sum()))
gray = {k: cv2.cvtColor(v.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(float) for k, v in img.items()}
halo = {}
for S in "ABC":
    m = (alpha[S] > 127).astype(np.uint8)
    ring_in = (m > 0) & ~(cv2.erode(m, np.ones((7, 7), np.uint8)) > 0)          # 1-3 px inside the edge
    deep = (cv2.erode(m, np.ones((9, 9), np.uint8)) > 0) & ~(cv2.erode(m, np.ones((17, 17), np.uint8)) > 0)  # 4-8 px inside
    ring_out = (cv2.dilate(m, np.ones((7, 7), np.uint8)) > 0) & (m == 0)        # 1-3 px outside
    g = gray[S]
    # per local window: is the edge ring brighter / darker than both its neighbours (a halo)?
    blur = lambda x, mk: cv2.blur(x * mk, (31, 31)) / np.maximum(cv2.blur(mk.astype(float), (31, 31)), 1e-6)  # noqa: E731
    gi, gd, go = blur(g, ring_in.astype(float)), blur(g, deep.astype(float)), blur(g, ring_out.astype(float))
    sel = ring_in
    lo, hi = np.minimum(gd, go)[sel], np.maximum(gd, go)[sel]
    v = gi[sel]
    above = np.clip(v - hi, 0, None)
    below = np.clip(lo - v, 0, None)
    halo[S] = dict(ring_px=int(sel.sum()), ring_above_both_p95=round(float(np.percentile(above, 95)), 2), ring_below_both_p95=round(float(np.percentile(below, 95)), 2),
                   share_above_both_by_5=round(float((above > 5).mean() * 100), 2), share_below_both_by_5=round(float((below > 5).mean() * 100), 2))
out["halo_band"] = halo
json.dump(out, open(os.path.join(OUT, "data", "swapdiff.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
tiles = []
c = Image.open(os.path.join(P, "composite-set-A-v2.png")).convert("RGB")
for box in ((1420, 860, 1500, 940), (2000, 880, 2080, 960), (1880, 1000, 1960, 1080), (2330, 1020, 2410, 1100)):
    tiles.append(c.crop(box).resize((320, 320), Image.NEAREST))
o = Image.new("RGB", (4 * 320 + 30, 320), (40, 40, 40))
for i, t in enumerate(tiles):
    o.paste(t, (i * 330, 0))
o.save(os.path.join(OUT, "overlays", "swap-edges-x4.jpg"), quality=90)
