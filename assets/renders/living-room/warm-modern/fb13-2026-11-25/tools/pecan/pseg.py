"""pseg.py: place the grok segment-map cut-outs (bbox-cropped RGBA) into the return by masked template matching (tools/wheel/segplace.py,
unchanged method), then carry them onto the sent crop by the registration. -> out/masks.npz (crop px, 0-1)"""
import sys, glob, os, json
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
ret = np.asarray(Image.open(PC + 'ret/pecan-nano.jpg').convert('RGB')).astype(np.float32)
H, W = ret.shape[:2]
full = {}
for f in sorted(glob.glob(PC + 'seg/P/*.png')):
    i = int(os.path.basename(f)[:-4])
    a = np.asarray(Image.open(f).convert('RGBA')).astype(np.float32)
    rgb, m = a[..., :3], a[..., 3]
    s = 4
    r4 = cv2.resize(ret, (W // s, H // s), interpolation=cv2.INTER_AREA)
    t4 = cv2.resize(rgb, (max(1, a.shape[1] // s), max(1, a.shape[0] // s)), interpolation=cv2.INTER_AREA)
    m4 = (cv2.resize(m, (t4.shape[1], t4.shape[0]), interpolation=cv2.INTER_AREA) > 200).astype(np.float32)
    res = cv2.matchTemplate(r4, t4, cv2.TM_SQDIFF, mask=np.repeat(m4[..., None], 3, 2))
    y4, x4 = np.unravel_index(np.argmin(res), res.shape)
    best = None
    mm = np.repeat((m > 200).astype(np.float32)[..., None], 3, 2)
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            x0, y0 = x4 * s + dx, y4 * s + dy
            if x0 < 0 or y0 < 0 or x0 + a.shape[1] > W or y0 + a.shape[0] > H:
                continue
            e = float((((ret[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] - rgb) ** 2) * mm).sum() / max(mm.sum(), 1))
            if best is None or e < best[0]:
                best = (e, x0, y0)
    fm = np.zeros((H, W), np.float32)
    fm[best[2]:best[2] + a.shape[0], best[1]:best[1] + a.shape[1]] = m / 255
    full[i] = fm
    print(i, 'offset', best[1], best[2], 'rms', round(best[0] ** 0.5, 2), 'px', int((fm > 0.5).sum()))
A = np.load(PC + 'out/reg.npz')['A']
cw, ch = 1280, 720
GR = dict(cushions=[1, 2, 3, 4, 5, 6, 7, 8, 9], throw=[10], table=[11], lamp=[17])
out = {}
for g, ids in GR.items():
    m = np.max(np.stack([full[i] for i in ids]), 0)
    m2 = cv2.warpAffine(m, A, (cw * 2, ch * 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out[g] = cv2.resize(m2, (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float16)
np.savez_compressed(PC + 'out/masks.npz', **out)
