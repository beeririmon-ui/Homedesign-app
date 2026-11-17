#!/usr/bin/env python3
"""
fix_sill.py: MP-D2 / 12.6 4(b), the sill slab's front edge honed (render-agent, 2026-11-17; 0 tokens). Step 4 of compose_plate.py.
The model gave the 4 cm limestone slab a rock-faced (chipped, pitted) front edge. The house stone is honed everywhere else. Only
inside the clay's slab mask (MB0-plate-id.png, id 14, dilated 6 px for the shadow line under the nose), in L*a*b*:
  - the edges: the two analytic lines of the slab's front face (lock-target.json: 'sill slab, top front edge (Z 0.75)' and
    'bottom front edge (Z 0.71)', extended along their own slope), so both edges are straight and the face is exactly 4 cm; the
    model's own edges are measured column by column and recorded (they sat about 2 px inside each line: a face of about 3.5 cm);
  - the face (between the lines, anti-aliased): the model's own face tone per column, robust (the 40-85 % of L* only, so chips and
    pits drop out), smoothed along x over 61 px, with the model's own median vertical profile (clipped to +-3 L*), and a fine grain
    taken from the model's own top surface 1 face-height + 10 px above (high pass sigma 2, clipped to +-3 L*, x0.8); the face's
    a* b* half way to hdx.png's limestone in shade (3.3, 16.5);
  - the arris: a thin light line along the top edge (the eased honed corner catching the sky), at the top surface's tone;
  - the top surface's last 5 rows above the edge: chip pixels (more than 6 L* under the local top tone) refilled from the top tone
    and grain; every other pixel there unchanged;
  - the line under the nose: rows yb..yb+4 rebuilt as a soft shadow from the model's own shadow minimum to its own wall below.
Faded to the plate over the slab's last 14 px at the reveal (x 431-445). Nothing outside the dilated mask changes.

  python3 fix_sill.py <in.png> <out.png> <out.json>        (standalone; compose_plate.py calls fix() as step 4)
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/"
M3 = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
X_END, FADE = 445, 14
HDX_SHADE = (3.3, 16.5)               # hdx.png's limestone in shade (a*, b*), as the bath's prep_plate.py


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


def line(name):
    lt = json.load(open(CLAY + "lock-target.json"))
    (x0, y0), (x1, y1) = lt["lines"][name]["px_ends"]
    k = (y1 - y0) / (x1 - x0)
    return lambda x: y0 + (np.asarray(x, float) - x0) * k, k


def smooth1d(v, w):
    v = np.asarray(v, float)
    pad = np.pad(v, w // 2, mode="edge")
    return np.convolve(pad, np.ones(w) / w, mode="valid")[: len(v)]


def fix(rgb):
    ids = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    H, W = ids.shape
    Lab = lab(rgb)
    L = Lab[..., 0]
    top_a, kt = line("sill slab, top front edge (Z 0.75)")
    bot_a, kb = line("sill slab, bottom front edge (Z 0.71)")
    xs = np.arange(0, X_END + 1)
    # ---- detect, then keep the analytic slope with the median offset ----
    dt, db = [], []
    for x in xs:
        ya, yb = top_a(x), bot_a(x)
        col = L[:, x]
        ltop = np.median(col[int(ya) - 14:int(ya) - 5])
        lface = np.median(col[int(ya) + 6:int(yb) - 3])
        mid = (ltop + lface) / 2
        for y in range(int(ya) - 6, int(ya) + 9):
            if col[y] < mid:
                dt.append(y - 0.5 - ya)
                break
        prof = np.convolve(col[int(yb) - 6:int(yb) + 7], np.ones(3) / 3, mode="same")
        db.append(int(yb) - 6 + int(np.argmin(prof[1:-1])) + 1 - yb)
    ot, ob = float(np.median(dt)), float(np.median(db))
    yt = top_a(xs)                    # the clay's lines: the face reads exactly 4 cm (the model's face sat 2 px inside each line)
    ybt = bot_a(xs)
    # ---- tones per column ----
    face_tone = np.zeros((len(xs), 3))
    top_tone = np.zeros((len(xs), 3))
    shadow_L = np.zeros(len(xs))
    wall_tone = np.zeros((len(xs), 3))
    prof_rows = []
    for i, x in enumerate(xs):
        t0, t1 = yt[i], ybt[i]
        top_tone[i] = np.median(Lab[int(t0) - 14:int(t0) - 5, x], 0)
        f = Lab[int(np.ceil(t0)) + 3:int(t1) - 2, x]
        lo, hi = np.percentile(f[:, 0], [40, 85])
        sel = f[(f[:, 0] >= lo) & (f[:, 0] <= hi)]
        face_tone[i] = np.median(sel if len(sel) else f, 0)
        shadow_L[i] = np.min(np.convolve(L[int(t1) - 2:int(t1) + 6, x], np.ones(3) / 3, mode="valid"))
        wall_tone[i] = np.median(Lab[int(t1) + 7:int(t1) + 14, x], 0)
        hgt = t1 - t0
        rows = np.arange(int(np.ceil(t0)), int(t1))
        prof_rows += [((r - t0) / hgt, L[r, x] - face_tone[i, 0]) for r in rows]
    for c in range(3):
        face_tone[:, c] = smooth1d(cv2.medianBlur(face_tone[:, c].astype(np.float32).reshape(-1, 1), 5).ravel(), 61)
        top_tone[:, c] = smooth1d(top_tone[:, c], 31)
        wall_tone[:, c] = smooth1d(wall_tone[:, c], 31)
    shadow_L = smooth1d(shadow_L, 31)
    face_tone[:, 1] = 0.5 * face_tone[:, 1] + 0.5 * HDX_SHADE[0]      # the face's chroma half way to the house stone in shade
    face_tone[:, 2] = 0.5 * face_tone[:, 2] + 0.5 * HDX_SHADE[1]
    pr = np.array(prof_rows)
    bins = np.linspace(0, 1, 11)
    vprof = np.array([np.median(pr[(pr[:, 0] >= a) & (pr[:, 0] < b), 1]) if ((pr[:, 0] >= a) & (pr[:, 0] < b)).any() else 0.0
                      for a, b in zip(bins[:-1], bins[1:])])
    vprof = np.clip(smooth1d(vprof, 3), -3, 3)
    # ---- grain from the top surface ----
    hp = L - cv2.GaussianBlur(L.astype(np.float32), (0, 0), 2.0)
    hp = np.clip(hp, -3.0, 3.0) * 0.8
    out = Lab.copy()
    for i, x in enumerate(xs):
        t0, t1 = yt[i], ybt[i]
        hgt = t1 - t0
        shift = int(round(hgt + 10))
        y_lo, y_hi = int(np.floor(t0)) - 5, int(np.ceil(t1)) + 5
        for y in range(y_lo, y_hi + 1):
            orig = out[y, x].copy()
            top = orig
            if y >= t0 - 5 and orig[0] < top_tone[i, 0] - 6:                               # chip on the top surface's last rows
                top = top_tone[i].copy()
                top[0] += hp[y - 6, x]
            face = face_tone[i].copy()
            face[0] += np.interp((y - t0) / hgt, (bins[:-1] + bins[1:]) / 2, vprof) + hp[y - shift, x]
            arris = np.array([top_tone[i, 0], top_tone[i, 1], top_tone[i, 2]])
            shade = np.array([shadow_L[i], wall_tone[i, 1], wall_tone[i, 2]])
            acc = np.zeros(3)
            for yy in (y - 0.375, y - 0.125, y + 0.125, y + 0.375):                         # 4 sub-rows: clean anti-aliasing
                if yy < t0:
                    acc += top
                elif yy < t0 + 1.0:                                                          # the arris: a thin line of light
                    acc += arris
                elif yy <= t1:
                    acc += face
                else:                                                                        # under the nose: soft shadow to the wall
                    k = min(1.0, (yy - t1) / 5.0) ** 1.5
                    acc += shade * (1 - k) + orig * k
            out[y, x] = acc / 4
    # ---- restrict to the clay mask (dilated 6 px) and fade at the reveal end ----
    m = cv2.dilate((ids == 14).astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
    m[:, X_END + 1:] = False
    w = np.zeros((H, W))
    w[m] = 1.0
    for x in range(X_END - FADE, X_END + 1):
        w[:, x] *= np.clip((X_END - x) / FADE, 0, 1)
    new = rgb_from_lab(out)
    res = rgb * (1 - w[..., None]) + new * w[..., None]
    changed = int((np.abs(np.rint(res * 255) - np.rint(rgb * 255)).max(-1) > 0).sum())
    outside = int(((np.abs(np.rint(res * 255) - np.rint(rgb * 255)).max(-1) > 0) & ~m).sum())
    rec = dict(what="MP-D2: the sill slab's front edge honed and straight (12.6 4(b)); in the clay's slab mask (id 14, dilated 6 px)",
               edges=dict(used="the clay's two analytic lines (lock-target.json), extended along their slopes: the face is exactly 4 cm",
                          detected_top_offset_px=round(ot, 2), detected_bottom_offset_px=round(ob, 2), slope_top=round(kt, 5), slope_bottom=round(kb, 5),
                          note="the model's own edges sat this far from the clay's lines (median over columns 0-445): its face read about 3.5 cm"),
               face_height_px=dict(at_x_75=round(float(ybt[75] - yt[75]), 1), at_x_220=round(float(ybt[220] - yt[220]), 1),
                                   at_x_430=round(float(ybt[430] - yt[430]), 1)),
               face_tone_Lab_median=[round(float(v), 1) for v in np.median(face_tone, 0)],
               top_tone_Lab_median=[round(float(v), 1) for v in np.median(top_tone, 0)],
               vertical_profile_L=[round(float(v), 2) for v in vprof], changed_px=changed, changed_outside_mask_px=outside,
               fade=f"x {X_END - FADE}-{X_END}")
    return res, rec


def main(src, dst, recp):
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float64) / 255
    res, rec = fix(rgb)
    Image.fromarray(np.clip(np.rint(res * 255), 0, 255).astype(np.uint8)).save(dst)
    json.dump(rec, open(recp, "w"), indent=1)
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
