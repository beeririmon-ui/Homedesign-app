#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the vase's right and left flanks after the R4 scale (rows 1000-1065), row by row: the soft-edge pixels (alpha 0.15-0.85) of the
r4 layer against the colour a clean edge would have there, a * (the vase 3-5 px inside) + (1 - a) * (the scene 3-5 px outside, i.e. what is
really behind it now). A positive dL = the edge is lighter than its own mix (window light carried down over the dark rail), negative =
darker (the rail carried down onto the light bench). Same for r3 (the edge where the render drew it).
Writes data/vase-edge.json.   ~/.venvs/motion/bin/python -I r4_vase_edge.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
res = {}
for tag in ("r3", "r4"):
    man = json.load(open(os.path.join(P2, f"layers/manifest-{tag}.json")))
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    a = np.asarray(Image.open(os.path.join(P2, "layers", byid["vase"]["file"])))[..., 3].astype(np.float32) / 255
    S = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png")).convert("RGB"))
    L = cv2.cvtColor(S.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
    for side in ("right", "left"):
        rows = []
        for y in range(1000, 1066):
            r = a[y]
            xs = np.nonzero(r > 0.5)[0]
            if not len(xs):
                continue
            if side == "right":
                xe = int(xs.max())
                soft = [x for x in range(xe - 2, xe + 4) if 0.15 <= r[x] <= 0.85]
                Li, Lo = float(np.median(L[y, xe - 5:xe - 2])), float(np.median(L[y, xe + 4:xe + 7]))
            else:
                xe = int(xs.min())
                soft = [x for x in range(xe - 3, xe + 3) if 0.15 <= r[x] <= 0.85]
                Li, Lo = float(np.median(L[y, xe + 3:xe + 6])), float(np.median(L[y, xe - 6:xe - 3]))
            if not soft:
                continue
            d = [float(L[y, x] - (r[x] * Li + (1 - r[x]) * Lo)) for x in soft]
            rows.append([y, round(Li, 1), round(Lo, 1), round(max(d, key=abs), 1)])
        dl = np.array([q[3] for q in rows])
        res[f"{tag} {side}"] = dict(rows=rows, n_rows=len(rows), rows_lighter_by_8=int((dl > 8).sum()), rows_darker_by_8=int((dl < -8).sum()),
                                    max_lighter=round(float(dl.max()), 1), max_darker=round(float(dl.min()), 1))
        print(tag, side, {k: v for k, v in res[f"{tag} {side}"].items() if k != "rows"})
json.dump(res, open(os.path.join(OUT, "data/vase-edge.json"), "w"), indent=1)
for q in res["r4 left"]["rows"]:
    print(q)
