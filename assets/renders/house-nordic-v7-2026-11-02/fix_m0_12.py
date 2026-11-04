#!/usr/bin/env python3
"""
fix_m0_12.py: M0 1.2 in code (briefs/render-m0-composite-and-cleanup-2026-11-04.md task 1; render-agent, 2026-11-04; 0 var2 tokens).

The model enlarged the living fixed furniture in every M0 1.2 attempt (m0-v8b, m0-v8b-r2, pose-m0p-v8b) while the shell, the window,
the armchair and the pendant landed on the clay; as in fix_v7.py (M0 r2) and fix_v8.py (B1 r3, W0-in r2), the pieces are put back on
the round-5b clay in code:
  m0   (on m0-v8b-r2, the reserve: the closest): the sofa group (sofa, back and scatter cushions, throw, legs and the shadow under its
       base) scaled uniformly about the mid-point of its measured outline and moved so its arms, back top and front-leg foot land on the
       clay's; the coffee-table group (oak table, runner, candle holders, bowl) scaled about its near legs onto the clay table; the holes
       filled by zone as in fix_v7 (wall column-wise from above with the wall's texture, skirting / floor / rug row-wise with their
       textures), the sofa's shadow on the wall and the floor carried as a ratio map with it;
  m0p  (on pose-m0p-v8b): the same for its sofa group and table;
  m0x  (on pose-m0x-v8b): one vertical affine (the frame's shift / scale from lock_v2's register).
Outputs next to each render: <id>-fix.png, <id>-fix.json (what, how, the numbers). The raw renders are never overwritten.
  python3 fix_m0_12.py m0 | m0p | m0x | all
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_v7 as F  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
R5B = os.path.join(REPO, "assets", "blockout", "house", "framing", "round5b")
OUT = {"m0-v8b-r2": "assets/renders/living-room/nordic/v8/", "pose-m0p-v8b": "assets/renders/poses/nordic/v8/", "pose-m0x-v8b": "assets/renders/poses/nordic/v8/"}
CLAY = {"m0-v8b-r2": "M0.png", "pose-m0p-v8b": "poses/M0p.png", "pose-m0x-v8b": "poses/M0x.png"}
FRAME = {"m0-v8b-r2": "M0", "pose-m0p-v8b": "M0p", "pose-m0x-v8b": "M0x"}
DATE = "2026-11-04"


def still(jid):
    return F.load(os.path.join(REPO, OUT[jid], jid + ".png"))


def clay(jid, W, H):
    from PIL import Image
    im = Image.open(os.path.join(R5B, CLAY[jid])).convert("RGB").resize((W, H), Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


def out_fix(jid):
    return os.path.join(REPO, OUT[jid], jid + "-fix.png")


def gray(a):
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def hls(a):
    h = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    return h[..., 0] * 2, h[..., 1] / 2.55, h[..., 2] / 2.55


def energy(a, sigma=4.0):
    g = gray(a)
    hp = g - cv2.GaussianBlur(g, (0, 0), 2.0)
    return np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), sigma))


def dil(m, k):
    return cv2.dilate((m > 0.5).astype(np.uint8), np.ones((2 * k + 1, 2 * k + 1), np.uint8)).astype(np.float32)


def fill_holes(m):
    ff = ((m > 0.5) * 255).astype(np.uint8)
    h, w = ff.shape
    mask = np.zeros((h + 2, w + 2), np.uint8)
    inv = ff.copy()
    cv2.floodFill(inv, mask, (0, 0), 255)
    return np.maximum((m > 0.5).astype(np.float32), (cv2.bitwise_not(inv) > 0).astype(np.float32))


def line_y(x, p0, p1):
    return p0[1] + (x - p0[0]) * (p1[1] - p0[1]) / (p1[0] - p0[0])


def affine(scale, anchor, dx, dy, sy=None):
    sx = scale
    sy = scale if sy is None else sy
    ax, ay = anchor
    return np.float32([[sx, 0, ax - sx * ax + dx], [0, sy, ay - sy * ay + dy]])


def warp(img, M, W, H, interp=None):
    flags = interp if interp is not None else (cv2.INTER_AREA if M[0, 0] < 1 else cv2.INTER_CUBIC)
    return cv2.warpAffine(img, M, (W, H), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def edges_v(g, r0, r1, c0, c1):
    p = np.abs(np.diff(g[r0:r1], axis=1)).mean(0)
    return c0 + int(np.argmax(p[c0:c1]))


def edges_h(g, c0, c1, r0, r1):
    p = np.abs(np.diff(g[:, c0:c1], axis=0)).mean(1)
    return r0 + int(np.argmax(p[r0:r1]))


def save_note(jid, note):
    note = dict(asset_id=jid + "-fix", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/fix_m0_12.py", **note)
    json.dump(note, open(os.path.join(REPO, OUT[jid], jid + "-fix.json"), "w"), indent=1, ensure_ascii=False)


# ---------------------------------------------------------------------------------------------------------------
# M0 (m0-v8b-r2): measured outlines (canvas px of the 2736 x 1539 still; render / clay), the sofa base line and feet line
# ---------------------------------------------------------------------------------------------------------------
M0 = dict(
    sofa_render=dict(arm_l=1246, arm_r=2483, back_top=832, foot_r=1354, base_l=(1246, 1171), base_r=(2483, 1272), feet_l=(1282, 1203), feet_r=(2445, 1356)),
    sofa_rect=(1236, 2600, 790, 1365), throw_rect=(2440, 2600, 1080, 1350), leg_l=(1266, 1298, 1165, 1208), leg_r=(2420, 2468, 1262, 1360),
    table_rect=(1240, 2232, 1035, 1539), runner_poly=[(1365, 1128), (1612, 1128), (1600, 1300), (1597, 1415), (1368, 1415), (1368, 1300)],
    bowl_rect=(1945, 2120, 1160, 1278), holders_rect=(1812, 1950, 1035, 1250), table_near_edge=1318)


def sofa_matte_m0(a, table):
    H, W = a.shape[:2]
    p = M0["sofa_render"]
    en = energy(a, 1.5)
    x0, x1, y0, y1 = M0["sofa_rect"]
    m = np.zeros((H, W), np.float32)
    X = np.arange(W)[None, :]
    Y = np.arange(H)[:, None]
    base = line_y(X, p["base_l"], p["base_r"])
    feet = line_y(X, p["feet_l"], p["feet_r"])
    tex = (en > 1.6).astype(np.float32)
    region = ((X >= p["arm_l"] - 2) & (X <= p["arm_r"] + 2) & (Y >= y0) & (Y <= base + 1)).astype(np.float32)
    body = tex * region
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(body)
    body = (lab_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))).astype(np.float32)      # the sofa: one body (no light-fan noise on the wall)
    # per column: everything from the first textured row down to the base line (the fabric's quiet patches are inside)
    top = np.full(W, -1)
    for x in range(p["arm_l"] - 2, p["arm_r"] + 3):
        ys = np.nonzero(body[y0:, x] > 0.5)[0]
        if len(ys):
            top[x] = y0 + ys[0]
    for x in range(W):
        if top[x] >= 0:
            m[top[x]:int(round(base[0, x])) + 1, x] = 1
    # the throw hanging outside the right arm: grabCut in its rect, seeded with the arm's edge as sure foreground and the wall /
    # skirting / floor beyond as sure background
    tx0, tx1, ty0, ty1 = M0["throw_rect"]
    _, L, S = hls(a)
    sub = np.ascontiguousarray(np.clip(a[ty0:ty1, tx0:tx1, ::-1], 0, 255).astype(np.uint8))
    gm = np.full(sub.shape[:2], cv2.GC_PR_BGD, np.uint8)
    gm[:, max(0, p["arm_r"] - 30 - tx0):p["arm_r"] + 6 - tx0] = cv2.GC_PR_FGD
    gm[:, 2575 - tx0:] = cv2.GC_BGD
    gm[:40, p["arm_r"] + 20 - tx0:] = cv2.GC_BGD
    gm[60:200, p["arm_r"] + 8 - tx0:p["arm_r"] + 40 - tx0] = cv2.GC_PR_FGD
    bg_, fg_ = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(sub, gm, None, bg_, fg_, 8, cv2.GC_INIT_WITH_MASK)
    throw = np.zeros((H, W), np.float32)
    throw[ty0:ty1, tx0:tx1] = ((gm == cv2.GC_FGD) | (gm == cv2.GC_PR_FGD)).astype(np.float32)
    throw = throw * (X > p["arm_r"] - 2)
    throw = fill_holes(cv2.morphologyEx(throw.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32))
    m = np.maximum(m, throw)
    # the legs (dark oak) and the dark band under the base down to the feet line (its contact shadow goes with it)
    for (lx0, lx1, ly0, ly1) in (M0["leg_l"], M0["leg_r"]):
        m[ly0:ly1, lx0:lx1] = np.maximum(m[ly0:ly1, lx0:lx1], (L[ly0:ly1, lx0:lx1] < 55).astype(np.float32))
    under = ((Y > base) & (Y <= feet) & (X >= p["arm_l"]) & (X <= p["arm_r"])).astype(np.float32) * (L < 40)
    m = np.maximum(m, under)
    m = fill_holes(m) * (1 - (table > 0.5))
    return m, dict(base=[p["base_l"], p["base_r"]], feet=[p["feet_l"], p["feet_r"]])


def table_matte_m0(a):
    H, W = a.shape[:2]
    Hh, L, S = hls(a)
    x0, x1, y0, y1 = M0["table_rect"]
    rect = F.rect_mask(H, W, x0 / W, x1 / W, y0 / H, y1 / H)
    oak = ((Hh >= 18) & (Hh <= 42) & (S >= 34) & (L >= 25) & (L <= 88)).astype(np.float32) * rect
    oak = cv2.morphologyEx(oak.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    oak = cv2.morphologyEx(oak, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(np.float32)
    n, lab, st, _ = cv2.connectedComponentsWithStats((oak > 0.5).astype(np.uint8))
    keep = np.zeros((H, W), np.float32)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 800:
            keep[lab == i] = 1
    # the top: the convex hull of the oak above its near edge (a rounded rectangle in perspective), so its highlights and the
    # runner's shadow are inside; the legs: oak pixels (S >= 26) below it, closed vertically
    top_rows = keep * (np.arange(H)[:, None] < M0["table_near_edge"])
    ys, xs = np.nonzero(top_rows > 0.5)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    top = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(top, hull, 1)
    legs = ((Hh >= 18) & (Hh <= 42) & (S >= 26) & (L >= 20) & (L <= 80)).astype(np.float32) * rect * (np.arange(H)[:, None] >= M0["table_near_edge"] - 10)
    legs = cv2.morphologyEx(legs.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 5), np.uint8))
    legs = cv2.morphologyEx(legs, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(np.float32)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats((legs > 0.5).astype(np.uint8))
    legs_k = np.zeros((H, W), np.float32)
    for i in range(1, n2):
        if st2[i, cv2.CC_STAT_HEIGHT] > 60 and st2[i, cv2.CC_STAT_WIDTH] < 70:
            legs_k[lab2 == i] = 1
    keep = np.maximum(top.astype(np.float32), legs_k)
    runner = np.zeros((H, W), np.uint8)
    cv2.fillPoly(runner, [np.array(M0["runner_poly"], np.int32)], 1)
    runner = runner.astype(np.float32) * (np.arange(H)[:, None] >= ys.min())
    bowl = F.grabcut(a, (M0["bowl_rect"][0] / W, M0["bowl_rect"][1] / W, M0["bowl_rect"][2] / H, M0["bowl_rect"][3] / H), iters=6, pad_uv=0.006, open_px=3)
    hold = F.grabcut(a, (M0["holders_rect"][0] / W, M0["holders_rect"][1] / W, M0["holders_rect"][2] / H, M0["holders_rect"][3] / H), iters=6, pad_uv=0.006, open_px=3)
    t = np.maximum.reduce([keep, runner.astype(np.float32), bowl, hold])
    t = fill_holes(cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32))
    return t


def debug_m0():
    jid = "m0-v8b-r2"
    a = still(jid)
    H, W = a.shape[:2]
    table = table_matte_m0(a)
    sofa, info = sofa_matte_m0(a, table)
    vis = a.copy()
    vis[sofa > 0.5] = vis[sofa > 0.5] * 0.55 + np.array([255, 0, 0]) * 0.45
    vis[table > 0.5] = vis[table > 0.5] * 0.55 + np.array([0, 0, 255]) * 0.45
    F.save(vis[700:1539, 1100:2700], "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/m0c/mattes2.png")
    print(F.bbox(sofa), F.bbox(table))
