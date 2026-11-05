#!/usr/bin/env python3
"""
grade_v6_m0.py: grading v6 of M0 1.2 on the seedream shell (m0-1-2-shell-seedream-fix.png), the designer's five code fixes
(docs/render-m0-1-2-review-2026-11-05.md section 4) after QA's light finding (qa/reports/2026-11-05-m0-seedream-fix3-g1.md section 3).
render-agent, 2026-11-05, 0 var2 tokens. v5 (process_v8.py --grade v5) is kept as it is; this is a new grading, new files only:
  assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-graded-fix-v6.png, -frame-fix-v6.png, -graded-os6-fix-v6.png,
  -measurements-fix-v6.json (every target point of the review's table, before = the composite, v5, and v6), -masks-fix-v6.jpg,
  and the before / after sheet assets/renders/house-nordic-m0-grade-v6-sheet-2026-11-05.jpg.

Why v5 failed (QA section 3, review section 1): one global exposure (+0.77 stop) aimed at the back wall by the corner, which is the
darkest part of the back wall in the seedream raw (L 73 against 81-84 in the centre), lifted the whole frame: the centre of the wall
to 96.5, the right end to 91.8, the rug to 87.6, the window flat on the roll-off ceiling, the products washed out.

v6 (the review's section 4, in its order; the test-page exception V7Q4 of Bible B3: grading up to the Bible targets, black point and
roll-off kept; in final assets this is fixed in the source, B3):
  masks  the round-5b clay's object index (m0_clay_passes.py) carried onto the canvas; the silhouettes of the objects in front of
         the walls and the floor refined on the render itself (grabCut seeded by the clay, then a guided filter on the render), because
         the soft products (cushions, throw, curtains, pendant, cubes) are not where the clay proxies are; the triptych and the wall
         round exactly from their code placements (art_m0_12.py, m0_shell_fix.py)
  (1)    exposure by the fall-off table, not by one point: one global lift solved in least squares against the four wall points
         (reported); the walls then get a low-frequency gradient along the back wall (a function of the wall's X only, from the raw's
         own wall profile at the Bible height Z 1.60, smoothed over 0.25 m) that puts the corner, the centre behind the picture and the
         right end on their Bible values; the window wall its own constant (80-88)
  (2)    the floor and the rug out of the lift: the oak planks to the oak range (the lit floor by the window, L 68-78; the review's
         "floor median" box is 82 % rug), the rug 6-10 L above the floor
  (3)    the window first: the glass on its own exposure so its median is >= 3 L above the brightest wall and its p99 <= 97 (the
         roll-off), the birch branches >= 4 L under the sky; no wall above 94
  (4)    depth: the S curve mix 0.12 -> 0.27 in the mid-tones only (full weight L 40-85, none below 25 or above 95); low clarity
         (sigma 20 px, +12 %) on the textiles and the wood only, inside their own masks (normalised convolution: no halo); the black
         point a toe only (the darkest 0.5 % patch to 12-15, nothing above L 25 moves)
  (5)    the products not whitened: every product mask at most +0.2 stop over the raw (the table lower, to its oak), no global chroma
         cut on them; the triptych the same, with its own fine clarity (sigma 8 px, +10 %); the travertine pair's glow back from the
         raw as a screen layer (the raw's excess over the wall's base in the two wash zones, + the lit cube faces)
  python3 grade_v6_m0.py masks | grade | sheet | all
"""
import colorsys
import json
import os
import sys

import cv2
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_m0_12 as A  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATE = "2026-11-05"
OD_REL = "assets/renders/living-room/nordic/v9/"
OD = os.path.join(REPO, OD_REL)
JID = "m0-1-2-shell-seedream"
SRC = os.path.join(OD, JID + "-fix.png")
V5 = os.path.join(OD, JID + "-graded-fix-v5.png")
INDEX = os.path.join(OD, "m0-clay-r5b-index.png")
SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/v6/"
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-grade-v6-sheet-2026-11-05.jpg")
GPT_REF = os.path.join(REPO, "assets/renders/house-nordic-v7-2026-11-02/refs/m0-v7-r2-graded-ref.jpg")
CAM = A.CAMS["m0-v8b-r2"]
Y = np.array([0.2126, 0.7152, 0.0722])
SHELL_KINDS = ("back_wall", "window_wall", "ceiling", "cornice", "skirting", "floor")
# canvas uv boxes of the second, local grabCut (name, (u0, u1, v0, v1), shell definite only farther than this from the clay's object, px)
LOCAL_BOXES = [("right curtain", (0.27, 0.41, 0.02, 0.84), 80), ("sofa, cushions, throw", (0.44, 0.94, 0.52, 0.92), 40),
               ("pendant and cord", (0.53, 0.69, 0.0, 0.26), 40), ("armchair, left curtain foot", (0.0, 0.36, 0.55, 1.0), 60)]
# the textiles' fold texture (name, box, threshold, their clay ids)
TEXTURE_BOXES = [("right curtain", (0.295, 0.365, 0.05, 0.772), 2.5, [34]), ("left curtain", (0.0, 0.13, 0.0, 0.985), 2.5, [34]),
                 ("throw drape", (0.855, 0.925, 0.62, 0.86), 2.5, [1, 41])]
HEM_POLY = [(880, 1100), (952, 1100), (955, 1150), (965, 1155), (973, 1168), (976, 1177), (968, 1183), (942, 1195), (910, 1194),
            (880, 1196)]                # canvas px: the right curtain's foot and hem on the floor, traced at 300 %
LEFT_STRIP = (0.035, 0.94)                    # u < 0.035, v < 0.94: the left curtain in the render (the clay has window wall there)
CUBE_BOXES = [(0.508, 0.548, 0.343, 0.400), (0.814, 0.858, 0.308, 0.378)]       # the two travertine cubes (render), with a margin


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def Lmap(a):
    return (a.max(2) + a.min(2)) / 2 * 100


# ---------------------------------------------------------------------------------------------------------------
# masks
# ---------------------------------------------------------------------------------------------------------------
def clay_kinds():
    I = cv2.imread(INDEX, cv2.IMREAD_UNCHANGED).astype(np.int32)
    cl = json.load(open(INDEX.replace(".png", ".json")))["classes"]
    kind = {int(k): v["kind"] for k, v in cl.items()}
    return I, kind


def art_round_masks(H, W):
    """the triptych's three frames (their code quads, the projected 50 x 70 targets) and the wall round (its projected 38 cm circle)."""
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    art = np.zeros((H, W), np.uint8)
    for q in n["placement"]["targets_px"]:
        cv2.fillConvexPoly(art, np.round(np.array(q) * 4).astype(np.int32), 1, lineType=cv2.LINE_8, shift=2)
    b = json.load(open(os.path.join(OD, JID + "-fix-base.json")))["wall_round"]["target"]
    rnd = np.zeros((H, W), np.uint8)
    (cx, cy), (ax, ay) = b["centre_px"], b["axes_px"]
    cv2.ellipse(rnd, ((cx, cy), (ax + 4, ay + 4), 0), 1, -1)
    return art.astype(bool), rnd.astype(bool)


def guided(I, p, r, eps):
    """He et al. guided filter (gray guide), box radius r."""
    k = (2 * r + 1, 2 * r + 1)
    mI, mp = cv2.blur(I, k), cv2.blur(p, k)
    cIp = cv2.blur(I * p, k) - mI * mp
    vI = cv2.blur(I * I, k) - mI * mI
    a_ = cIp / (vI + eps)
    b_ = mp - a_ * mI
    return cv2.blur(a_, k) * I + cv2.blur(b_, k)


def masks(a, write=True):
    """per-pixel group labels and soft weights. Returns dict of float maps (sum to 1) and records."""
    H, W = a.shape[:2]
    I, kind = clay_kinds()
    K = np.vectorize(lambda k: kind.get(int(k), "product"))(I)
    art, rnd = art_round_masks(H, W)
    shell = np.isin(K, SHELL_KINDS) & ~art & ~rnd
    obj = (K == "product") | art | rnd
    # grabCut at half size, seeded by the clay: definite shell far from the clay's objects, definite object deep inside them,
    # the glass and the window architecture definite non-shell; the art and the round exact
    h2, w2 = H // 2, W // 2
    a8 = cv2.resize((a * 255).astype(np.uint8), (w2, h2), interpolation=cv2.INTER_AREA)
    sh2 = cv2.resize(shell.astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST)
    ob2 = cv2.resize(obj.astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST)
    ex2 = cv2.resize((art | rnd).astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST)
    d_obj = cv2.distanceTransform((1 - ob2).astype(np.uint8), cv2.DIST_L2, 5)          # distance to the nearest clay object
    d_sh = cv2.distanceTransform((1 - sh2).astype(np.uint8), cv2.DIST_L2, 5)           # distance to the nearest clay shell
    gc = np.full((h2, w2), cv2.GC_BGD, np.uint8)                                        # glass, window: not shell
    gc[sh2 > 0] = cv2.GC_PR_FGD
    gc[(sh2 > 0) & (d_obj > 24)] = cv2.GC_FGD
    gc[ob2 > 0] = cv2.GC_PR_BGD
    gc[(ob2 > 0) & (d_sh > 22)] = cv2.GC_BGD
    gc[ex2 > 0] = cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(a8, gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    sh_gc = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    # keep only shell components connected to the definite shell (no islands inside products), fill small holes in the shell
    n, lab = cv2.connectedComponents(sh_gc)
    keep = np.zeros(n, bool)
    keep[np.unique(lab[(gc == cv2.GC_FGD)])] = True
    keep[0] = False
    sh_gc = keep[lab].astype(np.uint8)
    inv = (1 - sh_gc).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 60:
            sh_gc[lab == i] = 1
    sh_full = cv2.resize(sh_gc.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR) > 0.5
    sh_full[art | rnd] = False
    sh_full[~(shell | obj)] = False                                                     # glass and window stay as the clay has them
    # second pass, full size, local colour models, in boxes round the objects whose render silhouette is far from the clay's (the right
    # curtain's hem, the sofa's cushions and throw, the pendant, the armchair and the left curtain's foot); seeds: the first pass,
    # shell definite only where the clay is shell too and far from the clay's object
    a8f = (a * 255).astype(np.uint8)
    d_objf = cv2.distanceTransform((~obj).astype(np.uint8), cv2.DIST_L2, 5)
    local = []
    for nm, (u0, u1, v0, v1), far in LOCAL_BOXES:
        x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
        s1 = sh_full[y0:y1, x0:x1]
        g2 = np.where(s1, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
        e_s = cv2.erode(s1.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & shell[y0:y1, x0:x1] & (d_objf[y0:y1, x0:x1] > far)
        e_o = cv2.erode((~s1).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & obj[y0:y1, x0:x1]
        g2[e_s] = cv2.GC_FGD
        g2[e_o] = cv2.GC_BGD
        g2[~(shell | obj)[y0:y1, x0:x1]] = cv2.GC_BGD
        g2[(art | rnd)[y0:y1, x0:x1]] = cv2.GC_BGD
        b1, f1 = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(np.ascontiguousarray(a8f[y0:y1, x0:x1]), g2, None, b1, f1, 6, cv2.GC_INIT_WITH_MASK)
        new = (g2 == cv2.GC_FGD) | (g2 == cv2.GC_PR_FGD)
        local.append(dict(box=nm, uv=[u0, u1, v0, v1], flipped_to_object_px=int((s1 & ~new).sum()), flipped_to_shell_px=int((~s1 & new).sum())))
        sh_full[y0:y1, x0:x1] = new
    # the two travertine cubes: the stone's pores (the high-pass of L*, blurred 3 px) against the smooth plaster and the smooth wash,
    # inside a box round each; closed, the largest component, eroded back by the blur's spread, convex hull
    cubes = np.zeros((H, W), bool)
    Lc = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)[..., 0]
    texc = cv2.GaussianBlur(np.abs(Lc - cv2.GaussianBlur(Lc, (0, 0), 1.5)), (0, 0), 3)
    for (u0, u1, v0, v1) in CUBE_BOXES:
        x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
        t = texc[y0:y1, x0:x1]
        ring = np.ones_like(t, bool)
        ring[6:-6, 6:-6] = False
        m = (t > max(3 * np.median(t[ring]), 0.6)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = cv2.erode((lab == k).astype(np.uint8), np.ones((9, 9), np.uint8))
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
        mm = np.zeros_like(m)
        cv2.fillConvexPoly(mm, hull, 1)
        cubes[y0:y1, x0:x1] |= mm.astype(bool)
    sh_full[cubes] = False
    # the textiles grabCut still cuts short (the right curtain's shadowed folds and hem, the left curtain's edge and foot, the throw's
    # drape): the folds' texture (|dL*/dx| blurred 3 x 12 px) against the smooth plaster, connected to the textile's own core
    Ls = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)[..., 0]
    tex = cv2.GaussianBlur(np.abs(cv2.Sobel(cv2.GaussianBlur(Ls, (0, 0), 1.0), cv2.CV_32F, 1, 0, ksize=3)), (0, 0), sigmaX=3, sigmaY=12)
    textile = []
    for nm, (u0, u1, v0, v1), thr, ids in TEXTURE_BOXES:
        x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
        cand = (tex[y0:y1, x0:x1] > thr) | (~sh_full[y0:y1, x0:x1] & np.isin(I[y0:y1, x0:x1], ids))
        cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 5), np.uint8))
        core = cv2.erode((np.isin(I[y0:y1, x0:x1], ids) & ~sh_full[y0:y1, x0:x1]).astype(np.uint8), np.ones((9, 9), np.uint8))
        n, lab = cv2.connectedComponents(cand)
        keep = np.zeros(n, bool)
        keep[np.unique(lab[core > 0])] = True
        keep[0] = False
        m = keep[lab] & (shell | obj)[y0:y1, x0:x1] & ~np.isin(I[y0:y1, x0:x1], [8, 521])         # never the floor or the rug
        textile.append(dict(box=nm, uv=[u0, u1, v0, v1], to_object_px=int((m & sh_full[y0:y1, x0:x1]).sum())))
        sh_full[y0:y1, x0:x1] &= ~m
    # the right curtain's hem where it lies on the floor (linen: low chroma for its lightness, the oak has C*/L* ~0.39) and the left
    # curtain's outer strip (it covers the frame's left edge from the rod to the floor)
    hem = np.zeros((H, W), np.uint8)
    cv2.fillPoly(hem, [np.array(HEM_POLY, np.int32)], 1)
    hem = hem.astype(bool)
    x0, y0 = np.array(HEM_POLY).min(0)
    x1, y1 = np.array(HEM_POLY).max(0)
    box = np.zeros((H, W), bool)
    box[y0 - 4:y1 + 12, x0:x1 + 25] = True
    textile.append(dict(box="right curtain hem on the floor", poly_px=HEM_POLY, to_object_px=int((hem & sh_full).sum()),
                        to_floor_px=int((box & ~hem & ~sh_full & (I == 8)).sum()),
                        how="traced at 300 % on the render (the shadowed linen and the oak have the same chroma there); outside it, the clay floor is floor"))
    sh_full[hem] = False
    sh_full[box & ~hem & (I == 8)] = True
    strip = np.zeros((H, W), bool)
    strip[:int(LEFT_STRIP[1] * H), :int(LEFT_STRIP[0] * W)] = True
    textile.append(dict(box="left curtain outer strip", uv=[0, LEFT_STRIP[0], 0, LEFT_STRIP[1]], to_object_px=int((strip & sh_full).sum())))
    sh_full &= ~strip
    # the floor / rug edge is the clay's (it matches the render within a few px): clay floor that went to "object" only next to the rug
    # goes back to the floor, the clay rug is never shell
    sh_full[(I == 521)] = False
    objm0 = (K == "product") | art | rnd | cubes
    _, labn = cv2.distanceTransformWithLabels((~objm0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(objm0)
    lut = np.zeros(labn.max() + 1, np.int64)
    lut[labn[ys, xs]] = ys * W + xs
    nearest = I.reshape(-1)[lut[labn].reshape(-1)].reshape(H, W)
    back = (I == 8) & ~sh_full & (nearest == 521)
    sh_full[back] = True
    sh_full = sh_full.astype(np.float32)
    g = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    sh_soft = np.clip(guided(g, sh_full, 3, 2e-4), 0, 1)
    sh_soft[art | rnd | cubes] = 0.0
    sh_soft[~(shell | obj)] = 0.0
    # the shell's own classes from the clay (planes: their edges are corners, the clay is right there); object classes: the nearest
    # clay object's class
    shell_kind = np.where(shell, K, "")
    dist, lab = cv2.distanceTransformWithLabels((~shell).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(shell)
    lut = np.zeros(lab.max() + 1, np.int32)
    lin_idx = ys * W + xs
    lut[lab[ys, xs]] = lin_idx
    near_shell = K.reshape(-1)[lut[lab].reshape(-1)].reshape(H, W)
    sk = np.where(shell, K, near_shell)
    objlab = np.where(cubes, -4, np.where(art, -2, np.where(rnd, -3, I)))
    objm = (K == "product") | art | rnd | cubes
    dist, lab = cv2.distanceTransformWithLabels((~objm).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(objm)
    lut = np.zeros(lab.max() + 1, np.int32)
    lut[lab[ys, xs]] = ys * W + xs
    near_obj = objlab.reshape(-1)[lut[lab].reshape(-1)].reshape(H, W)
    ok = np.where(objm, objlab, near_obj)
    rec = dict(grabcut=dict(size=[w2, h2], iterations=6, definite_shell="clay shell farther than 24 px (half size) from any clay object",
                            definite_object="clay object farther than 22 px from the clay shell; the triptych and the round exact",
                            shell_px_clay=int(shell.sum()), shell_px_render=int((sh_soft > 0.5).sum())), local_grabcut=local, textiles=textile,
               cubes=dict(boxes=CUBE_BOXES, how="the stone's pores: |L* - blur 1.5| blurred 3 px > 3x the box rim's median; closed 9, largest component, eroded 4 px, convex hull", px=int(cubes.sum())),
               feather="guided filter on the render (r 3 px, eps 2e-4)")
    M = dict(shell=sh_soft, shell_kind=sk, obj_label=ok, K=K, I=I, art=art, rnd=rnd, cubes=cubes)
    if write:
        kinds = np.array(["", "back_wall", "window_wall", "ceiling", "cornice", "skirting", "floor"])
        skc = np.zeros((H, W), np.uint8)
        for i, k in enumerate(kinds[1:], 1):
            skc[sk == k] = i
        np.savez_compressed(SP + "masks.npz", shell=sh_soft.astype(np.float32), art=art, rnd=rnd, cubes=cubes, shell_kind=skc,
                            obj_label=ok.astype(np.int32), I=I)
        json.dump(rec, open(SP + "masks.json", "w"), indent=1)
        vis = (a * 255).astype(np.uint8).copy()
        e = cv2.morphologyEx((sh_soft > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(bool)
        ec = cv2.morphologyEx(shell.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(bool)
        vis[ec] = (255, 210, 0)
        vis[e] = (255, 0, 0)
        cv2.imwrite(SP + "masks-vis.png", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    return M, rec


def load_masks():
    d = np.load(SP + "masks.npz")
    kinds = np.array(["", "back_wall", "window_wall", "ceiling", "cornice", "skirting", "floor"])
    return dict(shell=d["shell"], shell_kind=kinds[d["shell_kind"]], obj_label=d["obj_label"], I=d["I"], art=d["art"], rnd=d["rnd"],
                cubes=d["cubes"]), json.load(open(SP + "masks.json"))


# ---------------------------------------------------------------------------------------------------------------
# measurement (the review's table, QA's points, the products)
# ---------------------------------------------------------------------------------------------------------------
WALL_PTS = [("back wall by the corner (0.427, 0.416) [90-94]", (0.4269, 0.4156), (90, 94), "corner"),
            ("back wall behind the picture (0.667, 0.312) [88-91] (review)", (0.667, 0.312), (88, 91), "centre"),
            ("centre above the triptych (0.62, 0.30) [88-91] (QA)", (0.62, 0.30), (88, 91), "centre"),
            ("centre between triptych and sofa (0.62, 0.55) [88-91] (QA)", (0.62, 0.55), (88, 91), "centre"),
            ("back wall right end (0.952, 0.382) [82-86] (review)", (0.952, 0.382), (82, 86), "right"),
            ("right edge of the back wall (0.97, 0.31) [82-86] (QA)", (0.97, 0.31), (82, 86), "right"),
            ("window wall (0.352, 0.415) [80-88]", (0.352, 0.415), (80, 88), "window"),
            ("ceiling (0.55, 0.04) [no Bible number]", (0.55, 0.04), None, "ceiling")]
BOX = {"charcoal cushion (QA box)": (0.70, 0.78, 0.66, 0.70), "sage cushion": (0.578, 0.622, 0.630, 0.685), "sage runner": (0.530, 0.575, 0.790, 0.825),
       "table top oak": (0.610, 0.645, 0.805, 0.850), "floor by the window (QA box)": (0.33, 0.40, 0.765, 0.79), "floor right strip": (0.88, 0.98, 0.82, 0.87),
       "rug by the window floor": (0.40, 0.47, 0.81, 0.85), "rug right (QA box)": (0.90, 0.98, 0.93, 0.97), "glass upper": (0.10, 0.26, 0.06, 0.35)}
LEGACY_FLOOR = (0.42, 0.98, 0.87, 0.99)
LEGACY_SHADOW = (0.52, 0.84, 0.76, 0.83)
# the triptych's print-local regions (s, t in the 50 x 70 frame, read on the composite): board, passe-partout, oak profile, marks
ART_REG = {"board": [(0.18, 0.82, 0.13, 0.24), (0.18, 0.82, 0.73, 0.86)], "passe-partout": [(0.16, 0.84, 0.045, 0.078)],
           "oak frame": [(0.008, 0.030, 0.15, 0.85), (0.970, 0.992, 0.15, 0.85)], "marks": [(0.30, 0.70, 0.25, 0.75)]}


def patch(a, u, v, w=0.01):
    H, W = a.shape[:2]
    hw = max(2, int(w * W / 2))
    x, y = int(u * W), int(v * H)
    return a[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


def hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)


def boxm(H, W, b):
    m = np.zeros((H, W), bool)
    m[int(b[2] * H):int(b[3] * H), int(b[0] * W):int(b[1] * W)] = True
    return m


def art_regions(H, W):
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    out = {k: [] for k in ART_REG}
    for q in n["placement"]["targets_px"]:
        q = np.array(q, np.float32)                                  # TL TR BR BL
        Hq = cv2.getPerspectiveTransform(np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]), q)
        regs = {}
        for k, rs in ART_REG.items():
            m = np.zeros((H, W), np.uint8)
            for (s0, s1, t0, t1) in rs:
                pts = cv2.perspectiveTransform(np.float32([[[s0, t0], [s1, t0], [s1, t1], [s0, t1]]]), Hq)[0]
                cv2.fillConvexPoly(m, np.round(pts * 4).astype(np.int32), 1, shift=2)
            regs[k] = m.astype(bool)
        # the wall just above the frame (t -0.12..-0.04)
        m = np.zeros((H, W), np.uint8)
        pts = cv2.perspectiveTransform(np.float32([[[0.1, -0.12], [0.9, -0.12], [0.9, -0.04], [0.1, -0.04]]]), Hq)[0]
        cv2.fillConvexPoly(m, np.round(pts * 4).astype(np.int32), 1, shift=2)
        regs["wall above"] = m.astype(bool)
        for k, m in regs.items():
            out.setdefault(k, []).append(m)
    return out


def wash_zones(Mk, H, W):
    """per cube: the cube face (its mask), the wash above and below it (12 x 30 cm Bible fans: a box 1 cube wide, 2.5 cube heights
    tall, above and below), and the plain wall beside at the same height (1.5-3 cube widths to the outer side)"""
    cubes = Mk["cubes"]
    n, lab, st, _ = cv2.connectedComponentsWithStats(cubes.astype(np.uint8))
    out = []
    for i in sorted(range(1, n), key=lambda i: st[i, cv2.CC_STAT_LEFT]):
        x, y, w, h = st[i, :4]
        face = lab == i
        cx = x + w / 2
        up = np.zeros((H, W), bool)
        up[max(0, int(y - 2.0 * h)):int(y - 0.15 * h), int(cx - 0.35 * w):int(cx + 0.35 * w)] = True
        dn = np.zeros((H, W), bool)
        dn[int(y + 1.15 * h):int(y + 2.5 * h), int(cx - 0.35 * w):int(cx + 0.35 * w)] = True
        side = 1 if cx > W * 0.7 else -1                            # the right cube: plain wall to its right; the left: to its left
        bw = np.zeros((H, W), bool)
        xa, xb = (cx + side * 1.6 * w, cx + side * 2.6 * w)
        bw[max(0, int(y - 1.0 * h)):int(y + 2.0 * h), int(min(xa, xb)):int(max(xa, xb))] = True
        out.append(dict(face=face, up=up, down=dn, beside=bw, box=[int(x), int(y), int(w), int(h)]))
    return out


def measure(img, Mk, label):
    """img: sRGB 0..1. Every target of the review's section 1 table and section 4, QA's fall-off points, the products."""
    H, W = img.shape[:2]
    L = Lmap(img)
    lab = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2LAB)
    Ls, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    hls_ = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2HLS)
    S = hls_[..., 2] * 100
    I = Mk["I"]
    r = dict(label=label, walls={}, fall_off={}, floor_rug={}, window={}, frame={}, shadows={}, products={}, triptych={}, lamps={})
    vals = {}
    for nm, (u, v), rng, grp in WALL_PTS:
        h_, s_, l_ = hsl(patch(img, u, v))
        lp = cv2.cvtColor(patch(img, u, v).reshape(1, 1, 3).astype(np.float32), cv2.COLOR_RGB2LAB)[0, 0]
        r["walls"][nm] = dict(L=l_, H=h_, S=s_, Lstar=round(float(lp[0]), 1), C=round(float(np.hypot(lp[1], lp[2])), 1),
                              range=list(rng) if rng else None, ok=(bool(rng[0] <= l_ <= rng[1]) if rng else None))
        vals.setdefault(grp, []).append(l_)
    c_, m_, rt = vals["corner"][0], float(np.mean(vals["centre"])), float(np.mean(vals["right"]))
    r["fall_off"] = dict(corner=c_, centre_mean=round(m_, 1), right_mean=round(rt, 1), corner_minus_centre=round(c_ - m_, 1),
                         centre_minus_right=round(m_ - rt, 1), ok=bool(c_ - m_ >= 1 and m_ - rt >= 3),
                         rule="corner >= centre + 1, centre >= right end + 3 (review 4.1)")
    # floor and rug
    fl = (I == 8) & (Mk["shell"] > 0.9)
    rug = (I == 521) & (Mk["shell"] < 0.1)
    lb = boxm(H, W, LEGACY_FLOOR)
    reg = img[lb].reshape(-1, 3)[::29]
    hh = np.array([colorsys.rgb_to_hls(*c) for c in reg])
    r["floor_rug"]["review box (u0.42-0.98, v0.87-0.99): median HSL L / S (82 % of it is the rug)"] = [round(float(np.median(hh[:, 1])) * 100, 1), round(float(np.median(hh[:, 2])) * 100, 1)]
    for nm in ("floor by the window (QA box)", "floor right strip"):
        m = boxm(H, W, BOX[nm]) & fl
        r["floor_rug"][nm + " [L 68-78, S 30-45]: median L / S"] = [round(float(np.median(L[m])), 1), round(float(np.median(S[m])), 1)]
    r["floor_rug"]["all visible oak planks: median L / S"] = [round(float(np.median(L[fl])), 1), round(float(np.median(S[fl])), 1)]
    for nm in ("rug by the window floor", "rug right (QA box)"):
        m = boxm(H, W, BOX[nm]) & rug
        r["floor_rug"][nm + ": median L"] = round(float(np.median(L[m])), 1)
    r["floor_rug"]["rug, whole: median L"] = round(float(np.median(L[rug])), 1)
    fw = r["floor_rug"]["floor by the window (QA box) [L 68-78, S 30-45]: median L / S"][0]
    rw = r["floor_rug"]["rug by the window floor: median L"]
    r["floor_rug"]["rug minus floor, side by side by the window [6-10]"] = round(rw - fw, 1)
    # window
    gl = cv2.erode((I == 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & (Mk["obj_label"] != 445) & (Lmap(img) > 0)
    gl &= ~boxm(H, W, (0.0, 0.10, 0.0, 1.0))                        # the left curtain over the glass
    walls = np.isin(Mk["shell_kind"], ["back_wall", "window_wall"]) & (Mk["shell"] > 0.95)
    nowash = np.ones((H, W), bool)
    for z in wash_zones(Mk, H, W):
        nowash &= ~cv2.dilate((z["up"] | z["down"] | z["face"]).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    wall_max = float(np.percentile(L[walls & nowash], 99.5))
    g50, g99 = float(np.median(L[gl])), float(np.percentile(L[gl], 99))
    gu = gl & boxm(H, W, BOX["glass upper"])
    r["window"] = dict(glass_p50=round(g50, 1), glass_p99=round(g99, 1), walls_p99_5=round(wall_max, 1),
                       glass_p50_minus_brightest_wall=round(g50 - wall_max, 1),
                       branches_vs_sky_upper_glass_p90_minus_p10=round(float(np.percentile(L[gu], 90) - np.percentile(L[gu], 10)), 1),
                       ok=dict(glass_brightest=bool(g50 - wall_max >= 3), p99_le_97=bool(g99 <= 97.0), no_wall_above_94=bool(wall_max <= 94.0),
                               branches=bool(np.percentile(L[gu], 90) - np.percentile(L[gu], 10) >= 4)),
                       rules="glass p50 >= the brightest wall (walls' p99.5 outside the lamp washes) + 3; glass p99 <= 97; no wall above 94; branches >= 4 L under the sky")
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    iy, ix = np.unravel_index(int(np.argmin(pm)), pm.shape)
    r["frame"] = dict(mean_L=round(float(L.mean()), 1), mean_L_range=[76, 80], share_Lstar_over_90=round(float((Ls > 90).mean()), 3),
                      mean_Cstar=round(float(C.mean()), 2), max_L=round(float(L.max()), 1), px_255=int((img.max(2) >= 254.5 / 255).sum()))
    kk = 32
    mu = cv2.blur(Ls, (kk, kk))
    sd = np.sqrt(np.maximum(cv2.blur(Ls * Ls, (kk, kk)) - mu * mu, 0))
    r["frame"]["local_contrast_median (QA: std of L* in 32 px)"] = round(float(np.median(sd)), 2)
    Lm = cv2.medianBlur((L * 2.55).astype(np.uint8), 3).astype(np.float32) / 2.55
    sb = boxm(H, W, LEGACY_SHADOW)
    r["shadows"] = {"under the sofa (review box u0.52-0.84, v0.76-0.83): min / p1 [p1 18-22]": [round(float(Lm[sb].min()), 1), round(float(np.percentile(Lm[sb], 1)), 1)],
                    "darkest 0.5 % patch [12-15, only in the deepest crevice]": round(float(pm.min()), 1),
                    "darkest patch at (u, v)": [round((ix * 4 + k / 2) / W, 3), round((iy * 4 + k / 2) / H, 3)]}
    # products
    for nm in ("charcoal cushion (QA box)", "sage cushion", "sage runner", "table top oak"):
        m = boxm(H, W, BOX[nm])
        h_, s_, l_ = hsl(img[m].mean(0))
        r["products"][nm] = dict(H=h_, S=s_, L=l_, median_L=round(float(np.median(L[m])), 1))
    r["products"]["charcoal cushion (QA box)"]["range_L"] = [25, 32]
    r["products"]["sage cushion"]["range_S"] = [8, 22]
    r["products"]["sage runner"]["range_S"] = [8, 22]
    r["products"]["table top oak"]["range_L"] = [60, 72]
    ar = art_regions(H, W)
    for i in range(3):
        d = {}
        for kx in ("board", "passe-partout", "oak frame", "wall above"):
            d[kx] = round(float(np.median(L[ar[kx][i]])), 1)
        mk = ar["marks"][i] & (L < 50)
        d["marks"] = round(float(np.median(L[mk])), 1) if mk.sum() > 20 else None
        d["passe-partout minus board [>= 6]"] = round(d["passe-partout"] - d["board"], 1)
        d["wall minus oak frame [>= 15]"] = round(d["wall above"] - d["oak frame"], 1)
        d["ok"] = dict(board=bool(80 <= d["board"] <= 86), passe_partout=bool(92 <= d["passe-partout"] <= 95), marks=bool(d["marks"] is not None and d["marks"] <= 28),
                       oak=bool(62 <= d["oak frame"] <= 72), board_vs_pp=bool(d["passe-partout minus board [>= 6]"] >= 6))
        r["triptych"][f"print {i + 1}"] = d
    r["triptych"]["ranges"] = "board L 80-86; passe-partout 92-95 (>= 6 over the board); marks <= 28; oak frame 62-72, >= 15 under the wall"
    for i, z in enumerate(wash_zones(Mk, H, W)):
        face = np.median(L[z["face"]])
        slot = np.percentile(L[z["face"]], 97)
        wash = max(np.percentile(L[z["up"]], 90), np.percentile(L[z["down"]], 90))
        beside = np.median(L[z["beside"] & walls])
        r["lamps"][["left cube", "right cube"][i]] = dict(stone_face_median_L=round(float(face), 1), glowing_slot_p97_L=round(float(slot), 1), wash_p90_L=round(float(wash), 1),
                                                          wall_beside_L=round(float(beside), 1), wash_minus_wall=round(float(wash - beside), 1),
                                                          ok=dict(glow=bool(93 <= slot <= 97), wash=bool(wash - beside >= 6)),
                                                          rule="the lamp's glow (the lit slot, p97 of the cube) L 93-97; the stone keeps its colour (product +0.2 at most); "
                                                               "wash >= 6 L over the plain wall beside (Bible fixed pool)")
    return r


# ---------------------------------------------------------------------------------------------------------------
# the wall profile and the exposure map
# ---------------------------------------------------------------------------------------------------------------
X_CTRL = (-1.75, 0.20, 1.85)          # corner (Bible point, Z 1.60), centre (behind the picture), right end (Bible point)
Z_REF = 1.60


def wall_xz(H, W):
    Hc = A.C_canvas(W, H) @ A.H_wall(CAM)
    Hi = np.linalg.inv(Hc)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    p = np.stack([xs, ys, np.ones_like(xs)], -1) @ Hi.T
    return (p[..., 0] / p[..., 2]).astype(np.float32), (p[..., 1] / p[..., 2]).astype(np.float32)


def wall_profile(lin, Mk, X, Z):
    """the raw back wall's luminance as f(X) + g(Z) (log2, robust medians in 0.1 m bins, alternating), the plain wall only: away from
    the objects, the triptych and the round with their shadows, the two lamp washes; f smoothed over 0.25 m"""
    H, W = X.shape
    Yl = (lin * Y).sum(2)
    m = (Mk["shell_kind"] == "back_wall") & (Mk["shell"] > 0.98)
    m &= ~cv2.dilate((Mk["art"] | Mk["rnd"]).astype(np.uint8), np.ones((51, 51), np.uint8)).astype(bool)
    for z in wash_zones(Mk, H, W):
        m &= ~cv2.dilate((z["up"] | z["down"] | z["face"]).astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    obj = Mk["shell"] < 0.5
    m &= ~cv2.dilate(obj.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    m &= (Z > 0.9) & (Z < 2.7)
    xb = np.arange(-2.30, 2.75, 0.05)
    zb = np.arange(0.9, 2.75, 0.1)
    xi = np.clip(np.digitize(X[m], xb) - 1, 0, len(xb) - 2)
    zi = np.clip(np.digitize(Z[m], zb) - 1, 0, len(zb) - 2)
    lv = np.log2(np.maximum(Yl[m], 1e-5))
    G = np.full((len(xb) - 1, len(zb) - 1), np.nan)
    Nn = np.zeros_like(G)
    for i in range(G.shape[0]):
        si = xi == i
        for j in range(G.shape[1]):
            sj = si & (zi == j)
            if sj.sum() >= 25:
                G[i, j] = np.median(lv[sj])
                Nn[i, j] = sj.sum()
    f = np.nanmedian(G, 1)
    f = np.where(np.isnan(f), np.nanmedian(f), f)
    g = np.zeros(G.shape[1])
    for _ in range(12):
        g = np.nanmedian(G - f[:, None], 0)
        g = np.where(np.isnan(g), 0, g)
        f = np.nanmedian(G - g[None, :], 1)
        ok = ~np.isnan(f)
        f = np.interp(np.arange(len(f)), np.flatnonzero(ok), f[ok])
    xc = (xb[:-1] + xb[1:]) / 2
    zc = (zb[:-1] + zb[1:]) / 2
    fs = cv2.GaussianBlur(f.reshape(1, -1).astype(np.float32), (0, 0), sigmaX=2.0, borderType=cv2.BORDER_REPLICATE).ravel()
    return xc, fs + float(np.interp(Z_REF, zc, g)), dict(bins_x=len(xc), filled=int(np.isfinite(G).sum()), px=int(m.sum()),
                                                        profile_L_at_Zref={f"{x:+.2f}": round(float(l2s(np.array(2 ** v)) * 100), 1)
                                                                           for x, v in zip(xc[::8], (fs + float(np.interp(Z_REF, zc, g)))[::8])})


def pchip(xk, yk, x):
    """piecewise linear through the control points, flat outside"""
    return np.interp(x, xk, yk)


def exposure_map(P, Mk, X, prof):
    """E (stops) per pixel: the walls (back wall, cornice, skirting: the fall-off field of X; the window wall a constant), the ceiling,
    the floor, the glass, the window architecture, the products (the table its own, the lamps their own), blended by the soft shell mask"""
    H, W = X.shape
    xc, f = prof
    fP = pchip(np.array(X_CTRL), np.interp(X_CTRL, xc, f), xc)
    corr = np.where((xc >= X_CTRL[0]) & (xc <= X_CTRL[-1]), fP - f, 0.0)   # undo the raw's own profile between the control points only
    sP = pchip(np.array(X_CTRL), np.array(P["wall_ctrl"]), xc)
    sP = np.where(xc < X_CTRL[0], P["wall_ctrl"][0], np.where(xc > X_CTRL[-1], P["wall_ctrl"][-1], sP))
    e_x = cv2.GaussianBlur((sP + corr).reshape(1, -1).astype(np.float32), (0, 0), sigmaX=2.0, borderType=cv2.BORDER_REPLICATE).ravel()   # 0.1 m
    E_bw = np.interp(np.clip(X, xc[0], xc[-1]), xc, e_x).astype(np.float32)
    sk = Mk["shell_kind"]
    Es = np.full((H, W), P["ceiling"], np.float32)
    bw = np.isin(sk, ["back_wall", "cornice", "skirting"])
    Es[bw] = E_bw[bw]
    Es[sk == "window_wall"] = P["window_wall"]
    Es[sk == "floor"] = P["floor"]
    Es = cv2.GaussianBlur(Es, (0, 0), 1.5)
    ol, I = Mk["obj_label"], Mk["I"]
    Eo = np.full((H, W), P["products"], np.float32)
    Eo[ol == 2] = P["table"]
    Eo[ol == 521] = P["rug"]
    n_, labc = cv2.connectedComponents(Mk["cubes"].astype(np.uint8))
    for i in range(1, n_):
        cxm = np.nonzero(labc == i)[1].mean()
        Eo[labc == i] = P["lamp_faces"][0 if cxm < W * 0.7 else 1]
    Eo[ol == -2] = E_bw[ol == -2]                                   # the triptych hangs flat on the wall: the wall's own light there
    Eo[I == 0] = P["glass"]
    Eo[np.isin(I, [4, 12, 14])] = P["window_arch"]
    Eo = cv2.GaussianBlur(Eo, (0, 0), 1.0)
    sh = Mk["shell"]
    return sh * Es + (1 - sh) * Eo, dict(wall_field_stops_at={f"{x:+.2f}": round(float(v), 3) for x, v in zip(xc[::8], e_x[::8])})


# ---------------------------------------------------------------------------------------------------------------
# the chain
# ---------------------------------------------------------------------------------------------------------------
def s_curve_mid(sr, mix):
    Lm = (sr.max(2) + sr.min(2)) / 2 * 100
    w = np.clip((Lm - 25) / 15, 0, 1) * np.clip((95 - Lm) / 10, 0, 1)
    return sr + w[..., None] * mix * (sr * sr * (3 - 2 * sr) - sr)


def clarity(sr, mask, sigma, amount):
    Lm = (sr * Y).sum(2)
    m = mask.astype(np.float32)
    bl = cv2.GaussianBlur(Lm * m, (0, 0), sigma) / np.maximum(cv2.GaussianBlur(m, (0, 0), sigma), 1e-4)
    det = (Lm - bl) * amount * cv2.GaussianBlur(m, (0, 0), 2.0)
    return np.clip(sr + det[..., None], 0, 1)


def toe(sr, W, lo=12.0, hi=15.0, tgt=13.5, pivot=0.35):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    Lg = Lmap(sr)
    kk = max(4, int(0.005 * W))
    d = float(swv(Lg, (kk, kk))[::4, ::4].mean((2, 3)).min()) / 100
    if lo / 100 <= d <= hi / 100:
        return sr, dict(darkest_before=round(d * 100, 1), applied="none")
    w = np.clip((pivot - sr) / pivot, 0, 1) ** 2
    shift = (tgt / 100 - d) / ((pivot - d) / pivot) ** 2
    return np.clip(sr + shift * w, 0, 1), dict(darkest_before=round(d * 100, 1), to=tgt, pivot_sRGB=pivot, shift=round(float(shift), 4),
                                               how="toe only: sr + shift * ((pivot - sr) / pivot)^2 below the pivot, nothing above it")


def art_curve(sr, Mk, P):
    """per print, inside the frame's inner area (not the oak profile): a monotone curve in L that sets the beige board on 83 and the printed
    passe-partout on 93 (the review's 80-86 / 92-95), the charcoal marks and everything under them unchanged, as a luminance ratio (hue kept)"""
    H, W = sr.shape[:2]
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    L = Lmap(sr)
    out = sr.copy()
    recs = []
    ar = art_regions(H, W)
    for i, q in enumerate(n["placement"]["targets_px"]):
        q = np.array(q, np.float32)
        Hq = cv2.getPerspectiveTransform(np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]), q)
        m = np.zeros((H, W), np.uint8)
        pts = cv2.perspectiveTransform(np.float32([[[0.035, 0.03], [0.965, 0.03], [0.965, 0.97], [0.035, 0.97]]]), Hq)[0]
        cv2.fillConvexPoly(m, np.round(pts * 4).astype(np.int32), 1, shift=2)
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0)
        b, pp = float(np.median(L[ar["board"][i]])), float(np.median(L[ar["passe-partout"][i]]))
        mk = float(np.median(L[ar["marks"][i] & (L < 50)])) if (ar["marks"][i] & (L < 50)).sum() > 20 else 15.0
        xs = [0.0, max(mk + 5, 30.0), b, pp, 100.0]
        ys = [0.0, max(mk + 5, 30.0), P["art_board"], P["art_pp"], 97.5]
        Ln = np.interp(L, xs, ys)
        ratio = np.where(L > 0.5, Ln / np.maximum(L, 0.5), 1.0)
        out = out * (1 + m * (ratio - 1))[..., None]
        recs.append(dict(print=i + 1, board_before=round(b, 1), pp_before=round(pp, 1), curve_L=[[round(x, 1), round(y, 1)] for x, y in zip(xs, ys)]))
    return np.clip(out, 0, 1), dict(prints=recs, how="piecewise-linear in HSL L inside each print (s 0.035-0.965, t 0.03-0.97 of the 50 x 70 frame), "
                                                       "applied as a luminance ratio; the oak profile outside it")


def grade(a, Mk, P, X, prof, rec=None):
    import process_v8 as PV
    H, W = a.shape[:2]
    rec = {} if rec is None else rec
    lin = s2l(a)
    cur = patch(a, 0.4269, 0.4156)
    h, l, s = colorsys.rgb_to_hls(*cur)
    tgt = np.array(colorsys.hls_to_rgb(36 / 360, l, s))
    gain = np.clip((s2l(tgt) / s2l(tgt).dot(Y)) / (s2l(cur) / s2l(cur).dot(Y)), 0.9, 1.1)
    rec["white_balance"] = dict(patch=[0.4269, 0.4156], H_before=round(h * 360, 1), H_target=36, gains_rgb=[round(float(x), 4) for x in gain], as_v5=True)
    lin = lin * gain
    E, erec = exposure_map(P, Mk, X, prof)
    rec["exposure"] = dict(params={k: (round(v, 3) if isinstance(v, float) else [round(x, 3) for x in v]) for k, v in P.items()}, **erec)
    lin = lin * (2.0 ** E)[..., None]
    # the lamps' glow back from the raw (screen in linear light): the raw's excess over the wall's base in the wash fans, scaled
    zs = wash_zones(Mk, H, W)
    rl = s2l(a)
    Yr = (rl * Y).sum(2)
    glow_tot = np.zeros((H, W, 3), np.float32)
    ys_, xs_ = np.mgrid[0:H, 0:W]
    for z in zs:
        x, y, w, h = z["box"]
        hard = cv2.dilate((z["up"] | z["down"] | z["face"]).astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
        wallm = ((Mk["shell"] > 0.98) & ~hard).astype(np.float32)
        num = cv2.GaussianBlur(Yr * wallm, (0, 0), 45)
        den = cv2.GaussianBlur(wallm, (0, 0), 45)
        base = num / np.maximum(den, 1e-4)
        soft = np.exp(-0.5 * (((xs_ - (x + w / 2)) / (1.3 * w)) ** 2 + ((ys_ - (y + h / 2)) / (2.6 * h)) ** 2)).astype(np.float32)
        soft *= (Mk["shell"] > 0.5)
        ex = np.clip(Yr - base, 0, None) / np.maximum(Yr, 1e-5)
        glow_tot += (rl * ex[..., None]) * soft[..., None] * (2.0 ** E)[..., None]
    lin = lin + P["glow"] * glow_tot
    glass = cv2.GaussianBlur((Mk["I"] == 0).astype(np.float32), (0, 0), 1.5)
    Yg = (lin * Y).sum(2)
    ysky = float(np.percentile(Yg[Mk["I"] == 0], 90))
    Lg = l2s(np.clip(Yg, 0, None)) * 100
    wgl = glass * np.clip((Lg - 80) / 8, 0, 1)
    fac = np.where(Yg > 0, (np.clip(Yg / ysky, 1e-4, None) ** (P["glass_gamma"] - 1)), 1.0)
    lin = lin * (1 + wgl * (fac - 1))[..., None]
    rec["window_glass"] = dict(exposure=round(P["glass"], 3), gamma=P["glass_gamma"], anchor="the glass's p90 luminance (the sky)",
                               how="Y' = Y (Y / Y_sky)^(gamma - 1) on the glass only where L > 80 (sky and branches; the leaves and the frame untouched), "
                                   "before the roll-off: the branches come down under the sky, the sky stays the brightest")
    rec["lamp_glow"] = dict(gain=P["glow"], how="the raw's own excess light over the plain wall (the wall in-painted across the fans: normalised blur sigma 45 px "
                                                "of the plain wall round them), in a soft ellipse round each cube (sigma 1.3 cube widths x 2.6 heights), keeping the raw's "
                                                "colour, times the pixel's exposure, added in linear light before the roll-off")
    # chroma: x0.90 off the products (v5's general cut), products keep their raw chroma
    prod = (1 - Mk["shell"]) * (~np.isin(Mk["I"], [0, 4, 12, 14])).astype(np.float32)
    cf = 0.90 + 0.10 * prod
    hh = cv2.cvtColor(np.clip(l2s(lin), 0, 1).astype(np.float32), cv2.COLOR_RGB2HLS)
    sage = ((hh[..., 0] >= 55) & (hh[..., 0] <= 110) & (hh[..., 2] > 0.03)).astype(np.float32) * prod
    sage = cv2.GaussianBlur(sage, (0, 0), 2.0)
    cf = cf * (1 + (P["sage_chroma"] - 1) * sage)
    flo = ((Mk["shell_kind"] == "floor") * Mk["shell"]).astype(np.float32)
    cf = cf * (1 + (P["floor_chroma"] / 0.90 - 1) * flo)
    rec["chroma"] = dict(off_products=0.90, products=1.0, sage_products=P["sage_chroma"], floor=round(P["floor_chroma"], 3),
                         sage="HSL hue 55-110 inside the product masks (Bible: sage S 8-22, never under 8)", floor_why="the oak's S 30-45 after its lift")
    lum = (lin * Y).sum(2, keepdims=True)
    lin = lum + cf[..., None] * (lin - lum)
    sr = np.clip(l2s(lin), 0, 1)
    sr = s_curve_mid(sr, P["s_mix"])
    rec["s_curve"] = dict(mix=P["s_mix"], weight="1 in L 40-85, ramps to 0 at L 25 and L 95 (mid-tones only)")
    sr, rec["triptych_curve"] = art_curve(sr, Mk, P)
    tex = np.isin(Mk["obj_label"], [1, 2, 3, 34, 41, 42, 43, 521]) & (Mk["shell"] < 0.5)
    tex |= (Mk["shell_kind"] == "floor") & (Mk["shell"] > 0.5)
    sr = clarity(sr, tex, 20, P["clarity"])
    sr = clarity(sr, Mk["art"], 8, P["art_clarity"])
    rec["clarity"] = dict(textiles_and_wood=dict(sigma_px=20, amount=P["clarity"], mask="sofa, table, armchair, curtains, throw, cushions, runner, rug, oak floor; "
                                                 "normalised convolution inside the mask (no halo at its edge)"), triptych=dict(sigma_px=8, amount=P["art_clarity"]))
    sr, rec["black_point"] = toe(sr, W)
    lin2 = s2l(sr)
    lin2, rec["near_white_chroma_guard_B4"] = PV.chroma_guard(lin2, a, W)
    lin2 = PV.rolloff(lin2, 0.94, 0.97)
    rec["highlight_rolloff"] = dict(knee_L=94, asymptote_L=97, position="last")
    return np.clip(l2s(lin2), 0, 1).astype(np.float32), rec


# ---------------------------------------------------------------------------------------------------------------
# the solve: the control stops to the targets (secant steps in linear light on the measured points)
# ---------------------------------------------------------------------------------------------------------------
P0 = dict(wall_ctrl=[0.75, 0.27, 0.52], window_wall=0.70, ceiling=0.30, floor=1.0, rug=0.0, table=0.0, products=0.2, lamp_faces=[0.2, 0.2],
          glass=0.15, window_arch=0.2, glow=0.0, s_mix=0.27, clarity=0.12, art_clarity=0.10, sage_chroma=1.2, art_board=83.0, art_pp=93.0,
          floor_chroma=0.80, glass_gamma=1.7)
TGT = dict(corner=91.0, centre=89.5, right=84.0, window=84.0, floor=72.0, rug_minus_floor=9.0, table=67.5, lamp=94.5, glass_margin=3.3)


def step(cur, tgt, s):
    return float(s + np.log2(max(s2l(np.array(tgt / 100.0)), 1e-4) / max(s2l(np.array(cur / 100.0)), 1e-4)))


def solve(a, Mk, X, prof, iters=5):
    P = json.loads(json.dumps(P0))
    hist = []
    for it in range(iters):
        g, _ = grade(a, Mk, P, X, prof)
        m = measure(g, Mk, "iter")
        wv = m["walls"]
        cen = np.mean([v["L"] for k, v in wv.items() if "88-91" in k])
        rgt = np.mean([v["L"] for k, v in wv.items() if "82-86" in k])
        cor = wv[WALL_PTS[0][0]]["L"]
        ww = wv[WALL_PTS[6][0]]["L"]
        fl, fS = m["floor_rug"]["floor by the window (QA box) [L 68-78, S 30-45]: median L / S"]
        rw = m["floor_rug"]["rug by the window floor: median L"]
        tb = m["products"]["table top oak"]["L"]
        lfs = [v["glowing_slot_p97_L"] for v in m["lamps"].values()]
        wmw = min(v["wash_minus_wall"] for v in m["lamps"].values())
        lf = float(np.mean(lfs))
        gl = m["window"]["glass_p50"]
        hist.append(dict(it=it, floor_S=None, branches=m["window"]["branches_vs_sky_upper_glass_p90_minus_p10"], corner=cor, centre=round(cen, 1), right=round(rgt, 1), window_wall=ww, floor=fl, rug=rw, table=tb, lamp=round(lf, 1),
                         glass=gl, walls_max=m["window"]["walls_p99_5"], mean=m["frame"]["mean_L"]))
        hist[-1]["floor_S"] = m["floor_rug"]["floor by the window (QA box) [L 68-78, S 30-45]: median L / S"][1]
        print(hist[-1], flush=True)
        P["wall_ctrl"] = [step(cor, TGT["corner"], P["wall_ctrl"][0]), step(cen, TGT["centre"], P["wall_ctrl"][1]), step(rgt, TGT["right"], P["wall_ctrl"][2])]
        P["window_wall"] = step(ww, TGT["window"], P["window_wall"])
        P["floor"] = step(fl, TGT["floor"], P["floor"])
        P["floor_chroma"] = float(np.clip(P["floor_chroma"] * 40.0 / max(fS, 1), 0.5, 1.0))
        br = m["window"]["branches_vs_sky_upper_glass_p90_minus_p10"]
        if br < 4.5:
            P["glass_gamma"] = float(min(P["glass_gamma"] + 0.3, 3.0))
        P["rug"] = float(np.clip(step(rw, fl + TGT["rug_minus_floor"], P["rug"]), -0.5, 0.2))
        P["table"] = float(np.clip(step(tb, TGT["table"], P["table"]), -0.6, 0.2))
        if wmw < 6.0:
            P["glow"] = float(min(P["glow"] + 0.25, 1.0))
        P["glass"] = float(np.clip(step(min(gl, 99.5), min(m["window"]["walls_p99_5"] + TGT["glass_margin"], 96.7), P["glass"]), -0.5, 1.0))
    return P, hist

# ---------------------------------------------------------------------------------------------------------------
# the run: solve, grade, write, measure (composite / v5 / v6), the mask sheet and the before / after sheet
# ---------------------------------------------------------------------------------------------------------------
def flat_rows(mb, m5, m6):
    """the review's table and the section 4 checks, one row per target: (name, target, composite, v5, v6, ok)"""
    rows = []
    for nm, (u, v), rng, grp in WALL_PTS:
        rows.append((nm.split(" [")[0] + (" " + nm.split("] ")[1] if "] " in nm else ""), f"{rng[0]}-{rng[1]}" if rng else "-",
                     mb["walls"][nm]["L"], m5["walls"][nm]["L"], m6["walls"][nm]["L"], m6["walls"][nm]["ok"]))
    for k, t, ok in (("corner_minus_centre", ">= 1", lambda x: x >= 1), ("centre_minus_right", ">= 3", lambda x: x >= 3)):
        rows.append(("fall-off: " + k.replace("_", " "), t, mb["fall_off"][k], m5["fall_off"][k], m6["fall_off"][k], ok(m6["fall_off"][k])))
    fr = "floor by the window (QA box) [L 68-78, S 30-45]: median L / S"
    rows.append(("oak floor by the window, median L", "68-78", mb["floor_rug"][fr][0], m5["floor_rug"][fr][0], m6["floor_rug"][fr][0], 68 <= m6["floor_rug"][fr][0] <= 78))
    rows.append(("oak floor by the window, S", "30-45", mb["floor_rug"][fr][1], m5["floor_rug"][fr][1], m6["floor_rug"][fr][1], 30 <= m6["floor_rug"][fr][1] <= 45))
    k2 = "floor right strip [L 68-78, S 30-45]: median L / S"
    rows.append(("oak floor right of the sofa (shade), median L", "-", mb["floor_rug"][k2][0], m5["floor_rug"][k2][0], m6["floor_rug"][k2][0], None))
    k3 = "review box (u0.42-0.98, v0.87-0.99): median HSL L / S (82 % of it is the rug)"
    rows.append(("review's 'floor median' box (82 % rug), L", "-", mb["floor_rug"][k3][0], m5["floor_rug"][k3][0], m6["floor_rug"][k3][0], None))
    k4 = "rug minus floor, side by side by the window [6-10]"
    rows.append(("rug minus floor, side by side", "6-10", mb["floor_rug"][k4], m5["floor_rug"][k4], m6["floor_rug"][k4], 6 <= m6["floor_rug"][k4] <= 10))
    w = ("glass_p50", "glass_p99", "walls_p99_5", "glass_p50_minus_brightest_wall", "branches_vs_sky_upper_glass_p90_minus_p10")
    tg = {"glass_p50": "brightest", "glass_p99": "<= 97", "walls_p99_5": "<= 94", "glass_p50_minus_brightest_wall": ">= 3", "branches_vs_sky_upper_glass_p90_minus_p10": ">= 4"}
    okf = {"glass_p50": None, "glass_p99": lambda x: x <= 97, "walls_p99_5": lambda x: x <= 94, "glass_p50_minus_brightest_wall": lambda x: x >= 3,
           "branches_vs_sky_upper_glass_p90_minus_p10": lambda x: x >= 4}
    for k in w:
        rows.append(("window: " + k.replace("_", " "), tg[k], mb["window"][k], m5["window"][k], m6["window"][k], okf[k](m6["window"][k]) if okf[k] else None))
    rows.append(("frame mean L", "76-80", mb["frame"]["mean_L"], m5["frame"]["mean_L"], m6["frame"]["mean_L"], 76 <= m6["frame"]["mean_L"] <= 80))
    rows.append(("share of the frame over L* 90", "-", mb["frame"]["share_Lstar_over_90"], m5["frame"]["share_Lstar_over_90"], m6["frame"]["share_Lstar_over_90"], None))
    k5 = "local_contrast_median (QA: std of L* in 32 px)"
    rows.append(("local contrast (QA)", "-", mb["frame"][k5], m5["frame"][k5], m6["frame"][k5], None))
    k6 = "under the sofa (review box u0.52-0.84, v0.76-0.83): min / p1 [p1 18-22]"
    rows.append(("contact shadow under the sofa, p1", "18-22", mb["shadows"][k6][1], m5["shadows"][k6][1], m6["shadows"][k6][1], 18 <= m6["shadows"][k6][1] <= 22))
    k7 = "darkest 0.5 % patch [12-15, only in the deepest crevice]"
    rows.append(("darkest 0.5 % patch", "12-15", mb["shadows"][k7], m5["shadows"][k7], m6["shadows"][k7], 12 <= m6["shadows"][k7] <= 15))
    for nm, key, rng in (("charcoal cushion", "L", (25, 32)), ("sage cushion", "S", (8, 22)), ("sage runner", "S", (8, 22)), ("table top oak", "L", (60, 72))):
        kk = nm if nm != "charcoal cushion" else "charcoal cushion (QA box)"
        rows.append((f"{nm}, {key}", f"{rng[0]}-{rng[1]}", mb["products"][kk][key], m5["products"][kk][key], m6["products"][kk][key], rng[0] <= m6["products"][kk][key] <= rng[1]))
    for i in (1, 2, 3):
        p_ = f"print {i}"
        for k, t, f in (("board", "80-86", lambda x: 80 <= x <= 86), ("passe-partout", "92-95", lambda x: 92 <= x <= 95), ("marks", "<= 28", lambda x: x is not None and x <= 28),
                        ("oak frame", "62-72", lambda x: 62 <= x <= 72), ("wall minus oak frame [>= 15]", ">= 15", lambda x: x >= 15)):
            rows.append((f"triptych {p_}: {k.split(' [')[0]}", t, mb["triptych"][p_][k], m5["triptych"][p_][k], m6["triptych"][p_][k], f(m6["triptych"][p_][k])))
    for c in ("left cube", "right cube"):
        rows.append((f"{c}: glowing slot L", "93-97", mb["lamps"][c]["glowing_slot_p97_L"], m5["lamps"][c]["glowing_slot_p97_L"], m6["lamps"][c]["glowing_slot_p97_L"],
                     93 <= m6["lamps"][c]["glowing_slot_p97_L"] <= 97))
        rows.append((f"{c}: wash minus wall", ">= 6", mb["lamps"][c]["wash_minus_wall"], m5["lamps"][c]["wash_minus_wall"], m6["lamps"][c]["wash_minus_wall"],
                     m6["lamps"][c]["wash_minus_wall"] >= 6))
    rows.append(("max L / px at 255", "<= 97 / 0", f"{mb['frame']['max_L']} / {mb['frame']['px_255']}", f"{m5['frame']['max_L']} / {m5['frame']['px_255']}",
                 f"{m6['frame']['max_L']} / {m6['frame']['px_255']}", m6["frame"]["max_L"] <= 97.05 and m6["frame"]["px_255"] == 0))
    return rows


def mask_sheet(a, Mk, E, path):
    H, W = a.shape[:2]
    I = Mk["I"]
    glass = np.isin(I, [0, 4, 12, 14])
    tint = np.zeros_like(a)
    tint[..., 2] = Mk["shell"]
    tint[..., 0] = (1 - Mk["shell"]) * (~glass)
    tint[..., 1] = glass
    v1 = np.clip(a * 0.6 + tint * 0.4, 0, 1)
    e = np.clip((E + 0.6) / 1.8, 0, 1)
    v2 = cv2.applyColorMap((e * 255).astype(np.uint8), cv2.COLORMAP_TURBO)[..., ::-1].astype(np.float32) / 255
    v2 = np.clip(v2 * 0.75 + a * 0.25, 0, 1)
    top = np.hstack([cv2.resize(v1, (1368, 770), interpolation=cv2.INTER_AREA), cv2.resize(v2, (1368, 770), interpolation=cv2.INTER_AREA)])
    im = Image.fromarray((top * 255).astype(np.uint8))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    d.text((12, 10), "masks: blue = walls / ceiling / floor (soft), red = products, green = window (clay)", fill=(0, 0, 0), font=f)
    d.text((1380, 10), "exposure map, stops (blue -0.6 ... red +1.2)", fill=(0, 0, 0), font=f)
    im.save(path, quality=88)


def sheet(g5, g6, rows, path):
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    w = 1280
    def fr(img):
        H, W = img.shape[:2]
        x0, y0 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H))
        x1, y1 = int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
        return Image.fromarray((img[y0:y1, x0:x1] * 255 + 0.5).astype(np.uint8)).resize((w, 720), Image.LANCZOS)
    ref = Image.open(GPT_REF).convert("RGB")
    ref = ref.resize((w, int(round(w * ref.size[1] / ref.size[0]))), Image.LANCZOS)
    if ref.size[1] != 720:
        ref = ref.resize((w, 720), Image.LANCZOS)
    rh = 25
    table_h = 60 + rh * (len(rows) + 1)
    out = Image.new("RGB", (2 * w + 30, 60 + 760 + max(820, table_h) + 20), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 14), f"M0 1.2 (seedream shell, composite -fix): grading v5 -> v6 ({DATE}, docs/render-m0-1-2-review-2026-11-05.md section 4; test page V7Q4). "
                     "Not QA'd.", fill=(0, 0, 0), font=fb)
    out.paste(fr(g5), (10, 60))
    out.paste(fr(g6), (w + 20, 60))
    d.text((14, 60 + 724), "v5 (as delivered): one global +0.77 stop", fill=(0, 0, 0), font=f)
    d.text((w + 24, 60 + 724), "v6: fall-off field on the walls, floor / rug / window / products each their own", fill=(0, 0, 0), font=f)
    y0 = 60 + 760
    out.paste(ref, (10, y0))
    d.text((14, y0 + 724), "reference only (geometry wrong: camera 1.1): the old gpt M0 v7 r2 graded, the light the review points to", fill=(0, 0, 0), font=f)
    d.text((14, y0 + 756), "before = the composite m0-1-2-shell-seedream-fix.png (ungraded). The review's 'floor median' box is 82 % rug: the oak is read on the planks.",
           fill=(0, 0, 0), font=f)
    d.text((14, y0 + 784), "Left cube wash: the wall there is ~92 (near the corner) and the roll-off ceiling is 97; the Bible caps a wash at +15 % (~+4 L there).",
           fill=(0, 0, 0), font=f)
    x = w + 20
    cols = [x, x + 560, x + 680, x + 820, x + 930, x + 1040]
    hdr = ["target point", "target", "before", "v5", "v6", "v6 ok"]
    for c, t in zip(cols, hdr):
        d.text((c, y0), t, fill=(0, 0, 0), font=fb)
    for i, r in enumerate(rows):
        yy = y0 + 32 + i * rh
        if i % 2 == 0:
            d.rectangle([x - 4, yy - 2, x + 1270, yy + rh - 4], fill=(244, 244, 244))
        okv = r[5]
        col = (0, 120, 0) if okv is True else ((190, 0, 0) if okv is False else (90, 90, 90))
        vals = [r[0][:58], str(r[1]), str(r[2]), str(r[3]), str(r[4]), "yes" if okv is True else ("NO" if okv is False else "-")]
        for c, t in zip(cols, vals):
            d.text((c, yy), t, fill=col if c == cols[-1] or c == cols[4] else (0, 0, 0), font=fs)
    out.save(path, quality=88)


def run():
    import time
    t0 = time.time()
    a = load(SRC)
    H, W = a.shape[:2]
    if not os.path.exists(SP + "masks.npz"):
        masks(a)
    Mk, mrec = load_masks()
    X, Z = wall_xz(H, W)
    xc, f, prec = wall_profile(s2l(a), Mk, X, Z)
    P, hist = solve(a, Mk, X, (xc, f), iters=6)
    g, rec = grade(a, Mk, P, X, (xc, f))
    E, _ = exposure_map(P, Mk, X, (xc, f))
    base = os.path.join(OD, JID)
    gim = Image.fromarray((g * 255 + 0.5).astype(np.uint8))
    gim.save(base + "-graded-fix-v6.png")
    x0, y0, x1, y1 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
    gim.crop((x0, y0, x1, y1)).save(base + "-frame-fix-v6.png")
    gim.crop((x0, 0, x1, H)).save(base + "-graded-os6-fix-v6.png")
    g8 = np.asarray(Image.open(base + "-graded-fix-v6.png")).astype(np.float32) / 255
    g5 = load(V5)
    mb, m5, m6 = measure(a, Mk, "composite (before grading)"), measure(g5, Mk, "v5"), measure(g8, Mk, "v6")
    rows = flat_rows(mb, m5, m6)
    mask_sheet(a, Mk, E, base + "-masks-fix-v6.jpg")
    sheet(g5, g8, rows, SHEET)
    lost = [r[0] for r in rows if r[5] is False]
    note = dict(asset_id=JID + "-graded-fix-v6", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/grade_v6_m0.py",
                input=OD_REL + JID + "-fix.png", v5_kept=OD_REL + JID + "-graded-fix-v5.png",
                brief=("coordinator 2026-11-05: QA qa/reports/2026-11-05-m0-seedream-fix3-g1.md section 3 and the designer docs/render-m0-1-2-review-2026-11-05.md "
                       "sections 1 and 4: apply section 4 exactly as a new grading v6, v5 kept"),
                bible_rule=("Bible 1.8 B3: +0.2 stop global and +-0.3 local (glass, window wall) in final assets; this is the test page (V7Q4: grading up to the "
                            "Bible targets, the black point and the roll-off kept). The local fields here (the walls' fall-off, the floor +1.1 stop, the rug and "
                            "the table under the raw) are test-page grading only: in a final asset they belong in the source (prompt, light)"),
                findings=["the review's 'floor median' box (u 0.42-0.98, v 0.87-0.99) is 82 % rug: the 68 -> 87.6 of the review is the rug. The oak planks "
                          "themselves read 48 by the window in the composite (35 in the shade right of the sofa) and 66 in v5. v6 sets the planks by the window "
                          "on the oak (72) and the rug 9 L above them, side by side",
                          "the seedream wall is darkest near the corner and brightest at X -1.0..-0.6 (the left cube's broad glow): the fall-off is put back by "
                          "a field of X along the wall that undoes the raw's own profile between the three Bible points (it keeps the raw's shading into "
                          "the corner itself and its vertical structure)",
                          "the triptych hangs on the wall and gets the wall's light at its place (not +0.2 below it, which would grey it against the plaster), "
                          "then a per-print curve that puts the board on 83 and the printed passe-partout on 93 (marks unchanged): print 3 rendered ~0.25 stop "
                          "darker than prints 1-2",
                          "the travertine cubes keep their stone (+0.2 like the products); their glow comes back as the raw's own excess light over the "
                          "in-painted wall, screened back x2 (gain 1.0) in a soft ellipse; the left cube sits where the wall is 92 near the corner, so its "
                          "fan can only reach +4 under the roll-off ceiling 97 (Bible: a wash adds up to 15 %, i.e. ~+4 L on a wall at 91)"],
                masks=mrec, wall_profile=prec, solve=dict(params=P, targets=TGT, iterations=hist), grade=rec,
                measured=dict(composite=mb, v5=m5, v6=m6),
                table=[dict(point=r[0], target=r[1], composite=r[2], v5=r[3], v6=r[4], ok=r[5]) for r in rows], not_met=lost,
                outputs=dict(graded=OD_REL + JID + "-graded-fix-v6.png", frame=OD_REL + JID + "-frame-fix-v6.png", os6=OD_REL + JID + "-graded-os6-fix-v6.png",
                             masks=OD_REL + JID + "-masks-fix-v6.jpg", sheet=os.path.relpath(SHEET, REPO),
                             clay_index=OD_REL + "m0-clay-r5b-index.png"),
                runtime_s=round(time.time() - t0))
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(clean(note), open(base + "-measurements-fix-v6.json", "w"), indent=1, ensure_ascii=False)
    for r in rows:
        print(f"{r[0][:60]:60s} {str(r[1]):10s} {str(r[2]):>12s} {str(r[3]):>12s} {str(r[4]):>12s}  {r[5]}")
    print("not met:", lost)


if __name__ == "__main__":
    os.makedirs(SP, exist_ok=True)
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w == "masks":
        import time
        t = time.time()
        M, rec = masks(load(SRC))
        print(json.dumps(rec), round(time.time() - t, 1), "s")
    if w in ("grade", "all"):
        if w == "all":
            masks(load(SRC))
        run()
    if w == "sheet":
        a = load(SRC)
        Mk, _ = load_masks()
        n = json.load(open(os.path.join(OD, JID + "-measurements-fix-v6.json")))
        rows = [(r["point"], r["target"], r["composite"], r["v5"], r["v6"], r["ok"]) for r in n["table"]]
        sheet(load(V5), load(os.path.join(OD, JID + "-graded-fix-v6.png")), rows, SHEET)
    if w == "probe":
        a = load(SRC)
        Mk, _ = load_masks()
        H, W = a.shape[:2]
        X, Z = wall_xz(H, W)
        xc, f, prec = wall_profile(s2l(a), Mk, X, Z)
        print(json.dumps(prec))
        for nm, (u, v), *_ in WALL_PTS:
            print(nm, "X", round(float(X[int(v * H), int(u * W)]), 2), "Z", round(float(Z[int(v * H), int(u * W)]), 2))
        m = measure(a, Mk, "raw")
        print(json.dumps(m, indent=0)[:6000])
    if w == "solve":
        a = load(SRC)
        Mk, _ = load_masks()
        H, W = a.shape[:2]
        X, Z = wall_xz(H, W)
        xc, f, prec = wall_profile(s2l(a), Mk, X, Z)
        P, hist = solve(a, Mk, X, (xc, f), iters=int(sys.argv[2]) if len(sys.argv) > 2 else 5)
        json.dump(dict(P=P, hist=[{k: (float(v) if not isinstance(v, int) else v) for k, v in h.items()} for h in hist], profile=prec), open(SP + "solve.json", "w"), indent=1)
        g, rec = grade(a, Mk, P, X, (xc, f))
        Image.fromarray((g * 255 + 0.5).astype(np.uint8)).save(SP + "v6-try.png")
        print(json.dumps(P))
