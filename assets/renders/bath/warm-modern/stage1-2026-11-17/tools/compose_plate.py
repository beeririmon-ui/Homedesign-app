#!/usr/bin/env python3
"""
compose_plate.py: the B2 empty plate from the model's r1 (render-agent, 2026-11-17; 0 tokens).
1. Lock: a global affine fit of the model's lines to the clay's (lock_b2.py on raw/plate-r1.png): seedream squeezed the frame
   vertically about the horizon (row 707) by about 1 % (the shelf 8 px high, the niche head 3 px low) and shifted it 1-2 px left.
   One smooth warp: y about the horizon by the fitted scale, x by the fitted constant (cv2.remap, bicubic). Nothing local.
2. The left strip (rejection list 1 and 7.3, B2 has no window, S10): the model read the bare plaster of the window wall
   (X 4.92-5.20, the clay's id 2, and its stone skirting, id 5 left of x 330) as a tall fluted window with a white reveal.
   Repaired from the model's own plaster and the clay's light, inside the clay's mask only:
   - the light: the clay B2-plate's luminance in the mask, as a ratio to the clay's plaster on the vanity wall (rows 250-1050,
     x 2250-2600), times the model's own plaster there (linear light);
   - the grain: seamless noise with the model's own plaster statistics there (fine grain and the soft trowel movement);
   - the skirting (limestone 8 cm): the model's own cladding stone near the floor, shaded by the clay (skirting / cladding).
   The cladding edge stays the model's (x 272 in the clay); the mask is dilated 2 px to the left of it only where the model is
   brighter than its stone (the white reveal's last pixels).
3. The bronze: chroma moved to base.png's bronze-espresso window frames (see the code), on the model's own bronze pixels only.

  python3 compose_plate.py raw/plate-r1.png <lock.json> plate.png plate-compose.json
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/"
HORIZON = 707.0
REF = (slice(250, 1050), slice(2250, 2600))


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


M3 = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])


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


def fit(lock):
    lt = json.load(open(CLAY + "lock-target.json"))
    ys, os_, ws, xo, xw = [], [], [], [], []
    for k, v in lock["lines"].items():
        if "median_offset_px" not in v or v["mean_corr"] < 0.6:
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
    c = float(np.average(xo, weights=xw))
    return float(a), float(b), c, dict(horizontal_lines=len(ys), vertical_lines=len(xo))


def main(raw, lockp, out, rec):
    im = np.asarray(Image.open(raw).convert("RGB")).astype(np.float32) / 255
    H, W = im.shape[:2]
    a, b, c, used = fit(json.load(open(lockp)))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    map_y = yy + a + b * (yy - HORIZON)            # the still's line sits at clay + offset(y): sample there
    map_x = xx + c
    w = cv2.remap(im, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    w = np.clip(w, 0, 1)
    ids = np.asarray(Image.open(CLAY + "B2-plate-id.png"))
    clay = np.asarray(Image.open(CLAY + "B2-plate.png").convert("RGB")).astype(np.float32) / 255
    xs = np.arange(W)[None, :]
    mask = (ids == 2) | ((ids == 5) & (xs < 330))
    skirt = (ids == 5) & (xs < 330)
    # light from the clay, level and colour from the model's plaster on the vanity wall
    cl = lin(clay) @ [0.2126, 0.7152, 0.0722]
    ref_m = (ids[REF] == 1)
    clay_ref = float(np.median(cl[REF][ref_m]))
    model_ref = np.median(lin(w)[REF][ref_m], 0)
    ratio = cl / clay_ref
    fill = ratio[..., None] * model_ref[None, None, :]
    # the grain: seamless noise with the statistics of the model's own plaster (fine grain sigma 1.2 px, trowel movement sigma 28 px)
    g = cv2.cvtColor(w, cv2.COLOR_RGB2GRAY)[REF]
    fine_sd = float(np.std((g - cv2.GaussianBlur(g, (0, 0), 3))[ref_m]))
    mid = cv2.GaussianBlur(g, (0, 0), 3) - cv2.GaussianBlur(g, (0, 0), 40)
    mid_sd = float(np.std(mid[ref_m]))
    rng = np.random.default_rng(20261117)
    n1 = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 1.2)
    n2 = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 28)
    n1 *= 0.5 * fine_sd / max(float(n1.std()), 1e-6)            # half: limewash is smoother than the model's sharpened grain
    n2 *= min(mid_sd, 0.012) / max(float(n2.std()), 1e-6)
    fill = srgb(fill) + (n1 + n2)[..., None]
    # the skirting: limestone 8 cm, the model's own cladding stone near the floor, shaded by the clay (skirting / cladding)
    st_ref = (ids == 12) & (np.arange(H)[:, None] > 1150) & (np.arange(H)[:, None] < 1330)
    if st_ref.any():
        st_col = np.median(lin(w)[st_ref], 0)
        st_clay = float(np.median(cl[st_ref]))
        fill[skirt] = srgb(cl[skirt][:, None] / st_clay * st_col[None, :])
    # the last bright pixels of the model's white reveal just left of the cladding edge
    edge = np.zeros_like(mask)
    for y in range(H):
        r = np.nonzero(ids[y] == 2)[0]
        if len(r):
            x1 = r.max()
            edge[y, max(0, x1 - 1):x1 + 3] = (w[y, max(0, x1 - 1):x1 + 3].mean(1) > np.median(w[y, x1 + 6:x1 + 30], 0).mean() + 0.06)
    m = mask | edge
    outp = w.copy()
    outp[m] = fill[m]
    # 3. the bronze (shell fittings 15, mirror profile 18, tap 25): seedream made it a warm copper-bronze (Lab about 27 / 6 / 14);
    #    the house's bronze-espresso is base.png's window frames (22.5 / 4.2 / 6.8). Inside the clay masks dilated 3 px, only on the
    #    model's own bronze pixels (L* < 50, b* > 4), the chroma is moved to the house value and L* down 3; the shading is kept.
    br = cv2.dilate(np.isin(ids, (15, 18, 25)).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    Lb = lab(outp)
    sel = br & (Lb[..., 0] < 50) & (Lb[..., 2] > 4)
    wgt = np.clip((50 - Lb[..., 0]) / 10, 0, 1)[sel]
    med = np.median(Lb[sel], 0)
    Lb[sel, 1] = Lb[sel, 1] + (4.2 - med[1]) * wgt
    Lb[sel, 2] = Lb[sel, 2] + (6.8 - med[2]) * wgt
    Lb[sel, 0] = Lb[sel, 0] - 3.0 * wgt
    outp[sel] = rgb_from_lab(Lb[sel])
    bronze = dict(px=int(sel.sum()), model_median_Lab=[round(float(v), 1) for v in med], target_ab=[4.2, 6.8], L_down=3.0)
    Image.fromarray(np.clip(np.rint(outp * 255), 0, 255).astype(np.uint8)).save(out)
    json.dump(dict(raw=raw, lock=lockp, warp=dict(y_offset_px=round(a, 3), y_scale_about_row_707=round(b, 6), x_offset_px=round(c, 3), used=used,
                                                   note="out(x, y) = raw(x + x_offset, y + y_offset + y_scale * (y - 707))"),
                   left_strip=dict(mask_px=int(mask.sum()), edge_px=int(edge.sum()), skirting_px=int(skirt.sum()),
                                   model_plaster_ref_lin=[round(float(v), 4) for v in model_ref], clay_ref_lin=round(clay_ref, 4)),
                   bronze=bronze, outside_the_masks="the warped r1, unchanged"), open(rec, "w"), indent=1)
    print("warp a", a, "b", b, "c", c, "mask", int(mask.sum()), "edge", int(edge.sum()))


if __name__ == "__main__":
    main(*sys.argv[1:5])
