"""
qa-agent 2026-11-07: v3 changes only the back wall? shell-v3.png against shell-v2.png and every composite v3 against v2 (ungraded):
changed pixels inside / outside the back wall (r4 clay index 5, the shared scratchpad copy, read only), and outside it also counted
after a 2 px dilation of the wall (edge antialias). Usage: ~/.venvs/motion/bin/python -I v3_vs_v2.py. Writes data/v3-vs-v2.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r4-shell-idx/M0.npz"
wall = cv2.resize((np.load(IDX)["idx"] == 5).astype(np.uint8), (2720, 1530), interpolation=cv2.INTER_NEAREST)
wall2 = cv2.dilate(wall, np.ones((5, 5), np.uint8)) > 0
out = {}
for a, b in (("shell-v2.png", "shell-v3.png"), ("shell-furniture-v2.png", "shell-furniture-v3.png"),
             ("composite-set-A-v2.png", "composite-set-A-v3.png"), ("composite-set-B-v2.png", "composite-set-B-v3.png"),
             ("composite-set-C-v2.png", "composite-set-C-v3.png")):
    x = np.asarray(Image.open(os.path.join(P, a)).convert("RGB")).astype(int)
    y = np.asarray(Image.open(os.path.join(P, b)).convert("RGB")).astype(int)
    d = np.abs(x - y).max(2) > 0
    out[b] = dict(changed=int(d.sum()), inside_wall=int((d & (wall > 0)).sum()), outside_wall=int((d & (wall == 0)).sum()),
                  outside_wall_dilated_2px=int((d & ~wall2).sum()))
json.dump(out, open(os.path.join(OUT, "data", "v3-vs-v2.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
