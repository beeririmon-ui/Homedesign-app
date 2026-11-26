"""w7compose.py: the wheel's three stacks (fix1 with set B, A or C in the cushions' slot) -> canvas + 1920 frame per set; RND2; fidelity of
the stack to the edit inside the set; the pieces' colours; F3 gaps to the neighbours. -> out/frame-<k>.png, out/checks.json"""
import sys, os, json
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
REPO = '/home/user/homedesign-app'
FB13 = REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
sys.path.insert(0, FB13 + 'tools/fix1'); import stack as ST
H, W = 1530, 2720
FBW = 2642.5147347740667 - 77.4852652259332
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
man, base, lays, lights = ST.load('layers/manifest-fix1.json')
names = [k for k, _, _ in lays]
IC = names.index('cushions')
SETS = {'B': (lays[IC][1], lays[IC][2])}
for k in sys.argv[1:] or ['A', 'C']:
    SETS[k] = (rd(W7 + f'out/set-{k}-layer.png', 'RGBA'), rd(W7 + f'out/set-{k}-shadow.png', 'RGB'))
stack = lambda k: [(n, *(SETS[k] if n == 'cushions' else (a, s))) for n, a, s in lays]
region = lambda a, s: (a[..., 3] > 0) | (s < 255).any(2)
chk = {}
canv = {}
for k in SETS:
    canv[k] = ST.compose(base, stack(k), lights)
    fr = ST.frame(canv[k], man)
    Image.fromarray(fr).save(W7 + f'out/frame-{k}.png', optimize=True)
stored = rd(FB13 + 'default-frame-m0w-fix1.png', 'RGB')
frB = rd(W7 + 'out/frame-B.png', 'RGB')
chk['B_stack_vs_stored_default_frame'] = dict(max=int(np.abs(frB.astype(int) - stored.astype(int)).max()), px_over_0=int((frB != stored).any(2).sum()))
regB = region(*SETS['B'])
without = ST.compose(base, [x for x in stack('B') if x[0] != 'cushions'], lights)
for k in SETS:
    if k == 'B':
        continue
    regK = region(*SETS[k])
    dif = (canv[k] != canv['B']).any(2)
    frk = rd(W7 + f'out/frame-{k}.png', 'RGB')
    hide = (without != canv[k]).any(2)
    T = np.load(W7 + f'out/target-{k}.npy').astype(np.float32)
    P = np.load(W7 + f'out/pieces-{k}.npz')
    a = SETS[k][0][..., 3]
    core = (a == 255) & ~np.isin(np.arange(1), [])  # all opaque set pixels
    vis = core.copy()
    for n, aa, _ in lays[IC + 1:]:
        vis &= aa[..., 3] == 0
    left_refit = np.zeros((H, W), bool); left_refit[:, :1570] = True
    vis_nr = vis & ~left_refit
    dd = np.abs(canv[k].astype(np.float32) - T).max(2)
    c = dict(canvas_changed_vs_B_px=int(dif.sum()), changed_outside_A_or_B_regions_px=int((dif & ~(regK | regB)).sum()),
             regions_union_px=int((regK | regB).sum()),
             frame_changed_vs_B_px=int((frk != frB).any(2).sum()),
             hide_set_changed_px=int(hide.sum()), hide_set_changed_outside_its_region_px=int((hide & ~regK).sum()),
             stack_vs_edit_inside_set_opaque_visible=dict(px=int(vis_nr.sum()), mean=round(float(dd[vis_nr].mean()), 3), p99=round(float(np.percentile(dd[vis_nr], 99)), 2),
                                                          note='outside the refitted left cushion (it moved)'))
    # the pieces' colours in the frame (median Lab of each piece's opaque, visible core, eroded 6 px)
    lab = cv2.cvtColor(canv[k].astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    col = {}
    for p in ('left', 'right', 'lumbar', 'throw'):
        m = cv2.erode(P[p].astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool) & vis
        col[p] = [round(float(v), 1) for v in np.median(lab[m], 0)]
    c['pieces_Lab_median'] = col
    # F3: the smallest gap between the set and each neighbouring product's alpha, in frame widths (only those under 0.05)
    hard = a > 127
    dt = cv2.distanceTransform((~hard).astype(np.uint8), cv2.DIST_L2, 5)
    gaps = {}
    for n, aa, _ in lays:
        if n == 'cushions':
            continue
        m = aa[..., 3] > 127
        if not m.any():
            continue
        if (m & hard).any():
            gaps[n] = 'overlaps (depth order: %s)' % ('in front of the set' if names.index(n) > IC else 'behind the set')
            continue
        g = float(dt[m].min()) / FBW
        if g < 0.05:
            gaps[n] = round(g, 4)
    c['F3_gap_frame_widths'] = gaps
    chk[k] = c
# set B's F3 for comparison
hardB = SETS['B'][0][..., 3] > 127
dtB = cv2.distanceTransform((~hardB).astype(np.uint8), cv2.DIST_L2, 5)
chk['B_F3_gap_frame_widths'] = {n: round(float(dtB[aa[..., 3] > 127].min()) / FBW, 4) for n, aa, _ in lays
                                if n != 'cushions' and (aa[..., 3] > 127).any() and not ((aa[..., 3] > 127) & hardB).any()
                                and float(dtB[aa[..., 3] > 127].min()) / FBW < 0.05}
json.dump(chk, open(W7 + 'out/checks.json', 'w'), indent=1)
print(json.dumps(chk, indent=1))
