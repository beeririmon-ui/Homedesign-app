#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): does each new layer hold the product the model actually drew? For every product of passes 4' and 5': the raw
render registered to the canvas (jobs-r5.json's register_to_input, inverse map), the scene that the layer makes (the default scene for the
re-rendered defaults, the variant's truth for the variants) and the layer's alpha, side by side at x3: crops/raw-vs-cut-<name>-x3.png.

Then a number per product, 'lost product': in a band 1-12 px OUTSIDE the alpha (alpha == 0), the pixels where the registered raw differs
from the scene by dE76 > 8 (after a local gain match on the band's own median), as a share of the band; a high share along one side
means the model drew product there and the cut left it out (or a relit wall / shadow - read with the crop).
Writes data/raw-vs-cut.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
J = {j["pass_"]: j for j in json.load(open(os.path.join(P2, "jobs-r5.json")))["jobs"]}
vf = {v["id"]: v["file"] for vs in m5["variants"].values() for v in vs}


def raw(p):
    j = J[p]
    M = np.array(j["register_to_input"], np.float32)
    r = np.asarray(Image.open(os.path.join(REPO, j["raw"])).convert("RGB")).astype(np.float32)
    return cv2.warpAffine(r, M, (r.shape[1], r.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


RAW = {"4'": raw("4'"), "5'": raw("5'")}
ITEMS = [
    ("vase", "4'", b5["vase"]["file"], "graded/default-scene-r5-set-B-graded-v3c.png", (600, 850, 740, 1080)),
    ("curtains-v2", "4'", vf["curtains-v2"], "graded/variant-r5-curtains-v2-set-B-graded-v3c.png", (150, 300, 330, 700)),
    ("framed-art-v2", "4'", vf["framed-art-v2"], "graded/variant-r5-framed-art-v2-set-B-graded-v3c.png", (1490, 480, 2200, 820)),
    ("accent-sconces-v2 left", "4'", vf["accent-sconces-v2"], "graded/variant-r5-accent-sconces-v2-set-B-graded-v3c.png", (1385, 520, 1480, 625)),
    ("accent-sconces-v2 right", "4'", vf["accent-sconces-v2"], "graded/variant-r5-accent-sconces-v2-set-B-graded-v3c.png", (2235, 470, 2340, 590)),
    ("planter", "5'", b5["planter"]["file"], "graded/default-scene-r5-set-B-graded-v3c.png", (930, 740, 1150, 1205)),
    ("vase-v2", "5'", vf["vase-v2"], "graded/variant-r5-vase-v2-set-B-graded-v3c.png", (600, 850, 740, 1080)),
    ("accent-sconces-v3 left", "5'", vf["accent-sconces-v3"], "graded/variant-r5-accent-sconces-v3-set-B-graded-v3c.png", (1385, 520, 1490, 625)),
    ("accent-sconces-v3 right", "5'", vf["accent-sconces-v3"], "graded/variant-r5-accent-sconces-v3-set-B-graded-v3c.png", (2230, 470, 2345, 590)),
    ("pendant-v2", "5'", vf["pendant-v2"], "graded/variant-r5-pendant-v2-set-B-graded-v3c.png", (1550, 0, 1810, 375)),
]


def lab(x):
    return cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


res = {}
for name, p, lf, scene, box in ITEMS:
    x0, y0, x1, y1 = box
    A = np.asarray(Image.open(os.path.join(P2, "layers", lf)))[..., 3]
    S = np.asarray(Image.open(os.path.join(P2, scene)).convert("RGB")).astype(np.float32)
    R = RAW[p]
    a = A[y0:y1, x0:x1]
    s = S[y0:y1, x0:x1]
    r = R[y0:y1, x0:x1]
    out = (a == 0)
    d = cv2.distanceTransform(out.astype(np.uint8), cv2.DIST_L2, 5)
    band = out & (d >= 1) & (d <= 12)
    if band.any():
        g = np.array([np.median(s[..., c][band]) / max(np.median(r[..., c][band]), 1) for c in range(3)], np.float32)
        rg = np.clip(r * g, 0, 255)
        dE = np.linalg.norm(lab(rg) - lab(s), axis=2)
        lost = band & (dE > 8)
        h, w = a.shape
        sides = {}
        cx = (np.nonzero(a > 127)[1].mean()) if (a > 127).any() else w / 2
        for side, m in (("left", np.arange(w)[None, :] < cx), ("right", np.arange(w)[None, :] >= cx)):
            bb = band & m
            sides[side] = round(float((lost & m).sum() / max(1, bb.sum())), 3)
        res[name] = dict(box=list(box), band_px=int(band.sum()), lost_share=round(float(lost.sum() / band.sum()), 3), lost_share_by_side=sides,
                         gain=[round(float(v), 3) for v in g])
    sc = 3
    tiles = [np.repeat(np.repeat(t.astype(np.uint8), sc, 0), sc, 1) for t in (r, s, np.dstack([a, a, a]))]
    gap = np.full((tiles[0].shape[0], 6, 3), 90, np.uint8)
    Image.fromarray(np.concatenate([tiles[0], gap, tiles[1], gap, tiles[2]], 1)).save(
        os.path.join(OUT, "crops", f"raw-vs-cut-{name.replace(' ', '-')}-x3.png"))
    print(name, res.get(name))
json.dump(res, open(os.path.join(OUT, "data/raw-vs-cut.json"), "w"), indent=1)
