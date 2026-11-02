#!/usr/bin/env python3
"""
Prompt records and manifest entries for the v7 test (render-agent, 2026-11-02), in the shape of
assets/prompts/recipe-v5.nordic/record-template.json (as Phase B's record.py): one record per finished job,
  masters -> assets/prompts/recipe-v5.nordic/<id>.json, poses -> assets/prompts/poses-v7.nordic/<id>.json,
and assets/manifest.json entries for the normalised raw, the graded file and (overscan stills) the 16:9 frame and the os6 crop.
Idempotent: existing manifest ids are kept. 0 tokens.
  python3 record_v7.py [--dry]
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DRY = '--dry' in sys.argv
J = json.load(open(os.path.join(HERE, 'jobs.json')))
tpl = json.load(open(os.path.join(REPO, 'assets', 'prompts', 'recipe-v5.nordic', 'record-template.json')))
man_path = os.path.join(REPO, 'assets', 'manifest.json')
man = json.load(open(man_path))
have = {a['id'] for a in man['assets']}
for j in J['jobs']:
    if j.get('status') != 'done':
        continue
    od = j['out_dir']
    meas = json.load(open(os.path.join(REPO, od, j['id'] + '-measurements.json')))
    prep = json.load(open(os.path.join(HERE, f"job-{j['id']}.json")))
    a = prep['args']
    clay = J['clay'][j['frame']]
    pose = j['kind'] == 'pose'
    rec = dict(tpl)
    rec.update({
        'asset_id': j['id'], 'room': j['room'], 'style': 'nordic', 'frame': j['frame'],
        'recipe': 'B (gpt-image-2-5 sunburst), v7 wow pass' + (' - transition pose, route R' if pose else ''),
        'stage': 'Nordic walk-through test (briefs/nordic-house-render-2026-10-24.md 8); 2K, not a site asset; gate 2 applies to the finals',
        'date': j.get('date', '2026-11-02'), 'tool': 'var2 MCP var2_create_image', 'model': a['model'], 'type': a['type'], 'resolution': a['resolution'],
        'quality': a['quality'], 'aspect_ratio': a['aspect_ratio'], 'returned_size_px': meas['returned_size_px'], 'seed': None,
        'seed_note': 'model exposes no seed; a regenerate is a new sample',
        'input_image': {'local': clay['local'], 'sha256': clay['sha256'], 'var2_url': clay['var2_url'],
                        'upload': 'var2_request_upload + PUT (curl); downloaded back, sha256 identical' if clay.get('verified') else 'var2_request_upload + PUT'},
        'image_refs': [{'n': i + 1, 'var2_url': u} for i, u in enumerate(a['image_refs'])],
        'image_refs_source': ('assets/renders/house-nordic-v7-2026-11-02/poses.json + refs/index-v7.json' if pose else
                              f"assets/renders/house-nordic-v7-2026-11-02/refs/index-v7.json frames[{j['frame']}] (the order of the prompt header)"),
        'negative_prompt': None, 'negative_note': 'no negative field; the prohibitions are the last paragraph of the prompt',
        'prompt': a['prompt'], 'prompt_source': j['prompt_file'], 'prompt_chars': len(a['prompt']), 'prompt_deviation': prep.get('prompt_deviation'),
        'idempotency_key': a['idempotency_key'],
        'var2': {'placeholder_id': j.get('placeholder_id'), 'task_id': j.get('task_id'), 'result_url': j.get('result_url'),
                 'share_url': ('https://www.var2.ai/image/' + j['placeholder_id']) if j.get('placeholder_id') else None},
        'credits_estimated': 600, 'credits': j.get('credits'), 'attempt': j['attempt'],
        'attempt_note': j.get('attempt_note', 'first and only attempt'),
        'normalised_16_9': meas['resize_16_9'], 'overscan': j.get('overscan'),
        'clay_lock': {'method': meas['clay_lock_note'], 'regions': meas['clay_lock'], 'auto_worst_abs_shift': meas['clay_lock_worst_abs_shift'],
                      'auto_worst_abs_shift_strong_peaks': meas['clay_lock_worst_abs_shift_strong_peaks'], 'verdict': j.get('lock')},
        'sofa_width_check': meas.get('sofa_width_check'),
        'product_check': {'rule': meas['product_box_rule'], 'overlay': od + j['id'] + '-boxes.png'},
        'grade': {'applied': True, 'script': 'assets/renders/house-nordic-v7-2026-11-02/process_v7.py', 'params': meas['grade'],
                  'output': od + j['id'] + '-graded.png',
                  'rule': 'docs/render-recipe-nordic-2026-10-24.md 2.6 (the Bible grade): WB on the hero-wall patch, exposure capped +-0.2 stop, chroma -10%, roll-off from L 94, S curve 0.12, black point to L 12.5 only if below 12, no grain, no vignette'},
        'measurements': od + j['id'] + '-measurements.json', 'self_check_verdict': j.get('verdict', ''),
        'output': od + j['id'] + '.png', 'output_raw': od + 'raw/' + j['id'] + '.' + j.get('raw_ext', 'png'), 'on_sheet': bool(j.get('sheet'))})
    if pose:
        rec['masters_as_references'] = j.get('masters')
    rdir = os.path.join(REPO, 'assets', 'prompts', 'poses-v7.nordic' if pose else 'recipe-v5.nordic')
    if not DRY:
        json.dump(rec, open(os.path.join(rdir, j['id'] + '.json'), 'w'), indent=1, ensure_ascii=False)
    status = ('v7 test still, ' + ('ON the sheet' if j.get('sheet') else 'NOT on the sheet (rejected attempt, kept for the record)') +
              '; self-checked by the render-agent, awaiting qa-agent / master-designer / user; not for site')
    outs = [('', od + j['id'] + '.png', 'raw-normalised'), ('-graded', od + j['id'] + '-graded.png', 'graded')]
    if (j.get('overscan') or {}).get('on') and os.path.exists(os.path.join(REPO, od, j['id'] + '-frame.png')):
        outs += [('-frame', od + j['id'] + '-frame.png', 'graded 16:9 frame (centre crop of the overscan canvas)'),
                 ('-os6', od + j['id'] + '-graded-os6.png', 'graded, frame width + 3% height top and bottom (motion-agent)')]
    for suf, path, kind in outs:
        aid = ('v7-pose-' if pose else 'v7-') + j['id'] + suf
        if aid in have:
            continue
        man['assets'].append({'id': aid, 'path': path, 'room': j['room'], 'style': 'nordic', 'kind': ('v7-pose-' if pose else 'v7-frame-') + kind,
                              'frame': j['frame'], 'recipe': 'B v7', 'model': a['model'], 'attempt': j['attempt'], 'status': status,
                              'clay': clay['local'], 'prompt_record': os.path.relpath(os.path.join(rdir, j['id'] + '.json'), REPO), 'created': '2026-11-02'})
        have.add(aid)
    print('record', j['id'], '| prompt', rec['prompt_chars'], '| refs', len(a['image_refs']), '| sheet', bool(j.get('sheet')))
if not DRY:
    json.dump(man, open(man_path, 'w'), indent=1, ensure_ascii=False)
print('manifest assets:', len(man['assets']))
