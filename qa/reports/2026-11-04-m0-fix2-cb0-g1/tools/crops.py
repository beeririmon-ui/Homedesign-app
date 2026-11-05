"""
qa-agent 2026-11-04: G1.12 crops at 100 % / 200 % of every region the code edited (fix2, CB-0 b1r3, M0 1.2 composites),
side by side with the previous version where one exists. Canvas pixels (2736 x 1539). Writes overlays/g112-*.jpg.
Usage: python3.12 -I crops.py
"""
import os
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/overlays")
R = os.path.join(REPO, "assets/renders")
B1 = (f"{R}/bath/nordic/v7/b1-v7-r3-graded-fix-v4.png", f"{R}/bath/nordic/v7/b1-v7-r3-graded-fix2-v5.png")
B2 = (f"{R}/bath/nordic/v7/b2-v7-r3-graded-fix-v4.png", f"{R}/bath/nordic/v7/b2-v7-r3-graded-fix2-v5.png")
W0 = (f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix-v4.png", f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix2-v5.png")
KG = (f"{R}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix-v4.png", f"{R}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix2-v5.png")
CB = (f"{R}/poses/nordic/v7/pose-cb-0-v7-graded-v4.png", f"{R}/poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png")
M0 = (f"{R}/living-room/nordic/v8/m0-v8b-r2-graded-v4.png", f"{R}/living-room/nordic/v8/m0-v8b-r2-graded-fix-v5.png")
M0P = (f"{R}/poses/nordic/v8/pose-m0p-v8b-graded-v4.png", f"{R}/poses/nordic/v8/pose-m0p-v8b-graded-fix-v5.png")
M0X = (f"{R}/poses/nordic/v8/pose-m0x-v8b-graded-v4.png", f"{R}/poses/nordic/v8/pose-m0x-v8b-graded-fix-v5.png")

JOBS = [
    # name, (before, after), box (x0, y0, x1, y1) canvas, zoom
    ("B1-fern-curtain", B1, (1300, 560, 1800, 1420), 1),
    ("B1-right-of-fern", B1, (1500, 700, 1800, 1100), 2),
    ("B1-brush", B1, (1170, 1080, 1400, 1420), 2),
    ("B2-planter-floor", B2, (0, 850, 800, 1539), 1),
    ("B2-floor-right-of-basket", B2, (300, 1250, 700, 1539), 2),
    ("B2-wall-panel", B2, (0, 450, 700, 1150), 1),
    ("W0-in-basket", W0, (0, 950, 760, 1539), 1),
    ("W0-in-basket-top", W0, (60, 950, 460, 1250), 2),
    ("K-girl-0-top", KG, (0, 0, 2736, 140), 1),
    ("K-girl-0-bottom", KG, (0, 1400, 2736, 1539), 1),
    ("CB-0-seam-top", CB, (600, 0, 1100, 770), 1),
    ("CB-0-seam-bottom", CB, (600, 770, 1100, 1539), 1),
    ("CB-0-left", CB, (0, 0, 860, 1539), 1),
    ("M0-sofa-wall", M0, (1100, 700, 2736, 1300), 1),
    ("M0-floor-rug", M0, (1100, 1150, 2736, 1539), 1),
    ("M0-left-strip", M0, (0, 900, 1400, 1539), 1),
    ("M0p-sofa", M0P, (500, 600, 2300, 1400), 1),
    ("M0x-door", M0X, (1200, 100, 2736, 1400), 1),
]


def side(a, b, box, zoom):
    ca = Image.open(a).convert("RGB").crop(box)
    cb = Image.open(b).convert("RGB").crop(box)
    if zoom != 1:
        ca = ca.resize((ca.width * zoom, ca.height * zoom), Image.NEAREST)
        cb = cb.resize((cb.width * zoom, cb.height * zoom), Image.NEAREST)
    horiz = ca.width <= ca.height * 1.3
    W = ca.width * 2 + 12 if horiz else ca.width
    H = ca.height + 30 if horiz else ca.height * 2 + 42
    im = Image.new("RGB", (W, H), (40, 40, 40))
    d = ImageDraw.Draw(im)
    if horiz:
        im.paste(ca, (0, 30)); im.paste(cb, (ca.width + 12, 30))
        d.text((6, 8), "before: " + os.path.basename(a), fill=(255, 255, 0))
        d.text((ca.width + 18, 8), "now: " + os.path.basename(b), fill=(0, 255, 0))
    else:
        d.text((6, 8), "before: " + os.path.basename(a), fill=(255, 255, 0))
        im.paste(ca, (0, 24))
        d.text((6, ca.height + 28), "now: " + os.path.basename(b), fill=(0, 255, 0))
        im.paste(cb, (0, ca.height + 42))
    return im


if __name__ == "__main__":
    for name, (a, b), box, z in JOBS:
        if not os.path.exists(a):
            a = b
        im = side(a, b, box, z)
        p = os.path.join(OUT, f"g112-{name}.jpg")
        im.save(p, quality=90)
        print(p, im.size)
