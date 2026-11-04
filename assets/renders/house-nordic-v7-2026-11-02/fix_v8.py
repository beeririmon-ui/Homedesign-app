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


def save_note(fid, note):
    p = os.path.join(VF.out_dir(fid), fid + "-fix.json")
    json.dump(dict(asset_id=fid, date=DATE, script=SCRIPT, tokens=0, **note), open(p, "w"), indent=1, ensure_ascii=False)
    return p


def still(fid):
    return F.load(os.path.join(VF.out_dir(fid), fid + ".png"))


def out_fix(fid):
    return os.path.join(VF.out_dir(fid), fid + "-fix.png")


# ---------------------------------------------------------------------------------------------------------------
# B1 r3: the invented plinth out, the planter (seagrass basket + fern) down 172 px to the floor; the brush x0.73 about its base
# ---------------------------------------------------------------------------------------------------------------
B1 = dict(planter_rect=(0.440, 0.598, 0.395, 0.768), plinth=(0.484, 0.562, 0.765, 0.884), dy=172,
          brush_rect=(0.448, 0.482, 0.680, 0.900), brush_scale=0.73,
          clay_pot=(0.49, 0.555, 0.75, 0.877), clay_brush=(0.4583, 0.475, 0.7432, 0.893))


def edge_col(g, v0, v1, u0, u1):
    """The column of the strongest vertical edge (mean |d/dx| over rows v0..v1) between u0 and u1."""
    H, W = g.shape
    prof = np.abs(np.diff(g[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)], axis=1)).mean(0)
    prof = cv2.GaussianBlur(prof.reshape(1, -1), (1, 0), 0).ravel() if False else prof
    return int(u0 * W) + int(np.argmax(prof))


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
    # the curtain part: only the pixels the leaves (and the plinth) actually covered, filled locally from just above
    hc = np.maximum(dil(pl, 4), F.rect_mask(H, W, pu0, pu1, pv0, pv1)) * curtain
    # the curtain: its own weave copied down with a period of 330 rows (the folds are vertical), then a low-frequency seam
    # correction read on a ring around the region (the copied estimate at the ring vs the curtain there)
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
    out = contact_shadow(out, ax - (bx1 - bx0) * s_ / 2, ax + (bx1 - bx0) * s_ / 2, by1 - 1, depth=0.75, h_px=6, spread=1.3)
    out = F.composite(out, b_rgb, b_al)
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
           doll_rect=(0.250, 0.345, 0.405, 0.603), doll_scale=0.70, master_doll_ratio=1.123)


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
    bg = F.fill_rows_valid(a, wall_h, valid * (1 - desk_rows), band_px=12, max_search=900)   # row by row: the band line stays straight
    bg = add_texture_m(a, bg, wall_h, (int(0.60 * W), int(0.12 * H), int(0.66 * W), int(0.22 * H)), 0.6)
    bg = F.shift_copy(bg, holes * desk_rows, dx=int(0.11 * W))
    fb = cv2.GaussianBlur(holes, (0, 0), 4)[..., None]                               # the fill fades into the wall over ~8 px: no edge lines
    bg = a * (1 - fb) + bg * fb
    # --- shadows as ratio maps, transformed with their objects
    ratio = np.clip(a / np.maximum(bg, 1.0), 0.45, 1.0)
    out = bg
    rp = np.where(((zp > 0.5) & (fr < 0.5))[..., None], ratio, 1.0)
    rp_m, zp_m = F.transform_layer(cv2.GaussianBlur(rp, (0, 0), 2.0), F.feather(zp, 4), sc_p, (cx, cy), tx - cx, ty - cy)
    out = out * (1 + (np.clip(rp_m, 0.45, 1.0) - 1) * zp_m[..., None])
    rd = np.where(((zd > 0.5) & (core < 0.5) & (dil(fr, 10) < 0.5))[..., None], ratio, 1.0)   # not the old frames' edges
    rd_m, zd_m = F.transform_layer(cv2.GaussianBlur(rd, (0, 0), 2.0), F.feather(zd, 4), KG0["doll_scale"], (seat_x, float(dy1)))
    out = out * (1 + (np.clip(rd_m, 0.45, 1.0) - 1) * zd_m[..., None])
    # --- the objects
    p_rgb, p_al = F.transform_layer(a, F.feather(fr, 0.6), sc_p, (cx, cy), tx - cx, ty - cy)
    out = F.composite(out, p_rgb, p_al)
    d_rgb, d_al = F.transform_layer(a, F.feather(dl, 0.7), KG0["doll_scale"], (seat_x, float(dy1)))
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
            lines_clay_1080=dict(slab_back=694, slab_top_front=768, slab_front_face_bottom=800, chair_top=835, drawer_bottom=923))


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
    c_rgb, c_al = F.transform_layer(a, F.feather(cup, 0.6), 1.0, (0, 0), 0, dy_cup)
    out = F.composite(out, c_rgb, c_al)
    # --- the plant on top, unmoved
    out = F.composite(out, a, F.feather(plant, 0.6))
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
        lines_clay_1080=W0IN["lines_clay_1080"], untouched="the shelf with its felt bins, the wall above row 640, the plant and its basket",
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
          mirror_head=False, limestone_patch_px=(300, 300, 420, 500), floor_patch_px=(700, 1460, 900, 1530))   # 2026-11-04, after lock v3: the head is on the clay (see MIRROR_HEAD_CHECK); True restores the first run's remap
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
    for reg, patch, strength in ((wall_r, (int(0.030 * W), int(0.12 * H), int(0.070 * W), int(0.22 * H)), 0.6), (lime_r, B2["limestone_patch_px"], 0.9)):
        hm = np.maximum(hullD, hole_p) * reg
        vv = (1 - np.maximum(hullD, hole_p)) * reg
        colf = F.fill_rows_valid(np.ascontiguousarray(out.transpose(1, 0, 2)), np.ascontiguousarray(hm.T), np.ascontiguousarray(vv.T),
                                 band_px=24, max_search=1400).transpose(1, 0, 2)
        colf = cv2.GaussianBlur(colf, (0, 0), sigmaX=8, sigmaY=2)
        out = np.where((hm > 0.5)[..., None], colf, out)
        out = add_texture_m(a, out, hm, patch, strength)
    hp_w, hp_l = np.maximum(hullD, hole_p) * wall_r, np.maximum(hullD, hole_p) * lime_r
    hp_c = hole_p * curt_r
    out = np.where((hp_c > 0.5)[..., None], copy_down_fill(out, hp_c, 40), out)
    hp_f = hole_p * floor_r
    fl_valid = valid * floor_r * (U < pu1 + 0.03).astype(np.float32) * (S < 14).astype(np.float32) * (L > 44).astype(np.float32)
    out = nc_fill(out, hp_f, fl_valid, scales=((40, 3), (120, 20), (300, 60), (600, 200)))
    out = add_texture_m(a, out, hp_f, B2["floor_patch_px"], 0.6)
    p_rgb, p_al = F.transform_layer(a, F.feather(pl, 0.8), B2["planter_scale"], (pax, float(pb_bot)))
    hw = (bot_cols.max() - bot_cols.min()) / 2 * B2["planter_scale"]
    out = contact_shadow(out, pax - hw, pax + hw, pb_bot - 4, depth=0.70, h_px=12, spread=1.08)
    out = F.composite(out, p_rgb, p_al)
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
                "pixels, from just above; a contact shadow under the basket. Earlier runs (superseded): "
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
        left_for_the_paid_pass=("the storage basket x0.80 (above), and the planter's seam at the curtain hem / floor if QA reads it as visible. The vanity's right side "
                                "is not a fix item any more (vanity_right). The v8 route: this -fix.png as the composite + one image-to-image pass (600)"),
        outputs=dict(fix=os.path.relpath(out_fix(fid), VF.REPO)))
    save_note(fid, note)
    print(json.dumps({k_: v for k_, v in note.items() if k_ != "method"}, indent=1))
    return note


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = dict(b1=fix_b1, kgirl0=fix_kgirl0, w0in=fix_w0in, b2=fix_b2)
    for k, fn in fns.items():
        if which in (k, "all"):
            fn()
