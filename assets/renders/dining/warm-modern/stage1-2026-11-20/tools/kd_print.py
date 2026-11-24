#!/usr/bin/env python3
"""
kd_print.py: print 05 into the frame's blank canvas, in code (render-agent, resumed session, 2026-11-20; 0 tokens). 10.7: the print of
framed-art-aliexpress-misty-landscape-386242-work, design 05 (landscape, 40 x 30), goes in from the listing's flat file, as in the
bedroom (master stage1 tools/fb10_compose.py set_print): the listing shows the print on white with a margin, so the non-white part is
taken; 10.9: the whole 5:4 print, contained by height (the sides become the float gap), lit by the canvas's own light in the edit (the edit's canvas over the colour it
was asked to be, #D8C8AE, 1.5 px blur), so the moulding's edge shadow and the LED's wash carry over.
The canvas is found in the D2 layer of the frame: the largest flat region of the asked colour inside the layer, its bounding box less
1 px. Run after kd_cut2.py (E-left) and before compose_edits.py project (D1 gets the print by the projection).
  python3 kd_print.py        (the supplier file is read from the scratchpad only; it never enters the repo)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

C = K.C
ST = K.ST
H, W = K.H, K.W
PRINT = os.path.join(K.PICKS, "img", "5aff04c0_Sffd2120da3974d409909687f874b51d0k.jpg")   # design 05, the bedroom's framed-art-2 file
CANVAS_ALBEDO = np.array([216, 200, 174]) / 255
PID = "framed-art-aliexpress-misty-landscape-386242-work-05-40x50"     # 10.9: the 40x50 SKU (was -05-30x40)
SELLER_CROP = 5 / 4     # 10.9 row 3: the 50 x 40 landscape print is the seller's central crop of the 4:3 design (about 3% off each side)


def main():
    man = json.load(open(os.path.join(ST, "manifest.json")))
    l = [x for x in man["layers"] if x["frame"] == "D2" and x["product"] == PID and not x.get("projected_from")][0]
    lp = os.path.join(ST, l["layer"])
    rgba = np.asarray(Image.open(lp)).copy()
    a = rgba[..., 3] > 250
    rgb = rgba[..., :3].astype(np.float64) / 255
    lab = C.to_lab(rgb)
    med = np.median(lab[C.ero(a, 6)], 0)
    flat = a & (np.linalg.norm(lab - med, axis=-1) < 9)
    flat = cv2.morphologyEx(flat.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(flat.astype(np.uint8), connectivity=4)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.nonzero(lb == i)
    x0, y0, x1, y1 = xs.min() + 1, ys.min() + 1, xs.max(), ys.max()
    pr = C.load(PRINT)
    nonw = pr.min(2) < 0.86
    py, px = np.nonzero(nonw)
    pr = pr[py.min() + 4:py.max() - 3, px.min() + 4:px.max() - 3]
    side = int(round((pr.shape[1] - SELLER_CROP * pr.shape[0]) / 2))     # 4:3 -> 5:4, centred
    if side > 0:
        pr = pr[:, side:pr.shape[1] - side]
    cw, ch = x1 - x0, y1 - y0
    # 10.9, the manager (2026-11-24): the whole 5:4 print, no height lost. The edit's canvas is a slightly slanted quad (the frame leans)
    # and wider than 5:4 (a float gap of 1-2 px): its four edges are fitted as lines; the print goes into the same quad, contained by
    # height, at the clay's own 50 x 40 canvas aspect where it projects (id 68), centred; between the moulding's inner edge and the
    # print the float gap of KD-17 (7 cm at the sides, 4.5 at top and bottom), from the edit's own gap profile (the median over rows,
    # moulding -> dark inner side -> canvas edge) stretched over the wider gap
    L = lab[..., 0]
    rows = np.arange(y0 + 3, y1 - 3)

    def fit(ys_, xs_):
        A_ = np.vstack([ys_, np.ones_like(ys_)]).T
        c_ = np.linalg.lstsq(A_, xs_, rcond=None)[0]
        r_ = np.abs(A_ @ c_ - xs_)
        k_ = r_ <= max(1.0, np.percentile(r_, 80))
        return np.linalg.lstsq(A_[k_], xs_[k_], rcond=None)[0]

    def edge_rows(side):
        cl, ml = [], []
        for y in rows:
            xs_c = np.nonzero(L[y, x0 - 12:x1 + 12] >= 70)[0] + x0 - 12
            if xs_c.size < 20:
                continue
            xe = xs_c.min() if side < 0 else xs_c.max()
            x = xe + side
            while abs(x - xe) < 16 and L[y, x] < 50 and rgba[y, x, 3] > 200:
                x += side
            cl.append((y, xe))
            ml.append((y, x - side))
        return np.array(cl, float), np.array(ml, float)

    cL, mL = edge_rows(-1)
    cR, mR = edge_rows(+1)
    fcL, fmL, fcR, fmR = fit(cL[:, 0], cL[:, 1]), fit(mL[:, 0], mL[:, 1]), fit(cR[:, 0], cR[:, 1]), fit(mR[:, 0], mR[:, 1])
    at = lambda f, y: f[0] * y + f[1]
    # the gap profile: per row, the edit's pixels from the moulding's inner edge to the canvas edge, resampled to 16, median
    prof = {}
    for nm, cc, mm in (("L", cL, mL), ("R", cR, mR)):
        ps = []
        for (y, xc_), (_, xm_) in zip(cc, mm):
            y, a_, b_ = int(y), int(min(xc_, xm_)), int(max(xc_, xm_))
            if b_ - a_ < 2:
                continue
            seg = C.lin(rgb[y, a_:b_ + 1])
            if nm == "R":
                seg = seg[::-1]                       # always moulding -> canvas
            if nm == "L":
                seg = seg                             # a_ is the moulding side on the left
            t = np.linspace(0, len(seg) - 1, 16)
            ps.append(np.stack([np.interp(t, np.arange(len(seg)), seg[:, c]) for c in range(3)], -1))
        prof[nm] = np.median(np.array(ps), 0)
    yc, xc = np.nonzero(K.ids("D2") == 68)
    persp = ((xc.max() - xc.min() + 1) / (yc.max() - yc.min() + 1)) / SELLER_CROP
    ym = (y0 + y1) / 2
    width_mid = at(fcR, ym) - at(fcL, ym)
    tw = ch * SELLER_CROP * persp
    band = (width_mid - tw) / 2
    src = np.float32([[0, 0], [pr.shape[1], 0], [pr.shape[1], pr.shape[0]], [0, pr.shape[0]]])
    dst = np.float32([[at(fcL, y0) + band, y0], [at(fcR, y0) - band, y0], [at(fcR, y1) - band, y1], [at(fcL, y1) + band, y1]])
    Mp = cv2.getPerspectiveTransform(src, dst)
    pl_ = cv2.warpPerspective(C.lin(pr).astype(np.float32), Mp, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
    cover = cv2.warpPerspective(np.ones(pr.shape[:2], np.float32), Mp, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
    rgb_g = C.lin(rgb).copy()
    gaps = []
    for y in range(y0, y1):
        for nm, fm_, fc_, sgn in (("L", fmL, fcL, +1), ("R", fmR, fcR, -1)):
            xm_ = at(fm_, y)
            xp_ = at(fc_, y) + sgn * band                    # the print's edge on this row
            a_, b_ = (xm_, xp_) if sgn > 0 else (xp_, xm_)
            xa_, xb_ = int(np.floor(a_)), int(np.ceil(b_))
            if xb_ - xa_ < 2:
                continue
            xs_ = np.arange(xa_, xb_ + 1)
            t = np.clip((xs_ - xm_) / (xp_ - xm_), 0, 1) * 15
            col = np.stack([np.interp(t, np.arange(16), prof[nm][:, c]) for c in range(3)], -1)
            rgb_g[y, xs_] = col
            gaps.append(xb_ - xa_)
    rgb = C.srgb(np.clip(rgb_g, 0, 1))
    light = C.blur(C.lin(rgba[..., :3].astype(np.float64) / 255), 1.5) / C.lin(CANVAS_ALBEDO)[None, None, :]
    box = cover > 0.5
    xa, xb = int(round(at(fcL, ym) + band)), int(round(at(fcR, ym) - band))
    kx, ky = tw / pr.shape[1], ch / pr.shape[0]
    k, sw, sh = ky, tw, ch
    lit = C.srgb(np.clip(pl_ * light, 0, 1))
    cv_ = np.clip(cover, 0, 1)[..., None]
    rgb2 = lit * cv_ + rgb * (1 - cv_)
    rgba[..., :3] = C.q(rgb2)
    Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
    rp = os.path.join(ST, "compose.json")
    rec = json.load(open(rp))
    li = C.luma(light[box])
    rec["print-05"] = dict(file=os.path.basename(PRINT).split("_")[0] + " (listing file, scratchpad only)", file_px=list(pr.shape[1::-1]),
                           seller_crop="5:4, %d px off each side of the 4:3 design (10.9 row 3)" % side,
                           canvas_box_px=[int(x0), int(y0), int(x1), int(y1)], canvas_px=[int(cw), int(ch)],
                           print_box_px=[int(xa), int(y0), int(xb), int(y1)], print_px=[int(tw), int(ch)], scale_xy=[round(float(kx), 4), round(float(ky), 4)],
                           projection_stretch=round(float(persp), 4), cropped_px=[0, 0], side_gap_px=[int(min(gaps)), int(max(gaps))] if gaps else None,
                           canvas_light_p5_p50_p95=[round(float(v), 3) for v in np.percentile(li, [5, 50, 95])],
                           rule="10.7 / 10.9: print 05 (the 40x50 SKU: the 4:3 design's central 5:4 crop), whole (the manager, 2026-11-24: no height lost), "
                                "contained by height in the edit's canvas at the clay canvas's projected aspect; the sides are the float gap (the edit's "
                                "gap profile stretched); lit by the edit's canvas light; D1 gets it by the projection")
    l["print"] = "05, in code (tools/kd_print.py)"
    json.dump(rec, open(rp, "w"), indent=1, default=str)
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    print(json.dumps(rec["print-05"]))


if __name__ == "__main__":
    main()
