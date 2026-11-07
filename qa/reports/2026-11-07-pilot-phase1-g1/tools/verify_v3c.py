"""
qa-agent 2026-11-07: verification of render-agent's F1-F3 on the display grade v3c (shell-fix-v3.json grade_v3c, lock_F3).
F1, the bench slab (render-agent's masks/stone-wide.png, read only; also the old masks/stone.png): per display file the slab's lit top and
its front face (the stone's darker 30 %) Lab and HSV H, the share of slab pixels with HSV H < 25 (chroma > 3, so near-greys don't count),
b* max and p99.9 and where the b* > 15 pixels are (inside the furniture's alpha edge or not); the b* / a* step across the wide mask's edge
(3 px in vs 3 px out); crops at 100 % and x4 (the front face's left end, and the armchair edge).
Black point: per display file the p0.5 of L*, and for set C where the pixels under L* 11 are (inside the set's layer alpha or the
fixed furniture or the shell), their lowest L*, and whether they keep texture (L* sd in 9 x 9 windows; a crushed floor would be ~0).
Usage: ~/.venvs/motion/bin/python -I verify_v3c.py. Writes data/verify-v3c.json, overlays/bench-v3c-100.jpg, overlays/bench-v3c-x4.jpg.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def hsv_h(rgb):
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV_FULL)
    return hsv[..., 0].astype(float) * 360 / 256, hsv[..., 1].astype(float) / 255 * 100


def mask(name):
    m = np.asarray(Image.open(os.path.join(P, "masks", name)).convert("L")) > 127
    return m


wide, old = mask("stone-wide.png"), mask("stone.png")
fa = np.asarray(Image.open(os.path.join(P, "fixed-furniture.png")))[..., 3]
out = {"stone_wide_px": int(wide.sum()), "stone_old_px": int(old.sum()), "added_px": int((wide & ~old).sum())}
FILES = ["shell-v3-graded-v3c.png", "shell-furniture-v3-graded-v3c.png"] + [f"composite-set-{S}-v3-graded-v3c.png" for S in "ABC"]
mi = cv2.erode(wide.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
ring_in = wide & ~(cv2.erode(wide.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
ring_out = (cv2.dilate(wide.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0) & ~wide
lay = {S: np.asarray(Image.open(os.path.join(P, "layers/cushions", f"set-{S}.png")))[..., 3] for S in "ABC"}
for n in FILES:
    rgb = np.asarray(Image.open(os.path.join(P, n)).convert("RGB")).astype(float)
    L = lab(rgb)
    H, Sat = hsv_h(rgb)
    v = L[mi]
    front = v[:, 0] < np.percentile(v[:, 0], 30)
    top = v[:, 0] >= np.percentile(v[:, 0], 50)
    hv, sv = H[mi], Sat[mi]
    C = np.hypot(v[:, 1], v[:, 2])
    pink = (hv < 25) & (C > 3)
    b = L[..., 2]
    hi = wide & (b > 15)
    rec = dict(top_lab=[round(float(x), 1) for x in np.median(v[top], 0)], front_lab=[round(float(x), 1) for x in np.median(v[front], 0)],
               front_hsv_h=round(float(np.median(hv[front])), 1), top_hsv_h=round(float(np.median(hv[top])), 1),
               px_H_below_25_chroma_gt3=int(pink.sum()), b_max=round(float(b[wide].max()), 2), b_p999=round(float(np.percentile(b[wide], 99.9)), 2),
               px_b_over_15=int(hi.sum()), px_b_over_15_on_furniture_edge=int((hi & (fa > 0) & (fa < 255)).sum()),
               px_b_over_15_under_furniture=int((hi & (fa == 255)).sum()),
               edge_step_b=round(float(np.median(L[ring_in][:, 2]) - np.median(L[ring_out][:, 2])), 2),
               edge_step_a=round(float(np.median(L[ring_in][:, 1]) - np.median(L[ring_out][:, 1])), 2),
               ring_out_px_b_over_20=int((ring_out & (b > 20)).sum()),
               black_point_p005=round(float(np.percentile(L[..., 0], 0.5)), 2), L_min=round(float(L[..., 0].min()), 2))
    if "set-C" in n:
        dark = L[..., 0] < 11
        sd = cv2.blur(L[..., 0].astype(np.float32) ** 2, (9, 9)) - cv2.blur(L[..., 0].astype(np.float32), (9, 9)) ** 2
        sd = np.sqrt(np.clip(sd, 0, None))
        rec["below_L11"] = dict(px=int(dark.sum()), in_set_C_layer=int((dark & (lay["C"] > 0)).sum()), in_fixed_furniture=int((dark & (lay["C"] == 0) & (fa > 0)).sum()),
                                in_shell=int((dark & (lay["C"] == 0) & (fa == 0)).sum()), L_min=round(float(L[..., 0][dark].min()), 2) if dark.any() else None,
                                L_p1=round(float(np.percentile(L[..., 0][dark], 1)), 2) if dark.any() else None,
                                texture_sd_9px_median=round(float(np.median(sd[dark])), 2) if dark.any() else None,
                                share_flat_sd_lt_0_3=round(float((sd[dark] < 0.3).mean() * 100), 2) if dark.any() else None)
    out[n] = rec
json.dump(out, open(os.path.join(OUT, "data", "verify-v3c.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
ys, xs = np.nonzero(wide)
box = (int(xs.min()) - 20, int(ys.min()) - 20, int(xs.max()) + 20, int(ys.max()) + 20)
t = [Image.open(os.path.join(P, n)).convert("RGB").crop(box) for n in ("shell-v3-graded-v3b.png", "shell-furniture-v3-graded-v3c.png")]
o = Image.new("RGB", (t[0].width, t[0].height * 2 + 10), (40, 40, 40))
o.paste(t[0], (0, 0))
o.paste(t[1], (0, t[0].height + 10))
o.save(os.path.join(OUT, "overlays", "bench-v3c-100.jpg"), quality=90)
im = Image.open(os.path.join(P, "composite-set-C-v3-graded-v3c.png")).convert("RGB")
x0, y1 = box[0] + 20, box[3] - 20
lft = im.crop((x0 - 10, y1 - 70, x0 + 110, y1 + 10)).resize((480, 320), Image.NEAREST)
hy, hx = np.nonzero(wide & (fa > 0) & (fa < 255))
if len(hx):
    cx, cy = int(np.median(hx)), int(np.median(hy))
    arm = im.crop((cx - 60, cy - 40, cx + 60, cy + 40)).resize((480, 320), Image.NEAREST)
else:
    arm = Image.new("RGB", (480, 320), (40, 40, 40))
o = Image.new("RGB", (970, 320), (40, 40, 40))
o.paste(lft, (0, 0))
o.paste(arm, (490, 0))
o.save(os.path.join(OUT, "overlays", "bench-v3c-x4.jpg"), quality=90)
