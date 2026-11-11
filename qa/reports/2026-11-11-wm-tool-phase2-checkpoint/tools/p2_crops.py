#!/usr/bin/env python3
"""
qa-agent 2026-11-11: crops for the checkpoint. For each of the 12 defaults: the r3 set-B scene at 100% around the product, the same at x4
on its key edge, and (scratchpad only, never in the repo: supplier images are not committed) a side-by-side with the supplier's SKU photo.
Repo output: crops/<slot>-100.jpg, crops/<slot>-x4-<spot>.png. Scratchpad: cmp-<slot>.jpg.
~/.venvs/motion/bin/python -I p2_crops.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
REFS = os.path.join(SCR, "ph2/refs-dl")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
B = Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB")
base = Image.open(os.path.join(P2, "layers/base.png")).convert("RGB")

boxes = {  # x0, y0, x1, y1 on the 2720 canvas, around the product (from the alpha boxes in data/integrity.json)
    "curtains": (0, 0, 330, 1530), "framed-art": (1480, 470, 2200, 830), "accent-sconces-left": (1380, 470, 1480, 620),
    "accent-sconces-right": (2250, 470, 2340, 620), "vase": (590, 780, 760, 1110), "rug": (430, 1180, 2720, 1530),
    "floor-lamp": (2290, 550, 2580, 1370), "planter-basket": (900, 720, 1220, 1260), "magazine-holder": (900, 1360, 1240, 1530),
    "bowl": (1880, 1200, 2120, 1370), "candle-holders": (1700, 1120, 1900, 1300), "pendant": (1490, 0, 1860, 420)}
ref = {"curtains": "curtains/img5.jpg", "framed-art": "framed-art/sku.jpg", "accent-sconces-left": "accent-sconces/sku.jpg",
       "accent-sconces-right": "accent-sconces/sku.jpg", "vase": "vase/sku.jpeg", "rug": "rug/sku.jpeg", "floor-lamp": "floor-lamp/sku.jpeg",
       "planter-basket": "planter/sku.jpg", "magazine-holder": "magazine-holder/sku-orange.jpg", "bowl": "bowl/sku.jpg",
       "candle-holders": "candle-holders/sku.jpg", "pendant": "pendant/img0.jpg"}
for k, bx in boxes.items():
    c = B.crop(bx)
    c.save(os.path.join(OUT, "crops", f"{k}-100.jpg"), quality=92)
    h = 520
    cs = c.resize((max(1, int(c.width * h / c.height)), h), Image.LANCZOS)
    rp = os.path.join(REFS, ref[k])
    if os.path.exists(rp):
        r = Image.open(rp).convert("RGB")
        r = r.resize((max(1, int(r.width * h / r.height)), h), Image.LANCZOS)
        cv = Image.new("RGB", (cs.width + r.width + 10, h), "white")
        cv.paste(r, (0, 0))
        cv.paste(cs, (r.width + 10, 0))
        cv.save(os.path.join(SCR, f"qa-p2-cmp-{k}.jpg"), quality=90)
print("ok")
