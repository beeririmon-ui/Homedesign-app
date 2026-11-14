#!/usr/bin/env python3
"""
lock_d0.py: the D0 still against its clay, render-agent, 2026-11-14 (briefs/wm-door-clay-and-d0-still-2026-11-14.md step 3;
motion-agent docs/proposals/wm-arrival-from-door-2026-11-14.md section 2, stills item 1: the leaf's rectangle, the outer opening, the two
corners and the floor line within 2 px). 0 tokens.

The clay's lines come from its id pass (exact model geometry): assets/blockout/house/framing/wm-door-2026-11-14/D0-closed-id.png.
In the image, each named line is found by sampling along it and searching across it for the strongest luminance step (+-SEARCH px).

  python3 lock_d0.py measure <image.png> [--json out.json]
  python3 lock_d0.py warp <image.png> <out.png>        # one smooth warp (x by column, y by row) that puts the named lines on the clay
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

CLAY_ID = "/home/user/homedesign-app/assets/blockout/house/framing/wm-door-2026-11-14/D0-closed-id.png"
SEARCH = 40
W, H = 2720, 1530


def clay_lines():
    """Named lines in canvas pixels, from the id pass: verticals (x, y0, y1) and horizontals (y, x0, x1)."""
    c = np.asarray(Image.open(CLAY_ID))

    def vstep(row, a, b, lo=0):
        r = c[row]
        for x in range(lo, W - 1):
            if r[x] in a and r[x + 1] in b:
                return x + 1
        return None

    def hstep(col, a, b, lo=0):
        r = c[:, col]
        for y in range(lo, H - 1):
            if r[y] in a and r[y + 1] in b:
                return y + 1
        return None
    rv = 1050                                        # a row below the window, through the door
    lc = vstep(rv, (62,), (61,))
    ol = vstep(rv, (61,), (64,))
    ll = vstep(rv, (64,), (70, 71), lo=ol)
    lr = vstep(rv, (70, 71, 72), (64,), lo=ll + 10)
    orr = vstep(rv, (64,), (61,), lo=lr)
    rc = vstep(rv, (61,), (63,), lo=orr)
    cx = (ol + orr) // 2
    oh = hstep(cx, (61,), (64, 99))
    lt = hstep(cx, (64, 99), (70, 71), lo=oh)
    lb = hstep(cx, (70, 71), (10, 60, 64), lo=lt + 10)
    fl = hstep(1500, (61, 66), (60,), lo=1000)
    fl2 = hstep(400, (61, 66), (60,), lo=1000)
    V = {"left corner (X 3.95 / Y 9.60)": (lc, 700, 1150), "outer opening, left (Y 8.80)": (ol, 200, 1150),
         "leaf, left": (ll, 300, 1150), "leaf, right": (lr, 300, 1150), "outer opening, right (Y 7.80)": (orr, 200, 1150),
         "right corner (X 3.95 / Y 6.55)": (rc, 200, 1100)}
    Hh = {"outer opening, head (Z 2.40)": (oh, ol + 40, orr - 40), "leaf, top": (lt, ll + 40, lr - 40), "leaf, bottom": (lb, ll + 40, lr - 40),
          "floor line, door wall left of the door": (fl2, lc + 40, ol - 40), "floor line, door wall right of the door": (fl, orr + 40, rc - 40)}
    return V, Hh


def lum(img):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    return cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.0)


CLAY_LIT = "/home/user/homedesign-app/assets/renders/hall/warm-modern/door-2026-11-14/d0-input.png"


def _shift(pa, pb, maxs):
    """Shift s (px) that best aligns profile pb to pa (pb(t + s) ~ pa(t)), by normalised correlation of the absolute derivatives."""
    da, db = np.abs(np.diff(pa)), np.abs(np.diff(pb))
    n = len(da)
    best, bs_ = -2, 0
    sc = {}
    for s in range(-maxs, maxs + 1):
        a = da[maxs:n - maxs]
        b = db[maxs + s:n - maxs + s]
        a0, b0 = a - a.mean(), b - b.mean()
        den = np.sqrt((a0 * a0).sum() * (b0 * b0).sum()) + 1e-9
        c = float((a0 * b0).sum() / den)
        sc[s] = c
        if c > best:
            best, bs_ = c, s
    if -maxs < bs_ < maxs:
        c0, c1, c2 = sc[bs_ - 1], sc[bs_], sc[bs_ + 1]
        den = c0 - 2 * c1 + c2
        sub = 0.0 if abs(den) < 1e-9 else 0.5 * (c0 - c2) / den
    else:
        sub = 0.0
    return bs_ + max(-0.5, min(0.5, sub)), best


def measure(path, ref=CLAY_LIT, half=70, maxs=40, seg=40):
    """Each named line: segments of seg px along it; in each, the across-line luminance profile (+-half px, averaged along the segment)
    of the image is registered to the same profile of the lit clay. Offset = image - clay (px)."""
    L = lum(Image.open(path))
    R = lum(Image.open(ref))
    V, Hh = clay_lines()
    out = {}
    near = lambda n: ("opening" in n or "leaf" in n)          # two edges 14-25 px apart: a narrow window, a short search
    for name, (x, y0, y1) in V.items():
        offs, cs = [], []
        h_, m_ = (12, 9) if near(name) else (half, maxs)
        for y in range(y0, y1 - seg + 1, seg):
            pa = R[y:y + seg, x - h_:x + h_ + 1].mean(0)
            pb = L[y:y + seg, x - h_:x + h_ + 1].mean(0)
            s_, c = _shift(pa, pb, m_)
            if c > 0.5:
                offs.append(s_)
                cs.append(c)
        a = np.array(offs) if offs else np.array([np.nan])
        out[name] = dict(kind="vertical", clay_px=x, median_offset_px=round(float(np.nanmedian(a)), 2), p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2),
                         n=len(offs), mean_corr=round(float(np.mean(cs)), 3) if cs else None)
    for name, (y, x0, x1) in Hh.items():
        offs, cs = [], []
        h_, m_ = (20, 16) if near(name) else (half, maxs)
        for x in range(x0, x1 - seg + 1, seg):
            pa = R[y - h_:y + h_ + 1, x:x + seg].mean(1)
            pb = L[y - h_:y + h_ + 1, x:x + seg].mean(1)
            s_, c = _shift(pa, pb, m_)
            if c > 0.5:
                offs.append(s_)
                cs.append(c)
        a = np.array(offs) if offs else np.array([np.nan])
        out[name] = dict(kind="horizontal", clay_px=y, median_offset_px=round(float(np.nanmedian(a)), 2), p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2),
                         n=len(offs), mean_corr=round(float(np.mean(cs)), 3) if cs else None)
    worst = max(abs(v["median_offset_px"]) for v in out.values() if np.isfinite(v["median_offset_px"]))
    return dict(lines=out, worst_median_offset_px=worst, pass_2px=bool(worst <= 2.0),
                method=f"per line, segments of {seg} px; the across-line luminance profile (+-{half} px) of the image registered to the lit clay's "
                       f"(normalised correlation of |d/dx|, +-{maxs} px, sub-pixel); segments with correlation <= 0.5 dropped; offset = image - clay, px at 2720 x 1530")


def warp(path, outp, rep=None):
    """x' (by column) and y' (by row) piecewise-linear maps through the measured lines: a line found at clay+off is moved back to clay.
    Columns and rows keep their order; verticals stay vertical, horizontals stay horizontal."""
    rep = rep or measure(path)
    img = np.asarray(Image.open(path).convert("RGB"))
    xs_src, xs_dst, ys_src, ys_dst = [0.0, W - 1.0], [0.0, W - 1.0], [0.0, H - 1.0], [0.0, H - 1.0]
    for name, v in rep["lines"].items():
        if v["kind"] == "vertical":
            xs_dst.append(float(v["clay_px"]))
            xs_src.append(float(v["clay_px"] + v["median_offset_px"]))
        elif "floor line" not in name or name.endswith("right of the door"):
            ys_dst.append(float(v["clay_px"]))
            ys_src.append(float(v["clay_px"] + v["median_offset_px"]))
    ox, oy = np.argsort(xs_dst), np.argsort(ys_dst)
    xd, xsrc = np.array(xs_dst)[ox], np.array(xs_src)[ox]
    yd, ysrc = np.array(ys_dst)[oy], np.array(ys_src)[oy]
    mapx = np.interp(np.arange(W, dtype=np.float32), xd, xsrc).astype(np.float32)
    mapy = np.interp(np.arange(H, dtype=np.float32), yd, ysrc).astype(np.float32)
    MX = np.repeat(mapx[None, :], H, 0)
    MY = np.repeat(mapy[:, None], W, 1)
    out = cv2.remap(img, MX, MY, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    Image.fromarray(out).save(outp)
    return dict(x_knots_clay_to_image=[[round(a, 1), round(b, 1)] for a, b in zip(xd, xsrc)],
                y_knots_clay_to_image=[[round(a, 1), round(b, 1)] for a, b in zip(yd, ysrc)])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "measure":
        r = measure(sys.argv[2])
        print(json.dumps(r, indent=1))
    elif cmd == "warp":
        k = warp(sys.argv[2], sys.argv[3])
        print(json.dumps(k, indent=1))
        print(json.dumps(measure(sys.argv[3]), indent=1))
