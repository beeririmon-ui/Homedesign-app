#!/usr/bin/env python3
"""
med_cushions.py: the Mediterranean bench's three back cushions are our product, cushions-cj-washed-cotton-frayed (master-designer,
docs/proposals/med-bench-cushions-2026-11-07.md), one SKU, one colour: the White SKU 50 x 50 (CJZT218451503CX; card ~#CFC7B6 in shade).
render-agent, 2026-11-07, 0 tokens, no var2. mediterranean-A-ed5.png -> mediterranean-A-ed6.png.
  - the Rice Soup SKU's own photo (CJZT218451536JQ) reads pale grey-blue, not sand: so all three take the White
  - the right cushion is already the White in this light (codefix3 kept it): it is the reference. The left and middle ones take its
    hue (a*, b*) and its value relation to the plaster right above each cushion (so the light's falloff along the bench is kept);
    hue and value only: an additive Lab shift inside each cushion's hand outline (feathered 2 px), the crinkle, the fringe and the
    shading kept; the terracotta, the moss lumbar, the hat and the deep gaps cut out by colour as in codefix3
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import load01  # noqa: E402
from codefix3 import save8, lab_of, lab_f, rgb_f, check, poly_mask  # noqa: E402

SRC = os.path.join(HERE, "mediterranean-A-ed5.png")
OUT = os.path.join(HERE, "mediterranean-A-ed6.png")
REC = os.path.join(HERE, "med-cushions.json")
LEFT = [(208, 713), (232, 716), (256, 725), (290, 730), (340, 736), (390, 739), (440, 738), (490, 734), (540, 727), (604, 722), (604, 1000),
        (470, 1000), (420, 1012), (264, 1012), (258, 960), (252, 900), (240, 834), (232, 786), (226, 772), (217, 752), (209, 717)]
MID = [(906, 726), (922, 725), (967, 732), (1033, 740), (1067, 742), (1100, 739), (1133, 737), (1167, 734), (1200, 727), (1208, 724),
       (1209, 765), (1212, 815), (1216, 890), (1223, 966), (1206, 966), (1192, 895), (1182, 826), (1140, 828), (1000, 834), (906, 842)]
RIGHT_INNER = [(1250, 740), (1540, 740), (1550, 940), (1250, 950)]                 # inside the White cushion (reference statistics only)


def main():
    a = load01(SRC)
    H, W = a.shape[:2]
    L, A_, B_ = lab_of(a)
    left = poly_mask(a.shape, LEFT)
    mid = poly_mask(a.shape, MID)
    yy, xx = np.mgrid[0:H, 0:W]
    # the other products by their own colours (the sand cushions themselves are b* 17-23, a* 5-8: not caught): the terracotta cushion
    # (a* > 12), the straw hat (b* > 25, low on the bench), the moss lumbar in its box, the deep gaps
    terr = A_ > 12
    hat = (B_ > 25) & (yy > 984) & (xx > 240) & (xx < 520)                    # the straw hat (crown from y ~987, brim to ~1085)
    olive = (L < 42) & (B_ > 14) & (A_ < 7) & (xx > 770) & (xx < 1240) & (yy > 805) & (yy < 1025)
    excl = cv2.dilate((terr | hat | olive | (L < 22)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    lab = lab_f(a)
    Lf, Af, Bf = lab[..., 0], lab[..., 1], lab[..., 2]
    ref = poly_mask(a.shape, RIGHT_INNER) & ~excl

    def lit_stats(m):
        v = Lf[m]
        sel = v >= np.percentile(v, 40)                              # the lit side (not the shade under the cushion's top roll)
        return float(np.median(v[sel])), float(np.median(Af[m][sel])), float(np.median(Bf[m][sel]))

    def wall_L(x0, x1):
        s = Lf[672:700, x0:x1]
        return float(np.median(s))

    Lr, ar, br = lit_stats(ref)
    Lw_r = wall_L(1250, 1550)
    rows = {}
    out = a.copy()
    allw = np.zeros((H, W), np.float32)
    for name, poly, (wx0, wx1) in (("left", left, (240, 590)), ("middle", mid, (920, 1200))):
        cm = poly & ~excl
        cm = cv2.morphologyEx(cm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
        cm_in = cv2.erode(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
        wgt = cv2.GaussianBlur(cm_in, (0, 0), 1.3) * cm
        Lc, ac, bc = lit_stats(cm)
        Lw = wall_L(wx0, wx1)
        L_t = Lw - (Lw_r - Lr)
        d = dict(dL=round(L_t - Lc, 2), da=round(ar - ac, 2), db=round(br - bc, 2))
        nl = lab.copy()
        nl[..., 0] = Lf + d["dL"]
        nl[..., 1] = Af + d["da"]
        nl[..., 2] = Bf + d["db"]
        rgb = rgb_f(nl)
        out = out * (1 - wgt[..., None]) + rgb * wgt[..., None]
        allw = np.maximum(allw, wgt)
        rows[name] = dict(before_lit_Lab=[round(Lc, 1), round(ac, 1), round(bc, 1)], wall_above_L=round(Lw, 1), target_L=round(L_t, 1), shift_Lab=d,
                          px=int((wgt > 0).sum()))
    o8 = save8(out, OUT)
    a8 = (a * 255 + 0.5).astype(np.uint8)
    zone = cv2.dilate((allw > 0).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    r = check(o8, a8, zone, "mediterranean-A-ed6.png")
    lab2 = lab_f(o8.astype(np.float32) / 255)
    after = {}
    for name, poly in (("left", left), ("middle", mid)):
        m = poly & ~excl
        v = lab2[..., 0][m]
        sel = v >= np.percentile(v, 40)
        after[name] = [round(float(np.median(v[sel])), 1), round(float(np.median(lab2[..., 1][m][sel])), 1), round(float(np.median(lab2[..., 2][m][sel])), 1)]
    card = [round(float(x), 1) for x in lab_f(np.array([[[207, 199, 182]]], np.float32) / 255)[0, 0]]
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="mediterranean-A-ed5.png", out="mediterranean-A-ed6.png",
               product="cushions-cj-washed-cotton-frayed, White 50 x 50 (CJZT218451503CX)", card_hex="#CFC7B6", card_Lab=card,
               choice="White on all three: the Rice Soup SKU photo (CJZT218451536JQ, cf.cjdropshipping.com/quick/product/73deb6c9-...) reads pale grey-blue, not sand",
               reference=dict(cushion="right (already the White in this light, kept as it is)", lit_Lab=[round(Lr, 1), round(ar, 1), round(br, 1)],
                              wall_above_L=round(Lw_r, 1), cushion_minus_wall_L=round(Lr - Lw_r, 1)),
               cushions=rows, after_lit_Lab=after, **r,
               method="additive Lab shift inside the hand outlines (codefix3's, along the frayed tops, feathered 2 px), the other products and the gaps "
                      "cut out by colour; hue (a*, b*) = the White cushion's; value = the White's relation to the plaster above, per cushion; "
                      "texture, fringe and shading untouched", note="TEST, not for the site; new files only")
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    # crops
    os.makedirs(os.path.join(HERE, "med-cushions-before-after"), exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    A = Image.open(SRC).convert("RGB")
    B = Image.open(OUT).convert("RGB")
    for name, box, sc in (("bench-100", (150, 650, 1650, 1060), 1), ("left-x3", (190, 690, 420, 860), 3), ("middle-x3", (890, 700, 1230, 860), 3)):
        w, h = box[2] - box[0], box[3] - box[1]
        rs = Image.NEAREST if sc > 1 else Image.LANCZOS
        pa, pb = A.crop(box).resize((w * sc, h * sc), rs), B.crop(box).resize((w * sc, h * sc), rs)
        wide = pa.width > 1400
        im = Image.new("RGB", ((pa.width + 20) if wide else (pa.width * 2 + 30), (pa.height * 2 + 70) if wide else (pa.height + 50)), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: ed5 -> ed6 (all three = cushions-cj-washed-cotton-frayed White)", fill=(0, 0, 0), font=f)
        if wide:
            im.paste(pa, (10, 30))
            im.paste(pb, (10, 40 + pa.height))
        else:
            im.paste(pa, (10, 30))
            im.paste(pb, (20 + pa.width, 30))
        im.save(os.path.join(HERE, "med-cushions-before-after", name + ".jpg"), quality=92)
    return rec


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, ensure_ascii=False)[:3000])
