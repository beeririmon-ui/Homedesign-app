#!/usr/bin/env python3
"""FB20 studio post (0 tokens): one backdrop for all, product untouched but for one global white balance.
Per raw: (1) coarse product mask against a smooth backdrop model (normalised convolution, 3 passes); (2) one global per-channel gain
that maps the lit backdrop to L* 92 / a* 1 / b* 7 (the camera's white balance and exposure: product and backdrop together);
(3) the backdrop's low-frequency shading compressed with distance from the product (gamma 1 within 25 px, 0.45 beyond 160 px), so the
contact shadow stays and the far backdrop goes uniform; (4) reframe: the product's bounding box to about 72% of the square, centred
(pendants: the cord kept to the top edge); new margins filled with the backdrop's border tone and grain. Out: 1024 x 1024."""
import json
import sys
import cv2
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from common import *  # noqa


def product_mask(rgb):
    h, w = rgb.shape[:2]
    k = 1024 / max(h, w)
    sm = cv2.resize(rgb, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    L = lab(sm)
    wgt = np.zeros(L.shape[:2], np.float32); b = 36
    wgt[:b], wgt[-b:], wgt[:, :b], wgt[:, -b:] = 1, 1, 1, 1
    tex = np.sqrt(np.clip(cv2.GaussianBlur(L[..., 0] ** 2, (0, 0), 2) - cv2.GaussianBlur(L[..., 0], (0, 0), 2) ** 2, 0, None))
    for _ in range(4):
        num = cv2.GaussianBlur(L * wgt[..., None], (0, 0), 70); den = cv2.GaussianBlur(wgt, (0, 0), 70)[..., None]
        B = num / np.maximum(den, 1e-4)
        d = np.sqrt((0.15 * (L[..., 0] - B[..., 0])) ** 2 + (L[..., 1] - B[..., 1]) ** 2 + (L[..., 2] - B[..., 2]) ** 2)
        prod = (d > 4.0) | (tex > 2.2) | (L[..., 0] < B[..., 0] - 38)
        wgt = (~cv2.dilate(prod.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)).astype(np.float32)
    m = cv2.morphologyEx(prod.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lb, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 0.004 * m.size: keep[lb == i] = 1
    ff = keep.copy(); cv2.floodFill(ff, None, (0, 0), 1); keep = keep | (1 - ff)   # fill holes
    keep = cv2.resize(keep, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    Bf = cv2.resize(B, (w, h), interpolation=cv2.INTER_LINEAR)
    wf = cv2.resize(wgt, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    return keep, Bf, wf


def process(raw, kind='flat', fill=0.72, max_up=1.25, shade_box=None, pre=None, restrict=False, sig_px=8, edge_px=40, t_px=(10, 60), keep_px=(12, 28)):
    rgb = load(raw) if pre is None else pre; h, w = rgb.shape[:2]
    m, B, bg = product_mask(rgb)
    if restrict and shade_box is not None:   # pendants and the frame: only the product's own box (and the cord above it) stays product
        e = 0.03
        x0b, y0b, x1b, y1b = int((shade_box[0] - e) * w), int((shade_box[1] - e) * h), int((shade_box[2] + e) * w), int((shade_box[3] + e) * h)
        keep = np.zeros_like(m); keep[max(0, y0b):y1b, max(0, x0b):x1b] = True
        if kind == 'pendant':
            cxb = int((shade_box[0] + shade_box[2]) / 2 * w); keep[:max(0, y0b), max(0, cxb - int(0.04 * w)):cxb + int(0.04 * w)] = True
        m = m & keep
    lin = to_lin(rgb)
    Lb = lab(rgb)[..., 0]
    sel = bg & (Lb >= np.percentile(Lb[bg], 40))
    c_ref = np.median(lin[sel], 0)
    g = TARGET_LIN / c_ref
    if kind == 'pendant':   # a lit lamp: the exposure only, no white balance, so the 2700 K glow stays as rendered
        gY = float(np.dot(TARGET_LIN, [0.2126, 0.7152, 0.0722]) / np.dot(c_ref, [0.2126, 0.7152, 0.0722]))
        g = np.full(3, gY, np.float32)
    lin_g = lin * g
    Y = np.maximum((lin_g * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1), 1e-6)
    Ys = np.where(Y > 0.82, 0.82 + 0.18 * (1 - np.exp(-(Y - 0.82) / 0.18)), Y)    # a soft shoulder: no highlight clips after the gain
    lin_g = lin_g * (Ys / Y)[..., None]
    lin_g = lin_g / np.maximum(1.0, lin_g.max(-1, keepdims=True))                   # no channel clips alone (a clipped red reads green-yellow)
    k = max(h, w) / 1024
    # the backdrop's own low-frequency shading (product pixels filled from around them), per channel, relative to the target
    bgw = (~cv2.dilate(m.astype(np.uint8), np.ones((int(5 * k),) * 2, np.uint8)).astype(bool)).astype(np.float32)
    sig = sig_px * k
    S = cv2.GaussianBlur(lin_g * bgw[..., None], (0, 0), sig) / np.maximum(cv2.GaussianBlur(bgw, (0, 0), sig), 1e-4)[..., None] / TARGET_LIN
    for _ in range(5):   # push the fill into the product's footprint
        S2 = cv2.GaussianBlur(S, (0, 0), 6 * sig)
        S = np.where(bgw[..., None] > 0, S, S2)
    dist = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) / k
    t = np.clip((dist - t_px[0]) / t_px[1], 0, 1); t = t * t * (3 - 2 * t)
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / k      # px (1024 scale) to the raw's border
    te = 1 - np.clip(edge / edge_px, 0, 1)
    t = np.maximum(t, te)                                                            # the field reaches the target at the raw's border
    field = TARGET_LIN * np.clip(S, 0.3, 1.6) ** (1 - t)[..., None]
    a = (1 - np.clip((dist - keep_px[0]) / keep_px[1], 0, 1)) * np.clip(edge / 6, 0, 1)
    out_lin = lin_g * a[..., None] + field * (1 - a[..., None])
    # reframe
    mm = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((max(3, int(9 * k)),) * 2, np.uint8))
    if shade_box is not None:
        bx = np.zeros_like(mm); bx[int(shade_box[1] * h):int(shade_box[3] * h), int(shade_box[0] * w):int(shade_box[2] * w)] = 1; mm = mm & bx
    ys, xs = np.nonzero(mm)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    up_cap = max_up / k
    if kind == 'pendant':
        s = min(fill * 1024 / (x1 - x0), up_cap); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        M = np.float32([[s, 0, 512 - s * cx], [0, s, min(0.0, 512 - s * cy)]])   # never down: the cord stays on the top edge
    else:
        s = min(fill * 1024 / max(x1 - x0, y1 - y0), up_cap); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        M = np.float32([[s, 0, 512 - s * cx], [0, s, 512 - s * cy]])
    o = cv2.warpAffine(out_lin.astype(np.float32), M, (1024, 1024), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=[float(v) for v in TARGET_LIN])
    a_o = cv2.warpAffine(a.astype(np.float32), M, (1024, 1024), flags=cv2.INTER_LINEAR, borderValue=0)
    cover = cv2.warpAffine(np.ones((h, w), np.float32), M, (1024, 1024), flags=cv2.INTER_LINEAR, borderValue=0)
    noise = np.random.default_rng(7).normal(0, 0.9 / 255, (1024, 1024, 1)).astype(np.float32) * (1 - a_o[..., None])
    o_s = np.clip(to_srgb(o) + noise, 0, 1)
    mo = cv2.warpAffine(m.astype(np.uint8), M, (1024, 1024), flags=cv2.INTER_NEAREST, borderValue=0).astype(bool)
    rec = dict(raw=raw, size=[w, h], gain=[round(float(v), 4) for v in g], backdrop_ref_lab=[round(float(v), 2) for v in lab(to_srgb(c_ref)[None, None].astype(np.float32))[0, 0]],
               scale=round(float(s), 4), bbox_raw=[int(x0), int(y0), int(x1), int(y1)])
    return o_s, mo, rec, m, rgb, to_srgb(lin_g)


def stats(o, mo):
    L = lab(o)
    bgm = ~cv2.dilate(mo.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    ys, xs = np.nonzero(mo)
    return dict(backdrop_lab=[round(float(v), 2) for v in np.median(L[bgm], 0)],
                fill=round(float(max(xs.max() - xs.min(), ys.max() - ys.min()) / 1024), 3),
                centre_px=[int((xs.max() + xs.min()) / 2), int((ys.max() + ys.min()) / 2)])


if __name__ == '__main__':
    raw, out = sys.argv[1], sys.argv[2]
    kind = sys.argv[3] if len(sys.argv) > 3 else 'flat'
    sb = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
    o, mo, rec, m, rgb, _ = process(raw, kind, shade_box=sb)
    save_png(out, o); rec.update(stats(o, mo)); print(json.dumps(rec))
