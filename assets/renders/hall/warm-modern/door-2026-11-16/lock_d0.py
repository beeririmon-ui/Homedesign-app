#!/usr/bin/env python3
"""
lock_d0.py: the final D0 still against its clay, render-agent, 2026-11-16 (briefs/wm-door-final-d0-2026-11-16.md step 2; motion-agent
docs/proposals/wm-arrival-from-door-2026-11-14.md section 2, stills item 1: the leaf's rectangle, the outer opening, the two corners and the
floor line within 2 px; master-designer ch. 11.4 item 1: the joints within 3 px, verticals within 0.5 deg, the planter, bench, lamp and doormat
within 0.01). 0 tokens. The 2026-11-14 lock_d0.py, on the new clay's ids (the stone wall 84 / 86, the reveal 85 / 64, the planter and the herbs in
front of the right corner below v 0.50, so that line is measured above them) and with the lines ch. 11.4 adds.

The clay's lines come from its id pass (exact model geometry): assets/blockout/house/framing/wm-door-2026-11-16/D0-closed-id.png.
In the image each named line is found per segment along it: the across-line luminance profile is registered to the lit clay's (d0-input.png).

  python3 lock_d0.py measure <image.png>
  python3 lock_d0.py warp <image.png> <out.png>        # one smooth warp (x by column, y by row) that puts the named lines on the clay
"""
import json
import math
import sys

import cv2
import numpy as np
from PIL import Image

CLAY_ID = "/home/user/homedesign-app/assets/blockout/house/framing/wm-door-2026-11-16/D0-closed-id.png"
CLAY_LIT = "/home/user/homedesign-app/assets/renders/hall/warm-modern/door-2026-11-16/d0-input.png"
W, H = 2720, 1530
OX, OY, FX, FY = 77.4882, 43.4301, 2642.5118 - 77.4882, 1486.5699 - 43.4301
WALL, JOINT, REVEAL, LEAF = (84, 86), (86,), (85, 64), (70, 71)
GATE = ("left corner (X 3.95 / Y 9.60)", "outer opening, left (Y 8.80)", "leaf, left", "leaf, right", "outer opening, right (Y 7.80)",
        "right corner (X 3.95 / Y 6.55), above the herbs", "outer opening, head (Z 2.40)", "leaf, top", "leaf, bottom",
        "floor line, door wall left of the door", "floor line, door wall right of the door")


def row_of(v):
    return int(round(OY + v * FY))


def col_of(u):
    return int(round(OX + u * FX))


def clay_lines():
    """Named lines in canvas pixels, from the id pass: verticals (x, y0, y1) and horizontals (y, x0, x1)."""
    c = np.asarray(Image.open(CLAY_ID))

    def vstep(r, a, b, lo=0):
        rr = c[r]
        for x in range(lo, W - 1):
            if rr[x] in a and rr[x + 1] in b:
                return x + 1
        return None

    def hstep(col, a, b, lo=0):
        r = c[:, col]
        for y in range(lo, H - 1):
            if r[y] in a and r[y + 1] in b:
                return y + 1
        return None
    rv = 1050
    lc = vstep(rv, (62, 97), WALL)
    ol = vstep(rv, WALL, REVEAL)
    ll = vstep(rv, REVEAL, LEAF, lo=ol)
    lr = vstep(rv, LEAF + (72,), REVEAL, lo=ll + 10)
    orr = vstep(rv, REVEAL, WALL, lo=lr)
    rc = vstep(row_of(0.30), WALL, (63, 97), lo=orr)
    pl = vstep(rv, WALL, (87, 89, 88), lo=orr)                                  # the planter's left side (Y 7.05 face)
    cx = (ol + orr) // 2
    oh = hstep(cx, WALL, REVEAL + (99,))
    lt = hstep(cx, REVEAL + (99,), LEAF, lo=oh)
    lb = hstep(cx, LEAF, (10, 60, 64, 85, 86), lo=lt + 10)
    fl = hstep(col_of(0.50), WALL, (60,), lo=1000)
    fl2 = hstep(400, WALL, (60,), lo=1000)
    lamp = np.nonzero(c == 91)
    ly0, ly1 = lamp[0].min(), lamp[0].max()
    lrow = (ly0 + ly1) // 2
    lx = np.nonzero(c[lrow] == 91)[0]
    mat = np.nonzero(c == 93)
    mrow = (mat[0].min() + mat[0].max()) // 2
    mx = np.nonzero(c[mrow] == 93)[0]
    mcol = (mx.min() + mx.max()) // 2
    mt = hstep(mcol, (60, 64, 85, 86), (93,), lo=1250)
    V = {"left corner (X 3.95 / Y 9.60)": (lc, 700, 1150), "outer opening, left (Y 8.80)": (ol, 200, 1150),
         "leaf, left": (ll, 300, 1150), "leaf, right": (lr, 300, 1150), "outer opening, right (Y 7.80)": (orr, 200, 1150),
         "right corner (X 3.95 / Y 6.55), above the herbs": (rc, 200, 700),
         "planter, left side (Y 7.05)": (pl, row_of(0.66), row_of(0.80)),
         "wall light, left side": (int(lx.min()), int(ly0) + 8, int(ly1) - 8), "wall light, right side": (int(lx.max()) + 1, int(ly0) + 8, int(ly1) - 8),
         "doormat, left edge": (int(mx.min()), int(mat[0].min()) + 10, int(mat[0].max()) - 10),
         "doormat, right edge": (int(mx.max()) + 1, int(mat[0].min()) + 10, int(mat[0].max()) - 10)}
    Hh = {"outer opening, head (Z 2.40)": (oh, ol + 40, orr - 40), "leaf, top": (lt, ll + 40, lr - 40), "leaf, bottom": (lb, ll + 40, lr - 40),
          "floor line, door wall left of the door": (fl2, lc + 40, ol - 40), "floor line, door wall right of the door": (fl, orr + 40, pl - 40),
          "doormat, far edge": (mt, int(mx.min()) + 40, int(mx.max()) - 40)}
    # the joints of the door wall: each horizontal joint left and right of the door
    for side, (x0, x1) in (("left", (lc + 40, ol - 40)), ("right", (orr + 40, pl - 40))):
        col = (x0 + x1) // 2
        r = c[:, col]
        ys = [y for y in range(1, H - 1) if r[y] == 86 and r[y - 1] != 86]
        for y in ys:
            z = sum(1 for k in range(y, min(H, y + 6)) if r[k] == 86)
            if 1 <= z <= 5 and y < 1300:
                xa, xb = x0, x1
                if side == "right":
                    lamp_cols = (int(lx.min()) - 60, int(lx.max()) + 60)
                    if ly0 - 120 < y < ly1 + 120:               # beside the lamp's fans: measure left of the lamp only
                        xb = min(xb, lamp_cols[0])
                if xb - xa >= 80:
                    Hh[f"joint at row {y + z / 2:.0f}, {side} of the door"] = (int(round(y + z / 2 - 0.5)), xa, xb)
    return V, Hh


def lum(img):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    return cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.0)


def _shift(pa, pb, maxs):
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


def measure(path, ref=CLAY_LIT, seg=40):
    L = lum(Image.open(path))
    R = lum(Image.open(ref))
    V, Hh = clay_lines()
    out = {}
    narrow = lambda n: ("opening" in n or "leaf" in n or "joint" in n or "wall light" in n or "doormat" in n or "planter" in n)
    for name, (x, y0, y1) in V.items():
        offs, cs, yc = [], [], []
        h_, m_ = (12, 9) if narrow(name) else (70, 40)
        for y in range(y0, y1 - seg + 1, seg):
            pa = R[y:y + seg, x - h_:x + h_ + 1].mean(0)
            pb = L[y:y + seg, x - h_:x + h_ + 1].mean(0)
            s_, c = _shift(pa, pb, m_)
            if c > 0.5:
                offs.append(s_)
                cs.append(c)
                yc.append(y + seg / 2)
        a = np.array(offs) if offs else np.array([np.nan])
        tilt = None
        if len(offs) >= 3:
            k = np.polyfit(np.array(yc), a, 1)[0]
            tilt = round(math.degrees(math.atan(k)), 3)
        out[name] = dict(kind="vertical", clay_px=x, median_offset_px=round(float(np.nanmedian(a)), 2), p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2),
                         n=len(offs), mean_corr=round(float(np.mean(cs)), 3) if cs else None, tilt_deg_vs_clay=tilt)
    for name, (y, x0, x1) in Hh.items():
        offs, cs = [], []
        h_, m_ = (6, 3) if ("joint" in name or "doormat" in name) else ((20, 16) if narrow(name) else (70, 40))
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
    fin = lambda v: v["median_offset_px"] is not None and np.isfinite(v["median_offset_px"])
    gate = [abs(out[k]["median_offset_px"]) for k in GATE if k in out and fin(out[k])]
    joints = [abs(v["median_offset_px"]) for k, v in out.items() if "joint" in k and fin(v)]
    objs = {k: v["median_offset_px"] for k, v in out.items() if any(t in k for t in ("planter", "wall light", "doormat"))}
    tilts = [abs(v["tilt_deg_vs_clay"]) for v in out.values() if v.get("tilt_deg_vs_clay") is not None and v["n"] >= 9]      # long verticals (>= 360 px)
    short_tilts = {k: v["tilt_deg_vs_clay"] for k, v in out.items() if v.get("tilt_deg_vs_clay") is not None and v["n"] < 9}
    return dict(lines=out, gate_lines_worst_px=max(gate), gate_pass_2px=bool(max(gate) <= 2.0 and len(gate) == len(GATE)),
                joints_worst_px=max(joints) if joints else None, joints_pass_3px=bool(joints and max(joints) <= 3.0), joints_n=len(joints),
                objects_offset_px=objs, objects_worst_m_at_the_wall=round(max(abs(x) for x in objs.values()) * 3.45 / (FX * (24 / 36)), 4) if objs else None,
                verticals_worst_tilt_deg=max(tilts) if tilts else None, verticals_pass_0_5=bool(tilts and max(tilts) <= 0.5),
                short_edges_tilt_deg=short_tilts,
                method=f"per line, segments of {seg} px; the across-line luminance profile of the image registered to the lit clay's (normalised "
                       "correlation of |d/dx|, sub-pixel); segments with correlation <= 0.5 dropped; offset = image - clay, px at 2720 x 1530; tilt = "
                       "slope of a line through the segment offsets (vs the clay, whose verticals are vertical)")


def warp(path, outp, rep=None):
    rep = rep or measure(path)
    img = np.asarray(Image.open(path).convert("RGB"))
    xs_src, xs_dst, ys_src, ys_dst = [0.0, W - 1.0], [0.0, W - 1.0], [0.0, H - 1.0], [0.0, H - 1.0]
    for name, v in rep["lines"].items():
        if not np.isfinite(v["median_offset_px"]) or name not in GATE:
            continue
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
    out = cv2.remap(img, np.repeat(mapx[None, :], H, 0), np.repeat(mapy[:, None], W, 1), cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    Image.fromarray(out).save(outp)
    return dict(x_knots_clay_to_image=[[round(a, 1), round(b, 1)] for a, b in zip(xd, xsrc)],
                y_knots_clay_to_image=[[round(a, 1), round(b, 1)] for a, b in zip(yd, ysrc)])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "measure":
        print(json.dumps(measure(sys.argv[2]), indent=1))
    elif cmd == "warp":
        print(json.dumps(warp(sys.argv[2], sys.argv[3]), indent=1))
        print(json.dumps(measure(sys.argv[3]), indent=1))
