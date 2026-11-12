#!/usr/bin/env python3
"""
fix_r7.py: R7, the 0-token code part (A) on the warm-modern tool layers (render-agent, 2026-11-12).
Brief: briefs/render-wm-tool-r7-2026-11-12.md; the designer: docs/proposals/owner-answers-applied-2026-11-12.md (sections 1, 6, 8);
slots 1.9.4, house plan 1.3.6. Code only: 0 tokens, no var2, no network. NEW FILES ONLY: work-r7/ (ungraded per-product layers and
shadows, the same form as work-r6/) and work-r7/fix-r7.json; grade_cut_r7.py grades and cuts them with the ONE v3c grade.

  planter       section 8: ONE factor k = 0.78 on R, G and B in linear light on the pot's body in the planter layer (the pot without the
                soil, the trunk and the crown; the pixels under the basket's edge included, so no light fringe shows along the basket),
                feathered 2 px at the inner boundary; the edge pixels get it through their own alpha (straight alpha: rgb x f is
                premultiplied rgb x a x f), so no light rim forms against the wall. Shadow unchanged. Targets measured on the graded set-B
                scene with QA R5's masks (qa/reports/2026-11-11-wm-tool-phase2-r5/tools/r5_designer_targets.py)
  curtains      section 6.3, 180502 (the default) and 554205 (curtains-v2, after its R6 L* fix): the sold length. One cut for both (only the
                hem's height differs: Z 0.12 for 270): below the hem (the free part beyond the bench end, u <= 0.020, and the overscan
                beyond it, along the stack's front face) and below the bench-top contact line (Z 0.45 on X -2.15, u 0.020-0.065, extended
                under the armchair) the free alpha is 0 (anti-aliased, ramp <= 1 px at 2720 = 1.5 px at 3840); the corner at the bench end
                spills over the stone arc as a short diagonal (5.3 px = 8 at 3840); the hem wobbles with the folds (<= 2 px = 3 at 3840);
                the hem band (3 cm = 18 px) L* -2; the break over the bench (the last 5 px = 7.5 at 3840) L* -4 softened; the shadow: the
                floor contact line removed, a soft shade under the hem on the end face (<= 6 %, gone 17 px = 25 at 3840 below the hem,
                blurred), a contact line on the stone (3.3 px = 5 at 3840, multiply 0.925, blur 2 = 3 at 3840)
  curtains-v3   the same cut at Z 0.22 (260), on 7''s cut (pass_r7.py), after its colour fix
  table group   section 1.5: the rendered defaults move with their shadows about each piece's contact point (the foot's bottom centre):
                travertine A du -0.0294 dv -0.0063 s 0.982, B du -0.0302 dv -0.0063 s 0.982, the black bowl du -0.0285 dv -0.0065 s 0.983
                (checked with step 0's P(): the plan points (0.33, 1.74) -> (0.205, 1.74), (0.48, 1.68) -> (0.355, 1.68),
                (0.72, 1.94) -> (0.62, 1.94)). The contact shadow is the frozen recipe's field (extract.shadow_one, measured on the step-3 /
                R2 renders) carried with its piece (premultiplied, INTER_AREA) and re-masked by the recipe at the new place: the band
                (SPEC 22 px), the surface it falls on (the table top), never on the other table item; 1 under the product. What the move
                uncovers is the scene below (the base's table top).

  python3 fix_r7.py planter | curtains | table | all        (curtains-v3 is run by pass_r7.py after 7')
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import extract as X  # noqa: E402
import fix_r6 as F6  # noqa: E402  (imports fix_r5 / grade_cut_r5 / r4 / r12 / r3 and the R6 sources)
import grade_cut_r12 as G12  # noqa: E402
import phase2_wm as W  # noqa: E402
import stack  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR5, WR6, WR7 = F6.WR5, F6.WR6, os.path.join(HERE, "work-r7")
WRES = F6.WRES
SIZE = W.SIZE
REC = os.path.join(WR7, "fix-r7.json")
SCR = os.path.join(X.SCR, "r7")
D = os.path.join
FX0, FY0, FX1, FY1 = 77.49, 43.43, 2642.51, 1486.57     # the 3840 x 2160 camera frame inside the 2720 x 1530 canvas
FW_, FH_ = FX1 - FX0, FY1 - FY0
K3840 = 2720 / 4072                                         # 3840-frame px -> work px

# ------------------------------------------------------------------------------------------------- the R7 sources
SRC6 = dict(F6.SRC6)
SRC7 = dict(SRC6)
SRC7.update({k: (D(WR7, "layers"), D(WR7, "shadows")) for k in ("planter", "curtains", "candle-holders", "bowl")})
VSRC7 = dict(F6.VSRC6)
VSRC7["curtains-v2"] = (D(WR7, "layers"), D(WR7, "shadows"))
for nm in ("bowl-v2", "candle-holders-v2", "vase-v3", "bowl-v3", "candle-holders-v3", "curtains-v3"):
    VSRC7[nm] = (D(WR7, "layers"), D(WR7, "shadows"))
VSLOT = dict(F6.VSLOT)
VSLOT.update({"bowl-v2": "bowl", "candle-holders-v2": "candle-holders", "vase-v3": "vase", "bowl-v3": "bowl", "candle-holders-v3": "candle-holders",
              "curtains-v3": "curtains"})
ACCEPTED = list(F6.ACCEPTED)


def src_ok(v, nm):
    return os.path.exists(D(v[0], f"{nm}.png")) and os.path.exists(D(v[1], f"{nm}.png"))


def use_r7_sources():
    """the R7 sources; a slot whose R7 file is not written yet reads its R6 source"""
    F6.use_r6_sources()
    G12.SRC.clear()
    G12.SRC.update({k: (v if src_ok(v, k) else F6.SRC6[k]) for k, v in SRC7.items()})


def variant_src(nm):
    v = VSRC7[nm]
    if src_ok(v, nm):
        return v
    return F6.VSRC6.get(nm, v)


def rel(p):
    return os.path.relpath(p, W.REPO)


f32, lab, rgb_of = F6.f32, F6.lab, F6.rgb_of


def record(key, val):
    os.makedirs(WR7, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-12", author="render-agent", tokens=0, brief="briefs/render-wm-tool-r7-2026-11-12.md",
        sources=dict(designer="docs/proposals/owner-answers-applied-2026-11-12.md", slots="data/slots/living-room.json 1.9.4",
                     plan="docs/house-plan.json 1.3.6"),
        note="ungraded per-product layers (RGBA, straight alpha) and shadows (grey RGB, multiply) in work-r7/; grade_cut_r7.py grades and "
             "cuts them with the ONE v3c grade; the numbers here are measured on graded scenes recomposed with the change (set B)")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save_layer(name, rgb, a):
    p = _new(D(WR7, "layers", f"{name}.png"))
    PW.save(p, np.clip(rgb, 0, 1).astype(np.float32), alpha=np.clip(a, 0, 1).astype(np.float32))
    return p


def save_shadow(name, sh):
    p = _new(D(WR7, "shadows", f"{name}.png"))
    PW.save(p, np.repeat(np.clip(sh, 0, 1)[..., None], 3, 2).astype(np.float32))
    return p


def save_alpha(name, a):
    p = _new(D(WR7, "layers", f"{name}-free-alpha.png"))
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(p)
    return p


# ------------------------------------------------------------------------------------------------- composing with the R7 sources
_P = []


def parts():
    if not _P:
        _P.append(stack.base_parts())
    return _P[0]


def compose7(variants=None, items=None, cushion_set="B", override=None):
    """the R7 stack (ACCEPTED + a cushion set) with some slots read from a variant ({slot: name}) or an override ({slot: (rgb, a,
    a_free or None, sh)})"""
    variants, override = variants or {}, override or {}
    use_r7_sources()
    orig = G12.product
    base_product = G12.product

    def prod(k, s=None):
        if k in override:
            rgb, a, af, sh = override[k]
            return rgb, (af if (k in stack.BEHIND and af is not None) else a), sh
        if k in variants:
            nm = variants[k]
            ld, sd = variant_src(nm)
            L = stack.f8(D(ld, f"{nm}.png"))
            a = L[..., 3]
            fp = D(ld, f"{nm}-free-alpha.png")
            if k in stack.BEHIND and os.path.exists(fp):
                a = stack.f8(fp, "L")
            return L[..., :3], a, stack.f8(D(sd, f"{nm}.png"), "L")
        return base_product(k, s)
    G12.product = prod
    sp = stack.product
    stack.product = prod
    try:
        return stack.compose(set(items or ACCEPTED) | {"cushions"}, parts(), cushion_set=cushion_set, keep_steps=True)
    finally:
        G12.product = orig
        stack.product = sp


def grade():
    return F6.grade()


def graded(variants=None, override=None, cushion_set="B"):
    U, steps = compose7(variants, cushion_set=cushion_set, override=override)
    A = np.zeros(SIZE[::-1], np.float32)
    for st in steps:
        A = np.maximum(A, st["a_eff"] if st["k"] != "cushions" else st["a"])
    return U, A, grade()(U, A)


def lab8(G8):
    return lab(G8.astype(np.float32) / 255)


def wpt(X_, Y_, Z_):
    """a plan point -> work px (step 0's P() and canvas)"""
    u, v, _ = S0.P(X_, Y_, Z_)
    return (S0.CX + u * S0.CW) * K3840, (S0.CY + v * S0.CH) * K3840


# ================================================================================================= planter (section 8)
PLANTER_K = 0.78


def qa_planter_measure(G8, ap, ab, allprod):
    """QA R5's measure (r5_designer_targets.py, the same masks) on a graded scene; + the designer's (a'') shoulder rows 1060-1107, the
    bottom band (rows 1180-1191) and the high-pass L* std on the pot"""
    S = lab8(G8)
    potzone = ((ap == 255) & ~(ab > 0))[:, 900:1150].sum(1) > 40
    potzone[:1000] = False
    rim = int(np.nonzero(potzone)[0].min())
    pot = (ap == 255) & ~(ab > 0)
    pot[:rim] = False
    Lsc = S[..., 0]
    soil = np.zeros(pot.shape, bool)
    soil[rim:rim + 16] = Lsc[rim:rim + 16] < 25
    pot &= ~soil
    pot = cv2.erode(pot.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    d = cv2.distanceTransform((~(ap > 0)).astype(np.uint8), cv2.DIST_L2, 5)
    ring = (d >= 15) & (d <= 40) & ~allprod
    ring[1112:] = False
    prow = np.nonzero(pot.any(1))[0]
    ring[: prow.min()] = False
    ring[:, 1000:] = False
    rows_both = sorted(set(np.nonzero(ring.any(1))[0]) & set(prow))
    pr = pot.copy()
    keep = np.zeros(pr.shape[0], bool)
    keep[rows_both] = True
    pr[~keep] = False

    def summ(m):
        L_, a_, b_ = np.median(S[m], 0)
        return dict(L=round(float(L_), 2), C=round(float(np.hypot(a_, b_)), 2), h=round(float(np.degrees(np.arctan2(b_, a_)) % 360), 1), px=int(m.sum()))
    sh_rows = pot.copy()
    sh_rows[:1060] = False
    sh_rows[1108:] = False
    bot = pot.copy()
    bot[:1180] = False
    bot[1192:] = False
    hp = Lsc - cv2.GaussianBlur(Lsc, (0, 0), 3)
    out = dict(rim_row=rim, pot_same_rows=summ(pr), ring=summ(ring), pot_whole=summ(pot), shoulder_1060_1107=summ(sh_rows),
               bottom_1180_1191=summ(bot), highpass_L_std=round(float(hp[pot].std()), 3))
    out["a1_dL_whole_minus_ring"] = round(out["pot_whole"]["L"] - out["ring"]["L"], 2)
    out["b_dC_same_rows"] = round(out["pot_same_rows"]["C"] - out["ring"]["C"], 2)
    out["c_dh_same_rows"] = round((out["pot_same_rows"]["h"] - out["ring"]["h"] + 180) % 360 - 180, 1)
    return out


def planter_mask(a, rgb):
    """the pot's body in the planter layer (work size, soft): the layer's alpha > 0 from the rim's ellipse down, minus the soil and
    the trunk in the opening (the projected opening r 0.1655 at Z 0.355: its upper half, and any dark pixel in it), minus everything
    above the rim (the crown, the trunk); grown 4 px outward (the outer edge keeps the whole factor: its alpha blends it), then
    feathered 2 px (Gaussian sigma 1) at the inner boundary"""
    Ls = PW.Lstar(rgb)
    to_w = lambda m: cv2.resize(m.astype(np.float32), SIZE, interpolation=cv2.INTER_AREA)  # noqa: E731
    inner = to_w(S0.raster([S0.circ(-1.95, 0.42, 0.1775 - 0.012, 0.355)])) > 0.5
    rim_e = to_w(S0.raster([S0.circ(-1.95, 0.42, 0.1775, 0.355)])) > 0.5
    ys, _ = np.nonzero(rim_e)
    top, cy = int(ys.min()), float(np.nonzero(inner)[0].mean())
    rows = np.arange(a.shape[0])[:, None]
    body = (a > 0) & (rows >= top)
    soil = (inner & (rows < cy)) | (rim_e & (Ls < 32))
    soil = cv2.dilate(soil.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & rim_e
    m = body & ~soil
    grow = cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool) & ~soil & (rows >= top)
    m = np.where(a > 0, m, grow)
    mf = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0)
    mf = np.where(m & ~cv2.dilate((~m).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool), 1.0, mf)
    return np.clip(mf, 0, 1).astype(np.float32), dict(rim_ellipse_top_row=top, opening_centre_row=round(cy, 1), soil_px=int(soil.sum()))


def planter():
    use_r7_sources()
    ld, sd = SRC6["planter"]
    L = f32(D(ld, "planter.png"))
    rgb, a = L[..., :3], L[..., 3]
    m, minfo = planter_mask(a, rgb)
    ap8 = (a * 255 + 0.5).astype(np.uint8)
    ab8 = (f32(D(SRC6["basket"][0], "basket.png"))[..., 3] * 255 + 0.5).astype(np.uint8)
    allprod = F6.all_product_alpha()
    _, _, G0 = graded()
    before = qa_planter_measure(G0, ap8, ab8, allprod)

    def apply(k):
        f = 1.0 - (1.0 - k) * m
        return np.clip(PW.l2s(PW.s2l(rgb) * f[..., None]), 0, 1).astype(np.float32)
    sh = f32(D(sd, "planter.png"), "L")
    rgb2 = apply(PLANTER_K)
    _, _, G1 = graded(override={"planter": (rgb2, a, None, sh)})
    after = qa_planter_measure(G1, ap8, ab8, allprod)
    hp_ratio = after["highpass_L_std"] / before["highpass_L_std"]
    hp_fix = None
    if hp_ratio < 0.90:
        # (d): the high pass back ONCE, x 1.0-1.1 (the designer's rule): the darkened low pass + g x the original high pass
        g = 1.0
        Lw0, Lw1 = lab(rgb)[..., 0], lab(rgb2)
        hp0 = Lw0 - cv2.GaussianBlur(Lw0, (0, 0), 3)
        hp1 = Lw1[..., 0] - cv2.GaussianBlur(Lw1[..., 0], (0, 0), 3)
        Lw1[..., 0] = Lw1[..., 0] + (hp0 * g - hp1) * m
        rgb2 = rgb_of(Lw1[..., 0], Lw1[..., 1], Lw1[..., 2])
        _, _, G1 = graded(override={"planter": (rgb2, a, None, sh)})
        after = qa_planter_measure(G1, ap8, ab8, allprod)
        hp_fix = g
    tg = {"(a') whole pot 6-10 L* darker than the ring": -10 <= after["a1_dL_whole_minus_ring"] <= -6,
          "(a'') lit shoulder rows 1060-1107 at 74-79": 74 <= after["shoulder_1060_1107"]["L"] <= 79,
          "bottom band moves <= 3": abs(after["bottom_1180_1191"]["L"] - before["bottom_1180_1191"]["L"]) <= 3,
          "(b) C* <= ring + 1.5": after["b_dC_same_rows"] <= 1.5,
          "(c) hue within +-10 deg of the ring": abs(after["c_dh_same_rows"]) <= 10,
          "(d) high-pass L* std within -10 %..+5 %": 0.90 <= after["highpass_L_std"] / before["highpass_L_std"] <= 1.05}
    lp = save_layer("planter", rgb2, a)
    sp = save_shadow("planter", sh)
    # the edge against the wall, x 4: the mean L* step across the pot's left contour (outside ring 1-3 px vs inside 1-3 px), before / after
    edge = {}
    for nm, G8 in (("before", G0), ("after", G1)):
        Lg = lab8(G8)[..., 0]
        out_ = (cv2.distanceTransform((ap8 == 0).astype(np.uint8), cv2.DIST_L2, 5) <= 3) & (ap8 == 0)
        in_ = (cv2.distanceTransform((ap8 > 0).astype(np.uint8), cv2.DIST_L2, 5) <= 3) & (ap8 == 255)
        rows = np.zeros_like(out_)
        rows[1060:1108, 900:1000] = True
        edge[nm] = dict(outside_1_3px=round(float(np.median(Lg[out_ & rows])), 2), inside_1_3px=round(float(np.median(Lg[in_ & rows])), 2))
    record("planter", dict(what="section 8: ONE factor in linear light on the pot's body (R, G, B alike), the planter layer only; the shadow file "
                                "is the R5 file's pixels, unchanged", k=PLANTER_K, allowed=[0.72, 0.84], mask=minfo,
                           mask_note="the pot without the soil, the trunk and the crown (QA's definition) INCLUDING its soft edge and the pixels "
                                     "under the basket's edge (else a light fringe along the basket); feathered 2 px inside",
                           highpass_restored=hp_fix, before=before, after=after, targets=tg, all_met=all(tg.values()),
                           expected_by_designer={"(a')": "~57.5 (about -8)", "(a'')": "~76.8", "bottom": "~14", "(b)": "~12"},
                           left_edge_L_median=edge, file=rel(lp), shadow=rel(sp), source=rel(D(ld, "planter.png"))))
    print(json.dumps(dict(before={k: before[k] for k in ("a1_dL_whole_minus_ring", "shoulder_1060_1107", "bottom_1180_1191", "highpass_L_std")},
                          after={k: after[k] for k in ("a1_dL_whole_minus_ring", "shoulder_1060_1107", "bottom_1180_1191", "highpass_L_std",
                                                        "b_dC_same_rows", "c_dh_same_rows")}, targets=tg, edge=edge), indent=1, default=float))
    np.save(D(SCR, "planter-G0.npy"), G0)
    np.save(D(SCR, "planter-G1.npy"), G1)


# ================================================================================================= curtains (section 6.3)
HEM_Z = {"curtains": 0.12, "curtains-v2": 0.12, "curtains-v3": 0.22}
CONTACT_Z = 0.45
X_FACE, Y_END, Y_FRONT, Y_BACK, X_BACKF = -2.15, 2.85, 2.95, 2.65, -2.29
SPILL_PX = 8 * K3840                 # the spill over the stone arc, <= 8 px at 3840
WOBBLE_PX = 2.0                      # the folds move the hem by <= 3 px at 3840
BAND_PX = 27 * K3840                 # the hem band: double fabric, 3 cm ~ 27 px at 3840
BREAK_PX = 7.5 * K3840               # the break over the bench: the last 6-10 px at 3840
SHADE_MAX, SHADE_FADE = 0.06, 25 * K3840
CONTACT_W, CONTACT_MUL, CONTACT_BLUR = 5 * K3840, 0.925, 3 * K3840 / 2.0


def lines(hem_z):
    """the plan's lines in work px: the hem along the stack's front face (X -2.29 -> -2.15 at Y 2.95) and its room-side face (Y 2.95 ->
    2.85 at X -2.15); the contact on the bench top (Z 0.45 on X -2.15, Y 2.85 -> 2.65)"""
    hem = [wpt(X_BACKF, Y_FRONT, hem_z), wpt(X_FACE, Y_FRONT, hem_z), wpt(X_FACE, Y_END, hem_z)]
    con = [wpt(X_FACE, Y_END, CONTACT_Z), wpt(X_FACE, Y_BACK, CONTACT_Z)]
    return hem, con


def _interp_line(pts, x):
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    y = np.interp(x, xs, ys)
    # straight extrapolation beyond the ends
    lo, hi = x < xs[0], x > xs[-1]
    y = np.where(lo, ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0]), y)
    y = np.where(hi, ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]), y)
    return y


def fold_wobble(rgb, a_free, hem_y, x_end):
    """the hem's wobble with the folds: the low-pass L* of the fabric just above the hem (rows hem-40 .. hem-12), high-passed along x
    (sigma 18 px), scaled to <= WOBBLE_PX; a fold crest (lighter) hangs a little lower"""
    Ls = PW.Lstar(rgb)
    xs = np.arange(int(math.ceil(x_end)) + 1)
    prof = np.zeros(len(xs), np.float32)
    for x in xs:
        y1 = int(hem_y[x]) - 12
        y0 = y1 - 28
        col = Ls[max(0, y0):max(1, y1), x]
        w_ = a_free[max(0, y0):max(1, y1), x] > 0.5
        prof[x] = float(np.median(col[w_])) if w_.any() else np.nan
    ok = ~np.isnan(prof)
    prof = np.interp(xs, xs[ok], prof[ok]) if ok.any() else np.zeros(len(xs))
    sm = cv2.GaussianBlur(prof.reshape(1, -1).astype(np.float32), (0, 0), 3).ravel()
    hp = sm - cv2.GaussianBlur(sm.reshape(1, -1), (0, 0), 18).ravel()
    m = float(np.abs(hp).max()) or 1.0
    return xs, (hp / m * WOBBLE_PX).astype(np.float32)


def cut_mask(hem_z, rgb, a_free, ss=4):
    """the fabric that stays (soft, area coverage at ss x ss): above the hem for x <= the bench end, above the bench-top contact beyond
    it, plus the spill over the stone arc at the corner; returns (keep 0..1, geometry record)"""
    H, Wd = a_free.shape
    hem, con = lines(hem_z)
    xv, yv = con[0]                                   # the bench end on the stack's room face: (X -2.15, Y 2.85, Z 0.45)
    xh = hem[-1][0]                                   # the hem's end at the bench end (same x)
    xs = np.arange(Wd, dtype=np.float32)
    hem_plan = _interp_line(hem, xs)
    # the stack's front corner (X -2.15, Y 2.95; in the overscan, u -0.0045) is a fold, not a point: the hem rounded there by a
    # 21 px moving average (its tip rises ~2 px; the plan line elsewhere is unchanged)
    k_ = np.ones(21, np.float32) / 21
    pad = np.pad(hem_plan, 10, mode="edge")
    hem_y = np.convolve(pad, k_, mode="valid").astype(np.float32)
    hem_y = np.where(np.abs(xs - hem[1][0]) <= 12, np.minimum(hem_y, hem_plan), hem_plan)
    xw, wob = fold_wobble(rgb, a_free, hem_y, xh)
    wob = wob * np.clip((xh - xw) / 10.0, 0, 1)                      # tapered to 0 at the bench end (the corner stays on the plan)
    hem_yw = hem_y.copy()
    hem_yw[: len(wob)] = hem_y[: len(wob)] + wob
    con_y = _interp_line(con, xs)
    # the removed region as a polygon (sub-pixel, cv2 shift 4 at ss x)
    pts = [(-4.0, float(hem_y[0]))]
    pts += [(float(x), float(hem_yw[x])) for x in range(0, int(math.floor(xh)) + 1)]
    pts += [(xh, float(_interp_line(hem, np.array([xh]))[0]))]
    pts += [(xh, yv + SPILL_PX), (xh + SPILL_PX, float(_interp_line(con, np.array([xh + SPILL_PX]))[0]))]
    xr_ = 420.0                                       # the stack never reaches x 420 (its alpha ends at ~310): the cut stops there
    pts += [(xr_, float(_interp_line(con, np.array([xr_]))[0])), (xr_, float(H + 4)), (-4.0, float(H + 4))]
    big = np.zeros((H * ss, Wd * ss), np.uint8)
    P = np.round((np.array(pts) * ss + (ss - 1) / 2.0) * 16).astype(np.int32)
    cv2.fillPoly(big, [P], 255, lineType=cv2.LINE_8, shift=4)
    removed = cv2.resize(big.astype(np.float32) / 255, (Wd, H), interpolation=cv2.INTER_AREA)
    keep = np.clip(1 - removed, 0, 1).astype(np.float32)
    geo = dict(hem_z=hem_z, hem_px=[[round(p[0], 1), round(p[1], 1)] for p in hem], contact_px=[[round(p[0], 1), round(p[1], 1)] for p in con],
               bench_end_x_px=round(xh, 1), spill_px=round(SPILL_PX, 2), wobble_max_px=round(float(np.abs(wob).max()), 2),
               lines_3840=dict(hem=[[round((p[0] / K3840 - S0.CX), 1), round((p[1] / K3840 - S0.CY), 1)] for p in hem],
                               contact=[[round((p[0] / K3840 - S0.CX), 1), round((p[1] / K3840 - S0.CY), 1)] for p in con]))
    return keep, hem_y, hem_yw, con_y, xh, geo


BAND_TOTAL = -2.8          # the band against the 30 px above (3840), as QA reads it: -2 +-1; the render's own gradient there is ~-2


def curtain_cut(name, ld, sd, out_name=None, band_step=-0.75):
    """section 6.3 on one curtain layer (its ungraded work files: <name>.png, <name>-free-alpha.png, shadow <name>.png). band_step: the hem
    band's own L* step, set so that the band reads BAND_TOTAL against the 30 px above with the render's own gradient included"""
    out_name = out_name or name
    hem_z = HEM_Z[out_name]
    L = f32(D(ld, f"{name}.png"))
    rgb, a_pic = L[..., :3].copy(), L[..., 3]
    af = f32(D(ld, f"{name}-free-alpha.png"), "L")
    sh0 = f32(D(sd, f"{name}.png"), "L")
    fa = W.furn_alpha()
    keep, hem_y, hem_yw, con_y, xh, geo = cut_mask(hem_z, rgb, af)
    H, Wd = af.shape
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    af2 = af * keep
    a2 = af2 * (1 - fa)
    # the hem band (the free part, x <= the bench end): L* -2, 1 px soft top edge, the folds' shading kept (a constant L* offset)
    t_hem = hem_yw[None, :Wd] - yy                                   # px above the (wobbled) hem
    band = np.clip((BAND_PX + 0.5 - t_hem), 0, 1) * (t_hem > -2) * (xx <= xh + 0.5)
    # the break over the bench (x beyond the bench end): the last BREAK_PX above the contact, L* -4 at the contact, smoothstep up
    t_con = con_y[None, :Wd] - yy
    s = np.clip(1 - t_con / BREAK_PX, 0, 1)
    brk = (s * s * (3 - 2 * s)) * (t_con > -2) * (xx > xh)
    Lw = lab(rgb)
    Lw[..., 0] = Lw[..., 0] + band_step * band - 4.0 * brk
    rgb2 = np.where((af2 > 0)[..., None], rgb_of(Lw[..., 0], Lw[..., 1], Lw[..., 2]), rgb).astype(np.float32)
    # the shadow: the old one where the fabric still is (and above the lines), 1 below; + the shade under the hem; + the stone contact
    removed_zone = ((keep < 0.999) | (yy > np.where(xx <= xh, hem_y[None, :Wd], con_y[None, :Wd]))) & (xx < 420)
    sh = np.where(removed_zone, 1.0, sh0)
    u = (yy - hem_yw[None, :Wd]) / SHADE_FADE                       # 0 at the hem .. 1 at 25 px (3840) below
    u = np.clip(u, 0, 1)
    shade = SHADE_MAX * (1 - u * u * (3 - 2 * u)) * (yy >= hem_yw[None, :Wd] - 1)
    xr = np.clip((xh + 3 - xx) / 6.0, 0, 1)                          # its right end, soft over 6 px at the bench end
    shade = shade * xr
    shade = cv2.GaussianBlur(shade.astype(np.float32), (0, 0), sigmaX=3.0, sigmaY=0.8)
    v = np.clip((yy - con_y[None, :Wd]) / CONTACT_W, 0, 1)
    cont = (1 - CONTACT_MUL) * (1 - v) * (yy >= con_y[None, :Wd] - 0.5) * (xx > xh - 1) * (xx < wpt(X_FACE, Y_BACK, CONTACT_Z)[0] + 6)
    cont = cv2.GaussianBlur(cont.astype(np.float32), (0, 0), CONTACT_BLUR)
    sh = sh * (1 - shade) * (1 - cont)
    sh = np.clip(sh * (1 - af2) + af2, 0.45, 1.0).astype(np.float32)
    # keep the region tight: nothing beyond 60 px of the alpha box (checked by verify)
    ys, xs_ = np.nonzero(af2 > 0)
    lp = save_layer(out_name, rgb2, a2)
    fp = save_alpha(out_name, af2)
    spth = save_shadow(out_name, sh)
    rec = dict(geometry=geo, removed_free_alpha_px=int(((af > 0.5) & (af2 <= 0.5)).sum()), kept_free_alpha_px=int((af2 > 0.5).sum()),
               hem_band_px=round(BAND_PX, 1), hem_band_step_dL=round(band_step, 2), break_px=round(BREAK_PX, 1), break_dL=-4.0,
               shadow=dict(old_removed_px=int(((sh0 < 0.99) & removed_zone).sum()), under_hem_max=SHADE_MAX, under_hem_fade_px=round(SHADE_FADE, 1),
                           contact=dict(width_px=round(CONTACT_W, 2), multiply=CONTACT_MUL, blur_sigma_px=round(CONTACT_BLUR, 2)),
                           note="the designer's explicit shadow (section 6.3 item 6) for the cut; the shadow above the lines is the frozen "
                                "recipe's file, unchanged"),
               files=dict(layer=rel(lp), free_alpha=rel(fp), shadow=rel(spth)),
               source=dict(layer=rel(D(ld, f"{name}.png")), shadow=rel(D(sd, f"{name}.png"))))
    return rec


def curtain_measure(G8, af2, hem_z):
    """on a graded scene: the hem's row per column in the free part (where the alpha crosses 0.5) against the plan line (3840 px: +-9 =
    +-1 cm); the hem band L* against the 30 px above (3840) inside the fabric; what lies below the hem (the base)"""
    hem, con = lines(hem_z)
    xh = con[0][0]
    xs = np.arange(0, int(xh) - 1)
    hem_plan = _interp_line(hem, xs.astype(np.float32))
    dev = []
    for x in xs:
        col = af2[:, x]
        idx = np.nonzero(col > 0.5)[0]
        if len(idx):
            dev.append(float(idx.max() + 0.5 - hem_plan[x]))
    dev = np.array(dev)
    Lg = lab8(G8)[..., 0]
    bandL, aboveL = [], []
    for x in xs[10:]:
        y = int(round(hem_plan[x]))
        bandL.append(np.median(Lg[y - int(BAND_PX) + 2: y - 2, x]))
        aboveL.append(np.median(Lg[y - int(BAND_PX) - int(30 * K3840): y - int(BAND_PX) - 1, x]))
    return dict(hem_dev_px_2720=dict(median=round(float(np.median(dev)), 2), min=round(float(dev.min()), 2), max=round(float(dev.max()), 2)),
                hem_dev_px_3840=dict(median=round(float(np.median(dev)) / K3840, 2), max_abs=round(float(np.abs(dev).max()) / K3840, 2)),
                band_dL_vs_above=round(float(np.median(np.array(bandL) - np.array(aboveL))), 2))


def curtains():
    """the default (180502) and curtains-v2 (554205): the same cut, hem Z 0.12 (270)"""
    out = {}
    pre = {"curtains": np.asarray(Image.open(D(HERE, "graded/default-scene-r6-set-B-graded-v3c.png"))),
           "curtains-v2": np.asarray(Image.open(D(HERE, "graded/variant-r6-curtains-v2-set-B-graded-v3c.png")))}
    for name, (ld, sd), out_name in (("curtains", SRC6["curtains"], "curtains"), ("curtains-v2", F6.VSRC6["curtains-v2"], "curtains-v2")):
        nat = curtain_measure(pre[name], f32(D(ld, f"{name}-free-alpha.png"), "L"), HEM_Z[out_name])["band_dL_vs_above"]
        step = float(np.clip(BAND_TOTAL - nat, -2.0, 0.0))
        rec = curtain_cut(name, ld, sd, out_name, band_step=step)
        rec["band_natural_dL_before_cut"] = nat
        out[out_name] = rec
    use_r7_sources()
    for nm in ("curtains", "curtains-v2"):
        af2 = f32(D(WR7, "layers", f"{nm}-free-alpha.png"), "L")
        _, _, G8 = graded(variants={"curtains": nm} if nm != "curtains" else None)
        out[nm]["measured"] = curtain_measure(G8, af2, HEM_Z[nm])
        np.save(D(SCR, f"{nm}-G.npy"), G8)
    record("curtains", dict(what="WM-C3 / SUP-C1 (owner 2026-11-12), the designer's section 6.3: the sold length 270 (180502 132 x 270, 554205 150 x "
                                 "270): hem Z 0.12; one cut and one shadow for both", **out))
    print(json.dumps({k: dict(v["measured"], removed=v["removed_free_alpha_px"], geo=v["geometry"]["lines_3840"]) for k, v in out.items()}, indent=1))


def curtains_v3():
    """curtain 3 (Linen, 200 x 260, 4 hook): the same cut at Z 0.22, on 7''s cut and colour fix (work-r7/layers/curtains-v3-render.png)"""
    use_r7_sources()
    _, _, Gpre = graded(override={"curtains": (*(lambda L_: (L_[..., :3], L_[..., 3]))(f32(D(WR7, "layers", "curtains-v3-render.png"))),
                                               f32(D(WR7, "layers", "curtains-v3-render-free-alpha.png"), "L"),
                                               f32(D(WR7, "shadows", "curtains-v3-render.png"), "L"))})
    nat = curtain_measure(Gpre, f32(D(WR7, "layers", "curtains-v3-render-free-alpha.png"), "L"), HEM_Z["curtains-v3"])["band_dL_vs_above"]
    step = float(np.clip(BAND_TOTAL - nat, -2.0, 0.0))
    rec = curtain_cut("curtains-v3-render", D(WR7, "layers"), D(WR7, "shadows"), "curtains-v3", band_step=step)
    rec["band_natural_dL_before_cut"] = nat
    use_r7_sources()
    af2 = f32(D(WR7, "layers", "curtains-v3-free-alpha.png"), "L")
    _, _, G8 = graded(variants={"curtains": "curtains-v3"})
    rec["measured"] = curtain_measure(G8, af2, HEM_Z["curtains-v3"])
    record("curtains-v3", dict(what="the same cut at the sold 260: hem Z 0.22", **rec))
    print(json.dumps(dict(rec["measured"], geo=rec["geometry"]["lines_3840"]), indent=1))


# ================================================================================================= the table group (section 1.5)
MOVE = {
    # A: the designer's -0.0294 / -0.0063 / 0.982 for (0.205, 1.74) measured A x B 0.0191 on the moved RENDERED pieces (< 0.02; the
    # card clay reads 0.0211): the pre-approved lever of section 1.4 (the gap 8 -> 9 cm, A 1 cm left: (0.195, 1.74)), with P()
    "candle-holders": dict(pieces={"A": (-0.0317, -0.0067, 0.980), "B": (-0.0302, -0.0063, 0.982)}, src="candle-holders",
                           lever=dict(A=dict(designer=(-0.0294, -0.0063, 0.982), used=(-0.0317, -0.0067, 0.980), point=(0.195, 1.74),
                                             why="A x B 0.0191 < 0.02 on the moved rendered layers; section 1.4 lever 'A-B -> 9 cm clear (A 1 cm left)'"))),
    "bowl": dict(pieces={"bowl": (-0.0285, -0.0065, 0.983)}, src="bowl"),
}


def pieces_of(a):
    n, lab_, st, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
    ids = [i for i in range(1, n) if st[i, 4] >= 200]
    ids.sort(key=lambda i: st[i, 0])                     # left to right: A, B
    return lab_, ids, st


def move_item(k):
    """each piece (its layer premultiplied and its shadow field) moved about its contact point; the frozen recipe's masks at the new place"""
    ld, sd = SRC6[k]
    L = f32(D(ld, f"{k}.png"))
    rgb, a = L[..., :3], L[..., 3]
    sh = f32(D(sd, f"{k}.png"), "L")
    lab_, ids, st = pieces_of(a)
    names = list(MOVE[k]["pieces"])
    assert len(ids) == len(names), (k, len(ids))
    # every pixel of the layer and of the shadow goes to its nearest piece
    seeds = np.zeros(a.shape, np.uint8)
    for j, i in enumerate(ids):
        seeds[lab_ == i] = j + 1
    _, near = cv2.distanceTransformWithLabels((seeds == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys0, xs0 = np.nonzero(seeds > 0)
    lut = np.zeros(int(near.max()) + 1, np.uint8)
    lut[near[ys0, xs0]] = seeds[ys0, xs0]
    owner = lut[near]
    outA = np.zeros_like(a)
    outP = np.zeros_like(rgb)
    outD = np.zeros_like(sh)
    rec = {}
    for j, (i, nm) in enumerate(zip(ids, names)):
        du, dv, s = MOVE[k]["pieces"][nm]
        ys, xs = np.nonzero(lab_ == i)
        ay = float(ys.max()) + 0.5
        ax = float(xs[ys >= ys.max() - 2].mean()) + 0.5
        tx, ty = du * FW_, dv * FH_
        M = np.float32([[s, 0, ax * (1 - s) + tx], [0, s, ay * (1 - s) + ty]])
        own = owner == j + 1
        ai = np.where(own, a, 0).astype(np.float32)
        di = np.where(own, 1 - sh, 0).astype(np.float32)
        outA += cv2.warpAffine(ai, M, SIZE, flags=cv2.INTER_AREA)
        outP += cv2.warpAffine(rgb * ai[..., None], M, SIZE, flags=cv2.INTER_AREA)
        outD = np.maximum(outD, cv2.warpAffine(di, M, SIZE, flags=cv2.INTER_AREA))
        rec[nm] = dict(anchor_px=[round(ax, 2), round(ay, 2)], translate_px=[round(tx, 2), round(ty, 2)], scale=s, du_dv=[du, dv],
                       new_anchor_px=[round(ax + tx, 2), round(ay + ty, 2)], box_before=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    a2 = np.clip(outA, 0, 1).astype(np.float32)
    rgb2 = np.where((outA > 1e-4)[..., None], outP / np.maximum(outA, 1e-4)[..., None], rgb).astype(np.float32)
    return rgb2, a2, np.clip(outD, 0, 1).astype(np.float32), rec


def remask_shadow(k, a, dfield, other_alpha):
    """the frozen recipe's masks (extract.shadow_one) at the new place: the band (SPEC band px) round the product, only on the surface
    it falls on (the table top), never on the other table item or the furniture in front; floored at 0.45; 1 under the product"""
    sp = X.SPEC[k]
    surf = X.surfaces()
    fa = W.furn_alpha()
    onto = surf["table"]
    prod = a > 0.02
    front = (fa > 0.02) & ~onto
    band = X.dil(prod, sp["band"] + 4) & ~prod & onto & ~front & ~(other_alpha > 0.02)
    d = np.where(band | prod, dfield, 0.0)
    sh = 1 - d
    return np.clip(sh * (1 - a) + a, 0.45, 1.0).astype(np.float32), int((dfield > 0.005).sum() - (d > 0.005).sum())


def table():
    use_r7_sources()
    out = {}
    moved = {}
    for k in ("candle-holders", "bowl"):
        moved[k] = move_item(k)
    for k in ("candle-holders", "bowl"):
        other = "bowl" if k == "candle-holders" else "candle-holders"
        rgb2, a2, dfield, rec = moved[k]
        sh2, clipped = remask_shadow(k, a2, dfield, moved[other][1])
        lp = save_layer(k, rgb2, a2)
        spth = save_shadow(k, sh2)
        out[k] = dict(pieces=rec, lever=MOVE[k].get("lever"), shadow_px_clipped_by_the_recipe_masks=clipped, files=dict(layer=rel(lp), shadow=rel(spth)),
                      source=dict(layer=rel(D(SRC6[k][0], f"{k}.png")), shadow=rel(D(SRC6[k][1], f"{k}.png"))))
    # the moved layers against the neighbours (frame-width units at 2720: / FW_), F3's 0.02; the soft edges are checked in the crops
    use_r7_sources()
    al = {k: f32(D(WR7, "layers", f"{k}.png"))[..., 3] > 0.5 for k in ("candle-holders", "bowl")}
    cs = {s: G12._STACK_PRODUCT("cushions", s)[1] > 0.5 for s in "ABC"}
    gaps = {}
    for k, m in al.items():
        for s, c in cs.items():
            dt = cv2.distanceTransform((~c).astype(np.uint8), cv2.DIST_L2, 5)
            gaps[f"{k} x cushions {s}"] = round(float(dt[m].min()) / FW_, 4)
    lab_, ids, _ = pieces_of(al["candle-holders"].astype(np.float32))
    pa, pb = lab_ == ids[0], lab_ == ids[1]
    gaps["A x B"] = round(float(cv2.distanceTransform((~pb).astype(np.uint8), cv2.DIST_L2, 5)[pa].min()) / FW_, 4)
    gaps["B x bowl"] = round(float(cv2.distanceTransform((~al["bowl"]).astype(np.uint8), cv2.DIST_L2, 5)[pb].min()) / FW_, 4)
    out["layer_gaps_frame"] = gaps
    out["note"] = ("measured on the moved RENDERED layers (alpha > 0.5; the real silhouettes, smaller than step 0's card cylinders); the bowl x "
                   "throw gap stays under 0.02 at the 1.9.4 point, as the clay shows (step0/r7-table-group): the bowl's point goes back to the "
                   "designer (section 1.4 'otherwise back to me'); the move itself is the owner-approved WM-T2 point")
    record("table", out)
    print(json.dumps(out, indent=1, default=float))


STEPS = [("planter", planter), ("curtains", curtains), ("table", table)]

if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what == "curtains-v3":
        curtains_v3()
    for name, fn in STEPS:
        if what in (name, "all"):
            print("==", name, flush=True)
            fn()
