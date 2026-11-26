#!/usr/bin/env python3
"""sheet.py: qa-sheet-m0w.jpg: the rebuilt default frame of M0-W at x1; x2 crops of the table, the sofa, the two wall lights and the
left floor group (from the 2720 canvas stack, so x2 is real pixels); the old M0 default frame beside the new one."""
import os, sys
import cv2, numpy as np
from PIL import Image, ImageDraw
import hwlib as L
sys.path.insert(0, os.path.join(L.REPO, "assets/renders/tools/finish"))
import finish as F
D = L.FB13
rd = lambda p, m="RGB": np.asarray(Image.open(p).convert(m))
import json
man = json.load(open(os.path.join(D, "layers", "manifest.json"))) if os.path.exists(os.path.join(D, "layers", "manifest.json")) else json.load(open(os.path.join(L.OUT, "manifest-parts.json")))
base = rd(os.path.join(D, "plate-PW.png"))
full = F.compose(base, [(rd(os.path.join(D, m["layer"]), "RGBA"), rd(os.path.join(D, m["shadow"]))) for m in man["layers"]], [rd(os.path.join(D, m["file"])) for m in man["light"]])
st = dict(frame_box=list(L.FB))
new = rd(os.path.join(D, "default-frame-m0w.png"))
old = rd(os.path.join(L.REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10/default-frame-basket-set-B.png"))
x0, y0, x1, y1 = L.FB
k = (x1 - x0) / 1920.0

def crop2(fx0, fy0, fx1, fy1):
    """a region of the 1920 frame at x2, from the canvas pixels"""
    w, h = int((fx1 - fx0) * 2), int((fy1 - fy0) * 2)
    M = np.float32([[k / 2, 0, x0 + fx0 * k], [0, k / 2, y0 + fy0 * k]])
    return cv2.warpAffine(full, M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

def lab(im, t):
    im = Image.fromarray(im); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 9 + 7 * len(t), 20], fill=(0, 0, 0)); d.text((5, 4), t, fill=(255, 255, 255)); return im

W = 2640
sheet = Image.new("RGB", (W, 1080 + 560 + 680), (24, 24, 24))
sheet.paste(lab(new, "M0-W default frame, rebuilt from the layers, x1 (1920 x 1080)"), (0, 0))
sheet.paste(lab(np.asarray(Image.fromarray(old).resize((640, 360), Image.LANCZOS)), "old M0 (phase 2, basket)"), (1960, 0))
sheet.paste(lab(np.asarray(Image.fromarray(new).resize((640, 360), Image.LANCZOS)), "new M0-W (default frame)"), (1960, 360))
sheet.paste(lab(F.frame_view(base, st, (640, 360)), "the plate P-W (empty room, lamps off)"), (1960, 720))
crops = dict(table=(700, 790, 1360, 1070), sconce_l=(770, 300, 1100, 580), sconce_r=(1390, 290, 1720, 570), sofa=(700, 560, 1360, 900), left=(170, 700, 830, 1040))
c = {n: crop2(*b) for n, b in crops.items()}
sheet.paste(lab(c["table"], "x2: the table group (Olia, bowl, candle holders) on the rug"), (0, 1080))
sheet.paste(lab(c["sconce_l"], "x2: left wall light, first print, leaf shadow"), (1320, 1080))
sheet.paste(lab(c["sconce_r"], "x2: right wall light, floor lamp"), (1980, 1080))
sheet.paste(lab(c["sofa"], "x2: the sofa, set B, the throw"), (0, 1640))
sheet.paste(lab(c["left"], "x2: basket, olive pot, magazine holder, armchair"), (1320, 1640))
sheet.save(os.path.join(D, "qa-sheet-m0w.jpg"), quality=88)
for n, im in c.items():
    Image.fromarray(im).save(os.path.join(L.OUT, f"z2-{n}.jpg"), quality=90)
print("sheet", sheet.size, os.path.getsize(os.path.join(D, "qa-sheet-m0w.jpg")))
