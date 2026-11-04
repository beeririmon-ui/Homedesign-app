#!/usr/bin/env python3
"""
fix_v8.py: QA's zero-token code fixes on the four v8 retakes (qa/reports/2026-11-03-retakes-g1.md §11.1; brief
briefs/render-retakes-code-fixes-2026-11-04.md task 1). render-agent, 2026-11-04. 0 var2 tokens. Nothing of the retakes is
overwritten: each fix reads the normalised still <out_dir>/<id>.png (2736x1539) and writes <out_dir>/<id>-fix.png (ungraded) and
<out_dir>/<id>-fix.json (what, how, the numbers before / after); the grade (v4) and the lock are run after by process_v8.py and
lock_v2.py on the -fix.png. The helpers are fix_v7.py's (mattes, fills, layer transforms), imported, unchanged.

  python3 fix_v8.py b1 | kgirl0 | w0in | b2 | all
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import fix_v7 as F  # noqa: E402

DATE = "2026-11-04"
SCRIPT = "assets/renders/house-nordic-v7-2026-11-02/fix_v8.py"
FIX_SUFFIX = "-fix"          # fix_v9.py (2026-11-04 cleanup) sets "-fix2": new files, the QA'd -fix stills stay


def hls(a):
    h = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    return h[..., 0] * 2, h[..., 1] / 255 * 100, h[..., 2] / 255 * 100      # hue deg, L %, S %


def largest(mask, min_area=0):
    m = (mask > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return m.astype(np.float32)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return (lab == k).astype(np.float32)


def keep_big(mask, min_area):
    m = (mask > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    out = np.zeros_like(m, np.float32)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] >= min_area:
            out[lab == k] = 1
    return out


def dil(mask, r):
    return cv2.dilate((mask > 0.5).astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)).astype(np.float32)


def contact_shadow(out, x0, x1, y, depth=0.72, h_px=14, spread=1.15):
    """A soft elliptical contact shadow on the floor under an object whose base spans x0..x1 at row y (multiplicative)."""
    H, W = out.shape[:2]
    m = np.zeros((H, W), np.float32)
    cx, rx = (x0 + x1) / 2, (x1 - x0) / 2 * spread
    cv2.ellipse(m, (int(cx), int(y)), (int(rx), int(h_px)), 0, 0, 360, 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), h_px * 0.8)
    m = m / max(m.max(), 1e-6)
    return out * (1 - (1 - depth) * m[..., None])


def nc_fill(a, hole, valid, scales=((30, 2), (60, 60), (160, 160)), min_den=0.02):
    """Fill `hole` by normalised convolution of the `valid` pixels: blur(a * valid) / blur(valid), first with the
    anisotropic scale (horizontal bands such as a skirting continue), then wider for what is still unfilled. For smooth
    surfaces (walls, floors). Returns a copy."""
    out = a.copy()
    todo = hole > 0.5
    v = valid.astype(np.float32)
    for sx, sy in scales:
        if not todo.any():
            break
        num = cv2.GaussianBlur(a * v[..., None], (0, 0), sigmaX=sx, sigmaY=sy)
        den = cv2.GaussianBlur(v, (0, 0), sigmaX=sx, sigmaY=sy)
        ok = todo & (den > min_den)
        out[ok] = num[ok] / den[ok][:, None]
        todo = todo & ~ok
    return out


def poly_fill(a, hole, valid, pad=160, deg=2):
    """Fill `hole` with a 2-D polynomial (degree `deg`, per channel) fitted to the `valid` pixels in the hole's bounding box
    grown by `pad` px: a smooth lit wall (lamp falloff, window gradient) without the far-away bias of a wide blur."""
    H, W = hole.shape
    ys, xs = np.nonzero(hole > 0.5)
    if len(ys) == 0:
        return a.copy()
    y0, y1, x0, x1 = max(0, ys.min() - pad), min(H, ys.max() + pad), max(0, xs.min() - pad), min(W, xs.max() + pad)
    sub_v = valid[y0:y1, x0:x1] > 0.5
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    cy, cx, sc = (y0 + y1) / 2, (x0 + x1) / 2, max(y1 - y0, x1 - x0) / 2
    Y_, X_ = (yy - cy) / sc, (xx - cx) / sc
    terms = [np.ones_like(X_)] + [X_ ** i * Y_ ** j for i in range(deg + 1) for j in range(deg + 1 - i) if i + j > 0]
    Afull = np.stack([t.ravel() for t in terms], 1)
    m = sub_v.ravel()
    step = max(1, int(m.sum() // 40000))
    idx = np.nonzero(m)[0][::step]
    out = a.copy()
    pred_full = a.copy()
    for c in range(3):
        b = a[y0:y1, x0:x1, c].ravel()
        coef, *_ = np.linalg.lstsq(Afull[idx], b[idx], rcond=None)
        pred = (Afull @ coef).reshape(y1 - y0, x1 - x0)
        pred_full[y0:y1, x0:x1, c] = pred
    # seam: the model's own step at a 12 px ring of valid pixels (original - prediction), spread into the hole and faded
    # with the distance from the ring, so the fill meets the intact wall exactly and keeps the model's smooth shape inside
    ring = ((dil(hole, 12) - (hole > 0.5)).clip(0, 1) * (valid > 0.5)).astype(np.float32)
    d = (a - pred_full) * ring[..., None]
    corr = cv2.GaussianBlur(d, (0, 0), 25) / np.maximum(cv2.GaussianBlur(ring, (0, 0), 25), 1e-4)[..., None]
    fade = np.clip(cv2.GaussianBlur(ring, (0, 0), 25) / 0.04, 0, 1)[..., None]
    h = (hole > 0.5)[..., None]
    out = np.where(h, pred_full + corr * fade, out)
    return out


def add_texture_m(a, filled, hole, src_box_px, strength=0.8, blur=6):
    """fix_v7.add_texture with the source patch's high-pass tiled MIRRORED (alternate tiles flipped), so the tile edges
    are continuous and leave no vertical / horizontal seam lines on a plain wall."""
    x0, y0, x1, y1 = src_box_px
    patch = a[y0:y1, x0:x1]
    hp = patch - cv2.GaussianBlur(patch, (0, 0), blur)
    tile = np.concatenate([np.concatenate([hp, hp[:, ::-1]], 1), np.concatenate([hp[::-1], hp[::-1, ::-1]], 1)], 0)
    H, W = hole.shape
    reps = (H // tile.shape[0] + 2, W // tile.shape[1] + 2, 1)
    big = np.tile(tile, reps)[:H, :W]
    m = (hole > 0.5)[..., None]
    return np.where(m, filled + strength * big, filled)


def copy_down_fill(a, hole, period):
    """Fill hole pixels row by row from top to bottom with the content `period` rows above (already filled rows reused):
    for vertical textures (curtain folds, weave). Returns a copy."""
    out = a.copy()
    ys = np.nonzero((hole > 0.5).any(1))[0]
    for y in ys:
        xs = np.nonzero(hole[y] > 0.5)[0]
        out[y, xs] = out[max(0, y - period), xs]
    return out


def seam_correct(filled, orig, hole, sigma=30, ring_px=8):
    """Low-frequency correction so a filled region meets its surroundings without a visible step: the difference between
    the original and the filled estimate is read on a ring around the hole (where the estimate is recomputed by the same
    rule, so the difference is the step) and spread into the hole by normalised convolution."""
    ring = (dil(hole, ring_px) - (hole > 0.5)).clip(0, 1)
    d = (orig - filled) * ring[..., None]
    num = cv2.GaussianBlur(d, (0, 0), sigma)
    den = cv2.GaussianBlur(ring, (0, 0), sigma)
    corr = num / np.maximum(den, 1e-4)[..., None]
    w = (hole > 0.5)[..., None]
    return np.where(w, filled + corr, filled)


def despeck(out, region, protect, thr=6.0, max_area=200):
    """Small dark flecks left on a plain wall (leaf fragments under the matte's size limit): components darker than the local
    median (15 px) by > thr L, area < max_area, inside `region` and outside `protect`, filled from their surroundings."""
    _, L, _ = hls(out)
    med = cv2.medianBlur(np.clip(L, 0, 100).astype(np.uint8), 15).astype(np.float32)
    m = (((med - L) > thr) & (region > 0.5) & (protect < 0.5)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] <= max_area:
            keep[lab == i] = 1
    hole = dil(keep.astype(np.float32), 3)
    return nc_fill(out, hole, 1 - hole, scales=((6, 6), (15, 15), (40, 40))), int(keep.sum())


def global_affine_to_clay(fid, out, A_fixed=None):
    """One affine on the whole still (the overscan canvas): the inverse of lock_v2's ECC register of this still against its clay
    (measured on the 16:9 frame at 1920 x 1080, carried to the canvas), so the frame's global shift and scale go to ~0 (G1.4);
    Lanczos, border replicated (only the outer canvas rows / columns, outside the 16:9 frame, are affected). Returns (still, record)."""
    import lock_v2 as LK
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    Hs, Ws = out.shape[:2]
    clay = LK.load_rgb(os.path.join(VF.R4, clay_file))

    def fit16(img):
        return LK.pr.fit(LK.crop_frame(img) if overscan else img, 1920, 1080)

    def reg(img01):
        _, M = LK.pr.register(fit16(img01), fit16(clay))
        return M
    a01 = np.clip(out / 255.0, 0, 1).astype(np.float32)
    M = reg(a01)
    fx0, fy0, fx1, fy1 = VF.frame_box_px(Ws, Hs) if overscan else (0, 0, Ws, Hs)
    sx, sy = (fx1 - fx0) / 1920.0, (fy1 - fy0) / 1080.0
    C = np.array([[sx, 0, fx0], [0, sy, fy0], [0, 0, 1]], float)
    A = C @ np.vstack([M, [0, 0, 1]]) @ np.linalg.inv(C)
    if A_fixed is not None:          # fix_v9: the canvas affine of an earlier, QA'd run (the same geometry under a cleaned patch)
        A = np.vstack([np.array(A_fixed, float), [0, 0, 1]])
    warped = cv2.warpAffine(out.astype(np.float32), A[:2], (Ws, Hs), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    warped = np.clip(warped, 0, 255)
    M2 = reg(np.clip(warped / 255.0, 0, 1).astype(np.float32))
    rec = dict(why="G1.4 global scale (+0.54 / +0.78 % after the code fix, proposal 0.5 %): the manager's approval 2026-11-04; QA re-checks",
               register_before=dict(affine=np.round(M, 5).tolist(), shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)],
                                    scale_pct=[round((float(M[0, 0]) - 1) * 100, 3), round((float(M[1, 1]) - 1) * 100, 3)]),
               canvas_affine_inverse_map=np.round(A[:2], 6).tolist(),
               register_after=dict(shift_px=[round(float(M2[0, 2]), 2), round(float(M2[1, 2]), 2)],
                                   scale_pct=[round((float(M2[0, 0]) - 1) * 100, 3), round((float(M2[1, 1]) - 1) * 100, 3)]),
               how="cv2.warpAffine(still, A, WARP_INVERSE_MAP, Lanczos4, border replicate); A = C . M . C^-1, C = the 16:9 frame at 1920 -> the canvas")
    return warped, rec


def save_note(fid, note):
    p = os.path.join(VF.out_dir(fid), fid + FIX_SUFFIX + ".json")
    json.dump(dict(asset_id=fid, date=DATE, script=SCRIPT, tokens=0, **note), open(p, "w"), indent=1, ensure_ascii=False)
    return p


def still(fid):
    return F.load(os.path.join(VF.out_dir(fid), fid + ".png"))


def out_fix(fid):
    return os.path.join(VF.out_dir(fid), fid + FIX_SUFFIX + ".png")


# ---------------------------------------------------------------------------------------------------------------
# B1 r3: the invented plinth out, the planter (seagrass basket + fern) down 172 px to the floor; the brush x0.73 about its base
# ---------------------------------------------------------------------------------------------------------------
B1 = dict(planter_rect=(0.440, 0.598, 0.395, 0.768), plinth=(0.484, 0.562, 0.765, 0.884), dy=172,
          brush_rect=(0.448, 0.482, 0.680, 0.900), brush_scale=0.73,
          clay_pot=(0.49, 0.555, 0.75, 0.877), clay_brush=(0.4583, 0.475, 0.7432, 0.893),
          narrow_fills=True, curtain_patch_px=(1560, 300, 1640, 520),   # False restores the first run (surface fill behind the brush, 40-row curtain copy)
          global_affine=True,   # 2026-11-04, the manager's approval: the whole frame by the inverse of lock_v2's register (G1.4 scale); False = without
          # 2026-11-04 cleanup (QA 2026-11-04-retakes-fixes-g1 §4, fix_v9.py): "profile" = the second run's column profile (patches), "copy_above" =
          # the intact linen copied along its folds from above (the shift searched on the ring); holder_ratio None = the brush as scaled, 0.38 = the
          # holder squashed about its base to 38 % of the brush's height (the card: 14.5 cm of 38 cm), the handle continued down to it
          curtain_fill="profile", holder_ratio=None)


def edge_col(g, v0, v1, u0, u1):
    """The column of the strongest vertical edge (mean |d/dx| over rows v0..v1) between u0 and u1."""
    H, W = g.shape
    prof = np.abs(np.diff(g[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)], axis=1)).mean(0)
    prof = cv2.GaussianBlur(prof.reshape(1, -1), (1, 0), 0).ravel() if False else prof
    return int(u0 * W) + int(np.argmax(prof))


def _curtain_copy_above(a, bg, hc, vc, prof, curtain):
    """The covered linen (hc) from the intact linen above it, shifted along the folds: (dx, dy) searched (dy -260..-420, dx -40..40)
    for the least high-pass difference on a 12 px ring of intact linen around hc; the copy scaled by the curtain's vertical light
    profile (prof[y] / prof[y + dy]), a second pass for what the first source did not cover, then a low-frequency seam correction."""
    H, W = hc.shape
    hm = hc > 0.5
    # the ring on the curtain's interior only (30 px clear of its edge against the wall: the edge's own line would steer dx)
    inner = cv2.erode((curtain > 0.5).astype(np.uint8), np.ones((1, 61), np.uint8)) > 0
    ring = (dil(hc, 12) > 0.5) & ~hm & (vc > 0.5) & inner
    ry, rx = np.nonzero(ring)
    g = F.gray(a)
    hp = g - cv2.GaussianBlur(g, (0, 0), 3.0)
    okv = vc > 0.5
    best = None
    for dy in range(-200, -441, -4):
        for dx in range(-6, 7, 1):          # the folds hang vertically in the frame (their slant over 400 rows is < 6 px)
            sy, sx = ry + dy, rx + dx
            ok = (sy >= 0) & (sx >= 0) & (sx < W)
            ok[ok] &= okv[sy[ok], sx[ok]]
            if len(ok) == 0 or ok.mean() < 0.7:
                continue
            c = float(np.mean((hp[sy[ok], sx[ok]] - hp[ry[ok], rx[ok]]) ** 2))
            if best is None or c < best[0]:
                best = (c, dx, dy)
    _, dx, dy = best
    out = bg.copy()
    done = np.zeros((H, W), bool)
    for k in (1.0, 1.25, 1.5, 2.0, 0.75):
        ys, xs = np.nonzero(hm & ~done)
        sy, sx = ys + int(round(k * dy)), xs + int(round(k * dx))
        ok = (sy >= 0) & (sx >= 0) & (sx < W)
        ok[ok] &= okv[sy[ok], sx[ok]]
        ys, xs, sy, sx = ys[ok], xs[ok], sy[ok], sx[ok]
        out[ys, xs] = a[sy, sx] * np.clip(prof[ys] / prof[sy], 0.8, 1.25)
        done[ys, xs] = True
    # seam correction read on the intact linen ring only (the wall left of the curtain's edge would pull the copy lighter)
    ring2 = ((dil(done.astype(np.float32), 5) > 0.5) & ~done & (vc > 0.5)).astype(np.float32)
    dif = (cv2.GaussianBlur(a, (0, 0), 1.0) - out) * ring2[..., None]
    corr = cv2.GaussianBlur(dif, (0, 0), 12) / np.maximum(cv2.GaussianBlur(ring2, (0, 0), 12), 1e-3)[..., None]
    wgt = np.clip(cv2.GaussianBlur(ring2, (0, 0), 12) / 0.02, 0, 1)[..., None]
    out = np.where(done[..., None], out + corr * wgt, bg)
    # each column's top 24 rows blend from the linen there (no horizontal step where the copy starts)
    top = np.full(W, H)
    for x in np.nonzero(done.any(0))[0]:
        top[x] = np.nonzero(done[:, x])[0][0]
    wt = np.clip((np.arange(H)[:, None] - top[None, :]) / 24.0, 0, 1)
    out = np.where(done[..., None], bg * (1 - wt[..., None]) + out * wt[..., None], out)
    return out, dict(shift_px=[int(dx), int(dy)], ring_mse=round(best[0], 2), px=int(done.sum()), not_covered_px=int((hm & ~done).sum()),
                     how="the intact linen (curtain, not the fern's outline / leaves / the brush, L > 30) copied along its folds from (dx, dy) above "
                         "(dx -6..6, dy -200..-440 searched on a 12 px ring of the curtain's interior), x the curtain's vertical light profile (clipped 0.8-1.25); "
                         "the pixels whose source is not linen from 1.25 / 1.5 / 2 / 0.75 (dx, dy); a low-frequency seam correction read on the linen ring only "
                         "(sigma 12); each column's top 24 rows blended. Not covered (left as before): the pixels under the moved planter")


def _holder_rebuild(b_rgb, b_al, ratio, base):
    """The brush layer with its holder squashed about the base to `ratio` of the brush's height (the handle top stays): the holder
    rows (matte width >= 60 % of the widest) remapped y' = base - k (base - y); the handle continued down to the new holder top by
    repeating its own rows from 6-26 px above the old holder top."""
    H, W = b_al.shape
    m = b_al > 0.5
    wid = m.sum(1)
    rows = np.nonzero(wid > 0)[0]
    y0 = int(rows.min())
    body = np.nonzero(wid >= 0.6 * wid.max())[0]
    yt = int(body.min())
    Ht, Hh = base - y0, base - yt
    Hn = ratio * Ht
    k = Hn / Hh
    new_top = int(round(base - Hn))
    ys_out = np.arange(H, dtype=np.float32)
    src = np.where(ys_out >= new_top, base - (base - ys_out) / k, ys_out)
    mapy = np.repeat(src[:, None], W, 1).astype(np.float32)
    mapx = np.repeat(np.arange(W, dtype=np.float32)[None, :], H, 0)
    rgb2 = cv2.remap(b_rgb, mapx, mapy, cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    al2 = cv2.remap(b_al, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # the handle between the old holder top and the new one: its rows from just above the old top, repeated
    ref0, ref1 = yt - 26, yt - 6
    for y in range(yt - 6, new_top):
        r = ref0 + (y - ref0) % (ref1 - ref0)
        rgb2[y] = b_rgb[r]
        al2[y] = b_al[r]
    rec = dict(ratio=ratio, brush_height_px=int(Ht), holder_before_px=int(Hh), holder_after_px=int(round(Hn)), k=round(k, 4),
               holder_top_before=yt, holder_top_after=new_top, base=base, holder_share_before=round(Hh / Ht, 3), holder_share_after=round(Hn / Ht, 3))
    return rgb2, np.clip(al2, 0, 1), rec


def fix_b1(preview=True):
    fid = "b1-v7-r3"
    a = still(fid)
    H, W = a.shape[:2]
    hue, L, S = hls(a)
    g = F.gray(a)
    # --- planter matte (fern + seagrass basket, above the plinth): sage leaves, their dark gaps, the brown basket
    u0, u1, v0, v1 = B1["planter_rect"]
    roi = F.rect_mask(H, W, u0, u1, v0, v1)
    fern = (((hue >= 48) & (hue <= 150) & (S >= 6) & (L <= 85)) | (L < 38)).astype(np.float32)     # backlit tips are light (L 66-80)
    brown = ((hue >= 10) & (hue <= 42) & (S > 18) & (L > 20) & (L < 64)).astype(np.float32)
    bu0_, bu1_, bv0_, bv1_ = B1["brush_rect"]
    roi = roi * (1 - dil(F.rect_mask(H, W, bu0_, bu1_, bv0_, bv1_), 6))       # the brush is not the planter
    pl = keep_big((fern + brown).clip(0, 1) * roi, 15)                          # thin fronds too
    pl = cv2.morphologyEx(pl.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32)
    px0, px1, py0, py1 = F.bbox(pl)
    # the basket band: rows whose brown run is wide (>= 60 % of the widest)
    bw = (brown * pl).sum(1)
    rows_b = np.nonzero(bw >= 0.6 * bw.max())[0]
    b_top, b_bot = int(rows_b.min()), int(rows_b.max())
    # --- the brush
    bu0, bu1, bv0, bv1 = B1["brush_rect"]
    br = ((L < 32) * F.rect_mask(H, W, bu0, bu1, bv0, bv1)).astype(np.float32)
    br = largest(cv2.morphologyEx(br.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    bx0, bx1, by0, by1 = F.bbox(br)
    # --- holes: a solid blob over the planter (its leaf shadows on the wall go too), the plinth, the brush
    pu0, pu1, pv0, pv1 = B1["plinth"]
    blob = cv2.morphologyEx(pl.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    cnts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blob = np.zeros((H, W), np.uint8)
    cv2.drawContours(blob, cnts, -1, 1, -1)
    hole_p = np.maximum(dil(blob, 40), F.rect_mask(H, W, pu0, pu1, pv0, pv1))     # the fern's soft shadow on the wall goes too (it moves with the fern below)
    hole_b = dil(br, 6)
    valid = 1 - np.maximum(hole_p, hole_b)
    # --- the curtain's left edge: where the linen's saturation rises above the wall's (S 13-14 -> 17-19 %), measured at
    # v 0.30-0.42 above the plant (u 0.532) and beside the plinth at the floor (u 0.556); a line between them
    ya, yb, xa, xb = 0.40, 0.84, int(0.532 * W), int(0.556 * W)
    Yr = np.arange(H)[:, None]
    xc = xa + (xb - xa) * (Yr / H - ya) / (yb - ya)
    curtain = (np.arange(W)[None, :] >= xc).astype(np.float32) * np.ones((H, W), np.float32)
    # --- fills. Wall, skirting and floor: normalised convolution of the true wall / floor pixels only (u >= 0.400, so not
    # the WC block's ledge; not the roll paper, the dark stand, the curtain or any hole), first horizontal (sx 30, sy 2: the
    # skirting band continues), then isotropic; with the wall's high-pass texture. Curtain columns: from the curtain above.
    U = np.arange(W)[None, :] / W * np.ones((H, 1), np.float32)
    holes = np.maximum(hole_p, hole_b)
    wall_valid = ((U >= 0.400) & (holes < 0.5) & (curtain < 0.5) & (L >= 40) & (L <= 88) & (S < 30)).astype(np.float32)
    hw = holes * (1 - curtain)
    Vr = Yr / H * np.ones((1, W), np.float32)
    hw_up, hw_low = hw * (Vr < 0.775), hw * (Vr >= 0.775)
    bg = poly_fill(a, hw_up, wall_valid, pad=160, deg=2)                                # the wall: a smooth quadratic surface fitted around the hole
    bg = nc_fill(bg, hw_low, wall_valid, scales=((30, 2), (60, 60), (160, 160)))     # skirting and floor rows: the bands continue
    bg = F.add_texture(a, bg, hw, (int(0.402 * W), int(0.40 * H), int(0.440 * W), int(0.47 * H)), 0.8)   # clean wall (no sconce edge, no roll)
    if B1.get("narrow_fills", True):
        # second run (2026-11-04): the brush's hole is narrow (~37 px): row by row between the wall / skirting / floor pixels left and
        # right of it, which keeps each row's light; the first run's surface fit left a lighter rectangle behind the smaller brush
        vb = ((holes < 0.5) & (curtain < 0.5) & (L >= 40) & (U >= 0.400)).astype(np.float32)
        bg = F.fill_rows_valid(bg, hole_b * (1 - hole_p), vb, band_px=6, max_search=60)
        bg = add_texture_m(a, bg, hole_b * (1 - hole_p), (int(0.402 * W), int(0.40 * H), int(0.440 * W), int(0.47 * H)), 0.6)
    # the curtain part: only the pixels the leaves (and the plinth) actually covered, filled locally from just above
    hc = np.maximum(dil(pl, 4), F.rect_mask(H, W, pu0, pu1, pv0, pv1)) * curtain
    # the curtain: its own weave copied down with a period of 330 rows (the folds are vertical), then a low-frequency seam
    # correction read on a ring around the region (the copied estimate at the ring vs the curtain there)
    if B1.get("narrow_fills", True):
        # second run: each covered curtain column continued down from the intact linen just above its covered part (the folds
        # are vertical), times the curtain's own vertical light profile (median of the intact columns x 1600-1650), with the
        # linen's high-pass weave from an intact patch; the first run's copy with a 40-row period left blocky steps, and an
        # interpolation to the linen below / between the fronds took the fern's shadow and left bars
        hc = dil(np.maximum(blob.astype(np.float32), F.rect_mask(H, W, pu0, pu1, pv0, pv1)), 6) * curtain    # the fern's whole outline on the linen
        linen = ((S < 25) & ((hue < 45) | (S < 8)) & (L > 55)).astype(np.float32)                           # no backlit frond tips as a reference
        vc = curtain * (1 - holes) * (1 - dil(pl, 4)) * (1 - hc) * linen
        prof = cv2.GaussianBlur(np.ascontiguousarray(a[:, 1600:1650].mean(1)), (0, 0), 20).reshape(H, 3)   # rows x RGB, smoothed along y
        prof = np.maximum(prof, 1.0)
        if B1.get("curtain_fill") == "copy_above":
            # the reference: intact linen (not the fern's outline, not its leaves, not the brush), the 40 px planter margin included
            vc2 = curtain * (1 - hc) * (1 - dil(pl, 6)) * (1 - hole_b) * (L > 30)        # the folds' dark valleys are linen too
            bg, curtain_copy = _curtain_copy_above(a, bg, hc, vc2, prof, curtain)
        filled = bg.copy()
        cols = np.nonzero((hc > 0.5).any(0))[0] if B1.get("curtain_fill") != "copy_above" else np.zeros(0, int)
        last_ref = None
        for x in cols:
            ys = np.nonzero(hc[:, x] > 0.5)[0]
            y_t = int(ys.min())
            r0, r1 = max(0, y_t - 70), max(1, y_t - 10)
            sel = np.nonzero(vc[r0:r1, x] > 0.5)[0] + r0
            if len(sel) >= 8:
                ref = np.median(a[sel, x] / prof[sel], 0)
                last_ref = ref
            elif last_ref is not None:
                ref = last_ref
            else:
                continue
            wtop = np.clip((ys - y_t) / 24.0, 0, 1)[:, None]                      # the top 24 rows blend from the linen there: no steps
            filled[ys, x] = a[ys, x] * (1 - wtop) + (ref[None, :] * prof[ys]) * wtop
        if B1.get("curtain_fill") != "copy_above":
            bg = np.where((hc > 0.5)[..., None], cv2.GaussianBlur(filled, (0, 0), sigmaX=1.2, sigmaY=6), bg)
            bg = add_texture_m(a, bg, hc, B1["curtain_patch_px"], 0.9, blur=3)
    else:
        est = copy_down_fill(bg, np.maximum(hc, dil(hc, 8)), 40)
        bg = np.where((hc > 0.5)[..., None], est, bg)
        ring = (dil(hc, 10) - (hc > 0.5)).clip(0, 1) * curtain * (1 - holes)       # intact curtain pixels around the region only
        d = (a - est) * ring[..., None]
        corr = cv2.GaussianBlur(d, (0, 0), 25) / np.maximum(cv2.GaussianBlur(ring, (0, 0), 25), 1e-4)[..., None]
        bg = np.where((hc > 0.5)[..., None], bg + corr, bg)
    out = bg
    dy = B1["dy"]
    # --- the fern's shadow on the wall as a ratio map (original / clean wall) in the wall zone around it, moved with it
    zone = hole_p * (1 - curtain) * (1 - F.rect_mask(H, W, pu0, pu1, pv0, pv1)) * (1 - dil(pl, 2)) * (1 - hole_b)
    ratio = np.clip(a / np.maximum(bg, 1.0), 0.45, 1.0)
    ratio = np.where((zone > 0.5)[..., None], ratio, 1.0)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 3.0)
    r_m, z_m = F.transform_layer(ratio, F.feather(zone, 6), 1.0, (0, 0), 0, dy)
    out = out * (1.0 + (np.clip(r_m, 0.45, 1.0) - 1.0) * z_m[..., None] * (1 - curtain[..., None]))
    # --- the planter down dy, contact shadow under the basket
    p_rgb, p_al = F.transform_layer(a, F.feather(pl, 0.8), 1.0, (0, 0), 0, dy)
    xs = np.nonzero(pl[b_bot - 4:b_bot + 1].sum(0) > 0)[0]
    out = contact_shadow(out, xs.min(), xs.max(), b_bot + dy - 2, depth=0.70, h_px=10, spread=1.08)
    out = F.composite(out, p_rgb, p_al)
    # --- the brush x0.73 about its base
    ax = float(np.nonzero(br[by1 - 4:by1 + 1] > 0.5)[1].mean())
    s_ = B1["brush_scale"]
    b_rgb, b_al = F.transform_layer(a, F.feather(br, 0.7), s_, (ax, float(by1)))
    holder = None
    if B1.get("holder_ratio"):
        b_rgb, b_al, holder = _holder_rebuild(b_rgb, b_al, B1["holder_ratio"], int(by1))
    out = contact_shadow(out, ax - (bx1 - bx0) * s_ / 2, ax + (bx1 - bx0) * s_ / 2, by1 - 1, depth=0.75, h_px=6, spread=1.3)
    out = F.composite(out, b_rgb, b_al)
    wall_zone = F.rect_mask(H, W, 0.440, 0.535, 0.40, 0.745) * (1 - curtain)       # right of the roll stand (u <= 0.433)
    out, n_speck = despeck(out, wall_zone, dil(np.maximum(p_al, b_al), 4))
    affine = None
    if B1.get("global_affine"):
        out, affine = global_affine_to_clay(fid, out)
    F.save(out, out_fix(fid))
    nb = F.bbox(b_al)
    pot, cb = B1["clay_pot"], B1["clay_brush"]
    note = dict(
        fix="B1 r3 (QA §11.1): the stone plinth the model invented under the seagrass basket removed and the planter (basket + fern) moved down onto the floor; the toilet brush scaled x0.73 about its base",
        method=("planter matte in u 0.440-0.598 (the roll holder's arm at u <= 0.433 stays out), v 0.395-0.768: sage leaves (hue 48-150, S >= 6, L <= 85: the backlit tips are light), their dark gaps (L < 38) and the brown basket (hue 10-42, "
                "S > 18), every component >= 15 px (thin fronds too), the brush's rect excluded, closed 7 px; hole = the planter and every leaf component >= 60 px closed 41 px, filled solid and dilated 40 px (its soft shadow on the wall goes with it and is "
                "carried down with the plant as a ratio map, original / clean wall, as in the K-girl doll fix), plus the plinth rect u 0.484-0.562, v 0.765-0.884; the curtain's left edge where the linen's saturation rises above the wall's "
                "(u 0.532 above the plant, 0.556 at the floor, a line); on the curtain only the pixels the leaves covered (dilated 4 px) are filled, with the curtain's own weave copied down from 40 rows above (the folds are vertical) and a low-frequency seam correction read on an 8 px ring; wall, "
                "skirting and floor columns, and the brush (L < 32 % in u 0.448-0.482, v 0.680-0.900, dilated 6 px), filled by normalised convolution of the true "
                "wall / floor pixels only (u >= 0.400, L 40-88 %, S < 30 %, no hole, no curtain), on the wall a quadratic surface per channel fitted to the intact wall within 160 px of the hole, and horizontal-first on the skirting / floor "
                "rows below v 0.775 (30 x 2 px: the bands continue), with a seam correction (the fit's own residual on a 12 px ring of intact wall, spread into the hole) and the high-pass texture of a clean wall patch (u 0.402-0.440, v 0.40-0.47); the planter layer moved down rigidly by dy px "
                "with a soft elliptical contact shadow under the basket; the brush scaled about the centre of its base (INTER_AREA) with a small contact shadow"),
        curtain_edge_px=dict(above_plant=[xa, int(ya * H)], at_the_floor=[xb, int(yb * H)], how="the linen's saturation rises above the wall's (S 13-14 -> 17-19 %)"),
        planter=dict(matte_box_uv=[round(px0 / W, 4), round(px1 / W, 4), round(py0 / H, 4), round(py1 / H, 4)], basket_rows_before=[b_top, b_bot],
                     basket_rows_after=[b_top + dy, b_bot + dy], dy_px=dy, clay_pot_box_rows=[round(pot[2] * H), round(pot[3] * H)],
                     basket_bottom_minus_clay_pot_bottom_px=int(b_bot + dy - round(pot[3] * H)),
                     basket_height_over_clay_pot=round((b_bot - b_top) / ((pot[3] - pot[2]) * H), 3),
                     qa_reference="QA bath-products.json: basket rows 1003-1180, plinth 1185-1357 (172 px), the plinth bottom 7 px below the clay pot bottom"),
        brush=dict(scale=s_, base_uv=[round(ax / W, 4), round(by1 / H, 4)], before_uv=[round(bx0 / W, 4), round(bx1 / W, 4), round(by0 / H, 4), round(by1 / H, 4)],
                   after_uv=[round(nb[0] / W, 4), round(nb[1] / W, 4), round(nb[2] / H, 4), round(nb[3] / H, 4)],
                   height_over_clay_box=dict(before=round((by1 - by0) / ((cb[3] - cb[2]) * H), 3), after=round((nb[3] - nb[2]) / ((cb[3] - cb[2]) * H), 3))),
        second_run=(dict(date="2026-11-04", why="the first run's 40-row curtain copy left blocky steps on the linen and its surface fill a lighter rectangle behind the smaller brush",
                         curtain=("the fern's whole outline on the linen (closed, dilated 6 px; the plinth rect too) refilled column by column from the intact linen "
                                  "60-10 rows above each column's covered part (hue / saturation gated: no backlit frond tips), times the curtain's own vertical light "
                                  "profile (median of the intact columns x 1600-1650), the top 24 rows blended, then the linen's weave (patch x 1560-1640, y 300-520)"),
                         brush="its hole filled row by row between the wall / skirting / floor pixels left and right (<= 60 px), + the wall texture at 0.6",
                         flecks_removed_px=n_speck) if B1.get("narrow_fills", True) else None),
        global_affine=affine,
        cleanup_2026_11_04=(dict(curtain_fill=B1.get("curtain_fill"), curtain_copy=(curtain_copy if B1.get("curtain_fill") == "copy_above" else None),
                                 holder=holder) if (B1.get("curtain_fill") == "copy_above" or holder) else None),
        untouched="everything else (WC block, ledge, glazing, roll stand, curtain, mat, vanity)", outputs=dict(fix=os.path.relpath(out_fix(fid), VF.REPO)))
    save_note(fid, note)
    print(json.dumps({k: v for k, v in note.items() if k != "method"}, indent=1))
    return note


# ---------------------------------------------------------------------------------------------------------------
# K-girl-0 r2: the two prints to their clay box (x0.646 by height, moved to the box centre) and the doll x0.70 about its seat
# (the K-girl master's fixed doll is 1.12x its box; the same doll at both ends of T-CGirl)
# ---------------------------------------------------------------------------------------------------------------
KG0 = dict(frames_px=[(838, 1115, 221, 615), (1149, 1449, 221, 615)], band_v=0.3593, desk_v=0.6283,
           prints_box=(0.334, 0.4816, 0.1463, 0.3118), doll_box=(0.2937, 0.3256, 0.4812, 0.5934),
           doll_rect=(0.250, 0.345, 0.405, 0.603), doll_scale=0.70, master_doll_ratio=1.123,
           # second run (2026-11-04, after the lock v3 overlay): the wall behind the prints and the doll by a quadratic surface per
           # paint field (white above the band step, pink below) instead of row interpolation + ratio maps, which left faint
           # vertical / horizontal lines at the old zones' edges; the prints' shadow drawn from the new frames (the raw's falloff:
           # L 81 -> 69 at the frame's right edge over ~35 px, ~5 % under its bottom). "rows" restores the first run.
           wall_fill="poly", corner_x_px=1630, white_patch_px=(1500, 230, 1620, 520), pink_patch_px=(1500, 640, 1620, 940),
           print_shadow=dict(dx=7, dy=2, sigma=11, depth=0.17))


def fix_kgirl0(preview=True):
    fid = "pose-k-girl-0-v7-r2"
    a = still(fid)
    H, W = a.shape[:2]
    # --- the prints: two frame rectangles (oak frames found by colour: hue 22-45, S >= 28, the bounding boxes)
    fr = np.zeros((H, W), np.float32)
    for x0, x1, y0, y1 in KG0["frames_px"]:
        fr[y0:y1 + 1, x0:x1 + 1] = 1
    X0, X1 = min(r[0] for r in KG0["frames_px"]), max(r[1] for r in KG0["frames_px"])
    Y0, Y1 = min(r[2] for r in KG0["frames_px"]), max(r[3] for r in KG0["frames_px"])
    bx = KG0["prints_box"]
    sc_p = round((bx[3] - bx[2]) * H / (Y1 - Y0), 3)                       # by height (30 x 40 portrait prints)
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    tx, ty = (bx[0] + bx[1]) / 2 * W, (bx[2] + bx[3]) / 2 * H
    # --- the doll (ears included): grabCut on a tall rect, its seat = the matte's bottom
    dl = F.grabcut(a, KG0["doll_rect"], iters=10, open_px=3)
    hue, Lp, Sp = hls(a)
    du0, du1, dv0, dv1 = KG0["doll_rect"]
    beige = ((hue >= 26) & (hue <= 55) & (Sp >= 7) & (Lp >= 45)).astype(np.float32) * F.rect_mask(H, W, du0, du1, dv0, 0.470)   # the ears only (above the head): cream (~34 deg), the wall is pink (~15 deg)
    dl = largest(cv2.morphologyEx(np.maximum(dl, beige).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    dl = cv2.morphologyEx(dl.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    dl = cv2.erode(dl, np.ones((3, 3), np.uint8)).astype(np.float32)                 # 1 px inside: no light rim from the wall
    dx0, dx1, dy0, dy1 = F.bbox(dl)
    seat_x = float(np.nonzero(dl[dy1 - 8:dy1 + 1] > 0.5)[1].mean())
    # --- zones (object + its soft shadow, the light from the window on the left): prints dilated 28 px, the doll as in the
    # K-girl fix (12 % of the width to the right on the wall rows, 3 % on the desk rows)
    zp = dil(fr, 28)
    core = dil(dl, 4)
    Yv = np.arange(H)[:, None] / H * np.ones((1, W), np.float32)
    desk_rows = (Yv >= KG0["desk_v"]).astype(np.float32)
    zx, zy = int(0.12 * W), int(0.012 * H)
    zone_wall = cv2.dilate((dl > 0.5).astype(np.uint8), np.ones((2 * zy + 1, zx + 8), np.uint8), anchor=(zx, zy)).astype(np.float32)
    zx2, zy2 = int(0.03 * W), int(0.006 * H)
    zone_desk = cv2.dilate((dl > 0.5).astype(np.uint8), np.ones((2 * zy2 + 1, zx2 + 8), np.uint8), anchor=(zx2, zy2)).astype(np.float32)
    zd = np.maximum(core, np.where(desk_rows > 0.5, zone_desk, zone_wall))
    holes = np.maximum(zp, zd)
    valid = 1 - holes
    # --- background: the wall rows by a horizontal normalised convolution (the band line and the wall's gradient continue
    # through the hole), the desk rows by the desk's grain 11 % of the width to the right (as in the K-girl fix)
    wall_h = holes * (1 - desk_rows)
    if KG0["wall_fill"] == "poly":
        # the band step's row (white above, pink below), per column outside the holes, fitted as a line
        Lr = Lp
        cols = [x for x in range(600, KG0["corner_x_px"] - 20, 8) if holes[:, x].max() < 0.5]
        yb_c = []
        for x in cols:
            prof = Lr[int(KG0["band_v"] * H) - 40:int(KG0["band_v"] * H) + 40, x:x + 4].mean(1)
            yb_c.append(int(KG0["band_v"] * H) - 40 + int(np.argmin(np.diff(prof))) + 1)
        kb, cb_ = np.polyfit(cols, yb_c, 1)
        Xc = np.arange(W)[None, :] * np.ones((H, 1), np.float32)
        Yr = np.arange(H)[:, None] * np.ones((1, W), np.float32)
        above = (Yr < kb * Xc + cb_).astype(np.float32)
        on_wall = (Xc < KG0["corner_x_px"]).astype(np.float32) * (1 - desk_rows)
        med = cv2.medianBlur(np.clip(Lr, 0, 100).astype(np.uint8), 21).astype(np.float32)
        clean = (np.abs(Lr - med) < 4).astype(np.float32)
        bg = a.copy()
        # white field: a quadratic surface (it is evenly lit); pink field: row by row between the nearest clean pixels left and
        # right (the doll's shadow and the darkening toward the desk top vary by row, which one surface does not follow)
        hm = wall_h * above
        bg = poly_fill(bg, hm, valid * above * on_wall * clean, pad=220, deg=2)
        bg = add_texture_m(a, bg, hm, KG0["white_patch_px"], 1.0)
        hm = wall_h * (1 - above)
        bg = F.fill_rows_valid(bg, hm, valid * (1 - above) * on_wall * clean, band_px=12, max_search=900)
        bg = add_texture_m(a, bg, hm, KG0["pink_patch_px"], 1.0)
        band_fit = dict(slope=round(float(kb), 5), row_at_x0=round(float(cb_), 1), columns=len(cols))
    else:
        bg = F.fill_rows_valid(a, wall_h, valid * (1 - desk_rows), band_px=12, max_search=900)   # row by row: the band line stays straight
        bg = add_texture_m(a, bg, wall_h, (int(0.60 * W), int(0.12 * H), int(0.66 * W), int(0.22 * H)), 0.6)
        band_fit = None
    bg = F.shift_copy(bg, holes * desk_rows, dx=int(0.11 * W))
    fb = cv2.GaussianBlur(holes, (0, 0), 4)[..., None]                               # the fill fades into the wall over ~8 px: no edge lines
    bg = a * (1 - fb) + bg * fb
    # --- shadows: the doll's as a ratio map transformed with it; the prints' drawn from the new frames (poly) or a ratio map (rows)
    ratio = np.clip(a / np.maximum(bg, 1.0), 0.45, 1.0)
    out = bg
    if KG0["wall_fill"] == "poly":
        ps = KG0["print_shadow"]
        _, p_al0 = F.transform_layer(a, fr, sc_p, (cx, cy), tx - cx + ps["dx"], ty - cy + ps["dy"])
        shm = cv2.GaussianBlur(p_al0, (0, 0), ps["sigma"])
        out = out * (1 - ps["depth"] * np.clip(shm / max(float(shm.max()), 1e-6), 0, 1))[..., None]
    else:
        rp = np.where(((zp > 0.5) & (fr < 0.5))[..., None], ratio, 1.0)
        rp_m, zp_m = F.transform_layer(cv2.GaussianBlur(rp, (0, 0), 2.0), F.feather(zp, 4), sc_p, (cx, cy), tx - cx, ty - cy)
        out = out * (1 + (np.clip(rp_m, 0.45, 1.0) - 1) * zp_m[..., None])
    if KG0["wall_fill"] == "poly":
        # under the doll's own outline (+4 px) the ratio is carried on from the ring just outside it (not 1), so the smaller doll
        # keeps its edge shadow: the first run's ratio 1 there left a light rim round it
        ring_d = ((dil(dl, 12) - dil(dl, 4)) > 0.5).astype(np.float32)
        ratio_d = nc_fill(ratio, core, ring_d, scales=((6, 6), (15, 15), (40, 40)), min_den=0.01)
        rd = np.where(((zd > 0.5) & (dil(fr, 10) < 0.5))[..., None], ratio_d, 1.0)
    else:
        rd = np.where(((zd > 0.5) & (core < 0.5) & (dil(fr, 10) < 0.5))[..., None], ratio, 1.0)   # not the old frames' edges
    rd_m, zd_m = F.transform_layer(cv2.GaussianBlur(rd, (0, 0), 2.0), F.feather(zd, 4), KG0["doll_scale"], (seat_x, float(dy1)))
    out = out * (1 + (np.clip(rd_m, 0.45, 1.0) - 1) * zd_m[..., None])
    # --- the objects
    p_rgb, p_al = F.transform_layer(a, F.feather(fr, 0.6), sc_p, (cx, cy), tx - cx, ty - cy)
    out = F.composite(out, p_rgb, p_al)
    d_rgb, d_al = F.transform_layer(a, F.feather(dl, 0.7), KG0["doll_scale"], (seat_x, float(dy1)))
    doll_edge_ratio = (round(float(np.median(ratio.mean(2)[(dil(dl, 12) - dil(dl, 4)) > 0.5])), 3) if KG0["wall_fill"] == "poly" else None)
    out = F.composite(out, d_rgb, d_al)
    F.save(out, out_fix(fid))
    pb, db = F.bbox(p_al), F.bbox(d_al)
    dbx = KG0["doll_box"]
    note = dict(
        fix="K-girl-0 r2 (QA §11.1): the two framed prints scaled to their clay box and moved to its centre; the bunny doll scaled about its seat on the desk, to the same size relative to its box as the K-girl master's fixed doll (T-CGirl pan endpoints)",
        method=("prints = the two oak-frame rectangles (hue 22-45, S >= 28: x 838-1115 and 1149-1449, y 221-615 px of 2736 x 1539), scaled by the clay box height "
                "over the pair's height about the pair's centre and moved to the box centre; the doll = grabCut on u 0.250-0.345, v 0.405-0.603 (10 iterations, "
                "ears added by their cream hue 26-55 above the head, against the pink wall (~15); eroded 1 px), scaled about the centre of its seat; zones for their soft shadows (prints dilated 28 px; the doll as in the K-girl fix: 12 % of "
                "the width to the right on the wall, 3 % on the desk); wall rows filled row by row between the nearest clean wall pixels left and right (the pink band "
                "line at v 0.3593 and the wall's gradient continue under the prints) with the wall's high-pass texture (tiled mirrored, no seams), desk rows from the desk grain 11 % of the "
                "width to the right; the fill fades into the original over ~8 px; the shadows carried as ratio maps (original / background, 0.45-1.0) with their objects"),
        prints=dict(before_px=[X0, X1, Y0, Y1], before_uv=[round(X0 / W, 4), round(X1 / W, 4), round(Y0 / H, 4), round(Y1 / H, 4)], scale=sc_p,
                    scale_note="QA §11.1 said x0.6; x%.3f is the clay box height over the pair's height (portrait 30 x 40 prints), so the pair ends at the box size" % sc_p,
                    after_uv=[round(pb[0] / W, 4), round(pb[1] / W, 4), round(pb[2] / H, 4), round(pb[3] / H, 4)], clay_box=list(bx),
                    ratio_to_box_before=dict(w=round((X1 - X0) / W / (bx[1] - bx[0]), 3), h=round((Y1 - Y0) / H / (bx[3] - bx[2]), 3)),
                    ratio_to_box_after=dict(w=round((pb[1] - pb[0]) / W / (bx[1] - bx[0]), 3), h=round((pb[3] - pb[2]) / H / (bx[3] - bx[2]), 3))),
        doll=dict(before_uv=[round(dx0 / W, 4), round(dx1 / W, 4), round(dy0 / H, 4), round(dy1 / H, 4)], seat_uv=[round(seat_x / W, 4), round(dy1 / H, 4)],
                  scale=KG0["doll_scale"], after_uv=[round(db[0] / W, 4), round(db[1] / W, 4), round(db[2] / H, 4), round(db[3] / H, 4)], clay_box=list(dbx),
                  height_ratio_to_box=dict(before=round((dy1 - dy0) / H / (dbx[3] - dbx[2]), 3), after=round((db[3] - db[2]) / H / (dbx[3] - dbx[2]), 3),
                                           k_girl_master_after_fix=KG0["master_doll_ratio"]),
                  scale_note="QA §11.1 said x0.5-0.6; x0.70 gives the doll the same size relative to its box as the K-girl master after its fix (1.12, ears included), so the doll is one size at both ends of T-CGirl; x0.6 would make it 0.96x its box, 15 % smaller than in K-girl"),
        wall_fill=(dict(mode="poly", run="second, 2026-11-04", band_step_fit=band_fit,
                        how=("the wall rows of the holes split at the band step (fitted as a line from the clean columns): the white field by a quadratic "
                             "surface fitted to its clean pixels (|L - median21| < 4) left of the room corner, with its own seam correction; the pink field "
                             "row by row between the nearest clean pixels (the doll's shadow and the darkening toward the desk vary by row); each with "
                             "its field's high-pass texture (patches clear of the old prints) at full strength; the prints' shadow "
                             "drawn from the new frames (offset +7 / +2 px, blur 11 px, 17 % at the edge: the raw falloff); the doll's shadow as a ratio map "
                             "moved with it, the ratio under its old outline (+4 px) continued from the ring just outside (median there: doll_edge_ratio)"),
                        doll_edge_ratio=doll_edge_ratio,
                        why="the first run (row interpolation + the prints' ratio map) left faint vertical / horizontal lines at the old zones' edges (x ~975, ~1310, ~1480, y ~645 px) and a light rim round the doll")
                   if KG0["wall_fill"] == "poly" else dict(mode="rows")),
        untouched="desk, bed foot, ledges and books, band, skirting, floor", outputs=dict(fix=os.path.relpath(out_fix(fid), VF.REPO)))
    save_note(fid, note)
    print(json.dumps({k: v for k, v in note.items() if k != "method"}, indent=1))
    return note


# ---------------------------------------------------------------------------------------------------------------
# W0-in r2: everything below the wall line down onto the clay lines by a smooth vertical warp (the measured offsets grow from
# +25 px at the slab's back edge to +46 at the drawer bottom, at 1080: the render's lower half is compressed); the plant (a
# filler in its seagrass basket) stays where it is, as in the W0 fix; the cup moves rigidly with the desk top under it
# ---------------------------------------------------------------------------------------------------------------
W0IN = dict(pairs_1080=[(640, 640), (669, 694), (732, 768), (761, 800), (794, 835), (877, 923)], dy_below=46,
            cup_rect=(0.312, 0.368, 0.480, 0.648), plant_rect=(0.0, 0.235, 0.05, 1.0),
            lines_clay_1080=dict(slab_back=694, slab_top_front=768, slab_front_face_bottom=800, chair_top=835, drawer_bottom=923),
            # 2026-11-04 second run (the manager's approval, after QA's fidelity note "the pen cup ~x1.4-2 its box"): the cup body is x1.37 the
            # clay box's width and x1.05 its height (measured on the matte: 1.402 / 1.047); one uniform scale puts both inside +-15 %:
            # k in [0.812, 0.820] -> 0.816 (the pencils, fillers, scale with it), and the cup is centred on the box (it sat ~15 px right of it,
            # its right edge then outside the +15 % margin). 1.0 restores the first run
            cup_scale=0.816, cup_box_clay=(0.3203, 0.3495, 0.5819, 0.6657),
            global_affine=True,   # 2026-11-04, the manager's approval (as B1 r3): the whole frame by the inverse of lock_v2's register; False = without
            # 2026-11-04 cleanup (QA §4: dark-green clumps in the basket's top rows, a dark rectangle on the skirting right of its base): the basket's
            # matte solid (its weave's light braids and dark gaps inside), and the plant's place below row 880 cleared in the background before the
            # warp, so no shifted copy of the stems / basket shows through or beside it. False = the r2 fix
            solid_basket=False)


def fix_w0in(preview=True):
    fid = "pose-w0-in-v7-r2"
    a = still(fid)
    H, W = a.shape[:2]
    k = H / 1080.0
    hue, L, S = hls(a)
    # --- the plant: green leaves (hue 60-170, S >= 20) and its seagrass basket (brown, bottom-left), kept unmoved on top
    pu0, pu1, pv0, pv1 = W0IN["plant_rect"]
    roi = F.rect_mask(H, W, pu0, pu1, pv0, pv1)
    leaf = ((hue >= 60) & (hue <= 170) & (S >= 20)).astype(np.float32) * roi
    pot = (((hue >= 15) & (hue <= 45) & (S >= 22) & (L < 72)).astype(np.float32) * F.rect_mask(H, W, 0.0, 0.16, 0.70, 1.0))
    plant = keep_big(np.maximum(leaf, pot), 40)
    plant = cv2.morphologyEx(plant.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(np.float32)
    basket_solid = None
    if W0IN.get("solid_basket"):
        wv = (((hue >= 10) & (hue <= 50) & (S >= 14) & (L < 88)) | (L < 30)).astype(np.float32) * F.rect_mask(H, W, 0.0, 0.20, 0.70, 1.0)
        wv = cv2.morphologyEx(wv.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8))
        wv = largest(cv2.morphologyEx(wv, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)))
        basket_solid = np.zeros((H, W), np.float32)
        for y in np.nonzero(wv.any(1))[0]:
            xs_ = np.nonzero(wv[y] > 0.5)[0]
            basket_solid[y, xs_.min():xs_.max() + 1] = 1          # convex per row: the weave's gaps are inside
        plant = np.maximum(plant, basket_solid)
    # --- the cup with its pencils: grabCut, removed before the warp and put back rigidly with the desk top under it
    cup = F.grabcut(a, W0IN["cup_rect"], iters=8, open_px=3)
    cu0, cu1, cv0, cv1 = W0IN["cup_rect"]
    crect = F.rect_mask(H, W, cu0, cu1, cv0, cv1)
    tips = ((L < 55) * crect * (np.arange(H)[:, None] < F.bbox(cup)[2] + 0.02 * H)).astype(np.float32)   # the thin graphite tips above the cup
    cup = np.maximum(cup, keep_big(tips, 6))
    cx0, cx1, cy0, cy1 = F.bbox(cup)
    hole = np.maximum(dil(cup, 5), crect)                                            # the whole rect: no ghost tips left behind
    valid = 1 - np.maximum(hole, plant)
    slab_back = int(669 * k)
    Yv = np.arange(H)[:, None] * np.ones((1, W), np.float32)
    wall_part = hole * (Yv < slab_back - 2)
    top_part = hole * (Yv >= slab_back - 2)
    bg = poly_fill(a, wall_part, valid * (Yv < slab_back - 2), pad=120, deg=2)
    bg = F.fill_rows_valid(bg, top_part, valid * (Yv >= slab_back - 2), band_px=12, max_search=300)     # the slab top's grain runs across
    bg = add_texture_m(a, bg, wall_part, (int(0.45 * W), int(0.40 * H), int(0.55 * W), int(0.50 * H)), 0.6)
    plant_bg = None
    if basket_solid is not None:
        # the plant's place below row 880 (the warp moves rows below 912 down by up to ~65 px: whatever is left there shows as a shifted copy)
        # cleared row by row from the wall / skirting / floor to its right, with the wall's texture
        plant_bg = dil(np.maximum(basket_solid, plant * (Yv >= 880)), 8)
        vpb = 1 - np.maximum(plant_bg, np.maximum(hole, dil(plant, 3)))
        bg = F.fill_rows_valid(bg, plant_bg, vpb, band_px=16, max_search=600)
        bg = add_texture_m(a, bg, plant_bg * (Yv < int(0.90 * H)), (int(0.45 * W), int(0.40 * H), int(0.55 * W), int(0.50 * H)), 0.6)
    # --- the warp: output row y' takes source row y with y + dy(y) = y' (dy piecewise linear between the measured pairs)
    src = np.array([p[0] for p in W0IN["pairs_1080"]] + [1080 + 200], float) * k
    dst = np.array([p[1] for p in W0IN["pairs_1080"]] + [1080 + 200 + W0IN["dy_below"]], float) * k
    yo = np.arange(H, dtype=np.float64)
    ys = np.interp(yo, dst, src, left=None, right=None)
    ys = np.where(yo < dst[0], yo, ys)
    mapy = np.repeat(ys[:, None], W, 1).astype(np.float32)
    mapx = np.repeat(np.arange(W, dtype=np.float32)[None, :], H, 0)
    warped = cv2.remap(bg, mapx, mapy, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    out = warped
    # --- the cup back, moved by the warp's offset at its base row
    base = float(cy1)
    dy_cup = float(np.interp(base, src, dst) - base)
    ks = W0IN["cup_scale"]
    bw_rows = cup.sum(1)
    body_rows = np.nonzero(bw_rows >= 0.6 * bw_rows.max())[0]                      # the cup body (the pencils are thin)
    body = cup * (np.arange(H)[:, None] >= body_rows.min())
    bx0_, bx1_, by0_, by1_ = F.bbox(body)
    cxb = float(np.nonzero(cup[int(base) - 6:int(base) + 1] > 0.5)[1].mean())
    cb_ = W0IN["cup_box_clay"]
    dx_cup = ((cb_[0] + cb_[1]) / 2 * W - cxb) if ks != 1.0 else 0.0           # centred on the clay box
    c_rgb, c_al = F.transform_layer(a, F.feather(cup, 0.6), ks, (cxb, base), dx_cup, dy_cup)
    if ks != 1.0:
        cxn = cxb + dx_cup
        out = contact_shadow(out, cxn - (bx1_ - bx0_) * ks / 2, cxn + (bx1_ - bx0_) * ks / 2, base + dy_cup - 1, depth=0.80, h_px=5, spread=1.15)
    out = F.composite(out, c_rgb, c_al)
    body_w, body_h = (bx1_ - bx0_) * ks, (by1_ - by0_) * ks
    nx0, nx1 = cxb + dx_cup - body_w / 2, cxb + dx_cup + body_w / 2
    cup_fit = dict(scale=ks, anchor_px=[round(cxb, 1), round(base + dy_cup, 1)], dx_px=round(dx_cup, 1), clay_box_uv=list(cb_),
                   body_after_uv=[round(nx0 / W, 4), round(nx1 / W, 4), round((base + dy_cup - body_h) / H, 4), round((base + dy_cup) / H, 4)],
                   inside_box_plus_15pct=bool(nx0 >= (cb_[0] - 0.15 * (cb_[1] - cb_[0])) * W and nx1 <= (cb_[1] + 0.15 * (cb_[1] - cb_[0])) * W),
                   body_over_box_before=dict(w=round((bx1_ - bx0_) / ((cb_[1] - cb_[0]) * W), 3), h=round((by1_ - by0_) / ((cb_[3] - cb_[2]) * H), 3)),
                   body_over_box_after=dict(w=round(body_w / ((cb_[1] - cb_[0]) * W), 3), h=round(body_h / ((cb_[3] - cb_[2]) * H), 3)),
                   body_cm_after_est=dict(note="from the clay proxy's 13 cm height (z 0.79-0.92) at the box's px per cm",
                                          h=round(body_h / ((cb_[3] - cb_[2]) * H) * 13.0, 1), d=round(body_w / ((cb_[3] - cb_[2]) * H) * 13.0, 1)),
                   envelope_cm=dict(d=[7, 10], h=[10, 14]))
    # --- the plant on top, unmoved
    out = F.composite(out, a, F.feather(plant, 0.6))
    affine = None
    if W0IN.get("global_affine"):
        out, affine = global_affine_to_clay(fid, out, A_fixed=W0IN.get("global_affine_A"))
        if W0IN.get("global_affine_A") is not None:
            affine["A_fixed_from"] = W0IN.get("global_affine_A_from")
    F.save(out, out_fix(fid))
    # --- the lines after, against the clay (QA's named-edge spans, at 1080)
    note = dict(
        fix="W0-in r2 (QA §11.1): the desk top, drawer, side panels, the chair and the floor objects down onto the clay lines; the plant unmoved; the pencil cup with the desk top",
        method=("measured at 1080 against the clay (horizontal edges in three column bands): slab back edge 669 -> 694, slab top-front edge 732 -> 768, front-face "
                "bottom 761 -> 800, chair back top 794 -> 835 (QA's 'chair back top 800 / -6' read the clay's desk line; the clay chair top is 835), drawer bottom "
                "877 -> 923; the floor objects and the skirting ~40 px high too; so a monotone vertical warp of everything below row 640: dy 0 at 640, the measured "
                "pairs, +46 below 877 (piecewise linear, cubic resampling); the plant (green hue 60-170, S >= 20, in u 0-0.235) and its seagrass basket (brown, "
                "bottom-left) composited back unmoved; the pencil cup (grabCut u 0.312-0.368, v 0.480-0.648, plus the thin dark pencil tips) removed first with its whole rect (wall: quadratic fit with seam "
                "correction; slab top: row by row) and put back rigidly by the warp's offset at its base"),
        pairs_1080=W0IN["pairs_1080"], dy_below_1080=W0IN["dy_below"], cup=dict(before_px=[cx0, cx1, cy0, cy1], dy_px=round(dy_cup, 1)),
        cup_to_box=(dict(cup_fit, run="second, 2026-11-04 (approved by the manager)", how="the cup layer (body + pencils) scaled uniformly about the centre of its base, centred on the clay box and moved with the warp; a soft contact shadow under the smaller base")
                    if W0IN["cup_scale"] != 1.0 else None),
        lines_clay_1080=W0IN["lines_clay_1080"], untouched="the shelf with its felt bins, the wall above row 640, the plant and its basket",
        global_affine=(dict(affine, why="G1.4 global scale (+0.41 / +0.70 % after the code fix, proposal 0.5 %): the manager's approval 2026-11-04 (as B1 r3); QA re-checks")
                       if affine else None),
        cleanup_2026_11_04=(dict(solid_basket_px=int(basket_solid.sum()), plant_place_cleared_px=int(plant_bg.sum()),
                                 how="the basket's matte convex per row (hue 10-50, S >= 14, L < 88 or L < 30, closed 21, opened 9, largest, in u 0-0.20 v 0.70-1); the plant's "
                                     "place below row 880 (dilated 8 px) cleared in the background before the warp, row by row from the right, + the wall texture")
                            if basket_solid is not None else None),
        outputs=dict(fix=os.path.relpath(out_fix(fid), VF.REPO)))
    save_note(fid, note)
    print(json.dumps({k_: v for k_, v in note.items() if k_ != "method"}, indent=1))
    return note


# ---------------------------------------------------------------------------------------------------------------
# B2 r3: the planter (seagrass basket + fern) x0.85 and the storage basket x0.80 about their floor / shelf contacts; the dark
# object in the mirror's top-left corner removed; the mirror (frame + reflection) compressed 0.933 about its bottom edge so its
# head lands on the clay line (QA named edges: top -35, bottom -8 at 1080). The vanity's right side (-43) is left for the paid
# pass: a code fix stretches the cabinet 7 % and moves the basin, soap, cup and vase (products) and closes on the hand towel.
# ---------------------------------------------------------------------------------------------------------------
B2 = dict(planter_rect=(0.000, 0.215, 0.360, 0.995), planter_scale=0.85, sbasket_rect=(0.555, 0.712, 0.760, 0.965), sbasket_scale=0.80,
          obj_rect_px=(1512, 1552, 222, 280), mirror_cols_px=(1505, 2185), mirror_bottom_px=712, mirror_top_px=60,
          mirror_dtop_1080=27, frame_rows_1080=1451.4, limestone_u=(0.0975, 0.160), floor_v=0.875,
          mirror_head=False, limestone_patch_px=(300, 300, 420, 500), floor_patch_px=(700, 1460, 900, 1530),   # 2026-11-04, after lock v3: the head is on the clay (see MIRROR_HEAD_CHECK); True restores the first run's remap
          # 2026-11-04 cleanup (QA 2026-11-04-retakes-fixes-g1 §4, fix_v9.py): fill_mode "columns" = the third run (column fill from above: a light
          # rectangle on the wall, lumps at the panel's base), "membrane" = each surface (wall, limestone panel, also in the low band) by a membrane
          # through its own intact boundary (no step) + its texture, the floor ring Telea as before, a contact shadow along the basket's bottom;
          # global_affine as B1 r3 (the inverse of lock_v2's register; the scale +0.64 / +0.74 %)
          fill_mode="columns", global_affine=False)
# the mirror head measured column by column (the first frame edge from the top, 6-px-wide columns, 1920x1080 of the frame): clay / raw r3 / first fix run (remap k 0.9343)
MIRROR_HEAD_CHECK = {"x_px": [1090, 1150, 1350, 1450, 1540], "clay": [125, 114, 79, 60, 44], "raw_r3": [123, 112, 76, 58, 42], "first_fix_run": [147, 137, 104, 86, 72],
                     "note": ("QA's -35 (and the -34 of the named edge 'mirror top') averages the sloped head over u 0.60-0.76, and the clay's strongest row there "
                              "(124) is the reflected ceiling line inside the glass, not the frame; per column the raw head is -2 px from the clay, and the first "
                              "fix run's remap had moved it +22 to +28 px. So the head is not changed.")}


def fix_b2(preview=True):
    fid = "b2-v7-r3"
    a = still(fid)
    H, W = a.shape[:2]
    hue, L, S = hls(a)
    U = np.arange(W)[None, :] / W * np.ones((H, 1), np.float32)
    Yv = np.arange(H)[:, None] / H * np.ones((1, W), np.float32)
    # --- 1. the object in the mirror corner: its dark pixels, inpainted from the mirror's reflected wall around it
    # the reflected curtain strip and its black hook at the mirror's left inner edge (x 1530-1548, v 0.14-0.47): every pixel
    # right of the oak frame that is not reflected wall (S >= 11 or L < 62), filled row by row from the reflected wall to its right
    # (x from 1526: the oak bar's inner shadow ends at 1524; rows from 226: below the head bar, which the first run's 0.135 H (207) had cut into)
    sx_0, sx_1, sv_0, sv_1 = 1526, 1556, 226, int(0.470 * H)
    strip = np.zeros((H, W), np.float32)
    strip[sv_0:sv_1, sx_0:sx_1] = ((S[sv_0:sv_1, sx_0:sx_1] >= 11) | (L[sv_0:sv_1, sx_0:sx_1] < 62))
    strip = dil(strip, 1) * F.rect_mask(H, W, sx_0 / W, sx_1 / W, sv_0 / H, sv_1 / H)
    refl = ((S < 11) & (L >= 62)).astype(np.float32) * F.rect_mask(H, W, 1548 / W, 1700 / W, sv_0 / H, sv_1 / H)
    out = F.fill_rows_valid(a, strip, refl, band_px=8, max_search=80)
    obj = strip
    # --- 2. the mirror head: compress rows above the bottom edge (frame + reflection) by k about the bottom row, per column of the mirror
    #     (off since the lock v3 check: MIRROR_HEAD_CHECK)
    c0, c1 = B2["mirror_cols_px"]
    yb, yt = B2["mirror_bottom_px"], B2["mirror_top_px"]
    d_rows = B2["mirror_dtop_1080"] * B2["frame_rows_1080"] / 1080.0
    kz = (yb - (yt + 100) - d_rows) / (yb - (yt + 100))                      # the measured top (~160 at the centre) -> down by d_rows
    reg = out[:, c0:c1].copy()
    ys_out = np.arange(H, dtype=np.float32)
    src = np.where(ys_out <= yb, yb - (yb - ys_out) / kz, ys_out)           # output row y' takes source row yb - (yb - y') / k
    mapy = np.repeat(src[:, None], c1 - c0, 1).astype(np.float32)
    mapx = np.repeat(np.arange(c1 - c0, dtype=np.float32)[None, :], H, 0)
    if B2["mirror_head"]:
        comp = cv2.remap(reg, mapx, mapy, interpolation=cv2.INTER_AREA if kz < 1 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        # rows whose source is above the image top (or above the old mirror top band) are wall: fill them by a quadratic fit
        vacated = np.zeros((H, W), np.float32)
        vacated[:, c0:c1] = (mapy < 0).astype(np.float32)
        out[:, c0:c1] = comp
        top_band = np.zeros((H, W), np.float32)
        top_band[:max(1, int(d_rows) + 4), c0:c1] = 1
        wall_v = ((L > 70) & (S < 30)).astype(np.float32) * (1 - top_band)
        out = poly_fill(out, np.maximum(vacated, top_band), wall_v * (Yv < 0.12), pad=140, deg=2)
    # --- 3. the planter x0.85 about the basket's floor contact, with its shadow; 4. the storage basket x0.80 about its shelf contact
    pu0, pu1, pv0, pv1 = B2["planter_rect"]
    roi = F.rect_mask(H, W, pu0, pu1, pv0, pv1)
    fern = (((hue >= 48) & (hue <= 150) & (S >= 3) & (L <= 92)) | (L < 30)).astype(np.float32)   # pale frond tips too (the stone and the linen are hue 30-40)
    # the basket only: the rope is hue 22-26, S 27-45; the limestone in shadow (S 16-25) and the curtain hem (S 12-24) are not (the
    # first run's S > 18 took both, and moved pieces of them with the planter); its largest component, closed and filled
    brown = ((hue >= 15) & (hue <= 30) & (S >= 26) & (L > 12) & (L < 66)).astype(np.float32) * roi
    brown = cv2.morphologyEx(brown.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(np.float32)
    brown = largest(brown)
    cb, _ = cv2.findContours(brown.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    brown = np.zeros((H, W), np.uint8)
    cv2.drawContours(brown, cb, -1, 1, -1)
    brown = brown.astype(np.float32)
    # the plant: the green fronds connected to the planter (components that touch the planter's core, dilated 30 px; the first runs
    # also took green-tinted specks on the curtain hem and the floor), and the dark gaps inside its closed outline
    green = ((hue >= 48) & (hue <= 150) & (S >= 3) & (L <= 92)).astype(np.float32) * roi
    core = largest(cv2.morphologyEx(np.clip(green + brown, 0, 1).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)))
    n_c, lab, st, _ = cv2.connectedComponentsWithStats((green > 0.5).astype(np.uint8))
    hit = np.unique(lab[(dil(core, 30) > 0.5) & (green > 0.5)])
    hit = hit[(hit > 0) & (st[hit, cv2.CC_STAT_AREA] >= 15)]
    green_k = np.isin(lab, hit).astype(np.float32)
    b_rows = np.nonzero(brown.sum(1) > 0)[0]
    green_k *= np.maximum((Yv < (b_rows.min() + 30) / H).astype(np.float32), dil(brown, 20))   # below the rim only fronds hanging on the basket
    hull = cv2.morphologyEx(np.clip(green_k + brown, 0, 1).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    ch, _ = cv2.findContours(hull, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = np.zeros((H, W), np.uint8)
    cv2.drawContours(hull, ch, -1, 1, -1)
    pl = np.clip(green_k + brown + ((L < 30) & (hull > 0)).astype(np.float32) * fern, 0, 1)
    pl = cv2.morphologyEx(pl.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32)
    bw = (brown * pl).sum(1)
    rows_b = np.nonzero(bw >= 0.6 * bw.max())[0]
    pb_top, pb_bot = int(rows_b.min()), int(rows_b.max())
    bot_cols = np.nonzero((brown * pl)[pb_bot - 6:pb_bot + 1] > 0.5)[1]
    pax = float(bot_cols.mean())
    hole_p = dil(pl, 5)                               # the planter and a 5-px fringe (anti-aliased leaf edges); its soft shadow stays
    hole_s = np.zeros((H, W), np.float32)            # the storage basket stays: not separable in code (see the note), left for the paid pass
    valid = 1 - hole_p
    # the background behind the planter by surface, each from its own intact pixels around (normalised convolution, so the
    # planter's soft shadow on the wall and the panel continues into the hole) + its own texture: the white wall (u < 0.0975),
    # the limestone panel (u 0.0975-0.160), the floor (v >= 0.875); on the curtain only the leaf pixels, from just above
    lu0, lu1 = B2["limestone_u"]
    fv = B2["floor_v"]
    wall_r = ((U < lu0) & (Yv < fv)).astype(np.float32)
    lime_r = ((U >= lu0) & (U < lu1) & (Yv < fv)).astype(np.float32)
    curt_r = ((U >= lu1) & (Yv < fv)).astype(np.float32)
    floor_r = (Yv >= fv).astype(np.float32)
    # on the wall and the limestone panel the whole closed outline of the plant (dilated 10 px: its pale, half-transparent frond
    # tips are outside any colour matte and read as ghost fronds once the plant is smaller) is filled column by column from the
    # intact surface above it (both are lit from the left, so their light runs vertically), smoothed across columns, + texture
    hullD = dil(hull, 10)
    membrane = B2.get("fill_mode") == "membrane"
    if membrane:
        import fix_m0_12 as FM
        # the bright glazed strip at the frame's left edge (x < 40, L 94-97) is its own surface: continued down from above, and kept out
        # of the wall's membrane (whose boundary it would otherwise lighten into a pale block)
        strip_r = ((U < 40.0 / W) & (Yv < fv)).astype(np.float32)
        wall_r = wall_r * (1 - strip_r)
        hm_s = np.maximum(hullD, hole_p) * strip_r
        if hm_s.any():
            out = F.fill_from_above(out, hm_s, (1 - np.maximum(hullD, hole_p)) * strip_r, band_px=10)
    for reg, patch, strength in ((wall_r, (int(0.030 * W), int(0.12 * H), int(0.070 * W), int(0.22 * H)), 0.6), (lime_r, B2["limestone_patch_px"], 0.9)):
        hm = np.maximum(hullD, hole_p) * reg
        vv = (1 - np.maximum(hullD, hole_p)) * reg
        if membrane:
            # the whole surface region down to the floor (the low band included), exact at its own intact boundary
            out = FM.laplace_fill(out, hm, reg, pad=80)
            out = add_texture_m(a, out, hm, patch, strength, blur=3)
            continue
        colf = F.fill_rows_valid(np.ascontiguousarray(out.transpose(1, 0, 2)), np.ascontiguousarray(hm.T), np.ascontiguousarray(vv.T),
                                 band_px=24, max_search=1400).transpose(1, 0, 2)
        colf = cv2.GaussianBlur(colf, (0, 0), sigmaX=8, sigmaY=2)
        out = np.where((hm > 0.5)[..., None], colf, out)
        out = add_texture_m(a, out, hm, patch, strength)
    hp_w, hp_l = np.maximum(hullD, hole_p) * wall_r, np.maximum(hullD, hole_p) * lime_r
    hp_c = hole_p * curt_r
    out = np.where((hp_c > 0.5)[..., None], copy_down_fill(out, hp_c, 40), out)
    # the low band (v >= 0.80: the floor, the wall / panel bases and the curtain hem around the basket): only a thin ring is
    # revealed there (the basket keeps its floor row), so it is inpainted from its own boundary (Telea, radius 9), which keeps the
    # grout lines and the hem's colours next to the ring; the second run's normalised convolution left pale blocks there
    low = np.maximum(hole_p, hullD * (wall_r + lime_r).clip(0, 1)) * (Yv >= 0.80).astype(np.float32)
    if membrane:
        low = low * floor_r                     # the wall and the panel's base are in the membrane above; only the floor ring is inpainted
    tel = cv2.inpaint(np.clip(a, 0, 255).astype(np.uint8), (dil(low, 2) > 0.5).astype(np.uint8), 9, cv2.INPAINT_TELEA).astype(np.float32)
    out = np.where((low > 0.5)[..., None], tel, out)
    hp_f = low
    # the basket's outer 3 px (closed and filled: pale floor between the rope ends) are left out of the composite
    pl_comp = np.clip(pl - (brown - cv2.erode(brown, np.ones((7, 7), np.uint8))), 0, 1)
    p_rgb, p_al = F.transform_layer(a, F.feather(pl_comp, 0.8), B2["planter_scale"], (pax, float(pb_bot)))
    # the basket's floor shadow follows its new (smaller) bottom outline: a band 18 px around the lower 40 % of the scaled basket,
    # blurred, 30 % deep at the outline (the old shadow went with the inpainted ring)
    _, b_al = F.transform_layer(a, F.feather(brown, 0.8), B2["planter_scale"], (pax, float(pb_bot)))
    b_m = (b_al > 0.5).astype(np.uint8)
    ring = np.clip(dil(b_m, 18) - b_m, 0, 1) * (Yv > (pb_top + 0.6 * (pb_bot - pb_top)) / H).astype(np.float32)
    ring = cv2.GaussianBlur(ring, (0, 0), 6)
    out = out * (1 - 0.30 * np.clip(ring / max(ring.max(), 1e-6), 0, 1))[..., None]
    if membrane:
        # the basket's floor contact: a soft dark line along its new bottom (the pale band QA saw), under the composite
        bys, bxs = np.nonzero(b_m)
        out = contact_shadow(out, float(bxs.min()), float(bxs.max()), float(bys.max()) - 1, depth=0.72, h_px=7, spread=1.02)
    out = F.composite(out, p_rgb, p_al)
    g_aff = None
    if B2.get("global_affine"):
        out, g_aff = global_affine_to_clay(fid, out)
    F.save(out, out_fix(fid))
    pa = F.bbox(p_al)
    note = dict(
        fix=("B2 r3 (QA §11.1): the planter x0.85 about its floor contact; the dark object reflected in the mirror's top-left corner removed" +
             ("; the mirror's head lowered onto the clay line (frame + reflection compressed about the bottom edge)" if B2["mirror_head"] else
              "; the mirror's head NOT lowered: measured per column it is already on the clay (-2 px), see mirror_head_check")),
        method=("object: the shower curtain and its black hook reflected at the mirror's left inner edge (every non-wall pixel right of the oak frame in x 1526-1556, rows 226 to v 0.470), filled row by row from the reflected wall to its right; " +
                ("mirror: columns x 1505-2185, rows above the bottom edge (y 712) remapped y' = 712 - k (712 - y) with k from QA's named edges (top -35, bottom -8 at 1080: 27 px "
                 "= 36 rows of the still), the strip above the new head filled by a quadratic fit of the wall; " if B2["mirror_head"] else "mirror: unchanged; ") +
                "planter (third run, 2026-11-04): the rope basket (hue 15-30, S >= 26, its largest component, filled) + the green fronds connected to it + the dark gaps inside its outline, in u 0-0.215, "
                "v 0.36-0.995, scaled x0.85 about the centre of the basket's floor contact; behind it (dilated 5 px) each surface from its own intact pixels around "
                "(normalised convolution, so its soft shadow continues) with its own texture: the white wall, the limestone panel, the floor; on the curtain only the leaf "
                "pixels, from just above; the low band (v >= 0.80) inpainted from its boundary (Telea); the basket's floor shadow along its new bottom outline. Earlier runs (superseded): "
                "planter: sage leaves + brown basket in u 0-0.215, "
                "v 0.36-0.995, every component >= 15 px, scaled about the centre of the basket's floor contact; its hole (closed 41 px, filled, dilated 24 px: "
                "its soft shadow) filled by surface: the white wall by a quadratic fit of its own pale pixels, on the limestone panel and the curtain only "
                "the leaf pixels (from just above, their stains / folds continue), floor rows row by row; its shadow carried as a ratio map"),
        mirror=(dict(k=round(kz, 4), rows_moved_at_top=round(d_rows, 1), bottom_row=yb, columns=[c0, c1], qa_named_edges_1080=dict(top=-35, bottom=-8))
                if B2["mirror_head"] else dict(changed=False, first_run_2026_11_04="k 0.9343 remap, withdrawn: it moved the head +22..+28 px off the clay")),
        mirror_head_check=MIRROR_HEAD_CHECK,
        object_removed=dict(px=int(obj.sum()), what="the shower curtain and its black hook reflected at the mirror's left inner edge", rect_px=[sx_0, sx_1, sv_0, sv_1]),
        planter=dict(scale=B2["planter_scale"], basket_rows_before=[pb_top, pb_bot], anchor_uv=[round(pax / W, 4), round(pb_bot / H, 4)],
                     after_uv=[round(pa[0] / W, 4), round(pa[1] / W, 4), round(pa[2] / H, 4), round(pa[3] / H, 4)],
                     basket_height_over_clay_pot_before=1.18, basket_height_over_clay_pot_after=round(1.18 * B2["planter_scale"], 3)),
        storage_basket=dict(scale_asked=B2["sbasket_scale"], done=False,
                            why=("not separable in code: the rope basket and its towels fill the vanity's opening almost from side panel to side panel, and "
                                 "their cream / grey colours match the shelf's back wall (L 58-72, S 13-22 %), so neither grabCut nor a colour matte isolates the basket "
                                 "without leaving its old outline (tried, 2026-11-04); left for the paid pass, with x0.80 written into its prompt")),
        vanity_right=dict(changed=False, why=("lock v3 (cross-correlation, rows 0.60-0.90): the outer right edge is +4 px (clay 1584-1591, raw 1595); the -43 of QA's "
                                               "strongest peak and of lock v2 is the render's drawer-front / side boundary (1541), whose clay twin is the clay's own "
                                               "front / side boundary at 1539 (+2): parallel edges, not a narrow cabinet. Seen in the clay / raw crop the same way.")),
        residual_seams=("at 100 %: the basket's floor contact (a thin pale sliver under the bottom rope and an even shadow band around it, also against the "
                        "wall on its left), and the limestone panel's base right of the fronds (a paler block at v 0.77-0.87, x 400-440 px of the still); "
                        "at the page size both read as soft. The mirror corner and the wall / panel behind the fronds are clean."),
        left_for_the_paid_pass=("the storage basket x0.80 (above) and the planter's floor contact / panel base (residual_seams). The vanity's right side "
                                "is not a fix item any more (vanity_right), nor the mirror head (mirror_head_check). The v8 route: this -fix.png as the composite + one image-to-image pass (600)"),
        outputs=dict(fix=os.path.relpath(out_fix(fid), VF.REPO)),
        cleanup_2026_11_04=(dict(fill_mode=B2.get("fill_mode"), global_affine=(dict(g_aff, why="QA 2026-11-04 (G1.4 +0.64 / +0.74 %): the same global affine as B1 r3") if g_aff else None),
                                 contact_shadow="depth 0.72, 7 px, along the scaled basket's bottom" if membrane else None,
                                 storage_basket="unchanged (QA: within +-15 %)") if (membrane or g_aff) else None))
    save_note(fid, note)
    print(json.dumps({k_: v for k_, v in note.items() if k_ != "method"}, indent=1))
    return note


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = dict(b1=fix_b1, kgirl0=fix_kgirl0, w0in=fix_w0in, b2=fix_b2)
    for k, fn in fns.items():
        if which in (k, "all"):
            fn()
