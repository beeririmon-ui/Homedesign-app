"""compose_fix1.py: the fix1 stack (old stack, planter and holder replaced, the curtain added at z 10) -> canvas + 1920 frame;
RND2 against the old stack composed by the same code; previews"""
import os, sys, json
import cv2, numpy as np
from PIL import Image
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/tools')
import stack as ST
S = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/'
O = S + 'out/stack-fix1/'
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
man, base, lays, lights = ST.load()
old_canvas = ST.compose(base, lays, lights)
new_lays = [('curtains', rd(O + 'layer-curtains.png', 'RGBA'), rd(O + 'shadow-curtains.png', 'RGB'))]
for k, a, s in lays:
    if k in ('planter', 'magazine-holder'):
        a, s = rd(O + f'layer-{k}.png', 'RGBA'), rd(O + f'shadow-{k}.png', 'RGB')
    if k == 'rug':
        a = rd(O + 'layer-rug.png', 'RGBA')
    new_lays.append((k, a, s))
lights_new = [rd(O + f'light-{i}.png', 'RGB') for i in range(len(lights))]
new_canvas = ST.compose(base, new_lays, lights_new)
np.save(S + 'out/new_canvas.npy', new_canvas); np.save(S + 'out/old_canvas.npy', old_canvas)
fr_new = ST.frame(new_canvas, man); fr_old = ST.frame(old_canvas, man)
Image.fromarray(fr_new).save(S + 'out/default-frame-m0w-fix1.png', optimize=True)
# RND2: the canvas differs only inside the changed layers' regions (old and new alpha and shadow of planter, holder, curtain)
reg = np.zeros(base.shape[:2], bool)
for lo, ln in zip(lights, lights_new):
    reg |= (lo != ln).any(2)
ro = [x for x in lays if x[0] == 'rug'][0][1]; rn = [x for x in new_lays if x[0] == 'rug'][0][1]
reg |= (ro != rn).any(2)
for k, a, s in lays:
    if k in ('planter', 'magazine-holder'):
        reg |= (a[..., 3] > 0) | (s < 255).any(2)
for k, a, s in new_lays:
    if k in ('planter', 'magazine-holder', 'curtains'):
        reg |= (a[..., 3] > 0) | (s < 255).any(2)
dif = (new_canvas != old_canvas).any(2)
fdif = (fr_new != fr_old).any(2)
stored = rd(ST.FB13 + '/default-frame-m0w.png', 'RGB')
rep = dict(canvas_changed_px=int(dif.sum()), canvas_changed_outside_regions_px=int((dif & ~reg).sum()), regions_px=int(reg.sum()),
           frame_changed_px=int(fdif.sum()),
           old_stack_recomposed_vs_stored_frame=dict(max=int(np.abs(fr_old.astype(int) - stored.astype(int)).max()),
                                                     px_over_0=int((fr_old != stored).any(2).sum())))
# hiding the new layers changes only their own regions
per = {}
for k in ('planter', 'magazine-holder', 'curtains'):
    wo = ST.compose(base, [x for x in new_lays if x[0] != k], lights_new)
    d = (wo != new_canvas).any(2)
    a, s = [(x[1], x[2]) for x in new_lays if x[0] == k][0]
    r = (a[..., 3] > 0) | (s < 255).any(2)
    per[k] = dict(changed_px=int(d.sum()), changed_outside_its_region_px=int((d & ~r).sum()))
rep['swap_one_product'] = per
json.dump(rep, open(O + 'rnd2.json', 'w'), indent=1)
print(json.dumps(rep))
v = lambda x: Image.fromarray(x)
v(fr_new).resize((1280, 720), Image.LANCZOS).save(S + 'v-new-frame.jpg', quality=88)
