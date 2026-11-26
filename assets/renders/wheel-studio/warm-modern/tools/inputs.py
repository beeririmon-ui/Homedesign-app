#!/usr/bin/env python3
"""Reference inputs for the flux-2 i2i jobs: 2x2 boards of the SKU photos for the cushion sets; crops without people for the
lifestyle SKU photos. Scratch only (supplier pixels never reach the output)."""
import json
from PIL import Image
V = json.load(open('plan.json'))
def sq(f, box=None, size=512):
    im = Image.open(f).convert('RGB')
    if box:
        w, h = im.size; im = im.crop((int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)))
    w, h = im.size; s = min(w, h); im = im.crop(((w-s)//2, (h-s)//2, (w-s)//2+s, (h-s)//2+s))
    return im.resize((size, size), Image.LANCZOS)
CROP = {'bedspread': (0.0, 0.40, 0.62, 1.0), 'flax-brown': (0.0, 0.38, 0.75, 1.0)}
jobs = {}
for v in V:
    if v['room'] == 'living-room':
        b = Image.new('RGB', (1024, 1024), 'white')
        for i, p in enumerate(v['products']):
            box = CROP['flax-brown'] if 'flax-brown' in str(p['option']) else None
            b.paste(sq(p['ref'], box), ((i % 2)*512, (i//2)*512))
        f = f"in/{v['variant']}.jpg"; b.save(f, quality=92); jobs[v['variant']] = f
    elif v['slot'] == 'bedspread':
        f = f"in/{v['products'][0]['sku']}.jpg"
        sq(v['products'][0]['ref'], CROP['bedspread'], 1024).save(f, quality=92); jobs[v['variant']] = f
    elif 'flax-brown' in v['variant']:
        f = 'in/master-flax.jpg'; sq(v['products'][0]['ref'], CROP['flax-brown'], 1024).save(f, quality=92); jobs[v['variant']] = f
json.dump(jobs, open('in/jobs-local.json', 'w'), indent=1)
print(json.dumps(jobs, indent=1))
