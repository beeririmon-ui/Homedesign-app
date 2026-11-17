#!/usr/bin/env python3
"""
prep_hdx.py: the model input of the HDx still, and the seed that is kept (render-agent, 2026-11-17). 0 tokens.
  the seed = base.png through M0's depth (site/tools/transitions/seeds.py hdx), kept ONLY where the clay HDx shows the
             living room (ids 30-43): base.png's depth knows nothing of the hall walls that hide part of it from HDx
             + the view through the glazing (clay id 0) from base.png by rotation alone (a view at infinity: exact),
             where base.png also shows the view (its depth map is 0 there)
  input    = the clay HDx (2496 x 1664, the tall 3:2 canvas) with:
             - the seed pasted
             - the living-room surfaces the seed does not cover, per id: a linear gain and the chroma that make them meet
               the seed at its boundary (the floor ahead of M0's frame, the ceiling, the holes behind the furniture)
             - the hall: the stone panel (94) tinted limestone at its clay level (11.9.3 target -1.0 is the clay's own
               -1.01); plaster (12, 14, 24) tinted bone; the walnut lining (20-23) to an oiled walnut, median L* 30;
               the hall floor (10, 25) to smoked oak at the hall's level (L* 42)
  python3 prep_hdx.py <seed_dir> <out_input.png> <out_keep_mask.png> <out_seed_full.png>
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
LIVING = tuple(range(30, 44))
W709 = np.array([0.2126, 0.7152, 0.0722])


def main(seed_dir, out, out_keep, out_seed):
    clay = np.asarray(Image.open(K.CLAY + "/HDx.png").convert("RGB")).astype(np.float64) / 255
    seed = np.asarray(Image.open(seed_dir + "/hdx-seed.png").convert("RGB")).astype(np.float64) / 255
    sm = np.asarray(Image.open(seed_dir + "/hdx-seed-mask.png")) > 127
    cls = K.clay_id("HDx")
    tcv = K.canvas("HDx")
    # the view through the glazing: base.png by rotation (M0 -> HDx); valid where base's depth map has no surface
    base = np.asarray(Image.open(K.BASE).convert("RGB")).astype(np.float32) / 255
    bcv = cg.Canvas.base(2720)
    view, cov = cg.rot_warp(base, cg.M0, bcv, cg.HDX, tcv)
    _, bvalid = cg.load_room_depth(K.REPO + "/assets/renders/living-room/warm-modern/depth.png")
    mx, my, _f = cg.rot_map(cg.M0, bcv, cg.HDX, tcv)
    bv = cv2.remap(bvalid.astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=1) > 0
    vmask = (cls == 0) & cov & ~bv
    vmask = cv2.erode(vmask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    keep = (sm & np.isin(cls, LIVING)) | vmask
    seedfull = np.where(sm[..., None], seed, 0.5)
    seedfull[vmask] = view[vmask]
    rep = dict(seed_raw_px=int(sm.sum()), seed_kept_px=int((sm & np.isin(cls, LIVING)).sum()), view_px=int(vmask.sum()),
               seed_dropped_on_hall_px=int((sm & ~np.isin(cls, LIVING)).sum()))

    lin = to_lin(clay)
    lin_seed = to_lin(seedfull)
    lab = lab_from_lin(lin)
    lab_seed = lab_from_lin(lin_seed)
    out_lin = lin.copy()
    k15 = np.ones((31, 31), np.uint8)
    near_keep = cv2.dilate(keep.astype(np.uint8), k15) > 0
    near_new = cv2.dilate((~keep).astype(np.uint8), k15) > 0
    per = {}
    for i in LIVING + (0,):
        new = (cls == i) & ~keep
        if new.sum() < 50:
            continue
        have = (cls == i) & keep
        a_in, a_out = have & near_new, new & near_keep
        Yc = lin @ W709
        Ys = lin_seed @ W709
        if a_in.sum() > 200 and a_out.sum() > 200:
            g = float(np.median(Ys[a_in]) / np.median(Yc[a_out]))
            ref = a_in
            how = "boundary"
        elif have.sum() > 200:
            g = float(np.median(Ys[have]) / np.median(Yc[new]))
            ref = have
            how = "whole id"
        else:
            per[i] = "no seed for this id: clay kept"
            continue
        sub = lab_from_lin(np.clip(lin[new] * g, 0, 1))
        sub[:, 1] = np.median(lab_seed[ref, 1]) + (sub[:, 1] - sub[:, 1].mean()) * 0.3
        sub[:, 2] = np.median(lab_seed[ref, 2]) + (sub[:, 2] - sub[:, 2].mean()) * 0.3
        out_lin[new] = lin_from_lab(sub)
        per[i] = dict(px=int(new.sum()), gain=round(g, 3), how=how)
    rep["living_new_surfaces"] = per

    def tint(ids, a, b, L=None):
        mm = np.isin(cls, ids) & ~keep
        if not mm.any():
            return 0
        sub = lab_from_lin(out_lin[mm])
        if L is not None:
            Ymed = float(np.median(out_lin[mm] @ W709))
            Yt = ((L + 16) / 116) ** 3
            sub = lab_from_lin(np.clip(out_lin[mm] * (Yt / Ymed), 0, 1))
        sub[:, 1] = a + (sub[:, 1] - sub[:, 1].mean()) * 0.3
        sub[:, 2] = b + (sub[:, 2] - sub[:, 2].mean()) * 0.3
        out_lin[mm] = lin_from_lab(sub)
        return int(mm.sum())
    # the view through the glazing that base.png cannot give from here: base.png's own view colour (its depth map is 0 there)
    bview = ~bvalid
    lab_b = lab_from_lin(to_lin(base.astype(np.float64)))
    vw = (cls == 0) & ~keep
    if vw.any():
        sub = lab_from_lin(out_lin[vw])
        Lt = float(np.median(lab_b[bview, 0]))
        sub[:, 0] = Lt + (sub[:, 0] - sub[:, 0].mean()) * 0.5
        sub[:, 1] = float(np.median(lab_b[bview, 1]))
        sub[:, 2] = float(np.median(lab_b[bview, 2]))
        out_lin[vw] = lin_from_lab(sub)
        rep["view_new"] = dict(px=int(vw.sum()), lab_from_base=[round(Lt, 1), round(float(np.median(lab_b[bview, 1])), 1), round(float(np.median(lab_b[bview, 2])), 1)])
    rep["hall"] = dict(stone=tint((94,), 2.5, 12.0), joints=tint((86,), 3.5, 11.0), plaster=tint((12, 14, 24), 1.2, 6.0),
                       walnut=tint((20, 21, 22, 23), 11.0, 18.0, L=30.0), floor=tint((10, 25), 6.0, 15.0, L=42.0))
    res = np.where(keep[..., None], lin_seed, out_lin)
    K.save_rgb(out, to_srgb(res))
    Image.fromarray(np.where(keep, 255, 0).astype(np.uint8)).save(out_keep)
    K.save_rgb(out_seed, to_srgb(np.where(keep[..., None], lin_seed, 0.5 ** 2.2)))
    rep["levels_of_input"] = K.levels("HDx", np.asarray(Image.open(out).convert("RGB")))
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:5])
