"""Review preview of a chained leg (no AVIF/WebP export, no repo writes): python3 preview_only.py CHAIN.json OUTDIR PREVIEW.mp4"""
import sys, json, subprocess
sys.path.insert(0, '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/arrival-fb19/tools')
import leg_fb21 as L
ch, out, prev = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
import numpy as np
W, AS = L.W, L.AS
def build_multi(chain, out):
    # like leg_fb21.build_multi, plus an optional 4th entry per clip: 'kling' (walk, 0.85-1.4x) or 'code' (a turn, up to 3.5x)
    rep = {'frames_in': [], 'lock': {}}; src = []; rate = []; seg = []
    for i, e in enumerate(chain):
        clip, f, l = e[:3]; st = e[3] if len(e) > 3 else 'kling'
        K = W.video(clip); rep['lock']['clip%d' % (i + 1)] = AS.end_lock(K, W.rd(f), W.rd(l), n=12); rep['frames_in'].append(len(K))
        src += K if i == 0 else K[1:]; rate += [24.0] * (len(K) - 1); seg += [st] * (len(K) - 1)
    return L.pace_and_render(src, np.array(rate), seg, W.rd(chain[0][1]), W.rd(chain[-1][2]), out, rep)
frames, rep = build_multi(ch, out)
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '60', '-i', '-',
                      '-vf', 'scale=1280:720:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', prev], stdin=subprocess.PIPE)
for f in frames: p.stdin.write(f.tobytes())
p.stdin.close(); p.wait()
print(json.dumps({k: rep[k] for k in ('out_frames', 'play_s', 'ease_in_frames_1920', 'ease_out_frames_1920', 'first_max_diff', 'last_max_diff', 'speed_max_jump_pct', 'picture_speed_px_s')}))
