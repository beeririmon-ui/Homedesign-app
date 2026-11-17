#!/usr/bin/env python3
"""compose_hdx.py: HDx = the model's render with the kept seed (base.png through M0's depth, ids 30-43 of the clay) pasted
back: a hard edge where the seed meets the hall's architecture, feathered (sigma 3 px) where it meets the model's own
continuation of the living room, and hard within 30 px of the furniture (no ghosting of the model's own legs). Then the seam
tone per surface at that paste. render-agent 2026-11-17, 0 tokens.
  python3 compose_hdx.py <raw.png> <seed_kept.png> <keep_mask.png> <out.png> <out_seam.json> [<alt.png>]
  with <alt.png>: the hall from <raw.png>, the living room's holes from <alt.png> (the split used for HDx r2, below)"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K, lock_tall as T
raw, seedp, keepp, out, outj = sys.argv[1:6]
alt = sys.argv[6] if len(sys.argv) > 6 else None     # another render of the same camera, for the living room
m = np.asarray(Image.open(raw).convert("RGB")).astype(np.float64) / 255
s = np.asarray(Image.open(seedp).convert("RGB")).astype(np.float64) / 255
keep = np.asarray(Image.open(keepp)) > 127
cls = K.clay_id("HDx")
if alt:
    import cv2 as _cv
    # the split (r2): the HALL from `raw` (r2, whose stone passed), the LIVING ROOM from the seed and, where the seed is missing
    # or dirty, from `alt` (fix1: same camera, same input, same lock, and it drew the whole room like base.png, the armchair and its
    # shadow included; r2 left the armchair out). The cut runs on the clay's living-room ids: hard at the walnut jamb and the
    # plaster arris (real edges), feathered (sigma 4 px) where the floor crosses the threshold (ids 30 / 25 / 10)
    a_ = np.asarray(Image.open(alt).convert("RGB")).astype(np.float64) / 255
    liv = np.isin(cls, tuple(range(30, 44)) + (0,)).astype(np.float32)
    soft = _cv.GaussianBlur(liv, (0, 0), 4.0)
    w = np.where(np.isin(cls, (30, 25, 10)), soft, liv)
    m = a_ * w[..., None] + m * (1 - w[..., None])
# the seed's reprojection is dirty at depth edges (a halo on the sofa back, stretched pixels under the armchair and the right
# table leg): around the furniture, where the seed disagrees strongly with the model (dE76 > 12, dilated 2 px), the model's
# pixel is used instead (it copied the products from the seed within ~1 px); everywhere else the seed is kept
from prep_d0o import lab_from_lin, to_lin
import cv2
dE = np.sqrt(((lab_from_lin(to_lin(m)) - lab_from_lin(to_lin(s))) ** 2).sum(-1))
near_furn = cv2.dilate(np.isin(cls, (41, 42, 43)).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
bad = near_furn & keep & (cv2.dilate((dE > 12).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
keep_used = keep & ~bad
res, alpha = T.paste_seed(m, s, keep_used, cls, tuple(range(30, 44)) + (0,), hard_ids=(41, 42, 43), hard_pad=30)
alpha = np.where(near_furn, cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), 1.0), alpha)
res = m * (1 - alpha[..., None]) + s * alpha[..., None]
K.save_rgb(out, res)
Y = K.lin_Y(np.asarray(Image.open(out).convert("RGB")))
Ym = K.lin_Y(np.asarray(Image.open(raw).convert("RGB")))
seam = T.seam_tone(Y, keep, cls, (30, 31, 32, 35, 36, 37, 38, 41, 42, 43))
model_vs_seed = T.seam_tone(np.where(keep, K.lin_Y(np.asarray(Image.open(seedp).convert('RGB'))), Ym), keep, cls, (30, 31, 32, 35, 36, 37, 41, 42, 43))
rep = dict(seed_artifact_px_replaced_by_model=int(bad.sum()), alpha_hard_px=int((alpha == 1).sum()), alpha_soft_px=int(((alpha > 0) & (alpha < 1)).sum()),
           seam_tone_after_paste=seam, seed_vs_model_across_the_paste_line_before_feather=model_vs_seed)
json.dump(rep, open(outj, "w"), indent=1)
print(json.dumps(rep, indent=1))
