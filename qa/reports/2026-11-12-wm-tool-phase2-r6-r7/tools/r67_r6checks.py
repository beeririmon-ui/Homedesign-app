#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R6): the code fixes QA R5 and the designer asked for, measured on the graded set-B truths (r5 = before, r6 = after;
r7 for the layers R7 did not touch, which keep r6's bytes). QA's own code.
  framed-art v2  the rails' inner edge (r5_art_seam.py's metric, copied): residual RMS / max, jumps >= 0.6 / 1.0 px, per rail, r5 vs r6,
                 for all columns and for the columns where the print beside the rail is light (L* > 45 three px inside);
                 QA R5's specks (1531, 610), (1531, 614), (1536, 669), (1677, 536) and the light line x 1963 rows 520-530: L* at each;
                 isolated light specks in the prints' black (layer) r5 vs r6.
  pendant 2      the canopy: its alpha's extent per row (rows 4-42) against the cord's column; the cord's L* / C* (alpha 255, rows 60-190);
                 the rings: per row, the paper's median L* over the lantern's middle third, minus a 12-row smooth -> residual std / max;
                 the right outline: per row the alpha-0.5 crossing minus a 6-row smooth -> max |residual| and the rows over 1 px.
  vases          the axis tilt (alpha-0.5 mid-points of the body rows, a line fit), the left / right half-width asymmetry about the axis,
                 the widest width in cm at the vase point (-2.42, 1.35, Z 0.45) against the card, the lit half's L / C / h (the window
                 side, x < the axis), and vase 2's body (alpha 255 eroded 5) against the designer's targets.
  magazine rods  the dark line under the front rod: pixels darker than both neighbours above and below by >= 4 L*, and pixels < L* 25,
                 in the band render-agent's record names (fix-r6.json rods.front), r5 vs r6.
Writes data/r6-checks.json.
"""
import importlib.util
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CAM = r1.CAM["M0"]
FW = 3840 * 2720 / 4072
M = {t: json.load(open(os.path.join(P2, f"layers/manifest-{t}.json"))) for t in ("r5", "r6", "r7")}
VV = {t: {v["id"]: v for vs in M[t]["variants"].values() for v in vs} for t in M}
BY = {t: {l_["id"]: l_ for l_ in M[t]["layers"]} for t in M}


def u8(p):
    return np.asarray(Image.open(p))


def lab(rgb8):
    return cv2.cvtColor(rgb8[..., :3].astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def truth(tag, vid=None):
    p = f"graded/variant-{tag}-{vid}-set-B-graded-v3c.png" if vid else f"graded/default-scene-{tag}-set-B-graded-v3c.png"
    return u8(os.path.join(P2, p))[..., :3]


def summ(px):
    L, a, b = np.median(px, 0)
    return dict(L=round(float(L), 2), C=round(float(np.hypot(a, b)), 2), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), px=int(len(px)))


res = {}
# ------------------------------------------------------------------ framed art 2
RAILS = [("print 1 top", 1525, 1690, 528, 552), ("print 2 top", 1735, 1910, 512, 540), ("print 3 top", 1965, 2160, 500, 530),
         ("print 1 bottom", 1525, 1690, 772, 796), ("print 2 bottom", 1735, 1910, 772, 796), ("print 3 bottom", 1965, 2160, 776, 802)]


def rail(L, x0, x1, y0, y1, top, light_only=False):
    ys, xs_ = [], []
    for x in range(x0, x1):
        col = L[y0:y1, x].astype(np.float64)
        g = np.diff(col) if top else -np.diff(col)
        i = int(np.argmax(g))
        off = 0.0
        if 0 < i < len(g) - 1:
            a, b, c = g[i - 1], g[i], g[i + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if abs(den) > 1e-6 else 0.0
        yy = y0 + i + 0.5 + float(np.clip(off, -0.5, 0.5))
        if light_only:
            yin = int(round(yy + (3 if top else -3)))
            if L[yin, x] <= 45:
                continue
        ys.append(yy)
        xs_.append(x)
    ys, xs_ = np.array(ys), np.array(xs_)
    k, b = np.polyfit(xs_, ys, 1)
    r = ys - (k * xs_ + b)
    j = np.abs(np.diff(ys))
    return dict(columns=int(len(xs_)), residual_rms=round(float(np.sqrt((r ** 2).mean())), 3), residual_max=round(float(np.abs(r).max()), 2),
                jumps_ge_0_6=int((j >= 0.6).sum()), jumps_ge_1_0=int((j >= 1.0).sum()))


fa = {}
for tag in ("r5", "r6", "r7"):
    L = lab(truth(tag, "framed-art-v2"))[..., 0]
    fa[tag] = {}
    for name, x0, x1, y0, y1 in RAILS:
        fa[tag][name] = dict(all=rail(L, x0, x1, y0, y1, "top" in name), light_print=rail(L, x0, x1, y0, y1, "top" in name, True))
    fa[tag]["qa_r5_points_L"] = {f"{x},{y}": round(float(L[y, x]), 1) for x, y in ((1531, 610), (1531, 614), (1536, 669), (1677, 536))}
    fa[tag]["qa_r5_points_neighbours_median_L"] = {f"{x},{y}": round(float(np.median(L[y - 2:y + 3, x - 2:x + 3])), 1) for x, y in ((1531, 610), (1531, 614), (1536, 669), (1677, 536))}
    fa[tag]["line_x1963_rows_520_530_L"] = [round(float(v), 1) for v in L[520:531, 1963]]
    fa[tag]["line_x1963_neighbours_L"] = [round(float(v), 1) for v in np.median(L[520:531, 1965:1969], 1)]
    lay = u8(os.path.join(P2, "layers", VV[tag]["framed-art-v2"]["file"]))
    La = lab(lay)[..., 0]
    a = lay[..., 3]
    black = (La < 25) & (a == 255)
    blk = cv2.morphologyEx(black.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    med = float(np.median(La[black]))
    spk = blk & ~black & (La > med + 25)
    k8 = np.ones((3, 3), np.float32)
    k8[1, 1] = 0
    nb = cv2.filter2D(black.astype(np.float32), -1, k8, borderType=cv2.BORDER_CONSTANT)
    iso = spk & (nb >= 7)
    ys, xs = np.nonzero(spk)
    fa[tag]["specks_layer"] = dict(light_px_inside_black=int(spk.sum()), isolated=int(iso.sum()),
                                   coords=[[int(x), int(y), round(float(La[y, x]), 1)] for y, x in zip(ys, xs)][:30])
    print("art", tag, {k: (v["all"]["jumps_ge_1_0"], v["light_print"]["jumps_ge_1_0"], v["all"]["residual_rms"]) for k, v in fa[tag].items() if k.startswith("print")},
          fa[tag]["qa_r5_points_L"], fa[tag]["specks_layer"]["light_px_inside_black"], fa[tag]["specks_layer"]["isolated"])
res["framed-art-v2"] = fa

# ------------------------------------------------------------------ pendant 2
pe = {}
for tag in ("r5", "r6"):
    lay = u8(os.path.join(P2, "layers", VV[tag]["pendant-v2"]["file"]))
    a = lay[..., 3].astype(np.float32) / 255
    T = truth(tag, "pendant-v2")
    Lab = lab(T)
    cord_rows = range(60, 190)
    cx = [float((np.arange(1600, 1760) * a[y, 1600:1760]).sum() / max(a[y, 1600:1760].sum(), 1e-6)) for y in cord_rows if a[y, 1600:1760].sum() > 0.5]
    cord_x = float(np.median(cx))
    can = []
    for y in range(4, 43):
        xs = np.nonzero(a[y, 1600:1760] >= 0.5)[0] + 1600
        if len(xs):
            can.append([y, int(xs.min()), int(xs.max()), round((xs.min() + xs.max()) / 2 - cord_x, 1)])
    widest = max(can, key=lambda r: r[2] - r[1]) if can else None
    cm = np.zeros(a.shape, bool)
    for y in cord_rows:
        cm[y, 1600:1760] = a[y, 1600:1760] >= 0.99
    pe[tag] = dict(cord_x=round(cord_x, 1), canopy_widest_row=widest, canopy_rows=len(can),
                   canopy_centre_minus_cord_px_median=round(float(np.median([r[3] for r in can])), 1) if can else None,
                   cord=summ(Lab[cm]))
    # the lantern: rows where the alpha is wide (> 60 px)
    w = (a >= 0.5).sum(1)
    rows = np.nonzero(w > 60)[0]
    rows = rows[rows >= 195]          # the lantern only (the canopy is above row 45)
    y0, y1 = int(rows.min()), int(rows.max())
    prof = []
    for y in range(y0 + 3, y1 - 3):
        xs = np.nonzero(a[y] >= 0.99)[0]
        if len(xs) < 30:
            prof.append(np.nan)
            continue
        x0_, x1_ = xs.min(), xs.max()
        t = (x1_ - x0_) / 3
        prof.append(float(np.median(Lab[y, int(x0_ + t):int(x1_ - t), 0])))
    prof = np.array(prof)
    ok = ~np.isnan(prof)
    sm = cv2.GaussianBlur(prof[ok].reshape(-1, 1).astype(np.float32), (0, 0), sigmaX=1, sigmaY=12).ravel()
    resid = prof[ok] - sm
    pe[tag]["rings_row_profile"] = dict(rows=[y0, y1], residual_std=round(float(resid.std()), 2), residual_max_abs=round(float(np.abs(resid).max()), 2))
    # right outline
    rx = []
    for y in range(y0 + 2, y1 - 2):
        row = a[y]
        xs = np.nonzero(row >= 0.5)[0]
        if not len(xs):
            continue
        x = int(xs.max())
        f = (row[x] - 0.5) / max(row[x] - row[x + 1], 1e-6)
        rx.append(x + float(np.clip(f, 0, 1)))
    rx = np.array(rx)
    sm2 = cv2.GaussianBlur(rx.reshape(-1, 1).astype(np.float32), (0, 0), sigmaX=1, sigmaY=6).ravel()
    rr = rx - sm2
    pe[tag]["right_outline"] = dict(max_abs_residual_px=round(float(np.abs(rr[6:-6]).max()), 2), rows_over_1px=int((np.abs(rr[6:-6]) > 1).sum()),
                                    rows=int(len(rr) - 12))
    print("pendant", tag, pe[tag])
res["pendant-v2"] = pe


# ------------------------------------------------------------------ vases
def px(X, Y, Z):
    u, v, d = r1.project(CAM, X, Y, Z)
    return 77.49 + u * FW, 43.43 + v * 2160 * 1530 / 2290, d


d_vase = px(-2.42, 1.35, 0.45)[2]
cmpp = 100 * d_vase / ((CAM.get("lens", 24) / 36) * FW)
foot = px(-2.42, 1.35, 0.45)
CARD = {"vase": (16, 32), "vase-v2": (22, 32), "vase-v3": (22.6, 33)}
va = {}
for tag, key, f, T in (("r5", "vase", BY["r5"]["vase"]["file"], truth("r5")), ("r6", "vase", BY["r6"]["vase"]["file"], truth("r6")),
                       ("r5", "vase-v2", VV["r5"]["vase-v2"]["file"], truth("r5", "vase-v2")), ("r6", "vase-v2", VV["r6"]["vase-v2"]["file"], truth("r6", "vase-v2")),
                       ("r7", "vase-v3", VV["r7"]["vase-v3"]["file"], truth("r7", "vase-v3"))):
    lay = u8(os.path.join(P2, "layers", f))
    a = lay[..., 3].astype(np.float32) / 255
    w = (a >= 0.5).sum(1)
    yb = int(np.nonzero(w > 0)[0].max())
    exp_top = px(-2.42, 1.35, 0.45 + CARD[key][1] / 100)[1]
    body = [y for y in range(int(exp_top) + 6, yb - 3) if w[y] > 0]
    mids, L_, R_ = [], [], []
    for y in body:
        row = a[y, 560:780]
        xs = np.nonzero(row >= 0.5)[0]
        if not len(xs):
            continue
        xl, xr = xs.min(), xs.max()
        fl = (row[xl] - 0.5) / max(row[xl] - row[xl - 1], 1e-6)
        fr = (row[xr] - 0.5) / max(row[xr] - row[xr + 1], 1e-6)
        lft = 560 + xl - float(np.clip(fl, 0, 1))
        rgt = 560 + xr + float(np.clip(fr, 0, 1))
        mids.append((y, (lft + rgt) / 2))
        L_.append(lft)
        R_.append(rgt)
    yy = np.array([m[0] for m in mids], float)
    mm = np.array([m[1] for m in mids])
    k, b = np.polyfit(yy, mm, 1)
    axis = k * yy + b
    hl, hr = axis - np.array(L_), np.array(R_) - axis
    asym = (hl - hr) / np.maximum(hl + hr, 1)
    widest = float((np.array(R_) - np.array(L_)).max())
    Lab = lab(T)
    inner = cv2.erode((lay[..., 3] == 255).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    lit = np.zeros(inner.shape, bool)
    for y, ax in zip(yy.astype(int), axis):
        lit[y, :int(ax)] = inner[y, :int(ax)]
    bodym = np.zeros(inner.shape, bool)
    bodym[int(yy.min()):int(yy.max()) + 1] = inner[int(yy.min()):int(yy.max()) + 1]
    ex = [px(-2.42 + CARD[key][0] / 200 * math.cos(t), 1.35 + CARD[key][0] / 200 * math.sin(t), z)[0]
          for t in np.linspace(0, 2 * math.pi, 72) for z in (0.45, 0.45 + CARD[key][1] / 100)]
    exp_w = max(ex) - min(ex)
    va[f"{key} [{tag}]"] = dict(expected_width_px_card=round(exp_w, 1), width_ratio_to_card=round(widest / exp_w, 3), tilt_deg=round(math.degrees(math.atan(k)), 2), body_rows=[int(yy.min()), int(yy.max())],
                                half_width_asymmetry_p90=round(float(np.percentile(np.abs(asym), 90)), 3), asym_median=round(float(np.median(asym)), 3),
                                widest_px=round(widest, 1), widest_cm=round(widest * cmpp, 1), card_cm=CARD[key], foot_row=yb, plan_foot_row=round(foot[1], 1),
                                foot_centre_x=round(float(axis[-1]), 1), plan_x=round(foot[0], 1), lit_half=summ(Lab[lit]), body=summ(Lab[bodym]))
    print("vase", key, tag, va[f"{key} [{tag}]"])
res["vases"] = va
res["vase_cm_per_px"] = round(cmpp, 4)

# ------------------------------------------------------------------ magazine-holder rods
fx = json.load(open(os.path.join(P2, "work-r6/fix-r6.json")))
mh = {}
for tag in ("r5", "r6"):
    L = lab(truth(tag))[..., 0]
    lay = u8(os.path.join(P2, "layers", BY[tag]["magazine-holder"]["file"]))
    A = lay[..., 3]
    # the rods: thin near-horizontal light lines; find in the holder box the rows with the most satin pixels per column window
    box = (900, 1360, 1245, 1530)
    sub = L[box[1]:box[3], box[0]:box[2]]
    up = np.roll(sub, 1, 0)
    dn = np.roll(sub, -1, 0)
    up2 = np.roll(sub, 2, 0)
    dn2 = np.roll(sub, -2, 0)
    dark = (sub < np.minimum(up2, dn2) - 4) & (sub < np.minimum(up, dn) + 1)
    mh[tag] = dict(dark_line_px_in_box=int(dark.sum()), below_L25_in_box=int((sub < 25).sum()))
res["magazine-holder"] = mh
res["magazine-holder_render_agent_record"] = fx["magazine-holder"].get("dark_line_px")
print("mh", mh)
json.dump(res, open(os.path.join(OUT, "data/r6-checks.json"), "w"), indent=1, default=float)
