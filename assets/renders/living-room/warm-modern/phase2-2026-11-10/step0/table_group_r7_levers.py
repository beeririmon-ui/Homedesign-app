#!/usr/bin/env python3
"""
table_group_r7_levers.py: R7, A.3 step 1, part 2 (render-agent, 2026-11-12; 0 tokens). After table_group_r7.py:
  (1) the pre-approved lever for the iron plates (owner-answers-applied section 1.4: "iron B candle vs a cushion set -> 16"): the three
      iron combinations re-run through step0_clay_checks.main() unchanged with B's candle at 16 (A stays 15);
  (2) the bowl against the cushion sets (the throw): FAILS at the 1.9.4 point for every bowl and every set, and no pre-approved lever
      addresses it (the throw's lower edge lies ABOVE the bowl, not beside it: the designer's estimate assumed its leaning left edge).
      For the designer, projected only, NOTHING MOVED: the bowl-throw gap (every set) and the bowl-holder gap (each pair) for a grid of
      bowl centres on the table top, with step 0's helpers (raster, min_dist; visible silhouettes; F3 0.02).
Writes step0/r7-table-group/levers-r7.json.        python3 table_group_r7_levers.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import step0_clay_checks as S0  # noqa: E402
import table_group_r7 as TG  # noqa: E402

T = S0.TABLE_TOP


def main():
    out = dict(date="2026-11-12", author="render-agent", tokens=0, script=os.path.relpath(__file__, S0.REPO))
    # (1) the iron lever
    TG.HOLDERS["iron-plates"]["candles"] = (0.15, 0.16)
    lev = {}
    for bowl in TG.BOWLS:
        rr = TG.run(bowl, "iron-plates", suffix="__B16")
        lev[bowl] = {k: dict(min_frame=v["min_frame"], verdict=v["verdict"], by_set=v["by_set"]) for k, v in rr["pairs"].items() if v["min_frame"] is not None}
        print("iron B16", bowl, json.dumps({k: v["min_frame"] for k, v in lev[bowl].items()}), flush=True)
    out["iron_B16"] = dict(lever="owner-answers-applied 1.4: the iron B candle 18 -> 16 (A 15)", per_bowl=lev,
                           a_vs_b=TG.a_vs_b("iron-plates"), folders="r7-table-group/<bowl>__iron-plates__B16/")
    # (2) the bowl: projected candidates (nothing moved)
    cush = {}
    for s in "ABC":
        a = np.asarray(Image.open(os.path.join(S0.P1, f"layers-v3c/cushions-set-{s}.png")))[..., 3]
        cush[s] = cv2.resize((a > 127).astype(np.uint8), (S0.GW, S0.GH), interpolation=cv2.INTER_NEAREST).astype(bool)
    hold = {h: S0.raster(TG.holder_parts(h)) for h in TG.HOLDERS}
    grid = []
    for bowl, b in TG.BOWLS.items():
        for x in (0.40, 0.45, 0.50, 0.55, 0.58, 0.62, 0.66, 0.70):
            for y in (1.86, 1.90, 1.94):
                bm = S0.raster([S0.cyl(x, y, b["D"] / 2, T, T + b["H"])])
                th = {s: round(S0.min_dist(bm, cush[s]) / S0.CW, 4) for s in "ABC"}
                hd = {}
                for h, hm in hold.items():
                    hd[h] = round(S0.min_dist(bm, hm) / S0.CW, 4) if not (bm & hm).any() else "overlap"
                front_in = 2.07 - y - b["D"] / 2
                grid.append(dict(bowl=bowl, centre=[x, y], throw_min=min(th.values()), throw=th, holders=hd, inside_front_edge_m=round(front_in, 3),
                                 box=S0.frame_box(bm),
                                 passes=min(th.values()) >= 0.02 and all(v != "overlap" and v >= 0.02 for v in hd.values()) and front_in >= 0.02))
    out["bowl_candidates"] = dict(note="PROJECTED ONLY (step 0's helpers, card cylinders, the bowl's full silhouette; the throw = the approved "
                                       "v3c cushion sets' alpha > 127). Nothing moved; the bowl's point is the designer's (owner WM-T2 approved "
                                       "(0.62, 1.94)). passes = throw >= 0.02 for every set, >= 0.02 from every holder pair at its 1.9.4 points, "
                                       ">= 2 cm inside the table's straight front edge (Y 2.07)", grid=grid,
                                  any_pass=[g for g in grid if g["passes"]])
    json.dump(out, open(os.path.join(TG.OUT, "levers-r7.json"), "w"), indent=1, ensure_ascii=False)
    for g in grid:
        print(g["bowl"], g["centre"], "throw", g["throw_min"], "holders", g["holders"], "front", g["inside_front_edge_m"], "PASS" if g["passes"] else "")


if __name__ == "__main__":
    main()
