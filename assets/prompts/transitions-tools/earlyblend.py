"""earlyblend.py (FB21 leg 3 fix, motion-agent, 2026-11-27): start a kling clip's own soft blend earlier, 0 tokens.
kling sometimes reaches the furnished room only by a late dissolve (leg 3, K3c2: the empty north side of the bedroom for
0.6 s, then a 3-frame blend that also jumps the camera back ~8 frames). This replaces frames A0..B1 with a two-layer blend:
layer A plays the frames before kling's blend (A0 -> A1, still walking), layer B the first clean frames after it
(B0 -> B1, flow-interpolated at fractional positions). A1 and B1 are chosen at the same place on the walk (the door jambs
line up), so the two layers converge while B fades in; B's weight rises fast at first (1 - (1 - s)^2) so the products
show at once. Optionally both layers are moved toward each other along a smoothed flow (`sigma` px; 0 = a plain blend).
Frames before A0 and after B1 are kling's own. Forward only: B is ahead of A on the walk at every step.
  python3 earlyblend.py CONFIG.json
CONFIG: {"clip", "a": [A0, A1], "b": [B0, B1], "frames": D, "sigma": 0, "out": "clip.mp4"}"""
import sys, os, json, subprocess, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walk_fb19 as W
AS = W.AS


def at(K, p, cache):
    """frame at fractional index p (DIS interpolation, as the leg assembler does)"""
    i = int(np.floor(p)); tau = p - i
    if tau < 1e-3 or i >= len(K) - 1: return K[min(i, len(K) - 1)].astype(np.float32)
    if i not in cache: cache[i] = (AS.flow(K[i], K[i + 1]), AS.flow(K[i + 1], K[i]))
    return AS.interpolate(K[i], K[i + 1], tau, *cache[i]).astype(np.float32)


def blend(A, B, w, sigma):
    if sigma <= 0: return A * (1 - w) + B * w
    a8 = np.clip(A + 0.5, 0, 255).astype(np.uint8); b8 = np.clip(B + 0.5, 0, 255).astype(np.uint8)
    sm = lambda f: np.stack([cv2.GaussianBlur(f[..., k], (0, 0), sigma) for k in range(2)], -1)
    fab = sm(AS.flow(a8, b8)); fba = sm(AS.flow(b8, a8))
    ft0 = -(1 - w) * w * fab + w * w * fba; ft1 = (1 - w) * (1 - w) * fab - w * (1 - w) * fba
    return AS.backwarp(A, ft0) * (1 - w) + AS.backwarp(B, ft1) * w


def build(cfg):
    K = W.video(cfg['clip']); (a0, a1), (b0, b1), D = cfg['a'], cfg['b'], cfg['frames']; sig = cfg.get('sigma', 0)
    out = [k.astype(np.float32) for k in K[:a0]]; ca, cb = {}, {}; ws = []
    for j in range(D + 1):
        s = j / D; w = 1 - (1 - s) ** 2
        A = at(K, a0 + (a1 - a0) * s, ca); B = at(K, b0 + (b1 - b0) * s, cb)
        out.append(B if j == D else (A if j == 0 else blend(A, B, w, sig))); ws.append(round(w, 3))
    out += [k.astype(np.float32) for k in K[b1 + 1:]]
    return out, dict(a=[a0, a1], b=[b0, b1], frames=D, sigma=sig, weights=ws, frames_in=len(K), frames_out=len(out))


def enc(frames, path, fps=24):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'medium', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(np.clip(f + 0.5, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()


if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1])); frames, rep = build(cfg); enc(frames, cfg['out'])
    json.dump(rep, open(cfg['out'].rsplit('.', 1)[0] + '.json', 'w'), indent=1); print(json.dumps(rep))
