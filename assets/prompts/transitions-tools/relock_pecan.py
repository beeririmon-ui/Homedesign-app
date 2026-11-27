"""relock_pecan.py (motion-agent, 2026-11-26): the landing of arrival-fb19/final re-converged onto the set-B muslin throw
(default-frame-m0w-fix1-pecan.png), 0 var2 tokens. The walk is rebuilt in memory exactly as walk_fb19.py made it; only the
frames inside T-E0-W's landing lock (its last 12 source frames) take the residual new - old landing frame, carried along the
flow and faded with the lock's own smoothstep in source position; the last frame = the new still. Only those frames' files
are rewritten (1920 and the 1080 frames that average them); every other file stays byte for byte. Master and preview re-encoded.
  python3 relock_pecan.py"""
import os, sys, json, subprocess, numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import walk_fb19 as W
AS = W.AS
REPO = '/home/user/homedesign-app'; V = REPO + '/assets/video/transitions/warm-modern/arrival-fb19'; BASE = V + '/final'
SCR = os.path.dirname(HERE); OUT = SCR + '/out'
NEW = REPO + '/assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1-pecan.png'

frames, rep = W.main(V + '/ka2.kling-3-omni.take1.mp4', V + '/turn.kling-3-omni.take1.mp4', V + '/te0w.kling-3-omni.take1.mp4', OUT)
n = len(frames)
# determinism: a frame outside the tail, re-encoded, must be the file that is there
probe = 300; tmp = SCR + '/probe.avif'
Image.fromarray(frames[probe - 1]).save(tmp, 'AVIF', quality=55, speed=6)
same = open(tmp, 'rb').read() == open(BASE + '/1920/%04d.avif' % probe, 'rb').read(); os.remove(tmp)
print('rebuild identical to the published frame', probe, ':', same)
if not same: raise SystemExit('the rebuild differs from the published walk: stop')
tl = np.load(OUT + '/timeline.npz'); pos = tl['pos']; L = len(tl['C']) - 1                   # source index of the landing
old_last = frames[-1].copy(); new = np.array(Image.open(NEW).convert('RGB'))
g = AS.flow(new, old_last); resid = new.astype(np.float32) - AS.backwarp(old_last, g).astype(np.float32)
lock_n = 12; changed = []
for j in range(n - 1):
    k = L - pos[j]
    if k >= lock_n + 1: continue
    w = 1 - float(k) / (lock_n + 1); w = float(w * w * (3 - 2 * w))
    h = AS.flow(frames[j], old_last)
    f2 = np.clip(AS.backwarp(frames[j], w * AS.backwarp(g, h)).astype(np.float32) + w * AS.backwarp(resid, h) + 0.5, 0, 255).astype(np.uint8)
    if not np.array_equal(f2, frames[j]): frames[j] = f2; changed.append(j)
frames[-1] = new.copy(); changed.append(n - 1)
# rewrite only what changed: 1920 frames, and the 1080 frames whose (0.25, 0.5, 0.25) window touches them
jobs = []
for j in changed:
    q = (55, 72) if j < n - 8 else (85, 92); jobs.append((j + 1, 1920, 1080, frames[j], q[0], q[1], BASE))
ch = set(changed); f30_idx = sorted({j // 2 for j in ch} | {(j + 1) // 2 for j in ch if (j + 1) % 2 == 0} | {(j - 1) // 2 for j in ch if j % 2 == 1})
n30 = len([x for x in os.listdir(BASE + '/1080') if x.endswith('.avif')])
for i in f30_idx:
    jj = 2 * i
    if jj >= n - 1 or i == n30 - 1: f = frames[-1]
    elif jj == 0: f = frames[0]
    else: f = np.clip(0.25 * frames[jj - 1].astype(np.float32) + 0.5 * frames[jj] + 0.25 * frames[jj + 1] + 0.5, 0, 255).astype(np.uint8)
    q = (50, 60) if i < n30 - 4 else (85, 92); jobs.append((i + 1, 1080, 608, f, q[0], q[1], BASE))
for jb in jobs: W._enc(jb)
for path, sc, crf in ((V + '/arrival-fb19.final.1920.60fps.mp4', None, 14), (SCR + '/preview.mp4', '1280:720', 18)):
    vf = ['-vf', 'scale=%s:flags=lanczos' % sc] if sc else []
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '60', '-i', '-'] + vf +
                         ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
res = dict(landing='default-frame-m0w-fix1-pecan.png', last_vs_new_max=int(np.abs(frames[-1].astype(int) - new.astype(int)).max()),
           changed_1920=[changed[0] + 1, changed[-1] + 1], changed_1920_count=len(changed), changed_1080=[f30_idx[0] + 1, f30_idx[-1] + 1],
           resid_px=int((np.abs(resid).max(-1) > 1).sum()), shift_px_median=round(float(np.median(np.hypot(g[..., 0], g[..., 1]))), 3))
json.dump(res, open(OUT + '/relock_pecan.json', 'w'), indent=1); print(json.dumps(res))
