#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): six random combinations (seed 1111) of the variants x cushion sets, composed with QA's own compose (the manifest
formula, one rounding per product), for the eye: crops/combos-r5-sheet.jpg (each scene at 50 %) and crops/combo-<n>-<area>-100.png for
the window corner and the wall, where most of the variants sit. Writes data/combos.json.
"""
import json
import os
import random

import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
LD = os.path.join(P2, "layers")
m = json.load(open(os.path.join(LD, "manifest-r5.json")))
by = {l_["id"]: l_ for l_ in m["layers"]}
order = m["compose"]["order"]
products = [i for i in order if i != "base" and not i.endswith("-shadow")]
base = np.asarray(Image.open(os.path.join(LD, "base.png")).convert("RGB")).astype(np.float32)


def u8(f):
    return np.asarray(Image.open(os.path.join(LD, f)))


def compose(s, repl):
    out = base.copy()
    for pid in products:
        if pid == "cushions":
            L, S = u8(m["slot_cushions"]["sets"][s]["layer"]), u8(m["slot_cushions"]["sets"][s]["shadow"])[..., :3]
        elif pid in repl:
            v = next(v for v in m["variants"][pid] if v["id"] == repl[pid])
            L, S = u8(v["file"]), u8(v["shadow"])[..., :3]
        else:
            L, S = u8(by[pid]["file"]), u8(by[pid + "-shadow"]["file"])[..., :3]
        a = L[..., 3:4].astype(np.float32) / 255
        out = np.floor(out * S.astype(np.float32) / 255 * (1 - a) + L[..., :3].astype(np.float32) * a + 0.5)
    return np.clip(out, 0, 255).astype(np.uint8)


rnd = random.Random(1111)
slots = sorted(m["variants"])
combos = []
for i in range(6):
    repl = {}
    for s in slots:
        ch = [None] + [v["id"] for v in m["variants"][s]]
        c = rnd.choice(ch)
        if c:
            repl[s] = c
    combos.append(dict(n=i + 1, set=rnd.choice("BAC"), variants=repl))
# make sure every variant appears at least once
seen = {v for c in combos for v in c["variants"].values()}
for s in slots:
    for v in m["variants"][s]:
        if v["id"] not in seen:
            combos[len(seen) % 6]["variants"][s] = v["id"]
            seen = {v_ for c in combos for v_ in c["variants"].values()}
tiles = []
for c in combos:
    img = compose(c["set"], c["variants"])
    Image.fromarray(img[300:1530, 0:1300]).save(os.path.join(OUT, "crops", f"combo-{c['n']}-window-corner-100.png"))
    Image.fromarray(img[0:900, 1300:2720]).save(os.path.join(OUT, "crops", f"combo-{c['n']}-wall-100.png"))
    t = Image.fromarray(img).resize((1360, 765), Image.LANCZOS)
    d = ImageDraw.Draw(t)
    lab = f"#{c['n']} set {c['set']}: " + (", ".join(c["variants"].values()) or "all defaults")
    d.rectangle([0, 0, 1360, 22], fill=(20, 20, 20))
    d.text((6, 4), lab, fill=(255, 255, 255))
    tiles.append(t)
sheet = Image.new("RGB", (1360 * 2 + 8, 765 * 3 + 16), (40, 40, 40))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 2) * 1368, (i // 2) * 773))
sheet.save(os.path.join(OUT, "crops", "combos-r5-sheet.jpg"), quality=88)
json.dump(combos, open(os.path.join(OUT, "data/combos.json"), "w"), indent=1)
print(json.dumps(combos, indent=1))
