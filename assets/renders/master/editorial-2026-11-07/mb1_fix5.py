#!/usr/bin/env python3
"""
mb1_fix5.py: two 0-token code fixes after QA round 3 (qa/reports/2026-11-10-ged-master-fix4.md, register v10; coordinator 2026-11-10),
render-agent; plus the P6b input crop and prompt prepared (NOT sent: SPEND1 week 3 starts Sun 2026-11-15).

  Nordic  nordic-MB-A-fix4.png -> nordic-MB-A-fix5.png
    the sheet-coloured wedge left of the lumbar (apex ~(1606, 798), base y ~846, x 1578-1642) becomes the left pillowcase's linen:
    per column, the vertical profile interpolated between the pillowcase columns either side of the wedge (x 1568-1574 and 1644-1650:
    linen down to the contact line where the pillowcase meets the sheet, so the soft contact shadow runs through), plus the linen's own
    high-frequency grain taken 48 px higher on the same pillowcase
  Warm modern  warm-modern-MB-A-fix3.png -> warm-modern-MB-A-fix4.png
    the dark blurred spot in the gap above the lumbar (x ~2016-2068, y 763-817) rebuilt by continuing the gap: the clean rows 736-762
    (the dark slit, the cream back pillow's edge and the caramel folds) sheared down along the band's slant (0.45 px / row) and
    cross-faded every 27 rows; the lumbar (its cream top edge) protected
  p6b-prep   writes warm-modern/raw/P6b-input.png (frame x 1380-2700, y 520-1086 = 1320 x 566, 2.33:1, seedream's 3122 x 1338),
             P6b-mask.png (the two caramel pillowcases only) and P6b-protect.png (the lumbar, its shadow, the cream back pillows)
record: mb1-fix5.json; crops: fix5-before-after/
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

NB, NO = "nordic/nordic-MB-A-fix4.png", "nordic/nordic-MB-A-fix5.png"
WB, WO = "warm-modern/warm-modern-MB-A-fix3.png", "warm-modern/warm-modern-MB-A-fix4.png"
REC = os.path.join(HERE, "mb1-fix5.json")
CROPS = os.path.join(HERE, "fix5-before-after")
WEDGE = [(1606, 794), (1626, 820), (1644, 847), (1576, 847)]
P6B_CROP = (1380, 520, 2700, 1086)
# the two caramel pillowcases (frame px; read off a 20 px grid on fix3) and what must not change
PILLOW_L = [(1488, 696), (1700, 690), (2012, 688), (2014, 760), (2012, 952), (1700, 956), (1500, 956), (1494, 830)]
PILLOW_R = [(2016, 690), (2300, 688), (2592, 690), (2612, 780), (2648, 950), (2300, 956), (2020, 955), (2016, 760)]
GAP_BAND = [(1998, 696), (2022, 696), (2062, 818), (1998, 818)]


def nordic():
    img = F.load(NB)
    H, W = img.shape[:2]
    wm = F.poly(img.shape, WEDGE)
    wm = cv2.dilate(wm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    lin = F.s2l(img)
    y0, y1 = 788, 850
    colL = lin[y0:y1, 1566:1574].mean(1)
    colR = lin[y0:y1, 1645:1652].mean(1)
    out = lin.copy()
    hp_src = img - cv2.GaussianBlur(img, (0, 0), 1.6)
    for x in range(1570, 1650):
        t = (x - 1570) / 79.0
        prof = colL * (1 - t) + colR * t
        out[y0:y1, x] = prof
    base = F.l2s(np.clip(out, 0, 1))
    tex = np.zeros_like(img)
    tex[y0:y1] = hp_src[y0 - 48:y1 - 48]
    fill = np.clip(base + tex, 0, 1)
    a = cv2.GaussianBlur(wm.astype(np.float32), (0, 0), 1.2) * cv2.dilate(wm.astype(np.uint8), np.ones((3, 3), np.uint8))
    res = img * (1 - a[..., None]) + fill * a[..., None]
    o8 = F.save(res, NO)
    b8 = (img * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    Lb = F.lab(o8.astype(np.float32) / 255)
    Lo = F.lab(img)
    inner = cv2.erode(wm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    ring = cv2.dilate(wm.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~wm & (np.arange(H)[:, None] < 842)
    Image.fromarray((a > 0).astype(np.uint8) * 255).save(os.path.join(HERE, "nordic/raw/fix5-mask.png"))
    return dict(base=NB, out=NO, mask_px=int((a > 0).sum()), px_changed=int(moved.sum()), px_changed_outside_mask=int((moved & ~(a > 0)).sum()),
                wedge_L_median=dict(before=round(float(np.median(Lo[..., 0][inner])), 1), after=round(float(np.median(Lb[..., 0][inner])), 1),
                                    pillowcase_ring=round(float(np.median(Lo[..., 0][ring])), 1)),
                method="per-column profile interpolated between the pillowcase columns 1566-1573 and 1645-1651 (linen + the contact line), linear light; "
                       "the linen grain (high-pass, sigma 1.6) from 48 px higher on the same pillowcase")


def warm():
    """the gap continued row by row: the slit / band boundary e1 and the band's lit right edge e2 extrapolated from rows 730-764 (slopes
    0.2 and 0.45 px/row); each row's band is the mean of rows 760-764 resampled from [e1s, e2s] to [e1(y), e2(y)], the dark line and the
    caramel's shaded ramp after e2 unscaled; further right the caramel folds copied from 34 px to the right on the same row (clean
    caramel); fine grain added; left of e1 (the slit) and the lumbar untouched"""
    img = F.load(WB)
    H, W = img.shape[:2]
    ya, yb, xr = 765, 818, 2080
    Lb = F.lab(img)
    L = Lb[..., 0]
    src = img[760:765].mean(0)
    e1s, e2s = 2015.3, 2033.0
    xs_all = np.arange(W, dtype=np.float32)
    fill = img.copy()
    region = np.zeros((H, W), bool)
    for y in range(ya, yb):
        e1 = 2015.5 + 0.2 * (y - 764)
        e2 = 2033.5 + 0.45 * (y - 764)
        xb = int(np.floor(e1)) - 1
        xsrc = np.where(xs_all <= e2, e1s + (xs_all - e1) * (e2s - e1s) / (e2 - e1), e2s + (xs_all - e2))
        row_band = np.stack([np.interp(xsrc, xs_all, src[:, c]) for c in range(3)], 1)
        row_car = np.stack([np.interp(xs_all + 34, xs_all, img[y, :, c]) for c in range(3)], 1)
        x_ramp_end = e2 + 12
        w = np.clip((xs_all - x_ramp_end) / 6.0, 0, 1)[:, None]
        wv = float(np.clip((y - ya) / 12.0, 0, 1))         # the copied caramel fades in below the clean rows (no seam at the top)
        row_car = img[y] * (1 - wv) + row_car * wv
        row = row_band * (1 - w) + row_car * w
        fill[y, xb:xr] = row[xb:xr]
        region[y, xb:xr] = True
    cush = (L > 38) & (np.arange(H)[:, None] >= 812)
    cush = cv2.dilate(cush.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    region &= ~cush
    hp = img[740:762, 2014:2060] - cv2.GaussianBlur(img[740:762, 2014:2060], (0, 0), 1.2)
    sd = float(1.4826 * np.median(np.abs(hp)))
    rng = np.random.default_rng(21)
    gr = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)
    gr = gr / max(float(gr[ya:yb, 2000:xr].std()), 1e-6) * sd
    fill = np.clip(fill + (gr * region)[..., None], 0, 1)
    a = region.astype(np.float32)
    a[:, xr - 6:xr] *= np.linspace(1, 0.15, 6)[None, :]
    a = cv2.GaussianBlur(a, (0, 0), 0.8) * region
    res = img * (1 - a[..., None]) + fill * a[..., None]
    o8 = F.save(res, WO)
    b8 = (img * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    Image.fromarray((a > 0).astype(np.uint8) * 255).save(os.path.join(HERE, "warm-modern/raw/fix4-mask.png"))
    Lo = F.lab(o8.astype(np.float32) / 255)[..., 0]
    box = (slice(770, 812), slice(2030, 2060))
    hpf = lambda z: z - cv2.GaussianBlur(z, (0, 0), 1.5)
    return dict(base=WB, out=WO, region=[2014, ya, xr, yb], mask_px=int((a > 0).sum()), px_changed=int(moved.sum()),
                px_changed_outside_mask=int((moved & ~(a > 0)).sum()),
                spot_box_L_median=dict(before=round(float(np.median(L[box])), 1), after=round(float(np.median(Lo[box])), 1)),
                spot_box_grain_sd=dict(before=round(float(np.std(hpf(L)[box])), 2), after=round(float(np.std(hpf(Lo)[box])), 2),
                                       clean_gap_rows_736_762=round(float(np.std(hpf(L)[736:762, 2030:2060])), 2)),
                method="the gap continued row by row: band edges extrapolated (0.2 / 0.45 px per row), the band resampled from rows 760-764, the caramel "
                       "folds copied from 34 px right on the same row, fine grain; the lumbar protected")


def p6b_prep():
    img = F.load(WO if os.path.exists(os.path.join(HERE, WO)) else WB)
    H, W = img.shape[:2]
    x0, y0, x1, y1 = P6B_CROP
    i8 = (img * 255 + 0.5).astype(np.uint8)
    Image.fromarray(i8[y0:y1, x0:x1]).save(os.path.join(HERE, "warm-modern/raw/P6b-input.png"))
    Lb = F.lab(img)
    L, C = Lb[..., 0], np.hypot(Lb[..., 1], Lb[..., 2])
    m = F.poly(img.shape, PILLOW_L) | F.poly(img.shape, PILLOW_R)
    lum = F.poly(img.shape, [(1866, 786), (2220, 786), (2228, 820), (2230, 930), (1866, 930)]) & (L > 45) & (C < 28)
    lum = cv2.morphologyEx(lum.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    ff = lum.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    lum = cv2.dilate(lum | (1 - ff), np.ones((7, 7), np.uint8)).astype(bool)
    yy = np.arange(H)[:, None]
    back = (L > 45) & (C < 24) & (yy >= 640) & (yy < 760)               # the cream back pillows (the bedding set's own)
    back = cv2.dilate(back.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    duvet = (L > 45) & (C < 24) & (yy >= 900)                           # the natural-linen duvet in front of the pillows' feet
    gap = F.poly(img.shape, GAP_BAND)                                   # the gap between the pillowcases, rebuilt in fix4
    protect = lum | back | gap | duvet
    mask = m & ~protect
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    mc = np.zeros((y1 - y0, x1 - x0), np.uint8)
    pc = np.zeros_like(mc)
    mc[mask[y0:y1, x0:x1]] = 255
    pc[protect[y0:y1, x0:x1]] = 255
    Image.fromarray(mc).save(os.path.join(HERE, "warm-modern/raw/P6b-mask.png"))
    Image.fromarray(pc).save(os.path.join(HERE, "warm-modern/raw/P6b-protect.png"))
    ov = i8[y0:y1, x0:x1].copy()
    ov[mc > 0] = (ov[mc > 0] * 0.5 + np.array([0, 160, 255]) * 0.5).astype(np.uint8)
    ov[pc > 0] = (ov[pc > 0] * 0.5 + np.array([255, 0, 160]) * 0.5).astype(np.uint8)
    Image.fromarray(ov).save(os.path.join(HERE, "warm-modern/raw/P6b-mask-overlay.jpg"), quality=88)
    return dict(base=os.path.basename(WO), crop=list(P6B_CROP), crop_px=[x1 - x0, y1 - y0], aspect=round((x1 - x0) / (y1 - y0), 3),
                seedream_native="3122 x 1338 (2.333)", input="warm-modern/raw/P6b-input.png", mask="warm-modern/raw/P6b-mask.png",
                protect="warm-modern/raw/P6b-protect.png", overlay="warm-modern/raw/P6b-mask-overlay.jpg", mask_px=int((mc > 0).sum()),
                protect_px=int((pc > 0).sum()), prompt="assets/prompts/master-editorial-2026-11-07/P6b-wm-caramel-pillowcases.txt",
                refs=["https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/7b3e9c2b-1261-4386-8edc-4428e34b6858.png (pillowcases, Caramel)"],
                status="PREPARED, NOT SENT: SPEND1 week 3 starts Sun 2026-11-15 (650; estimate first)",
                composite_plan="mb1_fix4.apply-style: the result placed at scale min(w/Wr, h/Hr) (native aspect: no centre crop), ECC on the pixels outside the mask, "
                               "the quadratic + local tone field, the mask feathered inward; the protect mask never written")


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    sets = [(NB, NO, "nordic-wedge-x4", (1540, 740, 1700, 880), 4), (NB, NO, "nordic-bed-head-100", (1460, 580, 2440, 960), 1),
            (WB, WO, "wm-gap-x5", (1970, 700, 2100, 830), 5), (WB, WO, "wm-bed-head-100", (1380, 620, 2700, 990), 1)]
    out = []
    for b, a, name, box, sc in sets:
        B = Image.open(os.path.join(HERE, b)).convert("RGB")
        A = Image.open(os.path.join(HERE, a)).convert("RGB")
        w, h = box[2] - box[0], box[3] - box[1]
        rs = Image.NEAREST if sc > 2 else Image.LANCZOS
        pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
        tag = "100 %" if sc == 1 else f"x{sc}"
        vert = pb.width > 900
        W_ = pb.width + 20 if vert else pb.width * 2 + 30
        H_ = pb.height * 2 + 90 if vert else pb.height + 60
        im = Image.new("RGB", (W_, H_), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"MB1 fix5 {name}: {os.path.basename(b)} -> {os.path.basename(a)}", fill=(0, 0, 0), font=f)
        if vert:
            d.text((10, 30), f"before {tag}", fill=(0, 0, 0), font=f)
            im.paste(pb, (10, 55))
            d.text((10, 60 + pb.height), f"after {tag}", fill=(0, 0, 0), font=f)
            im.paste(pa, (10, 85 + pb.height))
        else:
            d.text((10, 30), f"before {tag}", fill=(0, 0, 0), font=f)
            d.text((20 + pb.width, 30), f"after {tag}", fill=(0, 0, 0), font=f)
            im.paste(pb, (10, 55))
            im.paste(pa, (20 + pb.width, 55))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        out.append(os.path.relpath(p, HERE))
    R = json.load(open(REC))
    R["crops"] = out
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(out)


def main():
    R = dict(date="2026-11-10", by="render-agent", tokens=0, source="qa/reports/2026-11-10-ged-master-fix4.md (register v10); coordinator 2026-11-10",
             note="TEST, not for the site; new files only; awaiting qa-agent round 4")
    R["nordic"] = nordic()
    R["warm_modern"] = warm()
    R["P6b"] = p6b_prep()
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: R[k] for k in ("nordic", "warm_modern")}, indent=1))
    print({k: v for k, v in R["P6b"].items() if k in ("crop_px", "aspect", "mask_px", "protect_px")})


if __name__ == "__main__":
    {"run": main, "crops": crops}[sys.argv[1]]()
