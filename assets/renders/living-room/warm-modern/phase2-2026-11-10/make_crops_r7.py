#!/usr/bin/env python3
"""
make_crops_r7.py: the R7 review crops and the sheet of every option (render-agent, 2026-11-12; 0 tokens). Before = the R6 graded scenes;
after = the R7 ones (graded/default-scene-r7-set-B and the R7 variant truths).
  crops-r7/<item>-100.png    at 100 %
  crops-r7/<item>-x4.png     at x 4 (nearest neighbour: the pixels as they are)
  phase2-r7-sheet.jpg        the R7 default scene (set B), every option of every slot side by side, the R7 changes before / after, and
                             the two 7' products that failed (the raw render, marked: not layers)
  python3 make_crops_r7.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GRD = os.path.join(HERE, "graded")
OUT = os.path.join(HERE, "crops-r7")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)


def img(name):
    return Image.open(os.path.join(GRD, name)).convert("RGB")


S6, S7 = img("default-scene-r6-set-B-graded-v3c.png"), img("default-scene-r7-set-B-graded-v3c.png")
MAN = json.load(open(os.path.join(HERE, "layers/manifest-r7.json")))
T7 = {v["id"]: img(f"variant-r7-{v['id']}-set-B-graded-v3c.png") for vs in MAN["variants"].values() for v in vs}
T6c2 = img("variant-r6-curtains-v2-set-B-graded-v3c.png")
RAW7 = Image.fromarray((np.clip(np.load(os.path.join(HERE, "work-r7/p7-regt.npy")).astype(np.float32), 0, 1) * 255).astype(np.uint8))

ITEMS = {
    "planter": ([("R6", S6), ("R7: k 0.78", S7)], (880, 980, 1180, 1215), {"left-edge": (945, 1040, 1010, 1130), "shoulder": (950, 1050, 1060, 1110)}),
    "curtains-hems": ([("R6 180502 (to the floor)", S6), ("R7 180502, 270", S7), ("R7 554205, 270", T7["curtains-v2"]), ("R7 Linen, 260", T7["curtains-v3"])],
                      (0, 1050, 330, 1530), {"hem-270": (40, 1360, 200, 1460), "bench-corner": (100, 1170, 260, 1260)}),
    "curtain-3": ([("R7 Linen 200 x 260 (7')", T7["curtains-v3"]), ("R7 180502 (default)", S7)], (0, 300, 340, 1530), {"weave": (60, 600, 200, 740)}),
    "table-defaults": ([("R6", S6), ("R7: moved (WM-T2)", S7)], (1500, 1110, 2100, 1360),
                       {"holders": (1630, 1135, 1820, 1290), "bowl": (1840, 1230, 2030, 1350)}),
    "table-6": ([("R7 default", S7), ("ceramic trays (6')", T7["candle-holders-v2"]), ("white belly bowl (6')", T7["bowl-v2"])], (1500, 1110, 2100, 1360),
                {"trays": (1520, 1140, 1820, 1270), "bowl-v2": (1840, 1240, 2030, 1350)}),
    "vase-3": ([("default", S7), ("vase 2", T7["vase-v2"]), ("vase 3, white plum (6')", T7["vase-v3"])], (560, 820, 790, 1110), {"body": (600, 880, 740, 1075)}),
    "failed-7": ([("7' raw render (NOT layers)", RAW7), ("the plan (R7 default)", S7)], (1300, 1110, 2100, 1360), {}),
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
    sheet_parts = []
    for name, (tiles, box, x4) in ITEMS.items():
        t100 = labelled([(lab, im.crop(box)) for lab, im in tiles], 1, Image.NEAREST)
        t100.save(os.path.join(OUT, f"{name}-100.png"))
        sheet_parts.append((name, t100))
        for k, b in x4.items():
            labelled([(lab, im.crop(b)) for lab, im in tiles], 4, Image.NEAREST).save(os.path.join(OUT, f"{name}-{k}-x4.png"))
    # every option of every slot (set B truths), one row per slot
    boxes = {"curtains": (0, 300, 340, 1530), "framed-art": (1480, 470, 2200, 830), "accent-sconces": (1380, 470, 2340, 640),
             "vase": (560, 820, 790, 1110), "pendant": (1500, 0, 1900, 420), "bowl": (1820, 1220, 2050, 1360), "candle-holders": (1500, 1120, 1830, 1280)}
    rows = []
    for k, b in boxes.items():
        tiles = [(f"{k}: default", S7.crop(b))] + [(v["id"], T7[v["id"]].crop(b)) for v in MAN["variants"][k]]
        r = labelled(tiles, 1, Image.LANCZOS)
        rows.append((k, r))
    W = 2400
    head = S7.resize((W // 2, int(S7.height * (W // 2) / S7.width)), Image.LANCZOS)
    parts = [("R7 default scene, set B (12 defaults: planter k 0.78, curtains at 270, the table group moved)", head)]
    for k, r in rows:
        sc = min(1.0, W / r.width)
        parts.append((f"slot {k}: every option", r.resize((int(r.width * sc), int(r.height * sc)), Image.LANCZOS)))
    for n, t in sheet_parts:
        sc = min(1.0, W / t.width)
        parts.append((n, t.resize((int(t.width * sc), int(t.height * sc)), Image.LANCZOS)))
    H = sum(p.height + 40 for _, p in parts) + 60
    sheet = Image.new("RGB", (W, H), (245, 243, 238))
    d = ImageDraw.Draw(sheet)
    d.text((16, 14), "warm-modern tool, phase 2, R7 (2026-11-12): every option, and the R7 changes. Not QA'd. bowl-v3 and candle-holders-v3 FAILED in 7'",
           fill=(20, 20, 20), font=BIG)
    y = 60
    for lab, p in parts:
        d.text((16, y + 6), lab, fill=(20, 20, 20), font=FONT)
        sheet.paste(p, (16, y + 30))
        y += p.height + 40
    sheet.save(os.path.join(HERE, "phase2-r7-sheet.jpg"), quality=88)
    print("crops", sorted(os.listdir(OUT)), "sheet", sheet.size)


if __name__ == "__main__":
    main()
