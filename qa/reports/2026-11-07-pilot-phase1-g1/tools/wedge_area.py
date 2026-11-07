"""
qa-agent 2026-11-07: QA's own measure of the wedge residual, on the designer's condition (docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md
section 12, condition (1)): over the triptych and sconce area (back wall, frame u 0.45-0.85, v 0.15-0.45) the max L* change over 120 px <= 2.5.
QA's version differs from render-agent's step120 (rows and columns only) in that it also takes both diagonals, centres the 120 px span on
each pixel, and reports p99 and p95 next to the max (a single spot against the whole area).
L* = CIE L* (D65) of the image; low frequencies = blur sigma 12 normalised inside the back wall (r4 clay index 5, eroded 15 px, read only
from the shared scratchpad). Also: the whole back wall's left-to-right falloff (column medians of the mid-height band, v 0.35-0.75 of the
wall), against the designer's "soft falloff up to 6 L* along the whole wall".
Usage: ~/.venvs/motion/bin/python -I wedge_area.py <png> [<png> ...] (names inside the pilot folder). Writes data/wedge-area.json (merged).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r4-shell-idx/M0.npz"
W, H = 2720, 1530
idx = np.load(IDX)["idx"]
wall = cv2.resize((idx == 5).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
k = cv2.erode(wall, np.ones((15, 15), np.uint8)).astype(np.float32)
sel = k > 0
ax0, ax1 = int((116 + 0.45 * 3840) / 4072 * W), int((116 + 0.85 * 3840) / 4072 * W)
ay0, ay1 = int((65 + 0.15 * 2160) / 2290 * H), int((65 + 0.45 * 2160) / 2290 * H)
area = np.zeros((H, W), bool)
area[ay0:ay1, ax0:ax1] = True
area &= sel


def Lstar(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


CORE_X0 = 1350          # QA's core: the area minus its left 120 px, where every 120 px span stays clear of the corner's falloff (the back
                        # wall darkens toward the inside corner, x 1090-1290 at 2720: architecture, not the window wedge)


def measure(name):
    L = Lstar(np.asarray(Image.open(os.path.join(P, name)).convert("RGB")).astype(np.float64)).astype(np.float32)
    LF = cv2.GaussianBlur(L * k, (0, 0), 12) / np.maximum(cv2.GaussianBlur(k, (0, 0), 12), 1e-4)
    best = np.zeros((H, W), np.float32)
    dirs = {"row": (60, 0), "column": (0, 60), "diag_down": (42, 42), "diag_up": (42, -42)}   # 120 px span (diagonals 2 x 59.4 px)
    per = {}
    inside = np.zeros((H, W), np.float32)      # both ends of the 120 px span inside the area (the designer's condition, read literally)
    for n, (dx, dy) in dirs.items():
        M1 = np.float32([[1, 0, -dx], [0, 1, -dy]])
        M2 = np.float32([[1, 0, dx], [0, 1, dy]])
        a = cv2.warpAffine(LF, M1, (W, H), flags=cv2.INTER_NEAREST)         # LF(p + d)
        b = cv2.warpAffine(LF, M2, (W, H), flags=cv2.INTER_NEAREST)         # LF(p - d)
        sa = cv2.warpAffine(sel.astype(np.uint8), M1, (W, H), flags=cv2.INTER_NEAREST) > 0
        sb = cv2.warpAffine(sel.astype(np.uint8), M2, (W, H), flags=cv2.INTER_NEAREST) > 0
        d = np.where(area & sa & sb, np.abs(a - b), 0)
        per[n] = round(float(d.max()), 2)
        best = np.maximum(best, d)
        ia = cv2.warpAffine(area.astype(np.uint8), M1, (W, H), flags=cv2.INTER_NEAREST) > 0
        ib = cv2.warpAffine(area.astype(np.uint8), M2, (W, H), flags=cv2.INTER_NEAREST) > 0
        inside = np.maximum(inside, np.where(area & ia & ib, np.abs(a - b), 0))
    v = best[area & (best > 0)]
    core = area.copy()
    core[:, :CORE_X0] = False
    vc = best[core & (best > 0)]
    yc, xc = np.unravel_index(int(np.argmax(np.where(core, best, 0))), best.shape)
    y, x = np.unravel_index(int(np.argmax(best)), best.shape)
    # the whole wall's falloff, mid-height band
    rows = np.nonzero(sel.any(1))[0]
    cols = np.nonzero(sel.any(0))[0]
    med = []
    for xx in range(int(cols.min()) + 20, int(cols.max()) - 20, 20):
        rr = np.nonzero(sel[:, xx])[0]
        if len(rr) < 100:
            continue
        lo, hi = rr.min() + 0.35 * (rr.max() - rr.min()), rr.min() + 0.75 * (rr.max() - rr.min())
        band = rr[(rr >= lo) & (rr <= hi)]
        med.append((xx, float(np.median(LF[band, xx]))))
    m = np.array([q[1] for q in med])
    vi = inside[area & (inside > 0)]
    yi, xi = np.unravel_index(int(np.argmax(inside)), inside.shape)
    return dict(area_px=[ax0, ax1, ay0, ay1],
                both_ends_in_area=dict(max_dL_120=round(float(vi.max()), 2), p99=round(float(np.percentile(vi, 99)), 2),
                                       share_over_2_5_pct=round(float((vi > 2.5).mean() * 100), 2), worst_at_px=[int(xi), int(yi)]),
                centred_span_any_wall_max_dL_120=round(float(v.max()), 2), p99=round(float(np.percentile(v, 99)), 2),
                p95=round(float(np.percentile(v, 95)), 2), share_over_2_5_pct=round(float((v > 2.5).mean() * 100), 2),
                worst_at_px=[int(x), int(y)], per_direction_max=per,
                core_from_x1350=dict(max_dL_120=round(float(vc.max()), 2), p99=round(float(np.percentile(vc, 99)), 2),
                                     share_over_2_5_pct=round(float((vc > 2.5).mean() * 100), 2), worst_at_px=[int(xc), int(yc)]),
                wall_falloff_mid_band=dict(max=round(float(m.max()), 1), min=round(float(m.min()), 1), range=round(float(m.max() - m.min()), 1),
                                           left=round(float(m[:5].mean()), 1), right=round(float(m[-5:].mean()), 1)))


fn = os.path.join(OUT, "data", "wedge-area.json")
res = json.load(open(fn)) if os.path.exists(fn) else {}
for name in sys.argv[1:]:
    res[name] = measure(name)
    print(name, json.dumps(res[name]))
json.dump(res, open(fn, "w"), indent=1)
