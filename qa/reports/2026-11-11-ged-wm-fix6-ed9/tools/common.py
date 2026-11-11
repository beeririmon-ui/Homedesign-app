"""
qa-agent 2026-11-11: shared helpers for the box check on warm-modern-MB-A-fix6 (master) and warm-modern-A-ed9 (living room).
CIELAB D65 with the same formula as the gate's guardrails.py (qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py), written
again here (QA's own code, not render-agent's q_ed7_toe.py).
"""
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-11-ged-wm-fix6-ed9")
MB = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
LR = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
R5 = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")


def load(p):
    return np.asarray(Image.open(p).convert("RGB"))


def lab(rgb8):
    c = np.asarray(rgb8, np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def hue(a, b):
    return np.degrees(np.arctan2(b, a)) % 360


def mean_lab(lb, m):
    v = lb[m].mean(0)
    return dict(L=round(float(v[0]), 2), a=round(float(v[1]), 2), b=round(float(v[2]), 2),
                C=round(float(np.hypot(v[1], v[2])), 2), h=round(float(hue(v[1], v[2])), 1), px=int(m.sum()))


def gate_p(rgb8, qs=(0.5, 1, 5)):
    """G-ED.11's percentiles: L* on a quarter-size BILINEAR copy (the gate's guardrails.py)"""
    im = Image.fromarray(np.asarray(rgb8, np.uint8))
    w, h = im.size
    small = np.asarray(im.resize((w // 4, h // 4), Image.BILINEAR)).reshape(-1, 3)
    L = lab(small)[:, 0]
    return {f"p{q:g}": round(float(np.percentile(L, q)), 2) for q in qs}


def r(x, n=2):
    return round(float(x), n)
