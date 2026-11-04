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
    sofa_rect=(1236, 2600, 790, 1365), throw_rect=(2440, 2600, 960, 1350), leg_l=(1266, 1298, 1165, 1208), leg_r=(2420, 2468, 1262, 1360),
    table_rect=(1240, 2232, 1035, 1539), runner_poly=[(1365, 1128), (1612, 1128), (1600, 1300), (1597, 1415), (1368, 1415), (1368, 1300)],
    bowl_rect=(1945, 2120, 1160, 1278), holders_rect=(1812, 1950, 1035, 1250),
    table_near_line=((1300, 1247.0), (2000, 1318.0)),
    # the back wall's lines and the rug's far edge (canvas px, measured on the still: |d/dy| maxima of columns either side of the sofa)
    throw_fringe_box=(2478, 2590, 1325, 1362),
    skirting_line=((1100, 1090.0), (2635, 1201.5)), floor_line=((1100, 1130.5), (2635, 1257.0)), rug_line=((1150, 1222.0), (2650, 1353.0)))


# the clay targets (round-5b M0.png at the still's size; the same column / row edge measurements): sofa arms' outer edges, the middle
# back cushion's top, the right front foot; the table top's ends and far edge, the near-left leg's foot
M0_CLAY = dict(sofa=dict(arm_l=1290, arm_r=2373, back_top=941, foot_r=1407),
               table=dict(x0=1260, x1=2145, far=1176, foot_l=1468))
M0_TABLE_R = dict(x0=1256, x1=2204, far=1118, foot_l=1452)
M0_TEX = dict(wall=(2560, 620, 2720, 760), floor=(2612, 1262, 2730, 1342), rug=(2250, 1420, 2450, 1530), sofa_base=(2210, 1190, 2400, 1250))


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
    # the throw hanging outside the right arm, row by row: the run of textured fabric from the arm's outer edge (energy > 2,
    # the plain wall ~1) above the floor line, of cream fabric (S < 25; the oak floor S 27-31) below it, down to the rug's edge;
    # the edge median-filtered over 31 rows (the skirting's edge line is ~10 rows of energy)
    _, L, S = hls(a)
    en2 = energy(a, 2.0)
    tx0, tx1, ty0, ty1 = M0["throw_rect"]
    edge = np.full(H, -1)
    for y in range(ty0, ty1):
        if y >= line_y(p["arm_r"] + 40, *M0["rug_line"]) - 2:
            break
        floor_row = y >= line_y(p["arm_r"] + 40, *M0["floor_line"]) + 2
        x = p["arm_r"] - 2
        gap = 0
        last = x
        while x < tx1:
            ok = (S[y, x] < 26 and L[y, x] > 44) if floor_row else (en2[y, x] > 2.0)
            if ok:
                last = x
                gap = 0
            else:
                gap += 1
                if gap > (24 if floor_row else 3):
                    break
            x += 1
        edge[y] = last
    # the skirting's edge lines carry the run along the skirting: in its band the edge is interpolated between the rows just
    # above and below it
    xs_ = p["arm_r"] + 60
    sk0 = int(line_y(xs_, *M0["skirting_line"])) - 24
    sk1 = int(line_y(xs_, *M0["floor_line"])) + 16
    if edge[sk0] >= 0 and edge[sk1] >= 0:
        edge[sk0:sk1 + 1] = np.round(np.linspace(edge[sk0], edge[sk1], sk1 - sk0 + 1)).astype(int)
    ys_ = np.nonzero(edge >= 0)[0]
    e_med = edge.astype(np.float32).copy()
    ev = edge[ys_].astype(np.float32)
    pad = np.r_[np.full(15, ev[0]), ev, np.full(15, ev[-1])]
    e_med[ys_] = np.median(np.lib.stride_tricks.sliding_window_view(pad, 31), axis=1)
    throw = np.zeros((H, W), np.float32)
    for y in ys_:
        if e_med[y] > p["arm_r"]:
            throw[y, p["arm_r"] - 2:int(round(e_med[y])) + 1] = 1
    m = np.maximum(m, throw)
    # the legs (dark oak) and the dark band under the base down to the feet line (its contact shadow goes with it)
    for (lx0, lx1, ly0, ly1) in (M0["leg_l"], M0["leg_r"]):
        m[ly0:ly1, lx0:lx1] = np.maximum(m[ly0:ly1, lx0:lx1], (L[ly0:ly1, lx0:lx1] < 55).astype(np.float32))
    m_full = fill_holes(m)
    m = m_full * (1 - (table > 0.5))
    return m, dict(base=[p["base_l"], p["base_r"]], feet=[p["feet_l"], p["feet_r"]], full=m_full)


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
    Xg = np.arange(W)[None, :]
    near = line_y(Xg, *M0["table_near_line"])
    top_rows = keep * (np.arange(H)[:, None] < near)
    ys, xs = np.nonzero(top_rows > 0.5)
    hull = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    top = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(top, hull, 1)
    legs = ((Hh >= 18) & (Hh <= 42) & (S >= 31) & (L >= 20) & (L <= 80)).astype(np.float32) * rect * (np.arange(H)[:, None] >= near + 4)
    legs = cv2.morphologyEx(legs.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 5), np.uint8))
    legs = cv2.morphologyEx(legs, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(np.float32)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats((legs > 0.5).astype(np.uint8))
    legs_k = np.zeros((H, W), np.float32)
    for i in range(1, n2):
        if st2[i, cv2.CC_STAT_HEIGHT] > 60 and st2[i, cv2.CC_STAT_WIDTH] < 70:
            legs_k[lab2 == i] = 1
    keep = np.maximum(top.astype(np.float32), legs_k)
    keep = cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((21, 1), np.uint8)).astype(np.float32)
    runner = np.zeros((H, W), np.uint8)
    cv2.fillPoly(runner, [np.array(M0["runner_poly"], np.int32)], 1)
    runner = runner.astype(np.float32) * (np.arange(H)[:, None] >= ys.min())
    bowl = F.grabcut(a, (M0["bowl_rect"][0] / W, M0["bowl_rect"][1] / W, M0["bowl_rect"][2] / H, M0["bowl_rect"][3] / H), iters=6, pad_uv=0.006, open_px=3)
    hold = F.grabcut(a, (M0["holders_rect"][0] / W, M0["holders_rect"][1] / W, M0["holders_rect"][2] / H, M0["holders_rect"][3] / H), iters=6, pad_uv=0.006, open_px=3)
    t = np.maximum.reduce([keep, runner.astype(np.float32), bowl, hold])
    t = fill_holes(cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32))
    body = fill_holes(cv2.morphologyEx(np.maximum(keep, runner.astype(np.float32)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32))
    return t, dict(body=body, bowl=bowl, holders=hold)


def debug_m0():
    jid = "m0-v8b-r2"
    a = still(jid)
    H, W = a.shape[:2]
    table, _ = table_matte_m0(a)
    sofa, info = sofa_matte_m0(a, table)
    vis = a.copy()
    vis[sofa > 0.5] = vis[sofa > 0.5] * 0.55 + np.array([255, 0, 0]) * 0.45
    vis[table > 0.5] = vis[table > 0.5] * 0.55 + np.array([0, 0, 255]) * 0.45
    F.save(vis[700:1539, 1100:2700], "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/m0c/mattes2.png")
    print(F.bbox(sofa), F.bbox(table))


# ---------------------------------------------------------------------------------------------------------------
# fills: the back wall's lines slope (perspective), so the floor / rug / sofa-base rows are filled in a sheared frame where
# they are horizontal (integer column shifts: exact inverse); the skirting by its own profile (parameter t between its lines)
# ---------------------------------------------------------------------------------------------------------------
def shear_d(W, slope, x0=1100):
    return np.round(slope * (np.arange(W) - x0)).astype(int)


def to_sheared(img, d):
    H, W = img.shape[:2]
    Y = np.clip(np.arange(H)[:, None] + d[None, :], 0, H - 1)
    return img[Y, np.arange(W)[None, :]]


def from_sheared(img, d):
    H, W = img.shape[:2]
    Y = np.clip(np.arange(H)[:, None] - d[None, :], 0, H - 1)
    return img[Y, np.arange(W)[None, :]]


def sheared_rows_fill(a, hole, valid, slope, tex=None, band_px=24):
    """fill_rows_valid in the frame sheared by `slope` (rows parallel to the wall's lines); tex = (src_box_px in the ORIGINAL
    frame, strength, blur): a mirrored-tile high-pass texture added in the sheared frame (seams follow the lines)."""
    H, W = hole.shape
    d = shear_d(W, slope)
    A, Hs, Vs = to_sheared(a, d), to_sheared(hole, d), to_sheared(valid, d)
    out = F.fill_rows_valid(A, Hs, Vs, band_px=band_px, max_search=2000)
    if tex is not None:
        (x0, y0, x1, y1), strength, blur = tex
        dd = int(round(slope * ((x0 + x1) / 2 - 1100)))
        y0s, y1s = y0 - dd, y1 - dd
        out = add_texture_m(A, out, Hs, (x0, y0s, x1, y1s), strength=strength, blur=blur)
    back = from_sheared(out, d)
    return np.where((hole > 0.5)[..., None], back, a)


def add_texture_m(a, filled, hole, src_box_px, strength=0.8, blur=6):
    import fix_v8 as F8
    return F8.add_texture_m(a, filled, hole, src_box_px, strength=strength, blur=blur)


def skirting_fill(a, hole, skt, flr, xl, xr):
    """Each hole pixel between the skirting's top line and the floor line takes the skirting's profile at the same t = (y - top)
    / (bottom - top), the mean of the columns xl and of xr, blended linearly in x."""
    H, W = hole.shape
    out = a.copy()
    ys, xs = np.nonzero(hole > 0.5)
    if not len(ys):
        return out

    def prof(xr_):
        cols = np.arange(xr_[0], xr_[1])
        ts = np.linspace(-0.25, 1.25, 151)
        acc = np.zeros((len(ts), 3), np.float32)
        for x in cols:
            y0, y1 = line_y(x, *skt), line_y(x, *flr)
            yy = np.clip(y0 + ts * (y1 - y0), 0, H - 1)
            i0 = np.floor(yy).astype(int)
            f = (yy - i0)[:, None]
            acc += a[i0, x] * (1 - f) + a[np.minimum(i0 + 1, H - 1), x] * f
        return ts, acc / len(cols)
    ts, PL = prof(xl)
    _, PR = prof(xr)
    cl, cr = (xl[0] + xl[1]) / 2, (xr[0] + xr[1]) / 2
    y0 = line_y(xs, *skt)
    y1 = line_y(xs, *flr)
    t = (ys - y0) / (y1 - y0)
    w = np.clip((xs - cl) / (cr - cl), 0, 1)[:, None]
    vl = np.stack([np.interp(t, ts, PL[:, c]) for c in range(3)], 1)
    vr = np.stack([np.interp(t, ts, PR[:, c]) for c in range(3)], 1)
    out[ys, xs] = vl * (1 - w) + vr * w
    return out


def _jacobi(u, unk, dom, iters):
    """Harmonic (membrane) fill: the unknown pixels take the mean of their neighbours inside the domain (Neumann at its edge)."""
    d = dom.astype(np.float32)
    nb = np.zeros_like(d)
    for sh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb += np.roll(d, sh, axis=(0, 1))
    nb = np.maximum(nb, 1.0)
    for _ in range(iters):
        acc = np.zeros_like(u)
        for sh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(u * d[..., None], sh, axis=(0, 1))
        u = np.where(unk[..., None], acc / nb[..., None], u)
    return u


def laplace_fill(a, hole, domain, pad=60):
    """The low-frequency of a plain surface across a large hole: the membrane through the hole's boundary (exact there, so no
    step), solved coarse-to-fine (1/16 then 1/4 of the size) inside `domain` (the surface; other pixels are a free edge), upsampled,
    and the residual step on a 6 px ring spread back (seam correction). Texture is added after. Returns a copy."""
    import fix_v8 as F8
    H, W = hole.shape
    ys, xs = np.nonzero(hole > 0.5)
    if not len(ys):
        return a.copy()
    y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad), max(0, xs.min() - pad), min(W, xs.max() + pad)
    sub = cv2.GaussianBlur(a[y0:y1, x0:x1], (0, 0), 2.0)
    hs, ds = (hole[y0:y1, x0:x1] > 0.5), (domain[y0:y1, x0:x1] > 0.5) | (hole[y0:y1, x0:x1] > 0.5)
    u = None
    for f, iters in ((16, 3000), (4, 1500)):
        h_, w_ = max(2, (y1 - y0) // f), max(2, (x1 - x0) // f)
        img = cv2.resize(sub, (w_, h_), interpolation=cv2.INTER_AREA)
        unk = cv2.resize(hs.astype(np.float32), (w_, h_), interpolation=cv2.INTER_AREA) > 0.02
        dom = cv2.resize(ds.astype(np.float32), (w_, h_), interpolation=cv2.INTER_AREA) > 0.5
        dom |= unk
        known = dom & ~unk
        if u is None:
            v, _ = blur_n(img, known.astype(np.float32), 6.0)
        else:
            v = cv2.resize(u, (w_, h_), interpolation=cv2.INTER_LINEAR)
        v = np.where(unk[..., None], v, img)
        u = _jacobi(v.astype(np.float32), unk, dom, iters)
    up = cv2.resize(u, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    full = a.copy()
    blk = full[y0:y1, x0:x1]
    blk[hs] = up[hs]
    full[y0:y1, x0:x1] = blk
    # the step left at the boundary (the low-pass of the original vs the fill on a 6 px ring)
    lowa = a.copy()
    lowa[y0:y1, x0:x1] = sub
    return F8.seam_correct(full, lowa, hole, sigma=12, ring_px=6)


def shift_fill(a, hole, valid, slope, dx, search=0, gain=True, top_ramp=0, ramp_rows=None, passes=1):
    """Copy into the hole from (dx, slope * dx) px away, sub-pixel (bilinear remap), along the wall's lines (dx > 0: from the
    right), where that source is valid. search > 0: dx is chosen within +-search px (and dy within +-2 px) for the least squared
    difference on the 10 px band of valid pixels beyond the hole's far edge, so the planks / knit meet it. A low-frequency seam
    correction follows. Returns (filled copy, filled mask, (dx, dy))."""
    import fix_v8 as F8
    H, W = hole.shape
    hm = hole > 0.5
    if not hm.any():
        return a.copy(), hm, (dx, 0.0)
    Xf = np.arange(W, dtype=np.float32)[None, :].repeat(H, 0)
    Yf = np.arange(H, dtype=np.float32)[:, None].repeat(W, 1)
    best = (dx, slope * dx)
    if search:
        side = 1 if dx > 0 else -1
        band = (dil(hole, 10) > 0.5) & ~hm & (valid > 0.5)
        # the band on the source side only (beyond the hole, where the copy comes from)
        ys, xs = np.nonzero(hm)
        cx = xs.mean()
        Xg = np.arange(W)[None, :]
        band &= ((Xg - cx) * side > 0)
        by, bx = np.nonzero(band)
        g = gray(a)
        hp = g - cv2.GaussianBlur(g, (0, 0), 3.0)
        cost = []
        for ddx in range(dx - search, dx + search + 1):
            for ddy in np.arange(-2.0, 2.01, 0.5):
                sx_, sy_ = bx + ddx, by + slope * ddx + ddy
                ok = (sx_ >= 0) & (sx_ < W - 1) & (sy_ >= 0) & (sy_ < H - 1)
                if ok.mean() < 0.8:
                    continue
                v = cv2.remap(hp, (sx_[ok]).astype(np.float32).reshape(1, -1), (sy_[ok]).astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
                cost.append((float(np.mean((v - hp[by[ok], bx[ok]]) ** 2)), ddx, float(slope * ddx + ddy)))
        cost.sort()
        best = (cost[0][1], cost[0][2])
    mx, my = Xf + best[0], Yf + best[1]
    src = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    sv = cv2.remap(valid.astype(np.float32), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0.5
    okb = hm & sv
    if gain:
        # per-row gain so the copy meets the photo at the far edge (the shading along the wall differs: the old piece's shade)
        side = 1 if dx > 0 else -1
        ys, xs = np.nonzero(hm)
        Xg = np.arange(W)[None, :]
        band = (dil(hole, 8) > 0.5) & ~hm & (valid > 0.5) & ((Xg - xs.mean()) * side > 0)
        # rows of the sheared frame (along the wall's lines), so a row is all skirting, all floor or all rug
        d = shear_d(W, slope)
        ri = np.clip(np.arange(H)[:, None] - d[None, :], 0, H - 1)
        by, bx = np.nonzero(band)
        num = np.zeros((H, 3)); den = np.zeros((H, 3)); cnt = np.zeros(H)
        np.add.at(num, ri[by, bx], a[by, bx])
        np.add.at(den, ri[by, bx], src[by, bx])
        np.add.at(cnt, ri[by, bx], 1)
        r = np.ones((H, 3), np.float32)
        okr = cnt > 2
        r[okr] = num[okr] / np.maximum(den[okr], 1e-3)
        if okr.any():
            yy = np.arange(H)
            for c in range(3):
                r[:, c] = np.interp(yy, yy[okr], r[okr, c])
            r = cv2.GaussianBlur(r.astype(np.float32).reshape(H, 1, 3), (1, 0), sigmaX=0.1, sigmaY=2.0).reshape(H, 3)
            rl = np.clip(r.mean(1, keepdims=True), 0.9, 1.1)          # one gain for the three channels (no tint)
            src = src * rl[ri]
    # further passes: copies of the copy (dx again) where the first source was not valid (a hole wider than the valid
    # stretch beyond it, e.g. the rug's edge ending at its corner)
    fillimg = np.where(okb[..., None], src, a)
    for _ in range(passes - 1):
        src_k = cv2.remap(fillimg, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        sv_k = cv2.remap(((valid > 0.5) | okb).astype(np.float32), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0.5
        new = hm & ~okb & sv_k
        if not new.any():
            break
        fillimg = np.where(new[..., None], src_k, fillimg)
        okb = okb | new
    src = fillimg
    w = okb.astype(np.float32)
    if top_ramp:
        # the zone's upper rows blend into what is above (the wall fill): a ramp over top_ramp px
        top = np.full(W, H)
        cols = np.nonzero(okb.any(0))[0]
        for x in cols:
            top[x] = np.nonzero(okb[:, x])[0][0]
        ramp = np.clip((np.arange(H)[:, None] - top[None, :]) / float(top_ramp), 0, 1)
        if ramp_rows is not None:          # only where the zone starts at its top line (not where the hole starts lower down)
            ramp = np.where((top <= ramp_rows + 2)[None, :], ramp, 1.0)
        w = w * ramp
    res = a * (1 - w[..., None]) + src * w[..., None]
    res = F8.seam_correct(res, cv2.GaussianBlur(a, (0, 0), 1.0), okb.astype(np.float32), sigma=10, ring_px=4)
    return np.where(okb[..., None], res, a), okb, (int(best[0]), round(float(best[1]), 2))

def blur_n(img, mask, sigma):
    """Normalised convolution: the blur of img over mask only."""
    m = mask.astype(np.float32)
    num = cv2.GaussianBlur(img * m[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    return num / np.maximum(den, 1e-4)[..., None], den


def aff(sx, sy, tx, ty):
    return np.float32([[sx, 0, tx], [0, sy, ty]])


def fit_axes(src_x, dst_x, src_y, dst_y):
    """x' = sx x + tx through two x pairs, y' = sy y + ty through two y pairs."""
    sx = (dst_x[1] - dst_x[0]) / (src_x[1] - src_x[0])
    sy = (dst_y[1] - dst_y[0]) / (src_y[1] - src_y[0])
    return sx, sy, dst_x[0] - sx * src_x[0], dst_y[0] - sy * src_y[0]


def warp_layer(rgb, alpha, Mx, W, H):
    flags = cv2.INTER_AREA if Mx[0, 0] < 1 else cv2.INTER_CUBIC
    r = cv2.warpAffine(rgb, Mx, (W, H), flags=flags, borderMode=cv2.BORDER_REFLECT)
    al = cv2.warpAffine(alpha, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return r, np.clip(al, 0, 1)


def map_pt(Mx, x, y):
    return float(Mx[0, 0] * x + Mx[0, 2]), float(Mx[1, 1] * y + Mx[1, 2])


def fix_m0(preview=False):
    """M0 1.2 composite on m0-v8b-r2 (see the module docstring). Returns the note."""
    jid = "m0-v8b-r2"
    a = still(jid)
    H, W = a.shape[:2]
    X = np.arange(W)[None, :]
    Y = np.arange(H)[:, None]
    p, cs = M0["sofa_render"], M0_CLAY["sofa"]
    tr, tc = M0_TABLE_R, M0_CLAY["table"]
    # ---- mattes
    table, parts = table_matte_m0(a)
    sofa, info = sofa_matte_m0(a, table)
    sofa_full = info["full"]
    # ---- transforms (x and y fitted separately to the clay; the sofa's anisotropy is 2 %, the table's 7 %: its render is
    # 1.14x the clay in height but 1.07x in width, so its height goes to the card's h38 through the clay)
    ss = fit_axes((p["arm_l"], p["arm_r"]), (cs["arm_l"], cs["arm_r"]), (p["back_top"], p["foot_r"]), (cs["back_top"], cs["foot_r"]))
    Ms = aff(*ss)
    st = fit_axes((tr["x0"], tr["x1"]), (tc["x0"], tc["x1"]), (tr["far"], tr["foot_l"]), (tc["far"], tc["foot_l"]))
    Mt = aff(*st)
    # ---- the sofa layer completed behind the old table / decor (row-wise in the sheared frame, the base's slope), so what the
    # smaller table uncovers is sofa
    occ = (sofa_full > 0.5) & (table > 0.5)
    sofa_valid = (sofa > 0.5) & (dil(table, 3) < 0.5)
    slope_b = (p["base_r"][1] - p["base_l"][1]) / (p["base_r"][0] - p["base_l"][0])
    a_sofa = sheared_rows_fill(a, occ.astype(np.float32), sofa_valid.astype(np.float32), slope_b, tex=(M0_TEX["sofa_base"], 0.9, 3), band_px=16)
    # ---- the zones of the background
    skt = line_y(X, *M0["skirting_line"])
    flr = line_y(X, *M0["floor_line"])
    rug = line_y(X, *M0["rug_line"])
    wall_z = (Y < skt - 2)
    skirt_z = (Y >= skt - 2) & (Y < flr + 2)
    skirt_cz = (Y >= skt - 14) & (Y < flr + 2)          # the strips' skirting copies carry 12 px of wall above the bevel
    floor_z = (Y >= flr + 2) & (Y < rug)
    rug_z = (Y >= rug) | ((X < 1130) & (Y >= flr + 2) & (Y >= line_y(X, (1000, 1277.0), (1130, 1220.0))))
    base = line_y(X, p["base_l"], p["base_r"])
    feet = line_y(X, p["feet_l"], p["feet_r"])
    in_arms = (X >= p["arm_l"] - 4) & (X <= p["arm_r"] + 4)
    # holes: the old sofa (with the parts behind the table) and the old table group; carriers of shadow (known pixels darkened
    # by a piece, carried with it as a ratio map): the wall 70 px above / beside the sofa, the band under its base to 30 px
    # past the feet line, the rug under the table between its near edge and the legs' feet + 40 px
    objs = np.maximum(sofa_full, table)
    hole = dil(objs, 4)
    fr = M0["throw_fringe_box"]
    hole[fr[2]:fr[3], fr[0]:fr[1]] = 1          # the throw's fringe tips lying on the rug (outside the matte)
    old_top = np.full(W, H)
    cols = np.nonzero((sofa_full > 0.5).any(0))[0]
    for x in cols:
        old_top[x] = np.nonzero(sofa_full[:, x] > 0.5)[0][0]
    wall_band = np.zeros((H, W), np.float32)
    for x in range(max(0, cols.min() - 40), min(W, cols.max() + 41)):
        t0 = old_top[min(max(x, cols.min()), cols.max())]
        wall_band[max(0, t0 - 70):, x] = 1
    wall_band *= wall_z * (1 - hole)
    under = ((Y > base - 2) & (Y <= feet + 30) & in_arms).astype(np.float32) * (1 - hole)
    near = line_y(X, *M0["table_near_line"])
    # (the rug under the table: its ratio to the fill is 1.0-1.05, no shadow to carry; the table moves 13-58 px, its soft shade
    # under the top stays, the near-left foot gets a contact shadow at its new place)
    t_under = np.zeros((H, W), np.float32)
    carrier_s = np.maximum(wall_band, under)
    carrier_t = t_under * (1 - carrier_s)
    region = np.maximum.reduce([hole, carrier_s, carrier_t])
    valid = 1 - dil(region, 2)
    # ---- the clean background: wall (2-D polynomial + the ring correction, + the wall's texture), skirting (its profile),
    # floor and rug (rows in the sheared frame, + their textures)
    import fix_v8 as F8
    bg = a.copy()
    rw = region * wall_z
    bg = laplace_fill(bg, rw, wall_z.astype(np.float32) * (1 - dil(objs, 2) * (1 - region)))
    bg = add_texture_m(a, bg, rw, M0_TEX["wall"], strength=1.0, blur=2)
    rs = region * skirt_z
    bg = skirting_fill(bg, rs, M0["skirting_line"], M0["floor_line"], (1190, 1236), (2606, 2660))
    slope_f = (M0["floor_line"][1][1] - M0["floor_line"][0][1]) / (M0["floor_line"][1][0] - M0["floor_line"][0][0])
    rf = region * floor_z
    bg = sheared_rows_fill(bg, rf, valid * floor_z, slope_f, tex=(M0_TEX["floor"], 1.0, 4))
    rr = region * rug_z
    slope_r = (M0["rug_line"][1][1] - M0["rug_line"][0][1]) / (M0["rug_line"][1][0] - M0["rug_line"][0][0])
    bg = sheared_rows_fill(bg, rr, valid * rug_z, slope_r, tex=(M0_TEX["rug"], 1.0, 4))
    # the strips the smaller sofa uncovers beside its arms, and the old table's right leg: copies along the wall's lines from
    # just beyond them (the planks, the skirting's profile and the rug's knit continue), over the row fills
    low = region * (1 - wall_z)
    shifts = {}
    slope_sk = (M0["skirting_line"][1][1] - M0["skirting_line"][0][1]) / (M0["skirting_line"][1][0] - M0["skirting_line"][0][0])
    below = (Y >= skt - 14)          # skirting (with 12 px of wall above its bevel, ramped into the wall fill), floor and rug: ONE copy,
    #                                  so the skirting's bevel, the floor line and the rug's edge stay in register with each other
    # (right: 86 px, two passes: the rug's far-right corner is at x ~2690, so a longer copy brought floor into the rug's edge)
    for name, xr_, dx, srch, npass in (("right strip", (2370, W), 86, 8, 3), ("left strip", (0, 1305), -62, 10, 2), ("old right leg (rug)", (2075, 2160), 74, 10, 1)):
        hz = region * below * ((X >= xr_[0]) & (X < xr_[1]))
        bg, okb, used = shift_fill(bg, hz, valid * below, (slope_sk + slope_r) / 2, dx, search=srch, gain=True, top_ramp=10, ramp_rows=(skt - 14)[0], passes=npass)
        shifts[name] = dict(columns=list(xr_), shift_px=list(used), px=int(okb.sum()))
        dbg_shifts = shifts
    # ---- the ratio maps (low-pass of the known pixels / low-pass of the clean fill), and the base: the fill in the holes, the
    # de-shadowed original in the carriers
    known = (1 - hole) * (1 - dil(objs, 2))
    la, _ = blur_n(a, known, 4.0)
    lb, _ = blur_n(bg, np.ones((H, W), np.float32), 4.0)
    R = np.clip(la / np.maximum(lb, 1.0), 0.15, 1.1)
    # each carrier's ratio is divided by the membrane through its OUTER ring (away from the piece; the piece's side is a free
    # edge), so it is 1 at the carrier's border and only the piece's own shadow is moved (no rectangle where the lighting of the
    # fill differs from the photo's)
    for cm in (wall_band, under, carrier_t):
        ring = ((dil(cm, 4) > 0.5) & (cm < 0.5) & (hole < 0.5)).astype(np.float32)
        if ring.sum() < 50:
            continue
        Rb = laplace_fill(R.astype(np.float32), cm, np.maximum(cm, ring), pad=20)
        R = np.where((cm > 0.5)[..., None], np.clip(R / np.maximum(Rb, 0.2), 0.15, 1.05), R)
    car = np.maximum(carrier_s, carrier_t)
    # (the band under the base is too dark to de-shadow (ratio ~0.2): it takes the clean fill, its shadow comes back as the profile)
    base_img = np.where((np.maximum(hole, under) > 0.5)[..., None], bg, np.where((car > 0.5)[..., None], a / np.maximum(R, 0.15), a))
    # the band under the sofa: the old one is mostly behind the old table, so its ratio is a profile in t (base -> feet) taken
    # from the visible columns right of the table, re-drawn under the new base / feet lines
    vis_cols = np.arange(tr["x1"] + 8, p["arm_r"] - 50)
    ts = np.linspace(-0.2, 1.6, 181)
    acc = np.zeros((len(ts), 3), np.float32)
    n_ok = 0
    dbg_cols = []
    for x in vis_cols:
        b0, f0 = line_y(x, p["base_l"], p["base_r"]), line_y(x, p["feet_l"], p["feet_r"])
        yy = np.clip(np.round(b0 + ts * (f0 - b0)).astype(int), 0, H - 1)
        inside = (ts >= 0.02) & (yy <= f0 + 26)
        dbg_cols.append((int(x), float((hole[yy[inside], x] > 0.5).mean()), float((under[yy[inside], x] < 0.5).mean())))
        if (hole[yy[inside], x] > 0.5).mean() > 0.1 or (under[yy[inside], x] < 0.5).mean() > 0.1:
            continue
        r = R[yy, x].copy()
        r[~((ts < 0.02) | inside)] = 1.0
        acc += r
        n_ok += 1
    if n_ok < 20:
        raise RuntimeError(f"under-band profile: {n_ok} clean columns")
    prof_u = acc / n_ok
    prof_u[ts < 0.02] = prof_u[np.nonzero(ts >= 0.02)[0][0]]
    tail = np.nonzero(~((ts < 0.02) | (ts <= 1.0)))[0]
    prof_u[tail] = np.maximum(prof_u[tail], prof_u[tail[0] - 1] + (1 - prof_u[tail[0] - 1]) * np.linspace(0, 1, len(tail))[:, None])
    nb = lambda x: map_pt(Ms, x, line_y(x, p["base_l"], p["base_r"]))
    (nbx0, nby0), (nbx1, nby1) = nb(p["arm_l"]), nb(p["arm_r"])
    (nfx0, nfy0), (nfx1, nfy1) = map_pt(Ms, p["feet_l"][0], p["feet_l"][1]), map_pt(Ms, p["feet_r"][0], p["feet_r"][1])
    nbase = line_y(X, (nbx0, nby0), (nbx1, nby1))
    nfeet = line_y(X, (nfx0, nfy0), (nfx1, nfy1))
    tt = (Y - nbase) / np.maximum(nfeet - nbase, 1.0)
    in_new = (X >= nbx0 + 4) & (X <= nbx1 - 4)
    R_band = np.ones((H, W, 3), np.float32)
    for c in range(3):
        R_band[..., c] = np.where(in_new & (tt >= 0) & (tt <= 1.6), np.interp(tt, ts, prof_u[:, c]), 1.0)
    edge_fade = np.clip(np.minimum(X - nbx0, nbx1 - X) / 25.0, 0, 1)[..., None]
    R_band = 1 + (R_band - 1) * edge_fade
    # the carried ratio maps: the wall band with the sofa, the rug under the table with the table
    # (each ratio map is continued 14 px into the old piece's hole, so it meets the moved piece without a lit rim)
    def carried(cm):
        ext, den = blur_n(R, cm, 5.0)
        ring = (dil(cm, 14) > 0.5) & (cm < 0.5) & (hole > 0.5) & (den > 0.02)
        return np.where((cm > 0.5)[..., None], R, np.where(ring[..., None], ext, 1.0)).astype(np.float32)
    Rs = carried(wall_band)
    Rt = carried(carrier_t)
    Rs_new = cv2.warpAffine(Rs, Ms, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1, 1, 1))
    Rt_new = cv2.warpAffine(Rt, Mt, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1, 1, 1))
    out = base_img * Rs_new * Rt_new * R_band
    # ---- the layers: sofa (completed), the table body (top, legs, runner: anisotropic), the decor (uniform, sx, about its foot)
    s_al0 = cv2.erode((sofa_full > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    s_rgb, s_al = warp_layer(a_sofa, F.feather(s_al0, 1.0), Ms, W, H)
    out = F.composite(out, s_rgb, s_al)
    t_rgb, t_al = warp_layer(a, F.feather(parts["body"], 0.8), Mt, W, H)
    out = F.composite(out, t_rgb, t_al)
    decor = {}
    for k in ("holders", "bowl"):
        m = parts[k]
        x0_, x1_, y0_, y1_ = F.bbox(m)
        fx, fy = (x0_ + x1_) / 2.0, float(y1_)
        nfx, nfy = map_pt(Mt, fx, fy)
        k_ = float(Mt[0, 0])
        Md = np.float32([[k_, 0, nfx - k_ * fx], [0, k_, nfy - k_ * fy]])
        d_rgb, d_al = warp_layer(a, F.feather(m, 0.8), Md, W, H)
        out = F.composite(out, d_rgb, d_al)
        decor[k] = dict(foot_render=[round(fx, 1), round(fy, 1)], foot_new=[round(nfx, 1), round(nfy, 1)], scale=round(k_, 4))
    # the near-left leg's contact shadow at its new foot (the old one is under the moved leg)
    import fix_v8 as F8b
    lfx, lfy = map_pt(Mt, 1324.0, float(tr["foot_l"]))
    out_pre = out.copy()
    out = F8b.contact_shadow(out, lfx - 16, lfx + 16, lfy + 1, depth=0.78, h_px=5, spread=1.2)
    t_cover = cv2.warpAffine(parts["body"], Mt, (W, H), flags=cv2.INTER_LINEAR)
    out = np.where((t_cover > 0.5)[..., None], out_pre, out)
    out = np.clip(out, 0, 255)
    dbg = dict(shifts=shifts, hole=hole, carrier_s=carrier_s, carrier_t=carrier_t, R=R, bg=bg, R_band=R_band, Ms=Ms, Mt=Mt, sofa=sofa_full, table=table)
    if preview:
        return out, dbg
    F.save(out, out_fix(jid))
    note = dict(
        what="M0 1.2 composite in code on the reserve render m0-v8b-r2 (briefs/render-m0-composite-and-cleanup-2026-11-04.md task 1): the sofa group "
             "and the coffee-table group put on the round-5b clay; the shell, window, armchair, pendant and sconces untouched",
        source=OUT[jid] + jid + ".png", clay="assets/blockout/house/framing/round5b/M0.png", output=OUT[jid] + jid + "-fix.png",
        measured_px_canvas=dict(sofa_render={k: p[k] for k in ("arm_l", "arm_r", "back_top", "foot_r")}, sofa_clay=cs, table_render=tr, table_clay=tc,
                                lines=dict(skirting=M0["skirting_line"], floor=M0["floor_line"], rug=M0["rug_line"], table_near=M0["table_near_line"],
                                           sofa_base=[p["base_l"], p["base_r"]], sofa_feet=[p["feet_l"], p["feet_r"]])),
        sofa=dict(matrix=np.round(Ms, 5).tolist(), scale_x=round(ss[0], 4), scale_y=round(ss[1], 4),
                  how="matte: textured fabric (local high-pass energy > 1.6) per column from its first row to the base line, the throw outside the right "
                      "arm row by row (fabric run, median 31 rows), the legs; the parts behind the old table / decor completed row-wise along the base's "
                      "slope (+ the base's texture) so what the smaller table uncovers is sofa"),
        table=dict(matrix=np.round(Mt, 5).tolist(), scale_x=round(st[0], 4), scale_y=round(st[1], 4),
                   how="top (convex hull of the oak above its near edge), legs (oak S >= 31 below it), runner (polygon): x and y fitted separately "
                       "(ends + far edge + near-left foot); the render's table is 1.14x the clay in height and 1.07x in width, so its height comes to the card's h38",
                   decor=decor, decor_how="candle holders and bowl uniform (the table's x scale) about their foot, which goes where the table maps it"),
        fills=dict(wall="membrane (harmonic) fill of the low-pass, coarse-to-fine 1/16 -> 1/4, exact at the boundary + 6 px seam correction, + the wall's mirrored high-pass texture " + str(M0_TEX["wall"]),
                   strips=shifts,
                   skirting="the skirting's own profile at t between its top line and the floor line, left (1190-1236) and right (2606-2660) blended in x",
                   floor="rows in the frame sheared by the floor line's slope (" + str(round(slope_f, 4)) + ") + floor texture " + str(M0_TEX["floor"]),
                   rug="rows in the frame sheared by the rug edge's slope (" + str(round(slope_r, 4)) + ") + rug texture " + str(M0_TEX["rug"])),
        shadows=dict(wall="the wall 70 px above / 40 px beside the old sofa: ratio (low-pass known / low-pass clean fill), de-shadowed in place, re-applied moved with the sofa",
                     under_base="the band under the base: a ratio profile in t (base -> feet, to t 1.6) from the visible columns right of the table, "
                                "re-drawn under the new base / feet lines (" + str(n_ok) + " columns)",
                     table="none carried: the rug under the table reads 1.00-1.05 against the fill (no cast shadow to move); a contact shadow (depth 0.78, 5 px) at the near-left leg's new foot"),
        tokens=0)
    save_note(jid, note)
    return note
