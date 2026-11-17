#!/usr/bin/env python3
"""heal_legs.py: QA HDx-M2 (2026-11-17), 0 tokens. With the supersampled seed the coffee table's legs are base.png's (smooth
walnut, no dots). base.png's frame ends part-way down the legs, so their feet come from fix1 (the render that drew the room);
the hand-over was a hard edge, which read as a ring at the foot. Inside the legs' box (the clay's table id below its top,
dilated 15 px) the seed now fades into fix1 over RAMP px inside the seed's edge (smoothstep on the distance to that edge).
  python3 heal_legs.py <composite.png> <seed_kept.png> <keep_mask.png> <fix1_raw.png> <out.png> [ramp=10]"""
import json, sys
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
from prep_d0o import to_lin, to_srgb
comp = to_lin(np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float64) / 255)
seed = to_lin(np.asarray(Image.open(sys.argv[2]).convert("RGB")).astype(np.float64) / 255)
keep = np.asarray(Image.open(sys.argv[3])) > 127
fix1 = to_lin(np.asarray(Image.open(sys.argv[4]).convert("RGB")).astype(np.float64) / 255)
RAMP = int(sys.argv[6]) if len(sys.argv) > 6 else 10
cls = K.clay_id("HDx")
t = cls == 42
w = t.sum(1); rows = np.nonzero(w)[0]
y_legs = int(rows[w[rows] > 0.6 * w.max()].max()) + 4
legs = t.copy(); legs[:y_legs] = False
R = cv2.dilate(legs.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
R[:y_legs] = False
dt = cv2.distanceTransform(keep.astype(np.uint8), cv2.DIST_L2, 5)
s = np.clip(dt / RAMP, 0, 1); s = s * s * (3 - 2 * s)
a = np.where(keep, s, 0.0)
leg_mix = fix1 * (1 - a[..., None]) + seed * a[..., None]
b = cv2.GaussianBlur(R.astype(np.float32), (0, 0), 2.0)       # soft edge of the box itself
res = comp * (1 - b[..., None]) + leg_mix * b[..., None]
K.save_rgb(sys.argv[5], to_srgb(res))
print(json.dumps(dict(legs_box_px=int(R.sum()), ramp_px=RAMP, first_leg_row=y_legs)))
