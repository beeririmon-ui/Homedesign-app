#!/usr/bin/env python3
"""
work_qa_sheet.py: w0-qa-sheet.jpg for QA (render-agent, 2026-11-20; 0 tokens): the W0 defaults frame at x1 (1920 wide) with the QA
regions, then each region at about x2 of the 1920 frame (1.5 canvas px per px), then the sample slot's three prints side by side.
The regions (canvas px) are the README's.
  python3 work_qa_sheet.py
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

ST = M.ST
REGIONS = {
    "Q1 niche, arch, shelf, pendant, print 08": (940, 60, 1800, 800),
    "Q2 desk left: vase, tray, pen cup": (960, 700, 1240, 930),
    "Q3 desk right: Hiba bowl, dish": (1500, 780, 1800, 930),
    "Q4 under the desk: basket, bin": (1000, 1080, 1760, 1360),
    "Q5 left corner: curtain, cube sconce, palm, pot": (380, 300, 1100, 1360),
    "Q6 magazine rack": (1800, 1080, 2160, 1360),
    "Q7 frame 2, print 03": (2210, 260, 2440, 720),
    "Q8 throw and rug": (1100, 820, 1640, 1530),
    "Q9 plate: window, sill, plaster": (77, 43, 700, 1100),
}
SCALE = 1.5          # x2 of the 1920 frame = 1.5 canvas px per px (the frame is the canvas's 2565 px at 0.749)


def main():
    full = Image.open(os.path.join(ST, "w0-defaults.png")).convert("RGB")
    x0, y0, x1, y1 = (int(round(v)) for v in M.FRAME)
    k = 1920 / (x1 - x0)
    top = full.crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS)
    d = ImageDraw.Draw(top)
    for name, (a, b, c, e) in REGIONS.items():
        box = [(a - x0) * k, (b - y0) * k, (c - x0) * k, (e - y0) * k]
        d.rectangle(box, outline=(220, 40, 40), width=3)
        d.text((box[0] + 6, box[1] + 4), name.split(" ")[0], fill=(220, 40, 40))
    tiles = []
    for name, (a, b, c, e) in REGIONS.items():
        t = full.crop((a, b, c, e))
        t = t.resize((int(t.width * SCALE), int(t.height * SCALE)), Image.LANCZOS)
        if t.width > 1920:
            t = t.resize((1920, int(t.height * 1920 / t.width)), Image.LANCZOS)
        lab = Image.new("RGB", (t.width, t.height + 28), "white")
        lab.paste(t, (0, 28))
        ImageDraw.Draw(lab).text((6, 6), name + "  (about x2)", fill=(0, 0, 0))
        tiles.append(lab)
    pr = []
    for tag in ("defaults", "variant-art-01", "variant-art-02"):
        f = "w0-defaults.png" if tag == "defaults" else f"w0-{tag}.png"
        im = Image.open(os.path.join(ST, f)).convert("RGB").crop((1190, 500, 1530, 790))
        pr.append(im.resize((int(im.width * SCALE), int(im.height * SCALE)), Image.LANCZOS))
    strip = Image.new("RGB", (sum(p.width for p in pr) + 20 * 2, pr[0].height + 28), "white")
    x = 0
    for p, tag in zip(pr, ("V1 386242-08 (default)", "V2 386242-01", "V3 386242-02")):
        strip.paste(p, (x, 28))
        ImageDraw.Draw(strip).text((x + 6, 6), tag, fill=(0, 0, 0))
        x += p.width + 20
    tiles.append(strip)
    # pack the tiles in rows of 1920
    rows, row, w = [], [], 0
    for t in tiles:
        if w + t.width > 1920 and row:
            rows.append(row)
            row, w = [], 0
        row.append(t)
        w += t.width + 10
    rows.append(row)
    hgt = 1080 + 20 + sum(max(t.height for t in r) + 10 for r in rows)
    sheet = Image.new("RGB", (1920, hgt), "white")
    sheet.paste(top, (0, 0))
    yy = 1100
    for r in rows:
        xx = 0
        for t in r:
            sheet.paste(t, (xx, yy))
            xx += t.width + 10
        yy += max(t.height for t in r) + 10
    sheet.save(os.path.join(ST, "w0-qa-sheet.jpg"), quality=88)
    print(sheet.size)


if __name__ == "__main__":
    main()
