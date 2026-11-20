#!/usr/bin/env python3
"""kd_qa_sheet.py: the QA sheet of stage one (render-agent, 2026-11-20; 0 tokens): both frames at x0.5 with the regions boxed and
numbered, then each region at x2 of the 1920 frame (canvas x1.5), and the pendant's three variants side by side.
  python3 kd_qa_sheet.py   ->  qa-sheet.jpg"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

ST = K.ST
REG = [("D1", 1, "table group: pendant V1, runner, amphora + olive, iron dishes", (300, 0, 1330, 1000)),
       ("D1", 2, "curtain (wider than the clay's stack; seam flecks at the chair tops)", (77, 0, 720, 1110)),
       ("D1", 3, "right worktop and shelf: mills, oil, bowl + pears, plates, mugs (crop edit Dc)", (2120, 330, 2642, 780)),
       ("D1", 4, "corner: floor vase + eucalyptus (crop edit Bc)", (1080, 560, 1420, 1060)),
       ("D1", 5, "left shelf seen from D1: art (blank canvas), moon jar, sconce, board, sink set (projected from D2)", (1380, 260, 1980, 780)),
       ("D1", 6, "bench pad", (760, 960, 1720, 1420)),
       ("D2", 7, "left shelf, sconce, sink set, board (E r1 + crop edit Ec)", (100, 230, 760, 760)),
       ("D2", 8, "paper towel holder, canisters in the niche, tea towel", (1380, 450, 2200, 800)),
       ("D2", 9, "right shelf and worktop seen from D2 (projected from D1)", (1050, 380, 1560, 770))]


def main():
    fr = {f: Image.open(os.path.join(ST, f"{f}-defaults.png")).convert("RGB") for f in ("D1", "D2")}
    tops = []
    for f in ("D1", "D2"):
        im = fr[f].copy()
        d = ImageDraw.Draw(im)
        for g, n, _, b in REG:
            if g == f:
                d.rectangle(b, outline=(255, 40, 40), width=5)
                d.text((b[0] + 8, b[1] + 6), str(n), fill=(255, 40, 40), font_size=48)
        tops.append(im.resize((1360, 765), Image.LANCZOS))
    tiles = []
    for g, n, cap, b in REG:
        c = fr[g].crop(b)
        c = c.resize((int(c.size[0] * 1.5), int(c.size[1] * 1.5)), Image.LANCZOS)
        if c.size[0] > 1360:
            c = c.resize((1360, int(c.size[1] * 1360 / c.size[0])), Image.LANCZOS)
        if c.size[1] > 1100:
            c = c.resize((int(c.size[0] * 1100 / c.size[1]), 1100), Image.LANCZOS)
        t = Image.new("RGB", (c.size[0], c.size[1] + 50), "white")
        t.paste(c, (0, 50))
        ImageDraw.Draw(t).text((8, 8), f"{n} ({g}, x2): {cap}", fill=(0, 0, 0), font_size=26)
        tiles.append(t)
    vs = [Image.open(os.path.join(ST, f"{v}.png")).convert("RGB").crop((620, 0, 1220, 500)) for v in ("D1-defaults", "D1-V2", "D1-V3")]
    vt = Image.new("RGB", (1810, 550), "white")
    for i, v in enumerate(vs):
        vt.paste(v, (i * 605, 50))
    ImageDraw.Draw(vt).text((8, 8), "10: the sample slot, pendant V1 (default) / V2 (code: V1's shade, the white wire) / V3 (crop edit)", fill=(0, 0, 0), font_size=26)
    tiles.append(vt)
    Wd = 2730
    rows, row, w = [], [], 0
    for t in tiles:
        if w + t.size[0] > Wd and row:
            rows.append(row)
            row, w = [], 0
        row.append(t)
        w += t.size[0] + 10
    rows.append(row)
    H = 765 + 20 + sum(max(t.size[1] for t in r) + 10 for r in rows)
    S = Image.new("RGB", (Wd, H), "white")
    S.paste(tops[0], (0, 0))
    S.paste(tops[1], (1370, 0))
    y = 785
    for r in rows:
        x = 0
        for t in r:
            S.paste(t, (x, y))
            x += t.size[0] + 10
        y += max(t.size[1] for t in r) + 10
    S = S.resize((S.size[0] * 2 // 3, S.size[1] * 2 // 3), Image.LANCZOS)
    S.save(os.path.join(ST, "qa-sheet.jpg"), quality=86)
    print(S.size)


if __name__ == "__main__":
    main()
