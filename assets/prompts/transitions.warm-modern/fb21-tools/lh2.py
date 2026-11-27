"""lh2.py (FB21 leg 2 fix): the waypoint Lh2 on the plan camera, 0 tokens.
Through the living-hall portal: the hall exactly as HT2 and HC2 show it (msr.render), bench and its four products included.
The living side (the front wall around the portal, its plaster reveal, the walnut lining of the hall half, the east wall
at the left edge) is drawn in code: no approved still sees it; plain plaster per the plan, no object.
  python3 lh2.py OUT.png"""
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/route-leg2/tools')
import msr
cg = msr.cg
CAM = cg.Cam((1.80, 4.50, 1.10), 176.0, 0.50, 0.48)
PX0, PX1, PH = 0.95, 2.15, 2.40           # the portal: X, head
YL, YM, YH = 6.20, 6.27, 6.35             # living face, plaster / walnut split of the reveal, hall face
XE = 2.50                                 # the living room's east wall

def geometry(cam, cv, ss=2):
    big = cg.Canvas(cv.w * ss, cv.h * ss, tuple(b * ss for b in cv.box))
    D = cg.rays(cam, big); C = np.array(cam.loc)
    with np.errstate(divide='ignore', invalid='ignore'):
        tw = (YL - C[1]) / D[..., 1]; te = np.where(D[..., 0] > 0, (XE - C[0]) / D[..., 0], np.inf)
        tf = np.where(D[..., 2] < 0, -C[2] / D[..., 2], np.inf)
    Pw = C + tw[..., None] * D
    lab = np.zeros(D.shape[:2], np.uint8)       # 1 wall, 2 east wall, 3 floor, 4 reveal plaster, 5 reveal walnut, 9 through
    thru = (Pw[..., 0] > PX0) & (Pw[..., 0] < PX1) & (Pw[..., 2] < PH) & (Pw[..., 2] > 0)
    lab[:] = 1; lab[te < tw] = 2; lab[(tf < tw) & (tf < te)] = 3
    th = (YH - C[1]) / D[..., 1]; Ph = C + th[..., None] * D
    inside = thru & (Ph[..., 0] > PX0) & (Ph[..., 0] < PX1) & (Ph[..., 2] < PH)
    rev = thru & ~inside
    # where on the reveal: the jamb plane hit
    xj = np.where(Ph[..., 0] <= PX0, PX0, PX1)
    with np.errstate(divide='ignore', invalid='ignore'):
        tj = (xj - C[0]) / D[..., 0]
    yj = C[1] + tj * D[..., 1]
    lab[rev & (yj < YM)] = 4; lab[rev & (yj >= YM)] = 5; lab[inside] = 9
    P = np.where((lab == 2)[..., None], C + te[..., None] * D, Pw)
    return lab, P, ss

def plaster_detail(shape, seed=7):
    """the hall's own plaster grain (hc2-frame, a plain patch), high-passed and tiled"""
    hc = msr.rgb(msr.L2 + 'hc2-frame.png').astype(np.float32)
    patch = hc[120:520, 1560:1880]                       # the hall's front wall right of the corridor portal: plain plaster
    lo = cv2.GaussianBlur(patch, (0, 0), 25); hp = patch / np.maximum(lo, 1) - 1
    hp = cv2.resize(hp, None, fx=1.0, fy=1.0)
    reps = (shape[0] // hp.shape[0] + 2, shape[1] // hp.shape[1] + 2, 1)
    t = np.tile(np.concatenate([hp, hp[:, ::-1]], 1), reps)[:shape[0], :shape[1]]
    return t.mean(-1, keepdims=True), patch.reshape(-1, 3).mean(0)

def main(out):
    cv = cg.Canvas.frame(1920)
    srcs = [msr.src_ht2(no_sconce=True), msr.src_hc2(), msr.src_hdx2(), msr.src_hc130()]
    hall, val, Z, who = msr.render(CAM, cv, srcs, keep=lambda s: msr.world_y(s) > YM)
    lab2, P2, ss = geometry(CAM, cv)
    # area-average the labels' colours at 2x, then down
    H, W = lab2.shape
    u = (np.arange(W) + 0.5) / W
    base = np.array([214, 206, 194], np.float32)                     # the living plaster in this light (warm white, below HC2's lit wall)
    zf = np.clip(P2[..., 2] / 2.4, 0, 1)
    shade = (0.90 + 0.10 * zf) * (0.93 + 0.10 * u)[None, :]            # darker at the floor and toward the east corner
    col = np.zeros((H, W, 3), np.float32)
    col[:] = base * shade[..., None]
    sk = (lab2 == 1) & (P2[..., 2] < 0.12); col[sk] = np.array([226, 220, 209]) * shade[sk][:, None]
    skl = (lab2 == 1) & (P2[..., 2] >= 0.12) & (P2[..., 2] < 0.13); col[skl] *= 0.82
    col[lab2 == 2] *= 0.97
    col[lab2 == 4] = base * 0.74
    col[lab2 == 5] = np.array([74, 50, 35], np.float32)
    col[lab2 == 3] = np.array([92, 72, 56], np.float32)
    small = cv2.resize(col, (cv.w, cv.h), interpolation=cv2.INTER_AREA)
    thru = cv2.resize((lab2 == 9).astype(np.float32), (cv.w, cv.h), interpolation=cv2.INTER_AREA)
    det, _ = plaster_detail((cv.h, cv.w))
    plain = ~(cv2.resize(((lab2 == 5) | (lab2 == 3)).astype(np.float32), (cv.w, cv.h), interpolation=cv2.INTER_AREA) > 0.01)
    small = np.where(plain[..., None], small * (1 + 0.9 * det), small)
    # the hall: the clay's bench drawn in code where it is the nearest surface (the throw and the basket stay refed);
    # the floor no still sees: the corridor's oak on the same plank columns; the ceiling: a smooth fill
    hall_f = hall.astype(np.float32)
    bcol, bcov, bT = msr.bench_layer(CAM, cv)
    Zf = np.where(np.isfinite(Z), Z, np.inf)
    bm = (bcov > 0) & ~(val & (Zf < bT - 0.02))
    hall_f = np.where(bm[..., None], bcol * bcov[..., None] + hall_f * (1 - bcov[..., None]), hall_f)
    hole = (thru > 0.01) & ~val & ~(bcov > 0.99)
    D = cg.rays(CAM, cv)
    fl = hole & (D[..., 2] < 0)
    ftex, fm = msr.floor_fill(CAM, cv, fl, 0.75)
    hall_f[fm] = ftex[fm]
    rest = hole & ~fm
    # which hall surface a hole looks at: exit of the hall box (X 0.80-3.60, Y 6.35-9.80, Z 0-3.00) seen through the portal
    C = np.array(CAM.loc)
    with np.errstate(divide='ignore', invalid='ignore'):
        tz = np.where(D[..., 2] > 0, (3.0 - C[2]) / D[..., 2], np.inf); tn = (9.8 - C[1]) / D[..., 1]
        tw = np.where(D[..., 0] < 0, (0.8 - C[0]) / D[..., 0], (3.6 - C[0]) / D[..., 0])
    Pn = C + tn[..., None] * D
    into_corr = (Pn[..., 0] > 1.7) & (Pn[..., 0] < 3.1) & (Pn[..., 2] < 2.62)
    ce = rest & (tz < np.minimum(tn, tw)) & ~(into_corr & (tn < tz))
    hall_f[ce] = np.array([196, 187, 175], np.float32)
    rest = rest & ~ce
    hall_f = msr.smooth_fill(np.clip(hall_f, 0, 255).astype(np.uint8), rest).astype(np.float32)
    a = thru[..., None]
    img = small * (1 - a) + hall_f * a
    Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(out)
    rep = dict(cam=dict(loc=list(CAM.loc), yaw=CAM.yaw, lens=24, u0=CAM.u0, v0=CAM.v0), through_px=int((thru > 0.5).sum()),
               hall_valid_px=int((val & (thru > 0.5)).sum()), hall_hole_px=int((hole & (thru > 0.5)).sum()),
               by_source={s['name']: int(((who == i) & (thru > 0.5)).sum()) for i, s in enumerate(srcs)},
               hc2_lut_residual=srcs[1]['lut_residual'])
    json.dump(rep, open(out.rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(rep)
    np.save(out.rsplit('.', 1)[0] + '-masks.npy', np.stack([thru, val.astype(np.float32), hole.astype(np.float32), who.astype(np.float32), bm.astype(np.float32)]))

if __name__ == '__main__':
    main(sys.argv[1])
