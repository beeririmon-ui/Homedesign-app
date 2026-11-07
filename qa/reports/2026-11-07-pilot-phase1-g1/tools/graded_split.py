"""
qa-agent 2026-11-07: is the display grade one grade for all variants? On the graded composites (shell-furniture-<v>-graded.png and
composite-set-<S>-<v>-graded.png), the change outside the products and their shadows (layers/cushions/set-S.png alpha > 0 or
shadows/cushions/set-S.png < 255, both sides of the pair): pixel count over 2 levels, the max and p99 of dE76 (CIE Lab D65), where it is
(L* of the base there), and a x4 crop of the worst spot. Usage: ~/.venvs/motion/bin/python -I graded_split.py <v2|v3> [<graded suffix, default graded>].
Writes data/graded-split-<v>.json and overlays/graded-split-<v>.jpg.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
V = sys.argv[1] if len(sys.argv) > 1 else "v3"
G = sys.argv[2] if len(sys.argv) > 2 else "graded"          # e.g. graded-v3b


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


img = {"base": np.asarray(Image.open(os.path.join(P, f"shell-furniture-{V}-{G}.png")).convert("RGB")).astype(float)}
allowed = {"base": None}
for S in "ABC":
    img[S] = np.asarray(Image.open(os.path.join(P, f"composite-set-{S}-{V}-{G}.png")).convert("RGB")).astype(float)
    a = np.asarray(Image.open(os.path.join(P, "layers/cushions", f"set-{S}.png")))[..., 3] > 0
    s = np.asarray(Image.open(os.path.join(P, "shadows/cushions", f"set-{S}.png")).convert("RGB")).min(2) < 255
    allowed[S] = a | s
labs = {k: lab(v) for k, v in img.items()}
out, worst = {}, None
for x, y in [("base", "A"), ("base", "B"), ("base", "C"), ("A", "B"), ("A", "C"), ("B", "C")]:
    al = np.zeros(img["base"].shape[:2], bool)
    for k in (x, y):
        if allowed[k] is not None:
            al |= allowed[k]
    d8 = np.abs(img[x] - img[y]).max(2)
    de = np.linalg.norm(labs[x] - labs[y], axis=2)
    o = ~al
    dd = de[o & (d8 > 0)]
    rec = dict(outside_px_gt2_levels=int(((d8 > 2) & o).sum()), outside_px_gt0=int(((d8 > 0) & o).sum()),
               dE76_max=round(float(dd.max()), 2) if dd.size else 0.0, dE76_p99=round(float(np.percentile(dd, 99)), 2) if dd.size else 0.0,
               outside_px_dE_ge_1=int(((de >= 1) & o).sum()))
    if dd.size:
        yy, xx = np.unravel_index(int(np.argmax(np.where(o, de, 0))), de.shape)
        rec["worst_at_px"] = [int(xx), int(yy)]
        rec["base_L_at_worst"] = round(float(labs[x][yy, xx, 0]), 1)
        rec["L_of_changed_px_p50_p95"] = [round(float(np.percentile(labs[x][..., 0][o & (de >= 1)], q)), 1) for q in (50, 95)] if rec["outside_px_dE_ge_1"] else None
        if worst is None or rec["dE76_max"] > worst[0]:
            worst = (rec["dE76_max"], xx, yy, x, y)
    out[f"{x}->{y}"] = rec
json.dump(out, open(os.path.join(OUT, "data", f"graded-split-{V}{'' if G == 'graded' else '-' + G}.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
if worst:
    _, xx, yy, x, y = worst
    tiles = [Image.fromarray(img[k].astype(np.uint8)).crop((xx - 60, yy - 60, xx + 60, yy + 60)).resize((480, 480), Image.NEAREST) for k in (x, y)]
    diff = (np.abs(img[x] - img[y]).max(2) * 20).clip(0, 255).astype(np.uint8)
    tiles.append(Image.fromarray(diff).crop((xx - 60, yy - 60, xx + 60, yy + 60)).resize((480, 480), Image.NEAREST).convert("RGB"))
    o_ = Image.new("RGB", (3 * 490, 480), (40, 40, 40))
    for i, t in enumerate(tiles):
        o_.paste(t, (i * 490, 0))
    o_.save(os.path.join(OUT, "overlays", f"graded-split-{V}{'' if G == 'graded' else '-' + G}.jpg"), quality=90)
