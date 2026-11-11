#!/usr/bin/env python3
"""
qa-agent 2026-11-11: crops of the five R4 fixes at 100 % and x4 (nearest), r3 | r4 | raw, set B (the five regions are the same in A and C:
data/integrity.json). The raw render is registered here with the pass's recorded matrix (jobs.json / jobs-r3.json register_to_input,
inverse map, as recorded), then QA re-checks the registration on the crop (phase correlation of the high-pass against the r3 scene,
outside the products) and applies the residual shift; a per-crop gain (median scene / raw outside the products) puts it in the scene's
exposure. The raw is a reference of what the model drew, not a layer.
Writes crops/*.png and data/raw-registration.json.   ~/.venvs/motion/bin/python -I r4_crops.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
CR = os.path.join(OUT, "crops")
m3 = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b3 = {l_["id"]: l_ for l_ in m3["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}


def rgb(p):
    return np.asarray(Image.open(p).convert("RGB"))


S3 = rgb(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png"))
S4 = rgb(os.path.join(P2, "graded/default-scene-r4-set-B-graded-v3c.png"))
H, W = S3.shape[:2]
allprod = np.zeros((H, W), bool)
for l_ in m4["layers"] + m3["layers"]:
    if "product" in l_:
        allprod |= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] > 0
J = {j["id"]: j for j in json.load(open(os.path.join(P2, "jobs.json")))["jobs"]}
J.update({j["id"]: j for j in json.load(open(os.path.join(P2, "jobs-r3.json")))["jobs"]})
RAW = {"r3a": ("raw/r3a-seedream.png", "wm-ph2-fix-r3a-planter-basket"), "r3b": ("raw/r3b-seedream.png", "wm-ph2-fix-r3b-pendant"),
       "step2": ("raw/step2-seedream.png", "wm-ph2-step2-window-floor")}
reg_rec = {}


def raw_on(key, box):
    f, jid = RAW[key]
    M = np.array(J[jid]["register_to_input"], np.float32)
    raw = rgb(os.path.join(P2, f)).astype(np.float32)
    reg = cv2.warpAffine(raw, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    x0, y0, x1, y1 = box
    pad = 40
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    a = cv2.cvtColor(S3[Y0:Y1, X0:X1].astype(np.float32), cv2.COLOR_RGB2GRAY)
    b = cv2.cvtColor(reg[Y0:Y1, X0:X1], cv2.COLOR_RGB2GRAY)
    hp = lambda x: x - cv2.GaussianBlur(x, (0, 0), 3)  # noqa: E731
    bg = (~allprod[Y0:Y1, X0:X1]).astype(np.float32)
    win = cv2.createHanningWindow((X1 - X0, Y1 - Y0), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(hp(a) * bg, hp(b) * bg, win)
    T = np.float32([[1, 0, -dx], [0, 1, -dy]])
    reg = cv2.warpAffine(reg, T, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    m = ~allprod[Y0:Y1, X0:X1]
    g = np.array([np.median(S3[Y0:Y1, X0:X1, c][m]) / max(np.median(reg[Y0:Y1, X0:X1, c][m]), 1) for c in range(3)], np.float32)
    reg_rec[f"{key} {box}"] = dict(residual_shift_px=[round(float(dx), 2), round(float(dy), 2)], response=round(float(resp), 3),
                                   gain_rgb=[round(float(v), 3) for v in g])
    return np.clip(reg * g, 0, 255).astype(np.uint8)


def crop(img, box):
    x0, y0, x1, y1 = box
    return img[y0:y1, x0:x1]


def panel(imgs, labels, k, gap=6):
    ims = [Image.fromarray(i).resize((i.shape[1] * k, i.shape[0] * k), Image.NEAREST) for i in imgs]
    w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    h = max(i.height for i in ims) + 18
    out = Image.new("RGB", (w, h), (30, 30, 30))
    d = ImageDraw.Draw(out)
    x = 0
    for im, lb in zip(ims, labels):
        out.paste(im, (x, 18))
        d.text((x + 4, 3), lb, fill=(235, 235, 235))
        x += im.width + gap
    return out


def save(name, imgs, labels, k):
    p = os.path.join(CR, name)
    panel(imgs, labels, k).save(p)
    return p


made = []
# 1. the floor lamp's shade
b = (2290, 556, 2580, 760)
made.append(save("floor-lamp-shade-r3-r4-raw-100.png", [crop(S3, b), crop(S4, b), crop(raw_on("step2", b), b)],
                 ["r3 (lit)", "r4 (toned)", "raw step 2 (gain-matched)"], 1))
b = (2290, 550, 2580, 1380)
made.append(save("floor-lamp-whole-r3-r4-100.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 1))
b = (2396, 664, 2492, 712)
made.append(save("floor-lamp-collar-chain-r3-r4-x4.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 4))
b = (2318, 600, 2390, 650)
made.append(save("floor-lamp-shade-left-folds-r3-r4-raw-x4.png", [crop(S3, b), crop(S4, b), crop(raw_on("step2", b), b)],
                 ["r3", "r4", "raw step 2"], 4))
b = (2318, 660, 2400, 708)
made.append(save("floor-lamp-shade-lower-left-r3-r4-x4.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 4))
b = (2455, 690, 2480, 705)
made.append(save("floor-lamp-4b-pixel-2467-699-r3-r4-x8.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 8))
# 2. the pendant's canopy
b = (1560, 0, 1800, 200)
made.append(save("pendant-canopy-r3-r4-raw-100.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3b", b), b)], ["r3", "r4", "raw R3b"], 1))
b = (1628, 0, 1738, 78)
made.append(save("pendant-canopy-r3-r4-raw-x4.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3b", b), b)], ["r3", "r4", "raw R3b"], 4))
# 3. the basket's right edge
b = (1098, 1062, 1162, 1172)
made.append(save("basket-right-edge-r3-r4-raw-x4.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3a", b), b)], ["r3", "r4", "raw R3a"], 4))
b = (900, 720, 1220, 1290)
made.append(save("planter-basket-r3-r4-raw-100.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3a", b), b)], ["r3", "r4", "raw R3a"], 1))
# 4. the planter's left side and bottom
b = (925, 1022, 1000, 1112)
made.append(save("planter-left-side-r3-r4-raw-x4.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3a", b), b)], ["r3", "r4", "raw R3a"], 4))
b = (925, 1130, 1010, 1212)
made.append(save("planter-bottom-r3-r4-raw-x4.png", [crop(S3, b), crop(S4, b), crop(raw_on("r3a", b), b)], ["r3", "r4", "raw R3a"], 4))
# 5. the vase
b = (585, 770, 770, 1125)
made.append(save("vase-r3-r4-100.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 1))
made.append(save("vase-r3-r4-x2.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 2))
b = (625, 1048, 730, 1100)
made.append(save("vase-foot-contact-r3-r4-x4.png", [crop(S3, b), crop(S4, b)], ["r3", "r4"], 4))
b = (628, 870, 728, 960)
made.append(save("vase-neck-mouth-r4-x4.png", [crop(S4, b)], ["r4"], 4))
b = (600, 790, 740, 900)
made.append(save("vase-uncovered-area-r3-r4-x4.png", [crop(S3, b), crop(S4, b)], ["r3", "r4 (uncovered: base)"], 4))
json.dump(reg_rec, open(os.path.join(OUT, "data/raw-registration.json"), "w"), indent=1)
print("\n".join(made))
print(json.dumps(reg_rec, indent=1))
