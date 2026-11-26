"""w7build.py: M0-W step 7, the cushion wheel. Sets A and C cut from two nano edits of hero-HW-fix1.png, by the hero's method:
the base stays plate-PW.png; each set = its pixels of the edit (straight alpha; a feathered 4 px fringe of the edit's own room where it
meets the room, an anti-aliased solved edge where it meets another product); its shadow (multiply) = low-pass(edit) / low-pass(the stack
without the cushions), darker only, inside the set's zone of influence (90 px, as stage A); the higher layers' shadows (the table's) are
divided out of the set's pixels, the lamps' screen is solved through. Every other layer, shadow and light is the fix1 stack's, byte for
byte. One recorded refit: the left cushion (45 x 45 on the card) scaled about its seat line to 45/50 of set B's 50 x 50 left cushion.
-> out/set-<k>-layer.png, out/set-<k>-shadow.png, out/build-<k>.json"""
import sys, os, json
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
REPO = '/home/user/homedesign-app'
FB13 = REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
sys.path.insert(0, FB13 + 'tools/fix1'); import stack as ST
sys.path.insert(0, REPO + '/assets/renders/tools/finish'); import finish as F
H, W = 1530, 2720
CROP = (1120, 810, 2400, 1530)
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
RADIUS = 90                      # stage A's zone of influence for the cushions
B_LEFT_W = 272                   # set B's left cushion (card 50 x 50), alpha bbox width in canvas px
LEFT_CARD_CM, B_LEFT_CM = 45.0, 50.0
SPLIT_X = 1570                   # between the left cushion's zone (to 1565) and the lumbar's (from 1575)
srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
rd = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255


def nblur(img, w, sigma):
    if sigma >= 12.0:
        f = 4
        hs, ws = img.shape[0] // f, img.shape[1] // f
        wi = cv2.resize(w, (ws, hs), interpolation=cv2.INTER_AREA)
        im = cv2.resize(img * (w[..., None] if img.ndim == 3 else w), (ws, hs), interpolation=cv2.INTER_AREA)
        num = cv2.resize(cv2.GaussianBlur(im, (0, 0), sigma / f), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
        den = cv2.resize(cv2.GaussianBlur(wi, (0, 0), sigma / f), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        num = cv2.GaussianBlur(img * (w[..., None] if img.ndim == 3 else w), (0, 0), sigma)
        den = cv2.GaussianBlur(w, (0, 0), sigma)
    return num / np.maximum(den[..., None] if img.ndim == 3 else den, 1e-5), den


def fill_scales(img, w, sigmas=(3.0, 10.0, 30.0, 90.0, 270.0)):
    out = img.copy(); done = w > 0.5
    for sg in sigmas:
        m, den = nblur(img, w, sg)
        take = (~done) & (den > 0.05)
        out[take] = m[take]; done |= take
    return out


def ratio_field(A, B, w, near, s_small=2.5, s_large=12.0):
    """stage A's extract.ratio_field, unchanged"""
    As, _ = nblur(A, w, s_small); Bs, _ = nblur(B, w, s_small)
    Al, _ = nblur(A, w, s_large); Bl, _ = nblur(B, w, s_large)
    rs = np.clip(As / np.maximum(Bs, 0.012), 0.3, 2.0)
    rl = np.clip(Al / np.maximum(Bl, 0.012), 0.3, 2.0)
    r = np.exp(np.log(rl) * (1 - near[..., None]) + np.log(rs) * near[..., None])
    return fill_scales(r, (w > 0.5).astype(np.float32))


def vignette():
    x0, y0, x1, y1 = FB
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rho = np.hypot((xx - (x0 + x1) / 2) / ((x1 - x0) / 2), (yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) / np.sqrt(2.0)
    return (2.0 ** (-0.15 * np.clip(rho, 0, 1.15) ** 2.4)).astype(np.float32)


man, base, lays, lights = ST.load('layers/manifest-fix1.json')
names = [k for k, _, _ in lays]
IC = names.index('cushions')
V = vignette()
Lb = F.Lstar(base) / 100.0
GR = F.grain_field((H, W)) * 1.2 * np.clip(4 * Lb * (1 - Lb), 0.25, 1.0)
bakef = lambda rgb01: np.clip(lin2srgb(srgb2lin(np.clip(rgb01, 0, 1)) * V[..., None]) * 255.0 + GR[..., None], 0, 255)
Pbelow = F.compose(base, [(a, s) for _, a, s in lays[:IC]], []).astype(np.float32)
S_up = np.ones((H, W, 3), np.float32); a_up = np.zeros((H, W), np.float32)
for _, a, s in lays[IC + 1:]:
    S_up *= s.astype(np.float32) / 255
    a_up = 1 - (1 - a_up) * (1 - a[..., 3].astype(np.float32) / 255)
Su = np.clip(S_up, 0.05, 1.0)
keep_wo = np.ones((H, W), np.float32)
for k, a, _ in lays:
    if k != 'cushions':
        keep_wo *= 1 - a[..., 3].astype(np.float32) / 255
others_hard = np.zeros((H, W), bool)
for k, a, _ in lays:
    if k != 'cushions':
        others_hard |= a[..., 3] > 127
up_hard = a_up > 0.5
hero = rd(FB13 + 'hero-HW-fix1.png')
x0c, y0c, x1c, y1c = CROP
yy, xx = np.mgrid[0:H, 0:W]
dcrop = np.minimum.reduce([xx - x0c, yy - y0c, x1c - 1 - xx]).astype(np.float32)          # the bottom edge is the canvas edge
taper = np.clip((dcrop - 4) / 24.0, 0, 1) * ((xx >= x0c) & (xx < x1c) & (yy >= y0c))


def build(k, refit=True):
    z = np.load(W7 + f'out/reg-{k}.npz')
    E = hero.copy()
    E[y0c:y1c, x0c:x1c] = z['w1'].astype(np.float32)
    P = {}
    for p in ('left', 'right', 'lumbar', 'throw'):
        m = np.zeros((H, W), np.float32); m[y0c:y1c, x0c:x1c] = z['m_' + p].astype(np.float32); P[p] = m > 0.5
    hard = P['left'] | P['right'] | P['lumbar'] | P['throw']
    rec = dict(set=k)
    # the edit's table may stand a px off the stack's: the set goes 4 px on under the higher layers (hidden there; no seam)
    ext = dil(hard, 4) & dil(up_hard, 1) & ~hard & ~(others_hard & ~up_hard)
    T = bakef(E)
    # ---- alpha: stage A's (4 px fringe of the edit's room where it meets the room; anti-aliased against another product)
    FR = 4.0
    hard_a = hard | ext
    aa = cv2.GaussianBlur(hard_a.astype(np.float32), (0, 0), 0.8); aa[~dil(hard_a, 2)] = 0
    dk = cv2.distanceTransform((~hard_a).astype(np.uint8), cv2.DIST_L2, 5)
    fr = np.clip(1 - (dk - 0.5) / FR, 0, 1) ** 1.5
    fr_ok = ~dil(others_hard, 1)
    a = np.where(hard_a, 1.0, np.where(fr_ok, fr, np.minimum(aa, 0.999))).astype(np.float32)
    a[a < 0.02] = 0
    # ---- the target before the lamps' screen and without the higher layers' shadows
    keep_new = keep_wo * (1 - a)
    Q = np.ones((H, W, 3), np.float32)
    for lt in lights:
        Q *= 1 - lt.astype(np.float32) / 255 * keep_new[..., None]
    X = 255 - (255 - T) / np.maximum(Q, 1e-3)
    # where the table's shadow (stage A's, for the rug and set B's throw) is deeper than the edit's own shade, X / Su passes 255: bring the
    # pixel down as a whole, never per channel (a per-channel clip turned the throw blue beside the table's leg)
    Ck = np.clip(X / Su, 0, None)
    mx = Ck.max(2, keepdims=True)
    Ck = np.where(mx > 255, Ck * 255 / np.maximum(mx, 1e-3), Ck)
    rec_clip = int((mx[..., 0] > 255).sum())
    # ---- the shadow: low-pass(edit) / low-pass(stack without the cushions), darker only, in the zone of influence
    free = (~dil(hard_a, 2) & (a_up < 0.02) & (taper > 0)).astype(np.float32)
    dist_h = cv2.distanceTransform((~hard).astype(np.uint8), cv2.DIST_L2, 5)
    near = np.exp(-dist_h / 10.0).astype(np.float32)
    # on the luma only: the model re-drew the sofa's boucle a little off the plate's hue, and a per-channel min(r, 1) turned that into
    # tinted (cyan) "shadows"; a neutral multiply keeps the plate's own hue under the set's contact and cast shadows
    luma = lambda x: np.repeat((0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None], 3, 2)
    r = ratio_field(luma(Ck / 255.0), np.maximum(luma(Pbelow / 255.0), 0.004), free, near)
    d = np.minimum(r, 1.0)
    rest = hard & ~P['left']
    dl = cv2.distanceTransform((~P['left']).astype(np.uint8), cv2.DIST_L2, 5)
    dr = cv2.distanceTransform((~rest).astype(np.uint8), cv2.DIST_L2, 5)
    Wl = (np.clip(1 - dl / RADIUS, 0, 1) ** 1.5 * taper).astype(np.float32)
    Wr = (np.clip(1 - dr / RADIUS, 0, 1) ** 1.5 * taper).astype(np.float32)
    rec['zones_overlap_px'] = int(((Wl > 0) & (Wr > 0)).sum())
    S = (d ** np.maximum(Wl, Wr)[..., None]).astype(np.float32)
    # ---- the colours: the edit's own pixels; the edge against a lower product solved; under a higher layer, the set's own colour
    comp_s = np.rint(Pbelow * S)
    C = Ck.copy()
    edge = (a > 0.02) & (a < 0.999) & dil(others_hard & ~hard_a, 1)
    solve = np.clip((Ck - (1 - a[..., None]) * comp_s) / np.maximum(a[..., None], 0.02), 0, 255)
    C[edge & (a >= 0.3)] = solve[edge & (a >= 0.3)]
    inner = (hard & (a_up < 0.02)).astype(np.float32)
    nb, den = nblur(Ck, inner, 2.0)
    nb6, _ = nblur(Ck, inner, 6.0)
    nbf = np.where((den > 0.05)[..., None], nb, nb6)
    weak = edge & (a < 0.3)
    C[weak] = nbf[weak]
    hid = (a > 0) & (a_up > 0.02)
    C[hid] = nbf[hid]
    rec.update(over_255_scaled_px=rec_clip, edge_solved_px=int((edge & (a >= 0.3)).sum()), edge_weak_px=int(weak.sum()), under_higher_layers_px=int(hid.sum()),
               extended_under_higher_px=int(ext.sum()))
    # ---- the one refit: the left cushion to its card size, about its seat line (bottom centre); its shadow zone goes with it
    if refit:
        ys, xs = np.nonzero(P['left'])
        wpx = int(xs.max() - xs.min() + 1)
        sc = (B_LEFT_W * LEFT_CARD_CM / B_LEFT_CM) / wpx
        px_, py_ = (xs.min() + xs.max()) / 2.0, float(ys.max())
        Mh = np.float32([[sc, 0, px_ - sc * px_], [0, sc, py_ - sc * py_]])
        part = xx < SPLIT_X
        wa = lambda img, bv=0, interp=cv2.INTER_LINEAR: cv2.warpAffine(img, Mh, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=bv)
        a_l = np.where(part, a, 0).astype(np.float32)
        pm = (C * a_l[..., None]).astype(np.float32)
        a_w = wa(a_l); pm_w = wa(pm)
        C_w = np.where((a_w > 1e-3)[..., None], pm_w / np.maximum(a_w, 1e-3)[..., None], 0)
        d_w = cv2.warpAffine(d.astype(np.float32), Mh, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        Wl_w = wa(Wl)
        S_l = d_w ** Wl_w[..., None]
        S_r = d ** Wr[..., None]
        S = np.where(part[..., None], S_l * S_r, S).astype(np.float32)
        a = np.where(part, a_w, a).astype(np.float32)
        C = np.where(part[..., None], C_w, C)
        P['left'] = wa(P['left'].astype(np.float32)) > 0.5
        rec['refit_left'] = dict(card_cm=LEFT_CARD_CM, rendered_w_px=wpx, target_w_px=round(B_LEFT_W * LEFT_CARD_CM / B_LEFT_CM, 1),
                                 scale=round(float(sc), 4), about=[round(float(px_), 1), round(py_, 1)],
                                 why='the edit drew the 45 x 45 cm left cushion at the width of set B\'s 50 x 50 one (%d vs %d px)' % (wpx, B_LEFT_W),
                                 revealed='the sofa back of the plate, under the set\'s own shadow zone (moved with the cushion)')
    a8 = np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)
    C8 = np.clip(np.rint(C), 0, 255).astype(np.uint8); C8[a8 == 0] = 0
    S8 = np.clip(np.rint(S * 255), 0, 255).astype(np.uint8)
    S8[(S8 >= 254).all(2)] = 255
    layer = np.dstack([C8, a8])
    Image.fromarray(layer).save(W7 + f'out/set-{k}-layer.png', optimize=True)
    Image.fromarray(S8).save(W7 + f'out/set-{k}-shadow.png', optimize=True)
    np.savez_compressed(W7 + f'out/pieces-{k}.npz', **{p: v for p, v in P.items()})
    np.save(W7 + f'out/target-{k}.npy', np.rint(T).astype(np.uint8))
    ys, xs = np.nonzero(a8)
    rec.update(alpha_px=int((a8 > 0).sum()), alpha_255_px=int((a8 == 255).sum()), shadow_px=int((S8 < 255).any(2).sum()),
               bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
               shadow_min=int(S8.min()), pieces_px={p: int(v.sum()) for p, v in P.items()})
    json.dump(rec, open(W7 + f'out/build-{k}.json', 'w'), indent=1)
    print(json.dumps(rec))


if __name__ == '__main__':
    for k in sys.argv[1:]:
        build(k)
