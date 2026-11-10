#!/usr/bin/env python3
"""
mb1_fix7.py: P6b, the caramel pillowcases in the warm-modern master bedroom as plain envelopes (no flange); render-agent, 2026-11-10.
Brief: briefs/render-master-P6b-2026-11-10.md (SPEND2). QA: qa/reports/2026-11-10-ged-master-fix4.md. Base: warm-modern-MB-A-fix4.png
(fix3 + the 0-token gap rebuild of mb1_fix5.py; the dark spot in the gap is already fixed there and is protected here).

Jobs (var2), on the prepared crop warm-modern/raw/P6b-input.png (frame x 1380-2700, y 520-1086 = 1320 x 566, 2.33:1):
  1. grok-imagine-image-2 segment-map (0): segments 3 and 4 = the two caramel pillowcases (exact pixel match, flanges included)
  2. grok-imagine-image-2 segment-edit on [3, 4] (250): FAILED, the flanges were redrawn unchanged -> raw/P6b-grok.jpg (not used)
  3. seedream-5-pro i2i 2K, 21:9 (650): flanges gone on both -> raw/P6b-seedream.png (3122 x 1338, the crop's own aspect)

  seg     the segment cut-outs (RGBA, no offsets) located in the crop by an exact masked match -> raw/P6b-seg-mask.png (crop px)
  comp    the seedream result placed at scale min(w/Wr, h/Hr) (native aspect, no centre crop), ECC affine on the pixels outside the region,
          the quadratic + local log-gain field (mb1_fix4.apply), then written ONLY inside the region (v2):
            region = ((segments 3 | 4) grown 12 px | the gap band) minus the lumbar (+3 px) and the duvet (both recomputed with
            mb1_fix5.p6b_prep's own rules); feather 4 px inward
          why v2: v1 (segments + 3 px, minus the whole of P6b-protect.png) left the old flange in two places: the protected gap band held
          the right pillowcase's old flange strip beside seedream's new edge (a doubled, stepped edge at x4), and the flange's contact
          shadow lines on the cream back pillows stayed just outside the region (a cream line with dark dashes along the top edges). The
          gap's right side IS the old flange, so it cannot stay as it was; seedream's gap (slit, the back pillow's band, the new plain
          edge) is clean down to the lumbar's top. The back pillows change only in the 12 px ring round the old pillowcases.
          -> warm-modern/warm-modern-MB-A-fix5.png, raw/P6b-comp-mask.png (frame px)
  crops   fix7-before-after/ (100 %, x2, x4) and sheet-fix7.jpg
record: mb1-fix7.json (mb1-fix5.json already holds the 0-token pass of the same day, so this pass is numbered after mb1-fix6.json)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mb1_fix as F  # noqa: E402

BASE = "warm-modern/warm-modern-MB-A-fix4.png"
OUT = "warm-modern/warm-modern-MB-A-fix5.png"
RAW = "warm-modern/raw"
CROP = (1380, 520, 2700, 1086)
REC = os.path.join(HERE, "mb1-fix7.json")
CROPS = os.path.join(HERE, "fix7-before-after")
SWATCH = (34.0, 24.1, 32.1)          # QA's card swatch: the caramel reference crop's centre third (qa/reports/2026-11-07-ged-master-mb1/data/measure.json)
OLD_FRAME = (35.4, 18.6, 28.8)       # QA's read of the old pillowcase, the same patch (2026-11-08 / register r10)
PATCH_L = (1520, 720, 1780, 900)     # QA's patch: pillowcase (caramel, left), frame px
PATCH_R = (2300, 720, 2560, 900)     # the same patch size on the right pillowcase (clear of the lumbar's shadow)
GROW, FEATHER = 12, 4.0
GAP_BAND = [(1998, 696), (2022, 696), (2062, 818), (1998, 818)]     # mb1_fix5.GAP_BAND (frame px)


def protect_v2(frame):
    """the lumbar (+3 px) and the duvet, exactly as mb1_fix5.p6b_prep built them on the same fix4 frame (frame px)"""
    H, W = frame.shape[:2]
    Lb = F.lab(frame)
    L, C = Lb[..., 0], np.hypot(Lb[..., 1], Lb[..., 2])
    lum = F.poly(frame.shape, [(1866, 786), (2220, 786), (2228, 820), (2230, 930), (1866, 930)]) & (L > 45) & (C < 28)
    lum = cv2.morphologyEx(lum.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    ff = lum.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    lum = cv2.dilate(lum | (1 - ff), np.ones((7, 7), np.uint8)).astype(bool)
    duvet = (L > 45) & (C < 24) & (np.arange(H)[:, None] >= 900)
    return lum, duvet


def lab_qa(rgb8):
    """qa-agent's Lab (measure.py), so the numbers compare with QA's"""
    c = rgb8 / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de00(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    if C1p * C2p == 0:
        hbp = hs
    elif abs(h1p - h2p) <= 180:
        hbp = hs / 2
    else:
        hbp = (hs + 360) / 2 if hs < 360 else (hs - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def rec():
    return json.load(open(REC)) if os.path.exists(REC) else dict(
        date="2026-11-10", by="render-agent", pass_id="P6b", frame="warm_modern",
        source="briefs/render-master-P6b-2026-11-10.md; qa/reports/2026-11-10-ged-master-fix4.md (register v10)",
        spend="SPEND2 (owner 2026-11-10): targeted QA passes up to 650 each, var2_estimate_cost before each job; this pass's cap 900",
        note="TEST, not for the site; new files only; awaiting qa-agent round 4 (G-ED.8, G-ED.9) and the designer's eye")


def seg(segdir):
    """locate the segment-map cut-outs 3 and 4 in the crop (exact masked match) -> raw/P6b-seg-mask.png"""
    I = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-input.png")).convert("RGB")).astype(np.float32)
    H, W = I.shape[:2]
    full = np.zeros((H, W), bool)
    found = {}
    for i in (3, 4):
        a = np.asarray(Image.open(os.path.join(segdir, f"{i}.png"))).astype(np.float32)
        rgb, al = a[..., :3], a[..., 3] > 127
        r = cv2.matchTemplate(I, rgb, cv2.TM_SQDIFF, mask=np.repeat(al.astype(np.float32)[..., None], 3, 2))
        mn, _, (x, y), _ = cv2.minMaxLoc(r)
        h, w = al.shape
        full[y:y + h, x:x + w] |= al
        found[str(i)] = dict(offset=[int(x), int(y)], size=[int(w), int(h)], px=int(al.sum()), rms=round(float(np.sqrt(max(mn, 0) / (al.sum() * 3))), 3))
    Image.fromarray(full.astype(np.uint8) * 255).save(os.path.join(HERE, RAW, "P6b-seg-mask.png"))
    M = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-mask.png"))) > 127
    R = rec()
    R["segments"] = dict(found=found, union_px=int(full.sum()), hand_mask_px=int(M.sum()),
                         iou_with_hand_mask=round(float((full & M).sum() / (full | M).sum()), 3), file=f"{RAW}/P6b-seg-mask.png")
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(R["segments"])


def comp():
    frame = F.load(BASE)
    H, W = frame.shape[:2]
    x0, y0, x1, y1 = CROP
    org = frame[y0:y1, x0:x1]
    h, w = org.shape[:2]
    inp = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-input.png")).convert("RGB")).astype(np.float32) / 255
    assert np.abs(inp - org).max() < 1e-6, "P6b-input.png is not the fix4 crop"
    segm = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-seg-mask.png"))) > 127
    prot = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-protect.png"))) > 127
    hand = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-mask.png"))) > 127
    k = 2 * GROW + 1
    lum, duvet = protect_v2(frame)
    keep_out = (lum | duvet)[y0:y1, x0:x1]
    gap = F.poly(frame.shape, GAP_BAND)[y0:y1, x0:x1]
    reg_c = (cv2.dilate(segm.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool) | gap) & ~keep_out
    reg_c[:2], reg_c[-2:], reg_c[:, :2], reg_c[:, -2:] = False, False, False, False
    Image.fromarray(keep_out.astype(np.uint8) * 255).save(os.path.join(HERE, RAW, "P6b-protect-v2.png"))

    resfull = F.load(os.path.join(RAW, "P6b-seedream.png"))
    Hr, Wr = resfull.shape[:2]
    s0 = min(w / Wr, h / Hr)
    M0 = np.float32([[s0, 0, (w - Wr * s0) / 2], [0, s0, (h - Hr * s0) / 2]])
    res = cv2.warpAffine(cv2.GaussianBlur(resfull, (0, 0), 0.45 / s0), M0, (w, h), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    keep = ~cv2.dilate(reg_c.astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool)
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    regd, M = F.register(res, inp, keep)

    # tone: the quadratic log-gain field + the local residual near the region (mb1_fix4.apply), fitted on the pixels outside the region
    lo, lr = F.s2l(org), F.s2l(regd)
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = (xx - w / 2) / w, (yy - h / 2) / h
    A_ = np.stack([np.ones_like(xn), xn, yn, xn * xn, xn * yn, yn * yn], -1).astype(np.float32)
    Kf = keep & cv2.dilate(reg_c.astype(np.uint8), np.ones((161, 161), np.uint8)).astype(bool)
    Kn = (keep & ~cv2.dilate(reg_c.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)).astype(np.float32)
    wK = cv2.GaussianBlur(Kn, (0, 0), 30)
    field = np.ones_like(lr)
    coefs = []
    for c in range(3):
        r_ = np.log(np.maximum(lo[..., c], 1e-4) / np.maximum(lr[..., c], 1e-4))
        idx = np.flatnonzero(Kf.ravel())[::3]
        coef, *_ = np.linalg.lstsq(A_.reshape(-1, 6)[idx], r_.ravel()[idx], rcond=None)
        q = A_ @ coef
        res_ = np.clip(r_ - q, -0.5, 0.5)
        loc = cv2.GaussianBlur(res_ * Kn, (0, 0), 30) / np.maximum(wK, 1e-4)
        fade = np.clip(wK / 0.25, 0, 1)
        field[..., c] = np.exp(np.clip(q + loc * fade, -1.0, 1.0))
        coefs.append(np.round(coef, 4).tolist())
    lr = lr * field
    if os.environ.get("P6B_DEBUG_DIR"):          # the registered, re-toned result over the whole crop (inspection only, outside the repo)
        Image.fromarray((np.clip(F.l2s(lr), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(os.environ["P6B_DEBUG_DIR"], "seedream-reg.png"))

    rd = cv2.distanceTransform(reg_c.astype(np.uint8), cv2.DIST_L2, 5)
    edge = np.clip(rd / FEATHER, 0, 1)
    a = ((0.5 - 0.5 * np.cos(np.pi * edge)) * reg_c)[..., None].astype(np.float32)
    comp_ = F.l2s(lo * (1 - a) + lr * a)
    comp_ = np.where(a > 0, comp_, org)
    out = frame.copy()
    out[y0:y1, x0:x1] = np.clip(comp_, 0, 1)
    o8 = F.save(out, OUT)

    mk = np.zeros((H, W), bool)
    mk[y0:y1, x0:x1] = a[..., 0] > 0
    Image.fromarray(mk.astype(np.uint8) * 255).save(os.path.join(HERE, RAW, "P6b-comp-mask.png"))
    pf = np.zeros((H, W), bool)
    pf[y0:y1, x0:x1] = keep_out
    po = np.zeros((H, W), bool)
    po[y0:y1, x0:x1] = prot
    b8 = (frame * 255 + 0.5).astype(np.uint8)
    d = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2)
    moved = d > 0
    # residual registration error on the kept ring just outside the region (how well the result sits on the frame)
    ring = cv2.dilate(reg_c.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~cv2.dilate(reg_c.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~keep_out
    ring_err = float(np.median(np.abs(F.lab(np.clip(F.l2s(lr), 0, 1))[..., 0] - F.lab(org)[..., 0])[ring]))

    o_lab = lab_qa(o8.astype(np.float64))
    b_lab = lab_qa(b8.astype(np.float64))

    def med(L_, box):
        bx0, by0, bx1, by1 = box
        m = np.median(L_[by0:by1, bx0:bx1].reshape(-1, 3), 0)
        return [round(float(v), 1) for v in m]

    colour = {}
    for nm, box in (("left (QA's patch)", PATCH_L), ("right", PATCH_R)):
        nw, ol = med(o_lab, box), med(b_lab, box)
        colour[nm] = dict(box=list(box), before=ol, after=nw, dE00_after_vs_swatch=round(de00(SWATCH, nw), 2),
                          dE00_before_vs_swatch=round(de00(SWATCH, ol), 2), dE00_after_vs_before=round(de00(ol, nw), 2),
                          hue_after=round(float(np.degrees(np.arctan2(nw[2], nw[1]))), 1), chroma_after=round(float(np.hypot(nw[1], nw[2])), 1))
    R = rec()
    R["P6b"] = dict(
        base=BASE, out=OUT, crop=list(CROP), crop_px=[w, h],
        result_px=[Wr, Hr], placed_as=dict(scale=round(float(s0), 5), offset=[round(float(M0[0, 2]), 2), round(float(M0[1, 2]), 2)]),
        ecc_affine=np.round(M, 4).tolist(), tone_field_coef=coefs, tone_field_median=np.round(np.median(field[reg_c], 0), 4).tolist(),
        region=f"v2: ((segments 3 | 4) grown {GROW} px | the gap band) minus the lumbar (+3 px) and the duvet (raw/P6b-protect-v2.png); feather {FEATHER} px inward, linear light",
        region_v1_rejected="(segments 3 | 4) grown 3 px minus P6b-protect.png, feather 2 px: the old flange stayed in the protected gap band (a doubled edge) and as contact-shadow lines on the back pillows",
        comp_mask=f"{RAW}/P6b-comp-mask.png", comp_mask_px=int(mk.sum()),
        comp_mask_px_outside_hand_mask=int((reg_c & ~hand).sum()), hand_mask_px_not_written=int((hand & ~reg_c).sum()),
        px_changed=int(moved.sum()), px_changed_outside_mask=int((moved & ~mk).sum()), px_changed_in_protect_v2=int((moved & pf).sum()),
        px_changed_in_prepared_protect=dict(total=int((moved & po).sum()), note="the gap band and the back pillows' ring (12 px) round the old pillowcases; the lumbar and the duvet: 0"),
        px_changed_outside_crop=int(moved.sum() - moved[y0:y1, x0:x1].sum()), max_abs_change_8bit=int(d.max()),
        ring_L_median_abs_err=round(ring_err, 2), colour=colour, swatch=list(SWATCH), swatch_src="qa/reports/2026-11-07-ged-master-mb1/data/measure.json refs['pillow caramel'].product")
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k_: R["P6b"][k_] for k_ in ("placed_as", "ecc_affine", "comp_mask_px", "comp_mask_px_outside_hand_mask", "px_changed",
                                                 "px_changed_outside_mask", "px_changed_in_protect_v2", "px_changed_in_prepared_protect", "px_changed_outside_crop", "ring_L_median_abs_err", "colour")}, indent=1))


CROPSETS = [("wm-bed-head-100", (1380, 620, 2700, 990), 1, Image.LANCZOS), ("wm-pillow-left-x2", (1460, 670, 1800, 980), 2, Image.LANCZOS),
            ("wm-pillow-right-x2", (2280, 660, 2680, 970), 2, Image.LANCZOS), ("wm-gap-x4", (1960, 680, 2110, 840), 4, Image.NEAREST),
            ("wm-lumbar-edge-right-x4", (2190, 780, 2300, 940), 4, Image.NEAREST), ("wm-left-end-x4", (1470, 680, 1560, 960), 4, Image.NEAREST),
            ("wm-right-end-x4", (2560, 680, 2660, 960), 4, Image.NEAREST)]


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    B = Image.open(os.path.join(HERE, BASE)).convert("RGB")
    A = Image.open(os.path.join(HERE, OUT)).convert("RGB")
    out = []
    for name, box, sc, rs in CROPSETS:
        w, h = box[2] - box[0], box[3] - box[1]
        pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
        tag = "100 %" if sc == 1 else f"x{sc}"
        vert = pb.width > 900
        W_ = pb.width + 20 if vert else pb.width * 2 + 30
        H_ = pb.height * 2 + 90 if vert else pb.height + 60
        im = Image.new("RGB", (W_, H_), (250, 249, 247))
        dr = ImageDraw.Draw(im)
        dr.text((10, 5), f"MB1 fix7 (P6b) {name}: {os.path.basename(BASE)} -> {os.path.basename(OUT)}", fill=(0, 0, 0), font=f)
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
        p_ = os.path.join(CROPS, name + ".jpg")
        im.save(p_, quality=92)
        out.append(os.path.relpath(p_, HERE))
    # the before / after sheet: the whole frame (before, after) and the bed head at 100 %, with the mask outline
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    TW = 1368
    sB, sA = B.resize((TW, round(B.height * TW / B.width)), Image.LANCZOS), A.resize((TW, round(A.height * TW / A.width)), Image.LANCZOS)
    x0, y0, x1, y1 = (1380, 620, 2700, 990)
    cb, ca = B.crop((x0, y0, x1, y1)), A.crop((x0, y0, x1, y1))
    mk = np.asarray(Image.open(os.path.join(HERE, RAW, "P6b-comp-mask.png")))[y0:y1, x0:x1] > 127
    edge = mk & ~cv2.erode(mk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    cm = np.asarray(ca).copy()
    cm[edge] = (0, 200, 255)
    cmi = Image.fromarray(cm)
    PAD, LAB = 24, 44
    W_ = PAD * 3 + TW * 2
    H_ = PAD + LAB + sB.height + PAD + LAB + cb.height + PAD + LAB + cb.height + PAD
    sh = Image.new("RGB", (W_, H_), (246, 244, 240))
    dr = ImageDraw.Draw(sh)
    y = PAD
    dr.text((PAD, y), "before: warm-modern-MB-A-fix4", font=fb, fill=(30, 30, 30))
    dr.text((PAD * 2 + TW, y), "after: warm-modern-MB-A-fix5 (P6b)", font=fb, fill=(30, 30, 30))
    y += LAB
    sh.paste(sB, (PAD, y))
    sh.paste(sA, (PAD * 2 + TW, y))
    y += sB.height + PAD
    dr.text((PAD, y), "bed head 100 %: before (left), after (right)", font=fb, fill=(30, 30, 30))
    y += LAB
    sh.paste(cb, (PAD, y))
    sh.paste(ca, (PAD * 2 + TW, y))
    y += cb.height + PAD
    dr.text((PAD, y), "after, with the composite mask outline (cyan): nothing outside it changed", font=fb, fill=(30, 30, 30))
    y += LAB
    sh.paste(cmi, (PAD, y))
    p_ = os.path.join(HERE, "sheet-fix7.jpg")
    sh.save(p_, quality=90)
    R = rec()
    R["crops"] = out
    R["sheet"] = os.path.relpath(p_, HERE)
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(out, R["sheet"], sh.size)


if __name__ == "__main__":
    {"seg": seg, "comp": comp, "crops": crops}[sys.argv[1]](*sys.argv[2:])
