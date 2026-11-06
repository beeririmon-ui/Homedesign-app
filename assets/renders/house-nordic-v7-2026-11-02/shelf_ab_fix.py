#!/usr/bin/env python3
"""
shelf_ab_fix.py: the shelf A/B made faithful to size (QA G1 2026-11-06, §3; render-agent, 0 tokens, new files only).
The seedream shelf pass (m0-shelf-ab-pass.png, 650 tokens, 2026-11-06) drew the group about 1.9x wide: a ~105 cm board ~9 cm thick, the jar ~40 x 30,
the tray as white veined marble. Here, in code, on the fixed M0 frame (m0-1-2-products-fix2-graded-fix-v6.png = A):
  - the wall round is taken off the wall (a smooth fill of the wall round it with the wall's own grain);
  - the board is rebuilt to 55 x 18, 3 thick, top at 1.00 (house plan proposal docs/proposals/living-room-shelf-2026-11-06.md): its three visible
    faces (top, front, right end) projected by the M0 camera, each filled with the pass's oak of that face (perspective warp);
  - each object is cut from the pass (grabCut + thin dark lines for the branch and the reeds) and scaled onto its projected box from the position
    map (m0-shelf-ab-ref-clay.json): the jar to the card's 30 x 15, the column 25, the tray 24, the diffuser;
  - the tray re-coloured to travertine (warm beige, veins softened, fine pits);
  - soft shadows (the board on the wall, the objects to the right, contact on the board), tone matched to A, the area re-graded:
    no pixel at 255, black >= L 12 (the jar L 15-28 as its catalogue note asks).
  python3 shelf_ab_fix.py build | sheet
Outputs: v9/m0-1-2-products-fix2-shelf-graded-v6.png (+ -frame-), v9/m0-shelf-ab-fix.json, assets/renders/house-nordic-m0-shelf-ab-sheet-2026-11-06-fix.jpg
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
import m0_products_pass as PP  # noqa: E402

REPO, OD, OD_REL, DATE = PP.REPO, PP.OD, PP.OD_REL, PP.DATE
A_PATH = os.path.join(OD, "m0-1-2-products-fix2-graded-fix-v6.png")
PASS_REG = os.path.join(OD, "m0-shelf-ab-pass-reg.png")
REF_JSON = os.path.join(OD, "m0-shelf-ab-ref-clay.json")
OUT_ID = "m0-1-2-products-fix2-shelf-graded-v6"
REC = os.path.join(OD, "m0-shelf-ab-fix.json")
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-shelf-ab-sheet-2026-11-06-fix.jpg")
SHELF = dict(x=(-1.65, -1.10), y=(0.0, 0.18), z_top=1.00, t=0.03)
# the pass's objects (canvas px, registered pass): grabCut rectangles; the board's faces as quads (TL, TR, BR, BL)
RECTS = {"jar": (1158, 1260, 686, 834), "column": (1265, 1323, 737, 835), "tray": (1325, 1454, 801, 835), "diffuser": (1359, 1411, 752, 821)}
TRAY_ELLIPSE = ((1389, 819), (59, 13))          # the pass's tray: centre, semi-axes (canvas px)
LINES = {"branch": (1262, 1394, 584, 748), "reeds": (1372, 1402, 704, 772)}
PASS_FACES = {"top": [(1126, 821), (1461, 821), (1468, 832), (1121, 832)], "front": [(1122, 833), (1467, 833), (1467, 861), (1122, 861)],
              "end": [(1469, 833), (1487, 823), (1487, 857), (1469, 861)]}          # inside the pass's board by 1-3 px (its lit bottom edge left out)
Y_ = np.array([0.2126, 0.7152, 0.0722], np.float32)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def load01(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def Lstar(img):
    return cv2.cvtColor(np.clip(img, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)[..., 0]


def to_canvas(P, W=2736, H=1539):
    u, v, d = PP.proj(P)
    return ((u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H)


def grabcut(img, rect, iters=8):
    H, W = img.shape[:2]
    x0, x1, y0, y1 = rect
    m = np.zeros((H, W), np.uint8)
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut((np.clip(img, 0, 1) * 255).astype(np.uint8), m, (x0, y0, x1 - x0, y1 - y0), bg, fg, iters, cv2.GC_INIT_WITH_RECT)
    s = ((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)).astype(np.uint8)
    s = cv2.morphologyEx(s, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(s)
    if n > 1:
        s = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    inv = 1 - s
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 600:
            s[lab == i] = 1
    return s.astype(bool)


def thin_dark(img, rect, excl, thr=7.0, close=(3, 3)):
    """thin dark lines (the branch, the reeds) against the local wall: L below the local median by > thr, small gaps closed"""
    L = Lstar(img)
    x0, x1, y0, y1 = rect
    sub = L[y0:y1, x0:x1]
    med = cv2.medianBlur(np.clip(sub, 0, 100).astype(np.uint8), 31).astype(np.float32)
    m = np.zeros(L.shape, bool)
    m[y0:y1, x0:x1] = (med - sub) > thr
    m &= ~excl
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones(close, np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    keep = np.zeros(L.shape, bool)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 25:
            keep |= lab == i
    return keep


def main_strokes(m, reach=6):
    """the largest stroke and what lies within reach of it (stray chips of wall grain dropped)"""
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n <= 2:
        return m
    big = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    near = cv2.dilate(big.astype(np.uint8), np.ones((2 * reach + 1, 2 * reach + 1), np.uint8)).astype(bool)
    keep = big.copy()
    for i in range(1, n):
        if (lab == i).any() and (near & (lab == i)).any():
            keep |= lab == i
    return keep


def bbox(m):
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1


def place(img, mask, src_box, dst_box, H, W, extra=None):
    """non-uniform scale of the sprite (premultiplied) from its bbox onto the target box; extra masks ride the same transform"""
    sx0, sx1, sy0, sy1 = src_box
    dx0, dx1, dy0, dy1 = dst_box
    ax, ay = (dx1 - dx0) / (sx1 - sx0), (dy1 - dy0) / (sy1 - sy0)
    A = np.array([[ax, 0, dx0 - ax * sx0], [0, ay, dy0 - ay * sy0]], np.float32)
    al = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.6)
    pm = cv2.warpAffine(img * al[..., None], A, (W, H), flags=cv2.INTER_AREA if max(ax, ay) < 1 else cv2.INTER_LANCZOS4)
    a = np.clip(cv2.warpAffine(al, A, (W, H), flags=cv2.INTER_AREA if max(ax, ay) < 1 else cv2.INTER_LINEAR), 0, 1)
    col = np.clip(pm / np.maximum(a[..., None], 1e-4), 0, 1)
    out = [col, a, A]
    if extra is not None:
        out.append(np.clip(cv2.warpAffine(extra.astype(np.float32), A, (W, H), flags=cv2.INTER_AREA if max(ax, ay) < 1 else cv2.INTER_LINEAR), 0, 1))
    return out


def board_quads(W, H):
    sx0, sx1 = SHELF["x"]
    y0, y1 = SHELF["y"]
    zt, zb = SHELF["z_top"], SHELF["z_top"] - SHELF["t"]
    c = lambda X, Y, Z: to_canvas((X, Y, Z), W, H)
    return {"top": [c(sx0, y0, zt), c(sx1, y0, zt), c(sx1, y1, zt), c(sx0, y1, zt)],
            "front": [c(sx0, y1, zt), c(sx1, y1, zt), c(sx1, y1, zb), c(sx0, y1, zb)],
            "end": [c(sx1, y1, zt), c(sx1, y0, zt), c(sx1, y0, zb), c(sx1, y1, zb)]}


def warp_face(src, q_src, q_dst, H, W):
    M = cv2.getPerspectiveTransform(np.float32(q_src), np.float32(q_dst))
    img = cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_AREA)
    m = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(m, np.round(np.float32(q_dst) * 8).astype(np.int32), 1, shift=3)
    return img, m.astype(np.float32)


def fill_wall(A, mask):
    """the wall under the mask: a smooth fill (Telea at quarter size, upsampled) plus the wall's grain from beside it"""
    H, W = A.shape[:2]
    small = cv2.resize((A * 255).astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    ms = cv2.dilate(cv2.resize(mask.astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
    fs = cv2.inpaint(small, ms, 9, cv2.INPAINT_TELEA)
    low = cv2.GaussianBlur(cv2.resize(fs, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255, (0, 0), 6)
    hp = A - cv2.GaussianBlur(A, (0, 0), 4)
    ys, xs = np.nonzero(mask)
    grain = np.roll(hp, xs.max() - xs.min() + 40, axis=1)              # the grain of the wall left of the hole
    out = A.copy()
    a = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 3)[..., None]
    out = out * (1 - a) + np.clip(low + grain, 0, 1) * a
    return out


def build():
    A = load01(A_PATH)
    H, W = A.shape[:2]
    pr = load01(PASS_REG)
    ref = json.load(open(REF_JSON))["boxes_canvas_uv"]
    tbox = {k: (int(round(v[0] * W)), int(round(v[1] * W)), int(round(v[2] * H)), int(round(v[3] * H))) for k, v in ref.items()}
    rec = dict(asset_id="m0-shelf-ab-fix", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/shelf_ab_fix.py",
               qa="qa/reports/2026-11-06-m0-products-shelf-styles.md (G1, section 3)", A=os.path.relpath(A_PATH, REPO),
               pass_registered=os.path.relpath(PASS_REG, REPO), spec="docs/proposals/living-room-shelf-2026-11-06.md: 55 x 18, 3 thick, top at 1.00, X -1.65..-1.10",
               target_boxes_canvas_px=tbox)
    # tone: the pass onto A's tone (linear gain per channel on the wall round the group, the round and the sconce left out)
    ring = np.zeros((H, W), bool)
    ring[560:900, 1050:1560] = True
    ring[640:880, 1110:1500] = False
    sel = ring & (pr.min(2) > 0.3) & (pr.max(2) < 0.97) & (A.min(2) > 0.3) & (A.max(2) < 0.97)
    gains = np.array([float(np.median(s2l(A[..., c][sel]) / np.maximum(s2l(pr[..., c][sel]), 1e-4))) for c in range(3)], np.float32)
    pt = np.clip(l2s(s2l(pr) * gains), 0, 1).astype(np.float32)
    rec["tone_gains_rgb"] = [round(float(g), 4) for g in gains]
    # 1. the wall round off the wall (its ellipse and its soft shadow)
    rr = json.load(open(os.path.join(OD, "m0-1-2-shell-seedream-fix-base.json")))["wall_round"]["target"]
    rnd = np.zeros((H, W), np.uint8)
    cv2.ellipse(rnd, ((rr["centre_px"][0] + 4, rr["centre_px"][1] + 3), (rr["axes_px"][0] + 34, rr["axes_px"][1] + 34), 0), 1, -1)
    B = fill_wall(A, rnd.astype(bool))
    rec["round_removed"] = dict(centre_px=rr["centre_px"], axes_px=rr["axes_px"], fill="Telea at 1/4 size, upsampled, + the wall's grain from its left")
    # 2. the sprites from the pass
    sp = {k: grabcut(pt, r) for k, r in RECTS.items() if k != "tray"}
    # the tray: a thin oval on the board, grabCut finds nothing in so flat a box; its outline read on the pass (an ellipse), the diffuser left out
    tm = np.zeros((H, W), np.uint8)
    cv2.ellipse(tm, TRAY_ELLIPSE[0], TRAY_ELLIPSE[1], 0, 0, 360, 1, -1)
    sp["tray"] = tm.astype(bool) & ~cv2.dilate(sp["diffuser"].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    excl = np.zeros((H, W), bool)
    for m in sp.values():
        excl |= cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    branch = main_strokes(thin_dark(pt, LINES["branch"], excl))
    excl_r = np.zeros((H, W), bool)
    for k in ("jar", "column", "tray"):
        excl_r |= cv2.dilate(sp[k].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    reeds = main_strokes(thin_dark(pt, LINES["reeds"], excl_r | sp["diffuser"], close=(9, 1)), reach=14)
    # 3. the board: its three faces, projected, filled from the pass's faces
    q = board_quads(W, H)
    rec["board_quads_canvas_px"] = {k: [[round(x, 1), round(y, 1)] for x, y in v] for k, v in q.items()}
    board = np.zeros((H, W, 3), np.float32)
    ba = np.zeros((H, W), np.float32)
    for k in ("end", "top", "front"):
        img, m = warp_face(pt, PASS_FACES[k], q[k], H, W)
        board = board * (1 - m[..., None]) + img * m[..., None]
        ba = np.maximum(ba, m)
    ba = cv2.GaussianBlur(ba, (0, 0), 0.5)
    # 4. the objects onto their boxes (bottom on the board's top)
    objs = {}
    bx0, bx1, by0, by1 = bbox(sp["column"])
    col_c, col_a, Acol, br_a = place(pt, sp["column"], (bx0, bx1, by0, by1), tbox["column"], H, W, extra=branch)
    objs["column"] = (col_c, col_a)
    br_c = cv2.warpAffine(pt, Acol, (W, H), flags=cv2.INTER_AREA)
    objs["branch"] = (br_c, br_a)
    for k in ("jar", "tray"):
        c_, a_, _ = place(pt, sp[k], bbox(sp[k]), tbox[k], H, W)
        objs[k] = (c_, a_)
    # the diffuser: its vessel onto the vessel's own box (7 x 10.2 cm on the tray), the reeds riding the same transform
    tb = tbox["diffuser"]
    vh = int(round((1.12 - 1.018) * (tb[3] - tb[2]) / (1.22 - 1.018)))
    c_, a_, Ad, ra = place(pt, sp["diffuser"], bbox(sp["diffuser"]), (tb[0], tb[1], tb[3] + 2 - vh, tb[3] + 2), H, W, extra=reeds)
    rc = cv2.warpAffine(pt, Ad, (W, H), flags=cv2.INTER_AREA)
    objs["reeds"] = (rc, ra)
    objs["diffuser"] = (c_, a_)
    # the tray to travertine: warm beige, the veins softened, fine pits
    tc, ta = objs["tray"]
    lab = cv2.cvtColor(tc, cv2.COLOR_RGB2LAB)
    m_ = ta > 0.5
    Lm = float(np.median(lab[..., 0][m_]))
    lab[..., 0] = np.where(m_, Lm + 0.45 * (lab[..., 0] - Lm), lab[..., 0])
    lab[..., 1] = np.where(m_, 0.15 * lab[..., 1] + 0.85 * 3.5, lab[..., 1])
    lab[..., 2] = np.where(m_, 0.15 * lab[..., 2] + 0.85 * 15.0, lab[..., 2])
    rng = np.random.default_rng(3)
    pits = (rng.random((H, W)) < 0.04) & m_
    lab[..., 0] = np.where(pits, lab[..., 0] - 6, lab[..., 0])
    objs["tray"] = (np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1), ta)
    rec["tray_recolour"] = dict(L_median=round(Lm, 1), contrast=0.45, a_b_target=[3.5, 15.0], pits="4 % of the pixels, -6 L",
                                why="QA: the pass's tray reads as white marble with grey veins; the card is travertine")
    # 5. shadows: the board on the wall (soft, under it), the objects to the right (window light), contact on the board's top
    allobj = np.zeros((H, W), np.float32)
    for k, (c_, a_) in objs.items():
        allobj = np.maximum(allobj, a_)
    under = np.zeros((H, W), np.float32)
    fr = np.float32(q["front"])
    xs0, xs1 = int(fr[:, 0].min()), int(fr[:, 0].max())
    ybot = int(round(max(fr[2][1], fr[3][1])))
    for i in range(14):
        under[ybot + i, xs0 + 2:xs1 - 2] = math.exp(-i / 5.0)
    under = cv2.GaussianBlur(under, (0, 0), 3) * (1 - ba)
    sh = cv2.GaussianBlur(np.roll(allobj, 6, axis=1), (0, 0), 5) * (1 - allobj) * (1 - ba)
    dark = 1 - 0.28 * np.clip(under, 0, 1) - 0.12 * np.clip(sh, 0, 1)
    B = np.clip(l2s(s2l(B) * dark[..., None]), 0, 1)
    B = B * (1 - ba[..., None]) + board * ba[..., None]
    contact = np.zeros((H, W), np.float32)
    for k in ("jar", "column", "tray", "diffuser"):
        ys, xs = np.nonzero(objs[k][1] > 0.5)
        if len(ys):
            contact[ys.max() - 1:ys.max() + 3, xs.min():xs.max() + 1] = 1
    contact = cv2.GaussianBlur(contact, (0, 0), 1.5) * ba
    B = np.clip(l2s(s2l(B) * (1 - 0.3 * contact)[..., None]), 0, 1)
    for k in ("branch", "jar", "column", "tray", "reeds", "diffuser"):
        c_, a_ = objs[k]
        B = B * (1 - a_[..., None]) + c_ * a_[..., None]
    # 6. re-grade the shelf area: black >= L 12 (the jar's darks compressed into L 12-20), highlights below 255 (a soft knee from 0.94)
    grp = cv2.dilate(((allobj > 0.02) | (ba > 0.02) | (under > 0.02) | (sh > 0.02) | rnd.astype(bool)).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    L = Lstar(B)
    Ln = np.where(L < 20, 12 + L * 0.4, L)
    lin = s2l(B)
    Yc = np.maximum((lin * Y_).sum(2), 1e-6)
    Yn = ((Ln + 16) / 116) ** 3
    Yn = np.where(Ln <= 8, Ln / 903.3, Yn)
    Bn = np.clip(l2s(lin * (Yn / Yc)[..., None]), 0, 1)
    mx = Bn.max(2, keepdims=True)
    knee = np.where(mx > 0.94, 0.94 + (0.98 - 0.94) * np.tanh((mx - 0.94) / 0.04), mx)
    Bn = Bn * (knee / np.maximum(mx, 1e-6))
    B = np.where(grp[..., None], Bn, B)
    out = np.clip(B, 0, 1)
    p = os.path.join(OD, OUT_ID + ".png")
    o8 = (out * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(p)
    fx0, fy0, fx1, fy1 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H))
    Image.fromarray(o8).crop((fx0, fy0, fx1, fy1)).save(p.replace("-graded-v6", "-frame-v6"))
    # checks: what changed (only the group's area), the group's sizes against the spec, 255 and the black point in it
    d = np.abs(out - A).max(2) * 255
    zone = cv2.dilate(grp.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    fr_ = np.zeros((H, W), bool)
    fr_[fy0:fy1, fx0:fx1] = True
    ys, xs = np.nonzero(d > 1.5)
    Lo = Lstar(out)
    sizes = {}
    for k in ("jar", "column", "tray", "diffuser"):
        x0, x1, y0, y1 = bbox(objs[k][1] > 0.5)
        tx0, tx1, ty0, ty1 = tbox[k]
        sizes[k] = dict(drawn_px=[x1 - x0, y1 - y0], spec_px=[tx1 - tx0, ty1 - ty0])
    x0, x1, y0, y1 = bbox(ba > 0.5)
    tx0, tx1, ty0, ty1 = tbox["shelf"]
    sizes["shelf"] = dict(drawn_px=[x1 - x0, y1 - y0], spec_px=[tx1 - tx0, ty1 - ty0], front_face_px=round(float(fr[2][1] - fr[1][1]), 1))
    jar = objs["jar"][1] > 0.7
    rec.update(sizes=sizes, changed_px_canvas_uv=[round(xs.min() / W, 3), round(xs.max() / W, 3), round(ys.min() / H, 3), round(ys.max() / H, 3)],
               nothing_else_moved=dict(rule="max |delta| against A outside the group's area (+12 px)", mean_outside=round(float(d[fr_ & ~zone].mean()), 4),
                                       max_outside=round(float(d[fr_ & ~zone].max()), 2)),
               regrade=dict(at_255_in_area=int((o8[grp].max(1) >= 255).sum()), black_p01_in_area=round(float(np.percentile(Lo[grp], 0.1)), 1),
                            jar_L_median=round(float(np.median(Lo[jar])), 1), jar_L_p1=round(float(np.percentile(Lo[jar], 1)), 1),
                            how="L < 20 -> 12 + 0.4 L (the darks into 12-20), a soft knee on the brightest channel from 0.94 (max 0.98)"),
               output=OD_REL + OUT_ID + ".png", frame=OD_REL + OUT_ID.replace("-graded-v6", "-frame-v6") + ".png")
    json.dump(rec, open(REC, "w"), indent=1)
    S = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/"
    vis = (pt * 255).astype(np.uint8).copy()
    for k, m in list(sp.items()) + [("branch", branch), ("reeds", reeds)]:
        e = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        vis[e] = (255, 0, 0)
    Image.fromarray(vis[560:900, 1080:1540]).save(S + "shelf-sprites.png")
    print(json.dumps(dict(sizes=sizes, nem=rec["nothing_else_moved"], regrade=rec["regrade"], gains=rec["tone_gains_rgb"]), indent=0))


def sheet():
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    A = Image.open(A_PATH).convert("RGB")
    B = Image.open(os.path.join(OD, OUT_ID + ".png")).convert("RGB")
    W, H = A.size
    box = (int(round(116 / 4072 * W)), int(round(65 / 2290 * H)), int(round(3956 / 4072 * W)), int(round(2225 / 2290 * H)))
    Af, Bf = A.crop(box).resize((1280, 720), Image.LANCZOS), B.crop(box).resize((1280, 720), Image.LANCZOS)
    zb = (int(0.38 * W), int(0.38 * H), int(0.58 * W), int(0.62 * H))
    zs = (1280, int(1280 * (zb[3] - zb[1]) / (zb[2] - zb[0])))
    Az, Bz = A.crop(zb).resize(zs, Image.LANCZOS), B.crop(zb).resize(zs, Image.LANCZOS)
    rec = json.load(open(REC))
    out = Image.new("RGB", (2 * 1280 + 30, 60 + 720 + 40 + zs[1] + 100), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 16), f"M0 1.2, shelf A/B, true to size ({DATE}): A = the wall round (fixed M0, graded v6) | B = a 55 x 18 oak shelf, 3 thick, top at 1.00, "
                     "jar 30 x 15, column 25, travertine tray 24, diffuser. Not QA'd.", fill=(0, 0, 0), font=fb)
    out.paste(Af, (10, 60))
    out.paste(Bf, (1300, 60))
    d.text((14, 784), "A: round", fill=(0, 0, 0), font=f)
    d.text((1304, 784), "B: shelf (in code from the seedream pass, scaled to the spec)", fill=(0, 0, 0), font=f)
    out.paste(Az, (10, 820))
    out.paste(Bz, (1300, 820))
    s = rec["sizes"]
    line = ("Drawn vs spec (canvas px): " + "; ".join(f"{k} {v['drawn_px'][0]}x{v['drawn_px'][1]} vs {v['spec_px'][0]}x{v['spec_px'][1]}" for k, v in s.items())
            + f". Area re-graded: {rec['regrade']['at_255_in_area']} px at 255, black p0.1 L {rec['regrade']['black_p01_in_area']}, jar L {rec['regrade']['jar_L_median']}.")
    d.text((10, 820 + zs[1] + 12), line, fill=(0, 0, 0), font=f)
    d.text((10, 820 + zs[1] + 46), f"Outside the group's area B = A (mean |delta| {rec['nothing_else_moved']['mean_outside']}, max {rec['nothing_else_moved']['max_outside']}).",
           fill=(0, 0, 0), font=f)
    out.save(SHEET, quality=88)
    print(SHEET)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "build":
        build()
    if w == "sheet":
        sheet()
