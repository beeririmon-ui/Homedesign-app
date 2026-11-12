# qa-agent S23 (ת85, "no price changed"): every price in the three full catalogs of my S22 copy (9b6c6746) against my S23
# copy (bd5ac86a): the product's price, each variant's price, and each option row's retail. python3 -I <s22 gen> <s23 gen> <out>
import json, sys
a_dir, b_dir, out = sys.argv[1:4]
def prices(path):
    d = json.load(open(path))
    m = {}
    for p in d.get('products', []):
        m[(p['id'], '_product')] = p.get('price_agorot')
        for v in p.get('variants', []) or []:
            m[(p['id'], v.get('id'))] = (v.get('price_agorot'), v.get('unit_price_agorot'))
        o = p.get('options') or {}
        for i, (vals, price) in enumerate(zip(o.get('v') or [], o.get('p') or [])):
            m[(p['id'], 'opt:' + json.dumps(vals))] = price
        for v in p.get('variants_full', []) or []:
            m[(p['id'], 'full:' + str(v.get('id')))] = v.get('price_agorot')
    return m
res = {}
for cat in ['catalog.full.json', 'catalog.story.full.json', 'catalog.test-page.full.json', 'catalog.public.json']:
    A, B = prices(f'{a_dir}/{cat}'), prices(f'{b_dir}/{cat}')
    changed = sorted({k[0] for k in set(A) | set(B) if A.get(k) != B.get(k)})
    per = {}
    for k in set(A) | set(B):
        if A.get(k) != B.get(k):
            per.setdefault(k[0], 0)
            per[k[0]] += 1
    res[cat] = {'keys_s22': len(A), 'keys_s23': len(B), 'products_with_a_changed_price': changed,
                'changed_keys': sum(1 for k in set(A) | set(B) if A.get(k) != B.get(k)), 'changed_per_product': per,
                'option_prices_s22': sum(1 for k in A if k[1].startswith('opt:')), 'option_prices_s23': sum(1 for k in B if k[1].startswith('opt:'))}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
