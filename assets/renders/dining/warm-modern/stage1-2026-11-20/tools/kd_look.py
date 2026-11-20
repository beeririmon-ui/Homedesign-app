#!/usr/bin/env python3
"""kd_look.py: a quick look sheet (scratchpad): the composite crop, and the same crop with each layer's alpha outlined and the clay outline
  python3 kd_look.py <frame> x0 y0 x1 y1 <out.jpg> [composite.png]"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

fr, x0, y0, x1, y1, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
comp = sys.argv[7] if len(sys.argv) > 7 else os.path.join(K.ST, f"{fr}-defaults.png")
a = np.asarray(Image.open(comp).convert("RGB")).copy()
o = a.copy()
man = json.load(open(os.path.join(K.ST, "manifest.json")))
cols = [(255, 0, 0), (0, 160, 255), (0, 200, 0), (255, 160, 0), (200, 0, 200), (0, 0, 0)]
for i, l in enumerate([l for l in man["layers"] if l["frame"] == fr and l["default"]]):
    al = np.asarray(Image.open(os.path.join(K.ST, l["layer"])))[..., 3] > 127
    e = al & ~cv2.erode(al.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    o[e] = cols[i % len(cols)]
ids = K.ids(fr)
cl = (ids >= 50) & (ids < 80)
e = cl & ~cv2.erode(cl.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
o[e] = (255, 255, 255)
A = Image.fromarray(a[y0:y1, x0:x1])
B = Image.fromarray(o[y0:y1, x0:x1])
S = Image.new("RGB", (A.size[0] * 2 + 10, A.size[1]), "white")
S.paste(A, (0, 0))
S.paste(B, (A.size[0] + 10, 0))
if S.size[0] > 2400:
    S = S.resize((2400, int(S.size[1] * 2400 / S.size[0])), Image.LANCZOS)
S.save(out, quality=88)
