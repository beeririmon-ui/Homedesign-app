#!/usr/bin/env python3
"""
fix_r5.py: the 0-token colour fixes before passes 4' / 5' of the warm-modern living-room tool, phase 2 (render-agent, 2026-11-11).
Brief: briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md section 0; the designer: docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md
sections 3 (the curtains) and 4 (the magazine holder's thin rods). Code only: 0 tokens, no var2, no network. NEW FILES ONLY: work-r5/
(ungraded per-product layers and shadows, the same form as work-r4/) and work-r5/fix-r5.json; grade_cut_r5.py grades and cuts them with the
ONE v3c grade, like every earlier layer.

  curtains  a* and b* only, toward the card's cream (the photo: C 6.5, h 93; the layer today C 15.1, h 75): ONE hue rotation dh and ONE
            chroma factor k for every pixel of the layer (the slub keeps its differences; the part in front of the glazing takes the same
            factor), L* untouched, iterated on the graded set-B scene with QA's masks (p2_colour.py: the layer's alpha 255 eroded 2 px, rows
            100-1400; the plaster ring 15-40 px out) to the designer's targets: median h 85-95, median C* 5.5-7.5 and >= the plaster's + 0.5,
            p95 C* <= 11, median L* within +-0.5, the high-pass L* std within +-5 %.
            In the same cut, the armchair's walnut post (QA section 4): where the post's soft edge stands in front of the curtain, the
            furniture's edge colour was solved in phase 1 against the bright wall and reads as a 1 px light line over the darker curtain;
            the curtain's colour under that edge is set so the pixel shows the post's own dark colour (from its opaque core next to it)
            over the curtain: behind' = behind + (F_core - F) x fa / (1 - fa), clipped; only where 0.02 < fa < 0.98 and the curtain is behind.
  rods      the magazine holder's two thin strap rods to the SKU photo's satin silver (the photo, measured across the free rod spans:
            L* median 56, C* 2.5, a highlight band along the upper side, a darker lower edge): each rod a fitted straight line, its pixels
            (alpha > 0, within its half width, never the tubes it crosses, never the leather), recoloured to a satin cylinder profile across
            the rod at the photo's median L* and C*, one soft highlight, no environment reflection; the glossy black tubes are unchanged
            (the designer's documented exception, pending WM-M1).

  python3 fix_r5.py all     (or: curtains | rods)
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract as X  # noqa: E402
import phase2_wm as W  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR5 = os.path.join(HERE, "work-r5")
SIZE = W.SIZE
REC = os.path.join(WR5, "fix-r5.json")
SCR = X.SCR
U_CACHE = os.path.join(SCR, "r5", "U_r4_B.npy")
WRES = os.path.join(HERE, "work-reserve")


def rel(p):
    return os.path.relpath(p, W.REPO)


def f32(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


def lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_of(L, A, B):
    return np.clip(cv2.cvtColor(np.dstack([L, A, B]).astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def record(key, val):
    os.makedirs(WR5, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-11", author="render-agent", tokens=0, brief="briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md section 0",
        sources=dict(designer="docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md sections 3-4", qa="qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md"),
        note="ungraded per-product layers (RGBA, straight alpha) and shadows (grey RGB, multiply); grade_cut_r5.py grades and cuts them")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False)


def save_layer(name, rgb, a):
    os.makedirs(os.path.join(WR5, "layers"), exist_ok=True)
    p = os.path.join(WR5, "layers", f"{name}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, np.clip(rgb, 0, 1).astype(np.float32), alpha=np.clip(a, 0, 1).astype(np.float32))
    return p


def copy_to(src, sub, name):
    dst = os.path.join(WR5, sub, name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    assert not os.path.exists(dst) or os.environ.get("REDO"), dst
    shutil.copyfile(src, dst)
    return dst


def scene_r4_B():
    """the ungraded r4 composite with set B (grade_cut_r4's sources), cached in the scratchpad"""
    if os.path.exists(U_CACHE):
        return np.load(U_CACHE).astype(np.float32)
    import grade_cut_r4 as G4  # noqa: F401  (sets the r4 sources)
    import grade_cut_r12 as G12
    import stack
    U, _ = G12.compose(set(G4.ACCEPTED) | {"cushions"}, stack.base_parts(), cushion_set="B")
    os.makedirs(os.path.dirname(U_CACHE), exist_ok=True)
    np.save(U_CACHE, U.astype(np.float32))
    return U.astype(np.float32)


def products_alpha_r4():
    """the max alpha of every r4 product layer and set B (the grade's slab weight, as grade_cut's Aun)"""
    man = json.load(open(os.path.join(HERE, "layers/manifest-r4.json")))
    A = np.zeros(SIZE[::-1], np.float32)
    for l_ in man["layers"]:
        if "product" in l_:
            A = np.maximum(A, f32(os.path.join(HERE, "layers", l_["file"]))[..., 3])
    A = np.maximum(A, f32(os.path.join(HERE, "layers", man["slot_cushions"]["sets"]["B"]["layer"]))[..., 3])
    return A


# ================================================================================================= curtains
CUR_FILE_R4 = "curtains/curtains-aliexpress-beige-linen-sheer-curtains-554205.png"


def qa_curtain_masks():
    """QA's p2_colour.py: the layer's alpha 255 eroded 5x5, rows 100-1400; the plaster ring 15-40 px out from that mask"""
    a8 = np.asarray(Image.open(os.path.join(HERE, "layers", CUR_FILE_R4)))[..., 3]
    m = cv2.erode((a8 == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    r = np.zeros_like(m)
    r[100:1400] = True
    m &= r
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    ring = (d >= 15) & (d <= 40)
    return m, ring


def curtain_measure(G8, m, ring):
    LAB = lab(G8.astype(np.float32) / 255)
    L, A, B = LAB[..., 0], LAB[..., 1], LAB[..., 2]
    C = np.hypot(A, B)
    am, bm = float(np.median(A[m])), float(np.median(B[m]))
    hp = L - cv2.GaussianBlur(L, (0, 0), 3)
    wa, wb = float(np.median(A[ring])), float(np.median(B[ring]))
    return dict(L=round(float(np.median(L[m])), 2), a=round(am, 2), b=round(bm, 2), C=round(float(np.hypot(am, bm)), 2),
                h=round(float(np.degrees(np.arctan2(bm, am)) % 360), 2), C_px_median=round(float(np.median(C[m])), 2),
                C_px_p95=round(float(np.percentile(C[m], 95)), 2), highpass_std=round(float(hp[m].std()), 3),
                plaster_ring=dict(L=round(float(np.median(L[ring])), 2), C=round(float(np.hypot(wa, wb)), 2),
                                  h=round(float(np.degrees(np.arctan2(wb, wa)) % 360), 2)), px=int(m.sum()))


def recolour_ab(rgb, dh_deg, k):
    """one hue rotation and one chroma factor on a*b*, L* untouched"""
    Lw = lab(rgb)
    c, s = np.cos(np.radians(dh_deg)), np.sin(np.radians(dh_deg))
    A = k * (c * Lw[..., 1] - s * Lw[..., 2])
    B = k * (s * Lw[..., 1] + c * Lw[..., 2])
    return rgb_of(Lw[..., 0], A, B)


def post_line_fix(rgb_c, a_free, fa, F):
    """the curtain's colour under the furniture's soft edge, so the edge shows the furniture's own core colour over the curtain"""
    core = fa >= 0.98
    # the post's own colour at each fringe pixel: its nearest opaque core pixel (the furniture's soft tail runs 2-6 px), lightly smoothed
    # along the core (normalised blur sigma 1.5 over the core) so the grain of one pixel does not print
    Fs, _ = X_nblur(F, core.astype(np.float32), 1.5)
    _, lab_ = cv2.distanceTransformWithLabels((~core).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(core)
    lut = np.zeros((lab_.max() + 1, 2), np.int32)
    zl = lab_[ys, xs]
    lut[zl, 0], lut[zl, 1] = ys, xs
    Fc = Fs[lut[lab_, 0], lut[lab_, 1]]
    dist = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    fringe = (fa > 0.02) & (fa < 0.98) & (a_free > 0.02) & (dist <= 8)
    # the curtain itself next to the edge: its colour from the pixels the furniture leaves clear (no light seam from the cut)
    clear = ((fa <= 0.02) & (a_free > 0.5)).astype(np.float32)
    Cc, denc = X_nblur(rgb_c, clear, 2.0)
    base = np.where(((denc > 0.05) & fringe)[..., None], Cc, rgb_c)
    k = np.where(fringe, fa / np.maximum(1 - fa, 0.02) / np.maximum(a_free, 0.02), 0.0)
    out = np.clip(base + (Fc - F) * k[..., None], 0, 1)
    out = np.where(fringe[..., None], out, rgb_c)
    return out.astype(np.float32), fringe


def X_nblur(x, w, s):
    den = cv2.GaussianBlur(w, (0, 0), s)
    if x.ndim == 3:
        return cv2.GaussianBlur(x * w[..., None], (0, 0), s) / np.maximum(den, 1e-6)[..., None], den
    return cv2.GaussianBlur(x * w, (0, 0), s) / np.maximum(den, 1e-6), den


def curtains():
    import stack
    Lw = f32(os.path.join(WRES, "layers", "curtains.png"))
    rgb_w, a_in = Lw[..., :3], Lw[..., 3]
    a_free = f32(os.path.join(WRES, "layers", "curtains-free-alpha.png"), "L")
    P = stack.base_parts()
    fa, F = P["fa"], P["F"]
    U = scene_r4_B()
    Gr = stack.Grade()
    vis = (a_free * (1 - fa))[..., None]
    m, ring = qa_curtain_masks()
    G0 = np.asarray(Image.open(os.path.join(HERE, "graded/default-scene-r4-set-B-graded-v3c.png")).convert("RGB"))
    A_all = products_alpha_r4()
    reg = (a_free > 0) | X.dil((fa > 0.02) & (a_free > 0.02), 2)
    G0c = Gr(U, A_all)
    dmax = int(np.abs(G0c.astype(int) - G0.astype(int)).max(2)[reg].max())
    assert dmax <= 1, f"the cached r4 composite does not reproduce the r4 scene in the curtain's region ({dmax}): stop"
    Gr_ = Gr
    Gr = lambda U_: np.where(reg[..., None], Gr_(U_, A_all), G0)  # noqa: E731
    before = curtain_measure(G0, m, ring)
    # targets: h 90 (85-95), C 6.5 (5.5-7.5), >= plaster + 0.5
    want_h, want_C = 90.0, 6.5
    dh, k = want_h - before["h"], want_C / before["C"]
    hist = []
    for it in range(8):
        rgb_n = recolour_ab(rgb_w, dh, k)
        Gn = Gr(U + (rgb_n - rgb_w) * vis)
        mm = curtain_measure(Gn, m, ring)
        hist.append(dict(it=it, dh=round(dh, 3), k=round(k, 4), h=mm["h"], C=mm["C"], C_p95=mm["C_px_p95"], L=mm["L"]))
        eh, eC = want_h - mm["h"], want_C - mm["C"]
        if abs(eh) < 0.3 and abs(eC) < 0.05:
            break
        dh += eh
        k *= want_C / max(mm["C"], 1e-3)
    rgb_n = recolour_ab(rgb_w, dh, k)
    # the post's light line, in the same cut (the curtain's colour under the furniture's soft edge)
    rgb_f, fringe = post_line_fix(rgb_n, a_free, fa, F)
    Gf = Gr(U + (rgb_f - rgb_w) * vis)
    after = curtain_measure(Gf, m, ring)
    tg = {"1a L* median within +-0.5": dict(value=round(after["L"] - before["L"], 2), pass_=abs(after["L"] - before["L"]) <= 0.5),
          "1b high-pass L* std within +-5 %": dict(value=round(after["highpass_std"] / before["highpass_std"] - 1, 4),
                                                    pass_=abs(after["highpass_std"] / before["highpass_std"] - 1) <= 0.05),
          "2 median h 85-95": dict(value=after["h"], pass_=85 <= after["h"] <= 95),
          "3a median C* 5.5-7.5": dict(value=after["C"], pass_=5.5 <= after["C"] <= 7.5),
          "3b one factor k for every pixel": dict(value=round(k, 4), pass_=True),
          "3c p95 C* <= 11": dict(value=after["C_px_p95"], pass_=after["C_px_p95"] <= 11),
          "4 >= plaster C + 0.5": dict(value=round(after["C"] - after["plaster_ring"]["C"], 2), pass_=after["C"] >= after["plaster_ring"]["C"] + 0.5)}
    # the light line: the fringe's L* against its two sides (curtain clear of the post 3-6 px out; the post's core), before / after
    LG0, LGf = lab(G0.astype(np.float32) / 255)[..., 0], lab(Gf.astype(np.float32) / 255)[..., 0]
    near = fringe & (fa < 0.5)
    line = dict(fringe_px=int(fringe.sum()),
                fringe_fa_lt_0_5_L_median=dict(before=round(float(np.median(LG0[near])), 2), after=round(float(np.median(LGf[near])), 2)),
                fringe_px_lighter_than_the_curtain_beside=dict(before=None, after=None))
    curt_beside, _ = X_nblur(LG0, (((fa <= 0.02) & (a_free > 0.5)) & ~X.dil(fa > 0.02, 2)).astype(np.float32), 4.0)
    curt_besidef, _ = X_nblur(LGf, (((fa <= 0.02) & (a_free > 0.5)) & ~X.dil(fa > 0.02, 2)).astype(np.float32), 4.0)
    line["fringe_px_lighter_than_the_curtain_beside"] = dict(before=int((near & (LG0 > curt_beside + 1.5)).sum()),
                                                             after=int((near & (LGf > curt_besidef + 1.5)).sum()))
    pl = save_layer("curtains", rgb_f, a_in)
    copy_to(os.path.join(WRES, "layers", "curtains-free-alpha.png"), "layers", "curtains-free-alpha.png")
    copy_to(os.path.join(WRES, "shadows", "curtains.png"), "shadows", "curtains.png")
    changed = np.abs(f32(pl)[..., :3] - rgb_w).max(2) > 0
    record("curtains", dict(
        what="a* and b* only toward the card's cream (designer section 3), one hue rotation and one chroma factor for every pixel; the "
             "armchair post's light line (QA section 4) closed in the same cut",
        source=dict(layer=rel(os.path.join(WRES, "layers", "curtains.png")), free_alpha=rel(os.path.join(WRES, "layers", "curtains-free-alpha.png")),
                    shadow=rel(os.path.join(WRES, "shadows", "curtains.png")) + " (unchanged, copied)"),
        method=dict(recolour="Lab of the ungraded layer: (a, b) -> k R(dh) (a, b), L* unchanged; dh, k iterated on the graded set-B r4 scene",
                    dh_deg=round(dh, 3), k=round(k, 4), iterations=hist,
                    post_line="where 0.02 < fa < 0.98 and the curtain is behind: the curtain's own colour from its clear pixels beside the edge "
                              "(normalised blur, sigma 2), plus (F_core - F) x fa / ((1 - fa) a), F_core the furniture's opaque core next to the "
                              "edge (normalised blur, sigma 2); clipped to 0-1",
                    masks="QA p2_colour.py: alpha 255 eroded 5x5, rows 100-1400 (%d px); plaster ring 15-40 px" % m.sum()),
        before=before, after=after, targets=tg, all_met=all(v["pass_"] for v in tg.values()), post_line=line,
        changed_px=int(changed.sum()), changed_outside_alpha_px=int((changed & (a_in <= 0)).sum()),
        photo=dict(file="curtains/img1.jpg (scratchpad, never in the repo)", L=86.9, C=6.5, h=93.0, source="QA data/colour.json"),
        note="measured on the graded set-B scene recomposed with the change (the r4 stack); grade_cut_r5.py re-measures on the r5 scene"))
    print(json.dumps(dict(dh=dh, k=k, before={x: before[x] for x in ("L", "C", "h", "C_px_p95", "highpass_std")},
                          after={x: after[x] for x in ("L", "C", "h", "C_px_p95", "highpass_std", "plaster_ring")}, targets=tg, post_line=line), indent=1))


# ================================================================================================= rods
MH_LAYER = os.path.join(WRES, "layers", "magazine-holder.png")
ROD_TARGET = dict(L_median=56.0, C=2.5, h_deg=54.0, source="the Orange SKU photo, 66 columns across the free rod spans (scratchpad)")
# the two rods, read on the r3 layer at x3 (the back rod through the strap tops, the front rod lower and nearer); fitted below
ROD_SEEDS = {"back": [(1016, 1447), (1190, 1478)], "front": [(947, 1487), (1147, 1525)]}


def rod_masks(rgb, a):
    """each rod as a fitted line: dark neutral pixels within 10 px of the seed line, least squares; the rod = alpha > 0 within the half
    width of the fitted line, never the tubes (dark pixels farther than the half width + 2 from the line, closed vertically across the
    rod band) and never the leather (C* > 14)"""
    Lw = lab(rgb)
    C = np.hypot(Lw[..., 1], Lw[..., 2])
    dark = (a > 0.3) & (Lw[..., 0] < 34) & (C < 12)
    H, Wd = a.shape
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    out, info = {}, {}
    alln = np.zeros(a.shape, bool)
    for name, ((x0, y0), (x1, y1)) in ROD_SEEDS.items():
        d0 = np.abs((y1 - y0) * xx - (x1 - x0) * yy + x1 * y0 - y1 * x0) / np.hypot(y1 - y0, x1 - x0)
        sel = dark & (d0 <= 10) & (xx >= x0 - 4) & (xx <= x1 + 4)
        ys, xs = np.nonzero(sel)
        # robust line fit: two rounds, dropping points > 4 px off
        p = np.polyfit(xs, ys, 1)
        for _ in range(2):
            r = np.abs(ys - np.polyval(p, xs))
            keep = r < 4
            p = np.polyfit(xs[keep], ys[keep], 1)
        dist = (yy - np.polyval(p, xx)) / np.sqrt(1 + p[0] ** 2)         # signed: negative above the line
        r = np.abs(ys - np.polyval(p, xs))
        hw = float(np.percentile(r[r < 6], 90)) + 0.5
        near = (np.abs(dist) <= hw + 1.5) & (xx >= x0 - 6) & (xx <= x1 + 6)
        tube = dark & (np.abs(dist) > hw + 2)
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(2 * hw + 9)))
        tube = cv2.morphologyEx(tube.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
        tube = X.dil(tube, 1)
        rod = near & (a > 0.02) & ~tube & (C <= 14)
        out[name] = dict(mask=rod, t=np.clip(dist / max(hw, 1.0), -1.5, 1.5), hw=hw)
        alln |= rod
        info[name] = dict(line_y_eq_ax_plus_b=[round(float(p[0]), 5), round(float(p[1]), 2)], half_width_px=round(hw, 2), px=int(rod.sum()),
                          x_span=[int(np.nonzero(rod.any(0))[0].min()), int(np.nonzero(rod.any(0))[0].max())] if rod.any() else None)
    return out, info


def satin_profile(t):
    """L* across a satin metal cylinder lit from above-left by the soft window: a soft highlight band on the upper third, mid grey, a
    darker lower edge; scaled so the rod's median is the photo's 56"""
    hl = 26.0 * np.exp(-((t + 0.35) / 0.30) ** 2)
    body = 52.0 - 16.0 * np.clip(t, -1, 1.2)
    return body + hl


def rods():
    import stack
    Lw = f32(MH_LAYER)
    rgb, a = Lw[..., :3], Lw[..., 3]
    M, info = rod_masks(rgb, a)
    U = scene_r4_B()
    A_all = products_alpha_r4()
    G0 = np.asarray(Image.open(os.path.join(HERE, "graded/default-scene-r4-set-B-graded-v3c.png")).convert("RGB"))
    reg = a > 0
    Gr_ = stack.Grade()
    dmax = int(np.abs(Gr_(U, A_all).astype(int) - G0.astype(int)).max(2)[reg].max())
    assert dmax <= 1, f"the cached r4 composite does not reproduce the r4 scene in the holder's region ({dmax}): stop"
    Gr = lambda U_: np.where(reg[..., None], Gr_(U_, A_all), G0)  # noqa: E731
    out = rgb.copy()
    Lr = lab(rgb)
    gain = 1.0
    rodall = np.zeros(a.shape, bool)
    for name, r in M.items():
        rodall |= r["mask"]
    for it in range(6):
        out = rgb.copy()
        for name, r in M.items():
            m = r["mask"]
            Lt = satin_profile(r["t"]) * gain
            # the render's own light along the rod (its local mean L*, normalised): the shade a strap or the rug's light leaves on it
            loc, _ = X_nblur(Lr[..., 0], m.astype(np.float32), 6.0)
            ref = float(np.median(loc[m])) if m.any() else 1.0
            shade = np.clip(loc / max(ref, 1e-3), 0.85, 1.12) ** 0.5
            Ln = np.clip(Lt * shade, 0, 96)
            ch = np.radians(ROD_TARGET["h_deg"])
            An = np.full(a.shape, ROD_TARGET["C"] * np.cos(ch), np.float32)
            Bn = np.full(a.shape, ROD_TARGET["C"] * np.sin(ch), np.float32)
            new = rgb_of(Ln, An, Bn)
            out = np.where(m[..., None], new, out)
        G = Gr(U + (out - rgb) * a[..., None])
        LG = lab(G.astype(np.float32) / 255)
        core = rodall & (a >= 0.999)
        med = float(np.median(LG[..., 0][core]))
        if abs(med - ROD_TARGET["L_median"]) < 0.3:
            break
        gain *= ROD_TARGET["L_median"] / med
    LG0 = lab(np.asarray(Image.open(os.path.join(HERE, "graded/default-scene-r4-set-B-graded-v3c.png")).convert("RGB")).astype(np.float32) / 255)
    core = rodall & (a >= 0.999)
    meas = lambda LL, m: dict(L_median=round(float(np.median(LL[..., 0][m])), 2), L_p90=round(float(np.percentile(LL[..., 0][m], 90)), 2),  # noqa: E731
                              L_p10=round(float(np.percentile(LL[..., 0][m], 10)), 2),
                              C_median=round(float(np.hypot(np.median(LL[..., 1][m]), np.median(LL[..., 2][m]))), 2))
    before, after = meas(LG0, core), meas(LG, core)
    pl = save_layer("magazine-holder", out, a)
    copy_to(os.path.join(WRES, "shadows", "magazine-holder.png"), "shadows", "magazine-holder.png")
    changed = np.abs(f32(pl)[..., :3] - rgb).max(2) > 0
    frame_pct = 100.0 * rodall[43:1487, 77:2643].sum() / ((1487 - 43) * (2643 - 77))
    record("magazine-holder", dict(
        what="the two thin strap rods to the SKU photo's satin silver (designer section 4); the glossy black tubes unchanged (documented "
             "exception, pending WM-M1)", source=dict(layer=rel(MH_LAYER), shadow=rel(os.path.join(WRES, "shadows", "magazine-holder.png")) + " (unchanged)"),
        rods=info, target=ROD_TARGET, profile="L*(t) = (52 - 16 t + 26 exp(-((t + 0.35) / 0.30)^2)) x gain x the render's own light along the "
                                              "rod (normalised, ^0.5, 0.85-1.12); t = signed distance across the rod / half width (negative = up)",
        gain=round(gain, 4), measured_graded_rod_core=dict(before=before, after=after, px=int(core.sum())),
        rods_frame_pct=round(frame_pct, 3), changed_px=int(changed.sum()), changed_outside_rods_px=int((changed & ~rodall).sum()),
        note="QA measures the target on the r5 scene (the photo: L* median 56, C* 2.5)"))
    print(json.dumps(dict(rods=info, gain=gain, before=before, after=after, frame_pct=round(frame_pct, 3),
                          changed=int(changed.sum()), outside=int((changed & ~rodall).sum())), indent=1))
    vis = (np.asarray(Image.fromarray((np.clip(G, 0, 255)).astype(np.uint8)))).copy()
    Image.fromarray(vis[1380:1530, 900:1240]).resize((1020, 450), Image.LANCZOS).save(os.path.join(SCR, "r5", "rods-after-x3.png"))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("curtains", "all"):
        curtains()
    if what in ("rods", "all"):
        rods()
