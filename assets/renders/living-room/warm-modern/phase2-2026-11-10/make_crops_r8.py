#!/usr/bin/env python3
"""
make_crops_r8.py: the R8 before / after crops (render-agent, 2026-11-12; 0 tokens). Before = the R7 graded scenes and truths; after = the
R8 ones (graded/default-scene-r8-set-B, graded/variant-r8-<name>-set-B). Nearest neighbour at x 4 (the pixels as they are).
  crops-r8/<item>-100.png, crops-r8/<item>-<detail>-x4.png
  python3 make_crops_r8.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GRD = os.path.join(HERE, "graded")
OUT = os.path.join(HERE, "crops-r8")


def img(name):
    return Image.open(os.path.join(GRD, name)).convert("RGB")


FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)


def labelled(tiles, scale):
    """make_crops_r7.labelled(), copied: the tiles side by side, each with its label bar"""
    ims = []
    for lab, im in tiles:
        t = im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale != 1 else im
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
    S7, S8 = img("default-scene-r7-set-B-graded-v3c.png"), img("default-scene-r8-set-B-graded-v3c.png")
    V7 = {k: img(f"variant-r7-{k}-set-B-graded-v3c.png") for k in ("curtains-v2", "curtains-v3")}
    V8 = {k: img(f"variant-r8-{k}-set-B-graded-v3c.png") for k in ("curtains-v2", "curtains-v3")}
    items = {
        "travertine-marks": ([("R7 (marks between the feet)", S7), ("R8 (one soft ellipse per foot)", S8)], (1600, 1120, 1840, 1310),
                             {"between-feet": (1680, 1225, 1770, 1295)}),
        "curtain-3-specks": ([("R7 Linen", V7["curtains-v3"]), ("R8 Linen (specks out, L* by the card ratio)", V8["curtains-v3"])], (40, 560, 240, 780),
                             {"weave": (60, 600, 200, 740)}),
        "curtain-3-colour": ([("R7 Linen (L* 78.6)", V7["curtains-v3"]), ("R8 Linen (card ratio, pending the designer's eye)", V8["curtains-v3"]),
                              ("R8 180502 (default)", S8)], (0, 300, 340, 1530), {}),
        "curtain-3-corner": ([("R7 Linen", V7["curtains-v3"]), ("R8 Linen", V8["curtains-v3"])], (60, 1150, 280, 1380),
                             {"fringe": (100, 1195, 160, 1250)}),
        "curtains-bench": ([("R7 180502", S7), ("R8 180502", S8), ("R7 554205", V7["curtains-v2"]), ("R8 554205", V8["curtains-v2"]),
                            ("R7 Linen", V7["curtains-v3"]), ("R8 Linen", V8["curtains-v3"])], (110, 1150, 270, 1240),
                           {"break-contact": (180, 1160, 250, 1215)}),
    }
    for name, (tiles, box, x4) in items.items():
        labelled([(lab, im.crop(box)) for lab, im in tiles], 1).save(os.path.join(OUT, f"{name}-100.png"))
        for k, b in x4.items():
            labelled([(lab, im.crop(b)) for lab, im in tiles], 4).save(os.path.join(OUT, f"{name}-{k}-x4.png"))
        print(name)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    main()
