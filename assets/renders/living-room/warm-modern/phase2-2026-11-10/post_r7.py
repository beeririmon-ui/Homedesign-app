#!/usr/bin/env python3
"""
post_r7.py: the 0-token code fixes on the cuts of passes 6' / 7' (render-agent, 2026-11-12). The raw cut of each product stays as
<name>-cut.png (and its shadow); the fixed file takes the name grade_cut_r7.py reads. Record: work-r7/post-r7.json.

  balls       candle-holders-v2: extract.cut_one (GrabCut) left out the two walnut ball handles of each tray (walnut on a walnut table):
              they are added back from the render (Lab dE against the scene below > 12, at the tray's rows, touching the tray's ends,
              each blob filled to its convex hull: the balls are round), snapped with the guided filter as cut_one's soft edge
  shadow      the contact shadow re-measured by the FROZEN recipe (extract.shadow_one as is) on the final cut
  register    the model warped the table region locally (the global ECC affine cannot follow it): measured on the scene's own vertical
              features (the sofa's seat seams +10..+17 px, the table's right end +8, the throw's edge +9, the table's left end -15), and
              the products drawn on it moved with it. Each piece is put back on its placeholder (the slots 1.9.4 plan point), the
              translation measured on its own silhouette against the placeholder's (the foot rows' centre for x, the bottom row for y),
              layer premultiplied and shadow field together; the shadow re-masked at the new place by the recipe's masks (fix_r7.
              remask_shadow); only pieces off by more than 2 px are moved. A registration of the render, not a move of a placed product
  colour      reported against the card (and, for the vase, the default's off-white targets)

  python3 post_r7.py p6|p7
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract as X  # noqa: E402
import fix_r7 as F7  # noqa: E402
import pass_r7 as P7  # noqa: E402
import phase2_wm as W  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR7 = F7.WR7
REC = os.path.join(WR7, "post-r7.json")
SIZE = W.SIZE


def record(key, val):
    r = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-12", author="render-agent", tokens=0,
                                                              note="0-token code fixes on the pass cuts; the raw cuts are kept as <name>-cut.png")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def keep_cut(stem):
    for sub in ("layers", "shadows"):
        src, raw = os.path.join(WR7, sub, f"{stem}.png"), os.path.join(WR7, sub, f"{stem}-cut.png")
        if not os.path.exists(raw):
            shutil.copyfile(src, raw)
    fa = os.path.join(WR7, "layers", f"{stem}-free-alpha.png")
    if os.path.exists(fa) and not os.path.exists(os.path.join(WR7, "layers", f"{stem}-free-alpha-cut.png")):
        shutil.copyfile(fa, os.path.join(WR7, "layers", f"{stem}-free-alpha-cut.png"))


def load_cut(stem):
    L = F7.f32(os.path.join(WR7, "layers", f"{stem}-cut.png"))
    return L[..., :3], L[..., 3], F7.f32(os.path.join(WR7, "shadows", f"{stem}-cut.png"), "L")


def pieces(a, thr=0.5, min_area=150, join=9):
    """the pieces (left to right): components of the alpha grown by join px, so a tray's ball handles belong to their tray"""
    m = a > thr
    grown = cv2.dilate(m.astype(np.uint8), np.ones((join, join), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(grown)
    ids = sorted([i for i in range(1, n) if (m & (lab == i)).sum() >= min_area], key=lambda i: st[i, 0])
    return [(lab == i) & m for i in ids]


def add_balls(rgb, a, regt, below):
    """the walnut balls at both ends of each tray"""
    dE = X.lab_diff(regt, below, 0.8)
    out = a.copy()
    rec = []
    for m in pieces(a):
        ys, xs = np.nonzero(m)
        widths = {y: (xs[ys == y].min(), xs[ys == y].max()) for y in np.unique(ys)}
        wmax = max(r - l for l, r in widths.values())
        tray_rows = [y for y, (l, r) in widths.items() if r - l >= wmax - 6]
        y0, y1 = min(tray_rows) - 6, max(tray_rows) + 8
        x0, x1 = xs.min() - 30, xs.max() + 30
        cand = np.zeros(a.shape, bool)
        cand[y0:y1, x0:x1] = True
        cand &= (dE > 12) & ~(a > 0.5)
        n, lab, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
        near = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        for i in range(1, n):
            comp = lab == i
            if st[i, 4] < 15 or not (comp & near).any():
                continue
            hull = np.zeros(a.shape, np.uint8)
            cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(comp.astype(np.uint8))), 1)
            hb = hull.astype(bool)
            g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            sa = np.clip(PW.guided(g, hb.astype(np.float32), 2, 1e-3), 0, 1)
            sa = np.where(X.ero(hb, 1), 1.0, np.where(X.dil(hb, 2), sa, 0.0))
            out = np.maximum(out, sa.astype(np.float32))
            bx, by, bw, bh = st[i, :4]
            rec.append(dict(box=[int(bx), int(by), int(bw), int(bh)], px=int(hb.sum())))
    return out.astype(np.float32), rec


def offsets(a, sil):
    """per piece (left to right): the render's foot centre and bottom against the placeholder's (px, work size)"""
    out = []
    for mr, mp in zip(pieces(a), pieces(sil)):
        def foot(m):
            ys, xs = np.nonzero(m)
            yb = ys.max()
            rows = range(int(yb - 0.35 * (yb - ys.min())), int(yb) - 1)
            cs = [(xs[ys == y].min() + xs[ys == y].max()) / 2.0 for y in rows if (ys == y).any()]
            return float(np.median(cs)), float(yb)
        (xr, yr), (xp, yp) = foot(mr), foot(mp)
        out.append(dict(dx=round(xr - xp, 2), dy=round(yr - yp, 2), render_foot=[round(xr, 1), yr], placeholder_foot=[round(xp, 1), yp]))
    return out


def shift_pieces(rgb, a, sh, offs, min_px=2.0):
    """each piece (and its share of the shadow field, nearest piece) translated by (-dx, -dy) when |d| > min_px"""
    ps = pieces(a)
    seeds = np.zeros(a.shape, np.uint8)
    for j, m in enumerate(ps):
        seeds[m] = j + 1
    _, near = cv2.distanceTransformWithLabels((seeds == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys0, xs0 = np.nonzero(seeds > 0)
    lut = np.zeros(int(near.max()) + 1, np.uint8)
    lut[near[ys0, xs0]] = seeds[ys0, xs0]
    owner = lut[near]
    outA, outP, outD = np.zeros_like(a), np.zeros_like(rgb), np.zeros_like(sh)
    moved = []
    for j, o in enumerate(offs):
        own = owner == j + 1
        dx, dy = (o["dx"], o["dy"]) if max(abs(o["dx"]), abs(o["dy"])) > min_px else (0.0, 0.0)
        M = np.float32([[1, 0, -dx], [0, 1, -dy]])
        ai = np.where(own, a, 0).astype(np.float32)
        di = np.where(own, 1 - sh, 0).astype(np.float32)
        outA += cv2.warpAffine(ai, M, SIZE, flags=cv2.INTER_LINEAR)
        outP += cv2.warpAffine(rgb * ai[..., None], M, SIZE, flags=cv2.INTER_LINEAR)
        outD = np.maximum(outD, cv2.warpAffine(di, M, SIZE, flags=cv2.INTER_LINEAR))
        moved.append(dict(o, applied=[round(-dx, 2), round(-dy, 2)]))
    a2 = np.clip(outA, 0, 1).astype(np.float32)
    rgb2 = np.where((outA > 1e-4)[..., None], outP / np.maximum(outA, 1e-4)[..., None], rgb).astype(np.float32)
    return rgb2, a2, np.clip(outD, 0, 1).astype(np.float32), moved


def recipe_shadow(slot, a, regt, below, pass_):
    surf = X.surfaces()
    fa = W.furn_alpha()
    surf["front"] = fa > 0.02
    others = {}
    for k2, v2 in P7.PASSES[pass_]["products"]:
        if k2 != slot:
            nm2 = P7.fname(k2, v2)
            stem = "curtains-v3-render" if nm2 == "curtains-v3" else nm2
            p = os.path.join(WR7, "layers", f"{stem}.png")
            others[k2] = F7.f32(p)[..., 3]
    sh, _ = P7.shadow_new(slot, a, regt, below, surf, others)
    return sh


def table_item(nm, slot, pass_, balls=False):
    keep_cut(nm)
    rgb, a, sh0 = load_cut(nm)
    regt = np.load(os.path.join(WR7, f"{pass_}-regt.npy")).astype(np.float32)
    below = P7.scene(pass_)
    rec = {}
    if balls:
        a, rec["balls_added"] = add_balls(rgb, a, regt, below)
    sh = recipe_shadow(slot, a, regt, below, pass_) if balls else sh0
    sil, _ = P7.load_ph(pass_)
    offs = offsets(a, sil[slot])
    rgb2, a2, d2, moved = shift_pieces(rgb, a, sh, offs)
    other = "bowl" if slot == "candle-holders" else "candle-holders"
    on = P7.fname(other, P7.PASSES[pass_]["products"][[k for k, _ in P7.PASSES[pass_]["products"]].index(other)][1])
    oa = F7.f32(os.path.join(WR7, "layers", f"{on}.png"))[..., 3]
    sh2, clipped = F7.remask_shadow(slot, a2, d2, oa)
    PW.save(os.path.join(WR7, "layers", f"{nm}.png"), rgb2, alpha=a2)
    PW.save(os.path.join(WR7, "shadows", f"{nm}.png"), np.repeat(sh2[..., None], 3, 2))
    rec.update(registration=moved, shadow="the frozen recipe on the final cut (balls in), carried with each piece, re-masked" if balls
               else "the fetch's frozen-recipe shadow, carried with each piece, re-masked", shadow_px_clipped=clipped)
    return rec


def colour_report(nm, slot, variants):
    _, _, G8 = F7.graded(variants=variants)
    a = F7.f32(os.path.join(WR7, "layers", f"{nm}.png"))[..., 3]
    m = cv2.erode((a >= 0.999).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    LL = F7.lab8(G8)
    L_, A_, B_ = LL[..., 0][m], LL[..., 1][m], LL[..., 2][m]
    am, bm = float(np.median(A_)), float(np.median(B_))
    return dict(px=int(m.sum()), L=round(float(np.median(L_)), 2), C=round(float(np.hypot(am, bm)), 2),
                h=round(float(np.degrees(np.arctan2(bm, am)) % 360), 1), G8=G8)


def p6():
    out = {}
    out["candle-holders-v2"] = table_item("candle-holders-v2", "candle-holders", "p6", balls=True)
    out["bowl-v2"] = table_item("bowl-v2", "bowl", "p6")
    keep_cut("vase-v3")
    sil, _ = P7.load_ph("p6")
    a = F7.f32(os.path.join(WR7, "layers", "vase-v3.png"))[..., 3]
    out["vase-v3"] = dict(registration=offsets(a, sil["vase"]), note="reported only (the vase stands on its placeholder within 2 px: not moved)")
    rep = {}
    for nm, slot in (("candle-holders-v2", "candle-holders"), ("bowl-v2", "bowl"), ("vase-v3", "vase")):
        r = colour_report(nm, slot, {"bowl": "bowl-v2", "candle-holders": "candle-holders-v2", "vase": "vase-v3"})
        r.pop("G8")
        rep[nm] = r
    out["colour_graded_set_B"] = rep
    record("p6", out)
    print(json.dumps(out, indent=1, default=float))


def p7():
    out = {}
    out["candle-holders-v3"] = table_item("candle-holders-v3", "candle-holders", "p7", balls=False)
    out["bowl-v3"] = table_item("bowl-v3", "bowl", "p7")
    record("p7", out)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"p6": p6, "p7": p7}[sys.argv[1]]()
