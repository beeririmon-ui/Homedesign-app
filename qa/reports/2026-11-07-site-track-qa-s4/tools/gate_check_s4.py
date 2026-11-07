"""qa-agent, 2026-11-07 (S4): the frame gate and the dots against QA's register (the highest version), recomputed apart
from site/tools/lib/qa-frames.ts, on QA's snapshot of web/dist; and the links of a product shown in two options.

    QA_DIST=<snapshot> STORY_JSON=<git show 65f95d32:data/story/story.json> [REGISTER=<path>] python3 …/gate_check_s4.py out.json
"""
import json, os, re, sys, glob
REPO = '/home/user/homedesign-app'
DIST = os.environ['QA_DIST']
story = json.load(open(os.environ['STORY_JSON']))
regs = [(json.load(open(p)), p) for p in glob.glob(f'{REPO}/qa/reports/ged-register-*.json')]
# REGISTER: the register the build read (its log names it); else the highest version now
reg, reg_path = (json.load(open(os.environ['REGISTER'])), os.environ['REGISTER']) if os.environ.get('REGISTER') else max(regs, key=lambda r: r[0]['version'])
def row_of(rows, card, values):
    rs = [r for r in rows if r['card_id'] == card]
    exact = [r for r in rs if isinstance(r.get('option'), dict) and all((values or {}).get(k) == v for k, v in r['option'].items())]
    return (exact or [r for r in rs if not isinstance(r.get('option'), dict)] or rs or [None])[0]
out = {'register': reg_path.replace(REPO + '/', ''), 'version': reg['version'], 'pages': {}, 'mismatches': [], 'two_options': []}
for key, pair in story['pairs'].items():
    room, style = key.split('/')
    h = open(f'{DIST}/story/{room}/{style}/index.html', encoding='utf8').read()
    d = json.loads(re.search(r'<script type="application/json" id="st-data">\s*(.*?)\s*</script>', h, re.S).group(1))
    shown = {f['id'] for f in d['frames']}
    pg = out['pages'][key] = []
    for f in pair['frames']:
        fr = reg['frames'].get(f['qa_key'])
        state = fr['state'] if fr else ('superseded' if f['qa_key'] in reg.get('superseded_by', {}) else 'not_in_register')
        expect = state in story['allowed_states'] and bool(f.get('points'))
        pg.append({'frame': f['id'], 'qa_key': f['qa_key'], 'state': state, 'on_page': f['id'] in shown, 'expected': expect})
        if expect != (f['id'] in shown):
            out['mismatches'].append([key, f['id'], 'frame gate'])
        if f['id'] not in shown:
            continue
        for iid, it in d['items'].items():
            if it['frame'] != f['id']:
                continue
            r = row_of(fr['rows'], it['product'], it.get('values'))
            want = bool(r) and r['dot'] == 'yes'  # no close-ups in the register yet: closeup_only stays off
            if want != it['dot']:
                out['mismatches'].append([key, iid, it['product'], r and r['dot'], it['dot']])
    # a product shown in two options in one frame: each dot's link names its option when it is not the page's
    by = {}
    for iid, it in d['items'].items():
        by.setdefault(it['product'], []).append(it)
    for p, its in by.items():
        if len({json.dumps(x.get('values'), sort_keys=True) for x in its}) > 1:
            out['two_options'].append({'page': key, 'product': p, 'links': [(x['id'], x.get('values'), x['href']) for x in its]})
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ('register', 'version', 'mismatches', 'two_options')}, ensure_ascii=False, indent=1))
for k, v in out['pages'].items():
    print(k, v)
