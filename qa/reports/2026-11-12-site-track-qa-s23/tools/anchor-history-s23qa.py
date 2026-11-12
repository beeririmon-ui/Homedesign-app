# qa-agent S23 (ת85, the gate's data): does site/tools/price-anchors.json name the SKU each studio price was set for?
# The anchor list takes the card's default SKU at 7b42ddc1 (QA S21). That holds only if the default did not move between
# the day the price was set and 7b42ddc1. For every anchored card: the price's day (the date in retail_src, else the first
# commit of data/economics/products.json that holds this exact retail_ils+retail_src), then every default_sku the card
# had in git from that day to 7b42ddc1 (renames followed). Run from the repo root with python3 -I; writes JSON to argv[1].
import json, subprocess, sys, re
COMMIT = sys.argv[2] if len(sys.argv) > 2 else 'bd5ac86a'
BASE = '7b42ddc1'
def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True, check=True).stdout
def show(c, p):
    try:
        return json.loads(git('show', f'{c}:{p}'))
    except Exception:
        return None
anch = json.loads(git('show', f'{COMMIT}:site/tools/price-anchors.json'))['anchors']
base_date = git('show', '-s', '--format=%aI', BASE).strip()
econ_commits = git('log', '--reverse', '--format=%h %aI', COMMIT, '--', 'data/economics/products.json').split('\n')
econ_hist = []
for line in filter(None, econ_commits):
    h, d = line.split()
    e = (show(h, 'data/economics/products.json') or {}).get('products', {})
    econ_hist.append((h, d, e))
# where each card lives now
paths = {}
for p in git('ls-tree', '-r', '--name-only', COMMIT, 'data/products').split('\n'):
    if p.endswith('.json'):
        c = show(COMMIT, p)
        if isinstance(c, dict) and c.get('id'):
            paths[c['id']] = p
out = []
for pid, a in sorted(anch.items()):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', a.get('retail_src') or '')
    first = next(((h, d) for h, d, e in econ_hist if (e.get(pid) or {}).get('retail_ils') == a['retail_ils'] and (e.get(pid) or {}).get('retail_src') == a['retail_src']), None)
    day = min([x for x in [m.group(1) if m else None, first[1][:10] if first else None] if x])
    p = paths.get(pid)
    hist = []
    if p:
        log = git('log', '--follow', '--format=@@%h %aI', '--name-only', COMMIT, '--', p)
        cur = None
        for line in log.split('\n'):
            if line.startswith('@@'):
                cur = line[2:].split()
            elif line.strip() and cur:
                c = show(cur[0], line.strip())
                hist.append((cur[1], cur[0], ((c or {}).get('options') or {}).get('default_sku')))
                cur = None
    hist.sort()
    # the default when the price was set (the last commit on or before its day), and every default since, up to BASE
    before = [x for x in hist if x[0][:10] <= day]
    at_day = before[-1][2] if before else (hist[0][2] if hist else None)
    window = sorted({x[2] for x in hist if day <= x[0][:10] and x[0] <= base_date and x[2]})
    at_base = [x for x in hist if x[0] <= base_date]
    at_base = at_base[-1][2] if at_base else None
    now = hist[-1][2] if hist else None
    out.append({'id': pid, 'anchor_sku': a['sku'], 'from': a.get('from'), 'retail_ils': a['retail_ils'], 'retail_src': a['retail_src'], 'price_day': day,
                'default_at_price_day': at_day, 'defaults_price_day_to_base': window, 'default_at_base': at_base, 'default_now': now,
                'anchor_is_default_at_price_day': a['sku'] == at_day, 'moved_between_price_and_base': len(window) > 1 or (at_day is not None and at_base is not None and at_day != at_base)})
bad = [o for o in out if not o['anchor_is_default_at_price_day'] or o['moved_between_price_and_base']]
json.dump({'commit': COMMIT, 'anchors': len(out), 'flagged': bad, 'all': out}, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(json.dumps({'anchors': len(out), 'flagged': len(bad), 'ids': [(o['id'], o['anchor_sku'], o['default_at_price_day'], o['defaults_price_day_to_base'], o['default_now'], o['price_day']) for o in bad]}, ensure_ascii=False, indent=0))
