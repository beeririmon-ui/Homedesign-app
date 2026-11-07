"""qa-agent, 2026-11-07 (interface track S1/S2): the frame gate and "yes"-only dots, recomputed from the QA records
independently of site/tools/lib/qa-frames.ts, against the built pages.

    STORY_JSON=<the data file as built> python3 qa/reports/2026-11-07-site-track-qa-s1-s2/tools/gate_check.py
"""
import json, re, os, sys
REPO = '/home/user/homedesign-app'
os.chdir(REPO)
story = json.load(open(os.environ.get('STORY_JSON', 'data/story/story.json')))
recs = [json.load(open(p)) for p in story['qa_records']]
old, new = recs[0], recs[1]['part1']['frames']
def state_rows(key):
    if key in new:
        f = new[key]
        _, rows = state_rows(os.path.basename(f['against'])[:-4])
        rows = [dict(r) for r in rows]
        for ch in f.get('rows_changed', []):
            for r in rows:
                if r['card'].split(' ')[0] == ch['card'].split(' ')[0]:
                    r['faithful'] = ch['faithful']
        return f['state'], rows
    t = old['final_test'].get(key)
    st = 'final_test' if t and t.startswith('ready') else 'almost' if t and t.startswith('almost') else 'not_yet'
    return st, old['frames'].get(key, {}).get('rows', [])
bad, dots, out = [], 0, {}
for key, pair in story['pairs'].items():
    room, style = key.split('/')
    h = open(f'site/web/dist/story/{room}/{style}/index.html', encoding='utf8').read()
    data = json.loads(re.search(r'<script type="application/json" id="st-data">\s*(.*?)\s*</script>', h, re.S).group(1))
    shown = {f['id'] for f in data['frames']}
    page = out[key] = {'frames': []}
    for f in pair['frames']:
        st, rows = state_rows(f['qa_key'])
        expect = st in story['allowed_states'] and bool(f.get('points'))
        page['frames'].append({'id': f['id'], 'qa_key': f['qa_key'], 'state': st, 'on_page': f['id'] in shown, 'expected': expect})
        if expect != (f['id'] in shown):
            bad.append([key, f['id'], 'frame gate'])
        for iid, it in data['items'].items():
            if it['frame'] != f['id']:
                continue
            v = next((r['faithful'] for r in rows if r['card'].split(' ')[0] == it['product']), 'NOT IN QA')
            dots += it['dot']
            if bool(re.match(r'^yes\b', v)) != it['dot']:
                bad.append([key, iid, it['product'], v, it['dot']])
    if not shown:
        page['typographic_images'] = sorted(set(re.findall(r'/media/story/[^"?, ]+', h)))
        page['frame_media_served'] = os.path.isdir(f'site/web/dist/media/story/{room}/{style}')
json.dump({'pages': out, 'dots': dots, 'mismatches': bad}, open('qa/reports/2026-11-07-site-track-qa-s1-s2/data/gate-check.json', 'w'), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(k, v['frames'], v.get('typographic_images', ''), v.get('frame_media_served', ''))
print('dots', dots, 'mismatches', bad)
