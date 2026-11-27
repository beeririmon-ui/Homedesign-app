#!/usr/bin/env python3
"""prints.py: the Morandi triptych prints (SKU framed-art-cj-morandi-triptych-sage, style D, the in-room SKU photo) into the hero's
three blank canvases, lit by the canvas itself (render-agent, 2026-11-27). 0 tokens.
  python3 prints.py <hero_in.png> <sku_photo.jpg> <hero_out.png>
1. the prints are warped out of the SKU photo (hand-picked quads of the 800 px photo, 2 % inset: no frame sliver);
2. each canvas is found in the hero as the hole inside a dark frame (L* < 30, ROI x 0.40-0.72, y 0.22-0.52), as a 4-corner quad;
3. print -> quad (perspective), out = print * canvas_light / paper, canvas_light = the canvas blurred 2 px, paper = the print's own
   paper colour (its median brightest third): the paper reads exactly as the canvas the model drew (sun bars and shade kept)."""
import json
import sys

import cv2
import numpy as np
from PIL import Image

QUADS = {"L": [(155, 173), (317, 185), (317, 418), (155, 421)], "M": [(351, 194), (484, 202), (484, 413), (351, 416)],
         "R": [(515, 209), (625, 216), (625, 409), (515, 413)]}


def main(hero_p, sku_p, out_p):
    H = np.asarray(Image.open(hero_p).convert("RGB")).copy()
    h, w = H.shape[:2]
    sku = np.asarray(Image.open(sku_p).convert("RGB"))
    PW, PH = 460, 660
    prints = []
    for k in ("L", "M", "R"):
        q = np.float32(QUADS[k])
        c = q.mean(0)
        q = c + (q - c) * 0.96
        M = cv2.getPerspectiveTransform(q, np.float32([(0, 0), (PW, 0), (PW, PH), (0, PH)]))
        prints.append(cv2.warpPerspective(sku, M, (PW, PH), flags=cv2.INTER_LANCZOS4))
    x0, x1, y0, y1 = int(0.40 * w), int(0.72 * w), int(0.22 * h), int(0.52 * h)
    roi = H[y0:y1, x0:x1]
    L = cv2.cvtColor(roi, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) * 100 / 255
    dark = (L < 30).astype(np.uint8)
    cs, hier = cv2.findContours(dark, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = []
    for i, c in enumerate(cs):
        if hier[0][i][3] >= 0 and cv2.contourArea(c) > 0.004 * roi.shape[0] * roi.shape[1]:
            holes.append(c)
    holes = sorted(holes, key=lambda c: cv2.boundingRect(c)[0])[:3]
    if len(holes) != 3:
        raise SystemExit(f"found {len(holes)} canvases")
    rec = []
    out = H.astype(np.float32)
    for c, pr in zip(holes, prints):
        hull = cv2.convexHull(c)
        ap = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True).reshape(-1, 2).astype(np.float32)
        if len(ap) != 4:
            x, y, ww, hh = cv2.boundingRect(c)
            ap = np.float32([(x, y), (x + ww, y), (x + ww, y + hh), (x, y + hh)])
        s = ap.sum(1)
        d = np.diff(ap, axis=1).ravel()
        quad = np.float32([ap[np.argmin(s)], ap[np.argmin(d)], ap[np.argmax(s)], ap[np.argmax(d)]]) + np.float32([x0, y0])
        quad_in = quad.copy()
        M = cv2.getPerspectiveTransform(np.float32([(0, 0), (PW, 0), (PW, PH), (0, PH)]), quad_in)
        warped = cv2.warpPerspective(pr.astype(np.float32), M, (w, h), flags=cv2.INTER_AREA if False else cv2.INTER_LINEAR)
        mask = cv2.warpPerspective(np.ones((PH, PW), np.float32), M, (w, h), flags=cv2.INTER_LINEAR)
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
        light = cv2.GaussianBlur(H.astype(np.float32), (0, 0), 2.0)
        lum = pr.astype(np.float32).mean(-1)
        paper = np.median(pr.reshape(-1, 3)[lum.ravel() > np.percentile(lum, 66)], 0)
        lit = warped * light / np.maximum(paper, 1)
        a = cv2.GaussianBlur(mask, (0, 0), 0.6)[..., None]
        out = out * (1 - a) + lit * a
        rec.append(dict(quad=[[round(float(v), 1) for v in p] for p in quad], paper_rgb=[round(float(v), 1) for v in paper], px=int((mask > 0.5).sum())))
    Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8)).save(out_p)
    json.dump(rec, open(out_p[:-4] + "-prints.json", "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(*sys.argv[1:4])
