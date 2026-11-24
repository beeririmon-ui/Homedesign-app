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
    """K-G3 (QA 2026-11-24): the Beech cup built from the walnut cup's light, not its grain. The walnut's shading on a 4 px normalised
    blur (no grain, no gloss), its contrast compressed to 0.6 round the lit half, and 15 % of the fine grain kept; the lit half's median
    set to the Beech photo (L*78.2 C*31.8 h68), the chroma following L* (C*/L* of the photo), one hue: matte, even, light wood"""
    a = rgba[..., 3].astype(np.float64) / 255
    lab = C.to_lab(rgba[..., :3].astype(np.float64) / 255)
    L = lab[..., 0]
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
    cc = np.hypot(lab[..., 1], lab[..., 2])
    # the boy's olive band seen between the pencils was cut into the layer: it goes (the girl's band shows through)
    bg = (a > 0) & (hh > 90) & (hh < 140) & (cc > 4)
    a = np.where(bg, 0.0, a)
    # the cup: the clay's cup, and the dark walnut inside its opening (under the pencils), which is the cup's inside, not a pencil
    inside = C.dil(ids == 49, 1) & (L < 45) & (hh > 35) & (hh < 75) & (a > 0)
    cup = ((C.dil(ids == 48, 3) & ~C.dil(ids == 49, 1)) | inside) & (a > 0)
    w = cup.astype(np.float64)
    Ls = C.blur(L * w, 4) / np.maximum(C.blur(w, 4), 1e-4)
    core = cup & (a > 0.98)
    lit = core & (Ls >= np.median(Ls[core]))
    m_lit = float(np.median(Ls[lit]))
    Lt, Ct, ht = 78.2, 31.8, 68.0
    Ln = np.clip(Lt + 0.6 * (Ls - m_lit) + 0.15 * (L - Ls), 30, 92)
    t = K.from_lch(100.0, Ct / Lt * 100.0, ht)
    an, bn = t[1] * Ln / 100.0, t[2] * Ln / 100.0
    lab[..., 0] = np.where(cup, Ln, lab[..., 0])
    lab[..., 1] = np.where(cup, an, lab[..., 1])
    lab[..., 2] = np.where(cup, bn, lab[..., 2])
    rgb = KC.floor_lab(np.clip(C.from_lab(lab), 0, 1), a > 0)
    # the walnut's soft edge was unmixed against the olive band: as light beech it reads as a pale rim, so the cup's edge is pulled in 1 px
    rim = cup & ~C.ero(cup & (a > 0.98), 1)
    a = np.where(rim, a * 0.45, a)
    out = np.dstack([C.q(rgb), C.q(a)])
    out[..., :3][out[..., 3] == 0] = 0
    lab2 = C.to_lab(rgb)
    lit2 = core & (lab2[..., 0] >= np.median(lab2[..., 0][core]))
    med = np.median(lab2[lit2], 0)
    return out, dict(cup_px=int(cup.sum()), olive_background_removed_px=int(bg.sum()), inside_px=int(inside.sum()), lit_half_Lab=[round(float(v), 1) for v in med],
                     photo_Lab=[round(float(v), 1) for v in K.from_lch(Lt, Ct, ht)],
                     dE00_lit_half=round(float(C.de00(tuple(med), tuple(K.from_lch(Lt, Ct, ht)))), 2),
                     method=recolour_cup.__doc__.split("K-G3 (QA 2026-11-24): ")[1].strip())


def clean_olive_edge(rgba):
    """K-G2 (QA 2026-11-24): the boy's layers were cut on his olive band; at their edge (alpha under 1, and 2 px inside it) an olive
    tint (h 90-140, C* over 4) takes the product's own colour spread from inside"""
    a = rgba[..., 3] > 0
    solid = rgba[..., 3] >= 250
    edge = a & ~C.ero(solid, 2)
    rgb = rgba[..., :3].astype(np.float64) / 255
    lab = C.to_lab(rgb)
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
    cc = np.hypot(lab[..., 1], lab[..., 2])
    ol = edge & (h > 90) & (h < 140) & (cc > 4)
    if ol.any():
        fill = KC.KC.spread(rgb, (C.ero(solid, 2) & ~ol).astype(np.float64), (2.0, 5.0, 12.0))
        rgb = np.where(ol[..., None], fill, rgb)
    out = rgba.copy()
    out[..., :3] = C.q(rgb)
    out[..., :3][out[..., 3] == 0] = 0
    return out, int(ol.sum())


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
        if key in ("pen-cup", "bookends"):
            rgba, n_ = clean_olive_edge(rgba)
            rec.setdefault("olive edge cleaned px", {})[key] = n_
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
