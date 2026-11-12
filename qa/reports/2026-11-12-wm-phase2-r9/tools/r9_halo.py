#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R9): halos and fringes on the two layers R9 changed, with the checkpoint's metric: Lof() and analyse() copied
UNCHANGED from qa/reports/2026-11-12-wm-tool-phase2-r6-r7/tools/r67_halo.py (which copied them from r5_halo.py), plus one line that also
returns the per-contour-pixel flags, so the counts can be split by place: on pendant 2 the lantern (y >= 200, outside the collar
|x - 1676.5| <= 9) against the cord, canopy and collar; on curtain 3 the 11 F1 pixels' neighbourhood.
Runs on the R8 and R9 set-B truths of pendant-v2 and curtains-v3 (each with its own layer's alpha; nothing is above the pendant; above
the curtain, the layers above it as in r67_halo). P2-1 (e): <= 10 bright px on the lantern, no new dark fringe but the cord.
Writes data/halo.json and overlays/halo-*-x4.png for any run >= 8 px.     ~/.venvs/motion/bin/python3.12 -I r9_halo.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r9")
pass  # analyse() writes its x4 crops to OUT/overlays


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
                c.resize((c.width * 4, c.height * 4), Image.NEAREST).save(os.path.join(OUT, "overlays", f"halo-{name}-{kind}-x4.png"))
    rec['_flags'] = (ys, xs, flags, exc)
    return rec





M = {t: json.load(open(os.path.join(P2, f"layers/manifest-{t}.json"))) for t in ("r8", "r9")}
order = M["r9"]["compose"]["order"]
res = {}
for vid in ("pendant-v2", "curtains-v3"):
    for tag in ("r8", "r9"):
        man = M[tag]
        VV = {v["id"]: v for vs in man["variants"].values() for v in vs}
        by = {l_["id"]: l_ for l_ in man["layers"]}
        v = VV[vid]
        img = np.asarray(Image.open(os.path.normpath(os.path.join(P2, "layers", v["truth"]))).convert("RGB"))
        A = np.asarray(Image.open(os.path.join(P2, "layers", v["file"])))[..., 3]
        above = np.zeros(A.shape, bool)
        for o, l_ in by.items():
            if "product" in l_ and order.index(o) > order.index(v["slot"]):
                above |= cv2.dilate((np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        if order.index("cushions") > order.index(v["slot"]):
            above |= cv2.dilate((np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"]["B"]["layer"])))[..., 3] > 0).astype(np.uint8),
                                np.ones((7, 7), np.uint8)) > 0
        rec = analyse(Lof(img), A, f"{vid}-{tag}", img, above, save=True)
        ys, xs, flags, exc = rec.pop("_flags")
        if vid == "pendant-v2":
            lantern = (ys >= 200) & ~((np.abs(xs - 1676.5) <= 9) & (ys < 206))
            rec["split"] = dict(lantern=dict(contour=int(lantern.sum()), bright=int(((flags == 1) & lantern).sum()), dark=int(((flags == -1) & lantern).sum())),
                                cord_canopy_collar=dict(contour=int((~lantern).sum()), bright=int(((flags == 1) & ~lantern).sum()), dark=int(((flags == -1) & ~lantern).sum())))
            rec["lantern_flagged"] = [dict(x=int(x), y=int(y), kind="bright" if f == 1 else "dark", excess_L=round(float(e), 1))
                                      for x, y, f, e in zip(xs, ys, flags, exc) if f != 0 and y >= 200 and not (abs(x - 1676.5) <= 9 and y < 206)]
        else:
            near = np.zeros(len(ys), bool)
            mk = np.load(os.path.join(P2, "work-r9/curtain3-soft-edge-mask-r9.npy"))
            mk = cv2.dilate(mk.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
            near = mk[ys, xs]
            rec["near_the_11_px"] = dict(contour=int(near.sum()), bright=int(((flags == 1) & near).sum()), dark=int(((flags == -1) & near).sum()))
        res[f"{vid} [{tag}]"] = rec
        print(vid, tag, {k: v_ for k, v_ in rec.items() if k != "lantern_flagged"}, flush=True)
pl8, pl9 = res["pendant-v2 [r8]"]["split"]["lantern"], res["pendant-v2 [r9]"]["split"]["lantern"]
f8 = [(q["x"], q["y"]) for q in res["pendant-v2 [r8]"]["lantern_flagged"] if q["kind"] == "dark"]
f9 = [q for q in res["pendant-v2 [r9]"]["lantern_flagged"] if q["kind"] == "dark"]
new_spots = [q for q in f9 if min(np.hypot(q["x"] - x, q["y"] - y) for x, y in f8) > 2] if f8 else f9
added_next_to_r8 = [q for q in f9 if (q["x"], q["y"]) not in f8 and q not in new_spots]
res["P2-1 (e)"] = dict(bright_on_lantern_r9=pl9["bright"], dark_on_lantern_r8=pl8["dark"], dark_on_lantern_r9=pl9["dark"],
                       dark_new_spots_gt_2px_from_any_r8_flag=new_spots, dark_added_within_2px_of_an_r8_flag=added_next_to_r8,
                       dark_worst_excess_L=dict(r8=min(q["excess_L"] for q in res["pendant-v2 [r8]"]["lantern_flagged"] if q["kind"] == "dark"),
                                                r9=min(q["excess_L"] for q in f9)),
                       pass_=bool(pl9["bright"] <= 10 and not new_spots),
                       rule="<= 10 bright px on the lantern; no NEW dark fringe but the cord: a dark flag more than 2 px from every R8 flag is new")
print("P2-1 (e)", res["P2-1 (e)"], flush=True)
json.dump(res, open(os.path.join(OUT, "data/halo.json"), "w"), indent=1)
