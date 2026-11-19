#!/usr/bin/env python3
"""
hdx2.py: the wall light carried from HT2 to HDx2 in code (brief, 4.7 row 3), render-agent 2026-11-19. 0 tokens.
HDx2 (hall-2026-11-18/hdx2.png, accepted 12.7.3) is not edited: the light is layers on it, like HT2's.

The lamp sticks out 11 cm, and HDx (HX, 1.75 m away) sees it about 13 deg more from the side than HT (2.7 m) and 1.43x larger,
so one homography of the stone plane would put the cylinder ~2 cm off its plate. Three maps instead, all exact geometry of geo.py:
  - the stone (X 0.81): the beams and the lamp's shadow on the wall are the wall's own: every HDx2 stone pixel (clay depth) is
    projected into HT and takes HT2's gain there (compose.py r1 stage); the light and the shadow are solved on hdx2.png's own
    pixels (its joints stay its own).
  - the cylinder: ray cast in HDx (3 x 3 samples a pixel: the alpha), each hit turned about the lamp's axis by the angle between
    the two views (the side that faces HDx is drawn by the side that faced HT; the travertine is rotationally even), then into HT.
  - the walnut block: ray cast as a box; its +Y face, 27 px wide in HDx2 and 5 px in HT2, takes HT2's drawn strip (x 1729.6-1734.2)
    stretched over its depth, shaded down 15 % toward the wall corner; the other faces their own projection.
  Then HT -> r1 (compose.sconce_map, the refit) -> r1's 4K pixels, divided by the r1 stage's exposure, times HDx2 / HT2 on the stone
  round the lamp (outside the beams).
  python3 hdx2.py   ->  OUT/hdx2-products.png, -frame.png, OUT/hdx2/{layers,shadows,light}/..., OUT/hdx2/manifest.json
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C  # noqa: E402
import geo as G  # noqa: E402

K = G.K
HDX = os.path.join(G.HALL18, "hdx2.png")
BOX = (230, 110, 480, 650)                 # x0, y0, x1, y1 in HDx2's canvas: the lamp and its block
SS = 3
BLOCK_STRIP_HT = (1729.6, 1734.2)          # HT2's drawn +Y face of the block (compose.BLOCK_BOX measurement)
STONE_ID = 94


def rays(cam, cv, X, Y):
    u = (X + 0.5 - cv.box[0]) / cv.fw
    v = (Y + 0.5 - cv.box[1]) / cv.fh
    P = cam.unproject(u, v, np.ones_like(u))
    Cc = np.asarray(cam.loc, float)
    return Cc, P - Cc


def hit_cylinder(Cc, d):
    ax, ay = G.SCONCE["axis"]
    r = G.SCONCE["r"]
    z0, z1 = G.SCONCE["z"]
    ox, oy = Cc[0] - ax, Cc[1] - ay
    a = d[..., 0] ** 2 + d[..., 1] ** 2
    b = 2 * (ox * d[..., 0] + oy * d[..., 1])
    c = ox * ox + oy * oy - r * r
    disc = b * b - 4 * a * c
    t = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a)
    z = Cc[2] + t * d[..., 2]
    side = (disc >= 0) & (t > 0) & (z >= z0) & (z <= z1)
    tc = (z0 - Cc[2]) / d[..., 2]
    qx, qy = ox + tc * d[..., 0], oy + tc * d[..., 1]
    cap = (tc > 0) & (qx * qx + qy * qy <= r * r) & ~side
    tt = np.where(side, t, np.where(cap, tc, np.inf))
    return tt, side, cap


def hit_box(Cc, d, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (lo - Cc) / d
        t2 = (hi - Cc) / d
    tmin = np.nanmax(np.minimum(t1, t2), -1)
    tmax = np.nanmin(np.maximum(t1, t2), -1)
    hit = (tmax >= tmin) & (tmax > 0)
    return np.where(hit, tmin, np.inf)


def view_angle(cam):
    ax, ay = G.SCONCE["axis"]
    return math.atan2(cam.loc[1] - ay, cam.loc[0] - ax)


def lamp_hdx():
    """per HDx2 pixel in BOX: alpha (coverage) and the HT canvas point each sample shows (averaged per pixel later by sampling)"""
    camh, cvh = K.CAMS["HDx"], K.canvas("HDx")
    camt, cvt = K.CAMS["HT"], K.canvas("HT")
    x0, y0, x1, y1 = BOX
    off = (np.arange(SS) + 0.5) / SS - 0.5
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    X = xx[..., None, None] + off[None, None, None, :]
    Y = yy[..., None, None] + off[None, None, :, None]
    X, Y = np.broadcast_arrays(X, Y)
    Cc, d = rays(camh, cvh, X, Y)
    tcyl, side, cap = hit_cylinder(Cc, d)
    lo, hi = G.SCONCE["block"]
    tblk = hit_box(Cc, d, lo, hi)
    cyl = tcyl < tblk
    blk = np.isfinite(tblk) & ~cyl
    P = Cc + np.where(cyl, tcyl, np.where(blk, tblk, 0))[..., None] * d
    # the cylinder: turn about the axis by the angle between the views
    ax, ay = G.SCONCE["axis"]
    dth = view_angle(camt) - view_angle(camh)
    px, py = P[..., 0] - ax, P[..., 1] - ay
    Pt = P.copy()
    Pt[..., 0] = np.where(cyl, ax + px * math.cos(dth) - py * math.sin(dth), P[..., 0])
    Pt[..., 1] = np.where(cyl, ay + px * math.sin(dth) + py * math.cos(dth), P[..., 1])
    u, v, _ = camt.project(Pt)
    xt, yt = cvt.px(u, v)
    # the block's +Y face (the one HDx sees widely): HT2's drawn strip stretched over the face's depth
    on_py = blk & (np.abs(P[..., 1] - hi[1]) < 1e-4)
    f = np.clip((P[..., 0] - lo[0]) / (hi[0] - lo[0]), 0, 1)
    xt = np.where(on_py, BLOCK_STRIP_HT[0] + f * (BLOCK_STRIP_HT[1] - BLOCK_STRIP_HT[0]), xt)
    shade = np.where(on_py, 0.85 + 0.15 * f, 1.0)                 # toward the wall corner: a little darker
    alpha = (cyl | blk).mean((-1, -2)).astype(np.float32)
    return dict(xt=xt, yt=yt, w=(cyl | blk).astype(np.float32), shade=shade, alpha=alpha, dth_deg=math.degrees(dth),
                cyl_px=int((cyl.mean((-1, -2)) > 0.5).sum()), blk_px=int((blk.mean((-1, -2)) > 0.5).sum()))


def main():
    o1, r1rep = C.load_stage("r1")
    e = np.array(r1rep["wall-sconce"]["exposure"])
    m4 = C.rgb8(os.path.join(G.OUT, "sources", "ht2p-r1-nano2-4k.jpg"))
    lm = lamp_hdx()
    # HT canvas -> r1 canvas (the refit) -> 4K, per sample; averaged per pixel (the samples are the anti-alias)
    xs, ys, _ = C.sconce_map(lm["xt"], lm["yt"])
    h, w = xs.shape[:2]
    flat = lambda a: a.reshape(h, w * SS * SS)
    smp = C.remap4(m4, flat(xs), flat(ys), sig=(0.8, 0.8)).reshape(h, w, SS, SS, 3)
    smp = K.to_lin(np.clip(smp, 0, 1)) / e * lm["shade"][..., None]
    wsum = lm["w"].sum((-1, -2))
    lin = (smp * lm["w"][..., None]).sum((-2, -3)) / np.maximum(wsum, 1e-6)[..., None]
    # exposure HDx2 / HT2 on the stone round the lamp, outside the beams (the lamp's body rows, 40-90 px either side)
    base_h = C.rgb8(HDX) / 255.0
    base_t = C.rgb8(C.BASE) / 255.0
    Yh = K.to_lin(base_h) @ K.W709
    Yt = K.to_lin(base_t) @ K.W709
    rh = np.concatenate([Yh[300:480, 230:290].ravel(), Yh[300:480, 400:460].ravel()])
    rt = np.concatenate([Yt[340:500, 1660:1710].ravel(), Yt[340:500, 1810:1860].ravel()])
    kx = float(np.median(rh) / np.median(rt))
    lin = lin * kx
    x0, y0, x1, y1 = BOX
    H2, W2 = base_h.shape[:2]
    rgb = np.zeros((H2, W2, 3), np.float32)
    rgb[y0:y1, x0:x1] = K.to_srgb(np.clip(lin, 0, 1))
    alpha = np.zeros((H2, W2), np.float32)
    alpha[y0:y1, x0:x1] = lm["alpha"]
    # the wall's gain (beams and the lamp's shadow): HDx2 stone pixel -> world (clay depth) -> HT -> HT2's gain
    P, ok = K.world("HDx")
    ids = K.clay_id("HDx")
    stone = ok & (ids == STONE_ID)
    u, v, dd = K.CAMS["HT"].project(P)
    mx, my = K.canvas("HT").px(u, v)
    g_ht = o1["wall-sconce"]["gain"]
    g = np.ones((H2, W2, 3), np.float32)
    for c in range(3):
        g[..., c] = cv2.remap(g_ht[..., c], mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=1.0)
    g[~stone] = 1.0
    # files, as HT2's: shadow (grey multiply, z 13), the lamp (z 14), the light (screen, z 90)
    b8 = C.rgb8(HDX)
    S8 = C.grey_shadow(b8, g)
    A8 = C.q8(alpha * 255)
    RGB8 = C.q8(rgb * 255)
    RGB8[A8 == 0] = 0
    pre = C.compose_step(b8, S8, A8, RGB8)
    lightm = ((g @ K.W709.astype(np.float32)) > 1.0005) & (A8 == 0)
    tgt = K.to_srgb(np.clip(K.to_lin(pre / 255.0) * np.maximum(g, 1.0), 0, 1)) * 255
    Lt = 255 - 255 * (255 - tgt) / np.maximum(255 - pre.astype(np.float32), 1e-3)
    L8 = C.q8(np.where(lightm[..., None], np.clip(Lt, 0, 255), 0))
    final = C.screen(pre, L8)
    pid = G.PIDS["wall-sconce"]["pid"]
    d = os.path.join(G.OUT, "hdx2")
    paths = dict(layer=os.path.join(d, "layers", "wall-sconce", pid + ".png"), shadow=os.path.join(d, "shadows", "wall-sconce", pid + ".png"),
                 light=os.path.join(d, "light", pid + ".png"))
    for p in paths.values():
        os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(np.dstack([RGB8, A8]), "RGBA").save(paths["layer"], optimize=True)
    Image.fromarray(S8, "L").save(paths["shadow"], optimize=True)
    Image.fromarray(L8, "RGB").save(paths["light"], optimize=True)
    chk = C.compose_step(b8, np.asarray(Image.open(paths["shadow"])), np.asarray(Image.open(paths["layer"]))[..., 3],
                         np.asarray(Image.open(paths["layer"]))[..., :3])
    chk = C.screen(chk, np.asarray(Image.open(paths["light"])))
    assert np.array_equal(chk, final)
    touched = (S8 < 255) | (A8 > 0) | (L8.max(-1) > 0)
    rnd2 = int(np.abs(chk.astype(int) - b8.astype(int))[~touched].max())
    K.save(os.path.join(G.OUT, "hdx2-products.png"), chk)
    cvh = K.canvas("HDx")
    K.save(os.path.join(G.OUT, "hdx2-products-frame.png"), cvh.crop_frame(chk, 1920, 1080))
    ys_, xs_ = np.nonzero(A8 > 127)
    uv0 = K.uv_of_px("HDx", xs_.min() - 0.5, ys_.min() - 0.5)
    uv1 = K.uv_of_px("HDx", xs_.max() + 0.5, ys_.max() + 0.5)
    man = dict(frame="HDx2", room="hall", style="warm-modern", date="2026-11-19", canvas=[W2, H2], frame_box=list(cvh.box),
               base="../../hall-2026-11-18/hdx2.png (accepted 12.7.3; not edited)",
               compose=dict(order=["base", "wall-sconce-shadow (z 13)", "wall-sconce (z 14)", "light (screen, z 90)"],
                            formula="as HT2's (../layers/manifest.json)"),
               layers=[dict(slot="wall-sconce", product=pid, card=G.PIDS["wall-sconce"]["card"], sku=G.PIDS["wall-sconce"]["sku"], z=14,
                            shadow_z=13, default=True, layer=os.path.relpath(paths["layer"], d), shadow=os.path.relpath(paths["shadow"], d),
                            alpha_px=int((A8 > 0).sum()), shadow_px=int((S8 < 255).sum()))],
               light=[dict(slot="wall-sconce", product=pid, z=90, blend="screen", file=os.path.relpath(paths["light"], d),
                           px=int((L8.max(-1) > 0).sum()))],
               method=dict(stone="exact (wall plane via the clay depth) -> HT2's gain", cylinder="ray cast, turned %.2f deg about its axis" % lm["dth_deg"],
                           block="ray cast box; its +Y face from HT2's 5 px strip stretched to %d px, shaded 0.85-1 toward the wall" % 27,
                           exposure_r1=list(e), hdx2_over_ht2_stone=round(kx, 4), samples_per_px=SS * SS),
               lamp_uv=dict(u=[round(uv0[0], 4), round(uv1[0], 4)], v=[round(uv0[1], 4), round(uv1[1], 4)], designer="u 0.12-0.14, v 0.08-0.26 (4.3)"),
               rnd2=dict(outside_every_alpha_shadow_light_max_diff_vs_hdx2=rnd2, recomposed_equals_written=True),
               missing="the right lamp (row 15): a known temporary asymmetry (8.4)")
    K.dump(os.path.join(d, "manifest.json"), man)
    print(json.dumps(dict(rnd2=rnd2, kx=round(kx, 4), dth=round(lm["dth_deg"], 2), cyl_px=lm["cyl_px"], blk_px=lm["blk_px"],
                          lamp_uv=man["lamp_uv"], light_px=man["light"][0]["px"]), indent=1))


if __name__ == "__main__":
    main()
