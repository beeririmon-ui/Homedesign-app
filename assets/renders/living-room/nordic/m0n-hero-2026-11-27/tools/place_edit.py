#!/usr/bin/env python3
"""place_edit.py: paste a nano-banana edit of a hero crop back into the hero, only inside its zones (render-agent, 2026-11-27).
  python3 place_edit.py <hero_in.png> <edit.jpg> <crop x0,y0,x1,y1> <zones x0,y0,x1,y1;...> <hero_out.png> [<diff_thr>]
The edit (returned larger) is registered to the crop by SIFT + RANSAC affine, tone-matched (per channel, linear fit on the pixels the
edit left alone), and pasted where it changed (low-passed difference over the threshold, dilated 6 px, feathered 3 px), inside the
zones only. Prints the registration residual and the pasted pixel count."""
import json
import sys

import cv2
import numpy as np
from PIL import Image


def main(hero_p, edit_p, crop, zones, out_p, thr=10.0):
    x0, y0, x1, y1 = map(int, crop.split(","))
    Hh = np.asarray(Image.open(hero_p).convert("RGB")).copy()
    C = Hh[y0:y1, x0:x1].copy()
    ch, cw = C.shape[:2]
    E = np.asarray(Image.open(edit_p).convert("RGB"))
    s = 2.0
    Cb = cv2.resize(C, (int(cw * s), int(ch * s)), interpolation=cv2.INTER_CUBIC)
    sift = cv2.SIFT_create(12000)
    g = lambda a: cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    k1, d1 = sift.detectAndCompute(g(E), None)
    k2, d2 = sift.detectAndCompute(g(Cb), None)
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, b in m if a.distance < 0.7 * b.distance]
    src = np.float32([k1[a.queryIdx].pt for a in good])
    dst = np.float32([k2[a.trainIdx].pt for a in good])
    A, inl = cv2.estimateAffine2D(src, dst, ransacReprojThreshold=2.0, maxIters=5000)
    res = float(np.median(np.linalg.norm((src @ A[:, :2].T + A[:, 2]) - dst, axis=1)[inl.ravel() > 0]))
    A2 = A.copy()
    A2 /= s                                     # into crop pixels
    Ew = cv2.warpAffine(E, A2, (cw, ch), flags=cv2.INTER_AREA if False else cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    Ef, Cf = Ew.astype(np.float32), C.astype(np.float32)
    zone = np.zeros((ch, cw), bool)
    for z in zones.split(";"):
        a, b, c, d = map(int, z.split(","))
        zone[max(b - y0, 0):max(d - y0, 0), max(a - x0, 0):max(c - x0, 0)] = True
    same = (np.abs(cv2.GaussianBlur(Ef, (0, 0), 2) - cv2.GaussianBlur(Cf, (0, 0), 2)).mean(-1) < thr) & ~zone
    for i in range(3):                         # tone match on the pixels the edit left alone
        p = np.polyfit(Ef[..., i][same], Cf[..., i][same], 1)
        Ef[..., i] = Ef[..., i] * p[0] + p[1]
    diff = np.abs(cv2.GaussianBlur(Ef, (0, 0), 2.5) - cv2.GaussianBlur(Cf, (0, 0), 2.5)).mean(-1)
    chg = (diff > thr) & zone
    chg = cv2.morphologyEx(chg.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    chg = cv2.dilate(chg, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) & zone.astype(np.uint8)
    a = cv2.GaussianBlur(chg.astype(np.float32), (0, 0), 3.0)[..., None] * zone[..., None]
    Hh[y0:y1, x0:x1] = np.clip(Cf * (1 - a) + Ef * a, 0, 255).astype(np.uint8)
    Image.fromarray(Hh).save(out_p)
    rec = dict(matches=len(good), inliers=int(inl.sum()), residual_px_at_x2=round(res, 3), pasted_px=int((a[..., 0] > 0.5).sum()))
    print(json.dumps(rec))
    np.save(out_p[:-4] + "-region.npy", np.array([x0, y0, x1, y1]))
    Image.fromarray(np.rint(a[..., 0] * 255).astype(np.uint8)).save(out_p[:-4] + "-mask.png")


if __name__ == "__main__":
    main(*sys.argv[1:6], *(float(x) for x in sys.argv[6:7]))
