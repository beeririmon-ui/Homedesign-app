"""
qa-agent 2026-11-07: the bench slab in the display grade (designer 13.1 (3): the lit slab must not read yellow; b* after grading <= 12, or the
slab left out of the grade's warm shift). Inside render-agent's masks/stone.png (read only): L*, a*, b* median and p95 of b* on the shell
and on the shell + furniture, ungraded and graded, v2 and v3; and the b* step across the mask's edge (the 3 px ring inside vs the 3 px ring
outside, along the slab's top edge), so a cap seam would show. Crops at 100 % and x4 of the slab's lit end and its edge.
Usage: ~/.venvs/motion/bin/python -I bench_cap.py. Writes data/bench-cap.json, overlays/bench-v2-v3-v3b-100.jpg and overlays/bench-edge-v3b-x4.jpg.
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


st = np.asarray(Image.open(os.path.join(P, "masks/stone.png")).convert("L"))
if st.shape != (1530, 2720):
    st = cv2.resize(st, (2720, 1530), interpolation=cv2.INTER_NEAREST)
m = st > 127
mi = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
ring_in = m & ~(cv2.erode(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
ring_out = (cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~m
out = {"stone_mask_px": int(m.sum()), "target_#D8C8AE": [round(float(v), 2) for v in lab(np.array([[0xD8, 0xC8, 0xAE]], float))[0]]}
for n in ("shell-v2.png", "shell-v2-graded.png", "shell-v3.png", "shell-v3-graded.png", "shell-furniture-v3-graded.png", "composite-set-B-v3-graded.png",
          "shell-v3-graded-v3b.png", "shell-furniture-v3-graded-v3b.png", "composite-set-A-v3-graded-v3b.png", "composite-set-B-v3-graded-v3b.png", "composite-set-C-v3-graded-v3b.png"):
    Lb = lab(np.asarray(Image.open(os.path.join(P, n)).convert("RGB")).astype(float))
    v = Lb[mi]
    lit = v[v[:, 0] >= np.percentile(v[:, 0], 50)]
    rgb = np.asarray(Image.open(os.path.join(P, n)).convert("RGB")).astype(float)[mi]
    front = v[:, 0] < np.percentile(v[:, 0], 30)                # the 8 cm front face: the stone's darker 30 %
    fr = np.median(rgb[front], 0) / 255.0
    mx, mn = fr.max(), fr.min()
    hsv_h = 0.0 if mx == mn else (60 * ((fr[1] - fr[2]) / (mx - mn)) % 360 if mx == fr[0] else 60 * ((fr[2] - fr[0]) / (mx - mn)) + 120 if mx == fr[1] else 60 * ((fr[0] - fr[1]) / (mx - mn)) + 240)
    out[n] = dict(L=round(float(np.median(v[:, 0])), 1), a=round(float(np.median(v[:, 1])), 2), b=round(float(np.median(v[:, 2])), 2),
                  b_p95=round(float(np.percentile(v[:, 2], 95)), 2), lit_half_b=round(float(np.median(lit[:, 2])), 2),
                  edge_b_in=round(float(np.median(Lb[ring_in][:, 2])), 2), edge_b_out=round(float(np.median(Lb[ring_out][:, 2])), 2),
                  front_face_lab=[round(float(x), 1) for x in np.median(v[front], 0)], front_face_rgb=[int(x * 255 + 0.5) for x in fr],
                  front_face_hsv_h=round(float(hsv_h), 1), front_face_hsv_s=round(float((mx - mn) / mx * 100), 1))
json.dump(out, open(os.path.join(OUT, "data", "bench-cap.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
ys, xs = np.nonzero(m)
box = (int(xs.min()) - 20, int(ys.min()) - 20, int(xs.max()) + 20, int(ys.max()) + 20)
tiles = [Image.open(os.path.join(P, n)).convert("RGB").crop(box) for n in ("shell-v2-graded.png", "shell-v3-graded.png", "shell-v3-graded-v3b.png")]
o = Image.new("RGB", (tiles[0].width, tiles[0].height * 3 + 20), (40, 40, 40))
for i, t_ in enumerate(tiles):
    o.paste(t_, (0, i * (tiles[0].height + 10)))
o.save(os.path.join(OUT, "overlays", "bench-v2-v3-v3b-100.jpg"), quality=90)
# x4 on the slab's top edge, where the cap meets the plaster and the glazing
cy = int(np.median(ys[xs == int(np.median(xs))])) if (xs == int(np.median(xs))).any() else int(np.median(ys))
cx = int(np.median(xs))
yy = np.nonzero(m[:, cx])[0]
y_top = int(yy.min())
t = [Image.open(os.path.join(P, "shell-v3-graded-v3b.png")).convert("RGB").crop((cx - 60, y_top - 40, cx + 60, y_top + 40)).resize((480, 320), Image.NEAREST),
     Image.open(os.path.join(P, "shell-v3-graded-v3b.png")).convert("RGB").crop((box[0] + 20, int(ys[xs == xs.min()].mean()) - 40, box[0] + 140, int(ys[xs == xs.min()].mean()) + 40)).resize((480, 320), Image.NEAREST)]
o = Image.new("RGB", (970, 320), (40, 40, 40))
o.paste(t[0], (0, 0))
o.paste(t[1], (490, 0))
o.save(os.path.join(OUT, "overlays", "bench-edge-v3b-x4.jpg"), quality=90)
