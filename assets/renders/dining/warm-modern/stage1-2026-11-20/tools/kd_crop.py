#!/usr/bin/env python3
"""
kd_crop.py: crop edits for small products (render-agent, resumed session, 2026-11-20; 0 tokens beyond the sends).
Why: in the full-frame edits the model moved or enlarged the small products (D-right r1: the plates drawn on the left shelf, the mill
pair split, the bowl about 1.6x the card's 21 cm; E-left r1: the sconce and the board drawn right of the hood; B r1: the floor vase about
2x the card's 45 x 28). A crop round the placeholders, sent at 2K, makes each placeholder several times larger in the model's input, so
it holds place and size better, and the product comes back with more detail.
  prep <pass> <frame> x0 y0 x1 y1 <clay id> ...  : the full-canvas input (the plate with the clay placeholders of those ids) and its crop,
                                                   upscaled to 2048 on the long side (inputs/<pass>-input.png, inputs/<pass>-crop.png)
  prepv <pass> <frame> <frame png> x0 y0 x1 y1 : a variant's input (a finished frame) and its crop
  assemble <pass>                               : raw/<pass>-r1.png (the crop edit) back to the crop's size, locked (ECC affine on the
                                                   gradient, masked to the plate's architecture) onto the crop input and pasted into
                                                   the full input; written to the scratchpad (re-made from the raw at any time), and
                                                   passes.json points the cut at it
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

C = K.C
ST = K.ST


def prep(p, fr, x0, y0, x1, y1, ids_):
    base = C.load(os.path.join(ST, f"plate-{fr}.png"))
    clay = C.load(os.path.join(K.CLAY, f"{fr}.png"))
    ids = K.ids(fr)
    m = np.isin(ids, ids_)
    inp = base.copy()
    inp[m] = clay[m]
    ip = os.path.join(ST, "inputs", f"{p}-input.png")
    K.save(ip, inp)
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(ST, "inputs", f"{p}-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    rec = dict(pass_=p, frame=fr, base=f"plate-{fr}.png", crop_box=[x0, y0, x1, y1], crop_aspect=round((x1 - x0) / (y1 - y0), 4),
               upscale=round(s, 4), placeholder_ids=list(ids_), placeholder_px=int(m.sum()), input=os.path.relpath(ip, ST),
               crop=os.path.relpath(cp, ST), crop_sha256=K.sha(cp))
    json.dump(rec, open(os.path.join(ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


def prepv(p, fr, src, x0, y0, x1, y1):
    """a variant pass: the input is a finished frame (the defaults), not the plate with placeholders"""
    inp = C.load(os.path.join(ST, src))
    ip = os.path.join(ST, "inputs", f"{p}-input.png")
    K.save(ip, inp)
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(ST, "inputs", f"{p}-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    rec = dict(pass_=p, frame=fr, base=os.path.relpath(ip, ST), source_frame=src, crop_box=[x0, y0, x1, y1],
               crop_aspect=round((x1 - x0) / (y1 - y0), 4), upscale=round(s, 4), placeholder_ids=[50], placeholder_px=0,
               input=os.path.relpath(ip, ST), crop=os.path.relpath(cp, ST), crop_sha256=K.sha(cp))
    json.dump(rec, open(os.path.join(ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


def assemble(p):
    rec = json.load(open(os.path.join(ST, "inputs", f"{p}-prep.json")))
    x0, y0, x1, y1 = rec["crop_box"]
    fr = rec["frame"]
    inp = C.load(os.path.join(ST, rec["input"]))
    rp_ = os.path.join(ST, "raw", f"{p}-r1.png")
    rp_ = rp_ if os.path.exists(rp_) else rp_[:-4] + ".jpg"
    raw = Image.open(rp_).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS)
    r = np.asarray(raw).astype(np.float32)
    ref = (inp[y0:y1, x0:x1] * 255).astype(np.float32)
    pl_ids = K.ids(f"{fr}-plate")[y0:y1, x0:x1]
    ids = K.ids(fr)[y0:y1, x0:x1]
    stable = C.ero(np.isin(pl_ids, (1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 36, 37, 38, 40, 41, 42, 43)), 3)
    stable &= ~C.dil(np.isin(ids, rec["placeholder_ids"]), 50)

    def g(a):
        y = cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.5)
        gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
        mm = np.sqrt(gx * gx + gy * gy)
        return mm / (np.percentile(mm, 99) + 1e-6)
    w = np.eye(2, 3, dtype=np.float32)
    cc, warp = None, w
    try:
        cc, warp = cv2.findTransformECC(g(ref), g(r), w, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7),
                                        stable.astype(np.uint8), 5)
    except cv2.error:
        pass
    lk = cv2.warpAffine(r, warp, (x1 - x0, y1 - y0), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    out = inp.copy()
    out[y0:y1, x0:x1] = np.clip(lk / 255, 0, 1)
    op = os.path.join(K.SCR, f"{p}-canvas.png")
    K.save(op, out)
    rec["assemble"] = dict(ecc=None if cc is None else round(float(cc), 4), warp=[[round(float(v), 5) for v in row] for row in warp],
                           canvas=op, rule="re-made from raw/<pass>-r1.png by kd_crop.py assemble; the cut locks it again (ECC) on the full input")
    json.dump(rec, open(os.path.join(ST, "inputs", f"{p}-prep.json"), "w"), indent=1)
    J = json.load(open(os.path.join(ST, "passes.json")))
    J[p] = dict(raw=op, raw_repo=os.path.relpath(rp_, ST), input=rec["input"], base=rec["base"], crop_box=rec["crop_box"])
    json.dump(J, open(os.path.join(ST, "passes.json"), "w"), indent=1)
    print(p, json.dumps(rec["assemble"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "prep":
        prep(a[1], a[2], *map(int, a[3:7]), [int(v) for v in a[7:]])
    elif a[0] == "prepv":
        prepv(a[1], a[2], a[3], *map(int, a[4:8]))
    elif a[0] == "assemble":
        assemble(a[1])
