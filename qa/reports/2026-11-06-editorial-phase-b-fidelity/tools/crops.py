"""
qa-agent 2026-11-06: 100 % crops of product areas in the six phase B frames (fractions of each frame), for the fidelity table.
Writes overlays/<frame>-<area>.jpg. Usage: python3.12 -I crops.py
"""
import os
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/2026-11-06-editorial-phase-b-fidelity/overlays")
JOBS = {
    "nordic-A-fin": {"sofa-table": (0.33, 0.86, 0.45, 0.90), "corner": (0.20, 0.34, 0.15, 0.70), "rug": (0.15, 1.0, 0.75, 1.0)},
    "nordic-B-fin": {"armchair-throw": (0.58, 0.92, 0.48, 0.95), "round": (0.04, 0.20, 0.04, 0.30), "rug": (0.20, 1.0, 0.82, 1.0)},
    "warm-modern-A-fin": {"sofa-table": (0.20, 0.92, 0.42, 0.82), "pendant": (0.40, 0.66, 0.0, 0.16)},
    "boho-A": {"wall": (0.07, 0.62, 0.10, 0.40), "sofa": (0.08, 0.68, 0.43, 0.65), "table-runner": (0.28, 0.76, 0.62, 0.95), "corner": (0.62, 0.84, 0.25, 0.72), "pouf": (0.75, 0.99, 0.70, 1.0)},
    "mediterranean-A": {"art": (0.09, 0.55, 0.08, 0.45), "sofa": (0.07, 0.66, 0.45, 0.95), "table": (0.37, 0.64, 0.64, 0.88), "holder-basket": (0.62, 0.83, 0.54, 0.84), "sill": (0.75, 0.92, 0.35, 0.62)},
    "japandi-A": {"pendant": (0.04, 0.24, 0.17, 0.58), "sill-jar": (0.20, 0.33, 0.55, 0.76), "sofa": (0.32, 0.68, 0.58, 0.88), "table": (0.33, 0.67, 0.80, 0.95), "wall": (0.74, 0.97, 0.14, 0.52)},
}
if __name__ == "__main__":
    for f, areas in JOBS.items():
        im = Image.open(os.path.join(R, f + ".png")).convert("RGB")
        W, H = im.size
        for nm, (u0, u1, v0, v1) in areas.items():
            c = im.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H)))
            if c.width > 1400:
                c = c.resize((1400, int(c.height * 1400 / c.width)))
            c.save(os.path.join(OUT, f"{f}-{nm}.jpg"), quality=90)
            print(f, nm, c.size)
