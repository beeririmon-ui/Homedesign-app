#!/usr/bin/env python3
"""
mb1_fix3.py: the 0-token code round after QA round 2 (qa/reports/2026-11-08-ged-master-fix1.md, register v9; coordinator 2026-11-10),
render-agent.

  Nordic  nordic-MB-A-fix2.png -> nordic-MB-A-fix3.png
    1. the sconces re-scaled FROM THE SOURCE FRAME (MB-A), not from fix1: right x0.80, left x0.82 (QA: x0.68 came from the pillowcase
       basis; on the wall itself the right came out x0.86 of the card and the left x0.75). Same method as fix1 (mb1_fix.scale_lamp: the
       ring rebuilt as clean boards x the scaled shadow / glow ratio, the lamp body scaled about its centre; the left one dimmed). The rings
       were not touched by any pass (checked: fix2 == the fix1 code frame inside both rings), so the new rings simply replace them.
    2. the chair cloth (charcoal, fix2): the mask grown by 2 px, so the fringe tips and the edge feather lose the old pink-taupe; recoloured
       from the MB-A pixels as in fix2. Guard: band pixels much lighter than the cloth (the window / wall above it) stay out, so no grey
       outline is drawn on them.
  Warm modern  warm-modern-MB-A-fix1.png -> warm-modern-MB-A-fix2.png
    3. the two leaf fragments of the old sprig right of the new one (QA: x 1332-1350, y 651-685) removed: the dark pixels in that box
       (darker than the plaster around them), grown 2 px, filled from the plaster (Telea on the local window) plus the plaster's own grain.
record: mb1-fix3.json; crops: fix3-before-after/
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
import mb1_fix2 as F2  # noqa: E402

NSRC, NBASE, NOUT = "nordic/nordic-MB-A.png", "nordic/nordic-MB-A-fix2.png", "nordic/nordic-MB-A-fix3.png"
WBASE, WOUT = "warm-modern/warm-modern-MB-A-fix1.png", "warm-modern/warm-modern-MB-A-fix2.png"
REC = os.path.join(HERE, "mb1-fix3.json")
CROPS = os.path.join(HERE, "fix3-before-after")
RING_L, RING_R = (1366, 396, 1572, 572), (2436, 304, 2730, 566)
SCALE_L, SCALE_R = 0.82, 0.80
GHOST_BOX = (1326, 644, 1356, 692)


def nordic():
    orig = F.load(NSRC)
    base = F.load(NBASE)
    H, W = orig.shape[:2]
    out = base.copy()
    info = {}
    allowed = np.zeros((H, W), bool)
    # 1. sconces from the source
    sl, rg_l, info["sconce_left"] = F.scale_lamp(orig, F.cylinders([(1387, 1421, 411, 522), (1420, 1460, 408, 521), (1459, 1506, 407, 519)]),
                                                 RING_L, (1447, 467), SCALE_L, fill="boards", dim=True, exact=True)
    sr, rg_r, info["sconce_right"] = F.scale_lamp(orig, F.cylinders([(2458, 2525, 325, 501), (2524, 2597, 319, 498), (2596, 2673, 314, 494)]),
                                                  RING_R, (2566, 407), SCALE_R, fill="boards", exact=True)
    for (x0, y0, x1, y1), src in ((RING_L, sl), (RING_R, sr)):
        out[y0:y1, x0:x1] = src[y0:y1, x0:x1]
    allowed |= rg_l | rg_r
    # 2. the chair cloth, mask + 2 px
    cm, _ = F2.cloth_alpha(orig)
    Lb = F.lab(orig)
    L = Lb[..., 0]
    cm2 = cv2.dilate(cm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    for p in F.WOOD:
        cm2 &= ~F.poly(orig.shape, p)
    cm2 &= ~(L < 18)
    light_lim = float(np.percentile(L[cm], 98)) + 4.0
    band = cm2 & ~cm
    band &= L <= light_lim
    cm2 = cm | band
    ac2 = cv2.GaussianBlur(cv2.erode(cm2.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(np.float32), (0, 0), 0.8)
    rec_ = F.recolour(orig, ac2, F2.CHARCOAL, chroma_keep=0.5, gain=True)
    out = np.where((ac2 > 0)[..., None], rec_, out)
    allowed |= ac2 > 0
    inner = cv2.erode(cm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    o8 = F.save(out, NOUT)
    of = o8.astype(np.float32) / 255
    # the fringe tips: the band pixels' hue / chroma, fix2 -> fix3
    lb2, lb3 = F.lab(base), F.lab(of)
    edge = band | (cm & ~cv2.erode(cm.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool))
    low = edge.copy()
    low[:1040] = False
    def hc(lb, m):
        v = np.median(lb[m], 0)
        return [round(float(v[0]), 1), round(float(np.hypot(v[1], v[2])), 2), round(float(np.degrees(np.arctan2(v[2], v[1])) % 360), 1)]
    info["cloth"] = dict(grow_px=2, band_px=int(band.sum()), light_guard_L=round(light_lim, 1), mask_px=int(cm2.sum()),
                         Lab_C_h_inner_fix3=F.med_lab(of, inner), edge_lower_L_C_h=dict(fix2=hc(lb2, low), fix3=hc(lb3, low)),
                         edge_lower_px_C_over_8=dict(fix2=int((np.hypot(lb2[..., 1], lb2[..., 2])[low] > 8).sum()),
                                                     fix3=int((np.hypot(lb3[..., 1], lb3[..., 2])[low] > 8).sum())))
    b8 = (base * 255 + 0.5).astype(np.uint8)
    moved = np.abs(o8.astype(np.int16) - b8.astype(np.int16)).max(2) > 0
    info.update(base=NBASE, out=NOUT, px_changed_vs_fix2=int(moved.sum()), px_changed_outside_masks=int((moved & ~allowed).sum()))
    mk = np.zeros((H, W), np.uint8)
    mk[allowed] = 255
    Image.fromarray(mk).save(os.path.join(HERE, "nordic/raw/fix3-mask.png"))
    return info


def warm():
    img = F.load(WBASE)
    H, W = img.shape[:2]
    x0, y0, x1, y1 = GHOST_BOX
    Lb = F.lab(img)
    L = Lb[..., 0]
    win = (slice(y0 - 30, y1 + 30), slice(x0 - 30, x1 + 30))
    # the plaster's local level: a wide median blur of L* (the leaves are thin)
    Lw = cv2.medianBlur((np.clip(L[win], 0, 100) * 2.55).astype(np.uint8), 21).astype(np.float32) / 2.55
    m = np.zeros((H, W), bool)
    sub = (L[win] < Lw - 3.0)
    m[win] = sub
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    m &= box
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(bool) & box
    i8 = (img * 255 + 0.5).astype(np.uint8)
    wy, wx = win
    fill = cv2.inpaint(np.ascontiguousarray(i8[wy, wx]), m[wy, wx].astype(np.uint8), 6, cv2.INPAINT_TELEA).astype(np.float32) / 255
    fill = cv2.GaussianBlur(fill, (0, 0), 1.2)
    hp = img[wy, wx] - cv2.GaussianBlur(img[wy, wx], (0, 0), 1.5)
    ring = ~cv2.dilate(m[wy, wx].astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    ring &= (np.arange(fill.shape[1])[None, :] + wx.start) < 1350                        # the smoother plaster left of x 1350 (the pass side)
    sd = float(1.4826 * np.median(np.abs(hp[ring])))
    rng = np.random.default_rng(5)
    gr = cv2.GaussianBlur(rng.normal(0, 1, fill.shape[:2]).astype(np.float32), (0, 0), 0.7)
    gr = gr / max(float(gr.std()), 1e-6) * sd
    fill = np.clip(fill + gr[..., None], 0, 1)
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8) * cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = img.copy()
    out[wy, wx] = img[wy, wx] * (1 - a[wy, wx][..., None]) + fill * a[wy, wx][..., None]
    o8 = F.save(out, WOUT)
    moved = np.abs(o8.astype(np.int16) - i8.astype(np.int16)).max(2) > 0
    allowed = a > 0
    mk = np.zeros((H, W), np.uint8)
    mk[allowed] = 255
    Image.fromarray(mk).save(os.path.join(HERE, "warm-modern/raw/fix2-mask.png"))
    lo = F.lab(o8.astype(np.float32) / 255)[..., 0]
    return dict(base=WBASE, out=WOUT, ghost_box=list(GHOST_BOX), mask_px=int(m.sum()), grain_sd=round(sd, 4),
                dark_px_in_box=dict(before=int(((L < Lw_full(L, win) - 3.0) & box).sum()), after=int(((lo < Lw_full(lo, win) - 3.0) & box).sum())),
                px_changed=int(moved.sum()), px_changed_outside_mask=int((moved & ~allowed).sum()))


def Lw_full(L, win):
    out = np.full(L.shape, 1e9, np.float32)
    out[win] = cv2.medianBlur((np.clip(L[win], 0, 100) * 2.55).astype(np.uint8), 21).astype(np.float32) / 2.55
    return out


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    sets = [(NBASE, NOUT, "nordic-sconce-left-x3", (1340, 370, 1590, 590), 3), (NBASE, NOUT, "nordic-sconce-right-x2", (2400, 260, 2736, 580), 2),
            (NBASE, NOUT, "nordic-sconces-context-50", (1300, 250, 2736, 650), 0), (NBASE, NOUT, "nordic-cloth-fringe-x4", (150, 1060, 310, 1160), 4),
            (NBASE, NOUT, "nordic-cloth-100", (0, 660, 330, 1160), 1), (NBASE, NOUT, "nordic-cloth-top-x4", (0, 670, 110, 720), 4),
            (WBASE, WOUT, "wm-sprig-ghost-x6", (1270, 620, 1380, 720), 6), (WBASE, WOUT, "wm-nightstand-100", (1000, 500, 1420, 1060), 1)]
    out = []
    for b, a, name, box, sc in sets:
        B = Image.open(os.path.join(HERE, b)).convert("RGB")
        A = Image.open(os.path.join(HERE, a)).convert("RGB")
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
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"MB1 fix3 {name}: {os.path.basename(b)} -> {os.path.basename(a)}", fill=(0, 0, 0), font=f)
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
    R = dict(date="2026-11-10", by="render-agent", tokens=0, source="qa/reports/2026-11-08-ged-master-fix1.md (register v9); coordinator 2026-11-10",
             note="TEST, not for the site; new files only; awaiting qa-agent round 3")
    R["nordic"] = nordic()
    R["warm_modern"] = warm()
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    {"run": main, "crops": crops}[sys.argv[1]]()
