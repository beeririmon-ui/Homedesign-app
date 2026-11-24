#!/usr/bin/env python3
"""kd_qa_sheet.py: the QA sheet of stage one (10.9: the regions that changed) (render-agent, 2026-11-20; 0 tokens): both frames at x0.5 with the regions boxed and
numbered, then each region at x2 of the 1920 frame (canvas x1.5), and the pendant's three variants side by side.
  python3 kd_qa_sheet.py   ->  qa-sheet.jpg"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

ST = K.ST
# 10.9 (2026-11-24): only what changed (EFF1.3); stage one's regions passed QA on 2026-11-20
REG = [("D2", 1, "KD-15 seam: D1's 5 deg (matched) | D2o, the 2 deg cross-fade at x 304-364; floor, bench, table end", (77, 760, 760, 1486)),
       ("D2", 2, "KD-16 niche (walnut matched to stage one), its LEDs; plates standing, bowls; canisters (D2o); two towels", (1700, 200, 2420, 800)),
       ("D2", 3, "frame 64 x 49, the whole print 05 (40x50 SKU, 5:4) with the side float gap (fixed 2026-11-24), the jar at Y 1.735", (380, 240, 900, 520)),
       ("D2", 4, "serving boards behind the 280363 board (Hb; B scaled 0.78, F's right edge continued from F: the notch fixed)", (640, 520, 1000, 780)),
       ("D2", 5, "counter vessel + beech branches (Hv, re-cut in code), mugs, paper towel holder", (1380, 250, 1760, 790)),
       ("D1", 6, "KD-L4: the graded oak and plaster by the opening (bottom-left)", (77, 900, 1000, 1486)),
       ("D1", 7, "left shelf from D2: the bigger frame, the jar moved, the serving boards", (1380, 260, 1980, 780)),
       ("D1", 8, "right end: the shelf without the tableware; the vessel at the edge (0.43 %, the intended projection: accepted)", (2160, 150, 2642, 800))]


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
    vs = [Image.open(os.path.join(ST, f"{v}.png")).convert("RGB").crop((620, 0, 1220, 500)) for v in ("D1-defaults", "D1-V3")]
    vt = Image.new("RGB", (1210, 550), "white")
    for i, v in enumerate(vs):
        vt.paste(v, (i * 605, 50))
    ImageDraw.Draw(vt).text((8, 8), "9: the sample slot on the graded plate: V1 (default) / V3 (KD-L3: V2 left the wheel)", fill=(0, 0, 0), font_size=26)
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
