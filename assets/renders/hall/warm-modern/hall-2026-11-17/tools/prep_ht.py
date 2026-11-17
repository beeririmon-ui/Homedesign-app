#!/usr/bin/env python3
"""
prep_ht.py: the model input of the HT still (render-agent, 2026-11-17). 0 tokens.
  the seed  = site/tools/transitions/seeds.py ht (HD, HDx, base.png reprojected to HT; motion-agent's tool, the manager's addendum)
  the input = the clay HT (2720 x 1530, base.png's canvas) with the seed pasted, and:
    - the far wall (plaster, jib door, stone, skirting): a gain per row from the seed's side edges (the slot's wash continues)
    - every other surface the seed does not cover, per clay id: the linear gain and chroma that meet the seed at its boundary
      (a 15 px band each side; if the id has no boundary, its whole seeded part), so HD's wall, HDx's corner and base.png's room
      continue into the new parts
    - the hall floor (10): smoked oak, L* 42 (the hall's level, as in D0o)
    - the view through the glazing (0): base.png by rotation alone (a view at infinity) where base.png shows the view in that
      direction; elsewhere base.png's view colour
    - the edge of the open front-door leaf in the left margin (id 72, x 0-6, outside the 16:9 frame): painted as the plaster
      beside it, so the model draws no door (the code draws the leaf)
    - in the input only, the seed fades into the new parts over 30 px on the same surface
  python3 prep_ht.py <seed_dir> <out_input.png> <out_keep_mask.png> <out_seed_full.png>
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K  # noqa: E402
from prep_d0o import lab_from_lin, lin_from_lab, to_lin, to_srgb  # noqa: E402

cg = K.cg
W709 = np.array([0.2126, 0.7152, 0.0722])


def main(sd, out, out_keep, out_seed):
    clay = to_lin(np.asarray(Image.open(K.CLAY + "/HT.png").convert("RGB")).astype(np.float64) / 255)
    seed = to_lin(np.asarray(Image.open(sd + "/ht-seed.png").convert("RGB")).astype(np.float64) / 255)
    keep = np.asarray(Image.open(sd + "/ht-seed-mask.png")) > 127
    cls = K.clay_id("HT").copy()
    cls[cls == 72] = 11                                    # the leaf's edge in the margin -> plaster
    hcv = K.canvas("HT")
    # the view: base.png by rotation (M0 -> HT) where base.png's depth has no surface
    base = np.asarray(Image.open(K.BASE).convert("RGB")).astype(np.float32) / 255
    bcv = cg.Canvas.base(2720)
    view, cov = cg.rot_warp(base, cg.M0, bcv, K.HT_CAM, hcv)
    _, bvalid = cg.load_room_depth(K.REPO + "/assets/renders/living-room/warm-modern/depth.png")
    mx, my, _f = cg.rot_map(cg.M0, bcv, K.HT_CAM, hcv)
    bv = cv2.remap(bvalid.astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=1) > 0
    vmask = (cls == 0) & cov & ~bv & ~keep
    vmask = cv2.erode(vmask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    seed = seed.copy()
    seed[vmask] = to_lin(view[vmask].astype(np.float64))
    keep = keep | vmask
    rep = dict(seed_px=int(keep.sum()), view_by_rotation_px=int(vmask.sum()))
    Yc, Ys = clay @ W709, seed @ W709
    labs = lab_from_lin(seed)
    res = clay.copy()
    k31 = np.ones((31, 31), np.uint8)
    near_keep = cv2.dilate(keep.astype(np.uint8), k31) > 0
    near_new = cv2.dilate((~keep).astype(np.uint8), k31) > 0
    per = {}
    for i in np.unique(cls):
        new = (cls == i) & ~keep
        if new.sum() < 50 or i == 10:
            continue
        have = (cls == i) & keep
        a_in, a_out = have & near_new, new & near_keep
        if a_in.sum() > 200 and a_out.sum() > 200:
            g = float(np.median(Ys[a_in]) / np.median(Yc[a_out])); ref = a_in; how = "boundary"
        elif have.sum() > 200:
            g = float(np.median(Ys[have]) / np.median(Yc[new])); ref = have; how = "whole id"
        else:
            per[int(i)] = "no seed for this id"
            continue
        sub = lab_from_lin(np.clip(clay[new] * g, 0, 1))
        sub[:, 1] = np.median(labs[ref, 1]) + (sub[:, 1] - sub[:, 1].mean()) * 0.3
        sub[:, 2] = np.median(labs[ref, 2]) + (sub[:, 2] - sub[:, 2].mean()) * 0.3
        res[new] = lin_from_lab(sub)
        per[int(i)] = dict(px=int(new.sum()), gain=round(g, 3), how=how)
    # ids with no seed: the skirting as the plaster, the view as base.png's view colour
    for i, src in ((14, 11), (0, None)):
        new = (cls == i) & ~keep
        if not new.any() or (isinstance(per.get(int(i)), dict)):
            continue
        sub = lab_from_lin(res[new])
        if src is not None:
            g = per.get(src, {}).get("gain", 1.0) if isinstance(per.get(src), dict) else 1.0
            sub = lab_from_lin(np.clip(clay[new] * g, 0, 1))
            pm = (cls == src) & keep
            sub[:, 1] = np.median(labs[pm, 1]); sub[:, 2] = np.median(labs[pm, 2])
        else:
            lb = lab_from_lin(to_lin(base.astype(np.float64)))
            sub[:, 0] = float(np.median(lb[~bvalid, 0])) + (sub[:, 0] - sub[:, 0].mean()) * 0.5
            sub[:, 1] = float(np.median(lb[~bvalid, 1])); sub[:, 2] = float(np.median(lb[~bvalid, 2]))
        res[new] = lin_from_lab(sub)
        per[int(i)] = dict(px=int(new.sum()), how="from " + ("plaster" if src else "base.png's view colour"))
    # the far wall (X 0.80: plaster 11, jib door 82 / 83, stone 94 / 86, skirting 14): a gain PER ROW, measured where the seed's
    # side edges meet the same surface (15 px bands), smoothed (quadratic in the row inside the seeded rows, flat beyond them),
    # so that the wash from the roof-light slot continues above and below HD's patch instead of a block of one tone
    far = (11, 82, 83, 94, 86, 14)
    Hh, Ww = cls.shape
    for grp in ((11, 82, 83, 14), (94, 86)):
        g_rows = np.full(Hh, np.nan)
        for y in range(Hh):
            kr = keep[y]
            if not kr.any():
                continue
            xs = np.nonzero(np.diff(kr.astype(np.int8)) != 0)[0]
            gin, gout = [], []
            for x in xs:
                for side in (-1, 1):
                    a_in = slice(max(0, x + 1 + 3), min(Ww, x + 1 + 18)) if side == 1 else slice(max(0, x - 17), max(0, x - 2))
                    seg_keep = kr[a_in]
                    seg_cls = np.isin(cls[y, a_in], grp)
                    ins = seg_keep & seg_cls
                    outs = ~seg_keep & seg_cls
                    if ins.sum() >= 6:
                        gin += list(Ys[y, a_in][ins])
                    if outs.sum() >= 6:
                        gout += list(Yc[y, a_in][outs])
            if len(gin) >= 6 and len(gout) >= 6:
                g_rows[y] = np.median(gin) / np.median(gout)
        ok = np.isfinite(g_rows)
        if ok.sum() < 50:
            continue
        rows = np.arange(Hh)
        lo, hi = rows[ok].min(), rows[ok].max()
        c2 = np.polyfit(rows[ok], np.log(g_rows[ok]), 2)
        gfit = np.exp(np.polyval(c2, np.clip(rows, lo, hi)))
        sel = np.isin(cls, grp) & ~keep
        G = gfit[:, None].repeat(Ww, 1)
        res[sel] = clay[sel] * G[sel][:, None]
        ref = np.isin(cls, grp) & keep
        sub = lab_from_lin(res[sel])
        sub[:, 1] = np.median(labs[ref, 1]) + (sub[:, 1] - sub[:, 1].mean()) * 0.3
        sub[:, 2] = np.median(labs[ref, 2]) + (sub[:, 2] - sub[:, 2].mean()) * 0.3
        res[sel] = lin_from_lab(sub)
        per["far wall " + "/".join(map(str, grp))] = dict(rows_measured=int(ok.sum()), gain_range=[round(float(gfit.min()), 3), round(float(gfit.max()), 3)])
    fl = (cls == 10) & ~keep
    if fl.any():
        Yt = ((42 + 16) / 116) ** 3
        sub = lab_from_lin(np.clip(clay[fl] * (Yt / float(np.median(Yc[fl]))), 0, 1))
        sub[:, 1] = 6.0 + (sub[:, 1] - sub[:, 1].mean()) * 0.3
        sub[:, 2] = 15.0 + (sub[:, 2] - sub[:, 2].mean()) * 0.3
        res[fl] = lin_from_lab(sub)
        per[10] = dict(px=int(fl.sum()), how="smoked oak, L* 42")
    # in the INPUT only: the seed fades into the new parts over 30 px where the same surface continues (no hard rectangles for
    # the model to copy); the paste-back after the render uses the exact seed
    same = np.zeros_like(keep)
    for grp in ((11, 82, 83, 14), (94, 86), tuple(range(30, 44)) + (0,)):
        g_ = np.isin(cls, grp)
        same |= g_ & (cv2.dilate((g_ & ~keep).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0)
    dt = cv2.distanceTransform(keep.astype(np.uint8), cv2.DIST_L2, 5)
    a_in = np.where(same, np.clip(dt / 30.0, 0, 1), 1.0) * keep
    res = seed * a_in[..., None] + res * (1 - a_in[..., None])
    K.save_rgb(out, to_srgb(res))
    Image.fromarray(np.where(keep, 255, 0).astype(np.uint8)).save(out_keep)
    K.save_rgb(out_seed, to_srgb(np.where(keep[..., None], seed, 0.5 ** 2.2)))
    rep["per_id"] = per
    rep["levels_of_input"] = K.levels("HT", np.asarray(Image.open(out).convert("RGB")))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
