#!/usr/bin/env python3
"""sheet.py: the QA sheet of CM and CK (render-agent, 2026-11-27). Row 1: HC (the accepted corridor, its 16:9 frame), CM, CK at the same
width. Row 2: x2 crops of what changed or what QA should look at (the openings, the slot, the jambs). JPEG q90.
  python3 sheet.py"""
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.dirname(HERE)
REPO = "/home/user/homedesign-app"
HC = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-18/hc-frame.png")
W = 900
def load(p):
    return Image.open(p).convert("RGB")
def fit(im, w=W):
    return im.resize((w, int(round(im.size[1] * w / im.size[0]))), Image.LANCZOS)
def label(im, t):
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    d.rectangle([0, 0, 12 + 12 * len(t), 34], fill=(255, 255, 255))
    d.text((6, 5), t, fill=(20, 20, 20), font=f)
    return im
def crop2(p, box, t):
    im = load(p).crop(box)
    im = im.resize((im.size[0] * 2, im.size[1] * 2), Image.LANCZOS)
    return label(fit(im, 440), t)
hc, cm, ck = load(HC), load(os.path.join(OUT, "CM-frame.png")), load(os.path.join(OUT, "CK-frame.png"))
row1 = [label(fit(hc), "HC (accepted, 2026-11-18)"), label(fit(cm), "CM"), label(fit(ck), "CK")]
cmf, ckf = os.path.join(OUT, "CM-frame.png"), os.path.join(OUT, "CK-frame.png")
row2 = [crop2(cmf, (740, 60, 1180, 420), "CM x2: bedroom door, leaf"), crop2(cmf, (1180, 260, 1620, 620), "CM x2: girl's door"),
        crop2(ckf, (0, 300, 440, 660), "CK x2: boy's room (K-boy fb16)"), crop2(ckf, (700, 250, 1140, 610), "CK x2: hall, living (pecan)"),
        crop2(ckf, (1480, 300, 1920, 660), "CK x2: bath (B1 fb16)"), crop2(ckf, (300, 0, 740, 360), "CK x2: roof-light slot")]
h1 = max(i.size[1] for i in row1); h2 = max(i.size[1] for i in row2)
sheet = Image.new("RGB", (3 * W + 40, h1 + h2 + 30), (246, 244, 240))
for k, im in enumerate(row1):
    sheet.paste(im, (10 + k * (W + 10), 10))
x = 10
for im in row2:
    sheet.paste(im, (x, h1 + 20)); x += im.size[0] + 10
if x > sheet.size[0]:
    pass
sheet.save(os.path.join(OUT, "qa-sheet.jpg"), quality=90)
print(sheet.size)
