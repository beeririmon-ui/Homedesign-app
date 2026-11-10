"""
qa-agent 2026-11-10: DL1 ('the living room and the opening frame are the brightest in the house'; master-designer, docs/master-bedroom-
comparison-2026-11-07.md §5): L* of the master bedroom's wall above the panelling on its lit side (diffuse light, the sun stripes left out)
against the Nordic living room's back wall (nordic-A-fin2.png) on its lit side, the same way: boxes by eye, the median and p75 of L*, and the
pixels above the box's p95 dropped (the sun patches). Also the whole frame's median L* and its p90.
Usage: ~/.venvs/motion/bin/python -I dl1.py <master png> [...]. Writes data/dl1.json (merged per file).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix5")
LR = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06/nordic-A-fin2.png")


def Lstar(p):
    c = np.asarray(Image.open(p).convert("RGB")).astype(float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    Y = c @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def wall(L, boxes):
    v = np.concatenate([L[y0:y1, x0:x1].ravel() for x0, y0, x1, y1 in boxes])
    v = v[v <= np.percentile(v, 95)]
    return dict(median=round(float(np.median(v)), 1), p75=round(float(np.percentile(v, 75)), 1))


fn = os.path.join(OUT, "data", "dl1.json")
res = json.load(open(fn)) if os.path.exists(fn) else {}
Llr = Lstar(LR)
res["living-room nordic-A-fin2"] = dict(wall_lit=wall(Llr, [(1980, 120, 2340, 300), (800, 100, 1180, 280)]),
                                        frame_median=round(float(np.median(Llr)), 1), frame_p90=round(float(np.percentile(Llr, 90)), 1),
                                        boxes="back wall: right of the triptych above the sun patch (1980-2340 x 120-300) and left of the pendant (800-1180 x 100-280)")
for p in sys.argv[1:]:
    L = Lstar(p)
    w = wall(L, [(1720, 60, 2200, 250), (2200, 40, 2600, 200)])
    res[os.path.basename(p)] = dict(wall_lit=w, frame_median=round(float(np.median(L)), 1), frame_p90=round(float(np.percentile(L, 90)), 1),
                                    boxes="the wall above the panelling right of the sun stripes (1720-2200 x 60-250, 2200-2600 x 40-200)",
                                    wall_minus_living_room=round(w["median"] - res["living-room nordic-A-fin2"]["wall_lit"]["median"], 1),
                                    frame_median_minus_living_room=round(float(np.median(L)) - res["living-room nordic-A-fin2"]["frame_median"], 1))
json.dump(res, open(fn, "w"), indent=1)
print(json.dumps(res, indent=1))
