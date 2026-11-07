"""qa-agent 2026-11-07: warm-modern ed5, set A against the SKU photos (view only, session scratchpad wm-pilot-refs/): the milk-tea boucle
and the white boucle (same CJ listing, the same studio photo setup, so the two photos compare directly), and the flax-brown muslin throw.
Median Lab of each cushion face. Writes data/setA.json. Usage: ~/.venvs/motion/bin/python -I check_setA.py"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r3")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def med(img, box_frac):
    W, H = img.size
    u0, v0, u1, v1 = box_frac
    p = lab(np.asarray(img.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H)))).astype(float).reshape(-1, 3))
    m = np.median(p, 0)
    return [round(float(v), 1) for v in m] + [round(float(np.hypot(m[1], m[2])), 1)]


fr = Image.open(os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed5.png")).convert("RGB")
out = dict(
    frame=dict(milk_tea=med(fr, (0.735, 0.47, 0.82, 0.58)), white=med(fr, (0.315, 0.47, 0.38, 0.57))),
    sku_photos=dict(milk_tea=med(Image.open(REF + "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png").convert("RGB"), (0.25, 0.25, 0.75, 0.75)),
                    white=med(Image.open(REF + "A-cushions-cj-boucle-teddy-white-crop.png").convert("RGB"), (0.25, 0.25, 0.75, 0.75)),
                    flax_brown=med(Image.open(REF + "A-sofa-cover-cj-cotton-muslin-fringe-flax-brown-crop.png").convert("RGB"), (0.3, 0.3, 0.8, 0.8))),
    frame_throw=med(fr, (0.25, 0.55, 0.36, 0.78)), fields="[L*, a*, b*, C*], medians")
f, s = out["frame"], out["sku_photos"]
out["frame_milk_tea_minus_white"] = [round(f["milk_tea"][i] - f["white"][i], 1) for i in range(3)]
out["sku_milk_tea_minus_white"] = [round(s["milk_tea"][i] - s["white"][i], 1) for i in range(3)]
json.dump(out, open(os.path.join(OUT, "data", "setA.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
