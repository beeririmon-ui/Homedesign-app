# qa-agent S23 (ת85, the ladder half of the gate): my own reading of every option axis in a full catalog, independent of
# tools/lib/price-checks.ts: a value's size = the product of the first two numbers in its id or label (one number: that
# number squared, a diameter or a side); an axis counts when 2+ values have a size. Inverted pair: same other choices,
# smaller size, higher price. Also lists axes with values whose size I cannot read. python3 -I <catalog.full.json> <out>
import json, re, sys
d = json.load(open(sys.argv[1]))
def size(vid, label):
    for t in (label or '', vid):
        n = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', t)]
        if len(n) >= 2: return n[0] * n[1]
        if len(n) == 1: return n[0] ** 2
    return None
inv, unread = {}, {}
for p in d['products']:
    o = p.get('options') or {}
    axes = o.get('axes') or []
    rows = list(zip(o.get('v') or [], o.get('p') or []))
    for ai, a in enumerate(axes):
        vals = a['values']
        sz = [size(v[0], v[1] if len(v) > 1 else None) for v in vals]
        if sum(s is not None for s in sz) < 2: continue
        if a['id'] not in ('size', 'מידה') and not re.search(r'size|מידה|dimension', a['id'] + a.get('name_he', ''), re.I): continue
        if any(s is None for s in sz): unread[f"{p['id']}:{a['id']}"] = [v[0] for v, s in zip(vals, sz) if s is None]
        pairs = 0; worst = None
        for vx, px in rows:
            for vy, py in rows:
                if [j for i, j in enumerate(vx) if i != ai] != [j for i, j in enumerate(vy) if i != ai]: continue
                sx, sy = sz[vx[ai]], sz[vy[ai]]
                if sx is None or sy is None or not sx < sy or not px > py: continue
                pairs += 1
                if not worst or px - py > worst[1] - worst[3]: worst = (vals[vx[ai]][0], px / 100, vals[vy[ai]][0], py / 100)
        if pairs: inv[p['id']] = {'axis': a['id'], 'pairs': pairs, 'worst': worst}
json.dump({'inverted': inv, 'axes_with_unread_values': unread}, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
print(len(inv), 'products:'); [print(' ', k, v) for k, v in inv.items()]; print('unread', unread)
