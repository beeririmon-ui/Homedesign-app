#!/usr/bin/env python3
"""
fix_r6.py: R6, the 0-token code fixes on the warm-modern tool layers after QA R5 and the designer's eye (render-agent, 2026-11-12).
Brief: briefs/render-wm-tool-r6-codefix-2026-11-12.md. Sources: qa/reports/2026-11-11-wm-tool-phase2-r5.md (+ .json, tools, crops) and
docs/proposals/wm-phase2-r5-eye-2026-11-11.md. Code only: 0 tokens, no var2, no network. NEW FILES ONLY: work-r6/ (ungraded per-product
layers and shadows, the same form as work-r5/) and work-r6/fix-r6.json; grade_cut_r6.py grades and cuts them with the ONE v3c grade.

  curtains    the default is 180502 now (the designer, eye section 1): its R5 files (work-r5/layers/curtains-v2*) are copied byte for byte
              to work-r6/layers/curtains*.png so the stack reads them as the slot's default
  curtains-v2 554205, now variant 2: from its R1 render (work-reserve), relative to 180502 under the same mask (QA p2_colour's mask on
              both layers, intersected), L* included: ONE monotone tone curve on the low-frequency L* (a normalised blur of ~3 fold
              spacings), the high frequencies back x g (1 <= g <= 1.2); then a*b* by R5's method (one hue rotation, one chroma factor);
              then the armchair post's line solved again (fix_r5.post_line_fix); the shadow and the free alpha unchanged
  vase        the default (4'): re-cut from the registered raw render (work-r5/p4-regt.npy): per body row the render's own edges (its
              colour gradient; the lit flank's outermost step into its white band), and, the vase being a solid of revolution, an
              axis line and a smooth half-width profile; its left (lit) flank checked against the mirror
              of its right edge about the axis; straightened (the model drew it leaning 3.9 deg; the camera is level) and its width
              brought to the card (D16) about the foot; R5's a*b* fix re-solved on the whole body (lit half C* 4.5); the contact
              shadow by the frozen recipe (extract.shadow_one) on the final cut
  vase-v2     5': the same re-cut from work-r5/p5-regt.npy; a*b* toward the card's neutral charcoal (designer section 6.1)
  pendant-v2  5': the canopy re-cut whole (fix_r4.canopy_cut, centred on the cord), the right contour snapped to the render's own edge,
              the brown speck on the cord out, the cord black (the card: "black thin cord"), the paper's horizontal rings removed along
              the clay lantern's latitude lines (designer section 4, step 1)
  framed-art-v2  the band / print seam anti-aliased along each rail (one sub-pixel line per rail, the default's inner shadow line kept),
              the isolated light specks in the prints' black out, R5's black lift re-applied
  magazine-holder  the rods' satin profile carried into the rod's soft edge (fa 0.02-0.98): the black left in the pixels where the rod
              meets the leather or the rug is replaced by the silver, by un-mixing

  python3 fix_r6.py all     (or one of: curtains | curtains-v2 | vase | vase-v2 | pendant | art | rods)
"""
import json
import math
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import extract as X  # noqa: E402
import fix_r4 as F4  # noqa: E402
import fix_r5 as F5  # noqa: E402
import grade_cut_r5 as G5  # noqa: E402,F401  (sets the R5 sources in grade_cut_r12.SRC)
import grade_cut_r12 as G12  # noqa: E402
import pass_r5 as R  # noqa: E402
import phase2_wm as W  # noqa: E402
import stack  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR4, WR5, WR6 = os.path.join(HERE, "work-r4"), os.path.join(HERE, "work-r5"), os.path.join(HERE, "work-r6")
WRES = os.path.join(HERE, "work-reserve")
SIZE = W.SIZE
REC = os.path.join(WR6, "fix-r6.json")
SCR = os.path.join(X.SCR, "r6")
D = lambda *p: os.path.join(*p)  # noqa: E731

# ------------------------------------------------------------------------------------------------- the R6 sources
# the defaults: the R5 sources, with the R6 changes (curtains = 180502, the vase re-cut, the rods' soft edge)
SRC5 = dict(G12.SRC)
SRC6 = dict(SRC5)
SRC6.update({"curtains": (D(WR6, "layers"), D(WR6, "shadows")), "vase": (D(WR6, "layers"), D(WR6, "shadows")),
             "magazine-holder": (D(WR6, "layers"), D(WR5, "shadows"))})
# the variants: name -> (layers dir, shadows dir); file <name>.png in each
VSRC6 = {"curtains-v2": (D(WR6, "layers"), D(WR6, "shadows")), "framed-art-v2": (D(WR6, "layers"), D(WR5, "shadows")),
         "accent-sconces-v2": (D(WR5, "layers"), D(WR5, "shadows")), "accent-sconces-v3": (D(WR5, "layers"), D(WR5, "shadows")),
         "vase-v2": (D(WR6, "layers"), D(WR6, "shadows")), "pendant-v2": (D(WR6, "layers"), D(WR5, "shadows"))}
VSLOT = {"curtains-v2": "curtains", "framed-art-v2": "framed-art", "accent-sconces-v2": "accent-sconces", "accent-sconces-v3": "accent-sconces",
         "vase-v2": "vase", "pendant-v2": "pendant"}
CARDS6 = dict(G5.CARDS)
CARDS6["curtains"] = R.CARDS[("curtains", "v2")]                       # 180502, the default from R6
VCARDS6 = {nm: R.CARDS[(VSLOT[nm], nm.split("-")[-1])] for nm in VSRC6 if nm != "curtains-v2"}
VCARDS6["curtains-v2"] = G5.CARDS["curtains"]                          # 554205, variant 2 from R6
ACCEPTED = list(G5.ACCEPTED)


def use_r6_sources():
    """the R6 sources; a slot whose R6 file is not written yet reads its R5 file (the order of the fixes does not matter for the measures:
    the slots' regions are disjoint)"""
    G12.SRC.clear()
    G12.SRC.update({k: (v if os.path.exists(D(v[0], f"{k}.png")) else SRC5[k]) for k, v in SRC6.items()})


def rel(p):
    return os.path.relpath(p, W.REPO)


def f32(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


lab, rgb_of, nblur = F5.lab, F5.rgb_of, F5.X_nblur


def record(key, val):
    os.makedirs(WR6, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-12", author="render-agent", tokens=0, brief="briefs/render-wm-tool-r6-codefix-2026-11-12.md",
        sources=dict(qa="qa/reports/2026-11-11-wm-tool-phase2-r5.md (+ .json)", designer="docs/proposals/wm-phase2-r5-eye-2026-11-11.md"),
        note="ungraded per-product layers (RGBA, straight alpha) and shadows (grey RGB, multiply) in work-r6/; grade_cut_r6.py grades and "
             "cuts them with the ONE v3c grade; the numbers here are measured on graded scenes recomposed with the change (set B)")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def save_layer(name, rgb, a, sub="layers"):
    os.makedirs(D(WR6, sub), exist_ok=True)
    p = D(WR6, sub, f"{name}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, np.clip(rgb, 0, 1).astype(np.float32), alpha=np.clip(a, 0, 1).astype(np.float32))
    return p


def save_shadow(name, sh):
    os.makedirs(D(WR6, "shadows"), exist_ok=True)
    p = D(WR6, "shadows", f"{name}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, np.repeat(np.clip(sh, 0, 1)[..., None], 3, 2).astype(np.float32))
    return p


def save_alpha(name, a):
    p = D(WR6, "layers", f"{name}-free-alpha.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(p)
    return p


def copy_to(src, sub, name):
    dst = D(WR6, sub, name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    assert not os.path.exists(dst) or os.environ.get("REDO"), dst
    shutil.copyfile(src, dst)
    return dst


# ------------------------------------------------------------------------------------------------- composing with the R6 sources
_P = []


def parts():
    if not _P:
        _P.append(stack.base_parts())
    return _P[0]


def compose6(variants=None, items=None, cushion_set="B", override=None):
    """the R6 stack (ACCEPTED + a cushion set) with some slots read from a variant: variants = {slot: name}; override = {slot: (rgb, a,
    a_free or None, sh)} arrays for a slot (a candidate being measured)"""
    variants, override = variants or {}, override or {}
    use_r6_sources()
    orig = G12.product

    def prod(k, s=None):
        if k in override:
            rgb, a, af, sh = override[k]
            return rgb, (af if (k in stack.BEHIND and af is not None) else a), sh
        if k in variants:
            nm = variants[k]
            ld, sd = VSRC6[nm]
            L = stack.f8(D(ld, f"{nm}.png"))
            a = L[..., 3]
            fp = D(ld, f"{nm}-free-alpha.png")
            if k in stack.BEHIND and os.path.exists(fp):
                a = stack.f8(fp, "L")
            return L[..., :3], a, stack.f8(D(sd, f"{nm}.png"), "L")
        return orig(k, s)
    G12.product = prod
    sp = stack.product
    stack.product = prod
    try:
        return stack.compose(set(items or ACCEPTED) | {"cushions"}, parts(), cushion_set=cushion_set, keep_steps=True)
    finally:
        G12.product = orig
        stack.product = sp


_GR = []


def grade():
    if not _GR:
        _GR.append(stack.Grade())
    return _GR[0]


def graded(variants=None, override=None, cushion_set="B"):
    """(U, A_all, G8) of the R6 stack with the given variants / override (the measure scene; A_all = every product's alpha, the slab weight)"""
    U, steps = compose6(variants, cushion_set=cushion_set, override=override)
    A = np.zeros(SIZE[::-1], np.float32)
    for st in steps:
        A = np.maximum(A, st["a_eff"] if st["k"] != "cushions" else st["a"])
    return U, A, grade()(U, A)


def lab8(G8):
    return lab(G8.astype(np.float32) / 255)


# ================================================================================================= vases: the re-cut
VASE_BOX = (850, 1085, 585, 765)          # y0, y1, x0, x1 (QA's box 850-1080 x 590-760, grown)


def _sub_edge(prof, thr, rising):
    """the first sub-pixel crossing of thr in a 1-D profile (rising: from below thr to above)"""
    p = prof
    for i in range(len(p) - 1):
        a_, b_ = p[i], p[i + 1]
        if (rising and a_ < thr <= b_) or (not rising and a_ >= thr > b_):
            return i + (thr - a_) / (b_ - a_)
    return None


def _parab(g, i):
    """sub-pixel peak of g at i (parabola through i - 1, i, i + 1)"""
    if i <= 0 or i >= len(g) - 1:
        return float(i)
    a_, b_, c_ = g[i - 1], g[i], g[i + 1]
    den = a_ - 2 * b_ + c_
    return i + (float(np.clip(0.5 * (a_ - c_) / den, -0.5, 0.5)) if abs(den) > 1e-6 else 0.0)


def vase_recut(regt, a_cut, rim_row, axis0, white=None):
    """the vase's silhouette as the model drew it, row by row on its body (the rim + 3 to the foot's contact): the edges are the
    sub-pixel peaks of the render's own colour gradient (Lab, sigma-0.6 blur; central differences): the right edge within 8 px inside /
    3 px outside the old cut's (QA found that side right); the left edge within a window round the right edge's mirror about the
    axis. The axis is fitted as a line on the rows where both edges are found (robust: two rounds, residuals over 2 px dropped), the
    windows narrowed round it (10 px, then 5 px). The half width r(y) = (right - left) / 2, outliers against a 7-row median (> 1.5 px)
    replaced by it, then smoothed (sigma 1.5 rows): a turned body is smooth. Returns per body row the axis and r, and the record"""
    Lb = cv2.cvtColor(cv2.GaussianBlur(regt, (0, 0), 0.6), cv2.COLOR_RGB2LAB)
    gl = np.zeros(Lb.shape, np.float32)
    gl[:, 1:-1] = (Lb[:, 2:] - Lb[:, :-2]) / 2
    gm = np.sqrt((gl ** 2).sum(2))
    yb = int(np.nonzero((a_cut > 0.5).any(1))[0].max())
    rows = list(range(rim_row + 3, yb + 1))
    xR, sR = {}, {}
    for y in rows:
        xs = np.nonzero(a_cut[y] > 0.5)[0]
        if not len(xs):
            continue
        xm = int(xs.max())
        i = xm - 8 + int(np.argmax(gm[y, xm - 8:xm + 4]))
        xR[y], sR[y] = _parab(gm[y], i) + 0.5, float(gm[y, i])
    rows = [y for y in rows if y in xR]
    c1, c0 = 0.0, float(axis0)
    hist = []
    for win in (10, 5, 5):
        xL, sL = {}, {}
        for y in rows:
            mir = 2 * (c0 + c1 * y) - xR[y]
            lo, hi = int(math.floor(mir - win)), int(math.ceil(mir + win))
            if white is None:
                i = lo + int(np.argmax(gm[y, lo:hi + 1]))
                xL[y], sL[y] = _parab(gm[y], i) + 0.5, float(gm[y, i])
                continue
            # a white flank on a white window or a light bench: the OUTERMOST step into the flank's white band (the next 3 px L* >= 95.5
            # and b* <= 5.5): a rise of L* (the window, the rail) or a fall of b* (the warm bench), at least 1.5 per px
            e = np.maximum(gl[y, :, 0], -gl[y, :, 2])
            cand = [x for x in range(lo, hi + 1) if e[x] >= 1.5 and Lb[y, x + 1:x + 4, 0].mean() >= 95.5 and Lb[y, x + 1:x + 4, 2].mean() <= 5.5]
            if not cand:
                xL[y], sL[y] = mir, 0.0
                continue
            x = cand[0]
            while x + 1 <= hi and e[x + 1] > e[x]:
                x += 1                                              # up the rise to its peak
            xL[y], sL[y] = _parab(e, x) + 0.5, float(e[x])
        ys = np.array(rows, np.float64)
        mids = np.array([(xL[y] + xR[y]) / 2 for y in rows])
        strong = np.array([sL[y] >= (np.percentile(list(sL.values()), 30) if white is None else 1.5) for y in rows])
        keep = strong.copy()
        for _ in range(2):
            p = np.polyfit(ys[keep], mids[keep], 1)
            keep = strong & (np.abs(mids - np.polyval(p, ys)) <= 2.0)
        c1, c0 = float(p[0]), float(p[1])
        hist.append(dict(window_px=win, tilt_px_per_row=round(c1, 5), rows_used=int(keep.sum())))
    ys = np.array(rows)
    r = np.array([(xR[y] - xL[y]) / 2 for y in rows])
    good = keep.copy()
    med = np.array([np.median(r[max(0, i - 3):i + 4][good[max(0, i - 3):i + 4]]) if good[max(0, i - 3):i + 4].any() else r[i] for i in range(len(r))])
    rr = np.where(good & (np.abs(r - med) <= 1.5), r, med)
    rs = cv2.GaussianBlur(rr.astype(np.float32).reshape(-1, 1), (1, 0), 1.5, borderType=cv2.BORDER_REPLICATE).ravel()
    # the right edge is the old cut's side, measured: where the smooth profile and the measured right edge differ, the profile wins
    axis = c0 + c1 * ys
    info = dict(body_rows=[int(ys[0]), int(ys[-1])], axis=dict(x_at_foot=round(float(c0 + c1 * ys[-1]), 2), x_at_top=round(float(c0 + c1 * ys[0]), 2),
                                                               tilt_px_per_row=round(c1, 5), tilt_deg=round(math.degrees(math.atan(c1)), 2)),
                fit=hist, rows_left_edge_measured=int(good.sum()), rows_from_profile=int((~good).sum()),
                widest_px=round(float(2 * rs.max()), 2), widest_row=int(ys[int(np.argmax(rs))]),
                old_cut_width_px_median=round(float(np.median([(a_cut[y] > 0.5).sum() for y in rows])), 2),
                new_width_px_median=round(float(np.median(2 * rs)), 2))
    return dict(rows=ys, axis=axis, r=rs, xL=np.array([xL[y] for y in rows]), xR=np.array([xR[y] for y in rows]), good=good), info


def body_alpha(rows, axis, r, shape, soft=1.4):
    """the body's alpha from its axis and half width per row: 1 inside, a soft edge of `soft` px centred on each edge"""
    a = np.zeros(shape, np.float32)
    xx = np.arange(shape[1], dtype=np.float32)
    for y, c, h in zip(rows, axis, r):
        a[y] = np.clip(np.minimum(xx + 0.5 - (c - h), (c + h) - (xx + 0.5)) / soft + 0.5, 0, 1)
    return a


def recut_alpha(a_cut, prof):
    """the re-cut alpha in the render's own coordinates: the body rows from the profile (the old cut's soft bottom row kept as a vertical
    falloff), the old cut above the body (the lip, the branch)"""
    rows, axis, r, good = prof["rows"], prof["axis"].copy(), prof["r"].copy(), prof["good"]
    last_good = int(np.nonzero(good)[0].max())
    r[last_good + 1:] = r[last_good]                       # under the last measured row the foot keeps its width (a flat base)
    ab = body_alpha(rows, axis, r, a_cut.shape)
    a = a_cut.copy()
    for y in rows:
        a[y] = ab[y] * min(1.0, float(a_cut[y].max()))
    return a.astype(np.float32)


def straighten_scale(rgb, a, prof, foot_y, sx, sy):
    """the forward affine (render -> layer): the axis made vertical about the foot (x - tilt (y - foot_y): the camera is level, the
    window's mullion is vertical in the same render, so the model's lean is the model's), then the card's size about the foot (sx, sy);
    applied premultiplied (bilinear). Returns rgb, alpha, the matrix, the foot's axis x"""
    c1 = float(np.polyfit(prof["rows"], prof["axis"], 1)[0])
    ax = float(np.polyval(np.polyfit(prof["rows"], prof["axis"], 1), foot_y))
    M = np.float32([[sx, -sx * c1, sx * c1 * foot_y + ax * (1 - sx)], [0, sy, foot_y * (1 - sy)]])
    wa = cv2.warpAffine(a, M, SIZE, flags=cv2.INTER_LINEAR)
    wp = cv2.warpAffine(rgb * a[..., None], M, SIZE, flags=cv2.INTER_LINEAR)
    rgb2 = np.where((wa > 1e-4)[..., None], wp / np.maximum(wa, 1e-4)[..., None], rgb)
    return np.clip(rgb2, 0, 1).astype(np.float32), np.clip(wa, 0, 1).astype(np.float32), M, ax


def vase_widths(a, rows):
    w = np.array([float(a[y].sum()) for y in rows])
    w5 = np.convolve(w, np.ones(5) / 5, mode="same")
    i = int(np.argmax(w5[2:-2])) + 2
    return float(w5[i]), int(rows[i])


def vase_shadow(nm, a, regt, below, pass_, slot="vase"):
    """the contact shadow by the frozen recipe (pass_r5.shadow_new = extract.shadow_one with the slot's SPEC), with what stands in front
    of the vase in the scene (the layers above it, set B) and the pass's other products, as pass_r5.fetch had them"""
    surf = X.surfaces()
    fa = W.furn_alpha()
    surf["front"] = fa > 0.02
    keep = [k for k in R.ACCEPTED if k not in R.PASSES[pass_]["remove"]]
    use_r6_sources()
    above = np.zeros(SIZE[::-1], np.float32)
    for j in keep:
        if stack.ORDER.index(j) > stack.ORDER.index(slot) and j != "rug":
            _, aj, _ = G12.product(j)
            above = np.maximum(above, aj)
    _, ac, _ = G12._STACK_PRODUCT("cushions", "B")
    above = np.maximum(above, ac)
    others = {}
    for k2, v2 in R.PASSES[pass_]["products"]:
        if k2 == slot:
            continue
        nm2 = R.fname(k2, v2)
        p2 = D(WR5, "layers", f"{nm2}-cut.png") if os.path.exists(D(WR5, "layers", f"{nm2}-cut.png")) else D(WR5, "layers", f"{nm2}.png")
        others[k2] = f32(p2)[..., 3]
    others["_above"] = above
    sh, info = R.shadow_new(slot, a, regt, below, surf, others)
    return sh, info


def scale_about_foot(rgb, a, sh, sx, sy, ax, ay):
    """fix_r4.vase()'s scaling: the layer premultiplied, about the foot's contact (ax, ay), x and y apart; the contact shadow at the foot's
    scale (sx both ways: it lies on the bench); 1 under the new full alpha"""
    Ml = np.float32([[sx, 0, ax * (1 - sx)], [0, sy, ay * (1 - sy)]])
    Ms = np.float32([[sx, 0, ax * (1 - sx)], [0, sx, ay * (1 - sx)]])
    fl = cv2.INTER_AREA if min(sx, sy) < 1 else cv2.INTER_LINEAR
    wa = cv2.warpAffine(a, Ml, SIZE, flags=fl)
    wp = cv2.warpAffine(rgb * a[..., None], Ml, SIZE, flags=fl)
    rgb2 = np.where((wa > 1e-4)[..., None], wp / np.maximum(wa, 1e-4)[..., None], rgb)
    a2 = np.clip(wa, 0, 1)
    sh2 = np.clip(1 - cv2.warpAffine(1 - sh, Ms, SIZE, flags=fl), 0, 1)
    sh2 = np.where(a2 >= 0.999, 1.0, sh2)
    return rgb2.astype(np.float32), a2.astype(np.float32), sh2.astype(np.float32), Ml, Ms


POINT = R.POINT
VASE_CARD = {"vase": dict(D=0.16, H=0.32, mouth=0.09, foot=0.10, cm=(16, 32)),       # Large: D16 x H32, mouth 9 (card)
             "vase-v2": dict(D=0.22, H=0.32, mouth=0.13, foot=0.124, cm=(22, 32))}   # Style B: W22 x H32, mouth ~13 (card)
SIZE_TOL = 0.05        # QA R5 passed vase 2 at +4.5 %: an axis is brought to the card only beyond 5 %


def lip_top(a_cut, axis_x, rim_row, half):
    """the mouth's far rim: going up from the rim row, the last row whose alpha run round the axis is still >= 70 % of the rim row's"""
    w0 = float(a_cut[rim_row, int(axis_x - half):int(axis_x + half)].sum())
    y = rim_row
    while y > rim_row - 20 and float(a_cut[y - 1, int(axis_x - half):int(axis_x + half)].sum()) >= 0.7 * w0:
        y -= 1
    return y


def vase_measures(G8, a, body_from):
    """post_r5.vase_colour's measure: the lit half (left of the body's middle) of the body (alpha 255 eroded 5 px, rows from the rim) and
    the whole body; the surfaces beside (15-40 px out, L* 50-95)"""
    m = cv2.erode((a >= 0.999).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[:body_from] = False
    ys, xs = np.nonzero(m)
    lit = m & (np.arange(m.shape[1])[None, :] < (xs.min() + xs.max()) / 2)
    LL = lab8(G8)
    d = cv2.distanceTransform((~(a > 0)).astype(np.uint8), cv2.DIST_L2, 5)
    beside = (d >= 15) & (d <= 40) & (LL[..., 0] <= 95) & (LL[..., 0] >= 50)

    def s(mm):
        aa, bb = float(np.median(LL[..., 1][mm])), float(np.median(LL[..., 2][mm]))
        C = np.hypot(LL[..., 1][mm], LL[..., 2][mm])
        return dict(L=round(float(np.median(LL[..., 0][mm])), 2), C=round(math.hypot(aa, bb), 2), h=round(math.degrees(math.atan2(bb, aa)) % 360, 2),
                    C_px_median=round(float(np.median(C)), 2), px=int(mm.sum()))
    return dict(lit_half=s(lit), body=s(m), beside=s(beside))


def _vase(nm, pass_, src_cut, rim, axis0, white, colour):
    regt = np.load(D(WR5, f"{pass_}-regt.npy")).astype(np.float32)
    below = PW.load(D(WR5, f"scene-{pass_}.png"))
    Lc = f32(src_cut)
    a_cut = Lc[..., 3]
    prof, info = vase_recut(regt, a_cut, rim, axis0, white)
    a_src = recut_alpha(a_cut, prof)
    # the size against the card at the point
    cc = VASE_CARD[nm]
    card = F4.card_vase_box(*POINT, D=cc["D"], H=cc["H"], mouth=cc["mouth"], foot=cc["foot"])
    body = prof["rows"][:-3]
    wid, wrow = vase_widths(a_src, body)
    foot_y = F4.vase_measure(a_src, regt)["foot_contact_y"]
    top = lip_top(a_cut, float(np.median(prof["axis"][:5])), rim, float(prof["r"][0]) + 4)
    hgt = foot_y - (top - 0.5)
    rw, rh = wid / card["width"], hgt / card["height"]
    sx = card["width"] / wid if abs(rw - 1) > SIZE_TOL else 1.0
    sy = card["height"] / hgt if abs(rh - 1) > SIZE_TOL else 1.0
    rgb, a, M, ax = straighten_scale(regt, a_src, prof, foot_y, sx, sy)
    # the contact shadow: the frozen recipe on the FINAL cut, measured on the render carried by the same affine (so the darkening the
    # model drew round its foot is read where the foot now is; nothing the vase uncovered is left unshadowed next to it)
    regt_w = np.clip(cv2.warpAffine(regt, M, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), 0, 1).astype(np.float32)
    sh, sinfo = vase_shadow(nm, a, regt_w, below, pass_)
    pc = save_layer(f"{nm}-recut", rgb, a)                 # before the colour fix (for QA)
    rgb_f, crec = colour(rgb, a, sh)
    pl = save_layer(nm, rgb_f, a)
    ps = save_shadow(nm, sh)
    # after: the size and the axis in the layer
    mids = []
    for y in body:
        xs = np.nonzero(a[y] > 0.5)[0]
        if len(xs):
            mids.append((y, (xs.min() + xs.max()) / 2.0))
    mids = np.array(mids)
    tilt2 = float(np.polyfit(mids[:, 0], mids[:, 1], 1)[0])
    info2 = dict(axis=dict(tilt_px_per_row=round(tilt2, 5), tilt_deg=round(math.degrees(math.atan(tilt2)), 2), how="the alpha 0.5 mid-points of the body rows"))
    wid2, _ = vase_widths(a, body)
    a_old = a_cut
    lost = dict(old_cut_width_px_median_body=info["old_cut_width_px_median"],
                render_width_px_widest=round(wid, 2), layer_width_px_widest=round(wid2, 2))
    record(nm, dict(
        what=("re-cut from the raw render (QA R5 3.1: the cut followed R4's placeholder and lost the lit flank)" if nm == "vase" else
              "re-cut from the raw render, as the default (the brief: both vases)") + "; straightened and sized to the card about the foot; colour",
        source=dict(render=rel(D(WR5, f"{pass_}-regt.npy")) + " (the registered, tone-matched raw " + rel(D(W.RAW, f"{pass_}-r5-seedream.png")) + ")",
                    scene_behind=rel(D(WR5, f"scene-{pass_}.png")), old_cut=rel(src_cut)),
        method=dict(edges=vase_recut.__doc__.replace("\n", " "), alpha=recut_alpha.__doc__.replace("\n", " "),
                    straighten_and_size=straighten_scale.__doc__.replace("\n", " "),
                    shadow="extract.shadow_one (frozen, pass_r5.shadow_new) on the final cut, against the scene behind, on the render carried "
                           "by the layer's own affine"),
        recut=info, axis_check_in_layer=info2["axis"], size=dict(card_cm=list(cc["cm"]), card_at_point_px={k: round(v, 2) for k, v in card.items()},
                                                               render_widest_px=round(wid, 2), render_widest_row=wrow, render_height_px=round(hgt, 2),
                                                               lip_top_row=int(top), foot_contact_y=round(float(foot_y), 2),
                                                               render_vs_card=[round(rw, 4), round(rh, 4)],
                                                               render_cm=[round(cc["cm"][0] * rw, 1), round(cc["cm"][1] * rh, 1)],
                                                               tolerance=SIZE_TOL, scale=[round(sx, 4), round(sy, 4)],
                                                               layer_widest_px=round(wid2, 2),
                                                               layer_cm=[round(cc["cm"][0] * wid2 / card["width"], 1), round(cc["cm"][1] * rh * sy, 1)]),
        matrix_layer=np.round(M, 5).tolist(), foot_axis_x=round(ax, 2),
        widths=lost, shadow=dict(recipe=sinfo.get("recipe"), px_below_0_97=int((sh < 0.97).sum()), min=round(float(sh.min()), 3)),
        colour=crec, files=dict(layer=rel(pl), shadow=rel(ps), recut_before_colour=rel(pc))))
    return rgb_f, a, sh


def vase():
    """the default vase: R5's a*b* fix re-solved on the re-cut body (post_r5.vase_colour's method and targets: one hue rotation and one
    chroma factor for every body pixel, rows >= 935; the hue of the surfaces beside, L* unchanged), started from R5's dh and k. With its lit
    flank back the lit half is lighter (L* 88 against R5's 79) and R5's k alone gives C* 3.4, under the designer's 4-7 and cooler than
    the room's own white (the back wall, C* 4.05): the lit half is set to C* 4.5, inside the range and the nearest to the card's
    near-neutral #EEECE8"""
    rec5 = json.load(open(D(WR5, "post-r5.json")))["vase"]

    def colour(rgb, a, sh):
        body = np.zeros(a.shape, bool)
        body[935:] = True
        _, _, G0 = graded(override={"vase": (rgb, a, None, sh)})
        b0 = vase_measures(G0, a, 940)
        want_C, want_h = 4.5, b0["beside"]["h"]               # inside the designer's 4-7, above the room's white (C 4.05), nearest the card
        dh, k = rec5["dh_deg"], rec5["k"]
        hist = []
        for it in range(8):
            out = np.where(body[..., None], F5.recolour_ab(rgb, dh, k), rgb).astype(np.float32)
            _, _, G1 = graded(override={"vase": (out, a, None, sh)})
            b1 = vase_measures(G1, a, 940)
            hist.append(dict(it=it, dh=round(dh, 3), k=round(k, 4), **b1["lit_half"]))
            if abs(b1["lit_half"]["C"] - want_C) < 0.1 and abs((b1["lit_half"]["h"] - want_h + 180) % 360 - 180) < 0.5:
                break
            dh += (want_h - b1["lit_half"]["h"] + 180) % 360 - 180
            k *= want_C / max(b1["lit_half"]["C"], 1e-3)
        hb = b1["beside"]["h"]
        tg = {"C* median 4-7 on the lit half": 4 <= b1["lit_half"]["C"] <= 7,
              "hue within 10 deg of the surface beside": abs((b1["lit_half"]["h"] - hb + 180) % 360 - 180) <= 10,
              "not above C 7": b1["lit_half"]["C"] <= 7, "L* unchanged (+-0.5)": abs(b1["lit_half"]["L"] - b0["lit_half"]["L"]) <= 0.5}
        return out, dict(fix=vase.__doc__.replace("\n", " "), r5=dict(dh=rec5["dh_deg"], k=rec5["k"]), dh_deg=round(dh, 3), k=round(k, 4),
                         iterations=hist, before=b0, after=b1, targets_r5=tg, all_met=all(tg.values()), card="#EEECE8")
    return _vase("vase", "p4", D(WR5, "layers/vase-cut.png"), 936, 674.0, True, colour)


def vase_v2():
    """vase 2: a*b* toward the card's neutral charcoal (#3B3A38; designer section 6.1): the body only (alpha 255 eroded 5 px, from the
    rim + 4), one hue rotation and one chroma factor (R5's method), to the median C* between 2.5 and the C* of the surfaces beside
    (post_r5's 'beside': 15-40 px out, L* 50-95), the hue within 10 deg of theirs, L* within 0.5; the branch keeps its colour"""
    def colour(rgb, a, sh):
        body = np.zeros(a.shape, bool)
        body[944:] = True
        _, _, G0 = graded(variants={}, override={"vase": (rgb, a, None, sh)})
        b0 = vase_measures(G0, a, 946)
        ring = b0["beside"]
        if b0["body"]["C"] <= 4.5:
            return rgb, dict(fix="none needed (body median C* <= 4.5)", before=b0)
        want_C, want_h = (2.5 + ring["C"]) / 2, ring["h"]
        dh, k = want_h - b0["body"]["h"], want_C / max(b0["body"]["C"], 1e-3)
        hist = []
        for it in range(8):
            out = np.where(body[..., None], F5.recolour_ab(rgb, dh, k), rgb).astype(np.float32)
            _, _, G1 = graded(override={"vase": (out, a, None, sh)})
            b1 = vase_measures(G1, a, 946)
            hist.append(dict(it=it, dh=round(dh, 3), k=round(k, 4), **b1["body"]))
            if abs(b1["body"]["C"] - want_C) < 0.1 and abs((b1["body"]["h"] - want_h + 180) % 360 - 180) < 1.0:
                break
            dh += (want_h - b1["body"]["h"] + 180) % 360 - 180
            k *= want_C / max(b1["body"]["C"], 1e-3)
        tg = {"C* median 2.5 .. the surfaces beside": 2.5 <= b1["body"]["C"] <= ring["C"],
              "hue within 10 deg of the surfaces beside": abs((b1["body"]["h"] - ring["h"] + 180) % 360 - 180) <= 10,
              "L* within 0.5": abs(b1["body"]["L"] - b0["body"]["L"]) <= 0.5}
        return out, dict(fix=vase_v2.__doc__.replace("\n", " "), card="#3B3A38 (C 1.4, h 89)", target=dict(C=round(want_C, 2), h=round(want_h, 2)),
                         dh_deg=round(dh, 3), k=round(k, 4), iterations=hist, before=b0, after=b1, targets=tg, all_met=all(tg.values()))
    return _vase("vase-v2", "p5", D(WR5, "layers/vase-v2.png"), 942, 670.0, None, colour)


# ================================================================================================= curtains
def _sha(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def curtains():
    """180502 becomes the slot's default (the designer, eye section 1; FR-F): its R5 work files, byte for byte, under the default's names"""
    pairs = [(D(WR5, "layers/curtains-v2.png"), "layers", "curtains.png"), (D(WR5, "layers/curtains-v2-free-alpha.png"), "layers", "curtains-free-alpha.png"),
             (D(WR5, "shadows/curtains-v2.png"), "shadows", "curtains.png")]
    out = {}
    for src, sub, name in pairs:
        dst = copy_to(src, sub, name)
        out[rel(dst)] = dict(source=rel(src), same_bytes=_sha(src) == _sha(dst))
    record("curtains", dict(what="the default flips to 180502 (curtains-aliexpress-linen-blend-s-fold-180502, S-fold 132 x 270, SKU 12000059196236244): "
                                 "the designer's decision (wm-phase2-r5-eye section 1); 554205 becomes variant 2 (curtains-v2)",
                            files=out, unchanged="the R5 cut, its R5 colour fix and its shadow; the true length waits for the designer"))


def qa_mask(a, rows=(100, 1400)):
    """QA p2_colour's curtain mask: the layer's alpha 255 (here >= 0.999) eroded 5 x 5, rows 100-1400"""
    m = cv2.erode((a >= 0.999).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    r = np.zeros_like(m)
    r[rows[0]:rows[1]] = True
    return m & r


def all_product_alpha():
    use_r6_sources()
    A = np.zeros(SIZE[::-1], bool)
    for k in ACCEPTED:
        _, a, _ = G12.product(k)
        A |= a > 0
    for nm, (ld, _) in VSRC6.items():
        p = D(ld, f"{nm}.png")
        if os.path.exists(p):
            A |= f32(p)[..., 3] > 0
    for s in "ABC":
        _, ac, _ = G12._STACK_PRODUCT("cushions", s)
        A |= ac > 0
    return A


def curtain_stats(G8, m, ring):
    LL = lab8(G8)
    L, A_, B_ = LL[..., 0], LL[..., 1], LL[..., 2]
    C = np.hypot(A_, B_)
    am, bm = float(np.median(A_[m])), float(np.median(B_[m]))
    hp = L - cv2.GaussianBlur(L, (0, 0), 3)
    ra, rb = float(np.median(A_[ring])), float(np.median(B_[ring]))
    return dict(L=round(float(np.median(L[m])), 2), C=round(math.hypot(am, bm), 2), h=round(math.degrees(math.atan2(bm, am)) % 360, 2),
                C_px_p95=round(float(np.percentile(C[m], 95)), 2), L_p99=round(float(np.percentile(L[m], 99)), 2), L_max=round(float(L[m].max()), 2),
                highpass_std=round(float(hp[m].std()), 3), px=int(m.sum()),
                clean_ring=dict(L=round(float(np.median(L[ring])), 2), C=round(math.hypot(ra, rb), 2), h=round(math.degrees(math.atan2(rb, ra)) % 360, 2),
                                px=int(ring.sum())))


FOLD_PX = 50        # the folds' spacing on both curtains (the autocorrelation of the rows' L* high-pass: 46-53 px)


def curtains_v2():
    """554205 as variant 2 (designer section 1, 'the fix of 554205'): relative to 180502 in the same light and under the same mask (QA
    p2_colour's mask on each layer, intersected), L* included. (1) The lightness: ONE monotone tone curve on the low frequencies of L*
    (a normalised blur over the curtain, sigma 1.5 fold spacings = 75 px, i.e. a kernel about 3 spacings wide): the low-frequency L*
    quantiles of 554205 mapped onto 180502's (the same mask, the ungraded layers), shifted so the graded medians meet; the high
    frequencies (the folds, sigma 3-75, and the slub, under sigma 3) back x g, g = (L*180502 + 16) / (L*554205 + 16) clipped to 1-1.2
    (a brighter cloth shows the same folds as larger L* steps); two soft shoulders (the folds' crests over 89, the slub's specks over
    93.5) keep the brightest folds under burn (target 5). (2) The colour after the lightness: a*b* by R5's method (one hue rotation, one chroma
    factor for every pixel) to 180502's median C* and h. (3) The armchair post's line solved again (fix_r5.post_line_fix). The free alpha
    and the shadow layer are 554205's own, unchanged"""
    Lw = f32(D(WRES, "layers", "curtains.png"))
    rgb_w, a_in = Lw[..., :3], Lw[..., 3]
    a_free = f32(D(WRES, "layers", "curtains-free-alpha.png"), "L")
    sh = f32(D(WRES, "shadows", "curtains.png"), "L")
    L180 = f32(D(WR6, "layers", "curtains.png"))
    a180, af180 = L180[..., 3], f32(D(WR6, "layers", "curtains-free-alpha.png"), "L")
    P = parts()
    fa, F = P["fa"], P["F"]
    m554, m180 = qa_mask(a_in), qa_mask(a180)
    mm = m554 & m180
    _, _, G180 = graded()
    LG180 = lab8(G180)[..., 0]
    allp = all_product_alpha()
    d = cv2.distanceTransform((~((a_in > 0) | (a180 > 0))).astype(np.uint8), cv2.DIST_L2, 5)
    ring = (d >= 15) & (d <= 40) & ~allp & (fa <= 0.02) & (LG180 > 80)
    s180 = curtain_stats(G180, mm, ring)
    s180_own = curtain_stats(G180, m180, ring)
    ov = lambda rgb: {"curtains": (rgb, a_in, a_free, sh)}  # noqa: E731
    _, _, G0 = graded(override=ov(rgb_w))
    s0 = curtain_stats(G0, mm, ring)
    _, _, G5 = graded(override=ov(f32(D(WR5, "layers", "curtains.png"))[..., :3]))
    s5 = curtain_stats(G5, mm, ring)
    # (1) the tone curve
    sig = 1.5 * FOLD_PX
    lab_w = lab(rgb_w)
    low554, _ = nblur(lab_w[..., 0], (a_free > 0.5).astype(np.float32), sig)
    low180, _ = nblur(lab(L180[..., :3])[..., 0], (af180 > 0.5).astype(np.float32), sig)
    qs = np.linspace(0.5, 99.5, 100)
    qa_, qb_ = np.percentile(low554[mm], qs), np.percentile(low180[mm], qs)
    qa_ = np.maximum.accumulate(qa_ + np.arange(len(qa_)) * 1e-6)
    qb_ = np.maximum.accumulate(qb_ + np.arange(len(qb_)) * 1e-6)
    s_lo = float(np.clip((qb_[5] - qb_[0]) / max(qa_[5] - qa_[0], 1e-3), 0.3, 2.0))
    s_hi = float(np.clip((qb_[-1] - qb_[-6]) / max(qa_[-1] - qa_[-6], 1e-3), 0.3, 2.0))

    def curve(x, off):
        y = np.interp(x, qa_, qb_)
        y = np.where(x < qa_[0], qb_[0] + (x - qa_[0]) * s_lo, y)
        y = np.where(x > qa_[-1], qb_[-1] + (x - qa_[-1]) * s_hi, y)
        return y + off
    base3 = cv2.GaussianBlur(lab_w[..., 0], (0, 0), 3.0)
    folds, fine = base3 - low554, lab_w[..., 0] - base3            # the folds (sigma 3-75) and the slub (under sigma 3)
    g = float(np.clip((s180["L"] + 16) / (s0["L"] + 16), 1.0, 1.2))
    off = 0.0
    hist_L = []
    shoulder = lambda L_, s0_, w_: np.where(L_ > s0_, s0_ + w_ * np.tanh((L_ - s0_) / w_), L_)  # noqa: E731

    def lightness(off, g):
        Ln = shoulder(curve(low554, off) + g * folds, 89.0, 3.0) + g * fine
        Ln = shoulder(Ln, 93.5, 2.0)                                     # the slub's brightest specks (target 5: no burn)
        return rgb_of(np.clip(Ln, 0, 100), lab_w[..., 1], lab_w[..., 2])
    for it in range(8):
        rgb_L = lightness(off, g)
        _, _, G1 = graded(override=ov(rgb_L))
        s1 = curtain_stats(G1, mm, ring)
        hist_L.append(dict(it=it, offset=round(off, 3), g=round(g, 3), L=s1["L"], highpass_std=s1["highpass_std"], L_p99=s1["L_p99"]))
        ok_hp = 3.1 <= s1["highpass_std"] <= 4.2
        if abs(s1["L"] - s180["L"]) < 0.3 and ok_hp:
            break
        off += s180["L"] - s1["L"]
        if not ok_hp:
            g = float(np.clip(g * (3.9 if s1["highpass_std"] > 4.2 else 3.4) / max(s1["highpass_std"], 1e-3), 1.0, 1.2))
    # (2) a*b*, R5's method, to 180502's median C* and h
    want_C, want_h = s180["C"], float(np.clip(s180["h"], 87, 93))
    s_ = curtain_stats(G1, mm, ring)
    dh, k = want_h - s_["h"], want_C / max(s_["C"], 1e-3)
    hist_ab = []
    for it in range(10):
        rgb_n = F5.recolour_ab(rgb_L, dh, k)
        _, _, G2 = graded(override=ov(rgb_n))
        s2 = curtain_stats(G2, mm, ring)
        hist_ab.append(dict(it=it, dh=round(dh, 3), k=round(k, 4), C=s2["C"], h=s2["h"], C_p95=s2["C_px_p95"], L=s2["L"]))
        if abs(want_h - s2["h"]) < 0.3 and abs(want_C - s2["C"]) < 0.05 and s2["C_px_p95"] <= 10.9:
            break
        dh += want_h - s2["h"]
        k *= (want_C / max(s2["C"], 1e-3)) if s2["C_px_p95"] <= 10.9 else 10.8 / s2["C_px_p95"]
    rgb_n = F5.recolour_ab(rgb_L, dh, k)
    # (3) the armchair post's line
    rgb_f, fringe = F5.post_line_fix(rgb_n, a_free, fa, F)
    _, _, Gf = graded(override=ov(rgb_f))
    sf = curtain_stats(Gf, mm, ring)
    sf_own = curtain_stats(Gf, m554, ring)
    LLf = lab8(Gf)[..., 0]
    vis = (a_in > 0.5)
    burn = dict(L_p99_visible=round(float(np.percentile(LLf[vis], 99)), 2), px_at_100=int((LLf[vis] >= 99.95).sum()))
    tg = {"1 median L* = 180502's +-2": dict(value=round(sf["L"] - s180["L"], 2), pass_=abs(sf["L"] - s180["L"]) <= 2),
          "2a median C* = 180502's +-0.8": dict(value=round(sf["C"] - s180["C"], 2), pass_=abs(sf["C"] - s180["C"]) <= 0.8),
          "2b median C* >= the clean ring's + 0.5": dict(value=round(sf["C"] - sf["clean_ring"]["C"], 2), pass_=sf["C"] >= sf["clean_ring"]["C"] + 0.5),
          "3 median h 87-93": dict(value=sf["h"], pass_=87 <= sf["h"] <= 93),
          "4 p95 C* <= 11": dict(value=sf["C_px_p95"], pass_=sf["C_px_p95"] <= 11),
          "5 no burn: p99 L* <= 94, no pixel at 100": dict(value=burn, pass_=burn["L_p99_visible"] <= 94 and burn["px_at_100"] == 0),
          "6 folds: high-pass L* std 3.1-4.2": dict(value=sf["highpass_std"], pass_=3.1 <= sf["highpass_std"] <= 4.2)}
    pl = save_layer("curtains-v2", rgb_f, a_in)
    copy_to(D(WRES, "layers", "curtains-free-alpha.png"), "layers", "curtains-v2-free-alpha.png")
    copy_to(D(WRES, "shadows", "curtains.png"), "shadows", "curtains-v2.png")
    record("curtains-v2", dict(
        what="554205 (curtains-aliexpress-beige-linen-sheer-curtains-554205, hooks 150 x 270, SKU 12000029601125492), now variant 2: L* and "
             "a*b* relative to 180502 (designer section 1)", method=curtains_v2.__doc__.replace("\n", " "),
        source=dict(layer=rel(D(WRES, "layers", "curtains.png")) + " (R1, before R5's fix)", free_alpha=rel(D(WRES, "layers", "curtains-free-alpha.png")),
                    shadow=rel(D(WRES, "shadows", "curtains.png")) + " (unchanged, copied)"),
        masks=dict(same_mask="QA p2_colour's mask (alpha 255 eroded 5 x 5, rows 100-1400) of 554205 AND of 180502: %d px" % mm.sum(),
                   clean_ring="15-40 px out of both curtains, no product (both curtains, every slot and variant, the cushion sets), no "
                              "furniture, L* > 80 (plaster, not glass): %d px (QA R5: the targets' old ring was 23 %% curtain)" % ring.sum()),
        reference_180502=dict(same_mask=s180, own_mask=s180_own), before_r1=s0, before_r5=s5,
        tone_curve=dict(sigma_px=sig, fold_spacing_px=FOLD_PX, quantiles_554205=[round(float(v), 2) for v in qa_[::10]],
                        quantiles_180502=[round(float(v), 2) for v in qb_[::10]], offset=round(off, 3), high_gain=round(g, 3),
                        bands="low = the normalised blur (sigma 75); folds = blur 3 - low; slub = L - blur 3",
                        formula="L* = top(shoulder(curve(low) + offset + g folds) + g slub); shoulder: above 89, 89 + 3 tanh((L - 89) / 3); "
                                "top: above 93.5, 93.5 + 2 tanh((L - 93.5) / 2) (the crests and the slub's specks under burn, target 5)",
                        iterations=hist_L),
        ab=dict(dh_deg=round(dh, 3), k=round(k, 4), target=dict(C=want_C, h=want_h), iterations=hist_ab),
        post_line=dict(fringe_px=int(fringe.sum())), after=sf, after_own_mask=sf_own, targets=tg, all_met=all(v["pass_"] for v in tg.values()),
        file=rel(pl)))
    print(json.dumps(dict(ref=s180, before=s0, after=sf, targets=tg), indent=1, default=float))


# ================================================================================================= framed art 2: the seams and the specks
SS_ART = 8              # supersampling of the band / line / print coverage


def _side_lines(inner_piece):
    """the four sides of one print area as lines fitted through R5's integer staircase (the middle 80 % of each side): top / bottom
    y = k x + b (pixel-edge coordinates), left / right x = k y + b"""
    ys, xs = np.nonzero(inner_piece)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    cols = np.arange(int(x0 + 0.1 * (x1 - x0)), int(x1 - 0.1 * (x1 - x0)))
    rows = np.arange(int(y0 + 0.1 * (y1 - y0)), int(y1 - 0.1 * (y1 - y0)))
    top = np.array([np.nonzero(inner_piece[:, x])[0].min() for x in cols], np.float64)
    bot = np.array([np.nonzero(inner_piece[:, x])[0].max() + 1 for x in cols], np.float64)
    lef = np.array([np.nonzero(inner_piece[y])[0].min() for y in rows], np.float64)
    rig = np.array([np.nonzero(inner_piece[y])[0].max() + 1 for y in rows], np.float64)
    out = {}
    for nm, t, v in (("top", cols, top), ("bottom", cols, bot), ("left", rows, lef), ("right", rows, rig)):
        p = np.polyfit(t + 0.5, v, 1)
        r = v - np.polyval(p, t + 0.5)
        out[nm] = dict(k=float(p[0]), b=float(p[1]), staircase_steps=int((np.abs(np.diff(v)) > 0).sum()),
                       staircase_rms=round(float(np.sqrt((r ** 2).mean())), 3),
                       t0=float(x0 if nm in ("top", "bottom") else y0), t1=float(x1 if nm in ("top", "bottom") else y1))
    return out, (int(x0), int(y0), int(x1), int(y1))


def _default_edge_lines(LD, lines):
    """each side refitted on the DEFAULT's own moulding -> print edge (where its print begins), from the positions along the side where
    the default's print next to it is light (L* > 60 at 3.5 px inside: the step is clear): per position the sub-pixel peak of the L*
    step from the moulding into the print, within 3 px of R5's line; a line through them (two rounds, residuals over
    1 px dropped). A side with fewer than 20 such positions keeps R5's line"""
    out, info = {}, {}
    H, Wd = LD.shape
    for side, l in lines.items():
        horiz = side in ("top", "bottom")
        sgn = -1.0 if side in ("top", "left") else 1.0          # the outward direction (toward the moulding)
        lo_t, hi_t = (l["t0"], l["t1"])
        pts = []
        for t in range(int(lo_t) + 10, int(hi_t) - 10):
            c = l["k"] * (t + 0.5) + l["b"]                     # the boundary coordinate across the side (pixel edges)
            ci = int(math.floor(c))
            idx = np.arange(ci - 5, ci + 6)
            prof = LD[idx, t] if horiz else LD[t, idx]
            inside = (LD[int(math.floor(c - sgn * 3.5)), t] if horiz else LD[t, int(math.floor(c - sgn * 3.5))])
            if inside <= 60:
                continue
            # the step into the print: going inward (against sgn), L rises; the gradient between pixel centres j and j + 1
            g = (np.diff(prof) * (-sgn))
            pos = idx[:-1] + 1.0                                # the pixel edge between j and j + 1
            win = (pos >= c - 3.0) & (pos <= c + 3.0)
            if not win.any():
                continue
            gi = np.where(win, g, -1e9)
            j = int(np.argmax(gi))
            if g[j] < 4:
                continue
            o = _parab(g, j) - j
            pts.append((t + 0.5, pos[j] + o))
        if len(pts) >= 20:
            p_ = np.array(pts)
            keep = np.ones(len(p_), bool)
            for _ in range(2):
                q = np.polyfit(p_[keep, 0], p_[keep, 1], 1)
                keep = np.abs(p_[:, 1] - np.polyval(q, p_[:, 0])) <= 1.0
            out[side] = dict(l, k=float(q[0]), b=float(q[1]))
            mid = (lo_t + hi_t) / 2
            info[side] = dict(source="the default's edge", positions=int(len(pts)), used=int(keep.sum()),
                              shift_from_r5_px=round(float(np.polyval(q, mid) - (l["k"] * mid + l["b"])), 3))
        else:
            out[side] = l
            info[side] = dict(source="R5's staircase line (the default's print is dark along this side)", positions=int(len(pts)))
    return out, info


def _signed_inside(lines, X, Y):
    """per sample: the distance (px) inside the print area's four lines (negative outside), the minimum over the sides"""
    t, b, l_, r = lines["top"], lines["bottom"], lines["left"], lines["right"]
    d = np.minimum.reduce([Y - (t["k"] * X + t["b"]), (b["k"] * X + b["b"]) - Y, X - (l_["k"] * Y + l_["b"]), (r["k"] * Y + r["b"]) - X])
    return d


def framed_art_v2():
    """framed-art v2 (QA R5 3.5; the designer section 5): the seam between the default's walnut band and the variant's prints, along all
    six rails, anti-aliased. Each print area's four sides are ONE sub-pixel line each: fitted on the default's own moulding -> print edge
    where the default's print beside it is light (_default_edge_lines), else through R5's integer staircase. Per pixel the coverage (8 x 8
    samples) of three zones: the print (inside the lines), the default's inner line (the 1.2 px just outside them: the dark shadow line the
    default's top mouldings end with; its colour from the default's own whole pixels there) and the moulding (beyond: the default's own
    pixels, unchanged wherever a pixel is fully moulding). The print's colour next to the line is carried from 2.5 px inside it and 2 px
    inside R5's print area (a normalised blur, sigma 1.5, else 4: the render's light-oak frame was wider than the walnut band, as R5).
    R5's black lift on the prints, the same lift. Then the isolated light specks in the prints' black (L* > the 8 neighbours' median + 25
    with 7 of 8 neighbours black) take their neighbours' median colour"""
    Lc = f32(D(WR5, "layers", "framed-art-v2-cut.png"))
    Dd = f32(D(W.WORK, "layers", "framed-art.png"))
    ph = f32(D(WR5, "ph-p4", "layers", "framed-art.png"))
    inner = (np.abs(ph[..., :3] - Dd[..., :3]).max(2) > 1e-6) & (Dd[..., 3] > 0.5)
    rgb_c, a_c = Lc[..., :3], Lc[..., 3]
    # the print colour field: the render's print, carried out to the line from 2.5 px inside; R5's black lift (L* only)
    n, lb, st, _ = cv2.connectedComponentsWithStats(inner.astype(np.uint8))
    pieces = [i for i in range(1, n) if st[i, 4] > 5000]
    H, Wd = inner.shape
    w_print = np.zeros((H, Wd), np.float32)
    w_line = np.zeros((H, Wd), np.float32)
    dist_in = np.full((H, Wd), -99.0, np.float32)
    recs = {}
    LINE_W = 1.2
    LDd = lab(Dd[..., :3])[..., 0]
    for i in pieces:
        lines5, (x0, y0, x1, y1) = _side_lines(lb == i)
        lines, edge_info = _default_edge_lines(LDd, lines5)
        bx0, by0, bx1, by1 = x0 - 6, y0 - 6, x1 + 6, y1 + 6
        ys_, xs_ = np.mgrid[by0:by1, bx0:bx1].astype(np.float64)
        off = (np.arange(SS_ART) + 0.5) / SS_ART
        cp = np.zeros(ys_.shape)
        cl = np.zeros(ys_.shape)
        for oy in off:
            for ox in off:
                dd = _signed_inside(lines, xs_ + ox, ys_ + oy)
                cp += dd >= 0
                cl += (dd < 0) & (dd >= -LINE_W)
        w_print[by0:by1, bx0:bx1] = cp / SS_ART ** 2
        w_line[by0:by1, bx0:bx1] = cl / SS_ART ** 2
        dist_in[by0:by1, bx0:bx1] = _signed_inside(lines, xs_ + 0.5, ys_ + 0.5)
        recs[f"print area {len(recs) + 1} (x {x0}-{x1})"] = {k: dict(slope=round(v["k"], 5), offset=round(v["b"], 3), r5_staircase_steps=v["staircase_steps"],
                                                                      r5_staircase_rms_px=v["staircase_rms"], fit=edge_info[k]) for k, v in lines.items()}
    core = (dist_in >= 2.5) & X.ero(inner, 2)            # 2.5 px inside the new line AND 2 px inside R5's area (the render's oak frame)
    P, den = nblur(rgb_c, core.astype(np.float32), 1.5)
    P5, _ = nblur(rgb_c, core.astype(np.float32), 4.0)
    P = np.where((den > 1e-3)[..., None], P, P5)
    P = np.where(core[..., None], rgb_c, P)
    lift = json.load(open(D(WR5, "post-r5.json")))["framed-art-v2"]["blacks"]["lift_at_L5"]
    LP = lab(P)
    wl = np.clip((35.0 - LP[..., 0]) / 30.0, 0, 1)
    P = rgb_of(LP[..., 0] + lift * wl, LP[..., 1], LP[..., 2])
    # the specks: isolated light pixels in the prints' black
    LPn = lab(P)[..., 0]
    k8 = np.ones((3, 3), np.float32)
    k8[1, 1] = 0
    dark = (LPn < 25).astype(np.float32)
    ndark = cv2.filter2D(dark, -1, k8, borderType=cv2.BORDER_CONSTANT)
    stackn = np.stack([np.roll(np.roll(LPn, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], 0)
    med8 = np.median(stackn, 0)
    speck = (dist_in >= 1.0) & (ndark >= 7) & (LPn > med8 + 25)
    if speck.any():
        nb_rgb = np.stack([np.roll(np.roll(P, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], 0)
        P = np.where(speck[..., None], np.median(nb_rgb, 0), P)
    sy_, sx_ = np.nonzero(speck)
    # the default's own colours next to the line: the inner line (the pixels whose centre is 0.5-1.7 px outside it: whole pixels of the
    # default's band, its dark shadow line on the top rails, its moulding elsewhere) and the moulding beyond (centres 1.7+ px out)
    lin_px = (dist_in <= -0.5) & (dist_in >= -1.7) & (Dd[..., 3] > 0.3)       # straight alpha: the soft outer edge's colour is the moulding's
    Dk, dden = nblur(Dd[..., :3], lin_px.astype(np.float32), 1.5)
    Dk4, dden4 = nblur(Dd[..., :3], lin_px.astype(np.float32), 4.0)
    Dk = np.where((dden > 0.05)[..., None], Dk, np.where((dden4 > 1e-3)[..., None], Dk4, Dd[..., :3]))
    pure = (dist_in < -1.7) & (Dd[..., 3] > 0.3)
    M, mden = nblur(Dd[..., :3], pure.astype(np.float32), 1.0)
    M3, mden3 = nblur(Dd[..., :3], pure.astype(np.float32), 3.0)
    M = np.where((mden > 0.02)[..., None], M, np.where((mden3 > 1e-3)[..., None], M3, Dk))
    w_band = np.clip(1 - w_print - w_line, 0, 1)
    full_band = (w_band >= 0.999) & (dist_in > -98)
    mix = (w_band[..., None] * np.where(full_band[..., None], Dd[..., :3], M) + w_line[..., None] * Dk + w_print[..., None] * P)
    zone = dist_in > -98
    band_r5 = (Dd[..., 3] > 0) & ~inner
    rgb = np.where(band_r5[..., None], Dd[..., :3], rgb_c)                              # the band: the default's own pixels (as R5)
    rgb = np.where((zone & (dist_in >= 0))[..., None], P, rgb)                           # the prints
    rgb = np.where((zone & (dist_in >= -(LINE_W + 3)) & (dist_in < 3))[..., None], mix, rgb)   # the seam: the three zones' coverage
    a = np.where(band_r5 | (zone & (dist_in < 0)), Dd[..., 3], np.where(inner | (zone & (dist_in >= 0)), np.maximum(a_c, Dd[..., 3]), a_c))
    pl = save_layer("framed-art-v2", rgb, a)
    # measures (graded, the variant on the R6 stack): QA's rails and specks, the black median, the band identical to the default
    _, _, Gv = graded(variants={"framed-art": "framed-art-v2"})
    meas = art_measures(Gv)
    record("framed-art-v2", dict(what="the seam anti-aliased along every rail, the default's inner shadow line kept; the light specks out; R5's black lift",
                                 method=framed_art_v2.__doc__.replace("\n", " "), source=dict(cut=rel(D(WR5, "layers", "framed-art-v2-cut.png")),
                                                                                       default=rel(D(W.WORK, "layers", "framed-art.png"))),
                                 print_areas=recs, line_width_px=LINE_W, supersampling=SS_ART, black_lift_at_L5=lift,
                                 specks_fixed=[[int(x), int(y)] for y, x in zip(sy_, sx_)], measured=meas, file=rel(pl)))
    print(json.dumps(dict(specks=len(sx_), measured=meas), indent=1, default=float))


ART_RAILS = [("print 1 top", 1525, 1690, 528, 552), ("print 2 top", 1735, 1910, 512, 540), ("print 3 top", 1965, 2160, 500, 530),
             ("print 1 bottom", 1525, 1690, 772, 796), ("print 2 bottom", 1735, 1910, 772, 796), ("print 3 bottom", 1965, 2160, 776, 802)]


def _rail_profile(L, x0, x1, y0, y1, top, cols=None):
    """QA's r5_art_seam.rail_profile: per column the strongest frame -> print step, sub-pixel; a line fit; the residual and the jumps.
    cols: only these columns (the light-print ones: where the print beside the rail is black there is no frame -> print step to find)"""
    ys = []
    xs_used = [x for x in range(x0, x1) if cols is None or x in cols]
    for x in xs_used:
        col = L[y0:y1, x].astype(np.float64)
        g = np.diff(col) if top else -np.diff(col)
        i = int(np.argmax(g))
        if 0 < i < len(g) - 1:
            a_, b_, c_ = g[i - 1], g[i], g[i + 1]
            den = a_ - 2 * b_ + c_
            o = 0.5 * (a_ - c_) / den if abs(den) > 1e-6 else 0.0
        else:
            o = 0.0
        ys.append(y0 + i + 0.5 + float(np.clip(o, -0.5, 0.5)))
    ys = np.array(ys)
    xs = np.array(xs_used)
    k, b = np.polyfit(xs, ys, 1)
    r = ys - (k * xs + b)
    j = np.abs(np.diff(ys))
    return dict(residual_rms=round(float(np.sqrt((r ** 2).mean())), 3), residual_max=round(float(np.abs(r).max()), 2),
                jumps_ge_0_6=int((j >= 0.6).sum()), jumps_ge_1_0=int((j >= 1.0).sum()))


def art_measures(Gv):
    """QA's R5 art measures on the graded variant scene and the variant's own layer pixels: the rails, the isolated specks (layer: L* < 25
    black; light > median + 25 with 7 of 8 neighbours black), the blacks' median"""
    LV = cv2.cvtColor(Gv.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]
    LV = LV[..., 0]
    rails = {nm: _rail_profile(LV, x0, x1, y0, y1, "top" in nm) for nm, x0, x1, y0, y1 in ART_RAILS}
    rails_light = {}
    for nm, x0, x1, y0, y1 in ART_RAILS:
        yin = y1 + 6 if "top" in nm else y0 - 6                 # a row inside the print, past the rail's window
        cols = {x for x in range(x0, x1) if LV[yin, x] > 60 and LV[min(yin + (4 if "top" in nm else -4), LV.shape[0] - 1), x] > 60}
        rails_light[nm] = dict(_rail_profile(LV, x0, x1, y0, y1, "top" in nm, cols), columns=len(cols)) if len(cols) >= 20 else None
    Lp = f32(D(WR6, "layers", "framed-art-v2.png"))
    # the specks as QA counts them, on the graded scene inside the variant's alpha 255
    a = Lp[..., 3] >= 0.999
    black = (LV < 25) & a
    blk = cv2.morphologyEx(black.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    med = float(np.median(LV[black]))
    spk = blk & ~black & (LV > med + 25)
    k8 = np.ones((3, 3), np.float32)
    k8[1, 1] = 0
    nb = cv2.filter2D(black.astype(np.float32), -1, k8, borderType=cv2.BORDER_CONSTANT)
    iso = spk & (nb >= 7)
    inner_b = cv2.erode(black.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    return dict(rails_qa_as_is=rails, rails_light_print_columns=rails_light, specks_isolated=int(iso.sum()), light_px_inside_black=int(spk.sum()),
                light_px_inside_black_list=[[int(x), int(y)] for y, x in zip(*np.nonzero(spk))][:40],
                black_median_L=round(float(np.median(LV[inner_b])), 2))


# ================================================================================================= pendant 2
def latlong_map(cx, cy, z0, prof, nz=900, nt=2400, ss=2):
    """the clay lantern's surface coordinates per work pixel (the front surface, z-buffered): its height on the lantern (m from its
    bottom) and its angle; NaN off the lantern. The same projection as pass_r5.revolve (step 0's camera)"""
    Hs, Ws = SIZE[1] * ss, SIZE[0] * ss
    zb = np.full((Hs, Ws), np.inf, np.float32)
    zm = np.full((Hs, Ws), np.nan, np.float32)
    tm = np.full((Hs, Ws), np.nan, np.float32)
    dz = np.array([p[0] for p in prof], np.float32)
    rr = np.array([p[1] for p in prof], np.float32)
    zs = np.linspace(dz.min(), dz.max(), nz)
    ts = np.linspace(0, 2 * math.pi, nt)
    T, Zr = np.meshgrid(ts, zs)
    Rr = np.interp(Zr, dz, rr)
    drdz = np.gradient(np.interp(zs, dz, rr), zs)
    Dd = np.interp(Zr, zs, drdz)
    X_, Y_, Z_ = cx + Rr * np.cos(T), cy + Rr * np.sin(T), z0 + Zr
    nrm = np.stack([np.cos(T), np.sin(T), -Dd], -1)
    cam = np.array(S0.CAM["loc"], np.float32)
    view = cam[None, None, :] - np.stack([X_, Y_, Z_], -1)
    front = (nrm * view).sum(-1) > 0
    pts = [S0.P(float(x), float(y), float(z)) for x, y, z in zip(X_[front], Y_[front], Z_[front])]
    u = np.array([p[0] for p in pts]); v = np.array([p[1] for p in pts]); d = np.array([p[2] for p in pts])
    px = ((S0.CX + u * S0.CW) / S0.GW * Ws).astype(np.int32)
    py = ((S0.CY + v * S0.CH) / S0.GH * Hs).astype(np.int32)
    zz, tt = Zr[front], T[front]
    ok = (px >= 0) & (px < Ws) & (py >= 0) & (py < Hs)
    px, py, d, zz, tt = px[ok], py[ok], d[ok], zz[ok], tt[ok]
    order = np.argsort(-d)
    zb[py[order], px[order]] = d[order]
    zm[py[order], px[order]] = zz[order]
    tm[py[order], px[order]] = tt[order]
    # down to the work size: the mean of the samples that hit each pixel
    def down(m):
        v_ = np.where(np.isfinite(m), m, 0).reshape(SIZE[1], ss, SIZE[0], ss).sum((1, 3))
        n_ = np.isfinite(m).reshape(SIZE[1], ss, SIZE[0], ss).sum((1, 3))
        return np.where(n_ > 0, v_ / np.maximum(n_, 1), np.nan).astype(np.float32)
    return down(zm), down(tm)


def _nan_blur1d(M, w, sig, axis):
    """a normalised Gaussian blur of M (NaN where w == 0) along one axis"""
    k = int(max(3, round(3 * sig)))
    x = np.arange(-k, k + 1)
    g = np.exp(-0.5 * (x / max(sig, 1e-6)) ** 2)
    Mv = np.where(w > 0, M, 0.0)
    cv = lambda r: np.convolve(r, g, mode="full")[k:k + len(r)]  # noqa: E731  (zero padding; normalised by the weights)
    num = np.apply_along_axis(cv, axis, Mv * w)
    den = np.apply_along_axis(cv, axis, w)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), np.nan), den


def ring_profile(Lst, m, zm, tm, nb=120, ns=48, zmax=0.25):
    """the paper's L* per (sector, latitude bin): the median over the pixels of each cell (>= 6 px), and the cells' counts"""
    th0 = tm[m]
    tc = math.atan2(float(np.nanmean(np.sin(th0))), float(np.nanmean(np.cos(th0))))
    th = (th0 - tc + math.pi) % (2 * math.pi)                # the visible arc, contiguous (it may cross 0)
    t0, t1 = np.nanpercentile(th, 0.5), np.nanpercentile(th, 99.5)
    ti = np.clip(((th - t0) / max(t1 - t0, 1e-6) * ns).astype(int), 0, ns - 1)
    zi = np.clip((zm[m] / zmax * nb).astype(int), 0, nb - 1)
    M = np.full((ns, nb), np.nan)
    N = np.zeros((ns, nb))
    vals = Lst[m]
    key = ti * nb + zi
    order = np.argsort(key)
    ks, starts = np.unique(key[order], return_index=True)
    ends = list(starts[1:]) + [len(order)]
    for k_, s_, e_ in zip(ks, starts, ends):
        if e_ - s_ >= 6:
            M[k_ // nb, k_ % nb] = np.median(vals[order[s_:e_]])
            N[k_ // nb, k_ % nb] = e_ - s_
    tf = np.clip((th - t0) / max(t1 - t0, 1e-6) * ns - 0.5, 0, ns - 1)
    zf = np.clip(zm[m] / zmax * nb - 0.5, 0, nb - 1)
    return M, N, (t0, t1), ti, zi, tf, zf


def ring_residual(M, N, sig_z_bins, sig_t=1.5):
    """per sector the latitude profile's deviation from its own smooth course (sigma ~3 ring spacings along the latitude), smoothed
    across the sectors, its linear trend in z removed per sector (the light's top-to-bottom gradient stays)"""
    w = (N > 0).astype(np.float64)
    S, _ = _nan_blur1d(M, w, sig_z_bins, axis=1)
    R = np.where(w > 0, M - S, np.nan)
    Rs, den = _nan_blur1d(np.nan_to_num(R), w, sig_t, axis=0)
    zc = np.arange(M.shape[1], dtype=np.float64)
    for t in range(M.shape[0]):
        ok = (w[t] > 0) & np.isfinite(Rs[t])
        if ok.sum() >= 6:
            p = np.polyfit(zc[ok], Rs[t, ok], 1, w=N[t, ok])
            Rs[t] = Rs[t] - np.polyval(p, zc)
    return np.nan_to_num(Rs), S


def contour_snap(a, Lst, sel_fn, search=4.0, min_grad=2.5, smooth=3.0):
    """the alpha's 0.5 outline (at 4 x) moved along its normals to the render's own edge (the strongest L* step within +-search px,
    where it is at least min_grad L*/px) for the outline points sel_fn(x, y) selects; the offsets smoothed along the outline, then the
    outline itself (sigma `smooth` points); re-rasterised at 8 x and area-averaged (anti-aliased)"""
    up = cv2.resize(a.astype(np.float32), (SIZE[0] * 4, SIZE[1] * 4), interpolation=cv2.INTER_LINEAR)
    cs, _ = cv2.findContours((up > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float64) / 4.0 + 0.5 / 4 - 0.5      # pixel-centre coordinates
    c = c[::2]
    n = len(c)
    k = 7
    tx = np.roll(c[:, 0], -k) - np.roll(c[:, 0], k)
    ty = np.roll(c[:, 1], -k) - np.roll(c[:, 1], k)
    nrm = np.stack([ty, -tx], 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    # outward: the alpha falls along the normal
    probe = c + 1.5 * nrm
    av = cv2.remap(a.astype(np.float32), probe[:, 0].astype(np.float32).reshape(1, -1), probe[:, 1].astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
    av0 = cv2.remap(a.astype(np.float32), (c[:, 0] - 1.5 * nrm[:, 0]).astype(np.float32).reshape(1, -1),
                    (c[:, 1] - 1.5 * nrm[:, 1]).astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
    nrm[av > av0] *= -1
    ss = np.arange(-search, search + 1e-6, 0.25)
    off = np.zeros(n)
    used = np.zeros(n, bool)
    Lb = cv2.GaussianBlur(Lst.astype(np.float32), (0, 0), 0.7)
    for i in range(n):
        if not sel_fn(c[i, 0], c[i, 1]):
            continue
        px = (c[i, 0] + ss * nrm[i, 0]).astype(np.float32).reshape(1, -1)
        py = (c[i, 1] + ss * nrm[i, 1]).astype(np.float32).reshape(1, -1)
        prof = cv2.remap(Lb, px, py, cv2.INTER_LINEAR).ravel()
        g = np.abs(np.gradient(prof, 0.25))
        j = int(np.argmax(g))
        if g[j] >= min_grad:
            off[i], used[i] = ss[j], True
    w = used.astype(np.float64)
    k_ = int(3 * 4)
    x = np.arange(-k_, k_ + 1)
    gk = np.exp(-0.5 * (x / 4.0) ** 2)
    num = np.convolve(np.concatenate([off * w] * 3), gk, mode="same")[n:2 * n]
    den = np.convolve(np.concatenate([w] * 3), gk, mode="same")[n:2 * n]
    offs = np.where(den > 0.2, num / np.maximum(den, 1e-6), 0.0) * np.clip(den / 0.6, 0, 1)
    c2 = c + offs[:, None] * nrm
    ks = int(3 * smooth)
    x = np.arange(-ks, ks + 1)
    gs = np.exp(-0.5 * (x / smooth) ** 2)
    gs /= gs.sum()
    c3 = np.stack([np.convolve(np.concatenate([c2[:, j]] * 3), gs, mode="same")[n:2 * n] for j in (0, 1)], 1)
    S8 = 8
    canvas = np.zeros((SIZE[1] * S8, SIZE[0] * S8), np.uint8)
    cv2.fillPoly(canvas, [np.round((c3 + 0.5) * S8 - 0.5).astype(np.int32).reshape(-1, 1, 2)], 255)
    a2 = cv2.resize(canvas.astype(np.float32) / 255, SIZE, interpolation=cv2.INTER_AREA)
    return a2.astype(np.float32), dict(points=int(n), snapped=int(used.sum()), offset_px=dict(median=round(float(np.median(off[used])), 2) if used.any() else None,
                                                                                          p90_abs=round(float(np.percentile(np.abs(off[used]), 90)), 2) if used.any() else None))


RING_SPACING_M = 0.035        # the tiers the model drew: steps every ~3.5 cm of the lantern's height (the latitude profile)
OPEN_Z = 0.014                # the bottom opening (the clay's radius < 8.5 cm: the ring of the lamp holder the model drew)


def pendant_measures(G8, a_lan, zm, tm, top):
    """on the graded scene: the rings (the latitude profile's residual, the median over the sectors, per bin: its largest |value|),
    the pleats (the high-pass of L* across them, sigma 3 along the rows, std), the light (the paper's top third against its bottom
    third, median L*), the colour (median a*, b*), the opening (its brightest 1 % and median against the bottom third of the paper)"""
    LL = lab8(G8)
    m = (a_lan >= 0.999) & np.isfinite(zm) & (np.arange(a_lan.shape[0])[:, None] >= top + 3)
    m = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    paper = m & (np.nan_to_num(zm) >= OPEN_Z + 0.004)
    M, N = ring_profile(LL[..., 0], paper, zm, tm)[:2]
    zc = (np.arange(M.shape[1]) + 0.5) * 0.25 / M.shape[1]
    zks, Hs, _ = tier_fit(M, N, zc, thr=0.25)
    steps = {round(zk, 4): round(float(np.median(np.abs(Hs[Hs[:, k] != 0, k]))), 2) for k, zk in enumerate(zks) if (Hs[:, k] != 0).any()}
    for zk in TIER_Z:                                                   # the boundaries the R5 render had, measured there too
        zks2, Hs2, _ = [zk], *tier_fit_at(M, N, zc, zk)
        steps.setdefault(round(zk, 4), round(float(np.median(np.abs(Hs2[Hs2 != 0]))), 2) if (Hs2 != 0).any() else 0.0)
    rz = np.array(list(steps.values()) or [0.0])
    hp = LL[..., 0] - cv2.GaussianBlur(LL[..., 0], (0, 0), sigmaX=3.0, sigmaY=0.01)
    ys = np.nonzero(paper.any(1))[0]
    y0, y1 = ys.min(), ys.max() + 1
    third = (y1 - y0) / 3
    topm, botm = paper.copy(), paper.copy()
    topm[int(y0 + third):] = False
    botm[:int(y1 - third)] = False
    opening = m & (np.nan_to_num(zm, nan=1.0) < OPEN_Z)
    return dict(rings_max_abs_L=round(float(np.nanmax(np.abs(rz))), 2), ring_steps_L=steps,
                pleats_hp_std=round(float(hp[paper].std()), 3), light_top_minus_bottom_third=round(float(np.median(LL[..., 0][topm]) - np.median(LL[..., 0][botm])), 2),
                paper_a=round(float(np.median(LL[..., 1][paper])), 2), paper_b=round(float(np.median(LL[..., 2][paper])), 2),
                bottom_third_L=round(float(np.median(LL[..., 0][botm])), 2),
                opening=dict(px=int(opening.sum()), L_median=round(float(np.median(LL[..., 0][opening])), 2) if opening.any() else None,
                             L_p99=round(float(np.percentile(LL[..., 0][opening], 99)), 2) if opening.any() else None,
                             C_p99=round(float(np.percentile(np.hypot(LL[..., 1], LL[..., 2])[opening], 99)), 2) if opening.any() else None),
                paper_px=int(paper.sum()))


def pendant_v2():
    """pendant 2 (QA R5 3.6; the designer section 4, step 1). (1) The ceiling canopy re-cut whole: what differs from the ceiling (dE >
    3.5, closed), the largest piece, its convex hull, an ellipse fitted to it (a disc seen from below), rasterised at 8 x (fix_r4.
    canopy_cut's rule, with the shaded half of the disc kept: at dE > 6 only the lit two thirds passed). (2) The cord: one plumb line
    from the canopy's centre into the lantern's collar at the cord's own measured column, its alpha the cord's own cross-profile
    (R5's cut, the rows where it hangs alone); BLACK as the card ('black thin cord'): neutral, L* 15 with a soft highlight on the window
    side; the brown speck and anything else off the line are gone. (3) The lantern's outline snapped to the render's own edge (contour_snap)
    where the step is clear, then smoothed: the clay's facets out. (4) The rings: on the clay lantern's latitude lines (latlong_map) the
    paper's L* profile per sector; each step the model drew there (tier_fit: per sector a local fit of a step and its seam line at each
    boundary) replaced by the same rise spread over ~2 ring spacings and the seam line taken off (tier_correction), up to 3 rounds; then
    one linear ramp over the rows puts the paper's top and bottom thirds back to their medians (the light's course stays); L* only, a*b*
    unchanged. (5) The bottom opening (rendered off): not brighter than the paper's bottom third (a soft cap); the lamp holder's specks
    (over 6 L* above the opening round them) down to that surround and near-neutral"""
    regt = np.load(D(WR5, "p5-regt.npy")).astype(np.float32)
    below = PW.load(D(WR5, "scene-p5.png"))
    L5 = f32(D(WR5, "layers", "pendant-v2.png"))
    rgb5, a5 = L5[..., :3], L5[..., 3]
    top = int(json.load(open(D(WR5, "post-r5.json")))["pendant-v2"]["lantern_top_row"])
    # (1) the canopy
    bl = lambda x: cv2.GaussianBlur(np.clip(x, 0, 1).astype(np.float32), (0, 0), 0.8)  # noqa: E731
    dE = np.sqrt(((cv2.cvtColor(bl(regt), cv2.COLOR_RGB2LAB) - cv2.cvtColor(bl(below), cv2.COLOR_RGB2LAB)) ** 2).sum(2))
    box = np.zeros(a5.shape, bool)
    box[2:42, 1625:1735] = True
    cand = cv2.morphologyEx((box & (dE > 3.5)).astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    big = lbl == 1 + int(np.argmax(st[1:, 4]))
    hull_pts = cv2.convexHull(cv2.findNonZero(big.astype(np.uint8)))
    (ecx, ecy), (ew, eh), eang = cv2.fitEllipse(hull_pts)
    S8 = 8
    canv = np.zeros((SIZE[1] * S8, SIZE[0] * S8), np.uint8)
    cv2.ellipse(canv, ((ecx * S8 + (S8 - 1) / 2, ecy * S8 + (S8 - 1) / 2), (ew * S8, eh * S8), eang), 255, -1)
    a_can = cv2.resize(canv.astype(np.float32) / 255, SIZE, interpolation=cv2.INTER_AREA)
    # (2) the cord: its column and cross-profile from R5's cut where it hangs alone (rows 45-85, under the canopy, over the old sleeve)
    rows = range(45, 86)
    cx_ = float(np.median([(np.nonzero(a5[y] > 0.5)[0].min() + np.nonzero(a5[y] > 0.5)[0].max()) / 2.0 for y in rows]))
    c0, c1 = int(math.floor(cx_ - 6)), int(math.ceil(cx_ + 7))
    prof = np.median(a5[45:86, c0:c1], axis=0)
    xs_p = np.arange(c0, c1)
    cen = float((prof * xs_p).sum() / max(prof.sum(), 1e-6))
    hw = max(0.5 * float((prof > 0.5).sum()), 1.0)
    # the canopy's lower edge at the cord, the lantern's collar
    col = a_can[:, int(round(cen))]
    can_bot = int(np.nonzero(col > 0.5)[0].max())
    y_cord0, y_cord1 = can_bot - 3, top + 4
    a_cord = np.zeros(a5.shape, np.float32)
    a_cord[y_cord0:y_cord1, c0:c1] = prof[None, :]
    t = (xs_p + 0.5 - (cen + 0.5)) / hw
    Lc = 15.0 + 7.0 * np.exp(-((t + 0.35) / 0.35) ** 2)
    cord_rgb = rgb_of(np.repeat(Lc[None, :], 1, 0).astype(np.float32), np.zeros((1, len(xs_p)), np.float32), np.zeros((1, len(xs_p)), np.float32))[0]
    # (3) the lantern's outline
    a_lan = a5.copy()
    a_lan[:top] = 0
    Lst = lab(regt)[..., 0]
    zm, tm = latlong_map(0.20, 1.72, 1.90, R.PROF_PUMPKIN)
    a_lan2, snap = contour_snap(a_lan, Lst, lambda x, y: y >= top + 2)
    a_lan2[:top] = 0
    # (4) the rings
    lab_r = lab(regt)
    m = (a_lan2 > 0.5) & np.isfinite(zm) & (np.arange(a5.shape[0])[:, None] >= top)
    paper = m & (np.nan_to_num(zm) >= OPEN_Z)
    Lwork = lab_r[..., 0].astype(np.float64).copy()
    corr = np.zeros(a5.shape, np.float64)
    zpx = zm[paper].astype(np.float64)
    tiers = []
    for rnd in range(3):
        M, N, (t0, t1), ti, zi, tf, zf = ring_profile(Lwork, paper, zm, tm)
        zc = (np.arange(M.shape[1]) + 0.5) * 0.25 / M.shape[1]
        zks, Hs, Zs = tier_fit(M, N, zc, thr=0.5 if rnd == 0 else 0.25)
        keep = [k for k in range(len(zks)) if (Hs[:, k] != 0).any() and np.median(np.abs(Hs[Hs[:, k] != 0, k])) >= (0.5 if rnd == 0 else 0.3)]
        if not keep:
            break
        c = tier_correction(zpx, tf, [zks[k] for k in keep], Hs[:, keep], Zs[:, keep], TIER_LINES[0][:, keep])
        Lwork[paper] -= c
        corr[paper] += c
        tiers.append(dict(round=rnd, boundaries_z_m=[round(zks[k], 4) for k in keep],
                          step_L_median=[round(float(np.median(Hs[Hs[:, k] != 0, k])), 2) for k in keep]))
    # the light's course kept: the paper's top and bottom thirds (rows) back to their medians, by one linear ramp over the rows
    ys_ = np.nonzero(paper.any(1))[0]
    y0p, y1p = ys_.min(), ys_.max() + 1
    th_ = (y1p - y0p) / 3
    rows_px = np.nonzero(paper)[0].astype(np.float64)
    topm_, botm_ = rows_px < y0p + th_, rows_px >= y1p - th_
    L0p, L1p = lab_r[..., 0][paper].astype(np.float64), Lwork[paper]
    d_top = float(np.median(L1p[topm_]) - np.median(L0p[topm_]))
    d_bot = float(np.median(L1p[botm_]) - np.median(L0p[botm_]))
    yt, yb_ = y0p + th_ / 2, y1p - th_ / 2
    ramp = d_top + (d_bot - d_top) * np.clip((rows_px - yt) / max(yb_ - yt, 1), -0.5, 1.5)
    corr[paper] += ramp
    Lwork[paper] -= ramp
    corr = corr.astype(np.float32)
    cw = paper.astype(np.float32)
    ce, cden = nblur(corr, cw, 2.0)
    corr_f = np.where(paper, corr, np.where((cden > 0.02) & (a_lan2 > 0), ce, 0.0)).astype(np.float32)
    Ln = lab_r[..., 0] - corr_f
    An, Bn = lab_r[..., 1].copy(), lab_r[..., 2].copy()
    # (5) the opening: not brighter than the paper's bottom third; the holder's specks neutral
    ys = np.nonzero(paper.any(1))[0]
    y0p, y1p = ys.min(), ys.max() + 1
    botm = paper.copy()
    botm[:int(y1p - (y1p - y0p) / 3)] = False
    cap = float(np.median(Ln[botm])) - 1.5                           # a margin for the grade
    opening = (a_lan2 > 0) & (np.nan_to_num(zm, nan=1.0) < OPEN_Z) & (np.arange(a5.shape[0])[:, None] >= top + 20)
    opening = X.dil(opening, 1) & (a_lan2 > 0) & ~paper
    # the holder's specks: brighter than the opening round them (a normalised blur, sigma 4) by more than 6 L*: down to that
    # surround - 2 (the holder is in the lantern's shade) and near-neutral, with a soft weight (3-6 L* over it) so no hard rim
    loc, _ = nblur(Ln, opening.astype(np.float32), 4.0)
    dd = np.where(opening, Ln - loc, 0.0)
    w_hot = np.clip((dd - 3.0) / 3.0, 0, 1) * opening
    hot = w_hot > 0.5
    Ln = Ln * (1 - w_hot) + (loc - 2.0) * w_hot
    An = An * (1 - 0.75 * w_hot)
    Bn = Bn * (1 - 0.75 * w_hot)
    soft = np.where(Ln > cap, cap + 0.8 * np.tanh((Ln - cap) / 0.8), Ln)    # a soft cap: never above the paper's bottom third
    Ln = np.where(opening, soft, Ln)                                  # under it the opening keeps its own shading
    rgb_lan = rgb_of(np.clip(Ln, 0, 100), An, Bn)
    # the layer: the canopy, the cord over it, the lantern over the cord
    rgb = regt.copy()
    a = a_can.copy()
    rgb[y_cord0:y_cord1, c0:c1] = np.where((a_cord[y_cord0:y_cord1, c0:c1] > 0)[..., None],
                                           (cord_rgb[None, :, :] * a_cord[y_cord0:y_cord1, c0:c1, None] +
                                            rgb[y_cord0:y_cord1, c0:c1] * (a[y_cord0:y_cord1, c0:c1, None] * (1 - a_cord[y_cord0:y_cord1, c0:c1, None]))) /
                                           np.maximum(a_cord[y_cord0:y_cord1, c0:c1, None] + a[y_cord0:y_cord1, c0:c1, None] * (1 - a_cord[y_cord0:y_cord1, c0:c1, None]), 1e-4),
                                           rgb[y_cord0:y_cord1, c0:c1])
    a = a_cord + a * (1 - a_cord)
    al = a_lan2
    rgb = np.where((al > 0)[..., None], (rgb_lan * al[..., None] + rgb * (a * (1 - al))[..., None]) / np.maximum(al + a * (1 - al), 1e-4)[..., None], rgb)
    a = al + a * (1 - al)
    pl = save_layer("pendant-v2", rgb, a)
    # measures: R5 against R6, on the graded scene with the variant
    sh = f32(D(WR5, "shadows", "pendant-v2.png"), "L")
    _, _, G5 = graded(variants={"pendant": "pendant-v2"}, override={"pendant": (rgb5, a5, None, sh)})
    _, _, G6 = graded(override={"pendant": (rgb, a, None, sh)})
    m5, m6 = pendant_measures(G5, a_lan2, zm, tm, top), pendant_measures(G6, a_lan2, zm, tm, top)
    LL6 = lab8(G6)
    hot_m = hot & (a >= 0.999)
    spk5 = round(float(np.median(np.hypot(lab8(G5)[..., 1], lab8(G5)[..., 2])[hot_m])), 2) if hot_m.any() else 0.0
    spk6 = round(float(np.median(np.hypot(lab8(G6)[..., 1], lab8(G6)[..., 2])[hot_m])), 2) if hot_m.any() else 0.0
    cordm = (a_cord >= 0.99) & (a_lan2 < 0.01) & (a_can < 0.01)
    cord_meas = dict(L_median=round(float(np.median(LL6[..., 0][cordm])), 2), C_median=round(float(np.median(np.hypot(LL6[..., 1], LL6[..., 2])[cordm])), 2),
                     px=int(cordm.sum()))
    # the canopy against the cord
    tg = {"rings: the latitude profile's residual <= 1 L* end to end": dict(value=m6["rings_max_abs_L"], before=m5["rings_max_abs_L"], pass_=m6["rings_max_abs_L"] <= 1.0),
          "pleats: high-pass std within +-10 %": dict(value=round(m6["pleats_hp_std"] / m5["pleats_hp_std"] - 1, 4), pass_=abs(m6["pleats_hp_std"] / m5["pleats_hp_std"] - 1) <= 0.10),
          "light: top third - bottom third within +-1 L*": dict(value=round(m6["light_top_minus_bottom_third"] - m5["light_top_minus_bottom_third"], 2),
                                                                 pass_=abs(m6["light_top_minus_bottom_third"] - m5["light_top_minus_bottom_third"]) <= 1.0),
          "colour: a*b* unchanged (+-0.5)": dict(value=[round(m6["paper_a"] - m5["paper_a"], 2), round(m6["paper_b"] - m5["paper_b"], 2)],
                                                  pass_=abs(m6["paper_a"] - m5["paper_a"]) <= 0.5 and abs(m6["paper_b"] - m5["paper_b"]) <= 0.5),
          "opening: not brighter than the paper's bottom third": dict(value=dict(opening_L_p99=m6["opening"]["L_p99"], bottom_third_L=m6["bottom_third_L"]),
                                                                      pass_=(m6["opening"]["L_p99"] or 0) <= m6["bottom_third_L"] + 0.5),
          "opening: the holder's specks neutral (their C* median <= 3)": dict(value=dict(r5=spk5, r6=spk6), pass_=spk6 <= 3.0),
          "cord: black (L* <= 25, C* <= 3)": dict(value=cord_meas, pass_=cord_meas["L_median"] <= 25 and cord_meas["C_median"] <= 3)}
    record("pendant-v2", dict(
        what="the canopy re-cut whole and centred, the right outline snapped, the cord's speck out, the cord black, the paper's rings out",
        method=pendant_v2.__doc__.replace("\n", " "), source=dict(render=rel(D(WR5, "p5-regt.npy")), r5_layer=rel(D(WR5, "layers", "pendant-v2.png"))),
        canopy=dict(ellipse_centre_px=[round(ecx, 2), round(ecy, 2)], ellipse_axes_px=[round(ew, 2), round(eh, 2)], angle_deg=round(eang, 2),
                    cord_x_px=round(cen, 2), centre_minus_cord_px=round(ecx - cen, 2), hull_px=int(big.sum()),
                    box_px=[int(np.nonzero(a_can > 0.5)[1].min()), int(np.nonzero(a_can > 0.5)[0].min()),
                            int(np.nonzero(a_can > 0.5)[1].max()) + 1, int(np.nonzero(a_can > 0.5)[0].max()) + 1]),
        cord=dict(column_px=round(cen, 2), half_width_px=round(hw, 2), rows=[y_cord0, y_cord1], L_profile=[round(float(v), 1) for v in Lc],
                  measured_graded=cord_meas, card="black thin cord"),
        outline=snap, rings=dict(model="tier_fit / tier_correction: each step the model drew on a latitude line, per sector, replaced by the same "
                                       "rise spread over ~2 ring spacings (0.5 (1 + tanh((z - zk) / %.3f)))" % STEP_SOFT, tiers=tiers,
                                 sectors=48, latitude_bins=120,
                                 correction_L=dict(p5=round(float(np.percentile(corr[paper], 5)), 2), p95=round(float(np.percentile(corr[paper], 95)), 2))),
        opening=dict(cap_L_ungraded=round(cap, 2), px=int(opening.sum()), hot_px=int(hot.sum())),
        measured_r5=m5, measured_r6=m6, targets=tg, all_met=all(v["pass_"] for v in tg.values()), file=rel(pl)))
    print(json.dumps(dict(canopy=dict(c=[ecx, ecy], ax=[ew, eh], cord=cen), r5=m5, r6=m6, targets=tg), indent=1, default=float))


STEP_W = 0.0015        # a tier's step in the render: ~1 px across (m of the lantern's height)
LINE_W = 0.0025        # the seam line the model drew along a tier's edge (a Gaussian, m of the height)
TIER_LINES = []        # tier_fit's seam-line amplitudes (sectors x boundaries) of its last call
STEP_SOFT = 0.03       # the same step spread over ~2 ring spacings (0.5 (1 + tanh((z - zk) / 0.03)))


def _sstep(z, zk, w):
    return 0.5 * (1 + np.tanh((z - zk) / w))


def tier_fit(M, N, zc, win=8, thr=0.5):
    """the tiers in the latitude profiles. The boundaries zk: where the sectors' median derivative peaks, at least thr L* per bin and
    8 bins apart. Then per sector and boundary a local least squares on +-win bins (>= 4 measured bins each side): L(z) = a +
    b (z - zk) + hk step(z - zk), zk refined within +-2 bins; |hk| <= 15; the hk smoothed across the sectors (normalised, sigma 1.5)"""
    w = (N > 0) & np.isfinite(M)
    dM = np.diff(M, axis=1)
    g = np.array([np.nanmedian(dM[:, j]) if np.isfinite(dM[:, j]).sum() >= 0.4 * M.shape[0] else 0.0 for j in range(dM.shape[1])])
    g = np.convolve(np.nan_to_num(g), [0.25, 0.5, 0.25], mode="same")
    order = np.argsort(-np.abs(g))
    picked = []
    for j in order:
        if abs(g[j]) < thr:
            break
        if all(abs(j - p) >= 8 for p in picked):
            picked.append(int(j))
    zks = sorted(float((zc[j] + zc[j + 1]) / 2) for j in picked)
    dz = zc[1] - zc[0]
    H = np.zeros((M.shape[0], len(zks)))
    Hw = np.zeros((M.shape[0], len(zks)))
    Ln_ = np.zeros((M.shape[0], len(zks)))
    Z = np.tile(np.array(zks, np.float64), (M.shape[0], 1))
    for t in range(M.shape[0]):
        for k, zk0 in enumerate(zks):
            best = None
            for sh in np.linspace(-2, 2, 9) * dz:
                zk = zk0 + sh
                sel = w[t] & (np.abs(zc - zk) <= win * dz)
                lo, hi = sel & (zc < zk - 0.5 * dz), sel & (zc > zk + 0.5 * dz)
                if lo.sum() < 4 or hi.sum() < 4:
                    continue
                z, y, wt = zc[sel] - zk, M[t, sel], np.sqrt(N[t, sel])
                A = np.stack([np.ones_like(z), z, _sstep(z, 0.0, STEP_W), np.exp(-(z / LINE_W) ** 2)], 1)
                sol, *_ = np.linalg.lstsq(A * wt[:, None], y * wt, rcond=None)
                r = float((((A @ sol) - y) ** 2 * wt ** 2).sum())
                if best is None or r < best[0]:
                    best = (r, float(np.clip(sol[2], -15, 15)), zk, float(np.clip(sol[3], -15, 15)))
            if best is not None:
                H[t, k], Hw[t, k], Z[t, k], Ln_[t, k] = best[1], 1.0, best[2], best[3]
    kk = np.exp(-0.5 * (np.arange(-4, 5) / 1.5) ** 2)
    Hs, Ls = np.zeros_like(H), np.zeros_like(H)
    for k in range(len(zks)):
        den = np.convolve(Hw[:, k], kk, mode="same")
        Hs[:, k] = np.where(Hw[:, k] > 0, np.convolve(H[:, k] * Hw[:, k], kk, mode="same") / np.maximum(den, 1e-6), 0.0)
        Ls[:, k] = np.where(Hw[:, k] > 0, np.convolve(Ln_[:, k] * Hw[:, k], kk, mode="same") / np.maximum(den, 1e-6), 0.0)
    TIER_LINES.clear()
    TIER_LINES.append(Ls)
    return zks, Hs, Z


def tier_correction(zpx, tpx, zks, Hs, Zs, Ls=None):
    """per pixel: each sharp step replaced by the same step spread over ~2 ring spacings (no overshoot, the top-to-bottom light kept),
    and the seam line along it taken off"""
    ns = Hs.shape[0]
    t0 = np.clip(np.floor(tpx).astype(int), 0, ns - 1)
    t1 = np.clip(t0 + 1, 0, ns - 1)
    ft = np.clip(tpx - t0, 0, 1)
    c = np.zeros_like(zpx)
    for k in range(len(zks)):
        h = Hs[t0, k] * (1 - ft) + Hs[t1, k] * ft
        zk = Zs[t0, k] * (1 - ft) + Zs[t1, k] * ft
        c += h * (_sstep(zpx, zk, STEP_W) - _sstep(zpx, zk, STEP_SOFT))
        if Ls is not None:
            ln = Ls[t0, k] * (1 - ft) + Ls[t1, k] * ft
            c += ln * np.exp(-((zpx - zk) / LINE_W) ** 2)
    return c


TIER_Z = (0.0365, 0.0688, 0.1042)    # the tiers' boundaries in the R5 render (tier_fit on p5-regt; the measure checks them by name)


def tier_fit_at(M, N, zc, zk0, win=8):
    """one boundary's step per sector (tier_fit's local least squares, zk within +-2 bins)"""
    w = (N > 0) & np.isfinite(M)
    dz = zc[1] - zc[0]
    H = np.zeros(M.shape[0])
    Z = np.full(M.shape[0], zk0)
    for t in range(M.shape[0]):
        best = None
        for sh in np.linspace(-2, 2, 9) * dz:
            zk = zk0 + sh
            sel = w[t] & (np.abs(zc - zk) <= win * dz)
            lo, hi = sel & (zc < zk - 0.5 * dz), sel & (zc > zk + 0.5 * dz)
            if lo.sum() < 4 or hi.sum() < 4:
                continue
            z, y, wt = zc[sel] - zk, M[t, sel], np.sqrt(N[t, sel])
            A = np.stack([np.ones_like(z), z, _sstep(z, 0.0, STEP_W), np.exp(-(z / LINE_W) ** 2)], 1)
            sol, *_ = np.linalg.lstsq(A * wt[:, None], y * wt, rcond=None)
            r = float((((A @ sol) - y) ** 2 * wt ** 2).sum())
            if best is None or r < best[0]:
                best = (r, float(np.clip(sol[2], -15, 15)), zk)
        if best is not None:
            H[t], Z[t] = best[1], best[2]
    return H, Z


# ================================================================================================= the magazine holder's rods
def rods_edge():
    """the rods' soft edge (the designer's pre-approved fix, eye section 8; QA R5 4). R5 recoloured each rod's pixels within its half
    width + 1.5 px of the fitted line, but only those of C* <= 14: where the black rod meets the leather, the edge pixels (part rod,
    part cognac leather) were left black-and-leather, the dark broken line under the front rod at x 2. Here each rod's two edges are
    measured on its R1 render (per column, off the tubes: the sub-pixel crossing of half way between the rod's core L* and the
    neighbour's 4 px beyond; the median over the columns), so each pixel's rod share f is geometric: f = clip(E - |d| + 0.5, 0, 1) (d
    its distance from the line, E that side's edge). In the edge band (|d| from E - 1 to E + 1.5, off the tubes) the rod's black is
    replaced by R5's satin silver S of the nearest full rod pixel, in linear RGB: c' = c_R1 + f (S - K), K the R1 rod's black (its
    core's median). Alpha, the tubes, the leather beyond, the rest of R5's rods and the shadow: unchanged"""
    L1 = f32(F5.MH_LAYER)
    rgb1, a = L1[..., :3], L1[..., 3]
    L5 = f32(D(WR5, "layers", "magazine-holder.png"))
    rgb5 = L5[..., :3]
    Mk, info = F5.rod_masks(rgb1, a)
    lin1, lin5 = PW.s2l(rgb1).astype(np.float64), PW.s2l(rgb5).astype(np.float64)
    out = lin5.copy()
    H, Wd = a.shape
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float64)
    Lw = lab(rgb1)
    Cw = np.hypot(Lw[..., 1], Lw[..., 2])
    dark = (a > 0.3) & (Lw[..., 0] < 34) & (Cw < 12)
    rec = {}
    changed = np.zeros(a.shape, bool)
    for nm, r in Mk.items():
        k_, b_ = info[nm]["line_y_eq_ax_plus_b"]
        hw = info[nm]["half_width_px"]
        x0, x1 = info[nm]["x_span"]
        cosn = 1.0 / math.hypot(k_, 1.0)
        dist = (yy - (k_ * xx + b_)) * cosn
        tube = dark & (np.abs(dist) > hw + 2)
        tube = cv2.morphologyEx(tube.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(2 * hw + 9)))) > 0
        tube = X.dil(tube, 2)
        core = r["mask"] & (np.abs(dist) <= hw - 1.0) & (a >= 0.999) & ~tube
        K = np.median(lin1[core], 0)
        Lcore = float(np.median(Lw[..., 0][core]))
        # the edges, per side: along each column, the crossing of half way between the core and the neighbour 4 px beyond
        E = {}
        for side in (-1, 1):
            es = []
            for x in range(x0 + 3, x1 - 3, 1):
                yc = k_ * x + b_
                ys = np.arange(int(yc - side * 1) if side > 0 else int(yc + 1), int(yc + side * (hw + 7)), side)
                if ys.min() < 0 or ys.max() >= H or tube[ys, x].any():
                    continue
                prof = Lw[..., 0][ys, x]
                dd = (ys - yc) * cosn * side
                out_i = np.argmin(np.abs(dd - (hw + 4)))
                thr = 0.5 * (Lcore + prof[out_i])
                if prof[out_i] - Lcore < 8:
                    continue
                j = next((i for i in range(1, len(prof)) if prof[i - 1] < thr <= prof[i] and dd[i] > hw - 2.5), None)
                if j is None:
                    continue
                es.append(dd[j - 1] + (thr - prof[j - 1]) / max(prof[j] - prof[j - 1], 1e-6) * (dd[j] - dd[j - 1]))
            E[side] = float(np.median(es)) if len(es) >= 10 else hw + 0.5
            rec.setdefault(nm, {})[f"edge_{'upper' if side < 0 else 'lower'}_px"] = dict(value=round(E[side], 3), columns=len(es))
        Ed = np.where(dist < 0, E[-1], E[1])
        f = np.clip(Ed - np.abs(dist) + 0.5, 0, 1)
        band = (np.abs(dist) >= Ed - 1.0) & (np.abs(dist) <= Ed + 1.5) & (a > 0.02) & ~tube & (xx >= x0) & (xx <= x1) & (f > 0)
        full = r["mask"] & (np.abs(dist) <= Ed - 1.0)
        _, lbl = cv2.distanceTransformWithLabels((~full).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        ry, rx = np.nonzero(full)
        lut = np.zeros((lbl.max() + 1, 2), np.int64)
        lut[lbl[ry, rx]] = np.stack([ry, rx], 1)
        cy_, cx_ = np.nonzero(band)
        nr = lut[lbl[cy_, cx_]]
        S = lin5[nr[:, 0], nr[:, 1]]
        newc = np.clip(lin1[cy_, cx_] + f[cy_, cx_][:, None] * (S - K[None, :]), 0, 1)
        out[cy_, cx_] = newc
        changed[cy_, cx_] = True
        rec[nm].update(edge_band_px=int(band.sum()), rod_share_median=round(float(np.median(f[band])), 3) if band.any() else None,
                       black_K_srgb=[round(float(v), 4) for v in PW.l2s(K.reshape(1, 1, 3).astype(np.float32)).ravel()], core_L=round(Lcore, 2))
    rgb_n = np.clip(PW.l2s(out.astype(np.float32)), 0, 1).astype(np.float32)
    pl = save_layer("magazine-holder", rgb_n, a)
    # the black left on the rods' edges, before and after (graded set-B scene): within 3 px of a rod's R5 pixels (off the tubes), the
    # near-black neutral pixels (L* < 24, C* < 10: the R1 rod's black; the leather is L* 28-34 and chromatic, the satin edge >= 35)
    tubes_all = np.zeros(a.shape, bool)
    for nm, r in Mk.items():
        k_, b_ = info[nm]["line_y_eq_ax_plus_b"]
        hw = info[nm]["half_width_px"]
        dist_ = (yy - (k_ * xx + b_)) / math.hypot(k_, 1.0)
        tb = dark & (np.abs(dist_) > hw + 2)
        tb = cv2.morphologyEx(tb.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(2 * hw + 9)))) > 0
        tubes_all |= X.dil(tb, 2)

    def dark_line(G8):
        """pixels on a rod's edge darker by 4 L* than both the rod's own edge 2 px inside and the neighbour 2 px outside (a dark line
        between two lighter things); off the tubes"""
        LL = lab8(G8)[..., 0].astype(np.float32)
        n_ = dict(darker_than_both_sides_by_4=0, below_L25=0, band_px=0)
        for nm, r in Mk.items():
            k_, b_ = info[nm]["line_y_eq_ax_plus_b"]
            x0, x1 = info[nm]["x_span"]
            cosn = 1.0 / math.hypot(k_, 1.0)
            nrm = np.array([-k_, 1.0]) * cosn
            dist_ = (yy - (k_ * xx + b_)) * cosn
            for side in (-1, 1):
                Es = rec[nm][f"edge_{'upper' if side < 0 else 'lower'}_px"]["value"]
                band_ = (side * dist_ >= Es - 1.0) & (side * dist_ <= Es + 1.0) & (a > 0.02) & ~tubes_all & (xx >= x0) & (xx <= x1)
                cy_, cx_ = np.nonzero(band_)
                ins = cv2.remap(LL, (cx_ - 2 * side * nrm[0]).astype(np.float32).reshape(1, -1), (cy_ - 2 * side * nrm[1]).astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
                outs = cv2.remap(LL, (cx_ + 2 * side * nrm[0]).astype(np.float32).reshape(1, -1), (cy_ + 2 * side * nrm[1]).astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
                n_["darker_than_both_sides_by_4"] += int((LL[cy_, cx_] < np.minimum(ins, outs) - 4).sum())
                n_["below_L25"] += int((LL[cy_, cx_] < 25).sum())
                n_["band_px"] += int(len(cy_))
        return n_
    _, _, G5 = graded(override={"magazine-holder": (rgb5, a, None, f32(D(WR5, "shadows", "magazine-holder.png"), "L"))})
    _, _, G6 = graded(override={"magazine-holder": (rgb_n, a, None, f32(D(WR5, "shadows", "magazine-holder.png"), "L"))})
    record("magazine-holder", dict(what="the rods' satin silver carried into their soft edge (the dark line under the front rod)",
                                   method=rods_edge.__doc__.replace("\n", " "), source=dict(r1=rel(F5.MH_LAYER), r5=rel(D(WR5, "layers", "magazine-holder.png")),
                                                                                       shadow=rel(D(WR5, "shadows", "magazine-holder.png")) + " (unchanged)"),
                                   rods=rec, dark_line_px=dict(r5=dark_line(G5), r6=dark_line(G6)), changed_px=int(changed.sum()), file=rel(pl)))
    print(json.dumps(dict(rods=rec, dark_line=json.load(open(REC))["magazine-holder"]["dark_line_px"]), indent=1))


STEPS = [("curtains", curtains), ("rods", rods_edge), ("vase", vase), ("vase-v2", vase_v2), ("curtains-v2", curtains_v2),
         ("art", framed_art_v2), ("pendant", pendant_v2)]

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in STEPS:
        if what in (name, "all"):
            print("==", name, flush=True)
            fn()
