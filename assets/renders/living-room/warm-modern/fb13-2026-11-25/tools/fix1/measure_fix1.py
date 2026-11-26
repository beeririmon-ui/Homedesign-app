"""measure_fix1.py: the light targets (hwlib.measure on the old and the new default stack; the clay masks rebuilt from the repo's
m0w-ids.png / m0w-sun.png / m0w-light-*.png, since the run's passes are gone), V7Q6 and F3 numbers of the moved / added layers."""
import json, os, sys
import cv2, numpy as np
from PIL import Image
sys.path.insert(0, '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/tools')
import hwlib as L
S = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/'
O = S + 'out/stack-fix1/'
R = L.FB13 + '/'
ids = np.asarray(Image.open(R + 'm0w-ids.png')).astype(int)
code = ids[..., 0] * 65536 + ids[..., 1] * 256 + ids[..., 2]
idm = lambda c: np.roll(code == (c[0] * 65536 + c[1] * 256 + c[2]), 50, axis=0)
back = idm((238, 195, 185))
idx = np.where(back, 5, 0)
C = dict(idx=idx, idx_p=idx, sun=L.shifted_map('m0w-sun.png', 255.0))
for k in ('accent-sconces', 'floor-lamp', 'pendant', 'wall-sconce'):
    C['light-' + k] = L.shifted_map(f'm0w-light-{k}.png', 65535.0)
L._C.update(C)
old = np.load(S + 'out/old_canvas.npy').astype(np.float32) / 255
new = np.load(S + 'out/new_canvas.npy').astype(np.float32) / 255
rep = dict(light=dict(old_default=L.measure(old, hero=True), new_default=L.measure(new, hero=True),
                      targets='plaster shade L 74-80 (about 76), sunlit plaster L 88-92 (about 89), black point p0.5 9-11',
                      note='masks rebuilt from the repo clay maps (back wall id, sun map, lamp maps), so the old stack is measured the same way beside the new'))
FB = L.FB; FW = FB[2] - FB[0]; FH = FB[3] - FB[1]
fm = L.frame_mask()
rda = lambda p: np.asarray(Image.open(p))
def gap(a, b):
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return round(float(dt[a].min()) / FW, 4)
hol = rda(O + 'layer-magazine-holder.png')[..., 3] > 127
lamp = rda(R + 'layers/floor-lamp/floor-lamp-cj-pleated-walnut-stem-158.png')[..., 3] > 127
cush = rda(R + 'layers/cushions/set-B.png')[..., 3] > 127
rug = rda(O + 'layer-rug.png')[..., 3] > 127
sofa = idm((120, 160, 200))
ys, xs = np.nonzero(hol)
rep['holder'] = dict(bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], in_frame_share=round(float((hol & fm).sum() / hol.sum()), 4),
                     area_pct_of_frame=round(float(hol.sum()) / (FW * FH) * 100, 3), height_pct_of_frame=round((ys.max() - ys.min()) / FH * 100, 2),
                     f3_gap_frame=dict(floor_lamp=gap(hol, lamp), throw_and_cushions=gap(hol, cush), sofa=gap(hol, sofa), rug=gap(hol, rug)),
                     margin_to_frame_right=round((FB[2] - xs.max()) / FW, 4), margin_to_frame_bottom=round((FB[3] - ys.max()) / FH, 4))
cur = rda(O + 'layer-curtains.png')[..., 3] > 127
vase = rda(R + 'layers/vase/vase-cj-textured-white-stoneware.png')[..., 3] > 127
ys, xs = np.nonzero(cur & fm)
rep['curtain'] = dict(in_frame_share_of_layer=round(float((cur & fm).sum() / cur.sum()), 4), area_pct_of_frame=round(float((cur & fm).sum()) / (FW * FH) * 100, 3),
                      height_pct_of_frame=round((ys.max() - ys.min()) / FH * 100, 2), x_px_in_frame=[int(xs.min()), int(xs.max())],
                      vase_in_front_overlap_px=int((cur & vase).sum()), vase_px=int(vase.sum()),
                      vase_pixels_changed=False)
po = rda(R + 'layers/planter/planter-cj-cement-ribbed-belly.png')[..., 3] > 127
pn = rda(O + 'layer-planter.png')[..., 3] > 127
def tree(m):
    t = m.copy(); t[1178:] = False
    ys, xs = np.nonzero(t)
    crown = t[:800]
    cy, cx = np.nonzero(crown)
    return dict(top_y=int(ys.min()), crown_x=[int(cx.min()), int(cx.max())], px=int(t.sum()))
rep['olive'] = dict(old=tree(po), new=tree(pn))
json.dump(rep, open(O + 'measure.json', 'w'), indent=1)
print(json.dumps(rep, indent=1))
