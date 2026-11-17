#!/usr/bin/env python3
"""compose_hd2.py: HD with QA HD-M1 handled inside HD (run 5, 0 tokens). As compose_hd.py (the render, then HDx's projection on a
70 px smoothstep ramp right of its edge at u 0.717), except in the bottom course between the clay's joints at rows 1278 and 1563:
there the ramp runs over the whole width the turn allows, from the projection's edge to u 0.765 (HD = HDx exactly from u 0.765,
which keeps the turn's seam, u ~0.765-0.805, on HDx's own pixels), so HDx's rougher corner stone and the lit lip under its joint
fade in instead of starting at a vertical line. The ramp stays inside the course: the joint rows keep the 70 px ramp.
  python3 compose_hd2.py <render_on_canvas.png> <seed_dir> <out.png>"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
from prep_d0o import to_lin, to_srgb
rp, sd, out = sys.argv[1:4]
r = to_lin(np.asarray(Image.open(rp).convert("RGB")).astype(np.float64) / 255)
s = to_lin(np.asarray(Image.open(sd + "/hd-seed.png").convert("RGB")).astype(np.float64) / 255)
keep = np.asarray(Image.open(sd + "/hd-seed-mask.png")) > 127
H, W = keep.shape
cv = K.canvas("HD")
x765 = cv.box[0] + 0.765 * cv.fw - 0.5
xb = np.array([np.argmax(keep[y]) if keep[y].any() else W for y in range(H)])
ramp = np.full(H, 70.0)
cls = K.clay_id("HD")
col = cls[:, int(round(xb[1400]))]
joints = [y for y in range(1, H) if col[y] == 86 and col[y - 1] != 86]
lo = max(j for j in joints if j < 1400) + 4          # first row below the course's upper joint
hi = min(j for j in joints if j > 1400) - 1          # last row above its lower joint
for y in range(lo, hi):
    ramp[y] = max(70.0, x765 - xb[y])
x = np.arange(W)[None, :] - xb[:, None]
t = np.clip(x / ramp[:, None], 0, 1)
al = np.where(keep, t * t * (3 - 2 * t), 0.0)
K.save_rgb(out, to_srgb(r * (1 - al[..., None]) + s * al[..., None]))
print(json.dumps(dict(course_rows=[int(lo), int(hi)], ramp_in_course_px=round(float(ramp[(lo + hi) // 2]), 1), hdx_exact_from_u=0.765)))
