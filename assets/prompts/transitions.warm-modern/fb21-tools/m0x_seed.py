"""m0x_seed.py (motion-agent, FB21 leg 1, 2026-11-26): the seed of the M0x-W still, 0 tokens.
M0x-W = M0-W's point (0.95, 5.55, 1.05), 35 mm, turned to yaw -35 toward the kitchen opening (O-living-dining, X 2.50, Y 2.97-4.57).
  exact    what M0-W sees (its right-hand strip here): default-frame-m0w-fix1-pecan.png turned about the lens (no parallax)
  guide    the rest, ray-cast in the plan: the living room's right wall in M0-W's plaster, its floor and ceiling, and through the
           opening the dining room = D1 (fb16) carried through the dining room's box (walls and floor), for seedream to finish
  python3 m0x_seed.py OUTDIR"""
import sys, json, numpy as np, cv2
from PIL import Image
import geo
R = '/home/user/homedesign-app/assets/renders/'
M0W = R + 'living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1-pecan.png'
D1F = R + 'dining/warm-modern/stage1-2026-11-20/D1-defaults-fb16-frame.png'
V0 = 0.553
CW = geo.Cam((0.95, 5.55, 1.05), 14.0, 35.0, 0.5, V0)
CX = geo.Cam((0.95, 5.55, 1.05), -35.0, 35.0, 0.5, V0)
CD = geo.Cam((2.80, 3.80, 1.10), -56.0, 24.0, 0.52, 0.43)
LIV = dict(x=(-2.3, 2.5), y=(0.0, 6.2), z=(0.0, 3.0)); DIN = dict(x=(2.65, 7.25), y=(0.0, 6.2), z=(0.0, 3.0))
OPEN = dict(y=(2.97, 4.57), z=(0.0, 2.40))

def box_exit(C, D, b):
    lo = np.array([b['x'][0], b['y'][0], b['z'][0]]); hi = np.array([b['x'][1], b['y'][1], b['z'][1]])
    with np.errstate(divide='ignore', invalid='ignore'):
        t1 = (lo - C) / D; t2 = (hi - C) / D
    return np.nanmin(np.maximum(t1, t2), -1)

def main(out):
    yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64); px = np.stack([xx, yy], -1)
    D = CX.rays(px); C = CX.C
    W = np.array(Image.open(M0W).convert('RGB')).astype(np.float32); DF = np.array(Image.open(D1F).convert('RGB')).astype(np.float32)
    # exact: the same rays in M0-W
    q, d = CW.project(C + D); mx, my = q[..., 0].astype(np.float32), q[..., 1].astype(np.float32)
    exact = (d > 0) & (mx >= 0) & (mx <= 1919) & (my >= 0) & (my <= 1079)
    rot = cv2.remap(W, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # guide: the living room box; where the ray leaves through the right wall inside the opening, the dining room
    t = box_exit(C, D, LIV); P = C + t[..., None] * D
    right = np.abs(P[..., 0] - 2.5) < 1e-3
    through = right & (P[..., 1] > OPEN['y'][0]) & (P[..., 1] < OPEN['y'][1]) & (P[..., 2] < OPEN['z'][1])
    floor = np.abs(P[..., 2]) < 1e-3; ceil = np.abs(P[..., 2] - 3.0) < 1e-3
    plaster = np.median(W[300:500, 1500:1800].reshape(-1, 3), 0); oak = np.median(W[1000:1075, 1300:1500].reshape(-1, 3), 0)
    ceiling = np.median(W[0:30, 700:1200].reshape(-1, 3), 0)
    g = np.empty_like(W); g[:] = plaster
    g[floor] = oak; g[ceil] = ceiling
    shade = np.clip(1.15 - 0.06 * t, 0.75, 1.1)[..., None]; g = g * shade
    t2 = box_exit(C, D, DIN); P2 = C + t2[..., None] * D
    q2, d2 = CD.project(P2); m2x, m2y = q2[..., 0].astype(np.float32), q2[..., 1].astype(np.float32)
    inD = through & (d2 > 0) & (m2x >= 0) & (m2x <= 1919) & (m2y >= 0) & (m2y <= 1079)
    din = cv2.remap(DF, m2x, m2y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    g = np.where(inD[..., None], din, np.where(through[..., None], plaster * 0.95, g))
    # reveal of the opening (15 cm deep, plaster): a thin darker edge
    edge = cv2.morphologyEx(through.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((7, 7), np.uint8)) > 0
    g[edge] = g[edge] * 0.8
    seed = np.where(exact[..., None], rot, g)
    Image.fromarray(np.clip(seed, 0, 255).astype(np.uint8)).save(out + '/m0x-seed.png')
    Image.fromarray(exact.astype(np.uint8) * 255).save(out + '/m0x-exact-mask.png')
    np.save(out + '/m0x-rot.npy', np.clip(rot, 0, 255).astype(np.uint8))
    xs = np.nonzero(exact.any(0))[0]
    rep = dict(cam=dict(loc=[0.95, 5.55, 1.05], yaw=-35.0, lens=35, u0=0.5, v0=V0), exact_px=int(exact.sum()), exact_cols=[int(xs.min()), int(xs.max())],
               through_px=int(through.sum()), dining_from_D1_px=int(inD.sum()))
    json.dump(rep, open(out + '/m0x-seed.json', 'w'), indent=1); print(rep)

if __name__ == '__main__':
    main(sys.argv[1])
