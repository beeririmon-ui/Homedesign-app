#!/usr/bin/env python3
"""prep.py: FB13 stage A, from the returned frames to the two graded truths (scratch -> out/prep/).
  1. the three nano edits (crops of the hero) registered to their input crops (SIFT + RANSAC affine), tone-matched on the pixels the
     edit left alone, and E1 (the table's rolled ends) and E3 (the rug's right end) pasted into the hero inside their own regions;
     E2 (the hero without the table group) kept beside it, for what lies under the table;
  2. the plate registered to the hero (SIFT on the room's own structure, outside every product);
  3. the hero's tone matched to the plate's on the surfaces no product and no lamp touches (one monotone curve per channel);
  4. the three prints set into the blank canvases in code (prints.py);
  5. the ONE display grade (hwlib.GRADE) on the plate, the hero and the no-table frame alike.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

import hwlib as L
import prints

SP = L.SP
RAW = os.path.join(SP, "raw")
OUTP = os.path.join(L.OUT, "prep")
os.makedirs(OUTP, exist_ok=True)
H_, W_ = L.H, L.W
CROPS = json.load(open(os.path.join(SP, "edits", "crops.json")))
LOG = {}


def sift_affine(src, dst, mask_src=None, mask_dst=None, full=True, nfeat=12000):
    """the affine that maps src pixels onto dst pixels (both float RGB 0-1)"""
    g = lambda im: cv2.cvtColor((np.clip(im, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create(nfeatures=nfeat, contrastThreshold=0.02)
    k1, d1 = sift.detectAndCompute(g(src), None if mask_src is None else (mask_src * 255).astype(np.uint8))
    k2, d2 = sift.detectAndCompute(g(dst), None if mask_dst is None else (mask_dst * 255).astype(np.uint8))
    m = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [a for a, b in m if a.distance < 0.72 * b.distance]
    p1 = np.float32([k1[a.queryIdx].pt for a in good])
    p2 = np.float32([k2[a.trainIdx].pt for a in good])
    fn = cv2.estimateAffine2D if full else cv2.estimateAffinePartial2D
    A, inl = fn(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=5000, confidence=0.999)
    inl = inl.ravel().astype(bool)
    res = np.linalg.norm((p1[inl] @ A[:, :2].T + A[:, 2]) - p2[inl], axis=1)
    return A, dict(matches=len(good), inliers=int(inl.sum()), residual_px_median=round(float(np.median(res)), 3),
                   residual_px_p90=round(float(np.percentile(res, 90)), 3), A=[[round(float(v), 6) for v in r] for r in A])


def tone_fit(src, ref, mask, iters=3):
    """per channel gain and offset (sRGB values) that bring src to ref on mask; the pixels the edit changed are dropped by iteration"""
    out = src.copy()
    rec = []
    m = mask.copy()
    for c in range(3):
        mm = m.copy()
        a, b = 1.0, 0.0
        for _ in range(iters):
            x, y = src[..., c][mm], ref[..., c][mm]
            if len(x) < 1000:
                break
            a, b = np.polyfit(x, y, 1)
            r = np.abs(a * src[..., c] + b - ref[..., c])
            mm = m & (r < max(2.5 * float(np.median(r[mm])), 0.01))
        out[..., c] = a * src[..., c] + b
        rec.append([round(float(a), 4), round(float(b), 4)])
    return np.clip(out, 0, 1), rec


def place_edit(name, raw_file, H0):
    x0, y0, x1, y1 = CROPS["table" if name != "e3" else "rugend"]
    cw, ch = x1 - x0, y1 - y0
    inp = H0[y0:y1, x0:x1]
    res = L.rd(os.path.join(RAW, raw_file))
    inp2 = cv2.resize(inp, (cw * 2, ch * 2), interpolation=cv2.INTER_LANCZOS4)
    A, rec = sift_affine(res, inp2)
    w2 = cv2.warpAffine(res, A, (cw * 2, ch * 2), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.resize(w2, (cw, ch), interpolation=cv2.INTER_AREA)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    same = d < 0.05
    w1, tone = tone_fit(w1, inp, same)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    rec.update(tone_gain_offset=tone, unchanged_share=round(float((d < 0.04).mean()), 3), returned_px=list(res.shape[1::-1]),
               mean_abs_diff_unchanged=round(float(np.abs(w1 - inp)[d < 0.04].mean() * 255), 2))
    LOG[name] = rec
    full = np.zeros_like(H0)
    full[y0:y1, x0:x1] = w1
    dfull = np.zeros((H_, W_), np.float32)
    dfull[y0:y1, x0:x1] = d
    valid = np.zeros((H_, W_), bool)
    valid[y0 + 4:y1, x0 + 4:x1 - 4] = True
    return full, dfull, valid, A


def feather(m, px):
    m = m.astype(np.float32)
    return np.clip(cv2.GaussianBlur(m, (0, 0), px), 0, 1)


def main():
    H0 = L.rd(os.path.join(RAW, "hw-seedream-r1.png"))
    seg = dict(np.load(os.path.join(SP, "seg", "groups.npz")))
    seg = {k: v > 127 for k, v in seg.items()}
    dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
    # ---- 1. the edits
    e1, d1, v1, A1 = place_edit("e1", "e1-table-nano.jpg", H0)
    e2, d2, v2, A2 = place_edit("e2", "e2-notable-nano.jpg", H0)
    e3, d3, v3, A3 = place_edit("e3", "e3-rugend-nano.jpg", H0)
    np.save(os.path.join(OUTP, "A1.npy"), A1)
    # E1: the table group and what the new ends changed around them (their shadows on the rug), nothing further
    grp = seg["coffee-table"] | seg["bowl"] | seg["candle-holders"]
    chg = (d1 > 0.045) & v1
    chg = cv2.morphologyEx(chg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    n, lb = cv2.connectedComponents((chg | dil(grp, 3)).astype(np.uint8))
    keep = np.isin(lb, np.unique(lb[grp])[1:] if (lb[grp] == 0).any() else np.unique(lb[grp]))
    r1 = (dil(grp, 12) | (keep & dil(grp, 70))) & v1
    r1 &= ~dil(seg["throw"] & ~dil(grp, 30), 2)
    a1 = feather(r1, 4.0) * v1
    # E3: the rug's right end, where the edit differs, right of x 2130 and below the skirting
    yy, xx = np.mgrid[0:H_, 0:W_]
    zone = (xx > 2130) & (yy > 1275) & v3
    chg3 = (d3 > 0.035) & zone
    chg3 = cv2.morphologyEx(chg3.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    chg3 = cv2.morphologyEx(chg3, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8)).astype(bool)
    r3 = dil(chg3, 16) & zone & ~dil(seg["throw"] | seg["floor-lamp"] | seg["sofa"], 4)
    a3 = feather(r3, 5.0) * v3
    H1 = H0 * (1 - a3[..., None]) + e3 * a3[..., None]
    H1 = H1 * (1 - a1[..., None]) + e1 * a1[..., None]
    LOG["paste"] = dict(e1_px=int((a1 > 0.5).sum()), e3_px=int((a3 > 0.5).sum()), e1_changed_px=int(chg.sum()), e3_changed_px=int(chg3.sum()))
    np.savez_compressed(os.path.join(OUTP, "paste-masks.npz"), a1=(a1 * 255).astype(np.uint8), a3=(a3 * 255).astype(np.uint8),
                        v2=v2.astype(np.uint8))
    # ---- 2. the plate to the hero
    P0 = L.rd(os.path.join(L.OUT, "pw-raw-floor.png"))
    prod = np.zeros((H_, W_), bool)
    for k, m in seg.items():
        if k not in ("sofa", "armchair", "window", "window-frame"):
            prod |= m
    m = L.maps()
    prod |= dil(m["idx"] == L.PI["magazine-holder"], 30)
    free = ~dil(prod, 25)
    A, rec = sift_affine(P0, H1, mask_src=free.astype(np.float32), mask_dst=free.astype(np.float32), full=False)
    LOG["plate_to_hero"] = rec
    P1 = cv2.warpAffine(P0, A, (W_, H_), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    np.save(os.path.join(OUTP, "A_plate.npy"), A)
    # the clay's maps follow the plate (the plate is the clay's camera within its lock)
    warp_m = lambda a, nearest=False: cv2.warpAffine(a, A, (W_, H_), flags=cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    idx_p = warp_m(m["idx_p"].astype(np.float32), True).astype(np.int32)
    lamps = {k: warp_m(m["light-" + k]) for k in ("accent-sconces", "floor-lamp", "pendant", "wall-sconce")}
    np.savez_compressed(os.path.join(OUTP, "maps.npz"), idx_p=idx_p, idx=warp_m(m["idx"].astype(np.float32), True).astype(np.int32),
                        depth=warp_m(m["depth"]), sun=warp_m(m["sun"]), **{"light-" + k: v for k, v in lamps.items()})
    # ---- 3. the hero's tone to the plate's, on the quiet surfaces
    quiet = free & ~dil(prod, 60)
    for v in lamps.values():
        quiet &= v < 0.10
    quiet &= ~np.isin(idx_p, [1])                             # not the sofa (cushions, throw and lamp light fall on it)
    quiet[:6] = quiet[-6:] = False
    quiet[:, :6] = quiet[:, -6:] = False
    Pb, Hb = cv2.GaussianBlur(P1, (0, 0), 5.0), cv2.GaussianBlur(H1, (0, 0), 5.0)
    lp, lh0 = L.to_lab(Pb), L.to_lab(Hb)
    # (a) one curve on L* (the quiet surfaces' L* distribution of the hero onto the plate's: quantile to quantile, slope 1 beyond the
    #     1 % and 99 % points) and one shift of a*, b*
    qs = np.linspace(0.01, 0.99, 50)
    xq, yq = np.quantile(lh0[..., 0][quiet], qs), np.quantile(lp[..., 0][quiet], qs)
    yq = np.maximum.accumulate(yq)
    # the dark end: the quiet surfaces hold few darks, so the curve's toe is anchored on the armchair's own darks (its walnut frame,
    # the same object in both frames): its 1 %, 5 % and 20 % L* points, and (0, 0)
    arm = cv2.erode(seg["armchair"].astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    Lh_full, Lp_full = L.to_lab(H1)[..., 0], L.to_lab(P1)[..., 0]
    xd = np.percentile(Lh_full[arm], [1, 5, 20])
    yd = np.percentile(Lp_full[arm], [1, 5, 20])
    keep_q = xq > xd[-1] + 6.0
    xs = np.concatenate([[0.0], xd, xq[keep_q], [xq[-1] + 100.0]])
    ys = np.concatenate([[0.0], yd, yq[keep_q], [yq[-1] + 100.0]])
    ys = np.maximum.accumulate(ys)
    LOG["tone_dark_anchor"] = dict(armchair_hero_L=[round(float(v), 2) for v in xd], armchair_plate_L=[round(float(v), 2) for v in yd])
    dab = np.median((lp - lh0)[quiet][:, 1:], axis=0)

    def curve(rgb):
        lab = L.to_lab(rgb)
        lab[..., 0] = np.clip(np.interp(lab[..., 0], xs, ys), 0, 100)
        lab[..., 1] += dab[0]
        lab[..., 2] += dab[1]
        return lab

    labH = curve(H1)
    # (b) what is left at very low spatial frequency (the model re-lit whole surfaces a little): the plate over the hero on the quiet
    #     surfaces, sigma 140 px, carried across the products and the lamps' pools by a normalised blur; within +-10 L*, +-4 a*, b*
    lh1 = L.to_lab(cv2.GaussianBlur(L.from_lab(labH), (0, 0), 5.0))
    qf = quiet.astype(np.float32)
    field = np.zeros((H_, W_, 3), np.float32)
    den = cv2.GaussianBlur(qf, (0, 0), 140.0)
    den2 = cv2.GaussianBlur(qf, (0, 0), 420.0)
    for c in range(3):
        dlt = (lp[..., c] - lh1[..., c]) * qf
        f1 = cv2.GaussianBlur(dlt, (0, 0), 140.0) / np.maximum(den, 1e-4)
        f2 = cv2.GaussianBlur(dlt, (0, 0), 420.0) / np.maximum(den2, 1e-4)
        wgt = np.clip(den / 0.08, 0, 1)
        field[..., c] = np.clip(f1 * wgt + f2 * (1 - wgt), -10 if c == 0 else -4, 10 if c == 0 else 4)
    field = np.stack([cv2.GaussianBlur(field[..., c], (0, 0), 30.0) for c in range(3)], -1)
    H2 = L.from_lab(labH + field)
    xe = np.zeros_like(e2)
    v2f = v2.astype(np.float32)[..., None]
    NT = L.from_lab(curve(e2) + field) * v2f
    lh = L.to_lab(cv2.GaussianBlur(H2, (0, 0), 5.0))
    wallq = quiet & (idx_p == 5)
    LOG["tone_match"] = dict(quiet_px=int(quiet.sum()), L_curve=dict(x=[round(float(v), 2) for v in xq[::7]], y=[round(float(v), 2) for v in yq[::7]]),
                             ab_shift=[round(float(v), 2) for v in dab], field_L_range=[round(float(field[..., 0].min()), 2), round(float(field[..., 0].max()), 2)],
                             dLab_before=[round(float(v), 2) for v in np.median((lh0 - lp)[quiet], axis=0)],
                             dLab_after=[round(float(v), 2) for v in np.median((lh - lp)[quiet], axis=0)],
                             dL_after_p10_p90=[round(float(np.percentile((lh - lp)[quiet][:, 0], q)), 2) for q in (10, 90)],
                             wall_dL_before_after=[round(float(np.median((lh0 - lp)[wallq][:, 0])), 2), round(float(np.median((lh - lp)[wallq][:, 0])), 2)])
    # ---- 4. the prints
    plog = {}
    H3, cmasks, quads = prints.set_prints(H2, [os.path.join(SP, "refs", f"print-flat-{n}.png") for n in (1, 2, 3)], plog)
    LOG["prints"] = plog
    np.savez_compressed(os.path.join(OUTP, "canvas.npz"), masks=np.stack([c.astype(np.uint8) for c in cmasks]), quads=np.stack(quads))
    # ---- 5. the one grade
    Pg, Hg, NTg = L.apply_grade(P1), L.apply_grade(H3), L.apply_grade(NT)
    Hg_blank = L.apply_grade(H2)
    L.wr(os.path.join(OUTP, "plate-raw-reg.png"), P1)
    L.wr(os.path.join(OUTP, "hero-raw.png"), H3)
    L.wr(os.path.join(OUTP, "plate.png"), Pg)
    L.wr(os.path.join(OUTP, "hero.png"), Hg)
    L.wr(os.path.join(OUTP, "hero-blank-canvases.png"), Hg_blank)
    L.wr(os.path.join(OUTP, "notable.png"), NTg)
    Image.fromarray(np.rint(Hg * 255).astype(np.uint8)).resize((1360, 765), Image.LANCZOS).save(os.path.join(OUTP, "hero-small.jpg"), quality=90)
    LOG["measure_plate"] = L.measure(L.apply_grade(P0))
    LOG["measure_hero"] = L.measure(Hg, hero=True)
    json.dump(LOG, open(os.path.join(OUTP, "prep.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in LOG.items() if k not in ("prints", "tone_match")})[:2600])
    print("tone", {k: v for k, v in LOG["tone_match"].items() if k != "L_curve"})
    for k, v in plog.items():
        print(k, v["canvas"], v["quad"])


if __name__ == "__main__":
    main()
