"""headturn.py: M0-W -> M0x-W, the head turning right from the same point (exact: a rotation needs no depth). Each frame takes
M0-W where it sees, else M0x-W, with a 3-degree cross-fade where both see. Yaw 14 -> -35 on a smootherstep.
  python3 headturn.py M0W.png M0X.png OUT.mp4 seconds"""
import sys, subprocess, numpy as np, cv2
from PIL import Image
import geo
a, b, out, T = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
V0 = 0.553; P = (0.95, 5.55, 1.05)
A = np.array(Image.open(a).convert('RGB')).astype(np.float32); B = np.array(Image.open(b).convert('RGB')).astype(np.float32)
CA = geo.Cam(P, 14.0, 35.0, 0.5, V0); CB_ = geo.Cam(P, -35.0, 35.0, 0.5, V0)
yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64); px = np.stack([xx, yy], -1)
n = int(round(T * 60)) + 1; frames = []
for k in range(n):
    t = k / (n - 1); S = t ** 3 * (t * (6 * t - 15) + 10)
    cam = geo.Cam(P, 14.0 - 49.0 * S, 35.0, 0.5, V0); D = cam.rays(px); Q = cam.C + D
    out_ = np.zeros_like(A); ws = np.zeros((1080, 1920, 1), np.float32)
    for C, I in ((CA, A), (CB_, B)):
        q, d = C.project(Q); mx, my = q[..., 0].astype(np.float32), q[..., 1].astype(np.float32)
        ok = (d > 0) & (mx >= 0) & (mx <= 1919) & (my >= 0) & (my <= 1079)
        edge = np.minimum(np.minimum(mx, 1919 - mx), 60) / 60.0          # fade over 60 px from the source's side edges
        w = (ok * np.clip(edge, 0.02, 1)).astype(np.float32)[..., None]
        smp = cv2.remap(I, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        out_ += smp * w; ws += w
        if C is CA: nearA = smp
        else: nearB = smp
    f = out_ / np.maximum(ws, 1e-6)
    hole = ws[..., 0] <= 1e-6                                        # seen by neither (corners mid-turn): the nearer still, stretched
    f[hole] = (nearA if S < 0.5 else nearB)[hole]
    if k == 0: f = A
    if k == n - 1: f = B
    frames.append(np.clip(f + 0.5, 0, 255).astype(np.uint8))
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '60', '-i', '-',
                      '-c:v', 'libx264rgb', '-crf', '4', '-preset', 'fast', out], stdin=subprocess.PIPE)
for f in frames: p.stdin.write(f.tobytes())
p.stdin.close(); p.wait(); print('frames', n)
