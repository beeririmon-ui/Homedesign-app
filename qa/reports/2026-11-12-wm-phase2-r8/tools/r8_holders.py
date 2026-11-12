#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): the travertine pair's marks (designer 3.3.1: "the contact shadow is one soft ellipse under each foot; whatever
lies between the feet goes"). QA's own decomposition of the R7 shadow field (the frozen recipe's field, extract.shadow_one, as R7 carried
it with each piece), on the ungraded sources (work-r7 / work-r8) and on the graded files the tool reads:
  - the pieces: connected components of the pair's alpha >= 128 (A left, B right); the light comes from the left (the cast fans fall right);
  - each foot's OWN field (independent of fix_r8's rule):
      * its contact ellipse: the R7 darkening component under the piece's base (alpha 0, below the piece's lowest alpha row - 6), grown
        from the darkest under-base pixel over darkening >= 1/255;
      * its cast fan: per row, from the piece's right alpha edge going right while the R7 darkening does not rise by more than 2/255
        above its running minimum (the first rise ends the fan);
  - the MARKS: every other R7 darkening pixel (alpha 0) between A's fan and B's left alpha edge, rows 1236-1296;
  - checks: R8 == R7 on each foot's own field (pixels and mass); R8 <= R7 darkening everywhere (nothing added); every changed pixel is a
    mark pixel (outside it nothing changed) and inside the mark box; what remains on the marks (max, p99, count > 2/255) in R8; the
    scene: L* of the default set-B composite vs base.png on the mark pixels, r7 vs r8.
Writes data/holders.json and overlays/holders-*.png.    ~/.venvs/motion/bin/python3.12 -I r8_holders.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
LD = os.path.join(P2, "layers")


def u8(p):
    return np.asarray(Image.open(p))


def grey(p):
    a = u8(p)
    return (a[..., :3].min(2) if a.ndim == 3 else a).astype(np.int32)


def Lstar(rgb8):
    c = rgb8.astype(np.float64) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Y = lin @ np.array([0.2126729, 0.7151522, 0.0721750])
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    return 116 * f - 16


s7u = grey(os.path.join(P2, "work-r7/shadows/candle-holders.png"))
s8u = grey(os.path.join(P2, "work-r8/shadows/candle-holders.png"))
a7u = u8(os.path.join(P2, "work-r7/layers/candle-holders.png"))[..., 3].astype(np.int32)
a8u = u8(os.path.join(P2, "work-r8/layers/candle-holders.png"))[..., 3].astype(np.int32)
s7g = grey(os.path.join(LD, "candle-holders/candle-holders-cj-travertine-pedestal-r7-shadow.png"))
s8g = grey(os.path.join(LD, "candle-holders/candle-holders-cj-travertine-pedestal-r8-shadow.png"))
L7g = u8(os.path.join(LD, "candle-holders/candle-holders-cj-travertine-pedestal-r7.png")).astype(np.int32)
L8g = u8(os.path.join(LD, "candle-holders/candle-holders-cj-travertine-pedestal-r8.png")).astype(np.int32)
H, W = s7u.shape
res = dict(ungraded_layer_alpha_identical=bool((a7u == a8u).all()))

n, lab, st, _ = cv2.connectedComponentsWithStats((a7u >= 128).astype(np.uint8), 8)
ids = sorted([i for i in range(1, n) if st[i, 4] >= 200], key=lambda i: st[i, 0])
assert len(ids) == 2, st
PA, PB = lab == ids[0], lab == ids[1]
res["pieces"] = {k: dict(x0=int(st[i, 0]), y0=int(st[i, 1]), x1=int(st[i, 0] + st[i, 2] - 1), y1=int(st[i, 1] + st[i, 3] - 1))
                 for k, i in (("A", ids[0]), ("B", ids[1]))}
free = a7u == 0


def own_field(d, piece, name, tol=2.0):
    """one piece's own field on the darkening field d (0..255): a bottleneck (maximin) flood over alpha-0 pixels with d >= 1, seeded at the
    darkest pixel under the piece's base (its contact ellipse) and, per row, at the darkest pixel within 10 px off the piece's RIGHT alpha
    edge (its cast fan; the light comes from the left); a pixel joins only if it does not rise more than tol above the minimum along its
    best path (so a mark that rises again after the fan has fallen is not the foot's)"""
    import heapq
    p = res["pieces"][name]
    X0, X1, Y0, Y1 = p["x0"] - 30, p["x1"] + 40, p["y0"] - 4, p["y1"] + 40
    seeds = []
    sub = d[p["y1"] - 2:p["y1"] + 30, p["x0"]:p["x1"] + 1] * free[p["y1"] - 2:p["y1"] + 30, p["x0"]:p["x1"] + 1]   # the contact ellipse's peak
    yy, xx = np.unravel_index(np.argmax(sub), sub.shape)
    seeds.append((p["y1"] - 2 + int(yy), p["x0"] + int(xx)))
    for y in range(p["y0"], p["y1"] + 1):
        xs = np.nonzero(piece[y])[0]
        if len(xs):
            xr = int(xs.max()) + 1
            win = np.arange(xr, xr + 10)
            win = win[free[y, win]]
            if len(win):
                x = int(win[np.argmax(d[y, win])])      # the fan's peak in the 10 px off the piece's right edge
                if d[y, x] >= 1:
                    seeds.append((y, x))
    best = np.full(d.shape, -1.0)
    heap = []
    for (y, x) in seeds:
        if d[y, x] >= 1:
            best[y, x] = d[y, x]
            heapq.heappush(heap, (-float(d[y, x]), y, x))
    while heap:
        nb, y, x = heapq.heappop(heap)
        b = -nb
        if b < best[y, x]:
            continue
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            qy, qx = y + dy, x + dx
            if not (Y0 <= qy < Y1 and X0 <= qx < X1) or not free[qy, qx] or d[qy, qx] < 1:
                continue
            if d[qy, qx] > b + tol:
                continue
            nbq = min(b, float(d[qy, qx]))
            if nbq > best[qy, qx]:
                best[qy, qx] = nbq
                heapq.heappush(heap, (-nbq, qy, qx))
    return best >= 0


d7, d8 = 255 - s7u, 255 - s8u
sens = {}
for tol in (1.0, 1.5, 2.0):
    oA, oB = own_field(d7, PA, "A", tol), own_field(d7, PB, "B", tol)
    chg = d7 != d8
    sens[str(tol)] = dict(own_A_px=int(oA.sum()), own_B_px=int(oB.sum()), changed_on_own_A=int((chg & oA).sum()), changed_on_own_B=int((chg & oB).sum()),
                          max_change_on_own_A=int(np.abs(d7 - d8)[oA].max()), max_change_on_own_B=int(np.abs(d7 - d8)[oB].max()),
                          own_A_mass_r7_r8=[int(d7[oA].sum()), int(d8[oA].sum())], own_B_mass_r7_r8=[int(d7[oB].sum()), int(d8[oB].sum())])
res["own_field_tolerance_sensitivity"] = sens
ownA, ownB = own_field(d7, PA, "A", 1.5), own_field(d7, PB, "B", 1.5)
# the marks: every other R7 darkening pixel between A's fan and B's left alpha edge
band = np.zeros(d7.shape, bool)
band[1236:1297, res["pieces"]["A"]["x1"] - 2:res["pieces"]["B"]["x0"] + 6] = True
bx_left = np.full(H, W)
for y in range(H):
    xs = np.nonzero(PB[y])[0]
    if len(xs):
        bx_left[y] = xs.min()
cols = np.arange(W)[None, :]
left_of_B = cols < np.where(bx_left < W, bx_left, res["pieces"]["B"]["x0"] + 6)[:, None]
marks = band & free & (d7 >= 1) & ~ownA & ~ownB & left_of_B
ch_u = s7u != s8u
ch_g = s7g != s8g


def bb(m):
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


MARK_BOX = (1704, 1240, 1752, 1292)
DES_BOX = (1711, 1251, 1746, 1265)
inbox = np.zeros(d7.shape, bool)
inbox[MARK_BOX[1]:MARK_BOX[3], MARK_BOX[0]:MARK_BOX[2]] = True
res["changes"] = dict(
    ungraded=dict(px=int(ch_u.sum()), box=bb(ch_u), darker_px=int((s8u < s7u).sum()), outside_r8_mark_box=int((ch_u & ~inbox).sum()),
                  changed_not_mark_px=int((ch_u & ~marks).sum()), changed_on_own_A=int((ch_u & ownA).sum()), changed_on_own_B=int((ch_u & ownB).sum()),
                  changed_where_alpha_gt0=int((ch_u & ~free).sum())),
    graded=dict(px=int(ch_g.sum()), box=bb(ch_g), darker_px=int((s8g < s7g).sum()), outside_r8_mark_box=int((ch_g & ~inbox).sum()),
                changed_not_mark_px=int((ch_g & ~marks).sum()), changed_on_own_A=int((ch_g & ownA).sum()), changed_on_own_B=int((ch_g & ownB).sum())),
    r8_mark_box=MARK_BOX, designer_box_about=DES_BOX)
res["own_fields"] = {k: dict(px=int(m.sum()), box=bb(m), mass_r7=int(d7[m].sum()), mass_r8=int(d8[m].sum()), max_r7=int(d7[m].max()),
                             identical=bool((d7[m] == d8[m]).all()))
                     for k, m in (("A", ownA), ("B", ownB))}
dm7, dm8 = d7[marks], d8[marks]
res["marks"] = dict(px=int(marks.sum()), box=bb(marks), r7=dict(max=int(dm7.max()), mean=round(float(dm7.mean()), 2), mass=int(dm7.sum())),
                    r8=dict(max=int(dm8.max()), p99=float(np.percentile(dm8, 99)), mean=round(float(dm8.mean()), 3), mass=int(dm8.sum()),
                            px_gt0=int((dm8 > 0).sum()), px_gt2=int((dm8 > 2).sum()), px_gt4=int((dm8 > 4).sum())))
# what remains, split: A's fan carried on past its first rise (fix_r8's fade) vs the rest of the gap
fade = np.zeros(d7.shape, bool)
for y in range(1236, 1297):
    xs = np.nonzero(ownA[y])[0]
    if len(xs):
        x = int(xs.max()) + 1
        fade[y, x:x + 10] = True
fade &= marks
gap = marks & ~fade
res["remaining"] = dict(
    a_fan_fade_10px=dict(px=int(fade.sum()), max=int(d8[fade].max()) if fade.any() else 0, px_gt2=int((d8[fade] > 2).sum()),
                         r7_max=int(d7[fade].max()) if fade.any() else 0, cols_until_le2=int(max((np.nonzero(fade[y] & (d8[y] > 2))[0].max() - np.nonzero(fade[y])[0].min() + 1)
                                                                       for y in range(H) if (fade[y] & (d8[y] > 2)).any())) if (fade & (d8 > 2)).any() else 0,
                         note="the 10 px right of A's own fan, on mark pixels: fix_r8 fades A's field there (exp, 4 px) instead of the mark"),
    rest_of_gap=dict(px=int(gap.sum()), max=int(d8[gap].max()), px_gt2=int((d8[gap] > 2).sum()), px_gt0=int((d8[gap] > 0).sum())),
    r8_zone_x1718_1752=dict(max=int(d8[1240:1292, 1718:1752][free[1240:1292, 1718:1752]].max())))
# the gap between the two own fields along the table line: rows where both feet stand
res["darkening_values_remaining_hist"] = {str(v): int((dm8 == v).sum()) for v in np.unique(dm8)}

# the graded layer: 8 soft-edge px changed RGB (B's left edge): their effect on the composite
dA = L8g[..., 3]
drgb = np.abs(L8g[..., :3] - L7g[..., :3]).max(2)
m = (drgb > 0) & (dA > 0)
res["graded_layer_rgb_change"] = dict(px=int(m.sum()), alpha_max=int(dA[m].max()) if m.any() else 0, rgb_max=int(drgb[m].max()) if m.any() else 0,
                                      composite_effect_max_levels=round(float((drgb * dA / 255)[m].max()), 2) if m.any() else 0,
                                      alpha_identical=bool((L7g[..., 3] == L8g[..., 3]).all()))

# the scene: L* drop of the default composite vs base on the marks (set B; the sets share this region)
base = u8(os.path.join(LD, "base.png"))[..., :3]
Lb = Lstar(base)
sc = {}
for t in ("r7", "r8"):
    G = u8(os.path.join(P2, f"graded/default-scene-{t}-set-B-graded-v3c.png"))[..., :3]
    dL = Lstar(G) - Lb
    sc[t] = dict(marks_dL_min=round(float(dL[marks].min()), 2), marks_dL_median=round(float(np.median(dL[marks])), 2),
                 marks_dL_p1=round(float(np.percentile(dL[marks], 1)), 2), gap_dL_min=round(float(dL[gap].min()), 2),
                 gap_px_below_minus1=int((dL[gap] < -1).sum()), gap_px_below_minus0_5=int((dL[gap] < -0.5).sum()),
                 fade_dL_min=round(float(dL[fade].min()), 2) if fade.any() else None, fade_px_below_minus1=int((dL[fade] < -1).sum()))
res["scene_set_B_vs_base_on_marks"] = sc

# overlays: the field at x4 (r7 | r8 | own fields + marks), and the scene crop at x4
x0, y0, x1, y1 = 1640, 1220, 1830, 1300


def field_img(d):
    v = np.clip(255 - d[y0:y1, x0:x1] * 3, 0, 255).astype(np.uint8)
    rgb = np.dstack([v, v, v])
    al = a7u[y0:y1, x0:x1] > 0
    rgb[al] = (rgb[al] * 0.4 + np.array([60, 110, 200]) * 0.6).astype(np.uint8)
    return rgb


lab_img = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8)
lab_img[ownA[y0:y1, x0:x1]] = (90, 170, 90)
lab_img[ownB[y0:y1, x0:x1]] = (60, 140, 200)
lab_img[marks[y0:y1, x0:x1]] = (220, 80, 60)
lab_img[(ch_u & ~marks)[y0:y1, x0:x1]] = (0, 0, 0)
lab_img[(a7u > 0)[y0:y1, x0:x1]] = (200, 200, 200)
row = np.concatenate([field_img(d7), np.full((y1 - y0, 4, 3), 0, np.uint8), field_img(d8), np.full((y1 - y0, 4, 3), 0, np.uint8), lab_img], 1)
Image.fromarray(row).resize((row.shape[1] * 4, row.shape[0] * 4), Image.NEAREST).save(os.path.join(OUT, "overlays/holders-field-r7-r8-own-marks-x4.png"))
crops = []
for t in ("r7", "r8"):
    G = u8(os.path.join(P2, f"graded/default-scene-{t}-set-B-graded-v3c.png"))[..., :3]
    crops.append(G[y0:y1, x0:x1])
    crops.append(np.zeros((y1 - y0, 4, 3), np.uint8))
crops.append(base[y0:y1, x0:x1])
row = np.concatenate(crops, 1)
Image.fromarray(row).resize((row.shape[1] * 4, row.shape[0] * 4), Image.LANCZOS).save(os.path.join(OUT, "overlays/holders-scene-r7-r8-base-x4.png"))
json.dump(res, open(os.path.join(OUT, "data/holders.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
