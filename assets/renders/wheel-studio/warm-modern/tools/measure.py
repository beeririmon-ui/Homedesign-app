#!/usr/bin/env python3
"""check.py, then: every value also exposure-matched (the render's linear RGB scaled to the SKU photo's luminance: the lifestyle photos
are 1-2 stops darker than the studio, so the raw dE00 mostly measures the photo's exposure); the code-fixed set pieces and the lamps
measured on the final image."""
import json, os, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from fixes import locate, to_out, META
subprocess.run([sys.executable, 'tools/check.py'], check=True, capture_output=True)
R = json.load(open('out/check.json')); V = json.load(open('plan.json')); REF = {v['variant']: [p['ref'] for p in v['products']] for v in V}


def em(c_o, c_r):
    rl = to_lin(lab2rgb(np.array(c_o, np.float32)[None, None])[0, 0]); sl = to_lin(lab2rgb(np.array(c_r, np.float32)[None, None])[0, 0])
    Y = lambda c: float(np.dot(c, [0.2126, 0.7152, 0.0722])); k = Y(sl) / Y(rl)
    return round(de00(lab(to_srgb(rl * k)[None, None].astype(np.float32))[0, 0], np.array(c_r)), 2), round(k, 3)


for key, cut, idx, ref, b in [('set-A', 'seg/0a6f831d/5.png', 2, REF['set-A'][2], (.3, .3, .7, .7)), ('set-C', 'seg/4724bf21/2.png', 1, REF['set-C'][1], (.35, .25, .7, .55))]:
    m, _ = locate(META[key]['raw'], cut); mo = cv2.erode((to_out(m, key) > 0.5).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    c_o = main_colour(lab(load(f'out/{key}.png')), mo); c_r = main_colour(lab(box(load(ref), b)))
    R[key]['pieces'][idx].update(render_lab=c_o.round(1).tolist(), de00=round(de00(c_o, c_r), 2), measured_on='final image, piece mask (after the colour fix)')
for k, v in R.items():
    for p in v.get('pieces', [v]):
        p['de00_exposure_matched'], p['exposure_k'] = em(p['render_lab'], p['sku_lab'])
    if 'pieces' in v:
        v['de00'] = max(p['de00'] for p in v['pieces']); v['de00_exposure_matched'] = max(p['de00_exposure_matched'] for p in v['pieces'])
json.dump(R, open('out/check.json', 'w'), indent=1)
for k, v in R.items():
    print(f"{v['de00_exposure_matched']:6.2f} (raw {v['de00']:5.2f})  {k}", [p['de00_exposure_matched'] for p in v.get('pieces', [])])
