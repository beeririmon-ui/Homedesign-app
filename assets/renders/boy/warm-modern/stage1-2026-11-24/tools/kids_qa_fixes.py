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
    under its bottom). The slivers go first (an opening of 5 px; the pieces under 2,000 px; in the outer 6 px, C* < 24: the shade,
    the corduroy's p5 is 27.5); where they went along the bottom, the restriped duvet shows. The bottom edge's stair (1 px
    opaque lines under its soft rows) let go: over each column's last 6 rows the alpha may only fall. Row by row its outline (the leftmost alpha)
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
    # and the shade itself where it hugs the body: in the outer 6 px, C* under 24 on a 1 px blur (the corduroy: 27.5 at p5)
    labs = C.to_lab(C.blur(rgba[..., :3].astype(np.float64) / 255 * A0[..., None], 1.0) / np.maximum(C.blur(A0.astype(np.float64), 1.0), 1e-4)[..., None])
    shade_rim = A & ~C.ero(A0, 6) & (np.hypot(labs[..., 1], labs[..., 2]) < 24)
    A &= ~shade_rim
    op = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, lbl, stt, _ = cv2.connectedComponentsWithStats(op, 8)
    A = A & C.dil(np.isin(lbl, [i for i in range(1, n) if stt[i, 4] >= 2000]), 1)
    sliv = A0 & ~A
    # the left outline's 1-3 px breaks: closed (5 px), within 14 px of the row's leftmost pixel only (the bottom edge is a soft
    # stair the closing would turn into lines)
    Acl = cv2.morphologyEx(A.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
    lb14 = np.zeros((H, W), bool)
    for y in np.nonzero(A.any(1))[0]:
        lb14[y, :np.nonzero(A[y])[0].min() + 14] = True
    closed = Acl & ~A & lb14
    A = A | closed
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
    grey_pre = A & (np.hypot(C.to_lab(rgba[..., :3].astype(np.float64) / 255)[..., 1], C.to_lab(rgba[..., :3].astype(np.float64) / 255)[..., 2]) < 18)
    # the pockets the slivers left inside the new outline (alpha 0, the pillow showing through as light ticks): filled
    outl = (A | F).astype(np.uint8)
    ff = outl.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 2)
    holes = (ff == 0)
    # and, row by row, everything from the envelope to the first run of 3 solid cushion pixels (pockets open to the left)
    solid = A & (rgba[..., 3] >= 250) & ~grey_pre
    for i, y in enumerate(rows):
        x0 = int(np.ceil(env[i]))
        run = solid[y, x0:x0 + 40]
        r3 = np.nonzero(run[:-2] & run[1:-1] & run[2:])[0] if run.size > 2 else np.array([])
        if r3.size:
            holes[y, x0:x0 + r3[0]] = True
    closed = closed | holes
    fillm = F | grey | edge_px | closed
    # the inpaint draws from the cushion only: everything outside its alpha is unknown (in its bounding box, 24 px round)
    yy, xx = np.nonzero(A | fillm)
    by0, by1, bx0, bx1 = max(yy.min() - 24, 0), min(yy.max() + 25, H), max(xx.min() - 24, 0), min(xx.max() + 25, W)
    unknown = (fillm | ~A)[by0:by1, bx0:bx1]
    sub = cv2.inpaint(np.ascontiguousarray(rgba[by0:by1, bx0:bx1, :3]), unknown.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
    rgb = rgba[..., :3].copy()
    rgb[by0:by1, bx0:bx1] = sub
    rgba[..., :3] = np.where(fillm[..., None], rgb, rgba[..., :3])
    a = rgba[..., 3].astype(np.float64)
    a = np.where(F | grey | closed, 255, a)
    a = np.where(edge_px & ~A, np.maximum(a, frac * 255), a)
    # the bottom edge: under its soft rows the cut left 1 px opaque lines a step apart (a stair); down each column, over the last
    # 6 rows of the alpha, it may only fall (each row at most the one above)
    nb = 0
    for x in np.nonzero((a > 0).any(0))[0]:
        yy = np.nonzero(a[:, x] > 0)[0]
        for y in range(max(yy.max() - 5, yy.min() + 1), yy.max() + 1):
            if a[y, x] > a[y - 1, x]:
                a[y, x] = a[y - 1, x]
                nb += 1
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
    rec = dict(bottom_stair_px=nb, sliver_px_let_go=int(sliv.sum()), breaks_closed_px=int(closed.sum()), px_filled=int((F & ~A).sum()), grey_px_inpainted=int(grey.sum()), max_fill_px=int(np.max(lv - env)),
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
    go, so the plate's wall shows; from 10 to 3 px above that bottom only the dark shade (L* < 45)"""
    mv = man.get("code_fixes", {}).get("K-B3 nest", {}).get("moved_px")
    if not mv:
        return rgba
    st = K.ST[kid]
    lc = _layer(man, "cushions-pair")
    cu = np.asarray(Image.open(os.path.join(st, lc["layer"])))[..., 3] > 0
    old = cv2.warpAffine(cu.astype(np.uint8), np.float32([[1, 0, -mv], [0, 1, 0]]), (W, H), flags=cv2.INTER_NEAREST) > 0
    exposed = C.dil(old, 6) & ~cu
    bottom = np.where(old.any(0), H - 1 - np.argmax(old[::-1], 0), -1)      # the old pair's lowest row, per column
    yv = np.arange(H)[:, None]
    near = exposed & (yv >= (bottom - 10)[None, :]) & (yv < (bottom - 3)[None, :])   # just above it: only the dark shade (L* < 45)
    exposed &= yv < (bottom - 10)[None, :]                                  # above it: the wall; at it, the duvet's top edge
    A = rgba[..., 3] > 0
    lab = C.to_lab(C.blur(rgba[..., :3] * A[..., None], 1.5) / np.maximum(C.blur(A.astype(np.float64), 1.5), 1e-4)[..., None])
    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    ch = np.hypot(lab[..., 1], lab[..., 2])
    wall = A & exposed & (hue > 80) & (hue < 150) & (ch < 15) & (lab[..., 0] < 75)
    wall |= A & near & (hue > 80) & (hue < 150) & (ch < 15) & (lab[..., 0] < 45)
    wall = C.dil(wall, 1) & A & (exposed | near)
    out = rgba.copy()
    out[..., 3] = np.where(wall, 0, rgba[..., 3])
    edge = C.dil(wall, 1) & ~wall & A
    out[..., 3] = np.where(edge, np.minimum(out[..., 3], 0.5), out[..., 3])
    _bedding_exposed.px = int(wall.sum())
    return out


def restripe(kid, photo=(-10.5, 7.5)):
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
    e_seen = e.copy()                                                       # what the edit shows (the bear's bottom takes it)
    e = C.srgb(np.clip(C.lin(e) / np.maximum(shm, 0.2)[..., None], 0, 1))
    # the stripes' contrast brought to the photo's (QA: -10.5 ... +7.5; the same measure on the SKU photo: -10.1 ... +7.4): the
    # edit's fine structure (Lab minus its 12 px blur over the taken pixels) scaled by one gain
    w_ = take.astype(np.float64)
    lab_e = C.to_lab(e)
    low_e = np.stack([C.blur(lab_e[..., c] * w_, 12) / np.maximum(C.blur(w_, 12), 1e-4) for c in range(3)], -1)
    core = C.ero(take, 8)
    q5, q95 = np.percentile((lab_e[..., 0] - low_e[..., 0])[core], [5, 95])
    gain = min(1.0, (photo[1] - photo[0]) / max(q95 - q5, 1e-3))
    e = np.where(take[..., None], np.clip(C.from_lab(low_e + (lab_e - low_e) * gain), 0, 1), e)
    restripe.gain = gain
    # the bear's bottom (below 904, the legs' undersides, their contact shade and the duvet the bear's alpha still holds) takes the
    # edit too, the same contrast, so it meets the bedding without a seam; a ramp of 8 rows above
    lt = _layer(man, "soft-toy")
    tb = np.asarray(Image.open(os.path.join(st, lt["layer"]))).astype(np.float64) / 255
    lab_s = C.to_lab(e_seen)
    e_bear = np.clip(C.from_lab(low_e + (lab_s - low_e) * gain), 0, 1)
    wb = np.clip((np.arange(H)[:, None] - 904) / 8.0, 0, 1) * np.ones((1, W)) * S["box"] * (tb[..., 3] > 0) * (C.blur(w_, 12) > 0.05)
    tb_rgb = tb[..., :3] * (1 - wb[..., None]) + e_bear * wb[..., None]
    tout = np.dstack([C.q(tb_rgb), C.q(tb[..., 3])])
    tout[..., :3][tout[..., 3] == 0] = 0
    Image.fromarray(tout, "RGBA").save(os.path.join(st, lt["layer"]), optimize=True)
    restripe.bear_px = int((wb > 0).sum())
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
    rec = dict(contrast_gain=round(float(restripe.gain), 3), bear_bottom_px=restripe.bear_px, px_taken=int(take.sum()), wall_px_let_go=getattr(_bedding_exposed, "px", 0), stripes_L_p5_p95_before=[round(float(q5), 1), round(float(q95), 1)],
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


def islands(kid, keys=("pillowcase", "bedding"), max_px=2000):
    """K-L2 (and K-L1 in part): the pieces of a layer's alpha cut off from its body (the GB1 edit's grey smudges on the band under
    the sill, in the pillow layer, and their dark rims in the bedding layer): components under 2,000 px that are not the layer's
    largest let go; the layer's shadow under them (1.0: a product sat there) filled from the shade round them (a normalised blur)"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    rec = {}
    for key in keys:
        l = _layer(man, key)
        rgba = np.asarray(Image.open(os.path.join(st, l["layer"]))).copy()
        A = rgba[..., 3] > 0
        n, lbl, stt, _ = cv2.connectedComponentsWithStats(A.astype(np.uint8), 8)
        big = 1 + int(np.argmax(stt[1:, 4]))
        drop = np.isin(lbl, [i for i in range(1, n) if i != big and stt[i, 4] < max_px])
        if not drop.any():
            rec[key] = dict(px=0)
            continue
        rgba[..., 3][drop] = 0
        rgba[..., :3][drop] = 0
        Image.fromarray(rgba, "RGBA").save(os.path.join(st, l["layer"]), optimize=True)
        r = dict(px=int(drop.sum()), pieces=int(len(np.unique(lbl[drop]))))
        if l.get("shadow"):
            sh = np.asarray(Image.open(os.path.join(st, l["shadow"]))).astype(np.float64) / 255
            hole = C.dil(drop, 2)
            known = ~hole & C.dil(hole, 12)
            fillv = C.blur((1 - sh) * known, 5) / np.maximum(C.blur(known.astype(np.float64), 5), 1e-4)
            sh2 = np.where(hole, 1 - fillv, sh)
            sh2 = np.where(sh2 > 0.995, 1.0, sh2)
            Image.fromarray(C.q(sh2)).save(os.path.join(st, l["shadow"]), optimize=True)
            r["shadow_px_filled"] = int((hole & (sh2 < 1)).sum())
        rec[key] = r
    man.setdefault("code_fixes", {})["K-L2 islands"] = dict(rec, method=islands.__doc__.strip())
    KC.save_man(kid, man)
    print(json.dumps(rec))


def _alpha_union(kid, man):
    st = K.ST[kid]
    u = np.zeros((H, W))
    for l in man["layers"]:
        if l.get("default", True):
            u = np.maximum(u, np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] / 255)
    return u


def metrics(kid):
    """the QA findings measured on the rebuilt frames (and on the QA commit's frame, kept in the scratchpad, where it says before);
    merged into checks.json under K_fixes_2026_11_24"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    cf = man.get("code_fixes", {})
    ids = K.ids(f"K-{kid}")
    fr = K.frame_mask()
    out = {}
    now = C.load(os.path.join(st, f"K-{kid}-defaults.png"))
    was = C.load(os.path.join(K.SCR, f"before-K-{kid}-defaults.png"))
    U = _alpha_union(kid, man)
    def lab_h_c(rgb):
        lab = C.to_lab(rgb)
        return lab, np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360, np.hypot(lab[..., 1], lab[..., 2])
    if kid == "girl":
        band = np.isin(ids, (5, 8)) & fr
        below = np.isin(ids, (5, 8, 12, 19)) & fr & (U == 0)
        up_l = C.ero(np.isin(ids, (1, 2)), 4) & fr & (U == 0)
        r = {}
        for nm, im in (("before", was), ("after", now)):
            lab, hh, cc = lab_h_c(im)
            r8 = np.rint(im * 255)
            r[nm] = dict(band_px_all_three_over_245=int((band & (U == 0) & (r8 > 245).all(-1)).sum()),
                         band_L_p99=round(float(np.percentile(lab[..., 0][band & (U == 0)], 99)), 1),
                         plaster_L_p99=round(float(np.percentile(lab[..., 0][up_l], 99)), 1),
                         band_px_h70_110_C3_incl_product_edges=int((band & (U < 0.5) & (hh > 70) & (hh < 110) & (cc > 3)).sum()),
                         below_line_px_h95_135_C6_outside_products=int((below & (hh > 95) & (hh < 135) & (cc > 6)).sum()))
        out["K-G1_K-G2"] = r
        pc = cf.get("from the boy", {}).get("pen-cup", {})
        out["K-G3"] = dict(lit_half_Lab=pc.get("lit_half_Lab"), photo_Lab=pc.get("photo_Lab"), dE00=pc.get("dE00_lit_half"), before_dE00=8.3)
        sv = cf.get("sample slot variants", {})
        out["K-G4"] = dict({v: dict(lit_half_Lab=d["lit_half_Lab"], target=d["target_lit_half"], dE00_vs_photo=d["dE00_lit_half_vs_photo"])
                            for v, d in sv.get("variants", {}).items()}, deep_chestnut_lit_L=sv.get("variants", {}).get("V2", {}).get("lit_half_Lab", [None])[0],
                           boy_equivalent_lit_L=sv.get("girl_chestnut_lit_L"), before_dE00=[19.0, 19.9, 18.6])
        pl = C.load(os.path.join(st, "plate.png"))
        box = np.zeros((H, W), bool)
        box[815:870, 520:660] = True
        out["K-L2"] = {nm: int((box & (np.abs(C.to_lab(im)[..., 0] - C.to_lab(pl)[..., 0]) > 4) & ~np.isin(ids, (12,))).sum())
                       for nm, im in (("before_px_off_plate_4L", was), ("after_px_off_plate_4L", now))}
        out["K-L2"]["islands"] = {k: v for k, v in cf.get("K-L2 islands", {}).items() if k != "method"}
        # the recheck (QA after c4b811c0)
        rc = {}
        lpc = _layer(man, "pen-cup")
        ca = np.asarray(Image.open(os.path.join(st, lpc["layer"])))[..., 3]
        ids_ = K.ids("K-girl")
        Yv, Xv = np.arange(H)[:, None], np.arange(W)[None, :]
        body = (ca >= 250) & C.dil(np.isin(ids_, (48, 49)), 3) & (Yv > 822) & (Yv < 898)
        labn = C.to_lab(now)
        Ln = labn[..., 0]
        hp = Ln - C.blur(Ln * body, 3) / np.maximum(C.blur(body.astype(np.float64), 3), 1e-4)
        xs_ = np.nonzero(body.any(0))[0]
        th = np.array_split(np.arange(xs_.min(), xs_.max() + 1), 3)
        d_ = cv2.distanceTransform((ca == 0).astype(np.uint8), cv2.DIST_L2, 5)
        roi = (Yv > 830) & (Yv < 900) & (Xv < 2330) & (Xv > 2260)
        rc["K-G3"] = dict(cup=cf.get("from the boy", {}).get("pen-cup", {}).get("lit_half_Lab"), dE00=cf.get("from the boy", {}).get("pen-cup", {}).get("dE00_lit_half"),
                          grain_std_L_minus_blur3=round(float(np.std(hp[C.ero(body, 2)])), 2), photo_grain=3.28,
                          thirds_L=[round(float(np.median(Ln[body & np.isin(Xv, t3)])), 1) for t3 in th],
                          wall_left_L_at_0_4_4_8_8_14_px=[round(float(np.median(Ln[roi & (d_ > lo) & (d_ <= hi)])), 1) for lo, hi in ((0.5, 4), (4, 8), (8, 14))])
        g4 = {}
        for vn, fn in (("V1", "defaults"), ("V2", "V2"), ("V3", "V3")):
            im = C.load(os.path.join(st, f"K-{kid}-{fn}.png"))
            Lv = C.to_lab(im)[..., 0]
            was_ = C.to_lab(C.load(os.path.join(K.SCR, f"c4b-K-{kid}-{fn}.png")))[..., 0]
            lb_ = _layer(man, "bedspread")
            ta = np.asarray(Image.open(os.path.join(st, lb_["layer"])))[..., 3] >= 250
            patch = ta & (Yv >= 945) & (Yv <= 985) & (Xv >= 1262) & (Xv <= 1325)
            nb = ta & (Yv >= 945) & (Yv <= 985) & (Xv >= 1195) & (Xv <= 1255)
            seam = lambda LL: float(np.median(np.abs(LL[945:985, 1261] - LL[945:985, 1258])))   # noqa: E731
            g4[vn] = dict(patch_minus_neighbour_L_before=round(float(np.median(was_[patch]) - np.median(was_[nb])), 1),
                          after=round(float(np.median(Lv[patch]) - np.median(Lv[nb])), 1),
                          seam_step_L_x1258_1261_before_after=[round(seam(was_), 1), round(seam(Lv), 1)])
        g4["dE00_vs_photo"] = {v: d["dE00_lit_half_vs_photo"] for v, d in cf.get("sample slot variants", {}).get("variants", {}).items()}
        rc["K-G4"] = g4
        rc["K-L7"] = {k: v for k, v in cf.get("K-L7 edges", {}).items() if k != "method"}
        rc["K-L1_window"] = {k: v for k, v in cf.get("K-L1 window px", {}).items() if k != "method"}
        out["recheck"] = rc
    else:
        out["K-B1"] = {k: v for k, v in cf.get("K-B1 cars", {}).items() if k != "method"}
        out["K-B2"] = {k: v for k, v in cf.get("K-B2 stripes", {}).items() if k != "method"}
        lp, lc = _layer(man, "pillowcase"), _layer(man, "cushions-pair")
        P = np.asarray(Image.open(os.path.join(st, lp["layer"])))[..., 3] > 128
        Cm = np.asarray(Image.open(os.path.join(st, lc["layer"])))[..., 3] > 128
        ov = []
        for y in range(720, 801):                                    # QA's rows (y 720-800)
            c = np.nonzero(Cm[y])[0]
            if not c.size:
                continue
            p_ = np.nonzero(P[y, max(0, c.min() - 150):c.min() + 200])[0]
            if p_.size:
                ov.append(int(max(0, c.min() - 150) + p_.max() - c.min()))
        lab, hh, cc = lab_h_c(now)
        strip = np.zeros((H, W), bool)
        strip[728:800, 780:870] = True                               # the old strip, below the pillows' top
        out["K-B3"] = dict(overlap_px_min_p50=[int(min(ov)), int(np.median(ov))] if ov else None, need_px=int(round(0.02 * K.FW)),
                           plate_visible_px_in_old_strip=int((strip & (U == 0)).sum()),
                           nest={k: v for k, v in cf.get("K-B3 nest", {}).items() if k != "why"},
                           edge={k: v for k, v in cf.get("K-B3 nest edge", {}).items() if k != "method"})
        t = np.asarray(Image.open(os.path.join(st, _layer(man, "soft-toy")["layer"]))).astype(np.float64) / 255
        t0 = np.asarray(Image.open(os.path.join(K.SCR, "boy-soft-toy-cut.png"))).astype(np.float64) / 255
        def wall_in(tt):
            l_, h_, c_ = lab_h_c(tt[..., :3])
            return int(((tt[..., 3] > 0) & (l_[..., 0] < 45) & (h_ > 80) & (h_ < 150) & (c_ < 15)).sum())
        out["K-L1_bear"] = dict(dark_wall_px_in_alpha_cut_after=[wall_in(t0), wall_in(t)],
                                **{k: v for k, v in cf.get("K-L1 bear alpha", {}).items() if k not in ("method", "why")})
    path = os.path.join(st, "checks.json")
    ch = json.load(open(path))
    ch["K_fixes_2026_11_24"] = out
    json.dump(ch, open(path, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out)[:2500])


def girl_edges(kid="girl"):
    """K-L7 (QA recheck 2026-11-24): the right cushion's right edge (cut too deep by the GB2 wall trim, a notch at its top and a grey
    wedge at its foot) and the duvet's back edge under the pair (jagged on the band). The cushion's edge is taken from the GB2 edit itself:
    - the cushion: per row (715-897), the rightmost pixel of the edit's corduroy (C* > 14, L* < 70 on a 1 px blur, its ribs' local
      std over 1.5: its shade on the wall is smooth, C* 8-12) joined to the layer, a median of 7
      rows and a Gaussian of 2; the layer filled to that edge with the edit's corduroy (pockets inpainted from the cushion) and cut beyond it (the wedge
      goes), 1 px soft;
    - the duvet: per column (1010-1175), its own top edge, a median of 9 columns and a Gaussian of 2.5: notches filled (inpainted
      from the duvet), spikes cut, 1 px soft (the GB2 edit's duvet up to the cushions is lighter than GB1's: not used)"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    S = KC.edit_canvas("GB2-nest")
    e = S["e"]
    lab = C.to_lab(e)
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    cc = np.hypot(lab[..., 1], lab[..., 2])
    rec = {}
    # the cushion's right edge
    lc = _layer(man, "cushions-pair")
    src = os.path.join(K.SCR, f"{kid}-cushions-pre-L7.png")            # the layer before this step (kept once): re-runnable
    if not os.path.exists(src):
        Image.open(os.path.join(st, lc["layer"])).save(src)
    cu = np.asarray(Image.open(src)).astype(np.float64) / 255
    A = cu[..., 3] > 0
    Lh = lab[..., 0] - C.blur(lab[..., 0], 2)
    sd = np.sqrt(C.blur(Lh ** 2, 2))
    lb1 = C.to_lab(C.blur(e, 1.0))
    like = (np.hypot(lb1[..., 1], lb1[..., 2]) > 14) & (lb1[..., 0] < 70) & (sd > 1.5) & S["box"]     # the corduroy, not its shade
    like = cv2.morphologyEx(like.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    n, lbl, stt, _ = cv2.connectedComponentsWithStats((like | A).astype(np.uint8), 8)
    body = lbl == lbl[np.nonzero(C.ero(A, 6))][0] if C.ero(A, 6).any() else A
    body &= like | A
    rows = np.arange(715, 898)
    r = np.array([np.nonzero(body[y, 1040:1130] & like[y, 1040:1130])[0].max() + 1040 if (body[y, 1040:1130] & like[y, 1040:1130]).any() else np.nan for y in rows])
    ok = ~np.isnan(r)
    r = np.interp(rows, rows[ok], r[ok])
    rm = np.array([np.median(r[max(0, i - 3):i + 4]) for i in range(len(r))], np.float32)
    env = cv2.GaussianBlur(rm[:, None], (1, 0), sigmaX=0.1, sigmaY=2, borderType=cv2.BORDER_REPLICATE)[:, 0].astype(np.float64)
    xs = np.arange(W)[None, :]
    newA = A.copy()
    cov = np.zeros((H, W))
    band = np.zeros((H, W), bool)
    for i, y in enumerate(rows):
        lft = int(np.nonzero(A[y])[0].min()) if A[y].any() else 1040
        band[y, max(lft, 1040):1135] = True
        cov[y] = np.clip(env[i] + 0.5 - xs[0], 0, 1)
    fill = band & (cov > 0) & ~A & C.dil(like, 1)
    for i, y in enumerate(rows):                                  # pockets open to the right: from the edge in to the first solid run
        xe = int(np.floor(env[i]))
        seg = A[y, xe - 30:xe + 1][::-1]
        if seg.size > 3:
            r3 = np.nonzero(seg[:-2] & seg[1:-1] & seg[2:])[0]
            if r3.size and r3[0] > 0:
                fill[y, xe - r3[0] + 1:xe + 1] |= cov[y, xe - r3[0] + 1:xe + 1] > 0
    cut = band & (cov < 1) & A
    a_new = np.where(band, np.minimum(np.where(A | fill, np.where(A, cu[..., 3], 1.0), 0.0), cov), cu[..., 3])
    a_new = np.where(fill, np.maximum(a_new, np.minimum(cov, 1.0)), a_new)
    rgb = np.where((fill & like)[..., None], e, cu[..., :3])
    pocket = fill & ~like
    if pocket.any():
        yy_, xx_ = np.nonzero(fill | A)
        y0_, y1_, x0_, x1_ = yy_.min() - 4, yy_.max() + 5, xx_.min() - 4, xx_.max() + 5
        unk = (pocket | ~A)[y0_:y1_, x0_:x1_]
        sub = cv2.inpaint(C.q(rgb[y0_:y1_, x0_:x1_]), unk.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA).astype(np.float64) / 255
        rgb[y0_:y1_, x0_:x1_] = np.where(pocket[y0_:y1_, x0_:x1_, None], sub, rgb[y0_:y1_, x0_:x1_])
    inner = KC.KC.spread(cu[..., :3], (C.ero(A, 3) & band).astype(np.float64), (2.0, 4.0))
    lab_c = C.to_lab(cu[..., :3])
    edge = band & A & ~C.ero(A, 2) & (np.linalg.norm(lab_c - C.to_lab(inner), axis=-1) > 6)
    rgb = np.where(edge[..., None], inner, rgb)
    out = np.dstack([C.q(rgb), C.q(a_new)])
    out[..., :3][out[..., 3] == 0] = 0
    Image.fromarray(out, "RGBA").save(os.path.join(st, lc["layer"]), optimize=True)
    # its shadow was 1 under its old alpha: where the edge was cut back the band showed unshaded (a light line): filled from outside
    shp = os.path.join(st, lc["shadow"])
    sh = np.asarray(Image.open(shp)).astype(np.float64) / 255
    hole = C.dil(A & (a_new < 0.98) & band, 1)
    known = ~C.dil(A, 1) & C.dil(hole, 12)
    fv = C.blur((1 - sh) * known, 3) / np.maximum(C.blur(known.astype(np.float64), 3), 1e-4)
    sh2 = np.where(hole, np.minimum(sh, 1 - fv), sh)
    Image.fromarray(C.q(np.where(sh2 > 0.995, 1.0, sh2))).save(shp, optimize=True)
    rec["cushion_shadow_filled_px"] = int((hole & (sh2 < sh - 0.005)).sum())
    rec["cushion_right_edge"] = dict(rows=[715, 897], px_filled=int(fill.sum()), px_cut=int((cut & (a_new == 0)).sum()), edge_px_decontaminated=int(edge.sum()),
                                     edge_x_min_max=[round(float(env.min()), 1), round(float(env.max()), 1)])
    # the duvet's back edge under the pair
    cuA = out[..., 3] > 0
    lb = _layer(man, "bedding")
    srcb = os.path.join(K.SCR, f"{kid}-bedding-pre-L7.png")
    if not os.path.exists(srcb):
        Image.open(os.path.join(st, lb["layer"])).save(srcb)
    bd = np.asarray(Image.open(srcb)).astype(np.float64) / 255
    B = bd[..., 3] > 0
    cols = np.arange(1010, 1176)
    tops = np.array([np.nonzero(B[:, x])[0].min() if B[:, x].any() else np.nan for x in cols], np.float64)
    ok = ~np.isnan(tops)
    tops = np.interp(cols, cols[ok], tops[ok])
    tm = np.array([np.median(tops[max(0, i - 4):i + 5]) for i in range(len(tops))], np.float32)
    tenv = cv2.GaussianBlur(tm[None, :], (0, 1), sigmaX=2.5, sigmaY=0.1, borderType=cv2.BORDER_REPLICATE)[0].astype(np.float64)
    ys = np.arange(H)
    ab = bd[..., 3].copy()
    fillb = np.zeros((H, W), bool)
    for i, x in enumerate(cols):
        cv_ = np.clip(ys - tenv[i] + 0.5, 0, 1)
        zone = (ys >= tenv[i] - 3) & (ys <= tenv[i] + 12)
        fillb[:, x] = zone & (cv_ > 0) & ~B[:, x]
        ab[:, x] = np.where(zone, np.where(B[:, x] | fillb[:, x], cv_, 0.0) * np.where(B[:, x], np.maximum(bd[:, x, 3], cv_), 1.0), ab[:, x])
    rgbb = bd[..., :3].copy()
    if fillb.any():
        yy_, xx_ = np.nonzero(fillb)
        y0_, y1_, x0_, x1_ = yy_.min() - 6, yy_.max() + 7, xx_.min() - 6, xx_.max() + 7
        unk = (fillb | ~B)[y0_:y1_, x0_:x1_]
        sub = cv2.inpaint(C.q(rgbb[y0_:y1_, x0_:x1_]), unk.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA).astype(np.float64) / 255
        rgbb[y0_:y1_, x0_:x1_] = np.where(fillb[y0_:y1_, x0_:x1_, None], sub, rgbb[y0_:y1_, x0_:x1_])
    outb = np.dstack([C.q(rgbb), C.q(ab)])
    outb[..., :3][outb[..., 3] == 0] = 0
    Image.fromarray(outb, "RGBA").save(os.path.join(st, lb["layer"]), optimize=True)
    rec["duvet_back_edge"] = dict(cols=[1010, 1175], px_filled=int(fillb.sum()), px_cut=int((B & (outb[..., 3] == 0)).sum()))
    man.setdefault("code_fixes", {})["K-L7 edges"] = dict(rec, method=girl_edges.__doc__.strip())
    KC.save_man(kid, man)
    print(json.dumps(rec))


def window_px(kid="girl", key="pillowcase", win_ids=(0, 12, 13, 14, 20), thr=8.0):
    """K-L1 (QA recheck): the girl's pillowcase layer carried the window (the GB1 edit's copy of it, 1,390 px by QA): over the window's
    clay ids, the layer's pixels within dE76 8 of the plate let go (alpha 0). They are the plate's own colour, so the frame does not
    change; the layer holds only the pillows"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    l = _layer(man, key)
    rgba = np.asarray(Image.open(os.path.join(st, l["layer"]))).copy()
    ids = K.ids(f"K-{kid}")
    pl = C.load(os.path.join(st, "plate.png"))
    d = np.linalg.norm(C.to_lab(rgba[..., :3].astype(np.float64) / 255) - C.to_lab(pl), axis=-1)
    A = rgba[..., 3] > 0
    drop = A & np.isin(ids, win_ids) & (d < thr)
    rgba[..., 3][drop] = 0
    rgba[..., :3][drop] = 0
    Image.fromarray(rgba, "RGBA").save(os.path.join(st, l["layer"]), optimize=True)
    ys, xs = np.nonzero(rgba[..., 3])
    rec = dict(px=int(drop.sum()), left_on_window_ids=int((np.isin(ids, win_ids) & (rgba[..., 3] > 0)).sum()), layer_x=[int(xs.min()), int(xs.max())],
               method=window_px.__doc__.strip())
    for e in man["layers"]:
        if e["key"] == key and e.get("default", True):
            e["bbox_px"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            e["alpha_px"] = int(xs.size)
    man.setdefault("code_fixes", {})["K-L1 window px"] = rec
    KC.save_man(kid, man)
    print(json.dumps({k: v for k, v in rec.items() if k != "method"}))


FIX_CROPS = [   # finding, room, frame (before: the QA commit 1b062a0e, kept in the scratchpad), canvas box (240 x 150), what to look at
    ("K-G1", "girl", "defaults", (1080, 560, 1320, 710), "band right of the pillows: the white halo"),
    ("K-G2", "girl", "defaults", (1680, 900, 1920, 1050), "desk and chair legs on the band: olive strips"),
    ("K-G2", "girl", "defaults", (1420, 880, 1660, 1030), "foot-board edge on the band: olive strip"),
    ("K-G3", "girl", "defaults", (2210, 740, 2450, 890), "pen cup: beech, not brass"),
    ("K-G4", "girl", "defaults", (1000, 960, 1240, 1110), "throw V1 Linen Brown (default): lit half at the photo"),
    ("K-L2", "girl", "defaults", (520, 760, 760, 910), "under the sill: grey smudges"),
    ("K-B1", "boy", "defaults", (1790, 800, 2030, 950), "cars: the SKU's beetle, the card's size"),
    ("K-B2", "boy", "defaults", (600, 960, 840, 1110), "duvet set: wide soft melange stripes, the photo's contrast"),
    ("K-B3", "boy", "defaults", (690, 700, 930, 850), "nest: no strip between pillow and pair; the bear's alpha"),
]


FIX_CROPS_2 = [  # the recheck (QA after c4b811c0): before is c4b811c0's frame
    ("K-G3", "girl", "defaults", (2230, 740, 2470, 920), "pen cup: grain, the shade of its side, no ring, clean pencils"),
    ("K-G4", "girl", "defaults", (1150, 910, 1390, 1060), "throw V1 at the foot board: the pale patch and its seam"),
    ("K-G4", "girl", "V2", (1150, 910, 1390, 1060), "throw V2 at the foot board"),
    ("K-G4", "girl", "V3", (1150, 910, 1390, 1060), "throw V3 at the foot board"),
    ("K-L7", "girl", "defaults", (960, 700, 1200, 950), "the right cushion's right edge, the duvet's back edge"),
]


def board(crops=None, before_fmt=None, out_path=None):
    """kids-fixes.jpg (the boy's folder): before and after at x2 per finding, side by side; before is the QA commit's frame.
    board2: kids-fixes-2.jpg (the girl's folder), the recheck's findings, before = c4b811c0"""
    from PIL import ImageDraw
    crops = crops or FIX_CROPS
    before_fmt = before_fmt or "before-K-{kid}-{fr}.png"
    rows = []
    for fid, kid, fr, box, what in crops:
        before = Image.open(os.path.join(K.SCR, before_fmt.format(kid=kid, fr=fr))).convert("RGB").crop(box)
        after = Image.open(os.path.join(K.ST[kid], f"K-{kid}-{fr}.png")).convert("RGB").crop(box)
        w, h = (box[2] - box[0]) * 2, (box[3] - box[1]) * 2
        row = Image.new("RGB", (2 * w + 12, h + 26), (250, 250, 248))
        row.paste(before.resize((w, h), Image.LANCZOS), (0, 26))
        row.paste(after.resize((w, h), Image.LANCZOS), (w + 12, 26))
        d = ImageDraw.Draw(row)
        d.text((6, 6), f"{fid} ({kid}, {fr}) before: {what}", fill=(30, 30, 30))
        d.text((w + 18, 6), f"{fid} after (x2, canvas {box[0]}-{box[2]} x {box[1]}-{box[3]})", fill=(30, 30, 30))
        rows.append(row)
    W_ = max(r.size[0] for r in rows)
    out = Image.new("RGB", (W_, sum(r.size[1] + 10 for r in rows)), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.size[1] + 10
    path = out_path or os.path.join(K.ST["boy"], "kids-fixes.jpg")
    out.save(path, quality=84, optimize=True)
    print(path, out.size, os.path.getsize(path))


def chain(kid):
    """the boy's nest and bed after a re-cut of PB2-nest or PB1b-stripes, in order: nest, cushion_edge, bear, restripe"""
    for f in (nest, cushion_edge, bear, restripe):
        f(kid)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "board":
        board()
        sys.exit()
    if a[0] == "board2":
        board(FIX_CROPS_2, "c4b-K-{kid}-{fr}.png", os.path.join(K.ST["girl"], "kids-fixes-2.jpg"))
        sys.exit()
    {"nest": nest, "stripes": stripes, "restripe": restripe, "cars": cars, "bear": bear, "cushion_edge": cushion_edge, "chain": chain, "islands": islands, "metrics": metrics, "girl_edges": girl_edges, "window_px": window_px}[a[0]](a[1])
