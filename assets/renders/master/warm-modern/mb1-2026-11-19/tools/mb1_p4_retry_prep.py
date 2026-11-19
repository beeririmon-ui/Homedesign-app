#!/usr/bin/env python3
"""
mb1_p4_retry_prep.py: the input of the floor pass's retry (render-agent, 2026-11-19; 0 tokens). The first floor edit (raw/p4-floor.png)
drew the rug well, but left the throw's placeholder block on the bench's left end (it draped a throw over the right half instead) and set
the basket in the open floor in front of the bed, not under the bench. The retry's input: the composite after p1-p3, its rug placeholder
filled with that edit's rug (locked onto its input and matched outside the zone), except round the misplaced basket (its hull grown 30 px,
and its shadow), which keeps the flat placeholder; the throw and the basket placeholders as before.
  python3 mb1_p4_retry_prep.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST


def main():
    ids, pl_ids = M.ids("MB1"), M.ids("MB1-plate")
    base = C.load(os.path.join(ST, "inputs", "base-after-p3.png"))
    inp = C.load(os.path.join(ST, "inputs", "p4-floor-input.png"))
    zone = C.dil(np.isin(ids, (65, 66, 67)), 40)
    stable = C.ero(np.isin(pl_ids, (1, 2, 5, 9, 12, 13, 14, 20, 21, 24, 25, 28)), 3) & ~C.dil(zone, 40)
    e, rl = M.ecc_lock(os.path.join(ST, "raw", "p4-floor.png"), os.path.join(ST, "inputs", "p4-floor-input.png"), stable)
    g = C.gain_field(e, base, ~C.dil(zone, 40))
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    lab = C.to_lab(e)
    L, Ch = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    # the misplaced basket (with its shadow) and the throw draped down past the bench onto the rug: placeholder again (boxes from the
    # edit at x1: the basket x 1430-1740, y 1136-1476; the throw's fall x 320-880, y 1040-1480)
    hole = C.box_mask([(1405, 1110, 1770, 1505), (320, 1040, 880, 1480)])
    pts = cv2.findNonZero(hole.astype(np.uint8))
    rug = (ids == 67) & ~hole
    out = inp.copy()
    out[rug] = e[rug]
    p = os.path.join(ST, "inputs", "p4-floor-r2-input.png")
    M.save(p, out)
    np.save(os.path.join(M.SCR, "p4-first-locked.npy"), e.astype(np.float32))
    rec = dict(input=os.path.relpath(p, ST), input_sha256=M.sha(p), lock=rl, hole_px=int(hole.sum()),
               basket_drawn_bbox=[int(v) for v in cv2.boundingRect(pts)])
    json.dump(rec, open(os.path.join(ST, "inputs", "p4-floor-r2-prep.json"), "w"), indent=1)
    print(json.dumps(rec)[:600])


if __name__ == "__main__":
    main()
