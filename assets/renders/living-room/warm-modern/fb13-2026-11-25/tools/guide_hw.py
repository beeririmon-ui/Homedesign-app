#!/usr/bin/env python3
"""guide_hw.py: the seedream input of the hero H-W = the rendered plate P-W (as returned), lit by the clay's own light ratio
(clay with every product and every lamp over the clay plate: contact shadows, the olive's leaf shadow, the lamps' pools), with the
current default SKU layers of phase2-2026-11-10 (the M0 tool frame) re-projected onto their places in M0-W (the method of
concepts/guide.py, on the canvas 2720 x 1530). The three prints are blank sand canvases (#D8C8AE) in slim walnut frames: the art
is set in code afterwards (as MB0 / MB1). Scratch only.
  python3 guide_hw.py <plate png> [out name]
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guide_pw as G  # noqa: E402

SP = G.SP
OUT = G.OUT
REPO = "/home/user/homedesign-app"
LAY = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10/layers")
FB13 = G.FB13
FB = G.FB
W, H = 2720, 1530
SC = 1.0
PLATE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "pw-input.png")
NAME = sys.argv[2] if len(sys.argv) > 2 else "hw-input"
VIEW = json.load(open(os.path.join(OUT, "view.json")))
HOLDER = tuple(VIEW["holder"])
PLANTER = tuple(VIEW["planter"])
BASKET = tuple(VIEW["basket"])
CANVAS_ALBEDO = np.float32([216, 200, 174]) / 255.0          # #D8C8AE, the blank canvas of MB0 / MB1
PLASTER_ALBEDO = np.float32([236, 229, 218]) / 255.0         # #ECE5DA
ART_X = (-0.36, 0.20, 0.76)
ART_Z = (1.13, 1.83)
ART_HALF = 0.25
ART_Y = 0.03
MOULD = 0.016

srgb2lin, lin2srgb, to_lab, from_lab, blur_masked = G.srgb2lin, G.lin2srgb, G.to_lab, G.from_lab, G.blur_masked


def camera(loc, yaw, lens, u0, v0):
    y = math.radians(yaw)
    fw, rt, K = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y)), lens / 36.0

    def P(Xw, Yw, Zw, scale=1.0):
        dx, dy = Xw - loc[0], Yw - loc[1]
        d = fw[0] * dx + fw[1] * dy
        x = rt[0] * dx + rt[1] * dy
        u, v = u0 + K * x / d, v0 + K * 16 / 9 * (loc[2] - Zw) / d
        return np.array([(FB[0] + u * (FB[2] - FB[0])) * scale, (FB[1] + v * (FB[3] - FB[1])) * scale]), d

    def depth_at(py, Zw):
        v = (py - FB[1]) / (FB[3] - FB[1])
        return K * 16 / 9 * (loc[2] - Zw) / (v - v0)

    P.K, P.depth_at = K, depth_at
    return P


M0 = camera((0.83, 4.64, 1.20), 25, 24, 0.47, 0.50)
MW = camera((0.95, 5.55, 1.05), 14, 35, 0.50, 0.555)


def load_layer(rel):
    return np.asarray(Image.open(os.path.join(LAY, rel)).convert("RGBA")).astype(np.float32) / 255.0


def warp(layer, Hm):
    pm = layer.copy()
    pm[..., :3] *= pm[..., 3:4]
    o = cv2.warpPerspective(pm, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    al = o[..., 3:4]
    rgb = np.where(al > 1e-4, o[..., :3] / np.maximum(al, 1e-4), 0)
    return np.dstack([rgb, al])


def H_plane(pts_src_world, pts_dst_world=None):
    pts_dst_world = pts_dst_world or pts_src_world
    s = np.float32([M0(*p)[0] for p in pts_src_world])
    d = np.float32([MW(*p, scale=SC)[0] for p in pts_dst_world])
    return cv2.getPerspectiveTransform(s, d)


def H_sim(src_anchor_px, src_depth, dst_world):
    dpt, dw = MW(*dst_world, scale=SC)
    s = (MW.K / dw) / (M0.K / src_depth) * SC
    ax, ay = src_anchor_px
    return np.float64([[s, 0, dpt[0] - s * ax], [0, s, dpt[1] - s * ay], [0, 0, 1]]), s


def foot(layer, rows=0.06, thr=0.5):
    al = layer[..., 3] > thr
    ys, xs = np.where(al)
    y1 = ys.max()
    y0 = int(y1 - rows * (y1 - ys.min()))
    sel = ys >= y0
    return 0.5 * (xs[sel].min() + xs[sel].max()), float(y1), (xs.min(), ys.min(), xs.max(), y1)


def quad_mask(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32(np.rint(np.float32(pts) * 8))], 1, lineType=cv2.LINE_AA, shift=3)
    return m.astype(np.float32)


def art_quads():
    out = []
    for cx in ART_X:
        outer = [MW(cx - ART_HALF, ART_Y, ART_Z[1])[0], MW(cx + ART_HALF, ART_Y, ART_Z[1])[0], MW(cx + ART_HALF, ART_Y, ART_Z[0])[0],
                 MW(cx - ART_HALF, ART_Y, ART_Z[0])[0]]
        inner = [MW(cx - ART_HALF + MOULD, ART_Y, ART_Z[1] - MOULD)[0], MW(cx + ART_HALF - MOULD, ART_Y, ART_Z[1] - MOULD)[0],
                 MW(cx + ART_HALF - MOULD, ART_Y, ART_Z[0] + MOULD)[0], MW(cx - ART_HALF + MOULD, ART_Y, ART_Z[0] + MOULD)[0]]
        out.append((outer, inner))
    return out


def main():
    P_ = np.asarray(Image.open(PLATE).convert("RGB")).astype(np.float32) / 255.0
    assert P_.shape[:2] == (H, W), P_.shape
    z = np.load(os.path.join(OUT, "passes-full.npz"))
    idx = z["idx"]
    idx_p = np.load(os.path.join(OUT, "passes-plate.npz"))["idx"]
    log = {}
    c_on = G.materials(np.asarray(Image.open(os.path.join(OUT, "clay-B-full-on.png")).convert("RGB")).astype(np.float32) / 255.0, idx, log, "on_", sunmap=G.shifted_map(os.path.join(FB13, "m0w-sun.png"), W, H, 255.0))
    c_pl = G.materials(np.asarray(Image.open(os.path.join(OUT, "clay-B-plate.png")).convert("RGB")).astype(np.float32) / 255.0, idx_p, log, "plate_", sunmap=G.shifted_map(os.path.join(FB13, "m0w-sun.png"), W, H, 255.0))
    full = c_on
    PI = {"rug": 801, "vase": 803, "planter": 804, "basket": 805, "magazine-holder": 806, "floor-lamp": 807, "framed-art": 808,
          "accent-sconces": 809, "pendant": 810, "bowl": 811, "candle-holders": 812, "coffee-table": 813, "cushion-left": 814,
          "cushion-right": 815, "cushion-lumbar": 816, "throw": 817, "candles": 831}
    # 1. the clay's light ratio (every product and lamp over the plate) where both show the same surface; filled under the proxies
    same = (idx == idx_p)
    valid = cv2.erode(same.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    ratio = srgb2lin(c_on) / np.maximum(srgb2lin(c_pl), 0.004)
    ratio = np.clip(ratio, 0.25, 3.0)
    R, den = blur_masked(ratio, valid, 2.2)
    # behind a proxy: the ratio of the surfaces around it, taken 15 px away from every proxy (not the proxy's own contact shadow)
    valid_far = cv2.erode(same.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32)
    Rfill = np.ones_like(ratio)
    done = np.zeros((H, W), bool)
    for sg in (40.0, 120.0, 320.0):
        Rf, df = blur_masked(ratio, valid_far, sg)
        take = (~done) & (df > 0.02)
        Rfill[take] = Rf[take]
        done |= take
    R = np.where(valid[..., None] > 0, R, Rfill)
    R = np.stack([cv2.GaussianBlur(R[..., i], (0, 0), 1.0) for i in range(3)], -1)
    # the clay's exposure to the plate's (low frequencies), for the clay objects kept in the input (the olive, the table)
    okp = (idx_p == idx_p).astype(np.float32)
    adapt = cv2.GaussianBlur(srgb2lin(P_), (0, 0), 60.0) / np.maximum(cv2.GaussianBlur(srgb2lin(c_pl), (0, 0), 60.0), 0.01)
    adapt = np.clip(adapt.mean(2, keepdims=True), 0.5, 2.0)
    clay_obj = np.clip(lin2srgb(srgb2lin(full) * adapt), 0, 1).astype(np.float32)
    lit = np.clip(lin2srgb(srgb2lin(P_) * R), 0, 1).astype(np.float32)
    out = lit.copy()
    cover = np.zeros((H, W), np.float32)
    sun = G.shifted_map(os.path.join(FB13, "m0w-sun.png"), W, H, 255.0)
    sun = cv2.GaussianBlur(np.clip(sun / 0.6, 0, 1), (0, 0), 3.0)
    # the M0 cut-outs (their frame: plaster L 89.5) to this plate's shade, a slightly warmer balance
    Lp = to_lab(P_)[..., 0]
    back = idx_p == 5
    Lsh = float(np.percentile(Lp[back], 30))
    Y = lambda L: ((L + 16) / 116) ** 3
    g = Y(Lsh) / Y(89.5)
    tint = np.float32([1.02, 1.0, 0.96])
    # the sun on the cut-outs: the plate's own sun over its shade beside the patch (linear), on the clay's sun map
    sun_w = (idx_p == 5) & (sun > 0.9)
    near = (idx_p == 5) & (sun < 0.03) & (cv2.dilate((sun > 0.5).astype(np.uint8), np.ones((161, 161), np.uint8)) > 0)
    ksun = float(np.clip(Y(float(np.median(Lp[sun_w]))) / Y(float(np.median(Lp[near]))) - 1.0, 0.3, 1.2))
    log["ksun"] = round(ksun, 3)
    log["plate_shade_L"] = round(Lsh, 2)

    def relight(rgb, gain=1.0, sunmap=True):
        lin = srgb2lin(rgb) * g * gain * tint
        if sunmap:
            lin = lin * (1 + ksun * sun[..., None])
        return np.clip(lin2srgb(lin), 0, 1)

    def paste(rgba, mask=None, soft=0.0):
        nonlocal out, cover
        a = rgba[..., 3]
        if mask is not None:
            a = a * mask
        if soft:
            a = cv2.GaussianBlur(a, (0, 0), soft)
        out = out * (1 - a[..., None]) + rgba[..., :3] * a[..., None]
        cover = np.maximum(cover, a)

    # 2. the rug: the SKU layer of M0 rectified to the rug's plane (700 px / m), completed where M0 did not see it (the weave runs along
    # X: each row filled by reflecting its own valid span; rows M0 never saw by reflecting the valid rows), its M0 light removed (low
    # frequencies), then projected to M0-W and lit by the clay rug's low frequencies
    rug = load_layer("rug/rug-cj-braided-wool-natural-fb12s1.png")
    RX, RY, PXM = (-1.45, 1.85), (0.77, 3.07), 700.0
    Wt, Ht = int(round((RX[1] - RX[0]) * PXM)), int(round((RY[1] - RY[0]) * PXM))
    corners = [(RX[0], RY[0], 0.012), (RX[1], RY[0], 0.012), (RX[1], RY[1], 0.012), (RX[0], RY[1], 0.012)]
    tex_q = np.float32([[0, 0], [Wt, 0], [Wt, Ht], [0, Ht]])
    Hm0 = cv2.getPerspectiveTransform(np.float32([M0(*p)[0] for p in corners]), tex_q)
    pm = rug.copy()
    pm[..., :3] *= pm[..., 3:4]
    T = cv2.warpPerspective(pm, Hm0, (Wt, Ht), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    A = T[..., 3]
    Trgb = np.where(A[..., None] > 1e-3, T[..., :3] / np.maximum(A[..., None], 1e-3), 0)
    ok = A > 0.985
    ok = cv2.erode(ok.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    labT = to_lab(Trgb)
    loT, _ = blur_masked(labT[..., 0], ok.astype(np.float32), 45.0)
    det = np.where(ok, labT[..., 0] - loT, 0.0)
    ab = [float(np.median(labT[..., c][ok])) for c in (1, 2)]
    Lmean = float(np.median(labT[..., 0][ok]))
    filled = det.copy()
    okf = ok.copy()
    xs_all = np.arange(Wt)
    good_rows = []
    for y in range(Ht):
        r = ok[y]
        if r.sum() < 0.25 * Wt:
            continue
        xs = np.where(r)[0]
        # the longest run of valid pixels of the row
        br = np.where(np.diff(xs) > 1)[0]
        st = np.concatenate([[0], br + 1])
        en = np.concatenate([br, [len(xs) - 1]])
        k = int(np.argmax(en - st))
        a0, b0 = int(xs[st[k]]), int(xs[en[k]])
        n = b0 - a0
        if n < 0.2 * Wt:
            continue
        t = (xs_all - a0) % (2 * n)
        src = a0 + np.where(t <= n, t, 2 * n - t)
        row = det[y, src]
        filled[y] = np.where(r, det[y], row)
        okf[y] = True
        good_rows.append(y)
    good_rows = np.array(good_rows)
    g0, g1 = int(good_rows.min()), int(good_rows.max())
    n = g1 - g0
    for y in range(Ht):
        if okf[y].all():
            continue
        t = (y - g0) % (2 * n)
        ys = g0 + (t if t <= n else 2 * n - t)
        while not okf[ys].all():
            ys = ys + 1 if ys < g1 else g0
        filled[y] = np.where(okf[y], filled[y], filled[ys])
    texL = Lmean + filled
    tex = from_lab(np.dstack([texL, np.full_like(texL, ab[0]), np.full_like(texL, ab[1])]))
    Hmw = cv2.getPerspectiveTransform(tex_q, np.float32([MW(*p)[0] for p in corners]))
    wr = cv2.warpPerspective(np.dstack([tex, np.ones((Ht, Wt), np.float32)]), Hmw, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    rq = wr[..., 3]
    mrug_pure = (idx == PI["rug"]).astype(np.float32)
    # the rug shows wherever the clay shows the rug, and behind the proxies that stand on it
    onrug = np.isin(idx, [PI["rug"], PI["magazine-holder"], PI["coffee-table"], PI["bowl"], PI["candle-holders"], PI["candles"]])
    mrug = (onrug & (rq > 0.5)).astype(np.float32)
    lab_w, lab_c = to_lab(wr[..., :3]), to_lab(clay_obj)
    lo_c, _ = blur_masked(lab_c[..., 0], mrug_pure, 16.0)
    lo_w, _ = blur_masked(lab_w[..., 0], (rq > 0.99).astype(np.float32), 16.0)
    Lr = lo_c + (lab_w[..., 0] - lo_w)
    lab_n = np.dstack([Lr, lab_w[..., 1] + (lab_c[..., 1] - float(np.median(lab_c[..., 1][mrug_pure > 0]))) * 0.5,
                       lab_w[..., 2] + (lab_c[..., 2] - float(np.median(lab_c[..., 2][mrug_pure > 0]))) * 0.5])
    paste(np.dstack([from_lab(lab_n), mrug]), soft=0.7)
    log["rug"] = dict(px=int(mrug.sum()), texture_px=[Wt, Ht], seen_in_m0_share=round(float(ok.mean()), 3), rows_seen=[g0, g1])

    # 3. the three blank canvases in slim walnut frames, lit by the wall behind them (the plate times the clay's ratio)
    wall_lin = srgb2lin(lit)
    canvas_rgb = np.clip(lin2srgb(wall_lin * (srgb2lin(CANVAS_ALBEDO) / srgb2lin(PLASTER_ALBEDO))), 0, 1)
    walnut_rgb = np.clip(lin2srgb(wall_lin * (srgb2lin(np.float32([107, 74, 51]) / 255.0) / srgb2lin(PLASTER_ALBEDO))), 0, 1)
    for outer, inner in art_quads():
        mo, mi = quad_mask(outer), quad_mask(inner)
        # a thin shadow of the frame on the plaster, to the right and below (the sun comes from the left)
        sh = cv2.warpAffine(mo, np.float32([[1, 0, 5], [0, 1, 4]]), (W, H))
        sh = cv2.GaussianBlur(sh, (0, 0), 2.5) * (1 - mo)
        out = out * (1 - 0.30 * sh[..., None])
        paste(np.dstack([walnut_rgb, mo]))
        paste(np.dstack([canvas_rgb, mi]))
    log["framed-art"] = dict(canvas="#D8C8AE", quads=[[[round(float(c), 1) for c in p] for p in q[1]] for q in art_quads()])
    sc_ = load_layer("accent-sconces/accent-sconces-aliexpress-travertine-cylinder-walnut-choice.png")
    Hs = H_plane([(-1.0, 0.0575, 1.0), (1.5, 0.0575, 1.0), (1.5, 0.0575, 2.0), (-1.0, 0.0575, 2.0)])
    ws = warp(sc_, Hs)
    paste(np.dstack([relight(ws[..., :3], 1.3), ws[..., 3]]))

    def glow(halo, k=1.0):
        nonlocal out
        add = halo[..., None] * np.float32([0.16, 0.12, 0.06]) * k
        out = 1 - (1 - out) * (1 - np.clip(add, 0, 1))

    # 4. standing and hanging things: a similarity at the anchor (their drawn proportions kept)
    def stand(key, rel, z_src, dst_world, lit_band=None, rows=None, mask=None, gain=1.0, src_depth=None):
        lay = load_layer(rel)
        if rows is not None:
            fx, fy, bb = foot(lay)
            y0 = int(bb[1] + rows[0] * (bb[3] - bb[1]))
            y1 = int(bb[1] + rows[1] * (bb[3] - bb[1]))
            lay[:y0, :, 3] = 0
            lay[y1 + 1:, :, 3] = 0
        fx, fy, bb = foot(lay)
        d0 = src_depth if src_depth is not None else M0.depth_at(fy, z_src)
        Hm, s = H_sim((fx, fy), d0, dst_world)
        w = warp(lay, Hm)
        rgb = relight(w[..., :3], gain)
        if lit_band is not None:
            ys, xs = np.where(w[..., 3] > 0.5)
            ya, yb = ys.min() + lit_band[0] * (ys.max() - ys.min()), ys.min() + lit_band[1] * (ys.max() - ys.min())
            band = ((np.arange(H)[:, None] >= ya) & (np.arange(H)[:, None] <= yb)).astype(np.float32) * np.ones((1, W), np.float32)
            band = cv2.GaussianBlur(band, (0, 0), 2.0)
            warm = np.clip(lin2srgb(srgb2lin(w[..., :3]) * np.float32([1.55, 1.38, 1.05])), 0, 1)
            rgb = rgb * (1 - band[..., None]) + warm * band[..., None]
            glow(cv2.GaussianBlur(w[..., 3] * band, (0, 0), 26.0))
        paste(np.dstack([rgb, w[..., 3]]), mask=mask)
        log[key] = dict(src_foot=[round(fx, 1), round(fy, 1)], src_depth=round(float(d0), 3), scale_vs_m0_canvas=round(s / SC, 4),
                        dst_px=[round(float(v_), 1) for v_ in MW(*dst_world, scale=SC)[0]], px=int((w[..., 3] > 0.5).sum()))

    stand("vase", "vase/vase-cj-textured-white-stoneware-r6.png", 0.45, (-2.42, 1.35, 0.45), gain=1.0)
    stand("planter", "planter/planter-cj-cement-ribbed-belly-r7.png", 0.0, (PLANTER[0], PLANTER[1], 0.0), rows=(0.60, 1.0), gain=1.3)
    ol = cv2.GaussianBlur((idx == 830).astype(np.float32), (0, 0), 0.6)[..., None]          # the clay olive (trunk and crown) over the pot
    olive = clay_obj
    out = out * (1 - ol) + olive * ol
    stand("floor-lamp", "floor-lamp/floor-lamp-cj-pleated-walnut-stem-158-r5.png", 0.0, (1.44, 0.20, 0.0), lit_band=(0.0, 0.17))
    # set B: the wall-parallel plane of the sofa's cushions (Y 0.40); the left cushion 10 cm in from the wider rounded arm
    cu = load_layer("cushions/set-B-lfix.png")
    n, lab_ = cv2.connectedComponents((cu[..., 3] > 0.5).astype(np.uint8))
    sizes = sorted(((int((lab_ == i).sum()), i) for i in range(1, n)), reverse=True)
    big = [i for s_, i in sizes if s_ > 4000]
    cxs = {i: float(np.where(lab_ == i)[1].mean()) for i in big}
    left_i = min(cxs, key=cxs.get)
    left, right = cu.copy(), cu.copy()
    ml = cv2.dilate((lab_ == left_i).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    left[~ml, 3] = 0
    right[ml, 3] = 0
    q = [(-0.9, 0.40, 0.44), (1.3, 0.40, 0.44), (1.3, 0.40, 1.0), (-0.9, 0.40, 1.0)]
    wl = warp(left, H_plane(q, [(x + 0.10, y, z_) for x, y, z_ in q]))
    wr_ = warp(right, H_plane(q, [(x - 0.03, y, z_) for x, y, z_ in q]))
    arm = (idx_p == 3)
    paste(np.dstack([relight(wl[..., :3]), wl[..., 3]]), mask=(~arm).astype(np.float32))
    paste(np.dstack([relight(wr_[..., :3]), wr_[..., 3]]), mask=(~arm).astype(np.float32))
    log["cushions"] = dict(blobs=len(big), left_px=int((wl[..., 3] > 0.5).sum()), right_px=int((wr_[..., 3] > 0.5).sum()))
    # the Olia: the clay's own table (its clean geometry and light: one slab over two slab ends, open underneath), in natural oak with
    # a fine long grain; the rolled bend and the real grain come from the SKU references (the warped M0 layer broke at the ends)
    mt = (idx == PI["coffee-table"])
    lab_t = to_lab(clay_obj)
    rs = np.random.RandomState(120)
    gr_ = cv2.GaussianBlur(rs.randn(H, W).astype(np.float32), (0, 0), sigmaX=22.0, sigmaY=0.8)
    gr_ = gr_ / max(float(gr_.std()), 1e-6)
    lab_t[..., 0] = lab_t[..., 0] + 1.4 * gr_
    lab_t[..., 1] = 7.0 + 0.4 * (lab_t[..., 1] - float(np.median(lab_t[..., 1][mt])))
    lab_t[..., 2] = 24.0 + 0.4 * (lab_t[..., 2] - float(np.median(lab_t[..., 2][mt])))
    tab_rgb = from_lab(lab_t)
    x0, x1, y0, y1 = -0.30, 0.90, 1.395, 2.045
    topq = quad_mask([MW(x0, y0, 0.38)[0], MW(x1, y0, 0.38)[0], MW(x1, y1, 0.38)[0], MW(x0, y1, 0.38)[0]]) > 0.5
    small = np.isin(idx, [PI["bowl"], PI["candle-holders"], PI["candles"]]) & topq       # the top goes on behind the small things
    fill_t, _ = blur_masked(tab_rgb, (mt & topq).astype(np.float32), 14.0)
    tab_rgb = np.where(small[..., None], fill_t, tab_rgb)
    am = cv2.GaussianBlur((mt | small).astype(np.float32), (0, 0), 0.7)
    paste(np.dstack([tab_rgb, am]))
    log["coffee-table"] = dict(px=int(mt.sum()), source="the clay table, oak colour (Lab a 7, b 24) and a long grain")
    stand("bowl", "bowl/bowl-cj-matte-black-bowl-20-fb12s1.png", 0.38, (0.60, 1.90, 0.38), gain=1.0)
    stand("candle-holders", "candle-holders/candle-holders-cj-travertine-pedestal-fb12s1.png", 0.38, (0.28, 1.71, 0.38), gain=1.05)
    stand("pendant", "pendant/pendant-cj-tiered-fabric-drum-r4.png", None, (0.20, 1.72, 1.90), lit_band=(0.45, 1.0), src_depth=M0(0.20, 1.72, 1.9)[1])
    stand("basket", "basket/basket-cj-jute-rope-cylinder-r7.png", 0.0, (BASKET[0], BASKET[1], 0.0), mask=(idx_p != 3).astype(np.float32))
    # the magazine holder: its M0 cut-out (cut by the M0 canvas) on a plane facing the camera through its new point
    mh = load_layer("magazine-holder/magazine-holder-cj-gunmetal-leather-strap-r6.png")
    src_pt = (-0.54, 2.52)
    qs = [(src_pt[0] - 0.3, src_pt[1], 0.0), (src_pt[0] + 0.3, src_pt[1], 0.0), (src_pt[0] + 0.3, src_pt[1], 0.4), (src_pt[0] - 0.3, src_pt[1], 0.4)]
    qd = [(HOLDER[0] - 0.3, HOLDER[1], 0.0), (HOLDER[0] + 0.3, HOLDER[1], 0.0), (HOLDER[0] + 0.3, HOLDER[1], 0.4), (HOLDER[0] - 0.3, HOLDER[1], 0.4)]
    wm = warp(mh, H_plane(qs, qd))
    paste(np.dstack([relight(wm[..., :3]), wm[..., 3]]))
    log["magazine-holder"] = dict(px=int((wm[..., 3] > 0.5).sum()), at=list(HOLDER))

    o8 = np.rint(np.clip(out, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(OUT, NAME + ".png"), optimize=True)
    Image.fromarray(o8).resize((1360, 765), Image.LANCZOS).save(os.path.join(OUT, NAME + "-small.jpg"), quality=90)
    np.save(os.path.join(OUT, NAME + "-cover.npy"), (cover * 255).astype(np.uint8))
    log["global_gain"] = round(float(g), 4)
    json.dump(log, open(os.path.join(OUT, NAME + ".json"), "w"), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
