"""
qa-agent 2026-11-07: G-ED.8 for codefix5, grade-boho and med-cushions. |after - before| on the finished files (> 2 levels on any channel),
connected components on a 15 px dilation, and each component's box against the zones render-agent records
(codefix3.json, codefix4.json, mc1.json / mc1_regions.json and the saved masks in raw/). Writes data/diffs.json,
overlays/diff-<tag>.jpg (the |d| map, 1/3 size). Usage: ~/.venvs/motion/bin/python -I diffs.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix5-clay-r3")
# tag: (before, after, recorded zones as boxes [x0, y0, x1, y1] or a mask file in raw/)
PAIRS = {
    "boho fin4-fin5": ("boho-A-fin4.png", "boho-A-fin5.png", None),
    "boho fin5-fin6 (grade)": ("boho-A-fin5.png", "boho-A-fin6.png", None),
    "med ed5-ed6": ("mediterranean-A-ed5.png", "mediterranean-A-ed6.png", [[201, 706, 610, 1020], [918, 719, 1231, 974]]),
    "mc mc1-fix3": ("modern-country-A-mc1.png", "modern-country-A-fix3.png", None),
}


def load(p):
    return np.asarray(Image.open(os.path.join(R, p)).convert("RGB")).astype(np.int16)


if __name__ == "__main__":
    out = {}
    for tag, (a, b, zones) in PAIRS.items():
        A, B = load(a), load(b)
        if A.shape != B.shape:
            out[tag] = dict(error=f"size {A.shape} vs {B.shape}")
            continue
        d = np.abs(A - B).max(2)
        ch = d > 2
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ch.astype(np.uint8), np.ones((15, 15), np.uint8)))
        comps = []
        for i in range(1, n):
            sel = (lab == i) & ch
            comps.append(dict(px=int(sel.sum()), box=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + st[i, 2]), int(st[i, 1] + st[i, 3])],
                              max_delta=int(d[sel].max()) if sel.any() else 0))
        comps.sort(key=lambda c: -c["px"])
        rec = dict(before=a, after=b, changed_px=int(ch.sum()), max_delta=int(d.max()), components=comps[:12], n_components=len(comps))
        if isinstance(zones, str):
            m = np.asarray(Image.open(os.path.join(R, zones)).convert("L")) > 0
            if m.shape == ch.shape:
                rec["mask_file"] = zones
                rec["mask_px"] = int(m.sum())
                rec["changed_outside_mask_px"] = int((ch & ~m).sum())
                mm = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
                rec["changed_outside_mask_grown2_px"] = int((ch & ~mm).sum())
            else:
                rec["mask_file"] = f"{zones} (size {m.shape}, not comparable)"
        elif zones:
            z = np.zeros(ch.shape, bool)
            for x0, y0, x1, y1 in zones:
                z[y0:y1, x0:x1] = True
            rec["zones"] = zones
            rec["changed_outside_zones_px"] = int((ch & ~z).sum())
        out[tag] = rec
        vis = cv2.applyColorMap(np.clip(d * 8, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        cv2.imwrite(os.path.join(OUT, "overlays", f"diff-{tag.replace(' ', '_')}.jpg"), cv2.resize(vis, (vis.shape[1] // 3, vis.shape[0] // 3)), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(tag, rec["changed_px"], rec.get("changed_outside_zones_px", rec.get("changed_outside_mask_px", "-")), rec.get("changed_outside_mask_grown2_px", ""),
              [(c["box"], c["px"]) for c in comps[:6]])
    json.dump(out, open(os.path.join(OUT, "data", "diffs.json"), "w"), indent=1)
