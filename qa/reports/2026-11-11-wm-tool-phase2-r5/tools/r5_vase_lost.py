#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): how much of the vase the model drew in 4' is in the default vase layer. The registered raw 4' render against
base.png (what is behind the vase: window, rail, bench), smoothed |dE| > 6 -> the model's vase (+ its contact shadow), the component
that holds the layer's alpha core; per body row (4 px under the rim to row 1008, above the window rail; the mullion right of x 735 left out) the left / right edge of that mask against the layer's
alpha (> 0.5). Also vase v2 (5') the same way. Writes data/vase-lost.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")
m5 = json.load(open(os.path.join(P2, "layers/manifest-r5.json")))
b5 = {l_["id"]: l_ for l_ in m5["layers"]}
vf = {v["id"]: v["file"] for vs in m5["variants"].values() for v in vs}
J = {j["pass_"]: j for j in json.load(open(os.path.join(P2, "jobs-r5.json")))["jobs"]}
base = np.asarray(Image.open(os.path.join(P2, "layers/base.png")).convert("RGB")).astype(np.float32)
lab = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)  # noqa: E731
res = {}
for name, p, f, rim in (("vase r5", "4'", b5["vase"]["file"], 936), ("vase-v2", "5'", vf["vase-v2"], 942)):
    j = J[p]
    M = np.array(j["register_to_input"], np.float32)
    r = np.asarray(Image.open(os.path.join(REPO, j["raw"])).convert("RGB")).astype(np.float32)
    r = cv2.warpAffine(r, M, (r.shape[1], r.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    a = np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3].astype(np.float32) / 255
    y0, y1, x0, x1 = 850, 1080, 590, 760
    rr, bb = r[y0:y1, x0:x1], base[y0:y1, x0:x1]
    ring = np.ones(rr.shape[:2], bool)
    ring[:, 20:-20] = False
    g = np.array([np.median(bb[..., c][ring]) / max(np.median(rr[..., c][ring]), 1) for c in range(3)], np.float32)
    dE = np.linalg.norm(lab(rr * g) - lab(bb), axis=2)
    dE = cv2.GaussianBlur(dE, (0, 0), 1.2)
    m = (dE > 6).astype(np.uint8)
    n, labm, st, _ = cv2.connectedComponentsWithStats(m, 8)
    core = a[y0:y1, x0:x1] > 0.99
    ids = [i for i in range(1, n) if (core & (labm == i)).sum() > 500]
    vm = np.isin(labm, ids)
    rows = []
    yb = int(np.nonzero((a > 0.5).any(1))[0].max())
    for y in range(rim + 4, 1008):                      # the body above the window rail (~1012), the mullion (x > 735) out
        ry = y - y0
        xs_r = np.nonzero(vm[ry, :735 - x0])[0]
        xs_a = np.nonzero(a[y, x0:x1] > 0.5)[0]
        if len(xs_r) and len(xs_a):
            rows.append([y, int(xs_r.min() - xs_a.min()), int(xs_r.max() - xs_a.max()), int(len(xs_r)), int(xs_a.max() - xs_a.min() + 1),
                         int(xs_r.max() - xs_r.min() + 1)])
    R = np.array(rows)
    res[name] = dict(gain=[round(float(v), 3) for v in g], rows=len(rows),
                     left_edge_raw_minus_alpha_px=dict(median=float(np.median(R[:, 1])), min=int(R[:, 1].min()), rows_le_minus3=int((R[:, 1] <= -3).sum())),
                     right_edge_raw_minus_alpha_px=dict(median=float(np.median(R[:, 2])), max=int(R[:, 2].max()), rows_ge_3=int((R[:, 2] >= 3).sum())),
                     width_raw_px_median=float(np.median(R[:, 5])), width_alpha_px_median=float(np.median(R[:, 4])),
                     widest_raw_px=int(R[:, 5].max()), widest_alpha_px=int(R[:, 4].max()))
    Image.fromarray((vm * 255).astype(np.uint8)).resize((vm.shape[1] * 2, vm.shape[0] * 2), Image.NEAREST).save(os.path.join(OUT, "crops", f"{name.replace(' ', '-')}-raw-mask-x2.png"))
    print(name, res[name])
json.dump(res, open(os.path.join(OUT, "data/vase-lost.json"), "w"), indent=1)
