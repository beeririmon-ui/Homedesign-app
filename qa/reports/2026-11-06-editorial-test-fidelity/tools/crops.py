"""
qa-agent 2026-11-06: 100 % crops of every product area in the five editorial frames (ED1), for the fidelity table.
Boxes in fractions of each frame (judged on half-size views). Writes overlays/<frame>-<area>.jpg. Usage: python3.12 -I crops.py
"""
import os
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-test-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/2026-11-06-editorial-test-fidelity/overlays")
JOBS = {
    "nordic/nordic-A-nano-banana-2.jpg": {"wall": (0.50, 0.90, 0.22, 0.43), "table": (0.46, 0.79, 0.55, 0.86), "sofa": (0.45, 0.90, 0.47, 0.80), "pendant": (0.56, 0.73, 0.0, 0.23),
                                          "corner": (0.86, 1.0, 0.33, 0.80), "rug": (0.30, 0.95, 0.75, 1.0)},
    "nordic/nordic-A-gpt-image-2-5.jpg": {"wall": (0.38, 0.82, 0.20, 0.42), "table": (0.33, 0.78, 0.53, 0.92), "sofa": (0.31, 0.88, 0.44, 0.80), "pendant": (0.41, 0.59, 0.0, 0.22),
                                          "corner": (0.19, 0.40, 0.14, 0.70), "rug": (0.13, 1.0, 0.70, 1.0)},
    "nordic/nordic-B-nano-banana-2.jpg": {"round": (0.03, 0.20, 0.02, 0.30), "vase": (0.50, 0.66, 0.20, 0.52), "holder": (0.42, 0.60, 0.62, 0.92), "basket": (0.08, 0.24, 0.66, 0.99),
                                          "armchair": (0.58, 0.92, 0.47, 1.0), "rug": (0.20, 1.0, 0.83, 1.0)},
    "warm-modern/warm-modern-A-nano-banana-2.jpg": {"wall": (0.36, 0.73, 0.23, 0.48), "table": (0.37, 1.0, 0.62, 1.0), "sofa": (0.33, 0.77, 0.50, 0.78), "pendant": (0.50, 0.71, 0.0, 0.20),
                                                    "lamp-vase": (0.72, 0.92, 0.30, 0.86)},
    "warm-modern/warm-modern-A-gpt-image-2-5.jpg": {"wall": (0.30, 0.80, 0.14, 0.44), "table": (0.30, 0.90, 0.56, 1.0), "sofa": (0.19, 0.92, 0.42, 0.84), "pendant": (0.40, 0.66, 0.0, 0.16),
                                                    "lamp": (0.86, 1.0, 0.16, 0.77), "side": (0.0, 0.27, 0.75, 1.0)},
}
if __name__ == "__main__":
    for f, areas in JOBS.items():
        im = Image.open(os.path.join(R, f)).convert("RGB")
        W, H = im.size
        tag = os.path.basename(f).replace(".jpg", "")
        for nm, (u0, u1, v0, v1) in areas.items():
            c = im.crop((int(u0 * W), int(v0 * H), int(u1 * W), int(v1 * H)))
            if c.width > 1400:
                c = c.resize((1400, int(c.height * 1400 / c.width)))
            c.save(os.path.join(OUT, f"{tag}-{nm}.jpg"), quality=90)
            print(tag, nm, c.size)
