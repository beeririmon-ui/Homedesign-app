#!/usr/bin/env python3
"""
mb1_fix4.py: the SPEND1 week-2 passes (week of 2026-11-08; QA qa/reports/2026-11-08-ged-master-fix1.md, priority order P5, P7, P6, P8;
coordinator 2026-11-10), render-agent. Bases: nordic-MB-A-fix3.png, warm-modern-MB-A-fix2.png (the 0-token fix3 round).

QA's method (b): the model does not choose sizes. The input crop already carries the target sizes: the objects are cut out (hand outline
refined by GrabCut), scaled in code about their base point (sx, sy), the old footprint filled roughly behind them (boards: clean columns x
a vertical gradient x a smooth correction; plaster / fabric / table: Telea), and the pass is asked to keep every object's size and place
as in the input, to repair what is behind and to re-light.

  prep K   the input crop raw/K-input.png, and the old / new object masks raw/K-old.png, raw/K-new.png (frame px)
  comp     every pass with a result: the 2K result scaled to the crop, registered (ECC affine) on the pixels outside the region, a smooth
           quadratic log-gain field fitted on those pixels (per channel) brings the re-lit result back to the frame's light, and the
           region (old footprint + new objects, grown) is replaced, feathered 14 px inward; nothing outside the region changes
           -> nordic-MB-A-fix4.png (fix3 + P5 + P7), warm-modern-MB-A-fix3.png (fix2 + P6 + P8)
  crops / sheet
record: mb1-fix4.json
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
import mb1_fix as F  # noqa: E402

REC = os.path.join(HERE, "mb1-fix4.json")
CROPS = os.path.join(HERE, "fix4-before-after")
FR = {"nordic": ("nordic/nordic-MB-A-fix3.png", "nordic/nordic-MB-A-fix4.png", "nordic"),
      "warm_modern": ("warm-modern/warm-modern-MB-A-fix2.png", "warm-modern/warm-modern-MB-A-fix3.png", "warm-modern")}

# objects: name -> (outline polygon, base point, sx, sy, grabcut band); "candle" entries are stretched to a target height separately
PASSES = {
    "P5": dict(frame="nordic", crop=(1420, 560, 2440, 1000), fill="soft",
               objects={"lumbar": dict(poly=[(1630, 711), (1700, 707), (1800, 711), (1900, 717), (2000, 723), (2044, 729), (2041, 780), (2030, 830),
                                             (2010, 856), (1900, 853), (1800, 851), (1700, 848), (1645, 843), (1633, 790)],
                                       base=(1836, 852), s=(0.72, 0.72), band=6)},
               region=[(1484, 592), (1700, 592), (1940, 588), (2200, 592), (2404, 596), (2416, 700), (2414, 820), (2410, 918), (2200, 922),
                       (2000, 912), (1800, 898), (1600, 892), (1478, 886), (1468, 760), (1472, 650)],
               prompt="P5-nordic-bed-head.txt"),
    "P7": dict(frame="nordic", crop=(2316, 500, 2736, 1060), fill="boards", table_y=956, wall_x0=2440,
               objects={"bottle": dict(poly=[(2497, 740), (2495, 688), (2513, 688), (2514, 740), (2540, 790), (2557, 850), (2563, 948), (2452, 948),
                                             (2453, 860), (2475, 790)], base=(2504, 948), s=(0.70, 0.70), band=5, stem=(2440, 575, 2540, 692)),
                        "mug": dict(poly=[(2417, 892), (2501, 892), (2501, 968), (2490, 979), (2425, 979), (2414, 966), (2414, 950), (2395, 948),
                                          (2383, 935), (2381, 915), (2390, 902), (2414, 900)], base=(2458, 979), s=(0.80, 0.80), band=4),
                        "holder_l": dict(poly=[(2561, 861), (2632, 861), (2634, 897), (2622, 901), (2628, 986), (2566, 986), (2571, 901), (2560, 897)],
                                         base=(2597, 986), s=(0.71, 0.66), band=4,
                                         candle=dict(poly=[(2570, 776), (2623, 776), (2623, 864), (2570, 864)], flame=(2580, 748, 2608, 778),
                                                     target_px=110)),
                        "holder_r": dict(poly=[(2645, 884), (2714, 884), (2716, 918), (2706, 920), (2710, 991), (2648, 991), (2651, 920), (2642, 917)],
                                         base=(2680, 991), s=(0.74, 0.76), band=4,
                                         candle=dict(poly=[(2652, 852), (2703, 852), (2703, 886), (2652, 886)], flame=(2664, 826, 2690, 853),
                                                     target_px=73))},
               prompt="P7-nordic-nightstand-scale.txt"),
    "P6": dict(frame="warm_modern", crop=(1380, 620, 2700, 990), fill="soft",
               objects={"lumbar": dict(poly=[(1800, 790), (1850, 786), (2000, 783), (2150, 781), (2283, 782), (2287, 830), (2292, 920), (2200, 925),
                                             (2050, 926), (1900, 926), (1806, 926), (1800, 860)],
                                       base=(2044, 926), s=(0.74, 0.74), band=6)},
               region=[(1470, 690), (1700, 684), (2000, 680), (2300, 676), (2640, 676), (2652, 800), (2660, 940), (2400, 946), (2100, 946),
                       (1800, 946), (1484, 946), (1462, 820)],
               prompt="P6-wm-bed-head.txt"),
    "P8": dict(frame="warm_modern", crop=(1000, 560, 1420, 1060), fill="plaster", table_y=919,
               objects={"bottle": dict(poly=[(1268, 726), (1279, 726), (1281, 790), (1300, 830), (1318, 880), (1322, 938), (1214, 938), (1217, 880),
                                             (1236, 830), (1263, 790)], base=(1268, 938), s=(0.83, 0.83), band=4, stem=(1228, 620, 1325, 727)),
                        "holder_l": dict(poly=[(1085, 836), (1137, 836), (1137, 861), (1128, 864), (1134, 937), (1088, 937), (1093, 864), (1085, 861)],
                                         base=(1110, 937), cone=dict(cup_bottom=863, target_h=83), band=3),
                        "holder_r": dict(poly=[(1148, 844), (1199, 844), (1199, 869), (1190, 872), (1196, 939), (1151, 939), (1156, 872), (1148, 869)],
                                         base=(1173, 939), cone=dict(cup_bottom=871, target_h=83), band=3)},
               prompt="P8-wm-nightstand-scale.txt"),
}


def rec():
    return json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-10", by="render-agent", source="qa/reports/2026-11-08-ged-master-fix1.md (this week's passes, priority P5, P7, P6, P8); coordinator 2026-11-10",
        spend="SPEND1, the week of Sun 2026-11-08 to Sat 2026-11-14: up to 2,600, 650 max each", note="TEST, not for the site; new files only", passes={})


def refine(img8, poly, band, win):
    H, W = img8.shape[:2]
    p = F.poly(img8.shape, poly).astype(np.uint8)
    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    gc[cv2.dilate(p, np.ones((2 * band + 1,) * 2, np.uint8)) > 0] = cv2.GC_PR_BGD
    gc[p > 0] = cv2.GC_PR_FGD
    gc[cv2.erode(p, np.ones((2 * band + 1,) * 2, np.uint8)) > 0] = cv2.GC_FGD
    x0, y0, x1, y1 = win
    sub = gc[y0:y1, x0:x1].copy()
    cv2.grabCut(np.ascontiguousarray(img8[y0:y1, x0:x1]), sub, None, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_MASK)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = (sub == cv2.GC_FGD) | (sub == cv2.GC_PR_FGD)
    m &= cv2.dilate(p, np.ones((2 * band + 1,) * 2, np.uint8)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n > 1:
        m = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    ff = m.astype(np.uint8)
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    return m | (ff == 0)


def warp(img, alpha, M, shape):
    H, W = shape
    pre = cv2.GaussianBlur(img * alpha[..., None], (0, 0), 0.6)
    pa = cv2.GaussianBlur(alpha, (0, 0), 0.6)
    bs = cv2.warpAffine(pre, M, (W, H), flags=cv2.INTER_LINEAR)
    as_ = cv2.warpAffine(pa, M, (W, H), flags=cv2.INTER_LINEAR)
    return bs, as_


def fill_boards(img, hole, win, table_y, wall_x0=0):
    """wall above table_y: clean column profile (rows above the hole) x the vertical gradient of clean columns, corrected by a smooth
    ratio field from the clean wall round the hole; table below: Telea"""
    x0, y0, x1, y1 = win
    sub = F.s2l(img[y0:y1, x0:x1])
    hz = hole[y0:y1, x0:x1]
    h, w = hz.shape
    ty = table_y - y0
    clean_rows = [r for r in range(0, ty) if not hz[r].any()]
    top = np.median(sub[clean_rows[:12]], 0) if clean_rows else np.median(sub[:6], 0)
    wx = max(wall_x0 - x0, 0)                     # the boards start here (left of it: the headboard wood and the bed)
    cols = [c for c in range(wx, w) if not hz[:ty, c].any()]
    g = np.median(sub[:ty, cols] / np.maximum(top[None, cols], 1e-4), 1) if cols else np.ones((ty, 3), np.float32)
    B = top[None] * g[:, None]
    ok = ~cv2.dilate(hz.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)[:ty]
    r = sub[:ty] / np.maximum(B, 1e-4)
    K = ok.astype(np.float32)
    corr = np.ones_like(B)
    wK = cv2.GaussianBlur(K, (0, 0), 40)
    for c in range(3):
        corr[..., c] = np.where(wK > 0.02, cv2.GaussianBlur(r[..., c] * K, (0, 0), 40) / np.maximum(cv2.GaussianBlur(K, (0, 0), 40), 1e-4), 1.0)
    wall = F.l2s(np.clip(B * corr, 0, 1))
    out = img.copy()
    o = out[y0:y1, x0:x1]
    wz = hz[:ty].copy()
    wz[:, :wx] = False
    o[:ty] = np.where(wz[..., None], wall, o[:ty])
    i8 = (np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8)
    hz2 = hz.copy()
    hz2[:ty, wx:] = False
    if hz2.any():
        t = cv2.inpaint(i8, hz2.astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32) / 255
        o = np.where(hz2[..., None], t, o)
    out[y0:y1, x0:x1] = o
    return out


def fill_soft(img, hole, win, grain=True):
    x0, y0, x1, y1 = win
    i8 = (np.clip(img[y0:y1, x0:x1], 0, 1) * 255 + 0.5).astype(np.uint8)
    hz = hole[y0:y1, x0:x1].astype(np.uint8)
    h, w = hz.shape
    small = cv2.resize(i8, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    hs = cv2.dilate(cv2.resize(hz, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
    t = cv2.inpaint(small, hs, 7, cv2.INPAINT_TELEA)
    t = cv2.GaussianBlur(cv2.resize(t, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255, (0, 0), 2)
    if grain:
        hp = img[y0:y1, x0:x1] - cv2.GaussianBlur(img[y0:y1, x0:x1], (0, 0), 1.5)
        sd = float(1.4826 * np.median(np.abs(hp[hz == 0])))
        rng = np.random.default_rng(9)
        gr = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 0.7)
        t = t + (gr / max(float(gr.std()), 1e-6) * sd)[..., None]
    out = img.copy()
    out[y0:y1, x0:x1] = np.where(hz[..., None] > 0, np.clip(t, 0, 1), img[y0:y1, x0:x1])
    return out


def prep(k):
    J = PASSES[k]
    src, _, d = FR[J["frame"]]
    img = F.load(src)
    H, W = img.shape[:2]
    i8 = (img * 255 + 0.5).astype(np.uint8)
    cx0, cy0, cx1, cy1 = J["crop"]
    win = (cx0, cy0, cx1, cy1)
    L = F.lab(img)[..., 0]
    old = np.zeros((H, W), bool)
    layers = []                                   # (premultiplied rgb, alpha) to paste, back to front
    info = {}
    for name, o in J["objects"].items():
        m = refine(i8, o["poly"], o["band"], win)
        parts = [m]
        if "stem" in o:                           # the stem / sprig: darker than the wall in its box
            sx0, sy0, sx1, sy1 = o["stem"]
            loc = np.full((H, W), 1e9, np.float32)
            loc[sy0:sy1, sx0:sx1] = cv2.medianBlur((np.clip(L[sy0:sy1, sx0:sx1], 0, 100) * 2.55).astype(np.uint8), 31).astype(np.float32) / 2.55
            st = np.zeros((H, W), bool)
            st[sy0:sy1, sx0:sx1] = (L[sy0:sy1, sx0:sx1] < loc[sy0:sy1, sx0:sx1] - 5)
            st = cv2.morphologyEx(st.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
            parts.append(st)
        cand = None
        if "candle" in o:
            c = o["candle"]
            cm = F.poly(img.shape, c["poly"]) & (L > 55)
            fx0, fy0, fx1, fy1 = c["flame"]
            wall = float(np.median(L[fy0 - 10:fy0 - 2, fx0:fx1]))
            fl = np.zeros((H, W), np.float32)
            fl[fy0:fy1, fx0:fx1] = np.clip((L[fy0:fy1, fx0:fx1] - wall - 1.5) / 10.0, 0, 1)
            cand = (cm, fl)
            parts.append(cm | (fl > 0.05))
        mm = np.zeros((H, W), bool)
        for p_ in parts:
            mm |= p_
        old |= mm
        bx, by = o["base"]
        if "cone" in o:                           # squash only the cone (below the cup) vertically about the base
            cb = o["cone"]["cup_bottom"]
            top = int(np.nonzero(m.any(1))[0].min())
            cur_h = by - top
            cone_h = by - cb
            new_cone = o["cone"]["target_h"] - (cb - top)
            ky = new_cone / float(cone_h)
            yv = np.arange(H, dtype=np.float32)
            shift = cone_h - new_cone
            mapy = np.where(yv >= by - new_cone, by - (by - yv) / ky, yv - shift).astype(np.float32)
            mx, my = np.meshgrid(np.arange(W, dtype=np.float32), mapy)
            a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.6)
            bs = cv2.remap(img * a[..., None], mx, my, cv2.INTER_LINEAR)
            as_ = cv2.remap(a, mx, my, cv2.INTER_LINEAR)
            layers.append((bs, as_))
            info[name] = dict(height_before=cur_h, height_after=o["cone"]["target_h"], cone_ky=round(ky, 3))
            continue
        sx, sy = o["s"]
        M = np.float32([[sx, 0, bx * (1 - sx)], [0, sy, by * (1 - sy)]])
        body = mm.copy()
        if cand is not None:
            body &= ~(cand[0] | (cand[1] > 0.05))
        a = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 0.6) * cv2.dilate(body.astype(np.uint8), np.ones((3, 3), np.uint8))
        if "stem" in o:
            a = np.maximum(a, cv2.GaussianBlur(parts[1].astype(np.float32), (0, 0), 0.5))
        bs, as_ = warp(img, a, M, (H, W))
        layers.append((bs, as_))
        rows = np.nonzero(body.any(1))[0]
        info[name] = dict(base=[bx, by], sx=sx, sy=sy, height_before=int(by - rows.min()), height_after=round(float((by - rows.min()) * sy), 1))
        if cand is not None:
            cm, fl = cand
            # the candle: width x sx, height to target, its foot on the scaled cup top
            rows_c = np.nonzero(cm.any(1))[0]
            c_top, c_bot = int(rows_c.min()), int(rows_c.max())
            foot = by - (by - c_bot) * sy                         # where the candle meets the cup, after the holder's scaling
            ky = c["target_px"] / float(c_bot - c_top)
            Mc = np.float32([[sx, 0, bx * (1 - sx)], [0, ky, foot - c_bot * ky]])
            ac = np.maximum(cv2.GaussianBlur(cm.astype(np.float32), (0, 0), 0.6), fl)
            # the flame keeps its own size: moved with the candle top, not stretched
            flm = (fl > 0.02) & ~cm
            acand = cv2.GaussianBlur(cm.astype(np.float32), (0, 0), 0.6)
            bs_c, as_c = warp(img, acand, Mc, (H, W))
            new_top = c_top * ky + (foot - c_bot * ky)
            Mf = np.float32([[sx, 0, bx * (1 - sx)], [0, 1, new_top - c_top]])
            bs_f = cv2.warpAffine(img * fl[..., None], Mf, (W, H))
            as_f = cv2.warpAffine(fl, Mf, (W, H))
            layers.append((bs_c, as_c))
            layers.append((bs_f, as_f))
            info[name]["candle"] = dict(height_before=c_bot - c_top, height_after=c["target_px"], ky=round(ky, 3))
    hole = cv2.dilate(old.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    for o in J["objects"].values():               # the whole stem / sprig box goes into the hole (no remnants of the old seed head)
        if "stem" in o:
            sx0, sy0, sx1, sy1 = o["stem"]
            hole[sy0:sy1, sx0:sx1] = True
    if J["fill"] == "boards":
        base = fill_boards(img, hole, win, J["table_y"], J.get("wall_x0", 0))
    elif J["fill"] == "plaster":
        base = fill_soft(img, hole, win)
    else:
        base = fill_soft(img, hole, win, grain=False)
    new = np.zeros((H, W), np.float32)
    for bs, as_ in layers:
        col = bs / np.maximum(as_[..., None], 1e-4)
        base = col * as_[..., None] + base * (1 - as_[..., None])
        new = np.maximum(new, as_)
    # soft contact shadows under the new bases (the table)
    for name, o in J["objects"].items():
        if "s" not in o and "cone" not in o:
            continue
    o8 = (np.clip(base, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8[cy0:cy1, cx0:cx1]).save(os.path.join(HERE, d, "raw", f"{k}-input.png"))
    Image.fromarray(old.astype(np.uint8) * 255).save(os.path.join(HERE, d, "raw", f"{k}-old.png"))
    Image.fromarray((new > 0.05).astype(np.uint8) * 255).save(os.path.join(HERE, d, "raw", f"{k}-new.png"))
    Image.fromarray(o8[cy0:cy1, cx0:cx1]).save(os.path.join(HERE, d, "raw", f"{k}-input-preview.jpg"), quality=90)
    R = rec()
    R["passes"].setdefault(k, {}).update(frame=J["frame"], base=src, crop=list(J["crop"]), objects=info, fill=J["fill"],
                                         input=f"{d}/raw/{k}-input.png", old_mask=f"{d}/raw/{k}-old.png", new_mask=f"{d}/raw/{k}-new.png")
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(k, json.dumps(info))


def region_of(k, shape):
    J = PASSES[k]
    _, _, d = FR[J["frame"]]
    if "region" in J:
        r = F.poly(shape, J["region"])
    else:
        old = np.asarray(Image.open(os.path.join(HERE, d, "raw", f"{k}-old.png"))) > 127
        new = np.asarray(Image.open(os.path.join(HERE, d, "raw", f"{k}-new.png"))) > 127
        r = cv2.dilate(old.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) | cv2.dilate(new.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
        if "table_y" in J:                        # contact shadows: the table strip under the objects
            ys, xs = np.nonzero(old | new)
            r[J["table_y"] - 4:min(ys.max() + 14, shape[0]), max(xs.min() - 12, 0):xs.max() + 12] = True
    x0, y0, x1, y1 = J["crop"]
    cm = np.zeros(shape[:2], bool)
    cm[y0 + 2:y1 - 2, x0 + 2:x1 - 2] = True
    return r & cm


def apply(k, frame):
    J = PASSES[k]
    _, _, d = FR[J["frame"]]
    H, W = frame.shape[:2]
    x0, y0, x1, y1 = J["crop"]
    org = frame[y0:y1, x0:x1]
    inp = np.asarray(Image.open(os.path.join(HERE, d, "raw", f"{k}-input.png")).convert("RGB")).astype(np.float32) / 255
    h, w = org.shape[:2]
    resfull = F.load(os.path.join(d, "raw", f"{k}-seedream.png"))
    res = cv2.resize(resfull, (w, h), interpolation=cv2.INTER_AREA)
    region = region_of(k, frame.shape)
    reg_c = region[y0:y1, x0:x1]
    keep = ~cv2.dilate(reg_c.astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool)
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    regd, M = F.register(res, inp, keep)
    lo, lr = F.s2l(org), F.s2l(regd)
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = (xx - w / 2) / w, (yy - h / 2) / h
    A_ = np.stack([np.ones_like(xn), xn, yn, xn * xn, xn * yn, yn * yn], -1).astype(np.float32)
    Kf = keep & (cv2.dilate(reg_c.astype(np.uint8), np.ones((161, 161), np.uint8)).astype(bool))
    field = np.ones_like(lr)
    coefs = []
    for c in range(3):
        r_ = np.log(np.maximum(lo[..., c], 1e-4) / np.maximum(lr[..., c], 1e-4))
        idx = np.flatnonzero(Kf.ravel())[::5]
        coef, *_ = np.linalg.lstsq(A_.reshape(-1, 6)[idx], r_.ravel()[idx], rcond=None)
        field[..., c] = np.exp(np.clip(A_ @ coef, -1.0, 1.0))
        coefs.append(np.round(coef, 4).tolist())
    lr = lr * field
    rd = cv2.distanceTransform(reg_c.astype(np.uint8), cv2.DIST_L2, 5)
    edge = np.clip(rd / 14.0, 0, 1)
    a = ((0.5 - 0.5 * np.cos(np.pi * edge)) * reg_c)[..., None].astype(np.float32)
    comp = F.l2s(lo * (1 - a) + lr * a)
    comp = np.where(a > 0, comp, org)
    out = frame.copy()
    out[y0:y1, x0:x1] = np.clip(comp, 0, 1)
    mk = np.zeros((H, W), np.uint8)
    mk[y0:y1, x0:x1] = (a[..., 0] > 0.002).astype(np.uint8) * 255
    Image.fromarray(mk).save(os.path.join(HERE, d, "raw", f"{k}-mask.png"))
    return out, mk > 0, dict(result_px=list(resfull.shape[1::-1]), ecc_affine=np.round(M, 4).tolist(), tone_field_coef=coefs,
                             tone_field_median=np.round(np.median(field[reg_c], 0), 4).tolist(), mask_px=int((mk > 0).sum()))


def comp():
    R = rec()
    for fr, ks in (("nordic", ["P5", "P7"]), ("warm_modern", ["P6", "P8"])):
        src, dst, d = FR[fr]
        base = F.load(src)
        cur = base.copy()
        allowed = np.zeros(base.shape[:2], bool)
        done = []
        for k in ks:
            if not os.path.exists(os.path.join(HERE, d, "raw", f"{k}-seedream.png")):
                continue
            before = (cur * 255 + 0.5).astype(np.uint8)
            cur, mk, r = apply(k, cur)
            c8 = (np.clip(cur, 0, 1) * 255 + 0.5).astype(np.uint8)
            moved = np.abs(c8.astype(np.int16) - before.astype(np.int16)).max(2) > 0
            r.update(px_changed=int(moved.sum()), px_changed_outside_mask=int((moved & ~mk).sum()))
            R["passes"].setdefault(k, {}).update(r)
            allowed |= mk
            cur = c8.astype(np.float32) / 255
            done.append(k)
        if not done:
            continue
        o8 = F.save(cur, dst)
        b8 = (base * 255 + 0.5).astype(np.uint8)
        mv = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
        R.setdefault("final", {})[fr] = dict(file=dst, base=src, passes=done, px_changed=int(mv.sum()), px_changed_outside_masks=int((mv & ~allowed).sum()))
        print(fr, R["final"][fr])
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    {"prep": prep, "comp": comp}[sys.argv[1]](*sys.argv[2:])
