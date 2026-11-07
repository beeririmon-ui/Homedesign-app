#!/usr/bin/env python3
"""
codefix6.py: the modern-country fix4 from QA (qa/reports/2026-11-07-ged-codefix5-clay-r3.md section 1.1), render-agent, 2026-11-07.
0 tokens, no var2. modern-country-A-fix3.png -> modern-country-A-fix4.png. Each fix inside its own mask, 0 px changed outside.
  1. the dark-and-light spot (~4 x 6 px) on the sofa at (1199-1203, 1103-1110), where the old rim was: the pixels that stand out of
     the sofa round them (> 22 levels from the local median) filled from the surroundings (a membrane fill plus the sofa's own grain)
  2. the faint light line along the vase's old outline left of it (x ~1887-1895, y ~600-660): columns 1885-1897 rebuilt per row as a
     straight interpolation between the glass beside them, plus the glass's own grain
  3. (optional, x4 only) the flat-filled mullion right of the vase (L ~209, no grain) given the grain of the mullion's visible part
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
from codefix3 import check  # noqa: E402

SRC = os.path.join(HERE, "modern-country-A-fix3.png")
OUT = os.path.join(HERE, "modern-country-A-fix4.png")
REC = os.path.join(HERE, "codefix6.json")
CROPS = os.path.join(HERE, "codefix6-before-after")


def membrane(img, hole, iters=400):
    out = img.copy()
    k = ~hole
    m0 = cv2.blur(np.where(k[..., None], img, 0), (7, 7)) / np.maximum(cv2.blur(k.astype(np.float32), (7, 7))[..., None], 1e-4)
    out[hole] = m0[hole]
    for _ in range(iters):
        p = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = 0.25 * (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])
        out = np.where(hole[..., None], avg, img)
    return out


def main():
    a = load01(SRC)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    f = a * 255.0
    out = f.copy()
    rng = np.random.default_rng(66)
    rec = {}
    # ---- 1. the spot on the sofa
    box = (xx >= 1195) & (xx <= 1208) & (yy >= 1099) & (yy <= 1113)
    Lm = f.mean(2)
    ring = cv2.dilate(box.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~box
    med = np.median(Lm[ring])
    loc = cv2.medianBlur(np.clip(Lm, 0, 255).astype(np.uint8), 9).astype(np.float32)
    spot = box & (np.abs(Lm - loc) > 22)
    spot = cv2.dilate(spot.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & box
    sl = (slice(1080, 1135), slice(1175, 1230))
    fill = membrane(f[sl], spot[sl], 400)
    hp = f[sl] - cv2.GaussianBlur(f[sl], (0, 0), 1.5)
    sd = float(hp[ring[sl]].std())
    nz = cv2.GaussianBlur(rng.standard_normal(fill.shape[:2]).astype(np.float32), (0, 0), 0.7)
    nz *= sd / max(float(nz.std()), 1e-6)
    fill = fill + nz[..., None]
    o = out[sl]
    o[spot[sl]] = fill[spot[sl]]
    out[sl] = o
    rec["spot"] = dict(box=[1195, 1099, 1208, 1113], px=int(spot.sum()), sofa_median_L=round(float(med), 1), grain_sd=round(sd, 2),
                       method="pixels > 22 levels from the local median (9 px), grown 1 px, inside the box; membrane fill + the sofa's grain")
    # ---- 2. the light band along the vase's old left outline: the copied glass strip (x ~1885 to the new vase edge) kept its source's
    # brightness (+8-10 levels, peak at x ~1892). Its low frequencies (sigma 2 across, 12 along y) are brought down to the glass just
    # left of it (per row, smoothed), ramped in over 4 px; the glass's own texture stays; only the light excess is removed
    y0, y1 = 585, 700
    Lf = f.mean(2)
    vase_l = np.full(H, 1903)
    for y in range(y0, y1 + 1):
        c = np.nonzero((Lm[y, 1890:1925] < 185) & (f[y, 1890:1925, 0] - f[y, 1890:1925, 2] > 18))[0]
        vase_l[y] = 1890 + int(c.min()) if c.size else 1903
    LFl = cv2.GaussianBlur(f.mean(2), (0, 0), sigmaX=2.0, sigmaY=12.0)     # luminance only (one factor for the three channels: hue kept)
    ref = cv2.GaussianBlur(LFl[:, 1880:1884].mean(1).reshape(-1, 1).astype(np.float32), (0, 0), 6.0).ravel()   # the glass left of the strip, per row
    gain = np.ones((H, W), np.float32)
    line = np.zeros((H, W), bool)
    for y in range(y0, y1 + 1):
        xe = int(vase_l[y]) - 2
        if xe <= 1885:
            continue
        xs_ = np.arange(1884, xe)
        w = np.clip((xs_ - 1884) / 4.0, 0, 1)
        w *= np.clip((xe - xs_) / 2.0, 0, 1)                                 # and off again just before the vase's edge
        g = np.minimum(1.0, ref[y] / np.maximum(LFl[y, xs_], 1e-3))          # only the light excess
        gain[y, xs_] = 1 - w * (1 - g)
        line[y, xs_] = w > 0
    rw = np.ones((H, 1), np.float32)
    for k in range(6):
        rw[y0 + k] = rw[y1 - k] = (k + 1) / 7.0
    gain = 1 - (1 - gain) * rw
    corr = out * (gain[..., None] - 1)
    out = out * gain[..., None]
    def col_bump(img):
        pp = img[600:660, 1878:1900].mean((0, 2))
        return round(float(pp[8:17].max() - 0.5 * (pp[:4].mean() + pp[-3:].mean())), 1)
    rec["vase_line"] = dict(rows=[y0, y1], px=int(line.sum()), max_lowered_levels=round(float(-corr.min()), 1),
                            column_bump_levels=dict(before=col_bump(f), after=col_bump(out)),
                            method="the strip's low frequencies brought down to the glass left of it (light excess only), texture kept")
    # ---- 3. the mullion's grain (the flat per-row fill right of the vase)
    mx0, mx1, my0, my1 = 1988, 2010, 541, 698
    blk = f[my0:my1 + 1, mx0:mx1 + 1]
    flat = (cv2.blur(np.abs(blk - cv2.blur(blk, (3, 3))).mean(2), (3, 3)) < 0.35)
    flat_full = np.zeros((H, W), bool)
    flat_full[my0:my1 + 1, mx0:mx1 + 1] = flat
    vis = f[470:536, mx0:mx1 + 1]
    Lv = vis.mean(2)
    sel = cv2.erode((Lv > 190).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)   # the white bar's interior, off the stems
    vhp = (vis - cv2.GaussianBlur(vis, (0, 0), 1.2))
    msd = min(float(vhp[sel].std()), 3.0) if sel.sum() > 20 else 1.2
    nz3 = cv2.GaussianBlur(rng.standard_normal(blk.shape[:2]).astype(np.float32), (0, 0), 0.7)
    nz3 *= msd / max(float(nz3.std()), 1e-6)
    blk2 = out[my0:my1 + 1, mx0:mx1 + 1]
    blk2 = np.where(flat[..., None], blk2 + nz3[..., None], blk2)
    out[my0:my1 + 1, mx0:mx1 + 1] = blk2
    rec["mullion_grain"] = dict(box=[mx0, my0, mx1, my1], px=int(flat.sum()), grain_sd=round(msd, 2),
                                method="the flat pixels of the per-row fill (local variation < 0.35 levels) given the visible mullion's grain")
    o8 = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    a8 = (a * 255 + 0.5).astype(np.uint8)
    zone = spot | line | flat_full
    o8 = np.where(zone[..., None], o8, a8)
    Image.fromarray(o8).save(OUT)
    rec.update(check(o8, a8, zone, "modern-country-A-fix4.png"))
    rec.update(date="2026-11-07", by="render-agent", tokens=0, base="modern-country-A-fix3.png", out="modern-country-A-fix4.png",
               source="qa/reports/2026-11-07-ged-codefix5-clay-r3.md section 1.1", note="TEST, not for the site; new files only")
    # crops
    os.makedirs(CROPS, exist_ok=True)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    A = Image.open(SRC).convert("RGB")
    B = Image.open(OUT).convert("RGB")
    outl = []
    for name, bx, sc in (("sofa-spot-x8", (1175, 1085, 1230, 1130), 8), ("sofa-spot-100", (1100, 1060, 1300, 1160), 1),
                         ("vase-left-x4", (1868, 585, 1915, 675), 4), ("mullion-x4", (1975, 540, 2030, 700), 4)):
        w, h = bx[2] - bx[0], bx[3] - bx[1]
        rs = Image.NEAREST if sc > 1 else Image.LANCZOS
        pa, pb = A.crop(bx).resize((w * sc, h * sc), rs), B.crop(bx).resize((w * sc, h * sc), rs)
        im = Image.new("RGB", (pa.width * 2 + 30, pa.height + 40), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: fix3 | fix4", fill=(0, 0, 0), font=fnt)
        im.paste(pa, (10, 30))
        im.paste(pb, (20 + pa.width, 30))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    rec["crops"] = outl
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    return rec


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, ensure_ascii=False))
