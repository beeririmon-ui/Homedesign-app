"""extract_fix1.py (v2): the changed layers of M0-W fix1, by the hero's method. The base stays plate-PW.png; every product is cut from the
new hero (hero-HW-fix1.png = hero-HW.png + four nano edits pasted inside their own regions). Alpha: an opaque core where the new hero
differs from the room behind it (de-finished stack), soft only at the fringe; the shadow (multiply) is SOLVED so that the composed stack
gives the new hero's pixel exactly under the compose formula (lights screened x keep), then smoothed (1.4 px) with a 3 % dead zone, inside
the edit's region only. The finish of stage A (vignette 0.15 stop, the ONE grain field seed 1540 x 1.2 x midtone weight) baked into new
layer pixels; no DOF (sigma < 0.35 px at these depths). Changed files: planter layer+shadow, magazine-holder layer+shadow, curtains
layer (+ a neutral shadow), the rug layer (under the old holder only), the three light layers (under the old olive's leaves only)."""
import os, sys, json
import cv2, numpy as np
from PIL import Image
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/tools')
import stack as ST
import reg as RG
sys.path.insert(0, '/home/user/homedesign-app/assets/renders/tools/finish')
import finish as F
S = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix1/'
R = ST.FB13 + '/'
O = S + 'out/stack-fix1/'; os.makedirs(O, exist_ok=True)
H, W = 1530, 2720
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
MOUTH = 1178
srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
def vignette():
    x0, y0, x1, y1 = FB
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rho = np.hypot((xx - (x0 + x1) / 2) / ((x1 - x0) / 2), (yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) / np.sqrt(2.0)
    return (2.0 ** (-0.15 * np.clip(rho, 0, 1.15) ** 2.4)).astype(np.float32)
def nblur(img, w, s):
    img3 = img if img.ndim == 3 else img[..., None]
    num = cv2.GaussianBlur(img3 * w[..., None], (0, 0), s); den = cv2.GaussianBlur(w, (0, 0), s)
    num = num if num.ndim == 3 else num[..., None]
    out = num / np.maximum(den, 1e-5)[..., None]
    return (out if img.ndim == 3 else out[..., 0]), den
man, base, lays, lights = ST.load()
V = vignette()
Lb = F.Lstar(base) / 100.0
GR = F.grain_field((H, W)) * 1.2 * np.clip(4 * Lb * (1 - Lb), 0.25, 1.0)
bakef = lambda rgb01: np.clip(lin2srgb(srgb2lin(np.clip(rgb01, 0, 1)) * V[..., None]) * 255.0 + GR[..., None], 0, 255)
bake = lambda rgb01: np.rint(bakef(rgb01)).astype(np.uint8)
unbake = lambda rgb8: np.clip(lin2srgb(srgb2lin(np.clip((rgb8.astype(np.float32) - GR[..., None]) / 255.0, 0, 1)) / V[..., None]), 0, 1)
rd = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255
hero = rd(R + 'hero-HW.png')
new = np.load(S + 'out/hero-fix1-edits.npy').astype(np.float32)
Mk = np.load(S + 'out/masks.npz')
LAY = {k: (a, s) for k, a, s in lays}
names = [k for k, _, _ in lays]
rec = {}
# ---------------- E4: the old holder out (the rug under it from the nano removal)
w4, d4, r4 = RG.reg('e4-holderout', 'e4-holderout-nano.jpg')
rec['e4_registration'] = {k: v for k, v in r4.items() if k != 'A'}
x0, y0, x1, y1 = 560, 1071, 1376, 1530
e4 = new.copy(); e4[y0:y1, x0:x1] = w4
oldH = LAY['magazine-holder'][0][..., 3] > 0
oldHs = (LAY['magazine-holder'][1] < 255).any(2)
_hull = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(_hull, cv2.convexHull(np.argwhere(oldH)[:, ::-1].astype(np.int32)), 1)
Rh = dil(_hull.astype(bool) | oldH | oldHs, 4); Rh[:y0 + 4] = False; Rh[:, :x0 + 4] = False; Rh[:, x1 - 4:] = False
wh = cv2.GaussianBlur(Rh.astype(np.float32), (0, 0), 1.5) * dil(Rh, 2)
new = new * (1 - wh[..., None]) + e4 * wh[..., None]
rug_a, rug_s = LAY['rug']
rug_rgb = rug_a[..., :3].astype(np.float32)
rug_new = np.where((wh > 0)[..., None], rug_rgb * (1 - wh[..., None]) + bakef(e4) * wh[..., None], rug_rgb)
# the old holder stood on the rug (its whole hull lies inside the rug): the rug is whole there (the old layer had a few alpha-0 holes)
rug_in = cv2.morphologyEx((rug_a[..., 3] > 0).astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))).astype(bool)
wh = wh * rug_in
rug_alpha = np.where(Rh & rug_in & (wh > 0.5), 255, rug_a[..., 3]).astype(np.uint8)
rug_new = np.where((wh > 0)[..., None], bakef(e4) * np.maximum(wh, (rug_a[..., 3] == 0) & (wh > 0))[..., None]
                   + rug_rgb * (1 - np.maximum(wh, (rug_a[..., 3] == 0) & (wh > 0)))[..., None], rug_rgb)
rug_layer = np.dstack([np.clip(np.rint(rug_new), 0, 255).astype(np.uint8), rug_alpha])
rug_layer[rug_alpha == 0, :3] = rug_a[rug_alpha == 0, :3]
rec['rug_changed_px'] = int((rug_layer != rug_a).any(2).sum())
# ---------------- the planter's alpha: the body below the mouth = the old layer; the olive = an opaque core from the new hero
pa, ps = LAY['planter']
reg1 = Mk['e1']
def room_without(skip):
    L2 = [(np.zeros_like(a), s if not skip[k] else None) if k in skip else (a, s) for k, a, s in lays]
    return unbake(F.compose(base, L2, lights).astype(np.float32))
Bp = room_without({'planter': False})
diff = np.abs(new - Bp).max(2)
k = new.mean(2) / np.maximum(Bp.mean(2), 1e-3)
lab_n = cv2.cvtColor(np.clip(new, 0, 1), cv2.COLOR_RGB2LAB)
shadowlike = (np.abs(new - Bp * k[..., None]).max(2) < 0.035) & (k > 0.45) & (lab_n[..., 1] > -1.0)
core = (diff > 0.10) & ~shadowlike & dil(reg1, 2)
core[:, 1095:] = False                       # the crown ends at x ~1090; right of it is the leaf shadow and the wall light's cone
# the trunk (thin, warm grey): forced into the layer between the crown and the mouth
trunk = (diff > 0.06) & dil(reg1, 2); trunk[:700] = False; trunk[:, :840] = False; trunk[:, 960:] = False
core |= trunk
core[MOUTH:] = False
core = cv2.morphologyEx(core.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
n, lab, st, _ = cv2.connectedComponentsWithStats(dil(core, 2).astype(np.uint8))
core &= np.isin(lab, [i for i in range(1, n) if st[i, 4] > 3000])
ramp = np.clip((diff - 0.05) / 0.10, 0, 1) * dil(core, 2) * ~shadowlike
alpha_t = np.maximum(cv2.GaussianBlur(core.astype(np.float32), (0, 0), 0.6), ramp)
alpha_t[MOUTH:] = 0
pa_a = pa[..., 3].astype(np.float32) / 255
pa_a[:MOUTH] = alpha_t[:MOUTH]
# the soil band just above the rim line belongs to the planter too (the old layer's mouth pixels, where the new hero is the planter)
mouthband = np.zeros((H, W), bool); mouthband[MOUTH - 14:MOUTH] = True
mouthband &= (pa[..., 3] > 0)
pa_a[mouthband] = np.maximum(pa_a[mouthband], pa[..., 3][mouthband] / 255.0)
rgb_p = pa[..., :3].copy()
rgb_p[:MOUTH] = bake(new)[:MOUTH]
pl_layer = np.dstack([rgb_p, np.clip(np.rint(pa_a * 255), 0, 255).astype(np.uint8)])
pl_layer[pl_layer[..., 3] == 0, :3] = 0
# ---------------- the lights under the old olive's leaves (now open wall): filled from the wall around (they were never seen)
old_leaf = (pa[..., 3] > 0); old_leaf[MOUTH - 14:] = False
hole = dil(old_leaf, 3) & ~(pl_layer[..., 3] > 250)
lights_new = []
for lt in lights:
    f, _ = nblur(lt.astype(np.float32), (~dil(old_leaf, 3)).astype(np.float32), 10.0)
    l2 = lt.astype(np.float32).copy(); l2[hole] = f[hole]
    lights_new.append(np.clip(np.rint(l2), 0, 255).astype(np.uint8))
rec['lights_changed_px'] = [int((a != b).any(2).sum()) for a, b in zip(lights_new, lights)]
# ---------------- the curtain (z 10): nano's linen, alpha by its own hem; a neutral shadow (sheer; the sun patch kept)
a2 = Mk['e2_alpha'].astype(np.float32)
cu_rgb = bake(new); cu_rgb[a2 == 0] = 0
cu_layer = np.dstack([cu_rgb, np.rint(a2 * 255).astype(np.uint8)])
cu_shadow = np.full((H, W, 3), 255, np.uint8)
# ---------------- the holder (new place): opaque core from the new hero over the room there
B3 = room_without({'magazine-holder': True})
reg3 = Mk['e3']
d3 = np.abs(new - B3).max(2)
k3 = new.mean(2) / np.maximum(B3.mean(2), 1e-3)
sl3 = (np.abs(new - B3 * k3[..., None]).max(2) < 0.03) & (k3 < 1.0)
c3 = (d3 > 0.07) & reg3                  # the gunmetal tubes are near-neutral: the shadow-like test would take them, so only the diff decides
c3 = cv2.morphologyEx(c3.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
n, lab, st, _ = cv2.connectedComponentsWithStats(c3.astype(np.uint8))
c3 &= np.isin(lab, [i for i in range(1, n) if st[i, 4] > 1500])
ramp3 = np.clip((d3 - 0.04) / 0.05, 0, 1) * dil(c3, 2) * ~(sl3 & (d3 < 0.07))
ah = np.maximum(cv2.GaussianBlur(c3.astype(np.float32), (0, 0), 0.6), ramp3)
ah[~dil(c3, 2)] = 0
# on the floor strip (below the skirting's foot, row ~1350) the dark floor and the dark tubes have the same colour: there the layer keeps
# only the four legs, found where the tubes cross the skirting just above (narrow runs) and followed down to their feet
FLOOR0 = 1350
def narrow_runs(prof, maxw):
    out, x = [], 0
    while x < W:
        if prof[x]:
            x1 = x
            while x1 < W and prof[x1]:
                x1 += 1
            if x1 - x <= maxw:
                out.append((x, x1))
            x = x1
        else:
            x += 1
    return out
runs = narrow_runs((ah[1310:1340] > 0.5).mean(0) > 0.6, 30)
below = (d3[FLOOR0 + 5:FLOOR0 + 35] > 0.03).mean(0) > 0.6
below[:2300] = False; below[2620:] = False
runs += [r for r in narrow_runs(below, 24) if all(r[1] < a or r[0] > b for a, b in runs)]
runs = [r for r in runs if r[1] - r[0] >= 5]
legs = np.zeros((H, W), np.float32)
for xa, xb in runs:
    y, quiet = FLOOR0 - 30, 0
    while y < FLOOR0 + 50 and quiet < 3:
        quiet = quiet + 1 if (y > FLOOR0 and np.median(d3[y, xa:xb]) < 0.045) else 0
        y += 1
    legs[FLOOR0 - 30:y - quiet, max(0, xa - 1):xb + 1] = 1
legs_m = legs > 0
ah[FLOOR0 - 30:] = np.where(legs_m[FLOOR0 - 30:], np.maximum(ah[FLOOR0 - 30:], cv2.GaussianBlur(legs, (0, 0), 0.6)[FLOOR0 - 30:] * (d3[FLOOR0 - 30:] > 0.02)), ah[FLOOR0 - 30:])
ah[FLOOR0:] = np.where(legs_m[FLOOR0:], ah[FLOOR0:], 0)
_n, _lab, _st, _ = cv2.connectedComponentsWithStats((ah > 0.02).astype(np.uint8))
_small = np.isin(_lab, [i for i in range(1, _n) if _st[i, 4] < 80])
ah[_small] = 0
rec['holder_legs'] = [[int(a), int(b)] for a, b in runs]
h_rgb = bake(new); h_rgb[ah == 0] = 0
ho_layer = np.dstack([h_rgb, np.clip(np.rint(ah * 255), 0, 255).astype(np.uint8)])
# ---------------- the shadows, solved: final = 255 - (255 - o)*Q, o = P*S/255 (1 - a) + c a ; Q = prod(1 - L keep / 255)
def stack_new(sh_pl=None, sh_ho=None):
    out = [('curtains', cu_layer, cu_shadow)]
    for kk, a, s in lays:
        if kk == 'planter': a, s = pl_layer, (sh_pl if sh_pl is not None else s)
        if kk == 'magazine-holder': a, s = ho_layer, (sh_ho if sh_ho is not None else np.full_like(s, 255))
        if kk == 'rug': a = rug_layer
        out.append((kk, a, s))
    return out
T = bakef(new)
def solve(kname, region, s_init):
    L_ = stack_new()
    i = [x[0] for x in L_].index(kname)
    P = F.compose(base, [(a, s) for _, a, s in L_[:i]], []).astype(np.float32)
    keep = np.ones((H, W), np.float32)
    for _, a, _ in L_:
        keep *= 1 - a[..., 3].astype(np.float32) / 255
    Q = np.ones((H, W, 3), np.float32)
    for lt in lights_new:
        Q *= 1 - lt.astype(np.float32) / 255 * keep[..., None]
    up = np.zeros((H, W), np.float32)
    for _, a, _ in L_[i + 1:]:
        up = 1 - (1 - up) * (1 - a[..., 3].astype(np.float32) / 255)
    own = L_[i][1][..., 3].astype(np.float32) / 255
    o = 255 - (255 - T) / np.maximum(Q, 1e-3)
    Sraw = np.clip(o / np.maximum(P, 1.0), 0, 1.5)
    valid = ((own < 0.02) & (up < 0.02) & region).astype(np.float32)
    Ss, den = nblur(Sraw, valid, 1.4)
    Sf, _ = nblur(Sraw, valid, 6.0)
    Ss = np.where((den > 0.2)[..., None], Ss, Sf)
    art = LAY['framed-art'][0][..., 3] > 0
    lum, _ = nblur(Sraw.mean(2), valid, 3.0)
    Ss = np.where((art & region)[..., None], lum[..., None], Ss)
    Ss = np.clip(Ss / 0.97, 0, 1)
    z = cv2.GaussianBlur(region.astype(np.float32), (0, 0), 3) * dil(region, 6)
    z = z[..., None]
    return np.clip(np.rint((s_init.astype(np.float32) / 255 * (1 - z) + Ss * z) * 255), 0, 255).astype(np.uint8)
zone1 = dil(reg1, 6); zone1[MOUTH:] = False
pl_shadow = solve('planter', zone1, ps)
zone3 = dil(reg3, 8)
ho_shadow = solve('magazine-holder', zone3, np.full((H, W, 3), 255, np.uint8))
# ---- the one refit (recorded): nano drew the holder ~0.38 m wide (the card: 35 cm) and 0.015 of the frame from the floor lamp (F3 needs
# 0.02) with 0.022 to the frame's right edge (the edge-tangent rule needs 0.02). Scaled x0.92 about its feet line (the feet stay on the
# floor, same depth) and centred between the lamp and the edge; its shadow goes with it. Pixels re-baked at their new positions.
lampA = LAY['floor-lamp'][0][..., 3] > 127
ys_, xs_ = np.nonzero(ah > 0.5)
hx0, hx1, FEET = xs_.min(), xs_.max(), 1400.0
dt_l = cv2.distanceTransform((~lampA).astype(np.uint8), cv2.DIST_L2, 5)
lamp_x = float(hx0 - dt_l[ah > 0.5].min())                       # the lamp's nearest edge, as an x left of the holder
SC = 0.92
w_new = (hx1 - hx0) * SC
left_new = lamp_x + ((FB[2] - lamp_x) - w_new) / 2.0
cx = (hx0 + hx1) / 2.0
dx = left_new - (cx + SC * (hx0 - cx))
Mh = np.float32([[SC, 0, cx - SC * cx + dx], [0, SC, FEET - SC * FEET]])
warp = lambda img, interp=cv2.INTER_AREA: cv2.warpAffine(img, Mh, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
a_w = warp(ah.astype(np.float32), cv2.INTER_LINEAR)
pm = warp(new * ah[..., None], cv2.INTER_LINEAR)
rgb_w = np.where((a_w > 1e-3)[..., None], pm / np.maximum(a_w, 1e-3)[..., None], 0)
h_rgb = bake(rgb_w); h_rgb[a_w <= 1e-3] = 0
ho_layer = np.dstack([h_rgb, np.clip(np.rint(a_w * 255), 0, 255).astype(np.uint8)])
ho_layer[ho_layer[..., 3] == 0, :3] = 0
s_w = cv2.warpAffine(ho_shadow.astype(np.float32), Mh, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
ho_shadow = np.clip(np.rint(s_w), 0, 255).astype(np.uint8)
rec['holder_refit'] = dict(scale=SC, about='feet line y 1400', dx_px=round(float(dx), 1), matrix=[[round(float(v), 4) for v in r] for r in Mh])
# ---------------- the hero record: new hero; the vase (in front of the curtain) back over it
va = LAY['vase'][0][..., 3].astype(np.float32) / 255
heroN = new * (1 - va[..., None]) + hero * va[..., None]
Image.fromarray(np.rint(np.clip(heroN, 0, 1) * 255).astype(np.uint8)).save(S + 'out/hero-fix1.png')
out = dict(zip(['layer-planter', 'shadow-planter', 'layer-curtains', 'shadow-curtains', 'layer-magazine-holder', 'shadow-magazine-holder', 'layer-rug'],
               [pl_layer, pl_shadow, cu_layer, cu_shadow, ho_layer, ho_shadow, rug_layer]))
for i_, lt in enumerate(lights_new):
    out[f'light-{i_}'] = lt
for nm, arr in out.items():
    Image.fromarray(arr).save(O + nm + '.png')
rec.update(planter_alpha_px=int((pl_layer[..., 3] > 0).sum()), planter_shadow_px=int((pl_shadow < 255).any(2).sum()),
           curtain_alpha_px=int((cu_layer[..., 3] > 0).sum()), holder_alpha_px=int((ho_layer[..., 3] > 0).sum()),
           holder_alpha_opaque_px=int((ho_layer[..., 3] == 255).sum()), holder_shadow_px=int((ho_shadow < 255).any(2).sum()),
           planter_body_below_mouth_identical=bool((pl_layer[MOUTH:] == np.where(pa[MOUTH:, :, 3:4] > 0, pa[MOUTH:], 0)).all()))
json.dump(rec, open(O + 'extract.json', 'w'), indent=1)
print(json.dumps(rec))
