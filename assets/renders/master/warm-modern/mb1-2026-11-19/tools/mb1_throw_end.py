#!/usr/bin/env python3
"""
mb1_throw_end.py: M1 (QA 2026-11-19, the manager's ruling): the Pecan's near-right end, from the one approved mask edit, into the p1 edit
before the p1 cut (render-agent, 2026-11-19). Two tries were sent (800 tokens): r1 (raw/p5-throw-end.png) ends the throw about 13 cm
down the bed's side with a long loose-thread fringe (12-15 cm); r2 lengthened the throw again (about 23 cm) with twisted tassels. r1 is
used, and its fringe is trimmed in code to 2.3 cm (14 px at 5.8-6.6 px/cm): the threads below that are inpainted from the duvet drop the
edit drew round them.
Steps: lock r1 onto its input (inputs/p5-throw-end-input.png, the p1 edit with the placeholder); its gain to the p1 edit on a ring round
the patch box (MP-I1); the hem traced on r1 (HEM_R1); the fringe below KEEP px refilled with the duvet drop under it moved up (ZH px), its low frequencies matched to the duvet round it, a soft contact shadow under the kept fringe; into the p1 edit where r1 changed its input or
the placeholder was, feathered 4 px, inside the box only.
  used by mb1_compose.py (cut_pass p1-bed); alone: python3 mb1_throw_end.py <p1-locked.npy>  (writes a check crop to the scratchpad)
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402
import mb1_throw_end_prep as TP  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
RAW = "raw/p5-throw-end.png"
INP = "inputs/p5-throw-end-input.png"
BOX = (1262, 935, 1600, 1280)
KEEP = 14
ZH = 70                                                  # the fringe zone's height (to the tips, hem + 84)
HEM_R1 = ((1330, 1086), (1490, 1032))                 # r1's hem (canvas px, after the lock)
ARCH = (1, 2, 5, 9, 10, 12, 13, 14, 20, 21, 23, 24, 25, 28, 29, 30)


def patch(e, rec):
    pl_ids = M.ids("MB1-plate")
    box = C.box_mask([BOX])
    stable = C.ero(np.isin(pl_ids, ARCH), 3) & ~C.dil(box, 60)
    stable[1450:] = False
    e5, rl = M.ecc_lock(os.path.join(ST, RAW), os.path.join(ST, INP), stable)
    ring = C.dil(box, 80) & ~C.dil(box, 20)
    g = C.gain_field(e5, e, ring)
    ring_px = int(ring.sum())
    e5 = C.srgb(np.clip(C.lin(e5) * g, 0, 1))
    lab = C.to_lab(e5)
    Ch = np.hypot(lab[..., 1], lab[..., 2])
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    rust = (Ch > 10) & (hh > 30) & (hh < 65) & (lab[..., 0] < 62) & box
    # the hem: where the woven body ends and the fringe starts, traced on r1 locked (the fringe's threads are as dense as the body
    # under any colour rule): a straight line HEM_R1, the threads hang from it
    (hx0, hy0), (hx1, hy1) = HEM_R1
    xs = np.arange(hx0 - 12, hx1 + 8)
    yb = np.full(W, -1.0)
    yb[xs] = hy0 + (xs - hx0) * (hy1 - hy0) / (hx1 - hx0)
    rows = np.arange(H)[:, None]
    # the fringe zone: from KEEP px below the hem to its tips (hem + 84), over the fringe's columns. It is refilled with the duvet drop
    # right below it, moved up by the zone's height (the side drop's folds run down the bed, so they stay continuous), its low
    # frequencies (sigma 8) set to r1's own duvet light between the threads and round the zone, feathered 3 px; then a soft contact shadow under the kept 2.3 cm
    zx = np.arange(1320, 1507)
    top = np.full(W, H + 1.0)
    top[zx] = yb[zx] + KEEP
    zone = np.zeros((H, W), bool)
    zone[:, zx] = (rows >= top[zx][None, :]) & (rows < top[zx][None, :] + ZH)
    src = np.zeros_like(e5)
    src[:H - ZH] = e5[ZH:]
    clone = np.where(zone[..., None], src, e5)
    hh_ = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    rust_any = (Ch > 10) & (hh_ > 30) & (hh_ < 65) & (lab[..., 0] < 62)
    xx = np.arange(W)
    hem_all = hy0 + (xx - hx0) * (hy1 - hy0) / (hx1 - hx0)              # the hem line extended: the duvet is below it
    lring = C.dil(zone, 24) & ~C.dil(zone, 1) & ~C.dil(rust_any, 5) & (rows > hem_all[None, :] + KEEP + 6) & box

    def nb(img, w, sg=18):
        num = np.stack([C.blur(img[..., c] * w, sg) for c in range(3)], -1)
        return num / np.maximum(C.blur(w.astype(np.float64), sg), 1e-4)[..., None]
    between = zone & ~C.dil(rust_any, 2)                    # the duvet r1 shows between the threads: its light (the throw's soft cast
    lf_t = nb(C.lin(e5), (between | lring).astype(np.float64), 8)      # shadow included) is kept; the clone gives only the weave
    lf_c = nb(C.lin(clone), zone.astype(np.float64), 8)
    fill = C.srgb(np.clip(C.lin(clone) * lf_t / np.maximum(lf_c, 1e-4), 0, 1))
    dy = (rows - top[None, :]).astype(np.float64)
    shade = 1 - 0.10 * np.exp(-np.clip(dy, 0, None) / 5.0)
    fill = C.srgb(np.clip(C.lin(fill) * shade[..., None], 0, 1))
    wz = np.clip(C.blur(C.dil(zone, 2).astype(np.float64), 3.0) * 1.15, 0, 1) * C.dil(zone, 8)
    e5 = e5 * (1 - wz[..., None]) + fill * wz[..., None]
    threads = zone
    lfring_px = lring.sum()
    inp = C.load(os.path.join(ST, INP))
    d = np.linalg.norm(C.blur(C.to_lab(e5), 1.0) - C.blur(C.to_lab(inp), 1.0), axis=-1)
    take = (C.dil((d > 4) & box, 6) | C.dil(TP.placeholder_mask(), 6)) & C.ero(box, 6)
    take = cv2.morphologyEx(take.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(6)).astype(bool)
    w = C.blur(take.astype(np.float64), 2.0) * C.ero(box, 2)
    out = e * (1 - w[..., None]) + e5 * w[..., None]
    hem = [(int(x), round(float(yb[x]), 1)) for x in xs[::40]]
    rec["throw_end"] = dict(raw=RAW, try_used="r1 (r2 lengthened the throw, twisted tassels)", lock=rl, gain_ring_px=ring_px, lf_ring_px=int(lfring_px),
                            hem_samples=hem, fringe_kept_px=KEEP, fringe_zone_px=int(threads.sum()), patch_px=int((w > 0.5).sum()),
                            rule="the p1 edit inside the box replaced by r1 where r1 changed its input or the placeholder was (4 px feather)")
    return out


if __name__ == "__main__":
    e = np.load(sys.argv[1]).astype(np.float64)
    rec = {}
    out = patch(e, rec)
    print(json.dumps({k: v for k, v in rec["throw_end"].items() if k != "lock"}))
    from PIL import Image
    S = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/mb1/crops/"
    a = Image.fromarray(C.q(out[880:1300, 1180:1640])).resize((644, 588), Image.LANCZOS)
    a.save(S + "p5-patched.png")
