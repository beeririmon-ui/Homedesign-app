#!/usr/bin/env python3
"""
grade_plate.py: QA round 1 on the B2 plate (qa/reports/2026-11-17-bath-plate/README.md), render-agent, 2026-11-17. 0 tokens.
  BP-L1: the niche LED read as a 1-3 px bright line under the niche head (x about 980-1100, y 586-593, rising to the right). Painted
         in the soffit's own tone (per column, the soffit rows just above the line), only where a pixel is brighter than that soffit;
         the wash on the back wall below stays.
  BP-M1: the display grade WM-G1 (black point L* 11-14), as grade_d0.py: a toe on L* only (a*, b* kept), piecewise linear through
         (0, 0), (p0.5, 12.5), (30, 30), (100, 100), where p0.5 is the plate's own (the 16:9 frame). Nothing at L* 30 or above changes.
         The curve is written to plate-grade.json with its fixed control points; every asset derived from the plate (output 2, the
         towel variants, the layers) is graded with THE SAME curve (`apply` below), never re-solved, so RND2 (0 outside the masks) holds.

  python3 grade_plate.py make  <plate-ungraded.png> <plate.png> <plate-grade.json>
  python3 grade_plate.py apply <in.png> <out.png> <plate-grade.json>        # the recorded curve on a derived asset (no BP-L1)
"""
import json
import sys

import numpy as np
from PIL import Image

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
TARGET, KNEE = 12.5, 30.0
LED = dict(x=(970, 1110), y=(585, 594))


def to_lab(rgb):
    l = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    f = l @ M.T / WP
    f = np.where(f > 216 / 24389, np.cbrt(f), (24389 / 27 * f + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    l = np.clip(xyz @ np.linalg.inv(M).T, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def frame_p05(rgb):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    return float(np.percentile(to_lab(rgb[y0:y1, x0:x1])[..., 0], 0.5))


def curve_apply(rgb, xp, fp):
    lab = to_lab(rgb)
    L = lab[..., 0]
    m = L < xp[-2]                                   # below the knee only
    lab[..., 0] = np.interp(L, xp, fp)
    out = rgb.copy()
    out[m] = from_lab(lab[m])
    return out, m


def bp_l1(rgb):
    """Per column: the line's peak row in the box; the soffit = the median of the 3 rows just above the line (peak-5 .. peak-3);
    rows peak-2 .. peak+2 brighter than that soffit by more than 2 L* move to it (fully at +6)."""
    lab = to_lab(rgb)
    out = rgb.copy()
    n = 0
    (x0, x1), (y0, y1) = LED["x"], LED["y"]
    for x in range(x0, x1):
        col = lab[y0:y1 + 2, x, 0]
        pk = y0 + int(np.argmax(col))
        sof = np.median(rgb[pk - 5:pk - 2, x], 0)
        sofL = float(to_lab(sof[None])[0, 0])
        below = float(np.median(lab[pk + 3:pk + 6, x, 0]))
        if lab[pk, x, 0] - sofL < 4.0 or lab[pk, x, 0] - below < 4.0:     # no line here (a line is brighter than above AND below)
            continue
        for y in range(pk - 2, pk + 3):
            ex = lab[y, x, 0] - sofL
            if ex > 2.0:
                w = min(1.0, (ex - 2.0) / 4.0)
                out[y, x] = rgb[y, x] * (1 - w) + sof * w
                n += 1
    return out, n


def main():
    mode, src, dst, rec = sys.argv[1:5]
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float64) / 255
    if mode == "make":
        p_raw = frame_p05(rgb)
        rgb, n_led = bp_l1(rgb)
        p05 = frame_p05(rgb)
        xp, fp = [0.0, p05, KNEE, 100.0], [0.0, TARGET, KNEE, 100.0]
        out, m = curve_apply(rgb, xp, fp)
        after = frame_p05(out)
        json.dump(dict(source=src, rule="WM-G1: black point L* 11-14; toe on L* only (a*, b* kept), piecewise linear through the points below; "
                                        "nothing at L* 30 or above changes; no exposure change",
                       curve=dict(L_in=[round(v, 4) for v in xp], L_out=fp), knee=KNEE, p05_before_bp_l1=round(p_raw, 2), p05_before=round(p05, 2),
                       p05_after=round(after, 2), changed_px_share=round(float(m.mean()), 4),
                       bp_l1=dict(px=n_led, box=dict(x=LED["x"], y=LED["y"]),
                                  rule="per column: the line's peak row; the soffit = median of rows peak-5..peak-3; rows peak-2..peak+2 brighter "
                                       "than it by more than 2 L* move to it (fully at +6); columns whose peak is not 4 L* over both the soffit and the wall below are left alone"),
                       derived_assets="grade every asset derived from this plate with: python3 grade_plate.py apply <in> <out> plate-grade.json"),
                  open(rec, "w"), indent=1)
        print("BP-L1 px", n_led, "p0.5", round(p05, 2), "->", round(after, 2), "changed", round(float(m.mean()), 4))
    else:
        c = json.load(open(rec))["curve"]
        out, m = curve_apply(rgb, c["L_in"], c["L_out"])
        print("applied", c, "changed", round(float(m.mean()), 4))
    Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)).save(dst)


if __name__ == "__main__":
    main()
