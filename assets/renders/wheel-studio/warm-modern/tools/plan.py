#!/usr/bin/env python3
"""Build plan.json: the wheel-studio variants (FB20), their cards, SKUs and SKU image URLs."""
import json, os
R = '/home/user/homedesign-app/'
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def card(p): return json.load(open(R + p))
def sku_by_id(c, sid):
    for s in c.get('options', {}).get('skus', []):
        if s['id'] == sid: return s
    return None
def prod(cardpath, sku, role, option=None):
    c = card(cardpath); s = sku_by_id(c, sku) if sku else None
    img = s['image'] if s and s.get('image') else c['images']['urls'][0]
    return dict(card_id=c['id'], card=cardpath, sku=sku, option=option or (s['values'] if s else None), role=role,
                image=img, name=c['name'], dims=c.get('dimensions_cm'), texture=c.get('texture'), card_hex=c.get('colors', {}).get('dominant_hex'))
V = []
lw = json.load(open(R + 'assets/renders/living-room/warm-modern/fb13-2026-11-25/layers/manifest-wheel.json'))['cushions']['wheel']
for k in lw['order']:
    ps = []
    for p in lw['sets'][k]['products']:
        sku = p['sku'] or (p.get('sku_candidates') or [None])[0]
        q = prod(p['card'], sku, p['role'], p['option'])
        if not p['sku']: q['sku'] = None; q['sku_candidates'] = p.get('sku_candidates'); q['sku_image_from'] = sku
        ps.append(q)
    V.append(dict(room='living-room', slot='cushions', variant='set-' + k, default=lw['sets'][k]['default'], products=ps))
HT = 'data/products/bath/hand-towel/hand-towel-aliexpress-pure-linen-towel-38x55.json'
TT = 'data/products/dining/tea-towel/tea-towel-cj-waffle-cotton-beige-45x65-pair.json'
V += [dict(room='bath', slot='hand-towel', variant='hand-towel-aliexpress-pure-linen-towel-38x55-caramel', default=True, products=[prod(HT, '12000059652536005', 'hand towel 38 x 55')]),
      dict(room='bath', slot='hand-towel', variant='hand-towel-aliexpress-pure-linen-towel-38x55-linen', products=[prod(HT, '12000059652334993', 'hand towel 38 x 55')]),
      dict(room='bath', slot='hand-towel', variant='tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki', products=[prod(TT, 'CJYD223761707GT', 'towel 45 x 65')])]
PP = 'data/products/pendant/pendant-cj-silk-ribbed-pumpkin-40.json'
PB = 'data/products/pendant/pendant-cj-scalloped-pleated-bell.json'
V += [dict(room='dining', slot='dining-pendant', variant='pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light', default=True, products=[prod(PP, 'CJYD304604003CX', 'pendant 50 cm')]),
      dict(room='dining', slot='dining-pendant', variant='pendant-cj-scalloped-pleated-bell-45', products=[prod(PB, None, 'pendant 45 cm', {'variant': 'Warm Light Beige 45 cm', 'sku_note': 'CJYD272605101AZ (card notes)'})])]
V[-1]['products'][0]['sku'] = 'CJYD272605101AZ'
BS = 'data/products/kids/bedspread/bedspread-cj-waffle-gauze-fringe-150x200.json'
kid = json.load(open(R + 'data/slots/kids.json'))['by_style']['warm-modern']['wheel']
for room, key in (('boy', 'K-boy'), ('girl', 'K-girl')):
    for o in kid[key]['options']:
        V.append(dict(room=room, slot='bedspread', variant=o['product'], default=bool(o.get('default')), products=[prod(BS, o['sku'], 'bedspread 150 x 200')]))
SC = 'data/products/sofa-cover/sofa-cover-cj-cotton-muslin-fringe.json'
for i, (c, s) in enumerate((('pecan', 'CJYD205807508HS'), ('flax-brown', 'CJYD205807538LO'), ('clay', 'CJYD205807510JQ'))):
    V.append(dict(room='master', slot='throw', variant=f'sofa-cover-cj-cotton-muslin-fringe-{c}-150x200', default=i == 0, products=[prod(SC, s, 'throw 150 x 200')]))
FA = 'data/products/work/framed-art/framed-art-aliexpress-misty-landscape-386242-work.json'
for i, (c, s) in enumerate((('08', '12000038963447938'), ('01', '12000038963447931'), ('02', '12000038963447932'))):
    V.append(dict(room='work', slot='framed-art', variant=f'framed-art-aliexpress-misty-landscape-386242-work-{c}-30x40', default=i == 0, products=[prod(FA, s, 'print 30 x 40, no frame')]))
for v in V:
    v.setdefault('default', False)
    v['out'] = f"assets/renders/wheel-studio/warm-modern/{v['room']}/{v['slot']}/{v['variant']}.png"
json.dump(V, open(OUT + '/plan.json', 'w'), indent=1, ensure_ascii=False)
print(len(V), 'variants'); [print(' ', v['room'], v['slot'], v['variant'], [p['sku'] for p in v['products']]) for v in V]
