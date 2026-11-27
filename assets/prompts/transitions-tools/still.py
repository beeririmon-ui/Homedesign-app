"""still.py (FB21): a waypoint still's seedream input on a plan camera, from the approved stills. 0 tokens.
  python3 still.py CONFIG.json
CONFIG: {"name", "cam": {"loc", "yaw", "u0", "v0", "lens"}, "sources": {"HT2": "y>6.27", "M0W": "y<6.2", ...},
         "bench": true|false, "out": "DIR"}
Every pixel an approved still sees (msr.render: z-min over the sources, each limited to its own region of the plan by the
`keep` expression in world X, Y, Z) is that still's pixel; the rest is the plan's flat tones (plan_seed.cast), the
seedream input. Writes OUT/NAME-input.png, NAME-masks.npy (ones, valid, hole, who, bench) and NAME.json."""
import sys, os, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msr
cg = msr.cg
REG = dict(HT2=lambda: msr.src_ht2(no_sconce=True), HC2=msr.src_hc2, HDx2=msr.src_hdx2, HC130=msr.src_hc130, M0W=msr.src_m0w,
           CK=lambda: msr.src_corr('CK'), CM=lambda: msr.src_corr('CM'), **{k: (lambda k=k: msr.src_room(k)) for k in msr.ROOMSRC})

def world(s):
    u, v = s['cv'].uv(); return s['cam'].unproject(u, v, np.where(s['ok'], s['depth'], 1.0))

def main(cfgp):
    C = json.load(open(cfgp)); out = C['out']; os.makedirs(out, exist_ok=True); nm = C['name']
    c = C['cam']; dst = msr.LCam(c['loc'], c['yaw'], c['u0'], c['v0'], c.get('lens', 24.0)); cv = cg.Canvas.frame(1920)
    if 'canvas' in C:
        w, h = C['canvas']; cv = cg.Canvas(w, h, ((w - 1920) / 2, (h - 1080) / 2, (w + 1920) / 2, (h + 1080) / 2))
    def mk(k, v):
        if isinstance(v, dict):    # a finished waypoint still as a source: {"keep", "img", "depth_npy", "cam"}
            c2 = v['cam']; dd = np.load(v['depth_npy'])
            return dict(name=k, img=msr.rgb(v['img']), depth=dd, ok=dd > 0.05, cam=msr.LCam(c2['loc'], c2['yaw'], c2['u0'], c2['v0'], c2.get('lens', 24.0)), cv=cg.Canvas.frame(1920))
        return REG[k]()
    srcs = [mk(k, v) for k, v in C['sources'].items()]
    exprs = {k: (v['keep'] if isinstance(v, dict) else v) for k, v in C['sources'].items()}
    def keep(s):
        P = world(s); X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
        return eval(exprs[s['name']], {'np': np}, dict(x=X, y=Y, z=Z))
    img, val, Z, who = msr.render(dst, cv, srcs, keep=keep)
    base, PT = msr.plan_input(dst, cv)
    occl = val & (np.where(np.isfinite(Z), Z, 0) > PT * 1.03 + 0.05)          # behind a wall of the plan that no source shows
    val = val & ~occl; who = np.where(val, who, -1); Z = np.where(val, Z, np.nan)
    inp = np.where(val[..., None], img.astype(np.float32), base)
    bm = np.zeros(val.shape, bool)
    if C.get('bench'):
        bcol, bcov, bT = msr.bench_layer(dst, cv); Zf = np.where(np.isfinite(Z), Z, np.inf)
        bm = (bcov > 0) & ~(val & (Zf < bT - 0.02))
        inp = np.where(bm[..., None], bcol * bcov[..., None] + inp * (1 - bcov[..., None]), inp)
    for pan in C.get('panels', []):           # flat plan panels no still shows (a folded leaf, a colour block): plane x = X or y = Y
        D = dst.rays(cv); Cc = np.array(dst.loc); ax = 0 if 'x' in pan and not isinstance(pan['x'], list) else 1
        at = pan['x'] if ax == 0 else pan['y']; span = pan['y'] if ax == 0 else pan['x']
        with np.errstate(divide='ignore', invalid='ignore'):
            t = (at - Cc[ax]) / D[..., ax]
        P = Cc + t[..., None] * D; o = 1 - ax
        m = (t > 0) & (P[..., o] > span[0]) & (P[..., o] < span[1]) & (P[..., 2] > pan['z'][0]) & (P[..., 2] < pan['z'][1]) & (t <= PT + 0.02) & ~val
        inp[m] = np.array(pan['rgb'], np.float32) * (0.9 + 0.1 * np.clip(P[..., 2][m] / 2.4, 0, 1))[:, None]
    Image.fromarray(np.clip(inp + 0.5, 0, 255).astype(np.uint8)).save(f'{out}/{nm}-input.png')
    np.save(f'{out}/{nm}-masks.npy', np.stack([np.ones(val.shape, np.float32), val.astype(np.float32), (~val).astype(np.float32),
                                               who.astype(np.float32), bm.astype(np.float32)]))
    np.save(f'{out}/{nm}-depth.npy', np.where(val, np.nan_to_num(Z, nan=0.0), PT).astype(np.float32))   # planar depth: refed where valid, the plan's elsewhere
    rep = dict(name=nm, cam=c, sources=exprs, valid_share=round(float(val.mean()), 3),
               by_source={s['name']: round(float((who == i).mean()), 3) for i, s in enumerate(srcs)})
    json.dump(rep, open(f'{out}/{nm}-report.json', 'w'), indent=1); print(rep)

if __name__ == '__main__':
    main(sys.argv[1])
