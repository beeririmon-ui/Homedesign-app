#!/usr/bin/env python3
"""
girl_from_boy.py: the girl's family layers made by code from the boy's (ב.6 2: "the family slots above 1.25 (the pendant, the blind,
prints A and B) are moved by code from the boy, because the background is the same; the Type A art goes into the frames by code"),
render-agent, 2026-11-24; 0 tokens. The same camera and shell (+3.63 in Y), so a layer, its shadow and the lamp's light carry over pixel
for pixel; what changes:
  - the prints: the boy's frames with their blank canvases (kept by kids_art.py), the girl's Type A panels placed by kids_art.py;
  - the pen cup: the same listing in Beech (ד.2 row 7). The SKU photos of Walnut and Beech are one drawing in two woods, so the cup's
    pixels (the clay's cup region, not the pencils) are recoloured as the sample slot's variants: Y x (Y(78.2) / Y(41.9)), the hue and
    chroma of the Beech photo (L*78.2 C*31.8 h68) at the light's scale;
  - the toy cars are the boy's only and are not carried over.
Also carried, unchanged: the bookshelf (two ledge pairs, the face-out books, frame C on the top ledge), the bookends and their books.
  python3 girl_from_boy.py
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402
import kids_art as KA  # noqa: E402
from kids_passes import PRODUCTS, GIRL_FROM_BOY  # noqa: E402

C = K.C


def recolour_cup(rgba, ids):
    a = rgba[..., 3].astype(np.float64) / 255
    lab = C.to_lab(rgba[..., :3].astype(np.float64) / 255)
    cup = C.dil(ids == 48, 3) & ~C.dil(ids == 49, 1) & (a > 0)
    med = np.median(lab[cup & (a > 0.6)], 0)
    s = med[0] / 41.9
    tgt = K.from_lch(0, 31.8 * s, 68)
    Yr = ((78.2 + 16) / 116) ** 3 / (((41.9 + 16) / 116) ** 3)
    Y = np.where(lab[..., 0] > 8, ((lab[..., 0] + 16) / 116) ** 3, lab[..., 0] / 903.3) * Yr
    L = np.where(Y > 216 / 24389, 116 * np.cbrt(np.minimum(Y, 1.0)) - 16, 903.3 * Y)
    lab[..., 0] = np.where(cup, L, lab[..., 0])
    lab[..., 1] = np.where(cup, lab[..., 1] - med[1] + tgt[1], lab[..., 1])
    lab[..., 2] = np.where(cup, lab[..., 2] - med[2] + tgt[2], lab[..., 2])
    rgb = KC.floor_lab(np.clip(C.from_lab(lab), 0, 1), a > 0)
    out = np.dstack([C.q(rgb), rgba[..., 3]])
    out[..., :3][out[..., 3] == 0] = 0
    return out, dict(cup_px=int(cup.sum()), walnut_rendered_Lab=[round(float(v), 1) for v in med],
                     beech_Lab=[round(float(v), 1) for v in np.median(C.to_lab(rgb)[cup & (a > 0.6)], 0)])


def main():
    sb, sg = K.ST["boy"], K.ST["girl"]
    mb = KC.load_man("boy")
    mg = KC.load_man("girl")
    ids = K.ids("K-girl")
    rec = {}
    for key in GIRL_FROM_BOY:
        lb = [l for l in mb["layers"] if l["key"] == key and l.get("default", True)][0]
        slot, pid, z, cids, sku = PRODUCTS["girl"][key]
        lp = os.path.join(sg, "layers", slot, pid + ".png")
        sp = os.path.join(sg, "shadows", slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        src = os.path.join(sb, lb["layer"])
        if key == "framed-prints":
            src = os.path.join(K.SCR, "boy-framed-prints-blank.png")
        rgba = np.asarray(Image.open(src)).copy()
        if key == "pen-cup":
            rgba, rec["pen-cup"] = recolour_cup(rgba, ids)
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        shutil.copy(os.path.join(sb, lb["shadow"]), sp)
        mg["layers"] = [l for l in mg["layers"] if not (l["key"] == key and l.get("default", True))]
        e = dict(lb, product=pid, sku=sku, layer=os.path.relpath(lp, sg), shadow=os.path.relpath(sp, sg),
                 source=f"the boy's layer by code (tools/girl_from_boy.py, ב.6): {lb['source']}", pass_="from-boy", passes=["from-boy"] + lb.get("passes", []))
        mg["layers"].append(e)
    for li in mb["light"]:
        dst = os.path.join(sg, li["file"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(os.path.join(sb, li["file"]), dst)
        mg["light"] = [x for x in mg["light"] if x["file"] != li["file"]]
        mg["light"].append(dict(li, pass_="from-boy", note="the boy's pendant light, the same lamp at the same place"))
    mg.setdefault("code_fixes", {})["from the boy"] = dict(rec, carried=GIRL_FROM_BOY, not_carried=["toy-cars (the boy's only)"])
    KC.save_man("girl", mg)
    if os.path.exists(os.path.join(K.SCR, "wm-kids", "art", "girl-0.png")) or True:
        KA.place("girl")
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
