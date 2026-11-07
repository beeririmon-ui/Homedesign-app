"""
qa-agent 2026-11-07: warm-modern-A-ed7 (render-agent's 0-token chroma flattening of the milk-tea boucle, ed7-milktea.json) against ed6
and ed5. (1) the change: pixels and bounding box against ed6; everything outside the ed5->ed6 cushion mask unchanged since ed5 (the
21 Camel included); (2) the two-tone: C* of the darkest fifth minus the lightest fifth (by L*) inside the cushion, ed5 / ed6 / ed7, the
SKU photo and the White boucle of the same SKU in this frame (as in register v4); (3) the colour against the White boucle (a*, b*) and
the SKU photos' relation (+0.9, +1.6); (4) the 'greyish troughs': inside the cushion, the share of pixels with C* < 6 (near grey for a
cream) in the darkest fifth, and the trough pixels' hue spread, ed6 / ed7 / the SKU photo; (5) crops at 100 % and x4 (ed6 | ed7 | photo).
Usage: ~/.venvs/motion/bin/python -I check_ed7.py. Writes data/ed7.json and overlays/ed7-cushion-100-x4.jpg.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r5")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def stats(px):
    L, C = px[:, 0], np.hypot(px[:, 1], px[:, 2])
    h = np.degrees(np.arctan2(px[:, 2], px[:, 1]))
    dark = L <= np.percentile(L, 20)
    light = L >= np.percentile(L, 80)
    return dict(lab=[round(float(v), 1) for v in np.median(px, 0)], C_dark_minus_C_light=round(float(np.median(C[dark]) - np.median(C[light])), 2),
                dark_fifth_share_C_lt_6_pct=round(float((C[dark] < 6).mean() * 100), 1), dark_fifth_C_median=round(float(np.median(C[dark])), 1),
                dark_fifth_hue_sd=round(float(np.std(h[dark])), 1), all_hue_sd=round(float(np.std(h)), 1))


raw = {k: np.asarray(Image.open(os.path.join(E, f"warm-modern-A-{k}.png")).convert("RGB")).astype(int) for k in ("ed5", "ed6", "ed7")}
cush = np.abs(raw["ed5"] - raw["ed6"]).max(2) > 0
d76 = np.abs(raw["ed6"] - raw["ed7"]).max(2) > 0
d57 = np.abs(raw["ed5"] - raw["ed7"]).max(2) > 0
ys, xs = np.nonzero(d76)
L = {k: lab(v.astype(float)) for k, v in raw.items()}
out = dict(changed_vs_ed6=int(d76.sum()), bbox_vs_ed6=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
           changed_vs_ed6_outside_cushion=int((d76 & ~cush).sum()), changed_vs_ed5_outside_cushion=int((d57 & ~cush).sum()))
for k in ("ed5", "ed6", "ed7"):
    out[k] = stats(L[k][cush])
white = L["ed7"][760:830, 900:990].reshape(-1, 3)
out["white_boucle"] = stats(white)
out["ed7_minus_white_ab"] = [round(out["ed7"]["lab"][i] - out["white_boucle"]["lab"][i], 1) for i in (1, 2)]
out["ed6_minus_white_ab"] = [round(out["ed6"]["lab"][i] - out["white_boucle"]["lab"][i], 1) for i in (1, 2)]
out["sku_milk_tea_minus_white_ab"] = [0.9, 1.6]
ph = lab(np.asarray(Image.open(REF + "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png").convert("RGB")).astype(float))
H, W = ph.shape[:2]
out["sku_photo"] = stats(ph[H // 4:3 * H // 4, W // 4:3 * W // 4].reshape(-1, 3))
json.dump(out, open(os.path.join(OUT, "data", "ed7.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
x0, x1, y0, y1 = out["bbox_vs_ed6"]
box = (x0 - 20, y0 - 20, x1 + 20, y1 + 20)
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 30
z = (cx - 50, cy - 50, cx + 50, cy + 50)
tiles = [Image.fromarray(raw[k].astype(np.uint8)).crop(box) for k in ("ed6", "ed7")]
tiles += [Image.fromarray(raw[k].astype(np.uint8)).crop(z).resize((400, 400), Image.NEAREST) for k in ("ed6", "ed7")]
phi = Image.open(REF + "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png").convert("RGB")
s = 290 / (0.8 * phi.width)
phs = phi.resize((int(phi.width * s), int(phi.height * s)), Image.LANCZOS)
tiles.append(phs.crop((phs.width // 2 - 50, phs.height // 2 - 50, phs.width // 2 + 50, phs.height // 2 + 50)).resize((400, 400), Image.NEAREST))
hh = max(t.height for t in tiles)
o = Image.new("RGB", (sum(t.width for t in tiles) + 10 * len(tiles), hh), (40, 40, 40))
x = 0
for t in tiles:
    o.paste(t, (x, 0))
    x += t.width + 10
o.save(os.path.join(OUT, "overlays", "ed7-cushion-100-x4.jpg"), quality=90)
