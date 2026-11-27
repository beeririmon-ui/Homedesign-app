"""plan_seed.py (FB21): a waypoint still's seed ray-cast in the house plan (0 tokens): rooms as boxes, openings as holes, each
surface a flat tone sampled from the room's own display frame, the walnut linings as walnut. seedream finishes it.
  python3 plan_seed.py X Y Z YAW LENS U0 V0 OUT.png"""
import sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/clip-te0w/tools')
import geo
R = '/home/user/homedesign-app/assets/renders/'
ROOMS = {  # x, y, h, wall tone, floor tone (RGB)
 'living': ((-2.3, 2.5), (0.0, 6.2), 3.0), 'dining': ((2.65, 7.25), (0.0, 6.2), 3.0), 'hall': ((0.8, 3.6), (6.35, 9.8), 3.0),
 'corridor': ((1.7, 3.1), (9.8, 17.51), 2.7), 'bath': ((3.25, 6.25), (9.95, 13.59), 2.7), 'boy': ((-2.3, 1.55), (10.25, 13.73), 3.0),
 'girl': ((-2.3, 1.55), (13.88, 17.36), 3.0)}
OPEN = [  # (axis, plane, (lo, hi) along the other axis, top z, rooms joined, lining)
 ('x', 2.575, (2.97, 4.57), 2.4, ('living', 'dining'), 'plaster'), ('y', 6.275, (0.95, 2.15), 2.4, ('living', 'hall'), 'walnut'),
 ('y', 9.8, (1.7, 3.1), 2.62, ('hall', 'corridor'), 'walnut'), ('x', 3.175, (12.39, 13.39), 2.4, ('corridor', 'bath'), 'walnut'),
 ('x', 1.625, (12.63, 13.53), 2.4, ('corridor', 'boy'), 'walnut'), ('x', 1.625, (16.26, 17.16), 2.4, ('corridor', 'girl'), 'walnut')]
TONE = {'plaster': (226, 220, 210), 'floor': (92, 74, 58), 'ceiling': (232, 228, 220), 'walnut': (78, 52, 36), 'stone': (214, 200, 176)}

def cast(C, D):
    """march through boxes: start in the room holding C; at each exit, pass through an opening if the hit is inside it"""
    H, W = D.shape[:2]; out = np.zeros((H, W, 3), np.float32); done = np.zeros((H, W), bool)
    def room_of(P):
        for k, (xr, yr, h) in ROOMS.items():
            if xr[0] - 0.2 <= P[0] <= xr[1] + 0.2 and yr[0] - 0.2 <= P[1] <= yr[1] + 0.2: return k
    cur = np.full((H, W), room_of(C), object); org = np.broadcast_to(C, D.shape).copy(); tsum = np.zeros((H, W))
    for it in range(6):
        for k, (xr, yr, h) in ROOMS.items():
            m = (cur == k) & ~done
            if not m.any(): continue
            o, d = org[m], D[m]
            lo = np.array([xr[0], yr[0], 0.0]); hi = np.array([xr[1], yr[1], h])
            with np.errstate(divide='ignore', invalid='ignore'):
                t1 = (lo - o) / d; t2 = (hi - o) / d
            tmax = np.nanmin(np.maximum(t1, t2), -1); P = o + tmax[:, None] * d
            col = np.zeros((len(P), 3), np.float32); nxt = np.full(len(P), None, object)
            fl = np.abs(P[:, 2]) < 1e-4; ce = np.abs(P[:, 2] - h) < 1e-4
            col[:] = TONE['plaster']; col[fl] = TONE['floor']; col[ce] = TONE['ceiling']
            for ax, pl, (a0, a1), top, (r1, r2), lin in OPEN:
                if k not in (r1, r2): continue
                other = r2 if k == r1 else r1
                if ax == 'x': on = (np.abs(P[:, 0] - (xr[0] if abs(pl - xr[0]) < 0.2 else xr[1])) < 1e-3) & (np.abs(pl - P[:, 0]) < 0.2) & (P[:, 1] > a0) & (P[:, 1] < a1) & (P[:, 2] < top)
                else: on = (np.abs(P[:, 1] - (yr[0] if abs(pl - yr[0]) < 0.2 else yr[1])) < 1e-3) & (np.abs(pl - P[:, 1]) < 0.2) & (P[:, 0] > a0) & (P[:, 0] < a1) & (P[:, 2] < top)
                # the lining: a thin band just inside the opening's edges
                if ax == 'x': edge = on & ((P[:, 1] - a0 < 0.06) | (a1 - P[:, 1] < 0.06) | (top - P[:, 2] < 0.06))
                else: edge = on & ((P[:, 0] - a0 < 0.06) | (a1 - P[:, 0] < 0.06) | (top - P[:, 2] < 0.06))
                col[edge] = TONE[lin]; nxt[on & ~edge] = other
            shade = np.clip(1.08 - 0.035 * (tsum[m] + tmax), 0.7, 1.05)[:, None]
            idx = np.nonzero(m)
            go = np.array([n is not None for n in nxt])
            fin = ~go
            out[idx[0][fin], idx[1][fin]] = col[fin] * shade[fin]; done[idx[0][fin], idx[1][fin]] = True
            org[idx[0][go], idx[1][go]] = P[go] + d[go] * 0.16; tsum[idx[0][go], idx[1][go]] += tmax[go]
            cur[idx[0][go], idx[1][go]] = nxt[go]
    out[~done] = TONE['plaster']
    return out

if __name__ == '__main__':
    x, y, z, yaw, lens, u0, v0 = map(float, sys.argv[1:8]); outp = sys.argv[8]
    cam = geo.Cam((x, y, z), yaw, lens, u0, v0)
    yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64); D = cam.rays(np.stack([xx, yy], -1))
    img = cast(cam.C, D)
    Image.fromarray(np.clip(cv2.GaussianBlur(img, (0, 0), 0.7), 0, 255).astype(np.uint8)).save(outp)
    json.dump(dict(cam=dict(loc=[x, y, z], yaw=yaw, lens=lens, u0=u0, v0=v0)), open(outp.rsplit('.', 1)[0] + '.json', 'w'))
    print('ok', outp)
