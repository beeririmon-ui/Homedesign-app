#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): pendant 2, P2-1 (docs/proposals/wm-pendant2-eye-2026-11-12.md section 4), measured by QA's own code.
From render-agent only file names and, for comparison, its polar centre and theta zones (fix-r9.json). Everything else is QA's.

The 50 % line: rays from an interior point every 0.1 deg; alpha (/255) sampled bilinearly (cv2.remap, pixel centres at integer
coordinates) every 0.05 px; the first crossing of 0.5 from inside, linearly interpolated. (R9 uses marching squares; this is a different
extractor on purpose.) The collar and the cord (|x - 1676.5| <= 12, y < 206) are left out.
Zones, QA's own (by the outline's normal): flank = normal within 45 deg of horizontal (left / right by the normal's side); top arcs and
the bottom arc = the rest, split by the normal's vertical sign; the top arcs split left / right at the lantern's centre column.
R9's own theta zones about its centre are reported next to them (right_side -90..20.375, left_flank 154.875..199.375, top-left
199.375..270, the bottom arc between).
  1. The ramp: per outline point, alpha along the outward normal (-6..+6 px, 0.05 px, bilinear), the 10 % and 90 % crossings nearest
     the 50 % point; the median on the flanks per side (P2-1 (c): within +-0.5 px of the reference). The reference: the same measure on the
     default pendant (pendant-cj-tiered-fabric-drum-r4.png) below its drum top; and on the R8 lantern, its whole distribution (is there any
     part of R8's outline with a natural ramp the designer's first-choice reference could have used?).
  2. The turns: the outline resampled every 4 px of arc length (4 phases: 0, 1, 2, 3 px); the signed turn at each joint; opposite-sign
     turns (|turn| >= 0.1 deg) per zone; on the right edge (theta -45 deg .. the bottom arc), each turn against the mean of its two
     neighbours (denominator floored at 0.1 deg): max ratio, where (P2-1 (b): no ratio over 2).
  3. The line against a fit (P2-1 (a)): (i) against R9's own stored line (work-r9/pendant2-outline-r9.npy), the distance from each QA
     point to that polyline; (ii) the depth under the convex hull of the whole outline (the fill a fill-only convex line would need) per
     zone, max and where; (iii) the local bump: r(theta) minus its Gaussian smoothing (sigma 5 deg), max per zone.
  4. The line R8 -> R9: delta r per zone (median, max) - on the kept arcs the line must not move (+-0.3 px).
  5. The width (P2-1 (d)): per row the 50 % crossings along the row (linear between pixel centres); the widest row, R8 and R9; in cm by
     the R5 scale (41 cm for the lantern's width).
  6. Alpha only: RGB at alpha 255 (both) unchanged; RGB changed only where alpha rose; for those pixels the colour implied for the added
     coverage, (a9 rgb9 - a8 rgb8) / (a9 - a8), against the layer's own bleed (R8's stored RGB at the nearest alpha-0 pixels, <= 2.5 px);
     the cord, canopy and collar rows; the shadow file.
Writes data/pendant.json.     ~/.venvs/motion/bin/python3.12 -I r9_pendant.py
"""
import hashlib
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LD = os.path.join(P2, "layers")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
F8 = os.path.join(LD, "pendant/pendant-cj-pleated-pumpkin-lantern-40-r6.png")
F9 = os.path.join(LD, "pendant/pendant-cj-pleated-pumpkin-lantern-40-r9.png")
FD = os.path.join(LD, "pendant/pendant-cj-tiered-fabric-drum-r4.png")
R9C = (1674.587, 277.612)                       # R9's polar centre, used only to place its theta zones
COLLAR_X, COLLAR_HALF, COLLAR_Y = 1676.5, 12, 206


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rgba(p):
    return np.asarray(Image.open(p)).astype(np.float32)


L8, L9, LDf = rgba(F8), rgba(F9), rgba(FD)
A8, A9, AD = L8[..., 3] / 255, L9[..., 3] / 255, LDf[..., 3] / 255


def body_top(A, min_span=60, start=150):
    for y in range(start, A.shape[0]):
        xs = np.nonzero(A[y] >= 0.5)[0]
        if len(xs) and xs.max() - xs.min() > min_span:
            return y
    return None


def centre_of(A, top):
    m = A >= 0.5
    m[:top] = False
    ys, xs = np.nonzero(m)
    return (float(xs.min() + xs.max()) / 2, float(ys.min() + ys.max()) / 2), [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def outline(A, C, r0=30.0, r1=200.0, step=0.05, dth=0.1):
    th = np.deg2rad(np.arange(-180, 180, dth))
    rs = np.arange(r0, r1, step, dtype=np.float64)
    X = (C[0] + np.cos(th)[:, None] * rs[None, :]).astype(np.float32)
    Y = (C[1] + np.sin(th)[:, None] * rs[None, :]).astype(np.float32)
    S = cv2.remap(A, X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    below = S < 0.5
    i = below.argmax(1)
    ok = below.any(1) & (i > 0)
    i = np.maximum(i, 1)
    s0, s1 = S[np.arange(len(th)), i - 1], S[np.arange(len(th)), i]
    r = rs[i - 1] + (s0 - 0.5) / np.maximum(s0 - s1, 1e-6) * step
    P = np.stack([C[0] + np.cos(th) * r, C[1] + np.sin(th) * r], 1)
    return np.rad2deg(th), r, P, ok


def normals(P, C, k=10):
    T = np.roll(P, -k, 0) - np.roll(P, k, 0)
    n = np.stack([T[:, 1], -T[:, 0]], 1)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    flip = ((P - np.array(C)) * n).sum(1) < 0
    n[flip] *= -1
    return n


def ramp(A, P, n, half=6.0, step=0.05):
    t = np.arange(-half, half + 1e-9, step)
    X = (P[:, 0, None] + n[:, 0, None] * t[None, :]).astype(np.float32)
    Y = (P[:, 1, None] + n[:, 1, None] * t[None, :]).astype(np.float32)
    S = cv2.remap(A, X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    c = len(t) // 2
    w = np.full(len(P), np.nan)
    for j in range(len(P)):
        s = S[j]
        ii = np.nonzero(s[:c + 1] >= 0.9)[0]           # inward: the last sample >= 0.9 before the centre
        oo = np.nonzero(s[c:] <= 0.1)[0]               # outward: the first sample <= 0.1 after the centre
        if not len(ii) or not len(oo):
            continue
        i9 = ii.max()
        o1 = c + oo.min()
        if i9 + 1 >= len(s) or o1 - 1 < 0:
            continue
        t9 = t[i9] + (s[i9] - 0.9) / max(s[i9] - s[i9 + 1], 1e-6) * step
        t1 = t[o1 - 1] + (s[o1 - 1] - 0.1) / max(s[o1 - 1] - s[o1], 1e-6) * step
        w[j] = t1 - t9
    return w


def zones_qa(P, n, cx, collar):
    z = np.empty(len(P), object)
    flank = np.abs(n[:, 0]) >= np.abs(n[:, 1])
    z[flank & (n[:, 0] < 0)] = "left_flank"
    z[flank & (n[:, 0] >= 0)] = "right_flank"
    top = ~flank & (n[:, 1] < 0)
    z[top & (P[:, 0] < cx)] = "top_left_arc"
    z[top & (P[:, 0] >= cx)] = "top_right_arc"
    z[~flank & (n[:, 1] >= 0)] = "bottom_arc"
    z[collar] = "collar"
    return z


def zones_r9(P):
    th = np.rad2deg(np.arctan2(P[:, 1] - R9C[1], P[:, 0] - R9C[0]))
    t = np.where(th < -90, th + 360, th)                 # -90 .. 270
    z = np.empty(len(P), object)
    z[(t >= -90) & (t < 20.375)] = "right_side"
    z[(t >= 20.375) & (t < 154.875)] = "bottom_arc"
    z[(t >= 154.875) & (t < 199.375)] = "left_flank"
    z[(t >= 199.375)] = "top_left_arc"
    return z


def ordered_open(P, keep):
    """the outline as an open polyline from just right of the collar, clockwise (theta increasing), round to just left of it"""
    idx = np.nonzero(keep)[0]
    th = np.rad2deg(np.arctan2(P[idx, 1] - R9C[1], P[idx, 0] - R9C[0]))
    t = np.where(th < -90, th + 360, th)
    o = idx[np.argsort(t)]
    return o


def resample(Q, step, phase):
    seg = np.hypot(*np.diff(Q, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    ss = np.arange(phase, s[-1], step)
    return np.stack([np.interp(ss, s, Q[:, 0]), np.interp(ss, s, Q[:, 1])], 1)


def turns(R):
    d = np.diff(R, axis=0)
    a = np.arctan2(d[:, 1], d[:, 0])
    tr = np.rad2deg(np.angle(np.exp(1j * (a[1:] - a[:-1]))))
    return tr, R[1:-1]                                    # turn at each interior joint and the joint's position


def dist_to_polyline(pts, poly):
    """distance from every point to the polyline (segments), by blocks"""
    A_ = poly[:-1]
    B_ = poly[1:]
    AB = B_ - A_
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    out = np.empty(len(pts))
    for i0 in range(0, len(pts), 256):
        p = pts[i0:i0 + 256, None, :]
        t = np.clip(((p - A_[None]) * AB[None]).sum(2) / L2[None], 0, 1)
        proj = A_[None] + t[..., None] * AB[None]
        out[i0:i0 + 256] = np.sqrt(((p - proj) ** 2).sum(2)).min(1)
    return out


def hull_depth(P, keep):
    H = cv2.convexHull(P[keep].astype(np.float32)).reshape(-1, 2).astype(np.float64)
    H = np.vstack([H, H[:1]])
    d = dist_to_polyline(P, H)
    inside = np.array([cv2.pointPolygonTest(H.astype(np.float32), (float(x), float(y)), False) >= 0 for x, y in P])
    return np.where(inside, d, -d)


def row_width(A, y0, y1):
    best = (-1, None, None, None)
    rows = {}
    for y in range(y0, y1):
        a = A[y].astype(np.float64)
        ins = np.nonzero(a >= 0.5)[0]
        if len(ins) < 20:
            continue
        i = ins.min()
        xl = i - 1 + (0.5 - a[i - 1]) / max(a[i] - a[i - 1], 1e-9) if i > 0 else float(i)
        j = ins.max()
        xr = j + (a[j] - 0.5) / max(a[j] - a[j + 1], 1e-9) if j + 1 < len(a) else float(j)
        rows[y] = (xl, xr)
        if xr - xl > best[0]:
            best = (xr - xl, y, xl, xr)
    return best, rows


def stats(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    return dict(n=int(len(v)), median=round(float(np.median(v)), 3), p10=round(float(np.percentile(v, 10)), 3),
                p90=round(float(np.percentile(v, 90)), 3), min=round(float(v.min()), 3), max=round(float(v.max()), 3))


_m9 = json.load(open(os.path.join(LD, "manifest-r9.json")))
V9S = next(v for vs in _m9["variants"].values() for v in vs if v["id"] == "pendant-v2")["shadow"]
R8SH = next(r["sha256_qa"] for r in json.load(open(os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8/data/manifest.json")))["manifest_r8"]["rows"]
            if r["name"] == "pendant-v2 shadow")
res = {}
top8, top9, topD = body_top(A8), body_top(A9), body_top(AD)
C8, bb8 = centre_of(A8, top8)
C9, bb9 = centre_of(A9, top9)
CD, bbD = centre_of(AD, topD)
res["frame"] = dict(lantern_top_row=dict(r8=top8, r9=top9, drum_r4=topD), qa_centre=dict(r8=C8, r9=C9, drum_r4=CD), alpha50_box=dict(r8=bb8, r9=bb9, drum=bbD),
                    r9_centre=R9C, rays_from="R9's centre for both lanterns (any interior point serves: the outline is star-shaped about it)")
print("frame", res["frame"], flush=True)

out = {}
for tag, A in (("r8", A8), ("r9", A9)):
    th, r, P, ok = outline(A, R9C)
    collar = (np.abs(P[:, 0] - COLLAR_X) <= COLLAR_HALF) & (P[:, 1] < COLLAR_Y)
    n = normals(P, R9C)
    zq = zones_qa(P, normals(P, R9C, k=60), C9[0], collar)       # zones from the normal over +-6 deg (a local step does not flip a zone)
    zr = zones_r9(P)
    zr[collar] = "collar"
    w = ramp(A, P, n)
    out[tag] = dict(th=th, r=r, P=P, ok=ok, collar=collar, n=n, zq=zq, zr=zr, w=w)

# where QA's zones meet (theta about R9's centre), against R9's boundaries (20.375, 154.875, 199.375)
bnd = {}
o = out["r9"]
thz = np.rad2deg(np.arctan2(o["P"][:, 1] - R9C[1], o["P"][:, 0] - R9C[0]))
thz = np.where(thz < -90, thz + 360, thz)
srt = np.argsort(thz)
zs_ = o["zq"][srt]
for i in range(1, len(srt)):
    if zs_[i] != zs_[i - 1] and "collar" not in (zs_[i], zs_[i - 1]):
        bnd[f"{zs_[i - 1]} -> {zs_[i]}"] = round(float(thz[srt][i]), 2)
res["zone_boundaries_theta_qa"] = bnd
res["zone_boundaries_theta_r9"] = {"right_side -> bottom_arc": 20.375, "bottom_arc -> left_flank": 154.875, "left_flank -> top_left_arc": 199.375}
print("boundaries", bnd, flush=True)

# ---------------------------------------------------------------- 1. the ramp
thD, rD, PD, okD = outline(AD, CD)
nD = normals(PD, CD)
cordD = (np.abs(PD[:, 0] - COLLAR_X) <= COLLAR_HALF) & (PD[:, 1] < topD + 8)
wD = ramp(AD, PD, nD)
flD = (np.abs(nD[:, 0]) >= np.abs(nD[:, 1])) & ~cordD & okD
res["ramp"] = dict(
    reference_drum_r4=dict(flanks_both=stats(wD[flD]), flanks_left=stats(wD[flD & (nD[:, 0] < 0)]), flanks_right=stats(wD[flD & (nD[:, 0] >= 0)]),
                           whole_outline=stats(wD[~cordD & okD]), r9_says=dict(flanks=2.91, whole_outline=2.778)),
)
for tag in ("r8", "r9"):
    o = out[tag]
    rr = {}
    for zn in ("left_flank", "right_flank", "top_left_arc", "top_right_arc", "bottom_arc"):
        rr[zn] = stats(o["w"][(o["zq"] == zn) & o["ok"]])
    rr["whole_outline_no_collar"] = stats(o["w"][(o["zq"] != "collar") & o["ok"]])
    res["ramp"][tag] = rr
ref = res["ramp"]["reference_drum_r4"]["flanks_both"]["median"]
res["ramp"]["P2-1 (c)"] = {side: dict(value=res["ramp"]["r9"][side]["median"], reference=ref, diff=round(res["ramp"]["r9"][side]["median"] - ref, 3),
                                      pass_=abs(res["ramp"]["r9"][side]["median"] - ref) <= 0.5) for side in ("left_flank", "right_flank")}
res["ramp"]["r8_any_natural_ramp"] = dict(
    share_of_r8_outline_points_with_ramp_ge_2px=round(float((out["r8"]["w"][(out["r8"]["zq"] != "collar")] >= 2).mean()), 4),
    r8_p90_whole=res["ramp"]["r8"]["whole_outline_no_collar"]["p90"],
    reading="if R8's outline had a part that kept the render's own (wider) ramp it would show here; the designer's fallback (the default pendant) applies otherwise")
print("ramp", json.dumps(res["ramp"], default=str)[:1500], flush=True)

# ---------------------------------------------------------------- 2. the turns
tur = {}
for tag in ("r8", "r9"):
    o = out[tag]
    keep = o["ok"] & ~o["collar"]
    oo = ordered_open(o["P"], keep)
    Q = o["P"][oo]
    per_phase = []
    for ph in (0.0, 1.0, 2.0, 3.0):
        R = resample(Q, 4.0, ph)
        tr, J = turns(R)
        dom = np.sign(tr.sum())
        # the joint's zones: nearest outline point
        dd = ((J[:, None, :] - Q[None, ::5, :]) ** 2).sum(2).argmin(1) * 5
        zqj = o["zq"][oo][dd]
        zrj = o["zr"][oo][dd]
        rec = dict(phase=ph, dominant_sign=int(dom))
        for nm, zz in (("qa", zqj), ("r9", zrj)):
            for zn in sorted(set(zz)):
                sel = zz == zn
                rec[f"{nm}:{zn}"] = dict(n=int(sel.sum()), opposite=int(((np.sign(tr) == -dom) & (np.abs(tr) >= 0.1) & sel).sum()),
                                         straight=int((np.abs(tr) < 0.1)[sel].sum()))
        # the right edge: theta -45 .. the bottom arc (QA's zones: the right flank from where theta >= -45)
        thj = np.rad2deg(np.arctan2(J[:, 1] - R9C[1], J[:, 0] - R9C[0]))
        edge = (thj >= -45) & (thj < 90) & (zqj == "right_flank")
        ii = np.nonzero(edge)[0]
        ratios = []
        for i in ii:
            if i - 1 < 0 or i + 1 >= len(tr):
                continue
            den = max((abs(tr[i - 1]) + abs(tr[i + 1])) / 2, 0.1)
            ratios.append((abs(tr[i]) / den, i))
        if ratios:
            mx, im = max(ratios)
            rec["right_edge"] = dict(chords=len(ratios), max_ratio=round(float(mx), 3), at=[round(float(v), 1) for v in J[im]], turn_deg=round(float(tr[im]), 2),
                                     over_2x=int(sum(1 for q, _ in ratios if q > 2)), theta_range=[round(float(thj[ii].min()), 1), round(float(thj[ii].max()), 1)])
        rec["opposite_detail_fitted"] = [dict(at=[round(float(v), 1) for v in J[i]], turn_deg=round(float(tr[i]), 3), qa_zone=str(zqj[i]), r9_zone=str(zrj[i]))
                                         for i in np.nonzero((np.sign(tr) == -dom) & (np.abs(tr) >= 0.1))[0]
                                         if zqj[i] in ("left_flank", "right_flank", "top_right_arc") or zrj[i] in ("left_flank", "right_side")]
        per_phase.append(rec)
    tur[tag] = per_phase
    print("turns", tag, [(p["phase"], p.get("right_edge", {}).get("max_ratio"), p.get("right_edge", {}).get("over_2x"),
                          {k: v["opposite"] for k, v in p.items() if isinstance(v, dict) and "opposite" in v}) for p in per_phase], flush=True)
res["turns"] = tur
res["turns_summary"] = {tag: dict(right_edge_max_ratio_over_phases=max(p["right_edge"]["max_ratio"] for p in tur[tag]),
                                  right_edge_over_2x_any_phase=sum(p["right_edge"]["over_2x"] for p in tur[tag]),
                                  opposite_qa_zones_max_over_phases={z: max(p.get(f"qa:{z}", {}).get("opposite", 0) for p in tur[tag])
                                                                     for z in ("left_flank", "right_flank", "top_right_arc", "top_left_arc", "bottom_arc")},
                                  opposite_r9_zones_max_over_phases={z: max(p.get(f"r9:{z}", {}).get("opposite", 0) for p in tur[tag])
                                                                     for z in ("right_side", "left_flank", "top_left_arc", "bottom_arc")},
                                  n_r9_zones_phase0={z: tur[tag][0].get(f"r9:{z}", {}).get("n", 0) for z in ("right_side", "left_flank", "top_left_arc", "bottom_arc")})
                        for tag in tur}
print("turns summary", res["turns_summary"], flush=True)

# ---------------------------------------------------------------- 3. the line against a fit
poly9 = np.load(os.path.join(P2, "work-r9/pendant2-outline-r9.npy"), allow_pickle=False)
fit = {}
for tag in ("r8", "r9"):
    o = out[tag]
    keep = o["ok"] & ~o["collar"]
    dpol = dist_to_polyline(o["P"], np.vstack([poly9, poly9[:1]])) if tag == "r9" else None
    hd = hull_depth(o["P"], keep)
    # local bump: r minus its Gaussian smoothing over theta (sigma 5 deg = 50 samples), circular
    rr = o["r"].copy()
    bad = ~keep
    rr[bad] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], rr[~bad], period=len(rr))
    g = np.exp(-0.5 * (np.arange(-150, 151) / 50.0) ** 2)
    g /= g.sum()
    sm = np.convolve(np.concatenate([rr[-150:], rr, rr[:150]]), g, mode="same")[150:-150]
    bump = rr - sm
    rec = {}
    for zs, zz in (("qa", o["zq"]), ("r9", o["zr"])):
        for zn in sorted(set(zz)):
            if zn == "collar":
                continue
            sel = (zz == zn) & keep
            if not sel.any():
                continue
            i = np.nonzero(sel)[0][np.argmax(hd[sel])]
            r_ = dict(hull_depth_max=round(float(hd[sel].max()), 3), hull_depth_at=[round(float(v), 1) for v in o["P"][i]],
                      bump_max_abs=round(float(np.abs(bump[sel]).max()), 3))
            if dpol is not None:
                r_["dist_to_r9_stored_line_max"] = round(float(dpol[sel].max()), 3)
                r_["dist_to_r9_stored_line_p99"] = round(float(np.percentile(dpol[sel], 99)), 3)
            rec[f"{zs}:{zn}"] = r_
    fit[tag] = rec
    print("fit", tag, json.dumps(rec), flush=True)
res["fit"] = fit

# ---------------------------------------------------------------- 4. the line R8 -> R9
dr = out["r9"]["r"] - out["r8"]["r"]
mv = {}
okb = out["r8"]["ok"] & out["r9"]["ok"] & ~out["r8"]["collar"] & ~out["r9"]["collar"]
for zs, zz in (("qa", out["r9"]["zq"]), ("r9", out["r9"]["zr"])):
    for zn in sorted(set(zz)):
        sel = (zz == zn) & okb
        if sel.any():
            mv[f"{zs}:{zn}"] = dict(n=int(sel.sum()), median_abs=round(float(np.median(np.abs(dr[sel]))), 3), max_abs=round(float(np.abs(dr[sel]).max()), 3),
                                    max_out=round(float(dr[sel].max()), 3), max_in=round(float(dr[sel].min()), 3))
res["line_move_r8_to_r9_px"] = mv
print("line move", json.dumps(mv), flush=True)

# ---------------------------------------------------------------- 5. the width
(w8, y8, xl8, xr8), rows8 = row_width(A8, top8 + 8, 362)
(w9, y9, xl9, xr9), rows9 = row_width(A9, top9 + 8, 362)
CM_PER_PX = 41.0 / w8
res["width"] = dict(r8=dict(width_px=round(w8, 3), row=y8, xl=round(xl8, 3), xr=round(xr8, 3)), r9=dict(width_px=round(w9, 3), row=y9, xl=round(xl9, 3), xr=round(xr9, 3)),
                    change_px=round(w9 - w8, 3), change_cm=round((w9 - w8) * CM_PER_PX, 3), cm_per_px=round(CM_PER_PX, 4),
                    scale_note="41 cm = R8's widest row (R5 measured 41.2 cm; the card says 40)",
                    P2_1_d=dict(rule="max width changes <= 2 px (41 +- 0.3 cm)", pass_=abs(w9 - w8) <= 2 and abs((w9 - w8) * CM_PER_PX) <= 0.3),
                    r9_says=dict(r8=240.221, r9=239.879, change=-0.342))
print("width", res["width"], flush=True)

# ---------------------------------------------------------------- 6. alpha only, the bleed, the untouched parts
a8, a9 = L8[..., 3], L9[..., 3]
c8, c9 = L8[..., :3], L9[..., :3]
dc = np.abs(c8 - c9).max(2)
rose = a9 > a8
chg = dc > 0
ys, xs = np.nonzero(chg)
# the bleed near each changed pixel: R8's stored RGB at alpha-0 pixels within 2.5 px
zero = a8 == 0
imp, near, inside = [], [], []
for y, x in zip(ys, xs):
    A_, B_ = a8[y, x], a9[y, x]
    add = (B_ * c9[y, x] - A_ * c8[y, x]) / max(B_ - A_, 1e-6)
    y0, y1, x0, x1 = max(0, y - 3), y + 4, max(0, x - 3), x + 4
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = zero[y0:y1, x0:x1] & (np.hypot(yy - y, xx - x) <= 2.5)
    if m.any():
        bl = c8[y0:y1, x0:x1][m]
        imp.append(float(np.abs(add - bl.mean(0)).max()))
        lo = np.minimum(bl.min(0), c8[y, x]) - 1
        hi = np.maximum(bl.max(0), c8[y, x]) + 1
        inside.append(bool(((c9[y, x] >= lo) & (c9[y, x] <= hi)).all()))
    near.append(bool(m.any()))


def lab1(c):
    return cv2.cvtColor(np.asarray(c, np.float32).reshape(1, -1, 3) / 255, cv2.COLOR_RGB2LAB).reshape(-1, 3)


dL = lab1(c9[chg])[:, 0] - lab1(c8[chg])[:, 0]
big = np.argsort(dL)[:8]
dL_detail = [dict(x=int(xs[i]), y=int(ys[i]), a8=int(a8[ys[i], xs[i]]), a9=int(a9[ys[i], xs[i]]), dL_straight=round(float(dL[i]), 2),
                  dL_weighted_by_a9=round(float(dL[i] * a9[ys[i], xs[i]] / 255), 2)) for i in big]
cord = np.zeros(a8.shape, bool)
cord[:195] = True                              # the canopy and the cord, above the lantern (R9's top changes start at row 195)
collar = np.zeros(a8.shape, bool)
collar[:204, int(np.ceil(COLLAR_X - 9)):int(np.floor(COLLAR_X + 9)) + 1] = True
ch_any = (a8 != a9) | chg
z9 = out["r9"]["zq"]
zone_of_chg = {}
P9 = out["r9"]["P"]
for y, x in zip(ys, xs):
    k = int(np.argmin((P9[:, 0] - x) ** 2 + (P9[:, 1] - y) ** 2))
    zone_of_chg[z9[k]] = zone_of_chg.get(z9[k], 0) + 1
res["alpha_only"] = dict(
    rgb_changed_px=int(chg.sum()), rgb_changed_at_alpha255_both=int((chg & (a8 == 255) & (a9 == 255)).sum()), rgb_changed_where_alpha_not_raised=int((chg & ~rose).sum()),
    rgb_changed_zones=zone_of_chg,
    implied_added_colour_vs_bleed=dict(px_with_bleed_within_2_5=int(sum(near)), max_abs_diff_levels=round(max(imp), 2) if imp else None,
                                       p95=round(float(np.percentile(imp, 95)), 2) if imp else None, median=round(float(np.median(imp)), 2) if imp else None),
    new_rgb_between_old_and_bleed_px=int(sum(inside)), of_px=len(inside),
    dL_on_changed_rgb=dict(median=round(float(np.median(dL)), 2), min=round(float(dL.min()), 2), max=round(float(dL.max()), 2),
                           weighted_by_new_alpha_min=round(float((dL * a9[chg] / 255).min()), 2), darkest=dL_detail),
    rows_lt_195_changed_px=int((ch_any & cord).sum()), collar_zone_changed_px=int((ch_any & collar).sum()),
    shadow_file=dict(r9_manifest=V9S, same_as_r8_qa_list=sha(os.path.join(LD, V9S)) == R8SH),
    alpha_changed_px=int((a8 != a9).sum()), alpha_raised=int(rose.sum()), alpha_lowered=int((a9 < a8).sum()))
print("alpha only", res["alpha_only"], flush=True)

# the top-left arc for the designer (the stop rule)
tl = {}
for tag in ("r8", "r9"):
    o = out[tag]
    sel = (o["zq"] == "top_left_arc") & o["ok"]
    tl[tag] = dict(points=int(sel.sum()), ramp=stats(o["w"][sel]), x_range=[round(float(o["P"][sel, 0].min()), 1), round(float(o["P"][sel, 0].max()), 1)])
tl["line_move"] = mv.get("qa:top_left_arc")
tl["hull_depth_r9"] = fit["r9"].get("qa:top_left_arc")
tl["hull_depth_r8"] = fit["r8"].get("qa:top_left_arc")
tl["r9_says"] = dict(least_squares_fill=2.248, at=[1614.8, 216.4], line_move_median=0.045, line_move_max=0.124, opposite_turns="9 of 23")
res["top_left_arc"] = tl
print("top-left", json.dumps(tl), flush=True)

# keep the outlines for the overlays
np.savez_compressed(os.path.join(OUT, "data/pendant-outlines.npz"), **{f"{t}_{k}": out[t][k] for t in out for k in ("P", "r", "w", "ok", "collar")},
                    **{f"{t}_zq": out[t]["zq"].astype(str) for t in out})
json.dump(res, open(os.path.join(OUT, "data/pendant.json"), "w"), indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
print("written", flush=True)

# the kept arcs without R9's declared blends (fix-r9.json geometry.blends: 6 deg at the bottom arc's ends and at the top-left arc's start,
# 12 deg at the top centre): does the line stay within +-0.3 px there?
thr9 = np.rad2deg(np.arctan2(out["r9"]["P"][:, 1] - R9C[1], out["r9"]["P"][:, 0] - R9C[0]))
thr9 = np.where(thr9 < -90, thr9 + 360, thr9)
kb = {}
for nm, lo, hi in (("bottom_arc", 20.375, 154.875), ("top_left_arc", 199.375, 270.0)):
    sel = okb & (thr9 >= lo) & (thr9 < hi)
    core = sel & (thr9 >= lo + 6) & (thr9 < hi - (12 if nm == "top_left_arc" else 6))
    i = np.nonzero(sel)[0][np.argmax(np.abs(dr[sel]))]
    kb[nm] = dict(all=dict(max_abs=round(float(np.abs(dr[sel]).max()), 3), at_theta=round(float(thr9[i]), 2), at=[round(float(v), 1) for v in out["r9"]["P"][i]]),
                  without_blends=dict(n=int(core.sum()), median_abs=round(float(np.median(np.abs(dr[core]))), 3), max_abs=round(float(np.abs(dr[core]).max()), 3),
                                      pass_0_3=bool(np.abs(dr[core]).max() <= 0.3)))
res["kept_arcs_line_move"] = kb
print("kept arcs", kb, flush=True)
json.dump(res, open(os.path.join(OUT, "data/pendant.json"), "w"), indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
