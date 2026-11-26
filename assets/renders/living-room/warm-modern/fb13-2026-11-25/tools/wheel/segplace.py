"""segplace.py: place grok segment-map cutouts (bbox-cropped RGBA) into the full return frame by masked template matching"""
import sys, json, glob, os
import cv2, numpy as np
from PIL import Image
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
def place(setk):
    ret = np.asarray(Image.open(W7 + f'ret/set{setk}-nano.jpg').convert('RGB')).astype(np.float32)
    H, W = ret.shape[:2]
    out = {}
    for f in sorted(glob.glob(W7 + f'seg/{setk}/*.png')):
        i = int(os.path.basename(f)[:-4])
        a = np.asarray(Image.open(f).convert('RGBA')).astype(np.float32)
        rgb, m = a[..., :3], a[..., 3]
        # coarse search at 1/4, then refine at full res around the best
        s = 4
        r4 = cv2.resize(ret, (W // s, H // s), interpolation=cv2.INTER_AREA)
        t4 = cv2.resize(rgb, (max(1, a.shape[1] // s), max(1, a.shape[0] // s)), interpolation=cv2.INTER_AREA)
        m4 = cv2.resize(m, (t4.shape[1], t4.shape[0]), interpolation=cv2.INTER_AREA)
        m4 = (m4 > 200).astype(np.float32)
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
        full = np.zeros((H, W), np.uint8)
        full[best[2]:best[2] + a.shape[0], best[1]:best[1] + a.shape[1]] = m.astype(np.uint8)
        out[i] = full
        print(setk, i, 'offset', best[1], best[2], 'rms', round(best[0] ** 0.5, 2), 'px', int((full > 127).sum()))
    np.savez_compressed(W7 + f'seg/full-{setk}.npz', **{str(k): v for k, v in out.items()})
if __name__ == '__main__':
    for k in sys.argv[1:]:
        place(k)
