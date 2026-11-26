"""refeed.py (motion-agent, T-E0-W, 2026-11-26): the living room seen through the HDx2 opening rebuilt from M0-W fix1.
fb16 (hdx2-products-fb16-frame.png) showed the pre-fix1 M0-W through the opening, plus the old table's drums and smeared
products where its forward warp met the clay's misregistration. Here the whole opening is ray-cast from HDx2:
  shell   the room box (floor, back wall, window wall, right wall, ceiling) + the sofa box, textured by the fix1 'shell'
          (plate + rug + every product shadow + the lamps' light) seen from M0-W;
  armchair its box, the same texture, painted in depth order;
  products every fix1 layer as a billboard (vertical plane facing M0-W) on its own floor contact, wall art and sconces on the
          back wall, the curtain on the window wall; painted far to near.
The mapping convention is fb16's (M0-W clay camera, v0 0.52). Outside the opening: fb16, pixel for pixel.
  python3 refeed.py OUTDIR"""
import os, sys, json, numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geo
REPO = '/home/user/homedesign-app'
sys.path.insert(0, REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/tools/fix1')
import stack as ST
F = ST.F
HALL = REPO + '/assets/renders/hall/warm-modern/hall-products-2026-11-19/'
IDS = REPO + '/assets/blockout/house/framing/wm-hall-2026-11-18/HDx-id.png'
HFB = [71.10847058823515, 169.99851470588226, 2424.891529411765, 1494.0014852941176]
Mc = geo.Cam(**geo.M0W_CLAY)
VIEWS = dict(
    HDx2=dict(cam=geo.HDX2, ids=REPO + '/assets/blockout/house/framing/wm-hall-2026-11-18/HDx-id.png', fb=HFB, base=HALL + 'hdx2-products-fb16-frame.png'),
    HT2=dict(cam=dict(loc=(3.6, 8.15, 1.2), yaw=90.0, lens=24.0, u0=0.36, v0=0.48), ids=REPO + '/assets/blockout/house/framing/wm-hall-2026-11-18/HT-id.png',
             fb=[77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468], base=HALL + 'ht2-products-fb16-frame.png'))
Hc = None
MIRROR_FLOOR = False   # tried 2026-11-26: the mirrored planks read as chevrons; the unseen floor stays fb16
ROOM = dict(x=(-2.3, 2.5), y=(0.0, 6.2), h=3.0)
SOFA = dict(x=(-0.98, 1.26), y=(0.0, 0.88), z=(0.0, 0.70))      # fitted to the image in this convention (plinth row 988, back top 0.68-0.70)
ARM = dict(x=(-1.58, -0.74), y=(2.27, 3.16), z=(0.0, 0.70))      # the clay's armchair (m0w-ids 3 through m0w-depth), 3 cm margin

def canvas_A(fb):
    x0, y0, x1, y1 = fb; sx, sy = 1920 / (x1 - x0), 1080 / (y1 - y0)
    return np.array([[sx, 0, -x0 * sx + 0.5 * sx - 0.5], [0, sy, -y0 * sy + 0.5 * sy - 0.5], [0, 0, 1]])

def opening_mask(V):
    ids = np.array(Image.open(V['ids'])); x0, y0, x1, y1 = V['fb']; sx, sy = (x1 - x0) / 1920, (y1 - y0) / 1080
    A = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    f = cv2.warpAffine(ids, A, (1920, 1080), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
    return f, ((f >= 30) & (f <= 43)) | (f == 0)

def box_hit(C, D, b, inside=False):
    """slab test; D (...,3) rays with planar depth 1 along the camera axis; returns t (planar depth), inf where missed"""
    lo = np.array([b['x'][0], b['y'][0], b['z'][0]]); hi = np.array([b['x'][1], b['y'][1], b['z'][1]])
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (lo - C) / D; t2 = (hi - C) / D
    tmin = np.nanmax(np.minimum(t1, t2), -1); tmax = np.nanmin(np.maximum(t1, t2), -1)
    t = tmax if inside else tmin
    ok = (tmax >= tmin) & (t > 0.2)
    return np.where(ok, t, np.inf)

def warp_rgba(rgba, Ht):
    a = rgba[..., 3:4].astype(np.float32) / 255; pm = np.concatenate([rgba[..., :3].astype(np.float32) * a, a * 255], -1)
    s = np.sqrt(abs(np.linalg.det(Ht[:2, :2] / Ht[2, 2])))
    if s < 0.9: pm = cv2.GaussianBlur(pm, (0, 0), 0.45 / s)
    o = cv2.warpPerspective(pm, Ht, (1920, 1080), flags=cv2.INTER_LINEAR, borderValue=0)
    return o[..., :3], np.clip(o[..., 3:4] / 255, 0, 1)

def floor_anchor(alpha, A):
    ys, xs = np.nonzero(alpha > 128); yb = ys.max(); sel = ys >= yb - 3
    q = A @ np.array([xs[sel].mean(), yb, 1.0])
    P, _ = geo.plane_hit(Mc, q[:2][None], np.array([0, 0, 1.0]), 0.0); return P[0]

def build(view='HDx2'):
    global Hc
    V = VIEWS[view]; Hc = geo.Cam(**V['cam'])
    man, base, lays, lights = ST.load('layers/manifest-fix1.json')
    A = canvas_A(man['frame_box'])
    shell_l = [(a if s == 'rug' else np.concatenate([a[..., :3], 0 * a[..., 3:]], -1), sh) for s, a, sh in lays]
    S = ST.frame(F.compose(base, shell_l, lights), man).astype(np.float32)
    hd = np.array(Image.open(V['base']).convert('RGB')).astype(np.float32)
    ids, om = opening_mask(V)
    yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64); px = np.stack([xx, yy], -1)
    D = Hc.rays(px); C = Hc.C
    t_room = box_hit(C, D, dict(x=ROOM['x'], y=ROOM['y'], z=(0, ROOM['h'])), inside=True)
    t_sofa = box_hit(C, D, SOFA)
    t_sh = np.minimum(t_room, t_sofa)
    ARMM = (np.array(Image.open(os.path.join(HERE, 'arm_mask_m0w_frame.png'))) > 127).astype(np.float32)   # GrabCut on the plate frame
    armd = cv2.dilate(ARMM, np.ones((5, 5), np.uint8))
    def tex(t):
        P = C + np.where(np.isfinite(t), t, 1.0)[..., None] * D
        q, d = Mc.project(P)
        mx, my = q[..., 0].astype(np.float32), q[..., 1].astype(np.float32)
        ok = np.isfinite(t) & (d > 0.3) & (mx >= 0) & (mx <= 1919) & (my >= 0) & (my <= 1079)
        behind = cv2.remap(armd, mx, my, cv2.INTER_NEAREST, borderValue=0) > 0.5   # hidden by the armchair from M0-W
        return cv2.remap(S, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), ok & ~behind
    img, ok_sh = tex(t_sh)
    # the floor M0-W never sees (between its bottom edge and the opening): the same floor, mirrored in M0-W depth about
    # the bottom edge (a triangle wave inside a 0.7 m band), so the planks run on; the rug only up to RUG_Y
    shell0_l = [(np.concatenate([a_[..., :3], 0 * a_[..., 3:]], -1), sh) for s_, a_, sh in lays]
    S0 = ST.frame(F.compose(base, shell0_l, lights), man).astype(np.float32)
    Pf = C + np.where(np.isfinite(t_sh), t_sh, 1.0)[..., None] * D
    floor = np.isfinite(t_sh) & (np.abs(Pf[..., 2]) < 0.005) & ~ok_sh
    Q = Pf - Mc.C; dP = Q @ Mc.f; xP = Q @ Mc.r
    d_cut = Mc.k * 16 / 9 * Mc.C[2] / (1.0 - Mc.v0) + 0.03            # depth of M0-W's bottom row on the floor (+ a margin)
    band = 0.7; e = np.abs(dP - d_cut); e = np.mod(e, 2 * band); e = np.where(e > band, 2 * band - e, e)
    dR = d_cut + e
    PR = Mc.C + dR[..., None] * Mc.f + xP[..., None] * Mc.r; PR[..., 2] = 0
    q, _ = Mc.project(PR); mx, my = q[..., 0].astype(np.float32), q[..., 1].astype(np.float32)
    rugA = ST.frame(np.repeat([l for l in lays if l[0] == 'rug'][0][1][..., 3:4], 3, -1).astype(np.float64), man)[..., 0] / 255.0
    in_rug = cv2.remap(rugA.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderValue=0) > 0.5
    RUG_Y = 2.75
    use_rug = in_rug & (Pf[..., 1] < RUG_Y)
    fl = np.where(use_rug[..., None], cv2.remap(S, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT),
                  cv2.remap(S0, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
    okR = floor & (mx >= 0) & (mx <= 1919) & (my >= 0) & (my <= 1079) & ~(cv2.remap(armd, mx, my, cv2.INTER_NEAREST, borderValue=0) > 0.5)
    if MIRROR_FLOOR: img = np.where(okR[..., None], fl, img); ok_sh = ok_sh | okR
    # the armchair: a billboard of the shell texture through its GrabCut mask, at the clay's armchair centre
    P_arm = np.array([-1.16, 2.70, 0.0]); n = Mc.f.copy()
    Ha = geo.plane_H(Mc, Hc, n, float(n @ P_arm))
    arm_pm = cv2.warpPerspective(np.concatenate([S * ARMM[..., None], ARMM[..., None] * 255], -1), Ha, (1920, 1080), flags=cv2.INTER_LINEAR)
    arm_rgb, arm_a = arm_pm[..., :3], np.clip(arm_pm[..., 3:4] / 255, 0, 1)
    # billboards
    lay = {s: a for s, a, sh in lays}
    def bb(slot, P0=None, back=0.0, n=None):
        a = lay[slot]
        if P0 is None: P0 = floor_anchor(a[..., 3], A)
        n = Mc.f.copy() if n is None else np.array(n, float)
        P1 = P0 + back * Mc.f
        Hf = geo.plane_H(Mc, Hc, n, float(n @ P1))
        rgb, al = warp_rgba(a, Hf @ A)
        dist = float(np.linalg.norm((P1 - C)[:2]))
        with np.errstate(divide='ignore', invalid='ignore'):
            tp = (float(n @ P1) - float(n @ C)) / (D @ n)
        return dict(slot=slot, rgb=rgb, a=al, P=P1, dist=dist, t=tp)
    T = bb('coffee-table', back=0.30)
    items = [bb('framed-art', P0=np.array([0, 0.03, 0]), n=(0, 1, 0)), bb('accent-sconces', P0=np.array([0, 0.06, 0]), n=(0, 1, 0)),
             bb('curtains', P0=np.array([-2.2, 0, 0]), n=(1, 0, 0)), bb('vase', P0=np.array([-2.40, 1.38, 0.0])),
             bb('cushions', P0=np.array([0.2, 0.45, 0.0])), bb('pendant', P0=np.array([0.20, 1.72, 0.0])),
             bb('planter', back=0.15), bb('basket', back=0.12), bb('floor-lamp', back=0.10), bb('magazine-holder', back=0.10),
             T, bb('candle-holders', P0=T['P']), bb('bowl', P0=T['P'])]
    items.sort(key=lambda it: -it['dist'])
    arm_dist = float(np.linalg.norm(np.array([-1.16, 2.7]) - C[:2]))
    dep = np.where(np.isfinite(t_sh), t_sh, np.nan)
    with np.errstate(divide='ignore', invalid='ignore'):
        t_arm = (float(n @ P_arm) - float(n @ C)) / (D @ n)
    for it in items:
        if it['dist'] < arm_dist and 'arm_done' not in locals():
            img = arm_rgb + img * (1 - arm_a); arm_done = True; dep = np.where(arm_a[..., 0] > 0.5, t_arm, dep)
        img = it['rgb'] + img * (1 - it['a']); dep = np.where(it['a'][..., 0] > 0.5, it['t'], dep)
    if 'arm_done' not in locals(): img = arm_rgb + img * (1 - arm_a); dep = np.where(arm_a[..., 0] > 0.5, t_arm, dep)
    rec = dict(anchors={it['slot']: [round(float(v), 3) for v in it['P']] for it in items}, order=[it['slot'] for it in items])
    return dict(img=img, hd=hd, om=om, ok=ok_sh, ids=ids, rec=rec, depth=dep)

if __name__ == '__main__':
    out = sys.argv[1]; view = sys.argv[2] if len(sys.argv) > 2 else 'HDx2'; r = build(view)
    np.savez_compressed(out + '/refeed-%s.npz' % view, img=r['img'].clip(0, 255).astype(np.uint8), om=r['om'], ok=r['ok'], ids=r['ids'], depth=r['depth'].astype(np.float32))
    json.dump(r['rec'], open(out + '/refeed-anchors-%s.json' % view, 'w'), indent=1); print(r['rec']['order'])
