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


def restripe(kid):
    """K-B2 by the PB1b edit: the bedding layer keeps its alpha (the geometry QA passed) and takes the edit's pixels, matched to its base
    by the gain field (kids_cut.edit_canvas), wherever it is solid (alpha 250+) and no product above it shows (the throw, the pillows,
    the basket, the cushions, the toy: alpha 0 there); under them and at its own soft edge it keeps its earlier colours"""
    st = K.ST[kid]
    man = KC.load_man(kid)
    lb = _layer(man, "bedding")
    S = KC.edit_canvas("PB1b-stripes")
    e = S["e"]
    src = os.path.join(K.SCR, f"{kid}-bedding-cut.png")
    rgba = np.asarray(Image.open(src if os.path.exists(src) else os.path.join(st, lb["layer"]))).astype(np.float64) / 255
    upper = np.zeros((H, W))
    for l in man["layers"]:
        if l.get("default", True) and l["z"] > lb["z"]:
            upper = np.maximum(upper, np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] / 255)
    take = (rgba[..., 3] >= 250 / 255) & (upper == 0) & S["box"]
    take = C.ero(take, 1)
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
    rec = dict(px_taken=int(take.sum()), stripes_L_p5_p95_before=[round(float(q5), 1), round(float(q95), 1)],
               after=[round(float(r5), 1), round(float(r95), 1)], photo=[-10.5, 7.5], method=restripe.__doc__.strip(),
               why="K-B2: the set's stripes are wide and soft (melange jersey); the code attempt (a blur across, then the photo's contrast) "
                   "read out of focus at x2, so one edit (400) redrew the pattern only")
    man.setdefault("code_fixes", {})["K-B2 stripes"] = rec
    KC.save_man(kid, man)
    print(json.dumps(rec))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"nest": nest, "stripes": stripes, "restripe": restripe}[a[0]](a[1])
