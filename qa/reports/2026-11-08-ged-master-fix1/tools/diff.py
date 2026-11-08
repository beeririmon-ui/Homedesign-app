"""
qa-agent 2026-11-08: G-ED.8 on the MB1 fix round: fix1 against MB-A, per frame: changed pixels (> 2 levels in any channel), their
connected components on a 15 px dilation, each component's bounding box and size, against the regions render-agent declares in
mb1-fix.json (the code rings / bboxes and the pass crops). Usage: ~/.venvs/motion/bin/python -I diff.py. Writes data/diff.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1")
fx = json.load(open(os.path.join(B, "mb1-fix.json")))
DECL = {"nordic": {"sconce_left": fx["code"]["nordic"]["sconce_left"]["ring"], "sconce_right": fx["code"]["nordic"]["sconce_right"]["ring"],
                   "P1 throw": fx["passes"]["P1"]["crop"], "P2 nightstand": fx["passes"]["P2"]["crop"], "P3 sill": fx["passes"]["P3"]["crop"],
                   "planter (mask)": None, "chair cloth (mask)": None},
        "warm-modern": {"sconce_left": fx["code"]["warm_modern"]["sconce_left"]["region_bbox"], "sconce_right": fx["code"]["warm_modern"]["sconce_right"]["region_bbox"],
                        "P4 nightstand": fx["passes"]["P4"]["crop"]}}
out = {}
for sub, a, b in (("nordic", "nordic-MB-A.png", "nordic-MB-A-fix1.png"), ("warm-modern", "warm-modern-MB-A.png", "warm-modern-MB-A-fix1.png")):
    x = np.asarray(Image.open(os.path.join(B, sub, a)).convert("RGB")).astype(int)
    y = np.asarray(Image.open(os.path.join(B, sub, b)).convert("RGB")).astype(int)
    if x.shape != y.shape:
        out[sub] = {"shape_mismatch": [list(x.shape), list(y.shape)]}
        continue
    d = np.abs(x - y).max(2) > 2
    n, lbl, st, _ = cv2.connectedComponentsWithStats((cv2.dilate(d.astype(np.uint8), np.ones((15, 15), np.uint8))), connectivity=8)
    comps = []
    for i in range(1, n):
        x0, y0, w, h, area = st[i]
        px = int((d & (lbl == i)).sum())
        if px < 20:
            continue
        inside = []
        for k, r in DECL[sub].items():
            if r and x0 >= r[0] - 20 and y0 >= r[1] - 20 and x0 + w <= r[2] + 20 and y0 + h <= r[3] + 20:
                inside.append(k)
        comps.append(dict(bbox=[int(x0), int(y0), int(x0 + w), int(y0 + h)], changed_px=px, inside_declared=inside))
    out[sub] = dict(changed_px_gt2=int(d.sum()), components=sorted(comps, key=lambda c: -c["changed_px"]), declared=DECL[sub])
json.dump(out, open(os.path.join(OUT, "data", "diff.json"), "w"), indent=1)
for s, v in out.items():
    print(s, v.get("changed_px_gt2"))
    for c in v.get("components", [])[:15]:
        print("   ", c)
