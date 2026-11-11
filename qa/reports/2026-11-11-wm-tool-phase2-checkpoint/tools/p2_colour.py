#!/usr/bin/env python3
"""
qa-agent 2026-11-11: colour of each default's main material, the layer (r3 set-B scene, alpha 255 eroded 2 px, the material picked
by rows / hue) against the supplier's SKU photo (box on the product's main material; the photos stay in the scratchpad, never in the
repo) and the card hex. Lab D65 (OpenCV), median; dE00; HSL for the magazine holder's straps against the Bible caramel band
(H 20-30, S 40-58, L 32-48). The room light is not the studio light: L* is reported, the judgement leans on hue and chroma.
Writes data/colour.json.   ~/.venvs/motion/bin/python -I p2_colour.py
"""
import colorsys
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/ph2/refs-dl"
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
S = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
LABS = cv2.cvtColor(S.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def lab_of(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32).reshape(-1, 1, 3) / 255, cv2.COLOR_RGB2LAB).reshape(-1, 3)


def de00(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hbp = (h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    SL = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hbp - 275) / 25) ** 2)))
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH)))


def summ(lab):
    L, a, b = np.median(lab, 0)
    return dict(L=round(float(L), 1), a=round(float(a), 1), b=round(float(b), 1), C=round(float(np.hypot(a, b)), 1),
                h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1))


def hexlab(h):
    h = h.lstrip("#")
    return summ(lab_of(np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)]], np.uint8)))


def layer_px(k, rows=None, extra=None):
    a = np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3]
    m = cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if rows:
        r = np.zeros_like(m)
        r[rows[0]:rows[1]] = True
        m &= r
    if extra is not None:
        m &= extra
    return LABS[m], m


def photo_px(f, box, keep=None):
    im = np.asarray(Image.open(os.path.join(REF, f)).convert("RGB"))
    c = im[box[1]:box[3], box[0]:box[2]].reshape(-1, 3)
    lab = lab_of(c)
    if keep is not None:
        lab = lab[keep(lab, c)]
    return lab


def ring_wall(m, r0=15, r1=40):
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    return LABS[(d >= r0) & (d <= r1)]


res = {}
items = {
    "planter": dict(layer=dict(rows=(1040, 1195), extra_x=(940, 1000)), photo=("planter/sku.jpg", (120, 130, 640, 640), "not_bg_text"), hex="#BDB6A8"),
    "basket": dict(layer=dict(rows=(1065, 1230)), photo=("basket/sku.jpeg", (120, 90, 380, 450), "not_bg_text"), hex="#B99B74"),
    "vase": dict(layer=dict(rows=(930, 1075)), photo=("vase/sku.jpeg", (300, 250, 480, 600), None), hex="#EEECE8"),
    "curtains": dict(layer=dict(rows=(100, 1400)), photo=("curtains/img1.jpg", (100, 100, 900, 650), None), hex=None),
    "rug": dict(layer=dict(rows=(1250, 1530)), photo=("rug/sku.jpeg", (60, 40, 480, 340), None), hex="#E4D5C2"),
    "bowl": dict(layer=dict(rows=None), photo=("bowl/sku.jpg", (150, 60, 290, 190), None), hex="#2F2F2E"),
    "candle-holders": dict(layer=dict(rows=(1215, 1280)), photo=("candle-holders/sku.jpg", (430, 450, 670, 900), "not_bg_text"), hex="#E3D6C2"),
    "accent-sconces": dict(layer=dict(rows=None, light=True), photo=("accent-sconces/sku.jpg", (345, 110, 480, 500), None), hex="#D9C7A3"),
    "pendant": dict(layer=dict(rows=(200, 380)), photo=("pendant/img0.jpg", (250, 30, 750, 300), "not_bg_text"), hex="#EEE9E0"),
    "floor-lamp shade": dict(key="floor-lamp", layer=dict(rows=(585, 700)), photo=("floor-lamp/sku.jpeg", (420, 140, 560, 290), None), hex="#F1E8D8"),
    "floor-lamp pole": dict(key="floor-lamp", layer=dict(rows=(1000, 1250), dark=True), photo=None, hex="#4A3528"),
}
for name, it in items.items():
    k = it.get("key", name)
    lo = it["layer"]
    extra = None
    if "extra_x" in lo:
        extra = np.zeros(S.shape[:2], bool)
        extra[:, lo["extra_x"][0]:lo["extra_x"][1]] = True
    lab, m = layer_px(k, lo.get("rows"), extra)
    if lo.get("light"):
        lab = lab[lab[:, 0] > 55]
    if lo.get("dark"):
        lab = lab[lab[:, 0] < 45]
    rec = dict(layer=summ(lab), layer_px=int(len(lab)))
    rec["wall_ring_15_40"] = summ(ring_wall(m)) if m.any() else None
    if it["photo"]:
        f, box, keep = it["photo"]
        kf = None
        if keep == "not_bg_text":
            kf = lambda L, c: (L[:, 0] < 93) & (L[:, 0] > 35)
        pl = photo_px(f, box, kf)
        rec["photo"] = summ(pl)
        rec["photo_file"] = f
        rec["dE00_layer_vs_photo"] = round(de00([rec["layer"][x] for x in "Lab"], [rec["photo"][x] for x in "Lab"]), 2)
        rec["dC"] = round(rec["layer"]["C"] - rec["photo"]["C"], 1)
        dh = (rec["layer"]["h"] - rec["photo"]["h"] + 180) % 360 - 180
        rec["dh_deg"] = round(dh, 1)
    if it["hex"]:
        rec["card_hex"] = it["hex"]
        rec["card_hex_lab"] = hexlab(it["hex"])
        rec["dE00_layer_vs_card_hex"] = round(de00([rec["layer"][x] for x in "Lab"], [rec["card_hex_lab"][x] for x in "Lab"]), 2)
    res[name] = rec

# magazine holder: straps by hue in the layer and in the Orange SKU photo; tubes
a = np.asarray(Image.open(os.path.join(P2, "layers", byid["magazine-holder"]["file"])))[..., 3]
m = cv2.erode((a == 255).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
hsv = cv2.cvtColor(S, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
H = hsv[..., 0] * 360 / 256
sat = hsv[..., 1] / 255
strap = m & (H >= 5) & (H <= 45) & (sat > 0.3) & (LABS[..., 0] > 20)
tube = m & (LABS[..., 0] < 22) & (sat < 0.35)


def hsl_med(rgb):
    r, g, b = np.median(rgb, 0) / 255
    h, l_, s = colorsys.rgb_to_hls(r, g, b)
    return dict(H=round(h * 360, 1), S=round(s * 100, 1), L=round(l_ * 100, 1))


im = np.asarray(Image.open(os.path.join(REF, "magazine-holder/sku-orange.jpg")).convert("RGB"))
hp = cv2.cvtColor(im, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
Hp, Sp = hp[..., 0] * 360 / 256, hp[..., 1] / 255
Lp = cv2.cvtColor(im.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
strap_p = (Hp >= 5) & (Hp <= 45) & (Sp > 0.3) & (Lp > 20)
tube_p = (Lp < 30) & (Sp < 0.35)
spec_p = tube_p.copy()
res["magazine-holder"] = dict(
    straps_layer=dict(px=int(strap.sum()), lab=summ(LABS[strap]), hsl=hsl_med(S[strap])),
    straps_photo_orange=dict(px=int(strap_p.sum()), lab=summ(cv2.cvtColor(im.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[strap_p]), hsl=hsl_med(im[strap_p])),
    bible_caramel_hsl="H 20-30, S 40-58, L 32-48 (#A0663A)",
    tubes_layer=dict(px=int(tube.sum()), L_p50_p99=[round(float(np.percentile(LABS[..., 0][tube], q)), 1) for q in (50, 99)]),
    tubes_layer_highlight_share_L_gt60=round(float(((LABS[..., 0] > 60) & m & ~strap).sum() / max(1, (m & ~strap).sum())), 3),
    card_hex="#D9822B (label reading)")
for side in ("straps_layer", "straps_photo_orange"):
    h = res["magazine-holder"][side]["hsl"]
    res["magazine-holder"][side]["in_caramel_band"] = dict(H=bool(20 <= h["H"] <= 30), S=bool(40 <= h["S"] <= 58), L=bool(32 <= h["L"] <= 48))
res["magazine-holder"]["dE00_straps_layer_vs_photo"] = round(de00([res["magazine-holder"]["straps_layer"]["lab"][x] for x in "Lab"],
                                                                  [res["magazine-holder"]["straps_photo_orange"]["lab"][x] for x in "Lab"]), 2)
json.dump(res, open(os.path.join(OUT, "data/colour.json"), "w"), indent=1)
for k, v in res.items():
    print(k, json.dumps(v))
