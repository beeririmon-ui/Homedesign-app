#!/usr/bin/env python3
"""heal_hdx_corner.py: QA HD-M1 (2026-11-17, run 5), 0 tokens. HDx's lower-left entrance stone (the clay's stone that HD magnifies
about x2 in its bottom course) is rougher than the others: pitted texture and a lit lip under its upper joint. Its fine texture is
replaced, its tone kept: per pixel, new = the stone's own masked low-pass (sigma 10 px, linear light, estimated 4 px inside its joints) x the luminance detail of the
smooth stone next to it (across the vertical joint), shifted onto it (a few offsets in turn, until every pixel has detail). In a 6 px band along its joints the detail is neutral (tone only), so no donor edge is copied in; along its upper joint HDx's own 6 px are kept (the lit lip every joint has). Only that stone's pixels change; the joints around it are kept.
  python3 heal_hdx_corner.py <hdx.png> <out.png>"""
import json, sys
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K
from prep_d0o import to_lin, to_srgb
img = to_lin(np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float64) / 255)
cls = K.clay_id("HDx")
n, lab = cv2.connectedComponents((cls == 94).astype(np.uint8), connectivity=4)
S = lab == lab[1491, 51]                       # the stone (HD (1800, 1420) -> HDx (51, 1491))
D = lab == lab[1472, 230]                      # its smooth neighbour across the vertical joint
W709 = np.array([0.2126, 0.7152, 0.0722])
def masked_blur(a, m, s):
    num = cv2.GaussianBlur(a * m[..., None] if a.ndim == 3 else a * m, (0, 0), s)
    den = cv2.GaussianBlur(m.astype(np.float64), (0, 0), s)
    return num / np.maximum(den[..., None] if a.ndim == 3 else den, 1e-6)
Sin = cv2.erode(S.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0       # the tone from the stone's interior: the lit lip at its edge does not feed it
lowS = masked_blur(img, Sin, 10.0)
Y = img @ W709
detD = Y / np.maximum(masked_blur(Y, D, 10.0), 1e-6)
Din = cv2.erode(D.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0     # donor pixels at least 5 px from its joints
det = np.ones(Y.shape)
ys, xs = np.nonzero(S)
done = np.zeros(len(ys), bool)
for dx, dy in ((250, -60), (250, -160), (330, -120), (180, -200), (400, -180), (300, -240), (450, -260), (380, -40), (220, -110), (420, -320), (300, -330)):
    sy, sx = ys + dy, xs + dx
    ok = ~done & (sy >= 0) & (sy < Y.shape[0]) & (sx >= 0) & (sx < Y.shape[1])
    ok[ok] &= Din[sy[ok], sx[ok]]
    det[ys[ok], xs[ok]] = detD[sy[ok], sx[ok]]
    done |= ok
ok = done
edge = S & ~(cv2.erode(S.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0)   # 6 px along the stone's joints: tone only, no copied detail
det[edge] = 1.0
out = img.copy()
out[S] = np.clip(lowS[S] * det[S][:, None], 0, 1)
# the lit lip under the stone's upper joint is the scene's light (every joint in HDx and HD has one): keep HDx's own pixels there
top = np.full(S.shape[1], -1)
cols = np.nonzero(S.any(0))[0]
lip = np.zeros_like(S)
for x in cols:
    y0 = int(np.nonzero(S[:, x])[0].min())
    lip[y0:y0 + 6, x] = S[y0:y0 + 6, x]
out[lip] = img[lip]
K.save_rgb(sys.argv[2], to_srgb(out))
Yo = K.lin_Y(np.asarray(Image.open(sys.argv[2]).convert("RGB")))
print(json.dumps(dict(stone_px=int(S.sum()), donor_covered=round(float(ok.mean()), 3),
                      stone_median_level_change_pct=round(100 * (np.median(Yo[S]) / np.median(K.lin_Y(np.asarray(Image.open(sys.argv[1]).convert("RGB")))[S]) - 1), 2),
                      stone_box=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())])))
