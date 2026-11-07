"""
qa-agent 2026-11-07: set C's black point (p0.5 L* 10.0 in v3c) against WM-G1 (L* 11-14) and G1.9 (the black point in the deep crevice
L* 12-15; cast and contact shadows on open floor not darker than L* 30). Per set, on the v3c display composites: L* p0.5 overall, inside the
set's layer, on the fixed furniture and on the shell; the deep crevice (the base's darkest 0.1 %, fixed positions) in every set; the set's
cushion shadow where it falls on the shell (outside every alpha): its p1 and min L*. Usage: ~/.venvs/motion/bin/python -I dark_c.py.
Writes data/dark-c.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")


def Lstar(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


fa = np.asarray(Image.open(os.path.join(P, "fixed-furniture.png")))[..., 3]
base = Lstar(np.asarray(Image.open(os.path.join(P, "shell-furniture-v3-graded-v3c.png")).convert("RGB")).astype(float))
crev = base <= np.percentile(base, 0.1)
out = {"base_p005": round(float(np.percentile(base, 0.5)), 2), "base_crevice_L_median": round(float(np.median(base[crev])), 2)}
for S in "ABC":
    L = Lstar(np.asarray(Image.open(os.path.join(P, f"composite-set-{S}-v3-graded-v3c.png")).convert("RGB")).astype(float))
    la = np.asarray(Image.open(os.path.join(P, "layers/cushions", f"set-{S}.png")))[..., 3]
    sh = np.asarray(Image.open(os.path.join(P, "shadows/cushions", f"set-{S}.png")).convert("RGB")).min(2) < 255
    on_shell = sh & (la == 0) & (fa == 0)
    out[S] = dict(p005=round(float(np.percentile(L, 0.5)), 2), layer_p005=round(float(np.percentile(L[la > 0], 0.5)), 2),
                  layer_share_below_11_pct=round(float((L[la > 0] < 11).mean() * 100), 2),
                  furniture_p005=round(float(np.percentile(L[(la == 0) & (fa > 0)], 0.5)), 2), shell_p005=round(float(np.percentile(L[(la == 0) & (fa == 0)], 0.5)), 2),
                  crevice_L_median=round(float(np.median(L[crev & (la == 0)])), 2) if (crev & (la == 0)).any() else None,
                  shadow_on_shell_px=int(on_shell.sum()), shadow_on_shell_p1=round(float(np.percentile(L[on_shell], 1)), 2) if on_shell.any() else None,
                  shadow_on_shell_min=round(float(L[on_shell].min()), 2) if on_shell.any() else None)
json.dump(out, open(os.path.join(OUT, "data", "dark-c.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
