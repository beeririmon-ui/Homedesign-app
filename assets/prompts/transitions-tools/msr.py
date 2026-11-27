"""msr.py (motion-agent, FB21 leg 2 fix, 2026-11-27): multi-source refeed. 0 tokens.
Renders any camera of the hall/corridor from the approved stills and their depth (camgeo.dibr), so that every surface
and every product the new view shares with an approved still is that still's pixels, re-projected:
  HT2  ht2-products-fb16-finish.png (2720 canvas) + the clay HT depth, the four products' depth set from their own
       placement (the clay has none of them)
  HC2  hc.png (tall canvas) + hc-depth-fb17, graded to hc2-frame (the FB16 hall grade, per-channel LUT)
Combination: a pixel takes the nearest surface any source sees there (z-min over the sources), from the first source
in priority order that sees that surface; `valid` is False where no source sees it."""
import sys, os, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/home/user/homedesign-app/site/tools/transitions')
import camgeo as cg
sys.path.insert(0, '/home/user/homedesign-app/assets/renders/hall/warm-modern/hall-2026-11-18/tools')
import kit as K
R = '/home/user/homedesign-app/'
HP = R + 'assets/renders/hall/warm-modern/hall-products-2026-11-19/'
HA = R + 'assets/renders/hall/warm-modern/hall-2026-11-18/'
BLK = R + 'assets/blockout/house/framing/wm-hall-2026-11-18/'
L2 = R + 'assets/video/transitions/warm-modern/route-fb21/leg2/stills/'
HX = (2.462, 8.15, 1.20)

def rgb(p): return np.array(Image.open(p).convert('RGB'))

def lut_fit(a, b, m):
    """per-channel monotone LUT a -> b over mask m"""
    L = np.zeros((3, 256), np.float32)
    for c in range(3):
        x = a[..., c][m].astype(np.int64); y = b[..., c][m].astype(np.float64)
        s = np.bincount(x, y, 256); n = np.bincount(x, None, 256); ok = n > 20
        v = np.interp(np.arange(256), np.nonzero(ok)[0], s[ok] / n[ok])
        L[c] = np.maximum.accumulate(v)
    return L

def lut_apply(img, L):
    return np.stack([L[c][img[..., c]] for c in range(3)], -1).clip(0, 255).astype(np.uint8)

SCONCE = HP + 'layers/wall-sconce/wall-sconce-aliexpress-travertine-walnut-cylinder-332886-hall.png'
SCONCE_LIGHT = HP + 'layers/light/wall-sconce-aliexpress-travertine-walnut-cylinder-332886-hall-fb16.png'

def src_ht2(no_sconce=False):
    cv = K.canvas('HT'); cam = cg.HT
    img = rgb(HP + 'ht2-products-fb16-finish.png')
    if no_sconce:   # the sconce goes in as a billboard (sconce_sprite): here the wall behind it, with its light
        a = np.array(Image.open(SCONCE))[..., 3] > 4
        base = rgb(HA + 'ht2-fb16.png').astype(np.float32); Lg = rgb(SCONCE_LIGHT).astype(np.float32)
        scr = 255 - (255 - base) * (255 - Lg) / 255
        img = img.copy(); img[a] = np.clip(scr[a] + 0.5, 0, 255).astype(np.uint8)
    d, ok = cg.load_depth_png(BLK + 'HT-depth.png')
    d = d.copy()
    # the products are not in the clay: their pixels take the depth of their own placement (hall.json plan_m), ray-cast
    # from HT on the canvas: the sconce and the hooks a thin slab on the wall, the throw a folded block on the seat's +Y end
    # with its last panel dropping over the front edge, the basket a cylinder under the seat
    u, v = cv.uv(); D = cg.rays(cam, cv); C = np.array(cam.loc)
    def box(lo, hi):
        lo = np.array(lo); hi = np.array(hi)
        with np.errstate(divide='ignore', invalid='ignore'):
            t1 = (lo - C) / D; t2 = (hi - C) / D
        tn = np.nanmax(np.minimum(t1, t2), -1); tx = np.nanmin(np.maximum(t1, t2), -1)
        return np.where((tx >= tn) & (tn > 0), tn, np.inf)
    def cyl(cx, cy, r, z0, z1):
        ox, oy = C[0] - cx, C[1] - cy; a = D[..., 0] ** 2 + D[..., 1] ** 2; b = 2 * (ox * D[..., 0] + oy * D[..., 1]); c = ox * ox + oy * oy - r * r
        disc = b * b - 4 * a * c; t = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a); z = C[2] + t * D[..., 2]
        return np.where((disc > 0) & (z > z0) & (z < z1) & (t > 0), t, np.inf)
    geo_t = dict(**{'wall-sconce': box((0.80, 6.80, 1.50), (0.92, 7.05, 1.95)), 'wall-hooks': box((0.80, 6.70, 1.30), (0.86, 7.55, 1.55)),
                    'bench-throw': np.minimum(box((0.81, 7.09, 0.45), (1.215, 7.46, 0.525)), box((1.215, 7.09, 0.30), (1.235, 7.46, 0.525))),
                    'basket': cyl(1.01, 7.10, 0.15, 0.0, 0.30)})
    if no_sconce: geo_t.pop('wall-sconce')
    for slot, t in geo_t.items():
        f = [p for p in os.listdir(HP + 'layers/' + slot) if p.endswith('.png')][0]
        a = np.array(Image.open(HP + 'layers/' + slot + '/' + f))[..., 3] > 40
        hit = a & np.isfinite(t)
        d[hit] = np.minimum(d[hit], t[hit]); ok[a] = True
        d[a & ~np.isfinite(t)] = np.minimum(d[a & ~np.isfinite(t)], d[a & ~np.isfinite(t)])
    return dict(name='HT2', img=img, depth=d, ok=ok, cam=cam, cv=cv)

def hc2_lut():
    cv = K.canvas('HC'); raw = rgb(HA + 'hc.png')
    fr = cv.crop_frame(raw, 1920, 1080); g = rgb(L2 + 'hc2-frame.png')
    m = np.ones(fr.shape[:2], bool)
    L = lut_fit(fr, g, m); res = np.abs(lut_apply(fr, L).astype(int) - g.astype(int)).mean()
    return L, res

def src_hc2():
    cv = K.canvas('HC'); cam = cg.Cam(HX, 180.0, 0.50, 0.50)
    L, res = hc2_lut(); img = lut_apply(rgb(HA + 'hc.png'), L)
    d, ok = cg.load_room_depth(HA + 'hc-depth-fb17.png')
    return dict(name='HC2', img=img, depth=d, ok=ok, cam=cam, cv=cv, lut_residual=float(res))

def src_hdx2():
    cv = K.canvas('HDx'); cam = cg.HDX
    img = rgb(HP + 'hdx2-products-fb16-finish.png')
    d, ok = cg.load_room_depth(HP + 'hdx2-depth-fb17.png')
    return dict(name='HDx2', img=img, depth=d, ok=ok, cam=cam, cv=cv)

def src_hc130():
    cv = K.canvas('HC130'); cam = cg.Cam(HX, 130.0, 0.50, 0.50)
    L, res = hc2_lut(); img = lut_apply(rgb(HA + 'hc130.png'), L)
    d, ok = cg.load_depth_png(BLK + 'HC130-depth.png')
    return dict(name='HC130', img=img, depth=d, ok=ok, cam=cam, cv=cv)

def world_y(s):
    u, v = s['cv'].uv(); P = s['cam'].unproject(u, v, np.where(s['ok'], s['depth'], 1.0)); return P[..., 1]

def render(dst, dcv, srcs, keep=None, tol=0.04):
    """keep(src) -> bool mask on the source canvas of the points allowed to project (e.g. the hall side only)"""
    outs = []
    for s in srcs:
        dv = s['ok'] & (keep(s) if keep else True)
        o, v, z = cg.dibr(s['img'], s['depth'], s['cam'], s['cv'], dst, dcv, interp=cv2.INTER_LINEAR, tol=tol, depth_valid=dv)
        outs.append((o, v, np.where(np.isfinite(z), z, np.inf)))
    Z = np.min(np.stack([np.where(v, z, np.inf) for o, v, z in outs]), 0)
    img = np.zeros(outs[0][0].shape, np.uint8); val = np.zeros(Z.shape, bool); who = np.full(Z.shape, -1, np.int8)
    for i, (o, v, z) in enumerate(outs):
        take = v & ~val & (np.abs(z - Z) <= tol * np.maximum(Z, 0.05) + 0.01)
        img[take] = o[take]; val |= take; who[take] = i
    return img, val, np.where(val, Z, np.nan), who

# ---------------------------------------------------------------------------------------------------------------
# what no approved still sees, drawn in code on the plan geometry (no object is invented: fixed furniture of the clay,
# the floor and the ceiling of the plan)
# ---------------------------------------------------------------------------------------------------------------
WAL = np.array([61, 36, 23], np.float32)          # walnut, the bench's front edge in HT2 (shaded, facing +X)
BENCH = [((0.81, 6.70, 0.40), (1.21, 7.50, 0.45)), ((0.81, 6.70, 0.0), (1.21, 6.75, 0.40)), ((0.81, 7.45, 0.0), (1.21, 7.50, 0.40))]

def _box_t(C, D, lo, hi):
    lo = np.array(lo); hi = np.array(hi)
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (lo - C) / D; t2 = (hi - C) / D
    tn = np.nanmax(np.minimum(t1, t2), -1); tx = np.nanmin(np.maximum(t1, t2), -1)
    t = np.where((tx >= tn) & (tn > 0.05), tn, np.inf)
    P = C + np.where(np.isfinite(t), t, 0)[..., None] * D
    eps = 1e-4; n = np.zeros(D.shape, np.float32)
    for k in range(3):
        n[..., k] = np.where(np.abs(P[..., k] - lo[k]) < eps, -1, np.where(np.abs(P[..., k] - hi[k]) < eps, 1, 0))
    return t, n

def bench_layer(cam, cv, ss=2):
    """the clay's walnut bench (route 2.2) in this view: colour, coverage, planar depth"""
    big = cg.Canvas(cv.w * ss, cv.h * ss, tuple(b * ss for b in cv.box)); D = cg.rays(cam, big); C = np.array(cam.loc)
    T = np.full(D.shape[:2], np.inf); N = np.zeros(D.shape, np.float32)
    for lo, hi in BENCH:
        t, n = _box_t(C, D, lo, hi); m = t < T; T[m] = t[m]; N[m] = n[m]
    # face shading: top lit, faces toward the hall's light (+X) mid, end faces darker
    sh = np.where(N[..., 2] > 0.5, 1.55, np.where(np.abs(N[..., 0]) > 0.5, 1.0, 0.78))
    P = C + np.where(np.isfinite(T), T, 0)[..., None] * D
    grain = 1 + 0.06 * np.sin(P[..., 1] * 140 + 3 * np.sin(P[..., 0] * 37)) * (N[..., 2] > 0.5) + 0.05 * np.sin(P[..., 2] * 160 + 2 * np.sin(P[..., 0] * 41)) * (N[..., 2] <= 0.5)
    col = WAL[None, None] * (sh * grain)[..., None]
    cov = np.isfinite(T).astype(np.float32)
    col = cv2.resize(col * cov[..., None], (cv.w, cv.h), interpolation=cv2.INTER_AREA)
    cov = cv2.resize(cov, (cv.w, cv.h), interpolation=cv2.INTER_AREA)
    Tm = cv2.resize(np.where(np.isfinite(T), T, 1e3).astype(np.float32), (cv.w, cv.h), interpolation=cv2.INTER_NEAREST)
    return col / np.maximum(cov, 1e-3)[..., None], cov, np.where(cov > 0, Tm, np.inf)

_FLOOR = None
def floor_tex():
    """the corridor's smoked oak as HC2 shows it, rectified onto the plan: (X 1.70-3.10, Y 11.5-14.5) at 4 mm"""
    global _FLOOR
    if _FLOOR is None:
        s = src_hc2(); xs = np.arange(1.70, 3.10, 0.004); ys = np.arange(11.5, 14.5, 0.004)
        X, Y = np.meshgrid(xs, ys); P = np.stack([X, Y, np.zeros_like(X)], -1)
        u, v, d = s['cam'].project(P); mx, my = s['cv'].px(u, v)
        _FLOOR = cv2.remap(s['img'], mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
    return _FLOOR

def floor_fill(cam, cv, mask, gain):
    """floor pixels (Z = 0 of the plan) under `mask`: the corridor oak at the same plank columns (period 6 x 0.22 = 1.32 m)"""
    D = cg.rays(cam, cv); C = np.array(cam.loc)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = -C[2] / D[..., 2]
    P = C + t[..., None] * D
    tex = floor_tex(); h, w = tex.shape[:2]
    xs = 1.70 + np.mod(P[..., 0] - 1.70, 1.32); ys = 11.5 + np.mod(P[..., 1] - 11.5, 3.0)
    mx = ((xs - 1.70) / 0.004).astype(np.float32); my = ((ys - 11.5) / 0.004).astype(np.float32)
    out = cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out.astype(np.float32) * gain, 0, 255), mask & (t > 0)

def smooth_fill(img, hole, k=8):
    """large plain surfaces (the hall ceiling): inpainted at 1/k, then the plaster grain of the surroundings"""
    sm = cv2.resize(img, (img.shape[1] // k, img.shape[0] // k), interpolation=cv2.INTER_AREA)
    hm = cv2.resize(hole.astype(np.uint8), (img.shape[1] // k, img.shape[0] // k), interpolation=cv2.INTER_NEAREST)
    hm = cv2.dilate(hm, np.ones((3, 3), np.uint8))
    sm = cv2.inpaint(sm, hm * 255, 3, cv2.INPAINT_NS)
    up = cv2.resize(sm, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
    out = img.copy(); out[hole] = up[hole]; return out

def sconce_sprite(cam, cv):
    """the wall sconce (a cylinder: it looks the same from any side) as a camera-facing billboard from HT2's layer,
    at its own centre (from HT2's box and the wall + 6 cm), scaled by depth: (rgb float, alpha) on cv"""
    L = np.array(Image.open(SCONCE)).astype(np.float32); a = L[..., 3] / 255
    ys, xs = np.nonzero(a > 0.02); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    hcv = K.canvas('HT'); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    u = (cx + 0.5 - hcv.box[0]) / hcv.fw; v = (cy + 0.5 - hcv.box[1]) / hcv.fh
    d_ht = 3.60 - 0.86; P = cg.HT.unproject(u, v, d_ht)
    ud, vd, dd = cam.project(P); px, py = cv.px(ud, vd)
    s = (d_ht / float(dd)) * (cv.fw / hcv.fw)
    spr = L[y0:y1, x0:x1]; spr = np.concatenate([spr[..., :3] * spr[..., 3:] / 255, spr[..., 3:]], -1)   # premultiplied
    M = np.array([[s, 0, float(px) - s * (cx - x0)], [0, s, float(py) - s * (cy - y0)]], np.float32)
    o = cv2.warpAffine(spr, M, (cv.w, cv.h), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC, borderValue=0)
    al = np.clip(o[..., 3] / 255, 0, 1)
    return o[..., :3] / np.maximum(al, 1e-3)[..., None], al, dict(center_world=[round(float(c), 3) for c in P], px=[round(float(px), 1), round(float(py), 1)], scale=round(float(s), 4))

# ---------------------------------------------------------------------------------------------------------------
# any lens (camgeo.Cam is 24 mm): same interface (f, r, loc, u0, v0, project, unproject)
# ---------------------------------------------------------------------------------------------------------------
class LCam:
    def __init__(s, loc, yaw, u0, v0, lens=24.0):
        s.loc = tuple(float(x) for x in loc); s.yaw = float(yaw); s.u0 = float(u0); s.v0 = float(v0); s.lens = float(lens)
        s.ku = lens / 36.0; s.kv = s.ku * 16 / 9
        a = np.radians(yaw); s.f = np.array([-np.sin(a), -np.cos(a), 0.0]); s.r = np.array([np.cos(a), -np.sin(a), 0.0])
    def project(s, P):
        P = np.asarray(P, np.float64); q = P - np.asarray(s.loc); d = q @ s.f; x = q @ s.r
        with np.errstate(divide='ignore', invalid='ignore'):
            return s.u0 + s.ku * x / d, s.v0 + s.kv * (s.loc[2] - P[..., 2]) / d, d
    def unproject(s, u, v, d):
        u, v, d = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64), np.asarray(d, np.float64))
        x = (u - s.u0) / s.ku * d; z = s.loc[2] - (v - s.v0) / s.kv * d
        P = np.asarray(s.loc)[None] + d[..., None] * s.f + x[..., None] * s.r; P = P.reshape(d.shape + (3,)); P[..., 2] = z; return P
    def rays(s, cv):
        u, v = cv.uv(); x = (u - s.u0) / s.ku; z = (s.v0 - v) / s.kv
        return x[..., None] * s.r + z[..., None] * np.array([0.0, 0.0, 1.0]) + s.f

def cam(loc, yaw, u0, v0, lens=24.0):
    return LCam(loc, yaw, u0, v0, lens)

LIV = R + 'assets/renders/living-room/warm-modern/fb13-2026-11-25/'

def src_m0w():
    """the living room: default-frame-m0w-fix1-pecan.png (the frame) on the M0-W clay camera (35 mm, v0 0.52, the
    convention refeed.py was fitted in) with the clay depth (every product proxy) cut to the frame"""
    c = LCam((0.95, 5.55, 1.05), 14.0, 0.50, 0.52, 35.0); fcv = cg.Canvas.frame(1920)
    img = rgb(LIV + 'default-frame-m0w-fix1-pecan.png')
    d, ok = cg.load_room_depth(LIV + 'm0w-depth.png')
    bcv = cg.Canvas.base(2720); u, v = fcv.uv(); mx, my = bcv.px(u, v)
    d = cv2.remap(np.where(ok, d, 0).astype(np.float32), mx.astype(np.float32), my.astype(np.float32), cv2.INTER_NEAREST)
    return dict(name='M0W', img=img, depth=d, ok=d > 0, cam=c, cv=fcv)

def plan_input(dst, cv):
    """flat plan tones (rooms as boxes, openings as holes) for what no still sees: the seedream input's base"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('plan_seed', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plan_seed.py'))
    ps = importlib.util.module_from_spec(spec); spec.loader.exec_module(ps)
    D = dst.rays(cv) if hasattr(dst, 'rays') else cg.rays(dst, cv)
    return ps.cast(np.array(dst.loc), D, want_t=True)

# ---------------------------------------------------------------------------------------------------------------
# any room's display frame as a source (style-agnostic): the finish image on its own canvas + its depth-fb17 map
# + the camera of docs/house-plan.json by id
# ---------------------------------------------------------------------------------------------------------------
def plan_cam(cid, plan=R + 'docs/house-plan.json'):
    import json as _j
    p = _j.load(open(plan)); cs = p['cameras'] if isinstance(p['cameras'], list) else list(p['cameras'].values())
    c = [c for c in cs if c.get('id') == cid][0]
    return LCam(c['loc'], c['yaw_deg_left'], c.get('u0') or 0.5, c.get('v0') or 0.5, c.get('lens') or 24.0)

def src_frame(name, image, depth, cid=None, camera=None, canvas=None):
    """image: the frame's finish on the depth map's canvas (2720 x 1530 base unless `canvas`), depth: a depth-fb17 png
    (near = bright, json beside it), cid: the house-plan camera id (or `camera` = LCam)"""
    img = rgb(image); d, ok = cg.load_room_depth(depth)
    cv = canvas or (cg.Canvas.base(img.shape[1]) if img.shape[1] != 1920 else cg.Canvas.frame(1920))
    if d.shape[:2] != img.shape[:2]:
        raise SystemExit(f'{name}: image {img.shape[:2]} and depth {d.shape[:2]} are not on one canvas')
    return dict(name=name, img=img, depth=d, ok=ok, cam=camera or plan_cam(cid), cv=cv)

# ---------------------------------------------------------------------------------------------------------------
# warm-modern corridor and rooms (FB21 legs 4-5)
# ---------------------------------------------------------------------------------------------------------------
COR = R + 'assets/renders/corridor/warm-modern/route-2026-11-27/'
RN = R + 'assets/renders/'

def src_corr(name):
    """CK / CM: the still on its 2720 canvas + the clay's planar depth pass (the still is locked to the clay, 0-2 px)"""
    cam = dict(CK=LCam((2.45, 14.20, 1.20), 0.0, 0.5, 0.5), CM=LCam((2.45, 14.40, 1.20), 180.0, 0.5, 0.5))[name]
    img = rgb(COR + name + '.png'); d = np.load(COR + 'clay/' + name + '-passes.npz')['depth'].astype(np.float32)
    ok = np.isfinite(d) & (d > 0.05) & (d < 60)
    return dict(name=name, img=img, depth=np.where(ok, d, 1.0), ok=ok, cam=cam, cv=cg.Canvas.base(2720))

ROOMSRC = {
    'B1': (RN + 'bath/warm-modern/b1-2026-11-19/b1-defaults-fb16-finish.png', RN + 'bath/warm-modern/b1-2026-11-19/depth-fb17.png', 'B1', None),
    'K-boy': (RN + 'boy/warm-modern/stage1-2026-11-24/K-boy-defaults-fb16-finish.png', RN + 'boy/warm-modern/stage1-2026-11-24/depth-fb17.png', 'K-boy', None),
    'K-girl': (RN + 'girl/warm-modern/stage1-2026-11-24/K-girl-defaults-g1-fb16-finish.png', RN + 'girl/warm-modern/stage1-2026-11-24/depth-fb17.png', 'K-girl', None),
    'MB0': (RN + 'master/warm-modern/stage1-2026-11-17/mb0-defaults-fb16-finish.png', RN + 'master/warm-modern/stage1-2026-11-17/depth-fb17.png', 'MB0', None),
    'MB1': (RN + 'master/warm-modern/mb1-2026-11-19/mb1-defaults-fb16-finish.png', RN + 'master/warm-modern/mb1-2026-11-19/depth-fb17.png', None,
            ((1.60, 21.20, 1.05), 33.7, 0.5, 0.418)),
}

def src_room(name):
    img, dep, cid, cam = ROOMSRC[name]
    return src_frame(name, img, dep, cid=cid, camera=LCam(*cam) if cam else None)
