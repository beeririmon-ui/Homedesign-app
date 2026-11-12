#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): seams and halos on every layer R5 made or changed, with the checkpoint's metric (analyse() copied unchanged
from qa/reports/2026-11-11-wm-tool-phase2-r4/tools/r4_halo.py): for each contour pixel (alpha >= 128 next to alpha < 128) the L* profile
along the alpha normal, -8..+8 px; a bright halo when the edge zone (-2..+2) exceeds max(inside, outside) by more than
T = max(6, 2.5 x the local texture std); a dark fringe when it falls below min(inside, outside) by more than T; the longest connected run.
Defaults on the r5 set-B scene, variants on their own truth (graded/variant-r5-<id>-set-B). r4 values for the changed defaults.

Then the R4 vase finding (the right flank's soft edge carried the render's background down with the scale): the vase-edge test of
r4_vase_edge.py on the r5 default and on vase v2 - per row, the soft-edge pixels (alpha 0.15-0.85) against the clean mix
a * (the vase 3-5 px inside) + (1 - a) * (the scene 3-5 px outside); rows lighter / darker than their mix by > 8 L*.
Writes data/halo.json, data/vase-edge.json.
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
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))


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
order = m5["compose"]["order"]
for tag, man in (("r4", m4), ("r5", m5)):
    by, al = alphas_of(man)
    img = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{tag}-set-B-graded-v3c.png")).convert("RGB"))
    L = Lof(img)
    for k in ("curtains", "magazine-holder", "floor-lamp", "vase", "planter", "basket"):
        above = np.zeros(L.shape, bool)
        for o in al:
            if o != k and order.index(o) > order.index(k):
                above |= cv2.dilate((al[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{k} [{tag}]"] = analyse(L, al[k], f"{k}-{tag}", img, above, save=(tag == "r5"))
        print(tag, k, res[f"{k} [{tag}]"])
by, al = alphas_of(m5)
for slot, vs in m5["variants"].items():
    for v in vs:
        img = np.asarray(Image.open(os.path.join(P2, f"graded/variant-r5-{v['id']}-set-B-graded-v3c.png")).convert("RGB"))
        A = np.asarray(Image.open(os.path.join(P2, "layers", v["file"])))[..., 3]
        above = np.zeros(A.shape, bool)
        for o in al:
            if o != slot and order.index(o) > order.index(slot):
                above |= cv2.dilate((al[o] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        res[f"{v['id']}"] = analyse(Lof(img), A, v["id"], img, above)
        print(v["id"], res[v["id"]])
json.dump(res, open(os.path.join(OUT, "data/halo.json"), "w"), indent=1)

# ---------------------------------------------------------------- the vase edge test
ve = {}
for tag, f, scene in (("r5 default", by["vase"]["file"], "graded/default-scene-r5-set-B-graded-v3c.png"),
                      ("v2", next(v["file"] for v in m5["variants"]["vase"]), "graded/variant-r5-vase-v2-set-B-graded-v3c.png")):
    a = np.asarray(Image.open(os.path.join(P2, "layers", f)))[..., 3].astype(np.float32) / 255
    L = Lof(np.asarray(Image.open(os.path.join(P2, scene)).convert("RGB")))
    ys = np.nonzero((a > 0.5).any(1))[0]
    yb = int(ys.max())
    for side in ("right", "left"):
        rows = []
        for y in range(yb - 140, yb - 1):        # the body, below the neck, to the foot
            r = a[y]
            xs = np.nonzero(r > 0.5)[0]
            if not len(xs):
                continue
            if side == "right":
                xe = int(xs.max())
                soft = [x for x in range(xe - 2, xe + 4) if 0.15 <= r[x] <= 0.85]
                Li, Lo = float(np.median(L[y, xe - 5:xe - 2])), float(np.median(L[y, xe + 4:xe + 7]))
            else:
                xe = int(xs.min())
                soft = [x for x in range(xe - 3, xe + 3) if 0.15 <= r[x] <= 0.85]
                Li, Lo = float(np.median(L[y, xe + 3:xe + 6])), float(np.median(L[y, xe - 6:xe - 3]))
            if not soft:
                continue
            d = [float(L[y, x] - (r[x] * Li + (1 - r[x]) * Lo)) for x in soft]
            rows.append([y, round(Li, 1), round(Lo, 1), round(max(d, key=abs), 1)])
        dl = np.array([q[3] for q in rows])
        ve[f"{tag} {side}"] = dict(n_rows=len(rows), rows_lighter_by_8=int((dl > 8).sum()), rows_darker_by_8=int((dl < -8).sum()),
                                   max_lighter=round(float(dl.max()), 1), max_darker=round(float(dl.min()), 1),
                                   worst_rows=sorted(rows, key=lambda q: -abs(q[3]))[:5])
        print("vase edge", tag, side, {k: v for k, v in ve[f"{tag} {side}"].items()})
json.dump(ve, open(os.path.join(OUT, "data/vase-edge.json"), "w"), indent=1)
