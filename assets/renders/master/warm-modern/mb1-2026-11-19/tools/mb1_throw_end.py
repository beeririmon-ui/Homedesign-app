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
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
RAW = "raw/p5-throw-end.png"
INP = "inputs/p5-throw-end-input.png"
MASK = "inputs/p5-throw-end-mask.png"                    # the placeholder, as sent (the throw layer of the time)
BOX = (1262, 935, 1600, 1280)
KEEP = 14
FOLD = 0.4                                               # the folds' slope on the side drop (x per y down, r1: down and to the right)
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
    # the hem: where the woven body ends and the fringe starts, traced on r1 locked (the fringe's threads are as dense as the body
    # under any colour rule): a straight line HEM_R1, the threads hang from it
    (hx0, hy0), (hx1, hy1) = HEM_R1
    xs = np.arange(hx0 - 14, 1513)
    yb = np.full(W, -1.0)
    yb[xs] = hy0 + (xs - hx0) * (hy1 - hy0) / (hx1 - hx0)
    rows = np.arange(H)[:, None]
    # the fringe zone: from KEEP px below the hem to its tips (hem + 84), over the fringe's columns
    zx = np.arange(1320, 1513)
    top = np.full(W, H + 1.0)
    top[zx] = yb[zx] + KEEP
    zone = np.zeros((H, W), bool)
    zone[:, zx] = (rows >= top[zx][None, :]) & (rows < top[zx][None, :] + ZH)
    # the fill: the duvet just below the zone, reflected up about the zone's bottom edge along the side drop's folds (they run down
    # and to the right, FOLD px per px): a zone pixel d px above that edge takes the pixel 2d px further down the same fold, so the folds
    # run on through the edge without a seam and without a chevron; at the zone's left and right edges a 10 px cross-fade into r1
    bot = np.full(W, -1.0)
    bot[zx] = top[zx] + ZH
    yy = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    dd = np.clip(bot[None, :].astype(np.float32) - yy, 0, None)
    my = yy + 2 * dd
    mx = np.arange(W, dtype=np.float32)[None, :] + np.float32(FOLD) * 2 * dd
    refl = cv2.remap(e5.astype(np.float32), mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT).astype(np.float64)
    xx = np.arange(W)
    side = np.minimum(np.abs(xx[None, :] - zx[0]), np.abs(xx[None, :] - zx[-1])).astype(np.float64)
    fill = np.where(zone[..., None], refl, e5)
    dy = (rows - top[None, :]).astype(np.float64)
    shade = np.where(zone, 1 - 0.14 * np.exp(-np.clip(dy, 0, None) / 6.0), 1.0)     # only in the zone, under the kept fringe
    fill = C.srgb(np.clip(C.lin(fill) * shade[..., None], 0, 1))
    wz = np.clip(C.blur(C.dil(zone, 3).astype(np.float64), 3.0) * 1.2, 0, 1) * C.dil(zone, 8)
    wz = wz * np.clip((side + 2) / 10.0, 0, 1) ** 0.7
    e5 = e5 * (1 - wz[..., None]) + fill * wz[..., None]
    threads = zone
    inp = C.load(os.path.join(ST, INP))
    d = np.linalg.norm(C.blur(C.to_lab(e5), 1.0) - C.blur(C.to_lab(inp), 1.0), axis=-1)
    take = (C.dil((d > 4) & box, 6) | C.dil(np.asarray(Image.open(os.path.join(ST, MASK))) > 127, 6)) & C.ero(box, 6)
    take = cv2.morphologyEx(take.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(6)).astype(bool)
    w = C.blur((take & C.ero(box, 10)).astype(np.float64), 3.0)          # feathered inside the box: no hard edge at its sides
    out = e * (1 - w[..., None]) + e5 * w[..., None]
    hem = [(int(x), round(float(yb[x]), 1)) for x in xs[::40]]
    rec["throw_end"] = dict(raw=RAW, try_used="r1 (r2 lengthened the throw, twisted tassels)", lock=rl, gain_ring_px=ring_px, fold_slope=FOLD, fill="reflected up along the folds about the zone's bottom edge; contact shade 14 % over 6 px; 10 px side cross-fade",
                            hem_samples=hem, fringe_kept_px=KEEP, fringe_zone_px=int(threads.sum()), patch_px=int((w > 0.5).sum()),
                            rule="the p1 edit inside the box replaced by r1 where r1 changed its input or the placeholder was (3 px feather inside the box)")
    return out


if __name__ == "__main__":
    e = np.load(sys.argv[1]).astype(np.float64)
    rec = {}
    out = patch(e, rec)
    print(json.dumps({k: v for k, v in rec["throw_end"].items() if k != "lock"}))
    S = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/mb1/crops/"
    a = Image.fromarray(C.q(out[880:1300, 1180:1640])).resize((644, 588), Image.LANCZOS)
    a.save(S + "p5-patched.png")
