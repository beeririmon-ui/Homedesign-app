#!/usr/bin/env python3
"""
kids_crop.py: the crop edits of the kids' stage one (render-agent, 2026-11-24; 0 tokens beyond the sends), the kitchen's method
(dining stage1-2026-11-20/tools/kd_crop.py): the current canvas of the room with the defaults clay's placeholders pasted in their id
regions, cropped round them at a standard aspect and upscaled to 2048 on the long side; the edit comes back, is locked (ECC affine on the
gradient, masked to the plate's architecture away from the placeholders) onto the crop and pasted into the full canvas.
  prep <pass> <base.png>   : inputs/<pass>-input.png (full canvas) and inputs/<pass>-crop.png (the upload); <pass>-prep.json
  assemble <pass>          : raw/<pass>-r1.* back into the canvas -> scratchpad <pass>-canvas.png (re-made from the raw at any time)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
from kids_passes import PASSES, pass_ids  # noqa: E402

C = K.C


def prep(p, base_path):
    P = PASSES[p]
    kid = P["kid"]
    st = K.ST[kid]
    x0, y0, x1, y1 = P["box"]
    base = C.load(base_path)
    src = PASSES[p].get("clay", f"K-{kid}")
    clay = C.load(os.path.join(K.CLAY, f"{src}.png"))
    ids = K.ids(src)
    pid = pass_ids(p)
    # the clay's frames have dark corners (coplanar overlapping boxes): repainted in the frame's own colour so the model sees a plain frame
    for fid_ in (42, 44):
        fm = ids == fid_
        if fm.sum() > 50:
            lab = C.to_lab(clay)
            med = np.median(lab[fm], 0)
            dark = fm & (lab[..., 0] < med[0] - 12)
            if dark.any():
                lab[dark] = med
                clay = np.where(dark[..., None], np.clip(C.from_lab(lab), 0, 1), clay)
    m = np.isin(ids, pid) & (not P.get("no_placeholder"))
    inp = base.copy()
    inp[m] = clay[m]
    if P.get("base_pass"):
        # a redraw over an earlier edit: the placeholder grown 4 px (its own edge colour), so no edge of the earlier drawing shows round it
        ring = C.dil(m, 4) & ~m
        fill = K.C.spread(clay, m.astype(np.float64), (2.0, 5.0)) if hasattr(K.C, "spread") else None
        if fill is None:
            sys.path.insert(0, os.path.join(K.REPO, "assets/renders/dining/warm-modern/stage1-2026-11-20/tools"))
            import kd_cut2 as KC2
            fill = KC2.spread(clay, m.astype(np.float64), (2.0, 5.0))
        inp[ring] = fill[ring]
        m = m | ring
    ip = os.path.join(st, "inputs", f"{p}-input.png")
    K.save(ip, inp)
    crop = Image.fromarray(C.q(inp)).crop((x0, y0, x1, y1))
    s = 2048 / max(crop.size)
    cp = os.path.join(st, "inputs", f"{p}-crop.png")
    crop.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.LANCZOS).save(cp)
    # the placeholders' mask in the upload's frame (for the record: nano-banana-2 edits the whole crop, the mask says what may change)
    mk = Image.fromarray((m * 255).astype(np.uint8)).crop((x0, y0, x1, y1))
    mp = os.path.join(st, "inputs", f"{p}-mask.png")
    mk.resize((int(round(crop.size[0] * s)), int(round(crop.size[1] * s))), Image.NEAREST).save(mp, optimize=True)
    rec = dict(pass_=p, kid=kid, clay=src, base=K.rel(base_path), mask=K.rel(mp), crop_box=[x0, y0, x1, y1], crop_aspect=round((x1 - x0) / (y1 - y0), 4),
               aspect=P["aspect"], upscale=round(s, 4), placeholder_ids=list(pid), placeholder_px=int(m.sum()), input=K.rel(ip),
               crop=K.rel(cp), crop_sha256=K.sha(cp), board=f"scratchpad wm-kids/boards/{P['board']} (supplier photos, not in the repo)")
    json.dump(rec, open(os.path.join(st, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


def raw_path(p, kid):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        rp = os.path.join(K.ST[kid], "raw", f"{p}-r1{ext}")
        if os.path.exists(rp):
            return rp
    raise FileNotFoundError(p)


def assemble(p):
    P = PASSES[p]
    kid = P["kid"]
    st = K.ST[kid]
    rec = json.load(open(os.path.join(st, "inputs", f"{p}-prep.json")))
    x0, y0, x1, y1 = rec["crop_box"]
    inp = C.load(os.path.join(K.REPO, rec["input"]))
    rp_ = raw_path(p, kid)
    raw = Image.open(rp_).convert("RGB").resize((x1 - x0, y1 - y0), Image.LANCZOS)
    r = np.asarray(raw).astype(np.float32)
    ref = (inp[y0:y1, x0:x1] * 255).astype(np.float32)
    pl_ids = K.ids(f"K-{kid}-plate")[y0:y1, x0:x1]
    ids = K.ids(f"K-{kid}")[y0:y1, x0:x1]
    stable = C.ero(np.isin(pl_ids, K.ARCH), 3) & ~C.dil(np.isin(ids, rec["placeholder_ids"]), 50)
    w = np.eye(2, 3, dtype=np.float32)
    cc, warp = None, w
    try:
        cc, warp = cv2.findTransformECC(K.grad(ref), K.grad(r), w, cv2.MOTION_AFFINE,
                                        (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), stable.astype(np.uint8), 5)
    except cv2.error:
        pass
    lk = cv2.warpAffine(r, warp, (x1 - x0, y1 - y0), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    out = inp.copy()
    out[y0:y1, x0:x1] = np.clip(lk / 255, 0, 1)
    op = os.path.join(K.SCR, f"{p}-canvas.png")
    K.save(op, out)
    rec["assemble"] = dict(raw=K.rel(rp_), ecc=None if cc is None else round(float(cc), 4), warp=[[round(float(v), 5) for v in row] for row in warp],
                           canvas="scratchpad wm-kids/" + os.path.basename(op), stable_px=int(stable.sum()),
                           rule="re-made from raw/<pass>-r1 by kids_crop.py assemble")
    json.dump(rec, open(os.path.join(st, "inputs", f"{p}-prep.json"), "w"), indent=1)
    print(p, json.dumps(rec["assemble"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "prep":
        prep(a[1], a[2])
    elif a[0] == "assemble":
        assemble(a[1])
