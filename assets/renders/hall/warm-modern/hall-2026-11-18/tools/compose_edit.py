#!/usr/bin/env python3
"""
compose_edit.py: a mask edit composed back onto its approved still (HT2 on ht.png, HDx2 on hdx.png), render-agent 2026-11-18. 0 tokens.
  - the model's picture is resampled to the canvas; its global shift against the input is measured outside the mask (reported; it is
    only corrected when it is over 0.5 px)
  - inside the mask the model's pixels, on an alpha that is 1 on the core (the object and its shadow, grown by `grow` px) and falls to 0
    by a smoothstep over `band` px, all inside the 12 px mask; outside the mask the approved still byte for byte (route 12.0: 0 levels)
  python3 compose_edit.py <approved.png> <input.png> <mask.png> <core.png> <model.png> <out.png> <report.json> [grow band]
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402


def compose(approved, inp, maskp, corep, model, out, rep_path, grow=4, band=7):
    a8 = K.rgb8(approved)
    h, w = a8.shape[:2]
    i8 = K.rgb8(inp)
    m8 = K.rgb8(model)
    rep = dict(model_px=[int(m8.shape[1]), int(m8.shape[0])], canvas_px=[w, h])
    r8 = K.resample_to(m8, w, h)
    mask = K.rgb8(maskp)[..., 0] > 127
    core = K.rgb8(corep)[..., 0] > 127
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((161, 161), np.uint8)) > 0
    ring &= ~mask
    dx, dy, resp = K.shift_vs(i8.astype(np.float32) / 255, r8.astype(np.float32) / 255, ring.astype(np.float32))
    rep["shift_vs_input_outside_mask_px"] = dict(dx=round(dx, 2), dy=round(dy, 2), response=round(resp, 3), window="160 px around the mask")
    if abs(dx) > 0.5 or abs(dy) > 0.5:
        M = np.array([[1, 0, -dx], [0, 1, -dy]], np.float32)
        r8 = cv2.warpAffine(r8, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        rep["shift_corrected"] = True
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))
    c2 = cv2.dilate(core.astype(np.uint8), k) > 0
    al = K.feather_alpha(c2, band) * mask
    rl, al_ = K.to_lin(r8 / 255.0), al[..., None]
    res = K.to_srgb(K.to_lin(a8 / 255.0) * (1 - al_) + rl * al_)
    o8 = np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)
    o8[al <= 0] = a8[al <= 0]
    K.save(out, o8)
    chk = K.rgb8(out).astype(int)
    rep["outside_mask_max_diff_levels"] = int(np.abs(chk - a8.astype(int))[~mask].max())
    rep["alpha"] = dict(core_grow_px=grow, band_px=band, px_alpha_1=int((al >= 0.999).sum()), px_changed=int((al > 0).sum()))
    # how far the model moved what it was told to keep, inside the mask but off the core (the ring the alpha fades over)
    ringm = mask & ~c2
    if ringm.any():
        d = np.abs(K.to_lin(r8 / 255.0) @ K.W709 - K.to_lin(a8 / 255.0) @ K.W709)[ringm] / np.maximum(K.to_lin(a8 / 255.0) @ K.W709, 1e-3)[ringm]
        rep["mask_ring_rel_diff_median_pct"] = round(float(np.median(d)) * 100, 2)
    K.save(out.replace(".png", "-raw-on-canvas.png"), r8)
    K.dump(rep_path, rep)
    return rep


if __name__ == "__main__":
    a = sys.argv[1:]
    g, b = (int(a[7]), int(a[8])) if len(a) > 8 else (4, 7)
    print(compose(*a[:7], grow=g, band=b))
