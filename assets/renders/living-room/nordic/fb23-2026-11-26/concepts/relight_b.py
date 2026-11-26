#!/usr/bin/env python3
"""
relight_b.py: the input of concept B's retry (render-agent, 2026-11-26). 0 var2 tokens.
Concept A's returned photograph (raw/concept-A-flux2-r1.jpg) re-lit in code by the clay's own light ratio, so A and B keep ONE styling and
differ only in the light (the warm-modern retry method, fb13 concepts/guide_b2.py):
  1. guide-A.png and guide-B.png (written by ../clay_m0n.py, then floor-fixed; only their JPEG copies concept-A-input.jpg / concept-B-input.jpg are kept; the same material render, light groups: A = sky + lamps, B = sky + 0.2748 sun + lamps) are taken back to
     display-linear (the inverse of clay_m0n.tone with each lift); R = B / A per channel, blurred 1.2 px, clipped to [0.2, 8];
  2. guide-A is registered to the photograph (SIFT + RANSAC homography) and R is warped into the photograph's frame;
  3. photo-linear x R, then the same soft shoulder as the clay (0.72) and sRGB;
  4. two flux-2 inventions of concept A are taken out on the right (a side table where the floor lamp stands, a dark vase with pampas grass:
     both outside the product list), by inpainting, and the floor lamp of guide-B (the ids pass, index 807) is put back at its place.
  python3 -P relight_b.py            # writes concept-B-retry-input.png (1344 x 768) and relight_b.json
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LIFT = {"A": 0.006, "B": 0.013}
SHOULDER = 0.72
CUT = {"side table (flux-2 invention, where the floor lamp stands)": (1005, 478, 1082, 615),
       "pampas grass (flux-2 invention)": (1219, 375, 1344, 515), "dark vase (flux-2 invention)": (1258, 505, 1310, 622)}


def dec(s):
    s = s.astype(np.float32) / 255.0
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def enc(y):
    y = np.clip(y, 0, 1)
    return np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)


def untone(img, lift):
    y = (dec(img) - lift) / (1 - lift)
    y = np.clip(y, 0, 0.9995)
    return np.where(y < SHOULDER, y, SHOULDER - (1 - SHOULDER) * np.log(1 - (y - SHOULDER) / (1 - SHOULDER)))


def shoulder(x):
    return np.where(x < SHOULDER, x, SHOULDER + (1 - SHOULDER) * (1 - np.exp(-(x - SHOULDER) / (1 - SHOULDER))))


def main():
    gA = np.asarray(Image.open(os.path.join(HERE, "guide-A.png")).convert("RGB"))
    gB = np.asarray(Image.open(os.path.join(HERE, "guide-B.png")).convert("RGB"))
    ph = np.asarray(Image.open(os.path.join(HERE, "raw", "concept-A-flux2-r1.jpg")).convert("RGB"))
    H, W = ph.shape[:2]
    xa, xb = untone(gA, LIFT["A"]), untone(gB, LIFT["B"])
    bl = lambda x: cv2.GaussianBlur(x, (0, 0), 1.2)
    R = np.clip(bl(xb) / np.maximum(bl(xa), 1e-4), 0.2, 8.0).astype(np.float32)
    # registration: guide-A (1920 x 1080) -> the photograph (1344 x 768)
    sift = cv2.SIFT_create(6000)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(gA, cv2.COLOR_RGB2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(ph, cv2.COLOR_RGB2GRAY), None)
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, c in m if a.distance < 0.75 * c.distance]
    src = np.float32([k1[a.queryIdx].pt for a in good])
    dst = np.float32([k2[a.trainIdx].pt for a in good])
    Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    res = np.linalg.norm(cv2.perspectiveTransform(src[inl.ravel() > 0][None], Hm)[0] - dst[inl.ravel() > 0], axis=1)
    Rw = cv2.warpPerspective(R, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    out = shoulder(dec(ph) * Rw)
    # the right side: inventions out (inpaint on the re-lit image), the floor lamp of guide-B back in
    u8 = np.clip(np.rint(enc(out) * 255), 0, 255).astype(np.uint8)
    mask = np.zeros((H, W), np.uint8)
    for (x0, y0, x1, y1) in CUT.values():
        mask[y0:y1, x0:x1] = 255
    u8 = cv2.inpaint(u8, mask, 9, cv2.INPAINT_TELEA)
    rng = np.random.default_rng(11)                         # clay_m0n.ids_png's LUT
    lut = rng.integers(40, 255, (1024, 3)).astype(np.uint8)
    ids = np.asarray(Image.open(os.path.join(HERE, "..", "m0n-ids.png")).convert("RGB"))
    lamp = (ids == lut[807]).all(-1).astype(np.float32)
    lamp_w = cv2.warpPerspective(lamp, Hm, (W, H), flags=cv2.INTER_LINEAR)
    lamp_w = cv2.GaussianBlur(lamp_w, (0, 0), 0.6)[..., None]
    gBw = cv2.warpPerspective(gB, Hm, (W, H), flags=cv2.INTER_LINEAR)
    u8 = np.clip(np.rint(u8 * (1 - lamp_w) + gBw * lamp_w), 0, 255).astype(np.uint8)
    Image.fromarray(u8).save(os.path.join(HERE, "concept-B-retry-input.png"), optimize=True)
    Image.fromarray(u8).save(os.path.join(HERE, "concept-B-retry-input.jpg"), quality=90)
    rec = dict(homography_guide1920_to_photo1344=Hm.tolist(), sift_matches=len(good), inliers=int(inl.sum()),
               median_residual_px=round(float(np.median(res)), 3), ratio_clip=[0.2, 8.0], blur_px=1.2, shoulder=SHOULDER, lifts=LIFT,
               cut_boxes_photo_px=CUT, lamp_px=int((lamp_w[..., 0] > 0.5).sum()),
               ratio_stats=dict(p1=float(np.percentile(Rw, 1)), median=float(np.median(Rw)), p99=float(np.percentile(Rw, 99))))
    json.dump(rec, open(os.path.join(HERE, "relight_b.json"), "w"), indent=1)
    print(json.dumps({k: rec[k] for k in ("sift_matches", "inliers", "median_residual_px", "lamp_px", "ratio_stats")}))


if __name__ == "__main__":
    main()
