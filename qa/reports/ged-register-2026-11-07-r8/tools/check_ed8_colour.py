"""
qa-agent 2026-11-07: ed8's camel corduroy against its SKU photo with the frame light neutralised (von Kries in linear RGB): the frame's
cushion lit face divided by the White bouclé's lit face (the same CJ White SKU, photo 95.2 / 0.2 / 2.0 = near white), the photo's camel
lit face divided by the photo's white background; both scaled to the photo's luminance; then hue, chroma ratio, dE76 and dE00.
Usage: ~/.venvs/motion/bin/python -I check_ed8_colour.py. Writes data/ed8-colour.json.
"""
import json
import os

import numpy as np

OUT = "/home/user/homedesign-app/qa/reports/ged-register-2026-11-07-r8"
d = json.load(open(os.path.join(OUT, "data", "ed8.json")))
WN = np.array([0.9505, 1.0, 1.089])
Mi = np.linalg.inv(np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]))
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])


def lab2lin(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    f = np.array([fx, fy, fz])
    xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16 / 116) / 7.787) * WN
    return Mi @ xyz


def lin2lab(c):
    xyz = (M @ c) / WN
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


fc, fw = lab2lin(*d["camel_lit_ed8"][:3]), lab2lin(*d["white_lit"][:3])
pc, pw = lab2lin(*d["photo_camel_lit"][:3]), lab2lin(*d["photo_white"][:3])
WHITE_SKU = lab2lin(95.2, 0.2, 2.0)            # the White bouclé's own photo: near white, slightly warm
f_norm = fc / fw * WHITE_SKU
p_norm = pc / pw
f_norm = f_norm * ((M[1] @ p_norm) / (M[1] @ f_norm))
lf, lp = lin2lab(f_norm), lin2lab(p_norm)
hf, hp = np.degrees(np.arctan2(lf[2], lf[1])), np.degrees(np.arctan2(lp[2], lp[1]))
out = dict(frame_norm=[round(float(x), 1) for x in lf], photo_norm=[round(float(x), 1) for x in lp], d_hue=round(float(hf - hp), 1),
           chroma_ratio=round(float(np.hypot(lf[1], lf[2]) / np.hypot(lp[1], lp[2])), 2), dE76=round(float(np.linalg.norm(lf - lp)), 1))
json.dump(out, open(os.path.join(OUT, "data", "ed8-colour.json"), "w"), indent=1)
print(json.dumps(out))
