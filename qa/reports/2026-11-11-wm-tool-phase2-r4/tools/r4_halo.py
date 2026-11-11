#!/usr/bin/env python3
"""
qa-agent 2026-11-11: seams and halos on the five R4 products, r3 against r4 (set B), with the checkpoint's metric (the same analyse() as
qa/reports/2026-11-11-wm-tool-phase2-checkpoint/tools/p2_halo.py, copied here unchanged): for each contour pixel (alpha >= 128 next to
alpha < 128) the L* profile along the alpha normal, -8..+8 px; a bright halo when the edge zone (-2..+2) exceeds max(inside, outside) by
more than T = max(6, 2.5 x the local texture std); a dark fringe when it falls below min(inside, outside) by more than T; the longest
connected run along the contour.
For the basket and the planter the same metric also runs on the raw R3a render (registered here with the pass's recorded matrix, the
residual shift re-measured, gain-matched), WITH THE R4 ALPHA, so a run that is in the raw is the model's own drawing, not the cut.
Also per product: the run restricted to the fix's own box (the basket's right edge, the planter's left side and bottom, the canopy, the
vase's right flank on the bench).
Writes data/halo.json and crops/halo-<product>-r4-<kind>-x4.png.   ~/.venvs/motion/bin/python -I r4_halo.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
m3 = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
FIVE = ["floor-lamp", "vase", "planter", "basket", "pendant"]
BOX = {"basket": (1110, 1010, 1175, 1280), "planter": (925, 1025, 1012, 1215), "pendant": (1630, 0, 1740, 70),
       "vase": (676, 1000, 740, 1090), "floor-lamp": (2300, 570, 2560, 712)}


def Lof(img):
    return cv2.cvtColor(img.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]


def analyse(L, A, name, img, others, box=None, save=True):
    a = A.astype(np.float32) / 255
    g = cv2.GaussianBlur(a, (0, 0), 1.5)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    inside = A >= 128
    contour = inside & (cv2.dilate((~inside).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    contour[:3], contour[-3:], contour[:, :3], contour[:, -3:] = False, False, False, False
    contour &= ~others
    if box is not None:
        bm = np.zeros(contour.shape, bool)
        bm[box[1]:box[3], box[0]:box[2]] = True
        contour &= bm
    ys, xs = np.nonzero(contour)
    H, W = L.shape
    t = np.arange(-8, 9, dtype=np.float32)
    flags = np.zeros(len(ys), np.int8)
    exc = np.zeros(len(ys), np.float32)
    for i, (y, x) in enumerate(zip(ys, xs)):
        nx, ny = -gx[y, x], -gy[y, x]
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
    for kind, sgn in (("bright", 1), ("dark", -1)):
        m = np.zeros(L.shape, np.uint8)
        sel = flags == sgn
        m[ys[sel], xs[sel]] = 1
        rec[f"{kind}_longest_run_px"] = 0
        if sel.any():
            n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), 8)
            j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            run_px = int((lab[ys[sel], xs[sel]] == j).sum())
            bx = st[j]
            rec[f"{kind}_longest_run_px"] = run_px
            rec[f"{kind}_longest_run_box"] = [int(bx[0]), int(bx[1]), int(bx[0] + bx[2]), int(bx[1] + bx[3])]
            rec[f"{kind}_worst_excess_L"] = round(float(np.abs(exc[sel]).max()), 1)
            rec[f"{kind}_p90_excess_L"] = round(float(np.percentile(np.abs(exc[sel]), 90)), 1)
            if save and run_px >= 8:
                x0, y0, x1, y1 = rec[f"{kind}_longest_run_box"]
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                b = (max(0, cx - 40), max(0, cy - 40), min(W, cx + 40), min(H, cy + 40))
                c = Image.fromarray(img[b[1]:b[3], b[0]:b[2]])
                c.resize((c.width * 4, c.height * 4), Image.NEAREST).save(os.path.join(OUT, "crops", f"halo-{name}-{kind}-x4.png"))
    return rec


def raw_r3a():
    J = {j["id"]: j for j in json.load(open(os.path.join(P2, "jobs-r3.json")))["jobs"]}
    M = np.array(J["wm-ph2-fix-r3a-planter-basket"]["register_to_input"], np.float32)
    raw = np.asarray(Image.open(os.path.join(P2, "raw/r3a-seedream.png")).convert("RGB")).astype(np.float32)
    return cv2.warpAffine(raw, M, (raw.shape[1], raw.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


def fit_local(reg, ref, box, allprod):
    x0, y0, x1, y1 = box
    pad = 40
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad
    a = cv2.cvtColor(ref[Y0:Y1, X0:X1].astype(np.float32), cv2.COLOR_RGB2GRAY)
    b = cv2.cvtColor(reg[Y0:Y1, X0:X1], cv2.COLOR_RGB2GRAY)
    hp = lambda x: x - cv2.GaussianBlur(x, (0, 0), 3)  # noqa: E731
    bg = (~allprod[Y0:Y1, X0:X1]).astype(np.float32)
    win = cv2.createHanningWindow((X1 - X0, Y1 - Y0), cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(hp(a) * bg, hp(b) * bg, win)
    out = cv2.warpAffine(reg, np.float32([[1, 0, -dx], [0, 1, -dy]]), (reg.shape[1], reg.shape[0]), flags=cv2.INTER_LINEAR)
    m = ~allprod[Y0:Y1, X0:X1]
    g = np.array([np.median(ref[Y0:Y1, X0:X1, c][m]) / max(np.median(out[Y0:Y1, X0:X1, c][m]), 1) for c in range(3)], np.float32)
    return np.clip(out * g, 0, 255).astype(np.uint8), [round(float(dx), 2), round(float(dy), 2)]


res = {}
for tag, man in (("r3", m3), ("r4", m4)):
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    prods = [l_["id"] for l_ in man["layers"] if "product" in l_]
    img = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png")).convert("RGB"))
    L = Lof(img)
    alphas = {k: np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3] for k in prods}
    alphas["cushions"] = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"]["B"]["layer"])))[..., 3]
    order = man["compose"]["order"]
    pos = {k: order.index(k) for k in alphas}
    for k in FIVE:
        above = np.zeros(L.shape, bool)
        for o in alphas:
            if o != k and pos[o] > pos[k]:
                above |= cv2.dilate((alphas[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{k} [{tag}] whole"] = analyse(L, alphas[k], f"{k}-{tag}", img, above, save=(tag == "r4"))
        res[f"{k} [{tag}] fix box"] = analyse(L, alphas[k], f"{k}-{tag}-box", img, above, box=BOX[k], save=(tag == "r4"))
        print(tag, k, res[f"{k} [{tag}] fix box"])
    if tag == "r4":
        allprod = np.zeros(L.shape, bool)
        for v in alphas.values():
            allprod |= v > 0
        reg = raw_r3a()
        for k in ("basket", "planter"):
            rimg, sh = fit_local(reg, img, BOX[k], allprod)
            above = np.zeros(L.shape, bool)
            for o in alphas:
                if o != k and pos[o] > pos[k]:
                    above |= cv2.dilate((alphas[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
            r = analyse(Lof(rimg), alphas[k], f"{k}-raw", rimg, above, box=BOX[k], save=False)
            r["residual_shift_px"] = sh
            res[f"{k} [raw R3a, r4 alpha] fix box"] = r
            print("raw", k, r)
json.dump(res, open(os.path.join(OUT, "data/halo.json"), "w"), indent=1)
