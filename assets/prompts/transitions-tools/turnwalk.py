"""turnwalk.py (FB21 leg 1): the head turn M0-W -> M0x-W with the walk starting in its last third (0 tokens).
One smootherstep turn of 49 deg over T s. Phase A (p 0 -> 2/3): the two stills turned about the lens (exact). Phase B (the last
third): kling's first walking frames, each turned back by what is left of the turn (a rotation needs no depth), with the stills'
turned view filling what lies beyond the kling frame's left edge (feathered 48 px). So the camera is already walking forward when
the turn settles. Writes phaseA.mp4 (60 fps), its last frame as mid.png, and the kling clip with phase B in place (24 fps).
  python3 turnwalk.py M0W.png M0X.png KLING.mp4 OUTDIR [T]"""
import os, sys, subprocess, numpy as np, cv2
from PIL import Image
import geo
sys.path.insert(0, '/home/user/homedesign-app/site/tools/transitions'); import assemble as AS
a, b, klp, out = sys.argv[1:5]; T = float(sys.argv[5]) if len(sys.argv) > 5 else 1.2
V0 = 0.553; P = (0.95, 5.55, 1.05); Y0, Y1 = 14.0, -35.0
A = np.array(Image.open(a).convert('RGB')).astype(np.float32); B = np.array(Image.open(b).convert('RGB')).astype(np.float32)
CA = geo.Cam(P, Y0, 35.0, 0.5, V0); CB_ = geo.Cam(P, Y1, 35.0, 0.5, V0)
yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64); px = np.stack([xx, yy], -1)
ss = lambda t: t ** 3 * (t * (6 * t - 15) + 10)
def maps(src, yaw):
    cam = geo.Cam(P, yaw, 35.0, 0.5, V0); q, d = src.project(cam.C + cam.rays(px))
    mx, my = q[..., 0].astype(np.float32), q[..., 1].astype(np.float32)
    return mx, my, (d > 0) & (mx >= 0) & (mx <= 1919) & (my >= 0) & (my <= 1079)
def stills_view(yaw, p):
    acc = np.zeros_like(A); ws = np.zeros((1080, 1920, 1), np.float32); near = []
    for C, I in ((CA, A), (CB_, B)):
        mx, my, ok = maps(C, yaw); edge = np.minimum(np.minimum(mx, 1919 - mx), 60) / 60.0
        w = (ok * np.clip(edge, 0.02, 1)).astype(np.float32)[..., None]; smp = cv2.remap(I, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        acc += smp * w; ws += w; near.append(smp)
    f = acc / np.maximum(ws, 1e-6); hole = ws[..., 0] <= 1e-6; f[hole] = (near[0] if p < 0.5 else near[1])[hole]
    return f
def enc(frames, path, fps):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'fast', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(np.clip(f + 0.5, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
# phase A
tA = None
for k in range(2000):
    if ss(k / 2000) >= 2 / 3: tA = k / 2000 * T; break
nA = int(round(tA * 60)) + 1; fa = []
for k in range(nA):
    t = tA * k / (nA - 1); p = ss(t / T); f = A if k == 0 else stills_view(Y0 + (Y1 - Y0) * p, p); fa.append(f)
enc(fa, out + '/phaseA.mp4', 60); Image.fromarray(np.clip(fa[-1] + 0.5, 0, 255).astype(np.uint8)).save(out + '/mid.png')
# phase B on the kling frames (locked to M0x-W first)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', klp, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
K = [f.copy() for f in np.frombuffer(raw, np.uint8).reshape(-1, 1080, 1920, 3)]
AS.end_lock(K, B.astype(np.uint8), None, n=12)
import chords                                                        # the corner swoop kling inherited from the first M0x-W
straight = []
for k in range(0, 40):
    xr = chords.walnut_left_edge(K[k]); w = 1.0 if k < 30 else (40 - k) / 10.0
    if xr is None or xr < 300: break
    K[k], mx_ = chords.straighten(K[k], 8, xr - 60, w=w); straight.append(round(mx_, 1))
nB = int(np.ceil((T - tA) * 24)); x_feather = 48.0
for k in range(nB + 1):
    t = min(T, tA + k / 24.0); p = ss(t / T); yaw = Y0 + (Y1 - Y0) * p
    if abs(yaw - Y1) < 1e-4: break
    mx, my, ok = maps(CB_, yaw)                                      # the kling frame stands where M0x-W stands (it walks off it)
    kf = cv2.remap(K[k].astype(np.float32), mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    w = (ok * np.clip(np.minimum(mx, 1919 - mx) / x_feather, 0, 1)).astype(np.float32)[..., None]
    K[k] = np.clip(kf * w + stills_view(yaw, p) * (1 - w) + 0.5, 0, 255).astype(np.uint8)
enc([f.astype(np.float32) for f in K], out + '/kling-turnwalk.mp4', 24)
print(dict(T=T, tA=round(tA, 3), phaseA_frames=nA, phaseB_kling_frames=nB, straightened=len(straight), max_shift=max(straight) if straight else 0))
