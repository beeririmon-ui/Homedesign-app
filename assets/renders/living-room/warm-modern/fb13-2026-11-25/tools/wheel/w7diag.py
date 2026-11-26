import numpy as np, sys, cv2
sys.dont_write_bytecode = True
from PIL import Image
sys.path.insert(0, '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/tools/fix1'); import stack as ST
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
man, base, lays, lights = ST.load('layers/manifest-fix1.json')
for k in sys.argv[1:]:
    L = np.asarray(Image.open(W7 + f'out/set-{k}-layer.png')); S = np.asarray(Image.open(W7 + f'out/set-{k}-shadow.png'))
    st = [(n, *((L, S) if n == 'cushions' else (a, s))) for n, a, s in lays]
    c = ST.compose(base, st, lights)
    T = np.load(W7 + f'out/target-{k}.npy')
    lc = cv2.cvtColor(c.astype(np.float32) / 255, cv2.COLOR_RGB2LAB); lt = cv2.cvtColor(T.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    reg = ((L[..., 3] > 0) | (S < 255).any(2)) & (np.arange(L.shape[1])[None, :] >= 1570)
    a_up = np.zeros(L.shape[:2], bool)
    for n, a, s in lays[[x[0] for x in lays].index('cushions') + 1:]:
        a_up |= a[..., 3] > 0
    de = np.sqrt(((lc - lt) ** 2).sum(2))
    cool = (lc[..., 2] < lt[..., 2] - 8) & reg & ~a_up
    n, lab, stt, cen = cv2.connectedComponentsWithStats(cool.astype(np.uint8))
    big = sorted([(stt[i, 4], i) for i in range(1, n)], reverse=True)[:8]
    print(k, 'cool px', int(cool.sum()), [(int(a), [int(v) for v in stt[i, :4]]) for a, i in big])
    bad = (de > 15) & reg & ~a_up & (L[..., 3] < 250)
    n, lab, stt, cen = cv2.connectedComponentsWithStats(bad.astype(np.uint8))
    big = sorted([(stt[i, 4], i) for i in range(1, n)], reverse=True)[:8]
    print(k, 'dE>15 outside opaque px', int(bad.sum()), [(int(a), [int(v) for v in stt[i, :4]]) for a, i in big])
