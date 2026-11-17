#!/usr/bin/env python3
"""
compose_plate.py: the MB0 empty plate from the model's r1 (render-agent, 2026-11-17; 0 tokens). Three global steps, nothing local:
1. Lock: a global fit of the model's lines to the clay's (tools/lock_mb0.py on raw/plate-r1.png): y about the horizon (row 707.3) by a
   fitted offset and scale, x by the fitted constant (cv2.remap, bicubic).
2. One house (rejection list 7, chapter 9: the bed-wall plaster within +-3 L* of base.png's back wall): the model let the bed wall fall
   off from L* 90 at the left to 73 at the upper right (base.png: 91 -> 85.5). A smooth light field, fitted on the upper bed-wall
   plaster of the clay's id pass (log luminance, quadratic in x, linear in y), is flattened by half in log space toward its bright part;
   lift only (gain >= 1, at most +0.6 stop), one smooth field on every pixel (outside the fitted span the nearest wall value), linear
   light, chroma kept.
   The left stays as the model made it; the right keeps a gentle fall-off.
3. WM-G1 (black point L* 11-14; QA BP-M1 on the bath plate, the manager's ruling "the same curve on everything derived"): a toe on
   L* only, piecewise linear (0, 0) (p0.5, 12.5) (30, 30) (100, 100) on the 16:9 frame's p0.5; a* and b* kept; nothing above L* 30
   changes. The curve is recorded in plate-compose.json and must be applied to every layer derived from this plate (RND2).

  python3 compose_plate.py raw/plate-r1.png raw/plate-r1-lock.json plate.png plate-compose.json
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/"
HORIZON = 707.3
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
TARGET_BP, KNEE = 12.5, 30.0
FLATTEN, MAX_GAIN = 0.5, 2 ** 0.6

M3 = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def lab(rgb):
    xyz = lin(rgb) @ M3.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def rgb_from_lab(L):
    fy = (L[..., 0] + 16) / 116
    fx, fz = fy + L[..., 1] / 500, fy - L[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    return srgb(xyz @ np.linalg.inv(M3).T)


def fit_lock(lock):
    lt = json.load(open(CLAY + "lock-target.json"))
    ys, os_, ws, xo, xw = [], [], [], [], []
    for k, v in lock["lines"].items():
        if "median_offset_px" not in v or v["mean_corr"] < 0.6 or v["n"] < 8:
            continue
        s = [p for p in lt["lines"][k]["samples"] if p[2]]
        if v["kind"] == "horizontal":
            ys.append(np.mean([p[1] for p in s]))
            os_.append(v["median_offset_px"])
            ws.append(v["n"])
        else:
            xo.append(v["median_offset_px"])
            xw.append(v["n"])
    A = np.stack([np.ones(len(ys)), np.array(ys) - HORIZON], 1) * np.sqrt(ws)[:, None]
    a, b = np.linalg.lstsq(A, np.array(os_) * np.sqrt(ws), rcond=None)[0]
    c = float(np.median(np.repeat(xo, xw)))
    return float(a), float(b), c, dict(horizontal_lines=len(ys), vertical_lines=len(xo))


def light_field(rgbl, ids):
    """Fit log Y of the upper bed-wall plaster (id 1, eroded, rows 60-850: above the headboard and nightstand tops) with
    c0 + c1 x + c2 x^2 + c3 y + c4 x y; evaluate with x clamped to the fitted wall's span and y clamped to rows 60-850, so the window
    side, the floor and the bed foot take the field's nearest wall value; return the gain field and the record."""
    H, W = ids.shape
    wall = (ids == 1).astype(np.uint8)
    wall = cv2.erode(wall, np.ones((25, 25), np.uint8)).astype(bool)
    wall[:60] = False
    wall[850:] = False
    Y = rgbl @ np.array([0.2126, 0.7152, 0.0722])
    yy, xx = np.nonzero(wall)
    sel = np.arange(0, len(yy), 23)
    yy, xx = yy[sel], xx[sel]
    xn, yn = xx / W, yy / H
    A = np.stack([np.ones_like(xn), xn, xn * xn, yn, xn * yn], 1)
    coef = np.linalg.lstsq(A, np.log(np.maximum(Y[yy, xx], 1e-4)), rcond=None)[0]
    xlo, xhi = float(xn.min()), float(xn.max())
    gx, gy = np.meshgrid(np.clip(np.arange(W) / W, xlo, xhi), np.clip(np.arange(H), 60, 850) / H)
    F = coef[0] + coef[1] * gx + coef[2] * gx * gx + coef[3] * gy + coef[4] * gx * gy
    ref = float(np.percentile(A @ coef, 85))
    gain = np.clip(np.exp(FLATTEN * (ref - F)), 1.0, MAX_GAIN)
    return gain, dict(fit="log Y = c0 + c1 x + c2 x^2 + c3 y + c4 x y (canvas fractions) on the clay's bed-wall mask eroded 12 px, rows 60-850",
                      coef=[round(float(c), 5) for c in coef], x_span=[round(xlo, 4), round(xhi, 4)], rows_clamped=[60, 850],
                      reference_logY_p85=round(ref, 4), flatten=FLATTEN, max_gain=round(MAX_GAIN, 4),
                      gain_frame_min_max=[round(float(gain.min()), 4), round(float(gain.max()), 4)])


def main(raw, lockp, out, rec):
    im = np.asarray(Image.open(raw).convert("RGB")).astype(np.float32) / 255
    H, W = im.shape[:2]
    ids = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    a, b, c, nl = fit_lock(json.load(open(lockp)))
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    map_y = gy + a + b * (gy - HORIZON)
    map_x = gx + c
    warped = cv2.remap(im, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    warped = np.clip(warped, 0, 1).astype(np.float64)
    rgbl = lin(warped)
    gain, frec = light_field(rgbl, ids)
    out_l = np.clip(rgbl * gain[..., None], 0, 1)
    rgb2 = srgb(out_l)
    L = lab(rgb2)
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    p05 = float(np.percentile(L[y0:y1, x0:x1, 0], 0.5))
    toe = p05 < 11.0 or p05 > 14.0
    if toe:
        m = L[..., 0] < KNEE
        L2 = L.copy()
        L2[..., 0] = np.interp(L[..., 0], [0.0, p05, KNEE, 100.0], [0.0, TARGET_BP, KNEE, 100.0])
        rgb2 = rgb2.copy()
        rgb2[m] = rgb_from_lab(L2[m])
    after = float(np.percentile(lab(rgb2[y0:y1, x0:x1])[..., 0], 0.5))
    Image.fromarray(np.clip(np.rint(rgb2 * 255), 0, 255).astype(np.uint8)).save(out)
    fr = Image.fromarray(np.clip(np.rint(rgb2 * 255), 0, 255).astype(np.uint8)).crop((FRAME[0], FRAME[1], FRAME[2], FRAME[3])).resize((1920, 1080), Image.LANCZOS)
    fr.save(out.replace(".png", "-frame.png"))
    np.save("/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/plate-gain.npy", gain.astype(np.float32))
    rep = dict(source=raw, out=out, steps=[
        dict(step=1, what="lock warp", y_offset_px=round(a, 3), y_scale_about_horizon=round(1 + b, 5), horizon_row=HORIZON, x_offset_px=round(c, 3),
             lines_used=nl, rule="locked(x, y) = raw(x + c, y + a + b (y - horizon)); bicubic"),
        dict(step=2, what="one house: the bed wall's fall-off flattened by half toward its bright part (lift only)", **frec),
        dict(step=3, what="WM-G1 toe on L* (a*, b* kept)", applied=toe, p05_before=round(p05, 2), p05_after=round(after, 2), knee=KNEE,
             curve="(0, 0) (p05_before, 12.5) (30, 30) (100, 100), piecewise linear on L*; apply the same curve to every derived layer (RND2)")])
    json.dump(rep, open(rec, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
