#!/usr/bin/env python3
"""qa-agent 2026-11-12 (R7): the halo metric of r67_halo.py (analyse(), unchanged) restricted to the curtain cut: box x 0-260, y 1180-1445
(the hem, the spill corner and the stone contact), on the three curtain options' set-B truths. Writes data/hem-halo.json."""
import json
import os
import numpy as np
import cv2
from PIL import Image
src = open(os.path.join(os.path.dirname(__file__), "r67_halo.py")).read()
ns = {}
exec(src[src.index("def Lof"):src.index("def alphas_of")], {"np": np, "cv2": cv2, "Image": Image, "os": os,
     "OUT": "/home/user/homedesign-app/qa/reports/2026-11-12-wm-tool-phase2-r6-r7"}, ns)
P2 = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/phase2-2026-11-10"
m = json.load(open(os.path.join(P2, "layers/manifest-r7.json")))
b = {l_["id"]: l_ for l_ in m["layers"]}
V = {v["id"]: v for vs in m["variants"].values() for v in vs}
ff = np.asarray(Image.open("/home/user/homedesign-app/assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/fixed-furniture.png"))[..., 3] > 0
res = {}
for key, f, t in (("default", b["curtains"]["file"], "graded/default-scene-r7-set-B-graded-v3c.png"),
                  ("curtains-v2", V["curtains-v2"]["file"], "graded/variant-r7-curtains-v2-set-B-graded-v3c.png"),
                  ("curtains-v3", V["curtains-v3"]["file"], "graded/variant-r7-curtains-v3-set-B-graded-v3c.png")):
    img = np.asarray(Image.open(os.path.join(P2, t)).convert("RGB"))
    A = np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3]
    above = cv2.dilate(ff.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    res[key] = ns["analyse"](ns["Lof"](img), A, f"hem-{key}", img, above, box=(0, 1180, 260, 1445), save=True)
    print(key, res[key])
json.dump(res, open("/home/user/homedesign-app/qa/reports/2026-11-12-wm-tool-phase2-r6-r7/data/hem-halo.json", "w"), indent=1)
