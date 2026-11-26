"""pbuild.py: M0-W set B, the Pecan throw as muslin (fix1-pecan). One nano-banana-2 2K edit of the wheel's crop of hero-HW-fix1.png,
registered (prep.py) and cut by tools/wheel/w7build.py's method, but ONLY in the throw's region: the cushions keep set B's stage-A pixels.
  Z (layer region)  = (old throw (6 px) | new throw (6 px)) minus the cushions (segment map of the edit)
  the layer          = set-B.png outside Z; inside Z the edit's cut (alpha: 4 px fringe of the edit's room, anti-aliased against another
                       product, 4 px on under the table; colours: the edit baked with the stage-A finish, the lamps' screen solved out, the
                       table's shadow divided out)
  the shadow         = set-B shadow beyond 90 px of the throw; within 45 px the new one (low-pass luma(edit) / luma(the stack without the
                       cushions), darker only, the 90 px zone of influence of stage A); a log blend between; the old one under the cushions
  one patch          = the lamp's pole where the old knit hid it and the new throw does not (the floor-lamp layer has no pixels there):
                       the edit's pole, carried in set B's layer, inside the old throw's region
-> out/set-B-pecan-layer.png, out/set-B-pecan-shadow.png, out/frame-old.png, out/frame-new.png, out/checks.json"""
import sys, os, json
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
REPO = '/home/user/homedesign-app'
FB13 = REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
sys.path.insert(0, FB13 + 'tools/fix1'); import stack as ST
sys.path.insert(0, REPO + '/assets/renders/tools/finish'); import finish as F
H, W = 1530, 2720
CROP = (1120, 810, 2400, 1530)
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
FBW = FB[2] - FB[0]
RADIUS = 90
srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
ero = lambda m, r: cv2.erode(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
dist = lambda m: cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
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


man, base, lays, lights = ST.load('layers/manifest-wheel.json')          # cushions = set B (layers/cushions/set-B.png)
names = [k for k, _, _ in lays]
IC = names.index('cushions')
a_old8 = lays[IC][1][..., 3]; C_old8 = lays[IC][1][..., :3]; S_old8 = lays[IC][2]
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
lamp_a = lays[names.index('floor-lamp')][1][..., 3]
x0c, y0c, x1c, y1c = CROP
yy, xx = np.mgrid[0:H, 0:W]
dcrop = np.minimum.reduce([xx - x0c, yy - y0c, x1c - 1 - xx]).astype(np.float32)
taper = np.clip((dcrop - 4) / 24.0, 0, 1) * ((xx >= x0c) & (xx < x1c) & (yy >= y0c))

# ---- the edit on the canvas, and its pieces (segment map, carried by the registration)
z = np.load(PC + 'out/reg.npz')
E = rd(FB13 + 'hero-HW-fix1.png')
E[y0c:y1c, x0c:x1c] = z['w1'].astype(np.float32)
MS = np.load(PC + 'out/masks.npz')
def canv(m):
    o = np.zeros((H, W), np.float32); o[y0c:y1c, x0c:x1c] = m.astype(np.float32); return o
Kc = canv(MS['cushions']) > 0.5
Tn = canv(MS['throw']) > 0.5
lampS = canv(MS['lamp'])
# the old throw: set B's alpha away from the cushions (their 4 px fringe ring stays), its one big component
oldT = (a_old8 > 127) & ~dil(Kc, 5)
n, lab, st, _ = cv2.connectedComponentsWithStats(oldT.astype(np.uint8))
big = 1 + int(np.argmax(st[1:, 4]))
oldT = lab == big
TT = oldT | Tn
Z = (dil(oldT, 6) | dil(Tn, 6)) & ~Kc
rec = dict(old_throw_px=int(oldT.sum()), new_throw_px=int(Tn.sum()), cushions_px=int(Kc.sum()), Z_px=int(Z.sum()),
           revealed_px=int((oldT & ~Tn).sum()), added_px=int((Tn & ~(a_old8 > 127)).sum()))
# ---- the cut (tools/wheel/w7build.py, unchanged, on the whole set of the edit)
hard = Kc | Tn
ext = dil(hard, 4) & dil(up_hard, 1) & ~hard & ~(others_hard & ~up_hard)
T = bakef(E)
FR = 4.0
hard_a = hard | ext
aa = cv2.GaussianBlur(hard_a.astype(np.float32), (0, 0), 0.8); aa[~dil(hard_a, 2)] = 0
dk = dist(hard_a)
fr = np.clip(1 - (dk - 0.5) / FR, 0, 1) ** 1.5
fr_ok = ~dil(others_hard, 1)
a = np.where(hard_a, 1.0, np.where(fr_ok, fr, np.minimum(aa, 0.999))).astype(np.float32)
a[a < 0.02] = 0
# the patch: the lamp's pole where the old knit hid it (edit's segment, soft edge), only where the lamp layer is not opaque
pole = (oldT & ~Tn) & dil(lampS > 0.5, 1) & (lamp_a < 255)
a_pole = np.clip(cv2.GaussianBlur((lampS > 0.5).astype(np.float32), (0, 0), 0.7), 0, 1) * (1 - lamp_a.astype(np.float32) / 255)
a = np.where(pole, np.maximum(a, a_pole), a)
rec['pole_patch_px'] = int((pole & (a_pole > 0.02)).sum())
keep_new = keep_wo * (1 - a)
Q = np.ones((H, W, 3), np.float32)
for lt in lights:
    Q *= 1 - lt.astype(np.float32) / 255 * keep_new[..., None]
X = 255 - (255 - T) / np.maximum(Q, 1e-3)
Ck = np.clip(X / Su, 0, None)
mx = Ck.max(2, keepdims=True)
Ck = np.where(mx > 255, Ck * 255 / np.maximum(mx, 1e-3), Ck)
rec['over_255_scaled_px'] = int(((mx[..., 0] > 255) & Z).sum())
free = (~dil(hard_a, 2) & (a_up < 0.02) & (taper > 0) & ~pole).astype(np.float32)
near = np.exp(-dist(hard) / 10.0).astype(np.float32)
luma = lambda x: np.repeat((0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2])[..., None], 3, 2)
r = ratio_field(luma(Ck / 255.0), np.maximum(luma(Pbelow / 255.0), 0.004), free, near)
d = np.minimum(r, 1.0)
Wz = (np.clip(1 - dist(hard) / RADIUS, 0, 1) ** 1.5 * taper).astype(np.float32)
S_new = (d ** Wz[..., None]).astype(np.float32)
comp_s = np.rint(Pbelow * S_new)
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
hid = (a > 0) & (a_up > 0.02) & ~pole
C[hid] = nbf[hid]
# ---- merge into set B: the new cut inside Z only; the shadow blended by the distance to the throw
a8n = np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)
C8n = np.clip(np.rint(C), 0, 255).astype(np.uint8); C8n[a8n == 0] = 0
a8 = np.where(Z, a8n, a_old8).astype(np.uint8)
C8 = np.where(Z[..., None], C8n, C_old8).astype(np.uint8)
dT = dist(TT)
beta = np.clip((RADIUS - dT) / (RADIUS / 2), 0, 1).astype(np.float32)
beta[Kc] = 0
lS = (1 - beta[..., None]) * np.log(np.maximum(S_old8.astype(np.float32) / 255, 1e-4)) + beta[..., None] * np.log(np.maximum(S_new, 1e-4))
S8 = np.clip(np.rint(np.exp(lS) * 255), 0, 255).astype(np.uint8)
S8[(S8 >= 254).all(2) & (beta > 0)] = 255
S8 = np.where((beta > 0)[..., None], S8, S_old8).astype(np.uint8)
layer = np.dstack([C8, a8])
Image.fromarray(layer).save(PC + 'out/set-B-pecan-layer.png', optimize=True)
Image.fromarray(S8).save(PC + 'out/set-B-pecan-shadow.png', optimize=True)
np.save(PC + 'out/target.npy', np.rint(T).astype(np.uint8))
np.savez_compressed(PC + 'out/regions.npz', Z=Z, Kc=Kc, Tn=Tn, oldT=oldT, pole=pole)
ys, xs = np.nonzero(a8)
rec.update(alpha_px=int((a8 > 0).sum()), alpha_255_px=int((a8 == 255).sum()), shadow_px=int((S8 < 255).any(2).sum()),
           bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
ty, tx = np.nonzero(Tn)
rec['throw_bbox_px'] = [int(tx.min()), int(ty.min()), int(tx.max()), int(ty.max())]
oy, ox = np.nonzero(oldT)
rec['old_throw_bbox_px'] = [int(ox.min()), int(oy.min()), int(ox.max()), int(oy.max())]

# ---- compose, RND2, fidelity, colour, F3
stk = lambda L, S: [(n_, *((L, S) if n_ == 'cushions' else (a_, s_))) for n_, a_, s_ in lays]
c_old = ST.compose(base, lays, lights)
c_new = ST.compose(base, stk(layer, S8), lights)
f_old = ST.frame(c_old, man); f_new = ST.frame(c_new, man)
Image.fromarray(f_old).save(PC + 'out/frame-old.png'); Image.fromarray(f_new).save(PC + 'out/frame-new.png', optimize=True)
stored = np.asarray(Image.open(FB13 + 'default-frame-m0w-fix1.png').convert('RGB'))
chk = dict(build=rec)
chk['old_stack_vs_stored_default_frame_m0w_fix1'] = dict(max=int(np.abs(f_old.astype(int) - stored.astype(int)).max()), px_over_0=int((f_old != stored).any(2).sum()))
dl = (layer != lays[IC][1]).any(2); ds = (S8 != S_old8).any(2)
zone = dT <= RADIUS
region = Z | zone
dc = (c_new != c_old).any(2)
chk['rnd2'] = dict(rule='set B changes only in the throw: its layer only inside Z (the old and the new throw, 6 px, minus the cushions), its shadow only '
                        'within 90 px of the throw (stage A\'s zone of influence), every other layer, shadow and light byte-identical',
                   layer_changed_px=int(dl.sum()), layer_changed_outside_Z_px=int((dl & ~Z).sum()),
                   layer_changed_in_cushions_px=int((dl & Kc).sum()),
                   shadow_changed_px=int(ds.sum()), shadow_changed_outside_90px_of_throw_px=int((ds & ~zone).sum()),
                   canvas_changed_px=int(dc.sum()), canvas_changed_outside_throw_region_px=int((dc & ~region).sum()),
                   frame_changed_px=int((f_new != f_old).any(2).sum()))
fy, fx = np.nonzero((f_new != f_old).any(2))
chk['rnd2']['frame_changed_bbox_px'] = [int(fx.min()), int(fy.min()), int(fx.max()), int(fy.max())]
# hide the set: changes only its own region
without = ST.compose(base, [x for x in lays if x[0] != 'cushions'], lights)
reg_new = (a8 > 0) | (S8 < 255).any(2)
hide = (without != c_new).any(2)
chk['rnd2']['hide_set_changed_outside_its_region_px'] = int((hide & ~reg_new).sum())
# fidelity of the stack to the edit
Tt = T.astype(np.float32)
dd = np.abs(c_new.astype(np.float32) - Tt).max(2)
vis = (a_up < 0.02)
core = ero(Tn, 3) & vis
rv = (oldT & ~dil(Tn, 3)) & vis & ~(a8 > 0)
pole_v = pole & vis & (a8 > 127)
chk['fidelity_stack_vs_edit'] = dict(
    throw_opaque_visible=dict(px=int(core.sum()), mean=round(float(dd[core].mean()), 3), p99=round(float(np.percentile(dd[core], 99)), 2)),
    revealed_where_the_knit_was=dict(px=int(rv.sum()), mean=round(float(dd[rv].mean()), 2), p95=round(float(np.percentile(dd[rv], 95)), 2),
                                     note='the plate (sofa arm, wall) and the lower layers, under the new throw\'s shadow, against the edit\'s room'),
    pole_patch=dict(px=int(pole_v.sum()), mean=round(float(dd[pole_v].mean()), 2) if pole_v.any() else None))
# colours (Lab, D65): the new throw, the old knit, the SKU photo (exposure-matched as the studio's check)
def lab_of(img8, m):
    L_ = cv2.cvtColor(img8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    return np.median(L_[m], 0)
def de00(l1, l2):
    L1, a1, b1 = l1; L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = hs / 2 if abs(h1p - h2p) <= 180 else (hs + 360) / 2 if hs < 360 else (hs - 360) / 2
    Tq = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2); Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * Tq
    Rt = -2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hbp - 275) / 25) ** 2)))
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))
mnew = ero(Tn, 6) & vis
mold = ero(oldT, 6) & vis
lab_new = lab_of(c_new, mnew); lab_old = lab_of(c_old, mold)
sku = np.asarray(Image.open(PC + '../wm-pilot-refs/B-sofa-cover-cj-cotton-muslin-fringe-pecan-crop.png').convert('RGB'))
skl = cv2.cvtColor(sku.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
ms = (skl[..., 1] > 8) & (skl[..., 2] > 12) & (skl[..., 0] > 20)
lab_sku = np.median(skl[ms], 0)
def expo_match(sku_rgb, m, Lt):
    lin = srgb2lin(sku_rgb.astype(np.float32) / 255)
    Y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    def ycl(L):
        return ((L + 16) / 116) ** 3 if L > 8 else L / 903.3
    g = ycl(Lt) / max(float(np.median(Y[m])), 1e-6)
    out = np.clip(lin2srgb(np.clip(lin * g, 0, 1)) * 255, 0, 255).astype(np.uint8)
    return lab_of(out, m), g
lab_sku_x, gain = expo_match(sku, ms, float(lab_new[0]))
lab_sku_xo, _ = expo_match(sku, ms, float(lab_old[0]))
chk['colour_Lab_median'] = dict(new_throw_in_frame=[round(float(v), 1) for v in lab_new], old_knit_in_frame=[round(float(v), 1) for v in lab_old],
                                sku_photo=[round(float(v), 1) for v in lab_sku], sku_exposure_matched_to_new=[round(float(v), 1) for v in lab_sku_x],
                                exposure_gain=round(gain, 3),
                                de00_new_vs_sku_raw=round(de00(lab_new, lab_sku), 2), de00_new_vs_sku_exposure_matched=round(de00(lab_new, lab_sku_x), 2),
                                de00_old_vs_sku_exposure_matched=round(de00(lab_old, lab_sku_xo), 2),
                                note='medians of the throw\'s visible core (eroded 6 px) in the stack and of the SKU photo\'s throw (a* > 8, b* > 12); the SKU '
                                     'photo is a dim lifestyle shot, so the fidelity number is the exposure-matched one (as the wheel studio\'s check)')
hardN = a8 > 127
dtN = dist(hardN)
gaps = {}
for n_, aa_, _ in lays:
    if n_ == 'cushions':
        continue
    m = aa_[..., 3] > 127
    if not m.any():
        continue
    if (m & hardN).any():
        gaps[n_] = 'overlaps (%s)' % ('in front of the set' if names.index(n_) > IC else 'behind the set')
        continue
    g = float(dtN[m].min()) / FBW
    if g < 0.05:
        gaps[n_] = round(g, 4)
chk['F3_gap_frame_widths'] = gaps
json.dump(chk, open(PC + 'out/checks.json', 'w'), indent=1)
print(json.dumps(chk, indent=1))
