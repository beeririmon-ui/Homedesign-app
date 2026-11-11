#!/usr/bin/env python3
"""
fix_r4.py: code fixes R4 of the warm-modern living-room tool, phase 2 (render-agent, 2026-11-11). From QA's phase-2 checkpoint
(qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md + .json) and the designer's shade targets (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md
section 5). Code only: 0 tokens, no var2, no network. NEW FILES ONLY: work-r4/ (ungraded per-product layers and shadows, the same form as
work/, work-reserve/ and work-r3/) and work-r4/fix-r4.json. grade_cut_r4.py then grades and cuts them with the ONE v3c grade, like every
earlier layer (no layer is graded on its own).

  lamp     the floor lamp's shade FABRIC toned so the product layer reads OFF (section 5). Only the fabric: the collar, the stem, the base
           and the pull chain keep their pixels. The low frequencies are replaced by a smooth daylight field (left = window side lighter,
           right darker, the inside and the lower edge in shade, warmth no more than the wall's); the fold detail is the high-pass of the
           same pass's RAW render (raw/step2-seedream.png, registered with jobs.json's matrix, then a measured sub-pixel shift), because
           the tone match had clipped R and G on about half of the fabric. The light itself comes later, from the light layer in code.
  pendant  the ceiling canopy re-cut whole from the R3b render (work-r3/r3b-regt.npy): the disc is what is whiter than the ceiling
           (b* lower) or differs from it, rows above the cord's foot, the cord's column left out; ONE component, closed and filled to its
           convex hull (a disc seen from below is convex), the edge from a guided filter on the render. The cord keeps its R3 cut.
           canopy_cut() is the fixed cutting code for later pendant renders (pendant 2).
  basket   the right edge re-cut from the R3a render, and the contact shadow carried to the product's edge (below)
  planter  the left side and the bottom re-cut from the R3a render, and the contact shadow carried to the product's edge
           Both: (a) the soft edge's alpha re-estimated from the render (the pixel's colour projected between the product's colour just
           inside and the render's background just outside), the outline smoothed at 4x and anti-aliased, and the edge colour
           decontaminated (the render's background un-mixed out), so the render's darkened wall never reaches the room's own wall (the
           planter's dark rim); (b) the measured contact shadow is no longer diluted next to the product: its darkening is carried from
           the band into the product's soft edge before the blur, and the soft edge is no longer lightened by (1 - a) + a, so under a
           half-covered pixel the floor or wall is as dark as the render drew it (the basket's light line, the planter's ghost).
  vase     scaled in code to the card (Large: D16 x H32) at ITS OWN place: anchored at its current base (the foot's contact point), x and y
           separately (the render's proportion is off: ~2.3:1 against the card's 2:1), measured against the card's cylinder projected at
           the base point the vase actually stands on. NOT moved: the placement (~0.3 m nearer the camera than the plan point) is the
           designer's call. Its contact shadow is redone by the same anchor, at the foot's scale (sx in both axes: it lies on the bench).

  python3 fix_r4.py all            (or: lamp | pendant | edges | vase)
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
import phase2_wm as W  # noqa: E402
import reserve_r3 as R3  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR4 = os.path.join(HERE, "work-r4")
SIZE = W.SIZE
REC = os.path.join(WR4, "fix-r4.json")
R3MAN = json.load(open(os.path.join(HERE, "layers/manifest-r3.json")))
BYID = {l_["id"]: l_ for l_ in R3MAN["layers"]}


def rel(p):
    return os.path.relpath(p, W.REPO)


def f32(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


def record(key, val):
    os.makedirs(WR4, exist_ok=True)
    r = json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-11", author="render-agent", tokens=0,
        sources=dict(qa="qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md", designer="docs/proposals/wm-phase2-f3-decisions-2026-11-11.md section 5"),
        note="ungraded per-product layers (RGBA, straight alpha) and shadows (grey RGB, multiply); grade_cut_r4.py grades and cuts them")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False)


def save_layer(name, rgb, a):
    os.makedirs(os.path.join(WR4, "layers"), exist_ok=True)
    p = os.path.join(WR4, "layers", f"{name}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, np.clip(rgb, 0, 1).astype(np.float32), alpha=np.clip(a, 0, 1).astype(np.float32))
    return p


def save_shadow(name, sh):
    os.makedirs(os.path.join(WR4, "shadows"), exist_ok=True)
    p = os.path.join(WR4, "shadows", f"{name}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, np.repeat(np.clip(sh, 0, 1).astype(np.float32)[..., None], 3, 2))
    return p


def nblur(x, w, s):
    """normalised Gaussian blur of x over the support w (float), any channels"""
    w = w.astype(np.float32)
    den = cv2.GaussianBlur(w, (0, 0), s)
    if x.ndim == 3:
        num = cv2.GaussianBlur(x * w[..., None], (0, 0), s)
        return num / np.maximum(den, 1e-6)[..., None], den
    return cv2.GaussianBlur(x * w, (0, 0), s) / np.maximum(den, 1e-6), den


def lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_of(L, A, B):
    return np.clip(cv2.cvtColor(np.dstack([L, A, B]).astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


# ================================================================================================= 1. the floor lamp's shade
LAMP_W = os.path.join(W.WORK, "layers", "floor-lamp.png")
SCR = X.SCR
U_CACHE = os.path.join(SCR, "r4", "U_r3_B.npy")


def qa_lamp_masks(A8):
    """qa/reports/2026-11-11-wm-tool-phase2-checkpoint/tools/p2_lamp.py, the same masks: the cone's rows (from the layer's top down to
    where the full-alpha width falls under 40 px), the shade = alpha 255 in those rows eroded 3x3, its thirds by column, its bottom 15 %
    by row, and the wall ring 15-40 px from the lamp's alpha in the same rows, off every other product's alpha (manifest-r3)"""
    a = A8.astype(np.float32)
    rows = np.nonzero((a > 0).sum(1))[0]
    width = (a >= 255).sum(1)
    top = int(rows.min())
    y = top
    while y < a.shape[0] and (width[y] >= 40 or y < top + 10):
        y += 1
    bot = y
    shade = np.zeros(a.shape, bool)
    shade[top:bot] = a[top:bot] >= 255
    shade = cv2.erode(shade.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    xs = np.nonzero(shade.any(0))[0]
    x0, x1 = int(xs.min()), int(xs.max())
    w3 = (x1 - x0) / 3
    cols = np.arange(a.shape[1])[None, :].repeat(a.shape[0], 0)
    left, right = shade & (cols < x0 + w3), shade & (cols > x1 - w3)
    h = bot - top
    bottom = shade & (np.arange(a.shape[0])[:, None] >= bot - 0.15 * h)
    d = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
    ring = (d >= 15) & (d <= 40)
    ring[:top] = False
    ring[bot:] = False
    for l_ in R3MAN["layers"]:
        if "product" in l_ and l_["id"] != "floor-lamp":
            ring &= np.asarray(Image.open(os.path.join(HERE, "layers", l_["file"])))[..., 3] == 0
    return dict(top=top, bot=bot, x0=x0, x1=x1, shade=shade, left=left, right=right, bottom=bottom, ring=ring)


def collar_mask(rgb_w, a_w, M):
    """the brass collar under the shade and the top of the pull chain, which keep their pixels: brass colour (ungraded b* > 32, or
    L* < 75 with b* > 20) in the shade's lowest rows, only the pieces connected to the stem's top or to the chain's column below the shade
    (so no dark fold of the fabric is taken for brass). Returns the brass core and its 1 px ring (mixed brass / fabric pixels, which take
    half the fabric's change)"""
    Lw = lab(rgb_w)
    brass = (a_w > 0.02) & ((Lw[..., 2] > 32) | ((Lw[..., 0] < 75) & (Lw[..., 2] > 20)))
    brass[:M["bot"] - 14] = False
    brass[M["bot"] + 8:] = False
    n, lab_ = cv2.connectedComponents(brass.astype(np.uint8), connectivity=8)
    seed = np.zeros(brass.shape, bool)
    seed[M["bot"] + 2:M["bot"] + 8, 2405:2456] = True          # the stem's top under the collar
    seed[M["bot"] + 2:M["bot"] + 8, 2458:2478] = True          # the chain's column under the shade
    keep = np.isin(lab_, [i for i in np.unique(lab_[seed & brass]) if i > 0])
    ring = X.dil(keep, 1) & ~keep & (a_w > 0.02)
    return keep, ring


def lamp_measure(G8, M, fabric=None):
    """QA's numbers on a graded RGB (uint8) scene: the five targets of section 5 (on QA's shade mask, and on the fabric only)"""
    LAB = lab(G8.astype(np.float32) / 255)
    L, bb = LAB[..., 0], LAB[..., 2]
    med = lambda m, ch=L: float(np.median(ch[m]))  # noqa: E731
    ringL, ringb, ringb95 = med(M["ring"]), med(M["ring"], bb), float(np.percentile(bb[M["ring"]], 95))
    hp = L - cv2.GaussianBlur(L, (0, 0), 3)
    out = {}
    for name, sel in (("qa_shade_mask", None), ("fabric_only", fabric)):
        if name == "fabric_only" and fabric is None:
            continue
        cut = (lambda m: m) if sel is None else (lambda m: m & sel)  # noqa: E731
        sh, le, ri, bo = cut(M["shade"]), cut(M["left"]), cut(M["right"]), cut(M["bottom"])
        lL, rL, bL, sb = med(le), med(ri), med(bo), med(sh, bb)
        n8 = int((bb[sh] >= ringb95 + 8).sum())
        t = {"1 window gradient: left >= right + 5": dict(value=round(lL - rL, 2), pass_=bool(lL - rL >= 5)),
             "2 bottom/inside <= right - 5": dict(value=round(bL - rL, 2), pass_=bool(bL <= rL - 5)),
             "3a left third <= ring + 4": dict(value=round(lL - ringL, 2), pass_=bool(lL <= ringL + 4)),
             "3b right third <= ring": dict(value=round(rL - ringL, 2), pass_=bool(rL <= ringL)),
             "4a median b* <= ring b* + 4": dict(value=round(sb - ringb, 2), pass_=bool(sb <= ringb + 4)),
             "4b no px b* >= ring p95 + 8": dict(value=n8, pass_=n8 == 0)}
        out[name] = dict(px=int(sh.sum()), left_third_L=round(lL, 2), right_third_L=round(rL, 2), bottom15_L=round(bL, 2), shade_b=round(sb, 2),
                         shade_L_p50_p95_max=[round(float(np.percentile(L[sh], q)), 2) for q in (50, 95, 100)],
                         shade_b_max=round(float(bb[sh].max()), 2), highpass_std=round(float(hp[sh].std()), 3), targets=t,
                         all_met=all(v["pass_"] for v in t.values()))
    out["ring"] = dict(px=int(M["ring"].sum()), L=round(ringL, 2), b=round(ringb, 2), b_p95=round(ringb95, 2))
    return out


def raw_step2_registered(rgb_w, M):
    """the step-2 raw render on the work canvas: jobs.json's register_to_input matrix, then the sub-pixel shift measured on the shade
    (phase correlation of the blue channel's high-pass, the one channel the tone match left unclipped)"""
    J = json.load(open(W.JOBS))
    j = next(x for x in J["jobs"] if x["id"] == "wm-ph2-step2-window-floor")
    Mr = np.array(j["register_to_input"], np.float32)
    raw = PW.load(os.path.join(W.RAW, "step2-seedream.png"))
    reg = cv2.warpAffine(raw, Mr, SIZE, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    y0, y1, x0, x1 = M["top"] - 16, M["bot"] + 16, M["x0"] - 40, M["x1"] + 40
    hp = lambda x: (x - cv2.GaussianBlur(x, (0, 0), 3)).astype(np.float32)  # noqa: E731
    win = cv2.createHanningWindow((x1 - x0, y1 - y0), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(hp(rgb_w[y0:y1, x0:x1, 2]), hp(reg[y0:y1, x0:x1, 2]), win)
    T = np.float32([[1, 0, -dx], [0, 1, -dy]])
    reg2 = cv2.warpAffine(reg, T, SIZE, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    (dx2, dy2), _ = cv2.phaseCorrelate(hp(rgb_w[y0:y1, x0:x1, 2]), hp(reg2[y0:y1, x0:x1, 2]), win)
    return reg2, dict(matrix=np.round(Mr, 4).tolist(), subpixel_shift_px=[round(-dx, 3), round(-dy, 3)], response=round(float(resp), 3),
                      residual_after_px=[round(dx2, 3), round(dy2, 3)])


def lamp_tone_rgb(rgb_w, a_w, raw, M, fab, zone, ring, p):
    """the toned RGB of the lamp layer (ungraded). p: Lmid, G (left-right spread), D (lower drop), s (fold detail gain), bT (low b*)"""
    H, Wd = a_w.shape
    Lr = lab(raw)
    Lo, _ = nblur(Lr, fab, 8.0)                          # the raw's low frequencies over the fabric (sigma 8 ~ one fold spacing x 1)
    hpL, hpa, hpb = Lr[..., 0] - Lo[..., 0], Lr[..., 1] - Lo[..., 1], Lr[..., 2] - Lo[..., 2]
    xx = np.arange(Wd, dtype=np.float32)[None, :].repeat(H, 0)
    yy = np.arange(H, dtype=np.float32)[:, None].repeat(Wd, 1)
    u = (xx - M["x0"]) / max(1, M["x1"] - M["x0"])
    v = (yy - M["top"]) / max(1, M["bot"] - M["top"])
    t = np.clip((v - p["v0"]) / (p["v1"] - p["v0"]), 0, 1)
    drop = t * t * (3 - 2 * t)
    T = p["Lmid"] + p["G"] * (0.5 - u) - p["D"] * drop       # graded-L target; the grade is the identity below L 88 (its shoulder starts there)
    hue_a_over_b = float(np.median(Lo[..., 1][fab > 0.5]) / max(np.median(Lo[..., 2][fab > 0.5]), 1e-3))
    Ln = T + p["s"] * hpL
    bn = p["bT"] + p["sc"] * hpb
    an = p["bT"] * hue_a_over_b + p["sc"] * hpa
    t0, lim = p["b_soft"], p["b_lim"]                      # no pixel near ring p95 + 8: a soft knee above t0, never past lim
    over = np.maximum(bn - t0, 0)
    bn = np.where(bn > t0, t0 + over / (1 + over / max(lim - t0, 1e-3)), bn)
    new = rgb_of(Ln, an, bn)
    # the fabric takes the toned colour; its soft edge (alpha < 1) keeps the render's edge mix and takes the fabric's change times alpha
    full = fab > 0.5
    dlt, _ = nblur(new - rgb_w, full.astype(np.float32), 3.0)
    out = rgb_w.copy()
    soft = zone & ~full
    k = a_w * np.where(ring, 0.5, 1.0)                     # the collar's 1 px ring: half the change (mixed brass and fabric)
    out[full] = new[full]
    out[soft] = np.clip(rgb_w[soft] + k[soft][:, None] * dlt[soft], 0, 1)
    return out


def lamp():
    os.makedirs(WR4, exist_ok=True)
    Lw = f32(LAMP_W)
    rgb_w, a_w = Lw[..., :3], Lw[..., 3]
    A8 = np.asarray(Image.open(os.path.join(HERE, "layers", BYID["floor-lamp"]["file"])))[..., 3]
    M = qa_lamp_masks(A8)
    col, ring = collar_mask(rgb_w, a_w, M)
    fab = ((a_w >= 0.999) & ~col & ~ring).astype(np.float32)
    fab[:M["top"] - 2], fab[M["bot"] + 3:] = 0, 0
    zone = (a_w > 0) & ~col
    zone[:M["top"] - 2], zone[M["bot"] + 3:] = False, False
    raw, regrec = raw_step2_registered(rgb_w, M)
    # the scene: the r3 ungraded composite (set B) with the lamp's change added where the lamp shows: U += (L' - L) x a_free x (1 - fa)
    import stack
    if os.path.exists(U_CACHE):
        U = np.load(U_CACHE).astype(np.float32)
    else:
        import grade_cut_r12 as G12
        import grade_cut_r3  # noqa: F401  (sets the r3 sources)
        U, _ = G12.compose(set(grade_cut_r3.ACCEPTED) | {"cushions"}, stack.base_parts(), cushion_set="B")
        os.makedirs(os.path.dirname(U_CACHE), exist_ok=True)
        np.save(U_CACHE, U.astype(np.float32))
    Gr = stack.Grade()
    fa = W.furn_alpha()
    afree = f32(os.path.join(W.WORK, "layers", "floor-lamp-free-alpha.png"), "L")
    vis = (afree * (1 - fa))[..., None]
    fabric_qa = M["shade"] & (fab > 0.5)
    G0 = np.asarray(Image.open(os.path.join(HERE, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
    before = lamp_measure(G0, M, fabric_qa)
    wall = before["ring"]
    hp0 = before["fabric_only"]["highpass_std"]               # the folds: the fabric's graded high-pass std as in r3 (like for like)
    # targets with margins: right third = ring - 2.4, left = right + 5.6 (<= ring + 3.2), the bottom 15 % = right - 6.5, median b* = ring b* + 2.4
    want = dict(right=wall["L"] - 2.4, left=wall["L"] + 3.2, bottom=wall["L"] - 2.4 - 6.5, b=wall["b"] + 2.4)
    p = dict(Lmid=wall["L"], G=8.0, D=9.0, v0=0.70, v1=0.88, s=0.7, sc=0.8, bT=want["b"], b_soft=wall["b_p95"] + 5.6, b_lim=wall["b_p95"] + 7.4)
    hist = []
    for it in range(14):
        rgb_n = lamp_tone_rgb(rgb_w, a_w, raw, M, fab, zone, ring, p)
        Un = U + (rgb_n - rgb_w) * vis
        Gn = Gr(Un)
        m = lamp_measure(Gn, M, fabric_qa)["fabric_only"]
        hist.append(dict(it=it, p={k: round(v, 3) for k, v in p.items()}, left=m["left_third_L"], right=m["right_third_L"], bottom=m["bottom15_L"],
                         b=m["shade_b"], hp=m["highpass_std"]))
        e_r, e_l, e_b = want["right"] - m["right_third_L"], want["left"] - m["left_third_L"], want["bottom"] - m["bottom15_L"]
        e_c, e_h = want["b"] - m["shade_b"], hp0 / max(m["highpass_std"], 1e-3)
        if max(abs(e_r), abs(e_l), abs(e_b), abs(e_c)) < 0.15 and abs(e_h - 1) < 0.02:
            break
        # left / right: the mean and the spread of the ramp; the bottom: the drop; b*: the low b*; the folds: the detail gain
        p["Lmid"] += 0.5 * (e_r + e_l)
        p["G"] += (e_l - e_r) * 1.2
        p["D"] -= e_b - 0.5 * (e_r + e_l)
        p["bT"] += e_c
        p["s"] *= e_h ** 0.9
    rgb_n = lamp_tone_rgb(rgb_w, a_w, raw, M, fab, zone, ring, p)
    pl = save_layer("floor-lamp", rgb_n, a_w)
    for f in ("floor-lamp-free-alpha.png",):
        dst = os.path.join(WR4, "layers", f)
        assert not os.path.exists(dst) or os.environ.get("REDO"), dst
        shutil.copyfile(os.path.join(W.WORK, "layers", f), dst)
    dsts = os.path.join(WR4, "shadows", "floor-lamp.png")
    os.makedirs(os.path.dirname(dsts), exist_ok=True)
    assert not os.path.exists(dsts) or os.environ.get("REDO"), dsts
    shutil.copyfile(os.path.join(W.WORK, "shadows", "floor-lamp.png"), dsts)
    changed = np.abs(f32(pl)[..., :3] - rgb_w).max(2) > 0
    record("floor-lamp", dict(
        what="the shade fabric toned to the designer's targets (section 5), so the product layer reads off; the collar, stem, base and chain "
             "keep their pixels; the light comes from the light layer later (code)",
        source=dict(layer=rel(LAMP_W), raw=rel(os.path.join(W.RAW, "step2-seedream.png")), registration=regrec),
        masks=dict(shade_rows=[M["top"], M["bot"]], shade_cols=[M["x0"], M["x1"]], fabric_px=int(fab.sum()), collar_and_chain_px=int(col.sum()), collar_ring_px=int(ring.sum()),
                   changed_px=int(changed.sum()), changed_outside_zone_px=int((changed & ~zone).sum())),
        method=dict(low_frequencies="replaced by T(u, v) = Lmid + G (0.5 - u) - D smoothstep((v - v0) / (v1 - v0)) in graded L* (u across the shade's "
                                    "columns, v down its rows); b* low = bT at the fabric's own hue",
                    folds="the raw's high-pass (L*, a*, b*) about a normalised sigma-8 blur over the fabric (the folds are ~3-9 px apart), "
                          "L* detail x s so the graded high-pass std stays at the r3 value (the grade's shoulder no longer compresses it)",
                    warmth="b* soft knee from ring p95 + 5.6, never past ring p95 + 7.4",
                    soft_edge="the alpha < 1 rim keeps its render mix plus alpha x the fabric's local change",
                    params={k: round(v, 4) for k, v in p.items()}, iterations=hist),
        targets_before_r3=before, note="targets measured with QA's p2_lamp.py masks on the graded set-B scene; the final numbers are re-measured "
                                       "by grade_cut_r4.py on the r4 scene"))
    print(json.dumps(hist[-1], indent=1))
    return p


# ================================================================================================= 2. the pendant's canopy
def canopy_cut(regt, below, a_old, box=(0, 48, 1615, 1735), cord_x=None, foot_row=None):
    """the ceiling canopy as one rigid convex piece: what is whiter than the ceiling (b* at least 2.5 lower) or differs from it (dE > 6),
    in the canopy's box, above the cord's foot, the cord's own column left out; the largest component, closed (5 px disc) and filled to
    its convex hull; the edge from a guided filter on the render (r 2): 1 in the hull eroded 1 px, 0 beyond 2 px. The cord: below row
    62 a_old's own cut; between the canopy's foot and row 62 the cord's own alpha profile (the median of rows 62-90 across its column,
    +-6 px: the cord hangs plumb), so nothing else of a_old above row 62 is kept (R3's half disc, its tail and the crescent)"""
    y0, y1, x0, x1 = box
    bl = lambda x: cv2.GaussianBlur(np.clip(x, 0, 1).astype(np.float32), (0, 0), 0.8)  # noqa: E731
    lr, lb = cv2.cvtColor(bl(regt), cv2.COLOR_RGB2LAB), cv2.cvtColor(bl(below), cv2.COLOR_RGB2LAB)
    dE = np.sqrt(((lr - lb) ** 2).sum(2))
    whiter = (lb[..., 2] - lr[..., 2]) > 2.5
    if cord_x is None:                                  # the cord's centre where it hangs alone (rows 62-90)
        cord_x = float(np.median([(np.nonzero(a_old[y] > 0.5)[0].min() + np.nonzero(a_old[y] > 0.5)[0].max()) / 2.0 for y in range(62, 91)]))
    m = np.zeros(dE.shape, bool)
    m[y0:y1, x0:x1] = True
    cand = m & ((dE > 6) | whiter)
    if foot_row is None:
        foot_row = 42
    cand[foot_row:] = False
    cord_col = np.zeros(dE.shape, bool)
    cord_col[33:, int(round(cord_x - 3)):int(round(cord_x + 4))] = True
    cand &= ~cord_col
    n, lab_, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
    big = lab_ == 1 + int(np.argmax(st[1:, 4]))
    big = cv2.morphologyEx(big.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))).astype(bool)
    hull = np.zeros(dE.shape, np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(big.astype(np.uint8))), 1)
    hull = hull.astype(bool)
    g = cv2.cvtColor((np.clip(regt, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    ac = np.clip(PW.guided(g, hull.astype(np.float32), 2, 1e-3), 0, 1)
    ac = np.where(X.ero(hull, 1), 1.0, np.where(X.dil(hull, 2), ac, 0.0)).astype(np.float32)
    hb = int(np.nonzero(hull.any(1))[0].max())
    cord = np.zeros(a_old.shape, np.float32)
    c0, c1 = int(math.floor(cord_x - 6)), int(math.ceil(cord_x + 7))
    prof = np.median(a_old[62:91, c0:c1], axis=0)
    cord[hb - 4:62, c0:c1] = prof[None, :]
    out = a_old.copy()
    out[:62] = np.maximum(ac[:62], cord[:62])
    ys, xs = np.nonzero(hull)
    info = dict(cord_x=round(cord_x, 1), hull_box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], hull_px=int(hull.sum()),
                candidate_components=int(n - 1), kept_component_px=int(big.sum()))
    return out.astype(np.float32), hull, info


def pendant():
    L = f32(os.path.join(R3.WR3, "layers", "pendant.png"))
    a_old = L[..., 3]
    regt = np.load(os.path.join(R3.WR3, "r3b-regt.npy")).astype(np.float32)
    below = PW.load(os.path.join(R3.WR3, "scene-B9.png"))
    a_new, hull, info = canopy_cut(regt, below, a_old)
    # the canopy's pieces: R3 (old) against R4 (new), components above row 60
    comps = {}
    for name, a in (("r3", a_old), ("r4", a_new)):
        n, _, st, _ = cv2.connectedComponentsWithStats((a[:62] > 0.5).astype(np.uint8), connectivity=8)
        comps[name] = [int(s) for s in st[1:, 4] if s >= 5]
    save_layer("pendant", L[..., :3], a_new)
    sh = f32(os.path.join(R3.WR3, "shadows", "pendant.png"), "L")
    save_shadow("pendant", sh)
    ch = np.abs(a_new - a_old) > 0
    ys, xs = np.nonzero(ch)
    record("pendant", dict(what="the ceiling canopy re-cut whole from the R3b render (QA: half disc + separate crescent)", source=rel(os.path.join(R3.WR3, "r3b-regt.npy")),
                           method=canopy_cut.__doc__.replace("\n", " "), canopy=info, pieces_above_row_62_px=comps,
                           alpha_changed_px=int(ch.sum()), alpha_changed_box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                           rgb="the R3b render (work-r3/layers/pendant.png's own RGB), unchanged; shadow: none (all white), as in the slot"))
    print("pendant", json.dumps(info), comps)


# ================================================================================================= 3-4. the basket and the planter
SPEC = R3.SPEC


def shadow_r3(k, a, regt, below, surf, others):
    """the contact shadow exactly as R3 measured it (extract.shadow_one with reserve_r3's SPEC)"""
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        return X.shadow_one(k, a, regt, below, surf, others)
    finally:
        X.SPEC[k] = saved


def shadow_ext(k, a, regt, below, surf, others, near=(3.0, 4.5)):
    """R3's measured contact shadow, with the edge fix only: extract.shadow_one blurs the darkening with zeros inside the product and then
    lightens the soft edge by (1 - a) + a, so within ~3 px of the product it fades out and a lighter strip shows between the product and
    its shadow (the basket's light line, the planter's ghost). Here, within 3 px outside the product and on its soft edge (0 < a < 1),
    each pixel takes the shadow R3 measured 3-4.5 px out from the product (a sigma-2.5 blur normalised over that ring, so it follows the
    edge and tapers where R3's shadow ends), never lighter than R3's own value
    and, where that is a real shadow (<= 0.85), never lighter than the render's own darkening right there (the contact occlusion; at most
    20 % deeper); everywhere else the shadow is R3's, unchanged"""
    sh0 = shadow_r3(k, a, regt, below, surf, others)
    prod = a > 0.02
    dist = cv2.distanceTransform((~prod).astype(np.uint8), cv2.DIST_L2, 5)
    ring_all = (dist >= near[0]) & (dist <= near[1])          # the whole ring, shadowed or not, so the carried shadow tapers where R3's ends
    ref = ring_all & (sh0 < 0.999)
    dk, den = nblur((1 - sh0).astype(np.float32), ring_all.astype(np.float32), 2.5)
    she = (1 - dk).astype(np.float32)
    dref = cv2.distanceTransform((~ref).astype(np.uint8), cv2.DIST_L2, 5)
    zone = (((dist < near[0]) & ~prod) | (prod & (a < 0.999))) & (dref <= near[1] + 1.0) & (den > 0.02)
    sh = np.where(zone, np.minimum(sh0, she), sh0)
    # right at the edge the render is often darker still (contact occlusion): in the zone, the shadow is also never lighter than the
    # render's own darkening there (its sRGB-encoded luminance over the scene's, as the multiply works on encoded values; sigma-1 blurs
    # normalised off every product; on the soft edge the
    # value of the nearest pixel 1-2.5 px out), floored at 0.45 as R3's
    occ_any = np.zeros(a.shape, bool)
    for j, m in others.items():
        occ_any |= m > 0.02
    free = (~(prod | occ_any)).astype(np.float32)
    wl = np.array([0.2126, 0.7152, 0.0722], np.float32)       # on the ENCODED values: the multiply layer acts on sRGB-encoded pixels
    nr, _ = nblur((np.clip(regt, 0, 1) * wl).sum(2).astype(np.float32), free, 1.0)
    nb_, _ = nblur((np.clip(below, 0, 1) * wl).sum(2).astype(np.float32), free, 1.0)
    r = np.clip((nr + 1e-4) / (nb_ + 1e-4), 0.45, 1.0)
    out1 = (dist >= 1.0) & (dist <= 2.5) & (free > 0)
    _, lbl2 = cv2.distanceTransformWithLabels((~out1).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    oy, ox = np.nonzero(out1)
    lut2 = np.ones(lbl2.max() + 1, np.float32)
    lut2[lbl2[oy, ox]] = r[oy, ox]
    r_use = np.where((dist >= 1.0) & (free > 0), r, lut2[lbl2])
    # only where R3 measured a real contact shadow nearby (<= 0.85), and at most 20 % deeper than it: elsewhere the render's darker
    # wall next to a product is its relighting, not a shadow (the planter's left side)
    deep = zone & (she <= 0.85)
    sh = np.where(deep, np.minimum(sh, np.maximum(r_use, 0.8 * she)), sh)
    sh = np.where(a >= 0.999, 1.0, sh)
    return np.clip(sh, 0.45, 1.0).astype(np.float32), sh0, dict(edge_px_extended=int((zone & (sh < sh0 - 1 / 255)).sum()), reference_px=int(ref.sum()))


def rematte(regt, a_old, sel, bg):
    """the soft edge re-estimated from the render, in the selection only: F = the product's colour just inside (normalised blur over the
    alpha core, eroded 3 px), B = the render's background just outside (2-7 px beyond the cut, on `bg`); per pixel of the edge band the
    alpha is the projection of its colour on F - B (where |F - B| > 0.06; elsewhere the old alpha); the outline is smoothed at 4x (sigma
    1 px) and anti-aliased; the colour in the band is un-mixed (C - (1 - a) B) / a toward F, so no background of the render stays in it"""
    M = a_old > 0.5
    core = X.ero(M, 3)
    outer = X.dil(M, 7) & ~X.dil(M, 2) & bg
    F, wF = nblur(regt, core.astype(np.float32), 2.0)
    F5, _ = nblur(regt, core.astype(np.float32), 5.0)
    F = np.where((wF > 0.02)[..., None], F, F5)
    B, wB = nblur(regt, outer.astype(np.float32), 2.0)
    B5, _ = nblur(regt, outer.astype(np.float32), 5.0)
    B = np.where((wB > 0.02)[..., None], B, B5)
    band = X.dil(M, 3) & ~core
    D = F - B
    den = (D * D).sum(2)
    aest = np.clip(((regt - B) * D).sum(2) / np.maximum(den, 1e-6), 0, 1)
    ok = band & (np.sqrt(den) > 0.06)
    a_est = np.where(ok, aest, a_old)
    a_est = np.where(core, 1.0, a_est)
    a_est = np.where(X.dil(M, 3), a_est, 0.0).astype(np.float32)
    # the outline: smooth at 4x, anti-aliased back (about a 1.5 px soft edge, as the render's neighbours)
    hard = (a_est > 0.5).astype(np.float32)
    up = cv2.resize(hard, (SIZE[0] * 4, SIZE[1] * 4), interpolation=cv2.INTER_NEAREST)
    up = (cv2.GaussianBlur(up, (0, 0), 4.0) > 0.5).astype(np.float32)
    a_s = cv2.resize(up, SIZE, interpolation=cv2.INTER_AREA)
    a_s = cv2.GaussianBlur(a_s, (0, 0), 0.6)
    a_s = np.where(core, 1.0, a_s)
    wsel = cv2.GaussianBlur(sel.astype(np.float32), (0, 0), 2.0) * sel
    a_new = (wsel * a_s + (1 - wsel) * a_old).astype(np.float32)
    # colour: un-mixed in the band where the estimate is trusted, toward F where it is not
    Fu = (regt - (1 - a_est[..., None]) * B) / np.maximum(a_est, 0.5)[..., None]
    kk = np.clip((a_est - 0.5) / 0.4, 0, 1)[..., None]
    col = np.clip(kk * Fu + (1 - kk) * F, 0, 1)
    use = band & (a_est < 0.95) & ok
    rgb = np.where(use[..., None], col, regt)
    rgb = (wsel[..., None] * rgb + (1 - wsel[..., None]) * regt).astype(np.float32)
    return a_new, rgb, dict(band_px=int((band & sel).sum()), trusted_px=int((ok & sel).sum()), decontaminated_px=int((use & sel).sum()),
                            alpha_changed_px=int((np.abs(a_new - a_old) > 1 / 255).sum()))


def rim_clip(a, rgb, regt, rows=(1030, 1056), fit_rows=(1056, 1076)):
    """the grey crescent left of the pot's mouth (rows ~1034-1052) lies outside the pot's own silhouette: R1's wider rim, carried by the
    photographic placeholder into the R3a render (on the window side, so it cannot be a shadow). The pot's left edge (the alpha 0.5
    crossing) is fitted as a line on rows 1056-1076 and extended up through the rim; left of it the alpha is cut with a 1 px
    anti-aliased edge; the colours are the render's own"""
    ys = np.arange(*fit_rows)
    xe = []
    for y in ys:
        r = a[y]
        x = int(np.nonzero(r > 0.5)[0].min())
        xe.append(x - 0.5 + (0.5 - r[x - 1]) / max(r[x] - r[x - 1], 1e-3))
    k, b = np.polyfit(ys, np.array(xe), 1)
    H, Wd = a.shape
    yy = np.arange(H, dtype=np.float32)[:, None].repeat(Wd, 1)
    xx = np.arange(Wd, dtype=np.float32)[None, :].repeat(H, 0)
    half = np.clip(xx - (k * yy + b) + 0.5, 0, 1)
    zone = np.zeros(a.shape, bool)
    zone[rows[0]:rows[1]] = True
    zone &= xx < (k * yy + b) + 6
    a2 = np.where(zone, a * half, a).astype(np.float32)
    return a2, rgb, dict(line="x = %.4f y + %.2f (the pot's left edge on rows %d-%d)" % (k, b, fit_rows[0], fit_rows[1] - 1),
                          rows=list(rows), alpha_removed_px=round(float((a - a2).sum()), 1), alpha_cut_px=int(((a - a2) > 1 / 255).sum()))


def edges():
    regt = np.load(os.path.join(R3.WR3, "r3a-regt.npy")).astype(np.float32)
    below = PW.load(os.path.join(R3.WR3, "scene-B9.png"))
    Lp, Lb = f32(os.path.join(R3.WR3, "layers", "planter.png")), f32(os.path.join(R3.WR3, "layers", "basket.png"))
    ap, ab = Lp[..., 3], Lb[..., 3]
    ea = R3.layered_alpha()
    H, Wd = ap.shape
    yy = np.arange(H)[:, None].repeat(Wd, 1)
    xx = np.arange(Wd)[None, :].repeat(H, 0)
    surf = X.surfaces()
    surf["front"] = W.furn_alpha() > 0.02
    # the planter: its left side where it stands against the plain wall (no contact shadow within 4 px): the render darkened that wall
    # (relighting, not shadow: the planter's shadow falls on the floor only), and its soft edge carried that dark wall onto the room's
    # own wall (QA's dark dotted rim): re-matted and un-mixed. Its lower left and its bottom stand in its contact shadow: shadow fix only
    sh_p_r3 = f32(os.path.join(R3.WR3, "shadows", "planter.png"), "L")
    shadowed = X.dil(sh_p_r3 < 0.95, 4)
    sel_p = (yy >= 1046) & (yy <= 1205) & (xx >= 935) & (xx <= 1010) & ~X.dil(ab > 0.02, 3) & ~shadowed
    bg_p = (ea < 0.5) & (ab < 0.02)
    ap2, rgb_p, rp = rematte(regt, ap, sel_p, bg_p)
    ap2, rgb_p, rim = rim_clip(ap2, rgb_p, regt)
    sh_p, sh_p0, ip = shadow_ext("planter", ap2, regt, below, surf, {"basket": ab, "_layered": ea})
    # the basket: its cut is kept (its right edge's lit rope ends are the render's own); the light line was its contact shadow fading
    # out next to it: shadow fix only
    sh_b, sh_b0, ib = shadow_ext("basket", ab, regt, below, surf, {"planter": ap2, "_layered": ea})
    save_layer("planter", rgb_p, ap2)
    save_layer("basket", Lb[..., :3], ab)
    save_shadow("planter", sh_p)
    save_shadow("basket", sh_b)
    sh_b_r3 = f32(os.path.join(R3.WR3, "shadows", "basket.png"), "L")
    record("edges", dict(
        what="the planter's left side re-matted where it meets the plain wall, and the grey crescent left of its mouth (R1's wider rim, "
             "carried into R3a) cut at the pot's own edge; the planter's and the basket's contact shadows no longer fade out next to them "
             "(the basket's light line, the planter's ghost); the basket's cut, colours and alpha are R3's",
        source=rel(os.path.join(R3.WR3, "r3a-regt.npy")), below=rel(os.path.join(R3.WR3, "scene-B9.png")),
        rematte=rematte.__doc__.replace("\n", " "), shadow=shadow_ext.__doc__.replace("\n", " "),
        basket=dict(alpha_and_rgb="R3's (work-r3/layers/basket.png), unchanged", shadow=ib,
                    shadow_recomputed_equals_r3_px=int((np.abs(sh_b0 - sh_b_r3) <= 1 / 255).sum()), shadow_px_changed_vs_r3=int((np.abs(sh_b - sh_b_r3) > 1 / 255).sum())),
        planter=dict(selection="the pot's left side, rows 1046-1205, x 935-1010, off the basket (+3 px) and off its R3 contact shadow (+4 px)",
                     rematte=rp, rim_clip=rim, shadow=ip, shadow_px_changed_vs_r3=int((np.abs(sh_p - sh_p_r3) > 1 / 255).sum()))))
    print("edges", json.dumps(dict(basket=ib, planter=rp, shadow_p=ip)))


# ================================================================================================= 5. the vase
def px_of(X_, Y_, Z_):
    u, v, d = S0.P(X_, Y_, Z_)
    return (S0.CX + u * S0.CW) / S0.GW * SIZE[0], (S0.CY + v * S0.CH) / S0.GH * SIZE[1], d


def unproject(xp, yp, Z_):
    """work px on the plane Z = Z_ -> (X, Y, depth); the inverse of step0_clay_checks.P (house plan 1.3.5, M0)"""
    cam = S0.CAM
    C, yaw = cam["loc"], math.radians(cam["yaw_deg_left"])
    f, r = (-math.sin(yaw), -math.cos(yaw)), (math.cos(yaw), -math.sin(yaw))
    u = (xp * S0.GW / SIZE[0] - S0.CX) / S0.CW
    v = (yp * S0.GH / SIZE[1] - S0.CY) / S0.CH
    d = 1.1852 * (C[2] - Z_) / (v - cam["v0"])
    x = (u - cam["u0"]) * d / 0.6667
    return C[0] + d * f[0] + x * r[0], C[1] + d * f[1] + x * r[1], d


def card_vase_box(cx, cy, D=0.16, H=0.32, mouth=0.09, foot=0.10, z0=0.45, n=180):
    """the card's vase (Large: D16, H32, mouth 9; foot ~10, from the render's proportion) projected at (cx, cy) on the bench (Z 0.45):
    the widest silhouette, the mouth's far rim (top) and the foot's near edge (bottom), work px"""
    z1 = z0 + H
    body = [px_of(cx + D / 2 * math.cos(t), cy + D / 2 * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, n) for z in np.linspace(z0 + 0.06, z1 - 0.06, 7)]
    top = min(px_of(cx + mouth / 2 * math.cos(t), cy + mouth / 2 * math.sin(t), z1)[1] for t in np.linspace(0, 2 * math.pi, n))
    bot = max(px_of(cx + foot / 2 * math.cos(t), cy + foot / 2 * math.sin(t), z0)[1] for t in np.linspace(0, 2 * math.pi, n))
    xs = [p[0] for p in body]
    cxp = px_of(cx, cy, z0 + H / 2)
    return dict(width=max(xs) - min(xs), left=min(xs), right=max(xs), top=top, bottom=bot, height=bot - top, centre_x=cxp[0], depth=cxp[2])


def vase_measure(a, rgb):
    """the vase as it is drawn: the foot's contact (the alpha-0.5 crossing on the foot's centre column, and the foot's centre x); the
    mouth's far rim (the row where the median L* of the alpha run through the foot's column falls most from the row above: the dry
    stems against the bright window, then the mouth's opening; searched 100-260 rows above the foot; read on a 3x zoom of the r3 scene
    as row 897); the widest row of the body (sub-pixel: the alpha sum per row, 5-row mean), between the two"""
    m = a > 0.5
    ys = np.nonzero(m.any(1))[0]
    yb = int(ys.max())
    cols = np.nonzero(m[yb - 3:yb + 1].any(0))[0]
    xc = (cols.min() + cols.max() + 1) / 2.0
    ix = int(round(xc))
    col = a[:, ix]
    yb_sub = yb + (float(col[yb]) - 0.5) / max(float(col[yb]) - float(col[yb + 1]), 1e-3)
    Lb = lab(rgb)[..., 0]

    def run_L(y):
        r = m[y]
        if not r[ix]:
            return np.nan
        x0 = ix
        while x0 > 0 and r[x0 - 1]:
            x0 -= 1
        x1 = ix
        while x1 < r.size - 1 and r[x1 + 1]:
            x1 += 1
        return float(np.median(Lb[y, x0:x1 + 1]))
    rr = np.arange(max(int(ys.min()) + 1, yb - 260), yb - 100)
    drops = np.array([run_L(y - 1) - run_L(y) for y in rr])
    top = int(rr[int(np.nanargmax(drops))])
    rows = np.arange(top + 8, yb - 8)
    wsum = a[rows].sum(1)
    w5 = np.convolve(wsum, np.ones(5) / 5, mode="same")
    i = int(np.argmax(w5[2:-2])) + 2
    return dict(foot_centre_x=round(float(xc), 2), foot_contact_y=round(float(yb_sub), 2), foot_row=yb, mouth_top_y=top,
                height_px=round(float(yb_sub - (top - 0.5)), 2), widest_row=int(rows[i]), width_px=round(float(w5[i]), 2))


def vase():
    Lv = f32(os.path.join(W.WORK, "layers", "vase.png"))
    rgb, a = Lv[..., :3], Lv[..., 3]
    Sh = f32(os.path.join(W.WORK, "shadows", "vase.png"), "L")
    m0 = vase_measure(a, rgb)
    # where it actually stands: the foot's near edge on the bench top (Z 0.45), on the ray through the drawn contact; the foot's centre
    # 5 cm behind it, away from the camera
    fx, fy, _ = unproject(m0["foot_centre_x"], m0["foot_contact_y"], 0.45)
    C = S0.CAM["loc"]
    dx, dy = fx - C[0], fy - C[1]
    nrm = math.hypot(dx, dy)
    cx, cy = fx + 0.05 * dx / nrm, fy + 0.05 * dy / nrm
    card = card_vase_box(cx, cy)
    plan = card_vase_box(-2.42, 1.35)
    cmpx = 100 * card["depth"] / ((S0.CAM["lens"] / 36) * S0.CW * SIZE[0] / S0.GW)
    sx, sy = card["width"] / m0["width_px"], card["height"] / m0["height_px"]
    ax, ay = m0["foot_centre_x"], m0["foot_contact_y"]
    Ml = np.float32([[sx, 0, ax * (1 - sx)], [0, sy, ay * (1 - sy)]])
    Ms = np.float32([[sx, 0, ax * (1 - sx)], [0, sx, ay * (1 - sx)]])     # the contact shadow lies on the bench: the foot's scale both ways
    wa = cv2.warpAffine(a, Ml, SIZE, flags=cv2.INTER_AREA)
    wp = cv2.warpAffine(rgb * a[..., None], Ml, SIZE, flags=cv2.INTER_AREA)
    rgb2 = np.where((wa > 1e-4)[..., None], wp / np.maximum(wa, 1e-4)[..., None], 0.0)
    a2 = np.clip(wa, 0, 1)
    # the RGB under alpha 0 (bleed, no effect on the picture): the scaled render where the warp reaches, else the old values
    rgb2 = np.where((wa > 1e-4)[..., None], rgb2, rgb)
    dark = cv2.warpAffine(1 - Sh, Ms, SIZE, flags=cv2.INTER_AREA)
    sh2 = np.clip(1 - dark, 0, 1)
    sh2 = np.where(a2 >= 0.999, 1.0, sh2)
    m1 = vase_measure(a2, rgb2)
    save_layer("vase", rgb2, a2)
    save_shadow("vase", sh2)
    rec = dict(
        what="scaled in code to the card (Large D16 x H32), anchored at its current base; NOT moved (placement pending the designer)",
        source=dict(layer=rel(os.path.join(W.WORK, "layers", "vase.png")), shadow=rel(os.path.join(W.WORK, "shadows", "vase.png"))),
        measured_before=m0, stands_at=dict(foot_near_edge_xy=[round(fx, 3), round(fy, 3)], base_centre_xy=[round(cx, 3), round(cy, 3)], Z=0.45,
                                          depth_m=round(card["depth"], 3), cm_per_px=round(cmpx, 4),
                                          vs_plan_point=dict(plan=[-2.42, 1.35], offset_m=round(math.hypot(cx + 2.42, cy - 1.35), 3),
                                                             toward_camera_m=round(math.hypot(4.355 - card["depth"], 0), 3))),
        card_at_its_place_px={k: round(v, 2) for k, v in card.items()}, card_at_plan_point_px={k: round(v, 2) for k, v in plan.items()},
        before_cm=dict(height=round(32 * m0["height_px"] / card["height"], 1), width=round(16 * m0["width_px"] / card["width"], 1),
                       how="the card's cylinder projected at the vase's own base point is the ruler (H 32 = card height px, D 16 = card width px)",
                       ratio_vs_card=[round(m0["width_px"] / card["width"], 3), round(m0["height_px"] / card["height"], 3)]),
        scale=dict(sx=round(sx, 4), sy=round(sy, 4), anchor_px=[round(ax, 2), round(ay, 2)], layer_matrix=np.round(Ml, 4).tolist(),
                   shadow_matrix=np.round(Ms, 4).tolist(), why_two_factors="the render's height : width is ~2.3 : 1 against the card's 2 : 1 "
                   "(QA: proportion partial), so each axis is brought to the card (QA's recipe: uniform unless the source proportion is wrong)"),
        measured_after=m1, after_cm=dict(height=round(32 * m1["height_px"] / card["height"], 1), width=round(16 * m1["width_px"] / card["width"], 1),
                                         ratio_vs_card=[round(m1["width_px"] / card["width"], 3), round(m1["height_px"] / card["height"], 3)]),
        base_kept=dict(foot_centre_x_shift_px=round(m1["foot_centre_x"] - m0["foot_centre_x"], 2),
                       foot_contact_y_shift_px=round(m1["foot_contact_y"] - m0["foot_contact_y"], 2)),
        shadow="the measured contact shadow (work/shadows/vase.png) shrunk about the same anchor at the foot's scale (sx, sx): it lies on "
               "the bench; 1 under the new full alpha; what the vase uncovers is the base's own window, frame and bench",
        status="size fixed; placement pending the designer")
    record("vase", rec)
    print(json.dumps({k: rec[k] for k in ("measured_before", "before_cm", "scale", "measured_after", "after_cm", "base_kept")}, indent=1))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("lamp", "all"):
        lamp()
    if what in ("pendant", "all"):
        pendant()
    if what in ("edges", "all"):
        edges()
    if what in ("vase", "all"):
        vase()
