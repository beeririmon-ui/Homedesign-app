"""walk_fb19.py (motion-agent, 2026-11-26): the FB19 arrival as ONE walk, D0 -> K-A -> 1a -> K-C -> M0-W fix1. 0 var2 tokens.
  sources  D0 (its 16:9 frame), K-A (kling), clip 1a from 2.00 m (arrival-v2, frames 147-219, 60 fps), HT2 after FB16, K-C (kling),
           M0-W fix1 (default-frame-m0w-fix1.png)
  locks    every seam is a still both pieces share: K-A's ends -> D0 / 1a@2.00 m; 1a's end -> HT2 fb16 (with the FB16 grade
           ramped in along 1a); K-C's ends -> HT2 fb16 / M0-W fix1. assemble.end_lock: flow warp + a residual that fades out.
  pace     one progress axis = the picture's own motion (median DIS flow, px); the natural speed of every piece at its own
           rate, smoothed across the seams, eased in from rest at D0 and out onto M0-W; output frames at 60 fps, each
           interpolated (DIS) at its fractional source position. Forward only, no hold, no cut.
  gait     a very subtle step: vertical bob 2.4 px at 1080 (step rate 1.9 Hz) and roll 0.12 deg (stride rate), both
           scaled by speed, 0 at both ends (the first and last frames are the stills, pixel for pixel).
  python3 walk_fb19.py KA.mp4 KC.mp4 OUTDIR"""
import os, sys, json, subprocess, numpy as np, cv2
from PIL import Image
sys.path.insert(0, '/home/user/homedesign-app/site/tools/transitions')
import assemble as AS
REPO = '/home/user/homedesign-app'
SCR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2 = REPO + '/assets/video/transitions/warm-modern/arrival-v2/arrival-v2.desktop.1920.60fps.clean.mp4'
HT2 = REPO + '/assets/renders/hall/warm-modern/hall-products-2026-11-19/ht2-products-fb16-frame.png'
M0W = REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1.png'
D0F = SCR + '/in/d0-frame.png'
FPS = 60

def rd(p): return np.array(Image.open(p).convert('RGB'))

def video(path, first=0, last=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920, 3)
    return [a[i].copy() for i in range(first, len(a) if last is None else last + 1)]

def lut_fit(src, dst, mask):
    """per-channel monotone tone curve src -> dst on the masked pixels (256-entry LUTs)"""
    L = []
    for c in range(3):
        s = src[..., c][mask].astype(int); d = dst[..., c][mask].astype(np.float64)
        sums = np.bincount(s, d, 256); cnt = np.bincount(s, None, 256)
        x = np.nonzero(cnt > 20)[0]; y = sums[x] / cnt[x]
        y = np.maximum.accumulate(y)
        L.append(np.interp(np.arange(256), x, y))
    return np.stack(L, -1)

def apply_lut(img, lut, w):
    out = np.stack([lut[..., c][img[..., c]] for c in range(3)], -1)
    return np.clip(img * (1 - w) + out * w + 0.5, 0, 255).astype(np.uint8)

def motion(frames):
    """median flow magnitude between consecutive frames, px at 1920 (computed at 480 wide)"""
    m = []
    for a, b in zip(frames[:-1], frames[1:]):
        f = AS.flow(cv2.resize(a, (480, 270), interpolation=cv2.INTER_AREA), cv2.resize(b, (480, 270), interpolation=cv2.INTER_AREA), scale=1.0)
        m.append(float(np.median(np.hypot(f[..., 0], f[..., 1]))) * 4)
    return np.array(m)

def main(ka_path, kc_path, out):
    os.makedirs(out, exist_ok=True); rep = {}
    d0, ht2, m0w = rd(D0F), rd(HT2), rd(M0W)
    KA = video(ka_path); KC = video(kc_path); A1 = video(A2, 146, 218)        # 1a: 2.00 m (frame 147) .. 3.80 m (frame 219)
    rep['frames_in'] = dict(KA=len(KA), A1=len(A1), KC=len(KC))
    # 1a: the FB16 grade ramped in from 2.0 m (0) to 3.8 m (1); its last frames locked onto HT2 fb16
    pre = A1[-1]; diff = np.abs(pre.astype(int) - ht2.astype(int)).max(-1)
    lut = lut_fit(pre, ht2, cv2.erode((diff < 40).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)
    n1 = len(A1)
    for i in range(n1):
        s = i / (n1 - 1); w = s * s * (3 - 2 * s); A1[i] = apply_lut(A1[i], lut, w)
    rep['lock_1a'] = AS.end_lock(A1, None, ht2, n=24)
    rep['lock_KA'] = AS.end_lock(KA, d0, A1[0], n=10)
    rep['lock_KC'] = AS.end_lock(KC, ht2, m0w, n=12)
    # one source axis (shared seam frames once) with its native rate
    src = KA + A1[1:] + KC[1:]
    rate = np.array([24.0] * (len(KA) - 1) + [60.0] * (len(A1) - 1) + [24.0] * (len(KC) - 1))
    seg = ['K-A'] * (len(KA) - 1) + ['1a'] * (len(A1) - 1) + ['K-C'] * (len(KC) - 1)
    mag = motion(src); mag = np.maximum(mag, 0.05)
    C = np.concatenate([[0], np.cumsum(mag)])                                 # progress at each source frame (px)
    vnat = mag * rate                                                       # px per second at the native timing
    # smooth the natural speed over the progress axis (0.5 s wide), then ease in / out
    tn = np.concatenate([[0], np.cumsum(1 / rate)])
    tg = np.arange(0, tn[-1], 1 / 240); vg = np.interp(tg, tn[:-1], vnat)
    sig = 0.25 * 240; k = np.exp(-0.5 * (np.arange(-3 * sig, 3 * sig + 1) / sig) ** 2); k /= k.sum()
    vs = np.convolve(np.pad(vg, (len(k) // 2, len(k) // 2), mode='edge'), k, 'valid')
    Cg = np.interp(tg, tn, C)
    # scrubbing wants an even flow of picture: kling's own slow start and long landing crawl are lifted, the fast jamb
    # pass and 1a's 1.5 m/s are slowed (0.5x .. 1.6x of the median picture speed); the real ease is the one below
    med = float(np.median(vs)); vs = np.clip(vs, 0.5 * med, 1.6 * med); rep['picture_speed_px_s'] = dict(median=round(med), lo=round(0.5 * med), hi=round(1.6 * med))
    # integrate output time: dC/dt = vs(C) * ease
    T_in, T_out = 0.5, 0.7
    t, c, Cs = 0.0, 0.0, [0.0]
    while c < C[-1] - 1e-6:
        v = np.interp(c, Cg, vs)
        e_in = min(1.0, 0.15 + 0.85 * t / T_in) if t < T_in else 1.0
        rem = C[-1] - c; v_end = np.interp(c, Cg, vs)
        e_out = min(1.0, np.sqrt(max(rem, 0) / (v_end * T_out / 2 + 1e-6)))      # constant deceleration onto the last frame
        c = min(C[-1], c + v * e_in * max(e_out, 0.04) / FPS); t += 1 / FPS; Cs.append(c)
        if len(Cs) > 4000: break
    Cs = np.array(Cs); Cs[-1] = C[-1]
    pos = np.interp(Cs, C, np.arange(len(C)))                               # fractional source index per output frame
    rep['out_frames'] = len(pos); rep['play_s'] = round((len(pos) - 1) / FPS, 3)
    # gait
    n = len(pos); tt = np.arange(n) / FPS
    sp = np.gradient(Cs) * FPS; spn = np.clip(sp / np.median(sp[sp > 0]), 0, 1.2)
    env = np.minimum(1, np.minimum(tt / 0.6, (tt[-1] - tt) / 0.6)).clip(0, 1); env = env * env * (3 - 2 * env)
    phase = np.cumsum(spn) / FPS * 1.9 * 2 * np.pi
    bob = 2.4 * 1920 / 1080 / 1.7778 * np.cos(phase) * spn * env          # px at 1920x1080 (2.4 px at 1080 tall)
    roll = 0.12 * np.sin(phase / 2) * spn * env
    scl = 1 + 0.004 * env
    rep['gait'] = dict(bob_px_max=round(float(np.abs(bob).max()), 2), roll_deg_max=round(float(np.abs(roll).max()), 3), overscan=0.004)
    np.savez_compressed(out + '/timeline.npz', pos=pos, Cs=Cs, C=C, rate=rate, mag=mag, bob=bob, roll=roll, scl=scl)
    rep['seg_of_output'] = {}
    flows = {}
    def F(i):
        if i not in flows:
            flows.clear(); flows[i] = (AS.flow(src[i], src[i + 1]), AS.flow(src[i + 1], src[i]))
        return flows[i]
    frames = []
    for j, p in enumerate(pos):
        i = int(np.floor(p)); tau = float(p - i)
        if i >= len(src) - 1: im = src[-1]
        elif tau < 1e-3: im = src[i]
        else:
            f01, f10 = F(i); im = AS.interpolate(src[i], src[i + 1], tau, f01, f10)
        if 0 < j < n - 1 and env[j] > 0:
            M = cv2.getRotationMatrix2D((960, 540), roll[j], scl[j]); M[1, 2] += bob[j]
            im = cv2.warpAffine(im, M, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        frames.append(im)
        s_ = seg[min(i, len(seg) - 1)]; rep['seg_of_output'].setdefault(s_, [j + 1, j + 1])[1] = j + 1
    frames[0] = d0.copy(); frames[-1] = m0w.copy()
    rep['first_vs_D0_max'] = int(np.abs(frames[0].astype(int) - d0.astype(int)).max())
    rep['last_vs_M0W_max'] = int(np.abs(frames[-1].astype(int) - m0w.astype(int)).max())
    json.dump(rep, open(out + '/walk.json', 'w'), indent=1)
    return frames, rep
    print(json.dumps({k: v for k, v in rep.items() if k not in ('lock_1a', 'lock_KA', 'lock_KC')}))
    print('locks', {k: rep[k] for k in ('lock_1a', 'lock_KA', 'lock_KC')})

# ---------------------------------------------------------------------------------------------------------------- export
_FR = None
def _enc(job):
    i, w, h, src, aq, wq, base = job
    im = Image.fromarray(src if (w, h) == (1920, 1080) else cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA))
    pa = '%s/%d/%04d.avif' % (base, w, i); pw = '%s/%d/%04d.webp' % (base, w, i)
    im.save(pa, 'AVIF', quality=aq, speed=6); im.save(pw, 'WEBP', quality=wq, method=5)
    return os.path.getsize(pa), os.path.getsize(pw)

def export(frames, rep, base, preview, master):
    import multiprocessing as mp
    os.makedirs(base + '/1920', exist_ok=True); os.makedirs(base + '/1080', exist_ok=True)
    n = len(frames)
    jobs = [(i + 1, 1920, 1080, frames[i], 55 if i < n - 8 else 85, 72 if i < n - 8 else 92, base) for i in range(n)]   # the landing frames finer
    f30 = []                                                                   # 30 fps: (0.25, 0.5, 0.25) around every 2nd frame
    for j in range(0, n, 2):
        if j == 0 or j >= n - 1: f30.append(frames[min(j, n - 1)])
        else: f30.append(np.clip(0.25 * frames[j - 1].astype(np.float32) + 0.5 * frames[j] + 0.25 * frames[j + 1] + 0.5, 0, 255).astype(np.uint8))
    if (n - 1) % 2: f30.append(frames[-1])
    f30[-1] = frames[-1]
    jobs += [(i + 1, 1080, 608, f30[i], 50 if i < len(f30) - 4 else 85, 60 if i < len(f30) - 4 else 92, base) for i in range(len(f30))]
    with mp.get_context('fork').Pool(4) as pool:
        sizes = pool.map(_enc, jobs, chunksize=4)
    b1920 = np.array(sizes[:n]); b1080 = np.array(sizes[n:])
    for path, sc, crf in ((master, None, 14), (preview, '1280:720', 18)):
        vf = ['-vf', 'scale=%s:flags=lanczos' % sc] if sc else []
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(FPS), '-i', '-'] + vf +
                             ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path], stdin=subprocess.PIPE)
        for f in frames: p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait()
    return dict(n1920=n, n1080=len(f30), bytes={'1920': dict(avif=int(b1920[:, 0].sum()), webp=int(b1920[:, 1].sum())),
                                                 '1080': dict(avif=int(b1080[:, 0].sum()), webp=int(b1080[:, 1].sum()))})

if __name__ == '__main__':
    ka, kc, out, base, preview, master = sys.argv[1:7]
    frames, rep = main(ka, kc, out)
    ex = export(frames, rep, base, preview, master)
    rep['export'] = ex; json.dump(rep, open(out + '/walk.json', 'w'), indent=1); print(json.dumps(ex))
