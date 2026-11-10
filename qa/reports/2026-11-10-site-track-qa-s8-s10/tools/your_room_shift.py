"""qa-agent 2026-11-10 (S8): is the layer in "החדר שלך" where the engine puts it? For each order's 1280 capture, the
figure (the top 640×360 of the capture) is compared with my composite of the same files (the base, the drawn layer in its
rect), inside the layer's box only, with the layer shifted by −3…+3 px: the best shift must be (0, 0).
Usage: python3 -I your_room_shift.py <qa folder> <copy>/site"""
import json, sys
import numpy as np
from PIL import Image
qa, site = sys.argv[1:3]
d = json.load(open(f'{qa}/data/your-room.json'))
out = []
for o in d['orders']:
    v = o['views'][0]
    f = v['figure']
    W, H = int(f['frame'][2]), int(f['frame'][3])
    shot = np.asarray(Image.open(f"{qa}/overlays/your-room-{o['name']}-1280.png").convert('RGB'), dtype=np.int16)[:H, :W]
    base = Image.open(f"{site}/web/public/media/{f['base']['src']}").convert('RGB').resize((W, H), Image.BILINEAR)
    lay = f['layers'][0]
    lx, ly, lw, lh = [round(x) for x in lay['box']]
    layer = Image.open(f"{site}/web/public/media/{lay['src']}").convert('RGBA').resize((round(lay['box'][2]), round(lay['box'][3])), Image.BILINEAR)
    res = {}
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            comp = base.copy()
            comp.alpha_composite if False else None
            c = comp.convert('RGBA')
            c.alpha_composite(layer, (lx + dx, ly + dy))
            a = np.asarray(c.convert('RGB'), dtype=np.int16)
            box = (slice(ly, ly + lh), slice(lx, lx + lw))
            res[(dx, dy)] = float(np.abs(a[box] - shot[box]).mean())
    best = min(res, key=res.get)
    out.append({'order': o['name'], 'layer': lay['src'], 'box': lay['box'], 'best_shift': best, 'mean_abs_at_best': round(res[best], 2), 'mean_abs_at_0': round(res[(0, 0)], 2), 'mean_abs_at_1px': round(min(res[(1, 0)], res[(-1, 0)], res[(0, 1)], res[(0, -1)]), 2)})
json.dump(out, open(f'{qa}/data/your-room-shift.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
