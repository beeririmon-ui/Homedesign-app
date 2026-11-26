"""pcolour.py: the throw's colour against its SKU photo, the same measure for B (new Pecan, old knit), A (Flax) and C (Clay): the throw's
lower falls (alpha 255, x 1780-2320, y 1160-1460, not under the table), median Lab in the stack, against the SKU photo exposure-matched"""
import sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/tools')
FB13 = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
REF = PC + '../wm-pilot-refs/'
sys.path.insert(0, FB13 + 'tools/fix1'); import stack as ST
src = open(PC + 'tools/pbuild.py').read()
ns = {}
exec(src[src.index('def de00'):src.index('mnew = ')].replace('def lab_of', 'def _x'), dict(np=np, cv2=cv2), ns)
exec('def lab_of(img8, m):\n    L_ = cv2.cvtColor(img8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)\n    return np.median(L_[m], 0)\n', dict(np=np, cv2=cv2), ns)
de00 = ns['de00']; lab_of = ns['lab_of']
srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
man, base, lays, lights = ST.load('layers/manifest-wheel.json')
names = [n for n, _, _ in lays]; IC = names.index('cushions')
a_up = np.zeros(base.shape[:2], np.float32)
for _, a, _ in lays[IC + 1:]:
    a_up = 1 - (1 - a_up) * (1 - a[..., 3] / 255.)
box = np.zeros(base.shape[:2], bool); box[1160:1460, 1780:2320] = True
def measure(L, S, sku):
    c = ST.compose(base, [(n, *((L, S) if n == 'cushions' else (a, s))) for n, a, s in lays], lights)
    m = cv2.erode(((L[..., 3] == 255) & box & (a_up < 0.02)).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    lab = lab_of(c, m)
    im = np.asarray(Image.open(REF + sku).convert('RGB'))
    sl = cv2.cvtColor(im.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    ms = (np.hypot(sl[..., 1], sl[..., 2]) > 6) & (sl[..., 0] > 15)
    lin = srgb2lin(im.astype(np.float32) / 255); Y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    yt = ((lab[0] + 16) / 116) ** 3
    g = yt / float(np.median(Y[ms]))
    lx = lab_of(np.clip(lin2srgb(np.clip(lin * g, 0, 1)) * 255, 0, 255).astype(np.uint8), ms)
    hue = lambda l: round(float(np.degrees(np.arctan2(l[2], l[1]))), 1)
    return dict(px=int(m.sum()), render=[round(float(v), 1) for v in lab], sku=[round(float(v), 1) for v in lab_of(im, ms)],
                sku_exposure_matched=[round(float(v), 1) for v in lx], de00_exposure_matched=round(de00(lab, lx), 2),
                hue_render=hue(lab), hue_sku=hue(lx), chroma_render=round(float(np.hypot(lab[1], lab[2])), 1), chroma_sku_matched=round(float(np.hypot(lx[1], lx[2])), 1))
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
out = {}
out['B_new_pecan'] = measure(rd(PC + 'out/set-B-pecan-layer.png', 'RGBA'), rd(PC + 'out/set-B-pecan-shadow.png', 'RGB'), 'B-sofa-cover-cj-cotton-muslin-fringe-pecan-crop.png')
out['B_old_knit'] = measure(lays[IC][1], lays[IC][2], 'B-sofa-cover-cj-cotton-muslin-fringe-pecan-crop.png')
for k, f in (('A_flax', 'A-sofa-cover-cj-cotton-muslin-fringe-flax-brown-crop.png'), ('C_clay', 'C-sofa-cover-cj-cotton-muslin-fringe-clay-crop.png')):
    out[k] = measure(rd(FB13 + f'layers/cushions/set-{k[0]}.png', 'RGBA'), rd(FB13 + f'shadows/cushions/set-{k[0]}.png', 'RGB'), f)
json.dump(out, open(PC + 'out/colour.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
