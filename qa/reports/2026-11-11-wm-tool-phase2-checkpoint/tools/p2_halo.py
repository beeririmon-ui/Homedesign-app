#!/usr/bin/env python3
"""
qa-agent 2026-11-11: seams and halos on every product edge of the r3 default scene (set B; the floor lamp and the cushions' neighbours
also on A and C). For each contour pixel of a layer (alpha >= 128 next to alpha < 128) the L* profile along the alpha gradient normal,
-8..+8 px: inside reference = median of +4..+8, outside reference = median of -8..-4, edge zone = -2..+2. A bright halo: the edge zone's
max exceeds max(inside, outside) by > T; a dark fringe: its min is below min(inside, outside) by > T; T = max(6, 2.5 x the local
texture std of the two references). Reported per layer: contour length, halo / fringe share, the longest connected run along the contour
(px), the worst excess, and where. Crops of the worst run at 100% and x4 go to crops/halo-<layer>-*.png.
Writes data/halo.json.   ~/.venvs/motion/bin/python -I p2_halo.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
prods = [l_["id"] for l_ in man["layers"] if "product" in l_]


def Lof(p):
    a = np.asarray(Image.open(p).convert("RGB"))
    return cv2.cvtColor(a.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0], a


def analyse(L, A, name, img, others):
    a = A.astype(np.float32) / 255
    g = cv2.GaussianBlur(a, (0, 0), 1.5)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    inside = A >= 128
    contour = inside & (cv2.dilate((~inside).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    # skip contour pixels that touch the canvas border or another layer drawn above this one (occlusion edges belong to the upper layer)
    contour[:3], contour[-3:], contour[:, :3], contour[:, -3:] = False, False, False, False
    contour &= ~others
    ys, xs = np.nonzero(contour)
    H, W = L.shape
    t = np.arange(-8, 9, dtype=np.float32)
    flags = np.zeros(len(ys), np.int8)
    exc = np.zeros(len(ys), np.float32)
    for i, (y, x) in enumerate(zip(ys, xs)):
        nx, ny = -gx[y, x], -gy[y, x]          # points into the product (alpha grows inward)
        n = np.hypot(nx, ny)
        if n < 1e-4:
            continue
        nx, ny = nx / n, ny / n
        px_ = np.clip(np.round(x + nx * t).astype(int), 0, W - 1)
        py_ = np.clip(np.round(y + ny * t).astype(int), 0, H - 1)
        prof = L[py_, px_]
        ins, out, edge = prof[12:], prof[:5], prof[6:11]
        ri, ro = np.median(ins), np.median(out)
        T = max(6.0, 2.5 * max(float(ins.std()), float(out.std())))
        hi, lo = edge.max() - max(ri, ro), min(ri, ro) - edge.min()
        if hi > T:
            flags[i], exc[i] = 1, hi
        elif lo > T:
            flags[i], exc[i] = -1, -lo
    rec = dict(contour_px=int(len(ys)), bright_halo_px=int((flags == 1).sum()), dark_fringe_px=int((flags == -1).sum()))
    rec["bright_share"] = round(rec["bright_halo_px"] / max(1, len(ys)), 4)
    rec["dark_share"] = round(rec["dark_fringe_px"] / max(1, len(ys)), 4)
    for kind, sgn in (("bright", 1), ("dark", -1)):
        m = np.zeros(L.shape, np.uint8)
        sel = flags == sgn
        m[ys[sel], xs[sel]] = 1
        if sel.any():
            n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), 8)
            j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            run_px = int((lab[ys[sel], xs[sel]] == j).sum())
            bx = st[j]
            rec[f"{kind}_longest_run_px"] = run_px
            rec[f"{kind}_longest_run_box"] = [int(bx[0]), int(bx[1]), int(bx[0] + bx[2]), int(bx[1] + bx[3])]
            rec[f"{kind}_worst_excess_L"] = round(float(np.abs(exc[sel]).max()), 1)
            rec[f"{kind}_p90_excess_L"] = round(float(np.percentile(np.abs(exc[sel]), 90)), 1)
            if run_px >= 8:
                x0, y0, x1, y1 = rec[f"{kind}_longest_run_box"]
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                b = (max(0, cx - 40), max(0, cy - 40), min(W, cx + 40), min(H, cy + 40))
                c = Image.fromarray(img[b[1]:b[3], b[0]:b[2]])
                c.resize((c.width * 4, c.height * 4), Image.NEAREST).save(os.path.join(OUT, "crops", f"halo-{name}-{kind}-x4.png"))
    return rec


res = {}
for s in ("B", "A", "C"):
    L, img = Lof(os.path.join(P2, f"graded/default-scene-r3-set-{s}-graded-v3c.png"))
    alphas = {k: np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3] for k in prods}
    alphas["cushions"] = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])))[..., 3]
    zs = {k: byid[k]["z"] for k in prods}
    zs["cushions"] = 55
    order = man["compose"]["order"]
    pos = {k: order.index(k) for k in alphas}
    names = prods + ["cushions"] if s == "B" else ["floor-lamp", "cushions", "bowl", "candle-holders"]
    for k in names:
        above = np.zeros(L.shape, bool)
        for o in alphas:
            if o != k and pos[o] > pos[k]:
                above |= cv2.dilate((alphas[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{k} [set {s}]"] = analyse(L, alphas[k], f"{k}-{s}", img, above)
        print(k, s, res[f"{k} [set {s}]"])
json.dump(res, open(os.path.join(OUT, "data/halo.json"), "w"), indent=1)
