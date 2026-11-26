"""w7sheet.py: qa-sheet-m0w-wheel.jpg: the three sets (B default, A, C) at x1 of the 1920 frame, and each set's cushions and throw at x2"""
import sys
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
fr = {k: np.asarray(Image.open(W7 + f'out/frame-{k}.png').convert('RGB')) for k in 'BAC'}
lab = {'B': 'set B (default): oatmeal boucle 50, camel corduroy 50, beige linen lumbar 30x50, Pecan muslin throw',
       'A': 'set A: taupe chenille 45, white boucle 50, milk-tea boucle lumbar 30x50, Flax muslin throw',
       'C': 'set C: dark coffee corduroy 45, light brown boucle 50, light beige-grey linen lumbar 30x50, Clay muslin throw'}
def text(img, s, xy, scale=0.9):
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 5, cv2.LINE_AA)
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (20, 20, 20), 2, cv2.LINE_AA)
X1 = (800, 590, 1720, 1080)
top = []
for k in 'BAC':
    t = fr[k][X1[1]:X1[3], X1[0]:X1[2]].copy()
    text(t, f'{k}  x1', (16, 36), 1.0)
    top.append(t)
top = np.concatenate([np.pad(t, ((0, 0), (0, 8), (0, 0)), constant_values=255) for t in top], 1)
CR = [(840, 630, 1090, 850), (1190, 630, 1600, 850), (1330, 820, 1700, 1050)]
rows = []
for k in 'BAC':
    tiles = []
    for (x0, y0, x1, y1) in CR:
        c = cv2.resize(fr[k][y0:y1, x0:x1], ((x1 - x0) * 2, (y1 - y0) * 2), interpolation=cv2.INTER_CUBIC)
        tiles.append(np.pad(c, ((0, 0), (0, 8), (0, 0)), constant_values=255))
    h = max(t.shape[0] for t in tiles)
    r = np.concatenate([np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0)), constant_values=255) for t in tiles], 1)
    text(r, f'{k}  x2   ' + lab[k], (16, 36), 0.9)
    rows.append(r)
Wd = max(top.shape[1], max(r.shape[1] for r in rows))
pad = lambda a: np.pad(a, ((0, 10), (0, Wd - a.shape[1]), (0, 0)), constant_values=255)
sheet = np.concatenate([pad(top)] + [pad(r) for r in rows], 0)
Image.fromarray(sheet).save(W7 + 'out/qa-sheet-m0w-wheel.jpg', quality=88, optimize=True)
print(sheet.shape)
