#!/usr/bin/env python3
"""
mb1_fix.py: the MB1 fix round (qa/reports/2026-11-07-ged-master-mb1.md, coordinator 2026-11-07), render-agent.
Order (coordinator): 1. code fixes (0 tokens), then 2. the SPEND1 passes (seedream-5-pro on crops, masked back in code).

  code-nordic   nordic-MB-A.png -> raw/nordic-MB-A-code.png
                  sconces x0.68 about their centres on the panelling (the boards rebuilt per column, the sconce's own shadow / glow
                  kept as a smoothed ratio to the clean boards and scaled with it), the left one dimmed (glow off, the shade's
                  emission lowered); the seagrass planter recoloured (hue 90, L* 50, the weave kept); the chair cloth recoloured to a
                  sage-grey linen (provisional, the designer picks; one parameter, CLOTH_TARGET)
  code-wm       warm-modern-MB-A.png -> raw/warm-modern-MB-A-code.png
                  sconces x0.8 about the walnut plate's centre on the plaster (the plaster rebuilt by inpainting plus grain, the glow /
                  shadow ratio scaled with the lamp); the olive sprig under the left lamp protected
  pass-input K  writes the crop of the code-fixed frame for pass K (raw/<K>-input.png)
  pass-comp K   the 2K result scaled to the crop, registered (ECC affine) away from the edit, colour-matched on a ring, masked
                  (hand region, the result's difference over a threshold, closed / filled / grown, minus protected areas), composited
  final         chains the passes onto the code-fixed frames -> nordic-MB-A-fix1.png, warm-modern-MB-A-fix1.png; px checks
  crops / sheet before/after crops (fix1-before-after/) and the updated sheet
record: mb1-fix.json
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
REC = os.path.join(HERE, "mb1-fix.json")
CROPS = os.path.join(HERE, "fix1-before-after")
NB, NC, NF = "nordic/nordic-MB-A.png", "nordic/raw/nordic-MB-A-code.png", "nordic/nordic-MB-A-fix1.png"
WB, WC, WF = "warm-modern/warm-modern-MB-A.png", "warm-modern/raw/warm-modern-MB-A-code.png", "warm-modern/warm-modern-MB-A-fix1.png"


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def load(p):
    return np.asarray(Image.open(os.path.join(HERE, p)).convert("RGB")).astype(np.float32) / 255


def save(a, p):
    o8 = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(HERE, p))
    return o8


def rec():
    return json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent", source="qa/reports/2026-11-07-ged-master-mb1.md (+ .json)",
                                                                 note="TEST, not for the site; new files only", code={}, passes={})


def poly(shape, pts):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


def lab(a):
    return cv2.cvtColor(np.ascontiguousarray(a.astype(np.float32)), cv2.COLOR_RGB2Lab)


def rgb(lb):
    return cv2.cvtColor(np.ascontiguousarray(lb.astype(np.float32)), cv2.COLOR_Lab2RGB)


def med_lab(a, m):
    v = np.median(lab(a)[m], 0)
    return [round(float(x), 2) for x in v] + [round(float(np.hypot(v[1], v[2])), 2), round(float(np.degrees(np.arctan2(v[2], v[1])) % 360), 1)]


# ---------------------------------------------------------------- lamps
def cylinders(specs, sag=3):
    """outline polygons of side-by-side vertical cylinders: (x_left, x_right, y_top_mid, y_bottom_mid); rims as shallow arcs"""
    out = []
    for xl, xr, yt, yb in specs:
        xs = np.linspace(xl, xr, 12)
        u = (xs - (xl + xr) / 2) / ((xr - xl) / 2)
        top = [(float(x), float(yt + sag * v * v)) for x, v in zip(xs, u)]
        bot = [(float(x), float(yb - sag * v * v)) for x, v in zip(xs[::-1], u[::-1])]
        out.append(top + bot)
    return out


def scale_lamp(img, body_poly, ring, centre, s, fill="boards", dim=False, protect=None, body_thr=0.035, exact=False):
    """img: sRGB float frame (modified copy returned). body_poly: rough outline of the lamp body; ring: (x0, y0, x1, y1) box holding the
    lamp's shadow / glow, clean wall on its edges; centre: the fixed point; s: scale."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = ring
    sub = img[y0:y1, x0:x1]
    lin = s2l(sub)
    h, w = sub.shape[:2]
    polys = body_poly if isinstance(body_poly[0][0], (tuple, list)) else [body_poly]
    rough = np.zeros(img.shape[:2], bool)
    for p_ in polys:
        rough |= poly(img.shape, p_)
    rough = rough[y0:y1, x0:x1]
    prot = np.zeros((h, w), bool) if protect is None else protect[y0:y1, x0:x1]
    # the clean wall B (linear)
    if fill == "boards":                           # vertical boards: per column, linear between the ring's top and bottom bands
        top = np.median(lin[0:4], 0)
        bot = np.median(lin[h - 4:h], 0)
        t = np.linspace(0, 1, h)[:, None, None]
        B = top[None] * (1 - t) + bot[None] * t
    else:                                          # plaster: B = a smooth wall from the ring's border (inpainted, quarter size, blurred);
        inner = np.zeros((h, w), np.uint8)         # Bh = the lamp's hole filled (half-size Telea + grain), the plaster under the lamp
        inner[6:-6, 6:-6] = 1
        q4 = cv2.resize((sub * 255).astype(np.uint8), (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        i4 = cv2.resize(inner, (w // 4, h // 4), interpolation=cv2.INTER_NEAREST)
        f4 = cv2.inpaint(q4, i4, 9, cv2.INPAINT_TELEA)
        Bsm = cv2.GaussianBlur(cv2.resize(f4, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255, (0, 0), 6)
        Bsm = np.where(inner[..., None] > 0, Bsm, sub)
        B = s2l(np.clip(cv2.GaussianBlur(Bsm, (0, 0), 3), 0, 1))
        hole = cv2.dilate(rough.astype(np.uint8), np.ones((15, 15), np.uint8))
        small = cv2.resize((sub * 255).astype(np.uint8), (w // 2, h // 2), interpolation=cv2.INTER_AREA)
        hs = cv2.dilate(cv2.resize(hole, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        fs = cv2.inpaint(small, hs, 7, cv2.INPAINT_TELEA)
        fl = cv2.GaussianBlur(cv2.resize(fs, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255, (0, 0), 3)
        hp = sub - cv2.GaussianBlur(sub, (0, 0), 2)
        sd = float(np.std(hp[~cv2.dilate(hole, np.ones((9, 9), np.uint8)).astype(bool)]))
        rng = np.random.default_rng(7)
        grain = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.8)
        grain = grain / max(float(grain.std()), 1e-6) * sd
        Bh = s2l(np.clip(np.where(hole[..., None] > 0, fl + grain[..., None], sub), 0, 1))
    # the body: inside the rough outline, the pixels that differ from the clean wall (closed, filled)
    d = np.abs(l2s(lin) - l2s(B)).max(2)
    body = (rough & (cv2.GaussianBlur(d, (0, 0), 1.5) > body_thr)).astype(np.uint8)
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    ff = body.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    body = (body | (1 - ff)) & rough
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    if exact:                                      # the outline is the body (the glow on the boards would read as body otherwise)
        body = rough.copy()
    # the ratio Q (shadow < 1, glow > 1), smoothed, its body area inpainted
    Q = lin / np.maximum(B, 1e-4)
    Q = np.clip(Q, 0.2, 3.0)
    bm = cv2.dilate(body.astype(np.uint8), np.ones((5, 5), np.uint8))
    Qf = np.stack([cv2.inpaint(Q[..., c].astype(np.float32), bm, 5, cv2.INPAINT_TELEA) for c in range(3)], 2)
    Qsm = cv2.GaussianBlur(Qf, (0, 0), 0.8 if fill == "boards" else 3.0)   # boards: the sun shadow's edge is crisp
    if dim:
        Qsm = np.minimum(Qsm, 1.0)
    # scale about the centre (in ring coordinates)
    cx, cy = centre[0] - x0, centre[1] - y0
    M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
    pad = 40
    Qp = cv2.copyMakeBorder(Qsm, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(1.0, 1.0, 1.0))
    Mp = np.float32([[s, 0, (cx + pad) * (1 - s)], [0, s, (cy + pad) * (1 - s)]])
    Qs = cv2.warpAffine(Qp, Mp, (w + 2 * pad, h + 2 * pad), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1, 1, 1))[pad:-pad, pad:-pad]
    if fill == "boards":                           # the whole ring rebuilt: clean boards x the scaled shadow / glow, plus the paint's grain
        hp = l2s(lin) - cv2.GaussianBlur(l2s(lin), (0, 0), 1.5)
        flat = (np.abs(Qf.mean(2) - 1) < 0.05) & ~cv2.dilate(body.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        sd = float(1.4826 * np.median(np.abs(hp[flat])))                         # robust: the paint's grain, not the grooves
        rng = np.random.default_rng(11)
        gr = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.7)
        gr = gr / max(float(gr.std()), 1e-6) * sd
        wall = s2l(np.clip(l2s(B * Qs) + gr[..., None], 0, 1))
    else:
        wall = np.where(body[..., None], Bh, lin) * Qs / np.maximum(Qsm, 1e-4)
    # the lamp body, scaled (pre-blurred against aliasing)
    blin = lin.copy()
    if dim:
        Lb = lab(l2s(blin))
        Y = Lb[..., 0]
        Lb[..., 0] = Y * 0.94
        Lb[..., 1] *= 0.7
        Lb[..., 2] = Lb[..., 2] * 0.7 + 2.5
        Cd = np.hypot(Lb[..., 1], Lb[..., 2])
        k = np.minimum(1.0, 14.0 / np.maximum(Cd, 1e-3))                       # no saturated specks at the shade's lit edge
        Lb[..., 1] *= k
        Lb[..., 2] *= k
        blin = s2l(np.clip(rgb(Lb), 0, 1))
    a = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 0.7)
    pre = cv2.GaussianBlur(blin * a[..., None], (0, 0), 0.5 / s)
    pa = cv2.GaussianBlur(a, (0, 0), 0.5 / s)
    bs = cv2.warpAffine(pre, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    as_ = cv2.warpAffine(pa, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)[..., None]
    col = bs / np.maximum(as_, 1e-4)
    outl = col * as_ + wall * (1 - as_)
    out_sub = l2s(np.clip(outl, 0, 1))
    # feather into the untouched frame over the ring's outer 12 px (no seam where the scaled ratio meets the edge)
    fe = np.ones((h, w), np.float32)
    rmp = np.clip(np.minimum.reduce([np.arange(w)[None, :].repeat(h, 0), (w - 1 - np.arange(w))[None, :].repeat(h, 0),
                                     np.arange(h)[:, None].repeat(w, 1), (h - 1 - np.arange(h))[:, None].repeat(w, 1)]) / 12.0, 0, 1)
    fe = (0.5 - 0.5 * np.cos(np.pi * rmp)).astype(np.float32)
    out_sub = sub + (out_sub - sub) * fe[..., None]
    out_sub = np.where(prot[..., None], sub, out_sub)
    out = img.copy()
    out[y0:y1, x0:x1] = out_sub
    region = np.zeros((H, W), bool)
    region[y0:y1, x0:x1] = ~prot
    bb = np.argwhere(body)
    return out, region, dict(ring=list(ring), centre=list(centre), scale=s, fill=fill, dim=dim, body_px=int(body.sum()),
                             body_bbox=[int(bb[:, 1].min() + x0), int(bb[:, 0].min() + y0), int(bb[:, 1].max() + x0), int(bb[:, 0].max() + y0)])


def scale_patch(img, outline, centre, s, grow=10, fall=22, protect=None):
    """plaster: the lamp with its wall (glow, plate shadow, plaster) scaled by s about the centre and blended over the frame: weight 1
    over the old lamp outline grown by `grow`, cosine falloff over `fall` px; 0 where the output or its source pixel is protected."""
    H, W = img.shape[:2]
    cx, cy = centre
    M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
    src = img
    if protect is not None:                        # the protected object is taken out of the source (inpainted), so no scaled copy of it
        pm8 = cv2.dilate(protect.astype(np.uint8), np.ones((5, 5), np.uint8))
        src = cv2.inpaint((img * 255 + 0.5).astype(np.uint8), pm8, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255
        src = np.where(pm8[..., None] > 0, src, img)
    pre = cv2.GaussianBlur(src, (0, 0), 0.5 / s)
    sc = cv2.warpAffine(pre, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)   # past the frame edge: the wall column, not a mirrored lamp
    o = poly(img.shape, outline).astype(np.uint8)
    core = cv2.dilate(o, np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    dist = cv2.distanceTransform(1 - core, cv2.DIST_L2, 5)
    wgt = np.where(core > 0, 1.0, np.clip(1 - dist / fall, 0, 1)).astype(np.float32)
    wgt = (0.5 - 0.5 * np.cos(np.pi * wgt)).astype(np.float32)
    if protect is not None:                        # the object itself stays as it is
        soft = cv2.GaussianBlur(cv2.dilate(protect.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)
        wgt = wgt * (1 - np.clip(soft * 1.5, 0, 1)) * ~protect
    out = img * (1 - wgt[..., None]) + sc * wgt[..., None]
    region = wgt > 0
    ys, xs = np.nonzero(region)
    return out, region, dict(method="lamp + its wall scaled about the plate centre, blended (core = outline + %d px, falloff %d px)" % (grow, fall),
                             centre=list(centre), scale=s, region_bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], region_px=int(region.sum()))


# ---------------------------------------------------------------- recolour
def recolour(img, alpha, target, L_shift=None, chroma_keep=0.5, gain=False):
    """alpha: float mask; target: (L, a, b) median in the frame. L: shifted by (tL - median L) (or L_shift), so the weave / folds keep
    their light; hue rotated to the target's, chroma scaled to the target's around the median (the texture's chroma variation x
    chroma_keep)."""
    Lb = lab(img)
    m = alpha > 0.5
    L, A, Bb = Lb[..., 0], Lb[..., 1], Lb[..., 2]
    C = np.hypot(A, Bb)
    hh = np.arctan2(Bb, A)
    mL, mA, mB = (float(np.median(v[m])) for v in (L, A, Bb))
    mC, mh = float(np.hypot(mA, mB)), float(np.arctan2(mB, mA))
    tL, tA, tB = target
    tC, th = float(np.hypot(tA, tB)), float(np.arctan2(tB, tA))
    dL = (tL - mL) if L_shift is None else L_shift
    if gain:                                   # exposure as a linear-light gain: the median to tL, the weave's light ratios kept
        Yf = lambda l_: np.where(l_ > 8, ((l_ + 16) / 116) ** 3, l_ / 903.3)
        Lf = lambda y_: np.where(y_ > 0.008856, 116 * np.cbrt(y_) - 16, 903.3 * y_)
        k = float(Yf(np.array(tL)) / Yf(np.array(mL)))
        nL = Lf(Yf(L) * k)
    else:
        nL = L + dL
    nL = np.where(nL > 88, 88 + (nL - 88) * 0.4, nL)                         # soft shoulder: no clipping in the sun
    nC = np.clip(tC + (C - mC) * chroma_keep * tC / max(mC, 1e-3), 0, None)
    nh = hh + (th - mh)
    out = np.stack([nL, nC * np.cos(nh), nC * np.sin(nh)], 2)
    res = np.clip(rgb(out), 0, 1)
    return img * (1 - alpha[..., None]) + res * alpha[..., None]


# Nordic: the planter (seagrass belly basket) and the chair cloth
PLANTER = [(755, 770), (758, 742), (768, 731), (782, 731), (786, 758), (888, 756), (893, 738), (902, 728), (915, 729), (921, 748), (922, 766),
           (927, 800), (931, 850), (930, 900), (926, 950), (900, 975), (820, 1000), (811, 1000), (811, 822), (806, 817), (755, 815)]
SEAGRASS_H, SEAGRASS_C, SEAGRASS_L = 86.0, 21.0, 50.0       # QA: hue toward 90 (photo 91.6), L* +15; the frame's warm light alone gives h ~81
SEAGRASS_TARGET = (SEAGRASS_L, SEAGRASS_C * np.cos(np.radians(SEAGRASS_H)), SEAGRASS_C * np.sin(np.radians(SEAGRASS_H)))
CLOTH = [[(0, 687), (10, 687), (30, 686), (53, 687), (73, 689), (87, 691), (98, 693), (98, 753), (100, 770), (110, 803), (120, 827), (132, 838),
          (147, 843), (173, 848), (200, 853), (227, 863), (253, 870), (267, 877), (273, 887), (277, 903), (278, 923), (278, 1000), (279, 1067),
          (280, 1117), (300, 1133), (293, 1137), (273, 1140), (250, 1146), (233, 1143), (220, 1133), (207, 1113), (200, 1097), (187, 1087),
          (163, 1092), (157, 1087), (150, 1050), (143, 1010), (140, 1000), (140, 903), (0, 903)],
         [(0, 995), (55, 995), (55, 1075), (40, 1080), (20, 1088), (0, 1090)]]
WOOD = [[(0, 813), (95, 813), (97, 820), (96, 832), (0, 834)],                                 # the arm in front of the cloth
        [(51, 832), (89, 832), (91, 1160), (57, 1160)]]                                         # the front leg
CLOTH_TARGET = (46.0, -1.32, 9.41)         # muted sage-grey linen (h 98, C 9.5) (Bible accent #A7B09A) in the frame's morning light; PROVISIONAL, the designer picks


def code_nordic():
    img = load(NB)
    H, W = img.shape[:2]
    R = rec()
    out = img.copy()
    regions = np.zeros((H, W), bool)
    info = {}
    # sconces x0.68; the left one dimmed
    out, rg, info["sconce_left"] = scale_lamp(out, cylinders([(1387, 1421, 411, 522), (1420, 1460, 408, 521), (1459, 1506, 407, 519)]),
                                              (1366, 396, 1572, 572), (1447, 467), 0.68, fill="boards", dim=True, exact=True)
    regions |= rg
    out, rg, info["sconce_right"] = scale_lamp(out, cylinders([(2458, 2525, 325, 501), (2524, 2597, 319, 498), (2596, 2673, 314, 494)]),
                                               (2436, 304, 2730, 566), (2566, 407), 0.68, fill="boards", exact=True)
    regions |= rg
    # planter recolour: inside the outline, everything but the wall / curtain seen through the handles and past the rim, and the trunk
    Lb = lab(img)
    C = np.hypot(Lb[..., 1], Lb[..., 2])
    P = poly(img.shape, PLANTER)
    opening = np.zeros((H, W), bool)
    opening[758:790, 786:900] = True
    trunk = opening & (Lb[..., 0] < 24) & (C < 19)
    trunk |= poly(img.shape, [(829, 700), (850, 700), (850, 790), (829, 790)]) & (Lb[..., 0] < 30) & (C < 21)
    bg = (C < 21.0) & (Lb[..., 0] > 25)                                                   # wall, curtain: lighter and greyer than the weave
    pm = P & ~bg & ~trunk
    pm = cv2.morphologyEx(pm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(pm)
    pm = np.isin(lb_, [i for i in range(1, n_) if st_[i, cv2.CC_STAT_AREA] > 40]) & P
    soft = np.clip((C - 19.5) / 3.0, 0, 1)                                                  # anti-aliased against the background
    ap = np.where(pm, np.maximum(soft, (Lb[..., 0] <= 25).astype(np.float32)), 0).astype(np.float32)
    ap = cv2.GaussianBlur(ap, (0, 0), 0.6) * P * ~trunk
    before_p = med_lab(img, pm)
    out = recolour(out, ap, SEAGRASS_TARGET, chroma_keep=0.6, gain=True)
    info["planter"] = dict(mask_px=int(pm.sum()), Lab_C_h_before=before_p, Lab_C_h_after=med_lab(out, pm),
                           target=dict(L=SEAGRASS_L, C=SEAGRASS_C, h=SEAGRASS_H, method="linear-light gain to L* 50 (the weave's light ratios kept), hue rotated, chroma to 21 (texture chroma x0.6)",
                                       why="QA: hue toward 90 (photo 91.6), L* up about 15; the frame's warm light alone would give h ~81 (von Kries on the white panelling), so 86 sits between"))
    regions |= ap > 0
    # chair cloth recolour
    cm = np.zeros((H, W), bool)
    for p in CLOTH:
        cm |= poly(img.shape, p)
    for p in WOOD:
        cm &= ~poly(img.shape, p)
    cm &= ~((Lb[..., 0] < 18))                                                          # the chair's dark post / joints
    cm = cv2.morphologyEx(cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    ac = cv2.GaussianBlur(cv2.erode(cm.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32), (0, 0), 0.8)
    before_c = med_lab(img, cm)
    out = recolour(out, ac, CLOTH_TARGET, chroma_keep=0.5)
    info["chair_cloth"] = dict(mask_px=int(cm.sum()), Lab_C_h_before=before_c, Lab_C_h_after=med_lab(out, cm),
                               target="muted sage-grey linen: the hue of the Bible accent #A7B09A in the frame's morning light (h 98 by von Kries on the white panelling; full chroma 14 read as mint, so C 9.5), L* 46; PROVISIONAL: the designer picks the colour (QA G-ED.6); one parameter (CLOTH_TARGET)")
    regions |= ac > 0
    o8 = save(out, NC)
    b8 = (img * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    np.save(os.path.join(HERE, "nordic/raw/code-region.npy"), regions)
    info.update(out=NC, px_changed=int(moved.sum()), px_changed_outside_regions=int((moved & ~regions).sum()))
    R["code"]["nordic"] = info
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1))


def code_wm():
    img = load(WB)
    H, W = img.shape[:2]
    R = rec()
    out = img.copy()
    regions = np.zeros((H, W), bool)
    info = {}
    sprig = np.zeros((H, W), bool)
    sprig[600:640, 1240:1310] = True                                                    # the bottle's olive sprig under the left lamp
    Lb = lab(img)
    sprig &= Lb[..., 0] < 45
    sprig = cv2.dilate(sprig.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    out, rg, info["sconce_left"] = scale_patch(out, [(1216, 418), (1318, 418), (1318, 470), (1333, 572), (1190, 572), (1218, 480)], (1267, 468), 0.8,
                                               protect=sprig)
    regions |= rg
    out, rg, info["sconce_right"] = scale_patch(out, [(2592, 426), (2696, 426), (2696, 480), (2724, 573), (2598, 573), (2610, 500)], (2643, 477), 0.8)
    regions |= rg
    o8 = save(out, WC)
    b8 = (img * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    np.save(os.path.join(HERE, "warm-modern/raw/code-region.npy"), regions)
    info.update(out=WC, px_changed=int(moved.sum()), px_changed_outside_regions=int((moved & ~regions).sum()), protected_sprig_px=int(sprig.sum()))
    R["code"]["warm_modern"] = info
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1))


# ---------------------------------------------------------------- SPEND1 passes
PASSES = {
    "P1": dict(frame="nordic", crop=(870, 580, 2570, 1536), prompt="P1-nordic-throw.txt",
               region=[[(900, 1536), (905, 1300), (960, 1180), (1150, 1110), (1500, 1080), (1900, 1075), (2250, 1090), (2470, 1120), (2530, 1190), (2545, 1536)]],
               protect=[], thr=0.035, grow=6),
    "P2": dict(frame="nordic", crop=(2316, 500, 2736, 1060), prompt="P2-nordic-nightstand.txt",
               region=[[(2440, 565), (2736, 565), (2736, 1002), (2440, 1002)]],
               protect=[], protect_mug=(2378, 884, 2503, 984), tone="two_field", table_y=955, whole=True, thr=0.04, grow=5,
               objects=[(2440, 565, 2575, 960), (2540, 740, 2725, 995)], exclude=[(2316, 500, 2440, 1060)]),
    "P3": dict(frame="nordic", crop=(140, 330, 600, 790), prompt="P3-nordic-sill-vase.txt",
               region=[[(303, 573), (437, 573), (437, 737), (303, 737)]],
               protect=[], protect_dark_above=605, thr=0.04, grow=5),
    "P4": dict(frame="warm_modern", crop=(1000, 500, 1420, 1060), prompt="P4-wm-nightstand.txt",
               region=[[(1070, 600), (1342, 600), (1342, 948), (1070, 948)]],
               protect=[], tone="two_field", table_y=930, whole=True, thr=0.04, grow=5,
               objects=[(1078, 605, 1338, 945)], exclude=[(1180, 500, 1340, 560), (1375, 500, 1420, 1060)]),
}
FR = {"nordic": (NC, NF, "nordic"), "warm_modern": (WC, WF, "warm-modern")}


def pass_input(k):
    J = PASSES[k]
    src, _, d = FR[J["frame"]]
    x0, y0, x1, y1 = J["crop"]
    Image.open(os.path.join(HERE, src)).convert("RGB").crop((x0, y0, x1, y1)).save(os.path.join(HERE, d, "raw", f"{k}-input.png"))
    print(k, "crop", J["crop"], (x1 - x0, y1 - y0))


def register(res, org, keep):
    g1 = cv2.GaussianBlur(cv2.cvtColor((org * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    g2 = cv2.GaussianBlur(cv2.cvtColor((res * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255, (0, 0), 1.5)
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(g1, g2, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), keep.astype(np.uint8), 5)
    except cv2.error:
        pass
    h, w = org.shape[:2]
    return cv2.warpAffine(res, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT), M


def pass_apply(k, frame_img):
    """composite pass k's result into frame_img (sRGB float, full frame); returns the new frame, the mask (bool) and a record"""
    J = PASSES[k]
    _, _, d = FR[J["frame"]]
    H, W = frame_img.shape[:2]
    x0, y0, x1, y1 = J["crop"]
    org = frame_img[y0:y1, x0:x1]
    h, w = org.shape[:2]
    resfull = load(os.path.join(d, "raw", f"{k}-seedream.png"))
    res = cv2.resize(resfull, (w, h), interpolation=cv2.INTER_AREA)
    region = np.zeros((H, W), bool)
    for p_ in J["region"]:
        region |= poly(frame_img.shape, p_)
    protect = np.zeros((H, W), bool)
    for p_ in J["protect"]:
        protect |= poly(frame_img.shape, p_)
    if J.get("protect_mug"):                       # the dark stoneware mug (body + handle), from the frame itself
        mx0, my0, mx1, my1 = J["protect_mug"]
        Lb_ = lab(frame_img)
        Lf, Cf = Lb_[..., 0], np.hypot(Lb_[..., 1], Lb_[..., 2])
        mm = np.zeros((H, W), np.uint8)
        mm[my0:my1, mx0:mx1] = ((Cf[my0:my1, mx0:mx1] < 11) & (Lf[my0:my1, mx0:mx1] < 60)).astype(np.uint8)   # grey stoneware, not the brown bottle
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n_, lb_, st_, _ = cv2.connectedComponentsWithStats(mm)
        mm = np.isin(lb_, [i for i in range(1, n_) if st_[i, cv2.CC_STAT_AREA] > 200]).astype(np.uint8)
        ff_ = mm.copy()
        cv2.floodFill(ff_, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
        protect |= cv2.dilate(mm | (1 - ff_), np.ones((3, 3), np.uint8)).astype(bool)
    if J.get("protect_dark_above"):
        Lf = lab(frame_img)[..., 0]
        yy = np.arange(H)[:, None].repeat(W, 1)
        protect |= region & (Lf < 50) & (yy < J["protect_dark_above"])
    reg_c, prot_c = region[y0:y1, x0:x1], protect[y0:y1, x0:x1]
    keep = ~cv2.dilate(reg_c.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    regd, M = register(res, org, keep)
    ring = cv2.dilate(reg_c.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool) & ~reg_c
    lo, lr = s2l(org), s2l(regd)
    gain = np.array([np.median(lo[..., c][ring]) / max(np.median(lr[..., c][ring]), 1e-5) for c in range(3)], np.float32)
    gain = np.clip(gain, 0.8, 1.25)
    lr = lr * gain
    field = np.ones_like(lr)
    if J.get("tone") == "two_field":
        # tone match for a re-lit crop: a smooth quadratic gain field (per channel, in log ratio) fitted on the wall pixels that are wall in
        # both images (outside the hand-set object boxes, old and new, and the excluded boxes), applied to the wall and the new objects;
        # a constant gain from the table pixels for the table
        yy, xx = np.mgrid[0:h, 0:w]
        X, Y = (xx + x0).astype(np.float32), (yy + y0).astype(np.float32)
        def boxes(bl):
            m_ = np.zeros((h, w), bool)
            for bx0, by0, bx1, by1 in bl:
                m_[max(by0 - y0, 0):max(by1 - y0, 0), max(bx0 - x0, 0):max(bx1 - x0, 0)] = True
            return m_
        objs = boxes(J["objects"])
        excl = boxes(J.get("exclude", [])) | prot_c
        table = Y >= J["table_y"]
        Kw = ~objs & ~excl & ~table
        Kt = ~objs & ~excl & table
        xn, yn = (X - X.mean()) / w, (Y - Y.mean()) / h
        A_ = np.stack([np.ones_like(xn), xn, yn, xn * xn, xn * yn, yn * yn], -1)
        field = np.ones_like(lr)
        fit = {}
        for c in range(3):
            r_ = np.log(np.maximum(lo[..., c], 1e-4) / np.maximum(lr[..., c], 1e-4))
            idx = np.flatnonzero(Kw.ravel())[::7]
            coef, *_ = np.linalg.lstsq(A_.reshape(-1, 6)[idx], r_.ravel()[idx], rcond=None)
            fw_c = np.exp(np.clip(A_ @ coef, -1.2, 1.2))
            tc = float(np.exp(np.median(r_[Kt]))) if Kt.sum() > 200 else float(np.exp(np.median(r_[Kw])))
            field[..., c] = np.where(table & ~objs, tc, fw_c)
            fit[c] = (np.round(coef, 4).tolist(), round(tc, 4))
        field = cv2.GaussianBlur(field, (0, 0), 2.0)                # soften the wall / table step at the table's back edge
        lr = lr * field
    dd = cv2.GaussianBlur(np.abs(l2s(lr) - org).max(2), (0, 0), 3)
    m = (dd > J["thr"]) & reg_c
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    big = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 300:
            big[lb == i] = 1
    ff = big.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    filled = big | (1 - ff)
    g = int(J["grow"]) * 2 + 1
    m = cv2.dilate(filled, np.ones((g, g), np.uint8)).astype(bool) & reg_c & ~prot_c
    if J.get("whole"):                             # tone-matched result over the whole region (old and new objects overlap in colour,
        m = reg_c & ~prot_c                        # so a difference mask would keep pieces of the old object)
    rd = cv2.distanceTransform(reg_c.astype(np.uint8), cv2.DIST_L2, 5)
    edge = np.clip(rd / J.get("edge_feather", 14.0), 0, 1)
    edge = 0.5 - 0.5 * np.cos(np.pi * edge)
    a = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.5) * reg_c * ~prot_c * edge)[..., None]
    comp = l2s(lo * (1 - a) + lr * a)
    comp = np.where(a > 0, comp, org)              # no sRGB round trip outside the mask
    out = frame_img.copy()
    out[y0:y1, x0:x1] = np.clip(comp, 0, 1)
    mk = np.zeros((H, W), bool)
    mk[y0:y1, x0:x1] = a[..., 0] > 0.002
    Image.fromarray(mk.astype(np.uint8) * 255).save(os.path.join(HERE, d, "raw", f"{k}-mask.png"))
    return out, mk, region & ~protect, dict(crop=list(J["crop"]), result_px=list(resfull.shape[1::-1]), ecc_affine=np.round(M, 4).tolist(),
                                            colour_gain_linear=np.round(gain, 4).tolist(), local_gain_field_median=np.round(np.median(field[reg_c], 0), 4).tolist(), tone=J.get("tone", "global"),
                                            mask_px=int(mk.sum()))


def final():
    R = rec()
    for fr, ks in (("nordic", ["P1", "P2", "P3"]), ("warm_modern", ["P4"])):
        src, dst, d = FR[fr]
        base = load(src)
        cur = base.copy()
        allowed = np.zeros(base.shape[:2], bool)
        for k in ks:
            if not os.path.exists(os.path.join(HERE, d, "raw", f"{k}-seedream.png")):
                print("no result yet", k)
                continue
            before = cur.copy()
            cur, mk, allowed_k, r = pass_apply(k, cur)
            b8 = (before * 255 + 0.5).astype(np.uint8)
            c8 = (np.clip(cur, 0, 1) * 255 + 0.5).astype(np.uint8)
            moved = np.abs(c8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
            r.update(px_changed=int(moved.sum()), px_changed_outside_region=int((moved & ~allowed_k).sum()))
            R["passes"].setdefault(k, {}).update(r)
            allowed |= allowed_k
            cur = c8.astype(np.float32) / 255
        o8 = save(cur, dst)
        orig = np.asarray(Image.open(os.path.join(HERE, d, f"{d}-MB-A.png")).convert("RGB"))
        code8 = (base * 255 + 0.5).astype(np.uint8)
        code_reg = np.load(os.path.join(HERE, d, "raw", "code-region.npy"))
        mv_code = np.abs(code8.astype(np.int16) - orig.astype(np.int16)).max(2) > 0
        mv_all = np.abs(o8.astype(np.int16) - orig.astype(np.int16)).max(2) > 0
        R.setdefault("final", {})[fr] = dict(file=dst, px_changed_vs_MB_A=int(mv_all.sum()),
                                             px_changed_outside_code_and_pass_regions=int((mv_all & ~(code_reg | allowed)).sum()),
                                             code_px_changed_outside_code_regions=int((mv_code & ~code_reg).sum()))
        print(fr, R["final"][fr])
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)


CROPSETS = {
    "nordic": [("sconce-left-x2", (1340, 370, 1590, 590), 2), ("sconce-right-x2", (2400, 260, 2736, 580), 2), ("planter-x2", (620, 690, 980, 1030), 2),
               ("chair-cloth-100", (0, 660, 330, 1160), 1), ("throw-50", (860, 1000, 2600, 1536), 0), ("nightstand-x2", (2316, 500, 2736, 1060), 2),
               ("nightstand-x4", (2440, 800, 2736, 1000), 4), ("sill-vase-x2", (140, 330, 600, 790), 2), ("sill-vase-x4", (290, 560, 450, 740), 4)],
    "warm_modern": [("sconce-left-x2", (1150, 380, 1370, 660), 2), ("sconce-right-x2", (2530, 380, 2736, 640), 2), ("nightstand-x2", (1000, 500, 1420, 1060), 2),
                    ("nightstand-x4", (1060, 700, 1350, 960), 4)],
}


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    R = rec()
    outl = []
    for fr, sets in CROPSETS.items():
        _, dst, d = FR[fr]
        B = Image.open(os.path.join(HERE, d, f"{d}-MB-A.png")).convert("RGB")
        A = Image.open(os.path.join(HERE, dst)).convert("RGB")
        for name, box, sc in sets:
            w, h = box[2] - box[0], box[3] - box[1]
            if sc == 0:
                pb, pa, tag = B.crop(box).resize((w // 2, h // 2), Image.LANCZOS), A.crop(box).resize((w // 2, h // 2), Image.LANCZOS), "50 %"
            else:
                rs = Image.NEAREST if sc > 2 else Image.LANCZOS
                pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
                tag = "100 %" if sc == 1 else f"x{sc}"
            vert = pb.width > 900
            W_ = pb.width + 20 if vert else pb.width * 2 + 30
            H_ = pb.height * 2 + 90 if vert else pb.height + 60
            im = Image.new("RGB", (W_, H_), (250, 249, 247))
            dr = ImageDraw.Draw(im)
            dr.text((10, 5), f"MB1 fix1 {d} {name}: {d}-MB-A.png -> {os.path.basename(dst)}", fill=(0, 0, 0), font=f)
            if vert:
                dr.text((10, 30), f"before {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, 55))
                dr.text((10, 60 + pb.height), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pa, (10, 85 + pb.height))
            else:
                dr.text((10, 30), f"before {tag}", fill=(0, 0, 0), font=f)
                dr.text((20 + pb.width, 30), f"after {tag}", fill=(0, 0, 0), font=f)
                im.paste(pb, (10, 55))
                im.paste(pa, (20 + pb.width, 55))
            pth = os.path.join(CROPS, f"{d}-{name}.jpg")
            im.save(pth, quality=92)
            outl.append(os.path.relpath(pth, HERE))
    R["crops"] = outl
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(len(outl), "crops")


def sheet():
    ROOT = os.path.join(REPO, "assets", "renders")
    cols = [("נורדי", [("master/editorial-2026-11-07/nordic/nordic-MB-A-fix1.png", "חדר שינה הורים · MB-A fix1 (קוד + P1–P3)"),
                       ("master/editorial-2026-11-07/nordic/nordic-MB-A.png", "חדר שינה הורים · MB-A לפני התיקון"),
                       ("master/nordic/v7/mb0-v7-r2-graded-v5.png", "חדר שינה הורים · MB0 v7 הישן"),
                       ("editorial-phase-b-2026-11-06/nordic-A-fin2.png", "סלון · נורדי A (fin2)")]),
            ("מודרני חם", [("master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix1.png", "חדר שינה הורים · MB-A fix1 (קוד + P4)"),
                           ("master/editorial-2026-11-07/warm-modern/warm-modern-MB-A.png", "חדר שינה הורים · MB-A לפני התיקון"),
                           ("editorial-phase-b-2026-11-06/warm-modern-A-ed8.png", "סלון · מודרני חם A (ed8, CAM1)"),
                           (None, "")])]
    TW, TH, PAD, LAB, HEAD = 1280, 720, 24, 46, 70
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    rtl = (lambda t: t) if features.check("raqm") else (lambda t: t[::-1])
    W_ = PAD + 2 * (TW + PAD)
    H_ = HEAD + 4 * (TH + LAB + PAD) + PAD
    sh = Image.new("RGB", (W_, H_), (246, 244, 240))
    dr = ImageDraw.Draw(sh)
    for ci, (title, items) in enumerate(cols[::-1]):                 # right to left: Nordic on the right
        x = PAD + ci * (TW + PAD)
        dr.text((x + TW, 18), rtl(title), font=fb, fill=(30, 30, 30), anchor="ra")
        for ri, (fn, lab_) in enumerate(items):
            y = HEAD + ri * (TH + LAB + PAD)
            if fn is None:
                lines = ["MB1 fix1 · 2026-11-07 · לפני סבב QA שני", "קוד: 0 טוקנים · מעברים: 4 × 650 = 2,600 (SPEND1)",
                         "הבד על הכורסה: מרווה-אפור, זמני (המעצב בוחר)"]
                for i, t in enumerate(lines):
                    dr.text((x + TW, y + 40 + i * 44), rtl(t), font=f, fill=(70, 70, 70), anchor="ra")
                continue
            im = Image.open(os.path.join(ROOT, fn)).convert("RGB")
            sc = min(TW / im.width, TH / im.height)
            im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
            sh.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
            dr.text((x + TW, y + TH + 10), rtl(lab_), font=f, fill=(50, 50, 50), anchor="ra")
    out = os.path.join(HERE, "sheet-fix1.jpg")
    sh.save(out, quality=88)
    R = rec()
    R["sheet"] = os.path.relpath(out, HERE)
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(out, sh.size)


if __name__ == "__main__":
    {"code-nordic": code_nordic, "code-wm": code_wm, "pass-input": pass_input, "final": final, "crops": crops, "sheet": sheet}[sys.argv[1]](*sys.argv[2:])
