"""leg_fb21.py (motion-agent, 2026-11-26): one FB21 route leg (one kling clip) -> the site's scrubbable frame sequence. 0 tokens.
Same method as walk_fb19.py: both ends locked onto the rooms' display frames (assemble.end_lock: flow warp + a fading residual),
an even picture speed (0.5x-1.6x of the median), a short ease in and out (their frames are marked in the manifest so the player can
skip them when it chains legs at x2-x3), the very subtle gait (0 at both ends), 1920 @ 60 fps and 1080 @ 30 fps, AVIF + WebP.
  python3 leg_fb21.py CLIP.mp4 FIRST.png LAST.png OUTDIR BASE PREVIEW.mp4 MASTER.mp4 ID FROM TO"""
import os, sys, json, numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import walk_fb19 as W
AS = W.AS; FPS = 60
T_IN, T_OUT = 0.4, 0.6

def build_multi(chain, out):
    """chain: [(clip.mp4, first_still.png, last_still.png), ...]; consecutive clips share their waypoint still (locked onto it)"""
    rep = {'frames_in': [], 'lock': {}}; src = []; rate = []; seg = []
    for i, e in enumerate(chain):                 # an optional 4th entry: 'kling' (a walk, 0.85-1.4x) or 'code' (paced as a turn, up to 3.5x)
        clip, f, l = e[:3]; st = e[3] if len(e) > 3 else 'kling'
        K = W.video(clip); rep['lock']['clip%d' % (i + 1)] = AS.end_lock(K, W.rd(f), W.rd(l), n=12); rep['frames_in'].append(len(K))
        src += K if i == 0 else K[1:]; rate += [24.0] * (len(K) - 1); seg += [st] * (len(K) - 1)
    rep['pacing'] = [e[3] if len(e) > 3 else 'kling' for e in chain]
    return pace_and_render(src, np.array(rate), seg, W.rd(chain[0][1]), W.rd(chain[-1][2]), out, rep)

def build(clip, first, last, out, prefix=None, mid=None):
    """prefix: an optional code move at 60 fps that ends on `mid` (the kling clip's first frame); then the kling clip -> last"""
    rep = {}; A = W.rd(first); B = W.rd(last)
    K = W.video(clip)
    if prefix:
        P = W.video(prefix); M = W.rd(mid); P[0] = A.copy(); P[-1] = M.copy()
        rep['lock'] = AS.end_lock(K, M, B, n=12); src = P + K[1:]
        rate = np.array([60.0] * (len(P) - 1) + [24.0] * (len(K) - 1)); seg = ['code'] * (len(P) - 1) + ['kling'] * (len(K) - 1)
        rep['frames_in'] = dict(code=len(P), kling=len(K))
    else:
        rep['lock'] = AS.end_lock(K, A, B, n=12); src = K
        rate = np.full(len(K) - 1, 24.0); seg = ['kling'] * (len(K) - 1); rep['frames_in'] = len(K)
    return pace_and_render(src, rate, seg, A, B, out, rep)

def pace_and_render(src, rate, seg, A, B, out, rep):
    mag = np.maximum(W.motion(src), 0.05); C = np.concatenate([[0], np.cumsum(mag)])
    tn = np.concatenate([[0], np.cumsum(1 / rate)]); vnat = mag * rate
    tg = np.arange(0, tn[-1], 1 / 240); vg = np.interp(tg, tn[:-1], vnat)
    sig = 0.25 * 240; k = np.exp(-0.5 * (np.arange(-3 * sig, 3 * sig + 1) / sig) ** 2); k /= k.sum()
    vs = np.convolve(np.pad(vg, (len(k) // 2, len(k) // 2), mode='edge'), k, 'valid'); Cg = np.interp(tg, tn, C)
    segg = np.array(seg)[np.clip(np.searchsorted(tn, tg, side='right') - 1, 0, len(seg) - 1)]
    med = float(np.median(vs[segg == 'kling'])); hi = np.where(segg == 'code', 3.5 * med, 1.4 * med); lo = np.where(segg == 'code', 0.5 * med, 0.85 * med)
    vs = np.clip(vs, lo, hi)
    vs = np.convolve(np.pad(vs, (len(k) // 2, len(k) // 2), mode='edge'), k, 'valid')        # smooth again across the clamps and the seam
    rep['picture_speed_px_s'] = dict(median_walk=round(med), walk=[round(0.85 * med), round(1.4 * med)], turn_max=round(3.5 * med))
    t, c, Cs, EI, EO = 0.0, 0.0, [0.0], [0.15], [1.0]
    while c < C[-1] - 1e-6 and len(Cs) < 4000:
        v = np.interp(c, Cg, vs); e_in = min(1.0, 0.15 + 0.85 * t / T_IN)
        rem = C[-1] - c; e_out = min(1.0, np.sqrt(max(rem, 0) / (v * T_OUT / 2 + 1e-6)))
        c = min(C[-1], c + v * e_in * max(e_out, 0.04) / FPS); t += 1 / FPS; Cs.append(c); EI.append(e_in); EO.append(e_out)
    Cs = np.array(Cs); Cs[-1] = C[-1]; pos = np.interp(Cs, C, np.arange(len(C))); n = len(pos)
    sp = np.gradient(Cs) * FPS; full = 0.95 * np.interp(np.arange(n), np.arange(n), sp)
    EI, EO = np.array(EI[:n]), np.array(EO[:n]); EO[-1] = 0
    ease_in = int(np.nonzero(EI < 0.999)[0].max()) + 1                     # last frame still easing in (1-based)
    ease_out = int(np.nonzero(EO < 0.999)[0].min()) + 1                    # first frame of the landing deceleration
    tt = np.arange(n) / FPS; spn = np.clip(sp / np.median(sp[sp > 0]), 0, 1.2)
    env = np.minimum(1, np.minimum(tt / 0.5, (tt[-1] - tt) / 0.5)).clip(0, 1); env = env * env * (3 - 2 * env)
    phase = np.cumsum(spn) / FPS * 1.9 * 2 * np.pi
    bob = 2.4 * np.cos(phase) * spn * env; roll = 0.12 * np.sin(phase / 2) * spn * env; scl = 1 + 0.004 * env
    rep['gait'] = dict(bob_px_max=round(float(np.abs(bob).max()), 2), roll_deg_max=round(float(np.abs(roll).max()), 3), overscan=0.004)
    frames = []; cache = {}
    for j, p in enumerate(pos):
        i = int(np.floor(p)); tau = float(p - i)
        if i >= len(src) - 1: im = src[-1]
        elif tau < 1e-3: im = src[i]
        else:
            if i not in cache: cache.clear(); cache[i] = (AS.flow(src[i], src[i + 1]), AS.flow(src[i + 1], src[i]))
            im = AS.interpolate(src[i], src[i + 1], tau, *cache[i])
        if 0 < j < n - 1 and env[j] > 0:
            M = cv2.getRotationMatrix2D((960, 540), float(roll[j]), float(scl[j])); M[1, 2] += float(bob[j])
            im = cv2.warpAffine(im, M, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        frames.append(im)
    frames[0] = A.copy(); frames[-1] = B.copy()
    rep.update(out_frames=n, play_s=round((n - 1) / FPS, 3), ease_in_frames_1920=[1, ease_in], ease_out_frames_1920=[ease_out, n],
               first_max_diff=int(np.abs(frames[0].astype(int) - A.astype(int)).max()), last_max_diff=int(np.abs(frames[-1].astype(int) - B.astype(int)).max()),
               speed_max_jump_pct=round(float(100 * np.max(np.abs(np.diff(sp))) / np.median(sp)), 1))
    json.dump(rep, open(out + '/leg.json', 'w'), indent=1, default=str)
    return frames, rep

if __name__ == '__main__':
    if sys.argv[1] == '--chain':                                       # --chain CHAIN.json OUT BASE PREVIEW MASTER ID FROM TO
        import json as _j
        ch = _j.load(open(sys.argv[2])); out, base, preview, master, lid, frm, to = sys.argv[3:10]
        first, last = ch[0][1], ch[-1][2]
        os.makedirs(out, exist_ok=True); os.makedirs(base, exist_ok=True)
        frames, rep = build_multi(ch, out)
    else:
        clip, first, last, out, base, preview, master, lid, frm, to = sys.argv[1:11]
        prefix = sys.argv[11] if len(sys.argv) > 11 else None; mid = sys.argv[12] if len(sys.argv) > 12 else None
        os.makedirs(out, exist_ok=True); os.makedirs(base, exist_ok=True)
        frames, rep = build(clip, first, last, out, prefix, mid)
    ex = W.export(frames, rep, base, preview, master)
    n = rep['out_frames']; n2 = ex['n1080']; play = rep['play_s']
    lastenc = np.array(Image.open(base + '/1920/%04d.avif' % n).convert('RGB')).astype(int); B = W.rd(last).astype(int)
    man = {"id": lid, "from": frm, "to": to, "style": "warm-modern", "date": __import__("time").strftime("%Y-%m-%d"), "author": "motion-agent", "plan": "docs/proposals/wm-transitions-house-2026-11-26.md, FB21",
           "play_s": play, "sampling": "uniform in time at the nominal walk: frame i (1-based) is shown at (i - 1) / fps s; an even picture speed (0.5x-1.6x of the median) with a short ease in and out; forward only, no hold, no cut",
           "chain": {"first_frame": first.replace('/home/user/homedesign-app/', ''), "last_frame": last.replace('/home/user/homedesign-app/', ''),
                     "rule": "this leg's last frame is the next leg's first frame (the room's display frame): chain legs back to back",
                     "ease_in_frames": {"1920": rep['ease_in_frames_1920'], "1080": [1, (rep['ease_in_frames_1920'][1] + 1) // 2]},
                     "ease_out_frames": {"1920": rep['ease_out_frames_1920'], "1080": [(rep['ease_out_frames_1920'][0] + 1) // 2, n2]},
                     "fast_forward": "when chaining at x2-x3, skip the ease-in frames of every leg but the first and the ease-out frames of every leg but the last"},
           "path": "{variant}/{index:04d}.{ext}", "formats": ["avif", "webp"],
           "variants": {"1920": {"w": 1920, "h": 1080, "fps": 60, "frames": n, "avif_quality": 55, "webp_quality": 72, "last_frames_quality": {"frames": 8, "avif": 85, "webp": 92}},
                        "1080": {"w": 1080, "h": 608, "fps": 30, "frames": n2, "avif_quality": 50, "webp_quality": 60, "last_frames_quality": {"frames": 4, "avif": 85, "webp": 92}}},
           "bytes": ex['bytes'], "bytes_per_2s": {w: {e: int(ex['bytes'][w][e] / play * 2) for e in ('avif', 'webp')} for w in ('1920', '1080')},
           "ends": {"first_vs_still_before_encoding_max": rep['first_max_diff'], "last_vs_still_before_encoding_max": rep['last_max_diff'],
                    "last_avif_1920_mean_levels": round(float(np.abs(lastenc - B).mean()), 2)},
           "swap": {"at_start": "the room's live layers -> frame 1 (defaults): blend the visitor's variants out over 160-200 ms", "at_end": "last frame (defaults) -> the room's live layers: blend in over 160-200 ms"},
           "gait": rep['gait'], "lock": rep['lock'],
           "speed_max_jump_pct_per_frame": rep['speed_max_jump_pct'], "qa": "pending (qa-agent)"}
    json.dump(man, open(base + '/manifest.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: man[k] for k in ('play_s', 'bytes_per_2s', 'ends', 'lock', 'speed_max_jump_pct_per_frame')}), json.dumps(man['chain']['ease_in_frames']), json.dumps(man['chain']['ease_out_frames']))
