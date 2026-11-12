#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R6/R7): seams and halos on every layer R6 and R7 made or changed, with the checkpoint's metric (analyse() copied
unchanged from r5_halo.py): per contour pixel (alpha >= 128 next to < 128) the L* profile along the alpha normal, -8..+8 px; a bright halo
when the edge zone exceeds max(inside, outside) by more than T = max(6, 2.5 x local texture std); a dark fringe likewise below; the
longest connected run (>= 8 px gets a x4 crop). Defaults on the r6 / r7 set-B scenes (prev round for the before), variants on their own
set-B truths. Writes data/halo.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-tool-phase2-r6-r7")
M = {t: json.load(open(os.path.join(P2, f"layers/manifest-{t}.json"))) for t in ("r5", "r6", "r7")}


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



def alphas_of(man):
    by = {l_["id"]: l_ for l_ in man["layers"]}
    al = {k: np.asarray(Image.open(os.path.join(P2, "layers", by[k]["file"])))[..., 3] for k in by if "product" in by[k]}
    al["cushions"] = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"]["B"]["layer"])))[..., 3]
    return by, al


res = {}
order = M["r7"]["compose"]["order"]
JOBS = {"r5": ["vase", "magazine-holder"], "r6": ["vase", "magazine-holder", "planter", "curtains", "candle-holders", "bowl", "basket"],
        "r7": ["planter", "curtains", "candle-holders", "bowl", "basket"]}
for tag, ks in JOBS.items():
    by, al = alphas_of(M[tag])
    img = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png")).convert("RGB"))
    L = Lof(img)
    for k in ks:
        above = np.zeros(L.shape, bool)
        for o in al:
            if o != k and order.index(o) > order.index(k):
                above |= cv2.dilate((al[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{k} [{tag}]"] = analyse(L, al[k], f"{k}-{tag}", img, above, save=(tag in ("r6", "r7") and k in JOBS[tag] and not (tag == "r6" and k in JOBS["r7"])))
        print(tag, k, res[f"{k} [{tag}]"], flush=True)
for tag, vids in (("r5", ["vase-v2", "pendant-v2", "framed-art-v2", "curtains-v2"]), ("r6", ["vase-v2", "pendant-v2", "framed-art-v2", "curtains-v2"]),
                  ("r7", ["curtains-v2", "curtains-v3", "vase-v3", "bowl-v2", "candle-holders-v2"])):
    by, al = alphas_of(M[tag])
    VV = {v["id"]: v for vs in M[tag]["variants"].values() for v in vs}
    for vid in vids:
        v = VV[vid]
        img = np.asarray(Image.open(os.path.join(P2, f"graded/variant-{tag}-{vid}-set-B-graded-v3c.png")).convert("RGB"))
        A = np.asarray(Image.open(os.path.join(P2, "layers", v["file"])))[..., 3]
        above = np.zeros(A.shape, bool)
        for o in al:
            if o != v["slot"] and order.index(o) > order.index(v["slot"]):
                above |= cv2.dilate((al[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{vid} [{tag}]"] = analyse(Lof(img), A, f"{vid}-{tag}", img, above, save=(tag != "r5"))
        print(tag, vid, res[f"{vid} [{tag}]"], flush=True)
json.dump(res, open(os.path.join(OUT, "data/halo.json"), "w"), indent=1)
