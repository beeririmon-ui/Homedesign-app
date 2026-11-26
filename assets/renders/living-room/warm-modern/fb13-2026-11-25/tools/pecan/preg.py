"""preg.py: register the Pecan nano return onto its sent crop (prep.py's SIFT affine + tone fit, unchanged, as tools/wheel/w7reg.py).
-> out/reg.npz (w1 = the return at crop scale, d = blurred diff to the input), out/reg.json"""
import sys, json
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
PC = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/pecan/'
FB13 = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
_src = open(FB13 + 'tools/prep.py').read().split('\n')
_ns = dict(np=np, cv2=cv2); exec('\n'.join(_src[30:67]), _ns)
sift_affine, tone_fit = _ns['sift_affine'], _ns['tone_fit']
rd = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255
inp = rd(PC + 'send/cush-crop.png'); inp2 = rd(PC + 'send/cush-crop-x2.png')
ch, cw = inp.shape[:2]
ret = rd(PC + 'ret/pecan-nano.jpg')
A, rec = sift_affine(ret, inp2)
w2 = cv2.warpAffine(ret, A, (cw * 2, ch * 2), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
w1 = cv2.resize(w2, (cw, ch), interpolation=cv2.INTER_AREA)
d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
w1, tone = tone_fit(w1, inp, d < 0.05)
d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
rec.update(tone_gain_offset=tone, unchanged_share=round(float((d < 0.04).mean()), 3), returned_px=list(ret.shape[1::-1]),
           mean_abs_diff_unchanged=round(float(np.abs(w1 - inp)[d < 0.04].mean() * 255), 2))
np.savez_compressed(PC + 'out/reg.npz', w1=w1.astype(np.float16), d=d.astype(np.float16), A=np.asarray(A, np.float64))
json.dump({k: v for k, v in rec.items() if k != 'A'}, open(PC + 'out/reg.json', 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in rec.items() if k != 'A'}, default=float))
