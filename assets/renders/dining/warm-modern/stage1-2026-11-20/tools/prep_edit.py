#!/usr/bin/env python3
"""
prep_edit.py: the model input of one mask-edit pass (render-agent, 2026-11-20; 0 tokens). MB1's recipe: the current composite of the
frame (plate-<frame>.png, then the frame with the layers already cut) with flat placeholders where the pass's products go: the defaults
clay's own pixels in their id regions (<frame>.png / <frame>-id.png), so place and size come from the camera and the cards. The lit
clay lamp (the pendant, the sconce) is the placeholder of a lit lamp. The SKU board is made separately (kd_board.py, python3.12 -I,
scratchpad only).
  python3 prep_edit.py <pass> [<base.png>]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
from kd_passes import PASSES  # noqa: E402

C = K.C


def main(p, base_path=None):
    P = PASSES[p]
    fr = P["frame"]
    base_path = base_path or os.path.join(K.ST, f"plate-{fr}.png")
    base = C.load(base_path)
    clay = C.load(os.path.join(K.CLAY, f"{fr}.png"))
    ids = K.ids(fr)
    m = np.isin(ids, P["ids"])
    inp = base.copy()
    if not P.get("variant"):
        inp[m] = clay[m]
    ip = os.path.join(K.ST, "inputs", f"{p}-input.png")
    K.save(ip, inp)
    rec = dict(pass_=p, frame=fr, base=os.path.relpath(base_path, K.ST), placeholder_ids=list(P["ids"]), placeholder_px=int(m.sum()),
               input=os.path.relpath(ip, K.ST), input_sha256=K.sha(ip),
               sku_board=f"scratchpad render-dining/boards/{p}-sku.jpg (supplier photos, not in the repo)", sku=P["sku"])
    json.dump(rec, open(os.path.join(K.ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(*sys.argv[1:3])
