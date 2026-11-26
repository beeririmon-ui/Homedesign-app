#!/usr/bin/env python3
"""guide.py: the flux-2 input of an FB13 concept = the M0-W clay at v0 0.555 (lit; clay555.py) with the current default SKU layers of
phase2-2026-11-10 (the M0 tool frame) re-projected onto their clay proxies. flux-2 in var2 reads one image only, so the references
(the Olia layer, the rug, set B, the lamps, the trio) travel inside the input. Scratch only.
  python3 guide.py B|A
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-concepts-1126"
OUT = os.path.join(SP, "out")
REPO = "/home/user/homedesign-app"
LAY = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10/layers")
FB13 = os.path.join(REPO, "assets/renders/living-room/warm-modern/fb13-2026-11-25")
X = sys.argv[1]
RES = 2048
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
CW, CH = 2720, 1530
W, H = RES, int(round(RES * CH / CW))
SC = W / CW


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
        """planar depth of the point of the horizontal plane Z = Zw seen at canvas row py (full canvas px)"""
        v = (py - FB[1]) / (FB[3] - FB[1])
        return K * 16 / 9 * (loc[2] - Zw) / (v - v0)

    P.K, P.depth_at = K, depth_at
    return P


M0 = camera((0.83, 4.64, 1.20), 25, 24, 0.47, 0.50)
MW = camera((0.95, 5.55, 1.05), 14, 35, 0.50, 0.555)

srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)


def load_layer(rel):
    a = np.asarray(Image.open(os.path.join(LAY, rel)).convert("RGBA")).astype(np.float32) / 255.0
    return a


def warp(layer, Hm):
    """premultiplied warp of an RGBA layer (full M0 canvas) into the M0-W canvas at RES"""
    pm = layer.copy()
    pm[..., :3] *= pm[..., 3:4]
    o = cv2.warpPerspective(pm, Hm, (W, H), flags=cv2.INTER_AREA if SC < 1 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    al = o[..., 3:4]
    rgb = np.where(al > 1e-4, o[..., :3] / np.maximum(al, 1e-4), 0)
    return np.dstack([rgb, al])


def H_plane(pts_src_world, pts_dst_world=None):
    pts_dst_world = pts_dst_world or pts_src_world
    s = np.float32([M0(*p)[0] for p in pts_src_world])
    d = np.float32([MW(*p, scale=SC)[0] for p in pts_dst_world])
    return cv2.getPerspectiveTransform(s, d)


def H_sim(src_anchor_px, src_depth, dst_world):
    """similarity: the layer keeps its drawn proportions; scale = the two lenses and distances; the anchor lands on dst_world"""
    dpt, dw = MW(*dst_world, scale=SC)
    s = (MW.K / dw) / (M0.K / src_depth) * SC
    ax, ay = src_anchor_px
    return np.float64([[s, 0, dpt[0] - s * ax], [0, s, dpt[1] - s * ay], [0, 0, 1]]), s


def foot(layer, rows=0.06, thr=0.5):
    """bottom-centre of a cut-out: (x centre of its lowest rows, y of its bottom)"""
    al = layer[..., 3] > thr
    ys, xs = np.where(al)
    y1 = ys.max()
    y0 = int(y1 - rows * (y1 - ys.min()))
    sel = ys >= y0
    return 0.5 * (xs[sel].min() + xs[sel].max()), float(y1), (xs.min(), ys.min(), xs.max(), y1)


def blur_masked(img, m, sigma):
    num = cv2.GaussianBlur(img * m[..., None] if img.ndim == 3 else img * m, (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    return num / np.maximum(den[..., None] if img.ndim == 3 else den, 1e-4), den


def to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def from_lab(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def main():
    full = np.asarray(Image.open(os.path.join(OUT, f"clay555-{X}-{RES}.png")).convert("RGB")).astype(np.float32) / 255.0
    plate = np.asarray(Image.open(os.path.join(OUT, f"clay555-{X}-plate-{RES}.png")).convert("RGB")).astype(np.float32) / 255.0
    z = np.load(os.path.join(OUT, "passes555.npz"))
    idx = z["idx"]
    zp = np.load(os.path.join(OUT, "passes555-plate.npz"))
    idx_p = zp["idx"]
    assert idx.shape == (H, W), (idx.shape, H, W)
    P = {"rug": 801, "vase": 803, "planter": 804, "basket": 805, "magazine-holder": 806, "floor-lamp": 807, "framed-art": 808,
         "accent-sconces": 809, "pendant": 810, "bowl": 811, "candle-holders": 812, "coffee-table": 813, "cushion-left": 814,
         "cushion-right": 815, "cushion-lumbar": 816, "throw": 817, "candles": 831}
    # the sun's direct map on the clay (v0 0.52), moved down by the v0 change
    sun = np.asarray(Image.open(os.path.join(FB13, "m0w-sun.png"))).astype(np.float32) / 255.0
    sun = cv2.resize(sun, (W, H), interpolation=cv2.INTER_AREA)
    dy = 0.035 * (FB[3] - FB[1]) * SC
    sun = cv2.warpAffine(sun, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
    sun = cv2.GaussianBlur(np.clip(sun / 0.6, 0, 1), (0, 0), 2.0) if X == "B" else np.zeros_like(sun)
    # global relight of the M0 cut-outs (their frame: plaster L 89.5) to this clay's shade (B 74, A 78), and a warmer balance
    cal = json.load(open(os.path.join(OUT, "clay555-final.json")))
    Lsh = cal[X]["shaded"]
    Y = lambda L: ((L + 16) / 116) ** 3
    g = Y(Lsh) / Y(89.5)
    tint = np.float32([1.04, 1.0, 0.93]) if X == "B" else np.float32([1.03, 1.0, 0.95])
    ksun = 0.9

    def relight(rgb, gain=1.0, sunmap=True):
        lin = srgb2lin(rgb) * g * gain * tint
        if sunmap:
            lin = lin * (1 + ksun * sun[..., None])
        return np.clip(lin2srgb(lin), 0, 1)

    log = {}
    # the clay's balance: AgX and the 2700 K lamps leave the shaded plaster pink; bring it to bone in this light (one gain per channel,
    # on the full clay and the plate alike, so the sun patch and the lamp pools stay warmer than the shade)
    wall = (idx == 5) & (sun < 0.02)
    Lw = to_lab(full)
    shade_mask = wall & (np.abs(Lw[..., 0] - Lsh) < 4)
    med = np.median(full[shade_mask], axis=0)
    tgt_lab = np.float32([[[float(np.median(Lw[..., 0][shade_mask])), 2.5 if X == "B" else 1.5, 9.5 if X == "B" else 7.5]]])
    tgt = from_lab(tgt_lab)[0, 0]
    wb = srgb2lin(tgt) / srgb2lin(med)
    full = np.clip(lin2srgb(srgb2lin(full) * wb), 0, 1).astype(np.float32)
    plate = np.clip(lin2srgb(srgb2lin(plate) * wb), 0, 1).astype(np.float32)
    log["white_balance"] = dict(shade_rgb_before=[round(float(v_) * 255) for v_ in med], after=[round(float(v_) * 255) for v_ in tgt],
                                gains=[round(float(v_), 4) for v_ in wb])

    def chroma(img, m, ka, kb, dL=0.0, a0=None, b0=None):
        lab = to_lab(img)
        if a0 is not None:
            ma, mb_ = float(np.median(lab[..., 1][m])), float(np.median(lab[..., 2][m]))
            lab[..., 1] = np.where(m, a0 + ka * (lab[..., 1] - ma), lab[..., 1])
            lab[..., 2] = np.where(m, b0 + kb * (lab[..., 2] - mb_), lab[..., 2])
        else:
            lab[..., 1] = np.where(m, lab[..., 1] * ka, lab[..., 1])
            lab[..., 2] = np.where(m, lab[..., 2] * kb, lab[..., 2])
        lab[..., 0] = np.where(m, lab[..., 0] + dL, lab[..., 0])
        return from_lab(lab)

    # the smoked-oak floor (#8B6F55: a quiet brown, not orange)
    for nm in ("full", "plate"):
        im_ = full if nm == "full" else plate
        ii = idx if nm == "full" else idx_p
        im_ = chroma(im_, ii == 8, 0.55, 0.62, dL=-7.0)
        # the sofa: greige boucle (#CDC2B3), its clay facets smoothed
        sofa = (ii == 1)
        im_ = chroma(im_, sofa, 0.5, 0.5, dL=-6.5, a0=2.5, b0=11.0)
        sm, _ = blur_masked(im_, sofa.astype(np.float32), 7.0)
        soft_m = cv2.GaussianBlur(sofa.astype(np.float32), (0, 0), 1.5)[..., None]
        im_ = im_ * (1 - soft_m) + sm * soft_m
        rs = np.random.RandomState(1126)
        grain = cv2.GaussianBlur(rs.randn(H, W).astype(np.float32), (0, 0), 0.9) * 0.035
        im_ = np.clip(im_ + grain[..., None] * cv2.GaussianBlur(sofa.astype(np.float32), (0, 0), 1.0)[..., None], 0, 1)
        if nm == "full":
            full = im_.astype(np.float32)
        else:
            plate = im_.astype(np.float32)
    outside = ((idx == 0) | ((idx >= 700) & (idx < 800))) & (np.arange(W)[None, :] < 0.2 * W)
    if X == "B":
        om = cv2.GaussianBlur(outside.astype(np.float32), (0, 0), 1.0)[..., None]
        gold = np.clip(lin2srgb(srgb2lin(full) * np.float32([1.0, 0.90, 0.70])), 0, 1)
        full = (full * (1 - om) + gold * om).astype(np.float32)
    log["outside_px"] = int(outside.sum())
    out = full.copy()
    cover = np.zeros((H, W), np.float32)

    # 0. proxies that a cut-out replaces: the plate behind them, matched to the full clay around (the table and the rug stay as drawn)
    gone = np.isin(idx, [P[k] for k in ("planter", "basket", "framed-art", "accent-sconces", "pendant", "cushion-left",
                                           "cushion-right", "cushion-lumbar", "throw", "magazine-holder")])
    gone = cv2.dilate(gone.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & (idx != 830) & (idx != 833)
    valid = (~cv2.dilate(gone.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)).astype(np.float32)
    # the plate has no rug: under the holder the rug comes from the clay rug around it
    rugfill, _ = blur_masked(full, ((idx == P["rug"]) & (valid > 0)).astype(np.float32), 30.0)
    plate2 = plate.copy()
    mhm = cv2.dilate((idx == P["magazine-holder"]).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    plate2[mhm] = rugfill[mhm]
    R, den = blur_masked(srgb2lin(full) / np.maximum(srgb2lin(plate2), 0.01), valid, 22.0)
    R = np.where(den[..., None] > 0.02, np.clip(R, 0.7, 1.5), 1.0)
    fill = np.clip(lin2srgb(srgb2lin(plate2) * R), 0, 1)
    fill[mhm] = rugfill[mhm]
    gm = cv2.GaussianBlur(gone.astype(np.float32), (0, 0), 1.5)[..., None]
    out = out * (1 - gm) + fill * gm
    tele = np.isin(idx, [P["bowl"], P["candle-holders"], P["candles"], P["vase"], P["floor-lamp"]])
    tele = cv2.dilate(tele.astype(np.uint8), np.ones((7, 7), np.uint8))
    out = cv2.inpaint(np.rint(out * 255).astype(np.uint8), tele, 5, cv2.INPAINT_TELEA).astype(np.float32) / 255.0

    def paste(rgba, mask=None, soft=0.0):
        nonlocal out, cover
        a = rgba[..., 3]
        if mask is not None:
            a = a * mask
        if soft:
            a = cv2.GaussianBlur(a, (0, 0), soft)
        out = out * (1 - a[..., None]) + rgba[..., :3] * a[..., None]
        cover = np.maximum(cover, a)

    # 1. the rug: the floor's homography; its light from the clay rug (low frequencies), its weave and colour from the SKU layer
    rug = load_layer("rug/rug-cj-braided-wool-natural-fb12s1.png")
    Hr = H_plane([(-1.45, 0.77, 0.012), (1.85, 0.77, 0.012), (1.85, 3.07, 0.012), (-1.45, 3.07, 0.012)])
    wr = warp(rug, Hr)
    mrug_pure = (idx == P["rug"]).astype(np.float32)
    mrug = ((idx == P["rug"]) | (cv2.dilate((idx == P["magazine-holder"]).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)).astype(np.float32)
    have = (wr[..., 3] > 0.98).astype(np.float32)
    lab_s, lab_c = to_lab(wr[..., :3]), to_lab(full)
    lo_s, den = blur_masked(lab_s[..., 0], have, 14.0)
    lo_c, _ = blur_masked(lab_c[..., 0], mrug_pure, 14.0)
    # where the layer has no rug (it was hidden at M0), a tile of its own weave
    ys, xs = np.where(have > 0)
    det = lab_s[..., 0] - lo_s
    ab_mean = [float(np.median(lab_s[..., c][have > 0])) for c in (1, 2)]
    L_new = lo_c + np.where(have > 0, det, 0)
    lab_n = np.dstack([L_new, np.full_like(L_new, ab_mean[0]) + (lab_c[..., 1] - float(np.median(lab_c[..., 1][mrug_pure > 0]))) * 0.6,
                       np.full_like(L_new, ab_mean[1]) + (lab_c[..., 2] - float(np.median(lab_c[..., 2][mrug_pure > 0]))) * 0.6])
    # the missing weave: horizontal ribs synthesised at the layer's own pitch (perspective by row)
    rib = np.zeros((H, W), np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    # ground depth per row at M0-W -> world distance along the view -> ribs every 2.2 cm across the rug's length
    v = (yy / SC - FB[1]) / (FB[3] - FB[1])
    dgr = MW.K * 16 / 9 * 1.05 / np.maximum(v - 0.555, 1e-3)
    amp = float(np.std(det[have > 0])) if have.sum() else 1.5
    rib = np.sin(dgr / 0.022 * 2 * np.pi).astype(np.float32) * amp * 0.9
    rib = cv2.GaussianBlur(rib, (0, 0), 0.8)
    lab_n[..., 0] += np.where(have > 0, 0, rib)
    rug_rgb = from_lab(lab_n)
    paste(np.dstack([rug_rgb, mrug]), soft=0.6)
    log["rug"] = dict(px=int(mrug.sum()), from_layer_px=int((have * mrug).sum()))

    # 2. the trio and the sconces: the back wall's homography; the trio lit by the clay's own light on its panels
    art = load_layer("framed-art/framed-art-aliexpress-frameless-minimalist-wall-art-631735.png")
    Hw = H_plane([(-1.0, 0.03, 1.0), (1.5, 0.03, 1.0), (1.5, 0.03, 2.0), (-1.0, 0.03, 2.0)])
    wa = warp(art, Hw)
    mart = (idx == P["framed-art"]).astype(np.float32)
    Lc = to_lab(full)[..., 0]
    loA, _ = blur_masked(Lc, mart, 6.0)
    ref = float(np.median(Lc[(mart > 0) & (sun < 0.05)])) if ((mart > 0) & (sun < 0.05)).any() else float(np.median(Lc[mart > 0]))
    ratio = np.clip(Y(np.maximum(loA, 1)) / Y(ref), 0.6, 2.2)
    art_rgb = np.clip(lin2srgb(srgb2lin(wa[..., :3]) * g * 1.05 * tint * ratio[..., None]), 0, 1)
    paste(np.dstack([art_rgb, wa[..., 3]]))
    log["framed-art"] = dict(px=int((wa[..., 3] > 0.5).sum()), clay_px=int(mart.sum()))
    sc_ = load_layer("accent-sconces/accent-sconces-aliexpress-travertine-cylinder-walnut-choice.png")
    Hs = H_plane([(-1.0, 0.0575, 1.0), (1.5, 0.0575, 1.0), (1.5, 0.0575, 2.0), (-1.0, 0.0575, 2.0)])
    ws = warp(sc_, Hs)
    paste(np.dstack([relight(ws[..., :3], 1.25), ws[..., 3]]))

    # 3. standing and hanging things: similarity at the anchor (their drawn proportions kept)
    def stand(key, rel, z_src, dst_world, lit=None, rows=None, mask=None, gain=1.0, src_depth=None):
        lay = load_layer(rel)
        if rows is not None:                                   # keep only a band of the cut-out's rows (fractions of its bbox)
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
        if lit is not None:                                    # a lit shade: the band of rows (output px fractions of the warped bbox)
            ys, xs = np.where(w[..., 3] > 0.5)
            ya, yb = ys.min() + lit[0] * (ys.max() - ys.min()), ys.min() + lit[1] * (ys.max() - ys.min())
            band = ((np.arange(H)[:, None] >= ya) & (np.arange(H)[:, None] <= yb)).astype(np.float32) * np.ones((1, W), np.float32)
            band = cv2.GaussianBlur(band, (0, 0), 2.0)
            warm = np.clip(lin2srgb(srgb2lin(w[..., :3]) * np.float32([1.55, 1.38, 1.05])), 0, 1)
            rgb = rgb * (1 - band[..., None]) + warm * band[..., None]
            # the glow around the shade
            halo = cv2.GaussianBlur(w[..., 3] * band, (0, 0), 22.0)
            nonlocal_out_add(halo)
        paste(np.dstack([rgb, w[..., 3]]), mask=mask)
        log[key] = dict(src_foot=[round(fx, 1), round(fy, 1)], src_depth=round(float(d0), 3), scale_vs_m0_canvas=round(s / SC, 4),
                        dst_px=[round(float(v_), 1) for v_ in MW(*dst_world, scale=SC)[0]])

    def nonlocal_out_add(halo):
        nonlocal out
        add = halo[..., None] * np.float32([0.16, 0.12, 0.06])
        out = 1 - (1 - out) * (1 - np.clip(add, 0, 1))

    stand("vase", "vase/vase-cj-textured-white-stoneware-r6.png", 0.45, (-2.42, 1.35, 0.45), gain=1.0)
    stand("planter", "planter/planter-cj-cement-ribbed-belly-r7.png", 0.0, (-1.34, 0.55, 0.0), rows=(0.60, 1.0), gain=1.3)
    # the olive's trunk passes in front of the pot's rim: put the clay olive back over the pot
    ol = (idx == 830)
    out[ol] = full[ol]
    stand("floor-lamp", "floor-lamp/floor-lamp-cj-pleated-walnut-stem-158-r5.png", 0.0, (1.44, 0.20, 0.0), lit=(0.0, 0.17))
    # set B: the wall-parallel plane of the sofa's cushions (Y 0.40); the left cushion 10 cm in from the wider rounded arm
    cu = load_layer("cushions/set-B-fb12s0.png")
    n, lab_ = cv2.connectedComponents((cu[..., 3] > 0.5).astype(np.uint8))
    sizes = sorted(((int((lab_ == i).sum()), i) for i in range(1, n)), reverse=True)
    big = [i for s_, i in sizes if s_ > 4000]
    cxs = {i: float(np.where(lab_ == i)[1].mean()) for i in big}
    left_i = min(cxs, key=cxs.get)
    left, right = cu.copy(), cu.copy()
    ml = cv2.dilate((lab_ == left_i).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    left[~ml, 3] = 0
    ysl, xsl = np.where(left[..., 3] > 0.5)
    lumc = left[..., :3] @ np.float32([0.2126, 0.7152, 0.0722])
    xcut = xsl.max() - 0.14 * (xsl.max() - xsl.min())
    dark = (lumc < 0.16) & (np.arange(left.shape[1])[None, :] > xcut)
    left[cv2.dilate(dark.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool), 3] = 0
    right[ml, 3] = 0
    q = [(-0.9, 0.40, 0.44), (1.3, 0.40, 0.44), (1.3, 0.40, 1.0), (-0.9, 0.40, 1.0)]
    wl = warp(left, H_plane(q, [(x + 0.10, y, z_) for x, y, z_ in q]))
    wr_ = warp(right, H_plane(q, [(x - 0.03, y, z_) for x, y, z_ in q]))
    arm = (idx_p == 3)                                           # nothing of the set in front of the armchair
    paste(np.dstack([relight(wl[..., :3]), wl[..., 3]]), mask=(~arm).astype(np.float32))
    paste(np.dstack([relight(wr_[..., :3]), wr_[..., 3]]), mask=(~arm).astype(np.float32))
    log["cushions"] = dict(blobs=len(big), left_px=int((wl[..., 3] > 0.5).sum()), right_px=int((wr_[..., 3] > 0.5).sum()))
    # the Olia: the plane through the top's back edge and the feet's front edge; its light (low frequencies) from the clay table
    tb = load_layer("coffee-table/coffee-table-idana-javorina-olia-natural.png")
    x0, x1, y0, y1 = -0.30, 0.90, 1.395, 2.045
    top_q = [(x0, y0, 0.38), (x1, y0, 0.38), (x1, y1, 0.38), (x0, y1, 0.38)]
    inn_q = [(x0 + 0.03, y0, 0.0), (x0 + 0.03, y1, 0.0), (x0 + 0.03, y1, 0.36), (x0 + 0.03, y0, 0.36)]
    frn_q = [(x0, y1, 0.0), (x1, y1, 0.0), (x1, y1, 0.38), (x0, y1, 0.38)]

    def poly_mask(q):
        m_ = np.zeros(tb.shape[:2], np.uint8)
        cv2.fillPoly(m_, [np.int32([M0(*p_)[0] for p_ in q])], 1)
        return m_.astype(bool)

    m_top = poly_mask(top_q)
    m_inn = poly_mask(inn_q) & ~m_top
    m_frn = ~m_top & ~m_inn
    bl, br = M0(x0, y0, 0.38)[0], M0(x1, y0, 0.38)[0]
    fl_, fr2 = M0(x0, y1, 0.38)[0], M0(x1, y1, 0.38)[0]
    xx = np.arange(tb.shape[1], dtype=np.float32)[None, :]
    yyt = np.arange(tb.shape[0], dtype=np.float32)[:, None]
    front_line = fl_[1] + (fr2[1] - fl_[1]) * (xx - fl_[0]) / (fr2[0] - fl_[0])
    m_frn &= (yyt > front_line - 3) | (xx < bl[0] - 2)
    wt = np.zeros((H, W, 4), np.float32)
    for mm, q in ((m_frn, frn_q), (m_inn, inn_q), (m_top, top_q)):
        part = tb.copy()
        part[~cv2.dilate(mm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool), 3] = 0
        wp = warp(part, H_plane(q))
        a_ = wp[..., 3:4]
        wt[..., :3] = wt[..., :3] * (1 - a_) + wp[..., :3] * a_
        wt[..., 3:4] = np.maximum(wt[..., 3:4], a_)
    mt = np.isin(idx, [P["coffee-table"], P["bowl"], P["candle-holders"], P["candles"]]).astype(np.float32)
    at = (wt[..., 3] > 0.5).astype(np.float32)
    lab_t, lab_cc = to_lab(wt[..., :3]), to_lab(out)
    lo_t, _ = blur_masked(lab_t[..., 0], at, 18.0)
    lo_ct, _ = blur_masked(lab_cc[..., 0], mt, 18.0)
    lab_t2 = lab_t.copy()
    lab_t2[..., 0] = np.clip(lab_t[..., 0] - lo_t + 0.5 * lo_ct + 0.5 * (lo_t * (g ** (1 / 2.2))), 0, 100)
    lab_t2[..., 1] += 1.0
    lab_t2[..., 2] += 2.0
    paste(np.dstack([from_lab(lab_t2), wt[..., 3]]))
    log["coffee-table"] = dict(px=int(at.sum()), clay_px=int(mt.sum()))
    stand("bowl", "bowl/bowl-cj-matte-black-bowl-20-fb12s1.png", 0.38, (0.60, 1.90, 0.38), gain=1.0)
    stand("candle-holders", "candle-holders/candle-holders-cj-travertine-pedestal-fb12s1.png", 0.38, (0.28, 1.71, 0.38), gain=1.05)
    stand("pendant", "pendant/pendant-cj-tiered-fabric-drum-r4.png", None, (0.20, 1.72, 1.90), lit=(0.45, 1.0), src_depth=M0(0.20, 1.72, 1.9)[1])
    stand("basket", "basket/basket-cj-jute-rope-cylinder-r7.png", 0.0, (-1.80, 1.05, 0.0), mask=(idx_p != 3).astype(np.float32))
    mh = load_layer("magazine-holder/magazine-holder-cj-gunmetal-leather-strap-r6.png")
    # the holder is cut by the M0 canvas: the same world point (-0.47, 2.57), a plane facing the camera through it
    qm = [(-0.47 - 0.3, 2.57, 0.0), (-0.47 + 0.3, 2.57, 0.0), (-0.47 + 0.3, 2.57, 0.4), (-0.47 - 0.3, 2.57, 0.4)]
    wm = warp(mh, H_plane(qm))
    paste(np.dstack([relight(wm[..., :3]), wm[..., 3]]))
    log["magazine-holder"] = dict(px=int((wm[..., 3] > 0.5).sum()))

    # 4. the 16:9 frame, 1920 x 1080
    f = [v_ * SC for v_ in FB]
    Hc = np.float64([[1920 / (f[2] - f[0]), 0, -f[0] * 1920 / (f[2] - f[0])], [0, 1080 / (f[3] - f[1]), -f[1] * 1080 / (f[3] - f[1])], [0, 0, 1]])
    fr_ = cv2.warpPerspective(np.clip(out, 0, 1), Hc, (1920, 1080), flags=cv2.INTER_AREA)
    Image.fromarray(np.rint(fr_ * 255).astype(np.uint8)).save(os.path.join(OUT, f"guide-{X}.png"), optimize=True)
    Image.fromarray(np.rint(fr_ * 255).astype(np.uint8)).save(os.path.join(OUT, f"guide-{X}.jpg"), quality=92)
    fc = cv2.warpPerspective(full, Hc, (1920, 1080), flags=cv2.INTER_AREA)
    Image.fromarray(np.rint(fc * 255).astype(np.uint8)).save(os.path.join(OUT, f"clay-frame-{X}.png"), optimize=True)
    log["global_gain"] = round(float(g), 4)
    json.dump(log, open(os.path.join(OUT, f"guide-{X}.json"), "w"), indent=1)
    print(json.dumps(log, indent=1))


main()
