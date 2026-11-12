#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): the R9 BASELINE for P2-2 (docs/proposals/wm-pendant2-r9-eye-2026-11-12.md section 4): the left inner bands of
pendant 2. Measurement only; R9 is not judged on it (the manager's addendum). QA's own code; the same tool is meant to run on R10.

The frame (image space, so it does not depend on R6's clay map):
  - the paper: the layer's alpha == 255, eroded 5 x 5 (as R6's pendant_measures), rows >= the lantern top (200) + 3; out: the collar
    (|x - 1676.5| <= 9, y <= 206) and the bottom opening (an ellipse, centre (1673, 342), semi-axes 58 x 15 px, read off a x4 crop: the
    lamp holder's ring and the dark dashes);
  - the meridians: per row, the image longitude phi = asin((x - xc(y)) / hw(y)), xc and hw from the row's 50 % crossings (the lantern's
    own outline); 48 sectors of 7.5 deg round the lantern as R6 used, so 24 on the visible front: L1 (phi -90..-82.5, the left
    silhouette) .. L12 (-7.5..0), R1 (0..7.5) .. R12 (82.5..90). Inside a sector the pleats run along the profile and average out.
  - the profile: per sector and row, the mean L* of the sector's paper pixels on that row (>= 2 px), rows with data only; a sector needs
    >= 30 rows.
  - the smooth curve: a least-squares cubic B-spline with 4 interior knots, uniform over the sector's rows (the designer's "spline with
    about 4 knots over the lantern's height"); the residual = the profile minus the curve.
  - a step: |(L(y + 3) - L(y)) - (F(y + 3) - F(y))| > 1 L* (the designer's "more than 1 L* within 3 px, above the smooth curve"), the local
    peak of that, steps 6+ rows apart. Per step: the 3-px jump, the plateau height (the mean residual over y+3..y+8 minus over y-5..y-1),
    and the sharpness: the steepest one-row change against the curve's slope (L*/px) and the 10-90 % rise width (px) of the detrended
    profile over y-6..y+9.
  - the band lines: a step in sector k and a same-signed step in sector k+1 within 8 rows are one line; a line in 3+ sectors counts;
    bands in a half = its lines + 1.
  - both Labs: OpenCV float (R8's / R6's) and QA's numpy CIELAB D65 (as r8_curtains.py).
Also the P2-2 numbers that R10 is held to against R9: (b) the pleats' high-pass std (L* - GaussianBlur(sigmaX 3, sigmaY 0.01), R6's
measure) over the left half and the whole paper; (c) the left half's mean and median L*, its top third minus its bottom third (median, as
R6), left half against right half; (d) the median a*, b* (left half, whole).
Runs on R9 (the baseline) and on R8 (same RGB at alpha 255: a cross-check that R9 did not move the bands).
Writes data/bands.json, overlays/pendant-2-bands-profiles-r9.png (the left-half profiles with their curves and steps) and
overlays/pendant-2-bands-map-r9-x3.png (the sectors and the detected steps drawn on the lantern).
     ~/.venvs/motion/bin/python3.12 -I r9_bands.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
FILES = {"r9": "pendant/pendant-cj-pleated-pumpkin-lantern-40-r9.png", "r8": "pendant/pendant-cj-pleated-pumpkin-lantern-40-r6.png"}
TOP = 200
OPEN_C, OPEN_AX = (1673.0, 342.0), (58.0, 15.0)


def lab_cv(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB).astype(np.float64)


M_ = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
WP = np.array([0.95047, 1.0, 1.08883])


def lab_qa(rgb8):
    c = rgb8.astype(np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = c @ M_.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def bspline_basis(x, x0, x1, n_int=4, k=3):
    t_int = np.linspace(x0, x1, n_int + 2)[1:-1]
    t = np.concatenate([[x0] * (k + 1), t_int, [x1] * (k + 1)])
    nb = len(t) - k - 1
    B = np.zeros((len(x), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = (x >= t[i]) & (x < t[i + 1])
    B[x >= x1, nb - 1] = 1.0
    for d in range(1, k + 1):
        Bn = np.zeros((len(x), len(t) - d - 1))
        for i in range(len(t) - d - 1):
            a = (x - t[i]) / (t[i + d] - t[i]) * B[:, i] if t[i + d] > t[i] else 0
            b = (t[i + d + 1] - x) / (t[i + d + 1] - t[i + 1]) * B[:, i + 1] if t[i + d + 1] > t[i + 1] else 0
            Bn[:, i] = a + b
        B = Bn
    return B[:, :nb]


def frame(A, smooth=True):
    """per row: the 50 % crossings (xl, xr); smoothed by a degree-6 polynomial in y (so the meridians are smooth curves, not the outline's
    pixel jitter)"""
    rows = {}
    for y in range(TOP, A.shape[0]):
        a = A[y].astype(np.float64) / 255
        ins = np.nonzero(a >= 0.5)[0]
        if len(ins) < 10:
            continue
        i, j = ins.min(), ins.max()
        xl = i - 1 + (0.5 - a[i - 1]) / max(a[i] - a[i - 1], 1e-9)
        xr = j + (a[j] - 0.5) / max(a[j] - a[j + 1], 1e-9)
        rows[y] = (xl, xr)
    if smooth and rows:
        yy = np.array(sorted(rows), float)
        XL = np.array([rows[int(y)][0] for y in yy])
        XR = np.array([rows[int(y)][1] for y in yy])
        u = (yy - yy.mean()) / yy.std()
        pl, pr = np.polyfit(u, XL, 6), np.polyfit(u, XR, 6)
        rows = {int(y): (float(np.polyval(pl, v)), float(np.polyval(pr, v))) for y, v in zip(yy, u)}
    return rows


def paper_mask(A):
    m = A == 255
    m[:TOP + 3] = False
    m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    yy, xx = np.mgrid[0:A.shape[0], 0:A.shape[1]]
    m &= ~((np.abs(xx - 1676.5) <= 9) & (yy <= 206))
    m &= ((xx - OPEN_C[0]) / OPEN_AX[0]) ** 2 + ((yy - OPEN_C[1]) / OPEN_AX[1]) ** 2 > 1
    return m


def sector_map(A, m, rows):
    S = np.full(A.shape, -1, int)
    PHI = np.full(A.shape, np.nan)
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        if y not in rows:
            continue
        xl, xr = rows[y]
        xc, hw = (xl + xr) / 2, (xr - xl) / 2
        s = np.clip((x - xc) / hw, -1, 1)
        phi = np.degrees(np.arcsin(s))
        PHI[y, x] = phi
        S[y, x] = min(23, int((phi + 90) // 7.5))
    return S, PHI


def name_of(k):
    return f"L{k + 1}" if k < 12 else f"R{k - 11}"


def steps_of(yv, L, F):
    """the literal rule's steps; per step: the 3-px jump; the steepest one-row change of the detrended profile r = L - F near it; the
    plateaus round that row (median r over its 4 rows before, after a 1-row gap, and over its 4 rows after); the 10-90 % rise width
    between them (linear crossings); and the curve's own slope there"""
    out = []
    n = len(yv)
    d3 = np.full(n, 0.0)
    for i in range(n - 3):
        if yv[i + 3] - yv[i] == 3:
            d3[i] = (L[i + 3] - L[i]) - (F[i + 3] - F[i])
    cand = np.nonzero(np.abs(d3) > 1.0)[0]
    picked = []
    for i in cand[np.argsort(-np.abs(d3[cand]))]:
        if all(abs(yv[i] - yv[j]) >= 6 for j in picked):
            picked.append(i)
    R = L - F
    for i in sorted(picked):
        win = [j for j in range(max(0, i - 1), min(n - 1, i + 4)) if yv[j + 1] - yv[j] == 1]
        if not win:
            continue
        js = max(win, key=lambda j: abs(R[j + 1] - R[j]) * (1 if np.sign(R[j + 1] - R[j]) == np.sign(d3[i]) else 0))
        bef = R[max(0, js - 4):js] if js >= 1 else R[:1]
        aft = R[js + 2:js + 6]
        rec = dict(y=int(yv[i]), steep_row=int(yv[js]), jump3=round(float(d3[i]), 2), steepest_row_change=round(float(R[js + 1] - R[js]), 2),
                   curve_slope_per_row=round(float(F[min(js + 1, n - 1)] - F[js]), 3))
        if len(bef) >= 2 and len(aft) >= 2:
            h0, h1 = float(np.median(bef)), float(np.median(aft))
            h = h1 - h0
            rec["plateau"] = round(h, 2)
            seg_i = list(range(max(0, js - 3), min(n, js + 5)))
            r_ = (R[seg_i] - h0) / h if abs(h) > 0.3 else None
            rw = None
            if r_ is not None:
                yy = yv[seg_i].astype(float)

                def cross(level):
                    for q in range(len(r_) - 1):
                        if (r_[q] - level) * (r_[q + 1] - level) <= 0 and r_[q + 1] != r_[q]:
                            return yy[q] + (level - r_[q]) / (r_[q + 1] - r_[q]) * (yy[q + 1] - yy[q])
                    return None
                c1, c9 = cross(0.1), cross(0.9)
                rw = None if c1 is None or c9 is None else round(abs(c9 - c1), 2)
            rec["rise_10_90_px"] = rw
        else:
            rec["plateau"] = float("nan")
            rec["rise_10_90_px"] = None
        out.append(rec)
    return out


def lines_of(sect_steps, ks, tol=8, min_len=3):
    """chain same-signed steps in adjacent sectors within 8 rows"""
    used = set()
    lines = []
    for k in ks:
        for j, st in enumerate(sect_steps.get(k, [])):
            if (k, j) in used:
                continue
            chain = [(k, j)]
            used.add((k, j))
            kk, cur = k, st
            while kk + 1 in ks:
                nxt = [(jj, s) for jj, s in enumerate(sect_steps.get(kk + 1, [])) if (kk + 1, jj) not in used and np.sign(s["jump3"]) == np.sign(cur["jump3"])
                       and abs(s["y"] - cur["y"]) <= tol]
                if not nxt:
                    break
                jj, s = min(nxt, key=lambda q: abs(q[1]["y"] - cur["y"]))
                chain.append((kk + 1, jj))
                used.add((kk + 1, jj))
                kk, cur = kk + 1, s
            if len(chain) >= min_len:
                lines.append(dict(sectors=[name_of(a) for a, _ in chain], y=[sect_steps[a][b]["y"] for a, b in chain],
                                  jump3=[sect_steps[a][b]["jump3"] for a, b in chain], plateau=[sect_steps[a][b]["plateau"] for a, b in chain],
                                  rise_10_90_px=[sect_steps[a][b]["rise_10_90_px"] for a, b in chain],
                                  steepest_row_change=[sect_steps[a][b]["steepest_row_change"] for a, b in chain]))
    return lines


res = dict(frame=dict(top_row=TOP, opening_ellipse=dict(centre=OPEN_C, semi_axes=OPEN_AX), sectors="48 of 7.5 deg round the lantern; 24 visible",
                      erosion="5 x 5", knots=4, step_rule="> 1 L* within 3 px over the curve"))
keep_plot = {}
A9_ = np.asarray(Image.open(os.path.join(LD, FILES["r9"])))[..., 3]
A8_ = np.asarray(Image.open(os.path.join(LD, FILES["r8"])))[..., 3]
ROWS = frame(A9_)
MASK = paper_mask(np.where((A9_ == 255) & (A8_ == 255), 255, 0).astype(np.uint8))
S, PHI = sector_map(A9_, MASK, ROWS)
res["frame"]["mask"] = "both rounds on one mask: alpha 255 in R8 AND R9, then eroded; R9's outline for the meridians"
res["frame"]["paper_px"] = int(MASK.sum())
for tag, f in FILES.items():
    Lr = np.asarray(Image.open(os.path.join(LD, f)))
    A = Lr[..., 3]
    T = {}
    for lname, fn in (("opencv", lab_cv), ("qa", lab_qa)):
        LL = fn(Lr[..., :3])
        Lm = LL[..., 0]
        sec = {}
        sect_steps = {}
        d3_store = {}
        for k in range(24):
            sel = S == k
            ys = np.nonzero(sel.any(1))[0]
            yv, Lv, nv = [], [], []
            for y in ys:
                r_ = sel[y]
                if r_.sum() >= 2:
                    yv.append(y)
                    Lv.append(Lm[y][r_].mean())
                    nv.append(int(r_.sum()))
            if len(yv) < 30:
                sec[name_of(k)] = dict(rows=len(yv), measured=False)
                continue
            yv, Lv = np.array(yv), np.array(Lv)
            B = bspline_basis(yv.astype(float), float(yv.min()), float(yv.max()))
            coef, *_ = np.linalg.lstsq(B, Lv, rcond=None)
            F = B @ coef
            R = Lv - F
            st = steps_of(yv, Lv, F)
            d3all = [(Lv[i + 3] - Lv[i]) - (F[i + 3] - F[i]) for i in range(len(yv) - 3) if yv[i + 3] - yv[i] == 3]
            d3_store.setdefault("left" if k < 12 else "right", []).extend(d3all)
            sect_steps[k] = [q for q in st if abs(q["plateau"]) >= 2.0 and abs(q["jump3"]) >= 1.5]
            sec[name_of(k)] = dict(measured=True, rows=[int(yv.min()), int(yv.max())], n_rows=int(len(yv)), px=int(sel.sum()),
                                   residual_max_abs=round(float(np.abs(R).max()), 2), residual_p95_abs=round(float(np.percentile(np.abs(R), 95)), 2),
                                   steps_literal=st, n_steps_literal=len(st), strong_steps=sect_steps[k], n_strong=len(sect_steps[k]),
                                   max_jump3=round(float(max([abs(s["jump3"]) for s in st], default=0.0)), 2),
                                   profile=dict(y=[int(v) for v in yv], L=[round(float(v), 2) for v in Lv], fit=[round(float(v), 2) for v in F]))
            if tag == "r9" and lname == "qa":
                keep_plot[k] = (yv, Lv, F, [q for q in st if abs(q["jump3"]) >= 2 and np.isfinite(q["plateau"]) and abs(q["plateau"]) >= 2.5])
        # a band edge: a literal step with a 3-px jump >= 2 L* AND a plateau >= 2.5 L* (the right half, which the designer accepted, tops
        # out at 2.0: the threshold separates the two halves); chained over adjacent sectors within 25 rows (the edges fall steeply near
        # the silhouette)
        edge_steps = {k: [q for q in sec[name_of(k)]["steps_literal"] if abs(q["jump3"]) >= 2 and np.isfinite(q["plateau"]) and abs(q["plateau"]) >= 2.5]
                      for k in sect_steps}
        right_plateau_max = max([abs(q["plateau"]) for k in sect_steps if k >= 12 for q in sec[name_of(k)]["steps_literal"] if np.isfinite(q["plateau"])], default=0)
        left_plateau_max = max([abs(q["plateau"]) for k in sect_steps if k < 12 for q in sec[name_of(k)]["steps_literal"] if np.isfinite(q["plateau"])], default=0)
        left_k = [k for k in range(12) if k in sect_steps]
        right_k = [k for k in range(12, 24) if k in sect_steps]
        ll, rl = lines_of(sect_steps, left_k), lines_of(sect_steps, right_k)
        le, re_ = lines_of(edge_steps, left_k, tol=25, min_len=1), lines_of(edge_steps, right_k, tol=25, min_len=1)
        # P2-2's other numbers
        paper = S >= 0
        left, right = paper & (PHI < 0), paper & (PHI >= 0)
        hp = Lm - cv2.GaussianBlur(Lm.astype(np.float32), (0, 0), sigmaX=3.0, sigmaY=0.01).astype(np.float64)
        ys_ = np.nonzero(left.any(1))[0]
        y0, y1 = ys_.min(), ys_.max() + 1
        third = (y1 - y0) / 3
        topm, botm = left.copy(), left.copy()
        topm[int(y0 + third):] = False
        botm[:int(y1 - third)] = False
        T[lname] = dict(
            sectors=sec,
            plateau_max=dict(left=round(float(left_plateau_max), 2), right=round(float(right_plateau_max), 2)),
            band_edge_rule="literal step with |3-px jump| >= 2 L* and |plateau| >= 2.5 L*; chained over adjacent sectors within 25 rows",
            noise_floor=dict(rule="|d3| = |(L(y+3)-L(y)) - (F(y+3)-F(y))| over every row of every sector",
                             left=dict(p50=round(float(np.percentile(np.abs(d3_store["left"]), 50)), 2), p95=round(float(np.percentile(np.abs(d3_store["left"]), 95)), 2),
                                       share_gt1=round(float((np.abs(d3_store["left"]) > 1).mean()), 3)),
                             right=dict(p50=round(float(np.percentile(np.abs(d3_store["right"]), 50)), 2), p95=round(float(np.percentile(np.abs(d3_store["right"]), 95)), 2),
                                        share_gt1=round(float((np.abs(d3_store["right"]) > 1).mean()), 3))),
            left_half=dict(sectors_measured=[name_of(k) for k in left_k], sectors_with_a_strong_step=[name_of(k) for k in left_k if sect_steps[k]],
                           literal_steps=int(sum(sec[name_of(k)]["n_steps_literal"] for k in left_k)),
                           strong_steps=int(sum(len(sect_steps[k]) for k in left_k)), lines=ll, band_lines=len(ll), bands=len(ll) + 1,
                           band_edges=le, band_edge_count=len(le), bands_by_edges=len(le) + 1,
                           residual_max_abs=round(max(sec[name_of(k)]["residual_max_abs"] for k in left_k), 2),
                           sectors_residual_gt1=[name_of(k) for k in left_k if sec[name_of(k)]["residual_max_abs"] > 1]),
            right_half=dict(sectors_measured=[name_of(k) for k in right_k], sectors_with_a_strong_step=[name_of(k) for k in right_k if sect_steps[k]],
                            literal_steps=int(sum(sec[name_of(k)]["n_steps_literal"] for k in right_k)),
                            strong_steps=int(sum(len(sect_steps[k]) for k in right_k)), lines=rl, band_lines=len(rl), bands=len(rl) + 1,
                            band_edges=re_, band_edge_count=len(re_), bands_by_edges=len(re_) + 1,
                            residual_max_abs=round(max(sec[name_of(k)]["residual_max_abs"] for k in right_k), 2),
                            sectors_residual_gt1=[name_of(k) for k in right_k if sec[name_of(k)]["residual_max_abs"] > 1]),
            p2_2_baseline=dict(
                pleats_hp_std=dict(left_half=round(float(hp[left].std()), 3), whole=round(float(hp[paper].std()), 3)),
                light=dict(left_mean_L=round(float(Lm[left].mean()), 2), left_median_L=round(float(np.median(Lm[left])), 2),
                           right_mean_L=round(float(Lm[right].mean()), 2), left_minus_right_mean=round(float(Lm[left].mean() - Lm[right].mean()), 2),
                           left_top_third_minus_bottom_third_median=round(float(np.median(Lm[topm]) - np.median(Lm[botm])), 2), left_rows=[int(y0), int(y1 - 1)]),
                colour=dict(left_median_a=round(float(np.median(LL[..., 1][left])), 2), left_median_b=round(float(np.median(LL[..., 2][left])), 2),
                            whole_median_a=round(float(np.median(LL[..., 1][paper])), 2), whole_median_b=round(float(np.median(LL[..., 2][paper])), 2)),
                px=dict(paper=int(paper.sum()), left=int(left.sum()), right=int(right.sum()))))
        print(tag, lname, "noise", T[lname]["noise_floor"], "| left literal", T[lname]["left_half"]["literal_steps"], "right literal", T[lname]["right_half"]["literal_steps"])
        print(tag, lname, "left: strong steps", T[lname]["left_half"]["strong_steps"], "lines", len(ll), "bands", len(ll) + 1, "resid max", T[lname]["left_half"]["residual_max_abs"],
              "| right: strong steps", T[lname]["right_half"]["strong_steps"], "lines", len(rl), "resid max", T[lname]["right_half"]["residual_max_abs"], flush=True)
        for ln in le:
            print("   L edge", ln["sectors"], ln["y"], ln["jump3"], ln["plateau"], ln["rise_10_90_px"], ln["steepest_row_change"], flush=True)
        for ln in re_:
            print("   R edge", ln["sectors"], ln["y"], ln["jump3"], ln["plateau"], ln["rise_10_90_px"], flush=True)
        print("   ", T[lname]["p2_2_baseline"], flush=True)
    res[tag] = T
# R8 vs R9: the same bands (R9 changed no RGB at alpha 255)
res["r8_vs_r9_same_profiles"] = all(
    res["r8"]["qa"]["sectors"][s].get("profile", {}).get("L") == res["r9"]["qa"]["sectors"][s].get("profile", {}).get("L") for s in res["r9"]["qa"]["sectors"])
json.dump(res, open(os.path.join(OUT, "data/bands.json"), "w"), indent=1)

# ------------------------------------------------------------------ the overlays
# 1. the left-half profiles (QA Lab, R9): one strip per sector, L* against the row, the curve dashed, the steps marked
ks = [k for k in range(12) if k in keep_plot]
Wp, Hp, pad = 230, 330, 30
img = Image.new("RGB", (pad + len(ks) * Wp, Hp + 60), (250, 250, 248))
d = ImageDraw.Draw(img)
allL = np.concatenate([keep_plot[k][1] for k in ks])
lo, hi = np.floor(allL.min()) - 1, np.ceil(allL.max()) + 1
for c, k in enumerate(ks):
    yv, Lv, F, st = keep_plot[k]
    x0 = pad + c * Wp
    d.rectangle([x0 + 5, 30, x0 + Wp - 5, 30 + Hp - 20], outline=(180, 180, 180))
    d.text((x0 + 10, 8), f"{name_of(k)} ({-90 + 7.5 * k:.1f}..{-82.5 + 7.5 * k:.1f} deg)", fill=(20, 20, 20))

    def P(y, L):
        return (x0 + 10 + (L - lo) / (hi - lo) * (Wp - 25), 30 + (y - 200) / 165 * (Hp - 25))
    d.line([P(y, L) for y, L in zip(yv, Lv)], fill=(30, 30, 30), width=1)
    for i in range(0, len(yv) - 1, 2):
        d.line([P(yv[i], F[i]), P(yv[i + 1], F[i + 1])], fill=(200, 60, 60), width=1)
    for s in st:
        px_, py_ = P(s["y"], Lv[list(yv).index(s["y"])])
        d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], outline=(0, 90, 200), width=2)
d.text((pad, Hp + 40), f"pendant 2, R9 layer, left half: per-sector L* (QA Lab) down the meridian (rows 200-365), black; 4-knot curve, red; band edges (3-px jump >= 2 L*, plateau >= 2.5 L*), blue. L* axis {lo:.0f}..{hi:.0f}",
       fill=(20, 20, 20))
img.save(os.path.join(OUT, "overlays/pendant-2-bands-profiles-r9.png"))

# 2. the map: the R9 truth around the whole lantern at x3, sector borders and the steps
T9 = np.asarray(Image.open(os.path.join(P2, "graded/variant-r9-pendant-v2-set-B-graded-v3c.png")).convert("RGB"))
x0, y0, x1, y1 = 1540, 190, 1810, 368
cr = Image.fromarray(T9[y0:y1, x0:x1]).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS)
dd = ImageDraw.Draw(cr)
rows9 = ROWS
for k in range(1, 24):
    phi = np.radians(-90 + 7.5 * k)
    pts = [((((xl + xr) / 2 + (xr - xl) / 2 * np.sin(phi)) - x0) * 3, (y - y0) * 3) for y, (xl, xr) in sorted(rows9.items()) if y0 <= y < y1]
    dd.line(pts, fill=(120, 160, 255) if k != 12 else (255, 120, 120), width=1)
for k, (yv, Lv, F, st) in keep_plot.items():
    phi = np.radians(-90 + 7.5 * k + 3.75)
    for s in st:
        xl, xr = rows9[s["y"]]
        cx = ((xl + xr) / 2 + (xr - xl) / 2 * np.sin(phi) - x0) * 3
        cy = (s["y"] - y0) * 3
        col = (220, 40, 40) if s["jump3"] < 0 else (40, 160, 40)
        dd.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=col, width=2)
cr.save(os.path.join(OUT, "overlays/pendant-2-bands-map-r9-x3.png"))
print("overlays written; R8 = R9 profiles:", res["r8_vs_r9_same_profiles"], flush=True)
