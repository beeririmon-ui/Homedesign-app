#!/usr/bin/env python3
"""
make_crops_r6.py: the R6 review crops and sheet (render-agent, 2026-11-12; 0 tokens). Before = the R5 graded scenes (the default scene,
set B, and the R5 variant truths); after = the R6 ones. Each crop: before | after side by side, labelled.
  crops-r6/<item>-100.png    at 100 %
  crops-r6/<item>-x4.png     at x 4 (nearest neighbour: the pixels as they are)
  phase2-r6-sheet.jpg        the R6 default scene (set B) and every R6 change, before / after, at a size the owner can read
  python3 make_crops_r6.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GRD = os.path.join(HERE, "graded")
OUT = os.path.join(HERE, "crops-r6")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)


def img(name):
    return Image.open(os.path.join(GRD, name)).convert("RGB")


S5, S6 = img("default-scene-r5-set-B-graded-v3c.png"), img("default-scene-r6-set-B-graded-v3c.png")
T5 = {k: img(f"variant-r5-{k}-set-B-graded-v3c.png") for k in ("curtains-v2", "vase-v2", "pendant-v2", "framed-art-v2")}
T6 = {k: img(f"variant-r6-{k}-set-B-graded-v3c.png") for k in ("curtains-v2", "vase-v2", "pendant-v2", "framed-art-v2")}

# item: [(label, image)], box (x0, y0, x1, y1), the x4 boxes
ITEMS = {
    "curtains": ([("R5 default: 554205", S5), ("R6 default: 180502", S6), ("R6 variant 2: 554205", T6["curtains-v2"])], (0, 380, 340, 1530),
                 {"folds": (100, 700, 240, 800), "armchair-post": (150, 1150, 240, 1240)}),
    "vase-default": ([("R5", S5), ("R6", S6)], (560, 820, 790, 1110), {"body": (600, 900, 740, 1075)}),
    "vase-v2": ([("R5", T5["vase-v2"]), ("R6", T6["vase-v2"])], (560, 820, 790, 1110), {"body": (600, 900, 740, 1075)}),
    "pendant-v2": ([("R5", T5["pendant-v2"]), ("R6", T6["pendant-v2"])], (1500, 0, 1900, 420),
                   {"canopy": (1630, 0, 1730, 60), "cord": (1655, 40, 1700, 110), "right-edge": (1730, 200, 1805, 330),
                    "lantern-bottom": (1600, 300, 1760, 362)}),
    "framed-art-v2": ([("R5", T5["framed-art-v2"]), ("R6", T6["framed-art-v2"])], (1480, 470, 2200, 830),
                      {"print1-top-left": (1515, 522, 1610, 560), "print1-left-specks": (1515, 590, 1550, 700), "print1-bottom": (1525, 765, 1620, 800),
                       "print3-top-left": (1955, 500, 2050, 540), "print3-right": (2140, 600, 2172, 700)}),
    "magazine-holder-rods": ([("R5", S5), ("R6", S6)], (900, 1380, 1240, 1530), {"front-rod": (930, 1470, 1080, 1530), "back-rod": (1000, 1430, 1200, 1490)}),
}


def labelled(tiles, scale, resample):
    ims = []
    for lab, im in tiles:
        t = im.resize((im.width * scale, im.height * scale), resample) if scale != 1 else im
        bar = Image.new("RGB", (t.width, 24), (25, 25, 25))
        ImageDraw.Draw(bar).text((6, 3), lab, fill=(255, 255, 255), font=FONT)
        c = Image.new("RGB", (t.width, t.height + 24), (25, 25, 25))
        c.paste(bar, (0, 0))
        c.paste(t, (0, 24))
        ims.append(c)
    W = sum(i.width for i in ims) + 6 * (len(ims) - 1)
    out = Image.new("RGB", (W, max(i.height for i in ims)), (255, 255, 255))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + 6
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet_rows = []
    for item, (tiles, box, det) in ITEMS.items():
        im = labelled([(lab, t.crop(box)) for lab, t in tiles], 1, Image.NEAREST)
        im.save(os.path.join(OUT, f"{item}-100.png"))
        for dn, db in det.items():
            labelled([(lab, t.crop(db)) for lab, t in tiles], 4, Image.NEAREST).save(os.path.join(OUT, f"{item}-{dn}-x4.png"))
        sbox = (0, 380, 340, 1000) if item == "curtains" else box          # the curtains at 100 %: wide enough to read the cloth
        h = 620 if item == "curtains" else 360
        sc = [(lab, t.crop(sbox).resize((max(1, int((sbox[2] - sbox[0]) * h / (sbox[3] - sbox[1]))), h), Image.LANCZOS)) for lab, t in tiles]
        sheet_rows.append((item, labelled(sc, 1, Image.NEAREST)))
    # the sheet
    top = S6.resize((1600, 900), Image.LANCZOS)
    head = Image.new("RGB", (1600, 40), (25, 25, 25))
    ImageDraw.Draw(head).text((10, 8), "R6 default scene, set B (curtains 180502 now the default)", fill=(255, 255, 255), font=BIG)
    rows = [head, top]
    Wall = max([1600] + [r.width for _, r in sheet_rows])
    for item, r in sheet_rows:
        hb = Image.new("RGB", (Wall, 34), (25, 25, 25))
        ImageDraw.Draw(hb).text((8, 6), {"curtains": "Curtains: R5 default (554205) / R6 default (180502) / R6 variant 2 (554205, L* fixed)",
                                         "vase-default": "Vase (default): R5 / R6 (re-cut, straightened, sized to the card)",
                                         "vase-v2": "Vase 2: R5 / R6 (re-cut, neutral charcoal)",
                                         "pendant-v2": "Pendant 2: R5 / R6 (canopy whole, black cord, rings out)",
                                         "framed-art-v2": "Prints 2: R5 / R6 (seams, specks)",
                                         "magazine-holder-rods": "Magazine holder rods: R5 / R6 (soft edge)"}[item], fill=(255, 255, 255), font=FONT)
        rows += [hb, r]
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows) + 8 * len(rows)), (25, 25, 25))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    sheet.save(os.path.join(HERE, "phase2-r6-sheet.jpg"), quality=88)
    print(sorted(os.listdir(OUT)), sheet.size)


if __name__ == "__main__":
    main()
