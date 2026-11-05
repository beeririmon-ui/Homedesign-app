"""
qa-agent 2026-11-05: G1.12 crops at 100 % / 200 % of every region the code edited in the seedream composite and the fix3 round,
side by side with the previous version. Canvas pixels (2736 x 1539). Reuses side() of the 11-04 crops tool.
Writes overlays/g112-*.jpg. Usage: python3.12 -I crops.py
"""
import importlib.util
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1/overlays")
_s = importlib.util.spec_from_file_location("cr1104", os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/crops.py"))
CR = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CR)
R = os.path.join(REPO, "assets/renders")
M0S = (f"{R}/living-room/nordic/v9/m0-shell-seedream-graded-v5.png", f"{R}/living-room/nordic/v9/m0-1-2-shell-seedream-graded-fix-v5.png")
M0SR = (f"{R}/living-room/nordic/v9/m0-shell-seedream.png", f"{R}/living-room/nordic/v9/m0-1-2-shell-seedream-fix.png")
B1 = (f"{R}/bath/nordic/v7/b1-v7-r3-graded-fix2-v5.png", f"{R}/bath/nordic/v7/b1-v7-r3-graded-fix3-v5.png")
CB = (f"{R}/poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png", f"{R}/poses/nordic/v7/pose-cb-0-v7-graded-b1r3f3-v5.png")
W0 = (f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix2-v5.png", f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix3-v5.png")
W0F = (f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix-v4.png", f"{R}/poses/nordic/v7/pose-w0-in-v7-r2-graded-fix3-v5.png")
M0P = (f"{R}/poses/nordic/v8/pose-m0p-v8b-graded-fix-v5.png", f"{R}/poses/nordic/v8/pose-m0p-v8b-graded-fix3-v5.png")
KG = (f"{R}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix2-v5.png", f"{R}/poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix3-v5.png")
JOBS = [
    ("M0s-triptych-left-200", M0SR, (1490, 400, 1830, 760), 2),
    ("M0s-triptych-right-200", M0SR, (1990, 380, 2290, 740), 2),
    ("M0s-wall-round-raw-200", M0SR, (1150, 600, 1520, 940), 2),
    ("M0s-sofa-table", M0S, (1100, 900, 2736, 1539), 1),
    ("M0s-window-armchair", M0S, (0, 500, 1300, 1539), 1),
    ("B1-lumps-200", B1, (1500, 1000, 1700, 1300), 2),
    ("B1-curtain-left-200", B1, (1440, 560, 1640, 1000), 2),
    ("B1-fern-curtain", B1, (1300, 560, 1800, 1420), 1),
    ("CB-0-seam-top-100", CB, (650, 0, 1050, 400), 1),
    ("CB-0-top-wedge-100", CB, (800, 0, 1800, 330), 1),
    ("CB-0-bottom-wedge-100", CB, (800, 1250, 1800, 1539), 1),
    ("CB-0-fern-200", CB, (1850, 900, 2150, 1250), 2),
    ("W0-in-desk-corner", W0, (380, 940, 720, 1539), 1),
    ("W0-in-desk-corner-vs-fix", W0F, (380, 940, 720, 1539), 1),
    ("W0-in-basket-base-200", W0, (250, 1340, 600, 1539), 2),
    ("M0p-sofa", M0P, (500, 600, 2300, 1400), 1),
    ("M0p-bowl-200", M0P, (1050, 1180, 1350, 1340), 2),
    ("M0p-floor-right-leg-200", M0P, (1450, 1180, 1800, 1400), 2),
    ("M0p-top-strip", M0P, (0, 0, 2736, 160), 1),
    ("K-girl-0-left-quarter", KG, (0, 0, 700, 1539), 1),
    ("K-girl-0-left-200", KG, (0, 150, 330, 700), 2),
]

if __name__ == "__main__":
    for name, (a, b), box, z in JOBS:
        im = CR.side(a, b, box, z)
        p = os.path.join(OUT, f"g112-{name}.jpg")
        im.save(p, quality=90)
        print(p, im.size)
