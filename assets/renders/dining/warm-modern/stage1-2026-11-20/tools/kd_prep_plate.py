#!/usr/bin/env python3
"""
prep_plate.py: the model inputs of the D1 / D2 empty plates (render-agent, 2026-11-20; 0 tokens).
MB0's recipe (master stage1 tools/prep_plate.py): the lit clay <frame>-plate recoloured through its id pass so the model sees the house's
own materials. Chroma per material (half of the clay's own variation kept); lightness and shading are the clay's unless noted:
  plaster, hood, reveals (1-9, 12, 16, 37)  a* 0.5, b* 4.0     base.png's back wall (as MB0)
  smoked oak (10)                            a* 7.6, b* 16.3    base.png's floor; joints (11) the oak's chroma, L* 12 below
  walnut (20, 21, 22, 24, 38, 42)            a* 11.4, b* 17.6   base.png's coffee-table top
  cognac leather seats (23)                  a* 17, b* 27
  taupe lowers (30)                          #9C8B7A's a* b*
  plinths, grooves (31, 45)                  a* 7.0, b* 9.0, L* capped at 24
  limestone worktop, splash, sill (14, 32, 33)  a* 2.5, b* 13.5, L* -4 (as MB0 / the bath)
  sink (34)                                  the stone's chroma, L* -10
  brushed brass tap (35)                     a* 4, b* 30
  hob (36)                                   a* 0.5, b* 1.5, L* capped at 16
  bone talls (40, 41)                        #E3DBCF's a* b*
  espresso oven (43)                         #2E2824's a* b*, L* 18 + a third of the clay's variation
  bronze frame, oven bar (13, 44)            a* 2.4, b* 5.1, L* 24 + 0.3 of the variation
For D2 (--overlap D1-plate.png): where D1 sees the same direction, the finished D1 plate warped by the rotation homography replaces the clay
(a 60 px feather inside the overlap), so the model continues one house; recorded in the json.

  python3 kd_prep_plate.py D1
  python3 kd_prep_plate.py D2 --overlap plate-D1.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

C = K.C


def ab(hexc):
    v = K.lab_hex(hexc)
    return float(v[1]), float(v[2])


TARGET = {"plaster": ((1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 37), 0.5, 4.0, None), "oak": ((10,), 7.6, 16.3, None),
          "walnut": ((20, 21, 22, 24, 38, 42), 11.4, 17.6, None), "leather": ((23,), 17.0, 27.0, None),
          "taupe": ((30,), *ab("#9C8B7A"), None), "dark": ((31, 45), 7.0, 9.0, ("cap", 24.0)), "stone": ((14, 32, 33), 2.5, 13.5, ("shift", -4.0)),
          "sink": ((34,), 2.5, 13.5, ("shift", -10.0)), "brass": ((35,), 4.0, 30.0, None), "hob": ((36,), 0.5, 1.5, ("cap", 16.0)),
          "bone": ((40, 41), *ab("#E3DBCF"), None), "espresso": ((43,), *ab("#2E2824"), ("set", 18.0, 0.33)),
          "bronze": ((13, 44), 2.4, 5.1, ("set", 24.0, 0.3))}


def main(fr, overlap=None):
    clay = os.path.join(K.CLAY, f"{fr}-plate.png")
    a = C.load(clay)
    ids = K.ids(f"{fr}-plate")
    L = C.to_lab(a)
    rep = dict(frame=fr, clay=os.path.relpath(clay, "/home/user/homedesign-app"), materials={})
    for name, (gids, ta, tb, lm) in TARGET.items():
        m = np.isin(ids, gids)
        if not m.any():
            continue
        before = np.median(L[m], 0)
        L[m, 1] = ta + (L[m, 1] - before[1]) * 0.5
        L[m, 2] = tb + (L[m, 2] - before[2]) * 0.5
        if lm:
            if lm[0] == "cap":
                L[m, 0] = np.minimum(L[m, 0], lm[1])
            elif lm[0] == "shift":
                L[m, 0] = np.clip(L[m, 0] + lm[1], 0, 100)
            elif lm[0] == "set":
                L[m, 0] = lm[1] + (L[m, 0] - before[0]) * lm[2]
        rep["materials"][name] = dict(ids=list(gids), px=int(m.sum()), before_Lab=[round(float(x), 1) for x in before], after_ab=[round(ta, 1), round(tb, 1)],
                                      after_median_L=round(float(np.median(L[m, 0])), 1))
    j = ids == 11
    if j.any():
        L[j, 1], L[j, 2] = 7.6, 16.3
        L[j, 0] = np.clip(L[j, 0] - 12, 0, 100)
    out = np.clip(C.from_lab(L), 0, 1)
    if overlap:
        src = C.load(os.path.join(K.ST, overlap))
        mx, my, ok = K.map_between("D1", fr)
        wv = K.warp(src, "D1", fr, maps=(mx, my, ok))
        # the overlap inside D1's 16:9 frame only; feathered 60 px from its edge
        fm = K.warp(K.frame_mask(), "D1", fr, maps=(mx, my, ok))
        import cv2
        dist = cv2.distanceTransform(fm.astype(np.uint8), cv2.DIST_L2, 5)
        w = np.clip(dist / 60.0, 0, 1)[..., None]
        out = wv * w + out * (1 - w)
        rep["overlap"] = dict(source=overlap, px=int(fm.sum()), feather_px=60, frac_of_canvas=round(float(fm.mean()), 3),
                              note="the finished D1 plate, warped by the rotation homography about PD, replaces the clay where D1 sees it")
    p = os.path.join(K.ST, "inputs", f"plate-{fr}-input.png")
    K.save(p, out)
    rep["input"] = os.path.relpath(p, K.ST)
    rep["sha256"] = K.sha(p)
    json.dump(rep, open(os.path.join(K.ST, "inputs", f"plate-{fr}-input-prep.json"), "w"), indent=1)
    print(json.dumps(rep)[:1500])


if __name__ == "__main__":
    args = sys.argv[1:]
    ov = args[args.index("--overlap") + 1] if "--overlap" in args else None
    main(args[0], ov)
