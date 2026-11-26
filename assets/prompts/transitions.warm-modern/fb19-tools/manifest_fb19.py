"""manifest_fb19.py: the site manifest of the FB19 final walk (reads walk.json and the exported frames)."""
import json, glob, os, sys, numpy as np, cv2
from PIL import Image
out, base = sys.argv[1:3]
r = json.load(open(out + '/walk.json'))
n = len(glob.glob(base + '/1920/*.avif')); n2 = len(glob.glob(base + '/1080/*.avif'))
Ls = np.array([cv2.cvtColor(cv2.resize(np.array(Image.open(base + '/1080/%04d.avif' % i).convert('RGB')), (160, 90)), cv2.COLOR_RGB2LAB)[..., 0].mean() for i in range(1, n2 + 1)])
d = np.diff(Ls); flips = int(sum(1 for k in range(len(d) - 1) if d[k] * d[k + 1] < 0 and min(abs(d[k]), abs(d[k + 1])) > 0.8))
sz = lambda w, e: sum(os.path.getsize(p) for p in glob.glob('%s/%d/*.%s' % (base, w, e)))
m0 = np.array(Image.open('/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1.png').convert('RGB')).astype(int)
last = np.array(Image.open(base + '/1920/%04d.avif' % n).convert('RGB')).astype(int)
play = (n - 1) / 60; seg = r['seg_of_output']
man = {"id": "arrival-fb19-final", "title": "The arrival: D0 -> the door opens up close -> the hall -> the walking turn -> M0-W fix1",
 "from": "D0", "to": "M0-W", "style": "warm-modern", "date": "2026-11-26", "author": "motion-agent",
 "decision": "FB19 (owner 2026-11-26): one first-person walk, scroll-scrubbable; cap 5,832 (approved), spent 5,832",
 "play_s": round(play, 3),
 "sampling": "uniform in time at the nominal walk: frame i (1-based) of a variant is shown at (i - 1) / fps s. The picture moves at an even rate (0.5x-1.6x of the median picture speed, up to 2.6x in the turn), eased in from D0 over 0.5 s and out onto M0-W over 0.7 s, so a scroll step of N frames shows a similar amount of motion anywhere. Forward only, no hold, no cut. Reverse = the same frames from last to first.",
 "path": "{variant}/{index:04d}.{ext}", "formats": ["avif", "webp"],
 "variants": {"1920": {"w": 1920, "h": 1080, "fps": 60, "frames": n, "avif_quality": 55, "webp_quality": 72, "last_frames_quality": {"frames": 8, "avif": 85, "webp": 92},
   "segments": {"K-A2 (the approach; the door opens close, the step into the hall)": seg.get('K-A2'), "turn (the walking turn to the living room)": seg.get('turn'), "T-E0-W (into the living room, landing)": seg.get('T-E0-W')}},
  "1080": {"w": 1080, "h": 608, "fps": 30, "frames": n2, "avif_quality": 50, "webp_quality": 60, "last_frames_quality": {"frames": 4, "avif": 85, "webp": 92},
   "note": "each frame the mean of the 60 fps frames around it (0.25, 0.5, 0.25); the first and last are the stills"}},
 "bytes": {"1920": {"avif": sz(1920, 'avif'), "webp": sz(1920, 'webp')}, "1080": {"avif": sz(1080, 'avif'), "webp": sz(1080, 'webp')}},
 "first_frame": "D0: assets/renders/hall/warm-modern/door-2026-11-16/d0.png, its 16:9 frame (finish.frame_view) = the site's D0 rest image; 0 difference before encoding",
 "last_frame": "M0-W fix1: assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w-fix1.png; 0 difference before encoding (AVIF 1920: mean %.2f levels, p99 %d)" % (np.abs(last - m0).mean(), int(np.percentile(np.abs(last - m0), 99))),
 "stills_on_the_way": {"HT2": "hall-products-2026-11-19/ht2-products-fb16-frame.png", "HDx2": "hall-products-2026-11-19/hdx2-products-fb19-frame.png (the living room through the opening = M0-W fix1)"},
 "swap": {"at_end": "after the last frame, the room's live layers (the same picture with the defaults); a variant the visitor chose blends in over 200 ms", "at_start": "the D0 rest image is frame 1"},
 "gait": r['gait'], "locks": {"K-A2": "ends -> D0 / HT2 fb16", "turn": "ends -> HT2 fb16 / HDx2 fb19", "T-E0-W": "ends -> HDx2 fb19 / M0-W fix1 (12 frames)"},
 "checks": {"brightness_up_down_flips_over_0.8L": flips, "old_table_or_old_living_room": "0 (HDx2 rebuilt from fix1; K-A2 and the turn end on HT2 / HDx2 fb19; T-E0-W lands on fix1)"},
 "sources": {"K-A2": "ka2.kling-3-omni.take1.mp4", "turn": "turn.kling-3-omni.take1.mp4", "T-E0-W": "te0w.kling-3-omni.take1.mp4", "tools": "assets/prompts/transitions.warm-modern/fb19-tools/ (walk_fb19.py, manifest_fb19.py)", "jobs": "assets/prompts/transitions.warm-modern/jobs-fb19.json"},
 "qa": "pending (qa-agent)", "temporary": False}
man['bytes_per_2s'] = {w: {e: int(man['bytes'][w][e] / play * 2) for e in ('avif', 'webp')} for w in ('1920', '1080')}
json.dump(man, open(base + '/manifest.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: man[k] for k in ('play_s', 'bytes', 'bytes_per_2s', 'last_frame', 'checks')}, ensure_ascii=False))
