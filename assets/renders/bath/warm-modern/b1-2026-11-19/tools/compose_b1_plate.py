#!/usr/bin/env python3
"""
compose_b1_plate.py: the B1 empty plate from the model's r1 (render-agent, 2026-11-19; 0 tokens). "The same house as B2".
The model exposed B1 for its bright window: the plaster of the window wall read L* 67 where B2, on the same strip of the same wall
(X 4.95-5.15), reads 88.4, and the floor 67 against 88. B2's plate took that strip's light from the clay (compose_plate.py step 2:
the clay's light as a ratio, times the model's own plaster), and the clay renders both frames with one exposure and one white
balance. So B1 gets its light the same way, at large scale only:
  1. a gain field in linear light: K x blur(clay Y) / blur(render Y), sigma 120 px (normalised convolution, off the fluted glass,
     which keeps the model's own pixels, feathered 6 px), clamped 1.0-2.4; K = 1.04, B2's own render / clay ratio on its plaster.
     Everything the model drew below 120 px (the trowel, the joints, the soft fall-off, the shadows) stays. The lift moves L* only:
     a*/b* stay the model's (a linear gain would push the stone to b* 23);
  2. the plaster's colour: the model warmed the window wall (b* 10.8 at L* 67, 14 after the lift) where B2's plaster reads a* 0.5-1.0,
     b* 3.9-6.3. On the plaster ids only (walls 1-4, the WC box 28, the reveals 32), the smooth a*/b* field (sigma 40, normalised
     over plaster) is moved to (0.8, 5.5); the plaster's own variation round it stays;
  3. no lock warp: the lock residuals are a few px and split both ways (records in plate-compose.json);
  4. the WM-G1 grade: B2's plate-grade.json curve, as grade_plate.py apply (the same curve for every asset of the bath).

  python3 compose_b1_plate.py
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools")
sys.path.insert(0, HERE)
import grade_plate as G  # noqa: E402
from b1proj import px  # noqa: E402

CL = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
B2 = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/"
K, SIG, GMAX, SIG_AB, AB = 1.04, 120, 2.4, 40, (0.8, 5.5)
PLASTER = (1, 2, 3, 4, 28, 32)
W3 = np.array([0.2126, 0.7152, 0.0722])


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def nblur(v, w, s):
    return cv2.GaussianBlur((v * w).astype(np.float32), (0, 0), s) / (cv2.GaussianBlur(w.astype(np.float32), (0, 0), s) + 1e-6)


REGIONS = {"window wall strip X 4.95-5.15 (B2: the repaired strip)": [(x, 9.951, z) for x in np.linspace(4.95, 5.15, 5) for z in np.linspace(1.1, 1.9, 5)],
           "vanity wall Y 11.25-11.6": [(6.249, y, z) for y in np.linspace(11.25, 11.6, 5) for z in np.linspace(1.0, 2.0, 5)]}


def regions(img, yaw):
    out = {}
    for n, pts in REGIONS.items():
        vals = []
        for p in pts:
            X, Y = [int(v) for v in px(*p, yaw)]
            if 80 <= X < 2640 and 45 <= Y < 1485:
                vals.append(img[Y - 4:Y + 4, X - 4:X + 4].reshape(-1, 3).mean(0))
        out[n] = [round(float(v), 1) for v in G.to_lab(np.array(vals)).mean(0)] if vals else None
    return out


def materials(img, ids):
    g = {"plaster, window wall (2)": (2,), "plaster, north wall (3)": (3,), "plaster, vanity wall (1)": (1,), "WC box (28)": (28,),
         "stone, east cladding (12)": (12,), "stone, south cladding (11)": (11,), "stone, floor (9)": (9,), "ledge slab (29)": (29,),
         "walnut (20, 21)": (20, 21), "bronze (15, 25, 27, 30)": (15, 25, 27, 30)}
    L = G.to_lab(img)
    return {n: [round(float(v), 1) for v in np.median(L[np.isin(ids, v)], 0)] for n, v in g.items() if np.isin(ids, v).sum() > 200}


def relight(r, c, ids, K=K, sig=SIG, gmax=GMAX, gmin=1.0):
    """step 1 on any B1 still: L* only, K x blur(clay Y) / blur(still Y), off the fluted glass; a*/b* stay the still's"""
    glass = cv2.dilate((ids == 31).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    w = (~glass).astype(np.float32)
    g = np.clip(K * nblur(lin(c) @ W3, w, sig) / np.maximum(nblur(lin(r) @ W3, w, sig), 1e-4), gmin, gmax)
    fe = cv2.GaussianBlur(glass.astype(np.float32), (0, 0), 6)
    g = g * (1 - fe) + fe
    L = G.to_lab(srgb(lin(r) * g[..., None]))
    L[..., 1:] = G.to_lab(r)[..., 1:]
    return G.from_lab(L), g


def plaster_ab(img, ids):
    """step 2 on any B1 still: the plaster's smooth a*/b* to (0.8, 5.5), its own variation kept"""
    glass = cv2.dilate((ids == 31).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    L = G.to_lab(img)
    pm = np.isin(ids, PLASTER) & ~glass
    for k, t in ((1, AB[0]), (2, AB[1])):
        f = nblur(L[..., k], pm, SIG_AB)
        L[..., k] = np.where(pm, L[..., k] + (t - f), L[..., k])
    return G.from_lab(L)


def main():
    r = np.asarray(Image.open(os.path.join(ST, "raw", "plate-r1.png")).convert("RGB")).astype(np.float64) / 255
    c = np.asarray(Image.open(CL + "B1-plate.png").convert("RGB")).astype(np.float64) / 255
    ids = np.asarray(Image.open(CL + "B1-plate-id.png"))
    rec = dict(raw=dict(materials=materials(r, ids), shared_regions=regions(r, -22.0)))
    glass = cv2.dilate((ids == 31).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    w = (~glass).astype(np.float32)
    g = np.clip(K * nblur(lin(c) @ W3, w, SIG) / np.maximum(nblur(lin(r) @ W3, w, SIG), 1e-4), 1.0, GMAX)
    fe = cv2.GaussianBlur(glass.astype(np.float32), (0, 0), 6)
    g = g * (1 - fe) + fe
    out = srgb(lin(r) * g[..., None])
    L = G.to_lab(out)
    L[..., 1:] = G.to_lab(r)[..., 1:]               # the lift is light only: a*/b* stay the model's (a linear gain would add chroma)
    pm = np.isin(ids, PLASTER) & ~glass
    for k, t in ((1, AB[0]), (2, AB[1])):
        f = nblur(L[..., k], pm, SIG_AB)
        L[..., k] = np.where(pm, L[..., k] + (t - f), L[..., k])
    out = G.from_lab(L)
    rec["step1_gain"] = dict(K=K, sigma=SIG, clamp=[1.0, GMAX], p5_p50_p95=[round(float(v), 3) for v in np.percentile(g, [5, 50, 95])])
    rec["step2_plaster_ab"] = dict(target=list(AB), sigma=SIG_AB, ids=list(PLASTER))
    o8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    Image.fromarray(o8).save(os.path.join(ST, "raw", "plate-relit.png"))
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    gr, info = G.curve_apply(o8.astype(np.float64) / 255, curve)
    g8 = np.clip(np.rint(gr * 255), 0, 255).astype(np.uint8)
    Image.fromarray(g8).save(os.path.join(ST, "plate.png"))
    x0, y0, x1, y1 = [int(round(v)) for v in G.FRAME]
    Image.fromarray(g8[y0:y1, x0:x1]).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, "plate-frame.png"))
    gf = g8.astype(np.float64) / 255
    Lg = G.to_lab(gf)[..., 0][y0:y1, x0:x1]
    b2 = np.asarray(Image.open(B2 + "plate.png").convert("RGB")).astype(np.float64) / 255
    rec["final"] = dict(materials=materials(gf, ids), shared_regions=regions(gf, -22.0), frame_p05_L=round(float(np.percentile(Lg, 5)), 2),
                        frame_p01_L=round(float(np.percentile(Lg, 1)), 2), frame_min_L=round(float(Lg.min()), 2))
    rec["b2_plate_same_regions"] = regions(b2, -57.0)
    rec["grade"] = dict(file="plate-grade.json (B2's, unchanged)", note="grade_plate.curve_apply, as grade_plate.py apply")
    lk = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/b1/plate-r1-lock.json"
    if os.path.exists(lk):
        d = json.load(open(lk))
        rec["lock_not_applied"] = dict(fit=d.get("fit"), lines={k: {kk: v.get(kk) for kk in ("n", "median_offset_px", "p90_abs_px", "mean_corr")}
                                                               for k, v in d.items() if isinstance(v, dict) and "n" in v and v.get("n")},
                                       why="the verticals split both ways (window -8, NE corner -1, cladding end +5): no single warp improves them")
    json.dump(rec, open(os.path.join(ST, "plate-compose.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(final=rec["final"], b2=rec["b2_plate_same_regions"], gain=rec["step1_gain"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
