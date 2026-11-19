#!/usr/bin/env python3
"""
mb1_qa_sheet.py: MB1's QA sheet (render-agent, 2026-11-19; 0 tokens): the frame x1 with the QA regions boxed and numbered, then each
region as a crop at about x2 of the 1920 frame (the canvas at 1.5; tall regions smaller, the scale in the label). Art A (776445) is x1
only: no crop shows it (region 4 starts right of its frame).
  python3 mb1_qa_sheet.py            (writes mb1-qa-sheet.jpg)
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

ST = M.ST
REGIONS = [  # canvas px; the number is the region in the README
    ("1", "bench throw: drop and hem on the rug (traced)", (40, 990, 640, 1490)),
    ("2", "rug: tone to the living room's; edge on the oak", (600, 1180, 1500, 1530)),
    ("3", "left nightstand: duvet edge, vase, curtain, sconce W", (740, 470, 1110, 860)),
    ("4", "frame B (print in code), shelf vase R (art A x1 only)", (1392, 280, 1700, 480)),
    ("5", "right nightstand: pitcher, candles, sconce E", (1680, 440, 1960, 940)),
    ("6a", "floor lamp: shade and pole top", (1840, 300, 2140, 640)),
    ("6b", "floor lamp: pole foot and base", (1860, 1040, 2090, 1320)),
    ("7a", "ficus crown and trunk", (2120, 120, 2642, 640)),
    ("7b", "pot: tone to MB0's (R5 reading in the README)", (2200, 990, 2620, 1380)),
    ("8", "magazine holder (blank covers, 13.11)", (1960, 1120, 2350, 1430)),
    ("9", "Pecan throw on the bed: the right end's drop", (480, 830, 1560, 1260)),
    ("10", "pillows and cushion", (1080, 630, 1730, 870)),
]


def main():
    im = Image.open(os.path.join(ST, "mb1-defaults.png")).convert("RGB")
    fx0, fy0, fx1, fy1 = M.FRAME
    k = 1920 / (fx1 - fx0)
    frame = im.crop((round(fx0), round(fy0), round(fx1), round(fy1))).resize((1920, 1080), Image.LANCZOS)
    d = ImageDraw.Draw(frame)
    for n, _, (x0, y0, x1, y1) in REGIONS:
        b = [(x0 - fx0) * k, (y0 - fy0) * k, (x1 - fx0) * k, (y1 - fy0) * k]
        d.rectangle(b, outline=(255, 40, 40), width=3)
        d.rectangle([b[0], b[1], b[0] + 30, b[1] + 22], fill=(255, 40, 40))
        d.text((b[0] + 6, b[1] + 5), str(n), fill=(255, 255, 255))
    tiles = []
    for n, label, (x0, y0, x1, y1) in REGIONS:
        s = min(1.5, 700 / (y1 - y0), 940 / (x1 - x0))
        t = im.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * s), int((y1 - y0) * s)), Image.LANCZOS)
        tiles.append((f"{n}. {label}  (x{s / k:.1f} of the 1920 frame)", t))
    # rows of tiles, 1920 wide
    rows, row, w = [], [], 0
    for lab, t in tiles:
        if w + t.size[0] + 10 > 1920 and row:
            rows.append(row)
            row, w = [], 0
        row.append((lab, t))
        w += t.size[0] + 10
    rows.append(row)
    H = 1080 + 20 + sum(max(t.size[1] for _, t in r) + 46 for r in rows)
    sheet = Image.new("RGB", (1920, H), "white")
    sheet.paste(frame, (0, 0))
    y = 1100
    dd = ImageDraw.Draw(sheet)
    for r in rows:
        x = 0
        for lab, t in r:
            words, line, ly = lab.split(" "), "", y + 2
            for wd in words:                                   # wrapped to the tile's width
                if dd.textlength(line + " " + wd) > t.size[0] - 8 and line:
                    dd.text((x + 4, ly), line, fill=(0, 0, 0))
                    line, ly = wd, ly + 13
                else:
                    line = (line + " " + wd).strip()
            dd.text((x + 4, ly), line, fill=(0, 0, 0))
            sheet.paste(t, (x, y + 40))
            x += t.size[0] + 10
        y += max(t.size[1] for _, t in r) + 46
    out = os.path.join(ST, "mb1-qa-sheet.jpg")
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
