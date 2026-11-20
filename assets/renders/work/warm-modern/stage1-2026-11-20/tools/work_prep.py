#!/usr/bin/env python3
"""
work_prep.py: the inputs of the W0 layer passes (render-agent, 2026-11-20; 0 tokens), MB1's method (tools/mb1_prep.py).
Each input is the current W0 composite (the plate, then the plate with the layers already cut) with flat placeholders where the
pass's products go: the clay's own pixels in their id regions (W0.png / W0-id.png), so place and size come from the camera and the
cards. The canvases (42, 44) are painted flat #D8C8AE (the prints go in by code). The reference boards are SKU crops (and, for the
three temporary repeats, crops of MB1's approved frame): they stay in the scratchpad (supplier photos never enter the repo).
  python3 work_prep.py <pass> [<base.png>]        pass: pA-wall | pB-desk | pC-sides | pD-front
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

C = M.C
PASSES = {
    "pA-wall": dict(ids=(41, 42, 53, 54, 55, 56, 63)),
    "pB-desk": dict(ids=(47, 48, 57, 58, 59, 60, 61, 62)),
    "pC-sides": dict(ids=(40, 43, 44, 45, 49, 50, 51, 52)),
    "pD-front": dict(ids=(46, 64)),
}
CANVAS_IDS = (42, 44)
SAND = np.array([216, 200, 174]) / 255.0


def placeholders(base, pids):
    clay = C.load(os.path.join(M.CLAY, "W0.png"))
    ids = M.ids("W0")
    m = np.isin(ids, pids)
    out = base.copy()
    out[m] = clay[m]
    for k in CANVAS_IDS:
        if k in pids:
            out[ids == k] = SAND
    return out, m


def main(p, base_path=None):
    bp = base_path or os.path.join(M.ST, "plate.png")
    base = C.load(bp)
    P = PASSES[p]
    inp, m = placeholders(base, P["ids"])
    ip = os.path.join(M.ST, "inputs", f"{p}-input.png")
    M.save(ip, inp)
    boards = json.load(open(os.path.join(M.SCR, "sku", "boards.json")))
    b = boards[p]
    rec = dict(pass_=p, base=os.path.relpath(bp, M.ST), placeholder_ids=list(P["ids"]), placeholder_px=int(m.sum()),
               input=os.path.relpath(ip, M.ST), input_sha256=M.sha(ip),
               refs=[dict(file=b["file"] + " (scratchpad only)", tiles_left_to_right=b["order"], sha256=b["sha256"], size=b["size"])])
    json.dump(rec, open(os.path.join(M.ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(*sys.argv[1:3])
