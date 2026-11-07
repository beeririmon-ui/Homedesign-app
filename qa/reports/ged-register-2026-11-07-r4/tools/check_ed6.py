"""
qa-agent 2026-11-07: warm-modern-A-ed6 (render-agent's 0-token recolour of the milk-tea boucle, ed6-milktea.json) against ed5.
(1) the change: pixels changed and their bounding box (it must be the cushion only); (2) the cushion's colour: median Lab of the changed
pixels, ed5 and ed6, and the texture: L* standard deviation and the 5-95 % L* span inside the cushion after removing the low frequencies
(sigma 6), against the SKU photo's (view only, the scratchpad's wm-pilot-refs/); the share of pixels at L* >= 97; (3) crops at 100 % and x3.
Usage: ~/.venvs/motion/bin/python -I check_ed6.py. Writes data/ed6.json and overlays/ed6-cushion-100-x3.jpg.
"""
import json
import os

import cv2
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


def texture(Lmap, mask):
    k = mask.astype(np.float32)
    lf = cv2.GaussianBlur(Lmap * k, (0, 0), 6) / np.maximum(cv2.GaussianBlur(k, (0, 0), 6), 1e-4)
    hf = (Lmap - lf)[cv2.erode(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0]
    lo = lf[cv2.erode(mask.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0]
    return dict(hf_sd=round(float(hf.std()), 2), hf_span_5_95=round(float(np.percentile(hf, 95) - np.percentile(hf, 5)), 2),
                lowfreq_sd=round(float(lo.std()), 2))


a = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed5.png")).convert("RGB")).astype(float)
b = np.asarray(Image.open(os.path.join(E, "warm-modern-A-ed6.png")).convert("RGB")).astype(float)
d = np.abs(a - b).max(2) > 0
ys, xs = np.nonzero(d)
La, Lb = lab(a), lab(b)
m = d
out = dict(changed_px=int(d.sum()), bbox=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
           cushion_ed5=[round(float(v), 1) for v in np.median(La[m], 0)], cushion_ed6=[round(float(v), 1) for v in np.median(Lb[m], 0)],
           texture_ed5=texture(La[..., 0].astype(np.float32), m), texture_ed6=texture(Lb[..., 0].astype(np.float32), m),
           share_L_ge_97_ed6_pct=round(float((Lb[m][:, 0] >= 97).mean() * 100), 2), share_L_ge_97_ed5_pct=round(float((La[m][:, 0] >= 97).mean() * 100), 2))
ph = np.asarray(Image.open(REF + "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png").convert("RGB")).astype(float)
H, W = ph.shape[:2]
pm = np.zeros((H, W), bool)
pm[H // 4:3 * H // 4, W // 4:3 * W // 4] = True
# the photo's boucle at the frame's scale: the cushion spans ~290 px in the frame; the photo's cushion ~0.8 of the crop width
s = 290 / (0.8 * W)
phs = cv2.resize(ph, (max(1, int(W * s)), max(1, int(H * s))), interpolation=cv2.INTER_AREA)
pms = cv2.resize(pm.astype(np.uint8), (phs.shape[1], phs.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
out["sku_photo_texture_at_frame_scale"] = texture(lab(phs)[..., 0].astype(np.float32), pms)
out["sku_photo_lab"] = [round(float(v), 1) for v in np.median(lab(ph)[pm], 0)]
json.dump(out, open(os.path.join(OUT, "data", "ed6.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
x0, x1, y0, y1 = out["bbox"]
box = (x0 - 30, y0 - 30, x1 + 30, y1 + 30)
A = Image.fromarray(a.astype(np.uint8)).crop(box)
B = Image.fromarray(b.astype(np.uint8)).crop(box)
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
z = (cx - 60, cy - 60, cx + 60, cy + 60)
Az = Image.fromarray(a.astype(np.uint8)).crop(z).resize((360, 360), Image.NEAREST)
Bz = Image.fromarray(b.astype(np.uint8)).crop(z).resize((360, 360), Image.NEAREST)
Pz = Image.fromarray(phs.astype(np.uint8)).crop((phs.shape[1] // 2 - 60, phs.shape[0] // 2 - 60, phs.shape[1] // 2 + 60, phs.shape[0] // 2 + 60)).resize((360, 360), Image.NEAREST)
h = max(A.height, 360)
o = Image.new("RGB", (A.width * 2 + 3 * 370 + 30, h), (40, 40, 40))
o.paste(A, (0, 0))
o.paste(B, (A.width + 10, 0))
for i, t in enumerate((Az, Bz, Pz)):
    o.paste(t, (2 * A.width + 30 + i * 370, 0))
o.save(os.path.join(OUT, "overlays", "ed6-cushion-100-x3.jpg"), quality=90)
