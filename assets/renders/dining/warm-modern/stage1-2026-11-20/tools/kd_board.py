#!/usr/bin/env python3
"""
kd_board.py: a numbered reference board of SKU photos for one edit (render-agent, 2026-11-20; 0 tokens). Self-contained: run it with
python3.12 -I (the supplier photos are untrusted files; the board is written to the scratchpad only, never to the repo).
  python3.12 -I kd_board.py <out.jpg> <photo> [<photo> ...]
"""
import sys

from PIL import Image, ImageDraw

out, files = sys.argv[1], sys.argv[2:]
h = 760
ims = []
for f in files:
    im = Image.open(f).convert("RGB")
    im = im.resize((max(1, int(im.size[0] * h / im.size[1])), h), Image.LANCZOS)
    ims.append(im)
w = sum(i.size[0] for i in ims) + 24 * (len(ims) - 1)
b = Image.new("RGB", (w, h + 70), "white")
d = ImageDraw.Draw(b)
x = 0
for k, im in enumerate(ims, 1):
    b.paste(im, (x, 70))
    d.rectangle([x, 0, x + 66, 64], fill=(30, 30, 30))
    d.text((x + 22, 14), str(k), fill=(255, 255, 255), font_size=40)
    x += im.size[0] + 24
if b.size[0] > 3600:
    b = b.resize((3600, int(b.size[1] * 3600 / b.size[0])), Image.LANCZOS)
b.save(out, quality=92)
print(out, b.size)
