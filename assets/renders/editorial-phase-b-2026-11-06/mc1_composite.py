#!/usr/bin/env python3
"""
mc1_composite.py: the paid round of 2026-11-07 (briefs/render-country-targeted-passes-2026-11-07.md), render-agent. Four seedream-5-pro
image-to-image passes on local crops (MC1: the modern-country table and sill; EDR1: the rugs of Nordic A ed4 and warm modern ed5), each
put back into its frame in code with a mask, so nothing outside the mask can change:
  1. the 2K result scaled to the crop and registered to it (ECC, affine) on the pixels outside the edit region
  2. its colour matched to the frame (per-channel linear gain, on a ring round the region)
  3. the mask: inside the hand-set region, the pixels where the result differs from the frame (blurred difference over a threshold),
     closed, holes filled, grown; minus the hand-set protected areas (the cups' plain glaze, the candle holders, furniture legs ...)
  4. composited into the frame (feathered); outside the region not one pixel changes (counted)
  crops / sheet: mc1-before-after/ and mc1-sheet.jpg
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
from ed4_composite import register  # noqa: E402

RAW = os.path.join(HERE, "raw")
REC = os.path.join(HERE, "mc1.json")
CROPS = os.path.join(HERE, "mc1-before-after")


def poly(shape, pts):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


JOBS = {}            # filled by mc1_regions.json (frame coordinates)
CFG = os.path.join(HERE, "mc1_regions.json")
if os.path.exists(CFG):
    JOBS = json.load(open(CFG))


def one(k):
    J = JOBS[k]
    base = load01(os.path.join(HERE, J["base"]))
    H, W = base.shape[:2]
    x0, y0, x1, y1 = J["box"]
    org = base[y0:y1, x0:x1]
    h, w = org.shape[:2]
    res = cv2.resize(load01(os.path.join(HERE, J["result"])), (w, h), interpolation=cv2.INTER_AREA)
    region = np.zeros((H, W), bool)
    for p in J["region"]:
        region |= poly(base.shape, p)
    protect = np.zeros((H, W), bool)
    for p in J.get("protect", []):
        protect |= poly(base.shape, p)
    reg_c = region[y0:y1, x0:x1]
    prot_c = protect[y0:y1, x0:x1]
    keep = ~cv2.dilate(reg_c.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    if keep.mean() < 0.05:                                   # region fills the crop: register on the protected areas and the crop's rim
        keep = prot_c.copy()
        keep[:30], keep[-30:], keep[:, :30], keep[:, -30:] = True, True, True, True
    regd, M = register(res, org, keep)
    ring = cv2.dilate(reg_c.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool) & ~reg_c
    if ring.sum() < 500:
        ring = prot_c | ~reg_c
    lo, lr = s2l(org), s2l(regd)
    gain = np.array([np.median(lo[..., c][ring]) / max(np.median(lr[..., c][ring]), 1e-5) for c in range(3)], np.float32)
    gain = np.clip(gain, 0.8, 1.25)
    lr = lr * gain
    d = cv2.GaussianBlur(np.abs(l2s(lr) - org).max(2), (0, 0), J.get("blur", 3))
    m = (d > J.get("thr", 0.04)) & reg_c
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    big = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > J.get("min_area", 300):
            big[lab == i] = 1
    ff = big.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    filled = big | (1 - ff)
    g = int(J.get("grow", 6)) * 2 + 1
    m = cv2.dilate(filled, np.ones((g, g), np.uint8)).astype(bool) & reg_c & ~prot_c
    if J.get("whole_region"):
        m = reg_c & ~prot_c
    a = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), J.get("feather", 2.5)) * reg_c * ~prot_c)[..., None]
    comp = l2s(lo * (1 - a) + lr * a)
    out = base.copy()
    out[y0:y1, x0:x1] = np.clip(comp, 0, 1)
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(HERE, J["out"]))
    mk = np.zeros((H, W), np.uint8)
    mk[y0:y1, x0:x1] = (a[..., 0] > 0.002).astype(np.uint8) * 255
    Image.fromarray(mk).save(os.path.join(RAW, J["out"].replace(".png", "-mask.png")))
    b8 = (base * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    allowed = region & ~protect
    return dict(base=J["base"], crop_box=J["box"], result=J["result"], out=J["out"], ecc_affine=np.round(M, 4).tolist(),
                colour_gain_linear=np.round(gain, 4).tolist(), mask_px=int((a[..., 0] > 0.002).sum()),
                px_changed=int(moved.sum()), px_changed_outside_region=int((moved & ~allowed).sum()),
                px_changed_in_protected=int((moved & protect).sum()))


def crops(sets):
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    outl = []
    for name, b, a_, boxes in sets:
        Bm = Image.open(os.path.join(HERE, b)).convert("RGB")
        Am = Image.open(os.path.join(HERE, a_)).convert("RGB")
        panels = []
        for box, sc in boxes:
            w, h = box[2] - box[0], box[3] - box[1]
            rs = Image.NEAREST if sc > 1 else Image.LANCZOS
            panels.append((Bm.crop(box).resize((w * sc, h * sc), rs), Am.crop(box).resize((w * sc, h * sc), rs), sc))
        wide = any(p[0].width > 1400 for p in panels)
        Wd = (max(p[0].width for p in panels) + 20) if wide else max(max(p[0].width for p in panels) * 2 + 30, 700)
        Ht = (sum(2 * p[0].height + 60 for p in panels) + 40) if wide else (sum(p[0].height + 30 for p in panels) + 40)
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


def sheet(rows):
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    TH = 520
    tiles = []
    for title, b, a_, box in rows:
        B = Image.open(os.path.join(HERE, b)).convert("RGB").crop(box)
        A = Image.open(os.path.join(HERE, a_)).convert("RGB").crop(box)
        sc = TH / B.height
        tiles.append((title, B.resize((int(B.width * sc), TH), Image.LANCZOS), A.resize((int(A.width * sc), TH), Image.LANCZOS)))
    W = max(t[1].width for t in tiles) * 2 + 60
    H = 70 + len(tiles) * (TH + 60)
    out = Image.new("RGB", (W, H), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((20, 18), "MC1 / EDR1 (2026-11-07): four seedream-5-pro passes on local crops, masked back in code. TEST, not for the site.", fill=(0, 0, 0), font=fb)
    y = 70
    for title, B, A in tiles:
        d.text((20, y), title, fill=(0, 0, 0), font=f)
        out.paste(B, (20, y + 30))
        out.paste(A, (40 + B.width, y + 30))
        y += TH + 60
    p = os.path.join(HERE, "mc1-sheet.jpg")
    out.save(p, quality=90)
    return os.path.relpath(p, HERE)


if __name__ == "__main__":
    R = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-07", by="render-agent", brief="briefs/render-country-targeted-passes-2026-11-07.md",
                                                              cap=2600, note="TEST, not for the site")
    for k in sys.argv[1:]:
        r = one(k)
        sect = "rugs" if k.startswith("edr1") else "mc1"
        R.setdefault(sect, {}).setdefault(k, {}).update(r)
        print(k, {kk: vv for kk, vv in r.items() if "px" in kk or kk == "colour_gain_linear"})
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
