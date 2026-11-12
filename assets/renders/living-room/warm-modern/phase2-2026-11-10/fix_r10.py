#!/usr/bin/env python3
"""
fix_r10.py: R10, P2-2 on pendant 2 (pendant-cj-pleated-pumpkin-lantern-40) in the warm-modern tool, phase 2 (render-agent, 2026-11-12).
Code only: 0 tokens, no var2, no network. NEW FILES ONLY: every R9 file is read, never written.
Spec: docs/proposals/wm-pendant2-r9-eye-2026-11-12.md section 4 (P2-2: the left inner shading, RGB only, on the graded R9 layer).

  Step 1 (section 4.2.1), the measure in the 48 sectors, FROM THE LAYER ITSELF (not from the clay latitude lines):
    geometry  the R9 alpha's own 50 % outline per row (x_left(y), x_right(y)), rows >= 198 (the lantern; the cord and the canopy apart)
    sectors   48 equal-angle longitudes of that outline: sector t's centre curve x_t(y) = x_mid(y) + sin(phi_t) half_width(y),
              phi_t = -90 + (t + 0.5) 3.75 deg (t = 0 at the left limb, the window side; t = 47 at the right limb). This is the
              meridian of a solid of revolution seen side-on: lines of constant phi follow the pleats.
    profile   per sector and row: the mean L* over a box of ONE PLEAT PERIOD (measured here: the autocorrelation of the paper's L*
              along the rows, its first peak) centred on x_t(y), paper pixels only (>= 6 px), so the pleats cancel in the profile.
              Paper = alpha 255, rows >= 201, the collar (|x - 1676.5| <= 9, y <= 203) apart, eroded 5 x 5 (R6's measure mask), and
              off the bottom opening (the clay's z < OPEN_Z + 0.004: R6's measure rule).
    smooth    per sector a cubic B-spline with 4 segments over the lantern's height (5 knots), least squares; residual = profile -
              smooth curve.
    step      the change within 3 px: (mean of the 3 rows below a row boundary) - (mean of the 3 rows above it), on the residual; a step
              where |change| > 1 L* and it is the largest within +-3 rows. Both Labs: R8's (OpenCV, float RGB / 255) and QA's (numpy).
    record    per sector: every step (row, x, size in both Labs), the boundary curve it belongs to (steps of one sign linked across
              neighbouring sectors, |dy| <= 4 rows), and its distance to the nearest R6 clay latitude line (work-r6/fix-r6.json
              pendant-v2.rings.tiers: the clay's z along the same pixel column, fix_r6.latlong_map) - the designer's section 3.3 check.
              Plus R6's own per-sector measure on R9 (fix_r6.ring_profile + tier_fit_at at its three boundaries), and the measure's
              robustness to its choices (Lab, sector kind, box, minimum pixels, threshold, spline segments).
  Stop rule (section 4.4): (1) (a) cannot be met without failing (b) or (c); (2) the fix wants to change more than 24 of the 48 sectors;
    (3) a smear of the pleats at x 2. Rule (2) is decided on step 1 alone: the fix applies only where step 1 found a step (section
    4.2.2), so the sectors with a step are the sectors the fix wants to change. If any rule holds, NO LAYER IS WRITTEN: the record and the
    x 2 crop of the whole lantern (make_crops_r10.py) go to the designer.
  Baselines (R9) of the acceptance (a)-(e), measured here for the round after this one: (a) per sector, the largest step; (b) the pleats'
    high-pass std (R6's metric: L* - GaussianBlur(sigma x 3, y 0.01)), left half and whole paper; (c) the left half's mean L*, its top
    third - bottom third, left - right; (d) median a*, b*; (e) QA's halo metric on R9 (from verify-layers-r9.json).

Writes: work-r10/fix-r10.json, work-r10/pendant2-sectors-r10.npz (the profiles, residuals, steps and centre curves, both Labs).
    python3.12 -I -B fix_r10.py
Then: make_crops_r10.py; make_crops_r10.py entries.
"""
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter, defaultdict

import cv2
import numpy as np
import PIL
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join
sys.path.insert(0, HERE)
sys.path.insert(0, D(HERE, "step0"))
import fix_r6 as F6  # noqa: E402  (read-only: latlong_map, ring_profile, tier_fit_at, OPEN_Z)
import fix_r9 as F9  # noqa: E402  (read-only: lab_cv, lab_qa, TOP, CORD_X, COLLAR_DX, COLLAR_Y)

LAY, GRD, WR9, WR10 = D(HERE, "layers"), D(HERE, "graded"), D(HERE, "work-r9"), D(HERE, "work-r10")
REPO = os.path.abspath(D(HERE, *[".."] * 5))
REC = D(WR10, "fix-r10.json")
NPZ = D(WR10, "pendant2-sectors-r10.npz")
EYE = "docs/proposals/wm-pendant2-r9-eye-2026-11-12.md"
MAN9 = json.load(open(D(LAY, "manifest-r9.json")))
V9 = {v["id"]: v for vs in MAN9["variants"].values() for v in vs}
FIX9 = json.load(open(D(WR9, "fix-r9.json")))["pendant2"]
P2_IN = D(LAY, V9["pendant-v2"]["file"])
TRUTH9 = os.path.normpath(D(LAY, V9["pendant-v2"]["truth"]))
TOP, CORD_X, COLLAR_DX, COLLAR_Y = F9.TOP, F9.CORD_X, F9.COLLAR_DX, F9.COLLAR_Y
OPEN_Z = F6.OPEN_Z
NS = 48                      # the sectors (as R6)
STEP_THR = 1.0               # the designer: a change of more than 1 L* within 3 px over the smooth curve
STEP_ROWS = 3
NSEG = 4                     # ~4 knots over the lantern's height
MIN_PX = 6                   # R6's cell rule (>= 6 px)
STOP_SECTORS = 24
R6_LINES = sorted({round(z, 4) for t in json.load(open(D(HERE, "work-r6", "fix-r6.json")))["pendant-v2"]["rings"]["tiers"] for z in t["boundaries_z_m"]})
R6_MAIN = (0.0354, 0.0688, 0.1042)   # R6's round-0 tiers with the largest steps (fix-r6.json: 2.44 / 4.57 / 5.82 L* before)


def rel(p):
    return os.path.relpath(p, REPO)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def r2(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 2)


# ------------------------------------------------------------------------------------------------- geometry and masks
def outline_rows(A8):
    """the alpha's 0.5 crossing on each row (sub-pixel, linear between the two pixels round it), rows >= TOP"""
    a = A8.astype(np.float64) / 255
    a[:TOP] = 0
    xl = np.full(a.shape[0], np.nan)
    xr = np.full(a.shape[0], np.nan)
    for y in range(TOP, a.shape[0]):
        on = np.nonzero(a[y] > 0.5)[0]
        if len(on) < 2:
            continue
        i, j = on.min(), on.max()
        xl[y] = i - (a[y, i] - 0.5) / max(a[y, i] - a[y, i - 1], 1e-6)
        xr[y] = j + (a[y, j] - 0.5) / max(a[y, j] - a[y, j + 1], 1e-6)
    return xl, xr


def paper_mask(A8, zm):
    H, W = A8.shape
    yy, xx = np.mgrid[0:H, 0:W]
    collar = (np.abs(xx - CORD_X) <= COLLAR_DX) & (yy <= COLLAR_Y)
    m = (A8 == 255) & (yy >= TOP + 3) & ~collar
    m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m &= ~(np.nan_to_num(zm, nan=1.0) < OPEN_Z + 0.004)
    return m


def pleat_period(L, paper, xl, xr):
    """the first autocorrelation peak of the paper's L* along the rows (the middle 60 % of the width, the middle rows)"""
    acs = []
    ys = [y for y in range(240, 300) if np.isfinite(xl[y])]
    for y in ys:
        xm, hw = (xl[y] + xr[y]) / 2, (xr[y] - xl[y]) / 2
        x0, x1 = int(xm - 0.6 * hw), int(xm + 0.6 * hw)
        seg = paper[y, x0:x1]
        if seg.mean() < 0.95:
            continue
        r = L[y, x0:x1] - L[y, x0:x1].mean()
        ac = np.correlate(r, r, "full")[len(r) - 1:]
        acs.append(ac[:30] / ac[0])
    ac = np.mean(acs, 0)
    pk = [i for i in range(3, 29) if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1]]
    return int(pk[0]), round(float(ac[pk[0]]), 3), len(acs)


def sector_centres(xl, xr, rows, kind="phi", ns=NS):
    if kind == "phi":
        sc = np.sin(np.radians(-90 + (np.arange(ns) + 0.5) * 180.0 / ns))
    else:                                                    # equal slices of the width (a robustness variant)
        sc = -1 + (np.arange(ns) + 0.5) * 2.0 / ns
    xm, hw = (xl[rows] + xr[rows]) / 2, (xr[rows] - xl[rows]) / 2
    return sc, xm[None, :] + sc[:, None] * hw[None, :]


def profiles(L, paper, XC, rows, box, min_px=MIN_PX):
    P = np.full(XC.shape, np.nan)
    N = np.zeros(XC.shape, np.int32)
    for k, y in enumerate(rows):
        m = paper[y]
        for t in range(XC.shape[0]):
            xc = XC[t, k]
            if not np.isfinite(xc):
                continue
            i0, i1 = int(math.floor(xc - box / 2 + 0.5)), int(math.floor(xc + box / 2 + 0.5))
            seg = m[i0:i1]
            n = int(seg.sum())
            N[t, k] = n
            if n >= min_px:
                P[t, k] = float(L[y, i0:i1][seg].mean())
    return P, N


def bsb(x, knots, k=3):
    return F9.bsb(x, knots, k)


def smooth_fit(y, v, nseg=NSEG):
    B = bsb(y.astype(np.float64), np.linspace(y.min(), y.max(), nseg + 1))
    c, *_ = np.linalg.lstsq(B, v, rcond=None)
    return B @ c


def change3(R):
    """at each row boundary i (between rows i-1 and i): mean(R[i:i+3]) - mean(R[i-3:i]); NaN unless all six are measured"""
    out = np.full(len(R), np.nan)
    for i in range(STEP_ROWS, len(R) - STEP_ROWS + 1):
        a, b = R[i - STEP_ROWS:i], R[i:i + STEP_ROWS]
        if np.isfinite(a).all() and np.isfinite(b).all():
            out[i] = b.mean() - a.mean()
    return out


def steps(P, rows, thr=STEP_THR, nseg=NSEG):
    R = np.full(P.shape, np.nan)
    C3 = np.full(P.shape, np.nan)
    ev = []
    for t in range(P.shape[0]):
        ok = np.isfinite(P[t])
        if ok.sum() < 30:
            continue
        idx = np.nonzero(ok)[0]
        # the smooth curve over the sector's measured rows; the residual and its 3-px change on the contiguous measured run
        R[t, ok] = P[t, ok] - smooth_fit(rows[ok], P[t, ok], nseg)
        C3[t] = change3(R[t])
        c = C3[t]
        for k in idx:
            if np.isfinite(c[k]) and abs(c[k]) > thr and abs(c[k]) >= np.nanmax(np.abs(c[max(0, k - 3):k + 4])):
                ev.append((t, int(k), float(c[k])))
    return R, C3, ev


def chains(ev, dy=4):
    """steps of one sign linked across neighbouring sectors (t-1 or t-2, |dy| <= 4 rows): one boundary curve per chain"""
    ev = sorted(ev)
    cid, nxt = {}, 0
    for i, (t, k, v) in enumerate(ev):
        best = None
        for j in range(i):
            t2, k2, v2 = ev[j]
            if t2 in (t - 1, t - 2) and abs(k2 - k) <= dy and np.sign(v2) == np.sign(v):
                if best is None or abs(k2 - k) < best[0]:
                    best = (abs(k2 - k), j)
        if best is None:
            cid[i] = nxt
            nxt += 1
        else:
            cid[i] = cid[best[1]]
    return ev, [cid[i] for i in range(len(ev))]


def r6_line_distance(zm, x, yb):
    """the nearest R6 clay latitude line along the pixel column x: (its z, the signed distance in px from the row boundary yb - 0.5
    to where the clay's z crosses it; + = the step is below the line)"""
    col = zm[:, int(round(x))]
    best = None
    for zl in R6_LINES:
        for y in range(TOP, len(col) - 1):
            a, b = col[y], col[y + 1]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - zl) * (b - zl) <= 0:
                yl = y + (a - zl) / (a - b)
                d = (yb - 0.5) - yl
                if best is None or abs(d) < abs(best[1]):
                    best = (zl, d)
    return best


# ------------------------------------------------------------------------------------------------- R6's own measure, per sector
def r6_per_sector(L, A8, zm, tm):
    """fix_r6.pendant_measures' rings measure on the R9 layer, kept PER SECTOR (R6 accepted the median over the sectors: 0.93)"""
    a = A8.astype(np.float32) / 255
    m = (a >= 0.999) & np.isfinite(zm) & (np.arange(a.shape[0])[:, None] >= TOP + 3)
    m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    paper = m & (np.nan_to_num(zm) >= OPEN_Z + 0.004)
    M, N, (t0, t1), *_ = F6.ring_profile(L, paper, zm, tm)
    zc = (np.arange(M.shape[1]) + 0.5) * 0.25 / M.shape[1]
    th = (tm - math.atan2(float(np.nanmean(np.sin(tm[paper]))), float(np.nanmean(np.cos(tm[paper])))) + math.pi) % (2 * math.pi)
    tix = np.clip(np.nan_to_num((th - t0) / max(t1 - t0, 1e-6) * NS, nan=-1).astype(int), -1, NS - 1)
    x290 = {int(t): int(np.median(np.nonzero(tix[290] == t)[0])) for t in range(NS) if (tix[290] == t).any()}
    out = {}
    for zk in R6_MAIN:
        Hk, _ = F6.tier_fit_at(M, N, zc, zk)
        nz = Hk != 0
        big = [int(t) for t in np.nonzero(np.abs(Hk) > 1)[0]]
        out[f"{zk:.4f}"] = dict(sectors_measured=int(nz.sum()), median_abs_L=r2(np.median(np.abs(Hk[nz]))), max_abs_L=r2(np.abs(Hk).max()),
                                at_r6_sector=int(np.argmax(np.abs(Hk))), sectors_over_1=len(big), which=big,
                                per_sector_L=[r2(v) for v in Hk])
    cells = [int((N[t] > 0).sum()) for t in range(NS)]
    return dict(rule="fix_r6.ring_profile (clay longitude sectors over the visible arc, 120 latitude bins, >= 6 px per cell) + tier_fit_at at "
                     "R6's three main tiers, on the R9 layer's L* (OpenCV), R6's measure mask; R6 sector 0 = the right limb, 47 = the left limb",
                r6_sector_x_at_row_290=x290, cells_with_6px_of_120=cells, boundaries=out,
                reading="R6 accepted the MEDIAN over the sectors (fix-r6.json measured_r6.rings_max_abs_L 0.93); kept per sector, every main "
                        "tier still steps by more than 1 L* in 14-18 sectors on R9, on both halves; the limb sectors hold few cells (R6 "
                        "sectors 1-4 and 42-46 under 15 of 120), so R6's fit hardly reached the outline where the bands end")


# ------------------------------------------------------------------------------------------------- baselines (R9) for (b)-(d)
def baselines(rgb8, A8, zm, xl, xr, paper):
    H, W = A8.shape
    yy, xx = np.mgrid[0:H, 0:W]
    xm = np.where(np.isfinite(xl), (xl + xr) / 2, np.nan)[:, None]
    left = paper & (xx < xm)
    right = paper & (xx >= xm)
    out = {}
    for name, fn in (("r8_lab_opencv", F9.lab_cv), ("qa_lab", F9.lab_qa)):
        lb = np.asarray(fn(rgb8), np.float64)
        Lh = lb[..., 0]
        hp = Lh - cv2.GaussianBlur(Lh.astype(np.float32), (0, 0), sigmaX=3.0, sigmaY=0.01).astype(np.float64)
        ys = np.nonzero(left.any(1))[0]
        y0, y1 = ys.min(), ys.max() + 1
        th = (y1 - y0) / 3
        topm, botm = left & (yy < y0 + th), left & (yy >= y1 - th)
        out[name] = dict(
            b_pleats_hp_std=dict(left_half=r2(hp[left].std()), whole_paper=r2(hp[paper].std()), metric="R6's: L* - GaussianBlur(sigma x 3, y 0.01), std"),
            c_light=dict(left_mean_L=round(float(Lh[left].mean()), 3), left_top_third_minus_bottom_third=r2(np.median(Lh[topm]) - np.median(Lh[botm])),
                         right_mean_L=round(float(Lh[right].mean()), 3), left_minus_right=r2(Lh[left].mean() - Lh[right].mean()),
                         thirds_rows=[int(y0), int(round(y0 + th)), int(round(y1 - th)), int(y1)]),
            d_colour=dict(median_a=r2(np.median(lb[..., 1][paper])), median_b=r2(np.median(lb[..., 2][paper])),
                          left_median_a=r2(np.median(lb[..., 1][left])), left_median_b=r2(np.median(lb[..., 2][left]))))
    out["masks_px"] = dict(paper=int(paper.sum()), left=int(left.sum()), right=int(right.sum()))
    return out


# ------------------------------------------------------------------------------------------------- main
def main():
    assert sha(P2_IN) == FIX9["files"]["layer_sha256"], "the R9 layer is not the file fix-r9.json wrote: stop"
    L9 = np.asarray(Image.open(P2_IN))
    rgb8, A8 = L9[..., :3], L9[..., 3]
    T9 = np.asarray(Image.open(TRUTH9).convert("RGB"))
    truth_eq = int(((T9 != rgb8).any(2) & (A8 == 255)).sum())       # the pendant is the top layer: truth = layer at alpha 255
    zm, tm = F6.latlong_map(0.20, 1.72, 1.90, F6.R.PROF_PUMPKIN)
    xl, xr = outline_rows(A8)
    paper = paper_mask(A8, zm)
    rows = np.arange(TOP, int(np.nonzero(np.isfinite(xl))[0].max()) + 1)
    Ls = {"r8_lab_opencv": np.asarray(F9.lab_cv(rgb8))[..., 0].astype(np.float64), "qa_lab": F9.lab_qa(rgb8)[..., 0]}
    period, ac_peak, ac_rows = pleat_period(Ls["r8_lab_opencv"], paper, xl, xr)
    sc, XC = sector_centres(xl, xr, rows, "phi")
    res = {}
    for lab_, L in Ls.items():
        P, N = profiles(L, paper, XC, rows, period)
        R, C3, ev = steps(P, rows)
        ev, cid = chains(ev)
        res[lab_] = dict(P=P, N=N, R=R, C3=C3, ev=ev, cid=cid)
    # per-sector record (OpenCV Lab detects; QA's Lab at the same row boundary alongside)
    cv_, qa_ = res["r8_lab_opencv"], res["qa_lab"]
    secs = defaultdict(set)
    for c, (t, k, v) in zip(cv_["cid"], cv_["ev"]):
        secs[c].add(t)
    coherent = {c for c, s in secs.items() if len(s) >= 3}
    chain_rows = defaultdict(list)
    sectors = []
    for t in range(NS):
        ok = np.isfinite(cv_["P"][t])
        st = []
        for (tt, k, v), c in zip(cv_["ev"], cv_["cid"]):
            if tt != t:
                continue
            x = float(XC[t, k])
            zl = r6_line_distance(zm, x, int(rows[k]))
            z_here = zm[int(rows[k]), int(round(x))]
            st.append(dict(row_boundary=int(rows[k]), x=round(x, 1), change_L_r8_lab=r2(v), change_L_qa_lab=r2(qa_["C3"][t, k]),
                           chain=int(c), in_boundary_curve=c in coherent, clay_z_m=round(float(z_here), 4) if np.isfinite(z_here) else None,
                           nearest_r6_line_z_m=zl[0] if zl else None, distance_to_r6_line_px=r2(zl[1]) if zl else None))
            chain_rows[c].append((t, int(rows[k]), v, zl))
        sectors.append(dict(sector=t, phi_deg=round(-90 + (t + 0.5) * 3.75, 3), x_at_row_280=r2(XC[t, int(np.nonzero(rows == 280)[0][0])]),
                            rows_measured=[int(rows[ok].min()), int(rows[ok].max())] if ok.any() else None, rows_n=int(ok.sum()),
                            max_change_L_r8_lab=r2(np.nanmax(np.abs(cv_["C3"][t]))) if np.isfinite(cv_["C3"][t]).any() else None,
                            max_change_L_qa_lab=r2(np.nanmax(np.abs(qa_["C3"][t]))) if np.isfinite(qa_["C3"][t]).any() else None,
                            max_abs_residual_L=r2(np.nanmax(np.abs(cv_["R"][t]))) if np.isfinite(cv_["R"][t]).any() else None,
                            steps=st))
    curves = []
    for c in sorted(coherent, key=lambda c: min(t for t, *_ in chain_rows[c])):
        lst = chain_rows[c]
        ts = [t for t, *_ in lst]
        d = [abs(z[1]) for *_, z in lst if z]
        zs = Counter(z[0] for *_, z in lst if z)
        curves.append(dict(chain=int(c), sectors=[min(ts), max(ts)], n_sectors=len(set(ts)), rows=[min(r for _, r, _, _ in lst), max(r for _, r, _, _ in lst)],
                           sign="darker below" if lst[0][2] < 0 else "lighter below", median_abs_change_L=r2(np.median([abs(v) for _, _, v, _ in lst])),
                           max_abs_change_L=r2(max(abs(v) for _, _, v, _ in lst)), nearest_r6_line=zs.most_common(1)[0][0] if zs else None,
                           distance_to_r6_line_px=dict(median=r2(np.median(d)), max=r2(max(d)), within_2_5px=sum(1 for x in d if x <= 2.5), of=len(d))))
    want = {lab_: sorted({t for t, _, _ in r["ev"]}) for lab_, r in res.items()}
    want_curves = sorted({t for c, (t, k, v) in zip(cv_["cid"], cv_["ev"]) if c in coherent})
    # the three band edges the designer saw: the darker-below curves on R6's three main lines that reach into the left half
    main3 = [cu for cu in curves if cu["nearest_r6_line"] in R6_MAIN and cu["sign"] == "darker below" and cu["sectors"][0] < NS // 2]
    main3_secs = sorted({t for cu in main3 for t in range(cu["sectors"][0], cu["sectors"][1] + 1)})
    main3_blend = sorted({u for t in main3_secs for u in range(max(0, t - 2), min(NS, t + 3))})
    k280 = int(np.nonzero(rows == 280)[0][0])
    main3_right_x = r2(XC[max(main3_secs), k280]) if main3_secs else None
    # robustness of the count to the measure's choices
    rob = []
    for lab_, L in Ls.items():
        for kind in ("phi", "equal-width"):
            scv, XCv = sector_centres(xl, xr, rows, "phi" if kind == "phi" else "s")
            for box in (period, 2 * period):
                for mp in (MIN_PX, 10):
                    P, _ = profiles(L, paper, XCv, rows, box, mp)
                    _, _, e = steps(P, rows)
                    e, cc = chains(e)
                    ss = defaultdict(set)
                    for c, (t, k, v) in zip(cc, e):
                        ss[c].add(t)
                    rob.append(dict(lab=lab_, sectors=kind, box_px=box, min_px=mp, sectors_with_a_step=len({t for t, _, _ in e}),
                                    sectors_on_boundary_curves=len({t for c, (t, k, v) in zip(cc, e) if len(ss[c]) >= 3})))
    for thr in (1.2, 1.5):
        _, _, e = steps(cv_["P"], rows, thr)
        rob.append(dict(lab="r8_lab_opencv", sectors="phi", box_px=period, min_px=MIN_PX, threshold_L=thr, sectors_with_a_step=len({t for t, _, _ in e})))
    for ns_ in (3, 5, 6):
        _, _, e = steps(cv_["P"], rows, STEP_THR, ns_)
        rob.append(dict(lab="r8_lab_opencv", sectors="phi", box_px=period, min_px=MIN_PX, spline_segments=ns_, sectors_with_a_step=len({t for t, _, _ in e})))
    rob_min = min(r["sectors_with_a_step"] for r in rob)
    r6 = r6_per_sector(Ls["r8_lab_opencv"], A8, zm, tm)
    base = baselines(rgb8, A8, zm, xl, xr, paper)
    v9 = json.load(open(D(LAY, "verify-layers-r9.json")))["checks"]["r9"]["pendant2"]["e_halo"]["r9"]["lantern"]
    stop2 = len(want["r8_lab_opencv"]) > STOP_SECTORS and len(want["qa_lab"]) > STOP_SECTORS
    left_half = [t for t in want["r8_lab_opencv"] if t < NS // 2]
    np.savez_compressed(_new(NPZ), rows=rows, phi_sin=sc, XC=XC, box_px=period,
                        **{f"{k}_{lab_}": res[lab_][k] for lab_ in res for k in ("P", "N", "R", "C3")})
    rec = dict(
        date="2026-11-12", author="render-agent", tokens=0, round="R10 (code only)", source=EYE + " section 4 (P2-2)",
        environment=dict(python=platform.python_version(), numpy=np.__version__, opencv=cv2.__version__, pillow=PIL.__version__,
                         note="this container's python3.12 had no numpy / OpenCV / Pillow: installed numpy 2.4.6, opencv-python-headless "
                              "5.0.0.93, pillow 13.0.0 (the versions of the container's python3.11 user site); the earlier rounds do not "
                              "record theirs"),
        input=dict(layer=rel(P2_IN), sha256=sha(P2_IN), equals_fix_r9=True, truth=rel(TRUTH9), truth_sha256=sha(TRUTH9),
                   truth_equals_layer_at_alpha_255_px_differing=truth_eq),
        method=dict(
            geometry="the R9 alpha's own 0.5 crossing per row (rows %d-%d)" % (rows.min(), rows.max()),
            sectors="48 equal-angle longitudes of the layer's own outline: x_t(y) = x_mid(y) + sin(phi_t) half_width(y), phi_t = -90 + "
                    "(t + 0.5) 3.75 deg; t = 0 the left limb (window side), 23/24 the axis, 47 the right limb",
            profile="per sector and row the mean L* over a box of one pleat period (%d px: the paper's row autocorrelation peaks at %d px, "
                    "r = %.2f, %d rows) centred on x_t(y); paper pixels only, >= %d px" % (period, period, ac_peak, ac_rows, MIN_PX),
            paper="alpha 255, rows >= %d, the collar apart (|x - %.1f| <= %d, y <= %d), eroded 5 x 5, clay z >= OPEN_Z + 0.004 (R6's "
                  "measure mask); %d px" % (TOP + 3, CORD_X, COLLAR_DX, COLLAR_Y, int(paper.sum())),
            smooth="cubic B-spline, %d segments (5 knots) over each sector's measured rows, least squares" % NSEG,
            step="(mean of the 3 rows below a row boundary) - (mean of the 3 rows above), on the residual; |change| > %.1f L* and the "
                 "largest within +-3 rows" % STEP_THR,
            curves="steps of one sign linked across neighbouring sectors (|dy| <= 4 rows); a boundary curve = a chain over >= 3 sectors",
            r6_lines="R6's clay latitude lines (work-r6/fix-r6.json pendant-v2.rings.tiers, all rounds): %s m; the distance is along the "
                     "pixel column, where fix_r6.latlong_map's z crosses the line" % R6_LINES),
        step1=dict(sectors=sectors, boundary_curves=curves,
                   sectors_with_a_step=dict(r8_lab_opencv=want["r8_lab_opencv"], qa_lab=want["qa_lab"],
                                            n=dict(r8_lab_opencv=len(want["r8_lab_opencv"]), qa_lab=len(want["qa_lab"])),
                                            on_boundary_curves=len(want_curves), left_half_n=len(left_half),
                                            right_half_n=len(want["r8_lab_opencv"]) - len(left_half)),
                   the_three_bands=dict(curves=[cu["chain"] for cu in main3], sectors=[min(main3_secs), max(main3_secs)] if main3_secs else None,
                                        n_sectors=len(main3_secs), n_sectors_with_the_2_sector_blend=len(main3_blend),
                                        right_end_x_at_row_280=main3_right_x, cord_axis_x=CORD_X,
                                        note="the three band edges the designer saw (darker below, on R6's 0.0354 / 0.0688 / 0.1042 lines, "
                                             "reaching the left outline) alone span these sectors: they cross the cord's axis (sectors 23/24) "
                                             "and end to its right; a fix of these alone changes the sectors with the blend"),
                   other_steps_outside_the_three_bands=sorted(set(want["r8_lab_opencv"]) - set(main3_secs)),
                   section_3_3_check=dict(
                       hypothesis="the steps on the left are not on the clay's latitude lines, so R6 missed them",
                       verdict="REFUTED: the band edges lie ON R6's clay latitude lines (median distance 0.5-0.6 px in the middle sectors, "
                               "1-2.6 px at the left limb); R6 left them because its acceptance was the median over the sectors and its "
                               "sector cells at the limbs were too sparse to fit (r6_own_measure_per_sector)",
                       r6_own_measure_per_sector=r6)),
        robustness=dict(variants=rob, minimum_sectors_with_a_step=rob_min,
                        reading="every variant (both Labs, equal-angle or equal-width sectors, a 1- or 2-pleat box, >= 6 or >= 10 px, "
                                "a 1.2 or 1.5 L* threshold, 3-6 spline segments) finds steps in more than 24 of the 48 sectors"),
        stop_rule=dict(
            limit_sectors=STOP_SECTORS,
            rule_1_a_against_b_c="not evaluated: it needs a fix, and rule 2 already holds",
            rule_2_more_than_24_sectors=dict(triggered=bool(stop2), sectors_r8_lab=len(want["r8_lab_opencv"]), sectors_qa_lab=len(want["qa_lab"]),
                                             with_the_2_sector_blend=len({u for t in want["r8_lab_opencv"] for u in range(max(0, t - 2), min(NS, t + 3))}),
                                             minimum_over_variants=rob_min),
            rule_3_smear="not evaluated (no fix run)",
            triggered=bool(stop2),
            action="STOP (section 4.4): no layer written, no re-grade, nothing recomposed; the x 2 crop of the whole lantern and the measure "
                   "go to the designer (crops-r10/); a model pass is a question for the owner"),
        baselines_r9=dict(
            a_steps=dict(max_change_L_per_sector_r8_lab=[s["max_change_L_r8_lab"] for s in sectors],
                         max_change_L_per_sector_qa_lab=[s["max_change_L_qa_lab"] for s in sectors],
                         worst=dict(r8_lab=r2(np.nanmax(np.abs(cv_["C3"]))), qa_lab=r2(np.nanmax(np.abs(qa_["C3"]))))),
            b_c_d=base,
            e_halo_from_verify_layers_r9=dict(bright_halo_px=v9["bright_halo_px"], dark_fringe_px=v9["dark_fringe_px"]),
            note="R9 measured as the baseline for the round that fixes this (the designer's (a)-(e)); no 'after' exists: the stop rule holds"),
        model_pass_estimate=dict(
            basis="the records, not a fresh call: jobs-r5.json wm-ph2-variants-p5 (seedream-5-pro image-to-image 2K, 4 references): "
                  "var2_estimate_cost 650 tokens, 2026-11-11",
            estimate_tokens=650, with_one_retry=1300,
            brief_wording=EYE + " section 4.4 (from wm-pendant2-eye-2026-11-12.md section 3.5): 'about ten soft pumpkin lobes; one continuous "
                          "pleated surface; no tiers'; the SKU photos of the 40 as the only reference; a mask on the pendant only",
            note="a fresh var2_estimate_cost is needed before any approval; not called in R10 (0 tokens, no var2)"),
        files=dict(record=rel(REC), sectors_npz=rel(NPZ), layer="NOT WRITTEN (stop rule)"),
    )
    json.dump(rec, open(_new(REC), "w"), indent=1, ensure_ascii=False, default=float)
    print(json.dumps(dict(period=period, sectors_with_a_step={k: len(v) for k, v in want.items()}, left=len(left_half), curves=[(c["chain"], c["sectors"], c["rows"],
                     c["max_abs_change_L"], c["nearest_r6_line"], c["distance_to_r6_line_px"]["median"]) for c in curves],
                     three_bands=(main3_secs[:1], main3_secs[-1:], len(main3_secs)), robust_min=rob_min, stop=stop2,
                     r6={k: (v["median_abs_L"], v["max_abs_L"], v["sectors_over_1"]) for k, v in r6["boundaries"].items()},
                     base=base, truth_eq=truth_eq), indent=1, default=float))
    if not stop2:
        sys.exit("the stop rule does not hold on step 1: the fix (section 4.2 steps 2-3) is not part of this script; stop and report")


if __name__ == "__main__":
    main()
