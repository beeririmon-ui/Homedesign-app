"""pan.py (FB21): a head turn in code from stills taken at ONE centre (exact: a pure rotation), 0 tokens.
Each frame is the stills re-projected by rotation and feathered together where they overlap (cosine weight to each
still's frame edge). Written at 24 fps; the leg assembler paces it as a turn ("code") and adds the gait.
  python3 pan.py CONFIG.json
CONFIG: {"stills": [{"img": png, "cam": {"loc","yaw","u0","v0","lens"}}, ...] (in turn order), "deg_per_s": 60, "out": "x.mp4"}"""
import sys, os, json, subprocess, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msr
cg = msr.cg

def main(cfgp):
    C = json.load(open(cfgp)); cv = cg.Canvas.frame(1920)
    S = []
    for s in C['stills']:
        c = s['cam']; img = msr.rgb(s['img'])
        scv = cg.Canvas.frame(img.shape[1], img.shape[0]) if img.shape[1] == 1920 else cg.Canvas.base(img.shape[1])
        S.append(dict(img=img.astype(np.float32), cam=msr.LCam(c['loc'], c['yaw'], c['u0'], c['v0'], c.get('lens', 24.0)), cv=scv))
    a, b = S[0]['cam'], S[-1]['cam']; d = ((b.yaw - a.yaw + 180) % 360) - 180
    n = max(2, int(round(abs(d) / C.get('deg_per_s', 60) * 24)) + 1)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '24', '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'medium', C['out']], stdin=subprocess.PIPE)
    gaps = []
    for i in range(n):
        t = i / (n - 1); e = t * t * (3 - 2 * t)
        cam = msr.LCam(a.loc, a.yaw + d * e, a.u0 + (b.u0 - a.u0) * e, a.v0 + (b.v0 - a.v0) * e, a.lens)
        D = cam.rays(cv); acc = np.zeros((1080, 1920, 3), np.float32); wsum = np.zeros((1080, 1920), np.float32)
        for s in S:
            P = np.asarray(s['cam'].loc) + D            # a point on each ray (same centre: any depth projects the same)
            u, v, dd = s['cam'].project(P); mx, my = s['cv'].px(u, v)
            inside = (dd > 0) & (u > 0) & (u < 1) & (v > 0) & (v < 1)
            fe = np.clip(np.minimum.reduce([u, 1 - u, v, 1 - v]) / 0.04, 0, 1); w = np.where(inside, 0.5 - 0.5 * np.cos(np.pi * fe), 0)
            im = cv2.remap(s['img'], mx.astype(np.float32), my.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            acc += im * w[..., None]; wsum += w
        gaps.append(float((wsum < 1e-3).mean()))
        out = acc / np.maximum(wsum, 1e-6)[..., None]
        hole = wsum < 1e-3                                  # the top/bottom slivers no still covers mid-turn (rectilinear edges)
        if hole.any():
            out = cv2.inpaint(np.clip(out + 0.5, 0, 255).astype(np.uint8), cv2.dilate(hole.astype(np.uint8), np.ones((5, 5), np.uint8)) * 255, 7, cv2.INPAINT_TELEA).astype(np.float32)
        if i == 0: out = S[0]['img'] if S[0]['img'].shape[1] == 1920 else S[0]['cv'].crop_frame(S[0]['img'], 1920, 1080)
        if i == n - 1: out = S[-1]['img'] if S[-1]['img'].shape[1] == 1920 else S[-1]['cv'].crop_frame(S[-1]['img'], 1920, 1080)
        p.stdin.write(np.clip(out + 0.5, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    rep = dict(frames=n, degrees=round(d, 2), uncovered_max=round(max(gaps), 4)); json.dump(rep, open(C['out'].rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(rep)

if __name__ == '__main__':
    main(sys.argv[1])
