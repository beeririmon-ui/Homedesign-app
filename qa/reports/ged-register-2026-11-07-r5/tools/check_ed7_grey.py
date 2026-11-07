"""
qa-agent 2026-11-07: ed7's 'greyish troughs' (render-agent's note, seen at x4): inside the cushion, pixels that read cool or grey next to the
cream: b* < 5, or hue outside 55-100 deg with C* > 2; ed5 / ed6 / ed7 and the SKU photo (the share there is the photo's own grey-cream
loops). Also their clustering: the largest connected group (8-neighbour), so a scatter of specks is told from a patch.
Usage: ~/.venvs/motion/bin/python -I check_ed7_grey.py. Writes data/ed7-grey.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
E = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r5")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-pilot-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


raw = {k: np.asarray(Image.open(os.path.join(E, f"warm-modern-A-{k}.png")).convert("RGB")).astype(float) for k in ("ed5", "ed6", "ed7")}
m = np.abs(raw["ed5"] - raw["ed6"]).max(2) > 0
out = {}
for k, v in raw.items():
    L = lab(v)
    h = np.degrees(np.arctan2(L[..., 2], L[..., 1]))
    C = np.hypot(L[..., 1], L[..., 2])
    g = m & ((L[..., 2] < 5) | (((h < 55) | (h > 100)) & (C > 2)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), connectivity=8)
    out[k] = dict(px=int(g.sum()), share_pct=round(float(g.sum() / m.sum() * 100), 2), largest_group_px=int(st[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0,
                  b_lt_3=int((m & (L[..., 2] < 3)).sum()))
ph = lab(np.asarray(Image.open(REF + "A-cushions-cj-boucle-teddy-milk-tea-color-crop.png").convert("RGB")).astype(float))
H, W = ph.shape[:2]
pc = ph[H // 4:3 * H // 4, W // 4:3 * W // 4].reshape(-1, 3)
hp = np.degrees(np.arctan2(pc[:, 2], pc[:, 1]))
Cp = np.hypot(pc[:, 1], pc[:, 2])
out["sku_photo_share_pct"] = round(float(((pc[:, 2] < 5) | (((hp < 55) | (hp > 100)) & (Cp > 2))).mean() * 100), 1)
json.dump(out, open(os.path.join(OUT, "data", "ed7-grey.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
