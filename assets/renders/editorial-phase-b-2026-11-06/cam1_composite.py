#!/usr/bin/env python3
"""
cam1_composite.py: CAM1 (owner, 2026-11-07), render-agent. One seedream-5-pro image-to-image pass on a local crop of warm-modern A ed7
(the '21 Camel' chenille cushion -> set B's camel corduroy), put back into the frame in code, so nothing outside the cushion can change:
  1. the 2K result scaled to the crop and registered to it (ECC, affine) on the pixels away from the cushion
  2. its colour matched to the frame (per-channel linear gain on a ring round the cushion, sofa and wall only)
  3. the mask = the old cushion's silhouette (hand outline refined by GrabCut, cam1-mask-cushion.png) grown by GROW px,
     minus the candles and flames (cam1-mask-protect.png); feathered inside that region only
  4. composited; pixels changed outside the region are counted (must be 0), as are the changes on the neighbouring
     white cushion, the milk-tea cushion and the throw (must be 0)
usage: python3 cam1_composite.py masks | comp | crops
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
REC = os.path.join(HERE, "cam1.json")
CROPS = os.path.join(HERE, "cam1-before-after")
BASE, OUT = "warm-modern-A-ed7.png", "warm-modern-A-ed8.png"
RESULT = "raw/cam1-seedream.png"
BOX = (840, 560, 1520, 1070)
GROW = 3
# the old cushion, hand outline (frame px), refined by GrabCut in masks()
POLY = [(1027, 702), (1060, 708), (1095, 712), (1130, 718), (1170, 716), (1210, 705), (1262, 697), (1266, 702), (1270, 747), (1282, 807),
        (1297, 853), (1310, 887), (1323, 910), (1300, 912), (1190, 914), (1065, 918), (1058, 880), (1048, 820), (1035, 750)]
CANDLE_BOXES = [(1233, 850, 1308, 940), (1126, 885, 1200, 985)]
# neighbours that must not change (frame px boxes, checked after the composite, outside the grown region)
NEIGH = {"white_cushion": (880, 650, 1060, 920), "milk_tea_cushion": (1958, 684, 2250, 931), "throw": (640, 740, 1010, 1260)}


def masks():
    im = np.ascontiguousarray(np.asarray(Image.open(os.path.join(HERE, BASE)).convert("RGB")))
    H, W = im.shape[:2]
    P = np.zeros((H, W), np.uint8)
    cv2.fillPoly(P, [np.array(POLY, np.int32)], 1)
    lab = cv2.cvtColor(im.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
    cand = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in CANDLE_BOXES:
        cand[y0:y1, x0:x1] = (lab[y0:y1, x0:x1, 0] > 60).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(cand)
    cand = np.isin(lb, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 150]).astype(np.uint8)
    ff = cand.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    cand = cand | (1 - ff)
    cand = cv2.dilate(cand, np.ones((5, 5), np.uint8))                      # 2 px safety round the wax and the flames
    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    gc[cv2.dilate(P, np.ones((25, 25), np.uint8)) > 0] = cv2.GC_PR_BGD
    gc[P > 0] = cv2.GC_PR_FGD
    gc[cv2.erode(P, np.ones((21, 21), np.uint8)) > 0] = cv2.GC_FGD
    gc[cand > 0] = cv2.GC_BGD
    x0, y0, x1, y1 = 980, 660, 1370, 1000
    sub = gc[y0:y1, x0:x1].copy()
    cv2.grabCut(im[y0:y1, x0:x1], sub, None, np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_MASK)
    m = np.zeros((H, W), np.uint8)
    m[y0:y1, x0:x1] = ((sub == cv2.GC_FGD) | (sub == cv2.GC_PR_FGD)).astype(np.uint8)
    m = (m | cv2.erode(P, np.ones((5, 5), np.uint8))) & cv2.dilate(P, np.ones((7, 7), np.uint8)) & (1 - cand)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    m = np.isin(lb, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 100]).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    Image.fromarray(m * 255).save(os.path.join(RAW, "cam1-mask-cushion.png"))
    Image.fromarray(cand * 255).save(os.path.join(RAW, "cam1-mask-protect.png"))
    print("cushion px", int(m.sum()), "protect px", int(cand.sum()))


def comp():
    base = load01(os.path.join(HERE, BASE))
    H, W = base.shape[:2]
    cush = np.asarray(Image.open(os.path.join(RAW, "cam1-mask-cushion.png"))) > 127
    prot = np.asarray(Image.open(os.path.join(RAW, "cam1-mask-protect.png"))) > 127
    region = cv2.dilate(cush.astype(np.uint8), np.ones((2 * GROW + 1, 2 * GROW + 1), np.uint8)).astype(bool) & ~prot
    x0, y0, x1, y1 = BOX
    org = base[y0:y1, x0:x1]
    h, w = org.shape[:2]
    resfull = load01(os.path.join(HERE, RESULT))
    res = cv2.resize(resfull, (w, h), interpolation=cv2.INTER_AREA)
    reg_c, prot_c = region[y0:y1, x0:x1], prot[y0:y1, x0:x1]
    keep = ~cv2.dilate(reg_c.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & ~prot_c
    keep[:8], keep[-8:], keep[:, :8], keep[:, -8:] = False, False, False, False
    regd, M = register(res, org, keep)
    ring = cv2.dilate(reg_c.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool) & ~cv2.dilate(reg_c.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~prot_c
    lo, lr = s2l(org), s2l(regd)
    gain = np.array([np.median(lo[..., c][ring]) / max(np.median(lr[..., c][ring]), 1e-5) for c in range(3)], np.float32)
    gain = np.clip(gain, 0.8, 1.25)
    lr = lr * gain
    a = cv2.GaussianBlur(reg_c.astype(np.float32), (0, 0), 1.2) * reg_c          # feather only inward: zero outside the region
    a = a[..., None]
    comp_ = l2s(lo * (1 - a) + lr * a)
    out = base.copy()
    out[y0:y1, x0:x1] = np.clip(comp_, 0, 1)
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    b8 = np.asarray(Image.open(os.path.join(HERE, BASE)).convert("RGB"))
    # outside the region, copy the base bytes exactly (no 8-bit round-trip drift)
    o8[~region] = b8[~region]
    Image.fromarray(o8).save(os.path.join(HERE, OUT))
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    neigh = {}
    for k, (nx0, ny0, nx1, ny1) in NEIGH.items():
        box = np.zeros((H, W), bool)
        box[ny0:ny1, nx0:nx1] = True
        neigh[k] = dict(box=[nx0, ny0, nx1, ny1], px_changed_outside_cushion_region=int((moved & box & ~region).sum()),
                        px_changed_in_box=int((moved & box).sum()))
    # colour of the new cushion, against the SKU photo (exposure-normalised in the record notes)
    lab = cv2.cvtColor(o8.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
    labb = cv2.cvtColor(b8.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
    inner = cv2.erode(cush.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    def med(L_):
        mm = np.median(L_[inner], 0)
        return [round(float(v), 2) for v in mm] + [round(float(np.hypot(mm[1], mm[2])), 2), round(float(np.degrees(np.arctan2(mm[2], mm[1])) % 360), 1)]
    r = dict(result=RESULT, result_px=list(resfull.shape[1::-1]), ecc_affine=np.round(M, 4).tolist(), colour_gain_linear=np.round(gain, 4).tolist(),
             grow_px=GROW, region_px=int(region.sum()), px_changed=int(moved.sum()), px_changed_outside_region=int((moved & ~region).sum()),
             px_changed_in_protected=int((moved & prot).sum()), neighbours=neigh,
             cushion_Lab_C_h_median=dict(before_21_camel=med(labb), after_camel_corduroy=med(lab)))
    R = json.load(open(REC))
    R["composite"] = r
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(r, indent=1))


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    B = Image.open(os.path.join(HERE, BASE)).convert("RGB")
    A = Image.open(os.path.join(HERE, OUT)).convert("RGB")
    sets = [("cushion-100", (960, 640, 1400, 990), 1), ("ribs-x4", (1120, 760, 1240, 840), 4), ("edge-white-cushion-x4", (1000, 690, 1100, 790), 4),
            ("candle-x4", (1225, 840, 1335, 935), 4), ("context-50", (560, 360, 2360, 1300), 0)]
    out = []
    for name, box, sc in sets:
        w, h = box[2] - box[0], box[3] - box[1]
        if sc == 0:
            pb, pa = B.crop(box).resize((w // 2, h // 2), Image.LANCZOS), A.crop(box).resize((w // 2, h // 2), Image.LANCZOS)
            tag = "50 %"
        else:
            rs = Image.NEAREST if sc > 1 else Image.LANCZOS
            pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
            tag = "100 %" if sc == 1 else f"x{sc}"
        im = Image.new("RGB", (pb.width * 2 + 30, pb.height + 60), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"CAM1 {name}: {BASE} -> {OUT}", fill=(0, 0, 0), font=f)
        d.text((10, 30), f"before (ed7, 21 Camel chenille) {tag}", fill=(0, 0, 0), font=f)
        d.text((20 + pb.width, 30), f"after (ed8, camel corduroy) {tag}", fill=(0, 0, 0), font=f)
        im.paste(pb, (10, 55))
        im.paste(pa, (20 + pb.width, 55))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        out.append(os.path.relpath(p, HERE))
    R = json.load(open(REC))
    R["crops"] = out
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(out)


if __name__ == "__main__":
    {"masks": masks, "comp": comp, "crops": crops}[sys.argv[1]]()
