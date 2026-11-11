#!/usr/bin/env python3
"""
qa-agent 2026-11-11: five random combinations of the r4 layers (seed 1111): a cushion set from A/B/C and each of the 12 products on with
p = 0.75 (the five R4 products are forced to differ across the five, so each is seen both on and off at least once). Composed with the
manifest formula (QA's own stack), shown at 1/3 size with the R4 regions outlined. Writes crops/combos-r4-sheet.jpg and data/combos.json.
~/.venvs/motion/bin/python -I r4_combos.py
"""
import json
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
LD = os.path.join(P2, "layers")
man = json.load(open(os.path.join(LD, "manifest-r4.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
order = man["compose"]["order"]
products = [i for i in order if i != "base" and not i.endswith("-shadow")]
FIVE = ["floor-lamp", "vase", "planter", "basket", "pendant"]
u8 = lambda p: np.asarray(Image.open(p))  # noqa: E731
base = u8(os.path.join(LD, "base.png"))[..., :3].astype(np.float32)
lay, shd = {}, {}
for pid in products:
    if pid == "cushions":
        continue
    lay[pid] = u8(os.path.join(LD, byid[pid]["file"]))
    shd[pid] = u8(os.path.join(LD, byid[pid + "-shadow"]["file"]))[..., :3]
for s in "ABC":
    lay["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["layer"]))
    shd["set-" + s] = u8(os.path.join(LD, man["slot_cushions"]["sets"][s]["shadow"]))[..., :3]

rnd = random.Random(1111)
combos = []
patterns = [(1, 1, 0, 1, 1), (0, 1, 1, 0, 1), (1, 0, 1, 1, 0), (1, 1, 1, 0, 1), (0, 0, 0, 1, 1)]
for i in range(5):
    s = rnd.choice("ABC")
    on = {p: rnd.random() < 0.75 for p in products if p != "cushions"}
    for k, v in zip(FIVE, patterns[i]):
        on[k] = bool(v)
    combos.append(dict(set=s, on=[p for p in products if p == "cushions" or on[p]], off=[p for p in products if p != "cushions" and not on[p]]))
tiles = []
for c in combos:
    out = base.copy()
    for pid in products:
        if pid not in c["on"]:
            continue
        k = "set-" + c["set"] if pid == "cushions" else pid
        a = lay[k][..., 3:4].astype(np.float32) / 255
        out = np.clip(np.floor(out * shd[k].astype(np.float32) / 255 * (1 - a) + lay[k][..., :3].astype(np.float32) * a + 0.5), 0, 255)
    im = Image.fromarray(out.astype(np.uint8)).resize((907, 510), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 906, 16], fill=(20, 20, 20))
    d.text((4, 3), f"set {c['set']} | off: {', '.join(c['off']) or '-'}", fill=(240, 240, 240))
    tiles.append(im)
sheet = Image.new("RGB", (907 * 2 + 6, 510 * 3 + 12), (30, 30, 30))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 2) * 913, (i // 2) * 516))
sheet.save(os.path.join(OUT, "crops/combos-r4-sheet.jpg"), quality=90)
json.dump(dict(seed=1111, combos=combos), open(os.path.join(OUT, "data/combos.json"), "w"), indent=1)
print(json.dumps(combos, indent=1))
