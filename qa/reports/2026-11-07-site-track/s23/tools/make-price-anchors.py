# S23 (frontend-dev), QA S22 ת85: the SKU each studio price was set for, as a list the price gate reads
# (site/tools/price-anchors.json) until the price entries carry it themselves (`retail_sku`).
# For each entry of data/economics/products.json with a retail_ils, and a card with options:
#   - the entry unchanged since 7b42ddc1 (QA S21's commit: the same retail_ils and retail_src): the card's default SKU there;
#   - the entry set since (another retail_ils or retail_src): the card's default SKU now (the price was set against it).
# Reads git; writes the JSON to argv[1]. Run from the repo root: python3 -I <this> site/tools/price-anchors.json
import json, subprocess, sys, glob, os
BASE = '7b42ddc1'
def git_json(path):
    try:
        return json.loads(subprocess.run(['git', 'show', f'{BASE}:{path}'], capture_output=True, check=True).stdout)
    except Exception:
        return None
now_e = json.load(open('data/economics/products.json'))['products']
base_e = (git_json('data/economics/products.json') or {}).get('products', {})
cards = {}
for f in glob.glob('data/products/**/*.json', recursive=True):
    try:
        c = json.load(open(f))
    except Exception:
        continue
    if isinstance(c, dict) and c.get('id') and c.get('options', {}).get('default_sku'):
        cards[c['id']] = (f, c)
out, stats = {}, {'unchanged_since_base': 0, 'set_since_base': 0, 'default_moved_since_base': 0}
for pid, e in sorted(now_e.items()):
    if not isinstance(e.get('retail_ils'), (int, float)) or pid not in cards:
        continue
    f, c = cards[pid]
    b = base_e.get(pid) or {}
    same = b.get('retail_ils') == e.get('retail_ils') and b.get('retail_src') == e.get('retail_src')
    sku = c['options']['default_sku']
    if same:
        bc = git_json(f)
        bsku = (bc or {}).get('options', {}).get('default_sku')
        if bsku:
            sku = bsku
        stats['unchanged_since_base'] += 1
        if bsku and bsku != c['options']['default_sku']:
            stats['default_moved_since_base'] += 1
    else:
        stats['set_since_base'] += 1
    out[pid] = {'sku': sku, 'retail_ils': e['retail_ils'], 'retail_src': e.get('retail_src'), 'from': BASE if same else 'now'}
doc = {
    '_about': "S23 (QA S22 ת85): the SKU each studio price (data/economics/products.json retail_ils) was set for. The price gate in tools/build-catalog.ts warns when a card's default SKU is not this one while the price is unchanged (the whole option ladder would move with the default), and when a price was re-set without saying its SKU. A price entry's own `retail_sku` wins over this list. Made by qa/reports/2026-11-07-site-track/s23/tools/make-price-anchors.py: the default SKU at 7b42ddc1 for a price unchanged since, else the default when the price was read.",
    'base': BASE,
    'anchors': out,
}
json.dump(doc, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(json.dumps({'anchors': len(out), **stats}))
