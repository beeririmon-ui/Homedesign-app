#!/usr/bin/env python3
"""Per image: dE00 of the main colour (median Lab of the lit body, the 30-80 L-percentile band) against the SKU photo's.
Singles: the product mask on the final image. Sets: a box per piece on the white-balanced raw. SKU photo: a box on the product."""
import json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
V = json.load(open('plan.json')); META = json.load(open('out/meta.json'))
REF = {v['variant']: [p['ref'] for p in v['products']] for v in V}
B = lambda f, b: (f, b)
SKU = {
 'set-B': [B(REF['set-B'][0], (.25, .25, .75, .75)), B(REF['set-B'][1], (.45, .35, .85, .75)), B(REF['set-B'][2], (.3, .3, .7, .7)), B(REF['set-B'][3], (.3, .35, .7, .75))],
 'set-A': [B(REF['set-A'][0], (.35, .3, .75, .7)), B(REF['set-A'][1], (.5, .45, .85, .8)), B(REF['set-A'][2], (.3, .3, .7, .7)), B('in/master-flax.jpg', (.15, .15, .85, .85))],
 'set-C': [B(REF['set-C'][0], (.3, .3, .7, .7)), B(REF['set-C'][1], (.35, .25, .7, .55)), B(REF['set-C'][2], (.15, .4, .6, .85)), B(REF['set-C'][3], (.35, .4, .75, .8))],
}
PIECE = {'set-B': [(.18, .3, .35, .45), (.6, .3, .82, .5), (.33, .48, .62, .62), (.15, .72, .5, .8)],
         'set-A': [(.2, .22, .35, .45), (.55, .25, .72, .4), (.35, .45, .62, .58), (.15, .66, .45, .8)],
         'set-C': [(.25, .27, .45, .42), (.62, .35, .8, .55), (.3, .5, .6, .65), (.12, .74, .45, .84)]}
SINGLE = {
 'hand-towel-aliexpress-pure-linen-towel-38x55-caramel': B(REF['hand-towel-aliexpress-pure-linen-towel-38x55-caramel'][0], (.25, .45, .45, .8)),
 'hand-towel-aliexpress-pure-linen-towel-38x55-linen': B(REF['hand-towel-aliexpress-pure-linen-towel-38x55-linen'][0], (.3, .3, .6, .7)),
 'tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki': B(REF['tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki'][0], (.25, .2, .75, .75)),
 'pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light': B('refx/p0_5.jpg', (.25, .75, .75, .88)),
 'pendant-cj-scalloped-pleated-bell-45': B('refx/p1_3.jpg', (.35, .45, .65, .7)),
 'sofa-cover-cj-cotton-muslin-fringe-pecan-150x200': B(REF['set-B'][3], (.3, .35, .7, .75)),
 'sofa-cover-cj-cotton-muslin-fringe-flax-brown-150x200': B('in/master-flax.jpg', (.15, .15, .85, .85)),
 'sofa-cover-cj-cotton-muslin-fringe-clay-150x200': B(REF['set-C'][3], (.35, .4, .75, .8)),
}
for c, sku in (('deep-chestnut-brown', 'CJZW264585012LO'), ('coffee', 'CJZW264585008HS'), ('green', 'CJZW264585024XC'), ('linen-brown', 'CJZW264585004DW'), ('pink', 'CJZW264585020TG')):
    SINGLE[f'bedspread-cj-waffle-gauze-fringe-150x200-{c}'] = B(f'in/{sku}.jpg', (.15, .15, .85, .85))
R = {}
for k, (f, b) in SINGLE.items():
    if not os.path.exists(f'out/{k}.png'): continue
    o = load(f'out/{k}.png'); m = cv2.imread(f'out/mask/{k}.png', 0) > 0
    m = cv2.erode(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    c_o = main_colour(lab(o), m); c_r = main_colour(lab(box(load(f), b)))
    R[k] = dict(render_lab=c_o.round(1).tolist(), sku_lab=c_r.round(1).tolist(), de00=round(de00(c_o, c_r), 2))
for k in SKU:
    if k not in META: continue
    raw = load(META[k]['raw']); g = np.array(META[k]['gain'])
    corr = to_srgb(to_lin(raw) * g); Lc = lab(corr)
    pieces = []
    for (f, b), pb in zip(SKU[k], PIECE[k]):
        c_o = main_colour(box(Lc, pb)); c_r = main_colour(lab(box(load(f), b)))
        pieces.append(dict(render_lab=c_o.round(1).tolist(), sku_lab=c_r.round(1).tolist(), de00=round(de00(c_o, c_r), 2)))
    R[k] = dict(pieces=pieces, de00=max(p['de00'] for p in pieces))
json.dump(R, open('out/check.json', 'w'), indent=1)
for k, v in R.items():
    print(f"{v['de00']:6.2f}  {k}", v.get('render_lab'), v.get('sku_lab'), [p['de00'] for p in v.get('pieces', [])])
