"""
qa-agent 2026-11-08: the measuring grid of qa/reports/2026-11-07-ged-master-mb1/tools/grid.py on the fix1 frames (lines every 20 px,
labels every 100 px, frame coordinates; x2 when the crop is under 700 px wide).
Usage: ~/.venvs/motion/bin/python -I grid.py <nordic|warm-modern> x0 y0 x1 y1 <name>. Writes overlays/grid-<name>.jpg.
"""
import os
import sys

from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1/overlays")
sub, x0, y0, x1, y1, name = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
im = Image.open(os.path.join(B, sub, ("nordic-MB-A" if sub == "nordic" else "warm-modern-MB-A") + "-fix1.png")).convert("RGB").crop((x0, y0, x1, y1))
s = 2 if (x1 - x0) < 700 else 1
im = im.resize((im.width * s, im.height * s), Image.NEAREST)
d = ImageDraw.Draw(im)
for x in range((x0 // 20 + 1) * 20, x1, 20):
    X = (x - x0) * s
    d.line([(X, 0), (X, im.height)], fill=(255, 0, 0) if x % 100 == 0 else (0, 200, 255), width=1)
    if x % 100 == 0:
        d.text((X + 2, 2), str(x), fill=(255, 0, 0))
for y in range((y0 // 20 + 1) * 20, y1, 20):
    Y = (y - y0) * s
    d.line([(0, Y), (im.width, Y)], fill=(255, 0, 0) if y % 100 == 0 else (0, 200, 255), width=1)
    if y % 100 == 0:
        d.text((2, Y + 2), str(y), fill=(255, 0, 0))
im.save(os.path.join(OUT, f"grid-{name}.jpg"), quality=88)
