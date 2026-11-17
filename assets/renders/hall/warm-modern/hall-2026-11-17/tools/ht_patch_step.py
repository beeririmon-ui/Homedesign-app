#!/usr/bin/env python3
"""ht_patch_step.py: the tone across the top and bottom edges of HD's patch on HT's plaster (r1's failure 2), 0 tokens.
Per 100 px block of columns: median Y 10-40 px inside the patch over median Y 10-40 px outside it, in %.
  python3 ht_patch_step.py <img.png> <seed_dir>"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
img, sd = sys.argv[1:3]
Y = K.lin_Y(img)
src = np.asarray(Image.open(sd + "/ht-seed-source.png").convert("RGB"))
keep = np.asarray(Image.open(sd + "/ht-seed-mask.png")) > 127
hd = keep & (src[..., 0] > 128) & (src[..., 1] < 128)
cls = K.clay_id("HT")
pl = np.isin(cls, (11, 82))
out = {}
for edge in ("top", "bottom"):
    res = []
    for x0 in range(0, Y.shape[1], 100):
        a, b = [], []
        for x in range(x0, min(x0 + 100, Y.shape[1])):
            col = hd[:, x] & pl[:, x]
            if col.sum() < 100:
                continue
            ys = np.nonzero(col)[0]
            e = ys.min() if edge == "top" else ys.max()
            s = 1 if edge == "top" else -1
            ins = [e + s * d for d in range(10, 40)]
            outs = [e - s * d for d in range(10, 40)]
            ins = [y for y in ins if 0 <= y < Y.shape[0] and pl[y, x]]
            outs = [y for y in outs if 0 <= y < Y.shape[0] and pl[y, x]]
            a += [Y[y, x] for y in ins]; b += [Y[y, x] for y in outs]
        if len(a) > 300 and len(b) > 300:
            res.append((x0, round(100 * (np.median(a) / np.median(b) - 1), 1)))
    out[edge] = res
print(json.dumps(out))
