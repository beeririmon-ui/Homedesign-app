#!/usr/bin/env python3
"""
mb1_prep.py: the inputs and reference boards of the four MB1 layer passes (render-agent, 2026-11-19; 0 tokens).
Each input is the current MB1 composite (the plate, then the plate with the layers already cut) with flat placeholders where the
pass's products go: the clay's own pixels in their id regions (MB1.png / MB1-id.png), so place and size come from the camera and
the cards. The references are crops of MB0's approved frame (mb0-defaults.png), our own render; in the wall board the two canvases
are blanked to #D8C8AE in code (the prints go in by code, as in MB0; art A never goes to the model). The floor pass's board is the
SKU photos (scratchpad only: supplier photos never enter the repo).
  python3 mb1_prep.py <pass> [<base.png>]        pass: p1-bed | p2-right | p3-wall | p4-floor
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
PASSES = {
    "p1-bed": dict(ids=(51, 52, 53, 54), refs=[("mb0-bed", (180, 640, 2560, 1530))]),
    "p2-right": dict(ids=(44, 49, 50, 55, 61, 62, 63, 64), refs=[("mb0-right-nightstand", (1760, 440, 2160, 1010)), ("mb0-corner", (2140, 250, 2720, 1500))]),
    "p3-wall": dict(ids=(40, 41, 42, 43, 45, 46, 47, 48, 56, 57, 58, 59, 60),
                    refs=[("mb0-shelf-blank", (847, 60, 1873, 530)), ("mb0-left", (150, 440, 860, 1060))]),
    "p4-floor": dict(ids=(65, 66, 67), refs=[], sku=["0b466674_98cb4192-d24d-46b3-9c1a-035d20275995_trans.jpeg",
                                                     "e1250230_1619935797764.jpg", "3594713f_fc394992-638e-4235-abef-3731f45e02c7_trans.jpeg"]),
}
CANVASES = [(1096.5, 108.5, 1348.5, 459.0), (1406.5, 315.0, 1606.5, 461.0)]      # MB0's canvases (fb10-compose.json)


def placeholders(base, pids):
    clay = C.load(os.path.join(M.CLAY, "MB1.png"))
    ids = M.ids("MB1")
    m = np.isin(ids, pids)
    out = base.copy()
    out[m] = clay[m]
    return out, m


def ref_crops(name, box):
    mb0 = Image.open(os.path.join(M.MB0, "mb0-defaults.png")).convert("RGB")
    im = mb0.copy()
    if name == "mb0-shelf-blank":
        d = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in CANVASES:
            d.rectangle([int(x0), int(y0), int(x1), int(y1)], fill=(216, 200, 174))
    return im.crop(box)


def board(files, out, h=900):
    ims = [Image.open(f).convert("RGB") if isinstance(f, str) else f for f in files]
    ims = [i.resize((int(i.size[0] * h / i.size[1]), h), Image.LANCZOS) for i in ims]
    w = sum(i.size[0] for i in ims) + 20 * (len(ims) - 1)
    b = Image.new("RGB", (w, h), "white")
    x = 0
    for i in ims:
        b.paste(i, (x, 0))
        x += i.size[0] + 20
    b.save(out)
    return b.size


def main(p, base_path=None):
    base = C.load(base_path or os.path.join(M.ST, "plate.png"))
    P = PASSES[p]
    inp, m = placeholders(base, P["ids"])
    ip = os.path.join(M.ST, "inputs", f"{p}-input.png")
    M.save(ip, inp)
    os.makedirs(M.SCR, exist_ok=True)
    rec = dict(pass_=p, base=os.path.relpath(base_path or os.path.join(M.ST, "plate.png"), M.ST), placeholder_ids=list(P["ids"]),
               placeholder_px=int(m.sum()), input=os.path.relpath(ip, M.ST), input_sha256=M.sha(ip), refs=[])
    crops = [ref_crops(n, b) for n, b in P["refs"]]
    if crops:
        rp = os.path.join(M.ST, "inputs", f"{p}-ref-mb0.png")
        board(crops, rp)
        rec["refs"].append(dict(file=os.path.relpath(rp, M.ST), what=[n for n, _ in P["refs"]], sha256=M.sha(rp)))
    if P.get("sku"):
        rp = os.path.join(M.SCR, f"{p}-ref-sku.png")
        board([M.PICKS + f for f in P["sku"]], rp, h=700)
        rec["refs"].append(dict(file=rp + " (scratchpad only)", what="SKU photos: " + ", ".join(f.split("_")[0] for f in P["sku"]), sha256=M.sha(rp)))
    json.dump(rec, open(os.path.join(M.ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(*sys.argv[1:3])
