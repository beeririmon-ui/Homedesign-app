"""hero_fix1.py: the three nano edits (registered, tone-matched: reg.py) pasted into the graded hero, each inside its own region only.
E1: the olive (crown, trunk, the soil at the trunk's foot) and its leaf shadow on the plaster; the planter body below the mouth stays the hero's.
E2: the curtain only (left of its own hem, above the bench, never over the armchair); nano's moved vase and window posts are NOT taken.
E3: the holder and its contact shadow only. The old holder (cut by the bottom edge) is removed from the hero record by the stack itself
(the rug layer under it, de-finished). -> out/hero-fix1.npy, out/masks.npz"""
import os, sys
import cv2, numpy as np
from PIL import Image
S = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/'
R = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
os.makedirs(S + 'out', exist_ok=True)
H, W = 1530, 2720
rd = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255
rda = lambda p: np.asarray(Image.open(p)).astype(np.float32) / 255
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
def nblur(img, w, s):
    num = cv2.GaussianBlur(img * w[..., None], (0, 0), s); den = cv2.GaussianBlur(w, (0, 0), s)
    return num / np.maximum(den, 1e-4)[..., None], den
def place(name, box):
    x0, y0, x1, y1 = box
    out = np.zeros((H, W, 3), np.float32); dd = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = np.load(S + f'ret/{name}-reg.npy').astype(np.float32)
    dd[y0:y1, x0:x1] = np.load(S + f'ret/{name}-d.npy').astype(np.float32)
    inside = np.zeros((H, W), bool); inside[y0 + 4:y1 - 4, x0 + 4:x1 - 4] = True
    return out, dd, inside
hero = rd(R + 'hero-HW.png')
ids = np.asarray(Image.open(R + 'm0w-ids.png')).astype(int)
code = ids[..., 0] * 65536 + ids[..., 1] * 256 + ids[..., 2]
idm = lambda c: np.roll(code == (c[0] * 65536 + c[1] * 256 + c[2]), 50, axis=0)
sofa, arm = idm((120, 160, 200)), idm((110, 190, 140))
lay = lambda s, p: rda(R + f'layers/{s}/{p}.png')
planterL = lay('planter', 'planter-cj-cement-ribbed-belly')
cush = lay('cushions', 'set-B')[..., 3] > 0.02
vaseA = lay('vase', 'vase-cj-textured-white-stoneware')[..., 3]
lampA = lay('floor-lamp', 'floor-lamp-cj-pleated-walnut-stem-158')[..., 3] > 0.02
new = hero.copy()
M = {}
# ---------------- E1, the olive
e1, d1, in1 = place('e1-olive', (620, 0, 1432, 1444))
MOUTH = 1178                      # the planter's rim (the hero's planter: its mouth ellipse top ~1172-1185); below it the body is the hero's
zone1 = np.zeros((H, W), bool); zone1[330:1190, 640:1430] = True
old_tree = (planterL[..., 3] > 0.02); old_tree[MOUTH:] = False
chg1 = cv2.GaussianBlur((d1 > 0.035).astype(np.float32), (0, 0), 3) > 0.15
reg1 = zone1 & in1 & (chg1 | dil(old_tree, 6)) & ~sofa & ~cush
# the rim / soil: allow the mouth region inside the planter's ellipse above the rim line only
reg1[MOUTH:] = False
w1 = cv2.GaussianBlur(reg1.astype(np.float32), (0, 0), 2.0) * dil(reg1, 3)
new = new * (1 - w1[..., None]) + e1 * w1[..., None]
M['e1'] = reg1
# ---------------- E2, the curtain (nano's folds and hem, left of its own hem; above the bench; never the armchair)
e2, d2, in2 = place('e2-curtain', (0, 0, 812, 1444))
L2 = e2.mean(2)
edge = np.zeros(H, np.float32)
for y in range(H):
    seg = cv2.GaussianBlur(L2[max(0, y - 6):y + 7, 188:232].mean(0).reshape(1, -1), (0, 0), 1.2).ravel()
    edge[y] = 188 + int(np.argmin(seg))
edge = cv2.GaussianBlur(edge.reshape(-1, 1), (0, 0), 25).ravel()
xx = np.arange(W)[None, :].astype(np.float32)
a2 = np.clip((edge[:, None] + 2.0 - xx) / 3.0, 0, 1)          # the hem line itself belongs to the curtain
BOTTOM = 1150
a2[BOTTOM:] = 0
armd = dil(arm, 1)
a2[armd] = 0
a2[:, 812:] = 0
M['e2_alpha'] = a2
M['e2_edge'] = edge
new = new * (1 - a2[..., None]) + e2 * a2[..., None]
# ---------------- E3, the holder (+ its contact shadow on the floor)
e3, d3, in3 = place('e3-holder', (1632, 918, 2720, 1530))
zone3 = np.zeros((H, W), bool); zone3[1150:1440, 2300:2620] = True
chg3 = cv2.GaussianBlur((d3 > 0.03).astype(np.float32), (0, 0), 2) > 0.2
reg3 = zone3 & in3 & chg3 & ~lampA
n, lab, st, _ = cv2.connectedComponentsWithStats(reg3.astype(np.uint8))
keep = [i for i in range(1, n) if st[i, 4] > 400]
reg3 = np.isin(lab, keep)
reg3 = dil(reg3, 10) & zone3 & ~lampA
w3 = cv2.GaussianBlur(reg3.astype(np.float32), (0, 0), 2.0) * dil(reg3, 3)
new = new * (1 - w3[..., None]) + e3 * w3[..., None]
M['e3'] = reg3
np.save(S + 'out/hero-fix1-edits.npy', new.astype(np.float32))
np.savez_compressed(S + 'out/masks.npz', **{k: v for k, v in M.items()})
v = lambda x: Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
v(new).resize((1360, 765), Image.LANCZOS).save(S + 'v-hero-fix1.jpg', quality=85)
print('e1 px', int(reg1.sum()), 'e2 px', int((a2 > 0).sum()), 'edge x min/max', round(float(edge[:BOTTOM].min()), 1), round(float(edge[:BOTTOM].max()), 1), 'e3 px', int(reg3.sum()))
