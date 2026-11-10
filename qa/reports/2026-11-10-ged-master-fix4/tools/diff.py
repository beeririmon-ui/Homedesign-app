"""
qa-agent 2026-11-10: G-ED.8 on MB1 fix rounds 2-4: the current frames against the last ones QA checked (fix1): changed pixels (> 2 levels),
connected areas on a 15 px dilation with their boxes, against the regions declared in mb1-fix2.json, mb1-fix3.json and mb1-fix4.json.
Usage: ~/.venvs/motion/bin/python -I diff.py. Writes data/diff.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4")
f3, f4 = json.load(open(os.path.join(B, "mb1-fix3.json"))), json.load(open(os.path.join(B, "mb1-fix4.json")))
P = f4["passes"]
DECL = {"nordic": {"sconce_left ring": f3["nordic"]["sconce_left"]["ring"], "sconce_right ring": f3["nordic"]["sconce_right"]["ring"],
                   "cloth (mask, x 0-320)": [0, 640, 330, 1200], "P5 crop": P["P5"]["crop"], "P7 crop": P["P7"]["crop"]},
        "warm-modern": {"ghost box": f3["warm_modern"]["ghost_box"], "P6 crop": P["P6"]["crop"], "P8 crop": P["P8"]["crop"]}}
out = {}
for sub, a, b in (("nordic", "nordic-MB-A-fix1.png", "nordic-MB-A-fix4.png"), ("warm-modern", "warm-modern-MB-A-fix1.png", "warm-modern-MB-A-fix3.png")):
    x = np.asarray(Image.open(os.path.join(B, sub, a)).convert("RGB")).astype(int)
    y = np.asarray(Image.open(os.path.join(B, sub, b)).convert("RGB")).astype(int)
    d = np.abs(x - y).max(2) > 2
    n, lbl, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d.astype(np.uint8), np.ones((15, 15), np.uint8)), connectivity=8)
    comps = []
    for i in range(1, n):
        x0, y0, w, h, _ = st[i]
        px = int((d & (lbl == i)).sum())
        if px < 20:
            continue
        inside = [k for k, r in DECL[sub].items() if x0 >= r[0] - 20 and y0 >= r[1] - 20 and x0 + w <= r[2] + 20 and y0 + h <= r[3] + 20]
        comps.append(dict(bbox=[int(x0), int(y0), int(x0 + w), int(y0 + h)], changed_px=px, inside_declared=inside))
    out[sub] = dict(changed_px_gt2=int(d.sum()), components=sorted(comps, key=lambda c: -c["changed_px"]), declared=DECL[sub])
json.dump(out, open(os.path.join(OUT, "data", "diff.json"), "w"), indent=1)
for s, v in out.items():
    print(s, v["changed_px_gt2"], v["declared"])
    for c in v["components"]:
        print("   ", c)
