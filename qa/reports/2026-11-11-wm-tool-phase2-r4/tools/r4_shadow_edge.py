#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the R4 contact-shadow edge fix (basket and planter): the shadow file's value against the distance from the product's
alpha (0-12 px), r3 vs r4, in the fix areas (the basket's right side rows 1080-1160 x 1120-1175; the planter's lower left and bottom rows
1100-1205 x 925-1000), outside the product, off the other products. A clean fix: monotone (darkest at the edge, lighter outward), no step
at the 3-4.5 px seam of the carried zone. Also the scene's L* on the same bins (r3, r4).
Writes data/shadow-edge.json.   ~/.venvs/motion/bin/python -I r4_shadow_edge.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
AREAS = {"basket": (1120, 1080, 1175, 1160), "planter": (925, 1100, 1000, 1205)}
res = {}
for k, (x0, y0, x1, y1) in AREAS.items():
    res[k] = {}
    for t in ("r3", "r4"):
        man = json.load(open(os.path.join(P2, f"layers/manifest-{t}.json")))
        by = {l_["id"]: l_ for l_ in man["layers"]}
        a = np.asarray(Image.open(os.path.join(P2, "layers", by[k]["file"])))[..., 3]
        sh = np.asarray(Image.open(os.path.join(P2, "layers", by[k + "-shadow"]["file"])))[..., :3].min(2).astype(np.float32) / 255
        others = np.zeros(a.shape, bool)
        for l_ in man["layers"]:
            if "product" in l_ and l_["id"] != k:
                others |= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] > 0
        S = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{t}-set-B-graded-v3c.png")).convert("RGB"))
        L = cv2.cvtColor(S.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
        d = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
        box = np.zeros(a.shape, bool)
        box[y0:y1, x0:x1] = True
        prof = []
        for r in range(1, 13):
            m = box & (a == 0) & ~others & (d > r - 1) & (d <= r)
            if m.sum() >= 5:
                prof.append([r, int(m.sum()), round(float(np.median(sh[m])), 3), round(float(np.median(L[m])), 2)])
        steps = [prof[i + 1][2] - prof[i][2] for i in range(len(prof) - 1)]
        res[k][t] = dict(profile_dist_px_n_shadow_L=prof, max_step_lighter=round(max(steps), 3), any_darker_outward=bool(min(steps) < -0.01))
        print(k, t, prof)
json.dump(res, open(os.path.join(OUT, "data/shadow-edge.json"), "w"), indent=1)
