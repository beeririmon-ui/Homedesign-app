#!/usr/bin/env python3
"""Prepare one Phase B job: the prompt body (header stripped), the refs in header order as var2 URLs, the char count, and the clay
to send (round-3 PNG + sha256). Prints a JSON the render-agent passes to var2_create_image. 0 tokens.
usage: python3 prep_job.py <job id>"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
J = json.load(open(os.path.join(HERE, 'jobs.json')))
idx = json.load(open(os.path.join(HERE, 'refs', 'index.json')))
jid = sys.argv[1]
job = next(j for j in J['jobs'] if j['id'] == jid)
txt = open(os.path.join(REPO, 'assets', 'prompts', 'recipe-v5.nordic', job['prompt_file']), encoding='utf-8').read()
body = [l for l in txt.split('\n') if not l.startswith('#')]
while body and body[0].strip() == '':
    body.pop(0)
prompt = '\n'.join(body)
refs = [idx['refs'][k]['var2_url'] for k in idx['frames'][job['frame']] if idx['refs'].get(k, {}).get('var2_url')]
clay_local = {'M0': 'assets/blockout/living-room/m0-clay-4k.png'}.get(job['frame'], f"assets/blockout/house/framing/round3/{job['frame']}.png")
p = os.path.join(REPO, clay_local)
sha = hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else None
out = dict(id=jid, frame=job['frame'], prompt_chars=len(prompt), ascii=prompt.isascii(), refs=len(refs), clay=clay_local, clay_sha256=sha,
           clay_var2_url=J['clay'].get(job['frame'], {}).get('var2_url'), image_refs=refs, prompt=prompt)
json.dump(out, open(os.path.join(HERE, f'job-{jid}.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('prompt', 'image_refs')}))
print('refs:', len(refs), '| missing refs:', [k for k in idx['frames'][job['frame']] if not idx['refs'].get(k, {}).get('var2_url')])
