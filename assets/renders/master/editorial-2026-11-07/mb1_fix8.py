#!/usr/bin/env python3
"""
mb1_fix8.py: two 0-token grading fixes on the warm-modern master bedroom; render-agent, 2026-11-11.
Source: docs/master-bedroom-comparison-2026-11-07.md §6 (master-designer, the eye on fix5, 2026-11-10), QA
qa/reports/2026-11-10-ged-master-wm-fix5.md (+ .json, tools/cast_shadow.py, tools/shadow_floor.py), the gate's
qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py. Base: warm-modern/warm-modern-MB-A-fix5.png (not changed).
Out: warm-modern/warm-modern-MB-A-fix6.png. Record: mb1-fix8.json. Crops: fix8-before-after/.

  (b)  the core of the lumbar's cast shadow on the right caramel pillowcase, lifted (designer's polish (b)):
       target: the median L* in the box x 2210-2330, y 820-925 at 14-15 on the FINISHED frame (fix5: 10.5), so the shadow
       under the lit right sconce is lighter than the unfilled slit between the pillowcases.
       How (no pixel from fix4; a curve, not a fill):
         - base / detail: logY smoothed (Gaussian sigma 3, normalised over the pillowcase only; the cushion and the duvet
           are cut out, so neither bleeds into the base); detail = logY - base keeps the linen creases as they are.
         - the pillowcase's unshadowed level: a smooth fit (quadratic in x, the light falls off to the right) of the base
           on clearly lit pillowcase: the band above the cushion (y 790-812) and the strip right of the shadow (x 2480-2520).
         - the shadow's depth D = unshadowed - base (in logY); a soft threshold keeps shallow shading (A > 0.8: the linen's
           own folds) untouched; the depth beyond it is scaled by GAMMA: the same curve at every pixel of the shadow, so the
           wedge keeps its outline (its iso-lines do not move), it fades out where the shadow fades out, and nothing
           steps at a box edge.
         - kept: a 3 px contact line along the cushion's right edge (no lift within 3 px, a soft ramp to full at 12 px) and
           along the pillowcase's base against the duvet (3 px, ramp to 10 px).
         - colour: the lifted base takes the caramel shadow's own chroma at its new level (C* vs L* measured on this
           pillowcase in this frame) and the hue H_T 55.5 (the lit caramel is 56.5; QA's patch), the per-pixel a*, b*
           texture kept; the contact lines keep their L* and take the same hue. Never grey.
       Region: the cushion's cast shadow itself (bbox in the record, raw/fix6-b-region.png). DEVIATION, declared:
       QA's area was x 2215-2330, y 840-925. The shadow's lower half runs past x 2330 (L* < 14 to x 2440 at y 900-918) and
       its top starts at y 822; a lift cut at that box (tried first) left a 4-5 L* vertical step at x 2330 (y 880-915) and
       a dark cap above y 840: the wedge read as a lit rectangle. Following the shadow keeps the wedge.
  toe  Q-ED7 (a): q_ed7_toe.py (the same curve as the living room's ed9), after (b), on the whole frame: L* only, lift below
       12, soft blend to the identity at 20, nothing at L* >= 20 moves; hue and saturation kept; s0 solved so that the
       gate's p1 (quarter-size bilinear copy) is 9.0 (target 8.5-9.5).
  crops  fix8-before-after/: the pillowcase shadow, the muslin throw's deep folds, the walnut nightstand; 100 % and x4.

Usage: ~/.venvs/motion/bin/python -I mb1_fix8.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import q_ed7_toe as T  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASE = "warm-modern/warm-modern-MB-A-fix5.png"
OUT = "warm-modern/warm-modern-MB-A-fix6.png"
REGION_PNG = "warm-modern/raw/fix6-b-region.png"
REC = os.path.join(HERE, "mb1-fix8.json")
CROPS = os.path.join(HERE, "fix8-before-after")
QA_LUMBAR = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5/data/qa-lumbar-mask.png")

BOX = (2210, 820, 2330, 925)        # the designer's box for the median (x0, y0, x1, y1; exclusive ends, as QA's cast_shadow.py slices)
QA_AREA = (2215, 840, 2330, 925)    # QA's suggested lift area (record only; see DEVIATION)
SLIT = (2030, 770, 2060, 812)       # QA's gap spot box between the pillowcases (mb1-fix7.json gap.spot_box): the unfilled slit
WIN = (2150, 760, 2600, 960)        # working window (frame px)
H_T = 55.5                          # hue of the lifted shadow (lit caramel 56.5; the designer's window +-3 deg)
D0 = -np.log(0.8)                   # shallow shading (A > 0.8) is the linen's own form: untouched
KNEE = 0.08                         # soft-threshold knee (logY)
FINAL_MEDIAN_TARGET = 14.5          # middle of 14-15, on the finished frame (after the toe)


def load(p):
    return np.asarray(Image.open(os.path.join(HERE, p)).convert("RGB"))


def masks(L, C, yy, xx):
    """the cushion (Milk Tea boucle: L* > 30, C* < 28.5, the component holding (2190, 870)) and the duvet (per column,
    from the first pixel at L* >= 28 below y 912 that is not the cushion). Measured on fix5 in the window."""
    cand = ((L > 30) & (C < 28.5) & (xx <= 2245) & (yy <= 922) & (yy >= 805)).astype(np.uint8)
    _, lab_, _, _ = cv2.connectedComponentsWithStats(cand, connectivity=4)
    cush = lab_ == lab_[870 - WIN[1], 2190 - WIN[0]]
    duv = np.zeros_like(cush)
    for x in range(L.shape[1]):
        col = (L[:, x] >= 28) & (yy[:, x] >= 912) & ~cush[:, x]
        if col.any():
            duv[np.argmax(col):, x] = True
    return cush, duv & ~cush


def shadow_core(fr, gamma):
    x0, y0, x1, y1 = WIN
    cr = fr[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    lin = T.s2l(cr / 255.0)
    Y = lin @ T.WY
    L = T.Lstar(Y)
    lb = T.lab_lin(lin)
    C = np.hypot(lb[..., 1], lb[..., 2])
    cush, duv = masks(L, C, yy, xx)
    qa_lum = (np.asarray(Image.open(QA_LUMBAR)) > 127)[y0:y1, x0:x1]
    cush_all = cush | qa_lum                                    # QA's own lumbar mask is protected as well
    dom = ~cush_all & ~duv & (xx <= 2545)
    g = lambda a: cv2.GaussianBlur(a, (0, 0), 3.0)             # noqa: E731
    m = dom.astype(np.float64)
    den = np.maximum(g(m), 1e-6)
    lY = np.log(np.maximum(Y, 1e-5))
    base = g(lY * m) / den
    # the unshadowed level: quadratic in x on clearly lit pillowcase, refit without anything darker than 0.8 of it
    fit = dom & (((yy >= 790) & (yy <= 812) & (xx >= 2213) & (xx <= 2520)) | ((xx >= 2480) & (xx <= 2520) & (yy > 812) & (yy <= 912)))
    u = (xx - 2380) / 170.0
    Fm = np.stack([np.ones_like(u), u, u * u], -1)
    keep = fit.copy()
    for _ in range(4):
        coef, *_ = np.linalg.lstsq(Fm[keep], base[keep], rcond=None)
        trend = Fm @ coef
        keep = fit & ((base - trend) > np.log(0.8))
    D = np.clip(trend - base, 0, None)
    t = D - D0
    Deff = np.where(t > KNEE, t, np.where(t < -KNEE, 0, (t + KNEE) ** 2 / (4 * KNEE)))
    dc = cv2.distanceTransform((~cush_all).astype(np.uint8), cv2.DIST_L2, 5)
    dd = cv2.distanceTransform((~duv).astype(np.uint8), cv2.DIST_L2, 5)
    win = dom * T.smoothstep(806, 816, yy) * (1 - T.smoothstep(2490, 2510, xx))
    w_lift = win * T.smoothstep(3, 12, dc) * T.smoothstep(3, 10, dd)        # the contact lines keep their L*
    w_col = win * T.smoothstep(1.5, 3.5, dc) * T.smoothstep(1.5, 3.5, dd)   # ... and take the hue (not the edge pixels)
    lift = w_lift * (1 - gamma) * Deff
    lift_u = w_col * (1 - gamma) * Deff
    Ln = T.Lstar(Y * np.exp(lift))
    Lb = T.Lstar(np.exp(base))
    Lb2 = T.Lstar(np.exp(base + lift))
    Lb2u = T.Lstar(np.exp(base + lift_u))
    a_s, b_s = g(lb[..., 1] * m) / den, g(lb[..., 2] * m) / den
    # the caramel shadow's own chroma against L* (this pillowcase, this frame)
    sh = dom & (xx >= 2216) & (yy >= 815) & (yy <= 922) & (xx <= 2540)
    xs, ys = [], []
    for lo, hi in [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 12), (12, 14), (14, 17), (17, 20), (20, 25), (25, 32), (32, 40)]:
        mm = sh & (L >= lo) & (L < hi)
        if mm.sum() > 50:
            xs.append(float(np.median(L[mm])))
            ys.append(float(np.median(C[mm])))
    Cref = lambda q: np.interp(q, xs, ys)                       # noqa: E731
    rho = np.clip(np.hypot(a_s, b_s) / np.maximum(Cref(Lb), 1e-3), 0.6, 1.4)
    CT = Cref(Lb2) * rho
    aT, bT = CT * np.cos(np.radians(H_T)), CT * np.sin(np.radians(H_T))
    lam = np.clip((Lb2u - Lb) / 3.0, 0, 1)
    a_n = lb[..., 1] + lam * (aT - a_s)
    b_n = lb[..., 2] + lam * (bT - b_s)
    new = T.lin_from_lab(np.stack([Ln, a_n, b_n], -1))
    out = (np.clip(T.l2s(new), 0, 1) * 255 + 0.5).astype(np.uint8)
    chg = (lift > 1e-4) | (lam > 1e-4)
    out = np.where(chg[..., None], out, cr)
    full = fr.copy()
    full[y0:y1, x0:x1] = out
    region = np.zeros(fr.shape[:2], bool)
    region[y0:y1, x0:x1] = chg
    info = dict(gamma=round(float(gamma), 4), trend_coef_logY=[round(float(c), 5) for c in coef],
                trend_L_at={f"x{x}": round(float(T.Lstar(np.exp(coef[0] + coef[1] * ((x - 2380) / 170) + coef[2] * ((x - 2380) / 170) ** 2))), 1)
                            for x in (2220, 2280, 2340, 2400, 2460, 2520)},
                chroma_vs_L=[[round(a, 1), round(b, 1)] for a, b in zip(xs, ys)],
                max_lift_L_base=round(float((Lb2 - Lb).max()), 2))
    contact = np.zeros(fr.shape[:2], bool)                      # the contact line: 1.5-3 px off the cushion, rows 830-915, off the duvet
    contact[y0:y1, x0:x1] = (dc >= 1.5) & (dc <= 3.0) & (yy >= 830) & (yy <= 915) & (dd > 3) & (xx >= 2205)
    under = np.zeros(fr.shape[:2], bool)                        # the duvet below the pillowcase's base (per column, frame px)
    under[y0:y1, x0:x1] = duv
    cushion = np.zeros(fr.shape[:2], bool)
    cushion[y0:y1, x0:x1] = cush
    info["_masks"] = dict(contact=contact, duvet=under, cushion=cushion)
    return full, region, info


def box_median(fr, box=BOX):
    x0, y0, x1, y1 = box
    return float(np.median(T.L_of(fr[y0:y1, x0:x1])))


def shadow_hue(fr, region):
    """median a*, b* of the shadow pixels (L* < 20) in the designer's box, as a hue angle; and inside (b)'s region"""
    lb = T.lab(fr)
    out = {}
    x0, y0, x1, y1 = BOX
    boxm = np.zeros(fr.shape[:2], bool)
    boxm[y0:y1, x0:x1] = True
    for k, m in (("box_L_lt_20", boxm & (lb[..., 0] < 20)), ("b_region_L_lt_20", region & (lb[..., 0] < 20))):
        a, b = np.median(lb[..., 1][m]), np.median(lb[..., 2][m])
        out[k] = dict(L=round(float(np.median(lb[..., 0][m])), 1), C=round(float(np.hypot(a, b)), 1),
                      h=round(float(np.degrees(np.arctan2(b, a))), 1), px=int(m.sum()))
    return out


def solve(fr):
    """GAMMA so that the finished frame's box median lands on FINAL_MEDIAN_TARGET; the toe is solved on (b)'s result"""
    s0 = T.solve_s0(fr)
    for _ in range(3):
        f_inv = lambda target: _inv(lambda v: float(T.curve(v, s0)), target)   # noqa: E731
        want = f_inv(FINAL_MEDIAN_TARGET)
        lo, hi = 0.3, 1.0
        for _ in range(25):
            gm = (lo + hi) / 2
            med = box_median(shadow_core(fr, gm)[0])
            if abs(med - want) < 0.02:
                break
            if med > want:
                lo = gm
            else:
                hi = gm
        b_fr, region, info = shadow_core(fr, gm)
        s0 = T.solve_s0(b_fr)
        fin, tinfo = T.apply(b_fr, s0)
        if abs(box_median(fin) - FINAL_MEDIAN_TARGET) < 0.1:
            break
    return gm, s0, b_fr, region, info, fin, tinfo


PATCHES = {   # frame px (x0, y0, x1, y1), L* limit: the product reads for G-ED.3 spot checks (the same pixels before and after)
    "muslin throw, deep folds (L* < 25)": ((1820, 1230, 2300, 1470), 25.0),
    "muslin throw, whole foot of the bed (L* < 25)": ((940, 1140, 2736, 1536), 25.0),
    "walnut nightstand, drawer fronts (L* < 40)": ((1000, 960, 1320, 1200), 40.0),
    "the void under the nightstand (L* < 12)": ((990, 1230, 1300, 1280), 12.0),
}


def product_reads(before, after):
    out = {}
    for name, (box, lmax) in PATCHES.items():
        x0, y0, x1, y1 = box
        lb0 = T.lab(before[y0:y1, x0:x1]).reshape(-1, 3)
        lb1 = T.lab(after[y0:y1, x0:x1]).reshape(-1, 3)
        m = lb0[:, 0] < lmax
        r = {}
        for k, lb in (("fix5", lb0), ("fix6", lb1)):
            a, b = np.median(lb[m, 1]), np.median(lb[m, 2])
            r[k] = dict(L=round(float(np.median(lb[m, 0])), 1), C=round(float(np.hypot(a, b)), 1),
                        h=round(float(np.degrees(np.arctan2(b, a))), 1), p5_L=round(float(np.percentile(lb[m, 0], 5)), 1))
        r["px"], r["box"] = int(m.sum()), list(box)
        out[name] = r
    return out


def _inv(f, target, lo=0.0, hi=40.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    fr = load(BASE)
    gm, s0, b_fr, region, binfo, fin, tinfo = solve(fr)
    mk = binfo.pop("_masks")
    Image.fromarray(fin).save(os.path.join(HERE, OUT))
    Image.fromarray((region * 255).astype(np.uint8)).save(os.path.join(HERE, REGION_PNG))

    Lfr = T.L_of(fr)
    d_b = np.abs(b_fr.astype(int) - fr.astype(int)).max(2)
    d_all = np.abs(fin.astype(int) - fr.astype(int)).max(2)
    ys, xs = np.nonzero(d_b)
    qa_lum = np.asarray(Image.open(QA_LUMBAR)) > 127
    x0, y0, x1, y1 = BOX
    boxm = np.zeros(fr.shape[:2], bool)
    boxm[y0:y1, x0:x1] = True
    toe_chk = T.checks(b_fr, fin)
    rec = dict(
        date="2026-11-11", by="render-agent", pass_id="MB1 fix8 (0 tokens, code only)", frame="warm_modern",
        source="docs/master-bedroom-comparison-2026-11-07.md §6 (designer's eye on fix5: polish (b) and Q-ED7 (a)); "
               "qa/reports/2026-11-10-ged-master-wm-fix5.md (+ .json)",
        note="TEST, not for the site; new files only; fix5 and every approved file untouched; no var2, no tokens. "
             "Awaiting qa-agent: G-ED.8 / G-ED.9 in (b)'s region, the box median, G-ED.11 (p1, p5, split flag), G-ED.8 for the toe",
        base="warm-modern/warm-modern-MB-A-fix5.png", out=OUT, tokens=0,
        script="mb1_fix8.py", toe_module="q_ed7_toe.py (shared with ../../editorial-phase-b-2026-11-06/codefix_ed9.py)",
        b_cast_shadow_core=dict(
            method="base/detail on logY (Gaussian sigma 3 over the pillowcase only); the shadow's depth below the pillowcase's unshadowed "
                   "level (quadratic-in-x fit on lit pillowcase) scaled by gamma beyond a soft threshold (A < 0.8); the creases are the "
                   "detail layer, untouched; contact lines kept (3 px, ramps to 12 / 10 px); colour: the caramel shadow's own C* at the "
                   "new level and hue 55.5; no pixel from fix4",
            gamma=binfo["gamma"], designer_box=list(BOX), qa_area=list(QA_AREA),
            region_png=REGION_PNG, region_bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
            px_changed=int((d_b > 0).sum()), px_changed_gt2=int((d_b > 2).sum()), max_abs_change_8bit=int(d_b.max()),
            px_changed_outside_region=int(((d_b > 0) & ~region).sum()),
            px_changed_outside_designer_box=int(((d_b > 0) & ~boxm).sum()),
            px_changed_at_L_ge_20=int(((d_b > 0) & (Lfr >= 20)).sum()),
            px_changed_gt2_at_L_ge_20=int(((d_b > 2) & (Lfr >= 20)).sum()),
            px_changed_in_qa_lumbar_mask=int(((d_b > 0) & qa_lum).sum()),
            box_median_L={"fix5": round(box_median(fr), 2), "after_b": round(box_median(b_fr), 2), "fix6": round(box_median(fin), 2)},
            box_mean_L={"fix5": round(float(T.L_of(fr[y0:y1, x0:x1]).mean()), 2), "fix6": round(float(T.L_of(fin[y0:y1, x0:x1]).mean()), 2)},
            slit_median_L={"fix5": round(box_median(fr, SLIT), 2), "fix6": round(box_median(fin, SLIT), 2), "box": list(SLIT)},
            qa_area_median_L={"fix5": round(box_median(fr, QA_AREA), 2), "fix6": round(box_median(fin, QA_AREA), 2)},
            hue={"fix5": shadow_hue(fr, region), "fix6": shadow_hue(fin, region), "lit_caramel_h": 56.5, "window": [53.5, 59.5]},
            px_changed_in_cushion_mask=int(((d_b > 0) & mk["cushion"]).sum()),
            px_changed_in_duvet_below_the_base=int(((d_b > 0) & mk["duvet"]).sum()),
            contact_line_median_L={"fix5": round(float(np.median(Lfr[mk["contact"]])), 2),
                                   "after_b": round(float(np.median(T.L_of(b_fr)[mk["contact"]])), 2),
                                   "fix6": round(float(np.median(T.L_of(fin)[mk["contact"]])), 2),
                                   "px": int(mk["contact"].sum()),
                                   "read": "1.5-3 px off the cushion's right edge, y 830-915: (b) leaves its L* as it was; the toe lifts it like every dark"},
            fit=binfo,
            deviation=f"region follows the shadow (bbox x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}), not QA's x 2215-2330, y 840-925: "
                      "the shadow runs past x 2330 in its lower half (L* < 14 to x 2440 at y 900-918) and starts at y 822; cut at the box "
                      "(tried first) it left a 4-5 L* step at x 2330 (y 880-915) and a dark cap above y 840, the wedge read as a lit "
                      "rectangle. Only the right caramel pillowcase changes; the cushion (QA's lumbar mask and the colour mask) and the "
                      "duvet below the base: 0 px",
        ),
        toe=dict(
            curve="q_ed7_toe.curve: slope s0 below L* 12, smoothstep blend of the slope to 1 at 20, identity from 20; lift (1 - s0)(16 - L) below 12",
            s0=round(float(s0), 4), lift_by_L=T.lift_table(s0), chromaticity_own_from_L=T.REL_HI, chromaticity_local_below_L=T.REL_LO, local_sigma_px=T.SIGMA_LOC, local_source_L=list(T.REL_SRC), local_cover_k=T.COVER_K, fallback_srgb="#2E2824 (Bible espresso)", info=tinfo,
            gate_percentiles={"fix5": T.gate_percentiles(fr), "after_b": T.gate_percentiles(b_fr), "fix6": T.gate_percentiles(fin)},
            full_res_percentiles={"fix5": T.full_percentiles(fr), "fix6": T.full_percentiles(fin)},
            checks_toe_step=toe_chk,
            p1_target=[8.5, 9.5], p5_rise_max=3,
        ),
        whole_pass=dict(
            px_changed=int((d_all > 0).sum()),
            px_changed_at_L_ge_20_fix5=int(((d_all > 0) & (Lfr >= 20)).sum()),
            px_changed_at_L_ge_20_fix5_outside_b_region=int(((d_all > 0) & (Lfr >= 20) & ~region).sum()),
            px_changed_gt2_at_L_ge_20_fix5_outside_b_region=int(((d_all > 2) & (Lfr >= 20) & ~region).sum()),
        ),
    )
    rec["product_reads"] = product_reads(fr, fin)
    rec["gate_guardrails_py"] = T.gate_guardrails([os.path.join(HERE, BASE), os.path.join(HERE, OUT)])
    gb, gf = rec["toe"]["gate_percentiles"]["fix5"], rec["toe"]["gate_percentiles"]["fix6"]
    rec["toe"]["p5_rise"] = round(gf["p5"] - gb["p5"], 2)
    rec["toe"]["p1_rise"] = round(gf["p1"] - gb["p1"], 2)

    os.makedirs(CROPS, exist_ok=True)
    crops = []
    spec = [
        ("pillowcase-shadow-100.jpg", (2130, 770, 2560, 960), 1, "lumbar cast shadow, right caramel pillowcase", 1.0),
        ("pillowcase-shadow-x4.jpg", (2205, 815, 2325, 925), 4, "lumbar cast shadow, core", 1.0),
        ("pillowcase-shadow-x4-stretch.jpg", (2205, 815, 2345, 925), 4, "lumbar cast shadow, core", 2.6),
        ("muslin-throw-100.jpg", (1820, 1230, 2300, 1470), 1, "muslin throw, deep folds", 1.0),
        ("muslin-throw-x4.jpg", (1990, 1320, 2110, 1390), 4, "muslin throw, deepest fold", 1.0),
        ("walnut-nightstand-100.jpg", (960, 900, 1400, 1290), 1, "walnut nightstand and the void under it", 1.0),
        ("walnut-nightstand-x4.jpg", (1100, 1150, 1220, 1230), 4, "walnut nightstand, drawer and base", 1.0),
    ]
    for name, box, sc, title, st in spec:
        T.crop_pair(fr, fin, box, sc, "warm-modern-MB-A fix5 | fix6 · " + title, os.path.join(CROPS, name), stretch=st)
        crops.append("fix8-before-after/" + name)
    rec["crops"] = crops
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: rec[k] for k in ("b_cast_shadow_core", "toe", "whole_pass")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
