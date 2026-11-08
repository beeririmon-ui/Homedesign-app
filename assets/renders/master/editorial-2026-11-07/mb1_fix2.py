#!/usr/bin/env python3
"""
mb1_fix2.py: two code fixes (0 tokens) from master-designer, docs/proposals/story-page-design-notes-2026-11-07.md section 11
(coordinator 2026-11-08), render-agent. nordic-MB-A-fix1.png -> nordic-MB-A-fix2.png.

  1. the armchair cloth: warm charcoal, L* 36-40, C* <= 4, h 60-80 (about #4A4642), texture and shading kept.
     The same cloth mask as fix1 (mb1_fix.CLOTH minus the chair's wood), recoloured from the ORIGINAL MB-A pixels (not from the sage of
     fix1): linear-light gain to the target L* (the folds' light ratios kept), hue rotated, chroma to the target (texture chroma x0.5);
     composited as MB-A x (1 - a) + charcoal x a, so no sage is left at the feathered edge.
  2. the candles: the set is 2 x Small (the same 11 cm holder); the height difference comes from the candles (10 and 15 cm), i.e. one
     candle 5 cm taller than the other. Measured in fix1 (holder-relative): left 6.5 cm, right 4.0 cm (difference 2.5 cm, not 5). The left
     (taller) candle is extended by EXT px: its top rim and flame moved up EXT px, its body stretched between them; the bottom (where it
     sits in the cup) fixed; the wall above it covered by the candle / flame only (the flame composited with an alpha from its brightness
     over the wall).
record: mb1-fix2.json; crops: fix2-before-after/
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

SRC, FIX1, OUT = "nordic/nordic-MB-A.png", "nordic/nordic-MB-A-fix1.png", "nordic/nordic-MB-A-fix2.png"
REC = os.path.join(HERE, "mb1-fix2.json")
CROPS = os.path.join(HERE, "fix2-before-after")
CHARCOAL = (38.0, 3.0 * np.cos(np.radians(70.0)), 3.0 * np.sin(np.radians(70.0)))   # L* 38, C* 3, h 70

# candles (frame px, measured on fix1 by column profiles)
CAND = dict(x0=2564, x1=2628,           # the left candle's columns (body 2568-2623, +margin)
            flame=(2578, 776, 2610, 801), top_rim=(797, 812), body_end=865, cup_top=869,
            left_cm=6.5, right_cm=4.0, px_per_cm_left=10.4)
EXT = int(round((CAND["right_cm"] + 5.0 - CAND["left_cm"]) * CAND["px_per_cm_left"]))   # 26 px


EDGE_STRIP = [(133, 895), (143, 895), (143, 1003), (133, 1003)]


def cloth_alpha(img):
    H, W = img.shape[:2]
    Lb = F.lab(img)
    cm = np.zeros((H, W), bool)
    for p in F.CLOTH:
        cm |= F.poly(img.shape, p)
    for p in F.WOOD:
        cm &= ~F.poly(img.shape, p)
    cm |= F.poly(img.shape, EDGE_STRIP)                  # the cloth's turned left edge, 1-6 px past fix1's outline (left brown in fix1)
    cm &= ~(Lb[..., 0] < 18)
    cm = cv2.morphologyEx(cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    ac = cv2.GaussianBlur(cv2.erode(cm.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32), (0, 0), 0.8)
    return cm, ac


def extend_candle(img):
    H, W = img.shape[:2]
    x0, x1 = CAND["x0"], CAND["x1"]
    r0, r1 = CAND["top_rim"]
    be = CAND["body_end"]
    L = F.lab(img)[..., 0]
    # source alpha: the candle (top rim + body, filled) and the flame (brightness over the wall)
    A = np.zeros((H, W), np.float32)
    box = np.zeros((H, W), bool)
    box[r0 - 4:CAND["cup_top"], x0:x1] = True
    cmask = (box & (L > 58)).astype(np.uint8)
    cmask = cv2.morphologyEx(cmask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(cmask)
    cmask = (lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    ff = cmask.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    cmask = cmask | (1 - ff)
    A = np.maximum(A, cv2.GaussianBlur(cmask.astype(np.float32), (0, 0), 0.7) * box)
    fx0, fy0, fx1, fy1 = CAND["flame"]
    wall = float(np.median(L[fy0 - 12:fy0 - 2, fx0:fx1]))
    fl = np.zeros((H, W), np.float32)
    fl[fy0:fy1, fx0:fx1] = np.clip((L[fy0:fy1, fx0:fx1] - wall - 1.5) / 10.0, 0, 1)
    fl = cv2.GaussianBlur(fl, (0, 0), 0.8)
    A = np.maximum(A, fl)
    # the mapping (output row -> source row) in the candle's columns
    yv = np.arange(H, dtype=np.float32)
    new_r1 = r1 - EXT
    k = (be - r1) / float(be - new_r1)
    mapy = np.where(yv < new_r1, yv + EXT, np.where(yv <= be, r1 + (yv - new_r1) * k, yv)).astype(np.float32)
    mx, my = np.meshgrid(np.arange(W, dtype=np.float32), mapy)
    src = cv2.remap(img, mx, my, cv2.INTER_LINEAR)
    An = cv2.remap(A, mx, my, cv2.INTER_LINEAR)
    band = np.zeros((H, W), np.float32)
    band[:, x0:x1] = 1.0
    An = An * band
    An[CAND["cup_top"]:] = A[CAND["cup_top"]:] * band[CAND["cup_top"]:]           # below the body: as before
    out = img * (1 - An[..., None]) + src * An[..., None]
    # where the old candle / flame was and the new one does not cover (none expected: the new candle is taller, same columns), keep img
    region = (An > 0.002) | (A > 0.002)
    return out, region, dict(ext_px=EXT, stretch=round(1 / k, 3), new_top_rim=int(new_r1 - (r1 - r0)), flame_wall_L=round(wall, 1),
                             measured=dict(left_candle_px=68, left_holder_px=114, right_candle_px=36, right_holder_px=100),
                             heights_cm_after=dict(left=round(CAND["left_cm"] + EXT / CAND["px_per_cm_left"], 1), right=CAND["right_cm"]))


def main():
    orig = F.load(SRC)
    fix1 = F.load(FIX1)
    H, W = orig.shape[:2]
    R = dict(date="2026-11-08", by="render-agent", tokens=0, base=FIX1, out=OUT,
             source="docs/proposals/story-page-design-notes-2026-11-07.md section 11 (master-designer), items 1-2; coordinator 2026-11-08",
             note="TEST, not for the site; new files only; awaiting qa-agent (G-ED.6 on the cloth)")
    # 1. cloth
    cm, ac = cloth_alpha(orig)
    rec_ = F.recolour(orig, ac, CHARCOAL, chroma_keep=0.5, gain=True)       # orig x (1 - a) + charcoal x a
    out = np.where((ac > 0)[..., None], rec_, fix1)
    inner = cv2.erode(cm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    R["cloth"] = dict(target=dict(L=38.0, C=3.0, h=70.0, spec="L* 36-40, C* <= 4, h 60-80 (about #4A4642)"), mask_px=int(cm.sum()),
                      Lab_C_h_MB_A=F.med_lab(orig, inner), Lab_C_h_fix1=F.med_lab(fix1, inner), Lab_C_h_fix2=None)
    # 2. candle
    out, creg, cinfo = extend_candle(out)
    R["candle"] = cinfo
    o8 = F.save(out, OUT)
    R["cloth"]["Lab_C_h_fix2"] = F.med_lab(o8.astype(np.float32) / 255, inner)
    Lb = F.lab(o8.astype(np.float32) / 255)
    C = np.hypot(Lb[..., 1], Lb[..., 2])
    R["cloth"]["C_p95_fix2"] = round(float(np.percentile(C[inner], 95)), 2)
    R["cloth"]["L_p5_p95_fix2"] = [round(float(v), 1) for v in np.percentile(Lb[..., 0][inner], [5, 95])]
    f8 = (fix1 * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - f8.astype(np.int16)).max(2) > 0
    allowed = (ac > 0) | creg
    R["px_changed_vs_fix1"] = int(moved.sum())
    R["px_changed_outside_masks"] = int((moved & ~allowed).sum())
    mk = np.zeros((H, W), np.uint8)
    mk[allowed] = 255
    Image.fromarray(mk).save(os.path.join(HERE, "nordic/raw/fix2-mask.png"))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: R[k] for k in ("cloth", "candle", "px_changed_vs_fix1", "px_changed_outside_masks")}, indent=1))


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    B = Image.open(os.path.join(HERE, FIX1)).convert("RGB")
    A = Image.open(os.path.join(HERE, OUT)).convert("RGB")
    sets = [("chair-cloth-100", (0, 660, 330, 1160), 1), ("chair-cloth-x3", (120, 860, 290, 1010), 3), ("candles-x4", (2540, 730, 2735, 1000), 4),
            ("nightstand-100", (2316, 500, 2736, 1060), 1), ("context-50", (0, 300, 1400, 1300), 0)]
    out = []
    for name, box, sc in sets:
        w, h = box[2] - box[0], box[3] - box[1]
        if sc == 0:
            pb, pa, tag = B.crop(box).resize((w // 2, h // 2), Image.LANCZOS), A.crop(box).resize((w // 2, h // 2), Image.LANCZOS), "50 %"
        else:
            rs = Image.NEAREST if sc > 2 else Image.LANCZOS
            pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
            tag = "100 %" if sc == 1 else f"x{sc}"
        im = Image.new("RGB", (pb.width * 2 + 30, pb.height + 60), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"MB1 fix2 {name}: nordic-MB-A-fix1 -> fix2", fill=(0, 0, 0), font=f)
        d.text((10, 30), f"before (fix1) {tag}", fill=(0, 0, 0), font=f)
        d.text((20 + pb.width, 30), f"after (fix2) {tag}", fill=(0, 0, 0), font=f)
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
    {"run": main, "crops": crops}[sys.argv[1]]()
