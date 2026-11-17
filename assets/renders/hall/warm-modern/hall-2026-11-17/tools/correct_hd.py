#!/usr/bin/env python3
"""correct_hd.py: HD = r1 with ONE uniform exposure factor in linear light (a manager-approved exception to 11.9.3, 2026-11-17),
then HDx's projection (seeds.py hd) pasted back into the right part (u >= 0.717, feathered 2 px inside its edge).
render-agent, 0 tokens.  python3 correct_hd.py <r1.png> <seed_dir> <target_stops> <out.png>"""
import json, math, sys
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
from prep_d0o import to_lin, to_srgb
r1, sd, tgt, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
a = np.asarray(Image.open(r1).convert("RGB")).astype(np.float64) / 255
lin = to_lin(a)
s0 = K.levels("HD", r1)["stops_vs_base"]
k = 2 ** (tgt - s0)
clipped_r1 = float((a.max(-1) >= 254.5 / 255).mean())
cor = lin * k
seed = to_lin(np.asarray(Image.open(sd + "/hd-seed.png").convert("RGB")).astype(np.float64) / 255)
keep = (np.asarray(Image.open(sd + "/hd-seed-mask.png")) > 127).astype(np.float32)
al = cv2.GaussianBlur(cv2.erode(keep, np.ones((5, 5), np.uint8)), (0, 0), 1.0)
al = np.where(keep > 0, al, 0)
res = cor * (1 - al[..., None]) + seed * al[..., None]
K.save_rgb(out, to_srgb(res))
print(json.dumps(dict(r1_jib_stops=s0, factor=round(k, 4), factor_stops=round(math.log2(k), 3), r1_px_with_a_channel_at_255=clipped_r1)))
