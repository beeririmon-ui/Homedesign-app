# Builds assets/prompts/recipe-v5.nordic/<id>.json (shape of record-template.json) from jobs.json + <id>-measurements.json, and appends to assets/manifest.json.
import json, os, sys
R = '/home/user/homedesign-app/'
J = json.load(open(R + 'assets/renders/living-room/nordic/recipe-v5/jobs.json'))
tpl = json.load(open(R + 'assets/prompts/recipe-v5.nordic/record-template.json'))
man = json.load(open(R + 'assets/manifest.json'))
have = {a['id'] for a in man['assets']}
for j in J['jobs']:
    out_dir = 'assets/renders/%s/nordic/recipe-v5/' % j['room']
    meas = json.load(open(R + out_dir + j['id'] + '-measurements.json'))
    txt = open(R + 'assets/prompts/recipe-v5.nordic/' + j['prompt_file'], encoding='utf-8').read()
    if j['prompt_file'] == 'm0-A-styled.txt':
        body = [l for l in txt.split('\n') if not l.startswith('#')]
        while body and body[0].strip() == '': body.pop(0)
        prompt = '\n'.join(body); dev = 'lines starting with # stripped as the file header instructs (3,771 chars sent of 5,861 in the file)'
    else:
        prompt = txt; dev = 'none: sent as the file text'
    clay = J['clay'][j['frame']]
    rec = dict(tpl)
    rec.update({'asset_id': j['id'] + ('' if j['attempt'] == 1 else '-retake'), 'room': j['room'], 'style': 'nordic', 'frame': j['frame'], 'recipe': j['recipe'],
        'stage': 'recipe-v5 draft 2K (Phase A, gate 1)', 'date': '2026-10-24', 'tool': 'var2 MCP var2_create_image', 'model': j['model'], 'type': 'image-to-image',
        'resolution': '2K', 'quality': j['quality'], 'aspect_ratio': '16:9', 'returned_size_px': meas['returned_size_px'], 'seed': None,
        'seed_note': 'model exposes no seed; a regenerate is a new sample',
        'input_image': {'local': clay['local'], 'sha256': clay['sha256'], 'var2_url': clay['var2_url'], 'upload': 'var2_request_upload + PUT; downloaded back, sha256 identical'},
        'image_refs': [], 'negative_prompt': None, 'negative_note': 'no negative field; the prohibitions are the last paragraph of the prompt',
        'prompt': prompt, 'prompt_source': 'assets/prompts/recipe-v5.nordic/' + j['prompt_file'] + ' (master-designer, 2026-10-24)', 'prompt_chars': len(prompt),
        'prompt_deviation': dev, 'idempotency_key': j['idempotency_key'],
        'var2': {'placeholder_id': j['placeholder_id'], 'task_id': j['task_id'], 'result_url': j['result_url'], 'share_url': 'https://www.var2.ai/image/' + j['placeholder_id']},
        'credits_estimated': j['credits_estimated'], 'credits': j['credits'], 'attempt': j['attempt'],
        'attempt_note': j.get('attempt_note', 'first and only attempt' if j['attempt'] == 1 else 'second attempt: the first broke the clay lock'),
        'normalised_16_9': meas['resize_16_9'],
        'clay_lock': {'method': 'phase correlation of gradient maps vs the clay resized to the output, per region (du/dv as frame fractions); peaks below ~0.03 are unreliable, so the verdict is visual (clay-edge overlay) with the numbers as support',
                      'regions': meas['clay_lock'], 'auto_worst_abs_shift': meas['clay_lock_worst_abs_shift']},
        'grade': {'applied': True, 'script': out_dir + 'process.py', 'params': meas['grade'], 'output': out_dir + j['id'] + '-graded.png',
                  'rule': 'docs/render-recipe-nordic-2026-10-24.md 2.6: WB on the hero-wall patch, exposure capped +-0.2 stop, chroma -10%, roll-off from L 94, S curve 0.12, black point to L 12.5 only if below 12, no grain, no vignette'},
        'measurements': out_dir + j['id'] + '-measurements.json', 'self_check_verdict': j['verdict'],
        'output': out_dir + j['id'] + '.png', 'output_raw': out_dir + 'raw/' + j['id'] + '.' + j['raw_ext']})
    rid = j['id']
    json.dump(rec, open(R + 'assets/prompts/recipe-v5.nordic/' + rid + '.json', 'w'), indent=1, ensure_ascii=False)
    for suffix, path, kind in [('', out_dir + rid + '.png', 'recipe-v5-draft'), ('-graded', out_dir + rid + '-graded.png', 'recipe-v5-draft-graded')]:
        aid = 'recipe-v5-' + rid + suffix
        if aid in have: continue
        man['assets'].append({'id': aid, 'path': path, 'room': j['room'], 'style': 'nordic', 'kind': kind, 'frame': j['frame'], 'recipe': j['recipe'], 'model': j['model'],
            'status': 'draft for gate 1 (recipe choice); self-checked, awaiting qa-agent / master-designer / user (not for site)',
            'prompt_record': 'assets/prompts/recipe-v5.nordic/' + rid + '.json', 'created': '2026-10-24'})
        have.add(aid)
    print('record', rid)
json.dump(man, open(R + 'assets/manifest.json', 'w'), indent=1, ensure_ascii=False)
print('manifest assets:', len(man['assets']))
