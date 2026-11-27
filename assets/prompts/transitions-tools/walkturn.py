"""walkturn.py (FB21 leg 3 fix, motion-agent, 2026-11-27): a kling walk that hands over to an exact code turn while it is
still walking, so there is no walk -> stop -> pan back (leg 3, K3d: kling drifted left onto a blank wall for 1.5 s and the
code pan then turned back right to MB0). 0 tokens.
  * The kling clip is locked at its end onto its last still (the turn's first still, at the landing still's centre), as the
    leg assembler would, so its late frames converge onto the centre's view.
  * kling's yaw as seen from that centre is fitted per frame (the centre view with the least median DIS flow on textured
    pixels), linearly over `fit`, and pinned to the last still's yaw at the clip's end.
  * The walk is cut at `cut` (kept as is, 'kling' pace). From there the output yaw follows one smooth plan to `yaw_to`: it
    carries on at kling's own apparent rate, eases into the turn and decelerates onto the landing still.
  * Over the first `blend` turn frames the rest of the walk (kling frames cut .. end, played faster) is turned about its own
    lens to the output yaw (a rotation needs no depth: exact for what kling drew) and fades into the centre's view at the
    same yaw (the stills at one centre, re-projected and feathered as in pan.py). Because the locked kling frames converge
    onto that view, the two layers converge as the blend goes; no flow warp, so nothing bends. Where the turned kling frame
    has no pixels (its right edge, top and bottom wedges) the centre view shows, feathered.
  * Then the pure centre turn runs on; its last frame is the landing still, pixel for pixel.
  python3 walkturn.py CONFIG.json
CONFIG: {"clip", "cut", "fit": [t0, t1], "cand": [y0, y1], "blend", "frames" (turn frames after the cut), "ease_in",
         "yaw_to", "stills": [{"img", "cam"}, ...] (one centre, the last is the landing), "lock_last": png (kling's own last
         still), "out_walk", "out_turn", "out_split"}"""
import sys, os, json, subprocess, numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msr, walk_fb19 as W
cg = msr.cg
AS = W.AS


class Centre:
    """the view from the stills' common centre at any yaw (pan.py's re-projection and cosine feather)"""
    def __init__(s, stills, w=1920):
        s.w, s.h = w, int(round(w * 9 / 16)); s.cv = cg.Canvas.frame(w); s.S = []
        for st in stills:
            c = st['cam']; img = msr.rgb(st['img']).astype(np.float32)
            if img.shape[1] != w: img = cv2.resize(img, (w, s.h), interpolation=cv2.INTER_AREA)
            s.S.append(dict(img=img, cam=msr.LCam(c['loc'], c['yaw'], c['u0'], c['v0'], c.get('lens', 24.0))))
        s.loc = s.S[-1]['cam'].loc; s.u0, s.v0 = s.S[-1]['cam'].u0, s.S[-1]['cam'].v0

    def cam(s, yaw):
        return msr.LCam(s.loc, yaw, s.u0, s.v0, 24.0)

    def view(s, yaw, inpaint=True):
        D = s.cam(yaw).rays(s.cv); acc = np.zeros((s.h, s.w, 3), np.float32); ws = np.zeros((s.h, s.w), np.float32)
        for st in s.S:
            u, v, dd = st['cam'].project(np.asarray(st['cam'].loc) + D); mx, my = s.cv.px(u, v)
            inside = (dd > 0) & (u > 0.002) & (u < 0.998) & (v > 0.002) & (v < 0.998)
            fe = np.clip(np.minimum.reduce([u, 1 - u, v, 1 - v]) / 0.04, 0, 1); w = np.where(inside, 0.5 - 0.5 * np.cos(np.pi * fe), 0)
            im = cv2.remap(st['img'], mx.astype(np.float32), my.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            acc += im * w[..., None]; ws += w
        out = acc / np.maximum(ws, 1e-6)[..., None]; hole = ws < 1e-3
        if inpaint and hole.any():
            out = cv2.inpaint(np.clip(out + 0.5, 0, 255).astype(np.uint8), cv2.dilate(hole.astype(np.uint8), np.ones((5, 5), np.uint8)) * 255,
                              7, cv2.INPAINT_TELEA).astype(np.float32)
        return out, hole

    def small(s, w=480):
        o = Centre.__new__(Centre); o.__dict__.update(s.__dict__); o.w, o.h, o.cv = w, int(round(w * 9 / 16)), cg.Canvas.frame(w)
        o.S = [dict(st, img=cv2.resize(st['img'], (w, o.h), interpolation=cv2.INTER_AREA)) for st in s.S]; return o


def turn(img, cam_from, cam_to, cv):
    """img seen by cam_from, re-seen by cam_to at the same centre (exact): (float image, valid mask)"""
    D = cam_to.rays(cv); u, v, dd = cam_from.project(np.asarray(cam_from.loc) + D); mx, my = cv.px(u, v)
    ok = (dd > 0) & (mx >= 0) & (mx <= cv.w - 1) & (my >= 0) & (my <= cv.h - 1)
    out = cv2.remap(img.astype(np.float32), mx.astype(np.float32), my.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return out, ok


def fit_yaw(K, C, t0, t1, cand):
    sm = C.small(480); V = {y: sm.view(y) for y in np.arange(cand[0], cand[1] + 0.25, 0.5)}; pts = []
    for t in range(t0, t1 + 1, 2):
        k = cv2.resize(K[t], (sm.w, sm.h), interpolation=cv2.INTER_AREA); best = None
        for y, (v, h) in V.items():
            v8 = np.clip(v + 0.5, 0, 255).astype(np.uint8); g = cv2.cvtColor(v8, cv2.COLOR_RGB2GRAY).astype(np.float32)
            m = (np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) > 30) & ~h
            f = AS.flow(v8, k, 1.0) * (1920 / sm.w); sc = float(np.median(np.hypot(f[..., 0], f[..., 1])[m]))
            if best is None or sc < best[0]: best = (sc, float(y))
        pts.append((t, best[1], best[0]))
    p = np.array(pts); a, b = np.polyfit(p[:, 0], p[:, 1], 1)
    return a, b, [[int(t), y, round(r, 1)] for t, y, r in pts]


def yaw_plan(y0, r0, y1, N, ei):
    """N + 1 yaws: start at y0 moving at r0 per frame (kling's own apparent rate), ease into the turn over the first `ei`
    share, decelerate onto y1"""
    s = np.linspace(0, 1, N + 1)
    v = np.where(s < ei, 0.5 - 0.5 * np.cos(np.pi * s / ei), 0.5 + 0.5 * np.cos(np.pi * (s - ei) / (1 - ei)))
    base = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2)])
    lead = r0 * np.concatenate([[0], np.cumsum(np.clip(1 - s[1:] / ei, 0, 1) ** 2)])
    return y0 + lead + (y1 - y0 - lead[-1]) / base[-1] * base


def enc(frames, path, fps=24):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'medium', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(np.clip(np.asarray(f, np.float32) + 0.5, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()


def build(cfg):
    T, N, DB = cfg['cut'], cfg['frames'], cfg['blend']
    Kraw = W.video(cfg['clip']); K = [k.copy() for k in Kraw]; E = len(K) - 1
    C = Centre(cfg['stills']); cv = C.cv
    a, b, pts = fit_yaw(Kraw, C, cfg['fit'][0], cfg['fit'][1], cfg.get('cand', [36, 66]))
    last = W.rd(cfg['lock_last']); AS.end_lock(K, None, last, n=12)
    y_last = cfg['lock_last_yaw']; pin0 = E - 12
    yk = lambda t: a * t + b + (y_last - (a * E + b)) * float(np.clip((t - pin0) / 12, 0, 1))
    Y = yaw_plan(yk(T), yk(T + 1) - yk(T), cfg.get('yaw_to', 0.0), N, cfg.get('ease_in', 0.3))
    cache = {}
    def kat(p):
        i = int(np.floor(p)); tau = p - i
        if tau < 1e-3 or i >= E: return K[min(i, E)]
        if i not in cache: cache.clear(); cache[i] = (AS.flow(K[i], K[i + 1]), AS.flow(K[i + 1], K[i]))
        return AS.interpolate(K[i], K[i + 1], tau, *cache[i])
    frames = [Kraw[T].astype(np.float32)]
    for j in range(1, N + 1):
        if j == N: frames.append(C.S[-1]['img']); break
        B, _ = C.view(Y[j])
        if j < DB:
            s = j / DB; t = T + (E - T) * s
            A, ok = turn(kat(t), C.cam(yk(t)), C.cam(Y[j]), cv)
            w = s * s * (3 - 2 * s)
            okf = cv2.GaussianBlur(cv2.erode(ok.astype(np.float32), np.ones((5, 5), np.uint8)), (0, 0), 25)
            wa = ((1 - w) * okf)[..., None]; frames.append(A * wa + B * (1 - wa))
        else:
            frames.append(B)
    rep = dict(cut=T, blend=DB, frames=N, ease_in=cfg.get('ease_in', 0.3), kling_yaw_fit=dict(slope=round(float(a), 4), at_cut=round(float(yk(T)), 2),
               points=pts), yaw=[round(float(y), 2) for y in Y])
    return Kraw, frames, rep


if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1])); Kraw, frames, rep = build(cfg); T = cfg['cut']
    Image.fromarray(Kraw[T]).save(cfg['out_split'])
    enc(Kraw[:T + 1], cfg['out_walk']); enc(frames, cfg['out_turn'])
    json.dump(rep, open(cfg['out_turn'].rsplit('.', 1)[0] + '.json', 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('cut', 'blend', 'frames')}), rep['kling_yaw_fit']['at_cut'], rep['yaw'][:6])
