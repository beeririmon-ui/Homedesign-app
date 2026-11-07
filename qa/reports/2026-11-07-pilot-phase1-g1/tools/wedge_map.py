"""
qa-agent 2026-11-07: false-colour map of the back wall's low-frequency L* (sigma 12, normalised inside the r4 wall index 5), 1 L* per colour
step clipped to [78, 98], with the art / sconce area box, plus the L* profile of three rows across the area (printed).
Usage: ~/.venvs/motion/bin/python -I wedge_map.py <png> [...]. Writes overlays/wedge-map-<name>.jpg.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r4-shell-idx/M0.npz"
W, H = 2720, 1530
idx = np.load(IDX)["idx"]
wall = cv2.resize((idx == 5).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
k = cv2.erode(wall, np.ones((15, 15), np.uint8)).astype(np.float32)
ax0, ax1, ay0, ay1 = 1231, 2257, 259, 692
for name in sys.argv[1:]:
    rgb = np.asarray(Image.open(os.path.join(P, name)).convert("RGB")).astype(np.float64) / 255
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    L = np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y).astype(np.float32)
    LF = cv2.GaussianBlur(L * k, (0, 0), 12) / np.maximum(cv2.GaussianBlur(k, (0, 0), 12), 1e-4)
    q = np.clip((np.floor(LF) - 78) / 20, 0, 1)
    col = (cv2.applyColorMap((q * 255).astype(np.uint8), cv2.COLORMAP_TURBO)[..., ::-1]).copy()
    col[k == 0] = (rgb[k == 0] * 255 * 0.5).astype(np.uint8)
    cv2.rectangle(col, (ax0, ay0), (ax1, ay1), (255, 255, 255), 3)
    Image.fromarray(col).resize((1360, 765)).save(os.path.join(OUT, "overlays", f"wedge-map-{os.path.splitext(name)[0]}.jpg"), quality=88)
    for yy in (300, 450, 600):
        xs = list(range(1100, 2300, 60))
        print(name, "row", yy, [(x, round(float(LF[yy, x]), 1)) for x in xs if k[yy, x] > 0])
