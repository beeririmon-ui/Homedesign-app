#!/usr/bin/env python3
"""
make_crops_r9.py: the R9 before / after crops (render-agent, 2026-11-12; 0 tokens). Before = R8 (graded/variant-r8-<name>-set-B, the R8
layers), after = R9 (graded/variant-r9-<name>-set-B, the R9 layers). Nearest neighbour (the pixels as they are).
  crops-r9/pendant-2-100.png, -x2.png             the lantern, R8 | R9
  crops-r9/pendant-2-ledge-x4.png                 the lower-left ledge (P2-1 step 2)
  crops-r9/pendant-2-right-edge-x4.png            the step and the facet on the right, and the ramp (P2-1 steps 2-3)
  crops-r9/pendant-2-right-edge-alpha-x4.png      the same, the alpha alone
  crops-r9/pendant-2-top-left-stop-x2.png, -x4    the top-left arc the stop rule kept (for the designer: the tier step that would need 2.25 px)
  crops-r9/curtain-3-edge-x4.png                  curtain 3's room-side soft edge at y 664-704 (5 of the 11 pixels): the truths, and the
                                                  layer's straight RGB where the specks were
  python3.12 -I make_crops_r9.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GRD, LAY = os.path.join(HERE, "graded"), os.path.join(HERE, "layers")
OUT = os.path.join(HERE, "crops-r9")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)


def labelled(tiles, scale):
    """make_crops_r8.labelled(), copied: the tiles side by side, each with its label bar"""
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
    m8 = json.load(open(os.path.join(LAY, "manifest-r8.json")))
    m9 = json.load(open(os.path.join(LAY, "manifest-r9.json")))
    v8 = {v["id"]: v for vs in m8["variants"].values() for v in vs}
    v9 = {v["id"]: v for vs in m9["variants"].values() for v in vs}
    T = {(t, k): Image.open(os.path.join(GRD, f"variant-{t}-{k}-set-B-graded-v3c.png")).convert("RGB") for t in ("r8", "r9") for k in ("pendant-v2", "curtains-v3")}
    L = {(t, k): Image.open(os.path.join(LAY, (v8 if t == "r8" else v9)[k]["file"])) for t in ("r8", "r9") for k in ("pendant-v2", "curtains-v3")}
    p8, p9 = T[("r8", "pendant-v2")], T[("r9", "pendant-v2")]
    lantern = (1540, 190, 1810, 365)
    pair = [("R8", p8), ("R9 (P2-1)", p9)]
    labelled([(a, b.crop(lantern)) for a, b in pair], 1).save(os.path.join(OUT, "pendant-2-100.png"))
    labelled([(a, b.crop(lantern)) for a, b in pair], 2).save(os.path.join(OUT, "pendant-2-x2.png"))
    labelled([(a, b.crop((1546, 280, 1600, 340))) for a, b in (("R8: the ledge", p8), ("R9: one convex flank", p9))], 4).save(os.path.join(OUT, "pendant-2-ledge-x4.png"))
    edge = (1755, 230, 1800, 320)
    labelled([(a, b.crop(edge)) for a, b in (("R8: step, facet", p8), ("R9", p9))], 4).save(os.path.join(OUT, "pendant-2-right-edge-x4.png"))
    alpha = [(a, Image.fromarray(np.asarray(L[(t, "pendant-v2")])[..., 3]).convert("RGB").crop(edge)) for a, t in (("R8 alpha (1-px ramp)", "r8"), ("R9 alpha", "r9"))]
    labelled(alpha, 4).save(os.path.join(OUT, "pendant-2-right-edge-alpha-x4.png"))
    tl = (1585, 196, 1665, 245)
    labelled([(a, b.crop(tl)) for a, b in (("R8", p8), ("R9: kept (stop rule), ramp only", p9))], 2).save(os.path.join(OUT, "pendant-2-top-left-stop-x2.png"))
    labelled([(a, b.crop(tl)) for a, b in (("R8", p8), ("R9: kept (stop rule), ramp only", p9))], 4).save(os.path.join(OUT, "pendant-2-top-left-stop-x4.png"))
    box = (236, 664, 276, 704)

    def straight(t):
        return Image.fromarray(np.asarray(L[(t, "curtains-v3")])[..., :3]).crop(box)
    labelled([("R8 truth", T[("r8", "curtains-v3")].crop(box)), ("R9 truth", T[("r9", "curtains-v3")].crop(box)),
              ("R8 layer RGB (straight)", straight("r8")), ("R9 layer RGB (straight)", straight("r9"))], 4).save(os.path.join(OUT, "curtain-3-edge-x4.png"))
    print(sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
