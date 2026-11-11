#!/usr/bin/env python3
"""
make_crops_r4.py: before / after crops of the five R4 code fixes (render-agent, 2026-11-11), from the graded default scenes with set B:
before = graded/default-scene-r3-set-B-graded-v3c.png, after = graded/default-scene-r4-set-B-graded-v3c.png (the one v3c grade). Each crop
file is [before | after] at 100 % or at x4 (nearest neighbour, no smoothing); the vase also with the card's outline projected at its own base
point (magenta) and at the plan point (cyan). Also QA's seam / halo measure (qa/reports/2026-11-11-wm-tool-phase2-checkpoint/tools/p2_halo.py,
the same algorithm) on each fixed edge, before and after, into crops-r4/edges-r4.json. New files only: crops-r4/.
  python3 make_crops_r4.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_r4 as F  # noqa: E402

OUT = os.path.join(HERE, "crops-r4")
GRD = os.path.join(HERE, "graded")
LAY = os.path.join(HERE, "layers")
FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
M3 = json.load(open(os.path.join(LAY, "manifest-r3.json")))
M4 = json.load(open(os.path.join(LAY, "manifest-r4.json")))

# name: (box x0, y0, x1, y1 in the 2720 x 1530 canvas, zoom)
CROPS = {
    "floor-lamp-shade-100": ((2270, 540, 2600, 780), 1),
    "floor-lamp-shade-lower-left-and-collar-x4": ((2330, 640, 2460, 712), 4),
    "pendant-canopy-and-cord-100": ((1560, 0, 1800, 160), 1),
    "pendant-canopy-x4": ((1625, 0, 1730, 62), 4),
    "basket-planter-100": ((880, 980, 1200, 1280), 1),
    "basket-right-edge-x4": ((1095, 1060, 1160, 1250), 4),
    "planter-left-side-x4": ((935, 1035, 1005, 1150), 4),
    "planter-bottom-x4": ((940, 1130, 1010, 1205), 4),
    "vase-100": ((560, 780, 780, 1120), 1),
    "vase-foot-contact-x4": ((630, 1050, 725, 1100), 4),
}


def load(p):
    return np.asarray(Image.open(p).convert("RGB"))


def panel(imgs, names, zoom):
    tiles = [Image.fromarray(i).resize((i.shape[1] * zoom, i.shape[0] * zoom), Image.NEAREST) for i in imgs]
    w = sum(t.size[0] for t in tiles) + 12 * (len(tiles) - 1)
    h = max(t.size[1] for t in tiles) + 28
    im = Image.new("RGB", (w, h), (250, 249, 247))
    d = ImageDraw.Draw(im)
    x = 0
    for t, n in zip(tiles, names):
        d.text((x + 4, 4), n, fill=(0, 0, 0), font=FS)
        im.paste(t, (x, 28))
        x += t.size[0] + 12
    return im


def vase_outlines(img, box):
    """the card's vase (D16 x H32) projected at the vase's own base point (magenta) and at the plan point (cyan): the body's two
    silhouette lines, the foot's and the mouth's ellipses"""
    r = json.load(open(F.REC))["vase"]
    out = img.copy()
    for (cx, cy), col in ((r["stands_at"]["base_centre_xy"], (230, 30, 200)), ((-2.42, 1.35), (20, 170, 220))):
        pts = []
        for z, rad in ((0.45, 0.05), (0.77, 0.045)):
            ring = [F.px_of(cx + rad * math.cos(t), cy + rad * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, 90)]
            pts.append(np.array([[p[0], p[1]] for p in ring]))
        card = F.card_vase_box(cx, cy)
        sides = [np.array([[card["left"], card["top"] + 6], [card["left"], card["bottom"] - 6]]),
                 np.array([[card["right"], card["top"] + 6], [card["right"], card["bottom"] - 6]])]
        for poly in pts + sides:
            p = np.round(poly - [box[0], box[1]]).astype(np.int32)
            cv2.polylines(out, [p], isClosed=len(poly) > 2, color=col, thickness=1, lineType=cv2.LINE_AA)
    return out


# ------------------------------------------------------------------------------------------------- QA's halo measure (p2_halo.py)
def halo(L, A, others, box, raw_L=None):
    a = A.astype(np.float32) / 255
    g = cv2.GaussianBlur(a, (0, 0), 1.5)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    inside = A >= 128
    contour = inside & (cv2.dilate((~inside).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    contour[:3], contour[-3:], contour[:, :3], contour[:, -3:] = False, False, False, False
    contour &= ~others
    sel = np.zeros(contour.shape, bool)
    sel[box[1]:box[3], box[0]:box[2]] = True
    contour &= sel
    ys, xs = np.nonzero(contour)
    H, Wd = L.shape
    t = np.arange(-8, 9, dtype=np.float32)
    flags = np.zeros(len(ys), np.int8)
    exc = np.zeros(len(ys), np.float32)
    for i, (y, x) in enumerate(zip(ys, xs)):
        nx, ny = -gx[y, x], -gy[y, x]
        n = np.hypot(nx, ny)
        if n < 1e-4:
            continue
        nx, ny = nx / n, ny / n
        px_ = np.clip(np.round(x + nx * t).astype(int), 0, Wd - 1)
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
    if raw_L is not None:
        # the same profile on the graded raw render: a flag the raw has too is the render's own detail; the rest is made by the cut
        rflags = np.zeros(len(ys), np.int8)
        for i, (y, x) in enumerate(zip(ys, xs)):
            nx, ny = -gx[y, x], -gy[y, x]
            n = np.hypot(nx, ny)
            if n < 1e-4:
                continue
            nx, ny = nx / n, ny / n
            px_ = np.clip(np.round(x + nx * t).astype(int), 0, Wd - 1)
            py_ = np.clip(np.round(y + ny * t).astype(int), 0, H - 1)
            prof = raw_L[py_, px_]
            ins, out, edge = prof[12:], prof[:5], prof[6:11]
            ri, ro = np.median(ins), np.median(out)
            T = max(6.0, 2.5 * max(float(ins.std()), float(out.std())))
            if edge.max() - max(ri, ro) > T:
                rflags[i] = 1
            elif min(ri, ro) - edge.min() > T:
                rflags[i] = -1
        flags = np.where(flags == rflags, 0, flags)
        rec = dict(contour_px=int(len(ys)), cut_made_bright_px=int((flags == 1).sum()), cut_made_dark_px=int((flags == -1).sum()))
    for kind, sgn in (("bright", 1), ("dark", -1)):
        m = np.zeros(L.shape, np.uint8)
        s = flags == sgn
        m[ys[s], xs[s]] = 1
        if s.any():
            n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), 8)
            j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            rec[f"{kind}_longest_run_px"] = int((lab[ys[s], xs[s]] == j).sum())
            rec[f"{kind}_worst_excess_L"] = round(float(np.abs(exc[s]).max()), 1)
        else:
            rec[f"{kind}_longest_run_px"] = 0
            rec[f"{kind}_worst_excess_L"] = 0.0
    return rec


def edges():
    res = {}
    targets = {"basket right edge": ("basket", (1095, 1062, 1160, 1246)), "planter left side and bottom": ("planter", (935, 1046, 1010, 1206)),
               "pendant canopy": ("pendant", (1615, 0, 1735, 62)), "vase (whole)": ("vase", (560, 780, 780, 1120)),
               "floor lamp shade (whole)": ("floor-lamp", (2270, 560, 2600, 712))}
    for ver, man, scene in (("r3", M3, "default-scene-r3-set-B-graded-v3c.png"), ("r4", M4, "default-scene-r4-set-B-graded-v3c.png")):
        G = load(os.path.join(GRD, scene))
        L = cv2.cvtColor(G.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
        byid = {l_["id"]: l_ for l_ in man["layers"]}
        order = man["compose"]["order"]
        alph = {k: np.asarray(Image.open(os.path.join(LAY, l_["file"])))[..., 3] for k, l_ in byid.items() if "product" in l_}
        alph["cushions"] = np.asarray(Image.open(os.path.join(LAY, man["slot_cushions"]["sets"]["B"]["layer"])))[..., 3]
        for name, (k, box) in targets.items():
            above = np.zeros(L.shape, bool)
            for o, a in alph.items():
                if o != k and order.index(o) > order.index(k):
                    above |= cv2.dilate((a > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
            res.setdefault(name, {})[ver] = halo(L, alph[k], above, box)
    # the same, relative to the raw renders: only the flags the graded raw (R3a / R3b, registered and tone-matched, the one v3c grade)
    # does not have at the same contour pixel
    import stack
    Gr = stack.Grade()
    raws = {"basket right edge": "work-r3/r3a-regt.npy", "planter left side and bottom": "work-r3/r3a-regt.npy", "pendant canopy": "work-r3/r3b-regt.npy"}
    for ver, man, scene in (("r3", M3, "default-scene-r3-set-B-graded-v3c.png"), ("r4", M4, "default-scene-r4-set-B-graded-v3c.png")):
        G = load(os.path.join(GRD, scene))
        L = cv2.cvtColor(G.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
        byid = {l_["id"]: l_ for l_ in man["layers"]}
        order = man["compose"]["order"]
        alph = {k: np.asarray(Image.open(os.path.join(LAY, l_["file"])))[..., 3] for k, l_ in byid.items() if "product" in l_}
        for name, rp in raws.items():
            k, box = targets[name]
            R = Gr(np.load(os.path.join(HERE, rp)).astype(np.float32))
            RL = cv2.cvtColor(R.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]
            above = np.zeros(L.shape, bool)
            for o, a in alph.items():
                if o != k and order.index(o) > order.index(k):
                    above |= cv2.dilate((a > 0).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
            res[name][ver + "_vs_raw"] = halo(L, alph[k], above, box, raw_L=RL)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    b, a = load(os.path.join(GRD, "default-scene-r3-set-B-graded-v3c.png")), load(os.path.join(GRD, "default-scene-r4-set-B-graded-v3c.png"))
    written = []
    for name, ((x0, y0, x1, y1), z) in CROPS.items():
        cb, ca = b[y0:y1, x0:x1], a[y0:y1, x0:x1]
        imgs, names = [cb, ca], ["before (r3)", "after (r4)"]
        if name == "vase-100":
            imgs.append(vase_outlines(ca, (x0, y0, x1, y1)))
            names.append("after + card D16xH32: magenta here, cyan plan point")
        im = panel(imgs, names, z)
        p = os.path.join(OUT, f"{name}.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        im.save(p)
        written.append(os.path.relpath(p, HERE))
    e = edges()
    rec = dict(date="2026-11-11", author="render-agent", before="graded/default-scene-r3-set-B-graded-v3c.png",
               after="graded/default-scene-r4-set-B-graded-v3c.png", crops=written,
               halo_rule="QA's p2_halo.py: per contour pixel (alpha >= 128 next to < 128, off later layers +3 px), the L* profile -8..+8 px along "
                         "the normal; a bright halo / dark fringe when the edge zone (-2..+2) exceeds both references (inside +4..+8, outside "
                         "-8..-4) by more than max(6, 2.5 x their std); restricted to each fix's box. Many flags are real details (QA: dark "
                         "frames, the chain, the shade's inside); the runs are what matters",
               raw_relative="<ver>_vs_raw: a contour flag that the graded raw render also has at the same pixel (same sign) is the render's own "
                            "detail and is dropped; what remains (cut_made_*) is made by the cut or the shadow",
               edges=e)
    p = os.path.join(OUT, "edges-r4.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1)
    print(json.dumps(e, indent=1))


if __name__ == "__main__":
    main()
