#!/usr/bin/env python3
"""
fix_r9.py: R9, 0-token code fixes on two existing warm-modern tool layers (render-agent, 2026-11-12). Code only: 0 tokens, no var2, no
network. NEW FILES ONLY: every R8 file is read, never written. Both fixes work on the GRADED (cut) layer, after the one v3c grade: there is
no re-grade, no shadow file changes, and the frozen shadow recipe does not run.

  pendant2  P2-1 (docs/proposals/wm-pendant2-eye-2026-11-12.md section 4), pendant-cj-pleated-pumpkin-lantern-40: ALPHA ONLY.
            (1) The lantern's 50 % outline (the cord and the canopy apart: rows >= 198, the collar |x - 1676.5| <= 9, y <= 203 kept as it
                is) in polar form about the lantern's centre. The bottom outline is exempt (the designer: real lobes can show there): from
                where the outline turns more horizontal than vertical (tangent < 45 deg) on the lower half, it keeps its own points.
            (2) The fit, per side: u = 1/r on a cubic B-spline (knots every ~25 deg), least squares in r, the outline CONVEX by construction
                (u + u'' >= 0 is linear in u), the stop rule's own limits as bounds on every outline point (the old outline at most 2.9 px
                outside the fit, at most 1.9 px inside it; inactive here: the least-squares fit is inside them). The RIGHT side is fitted
                from the collar to the bottom arc (the step and the facet; its top arc is within the limits). On the LEFT, one convex line
                over the whole side would need 2.25 px of fill at a tier step on the top-left arc (x ~1615, y ~216): over the designer's 2,
                and a fit held to 2 px there flattens the shoulder into a new facet. So, per the stop rule, only the left FLANK is fitted
                (from the bottom arc to where the top-left arc starts, tangent 45 deg: the ledge), and the top-left arc keeps its line; the
                x 2 crop goes to the designer. Blends: the old outline points moved radially toward the fit over 6 deg (12 at the collar).
            (3) The new alpha: the signed distance to the new outline through a Gaussian edge (erf), its width set so that the 10-90 %
                ramp on the flanks equals the reference: the default pendant (pendant-cj-tiered-fabric-drum-r4.png) against the wall,
                because the R6 points that were not snapped are re-rasterised placeholder geometry (their ramp is R6's 1-px ramp too).
                The 50 % line is the fit (sides) and the old line (bottom).
            (4) Colour: RGB at alpha 255 is not touched. Where the alpha rises, the added part takes the layer's own bleed colour (cut()'s
                normalised blur of the premultiplied colour, sigma 4 / 12: checked equal to the bleed already stored under alpha 0), the
                old part keeps its colour (premultiplied sum). Where the alpha falls, the straight colour stays. Nothing is painted.
            (5) Stop rule: if the fit needs a cut over 3 px or a fill over 2 px anywhere on the sides, nothing is written.
  curtain3  QA R8 F1, curtains-cj-japanese-linen-half-shade (Linen): the pixels the designer's literal speck rule still flags on the graded
            layer at alpha > 0 (h 150-230 deg, C* > 6; in R8's OpenCV Lab and in QA's numpy Lab: the same 11, all in the room-side soft edge,
            alpha 3-13). R8's own method (fix_r8.neutralise): a*, b* -> the median of the pixels within radius 3 that are neither flagged
            nor transparent; L* kept; the 8-bit value among the 27 nearest that keeps L* closest and passes the rule in both Labs. Nothing
            else changes (checked).
  records   QA R8 F2: (1) R8's final speck pass (44 px; fix-r8.json curtain3.specks.final_pass) was not in the saved mask: it is rebuilt by
            re-running fix_r8.curtain3() in memory (every write redirected to a temporary folder, checked byte-identical to work-r8/) and
            saved NEXT TO the speck mask as work-r8/curtain3-speck-mask-final-pass.npy (a new file; no R8 file is edited); (2) the
            "alpha_unchanged" wording of fix-r8.json, corrected in this record (true for the ungraded sources only).

Writes: layers/pendant/pendant-cj-pleated-pumpkin-lantern-40-r9.png, layers/curtains/curtains-cj-japanese-linen-half-shade-r9.png,
work-r9/fix-r9.json, work-r9/pendant2-outline-r9.npy (the new 50 % line, canvas px), work-r9/curtain3-soft-edge-mask-r9.npy (the 11 px),
work-r8/curtain3-speck-mask-final-pass.npy.        python3.12 -I fix_r9.py pendant2 | curtain3 | records | all
Then: recompose_r9.py; layers/verify_layers_r9.py; make_crops_r9.py; recompose_r9.py entries.
"""
import hashlib
import itertools
import json
import math
import os
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join
LAY, WR8, WR9 = D(HERE, "layers"), D(HERE, "work-r8"), D(HERE, "work-r9")
REC = D(WR9, "fix-r9.json")
REPO = os.path.abspath(D(HERE, *[".."] * 5))
MAN8 = json.load(open(D(LAY, "manifest-r8.json")))
V8 = {v["id"]: v for vs in MAN8["variants"].values() for v in vs}
B8 = {l_["id"]: l_ for l_ in MAN8["layers"]}
P2_IN = D(LAY, V8["pendant-v2"]["file"])
P2_OUT = D(LAY, "pendant", "pendant-cj-pleated-pumpkin-lantern-40-r9.png")
C3_IN = D(LAY, V8["curtains-v3"]["file"])
C3_OUT = D(LAY, "curtains", "curtains-cj-japanese-linen-half-shade-r9.png")
DEFAULT_PENDANT = D(LAY, B8["pendant"]["file"])


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


def record(key, val):
    os.makedirs(WR9, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-12", author="render-agent", tokens=0, round="R9 (code only)",
        sources=dict(pendant2="docs/proposals/wm-pendant2-eye-2026-11-12.md section 4 (P2-1)",
                     curtain3_and_records="qa/reports/2026-11-12-wm-phase2-r8.md section 8 (F1, F2, F8)"),
        note="both fixes on the graded (cut) layers, after the one v3c grade: no re-grade, no shadow file changes; the variants' truths "
             "are recomposed over the graded scene under them (recompose_r9.py), not graded")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def rhu(x):
    return np.floor(x + 0.5)


# ================================================================================================= the pendant: geometry helpers
TOP = 198                      # the lantern's top row (work-r5/post-r5.json pendant-v2.lantern_top_row)
BOX = (1530, 185, 1820, 375)   # the lantern with a margin (x0, y0, x1, y1)
CORD_X = 1676.5                # the cord's column (fix-r6.json pendant-v2.cord.column_px 1676.05; 3 px wide)
COLLAR_DX, COLLAR_Y = 9, 203   # the collar kept as it is: |x - CORD_X| <= 9 and y <= 203, faded over 4 px
SPACING = 25.0                 # B-spline knots every 25 deg (the least-squares fit is convex at 25 and 30, not at 15 and 20)
CUT_MAX, FILL_MAX = 2.9, 1.9   # the designer's stop limits 3 / 2, with a 0.1 px margin
STOP_CUT, STOP_FILL = 3.0, 2.0
EPS_CONV = 0.0005              # u + u'' >= 0.0005 px^-1: a radius of curvature under 2,000 px everywhere on the sides
BLEND_BOTTOM, BLEND_TOP = 6.0, 12.0
SS = 8


def outline_pts(a, box=BOX, S=SS):
    """the alpha's 0.5 outline (marching squares on a x S bilinear upsample), canvas pixel-centre coordinates, in outline order"""
    x0, y0, x1, y1 = box
    up = cv2.resize(a[y0:y1, x0:x1].astype(np.float32), ((x1 - x0) * S, (y1 - y0) * S), interpolation=cv2.INTER_LINEAR)
    cs, _ = cv2.findContours((up > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float64) / S + 0.5 / S - 0.5
    c[:, 0] += x0
    c[:, 1] += y0
    return c


def normals(c, k):
    tx = np.roll(c[:, 0], -k) - np.roll(c[:, 0], k)
    ty = np.roll(c[:, 1], -k) - np.roll(c[:, 1], k)
    n = np.stack([ty, -tx], 1)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def outward(a, c, n):
    p1, p0 = c + 1.5 * n, c - 1.5 * n
    v1 = cv2.remap(a.astype(np.float32), p1[:, 0:1].astype(np.float32), p1[:, 1:2].astype(np.float32), cv2.INTER_LINEAR).ravel()
    v0 = cv2.remap(a.astype(np.float32), p0[:, 0:1].astype(np.float32), p0[:, 1:2].astype(np.float32), cv2.INTER_LINEAR).ravel()
    n = n.copy()
    n[v1 > v0] *= -1
    return n


def polar(c, cx, cy, step=0.25):
    th = np.degrees(np.arctan2(c[:, 1] - cy, c[:, 0] - cx))
    r = np.hypot(c[:, 0] - cx, c[:, 1] - cy)
    edges = np.arange(-180, 180 + 1e-9, step)
    idx = np.clip(np.digitize(th, edges) - 1, 0, len(edges) - 2)
    tb, rb, spread = [], [], 0.0
    for i in range(len(edges) - 1):
        s = idx == i
        if s.any():
            tb.append(edges[i] + step / 2)
            rb.append(float(np.median(r[s])))
            spread = max(spread, float(r[s].max() - r[s].min()))
    return np.array(tb), np.array(rb), spread


def smooth_circ(v, n):
    return np.convolve(np.concatenate([v] * 3), np.ones(n) / n, "same")[len(v):2 * len(v)]


def bsb(x, knots, k=3):
    """clamped cubic B-spline basis at x"""
    t = np.concatenate([[knots[0]] * k, knots, [knots[-1]] * k])
    n = len(t) - k - 1
    B = np.zeros((len(x), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = ((x >= t[i]) & (x < t[i + 1])).astype(float)
    B[x >= knots[-1], len(knots) + k - 2] = 1.0
    for d in range(1, k + 1):
        Bn = np.zeros((len(x), len(t) - 1 - d))
        for i in range(len(t) - 1 - d):
            a1 = (x - t[i]) / (t[i + d] - t[i]) if t[i + d] > t[i] else 0 * x
            a2 = (t[i + d + 1] - x) / (t[i + d + 1] - t[i + 1]) if t[i + d + 1] > t[i + 1] else 0 * x
            Bn[:, i] = a1 * B[:, i] + a2 * B[:, i + 1]
        B = Bn
    return B[:, :n]


def hildreth(Q, q, A, b, sweeps=3000, tol=1e-12):
    """min 1/2 c'Qc + q'c subject to A c <= b (Hildreth's dual coordinate ascent; Q positive definite)"""
    Qi = np.linalg.inv(Q)
    c = -Qi @ q
    d = np.einsum("ij,ij->i", A @ Qi, A)
    lam = np.zeros(len(b))
    for _ in range(sweeps):
        moved = 0.0
        for i in np.nonzero(((A @ c - b) > 0) | (lam > 0))[0]:
            new = max(0.0, lam[i] + (A[i] @ c - b[i]) / d[i])
            dl = new - lam[i]
            if dl != 0.0:
                c -= Qi @ A[i] * dl
                lam[i] = new
                moved = max(moved, abs(dl))
        if moved < tol:
            break
    return c, lam


def u_eval(tq, kn, c):
    return bsb(np.clip(tq, kn[0], kn[-1]), kn) @ c


def curvature_u(tq, kn, c, h=0.05):
    u = u_eval(tq, kn, c)
    upp = (u_eval(tq + h, kn, c) - 2 * u + u_eval(tq - h, kn, c)) / math.radians(h) ** 2
    up = (u_eval(tq + h, kn, c) - u_eval(tq - h, kn, c)) / (2 * math.radians(h))
    return u ** 3 * (u + upp) / (u ** 2 + up ** 2) ** 1.5


def sstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def ramp_widths(a, pts, nrm, lo=0.1, hi=0.9, span=5.0, step=0.05):
    """the 10-90 % width of the alpha along each outward normal (bilinear samples, 0.05 px)"""
    ss = np.arange(-span, span + 1e-9, step)
    px = (pts[:, 0:1] + ss[None, :] * nrm[:, 0:1]).astype(np.float32)
    py = (pts[:, 1:2] + ss[None, :] * nrm[:, 1:2]).astype(np.float32)
    prof = cv2.remap(a.astype(np.float32), px, py, cv2.INTER_LINEAR)
    out = []
    for p in prof:
        j = int(np.argmin(np.abs(p - 0.5)))
        k, i = j, j
        while k < len(p) - 1 and p[k] > lo:
            k += 1
        while i > 0 and p[i] < hi:
            i -= 1
        if p[k] > lo or p[i] < hi:
            out.append(np.nan)
            continue
        out.append((ss[k - 1] + (p[k - 1] - lo) / (p[k - 1] - p[k] + 1e-12) * step) - (ss[i] + (p[i] - hi) / (p[i] - p[i + 1] + 1e-12) * step))
    return np.array(out)


def flank_ramps(A8, cx, top=TOP):
    """the ramp on the flanks (outward normal within 45 deg of horizontal, the collar apart) and on the top / bottom, per side"""
    aa = A8.astype(np.float64) / 255.0
    a2 = aa.copy()
    a2[:top - 3] = 0
    c = outline_pts(a2)
    n = outward(a2, c, normals(c, 12))
    ang = np.degrees(np.arctan2(np.abs(n[:, 1]), np.abs(n[:, 0])))
    coll = (np.abs(c[:, 0] - CORD_X) <= COLLAR_DX + 4) & (c[:, 1] <= COLLAR_Y + 4)
    fl = (ang < 45) & ~coll
    w = ramp_widths(aa, c, n)
    return dict(left=round(float(np.nanmedian(w[fl & (c[:, 0] < cx)])), 3), right=round(float(np.nanmedian(w[fl & (c[:, 0] > cx)])), 3),
                top_bottom=round(float(np.nanmedian(w[~fl & ~coll])), 3), px=dict(left=int((fl & (c[:, 0] < cx)).sum()), right=int((fl & (c[:, 0] > cx)).sum())))


def default_pendant_ramp():
    """the reference: the default pendant's outline against the wall (the drum, rows >= its first row wider than 40 px below row 100; the
    cord above it apart): the median 10-90 % width on its flanks (outward normal within 45 deg of horizontal) and on the whole outline"""
    a = np.asarray(Image.open(DEFAULT_PENDANT))[..., 3].astype(np.float64) / 255
    rows = np.nonzero((a > 0.5).sum(1) > 40)[0]
    top = int(rows[rows >= 100].min())
    ld = a.copy()
    ld[:top] = 0
    ys, xs = np.nonzero(ld > 0.5)
    box = (int(xs.min()) - 20, top - 10, int(xs.max()) + 20, int(ys.max()) + 20)
    c = outline_pts(ld, box=box)
    n = outward(ld, c, normals(c, 12))
    w = ramp_widths(ld, c, n)
    ang = np.degrees(np.arctan2(np.abs(n[:, 1]), np.abs(n[:, 0])))
    side = (ang < 45) & (c[:, 1] > top + 3)
    return dict(file=rel(DEFAULT_PENDANT), drum_top_row=top, flanks=round(float(np.nanmedian(w[side])), 3), whole_outline=round(float(np.nanmedian(w)), 3),
                flanks_p25_p75=[round(float(np.nanpercentile(w[side], 25)), 3), round(float(np.nanpercentile(w[side], 75)), 3)],
                top_bottom=round(float(np.nanmedian(w[~side])), 3), points=int(len(c)))


def r6_unsnapped_ramp(L6a):
    """the designer's first choice of reference: the ramp at the R6 outline points contour_snap did NOT snap (fix_r6.contour_snap's own
    selection, reproduced on its inputs: work-r5/p5-regt.npy and the R5 layer's alpha)"""
    regt = np.load(D(HERE, "work-r5", "p5-regt.npy")).astype(np.float32)
    a5 = np.asarray(Image.open(D(HERE, "work-r5", "layers", "pendant-v2.png"))).astype(np.float32)[..., 3] / 255
    a_lan = a5.copy()
    a_lan[:TOP] = 0
    Lst = cv2.cvtColor(np.clip(regt, 0, 1), cv2.COLOR_RGB2LAB)[..., 0]
    H, W = a5.shape
    up = cv2.resize(a_lan, (W * 4, H * 4), interpolation=cv2.INTER_LINEAR)
    cs, _ = cv2.findContours((up > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = (max(cs, key=len)[:, 0, :].astype(np.float64) / 4.0 + 0.5 / 4 - 0.5)[::2]
    nrm = outward(a_lan, c, normals(c, 7))
    ss = np.arange(-4.0, 4.0 + 1e-6, 0.25)
    used = np.zeros(len(c), bool)
    Lb = cv2.GaussianBlur(Lst.astype(np.float32), (0, 0), 0.7)
    for i in range(len(c)):
        if c[i, 1] < TOP + 2:
            continue
        px = (c[i, 0] + ss * nrm[i, 0]).astype(np.float32).reshape(1, -1)
        py = (c[i, 1] + ss * nrm[i, 1]).astype(np.float32).reshape(1, -1)
        g = np.abs(np.gradient(cv2.remap(Lb, px, py, cv2.INTER_LINEAR).ravel(), 0.25))
        used[i] = g.max() >= 2.5
    lan6 = L6a.copy()
    lan6[:TOP] = 0
    co = outline_pts(lan6)
    no = outward(lan6, co, normals(co, 12))
    j = np.argmin((co[:, None, 0] - c[None, :, 0]) ** 2 + (co[:, None, 1] - c[None, :, 1]) ** 2, 1)
    keep = co[:, 1] >= TOP + 4
    w = ramp_widths(lan6, co, no)
    return dict(r6_points=int(len(c)), r6_snapped=int(used.sum()), record_says="1174 / 837 (work-r6/fix-r6.json pendant-v2.outline)",
                ramp_unsnapped=round(float(np.nanmedian(w[keep & ~used[j]])), 3), ramp_snapped=round(float(np.nanmedian(w[keep & used[j]])), 3),
                reading="the unsnapped points carry the same re-rasterised 1-px ramp as the snapped ones (contour_snap re-rasterises the whole "
                        "outline at 8 x): they are the placeholder's (clay) geometry, so the designer's fallback applies: the default pendant")


def chord_turns(c, step=4.0):
    """the outline resampled at equal 4 px arc steps; the signed turn at each vertex (deg)"""
    seg = np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    cc = np.vstack([c, c[:1]])
    P = np.stack([np.interp(t, s, cc[:, 0]), np.interp(t, s, cc[:, 1])], 1)
    v = np.diff(np.vstack([P, P[:1]]), axis=0)
    ang = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    turn = (np.roll(ang, -1) - ang + 180) % 360 - 180
    mid = np.roll(P, -1, axis=0)
    return mid, turn


def refine_line(a, c, k=12, span=2.0, step=0.01):
    """each outline point moved to the alpha's exact 0.5 crossing along its normal (bilinear samples every 0.01 px): the marching-squares
    points sit on a 1/8-px grid, which alone turns 4-px chords by +-1-2 deg"""
    n = outward(a, c, normals(c, k))
    ss = np.arange(-span, span + 1e-9, step)
    px = (c[:, 0:1] + ss[None, :] * n[:, 0:1]).astype(np.float32)
    py = (c[:, 1:2] + ss[None, :] * n[:, 1:2]).astype(np.float32)
    pr = cv2.remap(a.astype(np.float32), px, py, cv2.INTER_LINEAR)
    out = c.copy()
    for i, p in enumerate(pr):
        j = np.nonzero((p[:-1] >= 0.5) & (p[1:] < 0.5))[0]
        if len(j):
            j = j[np.argmin(np.abs(ss[j]))]
            out[i] = c[i] + (ss[j] + (p[j] - 0.5) / (p[j] - p[j + 1] + 1e-12) * step) * n[i]
    return out


def pendant_geometry(A8, cx, cy, poly, thR, thL, thTL):
    """on the alpha's refined 0.5 line: (a) the line against the fit on what was fitted (the right side, the left flank), and its turns at
    4-px chords (one sign; turns under 0.1 deg are straight, not counted); the same on the kept top-left arc, for the record; (b) the right
    edge: no 4-px chord turns more than 2 x the mean of its two neighbours; (d) the widest row"""
    a = A8.astype(np.float64) / 255
    lan = a.copy()
    lan[:TOP] = 0
    c = refine_line(lan, outline_pts(lan)[::4])
    th = np.degrees(np.arctan2(c[:, 1] - cy, c[:, 0] - cx))
    tu = np.where(th < 0, th + 360, th)
    coll = (np.abs(c[:, 0] - CORD_X) <= COLLAR_DX + 6) & (c[:, 1] <= COLLAR_Y + 6)
    sideR = (th >= -84) & (th <= thR) & ~coll
    sideL = (tu >= thL) & (tu <= thTL)
    out = {}
    if poly is not None:
        P = poly.reshape(-1, 1, 2).astype(np.float32)
        dev = np.array([cv2.pointPolygonTest(P, (float(x), float(y)), True) for x, y in c])
        out["line_vs_fit_px"] = dict(right_side_max_abs=round(float(np.abs(dev[sideR]).max()), 3), left_flank_max_abs=round(float(np.abs(dev[sideL]).max()), 3),
                                     rule="<= 1 px where fitted")
    mid, turn = chord_turns(c)
    mth = np.degrees(np.arctan2(mid[:, 1] - cy, mid[:, 0] - cx))
    mtu = np.where(mth < 0, mth + 360, mth)
    mcoll = (np.abs(mid[:, 0] - CORD_X) <= COLLAR_DX + 8) & (mid[:, 1] <= COLLAR_Y + 8)
    mR = (mth >= -84) & (mth <= thR) & ~mcoll
    mL = (mtu >= thL) & (mtu <= thTL)
    mT = (mtu > thTL + BLEND_BOTTOM) & (mtu <= 264) & ~mcoll
    sgn = np.sign(np.median(turn))
    opp = (np.sign(turn) == -sgn) & (np.abs(turn) >= 0.1)
    out["turns_4px"] = dict(right_side_opposite=int(opp[mR].sum()), right_side_n=int(mR.sum()), left_flank_opposite=int(opp[mL].sum()),
                            left_flank_n=int(mL.sum()), top_left_arc_opposite=int(opp[mT].sum()), top_left_arc_n=int(mT.sum()),
                            rule="one sign where fitted (convex); |turn| < 0.1 deg counts as straight; the top-left arc is kept (stop rule)")
    nb = (np.abs(np.roll(turn, 1)) + np.abs(np.roll(turn, -1))) / 2
    ratio = np.abs(turn) / np.maximum(nb, 1e-6)
    edge = (mth >= -45) & (mth <= thR)
    worst = int(np.argmax(np.where(edge, ratio, 0)))
    out["right_edge_corner"] = dict(max_turn_over_neighbours=round(float(ratio[edge].max()), 3), at=[round(float(v), 1) for v in mid[worst]],
                                    turn_deg=round(float(turn[worst]), 2), chords_over_2x=int((ratio[edge] > 2).sum()), chords=int(edge.sum()),
                                    rule="no 4-px chord turns more than 2 x the mean of its two neighbours (theta -45 deg .. the bottom arc)")
    widths = []
    for y in range(TOP + 2, 360):
        r_ = lan[y]
        idx = np.nonzero(r_ >= 0.5)[0]
        if len(idx) < 20:
            continue
        i, j = idx.min(), idx.max()
        widths.append(((j + (r_[j] - 0.5) / (r_[j] - r_[j + 1])) - (i - 1 + (0.5 - r_[i - 1]) / (r_[i] - r_[i - 1])), y))
    wmax = max(widths)
    out["widest_row"] = dict(width_px=round(float(wmax[0]), 3), row=int(wmax[1]))
    return out


def pendant2():
    L6 = np.asarray(Image.open(P2_IN))
    H, W = L6.shape[:2]
    A0 = L6[..., 3].astype(np.int32)
    a = A0 / 255.0
    lan = a.copy()
    lan[:TOP] = 0
    c_old = outline_pts(lan)
    ys, xs = np.nonzero(lan > 0.5)
    cx, cy = float(xs.mean()), float(ys.mean())
    tb, rb, spread = polar(c_old, cx, cy)
    rs = smooth_circ(rb, 41)
    X, Y = cx + rs * np.cos(np.radians(tb)), cy + rs * np.sin(np.radians(tb))
    tg = np.degrees(np.arctan2(np.abs(np.roll(Y, -8) - np.roll(Y, 8)), np.abs(np.roll(X, -8) - np.roll(X, 8))))
    low = (tb > 0) & (tb < 180) & (tg < 45)
    thR, thL = float(tb[low].min()), float(tb[low].max())            # the bottom arc (exempt), theta thR .. thL
    upp = (tb < 0) & (tg < 45)
    thTL = float(tb[upp].min()) + 360                                   # the left flank's top end (the top-left arc starts there)
    cosp = rs / np.sqrt(rs ** 2 + np.gradient(rs, np.radians(tb)) ** 2)
    th_c = np.degrees(np.arctan2(c_old[:, 1] - cy, c_old[:, 0] - cx))
    tu_c = np.where(th_c < 0, th_c + 360, th_c)
    r_c = np.hypot(c_old[:, 0] - cx, c_old[:, 1] - cy)
    coll = (np.abs(c_old[:, 0] - CORD_X) <= COLLAR_DX) & (c_old[:, 1] <= COLLAR_Y)
    sideR = (th_c >= -90) & (th_c <= thR) & ~coll                      # the right side: from the collar to the bottom arc
    sideL = (tu_c >= thL) & (tu_c <= thTL)                              # the left flank: from the bottom arc to the top-left arc
    topL = (tu_c > thTL) & (tu_c <= 270) & ~coll                        # the top-left arc: the stop rule's item (kept)
    bottom = (th_c > thR) & (tu_c < thL)
    cosp_c = np.interp(th_c, np.concatenate([tb - 360, tb, tb + 360]), np.concatenate([cosp] * 3))
    allow = {"cut": np.full(len(c_old), CUT_MAX), "fill": np.full(len(c_old), FILL_MAX)}
    fits = {}
    DOM = {"right": (-90.0 - BLEND_TOP / 2, thR + BLEND_BOTTOM), "left": (thL - BLEND_BOTTOM, thTL + BLEND_BOTTOM),
           "left_whole": (thL - BLEND_BOTTOM, 270.0 + BLEND_TOP / 2)}
    PTS = {"right": (sideR, th_c), "left": (sideL, tu_c), "left_whole": (sideL | topL, tu_c)}

    def side_data(side):
        dom = DOM[side]
        tt = tb if side == "right" else np.where(tb < 0, tb + 360, tb)
        s = (tt >= dom[0]) & (tt <= dom[1])
        o = np.argsort(tt[s])
        return dom, tt[s][o], rb[s][o]

    def do_fit(side, bounds=True):
        dom, t, r = side_data(side)
        pm, tcoord = PTS[side]
        kn = np.linspace(dom[0], dom[1], max(2, int(round((dom[1] - dom[0]) / SPACING)) + 1))
        B = bsb(t, kn)
        w = r ** 4
        Q = B.T @ (B * w[:, None]) + 1e-12 * np.eye(B.shape[1])
        q = -B.T @ (w / r)
        tc = np.linspace(dom[0], dom[1], 600)
        h = 0.05
        Bc = bsb(tc, kn)
        Bpp = (bsb(np.clip(tc + h, *dom), kn) - 2 * Bc + bsb(np.clip(tc - h, *dom), kn)) / math.radians(h) ** 2
        inner = (tc > dom[0] + h) & (tc < dom[1] - h)
        A_ = [-(Bc + Bpp)[inner]]
        b_ = [-np.full(inner.sum(), EPS_CONV)]
        nb = 0
        if bounds:
            Bb = bsb(tcoord[pm], kn)
            A_ += [Bb, -Bb]
            b_ += [1.0 / (r_c[pm] - allow["cut"][pm] / cosp_c[pm]), -1.0 / (r_c[pm] + allow["fill"][pm] / cosp_c[pm])]
            nb = int(pm.sum())
        A, b = np.vstack(A_), np.concatenate(b_)
        cf, lam = hildreth(Q, q, A, b)
        nc = int(inner.sum())
        act = dict(convexity=int((lam[:nc] > 0).sum()), cut_bound=int((lam[nc:nc + nb] > 0).sum()), fill_bound=int((lam[nc + nb:] > 0).sum()),
                   max_violation=float(max(0.0, (A @ cf - b).max())))
        fits[side] = dict(kn=kn, c=cf, dom=dom, act=act)

    def r_fit(side, th):
        f = fits[side]
        return 1.0 / u_eval(th, f["kn"], f["c"])

    def ordered(mask, key):
        """the old outline points of mask, in outline order, oriented so that key increases (the run must be contiguous)"""
        idx = np.nonzero(mask)[0]
        if not len(idx):
            return idx
        n = len(c_old)
        gaps = np.diff(np.concatenate([idx, idx[:1] + n]))
        start = (int(np.argmax(gaps)) + 1) % len(idx)
        run = np.roll(idx, -start)
        assert (np.diff(run) % n == 1).all(), "a kept run is not contiguous along the outline"
        if key[run[0]] > key[run[-1]]:
            run = run[::-1]
        return run

    def moved(run, key, side, w):
        """old points moved radially toward the fit by weight w (0 = kept, 1 = on the fit)"""
        tt, rr = key[run], r_c[run]
        r2 = (1 - w) * rr + w * r_fit(side, tt)
        ang = np.radians(th_c[run])
        return np.stack([cx + r2 * np.cos(ang), cy + r2 * np.sin(ang)], 1)

    def samples(side, t0, t1):
        tt = np.arange(t0, t1, 0.05)
        rr = r_fit(side, tt)
        return np.stack([cx + rr * np.cos(np.radians(tt)), cy + rr * np.sin(np.radians(tt))], 1)

    def polygon(left="left"):
        """theta order: the top blend into the right fit, the right fit, its bottom blend, the kept bottom, the left blend, the left fit, its
        top blend, the kept top-left arc (left="left_whole": the left fit runs to the collar instead, for the stop-rule diagnosis)"""
        t0 = -90 - BLEND_TOP / 2
        parts = []
        r_ = ordered((th_c >= t0) & (th_c < t0 + BLEND_TOP), th_c)
        if left == "left_whole":
            parts.append(np.stack([cx + ((1 - (w := sstep((th_c[r_] - t0) / BLEND_TOP))) * r_fit("left_whole", tu_c[r_]) + w * r_fit("right", th_c[r_]))
                                   * np.cos(np.radians(th_c[r_])), cy + ((1 - w) * r_fit("left_whole", tu_c[r_]) + w * r_fit("right", th_c[r_]))
                                   * np.sin(np.radians(th_c[r_]))], 1))
        else:
            parts.append(moved(r_, th_c, "right", sstep((th_c[r_] - t0) / BLEND_TOP)))
        parts.append(samples("right", t0 + BLEND_TOP, thR))
        r_ = ordered((th_c >= thR) & (th_c < thR + BLEND_BOTTOM), th_c)
        parts.append(moved(r_, th_c, "right", sstep((thR + BLEND_BOTTOM - th_c[r_]) / BLEND_BOTTOM)))
        parts.append(c_old[ordered((th_c >= thR + BLEND_BOTTOM) & (tu_c < thL - BLEND_BOTTOM), th_c)])
        r_ = ordered((tu_c >= thL - BLEND_BOTTOM) & (tu_c < thL), tu_c)
        parts.append(moved(r_, tu_c, left, sstep((tu_c[r_] - thL + BLEND_BOTTOM) / BLEND_BOTTOM)))
        if left == "left_whole":
            parts.append(samples("left_whole", thL, 360 + t0))
        else:
            parts.append(samples("left", thL, thTL))
            r_ = ordered((tu_c >= thTL) & (tu_c < thTL + BLEND_BOTTOM), tu_c)
            parts.append(moved(r_, tu_c, "left", sstep((thTL + BLEND_BOTTOM - tu_c[r_]) / BLEND_BOTTOM)))
            parts.append(c_old[ordered((tu_c >= thTL + BLEND_BOTTOM) & (tu_c < 360 + t0), tu_c)])
        poly = np.concatenate([p_ for p_ in parts if len(p_)], 0)
        assert np.isfinite(poly).all()
        assert np.hypot(*np.diff(np.vstack([poly, poly[:1]]), axis=0).T).max() < 0.6, "the new outline has a gap"
        return poly

    def deviation(poly):
        P = poly.reshape(-1, 1, 2).astype(np.float32)
        return np.array([cv2.pointPolygonTest(P, (float(x), float(y)), True) for x, y in c_old])   # + : the old point inside = a fill

    # the stop rule's diagnosis on the whole left side (the top-left arc included), least squares + convex, no bounds
    do_fit("right", bounds=False)
    do_fit("left_whole", bounds=False)
    dev_w = deviation(polygon("left_whole"))
    iw = int(np.argmax(np.where(topL | sideL, dev_w, -1e9)))
    whole_left = dict(cut=round(float(-dev_w[sideL | topL].min()), 3), fill=round(float(dev_w[sideL | topL].max()), 3),
                      fill_at=[round(float(c_old[iw, 0]), 1), round(float(c_old[iw, 1]), 1)], on_the_top_left_arc=bool(topL[iw]),
                      top_left_arc_fill=round(float(dev_w[topL].max()), 3), left_flank_fill=round(float(dev_w[sideL].max()), 3))
    # the least-squares need on what is fitted (convexity only, no bounds)
    do_fit("right", bounds=False)
    do_fit("left", bounds=False)
    dev_ls = deviation(polygon())
    ls_act = {k: v["act"] for k, v in fits.items() if k in ("right", "left")}
    iters = []
    for it in range(8):
        do_fit("right")
        do_fit("left")
        poly = polygon()
        dev = deviation(poly)
        sd = sideR | sideL
        iters.append(dict(fill_max=round(float(dev[sd].max()), 3), cut_max=round(float(-dev[sd].min()), 3),
                          act={k: v["act"] for k, v in fits.items() if k in ("right", "left")}))
        over_f = np.where(sd & (dev > FILL_MAX), dev - FILL_MAX, 0.0)
        over_c = np.where(sd & (-dev > CUT_MAX), -dev - CUT_MAX, 0.0)
        if not over_f.any() and not over_c.any():
            break
        for arr_, key in ((over_f, "fill"), (over_c, "cut")):
            for i in np.nonzero(arr_)[0]:
                j = np.arange(i - 6, i + 7) % len(c_old)
                allow[key][j] = np.minimum(allow[key][j], allow[key][i] - arr_[i] - 0.02)
    kept = ~(sideR | sideL) & ~((th_c >= -96) & (th_c < -84)) & ~((th_c > thR) & (th_c < thR + BLEND_BOTTOM)) \
        & ~((tu_c > thL - BLEND_BOTTOM) & (tu_c < thL)) & ~((tu_c > thTL) & (tu_c < thTL + BLEND_BOTTOM))
    need = dict(right_side=dict(cut=round(float(-dev[sideR].min()), 3), fill=round(float(dev[sideR].max()), 3)),
                left_flank=dict(cut=round(float(-dev[sideL].min()), 3), fill=round(float(dev[sideL].max()), 3)),
                kept_arcs_max_abs=round(float(np.abs(dev[kept]).max()), 4))
    stop = any(v["cut"] > STOP_CUT or v["fill"] > STOP_FILL for k, v in need.items() if k in ("right_side", "left_flank"))
    conv = {}
    for side, lo_, hi_ in (("right", -90, thR), ("left", thL, thTL)):
        f = fits[side]
        tq = np.linspace(f["dom"][0], f["dom"][1], 3000)
        insd = (tq >= lo_) & (tq <= hi_)
        k = curvature_u(tq, f["kn"], f["c"])
        conv[side] = dict(convex=bool((k[insd] > 0).all()), curvature_min=round(float(k[insd].min()), 5),
                          radius_of_curvature_max_px=round(float(1 / k[insd].min()), 1), knots_deg=[round(float(v), 3) for v in f["kn"]])
    where = {}
    for nm, m_, sgn in (("left_fill", sideL, 1), ("left_cut", sideL, -1), ("right_fill", sideR, 1), ("right_cut", sideR, -1)):
        i = int(np.argmax(sgn * np.where(m_, dev, -sgn * 1e9)))
        where[nm] = [round(float(c_old[i, 0]), 1), round(float(c_old[i, 1]), 1)]
    ledge = {}
    for y in (290, 300, 305, 310, 313, 316, 320, 324, 327):
        j = int(np.argmin(np.abs(c_old[:, 1] - y) + 1000 * (c_old[:, 0] > cx)))
        ledge[str(y)] = dict(x_old=round(float(c_old[j, 0]), 2), moved_px=round(float(-dev[j]), 2))

    def row_at(t):
        return round(float(cy + np.interp(t, np.concatenate([tb - 360, tb, tb + 360]), np.concatenate([rb] * 3)) * math.sin(math.radians(t))), 1)
    geo = dict(centre_px=[round(cx, 3), round(cy, 3)], polar_bin_spread_max_px=round(spread, 3),
               bottom_arc=dict(theta_deg=[thR, thL], rows_from=dict(right=row_at(thR), left=row_at(thL)),
                               rule="the lower half from where the outline's tangent is under 45 deg from horizontal: exempt, keeps its own points"),
               right_side=dict(theta_deg=[-90, thR], note="from the collar to the bottom arc (its top arc included: within the limits)"),
               left_flank=dict(theta_deg=[thL, thTL], rows=[row_at(thTL), row_at(thL)],
                               note="from the bottom arc to where the top-left arc starts (tangent under 45 deg); holds the ledge"),
               top_left_arc=dict(theta_deg=[thTL, 270], note="KEPT: the stop rule (see stop_rule.top_left_arc)"),
               collar=dict(kept=f"|x - {CORD_X}| <= {COLLAR_DX}, y <= {COLLAR_Y}", fade_px=4),
               blends=dict(bottom_deg=BLEND_BOTTOM, top_left_deg=BLEND_BOTTOM, top_centre_deg=BLEND_TOP,
                           how="the old outline points moved radially toward the fit (smoothstep): seamless at both ends"))
    rec = dict(what="P2-1: the ledge low on the left, the step and the facet on the right, on one convex fit per side; the ramp widened to the "
                    "reference everywhere on the lantern; alpha only (+ the bleed colour where the alpha rises)",
               source=dict(layer=rel(P2_IN), sha256=sha(P2_IN)), geometry=geo,
               fit=dict(model="u = 1/r on a clamped cubic B-spline in theta, knots every ~%g deg; least squares in r (weights r^4); convex by "
                              "construction (u + u'' >= %g); the stop limits less 0.1 px as bounds on every old outline point (inactive if the "
                              "least-squares fit is inside them)" % (SPACING, EPS_CONV), convexity=conv, iterations=iters,
                        least_squares_need=dict(right_side=dict(cut=round(float(-dev_ls[sideR].min()), 3), fill=round(float(dev_ls[sideR].max()), 3)),
                                                left_flank=dict(cut=round(float(-dev_ls[sideL].min()), 3), fill=round(float(dev_ls[sideL].max()), 3)),
                                                active=ls_act)),
               stop_rule=dict(limits=dict(cut=STOP_CUT, fill=STOP_FILL), applied=need, where=where, triggered_on_what_was_changed=bool(stop),
                              top_left_arc=dict(whole_left_side_least_squares=whole_left, triggered=bool(whole_left["fill"] > STOP_FILL),
                                                decision="NOT CHANGED (only its ramp): one convex line over the whole left side needs %.2f px of fill at "
                                                         "(%.1f, %.1f), a tier step the model drew on the top-left arc; a fit held to 2 px there "
                                                         "flattens the shoulder (a new facet). Per the stop rule: left as it is, the x 2 crop to the "
                                                         "designer (crops-r9/pendant-2-top-left-stop-x2.png)" % (whole_left["fill"], *whole_left["fill_at"])),
                              ledge_rows_left=ledge))
    if stop:
        rec["result"] = "STOPPED: nothing written"
        record("pendant2", rec)
        raise SystemExit(json.dumps(rec["stop_rule"], indent=1))
    # the new alpha
    x0, y0, x1, y1 = BOX
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [np.round(poly).astype(np.int32).reshape(-1, 1, 2)], True, 1)
    near = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))) > 0
    near[:y0], near[y1:], near[:, :x0], near[:, x1:] = False, False, False, False
    Pp = poly.reshape(-1, 1, 2).astype(np.float32)
    Dd = np.zeros((H, W))
    for y, x in zip(*np.nonzero(near)):
        Dd[y, x] = cv2.pointPolygonTest(Pp, (float(x), float(y)), True)
    inside = np.zeros((H, W), np.uint8)
    cv2.fillPoly(inside, [np.round(poly * 16).astype(np.int32).reshape(-1, 1, 2)], 1, shift=4)
    yy, xx = np.mgrid[0:H, 0:W]
    Z = (np.abs(xx - CORD_X) <= COLLAR_DX) & (yy <= COLLAR_Y)
    wcol = sstep(cv2.distanceTransform((~Z).astype(np.uint8), cv2.DIST_L2, 5) / 4.0)
    chg = near & (wcol > 0)
    beyond = (~near) & (yy >= TOP) & ~Z & (A0 != np.where(inside.astype(bool), 255, 0))
    assert not beyond.any(), "the old alpha differs from 0 / 255 outside the band"
    erf = np.vectorize(math.erf)

    def build(sigma):
        al = np.zeros((H, W))
        al[near] = 0.5 * (1 + erf(Dd[near] / (sigma * math.sqrt(2))))
        return np.clip(rhu(np.where(chg, wcol * al + (1 - wcol) * a, a) * 255), 0, 255).astype(np.int32)
    ref = default_pendant_ramp()
    target = ref["flanks"]
    lo, hi, hist = 0.4, 2.0, []
    for _ in range(14):
        sg = (lo + hi) / 2
        fr = flank_ramps(build(sg), cx)
        hist.append((round(sg, 4), fr["left"], fr["right"]))
        if (fr["left"] + fr["right"]) / 2 < target:
            lo = sg
        else:
            hi = sg
    sigma = (lo + hi) / 2
    A1 = build(sigma)
    # colour: the bleed (cut()'s formula on the old layer) for the part the alpha adds; RGB at alpha 255 untouched
    L0 = L6[..., :3].astype(np.float64)
    pm = (L0 * a[..., None]).astype(np.float32)
    n4, d4 = cv2.GaussianBlur(pm, (0, 0), 4.0), cv2.GaussianBlur(a.astype(np.float32), (0, 0), 4.0)
    n12, d12 = cv2.GaussianBlur(pm, (0, 0), 12.0), cv2.GaussianBlur(a.astype(np.float32), (0, 0), 12.0)
    bl = np.where((d4 > 0.01)[..., None], n4 / np.maximum(d4, 1e-12)[..., None], n12 / np.maximum(d12, 1e-12)[..., None])
    z0 = (A0 == 0) & (cv2.dilate((A0 > 0).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    bleed_same = int(((np.clip(rhu(bl), 0, 255) == L0).all(2) & z0).sum())
    up_ = A1 > A0
    L1 = L0.copy()
    L1[up_] = (L0[up_] * A0[up_, None] + bl[up_] * (A1[up_] - A0[up_])[:, None]) / A1[up_, None]
    L1 = np.clip(rhu(L1), 0, 255)
    out = np.dstack([L1.astype(np.uint8), A1.astype(np.uint8)])
    rgb_ch = (L1 != L0).any(2)
    a_ch = A1 != A0
    checks = dict(alpha_px_changed=int(a_ch.sum()), raised=int(up_.sum()), lowered=int((A1 < A0).sum()), rgb_px_changed=int(rgb_ch.sum()),
                  rgb_changed_where_alpha_did_not_rise=int((rgb_ch & ~up_).sum()), rgb_changed_at_alpha_255_both=int((rgb_ch & (A0 == 255) & (A1 == 255)).sum()),
                  changed_outside_box=int(((a_ch | rgb_ch) & ~np.pad(np.ones((y1 - y0, x1 - x0), bool), ((y0, H - y1), (x0, W - x1)))).sum()),
                  collar_zone_changed=int(((a_ch | rgb_ch) & Z).sum()),
                  bleed_formula_equals_stored_bleed=dict(px=bleed_same, of=int(z0.sum())),
                  cord_and_canopy_rows_below_190_changed=int(((a_ch | rgb_ch)[:190]).sum()))
    assert checks["rgb_changed_where_alpha_did_not_rise"] == 0 and checks["rgb_changed_at_alpha_255_both"] == 0 and checks["changed_outside_box"] == 0
    assert checks["collar_zone_changed"] == 0 and checks["cord_and_canopy_rows_below_190_changed"] == 0
    ramp = dict(reference=ref, r6_unsnapped=r6_unsnapped_ramp(a), target_flanks=target, sigma_px=round(sigma, 4), bisection=hist,
                before=flank_ramps(A0, cx), after=flank_ramps(A1, cx),
                profile="alpha = Phi(d / sigma) of the signed distance d to the new outline (erf), point-sampled at the pixel centres",
                measure="median 10-90 % width along the outward normal (bilinear, 0.05 px) on the flanks (normal within 45 deg of horizontal)")
    newc = refine_line(np.where(np.arange(H)[:, None] >= TOP, A1 / 255.0, 0.0), outline_pts(np.where(np.arange(H)[:, None] >= TOP, A1 / 255.0, 0.0)))
    bth = np.degrees(np.arctan2(newc[:, 1] - cy, newc[:, 0] - cx))
    btu = np.where(bth < 0, bth + 360, bth)
    line50 = {}
    for nm, selN, selO in (("bottom_arc", (bth > thR + BLEND_BOTTOM + 1) & (btu < thL - BLEND_BOTTOM - 1), (th_c > thR + BLEND_BOTTOM) & (tu_c < thL - BLEND_BOTTOM)),
                           ("top_left_arc", (btu > thTL + BLEND_BOTTOM + 1) & (btu < 264) & ~((np.abs(newc[:, 0] - CORD_X) <= COLLAR_DX + 6) & (newc[:, 1] <= COLLAR_Y + 6)),
                            (tu_c > thTL + BLEND_BOTTOM) & (tu_c < 264))):
        ob = c_old[selO]
        dd = np.array([np.min(np.hypot(ob[:, 0] - x, ob[:, 1] - y)) for x, y in newc[selN]])
        line50[nm] = dict(moved_px_median=round(float(np.median(dd)), 3), moved_px_max=round(float(dd.max()), 3), points=int(selN.sum()))
    line50["rule"] = "on the kept arcs the ramp widening keeps the 50 % line (+-0.3 px); old line = the R8 file's marching-squares points"
    geom_after = pendant_geometry(A1, cx, cy, poly, thR, thL, thTL)
    geom_before = pendant_geometry(A0, cx, cy, None, thR, thL, thTL)
    p = _new(P2_OUT)
    Image.fromarray(out, "RGBA").save(p, compress_level=9)
    po = _new(D(WR9, "pendant2-outline-r9.npy"))
    np.save(po, poly)
    rec.update(result="written", files=dict(layer=rel(p), layer_sha256=sha(p), outline=rel(po), outline_sha256=sha(po)),
               alpha_and_colour=checks, ramp=ramp, line_50pct=line50, geometry_after=geom_after, geometry_before=geom_before,
               width_change_px=round(geom_after["widest_row"]["width_px"] - geom_before["widest_row"]["width_px"], 3),
               shadow="unchanged: " + V8["pendant-v2"]["shadow"] + " (empty; the frozen recipe does not run)",
               not_touched="the canopy, the cord, the collar, the paper's RGB at alpha 255 (pleats, opening): byte-equal")
    record("pendant2", rec)
    print(json.dumps(dict(stop=rec["stop_rule"], ramp=dict(ref=target, sigma=sigma, before=ramp["before"], after=ramp["after"]),
                          geometry=geom_after, width_change=rec["width_change_px"], checks=checks), indent=1, default=float))


# ================================================================================================= curtain 3: the soft edge
def lab_cv(rgb8):
    return cv2.cvtColor(np.asarray(rgb8).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WP = np.array([0.95047, 1.0, 1.08883])


def lab_qa(c8):
    """QA's numpy Lab (qa/reports/2026-11-12-wm-phase2-r8/tools/r8_curtains.py lab(), copied)"""
    c = np.asarray(c8, np.float64) / 255
    li = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = li @ _M.T / _WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def speck_rules(lb, a8):
    """the designer's literal rule (h 150-230, C* > 6) and R8's wide rule (h 100-230, C* > 6, a* - median7 a* <= -8), alpha > 0"""
    A_, B_ = lb[..., 1], lb[..., 2]
    C = np.hypot(A_, B_)
    h = np.degrees(np.arctan2(B_, A_)) % 360
    on = a8 > 0
    lit = on & (h >= 150) & (h <= 230) & (C > 6)
    med = cv2.medianBlur(np.clip(np.round(A_ + 128), 0, 255).astype(np.uint8), 7).astype(np.float32) - 128
    wide = on & (h >= 100) & (h <= 230) & (C > 6) & (A_ - med <= -8)
    return lit, wide


def literal_one(q):
    h = math.degrees(math.atan2(q[2], q[1])) % 360
    return 150 <= h <= 230 and math.hypot(q[1], q[2]) > 6


def counts(rgb, a8):
    lc, wc = speck_rules(lab_cv(rgb), a8)
    lq, wq = speck_rules(lab_qa(rgb), a8)
    vis = a8 >= 128
    return dict(literal_alpha_gt0=dict(r8_lab=int(lc.sum()), qa_lab=int(lq.sum())),
                wide_visible_alpha_ge128=dict(r8_lab=int((wc & vis).sum()), qa_lab=int((wq & vis).sum())),
                wide_soft_edge_alpha_lt128=dict(r8_lab=int((wc & ~vis).sum()), qa_lab=int((wq & ~vis).sum()))), lc | lq


def curtain3():
    C8 = np.asarray(Image.open(C3_IN))
    rgb, a8 = C8[..., :3], C8[..., 3]
    before, m = counts(rgb, a8)
    lb = lab_cv(rgb)
    ok = (a8 > 0) & ~m
    yy, xx = np.mgrid[-3:4, -3:4]
    disk = (yy ** 2 + xx ** 2) <= 9
    H, W = m.shape
    new = rgb.copy()
    px = []
    for y, x in zip(*np.nonzero(m)):
        y0, y1, x0, x1 = max(0, y - 3), min(H, y + 4), max(0, x - 3), min(W, x + 4)
        dk = disk[y0 - y + 3:y1 - y + 3, x0 - x + 3:x1 - x + 3] & ok[y0:y1, x0:x1]
        assert dk.sum() >= 5, (x, y)
        L_, am, bm = lb[y, x, 0], float(np.median(lb[y0:y1, x0:x1, 1][dk])), float(np.median(lb[y0:y1, x0:x1, 2][dk]))
        tgt = cv2.cvtColor(np.array([[[L_, am, bm]]], np.float32), cv2.COLOR_LAB2RGB)[0, 0] * 255
        base = np.clip(rhu(tgt), 0, 255)
        best = None
        for d in itertools.product((-1, 0, 1), repeat=3):
            cnd = np.clip(base + np.array(d), 0, 255).astype(np.uint8)
            l1, l2 = lab_cv(cnd[None, None])[0, 0], lab_qa(cnd[None, None])[0, 0]
            if literal_one(l1) or literal_one(l2):
                continue
            score = abs(float(l1[0]) - float(L_)) + 0.1 * math.hypot(float(l1[1]) - am, float(l1[2]) - bm)
            if best is None or score < best[0]:
                best = (score, cnd, l1)
        new[y, x] = best[1]
        px.append(dict(x=int(x), y=int(y), alpha=int(a8[y, x]), neighbours=int(dk.sum()), lab_before=[round(float(v), 2) for v in lb[y, x]],
                       median_ab=[round(am, 2), round(bm, 2)], lab_after=[round(float(v), 2) for v in best[2]], dL=round(float(best[2][0] - L_), 3),
                       rgb_before=[int(v) for v in rgb[y, x]], rgb_after=[int(v) for v in best[1]]))
    after, _ = counts(new, a8)
    ch = (new != rgb).any(2)
    lc0, wc0 = speck_rules(lb, a8)
    _, wc1 = speck_rules(lab_cv(new), a8)
    rec = dict(what="QA R8 F1: the 11 soft-edge pixels the designer's literal rule still flagged on the graded layer (alpha 3-13, x 248-261)",
               source=dict(layer=rel(C3_IN), sha256=sha(C3_IN)),
               method="fix_r8.neutralise on the graded layer: a*, b* -> the median of the radius-3 pixels that are neither flagged nor transparent "
                      "(R8's OpenCV Lab); L* kept; the 8-bit value among the 27 nearest that keeps L* closest and passes the literal rule in both Labs",
               flagged=dict(r8_lab=int(lc0.sum()), qa_lab=int(before["literal_alpha_gt0"]["qa_lab"]), union=int(m.sum()),
                            same_set_in_both_labs=bool(before["literal_alpha_gt0"]["r8_lab"] == before["literal_alpha_gt0"]["qa_lab"] == int(m.sum()))),
               before=before, after=after, pixels=px,
               dL_max_abs=round(max(abs(p_["dL"]) for p_ in px), 3), px_changed=int(ch.sum()), px_changed_outside_flagged=int((ch & ~m).sum()),
               new_wide_rule_px=int((wc1 & ~wc0).sum()),
               alpha="unchanged (same bytes)", shadow="unchanged: " + V8["curtains-v3"]["shadow"],
               wide_rule_soft_edge_note="the wide rule (R8's own detector, a neighbourhood rule) still flags %d soft-edge pixels (alpha < 128, h 100-150: "
                                        "yellow-green, not in the designer's window); the brief limits this fix to the literal pixels, so they are left; "
                                        "0 at alpha >= 128 in R8's Lab, as in R8" % after["wide_soft_edge_alpha_lt128"]["r8_lab"])
    assert rec["px_changed_outside_flagged"] == 0 and after["literal_alpha_gt0"]["r8_lab"] == 0 and after["literal_alpha_gt0"]["qa_lab"] == 0
    assert rec["new_wide_rule_px"] == 0
    p = _new(C3_OUT)
    Image.fromarray(np.dstack([new, a8]), "RGBA").save(p, compress_level=9)
    pm_ = _new(D(WR9, "curtain3-soft-edge-mask-r9.npy"))
    np.save(pm_, m)
    rec["files"] = dict(layer=rel(p), layer_sha256=sha(p), mask=rel(pm_), mask_sha256=sha(pm_))
    record("curtain3", rec)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("pixels",)}, indent=1, default=float))


# ================================================================================================= F2: R8's records
def r8_final_pass():
    """re-run fix_r8.curtain3() in memory: every write goes to a temporary folder, the mask of its last neutralise() call is the final
    pass; the run must reproduce work-r8/'s curtain-3 layer, shadow and speck mask byte for byte"""
    sys.dont_write_bytecode = True
    sys.path.insert(0, HERE)
    sys.path.insert(0, D(HERE, "step0"))
    import fix_r8 as F8
    cap = dict(masks=[], rec={})
    with tempfile.TemporaryDirectory() as tmp:
        F8._new = lambda p: D(tmp, os.path.relpath(p, F8.WR8).replace(os.sep, "__"))
        F8.record = lambda k, v: cap["rec"].__setitem__(k, v)
        neu = F8.neutralise

        def spy(rgb01, a8, m):
            cap["masks"].append(m.copy())
            return neu(rgb01, a8, m)
        F8.neutralise = spy
        F8.curtain3()
        same = {}
        for a_, b_ in (("layers__curtains-v3.png", "layers/curtains-v3.png"), ("shadows__curtains-v3.png", "shadows/curtains-v3.png")):
            same[b_] = sha(D(tmp, a_)) == sha(D(WR8, b_))
        same["curtain3-speck-mask.npy"] = bool(np.array_equal(np.load(D(tmp, "curtain3-speck-mask.npy")), np.load(D(WR8, "curtain3-speck-mask.npy"))))
    assert all(same.values()), same
    return cap["masks"], cap["rec"]["curtain3"], same


def records():
    masks, rec8_new, same = r8_final_pass()
    fin = masks[-1]
    speck = np.load(D(WR8, "curtain3-speck-mask.npy"))
    rec8 = json.load(open(D(WR8, "fix-r8.json")))
    assert int(fin.sum()) == rec8["curtain3"]["specks"]["final_pass"]["px"]
    p = _new(D(WR8, "curtain3-speck-mask-final-pass.npy"))
    np.save(p, fin)
    # the "alpha_unchanged" wording: the graded alpha R7 -> R8 of the three curtains
    m7 = json.load(open(D(LAY, "manifest-r7.json")))
    f7 = {l_["id"]: l_["file"] for l_ in m7["layers"] if "file" in l_}
    f8 = {l_["id"]: l_["file"] for l_ in MAN8["layers"] if "file" in l_}
    for vs in m7["variants"].values():
        for v in vs:
            f7[v["id"]] = v["file"]
    for vs in MAN8["variants"].values():
        for v in vs:
            f8[v["id"]] = v["file"]
    graded = {}
    for key, src in (("curtains", "curtains"), ("curtains-v2", "curtains-v2"), ("curtains-v3", "curtains-v3")):
        a7 = np.asarray(Image.open(D(LAY, f7[key])))[..., 3].astype(int)
        a8 = np.asarray(Image.open(D(LAY, f8[key])))[..., 3].astype(int)
        s7 = np.asarray(Image.open(D(HERE, "work-r7", "layers", f"{src}.png")))[..., 3]
        s8 = np.asarray(Image.open(D(WR8, "layers", f"{src}.png")))[..., 3]
        fa7 = np.asarray(Image.open(D(HERE, "work-r7", "layers", f"{src}-free-alpha.png")))
        fa8 = np.asarray(Image.open(D(WR8, "layers", f"{src}-free-alpha.png")))
        d = a7 != a8
        soft = (s8 > 0) & (s8 < 255)
        graded[key] = dict(ungraded_alpha_and_free_alpha_same_bytes=bool(np.array_equal(s7, s8) and np.array_equal(fa7, fa8)),
                           graded_alpha_px_changed=int(d.sum()), graded_alpha_max_diff=int(np.abs(a7 - a8).max()),
                           changed_where_source_not_soft=int((d & ~soft).sum()), r7=f7[key], r8=f8[key])
    corr = dict(
        final_pass_mask=dict(file=rel(p), sha256=sha(p), px=int(fin.sum()), overlap_with_speck_mask=int((fin & speck).sum()),
                             speck_mask=rel(D(WR8, "curtain3-speck-mask.npy")), speck_mask_px=int(speck.sum()),
                             union_px=int((fin | speck).sum()),
                             how="fix_r8.curtain3() re-run in memory (writes to a temporary folder); its third and last neutralise() mask; the run "
                                 "reproduced work-r8's curtain-3 layer and shadow byte for byte and the speck mask exactly: " + json.dumps(same),
                             naming="fix-r8.json names this pass 'final_pass' (44 px); its 'pass_2' (4 px) is the second speck pass, already in "
                                    "the speck mask (pass_1 849 + pass_2 4 = 853)",
                             all_r8_changes="the speck mask (853) + this mask (44) = every pixel whose a*b* R8's speck steps changed (897)"),
        alpha_unchanged=dict(
            r8_said={"curtains_bench.curtains.alpha_unchanged": True, "curtains_bench.curtains-v2.alpha_unchanged": True,
                     "curtain3.alpha_unchanged": True, "manifest-r8 curtains-v3.r8.alpha": "unchanged (layer alpha and free alpha: the R7 sources)"},
            correct="TRUE for the UNGRADED sources only (work-r8/layers/<name>.png alpha and <name>-free-alpha.png are the R7 bytes). FALSE for "
                    "the graded layers in layers/: cut() raises a soft-edge alpha where the scene under it changed (soft_edge_alpha_raised), so "
                    "the graded alpha moved on %d / %d / %d soft-edge pixels (180502 / 554205 / Linen), max %d / %d / %d levels, and on 0 pixels "
                    "where the source is not soft" % tuple([graded[k]["graded_alpha_px_changed"] for k in ("curtains", "curtains-v2", "curtains-v3")] +
                                                           [graded[k]["graded_alpha_max_diff"] for k in ("curtains", "curtains-v2", "curtains-v3")]),
            per_curtain=graded, r8_files="not edited (this record carries the correction)"))
    record("r8_record_corrections", corr)
    print(json.dumps(corr, indent=1, default=float))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("pendant2", "all"):
        pendant2()
    if what in ("curtain3", "all"):
        curtain3()
    if what in ("records", "all"):
        records()
