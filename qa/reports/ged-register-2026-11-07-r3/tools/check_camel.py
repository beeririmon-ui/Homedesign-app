"""qa-agent 2026-11-07: the "21 Camel" chenille cushion in warm-modern-A-ed5 against its SKU photo (view only, session scratchpad
wm-pilot-refs/, not copied into the repo). Lab of the cushion in the frame (its lit side, the box of the story point) and of the
photo's cushions (crops.json box), each against a neutral in its own picture (the frame: the white boucle cushion beside it in the same
light; the photo: the white sofa / throw under the cushions), and both side by side at the same size for the eye.
Writes data/camel.json and overlays/camel-*.jpg. Usage: ~/.venvs/motion/bin/python -I check_camel.py"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r3")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"
FR = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed5.png")


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def stats(img, box):
    x0, y0, x1, y1 = box
    p = lab(np.asarray(img.crop(box)).astype(float).reshape(-1, 3))
    L, a, b = np.median(p, 0)
    return dict(box=list(box), Lab=[round(float(L), 1), round(float(a), 1), round(float(b), 1)], C=round(float(np.hypot(a, b)), 1),
                h_deg=round(float(np.degrees(np.arctan2(b, a))), 1))


fr = Image.open(FR).convert("RGB")
W, H = fr.size
# the story point's box [0.378, 0.485, 0.455, 0.6] (data/story/story.json, warm-modern A, the camel point); the white boucle point [0.305, 0.395, 0.445, 0.6]
cam_box = (int(0.395 * W), int(0.48 * H), int(0.47 * W), int(0.58 * H))
white_box = (int(0.32 * W), int(0.48 * H), int(0.38 * W), int(0.57 * H))
ph = Image.open(REF + "A-cushions-cj-knitted-chenille-bean-green-21-camel-color.jpg").convert("RGB")
ph_cush = (750, 600, 1250, 1050)    # the right cushion's face (1500 x 1500 photo)
ph_neutral = (60, 1330, 1400, 1460)  # the off-white knit throw in front
out = dict(frame=dict(cushion=stats(fr, cam_box), white_boucle_beside=stats(fr, white_box)),
           sku_photo=dict(file="A-cushions-cj-knitted-chenille-bean-green-21-camel-color.jpg (CJ, view only)", cushion=stats(ph, ph_cush), neutral_throw=stats(ph, ph_neutral)),
           card_hex="#B8915F", card_hex_Lab=[round(float(v), 1) for v in lab(np.array([[0xB8, 0x91, 0x5F]], float))[0]])
for k in ("frame", "sku_photo"):
    c, n = out[k]["cushion"]["Lab"], out[k]["white_boucle_beside" if k == "frame" else "neutral_throw"]["Lab"]
    out[k]["cushion_minus_neutral"] = [round(c[i] - n[i], 1) for i in range(3)]
json.dump(out, open(os.path.join(OUT, "data", "camel.json"), "w"), indent=1)
a = fr.crop((int(0.36 * W), int(0.44 * H), int(0.50 * W), int(0.61 * H)))
b = ph.crop((20, 140, 1500, 1360))
h = 520
a = a.resize((int(a.width * h / a.height), h), Image.LANCZOS)
b = b.resize((int(b.width * h / b.height), h), Image.LANCZOS)
o = Image.new("RGB", (a.width + b.width + 10, h), (40, 40, 40))
o.paste(a, (0, 0))
o.paste(b, (a.width + 10, 0))
o.save(os.path.join(OUT, "overlays", "camel-frame-vs-sku-photo.jpg"), quality=90)
print(json.dumps(out, indent=1))
