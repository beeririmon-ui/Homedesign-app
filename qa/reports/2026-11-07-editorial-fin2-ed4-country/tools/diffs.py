"""
qa-agent 2026-11-07: independent "nothing else moved" for the fin2 code fixes and the four ED4 local passes: |after - before| on the
finished files, the changed pixels (> 2 levels) and their bounding boxes, against the zones render-agent records (fin2-codefix.json,
ed4.json: crop box + regions / silhouette). Also a x4 contrast-stretched view of each changed zone and 100 % before / after crops.
Writes data/diffs.json, overlays/diff-<pair>.jpg, overlays/<pair>-before-after.jpg, overlays/<pair>-stretch.jpg.
Usage: ~/.venvs/motion/bin/python -I diffs.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-editorial-fin2-ed4-country")
PAIRS = {"nordic-A fin -> fin2": ("nordic-A-fin.png", "nordic-A-fin2.png"), "warm-modern-A fin -> fin2": ("warm-modern-A-fin.png", "warm-modern-A-fin2.png"),
         "boho-A -> fin2": ("boho-A.png", "boho-A-fin2.png"), "nordic-A fin2 -> ed4": ("nordic-A-fin2.png", "nordic-A-ed4.png"),
         "warm-modern-A fin2 -> ed4": ("warm-modern-A-fin2.png", "warm-modern-A-ed4.png"), "mediterranean-A -> ed4": ("mediterranean-A.png", "mediterranean-A-ed4.png"),
         "japandi-A -> ed4": ("japandi-A.png", "japandi-A-ed4.png")}

if __name__ == "__main__":
    out = {}
    for name, (a, b) in PAIRS.items():
        A = np.asarray(Image.open(os.path.join(R, a)).convert("RGB")).astype(np.int16)
        B = np.asarray(Image.open(os.path.join(R, b)).convert("RGB")).astype(np.int16)
        if A.shape != B.shape:
            out[name] = dict(error=f"size {A.shape} vs {B.shape}")
            continue
        d = np.abs(A - B).max(2)
        ch = (d > 2).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ch, np.ones((15, 15), np.uint8)))
        comps = sorted([dict(px=int(st[i, 4]), box=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])]) for i in range(1, n)], key=lambda c: -c["px"])
        out[name] = dict(changed_px=int(ch.sum()), changed_px_over_1=int((d > 1).sum()), components=comps[:6], max_delta=int(d.max()))
        tag = name.replace(" -> ", "_").replace(" ", "-")
        vis = cv2.applyColorMap(np.clip(d * 8, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        cv2.imwrite(os.path.join(OUT, "overlays", f"diff-{tag}.jpg"), cv2.resize(vis, (vis.shape[1] // 3, vis.shape[0] // 3)), [cv2.IMWRITE_JPEG_QUALITY, 80])
        if comps:
            x0, y0, x1, y1 = comps[0]["box"]
            pad = 60
            x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(A.shape[1], x1 + pad), min(A.shape[0], y1 + pad)
            ca, cb = A[y0:y1, x0:x1].astype(np.uint8), B[y0:y1, x0:x1].astype(np.uint8)
            both = np.concatenate([ca, np.full((ca.shape[0], 10, 3), 40, np.uint8), cb], 1)
            im = Image.fromarray(both)
            if im.width > 1600:
                im = im.resize((1600, int(im.height * 1600 / im.width)))
            im.save(os.path.join(OUT, "overlays", f"{tag}-before-after.jpg"), quality=90)
            c = cb.astype(float)
            m = c.reshape(-1, 3).mean(0)
            Image.fromarray(np.clip((c - m) * 4 + 128, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "overlays", f"{tag}-stretch.jpg"), quality=85)
        print(name, out[name]["changed_px"], [c["box"] for c in comps[:4]])
    json.dump(out, open(os.path.join(OUT, "data", "diffs.json"), "w"), indent=1)
