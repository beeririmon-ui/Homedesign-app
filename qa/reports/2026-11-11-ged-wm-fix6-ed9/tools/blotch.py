"""
qa-agent 2026-11-11: colour blotches in the near-blacks the toe lifted (render-agent fixed purple / red specks under the master's
nightstand in a first version). For each pair (ed8 -> ed9, fix5 -> fix6), on the px the toe changed:
  - off-family colour after the lift: C* >= 3 with a hue outside the warm family (h < 20 or h > 110 deg: magenta, purple, red-pink,
    green, blue), grouped on a 3 px dilation; the components of >= 6 px with their box, size, mean Lab, and the same px before;
  - the same test on the before frame at the same px, for reference;
  - a local test that does not assume the family: the px's a*, b* against the median a*, b* of the dark px within 15 px (after);
    |delta ab| >= 5 with C* >= 3, components >= 6 px;
  - the void under the master's nightstand (render-agent's box x 990-1300, y 1230-1280) and the black bowl's body in ed9 (x 1380-1630,
    y 1000-1110): mean Lab, the hue spread (p5-p95) and the off-family count.
Usage: ~/.venvs/motion/bin/python -I blotch.py. Writes data/blotch.json and overlays/blotch-map-<frame>.jpg (the toe's px in grey,
the off-family components boxed in cyan, the local ones in magenta).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LR, MB, OUT, hue, lab, load, mean_lab, r  # noqa: E402

PAIRS = {"ed9": (os.path.join(LR, "warm-modern-A-ed8.png"), os.path.join(LR, "warm-modern-A-ed9.png")),
         "fix6": (os.path.join(MB, "warm-modern-MB-A-fix5.png"), os.path.join(MB, "warm-modern-MB-A-fix6.png"))}
BOXES = {"fix6": {"void under the nightstand": (990, 1230, 1300, 1280)},
         "ed9": {"black bowl body": (1380, 1000, 1630, 1110)}}


def comps(mask, minpx=6):
    n, lbl, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
    res = []
    for k in range(1, n):
        m = mask & (lbl == k)
        if m.sum() >= minpx:
            ys, xs = np.nonzero(m)
            res.append((m, [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
    return sorted(res, key=lambda t: -t[0].sum())


out = {}
for name, (pb, pa) in PAIRS.items():
    b, a = load(pb), load(pa)
    lb, la = lab(b), lab(a)
    ch = np.abs(a.astype(int) - b.astype(int)).max(2) > 0
    Ca, ha = np.hypot(la[..., 1], la[..., 2]), hue(la[..., 1], la[..., 2])
    Cb, hb = np.hypot(lb[..., 1], lb[..., 2]), hue(lb[..., 1], lb[..., 2])
    off_a = ch & (Ca >= 3) & ((ha < 20) | (ha > 110))
    off_b = ch & (Cb >= 3) & ((hb < 20) | (hb > 110))
    ca = comps(off_a)
    # local test
    dark = (la[..., 0] < 25).astype(np.float32)
    k = 31
    num_a = cv2.boxFilter(la[..., 1].astype(np.float32) * dark, -1, (k, k), normalize=False)
    num_b = cv2.boxFilter(la[..., 2].astype(np.float32) * dark, -1, (k, k), normalize=False)
    den = np.maximum(cv2.boxFilter(dark, -1, (k, k), normalize=False), 1)
    da = np.hypot(la[..., 1] - num_a / den, la[..., 2] - num_b / den)
    loc = ch & (Ca >= 3) & (da >= 5)
    cl = comps(loc)
    e = dict(toe_px=int(ch.sum()),
             off_family_after_px=int(off_a.sum()), off_family_before_same_test_px=int(off_b.sum()),
             off_family_after_components_ge6=len(ca),
             off_family_top=[dict(box=bx, px=int(m.sum()), after=mean_lab(la, m), before=mean_lab(lb, m)) for m, bx in ca[:12]],
             local_dev_after_px=int(loc.sum()), local_dev_components_ge6=len(cl),
             local_dev_top=[dict(box=bx, px=int(m.sum()), after=mean_lab(la, m), before=mean_lab(lb, m)) for m, bx in cl[:12]])
    for bn, (x0, y0, x1, y1) in BOXES[name].items():
        m = np.zeros(ch.shape, bool)
        m[y0:y1, x0:x1] = True
        md = m & (lb[..., 0] < 25)
        hh = ha[md & (Ca >= 1.5)]
        e[bn] = dict(before=mean_lab(lb, md), after=mean_lab(la, md), off_family_after_px=int((off_a & m).sum()),
                     local_dev_after_px=int((loc & m).sum()),
                     hue_p5_p50_p95_after_C_ge_1_5=[r(np.percentile(hh, q), 1) for q in (5, 50, 95)] if hh.size else None)
    out[name] = e
    # the map
    vis = (a.astype(np.float32) * 0.55).astype(np.uint8)
    vis[ch] = (np.array([150, 150, 150]) * 0.5 + vis[ch] * 0.5).astype(np.uint8)
    for m, (x0, y0, x1, y1) in ca[:40]:
        cv2.rectangle(vis, (x0 - 6, y0 - 6), (x1 + 6, y1 + 6), (0, 230, 255), 2)
    for m, (x0, y0, x1, y1) in cl[:40]:
        cv2.rectangle(vis, (x0 - 9, y0 - 9), (x1 + 9, y1 + 9), (255, 0, 220), 2)
    Image.fromarray(vis).resize((vis.shape[1] // 2, vis.shape[0] // 2), Image.LANCZOS).save(os.path.join(OUT, "overlays", f"blotch-map-{name}.jpg"), quality=88)
json.dump(out, open(os.path.join(OUT, "data", "blotch.json"), "w"), indent=1)
for name, e in out.items():
    print(name, {k: v for k, v in e.items() if not k.endswith("_top")})
    for t in e["off_family_top"][:8]:
        print("  off", t["box"], t["px"], "after", t["after"]["L"], t["after"]["C"], t["after"]["h"], "before", t["before"]["L"], t["before"]["C"], t["before"]["h"])
    for t in e["local_dev_top"][:8]:
        print("  loc", t["box"], t["px"], "after", t["after"]["L"], t["after"]["C"], t["after"]["h"], "before", t["before"]["L"], t["before"]["C"], t["before"]["h"])
