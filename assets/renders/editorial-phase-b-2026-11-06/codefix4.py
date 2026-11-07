#!/usr/bin/env python3
"""
codefix4.py: two zero-token code fixes from master-designer (docs/proposals/tool-shells-and-qa-items-2026-11-07.md, rows 46-47),
render-agent, 2026-11-07. No var2. New files only; each fix inside its own mask, 0 px changed outside (counted in codefix4.json).
  rug      modern-country-A-fix1 -> modern-country-A-fix2: inside the rug only, the pattern's contrast ~60 % lower and its saturation
           ~40 % lower (a faded rug in close tones); the shadows and the light on it kept (an edge-preserving base carries them)
  basket   boho-A-fin3 -> boho-A-fin4: the seagrass basket alone x0.75 about its floor contact point (the planter and plant untouched),
           the wall, the door and the floor behind it rebuilt, a contact shadow for the new size; basket / planter ~0.84 as the cards
  crops    codefix4-before-after/
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01  # noqa: E402
from fin2_codefix import nblur, harmonic  # noqa: E402
from codefix3 import save8, lab_of, lab_f, rgb_f, check, poly_mask  # noqa: E402

REC = os.path.join(HERE, "codefix4.json")
CROPS = os.path.join(HERE, "codefix4-before-after")


# ----------------------------------------------------------------------------------------------------------------------------------
def rug():
    src = os.path.join(HERE, "modern-country-A-fix1.png")
    a = load01(src)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    # the rug: from its back edge (read per column, the strongest step in y 1393-1440, smoothed) to the frame's bottom, x 300 on
    Lb = cv2.GaussianBlur(L, (0, 0), 1.5)
    top = np.full(W, 1412.0)
    for x in range(300, W):
        g = np.abs(np.diff(Lb[1393:1440, x]))
        top[x] = 1393 + int(np.argmax(g)) + 1
    top[300:] = np.convolve(np.r_[[top[300]] * 25, top[300:], [top[-1]] * 25], np.ones(51) / 51, mode="same")[25:-25]
    rugm = (xx >= 300) & (yy >= top[None, :] + 2)
    # out: the runner and its tassels, the table and armchair legs (warm dark wood), the doorway on the left
    runner = poly_mask(a.shape, [(1124, 1250), (1609, 1250), (1609, 1508), (1124, 1508)])
    wood = (L < 52) & (B_ > 24) & (A_ > 9)
    wood = cv2.morphologyEx(wood.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab_, st, _ = cv2.connectedComponentsWithStats(wood)
    legs = np.zeros((H, W), bool)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 300 and st[i, cv2.CC_STAT_HEIGHT] > 30:
            legs |= lab_ == i
    legs = cv2.dilate(legs.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m = rugm & ~runner & ~legs
    lab = lab_f(a)
    Lf = lab[..., 0].astype(np.float32)
    wm = m.astype(np.float32)
    # L*: the light and the shadows on the rug are broad (the table's shadow, the soft legs' shadows): a sigma-8 base over the rug only
    # carries them; the motifs (2-15 px marks) are the detail
    baseL, _ = nblur(Lf, wm, 8)
    baseA, _ = nblur(lab[..., 1], wm, 10)
    baseB, _ = nblur(lab[..., 2], wm, 10)
    PC, SAT = 0.40, 0.60                                                   # pattern contrast x0.4 (-60 %), saturation x0.6 (-40 %)
    newL = baseL + PC * (Lf - baseL)
    na_ = baseA + PC * (lab[..., 1] - baseA)
    nb_ = baseB + PC * (lab[..., 2] - baseB)
    newlab = np.stack([newL, na_ * SAT, nb_ * SAT], -1)
    w = cv2.GaussianBlur(cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2) * m
    out = a * (1 - w[..., None]) + rgb_f(newlab) * w[..., None]
    o8 = save8(out, os.path.join(HERE, "modern-country-A-fix2.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    rec = check(o8, a8, m, "modern-country-A-fix2.png")
    Ls, As, Bs = lab_of(out)
    def pstats(Lx, Ax, Bx):
        d = (Lx - cv2.GaussianBlur(Lx, (0, 0), 10))[m]
        return dict(L_detail_std=round(float(d.std()), 2), chroma_median=round(float(np.median(np.hypot(Ax, Bx)[m])), 1))
    rec.update(base="modern-country-A-fix1.png", rug_top_edge="read per column (y 1393-1440), smoothed over 51 columns", pattern_contrast=PC,
               saturation=SAT, before=pstats(L, A_, B_), after=pstats(Ls, As, Bs),
               method="rug only (the runner and its tassels, the table and armchair legs kept out); L*: a sigma-8 base over the rug "
                      "keeps the broad shadows and the light, the motifs' detail x0.4; a/b: detail about a sigma-10 base x0.4, then chroma x0.6")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
def basket():
    src = os.path.join(HERE, "boho-A-fin3.png")
    a = load01(src)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    yy, xx = np.mgrid[0:H, 0:W]
    AXc, AYc, K = 2149.0, 1068.0, 0.75
    # the basket: seagrass straw is more saturated than the wall (b* 26), the door's stile (28) and panel (31): b* > 33 inside its box,
    # the largest part, the body's holes filled (the handle loops stay open: the wall and the door show through them)
    box = np.zeros((H, W), bool)
    box[760:1075, 2008:2292] = True
    raw = box & (B_ > 33) & (L > 22)
    raw = cv2.morphologyEx(raw.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab_, st, _ = cv2.connectedComponentsWithStats(raw)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    bm = (lab_ == k)
    body = np.zeros((H, W), np.uint8)
    body[870:1075] = bm[870:1075]
    ff = body.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    body = body | (1 - ff)
    bm = bm | body.astype(bool)
    # its shadowed lower rows are darker than the rule: the body's outline per row filled between its first and last pixel (y 880-1070)
    for y in range(880, 1072):
        xs = np.nonzero(bm[y, 2008:2292])[0]
        if xs.size > 10:
            bm[y, 2008 + xs.min():2008 + xs.max() + 1] = True
    alpha = cv2.GaussianBlur(bm.astype(np.float32), (0, 0), 0.7)
    lin = s2l(a)
    Am = np.float32([[K, 0, AXc * (1 - K)], [0, K, AYc * (1 - K)]])
    sc = cv2.warpAffine(lin * alpha[..., None], Am, (W, H), flags=cv2.INTER_AREA)
    sa = np.clip(cv2.warpAffine(alpha, Am, (W, H), flags=cv2.INTER_AREA), 0, 1)
    old = cv2.dilate(bm.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    # what lies behind, by place: the plain wall (x < 2158, above the floor), the door's stile (2158-2212) and panel (x >= 2212), the floor
    floor_y = 1036
    wallr = old & (xx < 2158) & (yy < floor_y)
    stile = old & (xx >= 2158) & (xx < 2212) & (yy < floor_y)
    panel = old & (xx >= 2212) & (yy < floor_y)
    floor = old & (yy >= floor_y)
    bg = lin.copy()
    # the wall: harmonic from the wall round it (the planter, its leaves and the basket kept out), with the wall's own grain level
    planter = (L < 18) | ((A_ < 0) & (B_ > 10))                           # its black base; the green leaves
    planter = cv2.dilate(planter.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    sl = (slice(680, 1060), slice(1990, 2200))
    known = ~old & ~planter & (xx < 2160) & (yy < floor_y)
    wl, den = nblur(lin, known.astype(np.float32), 3)
    kn = (known & (den > 0.3))[sl]
    hw_ = harmonic(np.where(kn[..., None], wl[sl], 0), kn, f=2, iters=3000)
    ref = lin[790:840, 2030:2080]
    sd = float(np.std((ref / np.maximum(cv2.GaussianBlur(ref, (0, 0), 2), 1e-5)).mean(2)))
    rng = np.random.default_rng(41)
    nz = cv2.GaussianBlur(rng.standard_normal(hw_.shape[:2]).astype(np.float32), (0, 0), 0.8)
    nz *= sd / max(float(nz.std()), 1e-6)
    tmp = lin.copy()
    tmp[sl] = hw_ * (1 + nz)[..., None]
    bg = np.where(wallr[..., None], tmp, bg)
    # the stile and the top of the panel: vertical structures, each column mirrored down from just above the old outline
    topy = np.full(W, H, int)
    for x in range(2150, 2292):
        ys = np.nonzero(old[:, x])[0]
        if ys.size:
            topy[x] = ys.min()
    mirror = lin.copy()
    for x in range(2150, 2292):
        t = topy[x]
        if t >= H:
            continue
        for y in range(t, floor_y):
            sy = t - 1 - (y - t)
            if sy < 600:
                break
            mirror[y, x] = lin[sy, x]
    bg = np.where(stile[..., None], mirror, bg)
    # the panel below its top band and the floor: shifted in from beside the basket along the rows (the panel's bottom rail and the
    # floor's tile lines are horizontal): the panel from 36 px right, the floor from 46 px left / right of the axis
    pr = cv2.warpAffine(lin, np.float32([[1, 0, -36], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    band_top = (yy < topy[None, :] + 45)
    bg = np.where((panel & band_top)[..., None], mirror, bg)
    bg = np.where((panel & ~band_top)[..., None], pr, bg)
    fl = cv2.warpAffine(lin, np.float32([[1, 0, 46], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    frr = cv2.warpAffine(lin, np.float32([[1, 0, -46], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REFLECT)
    bg = np.where((floor & (xx < AXc))[..., None], fl, bg)
    bg = np.where((floor & (xx >= AXc))[..., None], frr, bg)
    oa = cv2.GaussianBlur(old.astype(np.float32), (0, 0), 1.2)[..., None] * cv2.dilate(old.astype(np.uint8), np.ones((3, 3), np.uint8))[..., None]
    out = lin * (1 - oa) + bg * oa
    # a contact shadow for the new size (the old one went with the old base)
    fp = np.zeros((H, W), np.uint8)
    nb = np.nonzero(sa[1050:1072] > 0.5)
    half = int((nb[1].max() - nb[1].min()) / 2) if nb[1].size else 70
    cv2.ellipse(fp, (int(AXc), int(AYc) - 2), (half + 2, 5), 0, 0, 360, 1, -1)
    shadow = np.clip(0.55 * cv2.GaussianBlur(fp.astype(np.float32), (0, 0), 2.5)
                     + 0.25 * cv2.GaussianBlur(cv2.warpAffine(fp.astype(np.float32), np.float32([[1, 0, -8], [0, 1, 1]]), (W, H)), (0, 0), 7), 0, 0.7)
    shadow *= (yy >= 1040)
    out = out * (1 - shadow[..., None] * (1 - sa[..., None]))
    out = out * (1 - sa[..., None]) + np.clip(sc / np.maximum(sa[..., None], 1e-4), 0, 1) * sa[..., None]
    o8 = save8(l2s(out), os.path.join(HERE, "boho-A-fin4.png"))
    a8 = (a * 255 + 0.5).astype(np.uint8)
    zone = cv2.dilate((old | (sa > 0) | (shadow > 0.002)).astype(np.uint8), np.ones((5, 5), np.uint8))
    rec = check(o8, a8, zone, "boho-A-fin4.png")
    ys, xs = np.nonzero(bm)
    hb, wb = int(ys.max() - ys.min()), int(xs.max() - xs.min())
    # the planter (its basket part with the black base) read on the frame: x 1823-2022, y 820-1036
    rec.update(base="boho-A-fin3.png", anchor_floor_contact=[AXc, AYc], scale=K, basket_px_before=[wb, hb], basket_px_after=[round(wb * K, 1), round(hb * K, 1)],
               planter_px=[199, 216], ratio_width_after=round(wb * K / 199, 2), card_ratio=round(38 / 45, 2),
               method="the basket by its straw chroma (b* > 33) in its box, the body filled, the handle loops open; x0.75 about the floor "
                      "contact; behind it: the wall harmonic + grain, the stile and the panel's top mirrored down per column, the panel's lower "
                      "part and the floor shifted in along the rows; a contact shadow for the new base")
    return rec


# ----------------------------------------------------------------------------------------------------------------------------------
CROP_SETS = [
    ("mc-rug", "modern-country-A-fix1.png", "modern-country-A-fix2.png", [((300, 1390, 2736, 1536), 1), ((1950, 1420, 2150, 1536), 4),
                                                                        ((500, 1420, 700, 1536), 4)]),
    ("boho-basket", "boho-A-fin3.png", "boho-A-fin4.png", [((1780, 700, 2420, 1120), 1), ((2010, 760, 2300, 1080), 2)]),
]


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    outl = []
    for name, b, a_, boxes in CROP_SETS:
        Bm = Image.open(os.path.join(HERE, b)).convert("RGB")
        Am = Image.open(os.path.join(HERE, a_)).convert("RGB")
        panels = []
        for box, sc in boxes:
            w, h = box[2] - box[0], box[3] - box[1]
            rs = Image.NEAREST if sc > 1 else Image.LANCZOS
            panels.append((Bm.crop(box).resize((w * sc, h * sc), rs), Am.crop(box).resize((w * sc, h * sc), rs), sc))
        wide = any(p[0].width > 1400 for p in panels)
        if wide:   # stack before above after
            Wd = max(p[0].width for p in panels) + 20
            Ht = sum(2 * p[0].height + 60 for p in panels) + 40
        else:
            Wd = max(max(p[0].width for p in panels) * 2 + 30, 700)
            Ht = sum(p[0].height + 30 for p in panels) + 40
        im = Image.new("RGB", (Wd, Ht), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: {b} -> {a_}", fill=(0, 0, 0), font=f)
        y = 35
        for pb, pa, sc in panels:
            tag = "100 %" if sc == 1 else f"x{sc}"
            if wide:
                d.text((10, y), f"before {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, y + 24))
                d.text((10, y + 30 + pb.height), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pa, (10, y + 54 + pb.height))
                y += 2 * pb.height + 60
            else:
                d.text((10, y), f"before {tag}", fill=(0, 0, 0), font=f)
                d.text((20 + pb.width, y), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, y + 24))
                im.paste(pa, (20 + pb.width, y + 24))
                y += pb.height + 30
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    return outl


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent",
                                                              source="docs/proposals/tool-shells-and-qa-items-2026-11-07.md rows 46-47",
                                                              tokens=0, var2="none", note="TEST, not for the site; new files only")
    for k in sys.argv[1:]:
        r = globals()[k]()
        R[k] = r
        print(k, r if isinstance(r, list) else json.dumps({kk: vv for kk, vv in r.items() if "px" in kk or kk in ("file", "ratio_width_after", "before", "after")}))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
