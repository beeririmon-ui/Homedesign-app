#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the vase after R4, two places at x6: (1) its right flank against the window's bottom rail (rows 1005-1065), r3 | r4 |
base.png (what the shrink uncovers must be the base, untouched); (2) the pale lobe at its lower left (rows 1000-1075), r3 | r4 | the
alpha of r4. Writes crops/vase-right-flank-r3-r4-base-x6.png, crops/vase-lower-left-lobe-r3-r4-alpha-x6.png and data/vase-uncovered.json
(the scene r4 against base.png where the r3 vase was and the r4 vase is not).   ~/.venvs/motion/bin/python -I r4_vase_look.py
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
m3 = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b3 = {l_["id"]: l_ for l_ in m3["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
rgb = lambda p: np.asarray(Image.open(p).convert("RGB"))  # noqa: E731
S3 = rgb(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png"))
S4 = rgb(os.path.join(P2, "graded/default-scene-r4-set-B-graded-v3c.png"))
base = rgb(os.path.join(P2, "layers/base.png"))
cur = np.asarray(Image.open(os.path.join(P2, "layers", b4["curtains"]["file"])))
a3 = np.asarray(Image.open(os.path.join(P2, "layers", b3["vase"]["file"])))[..., 3]
a4 = np.asarray(Image.open(os.path.join(P2, "layers", b4["vase"]["file"])))[..., 3]
sh4 = np.asarray(Image.open(os.path.join(P2, "layers", b4["vase-shadow"]["file"])))[..., :3].min(2)


def strip(imgs, k):
    g = np.full((imgs[0].shape[0], 3, 3), 30, np.uint8)
    parts = []
    for i, im in enumerate(imgs):
        if im.ndim == 2:
            im = np.repeat(im[..., None], 3, 2)
        parts += [im, g] if i < len(imgs) - 1 else [im]
    s = np.concatenate(parts, 1)
    return Image.fromarray(s).resize((s.shape[1] * k, s.shape[0] * k), Image.NEAREST)


y0, y1, x0, x1 = 1005, 1065, 680, 735
strip([S3[y0:y1, x0:x1], S4[y0:y1, x0:x1], base[y0:y1, x0:x1]], 6).save(os.path.join(OUT, "crops/vase-right-flank-r3-r4-base-x6.png"))
y0, y1, x0, x1 = 995, 1080, 615, 670
strip([S3[y0:y1, x0:x1], S4[y0:y1, x0:x1], a4[y0:y1, x0:x1]], 6).save(os.path.join(OUT, "crops/vase-lower-left-lobe-r3-r4-alpha-x6.png"))
unc = (a3 > 0) & (a4 == 0) & (sh4 == 255) & (cur[..., 3] == 0)
d = np.abs(S4.astype(int) - base.astype(int)).max(2)
res = dict(uncovered_px=int(unc.sum()), uncovered_scene_vs_base_max_level=int(d[unc].max()), uncovered_px_differing=int((d[unc] > 0).sum()))
json.dump(res, open(os.path.join(OUT, "data/vase-uncovered.json"), "w"), indent=1)
print(res)
