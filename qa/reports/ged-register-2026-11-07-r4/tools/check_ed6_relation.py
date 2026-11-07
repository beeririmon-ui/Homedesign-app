"""
qa-agent 2026-11-07: ed6's milk-tea boucle against the white references in the same frame and light: the white stoneware vase (lit body,
x 1870-1930, y 900-990 at 2720) and the other White boucle of the same SKU (left of the throw, x 900-990, y 760-830), and against the
SKU photos' relation (milk tea minus White, the same CJ listing and photo setup: L* +1.1, a* +0.9, b* +1.6). Also the two-tone check:
C* of the darkest fifth minus C* of the lightest fifth (by L*) inside each cushion, ed5, ed6, the White boucle and the SKU photo.
Usage: ~/.venvs/motion/bin/python -I check_ed6_relation.py. Writes data/ed6-relation.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r4")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def stats(px):
    m = np.median(px, 0)
    L = px[:, 0]
    C = np.hypot(px[:, 1], px[:, 2])
    two_tone = float(np.median(C[L <= np.percentile(L, 20)]) - np.median(C[L >= np.percentile(L, 80)]))
    return dict(lab=[round(float(v), 1) for v in m], C_dark_minus_C_light=round(two_tone, 1))


a = lab(np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed5.png")).convert("RGB")).astype(float))
b = lab(np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed6.png")).convert("RGB")).astype(float))
raw_a = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed5.png")).convert("RGB")).astype(int)
raw_b = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed6.png")).convert("RGB")).astype(int)
m = np.abs(raw_a - raw_b).max(2) > 0
vase = b[900:990, 1870:1930].reshape(-1, 3)
white = b[760:830, 900:990].reshape(-1, 3)
out = dict(milk_tea_ed5=stats(a[m]), milk_tea_ed6=stats(b[m]), vase=stats(vase), white_boucle=stats(white))
for ref in ("vase", "white_boucle"):
    for ed in ("ed5", "ed6"):
        out[f"milk_tea_{ed}_minus_{ref}"] = [round(out[f"milk_tea_{ed}"]["lab"][i] - out[ref]["lab"][i], 1) for i in range(3)]
out["sku_milk_tea_minus_white"] = [1.1, 0.9, 1.6]
for n in ("milk-tea-color", "white"):
    ph = lab(np.asarray(Image.open(REF + f"A-cushions-cj-boucle-teddy-{n}-crop.png").convert("RGB")).astype(float))
    H, W = ph.shape[:2]
    out[f"sku_{n}"] = stats(ph[H // 4:3 * H // 4, W // 4:3 * W // 4].reshape(-1, 3))
json.dump(out, open(os.path.join(OUT, "data", "ed6-relation.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
