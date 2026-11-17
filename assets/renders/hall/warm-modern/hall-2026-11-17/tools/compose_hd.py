#!/usr/bin/env python3
"""compose_hd.py: HD = the render (on HD's canvas) with HDx's projection (seeds.py hd) pasted into the right part. The
paste edge (u 0.717) runs through the middle of stones, so the render hands over to HDx on a horizontal ramp of RAMP px just
RIGHT of that edge (smoothstep, inside the seed's coverage); from about u 0.75 on, HD is HDx exactly, which keeps the turn's
seam (yaw 57.5 +-2 deg, u ~0.765-0.805; measured over +-4 deg, u 0.722-0.853) on HDx's own pixels. render-agent, 0 tokens.
  python3 compose_hd.py <render_on_canvas.png> <seed_dir> <out.png> [ramp_px=70]"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
from prep_d0o import to_lin, to_srgb
rp, sd, out = sys.argv[1:4]
RAMP = int(sys.argv[4]) if len(sys.argv) > 4 else 70
r = to_lin(np.asarray(Image.open(rp).convert("RGB")).astype(np.float64) / 255)
s = to_lin(np.asarray(Image.open(sd + "/hd-seed.png").convert("RGB")).astype(np.float64) / 255)
keep = np.asarray(Image.open(sd + "/hd-seed-mask.png")) > 127
H, W = keep.shape
xb = np.array([np.argmax(keep[y]) if keep[y].any() else W for y in range(H)])
x = np.arange(W)[None, :] - xb[:, None]
t = np.clip(x / RAMP, 0, 1)
al = np.where(keep, t * t * (3 - 2 * t), 0.0)
K.save_rgb(out, to_srgb(r * (1 - al[..., None]) + s * al[..., None]))
cv = K.canvas("HD")
us = (xb + RAMP + 0.5 - cv.box[0]) / cv.fw
print(json.dumps(dict(ramp_px=RAMP, hdx_exact_from_u=round(float(np.median(us)), 4))))
