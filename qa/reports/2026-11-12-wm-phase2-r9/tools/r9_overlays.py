#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): the overlays for the eye. Every x2 crop of pendant 2 shows the WHOLE lantern, both flanks (the designer's rule,
docs/proposals/wm-pendant2-r9-eye-2026-11-12.md). Scenes are the set-B truths manifest-r8 / manifest-r9 name; upscales are LANCZOS
(what a browser's smooth scaling does at x2), the edge crops NEAREST (to see pixels).
  pendant-2-whole-x2-r8-r9.png        the whole lantern and the cord's lower part, x2, R8 | R9
  pendant-2-whole-x1-r9.png           the same at 100 % (x1 of the canvas) and at 0.74 (desktop x1), R9
  pendant-2-right-edge-x6-r8-r9.png   the right edge (theta -45 deg .. the bottom arc), x6: RGB and alpha, R8 | R9, QA's 50 % lines
  pendant-2-ledge-x4-r8-r9.png        the left flank (the ledge), x4, with QA's R8 (red) and R9 (green) 50 % lines
  pendant-2-top-left-arc-x4-r8-r9.png the top-left arc (kept under the stop rule), x4, with both lines and the convex hull (blue)
  curtain-3-f1-x8-r8-r9.png           four of the 11 F1 pixels, x8, layer over mid grey and the scene, R8 | R9
Writes overlays/.     ~/.venvs/motion/bin/python3.12 -I r9_overlays.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
OV = os.path.join(OUT, "overlays")
m8 = json.load(open(os.path.join(LD, "manifest-r8.json")))
m9 = json.load(open(os.path.join(LD, "manifest-r9.json")))
V8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
V9 = {v["id"]: v for vs in m9["variants"].values() for v in vs}


def img(p):
    return Image.open(p).convert("RGB")


T8 = img(os.path.normpath(os.path.join(LD, V8["pendant-v2"]["truth"])))
T9 = img(os.path.normpath(os.path.join(LD, V9["pendant-v2"]["truth"])))
L8 = np.asarray(Image.open(os.path.join(LD, V8["pendant-v2"]["file"])))
L9 = np.asarray(Image.open(os.path.join(LD, V9["pendant-v2"]["file"])))
O = np.load(os.path.join(OUT, "data/pendant-outlines.npz"), allow_pickle=False)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 20], fill=(25, 25, 25))
    d.text((6, 4), text, fill=(255, 255, 255))
    return im


def side(a, b, gap=8):
    s = Image.new("RGB", (a.width + b.width + gap, max(a.height, b.height)), (255, 255, 255))
    s.paste(a, (0, 0))
    s.paste(b, (a.width + gap, 0))
    return s


def lines(im, box, k, pts_list, cols, w=1):
    d = ImageDraw.Draw(im)
    x0, y0 = box[0], box[1]
    for P, c in zip(pts_list, cols):
        q = [((x - x0 + 0.5) * k - 0.5, (y - y0 + 0.5) * k - 0.5 + 20) for x, y in P if box[0] <= x < box[2] and box[1] <= y < box[3]]
        for a_, b_ in zip(q[:-1], q[1:]):
            if abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) < 4 * k:
                d.line([a_, b_], fill=c, width=w)
    return im


def crop(im, box, k, resample, text):
    c = im.crop(box).resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), resample)
    out = Image.new("RGB", (c.width, c.height + 20), (25, 25, 25))
    out.paste(c, (0, 20))
    return label(out, text)


# 1. the whole lantern, x2 (the designer's rule)
WHOLE = (1530, 150, 1820, 375)
side(crop(T8, WHOLE, 2, Image.LANCZOS, "R8, x2, whole lantern (set B truth)"), crop(T9, WHOLE, 2, Image.LANCZOS, "R9 (P2-1), x2, whole lantern")).save(os.path.join(OV, "pendant-2-whole-x2-r8-r9.png"))
# 2. x1 and desktop 0.74
c1 = crop(T9, (1480, 0, 1880, 420), 1, Image.LANCZOS, "R9, 100 % of the canvas")
c2 = T9.crop((1480, 0, 1880, 420)).resize((296, 311), Image.LANCZOS)
c2b = Image.new("RGB", (296, 331), (25, 25, 25))
c2b.paste(c2, (0, 20))
side(c1, label(c2b, "R9, 0.74 (desktop x1)")).save(os.path.join(OV, "pendant-2-whole-x1-r9.png"))
# 3. the right edge, x6, RGB and alpha, both lines
RE = (1755, 205, 1800, 330)
P8, P9 = O["r8_P"], O["r9_P"]
a8 = Image.fromarray(L8[..., 3]).convert("RGB")
a9 = Image.fromarray(L9[..., 3]).convert("RGB")
r8 = lines(crop(T8, RE, 6, Image.NEAREST, "R8 RGB x6"), RE, 6, [P8], [(230, 40, 40)])
r9 = lines(crop(T9, RE, 6, Image.NEAREST, "R9 RGB x6"), RE, 6, [P9], [(30, 170, 60)])
al8 = lines(crop(a8, RE, 6, Image.NEAREST, "R8 alpha x6"), RE, 6, [P8], [(230, 40, 40)])
al9 = lines(crop(a9, RE, 6, Image.NEAREST, "R9 alpha x6"), RE, 6, [P9], [(30, 170, 60)])
side(side(r8, r9), side(al8, al9)).save(os.path.join(OV, "pendant-2-right-edge-x6-r8-r9.png"))
# 4. the ledge, x4, both lines
LE = (1546, 270, 1600, 340)
side(lines(crop(T8, LE, 4, Image.NEAREST, "R8 x4 (red: R8 50 % line)"), LE, 4, [P8], [(230, 40, 40)]),
     lines(crop(T9, LE, 4, Image.NEAREST, "R9 x4 (red R8, green R9)"), LE, 4, [P8, P9], [(230, 40, 40), (30, 170, 60)])).save(os.path.join(OV, "pendant-2-ledge-x4-r8-r9.png"))
# 5. the top-left arc, x4, both lines and the convex hull of R9's outline
TL = (1566, 196, 1672, 252)
keep = O["r9_ok"] & ~O["r9_collar"]
H = cv2.convexHull(P9[keep].astype(np.float32)).reshape(-1, 2)
Hc = np.vstack([H, H[:1]])
dense = np.concatenate([np.linspace(Hc[i], Hc[i + 1], 40) for i in range(len(Hc) - 1)])
side(lines(crop(T8, TL, 4, Image.NEAREST, "R8 x4 top-left arc (red R8 line)"), TL, 4, [P8], [(230, 40, 40)]),
     lines(crop(T9, TL, 4, Image.NEAREST, "R9 x4 (red R8, green R9, blue convex hull)"), TL, 4, [dense, P8, P9], [(40, 90, 230), (230, 40, 40), (30, 170, 60)])
     ).save(os.path.join(OV, "pendant-2-top-left-arc-x4-r8-r9.png"))

# 6. curtain 3, four F1 pixels
G8 = np.asarray(Image.open(os.path.join(LD, V8["curtains-v3"]["file"])))
G9 = np.asarray(Image.open(os.path.join(LD, V9["curtains-v3"]["file"])))
C8 = img(os.path.normpath(os.path.join(LD, V8["curtains-v3"]["truth"])))
C9 = img(os.path.normpath(os.path.join(LD, V9["curtains-v3"]["truth"])))


def over_grey(G):
    a = G[..., 3:4].astype(np.float32) / 255
    return Image.fromarray(np.clip(G[..., :3] * a + 128 * (1 - a) + 0.5, 0, 255).astype(np.uint8))


tiles = []
for (x, y) in ((248, 23), (260, 677), (260, 690), (253, 997)):
    b = (x - 8, y - 8, x + 9, y + 9)
    row = side(side(crop(over_grey(G8), b, 8, Image.NEAREST, f"R8 layer/grey ({x},{y})"), crop(over_grey(G9), b, 8, Image.NEAREST, "R9 layer/grey")),
               side(crop(C8, b, 8, Image.NEAREST, "R8 scene"), crop(C9, b, 8, Image.NEAREST, "R9 scene")))
    tiles.append(row)
sheet = Image.new("RGB", (tiles[0].width, sum(t.height + 6 for t in tiles)), (255, 255, 255))
yy = 0
for t in tiles:
    sheet.paste(t, (0, yy))
    yy += t.height + 6
sheet.save(os.path.join(OV, "curtain-3-f1-x8-r8-r9.png"))
print("overlays written", sorted(os.listdir(OV)))
