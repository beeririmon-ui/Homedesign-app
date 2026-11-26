"""w7reg.py: register each nano return onto its sent crop (prep.py's SIFT affine + tone fit, unchanged), carry the segment masks along,
and measure the pieces in canvas px. -> out/reg-<k>.npz, out/reg.json"""
import sys, os, json, types
sys.dont_write_bytecode = True
import cv2, numpy as np
from PIL import Image
W7 = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel7/'
FB13 = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25/'
_src = open(FB13 + 'tools/prep.py').read().split('\n')
_ns = dict(np=np, cv2=cv2); exec('\n'.join(_src[30:67]), _ns)
sift_affine, tone_fit = _ns['sift_affine'], _ns['tone_fit']
CROP = (1120, 810, 2400, 1530)
PIECES = {'A': {'left': [4, 9], 'right': [6, 10], 'lumbar': [5, 7, 8], 'throw': [3], 'table': [1], 'lamp': [15]},
          'C': {'left': [1, 5, 8], 'right': [2, 6, 9], 'lumbar': [3, 4, 7], 'throw': [10], 'table': [11], 'lamp': [17]}}
rd = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255
def run(k):
    inp = rd(W7 + 'send/cush-crop.png'); inp2 = rd(W7 + 'send/cush-crop-x2.png')
    ch, cw = inp.shape[:2]
    ret = rd(W7 + f'ret/set{k}-nano.jpg')
    A, rec = sift_affine(ret, inp2)
    w2 = cv2.warpAffine(ret, A, (cw * 2, ch * 2), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.resize(w2, (cw, ch), interpolation=cv2.INTER_AREA)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    w1, tone = tone_fit(w1, inp, d < 0.05)
    d = np.abs(cv2.GaussianBlur(w1, (0, 0), 2.0) - cv2.GaussianBlur(inp, (0, 0), 2.0)).max(2)
    rec.update(tone_gain_offset=tone, unchanged_share=round(float((d < 0.04).mean()), 3), returned_px=list(ret.shape[1::-1]),
               mean_abs_diff_unchanged=round(float(np.abs(w1 - inp)[d < 0.04].mean() * 255), 2))
    seg = np.load(W7 + f'seg/full-{k}.npz')
    M = {}
    for piece, ids in PIECES[k].items():
        m = np.max(np.stack([seg[str(i)].astype(np.float32) / 255 for i in ids]), 0)
        m2 = cv2.warpAffine(m, A, (cw * 2, ch * 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        M[piece] = cv2.resize(m2, (cw, ch), interpolation=cv2.INTER_AREA)
    meas = {}
    for piece in ('left', 'right', 'lumbar', 'throw'):
        ys, xs = np.nonzero(M[piece] > 0.5)
        meas[piece] = dict(px=int(len(xs)), bbox_canvas=[int(xs.min() + CROP[0]), int(ys.min() + CROP[1]), int(xs.max() + CROP[0]), int(ys.max() + CROP[1])],
                           w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1))
    rec['pieces'] = meas
    np.savez_compressed(W7 + f'out/reg-{k}.npz', w1=w1.astype(np.float16), d=d.astype(np.float16), **{'m_' + p: v.astype(np.float16) for p, v in M.items()})
    return rec
if __name__ == '__main__':
    out = {}
    for k in sys.argv[1:]:
        out[k] = run(k)
        print(k, json.dumps({kk: v for kk, v in out[k].items() if kk != 'A'}))
    json.dump(out, open(W7 + 'out/reg.json', 'w'), indent=1)
