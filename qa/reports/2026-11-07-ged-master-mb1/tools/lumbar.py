"""
qa-agent 2026-11-07: the bouclé lumbar against its SKU photo (G-ED.3, Bible 1.9: the lit side), both frames: the lit faces (top 15 % L*
inside the patch) of the lumbar and of the neighbours in the same light (the duvet, the bedding set's own pillow, the wall), against the
photos' relation: milk tea vs the bedding's natural linen and vs White (the same CJ listing's White photo). Usage:
~/.venvs/motion/bin/python -I lumbar.py. Writes data/lumbar.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/master-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lit(arr, box):
    x0, y0, x1, y1 = box
    v = lab(arr[y0:y1, x0:x1].reshape(-1, 3).astype(float))
    t = v[v[:, 0] >= np.percentile(v[:, 0], 85)]
    return [round(float(x), 1) for x in np.median(t, 0)]


def photo(name):
    a = lab(np.asarray(Image.open(REF + name).convert("RGB")).astype(float))
    H, W = a.shape[:2]
    v = a[H // 3:2 * H // 3, W // 3:2 * W // 3].reshape(-1, 3)
    t = v[v[:, 0] >= np.percentile(v[:, 0], 85)]
    return [round(float(x), 1) for x in np.median(t, 0)]


out = {}
for f, boxes in {"nordic-MB-A": {"lumbar": (1640, 740, 1990, 860), "duvet": (800, 1200, 1200, 1320), "pillowcase": (2000, 650, 2350, 850)},
                 "warm-modern-MB-A": {"lumbar": (1830, 810, 2250, 920), "duvet": (1200, 960, 1800, 1080), "pillowcase (caramel)": (1520, 720, 1780, 900),
                                      "wall": (1600, 580, 1800, 640)}}.items():
    arr = np.asarray(Image.open(os.path.join(B, "nordic" if f.startswith("nordic") else "warm-modern", f + ".png")).convert("RGB"))
    m = {k: lit(arr, b) for k, b in boxes.items()}
    m["lumbar_minus_duvet"] = [round(m["lumbar"][i] - m["duvet"][i], 1) for i in range(3)]
    out[f] = m
ph = {k: photo(v) for k, v in {"white": "crop_cushion_white.png", "milk_tea": "crop_cushion_milktea.png", "bedding": "crop_bedding_natural.png"}.items()}
out["photos_lit"] = ph
out["photo_white_minus_bedding"] = [round(ph["white"][i] - ph["bedding"][i], 1) for i in range(3)]
out["photo_milk_tea_minus_bedding"] = [round(ph["milk_tea"][i] - ph["bedding"][i], 1) for i in range(3)]
json.dump(out, open(os.path.join(OUT, "data", "lumbar.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
