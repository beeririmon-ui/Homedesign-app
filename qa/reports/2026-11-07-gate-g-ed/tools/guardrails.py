"""qa-agent, 2026-11-07: numeric aids for the G-ED grading guardrails (CR5). The verdict stays by eye.

G-ED.12 clipped highlights: share of pixels with any channel >= 254 (clipped) and >= 250 (near clip),
whole frame; when a frame is over 1 %, pass a window mask (x0,y0,x1,y1 boxes) to exclude the window.
G-ED.11 orange-teal aid: mean a*, b* (CIELAB, D65) of the darkest and the brightest 10 % of pixels by L*.
G-ED.11 shadow floor (Bible 1.9, Nordic: the deepest shadow L* >= 8): L* at the 0.5th and 1st percentile
on a quarter-size copy (so single dark pixels do not decide).
A split grade shows as shadows b* < -4 together with highlights b* > +15; the light story can explain it
(japandi blue hour, country rain against lamps), so it is a prompt to look, not a fail.

Run it on the model's raw output too: a soft knee in finishing moves clipped pixels below 254 without
bringing their detail back, so G-ED.12 is judged on the raw (assets/renders/<round>/raw/).
Usage: ~/.venvs/motion/bin/python -I guardrails.py <frame.png> [<frame.png> ...] [--window x0,y0,x1,y1 ...] --out <json>
"""
import json
import sys

import numpy as np
from PIL import Image


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def measure(path, windows):
    im = np.asarray(Image.open(path).convert("RGB"))
    h, w, _ = im.shape
    keep = np.ones((h, w), bool)
    for x0, y0, x1, y1 in windows:
        keep[y0:y1, x0:x1] = False
    mx = im.max(2)
    n = keep.sum()
    out = dict(file=path, size=[w, h], window_boxes=windows,
               clipped_254_pct=round(float(((mx >= 254) & keep).sum() / n * 100), 3),
               near_clip_250_pct=round(float(((mx >= 250) & keep).sum() / n * 100), 3))
    try:
        import cv2
        m = ((mx >= 254) & keep).astype(np.uint8)
        n_, _, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((9, 9), np.uint8)))
        comps = sorted(([int(st[i, 4]), [int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])]] for i in range(1, n_)), reverse=True)[:3]
        out["clipped_top_components_px_box"] = comps
    except ImportError:
        out["clipped_top_components_px_box"] = "cv2 not available"
    small = np.asarray(Image.fromarray(im).resize((w // 4, h // 4), Image.BILINEAR)).reshape(-1, 3).astype(float)
    L = lab(small)
    order = np.argsort(L[:, 0])
    k = len(order) // 10
    dark, bright = L[order[:k]], L[order[-k:]]
    out["shadows_10pct_Lab"] = [round(float(v), 1) for v in dark.mean(0)]
    out["highlights_10pct_Lab"] = [round(float(v), 1) for v in bright.mean(0)]
    out["split_flag"] = bool(dark[:, 2].mean() < -4 and bright[:, 2].mean() > 15)
    out["shadow_floor_L_p0_5"] = round(float(np.percentile(L[:, 0], 0.5)), 1)
    out["shadow_floor_L_p1"] = round(float(np.percentile(L[:, 0], 1)), 1)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    out_path = args[args.index("--out") + 1]
    windows = []
    if "--window" in args:
        i = args.index("--window") + 1
        while i < len(args) and not args[i].startswith("--"):
            windows.append([int(v) for v in args[i].split(",")])
            i += 1
    frames = [a for a in args if a.endswith(".png")]
    res = [measure(p, windows) for p in frames]
    json.dump(res, open(out_path, "w"), indent=1)
    for r in res:
        print(r["file"].split("/")[-1], r["clipped_254_pct"], r["near_clip_250_pct"], r["shadows_10pct_Lab"], r["highlights_10pct_Lab"], r["split_flag"])
