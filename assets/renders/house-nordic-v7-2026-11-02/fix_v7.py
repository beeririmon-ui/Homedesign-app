#!/usr/bin/env python3
"""
fix_v7.py: the designer's zero-token fixes on the v7 stills (docs/render-v7-review-2026-11-02.md section 7), as new files
next to the originals. render-agent, 2026-11-03. 0 var2 tokens. Nothing of v7 is overwritten.

Each fix reads the normalised still <out_dir>/<id>.png (2736x1539, the input of process_v7 / process_v8), writes
<out_dir>/<id>-fix.png (same size, ungraded) and <out_dir>/<id>-fix.json (what changed, how, the numbers), and leaves the
grade to process_v8.py (--render <id>-fix.png --suffix -fix -> -graded-fix / -frame-fix / -graded-os6-fix /
-measurements-fix / -lock-fix). Coordinates are fractions of the canvas (u right, v down), as in the clay selfcheck.

  python3 fix_v7.py kboy0 | doll | window | w0 | m0 [--preview]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402

DATE = "2026-11-03"


# ---------------------------------------------------------------------------------------------------------------
# small library
# ---------------------------------------------------------------------------------------------------------------
def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def save(arr, path):
    Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8)).save(path)


def gray(a):
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def px(st, u, v):
    """(u, v) fractions -> (x, y) pixels of the still."""
    return int(round(u * st.shape[1])), int(round(v * st.shape[0]))


def feather(mask, r):
    """0..1 mask softened by a Gaussian of radius r px."""
    if r <= 0:
        return mask.astype(np.float32)
    k = int(2 * r) * 2 + 1
    return cv2.GaussianBlur(mask.astype(np.float32), (k, k), r)


def grabcut(a, rect_uv, iters=6, pad_uv=0.012, open_px=5):
    """A matte (0/1 float, full size) of the main object inside rect_uv (u0, u1, v0, v1) by grabCut."""
    H, W = a.shape[:2]
    u0, u1, v0, v1 = rect_uv
    X0, Y0 = max(0, int((u0 - pad_uv) * W)), max(0, int((v0 - pad_uv) * H))
    X1, Y1 = min(W, int((u1 + pad_uv) * W)), min(H, int((v1 + pad_uv) * H))
    sub = np.ascontiguousarray(np.clip(a[Y0:Y1, X0:X1, ::-1], 0, 255).astype(np.uint8))
    mask = np.zeros(sub.shape[:2], np.uint8)
    rect = (int(u0 * W) - X0, int(v0 * H) - Y0, int(u1 * W) - int(u0 * W), int(v1 * H) - int(v0 * H))
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(sub, mask, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    if open_px:
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((open_px, open_px), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = np.where(lab == k, 255, 0).astype(np.uint8)
    full = np.zeros((H, W), np.float32)
    full[Y0:Y1, X0:X1] = m / 255.0
    return full


def bbox(mask):
    ys, xs = np.nonzero(mask > 0.5)
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())


def fill_rows(a, hole, band_px=24):
    """Fill `hole` (0/1) row by row with a linear blend of the nearest non-hole pixels left and right of each hole run.
    For smooth surfaces (walls). Returns a copy."""
    out = a.copy()
    H, W = hole.shape
    for y in range(H):
        row = hole[y] > 0.5
        if not row.any():
            continue
        xs = np.nonzero(row)[0]
        # runs
        splits = np.nonzero(np.diff(xs) > 1)[0]
        starts = np.r_[xs[0], xs[splits + 1]]
        ends = np.r_[xs[splits], xs[-1]]
        for s, e in zip(starts, ends):
            l0, l1 = max(0, s - band_px), s
            r0, r1 = e + 1, min(W, e + 1 + band_px)
            L = out[y, l0:l1].mean(0) if l1 > l0 else None
            R = out[y, r0:r1].mean(0) if r1 > r0 else None
            if L is None and R is None:
                continue
            if L is None:
                L = R
            if R is None:
                R = L
            t = (np.arange(s, e + 1) - s + 0.5) / (e - s + 1)
            out[y, s:e + 1] = L[None, :] * (1 - t)[:, None] + R[None, :] * t[:, None]
    return out


def fill_cols(a, hole, band_px=24):
    """Same as fill_rows, column by column (for vertical gradients)."""
    return fill_rows(a.transpose(1, 0, 2), hole.T, band_px).transpose(1, 0, 2)


def add_texture(a, filled, hole, src_box_px, strength=1.0):
    """Put the fine texture of a source patch (its high-pass) onto the filled hole so it is not plastic-smooth."""
    x0, y0, x1, y1 = src_box_px
    patch = a[y0:y1, x0:x1]
    hp = patch - cv2.GaussianBlur(patch, (0, 0), 6)
    H, W = hole.shape
    reps = (H // hp.shape[0] + 2, W // hp.shape[1] + 2, 1)
    tile = np.tile(hp, reps)[:H, :W]
    m = (hole > 0.5)[..., None]
    return np.where(m, filled + strength * tile, filled)


def inpaint(a, hole, radius=5, method=cv2.INPAINT_TELEA):
    m = (hole > 0.5).astype(np.uint8) * 255
    src = np.clip(a, 0, 255).astype(np.uint8)
    return cv2.inpaint(src, m, radius, method).astype(np.float32)


def shift_copy(a, hole, dx=0, dy=0):
    """Fill the hole with the image content shifted by (dx, dy): for textures that continue (floor planks, rug)."""
    H, W = hole.shape
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    moved = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    m = (hole > 0.5)[..., None]
    return np.where(m, moved, a)


def transform_layer(a, alpha, scale, anchor_xy, dx=0, dy=0, out_size=None):
    """Scale the layer (rgb a, alpha) by `scale` about anchor_xy (pixels), then move by (dx, dy). Returns rgb, alpha."""
    H, W = alpha.shape
    ax, ay = anchor_xy
    M = np.float32([[scale, 0, ax - scale * ax + dx], [0, scale, ay - scale * ay + dy]])
    rgb = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    al = cv2.warpAffine(alpha, M, (W, H), flags=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return rgb, np.clip(al, 0, 1)


def composite(bg, fg, alpha):
    al = alpha[..., None]
    return bg * (1 - al) + fg * al


def overlay_clay_edges(a, fid, out_path, boxes_uv=None):
    """The clay's edges in red on the still (like <id>-lock.png), plus optional boxes in green."""
    frame, kind, clay_file, pan, overscan, room = VF.FRAMES[fid]
    c = load(os.path.join(VF.R4, clay_file))
    H, W = a.shape[:2]
    cg = cv2.resize(gray(c), (W, H), interpolation=cv2.INTER_AREA)
    e = cv2.Canny(cg.astype(np.uint8), 50, 130)
    im = np.clip(a, 0, 255).astype(np.uint8).copy()
    im[e > 0] = (255, 40, 40)
    if boxes_uv:
        for (u0, u1, v0, v1) in boxes_uv:
            cv2.rectangle(im, (int(u0 * W), int(v0 * H)), (int(u1 * W), int(v1 * H)), (40, 200, 40), 2)
    Image.fromarray(im).save(out_path, quality=85)


def write_note(fid, note):
    od = VF.out_dir(fid)
    p = os.path.join(od, fid + "-fix.json")
    note = dict(asset_id=fid, date=DATE, script="assets/renders/house-nordic-v7-2026-11-02/fix_v7.py", tokens=0, **note)
    json.dump(note, open(p, "w"), indent=1, ensure_ascii=False)
    return p


def still_path(fid):
    return os.path.join(VF.out_dir(fid), fid + ".png")


def fix_path(fid):
    return os.path.join(VF.out_dir(fid), fid + "-fix.png")


# ---------------------------------------------------------------------------------------------------------------
# 1. K-boy-0: the sage band and skirting must not wrap the near (south) wall (Bible: band on the east and north walls)
# ---------------------------------------------------------------------------------------------------------------
def fix_kboy0(preview=False):
    fid = "pose-k-boy-0-v7"
    a = load(still_path(fid))
    H, W = a.shape[:2]
    g = gray(a)
    # the corner: the strongest vertical edge in the white upper wall around u 0.60
    x0, x1 = int(0.56 * W), int(0.64 * W)
    prof = np.abs(np.diff(g[int(0.05 * H):int(0.30 * H), x0:x1], axis=1)).mean(0)
    corner = x0 + int(np.argmax(prof))
    # the band line on the near wall: the strongest horizontal edge per column band (u 0.65-0.98) around v 0.30-0.40
    rows = []
    for xa in range(int(0.65 * W), int(0.98 * W), 40):
        p = np.abs(np.diff(g[int(0.28 * H):int(0.42 * H), xa:xa + 40], axis=0)).mean(1)
        rows.append((xa + 20, int(0.28 * H) + int(np.argmax(p))))
    xs_, ys_ = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
    k, b = np.polyfit(xs_, ys_, 1)
    # the near wall below the band line, minus the floor (oak: hue 15-50 deg, S >= 20 %); the skirting is part of it
    hls = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    Hh, Ll, Ss = hls[..., 0] * 2, hls[..., 1], hls[..., 2]
    floor = (Hh >= 15) & (Hh <= 50) & (Ss >= 51)
    floor = cv2.morphologyEx(floor.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    X, Y = np.meshgrid(np.arange(W), np.arange(H))
    near = (X > corner) & (Y > (k * X + b) - 1)
    m = (near & (floor == 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] > 0.002 * W * H:
            keep[lab == i] = 1
    m = keep
    # reference colours on the near wall: white just above the band line, sage just below it (same light)
    band_y = (k * np.arange(W) + b)
    white_s, sage_s = [], []
    for x in range(corner + int(0.02 * W), int(0.98 * W)):
        yb = int(band_y[x])
        white_s.append(a[yb - int(0.05 * H):yb - int(0.01 * H), x])
        sage_s.append(a[yb + int(0.01 * H):yb + int(0.05 * H), x])
    white_ref = np.median(np.concatenate(white_s), 0)
    sage_ref = np.median(np.concatenate(sage_s), 0)
    ratio = white_ref / sage_ref
    al = feather(m.astype(np.float32), 1.0)
    recol = a * ratio[None, None, :]
    out = composite(a, recol, al)
    # the painted edge itself: its anti-aliased transition row would come out brighter than the wall, so the 7 px band
    # around the band line on the near wall is re-interpolated column-wise between the wall above and the repaint below
    line = ((np.abs(Y - (k * X + b)) <= 3) & (X > corner + 2)).astype(np.float32)
    out = fill_cols(out, line, band_px=6)
    save(out, fix_path(fid))
    if preview:
        overlay_clay_edges(out, fid, os.path.join(VF.out_dir(fid), fid + "-fix-lock.jpg"))
    # measurements after
    hls2 = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    sel = m > 0
    after = dict(H_deg=round(float(np.median(hls2[..., 0][sel]) * 2), 1), S_pct=round(float(np.median(hls2[..., 2][sel]) / 2.55), 1), L_pct=round(float(np.median(hls2[..., 1][sel]) / 2.55), 1))
    before = dict(H_deg=round(float(np.median(hls[..., 0][sel]) * 2), 1), S_pct=round(float(np.median(hls[..., 2][sel]) / 2.55), 1), L_pct=round(float(np.median(hls[..., 1][sel]) / 2.55), 1))
    wsel = (X > corner + 1) & (Y < band_y[None, :] - 0.01 * H) & (Y > 0.05 * H)
    wall_white = dict(H_deg=round(float(np.median(hls[..., 0][wsel]) * 2), 1), S_pct=round(float(np.median(hls[..., 2][wsel]) / 2.55), 1), L_pct=round(float(np.median(hls[..., 1][wsel]) / 2.55), 1))
    note = dict(
        fix="K-boy-0: the sage band and the skirting on the near (south) wall repainted warm white; the east wall keeps its band (review section 7 row 4; Bible 'kids rooms': band on the east and north walls only)",
        method="pixels right of the corner (strongest vertical edge in the white upper wall) and below the band line (fitted on the near wall), minus the oak floor (hue 15-50 deg, S >= 20 %), components >= 0.2 % of the frame; each pixel multiplied per channel by (white wall just above the band line) / (sage just below it) on the same wall, so the shading stays; 1 px feather; the 7 px band around the painted edge re-interpolated column-wise so the anti-aliased edge row does not stay as a bright line",
        corner_u=round(corner / W, 4), band_line=dict(v_at_corner=round(float(k * corner + b) / H, 4), v_at_right_edge=round(float(k * (W - 1) + b) / H, 4)),
        repainted_px=int(sel.sum()), repainted_pct_of_frame=round(float(sel.mean() * 100), 2),
        rgb_ratio=[round(float(x), 4) for x in ratio], white_ref_rgb=[round(float(x), 1) for x in white_ref], sage_ref_rgb=[round(float(x), 1) for x in sage_ref],
        hsl_before=before, hsl_after=after, hsl_white_wall_above=wall_white,
        acceptance="the near wall white all over, like K-girl-0; the band stops at a clean line at the corner (review section 7 row 4); after the grade: H 32-40, S 15-28 (Bible, G1.9)",
        untouched="the east wall band, the desk, the bed, the floor, the shelves",
        outputs=dict(fix=os.path.relpath(fix_path(fid), VF.REPO)))
    p = write_note(fid, note)
    print(json.dumps(note, ensure_ascii=False, indent=1))
    return p


# ---------------------------------------------------------------------------------------------------------------
# 2. K-girl: the doll on the desk at the slot's size (review section 7 row 5): scale ~0.70 about its seat on the desk
# ---------------------------------------------------------------------------------------------------------------
DOLL_BOX = (0.6854, 0.7171, 0.462, 0.5742)      # clay selfcheck girl/doll (canvas uv)
DOLL_SCALE = 0.68


def fix_doll(preview=False):
    fid = "k-girl-v7"
    a = load(still_path(fid))
    H, W = a.shape[:2]
    al = grabcut(a, (0.655, 0.740, 0.355, 0.560))
    x0, x1, y0, y1 = bbox(al)
    # the seat: the lowest 8 rows of the matte, their x centre
    low = al[y1 - 8:y1 + 1]
    ys, xs = np.nonzero(low > 0.5)
    ax, ay = float(xs.mean()), float(y1)
    # the desk-top back edge near the doll (where it sits)
    g = gray(a)
    prof = np.abs(np.diff(g[int(0.50 * H):int(0.60 * H), int(0.66 * W):int(0.75 * W)], axis=0)).mean(1)
    desk_v = (int(0.50 * H) + int(np.argmax(prof))) / H
    # the doll's own hole (matte dilated 4 px) and a generous zone for its cast shadow: the light comes from the window
    # on the left, so the shadow lies to the right of the doll and on the desk below it; the zone reaches 12 % of the
    # width to the right and 1.2 % of the height below the desk line, and is feathered 25 px so that nothing is cut
    core = cv2.dilate((al > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    Y = np.arange(H)[:, None]
    desk_rows = (Y >= desk_v * H).astype(np.float32) * np.ones((1, W), np.float32)
    zx, zy = int(0.12 * W), int(0.012 * H)
    zone_wall = cv2.dilate((al > 0.5).astype(np.uint8), np.ones((2 * zy + 1, zx + 8), np.uint8), anchor=(zx, zy)).astype(np.float32)   # anchor at the right: grows to the right
    zx2, zy2 = int(0.03 * W), int(0.006 * H)
    zone_desk = cv2.dilate((al > 0.5).astype(np.uint8), np.ones((2 * zy2 + 1, zx2 + 8), np.uint8), anchor=(zx2, zy2)).astype(np.float32)
    zone = np.maximum(core, np.where(desk_rows > 0.5, zone_desk, zone_wall))
    # a shadow-free background: the wall rows by a row-wise linear fill of the zone from 30 px bands left and right with
    # the wall's own fine texture; the desk rows by the desk's grain copied from the right (the grain runs horizontally)
    bg = fill_rows(a, zone * (1 - desk_rows), band_px=30)
    wall_patch = (int(0.76 * W), int(0.38 * H), int(0.80 * W), int(0.46 * H))
    bg = add_texture(a, bg, zone * (1 - desk_rows), wall_patch, 1.0)
    bg = shift_copy(bg, zone * desk_rows, dx=int(0.11 * W))
    # the shadow as a ratio map (original / background) in the zone outside the doll; scaled with the doll about its seat
    ratio = np.clip(a / np.maximum(bg, 1.0), 0.45, 1.0)
    ratio = np.where((zone > 0.5)[..., None] & (core < 0.5)[..., None], ratio, 1.0)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 2.0)
    doll_rgb, doll_al = transform_layer(a, feather(al, 0.7), DOLL_SCALE, (ax, ay))
    sh_rgb, sh_al = transform_layer(ratio, zone, DOLL_SCALE, (ax, ay))
    sh = 1.0 + (np.clip(sh_rgb, 0.45, 1.0) - 1.0) * sh_al[..., None]
    z = np.maximum(feather(zone, 25.0), feather(core, 1.0))       # the old doll itself is always fully replaced
    out = a * (1 - z[..., None]) + (bg * sh) * z[..., None]
    out = composite(out, doll_rgb, doll_al)
    save(out, fix_path(fid))
    nx0, nx1, ny0, ny1 = bbox(doll_al)
    new_box = (nx0 / W, nx1 / W, ny0 / H, ny1 / H)
    old_box = (x0 / W, x1 / W, y0 / H, y1 / H)
    bw, bh = DOLL_BOX[1] - DOLL_BOX[0], DOLL_BOX[3] - DOLL_BOX[2]
    if preview:
        overlay_clay_edges(out, fid, os.path.join(VF.out_dir(fid), fid + "-fix-lock.jpg"), [DOLL_BOX])
    note = dict(
        fix="K-girl: the doll on the desk scaled to the slot's size (review section 7 row 5: ~0.70 to the box [0.685, 0.717, 0.462, 0.574], anchored at its seat on the desk by the wall); the pink wall and the desk top filled behind it; its contact / cast shadow scaled with it",
        method="grabCut matte of the doll (rect 0.655-0.740 x 0.355-0.560, 6 iterations, largest component); shadow zone = matte dilated 12 % of the width to the right on the wall rows (3 % on the desk rows), feathered 25 px except over the old doll itself; background = row-wise linear fill of the wall rows from 30 px bands left and right with the high-pass texture of a wall patch (u 0.76-0.80, v 0.38-0.46), the desk rows copied from the desk grain 11 % of the width to the right; shadow = original / background as a ratio map (0.45-1.0, blurred 2 px), scaled with the doll; doll layer scaled by %.2f about the seat point with INTER_AREA, 0.7 px feather".replace("%.2f", str(DOLL_SCALE)),
        scale=DOLL_SCALE, anchor_seat_uv=[round(ax / W, 4), round(ay / H, 4)], desk_top_v_render=round(desk_v, 4), desk_top_v_clay=0.5729,
        clay_box=list(DOLL_BOX), doll_before=[round(x, 4) for x in old_box], doll_after=[round(x, 4) for x in new_box],
        height_ratio_to_box=dict(before=round((old_box[3] - old_box[2]) / bh, 3), after=round((new_box[3] - new_box[2]) / bh, 3)),
        width_ratio_to_box=dict(before=round((old_box[1] - old_box[0]) / bw, 3), after=round((new_box[1] - new_box[0]) / bw, 3),
                                note="the clay proxy is a thin cylinder + sphere; a seated rabbit doll is wider than its proxy by construction, the height is the measure"),
        acceptance="the doll inside the box +-15 % (height), no seam at 100 % (review section 7 row 5)",
        untouched="everything else in the frame", outputs=dict(fix=os.path.relpath(fix_path(fid), VF.REPO)))
    write_note(fid, note)
    print(json.dumps({k: v for k, v in note.items() if k != "method"}, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------------------------------------------
# 3. K-boy: the window view without snow: the glass gets K-girl's view, mirrored (review section 7 row 3)
# ---------------------------------------------------------------------------------------------------------------
def _leftmost_strong(prof, frac=0.5):
    m = prof.max()
    idx = np.nonzero(prof >= frac * m)[0]
    return int(idx.min())


def _rightmost_strong(prof, frac=0.5):
    m = prof.max()
    idx = np.nonzero(prof >= frac * m)[0]
    return int(idx.max())


def pane_geometry(a):
    """The two glass panes of the kids' window (left wall, straight verticals) as quads in pixels:
    vertical sides from the mullion / right frame bar edges, the bottom from the glass -> rail edge, the top at y = 0."""
    H, W = a.shape[:2]
    g = gray(a)
    gx = np.abs(np.diff(g, axis=1))
    band = gx[int(0.10 * H):int(0.40 * H)].mean(0)

    def col(u0, u1, pick):
        s = band[int(u0 * W):int(u1 * W)]
        return int(u0 * W) + pick(s)
    xm_l = col(0.068, 0.092, _leftmost_strong)        # mullion, left edge  (left pane's right side)
    xm_r = col(0.094, 0.112, _rightmost_strong)       # mullion, right edge (right pane's left side)
    xf_l = col(0.188, 0.214, _leftmost_strong)        # right frame bar, left edge (right pane's right side)
    gy = np.abs(np.diff(g, axis=0))

    def bottom_points(xa, xb):
        pts = []
        for x in range(xa + 6, xb - 6, 12):
            p = gy[int(0.44 * H):int(0.54 * H), x:x + 12].mean(1)
            thr = max(6.0, 0.45 * p.max())
            i = int(np.nonzero(p >= thr)[0].min())
            pts.append((x + 6, int(0.44 * H) + i))
        return np.array([q[0] for q in pts], float), np.array([q[1] for q in pts], float)

    def robust_fit(xs_, ys_, k0=None, b0=None, tol=5.0):
        if k0 is None:
            k0, b0 = np.polyfit(xs_, ys_, 1)
        for _ in range(3):
            keep = np.abs(ys_ - (k0 * xs_ + b0)) <= tol
            if keep.sum() < 3:
                break
            k0, b0 = np.polyfit(xs_[keep], ys_[keep], 1)
        return k0, b0, int(keep.sum())
    # the bottom rail is one straight line under both panes; the right pane's glass -> rail edge is reliable in both
    # renders (trees against the white rail), the left pane's can fail where snow meets the rail (K-boy): so the line is
    # fitted on the right pane first and the left pane's points are only kept where they agree with it (+-5 px)
    xR, yR = bottom_points(xm_r, xf_l)
    kR, bR, nR = robust_fit(xR, yR)
    xL, yL = bottom_points(0, xm_l)
    xs_all, ys_all = np.r_[xR, xL], np.r_[yR, yL]
    k, b, n_all = robust_fit(xs_all, ys_all, kR, bR, tol=5.0)
    kL = kR = k
    bL = bR = b
    nL, mL, mR = int((np.abs(yL - (k * xL + b)) <= 5.0).sum()), len(xL), len(xR)
    nR = int((np.abs(yR - (k * xR + b)) <= 5.0).sum())
    left = np.float32([[0, 0], [xm_l, 0], [xm_l, kL * xm_l + bL], [0, bL]])
    right = np.float32([[xm_r, 0], [xf_l, 0], [xf_l, kR * xf_l + bR], [xm_r, kR * xm_r + bR]])
    info = dict(mullion_left_u=round(xm_l / W, 4), mullion_right_u=round(xm_r / W, 4), right_bar_left_u=round(xf_l / W, 4),
                left_bottom_v=[round(bL / H, 4), round((kL * xm_l + bL) / H, 4)], right_bottom_v=[round((kR * xm_r + bR) / H, 4), round((kR * xf_l + bR) / H, 4)],
                bottom_fit_points=[f"{nL}/{mL}", f"{nR}/{mR}"])
    return left, right, info


def quad_mask(quad, H, W):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [quad.astype(np.int32)], 1)
    return m.astype(np.float32)


def fix_window(preview=False):
    fid, src_id = "k-boy-v7", "k-girl-v7"
    a = load(still_path(fid))
    s = load(still_path(src_id))
    H, W = a.shape[:2]
    qa = pane_geometry(a)
    qs = pane_geometry(s)
    out = a.copy()
    gains = []
    masks = []
    for (dst, src) in ((qa[0], qs[0]), (qa[1], qs[1])):
        # mirrored correspondence: dst TL->src TR, dst TR->src TL, dst BR->src BL, dst BL->src BR
        src_m = np.float32([src[1], src[0], src[3], src[2]])
        M = cv2.getPerspectiveTransform(dst, src_m)
        warped = cv2.warpPerspective(s, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        m = quad_mask(dst, H, W)
        m_er = cv2.erode(m, np.ones((5, 5), np.uint8))
        # brightness: match the sky (top 15 % of the pane) median luminance of the boy's own view
        sky = (m_er > 0.5) & (np.arange(H)[:, None] < 0.15 * dst[:, 1].max())
        lb, ls = np.median(gray(a)[sky]), np.median(gray(warped)[sky])
        gain = float(np.clip(lb / max(ls, 1.0), 0.9, 1.15))
        gains.append(round(gain, 4))
        al = feather(m_er, 1.0) * m
        out = composite(out, np.clip(warped * gain, 0, 255), al)
        masks.append(m_er)
    save(out, fix_path(fid))
    glass = np.maximum(masks[0], masks[1]) > 0.5
    gb, go = gray(a)[glass], gray(out)[glass]
    if preview:
        im = np.clip(out, 0, 255).astype(np.uint8).copy()
        for q in qa[:2]:
            cv2.polylines(im, [q.astype(np.int32)], True, (255, 40, 40), 2)
        Image.fromarray(im[:int(0.6 * H), :int(0.3 * W)]).save(os.path.join(VF.out_dir(fid), fid + "-fix-window.jpg"), quality=88)
        overlay_clay_edges(out, fid, os.path.join(VF.out_dir(fid), fid + "-fix-lock.jpg"))
    note = dict(
        fix="K-boy: the window view without snow: each glass pane receives K-girl v7's view of the same pane, mirrored left-right so the trees do not repeat between the two rooms; frame, mullion, sill and reveal stay K-boy's own pixels (review section 7 row 3; Bible: bare birches, no snow; TR3 open)",
        method="pane quads from each render: vertical sides = mullion / right-bar edges (strongest |dx| in u 0.068-0.092, 0.094-0.112, 0.188-0.214 over v 0.10-0.40), bottom = one line (the rail is straight under both panes) fitted robustly on the topmost glass->rail edge per 12 px column (v 0.44-0.54), seeded by the right pane where trees meet the rail, left-pane points kept only within 5 px of it (snow against the white rail gives no edge), top = the canvas top; per pane a homography K-boy quad -> K-girl quad with left and right swapped (cv2.warpPerspective); composite inside the quad eroded 2 px with a 1 px feather; gain per pane so the sky median luminance (top 15 %% of the pane) equals K-boy's own",
        panes_boy=qa[2], panes_girl=qs[2], gain_per_pane=gains,
        glass_px=int(glass.sum()), glass_L_median_before=round(float(np.median(gb)) / 2.55, 1), glass_L_median_after=round(float(np.median(go)) / 2.55, 1),
        glass_L_p99_before=round(float(np.percentile(gb, 99)) / 2.55, 1), glass_L_p99_after=round(float(np.percentile(go, 99)) / 2.55, 1),
        acceptance="no snow; bare birches; the same hour as the rest of the house; after the grade the window is still the brightest area with p99 <= 97 (G1.7, G1.13)",
        untouched="everything outside the two glass quads", outputs=dict(fix=os.path.relpath(fix_path(fid), VF.REPO)))
    write_note(fid, note)
    print(json.dumps({k: v for k, v in note.items() if k != "method"}, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------------------------------------------
# 4. W0: the desk group and the shelf down to the clay lines; basket and bin to their boxes (review section 7 row 6)
# ---------------------------------------------------------------------------------------------------------------
def rect_mask(H, W, u0, u1, v0, v1):
    m = np.zeros((H, W), np.float32)
    m[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)] = 1
    return m


def fill_rows_valid(a, hole, valid, band_px=24, max_search=600):
    """fill_rows whose references are the nearest `valid` pixels (not merely non-hole) left and right of each run."""
    out = a.copy()
    H, W = hole.shape
    for y in range(H):
        row = hole[y] > 0.5
        if not row.any():
            continue
        xs = np.nonzero(row)[0]
        splits = np.nonzero(np.diff(xs) > 1)[0]
        starts = np.r_[xs[0], xs[splits + 1]]
        ends = np.r_[xs[splits], xs[-1]]
        vrow = valid[y] > 0.5
        for s_, e_ in zip(starts, ends):
            L = R = None
            # left reference: walk left to the first valid pixel, then a band of valid pixels
            x = s_ - 1
            while x >= 0 and x >= s_ - max_search and not vrow[x]:
                x -= 1
            if x >= 0 and vrow[x]:
                sel = np.nonzero(vrow[max(0, x - band_px):x + 1])[0] + max(0, x - band_px)
                L = out[y, sel].mean(0)
            x = e_ + 1
            while x < W and x <= e_ + max_search and not vrow[x]:
                x += 1
            if x < W and vrow[x]:
                sel = np.nonzero(vrow[x:min(W, x + band_px + 1)])[0] + x
                R = out[y, sel].mean(0)
            if L is None and R is None:
                continue
            if L is None:
                L = R
            if R is None:
                R = L
            t = (np.arange(s_, e_ + 1) - s_ + 0.5) / (e_ - s_ + 1)
            out[y, s_:e_ + 1] = L[None, :] * (1 - t)[:, None] + R[None, :] * t[:, None]
    return out


def fill_from_above(a, hole, valid, band_px=10, blend_below=False):
    """Fill each hole column from the nearest valid pixels above it (a band of band_px rows), optionally blending to the
    nearest valid pixels below. For walls, whose vertical gradient is gentle."""
    out = a.copy()
    H, W = hole.shape
    for x in range(W):
        col = hole[:, x] > 0.5
        if not col.any():
            continue
        ys = np.nonzero(col)[0]
        splits = np.nonzero(np.diff(ys) > 1)[0]
        starts = np.r_[ys[0], ys[splits + 1]]
        ends = np.r_[ys[splits], ys[-1]]
        vcol = valid[:, x] > 0.5
        for s_, e_ in zip(starts, ends):
            y = s_ - 1
            while y >= 0 and not vcol[y]:
                y -= 1
            if y < 0:
                continue
            sel = np.nonzero(vcol[max(0, y - band_px):y + 1])[0] + max(0, y - band_px)
            A = out[sel, x].mean(0)
            B = None
            if blend_below:
                y2 = e_ + 1
                while y2 < H and not vcol[y2]:
                    y2 += 1
                if y2 < H:
                    sel2 = np.nonzero(vcol[y2:min(H, y2 + band_px + 1)])[0] + y2
                    B = out[sel2, x].mean(0)
            if B is None:
                out[s_:e_ + 1, x] = A
            else:
                t = (np.arange(s_, e_ + 1) - s_ + 0.5) / (e_ - s_ + 1)
                out[s_:e_ + 1, x] = A[None, :] * (1 - t)[:, None] + B[None, :] * t[:, None]
    return out


def row_edges(g, u0, u1, v0, v1, n=6, minsep=6):
    H, W = g.shape
    x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
    prof = np.abs(np.diff(g[y0:y1, x0:x1], axis=0)).mean(1)
    idx = np.argsort(prof)[::-1]
    out = []
    for i in idx:
        if all(abs(i - j) >= minsep for j, _ in out):
            out.append((i, prof[i]))
        if len(out) >= n:
            break
    return sorted([(round((y0 + i) / H, 4), round(float(s), 1)) for i, s in out])


# render-measured geometry of W0 v7 (uv of the 2736x1539 still), see the note for the clay values
W0_DESK = dict(slab=(0.3143, 0.6736, 0.530, 0.5789), drawer=(0.3238, 0.6433, 0.5789, 0.6381),
               panel_l=(0.3100, 0.3245, 0.5789, 0.8713), panel_r=(0.6425, 0.6780, 0.5789, 0.8713),
               void=(0.3245, 0.6425, 0.6381, 0.7250), chair=(0.4342, 0.5643, 0.5621, 0.7973), cup=(0.378, 0.412, 0.462, 0.540))
W0_SHELF = (0.350, 0.655, 0.178, 0.305)
W0_DY = 0.036            # desk group: drawer top 0.5789 -> clay 0.6148, panel bottom 0.8713 -> 0.9042, chair seat 0.7511 -> 0.7856
W0_DY_SHELF = 0.006      # shelf top 0.2482 -> clay 0.2542
W0_BASKET_BOX = (0.3609, 0.4232, 0.7389, 0.8806)
W0_BIN_BOX = (0.5844, 0.638, 0.7495, 0.8912)
W0_ZONES = dict(skirting_top=0.755, floor_top=0.7966, rug_top=0.862)


def fix_w0(preview=False):
    fid = "w0-v7"
    a = load(still_path(fid))
    H, W = a.shape[:2]
    hls = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    Hh, Ll, Ss = hls[..., 0] * 2, hls[..., 1], hls[..., 2]
    # the plant's leaves (stay in front of everything): green
    leaf = ((Hh >= 60) & (Hh <= 170) & (Ss >= 55) & (Ll < 200)).astype(np.uint8)
    leaf = cv2.morphologyEx(leaf, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    leaf = cv2.dilate(leaf, np.ones((3, 3), np.uint8)).astype(np.float32)
    # the chair legs below the seat: vertical oak bars. Their columns are read where they stand out: on the rug rows
    # (oak against the pale rug) and, for the shorter rear legs, as darker dips of the column mean on the floor rows;
    # the floor and the rug between the legs stay where they are
    chair = W0_DESK["chair"]
    cx0, cx1 = int(0.428 * W), int(0.572 * W)
    seat_y = int((chair[3] - 0.003) * H)
    rug_y, floor_y = int(W0_ZONES["rug_top"] * H), int(W0_ZONES["floor_top"] * H)
    oak = ((Hh >= 20) & (Hh <= 50) & (Ss >= 55) & (Ll > 90) & (Ll < 215)).astype(np.float32)

    def runs(mask1d, min_w):
        idx = np.nonzero(mask1d)[0]
        if len(idx) == 0:
            return []
        splits = np.nonzero(np.diff(idx) > 1)[0]
        starts, ends = np.r_[idx[0], idx[splits + 1]], np.r_[idx[splits], idx[-1]]
        return [(int(s_), int(e_)) for s_, e_ in zip(starts, ends) if e_ - s_ + 1 >= min_w]
    legs = np.zeros((H, W), np.float32)
    # rug rows: oak columns (fraction of oak pixels per column >= 0.6 over the rug rows)
    frac = oak[rug_y + 10:H - 4, cx0:cx1].mean(0)
    for s_, e_ in runs(frac >= 0.6, 8):
        legs[seat_y:H, cx0 + s_:cx0 + e_ + 1] = oak[seat_y:H, cx0 + s_:cx0 + e_ + 1]
        legs[seat_y:rug_y + 10, cx0 + s_:cx0 + e_ + 1] = 1          # above the rug the bar continues straight up to the seat
    # floor rows: darker dips (the rear legs end on the floor)
    Lcol = Ll[floor_y + 6:rug_y - 4, cx0:cx1].mean(0)
    dip = Lcol < (np.median(Lcol) - 10)
    for s_, e_ in runs(dip, 8):
        legs[seat_y:rug_y, cx0 + s_:cx0 + e_ + 1] = 1
    legs = cv2.dilate(legs.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
    leg_cols = [(round((cx0 + s_) / W, 4), round((cx0 + e_) / W, 4)) for s_, e_ in runs(frac >= 0.6, 8)] + \
               [(round((cx0 + s_) / W, 4), round((cx0 + e_) / W, 4)) for s_, e_ in runs(dip, 8)]
    # the group that moves by W0_DY: desk (slab, drawer, panels), the shadowed void wall under the drawer, chair, cup
    grp = np.zeros((H, W), np.float32)
    for k_, r in W0_DESK.items():
        grp = np.maximum(grp, rect_mask(H, W, *r))
    grp = np.maximum(grp, legs)
    basket = grabcut(a, (0.345, 0.432, 0.660, 0.848))
    bin_ = grabcut(a, (0.572, 0.655, 0.695, 0.858))
    grp_al = grp * (1 - basket) * (1 - bin_)
    # desk texture under the leaves (so the moved desk has no leaf-shaped holes); the plant itself goes back on top
    sprite = inpaint(a, (leaf > 0.5) & (grp_al > 0.5), radius=7)
    shelf = rect_mask(H, W, *W0_SHELF)
    # background: every sprite's original footprint filled by zone. Only what no moved sprite covers matters:
    # the wall strips above the slab, the cup and the shelf (from the lit wall above them) and the chair legs'
    # old footprints on the floor and the rug (the texture 28 px to the right / left)
    hole = np.maximum.reduce([grp_al, basket, bin_, shelf])
    valid = 1 - np.maximum(hole, leaf)
    Y = np.arange(H)[:, None] / H
    z = W0_ZONES
    wall_z = hole * (Y < z["skirting_top"])
    low_z = hole * (Y >= z["skirting_top"])
    bg = fill_from_above(a, wall_z, valid, band_px=10)
    bg = add_texture(a, bg, wall_z, (int(0.70 * W), int(0.40 * H), int(0.74 * W), int(0.50 * H)), 1.0)
    bg = shift_copy(bg, low_z, dx=-28)
    still = low_z * cv2.warpAffine(low_z, np.float32([[1, 0, -28], [0, 1, 0]]), (W, H))   # where the source was a hole too
    bg = shift_copy(bg, still, dx=28)
    out = bg
    # the group, shifted
    dy = W0_DY * H
    g_rgb, g_al = transform_layer(sprite, feather(grp_al, 0.6), 1.0, (0, 0), 0, dy)
    out = composite(out, g_rgb, g_al)
    # basket and bin: to their clay boxes from the floor contact (bottom centre), scaled to the box height (never up)
    rec = {}
    for nm, al, box in (("basket", basket, W0_BASKET_BOX), ("bin", bin_, W0_BIN_BOX)):
        x0, x1, y0, y1 = bbox(al)
        cx = float(np.nonzero(al[y1 - 6:y1 + 1] > 0.5)[1].mean()) + x0 * 0 if False else float(np.nonzero(al[y1 - 6:y1 + 1] > 0.5)[1].mean())
        h = (y1 - y0) / H
        scale = min(1.0, (box[3] - box[2]) / h)
        dyo = dy            # with the group: both bottoms then land within 0.007 of their box bottoms (0.8814 / 0.8846)
        r_rgb, r_al = transform_layer(a, feather(al, 0.6), scale, (cx, float(y1)), 0, dyo)
        out = composite(out, r_rgb, r_al)
        nx0, nx1, ny0, ny1 = bbox(r_al)
        rec[nm] = dict(before=[round(x0 / W, 4), round(x1 / W, 4), round(y0 / H, 4), round(y1 / H, 4)], after=[round(nx0 / W, 4), round(nx1 / W, 4), round(ny0 / H, 4), round(ny1 / H, 4)],
                       box=list(box), scale=round(scale, 3), dy=round(dyo / H, 4),
                       height_ratio_to_box=dict(before=round(h / (box[3] - box[2]), 3), after=round((ny1 - ny0) / H / (box[3] - box[2]), 3)),
                       width_ratio_to_box=dict(before=round((x1 - x0) / W / (box[1] - box[0]), 3), after=round((nx1 - nx0) / W / (box[1] - box[0]), 3)))
    # the shelf with its boxes and its shadow band, shifted
    s_rgb, s_al = transform_layer(a, feather(shelf, 0.6), 1.0, (0, 0), 0, W0_DY_SHELF * H)
    out = composite(out, s_rgb, s_al)
    # the plant back on top at its place
    out = composite(out, a, feather(leaf, 0.5))
    save(out, fix_path(fid))
    if preview:
        overlay_clay_edges(out, fid, os.path.join(VF.out_dir(fid), fid + "-fix-lock.jpg"), [W0_BASKET_BOX, W0_BIN_BOX])
    # measure the lines after, against the clay
    g2 = gray(out)
    gc = cv2.resize(gray(load(os.path.join(VF.R4, "W0.png"))), (W, H), interpolation=cv2.INTER_AREA)
    checks = {}
    for nm, (u0, u1, v0, v1, clay_v) in dict(shelf_top=(0.40, 0.46, 0.20, 0.30, 0.2542), drawer_top=(0.36, 0.42, 0.56, 0.66, 0.6148), drawer_bottom=(0.36, 0.42, 0.64, 0.72, 0.6787),
                                            panel_bottom=(0.655, 0.675, 0.86, 0.95, 0.9042), chair_top=(0.47, 0.53, 0.56, 0.64, 0.6023), chair_seat=(0.47, 0.53, 0.74, 0.82, 0.7856)).items():
        er = row_edges(g2, u0, u1, v0, v1, n=4)
        ec = row_edges(gc, u0, u1, v0, v1, n=4)
        best_c = min(ec, key=lambda t: abs(t[0] - clay_v))[0]          # the clay line nearest the expected value
        best_r = min(er, key=lambda t: abs(t[0] - best_c))[0]          # the render line nearest it (several lines share a band)
        checks[nm] = dict(render_after_v=best_r, clay_v=best_c, clay_v_expected=clay_v, d_v=round(best_r - best_c, 4), pass_0_01=bool(abs(best_r - best_c) <= 0.01))
    note = dict(
        fix="W0: the desk (slab, drawer, panels), the pencil cup, the chair, the rope basket and the paper bin moved down 0.036 of the height onto the clay lines; the shelf with its felt boxes down 0.006; the wall strips, skirting, floor and rug behind them filled; the plant and the rug not moved (review section 7 row 6, section 2.4)",
        method="render-measured rectangles for the desk slab (v 0.530-0.579), drawer (0.579-0.638), panels (to 0.871), the shadowed void wall under the drawer (0.638-0.725), the chair body (u 0.434-0.564, v 0.562-0.797) and its legs as vertical oak bars (columns read on the rug rows, the rear legs as darker dips on the floor rows), the cup (u 0.378-0.412, v 0.462-0.540): one group, shifted rigidly by +0.036 H; the leaves of the plant (green, hue 60-170) excluded from the group and put back on top, the desk under them inpainted first; basket and bin matted by grabCut, moved with the group (their bottoms then sit 0.001 and 0.007 from their clay box bottoms) and scaled about their floor contact to the box height only if taller than it (neither is: 0.99 and 0.98); shelf rect (u 0.350-0.655, v 0.178-0.305, with its shadow band) shifted +0.006 H; the wall strips the move exposes filled column-wise from the lit wall above them (with the wall's high-pass texture), the chair legs' old footprints on the floor and rug from the texture 28 px beside them",
        measured_before=dict(shelf_top=0.2482, drawer_top=0.5789, drawer_bottom=0.6381, panel_bottom=0.8713, chair_top=0.5621, chair_seat=0.7511, skirting_line=0.7966, rug_top=0.862,
                             note="the designer's review put the shelf ~0.03 high; measured against the clay it is 0.006 high (shelf top 0.2482 vs 0.2542), so it moves 0.006"),
        clay=dict(shelf_top=0.2542, drawer_top=0.6148, drawer_bottom=0.6787, panel_bottom=0.9042, chair_top=0.6023, chair_seat=0.7856, skirting_line=0.8338),
        dy_group=W0_DY, dy_shelf=W0_DY_SHELF, chair_leg_columns_u=leg_cols, basket=rec["basket"], bin=rec["bin"], lines_after=checks,
        left_as_is="the skirting (0.797 vs clay 0.834), the rug (0.862 vs 0.904) and the plant stay where the render put them (review: the plant and the rug do not move); the desk therefore stands 0.04 into the rug",
        acceptance="everything on the clay +-0.01; the plant and the rug not moved (review section 7 row 6)",
        outputs=dict(fix=os.path.relpath(fix_path(fid), VF.REPO)))
    write_note(fid, note)
    print(json.dumps({k: v for k, v in note.items() if k not in ("method",)}, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------------------------------------------
# 5. M0: stage 1 of m0-v7-r3.txt: the six moved pieces back to their clay size and place (review section 2.1 (b))
# ---------------------------------------------------------------------------------------------------------------
M0_SOFA_ARMS_RENDER = (0.5069, 0.848)        # m0-v7-r2-measurements.json sofa_width_check
M0_SOFA_ARMS_CLAY = (0.538, 0.8147)
M0_SOFA_BACK_TOP, M0_SOFA_ARM_TOPS = 0.494, (0.560, 0.568)
M0_SOFA_CONTACT_V = 0.814                     # the legs' feet in r2 (matte)
M0_TABLE_BOX = (0.512, 0.762, 0.6787, 0.8699)
M0_ARMCHAIR_BOX = (0.1896, 0.3867, 0.6218, 0.9056)
M0_BASKET_BOX = (0.862, 0.9245, 0.6671, 0.7968)
M0_PENDANT_U, M0_PENDANT_BOTTOM_V = (0.600, 0.655), 0.16
M0_LAMP_BOX, M0_SOCKET = (0.106, 0.130, 0.351, 0.444), (0.117, 0.431)
M0_ZONES = dict(skirting_top=0.710, floor_top=0.722, rug_top=0.785, cornice=(0.068, 0.097), curtain_hem=0.825, curtains=((0.112, 0.234), (0.316, 0.405)))


def m0_sofa_matte(a):
    H, W = a.shape[:2]
    u0, u1, v0, v1 = 0.47, 0.89, 0.44, 0.84
    X0, X1, Y0, Y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
    sub = np.ascontiguousarray(np.clip(a[Y0:Y1, X0:X1, ::-1], 0, 255).astype(np.uint8))
    m = np.full(sub.shape[:2], cv2.GC_PR_BGD, np.uint8)

    def r(uu0, uu1, vv0, vv1, val):
        m[int(vv0 * H) - Y0:int(vv1 * H) - Y0, int(uu0 * W) - X0:int(uu1 * W) - X0] = val
    r(0.47, 0.89, 0.44, 0.478, cv2.GC_BGD)
    r(0.47, 0.50, 0.44, 0.84, cv2.GC_BGD)
    r(0.86, 0.89, 0.44, 0.84, cv2.GC_BGD)
    r(0.52, 0.84, 0.50, 0.60, cv2.GC_PR_FGD)
    r(0.53, 0.83, 0.60, 0.72, cv2.GC_FGD)
    r(0.515, 0.84, 0.72, 0.78, cv2.GC_PR_FGD)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(sub, m, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    al = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    al = cv2.morphologyEx(al, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(al)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    al = np.where(lab == k, 1, 0).astype(np.uint8)
    full = np.zeros((H, W), np.float32)
    full[Y0:Y1, X0:X1] = al
    # the back and the arms against the cream wall are low-contrast: the geometric silhouette is added
    aL, aR = M0_SOFA_ARMS_RENDER
    full = np.maximum(full, rect_mask(H, W, aL + 0.012, aR - 0.012, M0_SOFA_BACK_TOP, 0.78))
    full = np.maximum(full, rect_mask(H, W, aL, aL + 0.014, M0_SOFA_ARM_TOPS[0], 0.78))
    full = np.maximum(full, rect_mask(H, W, aR - 0.014, aR, M0_SOFA_ARM_TOPS[1], 0.78))
    # the legs (oak) and the contact shadow band under the skirt, so the shadow scales with the sofa
    hls = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    Hh, Ll, Ss = hls[..., 0] * 2, hls[..., 1] / 2.55, hls[..., 2] / 2.55
    legs = ((Hh >= 20) & (Hh <= 50) & (Ss >= 25) & (Ll < 75)).astype(np.float32) * rect_mask(H, W, 0.50, 0.86, 0.77, 0.818)
    legs = cv2.morphologyEx(legs.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32)
    band = feather(rect_mask(H, W, aL + 0.004, aR - 0.004, 0.772, M0_SOFA_CONTACT_V), 4.0) * rect_mask(H, W, aL, aR, 0.77, M0_SOFA_CONTACT_V + 0.004)
    full = np.maximum(full, np.maximum(legs, band))
    full = cv2.morphologyEx((full > 0.5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8)).astype(np.float32)
    ff = (full * 255).astype(np.uint8)
    hole_fill = ff.copy()
    mask = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(hole_fill, mask, (0, 0), 255)
    full = np.maximum(full, (cv2.bitwise_not(hole_fill) > 0).astype(np.float32))
    return full


def clean_light(a, al):
    """Drop light low-saturation pixels (rug, throw, wall) from a matte; keep components > 400 px."""
    hls = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    Ll, Ss = hls[..., 1] / 2.55, hls[..., 2] / 2.55
    m2 = (al > 0.5) & ~((Ll > 78) & (Ss < 35))
    m2 = cv2.morphologyEx(m2.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    m2 = cv2.morphologyEx(m2, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m2)
    keep = np.zeros_like(m2)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 400:
            keep[lab == i] = 1
    return keep.astype(np.float32)


def place_in_box(al, box, H, W, scale=None, anchor="bottom-centre"):
    """Scale about the matte's bottom-centre (its floor contact) and move it onto the box's bottom-centre.
    scale None = fit the box (never enlarge)."""
    x0, x1, y0, y1 = bbox(al)
    w, h = (x1 - x0) / W, (y1 - y0) / H
    bw, bh = box[1] - box[0], box[3] - box[2]
    if scale is None:
        scale = min(1.0, bw / w, bh / h)
    ax, ay = (x0 + x1) / 2.0, float(y1)
    tx, ty = (box[0] + box[1]) / 2.0 * W, box[3] * H
    return scale, (ax, ay), (tx - ax, ty - ay)


def fix_m0(preview=False):
    fid = "m0-v7-r2"
    a = load(still_path(fid))
    H, W = a.shape[:2]
    z = M0_ZONES
    # ---- mattes
    sofa = m0_sofa_matte(a)
    table = grabcut(a, (0.465, 0.80, 0.625, 0.885), iters=8, pad_uv=0.01, open_px=3)
    armchair = clean_light(a, grabcut(a, (0.13, 0.385, 0.585, 0.925), iters=8, pad_uv=0.01, open_px=3))
    basket = clean_light(a, grabcut(a, (0.88, 0.99, 0.62, 0.82), iters=8, pad_uv=0.01, open_px=3))
    pendant = grabcut(a, (0.565, 0.715, 0.0, 0.175), iters=8, pad_uv=0.01, open_px=3)
    lamp = grabcut(a, (0.025, 0.125, 0.26, 0.45), iters=8, pad_uv=0.01, open_px=3)
    hls = cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    Ll, Ss = hls[..., 1] / 2.55, hls[..., 2] / 2.55
    # the lamp's hard parts: the dark plate / arm / stem and the shade (bright, bounded by the matte's upper part)
    lamp_dark = (lamp > 0.5) & (Ll < 35)
    shade = (lamp > 0.5) & (np.arange(H)[:, None] < 0.372 * H) & (np.arange(W)[None, :] > 0.045 * W)
    lamp_hard = cv2.morphologyEx(np.maximum(lamp_dark, shade).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32)
    n, lab, st, _ = cv2.connectedComponentsWithStats(lamp_hard.astype(np.uint8))
    keep = np.zeros_like(lamp_hard)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 300:
            keep[lab == i] = 1
    lamp_hard = keep
    plate = lamp_dark & (np.arange(H)[:, None] > 0.355 * H)
    ys, xs = np.nonzero(plate)
    plate_c = (float(xs.mean()), float(ys.mean()))
    # ---- transforms
    aL, aR = M0_SOFA_ARMS_RENDER
    cL, cR = M0_SOFA_ARMS_CLAY
    s_sofa = (cR - cL) / (aR - aL)
    sofa_anchor = ((aL + aR) / 2 * W, M0_SOFA_CONTACT_V * H)
    sofa_d = (0.0, (VF.M0_FURNITURE["sofa (fixed-product)"][3] - M0_SOFA_CONTACT_V) * H)
    tx0, tx1, ty0, ty1 = bbox(table)
    s_table = (M0_TABLE_BOX[1] - M0_TABLE_BOX[0]) / ((tx1 - tx0) / W)
    table_anchor = ((tx0 + tx1) / 2.0, float(ty1))
    table_d = ((M0_TABLE_BOX[0] + M0_TABLE_BOX[1]) / 2 * W - table_anchor[0], M0_TABLE_BOX[3] * H - table_anchor[1])
    s_arm, arm_anchor, arm_d = place_in_box(armchair, M0_ARMCHAIR_BOX, H, W)
    s_bask, bask_anchor, bask_d = place_in_box(basket, M0_BASKET_BOX, H, W)
    body = (pendant > 0.5) & (np.arange(H)[:, None] > 0.055 * H)
    bys, bxs = np.nonzero(body)
    body_box = (bxs.min() / W, bxs.max() / W, bys.min() / H, bys.max() / H)
    s_pend = (M0_PENDANT_U[1] - M0_PENDANT_U[0]) / (body_box[1] - body_box[0])
    pend_anchor = ((body_box[0] + body_box[1]) / 2 * W, body_box[3] * H)
    pend_d = ((M0_PENDANT_U[0] + M0_PENDANT_U[1]) / 2 * W - pend_anchor[0], M0_PENDANT_BOTTOM_V * H - pend_anchor[1])
    lamp_d = ((M0_LAMP_BOX[0] + M0_LAMP_BOX[1]) / 2 * W - plate_c[0], (M0_LAMP_BOX[2] + M0_LAMP_BOX[3]) / 2 * H - plate_c[1])
    # ---- background: every piece's footprint filled by zone
    dil = lambda m, k: cv2.dilate((m > 0.5).astype(np.uint8), np.ones((k, k), np.uint8)).astype(np.float32)
    glow = cv2.dilate((lamp_hard > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.09 * W) | 1, int(0.12 * H) | 1))).astype(np.float32)
    # the holes take the pieces' contact / cast shadow lines with them (a 5 px dilation left those lines on the wall
    # and the floor as ghost edges that the lock then measured as the old arms): 25 px round the sofa, 20 round the
    # table and the armchair, 15 round the basket, 9 round the pendant
    D = dict(sofa=25, table=20, armchair=20, basket=15, pendant=9)
    pieces = np.maximum.reduce([dil(sofa, D["sofa"]), dil(table, D["table"]), dil(armchair, D["armchair"]), dil(basket, D["basket"]), dil(pendant, D["pendant"])])
    hole = np.maximum(pieces, glow)
    valid = 1 - hole
    Y = np.arange(H)[:, None] / H
    X = np.arange(W)[None, :] / W
    bg = a.copy()
    # lamp glow and the pendant's ceiling / wall: Navier-Stokes inpainting (continuous at the boundary, so the wall's
    # shading runs into the hole and no ghost edge is left); the cornice band copied from the right
    pend_hole = dil(pendant, D["pendant"])
    cor = (Y >= z["cornice"][0]) & (Y <= z["cornice"][1])
    bg = inpaint(bg, np.maximum(glow, pend_hole * (~cor)), radius=12, method=cv2.INPAINT_NS)
    bg = shift_copy(bg, pend_hole * cor, dx=int(0.12 * W))
    # the curtains behind the armchair: vertical folds, copied from above
    curt = np.zeros((H, W), np.float32)
    for (cu0, cu1) in z["curtains"]:
        curt = np.maximum(curt, rect_mask(H, W, cu0, cu1, 0.0, z["curtain_hem"]))
    arm_hole = dil(armchair, D["armchair"])
    bg = shift_copy(bg, arm_hole * curt, dy=-int(0.33 * H))
    # the wall band behind the sofa's back (above the new back top): column-wise from the shaded wall above it, so
    # the sofa's shadow gradient on the wall continues; everything else row-wise
    # wall rows of every piece: inpainting (the shaded wall around the old silhouettes continues into the hole);
    # skirting, floor and rug rows: row-wise, which keeps the horizontal lines (skirting, rug edge) straight
    pieces_rest = np.maximum.reduce([dil(sofa, D["sofa"]), dil(table, D["table"]), arm_hole * (1 - curt), dil(basket, D["basket"])])
    wall_part = pieces_rest * (Y < z["skirting_top"])
    rest = pieces_rest * (Y >= z["skirting_top"])
    bg = fill_rows_valid(bg, rest, valid, band_px=24)          # the lower rows first, so the wall fill below
    # wall rows column-wise from the wall above (keeps the vertical corner line at u ~0.485 and the horizontal
    # gradient; inpainting mixed the darker window wall into the back wall across that corner) and blended to the
    # filled skirting below
    bg = fill_from_above(bg, wall_part, 1 - np.maximum(wall_part, rest * 0), band_px=10, blend_below=True)
    floor_z = rest * ((Y >= z["floor_top"]) & (Y < z["rug_top"]))
    rug_z = rest * (Y >= z["rug_top"])
    bg = add_texture(a, bg, floor_z, (int(0.05 * W), int(0.83 * H), int(0.11 * W), int(0.90 * H)), 1.0)
    bg = add_texture(a, bg, rug_z, (int(0.60 * W), int(0.87 * H), int(0.68 * W), int(0.94 * H)), 1.0)
    bg = add_texture(a, bg, wall_part, (int(0.88 * W), int(0.50 * H), int(0.95 * W), int(0.58 * H)), 0.7)
    out = bg
    # ---- the lamp's glow as a ratio map, moved with it
    ratio = np.clip(a / np.maximum(bg, 1.0), 1.0, 3.0)
    ratio = np.where((glow > 0.5)[..., None] & (lamp_hard < 0.5)[..., None], ratio, 1.0)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 2.0)
    g_rgb, g_al = transform_layer(ratio, feather(glow, 20.0), 1.0, (0, 0), *lamp_d)
    out = out * (1.0 + (np.clip(g_rgb, 1.0, 3.0) - 1.0) * g_al[..., None])
    l_rgb, l_al = transform_layer(a, feather(dil(lamp_hard, 3), 0.8), 1.0, (0, 0), *lamp_d)
    out = composite(out, l_rgb, l_al)
    # ---- the pendant: body scaled about its bottom centre, the rod redrawn straight to the ceiling
    body_al = feather(body.astype(np.float32), 0.8)
    p_rgb, p_al = transform_layer(a, body_al, s_pend, pend_anchor, *pend_d)
    out = composite(out, p_rgb, p_al)
    cord_px = a[(pendant > 0.5) & (Ll < 45) & (np.arange(H)[:, None] < 0.05 * H)]
    cord_rgb = np.median(cord_px, 0) if len(cord_px) else np.array([40.0, 36.0, 34.0])
    rod_x = int(round((M0_PENDANT_U[0] + M0_PENDANT_U[1]) / 2 * W))
    new_top = int(round(pend_anchor[1] + pend_d[1] - s_pend * (body_box[3] - body_box[2]) * H)) + 4
    rod = np.zeros((H, W), np.float32)
    cv2.line(rod, (rod_x, 0), (rod_x, new_top), 1.0, 3)
    out = composite(out, np.broadcast_to(cord_rgb, out.shape).astype(np.float32), feather(rod, 0.6))
    # ---- sofa, basket, table, armchair (depth order)
    s_rgb, s_al = transform_layer(a, feather(sofa, 1.0), s_sofa, sofa_anchor, *sofa_d)
    out = composite(out, s_rgb, s_al)
    b_rgb, b_al = transform_layer(a, feather(basket, 0.8), s_bask, bask_anchor, *bask_d)
    out = composite(out, b_rgb, b_al)
    t_rgb, t_al = transform_layer(a, feather(table, 0.8), s_table, table_anchor, *table_d)
    out = composite(out, t_rgb, t_al)
    c_rgb, c_al = transform_layer(a, feather(armchair, 0.8), s_arm, arm_anchor, *arm_d)
    out = composite(out, c_rgb, c_al)
    save(out, fix_path(fid))
    # ---- checks: the sofa arms (strongest vertical edge within +-0.035 of each clay arm, rows 35-85 % of the box)
    g2 = gray(out)
    box = VF.M0_FURNITURE["sofa (fixed-product)"]
    ry0, ry1 = int((box[2] + 0.35 * (box[3] - box[2])) * H), int((box[2] + 0.85 * (box[3] - box[2])) * H)
    prof = np.abs(np.diff(g2[ry0:ry1], axis=1)).mean(0)
    arms_after = []
    for c in M0_SOFA_ARMS_CLAY:
        x0, x1 = int((c - 0.035) * W), int((c + 0.035) * W)
        arms_after.append(round((x0 + int(np.argmax(prof[x0:x1]))) / W, 4))
    def after_box(al, scale, anchor, d):
        _, al2 = transform_layer(a, al, scale, anchor, *d)
        x0, x1, y0, y1 = bbox(al2)
        return [round(x0 / W, 4), round(x1 / W, 4), round(y0 / H, 4), round(y1 / H, 4)]
    rec = dict(
        sofa=dict(scale=round(s_sofa, 4), anchor_uv=[round(sofa_anchor[0] / W, 4), round(sofa_anchor[1] / H, 4)], dy=round(sofa_d[1] / H, 4),
                  arms_before=list(M0_SOFA_ARMS_RENDER), arms_clay=list(M0_SOFA_ARMS_CLAY), arms_after=arms_after,
                  width_ratio_after=round((arms_after[1] - arms_after[0]) / (cR - cL), 4), bbox_after=after_box(sofa, s_sofa, sofa_anchor, sofa_d), clay_box=list(box)),
        table=dict(scale=round(s_table, 4), bbox_before=[round(tx0 / W, 4), round(tx1 / W, 4), round(ty0 / H, 4), round(ty1 / H, 4)], bbox_after=after_box(table, s_table, table_anchor, table_d), clay_box=list(M0_TABLE_BOX)),
        armchair=dict(scale=round(s_arm, 4), shift_uv=[round(arm_d[0] / W, 4), round(arm_d[1] / H, 4)], bbox_before=[round(v, 4) for v in (bbox(armchair)[0] / W, bbox(armchair)[1] / W, bbox(armchair)[2] / H, bbox(armchair)[3] / H)],
                      bbox_after=after_box(armchair, s_arm, arm_anchor, arm_d), clay_box=list(M0_ARMCHAIR_BOX)),
        basket=dict(scale=round(s_bask, 4), shift_uv=[round(bask_d[0] / W, 4), round(bask_d[1] / H, 4)], bbox_after=after_box(basket, s_bask, bask_anchor, bask_d), clay_box=list(M0_BASKET_BOX)),
        pendant=dict(scale=round(s_pend, 4), body_before=[round(v, 4) for v in body_box], body_after=after_box(body.astype(np.float32), s_pend, pend_anchor, pend_d), target=dict(u=list(M0_PENDANT_U), bottom_v=M0_PENDANT_BOTTOM_V), rod_u=round(rod_x / W, 4)),
        lamp=dict(shift_uv=[round(lamp_d[0] / W, 4), round(lamp_d[1] / H, 4)], plate_centre_before=[round(plate_c[0] / W, 4), round(plate_c[1] / H, 4)], plate_centre_after=[round((plate_c[0] + lamp_d[0]) / W, 4), round((plate_c[1] + lamp_d[1]) / H, 4)],
                  clay_box=list(M0_LAMP_BOX), socket=list(M0_SOCKET), bbox_after=after_box(lamp_hard, 1.0, (0, 0), lamp_d)))
    if preview:
        overlay_clay_edges(out, fid, os.path.join(VF.out_dir(fid), fid + "-fix-lock.jpg"), [box, M0_TABLE_BOX, M0_ARMCHAIR_BOX, M0_BASKET_BOX, M0_LAMP_BOX])
    note = dict(
        fix="M0 r2, stage 1 of m0-v7-r3.txt (review section 2.1 (b), section 7 row 1): the sofa group scaled 0.811 about the mid-point of its floor-contact line and that line put on the clay's; the coffee-table group scaled to the clay table about the near legs; the armchair scaled into its clay box and moved right; the basket into its box; the pendant body to the clay's size and place with the rod redrawn straight to the ceiling; the wall lamp with its glow moved into its clay box. The holes behind them filled from the wall, cornice, skirting, floor, rug and curtains around them. Ungraded; no +0.6 stop lift (BIB1 open: one flag in process_v8 when decided). Conditional on V7Q1 = (a); discarded if the owner picks a new camera",
        method="mattes: sofa by grabCut seeded with a mask (sure background above the back, sure foreground on the seat) plus the geometric back / arm silhouette (back top v 0.494, arm tops 0.560 / 0.568, arms u 0.5069-0.848), the oak legs and the contact-shadow band to the feet (v 0.814); table, armchair, basket, pendant, lamp by grabCut in rects, armchair and basket cleaned of light low-saturation (rug / throw) pixels; the lamp's glow as a ratio map (original / wall fill) moved with the lamp. Fills: wall rows column-wise from the wall above each hole, blended to the filled skirting below (keeps the corner line at u ~0.485 and the horizontal gradient), with the wall's high-pass texture; the lamp's glow zone and the pendant's ceiling / wall by Navier-Stokes inpainting; skirting, floor and rug rows row-wise from the nearest untouched pixels with the zone's high-pass texture (keeps the skirting and rug lines straight), the cornice band copied from the right, the curtains behind the armchair copied from 0.33 H above, the lamp's wall column-wise from above and below. The holes are dilated 9-25 px so the pieces' contact-shadow lines go with them. Seams are rough by design: stage 2 (the paid image-to-image pass) repairs them",
        pieces=rec, zones=z,
        qa="sofa width ratio <= 1.05 against the clay arm edges, each edge within +-0.01 of 0.538 / 0.8147; table, armchair, basket, pendant, lamp inside their clay boxes +-15 %; the overlay <id>-fix-lock.jpg",
        untouched="art a, cubes b, curtains d, vase e (its ~0.02 drift left of its box recorded, not moved), window, walls, ceiling, rug outline",
        known_rough="the moved lamp shade crosses the left curtain's edge (the render drew the curtain 0.045 left of the clay); the sofa's new back top sits on a filled wall strip; the table's old top strip is filled rug; all for stage 2",
        outputs=dict(fix=os.path.relpath(fix_path(fid), VF.REPO)))
    write_note(fid, note)
    print(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["kboy0", "doll", "window", "w0", "m0"])
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    {"kboy0": fix_kboy0, "doll": fix_doll, "window": fix_window, "w0": fix_w0, "m0": fix_m0}.get(a.what, lambda **k: print("not implemented yet"))(preview=a.preview)
