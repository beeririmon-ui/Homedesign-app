#!/usr/bin/env python3
"""
qa-agent 2026-11-11: combinations. The tool has no empty slot and every slot but the cushions has one variant today, so the real
combination space is the three cushion sets (all composed and swap-diffed in p2_integrity.py). This sheet adds the two dependency
probes that matter for steps 4-7 and for future basket / planter variants: the scene without the basket (the pot's hidden part is not
in the planter layer) and without the planter (what the basket stands against). Composed from the layers (P1 path), set B.
Writes overlays/combos-sheet.jpg and crops/combo-no-basket-x2.jpg.   ~/.venvs/motion/bin/python -I p2_combos.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
order = [i for i in man["compose"]["order"] if i != "base" and not i.endswith("-shadow")]
rd = lambda p: np.asarray(Image.open(p)).astype(np.float64)
base = rd(os.path.join(P2, "layers/base.png"))


def comp(s, skip=()):
    out = base.copy()
    for k in order:
        if k in skip:
            continue
        if k == "cushions":
            Lr, Sh = rd(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])), rd(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["shadow"]))
        else:
            Lr, Sh = rd(os.path.join(P2, "layers", byid[k]["file"])), rd(os.path.join(P2, "layers", byid[k + "-shadow"]["file"]))
        a = Lr[..., 3:4] / 255
        out = np.floor(out * Sh / 255 * (1 - a) + Lr[..., :3] * a + 0.5)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


combos = [("set A, all 12", "A", ()), ("set B, all 12 (default)", "B", ()), ("set C, all 12", "C", ()),
          ("set B without the basket (probe)", "B", ("basket",)), ("set B without the planter (probe)", "B", ("planter",))]
tiles = []
for name, s, skip in combos:
    im = comp(s, skip)
    if skip == ("basket",):
        c = im.crop((880, 700, 1240, 1260))
        c.resize((c.width * 2, c.height * 2), Image.LANCZOS).save(os.path.join(OUT, "crops", "combo-no-basket-x2.jpg"), quality=92)
    t = im.resize((680, 383), Image.LANCZOS)
    d = ImageDraw.Draw(t)
    d.rectangle([0, 0, 680, 18], fill=(255, 255, 255))
    d.text((4, 3), name, fill=(0, 0, 0))
    tiles.append(t)
sheet = Image.new("RGB", (680 * 3 + 20, 383 * 2 + 10), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 3) * 690, (i // 3) * 393))
sheet.save(os.path.join(OUT, "overlays", "combos-sheet.jpg"), quality=88)
print("ok")
