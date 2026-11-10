#!/usr/bin/env python3
"""
alt_fold.py: qa-agent, 2026-11-10. Simulates render-agent's alternative for the shadow-band residual:
fold the pixels a multiply cannot brighten into the product layer's alpha (shadow stays as is), then measures
what it buys (the recomposite error) and what it costs (alpha pixels outside the product silhouette).

For each residual pixel in the shadow band (layer alpha 0, recomposite != approved): the smallest integer alpha a in 1..255
and an RGB L in 0..255 such that BOTH the straight-exact path (P1) and the browser premultiplied path (P4) give the approved
pixel within 1 level per channel; a is taken as small as possible. Nothing is written to the layer files; the folded layer is
built in memory only.
Usage: python3 alt_fold.py <out_json>
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_recomposite as q  # noqa: E402

B = np.asarray(Image.open(os.path.join(q.LAYERS, "base.png"))).astype(np.int64)
res = {}
for s in q.SETS:
    LA = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}.png"))).copy()
    S = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}-shadow.png"))).astype(np.int64)
    T = np.asarray(Image.open(os.path.join(q.PILOT, f"composite-set-{s}-v3-graded-v3c.png"))).astype(np.int64)
    A = LA[..., 3].astype(np.int64)
    L = LA[..., :3].astype(np.int64)
    o1 = q.p1(B, S, L, A).astype(np.int64)
    band = (A == 0) & (S < 255).any(2)
    todo = band & (o1 != T).any(2)
    ys, xs = np.nonzero(todo)
    newA = A.copy()
    newL = L.copy()
    chosen = []
    for y, x in zip(ys, xs):
        b, sh, t = B[y, x], S[y, x], T[y, x]
        for a in range(1, 256):
            # solve L per channel for the exact path, then check both paths
            num = t * 65025 - b * sh * (255 - a)
            Lc = np.clip(np.round(num / (255.0 * a)), 0, 255).astype(np.int64)
            ok = True
            for path in (q.p1, q.p4):
                out = path(b[None, None], sh[None, None], Lc[None, None], np.array([[a]]))[0, 0].astype(np.int64)
                if np.abs(out - t).max() > 1:
                    ok = False
                    break
            if ok:
                newA[y, x] = a
                newL[y, x] = Lc
                chosen.append(a)
                break
    chosen = np.array(chosen)
    r = dict(residual_band_px=int(todo.sum()), folded_px=int(len(chosen)),
             alpha_levels=dict(min=int(chosen.min()), median=float(np.median(chosen)), max=int(chosen.max()),
                               hist={int(k): int(v) for k, v in zip(*np.unique(chosen, return_counts=True))}))
    for name, path in (("P1", q.p1), ("P4", q.p4)):
        before = np.abs(path(B, S, L, A).astype(np.int64) - T).max(2)
        after = np.abs(path(B, S, newL, newA).astype(np.int64) - T).max(2)
        r[f"{name}_max_before"], r[f"{name}_max_after"] = int(before.max()), int(after.max())
        r[f"{name}_px_ge3_before"], r[f"{name}_px_ge3_after"] = int((before >= 3).sum()), int((after >= 3).sum())
    # cost: where are the new alpha pixels relative to the product silhouette (original alpha > 0)?
    sil = (A > 0).astype(np.uint8)
    dist = cv2.distanceTransform((1 - sil).astype(np.uint8), cv2.DIST_L2, 5)
    dd = dist[todo]
    r["new_alpha_px_distance_from_silhouette_px"] = dict(min=round(float(dd.min()), 1), median=round(float(np.median(dd)), 1),
                                                         p90=round(float(np.percentile(dd, 90)), 1), max=round(float(dd.max()), 1),
                                                         farther_than_2px=int((dd > 2).sum()), farther_than_8px=int((dd > 8).sum()))
    # new islands: connected components of the folded alpha that do not touch the original silhouette
    n, lab = cv2.connectedComponents((newA > 0).astype(np.uint8), connectivity=8)
    touching = set(np.unique(lab[A > 0]).tolist())
    islands = [k for k in range(1, n) if k not in touching]
    r["new_alpha_islands"] = dict(n=len(islands), px=int(np.isin(lab, islands).sum()) if islands else 0)
    ys2, xs2 = np.nonzero(A > 0)
    ys3, xs3 = np.nonzero(newA > 0)
    r["alpha_bbox_before"] = [int(xs2.min()), int(ys2.min()), int(xs2.max()), int(ys2.max())]
    r["alpha_bbox_after"] = [int(xs3.min()), int(ys3.min()), int(xs3.max()), int(ys3.max())]
    # what the folded pixels carry: their colour is the approved shadow-band colour (sofa plinth / floor), not the product
    lab_new = q.srgb_to_lab(newL[todo].astype(np.uint8))
    r["folded_rgb_Lstar"] = [round(float(x), 1) for x in np.percentile(lab_new[:, 0], [0, 50, 100])]
    res[s] = r
    print(s, json.dumps(r))
json.dump(res, open(sys.argv[1], "w"), indent=1)
