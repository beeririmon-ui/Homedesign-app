#!/usr/bin/env python3
"""
kids_qa_fixes.py: code fixes of the kids' stage one after QA (qa/reports/2026-11-24-kids-stage1), render-agent, 2026-11-24; 0 tokens.
Each step works on the layers a cut wrote, so it is re-run after that cut.
  python3 kids_qa_fixes.py nest boy      K-B3: the cushion pair (layer and shadow) moved left until its left cushion overlaps the
                                          standing pillow by 0.02 of the frame's width (ד.2: "at least 0.02, no strip") on every row
                                          where both are; the bear stays in front (z 57)
  python3 kids_qa_fixes.py stripes boy   K-B2: the duvet set's stripes (the bedding layer): the thin, sharp, paired lines widened to
                                          about half the period and softened (melange), their contrast brought to the photo's
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402

C = K.C
H, W = K.H, K.W


def _layer(man, key):
    return [l for l in man["layers"] if l["key"] == key and l.get("default", True)][0]


def nest(kid):
    st = K.ST[kid]
    man = KC.load_man(kid)
    lp, lc = _layer(man, "pillowcase"), _layer(man, "cushions-pair")
    P = np.asarray(Image.open(os.path.join(st, lp["layer"])))[..., 3] > 128
    cu_rgba = np.asarray(Image.open(os.path.join(st, lc["layer"])))
    cu_sh = np.asarray(Image.open(os.path.join(st, lc["shadow"])))
    Cm = cu_rgba[..., 3] > 128
    need = int(round(0.02 * K.FW)) + 1
    # the rows where the standing pillow and the pair meet: the pair's left edge, the pillow's right edge just left of it
    gaps, rows = [], []
    ys_c = np.nonzero(Cm.any(1))[0]
    for y in range(ys_c.min(), ys_c.max() + 1):
        c = np.nonzero(Cm[y])[0]
        if not c.size:
            continue
        p = np.nonzero(P[y, max(0, c.min() - 150):c.min() + 1])[0]
        if p.size:
            gaps.append(c.min() - (max(0, c.min() - 150) + p.max()))
            rows.append(y)
    gap = int(np.percentile(gaps, 95)) if gaps else 0
    dx = -(gap + need)
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    rgba2 = np.dstack([cv2.warpAffine(cu_rgba[..., c], M, (W, H), flags=cv2.INTER_NEAREST, borderValue=0) for c in range(4)])
    sh2 = cv2.warpAffine(cu_sh, M, (W, H), flags=cv2.INTER_NEAREST, borderValue=255)
    Image.fromarray(rgba2, "RGBA").save(os.path.join(st, lc["layer"]), optimize=True)
    Image.fromarray(sh2).save(os.path.join(st, lc["shadow"]), optimize=True)
    C2 = rgba2[..., 3] > 128
    ov = []
    for y in rows:
        c = np.nonzero(C2[y])[0]
        p = np.nonzero(P[y, :c.min() + 200])[0] if c.size else np.array([])
        if c.size and p.size:
            ov.append(int(p.max() - c.min()))
    ys, xs = np.nonzero(C2)
    for l in man["layers"]:
        if l["key"] == "cushions-pair" and l.get("default", True):
            l["bbox_px"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    rec = dict(gap_before_px_p95=gap, moved_px=dx, overlap_after_px_min_p50=[min(ov), int(np.median(ov))] if ov else None,
               need_px=need, why="K-B3: the strip between the standing pillow and the pair (ד.8, Bible 1.1 'the nest'); ד.2 asks an "
                                 "overlap of at least 0.02")
    man.setdefault("code_fixes", {})["K-B3 nest"] = rec
    KC.save_man(kid, man)
    print(json.dumps(rec))


def cushion_edge(kid):
    """K-B3 follow-up: the pair's left edge, cut against the wall in PB2 (wall_trim "chroma"), lies on the standing pillow since the
    move and reads torn (notches up to about 12 px, grey bits of the old strip in them, brown slivers of its shade on the strip and
    under its bottom). The slivers go first (an opening of 5 px; the pieces under 2,000 px). Row by row its outline (the leftmost alpha)
    is filled out to a smooth outer envelope (the rolling min over 41 rows, a Gaussian of 6 rows, at most 14 px out); the filled
    pixels and the not-cushion bits at the left edge (C* < 18 within 4 px) are inpainted (Telea, 5 px) from the cushion only, a 1 px
    soft edge. Never cuts (under the cut the pillow layer carries the old strip's grey). Its shade left of the edge (cast on the
    old strip, ragged, down to 0.67) blurred 4 px and held to 0.25 at most: on the pillow it touches. Re-run after nest"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lc = _layer(man, "cushions-pair")
    rgba = np.asarray(Image.open(os.path.join(st, lc["layer"]))).copy()
    A0 = rgba[..., 3] > 0
    # the slivers the PB2 wall trim left round the pair (its brown shade on the strip and under its bottom, cut off from the body
    # by alpha 0 or a 1-2 px neck): an opening of 5 px, the body's pieces of 2,000 px or more, grown back 1 px
    op = cv2.morphologyEx(A0.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, lbl, stt, _ = cv2.connectedComponentsWithStats(op, 8)
    body = np.isin(lbl, [i for i in range(1, n) if stt[i, 4] >= 2000])
    A = A0 & C.dil(body, 1)
    sliv = A0 & ~A
    rgba[..., 3][sliv] = 0
    ys = np.nonzero(A.any(1))[0]
    rows = np.arange(ys.min(), ys.max() + 1)
    lv = np.array([np.nonzero(A[y])[0].min() if A[y].any() else W for y in rows], np.float64)
    col = lv.astype(np.float32)[:, None]
    mn = cv2.erode(col, np.ones((41, 1), np.uint8), borderType=cv2.BORDER_REPLICATE)
    env = cv2.GaussianBlur(mn, (1, 0), sigmaX=0.1, sigmaY=6, borderType=cv2.BORDER_REPLICATE)[:, 0].astype(np.float64)
    env = np.minimum(np.maximum(env, lv - 14), lv)
    xs = np.arange(W)[None, :]
    F = np.zeros((H, W), bool)
    frac = np.zeros((H, W))
    F[rows] = (xs >= np.ceil(env)[:, None]) & (xs < lv[:, None])
    edge_px = np.zeros((H, W), bool)
    edge_px[rows] = (xs == (np.ceil(env) - 1)[:, None])
    frac[rows] = np.where(edge_px[rows], (np.ceil(env) - env)[:, None], 0)
    lab = C.to_lab(rgba[..., :3].astype(np.float64) / 255)
    leftband = np.zeros((H, W), bool)
    leftband[rows] = xs < (lv + 4)[:, None]
    grey = A & leftband & (np.hypot(lab[..., 1], lab[..., 2]) < 18)
    fillm = F | grey | edge_px
    # the inpaint draws from the cushion only: everything outside its alpha is unknown (in its bounding box, 24 px round)
    yy, xx = np.nonzero(A | fillm)
    by0, by1, bx0, bx1 = max(yy.min() - 24, 0), min(yy.max() + 25, H), max(xx.min() - 24, 0), min(xx.max() + 25, W)
    unknown = (fillm | ~A)[by0:by1, bx0:bx1]
    sub = cv2.inpaint(np.ascontiguousarray(rgba[by0:by1, bx0:bx1, :3]), unknown.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
    rgb = rgba[..., :3].copy()
    rgb[by0:by1, bx0:bx1] = sub
    rgba[..., :3] = np.where(fillm[..., None], rgb, rgba[..., :3])
    a = rgba[..., 3].astype(np.float64)
    a = np.where(F | grey, 255, a)
    a = np.where(edge_px & ~A, np.maximum(a, frac * 255), a)
    rgba[..., 3] = np.clip(np.round(a), 0, 255).astype(np.uint8)
    rgba[..., :3][rgba[..., 3] == 0] = 0
    Image.fromarray(rgba, "RGBA").save(os.path.join(st, lc["layer"]), optimize=True)
    # its shade on the standing pillow, left of the new edge: the old shade (cast on the strip, ragged) blurred 4 px, at most 0.25
    sh = np.asarray(Image.open(os.path.join(st, lc["shadow"]))).astype(np.float64) / 255
    band = np.zeros((H, W), bool)
    band[rows] = (xs >= (env - 30)[:, None]) & (xs < (env + 3)[:, None])
    dark = np.minimum(C.blur(1 - sh, 4), 0.25)
    sh2 = np.where(band, 1 - dark, sh)
    sh2 = np.where(sh2 > 0.995, 1.0, sh2)
    Image.fromarray(C.q(sh2)).save(os.path.join(st, lc["shadow"]), optimize=True)
    rec = dict(sliver_px_let_go=int(sliv.sum()), px_filled=int((F & ~A).sum()), grey_px_inpainted=int(grey.sum()), max_fill_px=int(np.max(lv - env)),
               shade_band_max_before_after=[round(float((1 - sh)[band].max()), 3), round(float((1 - sh2)[band].max()), 3)],
               method=cushion_edge.__doc__.strip())
    man.setdefault("code_fixes", {})["K-B3 nest edge"] = rec
    KC.save_man(kid, man)
    print(json.dumps({k: v for k, v in rec.items() if k != "method"}))


def stripes(kid, sig=2.2, gain=None):
    """the bedding layer's fine structure (L* minus its 12 px blur) is the stripes: blurred across (sigma 2.2 px) they widen to a soft
    band about half the ~24 px period, then scaled so its p5-p95 is the photo's (-10.5 ... +7.5 against -19.6 ... +11.4 drawn)"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lb = _layer(man, "bedding")
    src = os.path.join(K.SCR, f"{kid}-bedding-cut.png")          # the layer as cut (never this step's own output)
    rgba = np.asarray(Image.open(src if os.path.exists(src) else os.path.join(st, lb["layer"]))).astype(np.float64) / 255
    a = rgba[..., 3]
    m = a > 0
    lab = C.to_lab(rgba[..., :3])
    w = m.astype(np.float64)
    low = np.stack([C.blur(lab[..., c] * w, 12) / np.maximum(C.blur(w, 12), 1e-4) for c in range(3)], -1)   # about half the period
    hp = lab - low
    core = C.ero(m, 8)
    p5, p95 = np.percentile(hp[..., 0][core], [5, 95])
    hp2 = np.stack([C.blur(hp[..., c] * w, sig) / np.maximum(C.blur(w, sig), 1e-4) for c in range(3)], -1)
    q5, q95 = np.percentile(hp2[..., 0][core], [5, 95])
    g = gain if gain else (7.5 + 10.5) / max(q95 - q5, 1e-3)
    new = low + hp2 * g
    new[..., 0] = np.clip(new[..., 0], 0, 100)
    out_lab = np.where(m[..., None], new, lab)
    rgb = KC.floor_lab(np.clip(C.from_lab(out_lab), 0, 1), m)
    out = np.dstack([C.q(rgb), C.q(a)])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(st, lb["layer"]), optimize=True)
    r5, r95 = np.percentile((out_lab - low)[..., 0][core], [5, 95])
    rec = dict(drawn_p5_p95=[round(float(p5), 1), round(float(p95), 1)], after_p5_p95=[round(float(r5), 1), round(float(r95), 1)],
               photo_p5_p95=[-10.5, 7.5], blur_sigma_px=sig, gain=round(float(g), 3), method=stripes.__doc__.strip(),
               why="K-B2: the set's stripes are wide and soft (melange jersey), about as wide as the gap; drawn thin, sharp and paired")
    man.setdefault("code_fixes", {})["K-B2 stripes"] = rec
    KC.save_man(kid, man)
    print(json.dumps(rec))


def _bedding_exposed(kid, man, rgba):
    """where the cushion pair stood before K-B3 moved it (its alpha shifted back), above its old bottom less 10 px, the bedding
    layer's pieces of the wall (the PB1 edit's shade of the pair on the wall: h 80-150, C* < 15, L* < 75, on a 1.5 px blur) let
    go, so the plate's wall shows"""
    mv = man.get("code_fixes", {}).get("K-B3 nest", {}).get("moved_px")
    if not mv:
        return rgba
    st = K.ST[kid]
    lc = _layer(man, "cushions-pair")
    cu = np.asarray(Image.open(os.path.join(st, lc["layer"])))[..., 3] > 0
    old = cv2.warpAffine(cu.astype(np.uint8), np.float32([[1, 0, -mv], [0, 1, 0]]), (W, H), flags=cv2.INTER_NEAREST) > 0
    exposed = C.dil(old, 6) & ~cu
    bottom = np.where(old.any(0), H - 1 - np.argmax(old[::-1], 0), -1)      # the old pair's lowest row, per column
    exposed &= np.arange(H)[:, None] < (bottom - 10)[None, :]               # above it: the wall; at it, the duvet's top edge
    A = rgba[..., 3] > 0
    lab = C.to_lab(C.blur(rgba[..., :3] * A[..., None], 1.5) / np.maximum(C.blur(A.astype(np.float64), 1.5), 1e-4)[..., None])
    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    ch = np.hypot(lab[..., 1], lab[..., 2])
    wall = A & exposed & (hue > 80) & (hue < 150) & (ch < 15) & (lab[..., 0] < 75)
    wall = C.dil(wall, 1) & A & exposed
    out = rgba.copy()
    out[..., 3] = np.where(wall, 0, rgba[..., 3])
    edge = C.dil(wall, 1) & ~wall & A
    out[..., 3] = np.where(edge, np.minimum(out[..., 3], 0.5), out[..., 3])
    _bedding_exposed.px = int(wall.sum())
    return out


def restripe(kid):
    """K-B2 by the PB1b edit: the bedding layer keeps its alpha (the geometry QA passed) and takes the edit's pixels, matched to its base
    by the gain field (kids_cut.edit_canvas), wherever it is solid (alpha 250+) and no product above it is solid (the throw, the
    pillows, the basket, the cushions, the toy: under their soft edges it takes the edit too, which drew them in the same place, so
    no edge mixes with the old stripes); under them and at its own soft edge it keeps its earlier colours"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lb = _layer(man, "bedding")
    S = KC.edit_canvas("PB1b-stripes")
    e = S["e"]
    src = os.path.join(K.SCR, f"{kid}-bedding-cut.png")
    rgba = np.asarray(Image.open(src if os.path.exists(src) else os.path.join(st, lb["layer"]))).astype(np.float64) / 255
    rgba = _bedding_exposed(kid, man, rgba)
    upper = np.zeros((H, W))
    for l in man["layers"]:
        if l.get("default", True) and l["z"] > lb["z"]:
            upper = np.maximum(upper, np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] / 255)
    take = (rgba[..., 3] >= 250 / 255) & (upper < 0.999) & S["box"]    # under an upper product's soft edge too: the edit drew it there
    take = C.ero(take, 1)
    # the base the edit saw carried the products' shadows (multiply, z above the bedding); the edit drew them again, so the layer
    # takes the edit divided by them (linear), and the composite multiplies them back once
    shm = np.ones((H, W))
    for l in man["layers"]:
        if l.get("default", True) and l.get("shadow") and l.get("shadow_z", -1) > lb["z"]:
            shm *= np.asarray(Image.open(os.path.join(st, l["shadow"]))).astype(np.float64) / 255
    e = C.srgb(np.clip(C.lin(e) / np.maximum(shm, 0.2)[..., None], 0, 1))
    wgt = C.blur(take.astype(np.float64), 1.0)[..., None] * (rgba[..., 3:] >= 250 / 255)
    rgb = rgba[..., :3] * (1 - wgt) + e * wgt
    out = np.dstack([C.q(rgb), C.q(rgba[..., 3])])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(st, lb["layer"]), optimize=True)
    lab = C.to_lab(e)
    w_ = take.astype(np.float64)
    low = C.blur(lab[..., 0] * w_, 12) / np.maximum(C.blur(w_, 12), 1e-4)
    core = C.ero(take, 8)
    r5, r95 = np.percentile((lab[..., 0] - low)[core], [5, 95])
    lab0 = C.to_lab(rgba[..., :3])
    low0 = C.blur(lab0[..., 0] * w_, 12) / np.maximum(C.blur(w_, 12), 1e-4)
    q5, q95 = np.percentile((lab0[..., 0] - low0)[core], [5, 95])
    rec = dict(px_taken=int(take.sum()), wall_px_let_go=getattr(_bedding_exposed, "px", 0), stripes_L_p5_p95_before=[round(float(q5), 1), round(float(q95), 1)],
               after=[round(float(r5), 1), round(float(r95), 1)], photo=[-10.5, 7.5], method=restripe.__doc__.strip(),
               why="K-B2: the set's stripes are wide and soft (melange jersey); the code attempt (a blur across, then the photo's contrast) "
                   "read out of focus at x2, so one edit (400) redrew the pattern only")
    man.setdefault("code_fixes", {})["K-B2 stripes"] = rec
    KC.save_man(kid, man)
    print(json.dumps(rec))


def bear(kid):
    """the soft toy's alpha, the bear only. In its lower half (below 880, the top of the arms) the PB2 cut carried the duvet round
    the feet (the edit's white and grey, b* about 5 against the bear's 15): GrabCut on the composite the PB1b edit saw (5 rounds),
    the outside of the alpha the background, the alpha above 880 and its cream core (6 px in, b* > 12) the bear, the rest of the
    lower alpha probable bear where b* > 10, probable duvet where not; the bear's piece kept (small islands let go), the cut edge
    softened 0.7 px; nothing above 880 changes but the white fringe of the outline (edge pixels lighter than the bear 3 px inside
    take its colour). Run before restripe, which then draws the duvet where the alpha let go"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lt = _layer(man, "soft-toy")
    src = os.path.join(K.SCR, f"{kid}-soft-toy-cut.png")
    if not os.path.exists(src):                                    # the layer as cut, kept once, so the step can be re-run
        Image.open(os.path.join(st, lt["layer"])).save(src)
    rgba = np.asarray(Image.open(src)).astype(np.float64) / 255
    a = rgba[..., 3]
    A = a > 0
    lab = C.to_lab(C.blur(rgba[..., :3] * A[..., None], 1.5) / np.maximum(C.blur(A.astype(np.float64), 1.5), 1e-4)[..., None])
    Y = np.arange(H)[:, None] + np.zeros((1, W), int)
    ys, xs = np.nonzero(A)
    x0, y0, x1, y1 = xs.min() - 20, 860, xs.max() + 21, ys.max() + 21
    img = np.asarray(Image.open(os.path.join(K.SCR, f"base-{kid}-PB1b.png")).convert("RGB"))[y0:y1, x0:x1].copy()
    gc = np.full(img.shape[:2], cv2.GC_BGD, np.uint8)
    sA, sY, sb = A[y0:y1, x0:x1], Y[y0:y1, x0:x1], lab[y0:y1, x0:x1, 2]
    gc[sA & (sb > 10)] = cv2.GC_PR_FGD
    gc[sA & (sb <= 10)] = cv2.GC_PR_BGD
    gc[sA & (sY <= 880)] = cv2.GC_FGD
    gc[C.ero(A, 6)[y0:y1, x0:x1] & (sb > 12)] = cv2.GC_FGD
    bgm, fgm = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, gc, None, bgm, fgm, 5, cv2.GC_INIT_WITH_MASK)
    fg = np.zeros((H, W), bool)
    fg[y0:y1, x0:x1] = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    keep = A & ((Y <= 880) | fg)
    keep = np.where(Y > 880, cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0, keep)
    n, lb, stt, _ = cv2.connectedComponentsWithStats(keep.astype(np.uint8), 8)
    keep = lb == (1 + int(np.argmax(stt[1:, 4])))
    rgb = rgba[..., :3].copy()
    solid = C.ero(keep & (a > 0.98), 3)
    w2 = C.blur(solid.astype(np.float64), 3)
    in2 = np.stack([C.blur(rgba[..., c] * solid, 3) for c in range(3)], -1) / np.maximum(w2, 1e-4)[..., None]
    rim = keep & ~solid & (w2 > 0.02) & (C.luma(rgb) > C.luma(in2) + 0.03)
    rgb[rim] = in2[rim]
    cut_edge = keep & C.dil(A & ~keep, 1)
    soft = C.blur(keep.astype(np.float64), 0.7)
    a2 = np.where(keep, np.where(cut_edge, np.minimum(a, soft), a), 0.0)
    a2[a2 < 2 / 255] = 0
    out = np.dstack([C.q(rgb), C.q(a2)])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(st, lt["layer"]), optimize=True)
    ys, xs = np.nonzero(out[..., 3])
    for l in man["layers"]:
        if l["key"] == "soft-toy" and l.get("default", True):
            l["alpha_px"] = int(xs.size)
            l["bbox_px"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    rec = dict(px_dropped=int((A & (out[..., 3] == 0)).sum()), alpha_px_before_after=[int(A.sum()), int(xs.size)],
               rim_px_defringed=int(rim.sum()), method=bear.__doc__.strip(),
               why="K-B3 / K-L1: the bear's alpha carried the duvet round its feet; with the new stripes (K-B2) it read as a white patch")
    man.setdefault("code_fixes", {})["K-L1 bear alpha"] = rec
    KC.save_man(kid, man)
    print(json.dumps({k: v for k, v in rec.items() if k != "method"}))


def cars(kid, cm_px=0.150, card_cm=(8.5, 4.3)):
    """K-B1: the cars from the PB5b edit (the SKU photo its reference), their size the card's.
    1. the cars: what the edit changed against the empty plate (dE76 > 12), beech (L* > 42, C* > 12, h 40-90), the wheels' dark
       undersides grown in (changed by 14+, not a shade: a shade keeps the plate's hue and is darker), small holes filled, the round
       hole of each body left open (the plate's wall shows through it);
    2. one uniform scale s for the group, the geometric mean of the card's length and height over the cars' (the two side-on cars'
       bounding boxes), so each is within about 10 % of 8.5 x 4.3 cm; about the group's contact point (centre x, lowest contact y),
       premultiplied, INTER_AREA;
    3. the contact shade: the edit's darkening of the plate round the cars (kids_cut.shadow_soft, band 12, rim 3), scaled the same
       way, kept on the desk top only"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lc = _layer(man, "toy-cars")
    lb = _layer(man, "bookends")
    S = KC.edit_canvas("PB5b-cars")
    e = S["e"]
    plate = C.load(os.path.join(st, "plate.png"))
    le, lp = C.to_lab(e), C.to_lab(plate)
    d = np.linalg.norm(le - lp, axis=-1)
    ch = np.hypot(le[..., 1], le[..., 2])
    hue = np.degrees(np.arctan2(le[..., 2], le[..., 1]))
    hp = np.degrees(np.arctan2(lp[..., 2], lp[..., 1]))
    book = C.dil(np.asarray(Image.open(os.path.join(st, lb["layer"])))[..., 3] > 0, 3)
    box = S["box"] & ~book
    box[:S["rec"]["crop_box"][1] + 4] = False
    seed = box & (d > 12) & (le[..., 0] > 42) & (ch > 12) & (hue > 40) & (hue < 90)
    dh = np.abs((hue - hp + 180) % 360 - 180)
    shade = (dh < 12) & (le[..., 0] < lp[..., 0] - 1)
    car = seed | (C.dil(seed, 5) & box & (d > 14) & ~shade)
    car = cv2.morphologyEx(car.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
    n, lab, stt, _ = cv2.connectedComponentsWithStats(car.astype(np.uint8), 8)
    car = np.isin(lab, [i for i in range(1, n) if stt[i, 4] >= 30])
    inv = (~car).astype(np.uint8)
    n, lab, stt, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, n):
        if stt[i, 4] < 40:
            car |= lab == i
    ys, xs = np.nonzero(car)
    X0, Y0, X1, Y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    # the side-on cars: the columns split at the two deepest gaps of the column profile, the first two pieces
    prof = car[Y0:Y1, X0:X1].sum(0).astype(np.float64)
    sm = np.convolve(prof, np.ones(5) / 5, "same")
    w_ = X1 - X0
    cuts = []
    for lo, hi in [(int(w_ * 0.25), int(w_ * 0.5)), (int(w_ * 0.55), int(w_ * 0.8))]:
        cuts.append(X0 + lo + int(np.argmin(sm[lo:hi])))
    pieces = [(X0, cuts[0]), (cuts[0], cuts[1]), (cuts[1], X1)]
    dims = []
    for a, b in pieces:
        yy, xx = np.nonzero(car[:, a:b])
        dims.append((int(xx.max() - xx.min() + 1), int(yy.max() - yy.min() + 1)))
    Lm = np.mean([dims[0][0], dims[1][0]])
    Hm = np.mean([dims[0][1], dims[1][1]])
    tL, tH = card_cm[0] / cm_px, card_cm[1] / cm_px
    s = float(np.sqrt((tL / Lm) * (tH / Hm)))
    # contact point: the group's centre x, its lowest car pixel
    ax, ay = (X0 + X1) / 2.0, float(Y1)
    # 3. the contact shade, in the edit's own place
    block = book
    sh = KC.shadow_soft(e, plate, car, dict(band=12, rim=3), block, cap=0.55)
    dark = 1 - sh
    # 2. the scale: premultiplied crop, INTER_AREA
    m = 16
    cx0, cy0, cx1, cy1 = X0 - m, Y0 - m, X1 + m, Y1 + m
    a_full = C.blur(car.astype(np.float64), 0.6)
    a_full[~C.dil(car, 2)] = 0
    a_full[car & C.ero(car, 1)] = 1
    crop_rgb = e[cy0:cy1, cx0:cx1] * a_full[cy0:cy1, cx0:cx1, None]
    crop_a = a_full[cy0:cy1, cx0:cx1]
    crop_d = dark[cy0:cy1, cx0:cx1]
    nw, nh = int(round((cx1 - cx0) * s)), int(round((cy1 - cy0) * s))
    r_rgb = cv2.resize(crop_rgb, (nw, nh), interpolation=cv2.INTER_AREA)
    r_a = cv2.resize(crop_a, (nw, nh), interpolation=cv2.INTER_AREA)
    r_d = cv2.resize(crop_d, (nw, nh), interpolation=cv2.INTER_AREA)
    ox = int(round(ax - (ax - cx0) * s))
    oy = int(round(ay - (ay - cy0) * s))
    A = np.zeros((H, W))
    RGB = np.zeros((H, W, 3))
    D = np.zeros((H, W))
    A[oy:oy + nh, ox:ox + nw] = r_a
    RGB[oy:oy + nh, ox:ox + nw] = r_rgb
    D[oy:oy + nh, ox:ox + nw] = r_d
    rgb = np.clip(RGB / np.maximum(A[..., None], 1e-4), 0, 1)
    A[A < 1.5 / 255] = 0
    desk = (lp[..., 0] < 52) & ~book                        # the walnut top under the cars, never the wall behind them
    D = np.where(desk & (A < 0.999), D, 0)
    D = C.blur(D, 0.8) * desk
    out = np.dstack([C.q(rgb), C.q(A)])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(st, lc["layer"]), optimize=True)
    shp = np.where(D > 0.004, 1 - D, 1.0)
    Image.fromarray(C.q(shp)).save(os.path.join(st, lc["shadow"]), optimize=True)
    # what came out, in cm, per car
    Ab = A > 0.5
    after = []
    for a, b in pieces:
        a2, b2 = int(round(ax + (a - ax) * s)), int(round(ax + (b - ax) * s))
        yy, xx = np.nonzero(Ab[:, a2:b2])
        after.append([round((xx.max() - xx.min() + 1) * cm_px, 1), round((yy.max() - yy.min() + 1) * cm_px, 1)])
    labc = C.to_lab(rgb)
    yy, xx = np.nonzero(Ab)
    lit = Ab & (np.arange(H)[:, None] < yy.min() + 0.4 * (yy.max() - yy.min() + 1))
    Lv = np.median(labc[..., 0][lit]); av = np.median(labc[..., 1][lit]); bv = np.median(labc[..., 2][lit])
    for l in man["layers"]:
        if l["key"] == "toy-cars" and l.get("default", True):
            l["alpha_px"] = int((out[..., 3] > 0).sum())
            l["shadow_px"] = int((shp < 1).sum())
            l["bbox_px"] = [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]
            l["source"] = "pass PB5b-cars (nano-banana-2 crop edit, the SKU photo as reference), cut and scaled to the card in code " \
                          "(tools/kids_qa_fixes.py cars)"
    rec = dict(edit_cars_px_LxH=[list(map(int, x)) for x in dims], scale=round(s, 3), anchor_px=[round(ax, 1), round(ay, 1)],
               after_cm_LxH=after, card_cm=list(card_cm), cm_per_px=cm_px,
               lit_lab=[round(float(Lv), 1), round(float(av), 1), round(float(bv), 1)],
               lit_lch=[round(float(Lv), 1), round(float(np.hypot(av, bv)), 1), round(float(np.degrees(np.arctan2(bv, av))), 1)],
               method=cars.__doc__.strip(), why="K-B1: the cars were roadsters 1.6-2x the card; the edit drew the SKU's beetle")
    man.setdefault("code_fixes", {})["K-B1 cars"] = rec
    KC.save_man(kid, man)
    print(json.dumps({k: v for k, v in rec.items() if k != "method"}))


def chain(kid):
    """the boy's nest and bed after a re-cut of PB2-nest or PB1b-stripes, in order: nest, cushion_edge, bear, restripe"""
    for f in (nest, cushion_edge, bear, restripe):
        f(kid)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"nest": nest, "stripes": stripes, "restripe": restripe, "cars": cars, "bear": bear, "cushion_edge": cushion_edge, "chain": chain}[a[0]](a[1])
