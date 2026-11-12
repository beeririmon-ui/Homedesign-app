#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R6/R7): the frozen shadow recipe, the measure of r5_shadow.py (copied; inputs changed to manifest-r7 / r6):
per slot with variants, the default's and each variant's shadow file (fingerprint = darkening 1-2 px out over 3-4.5 px out: < 1 is
extract.shadow_one's light strip; floor; depth; mass; the darkness centroid offset = direction); and the five defaults R7 changed, r7 vs r6.
Writes data/shadow.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
m5 = json.load(open(os.path.join(P2, "layers/manifest-r7.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r6.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
others = np.zeros((1530, 2720), bool)
for l_ in m5["layers"]:
    if "product" in l_:
        others |= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] > 5


def meas(lf, sf, own_slot_files):
    L = np.asarray(Image.open(os.path.join(P2, "layers", lf)))
    a = L[..., 3].astype(np.float32) / 255
    s = np.asarray(Image.open(os.path.join(P2, "layers", sf)).convert("RGB")).astype(np.float32).min(2) / 255
    prod = a > 0.02
    occ = others.copy()
    for f in own_slot_files:
        occ &= ~(np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3] > 5)
    occ &= ~prod
    dist = cv2.distanceTransform((~prod).astype(np.uint8), cv2.DIST_L2, 5)
    near = (dist >= 1) & (dist <= 2) & ~occ
    ring = (dist >= 3) & (dist <= 4.5) & ~occ
    # pair each near pixel with the ring: use the ring's shadow blurred (normalised) at the near pixel, so the ratio is local
    sh_ring = np.where(ring, 1 - s, 0).astype(np.float32)
    w = cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 2.0)
    rb = cv2.GaussianBlur(sh_ring, (0, 0), 2.0) / np.maximum(w, 1e-4)
    use = near & (w > 0.05) & (rb > 0.02)
    dk = s < 0.99
    ys, xs = np.nonzero(prod)
    dy, dx = np.nonzero(dk)
    wts = (1 - s)[dk]
    rec = dict(alpha_px=int(prod.sum()), shadow_px_lt_0_99=int(dk.sum()), min=round(float(s.min()), 3),
               p05=round(float(np.percentile(s[dk], 5)), 3) if dk.any() else None, median=round(float(np.median(s[dk])), 3) if dk.any() else None,
               mass_per_alpha_px=round(float((1 - s)[dk].sum() / max(1, prod.sum())), 3),
               centroid_offset_px=[round(float((dx * wts).sum() / wts.sum() - xs.mean()), 1), round(float((dy * wts).sum() / wts.sum() - ys.mean()), 1)] if dk.any() else None,
               edge_px=int(use.sum()))
    if use.any():
        rec["edge_ratio_1_2_over_3_4p5"] = round(float(np.median((1 - s)[use] / rb[use])), 3)
        rec["edge_darkening_1_2"] = round(float(np.median((1 - s)[use])), 3)
        rec["ring_darkening_3_4p5"] = round(float(np.median(rb[use])), 3)
    return rec


res = {}
for slot, vs in m5["variants"].items():
    files = [b5[slot]["file"]] + [v["file"] for v in vs]
    res[slot] = {"default": meas(b5[slot]["file"], b5[slot + "-shadow"]["file"], files)}
    for v in vs:
        res[slot][v["variant"]] = meas(v["file"], v["shadow"], files)
    print(slot, json.dumps(res[slot]))
for k in ("planter", "basket", "bowl", "candle-holders", "curtains"):
    res[k + " r7 vs r6"] = {"r7": meas(b5[k]["file"], b5[k + "-shadow"]["file"], [b5[k]["file"], b4[k]["file"]]),
                            "r6": meas(b4[k]["file"], b4[k + "-shadow"]["file"], [b5[k]["file"], b4[k]["file"]])}
    print(k, res[k + " r7 vs r6"])
for k in ("magazine-holder", "rug"):
    res[k] = meas(b5[k]["file"], b5[k + "-shadow"]["file"], [b5[k]["file"]])
json.dump(res, open(os.path.join(OUT, "data/shadow.json"), "w"), indent=1)
