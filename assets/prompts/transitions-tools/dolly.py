"""dolly.py (FB21, the saving lever): a straight walk in code between two stills of one space, 0 tokens.
Every frame is rendered from BOTH ends with their planar depth (camgeo.dibr): the start still A (a waypoint: its
still.py depth, refed where valid and the plan's elsewhere) and the end still B (an approved still with its clay depth);
where both see a surface they are blended by progress (smoothstep), else the one that sees it; pin-holes inpainted.
The camera moves on a straight line, yaw and height interpolated; the leg assembler then paces it as a walk and adds
the gait. Written at 24 fps so it chains with the kling clips.
  python3 dolly.py CONFIG.json
CONFIG: {"A": {"img", "depth_npy", "cam": {...}}, "B": {"src": "CK"} | {"img", "depth_npy", "cam"}, "metres_per_s": 1.1, "out": "x.mp4"}"""
import sys, os, json, subprocess, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msr
cg = msr.cg

def load(e):
    if 'src' in e:
        s = msr.src_corr(e['src']) if e['src'] in ('CK', 'CM') else msr.src_room(e['src'])
        return s
    c = e['cam']; d = np.load(e['depth_npy'])
    return dict(name='A', img=msr.rgb(e['img']), depth=d, ok=np.isfinite(d) & (d > 0.05), cam=msr.LCam(c['loc'], c['yaw'], c['u0'], c['v0'], c.get('lens', 24.0)),
                cv=cg.Canvas.frame(1920))

def main(cfgp):
    C = json.load(open(cfgp)); A = load(C['A']); B = load(C['B'])
    if C.get('door_zones'):     # A's pixels near door reveals: its depth there is the plan's flat wall, not the reveal: B only
        u, v = A['cv'].uv(); P = A['cam'].unproject(u, v, np.where(A['ok'], A['depth'], 1.0)); bad = np.zeros(A['depth'].shape, bool)
        for zx, zy in C['door_zones']:
            bad |= (P[..., 0] > zx[0]) & (P[..., 0] < zx[1]) & (P[..., 1] > zy[0]) & (P[..., 1] < zy[1])
        A['unreliable'] = cv2.dilate(bad.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    a, b = A['cam'], B['cam']; L = float(np.linalg.norm(np.subtract(b.loc, a.loc)))
    n = max(2, int(round(L / C.get('metres_per_s', 1.1) * 24)) + 1); cv = cg.Canvas.frame(1920)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '24', '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'medium', C['out']], stdin=subprocess.PIPE)
    holes = []
    for i in range(n):
        t = i / (n - 1); w = t * t * (3 - 2 * t)
        loc = tuple(np.add(a.loc, np.multiply(np.subtract(b.loc, a.loc), t))); dyaw = ((b.yaw - a.yaw + 180) % 360) - 180
        cam = msr.LCam(loc, a.yaw + dyaw * t, a.u0 + (b.u0 - a.u0) * t, a.v0 + (b.v0 - a.v0) * t, a.lens)
        if i == 0: im = A['img'] if A['img'].shape[1] == 1920 else A['cv'].crop_frame(A['img'], 1920, 1080)
        elif i == n - 1: im = B['img'] if B['img'].shape[1] == 1920 else B['cv'].crop_frame(B['img'], 1920, 1080)
        else:
            oa, va, za = cg.dibr(A['img'], A['depth'], a, A['cv'], cam, cv, depth_valid=A['ok'] & ~A.get('unreliable', False))
            ob, vb, zb = cg.dibr(B['img'], B['depth'], b, B['cv'], cam, cv, depth_valid=B['ok'])
            za = np.where(va, za, np.inf); zb = np.where(vb, zb, np.inf); Z = np.minimum(za, zb)
            ta = va & (za <= Z * 1.04 + 0.02); tb = vb & (zb <= Z * 1.04 + 0.02)
            wB = min(1.0, t / C.get('blend_until', 0.25)); wB = wB * wB * (3 - 2 * wB)     # B (the approved still) takes over early
            wa = np.where(ta & tb, 1 - wB, np.where(ta, 1.0, 0.0)); wb = np.where(ta & tb, wB, np.where(tb, 1.0, 0.0))
            im = oa.astype(np.float32) * wa[..., None] + ob.astype(np.float32) * wb[..., None]
            hole = ~(ta | tb); holes.append(float(hole.mean()))
            im = np.clip(im + 0.5, 0, 255).astype(np.uint8)
            if hole.any(): im = cv2.inpaint(im, hole.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
        p.stdin.write(np.ascontiguousarray(im).tobytes())
    p.stdin.close(); p.wait()
    rep = dict(frames=n, metres=round(L, 3), hole_share_max=round(max(holes or [0]), 4), hole_share_mean=round(float(np.mean(holes or [0])), 4))
    json.dump(rep, open(C['out'].rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(rep)

if __name__ == '__main__':
    main(sys.argv[1])
