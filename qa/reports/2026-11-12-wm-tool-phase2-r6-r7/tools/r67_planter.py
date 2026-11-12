#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R7): the planter's k = 0.78 against the designer's section 8 targets, on QA R5's own masks
(qa/reports/2026-11-11-wm-tool-phase2-r5/tools/r5_designer_targets.py, copied): pot = planter alpha 255 minus basket alpha > 0, minus the
soil under the rim, eroded 3 px; ring = wall only (rows < 1112), 15-40 px from the pot alpha, no product, x < 1000, at the pot's rows.
  (a')  whole-pot median L* vs the ring's median: 6-10 darker;   (a'') the lit shoulder rows 1060-1107 (pot mask): 74-79;
  bottom rows 1180-1191 (moves <= 3);   (b) C* <= ring + 1.5;   (c) hue within +-10 deg of the ring;
  (d) high-pass L* std (sigma 3) on the pot within -10 %..+5 % of r6;   k itself: the linear-light ratio r7/r6 of the ungraded pot
  (work-r7 vs work-r5 layers; R, G, B alike).
Writes data/planter.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
m7 = json.load(open(os.path.join(P2, "layers/manifest-r7.json")))
b7 = {l_["id"]: l_ for l_ in m7["layers"]}


def lab_img(p):
    return cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def summ(px):
    L, a, b = np.median(px, 0)
    return dict(L=round(float(L), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), px=int(len(px)))


def alpha(f):
    return np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3]


ap, ab = alpha(b7["planter"]["file"]), alpha(b7["basket"]["file"])
allprod = np.zeros(ap.shape, bool)
for l_ in m7["layers"]:
    if "product" in l_:
        allprod |= alpha(l_["file"]) > 0
res = {}
masks = None
for tag in ("r6", "r7"):
    S = lab_img(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png"))
    if masks is None:     # the masks from r6 (before), reused for r7 so both read the same pixels
        potzone = ((ap == 255) & ~(ab > 0))[:, 900:1150].sum(1) > 40
        potzone[:1000] = False
        rim = int(np.nonzero(potzone)[0].min())
        pot = (ap == 255) & ~(ab > 0)
        pot[:rim] = False
        soil = np.zeros(pot.shape, bool)
        soil[rim:rim + 16] = S[..., 0][rim:rim + 16] < 25
        pot &= ~soil
        pot = cv2.erode(pot.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        d = cv2.distanceTransform((~(ap > 0)).astype(np.uint8), cv2.DIST_L2, 5)
        ring = (d >= 15) & (d <= 40) & ~allprod
        ring[1112:] = False
        prow = np.nonzero(pot.any(1))[0]
        ring[: prow.min()] = False
        ring[:, 1000:] = False
        sh = pot.copy()
        sh[:1060] = False
        sh[1108:] = False
        bot = pot.copy()
        bot[:1180] = False
        bot[1192:] = False
        masks = dict(pot=pot, ring=ring, sh=sh, bot=bot, rim=rim)
    pot, ring = masks["pot"], masks["ring"]
    lo = cv2.GaussianBlur(S[..., 0], (0, 0), 3)
    r = dict(pot_whole=summ(S[pot]), ring=summ(S[ring]), shoulder_1060_1107=summ(S[masks["sh"]]), bottom_1180_1191=summ(S[masks["bot"]]),
             highpass_L_std=round(float(np.std((S[..., 0] - lo)[pot])), 3))
    r["a1_dL_whole_minus_ring"] = round(r["pot_whole"]["L"] - r["ring"]["L"], 2)
    r["b_dC_whole_minus_ring"] = round(r["pot_whole"]["C"] - r["ring"]["C"], 2)
    r["c_dh_whole_minus_ring"] = round((r["pot_whole"]["h"] - r["ring"]["h"] + 180) % 360 - 180, 1)
    res[tag] = r
    print(tag, r)
r6, r7 = res["r6"], res["r7"]
res["targets"] = {
    "(a') whole pot 6-10 darker than the ring": dict(value=r7["a1_dL_whole_minus_ring"], pass_=-10 <= r7["a1_dL_whole_minus_ring"] <= -6),
    "(a'') shoulder 74-79": dict(value=r7["shoulder_1060_1107"]["L"], pass_=74 <= r7["shoulder_1060_1107"]["L"] <= 79),
    "bottom moves <= 3": dict(value=round(r7["bottom_1180_1191"]["L"] - r6["bottom_1180_1191"]["L"], 2),
                              pass_=abs(r7["bottom_1180_1191"]["L"] - r6["bottom_1180_1191"]["L"]) <= 3),
    "(b) C* <= ring + 1.5": dict(value=r7["b_dC_whole_minus_ring"], pass_=r7["b_dC_whole_minus_ring"] <= 1.5),
    "(c) hue +-10 deg of the ring": dict(value=r7["c_dh_whole_minus_ring"], pass_=abs(r7["c_dh_whole_minus_ring"]) <= 10),
    "(d) high-pass std -10 %..+5 %": dict(value=round(r7["highpass_L_std"] / r6["highpass_L_std"] - 1, 4),
                                          pass_=-0.10 <= r7["highpass_L_std"] / r6["highpass_L_std"] - 1 <= 0.05)}
# k in linear light on the ungraded layers (work-r5 -> work-r7), interior pot pixels
u5 = np.asarray(Image.open(os.path.join(P2, "work-r5/layers/planter.png"))).astype(np.float64)
u7 = np.asarray(Image.open(os.path.join(P2, "work-r7/layers/planter.png"))).astype(np.float64)


def lin(c):
    c = c / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


inner = masks["pot"] & (u5[..., 3] == 255) & (u7[..., 3] == 255)
inner &= (u5[..., :3].min(2) > 20)
k = lin(u7[..., :3][inner]) / np.maximum(lin(u5[..., :3][inner]), 1e-6)
res["k_linear"] = dict(px=int(inner.sum()), median_RGB=[round(float(np.median(k[:, i])), 4) for i in range(3)],
                       p5_p95=[round(float(np.percentile(k, 5)), 4), round(float(np.percentile(k, 95)), 4)])
print(res["targets"], res["k_linear"])
json.dump(res, open(os.path.join(OUT, "data/planter.json"), "w"), indent=1)
