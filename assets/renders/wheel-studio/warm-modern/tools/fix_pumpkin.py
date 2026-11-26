#!/usr/bin/env python3
"""The pumpkin's glow toward its SKU photo (warm white, b* about 16; the render glowed amber, b* about 29): b* x0.6 on the shade only. Run once."""
import json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
k = 'pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light'
mo = cv2.imread(f'out/mask/{k}.png', 0) > 0
inner = cv2.distanceTransform(mo.astype(np.uint8), cv2.DIST_L2, 5); a = np.clip(inner / 3.0, 0, 1)[..., None]
o = load(f'out/{k}.png'); L = lab(o); L[..., 2] *= 0.6
save_png(f'out/{k}.png', lab2rgb(L) * a + o * (1 - a))
M = json.load(open('out/meta.json')); M[k]['colour_fix'] = dict(fix='b* x0.6 on the shade (the SKU photo glows warm white, b* about 16)'); json.dump(M, open('out/meta.json', 'w'), indent=1)
