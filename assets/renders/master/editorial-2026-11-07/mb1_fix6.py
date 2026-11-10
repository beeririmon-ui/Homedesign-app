#!/usr/bin/env python3
"""
mb1_fix6.py: master-designer's two 0-token items before "final test" (docs/master-bedroom-comparison-2026-11-07.md section 5; coordinator
2026-11-10), render-agent. nordic-MB-A-fix5.png -> nordic-MB-A-fix6.png.

  1. the candles put out: each flame and its small halo on the boards replaced by the boards behind (per column: the clean board value
     above the halo x the vertical light gradient of clean columns either side); the wax top and the holders untouched; a short dark
     wick drawn where the flame stood; the lit-candle glow inside the wax (the warm, saturated right halves, C* ~40) taken out: chroma
     capped to the wax's daylight value (the left halves, C* ~25) and the hue eased to theirs, L* (the shading) kept
  2. DL1 exposure check: L* of the wall above the panelling against the Nordic living room's back wall (fin2; ed4 is identical there).
     If the bedroom is brighter, the whole frame is lowered by up to 1/3 stop in linear light, with a shoulder that keeps the sun-stripe
     highlights (gain 2^-1/3 up to L* 80, easing to 1.0 at L* 97) and a toe that keeps the Nordic shadow floor (L* p1 >= 8)
record: mb1-fix6.json; crops: fix6-before-after/
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
import mb1_fix as F  # noqa: E402

SRC, OUT = "nordic/nordic-MB-A-fix5.png", "nordic/nordic-MB-A-fix6.png"
LIVING = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06/nordic-A-fin2.png")
REC = os.path.join(HERE, "mb1-fix6.json")
CROPS = os.path.join(HERE, "fix6-before-after")
# flames: box (x0, y0, x1, y1), the wax top row (protected from there down), the wick (x, y top, y bottom), clean columns either side
FLAMES = {"left": dict(box=(2583, 756, 2610, 797), wax_top=797, wick=(2596.5, 789, 798), clean=((2568, 2580), (2613, 2624))),
          "right": dict(box=(2665, 808, 2692, 846), wax_top=846, wick=(2677.5, 839, 847), clean=((2648, 2660), (2697, 2708)))}
CANDLES = {"left": (2580, 797, 2622, 902), "right": (2659, 846, 2698, 905)}
STOP = -1.0 / 3.0


def put_out(img):
    out = img.copy()
    lin = F.s2l(img)
    L = F.lab(img)[..., 0]
    info = {}
    region = np.zeros(img.shape[:2], bool)
    for k, c in FLAMES.items():
        x0, y0, x1, y1 = c["box"]
        ref = lin[y0 - 8:y0 - 2, x0:x1].mean(0)                       # the boards just above the halo
        cols = np.r_[c["clean"][0][0]:c["clean"][0][1], c["clean"][1][0]:c["clean"][1][1]]
        g = lin[y0:y1, cols].mean(1) / np.maximum(lin[y0 - 8:y0 - 2, cols].mean(0).mean(0), 1e-4)   # vertical gradient (rows, 3)
        wall = ref[None] * g[:, None, :]
        wall_s = F.l2s(np.clip(wall, 0, 1))
        Lw = F.lab(wall_s)[..., 0]
        d = L[y0:y1, x0:x1] - Lw
        a = np.clip((d - 0.5) / 3.0, 0, 1)                            # flame and halo: brighter than the boards behind
        a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.8)
        a[c["wax_top"] - y0:] = 0                                     # the wax top and below: untouched
        xs_ = np.arange(x0, x1)[None, :]
        rim = (np.arange(y0, y1)[:, None] >= c["wax_top"] - 7) & (np.abs(xs_ - c["wick"][0]) > 6)
        a[rim] = 0                                                    # the candle's rounded top rim: untouched (only the flame base near the wick)
        # the flame's base sits on the candle's top rim: there the fill is the rim itself, interpolated across the wick (x +-7) row by row
        fillc = wall_s.copy()
        wxi = int(round(c["wick"][0]))
        for yy_ in range(c["wax_top"] - 7, c["wax_top"]):
            r_ = yy_ - y0
            xl, xr_ = wxi - 7, wxi + 7
            for xx_ in range(xl + 1, xr_):
                t_ = (xx_ - xl) / float(xr_ - xl)
                v = img[yy_, xl] * (1 - t_) + img[yy_, xr_] * t_
                if F.lab(v[None, None])[0, 0, 0] > Lw[r_, xx_ - x0] + 6:   # the rim (cream) on both sides: use it; else the boards
                    fillc[r_, xx_ - x0] = v
        sub = out[y0:y1, x0:x1]
        out[y0:y1, x0:x1] = sub * (1 - a[..., None]) + fillc * a[..., None]
        region[y0:y1, x0:x1] |= a > 0.002
        # the wick: a short dark charred wick, anti-aliased
        wx, wt, wb = c["wick"]
        for y in range(wt, wb + 1):
            fr = (y - wt) / max(wb - wt, 1)
            wick_col = np.array([0.16, 0.12, 0.10], np.float32) * (1 - 0.35 * fr) + np.array([0.33, 0.27, 0.22], np.float32) * 0.35 * fr
            bend = 0.6 * ((wb - y) / max(wb - wt, 1)) ** 2          # a slight curl at the tip
            xc = wx + bend
            for x in range(int(np.floor(xc - 1.5)), int(np.ceil(xc + 1.5)) + 1):
                cov = float(np.clip(0.85 - (abs(x - xc) - 0.35) * 1.2, 0, 0.85))
                if y == wt:
                    cov *= 0.5
                if cov > 0:
                    out[y, x] = out[y, x] * (1 - cov) + wick_col * cov
                    region[y, x] = True
        info[k] = dict(box=list(c["box"]), flame_halo_px=int((a > 0.05).sum()), max_dL_over_boards_before=round(float(d.max()), 1))
    # the glow inside the wax
    Lb = F.lab(out)
    for k, (x0, y0, x1, y1) in CANDLES.items():
        sub = Lb[y0:y1, x0:x1].copy()
        Ls, A, B = sub[..., 0], sub[..., 1], sub[..., 2]
        C = np.hypot(A, B)
        hh = np.arctan2(B, A)
        w_ = x1 - x0
        left_half = (slice(None), slice(2, w_ // 2 - 4))
        Cref = float(np.median(C[left_half]))
        href = float(np.arctan2(np.median(B[left_half]), np.median(A[left_half])))
        wgt = np.clip((C - (Cref * np.clip(Ls / float(np.median(Ls[left_half])), 0.6, 1.0) + 1.0)) / 6.0, 0, 1)
        edge = np.ones_like(wgt)
        edge[:, :1] = edge[:, -1:] = 0.5
        wgt *= edge
        Lref = float(np.median(Ls[left_half]))
        Ccap = Cref * np.clip(Ls / Lref, 0.6, 1.0) + 1.0              # daylight wax: chroma follows its own shading
        nC = C + (np.minimum(C, Ccap) - C) * wgt
        nh = hh + (0.35 * (href - hh)) * wgt                          # the hue only nudged (a full turn reads olive in the shade)
        sub[..., 1], sub[..., 2] = nC * np.cos(nh), nC * np.sin(nh)
        new = np.clip(F.rgb(sub), 0, 1)
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - wgt[..., None]) + new * wgt[..., None]
        region[y0:y1, x0:x1] |= wgt > 0.002
        right_half = (slice(None), slice(w_ // 2 + 4, w_ - 2))
        Cn = np.hypot(sub[..., 1], sub[..., 2])
        info[k + "_wax"] = dict(box=[x0, y0, x1, y1], C_left_half=round(Cref, 1), C_right_half_before=round(float(np.median(C[right_half])), 1),
                               C_right_half_after=round(float(np.median(Cn[right_half])), 1), L_right_half=round(float(np.median(Ls[right_half])), 1))
    return out, region, info


def wall_stats(L, kind):
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    if kind == "master":
        rail = 383 - (xx - 1327) * (129 / 1409)
        m = (xx >= 1360) & (xx < 2700) & (yy >= 30) & (yy < rail - 12) & ~((xx > 2420) & (yy > 280))
    else:
        m = (xx >= 1200) & (xx < 2380) & (yy >= 80) & (yy < 680)
        for (a, b, c, d) in ((1250, 310, 1960, 630), (1080, 370, 1170, 510), (2060, 370, 2150, 510), (1190, 40, 1540, 220)):
            m &= ~((xx >= a) & (xx < c) & (yy >= b) & (yy < d))
    v = L[m]
    return dict(p10=round(float(np.percentile(v, 10)), 1), p50=round(float(np.percentile(v, 50)), 1), p80=round(float(np.percentile(v, 80)), 1),
                p90=round(float(np.percentile(v, 90)), 1), p98=round(float(np.percentile(v, 98)), 1), n=int(v.size))


def expose(img, stop):
    lin = F.s2l(img)
    Y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    Lf = lambda y_: np.where(y_ > 0.008856, 116 * np.cbrt(y_) - 16, 903.3 * y_)
    L = Lf(Y)
    t = np.clip((L - 80.0) / 17.0, 0, 1)
    t = t * t * (3 - 2 * t)
    g = (2.0 ** stop) * (1 - t) + 1.0 * t
    # toe: the deepest shadows keep the Nordic floor (L* p1 >= 8, G-ED.11): the gain eases to 0.88 below L* 20 -> 9
    u = np.clip((20.0 - L) / 11.0, 0, 1)
    u = u * u * (3 - 2 * u)
    g = g * (1 - u) + np.maximum(g, 0.88) * u
    return F.l2s(np.clip(lin * g[..., None], 0, 1))


def main():
    img = F.load(SRC)
    R = dict(date="2026-11-10", by="render-agent", tokens=0, base=SRC, out=OUT,
             source="docs/master-bedroom-comparison-2026-11-07.md section 5 (master-designer: G-ED.13, the candles; DL1); coordinator 2026-11-10",
             note="TEST, not for the site; new files only; awaiting qa-agent (G-ED.8, G-ED.9)")
    out, region, info = put_out(img)
    R["candles"] = info
    L5 = F.lab(img)[..., 0]
    Lliv = F.lab(F.load(LIVING))[..., 0]
    before = wall_stats(F.lab(out)[..., 0], "master")
    liv = wall_stats(Lliv, "living")
    stop = 0.0
    if before["p50"] > liv["p50"]:
        # the smallest stop (to 1/3) that brings the bedroom wall's median to the living room's
        for s in np.linspace(0, -1 / 3, 34):
            if wall_stats(F.lab(expose(out, s))[..., 0], "master")["p50"] <= liv["p50"]:
                stop = float(s)
                break
        else:
            stop = STOP
    exp = expose(out, stop) if stop != 0 else out
    o8 = F.save(exp, OUT)
    Lo = F.lab(o8.astype(np.float32) / 255)[..., 0]
    after = wall_stats(Lo, "master")
    i8 = (img * 255 + 0.5).astype(np.uint8)
    c8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    moved_candles = np.abs(c8.astype(np.int16) - i8.astype(np.int16)).max(2) > 0
    R["candles_px_changed"] = int(moved_candles.sum())
    R["candles_px_changed_outside_boxes"] = int((moved_candles & ~region).sum())
    R["DL1"] = dict(measure="L* of the wall above the panelling (master, x 1360-2700 above the oak rail, the right sconce excluded) against the Nordic living "
                            "room's back wall (fin2, x 1200-2380, y 80-680, the art, sconces and pendant excluded; ed4 is the same there)",
                    living_fin2=liv, master_before=before, master_after=after, stop_applied=round(stop, 3), gain_midtones=round(2 ** stop, 4),
                    shoulder="gain eases to 1.0 from L* 80 to 97 (the sun stripes' highlights kept); toe: gain eases to 0.88 from L* 20 to 9 (the Nordic shadow floor, G-ED.11)",
                    frame_L_p1=dict(before=round(float(np.percentile(L5, 1)), 1), after=round(float(np.percentile(Lo, 1)), 1), nordic_floor=8),
                    frame_L_p50=dict(before=round(float(np.median(L5)), 1), after=round(float(np.median(Lo)), 1),
                                     living_fin2=round(float(np.median(Lliv)), 1)),
                    clipped_254_pct=dict(before=round(float((i8.min(2) >= 254).mean() * 100), 3), after=round(float((o8.min(2) >= 254).mean() * 100), 3)),
                    verdict=("the bedroom was brighter than the living room; lowered" if stop < 0 else "not brighter; no change"))
    R["px_changed_vs_fix5"] = int((np.abs(o8.astype(np.int16) - i8.astype(np.int16)).max(2) > 0).sum())
    mk = np.zeros(region.shape, np.uint8)
    mk[region] = 255
    Image.fromarray(mk).save(os.path.join(HERE, "nordic/raw/fix6-candles-mask.png"))
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(R, indent=1))


def crops():
    os.makedirs(CROPS, exist_ok=True)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    sets = [("candles-x4", (2550, 740, 2730, 930), 4), ("nightstand-100", (2316, 500, 2736, 1060), 1), ("frame-33", (0, 0, 2736, 1536), 0)]
    B = Image.open(os.path.join(HERE, SRC)).convert("RGB")
    A = Image.open(os.path.join(HERE, OUT)).convert("RGB")
    out = []
    for name, box, sc in sets:
        w, h = box[2] - box[0], box[3] - box[1]
        if sc == 0:
            pb, pa, tag = B.crop(box).resize((w // 3, h // 3), Image.LANCZOS), A.crop(box).resize((w // 3, h // 3), Image.LANCZOS), "33 %"
        else:
            rs = Image.NEAREST if sc > 2 else Image.LANCZOS
            pb, pa = B.crop(box).resize((w * sc, h * sc), rs), A.crop(box).resize((w * sc, h * sc), rs)
            tag = "100 %" if sc == 1 else f"x{sc}"
        im = Image.new("RGB", (pb.width * 2 + 30, pb.height + 60), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"MB1 fix6 {name}: nordic-MB-A-fix5 -> fix6", fill=(0, 0, 0), font=f)
        d.text((10, 30), f"before {tag}", fill=(0, 0, 0), font=f)
        d.text((20 + pb.width, 30), f"after {tag}", fill=(0, 0, 0), font=f)
        im.paste(pb, (10, 55))
        im.paste(pa, (20 + pb.width, 55))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        out.append(os.path.relpath(p, HERE))
    # DL1 side by side: the bedroom (fix6) and the living room (fin2) at the same size
    Lv = Image.open(LIVING).convert("RGB")
    a = A.resize((912, 512), Image.LANCZOS)
    b = Lv.resize((912, int(912 * Lv.height / Lv.width)), Image.LANCZOS)
    im = Image.new("RGB", (912 * 2 + 30, max(a.height, b.height) + 40), (250, 249, 247))
    d = ImageDraw.Draw(im)
    d.text((10, 8), "DL1: master bedroom fix6 (left) | Nordic living room fin2 (right)", fill=(0, 0, 0), font=f)
    im.paste(a, (10, 35))
    im.paste(b, (20 + 912, 35))
    p = os.path.join(CROPS, "dl1-master-vs-living.jpg")
    im.save(p, quality=90)
    out.append(os.path.relpath(p, HERE))
    R = json.load(open(REC))
    R["crops"] = out
    json.dump(R, open(REC, "w"), indent=1, ensure_ascii=False)
    print(out)


if __name__ == "__main__":
    {"run": main, "crops": crops}[sys.argv[1]]()
