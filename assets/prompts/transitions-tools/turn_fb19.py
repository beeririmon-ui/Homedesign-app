"""turn_fb19.py (motion-agent, 2026-11-26): the walking turn HT2 -> HDx2 (fb19) in code, 0 var2 tokens.
The camera keeps walking (constant speed along a Bezier from HT2 to HDx2: leaving along -X, arriving heading about yaw 30, i.e.
already walking toward the living-room opening) while the head and body turn 90 -> 25 deg with a smootherstep (ease in and out,
never a pivot in place). Every frame = both stills carried to its camera through their depth (camgeo.dibr), weighted by
1/(distance + 0.05)^2 where each sees the point. HT2: its fb16 frame + the hall clay depth; HDx2: the fb19 frame + the hall clay
depth, and inside the opening the depth of the fb19 re-feed. Frame 1 = HT2, the last frame = HDx2 fb19, pixel for pixel.
  python3 turn_fb19.py OUT.mp4 [seconds]   (near-lossless RGB H.264, 60 fps)"""
import os, sys, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/home/user/homedesign-app/site/tools/transitions')
import camgeo as cg
REPO = '/home/user/homedesign-app'
HALL = REPO + '/assets/renders/hall/warm-modern/hall-products-2026-11-19/'
CLAY = REPO + '/assets/blockout/house/framing/wm-hall-2026-11-18/'
REFEED = os.environ.get('REFEED', 'refeed-HDx2.npz')   # made by: python3 refeed.py OUTDIR HDx2
HFB = (71.10847058823515, 169.99851470588226, 2424.891529411765, 1494.0014852941176)
FR = cg.Canvas.frame(1920, 1080)

def crop(a, box, interp):
    x0, y0, x1, y1 = box; sx, sy = (x1 - x0) / 1920, (y1 - y0) / 1080
    A = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(a, A, (1920, 1080), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

def clay_depth(name, box):
    d, v = cg.load_depth_png(CLAY + name)
    d = crop(np.where(v, d, 0).astype(np.float32), box, cv2.INTER_NEAREST)
    return d, d > 0

def stations():
    ht = np.array(Image.open(HALL + 'ht2-products-fb16-frame.png').convert('RGB')).astype(np.float32) / 255
    hx = np.array(Image.open(HALL + 'hdx2-products-fb19-frame.png').convert('RGB')).astype(np.float32) / 255
    dht, vht = clay_depth('HT-depth.png', cg.BASE_BOX)
    dhx, vhx = clay_depth('HDx-depth.png', HFB)
    z = np.load(REFEED); om = z['om']; rd = z['depth']
    dhx = np.where(om & np.isfinite(rd), rd, dhx); vhx = vhx | (om & np.isfinite(rd))
    return [dict(cam=cg.HT, img=ht, depth=dht, valid=vht), dict(cam=cg.HDX, img=hx, depth=dhx, valid=vhx)]

def path(T, fps=60):
    P0 = np.array([3.60, 8.15]); P3 = np.array([2.462, 8.15])
    P1 = P0 + 0.45 * np.array([-1.0, 0.0])
    e = np.radians(30.0); P2 = P3 - 0.35 * np.array([-np.sin(e), -np.cos(e)])
    B = lambda p: ((1 - p) ** 3)[:, None] * P0 + (3 * (1 - p) ** 2 * p)[:, None] * P1 + (3 * (1 - p) * p ** 2)[:, None] * P2 + (p ** 3)[:, None] * P3
    pp = np.linspace(0, 1, 2001); pts = B(pp); arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    n = int(round(T * fps)) + 1; t = np.linspace(0, 1, n)
    p = np.interp(t * arc[-1], arc, pp)                                       # constant walking speed along the curve
    S = t ** 3 * (t * (6 * t - 15) + 10)                                     # smootherstep: the turn eases in and out
    cams = []
    for k in range(n):
        xy = B(np.array([p[k]]))[0]
        cams.append(cg.Cam((float(xy[0]), float(xy[1]), 1.20), 90.0 - 65.0 * S[k], 0.36 + 0.11 * S[k], 0.48 + 0.02 * S[k]))
    return cams, float(arc[-1])

def render(st, cam):
    acc = np.zeros((1080, 1920, 3), np.float32); ws = np.zeros((1080, 1920), np.float32); best = None; bestw = -1
    for s in st:
        dist = float(np.linalg.norm(np.asarray(s['cam'].loc) - np.asarray(cam.loc)))
        img, valid, _ = cg.dibr(s['img'], s['depth'], s['cam'], FR, cam, FR, depth_valid=s['valid'])
        w = valid.astype(np.float32) / (dist + 0.05) ** 2
        acc += img * w[..., None]; ws += w
        if valid.mean() > bestw: bestw, best = valid.mean(), img
    hole = ws <= 0
    out = acc / np.maximum(ws, 1e-9)[..., None]; out[hole] = best[hole]
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), float(hole.mean())

if __name__ == '__main__':
    out = sys.argv[1]; T = float(sys.argv[2]) if len(sys.argv) > 2 else 1.7
    st = stations(); cams, L = path(T)
    frames, holes = [], []
    for k, c in enumerate(cams):
        if k == 0: f, h = np.clip(st[0]['img'] * 255 + 0.5, 0, 255).astype(np.uint8), 0.0
        elif k == len(cams) - 1: f, h = np.clip(st[1]['img'] * 255 + 0.5, 0, 255).astype(np.uint8), 0.0
        else: f, h = render(st, c)
        frames.append(f); holes.append(h)
    import subprocess
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '60', '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'fast', out], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    rep = dict(frames=len(frames), seconds=T, path_m=round(L, 3), yaw=[90, 25], hole_frac_max=round(max(holes), 4),
               cams=[dict(loc=[round(v, 3) for v in c.loc], yaw=round(c.yaw, 2)) for c in cams[::10]])
    json.dump(rep, open(out.rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(json.dumps({k: v for k, v in rep.items() if k != 'cams'}))
