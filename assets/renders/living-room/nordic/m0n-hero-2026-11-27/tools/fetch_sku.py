"""fetch_sku.py: the SKU photos of the M0-N hero products into scratch (render-agent, 2026-11-27). Run from the repo root.
The list = ch.7 defaults, with the slot/engine rendered defaults where they differ (curtains, framed-art, floor-lamp)."""
import json, glob, os, subprocess, sys
from PIL import Image
SK = sys.argv[1]
ids = """curtains-cj-japanese-linen-half-shade framed-art-cj-morandi-triptych-sage wall-decor-aliexpress-natural-raffia-woven-bohemian-763597
accent-sconces-aliexpress-indoor-stone-wall-lamp vase-cj-textured-white-stoneware rug-cj-braided-wool-natural floor-lamp-cj-black-drum-linen
planter-cj-seagrass-belly sofa-cover-cj-cotton-muslin-fringe cushions-cj-boucle-teddy cushions-cj-knitted-chenille-bean-green
cushions-cj-linen-look-charcoal basket-cj-jute-rope-cylinder magazine-holder-cj-felt-log-basket table-runner-cj-linen-look-sage-fringe
bowl-cj-speckled-ivory-wide-bowl-21 candle-holders-cj-travertine-pedestal pouf-cj-cotton-knit-ball-cover pendant-cj-pleated-pumpkin-lantern-40
coffee-table-idana-javorina-olia-natural pool-cj-travertine-organic-tray-24""".split()
out = {}
for i in ids:
    c = json.load(open(glob.glob(f'data/products/**/{i}.json', recursive=True)[0]))
    urls = (c.get('images') or {}).get('urls', [])
    sku_img = [s.get('image') for s in (c.get('options') or {}).get('skus', []) if isinstance(s, dict) and s.get('in_room') and s.get('image')]
    cand = (sku_img[:1] + urls)[:4]
    out[i] = []
    for n, u in enumerate(cand):
        p = os.path.join(SK, f'{i}__{n}.img')
        subprocess.run(['curl', '-s', '-m', '25', '-o', p, u], capture_output=True, text=True)
        try:
            im = Image.open(p); im.load(); im.convert('RGB').save(p[:-4] + '.jpg', quality=90); os.remove(p)
            out[i].append(dict(url=u, file=os.path.basename(p[:-4] + '.jpg'), px=im.size, in_room_sku=(n == 0 and bool(sku_img))))
        except Exception:
            if os.path.exists(p): os.remove(p)
json.dump(out, open(os.path.join(SK, 'index.json'), 'w'), indent=1)
print({k: len(v) for k, v in out.items()})
