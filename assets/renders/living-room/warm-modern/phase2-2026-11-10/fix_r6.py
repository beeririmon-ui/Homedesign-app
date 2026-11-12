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
  vase        the default (4'): re-cut from the registered raw render (work-r5/p4-regt.npy): a difference matte against the scene behind
              (known: work-r5/scene-p4.png), and, the vase being a solid of revolution, its left (lit) flank checked against the mirror
              of its right edge about the axis; then the size against the card at the point; then R5's a*b* fix (the same dh and k);
              the contact shadow by the frozen recipe (extract.shadow_one) on the new cut
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
    frequencies back x g, g = (L*180502 + 16) / (L*554205 + 16) clipped to 1-1.2 (a brighter cloth shows the same folds as larger L*
    steps), lowered if the high-pass leaves 3.1-4.2. (2) The colour after the lightness: a*b* by R5's method (one hue rotation, one chroma
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
    high = lab_w[..., 0] - low554
    g = float(np.clip((s180["L"] + 16) / (s0["L"] + 16), 1.0, 1.2))
    off = 0.0
    hist_L = []

    def lightness(off, g):
        Ln = curve(low554, off) + g * high
        Ln = np.where(Ln > 92, 92 + 4 * np.tanh((Ln - 92) / 4), Ln)          # a soft shoulder: never a burnt fold (target 5)
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
                        shoulder="L > 92: 92 + 4 tanh((L - 92) / 4)", iterations=hist_L),
        ab=dict(dh_deg=round(dh, 3), k=round(k, 4), target=dict(C=want_C, h=want_h), iterations=hist_ab),
        post_line=dict(fringe_px=int(fringe.sum())), after=sf, after_own_mask=sf_own, targets=tg, all_met=all(v["pass_"] for v in tg.values()),
        file=rel(pl)))
    print(json.dumps(dict(ref=s180, before=s0, after=sf, targets=tg), indent=1, default=float))
