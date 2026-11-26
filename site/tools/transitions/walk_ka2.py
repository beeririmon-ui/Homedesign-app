"""MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md): the part of the FB19 arrival that is final, K-A2
(motion-agent's take, from the door D0 to the hall HT2 fb16: assets/video/transitions/warm-modern/arrival-fb19/
ka2.kling-3-omni.take1.mp4, 5 s at 24 fps), made into the site's walk the way motion-agent made the whole walk
(assets/prompts/transitions.warm-modern/fb19-tools/walk_fb19.py), read only:

  locks  both ends onto the stills the clip was made from: its first frames onto D0's 16:9 frame (the site's door), its
         last onto HT2 fb16 (assemble.end_lock: a flow warp and a residual that fades out); frame 1 IS D0 and the last
         frame IS HT2, pixel for pixel
  pace   one progress axis = the picture's own motion (median DIS flow); an even picture speed (0.5x-1.6x of its median),
         eased in from rest at D0; at HT2 it slows but does not stop (the walk goes on into the living room: in code,
         until the rest of the walk is made), 60 fps, every frame interpolated (DIS) at its fractional source position
  gait   the same very subtle step as the whole walk (bob 2.4 px at 1080, roll 0.12 deg), 0 at both ends

Writes the 60 fps master (H.264 crf 12, yuv420p) and a small record beside it. Nothing in the repo's asset folders is
written. Usage: python3.12 -I walk_ka2.py <ka2.mp4> <d0.png> <ht2-frame.png> <out.mp4> <out.json>
"""
import json
import os
import subprocess
import sys

import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as AS  # noqa: E402

FPS = 60
SRC_FPS = 24.0
# the 16:9 frame of a 2720 canvas at 24 mm (finish.frame_view, the door's own; the site's door image is this frame)
D0_BOX = (77.4853, 43.4279, 2642.5147, 1486.5721)


def rd(p):
    return np.array(Image.open(p).convert('RGB'))


def frame_view(img, box, size=(1920, 1080)):
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0) / size[0], (y1 - y0) / size[1]
    M = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(img, M, size, flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


def video(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920, 3)
    return [a[i].copy() for i in range(len(a))]


def motion(frames):
    m = []
    for a, b in zip(frames[:-1], frames[1:]):
        f = AS.flow(cv2.resize(a, (480, 270), interpolation=cv2.INTER_AREA), cv2.resize(b, (480, 270), interpolation=cv2.INTER_AREA), scale=1.0)
        m.append(float(np.median(np.hypot(f[..., 0], f[..., 1]))) * 4)
    return np.array(m)


def main(ka2, d0p, ht2p, out_mp4, out_json):
    d0 = rd(d0p)
    d0 = frame_view(d0, D0_BOX) if d0.shape[:2] != (1080, 1920) else d0
    ht2 = rd(ht2p)
    src = video(ka2)
    rep = {'frames_in': len(src), 'src_fps': SRC_FPS}
    rep['lock'] = AS.end_lock(src, d0, ht2, n=10)
    mag = np.maximum(motion(src), 0.05)
    C = np.concatenate([[0], np.cumsum(mag)])
    vnat = mag * SRC_FPS
    tn = np.concatenate([[0], np.cumsum(np.full(len(mag), 1 / SRC_FPS))])
    tg = np.arange(0, tn[-1], 1 / 240)
    vg = np.interp(tg, tn[:-1], vnat)
    sig = 0.25 * 240
    k = np.exp(-0.5 * (np.arange(-3 * sig, 3 * sig + 1) / sig) ** 2)
    k /= k.sum()
    vs = np.convolve(np.pad(vg, (len(k) // 2, len(k) // 2), mode='edge'), k, 'valid')
    Cg = np.interp(tg, tn, C)
    med = float(np.median(vs))
    vs = np.clip(vs, 0.5 * med, 1.6 * med)
    rep['picture_speed_px_s'] = dict(median=round(med), lo=round(0.5 * med), hi=round(1.6 * med))
    # eased in from rest at D0 (0.5 s); at HT2 it slows to 40 % over the last 0.6 s and walks on (no stop: FB19)
    T_in, T_out, FLOOR = 0.5, 0.6, 0.4
    t, c, Cs = 0.0, 0.0, [0.0]
    while c < C[-1] - 1e-6 and len(Cs) < 4000:
        v = np.interp(c, Cg, vs)
        e_in = min(1.0, 0.15 + 0.85 * t / T_in)
        rem = C[-1] - c
        e_out = max(FLOOR, min(1.0, np.sqrt(max(rem, 0) / (v * T_out / 2 + 1e-6))))
        c = min(C[-1], c + v * e_in * e_out / FPS)
        t += 1 / FPS
        Cs.append(c)
    Cs = np.array(Cs)
    Cs[-1] = C[-1]
    pos = np.interp(Cs, C, np.arange(len(C)))
    n = len(pos)
    rep['out_frames'] = n
    rep['play_s'] = round((n - 1) / FPS, 3)
    tt = np.arange(n) / FPS
    sp = np.gradient(Cs) * FPS
    spn = np.clip(sp / np.median(sp[sp > 0]), 0, 1.2)
    env = np.minimum(1, np.minimum(tt / 0.6, (tt[-1] - tt) / 0.6)).clip(0, 1)
    env = env * env * (3 - 2 * env)
    phase = np.cumsum(spn) / FPS * 1.9 * 2 * np.pi
    bob = 2.4 * np.cos(phase) * spn * env
    roll = 0.12 * np.sin(phase / 2) * spn * env
    scl = 1 + 0.004 * env
    rep['gait'] = dict(bob_px_max=round(float(np.abs(bob).max()), 2), roll_deg_max=round(float(np.abs(roll).max()), 3), overscan=0.004)
    enc = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(FPS), '-i', '-',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-g', str(FPS), out_mp4],
        stdin=subprocess.PIPE)
    flows = {}

    def F(i):
        if i not in flows:
            flows.clear()
            flows[i] = (AS.flow(src[i], src[i + 1]), AS.flow(src[i + 1], src[i]))
        return flows[i]

    for j, p in enumerate(pos):
        i = int(np.floor(p))
        tau = float(p - i)
        if j == 0:
            im = d0
        elif j == n - 1:
            im = ht2
        else:
            im = src[-1] if i >= len(src) - 1 else (src[i] if tau < 1e-3 else AS.interpolate(src[i], src[i + 1], tau, *F(i)))
            if env[j] > 0:
                M = cv2.getRotationMatrix2D((960, 540), roll[j], scl[j])
                M[1, 2] += bob[j]
                im = cv2.warpAffine(im, M, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        enc.stdin.write(np.ascontiguousarray(im).tobytes())
    enc.stdin.close()
    if enc.wait():
        raise SystemExit('walk_ka2: ffmpeg failed')
    rep['first_is_d0'] = True
    rep['last_is_ht2'] = True
    json.dump(rep, open(out_json, 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != 'lock'}))


if __name__ == '__main__':
    main(*sys.argv[1:6])
