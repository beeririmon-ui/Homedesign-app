#!/usr/bin/env python3
"""Colour fixes toward the SKU photos (0 tokens), on the final 1024 images, product pieces only:
set-A lumbar (milk-tea): chroma x0.3 (the render drew it peach; the SKU is a pale greige); set-C corduroy (dark coffee): x3 linear
(the render drew it near-black; the SKU is a rich rust brown; the other set-C pieces sit at the SKU's exposure); pink bedspread: b* toward
the SKU's warmer pink. Piece masks: grok segment-map cutouts (free) located in the raw by template match, moved like the post moved the raw."""
import json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
META = json.load(open('out/meta.json'))


def locate(raw, cut_png):
    img = cv2.imread(raw).astype(np.float32); cut = cv2.imread(cut_png, cv2.IMREAD_UNCHANGED).astype(np.float32)
    t, a = cut[..., :3], (cut[..., 3] > 127).astype(np.float32); q = 8
    r = cv2.matchTemplate(cv2.resize(img, None, fx=1 / q, fy=1 / q, interpolation=cv2.INTER_AREA), cv2.resize(t, None, fx=1 / q, fy=1 / q, interpolation=cv2.INTER_AREA),
                          cv2.TM_SQDIFF, mask=cv2.resize(a, None, fx=1 / q, fy=1 / q))
    x, y = cv2.minMaxLoc(r)[2]; x, y = x * q, y * q; best = None
    for dy in range(-q, q + 1, 2):
        for dx in range(-q, q + 1, 2):
            X, Y = x + dx, y + dy
            if X < 0 or Y < 0 or X + t.shape[1] > img.shape[1] or Y + t.shape[0] > img.shape[0]: continue
            e = (((img[Y:Y + t.shape[0], X:X + t.shape[1]] - t) ** 2).sum(-1) * a).sum() / a.sum()
            if best is None or e < best[0]: best = (e, X, Y)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            X, Y = best[1] + dx, best[2] + dy
            if X < 0 or Y < 0 or X + t.shape[1] > img.shape[1] or Y + t.shape[0] > img.shape[0]: continue
            e = (((img[Y:Y + t.shape[0], X:X + t.shape[1]] - t) ** 2).sum(-1) * a).sum() / a.sum()
            if e < best[0]: best = (e, X, Y)
    m = np.zeros(img.shape[:2], np.uint8); m[best[2]:best[2] + t.shape[0], best[1]:best[1] + t.shape[1]] = (a > 0)
    return m, float(best[0])


def to_out(m, key):
    r = META[key]; s = r['scale']; b = r['bbox_raw']; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    M = np.float32([[s, 0, 512 - s * cx], [0, s, 512 - s * cy]])
    return cv2.warpAffine(m.astype(np.float32), M, (1024, 1024), flags=cv2.INTER_AREA)


def soft(mo):
    inner = cv2.distanceTransform((mo > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    return np.clip(inner / 2.0, 0, 1)[..., None]


if __name__ == '__main__':
    LOG = {}
    # set-A lumbar
    m, e = locate('raw/set-A-r1.jpg', 'seg/0a6f831d/5.png'); a = soft(to_out(m, 'set-A'))
    o = load('out/set-A.png'); L = lab(o); L2 = L.copy(); L2[..., 1:] *= 0.3
    save_png('out/set-A.png', lab2rgb(L2) * a + o * (1 - a)); LOG['set-A'] = dict(piece='30 x 50 lumbar (milk-tea)', fix='a*, b* x 0.3', match_err=round(e, 2), px=int((a > 0.5).sum()))
    # set-C corduroy
    m, e = locate('raw/set-C-r1.jpg', 'seg/4724bf21/2.png'); a = soft(to_out(m, 'set-C'))
    o = load('out/set-C.png'); o2 = to_srgb(to_lin(o) * 3.0)
    save_png('out/set-C.png', o2 * a + o * (1 - a)); LOG['set-C'] = dict(piece='45 x 45 corduroy patchwork (dark-coffee)', fix='x3.0 linear', match_err=round(e, 2), px=int((a > 0.5).sum()))
    # pink
    k = 'bedspread-cj-waffle-gauze-fringe-150x200-pink'
    mo = cv2.imread(f'out/mask/{k}.png', 0) > 0; a = soft(cv2.erode(mo.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32))
    o = load(f'out/{k}.png'); L = lab(o); L2 = L.copy(); L2[..., 2] += 4.5
    save_png(f'out/{k}.png', lab2rgb(L2) * a + o * (1 - a)); LOG[k] = dict(fix='b* +4.5 (the SKU pink is warmer)')
    M2 = json.load(open('out/meta.json'))
    for kk, v in LOG.items(): M2[kk]['colour_fix'] = v
    json.dump(M2, open('out/meta.json', 'w'), indent=1)
    print(json.dumps(LOG))
