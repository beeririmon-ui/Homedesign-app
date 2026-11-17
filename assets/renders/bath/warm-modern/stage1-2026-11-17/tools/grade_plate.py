#!/usr/bin/env python3
"""
grade_plate.py: QA round 1 on the B2 plate (qa/reports/2026-11-17-bath-plate/README.md), render-agent, 2026-11-17. 0 tokens.
  BP-L1: the niche LED read as a 1-3 px bright line under the niche head (x about 980-1100, y 586-593, rising to the right). Painted
         in the soffit's own tone (per column, the soffit rows just above the line), only where a pixel is brighter than that soffit;
         the wash on the back wall below stays.
  BP-M1: the display grade WM-G1 (black point L* 11-14). Round 3 (QA round 2: the round-2 straight segment (0,0)-(1.42,12.5) had a slope
         of 8.8 and made the near-black pixels into "soot", and keeping a*/b* turned the shadowed walnut grey):
         - L*: a smooth toe f(L) = L + A (1 - L/K)^2 below the knee K = 30, identity above. f(0) = A, f'(L) = 1 - (2A/K)(1 - L/K), so
           the slope is 1 - 2A/K (0.27 for A 11) at black and rises to exactly 1 at the knee: never above 1, and continuous at K;
         - chroma lifts with the lightness: a*, b* += (f(L) - L) * r, r = (a*, b*) / L* of base.png's shadowed walnut (14.4, 5.1, 6.4),
           so a pixel lifted from black lands on that walnut-shadow ratio, and the lift fades to 0 at the knee;
         - pointwise only, no blur and no neighbourhood: the same pixel gives the same result in every asset.
         Nothing at L* 30 or above changes. The curve is written to plate-grade.json; every asset derived from the plate (output 2, the
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
A, KNEE = 11.0, 30.0
SHADOW_WALNUT = (14.4, 5.1, 6.4)                    # base.png's walnut in shadow (QA round 2)
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


def curve_apply(rgb, c):
    """c: dict(A, knee, chroma_per_lift=[ra, rb]). Pointwise."""
    lab = to_lab(rgb)
    L = lab[..., 0]
    m = L < c["knee"]                                 # below the knee only
    Lm = L[m]
    lift = c["A"] * (1 - Lm / c["knee"]) ** 2
    new = lab[m].copy()
    new[:, 0] = Lm + lift
    new[:, 1] += lift * c["chroma_per_lift"][0]
    new[:, 2] += lift * c["chroma_per_lift"][1]
    out = rgb.copy()
    out[m] = from_lab(new)
    return out, m


def de00(l1, l2):
    """CIEDE2000 between two Lab triples (arrays ... x 3)."""
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2[..., 0], l2[..., 1], l2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(np.abs(dh) > 180, dh - 360 * np.sign(dh), dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hpm = np.where(np.abs(h1p - h2p) > 180, (hs + 360) / 2, hs / 2) % 360
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dth = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def neighbour_contrast(L, mask):
    """Per pixel: the mean |L* difference| to its 4 neighbours; returned for the pixels of mask."""
    d = np.zeros_like(L)
    for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
        d += np.abs(L - np.roll(L, sh, axis=ax))
    return (d / 4)[mask]


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
        r = [SHADOW_WALNUT[1] / SHADOW_WALNUT[0], SHADOW_WALNUT[2] / SHADOW_WALNUT[0]]
        c = dict(kind="smooth toe + chroma lift", A=A, knee=KNEE, chroma_per_lift=[round(r[0], 5), round(r[1], 5)],
                 formula="L < knee: L' = L + A (1 - L/knee)^2; a*' = a* + (L' - L) * r_a; b*' = b* + (L' - L) * r_b; L >= knee: unchanged",
                 slope_at_black=round(1 - 2 * A / KNEE, 4), slope_at_knee=1.0, f0=A, shadow_walnut_target=list(SHADOW_WALNUT))
        out, m = curve_apply(rgb, c)
        after = frame_p05(out)
        # the checks QA asked for
        x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
        L0, L1 = to_lab(rgb)[..., 0], to_lab(out)
        inf = np.zeros(L0.shape, bool)
        inf[y0:y1, x0:x1] = True
        reg = inf & (L0 < p05)
        nc_before, nc_after = neighbour_contrast(L0, reg), neighbour_contrast(L1[..., 0], reg)
        above = float(np.abs(L1[..., 0] - L0)[L0 >= KNEE].max())
        chk = dict(p05_after=round(after, 2), p05_ok=bool(11 <= after <= 14), max_dL_at_or_above_knee=round(above, 4),
                   neighbour_contrast_p90_in_the_region_under_p05=dict(before=round(float(np.percentile(nc_before, 90)), 3),
                                                                          after=round(float(np.percentile(nc_after, 90)), 3), px=int(reg.sum())))
        ids_p = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/B2-plate-id.png"
        ids = np.asarray(Image.open(ids_p))
        rows = np.arange(ids.shape[0])[:, None]
        shelf = (ids == 20) & (rows > 1235) & inf & (L1[..., 0] >= 10) & (L1[..., 0] <= 20)       # the open shelf, below the drawer
        if shelf.any():
            med = np.median(L1[shelf], 0)
            chk["shelf_walnut_L10_20"] = dict(px=int(shelf.sum()), median_Lab=[round(float(v), 2) for v in med],
                                              de00_to_target=round(float(de00(med, np.array(SHADOW_WALNUT))), 2),
                                              C_over_L=round(float(np.hypot(med[1], med[2]) / med[0]), 3))
        json.dump(dict(source=src, rule="WM-G1 (black point L* 11-14), round 3 after QA round 2: a smooth toe on L* whose slope never exceeds 1, "
                                        "with the chroma lifted with the lift toward base.png's shadowed walnut; pointwise; nothing at L* 30 or above changes",
                       curve=c, p05_before_bp_l1=round(p_raw, 2), p05_before=round(p05, 2), p05_after=round(after, 2),
                       changed_px_share=round(float(m.mean()), 4), checks=chk,
                       replaces="round 2's piecewise-linear toe (0,0) (1.42,12.5) (30,30) (100,100) with a*/b* kept: soot and grey walnut (QA round 2)",
                       bp_l1=dict(px=n_led, box=dict(x=LED["x"], y=LED["y"]),
                                  rule="per column: the line's peak row; the soffit = median of rows peak-5..peak-3; rows peak-2..peak+2 brighter "
                                       "than it by more than 2 L* move to it (fully at +6); columns whose peak is not 4 L* over both the soffit and the wall below are left alone"),
                       derived_assets="grade every asset derived from this plate with: python3 grade_plate.py apply <in> <out> plate-grade.json"),
                  open(rec, "w"), indent=1)
        print("BP-L1 px", n_led, "p0.5", round(p05, 2), "->", round(after, 2), "changed", round(float(m.mean()), 4))
        print(json.dumps(chk, indent=1))
    else:
        c = json.load(open(rec))["curve"]
        out, m = curve_apply(rgb, c)
        print("applied", c["kind"], "changed", round(float(m.mean()), 4))
    Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)).save(dst)


if __name__ == "__main__":
    main()
