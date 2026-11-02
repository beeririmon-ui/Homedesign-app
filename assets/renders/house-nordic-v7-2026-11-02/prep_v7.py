#!/usr/bin/env python3
"""Prepare one v7 job (frame or pose): the prompt body (# header stripped), the references in header order as var2 URLs, the char
count, the round-4 clay (local + sha256 + var2 URL). Writes job-<id>.json with the exact var2_create_image arguments. 0 tokens.
usage: python3 prep_v7.py <job id>"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
J = json.load(open(os.path.join(HERE, 'jobs.json')))
idx = json.load(open(os.path.join(HERE, 'refs', 'index-v7.json')))
jid = sys.argv[1]
job = next(j for j in J['jobs'] if j['id'] == jid)
txt = open(os.path.join(REPO, job['prompt_file']), encoding='utf-8').read()
body = [l for l in txt.split('\n') if not l.startswith('#')]
while body and body[0].strip() == '':
    body.pop(0)
while body and body[-1].strip() == '':
    body.pop()
prompt = '\n'.join(body)
if job['kind'] == 'master':
    refs = [r['var2_url'] for r in idx['frames'][job['frame']]]
else:
    refs = list(job['refs'])
missing = [i + 1 for i, r in enumerate(refs) if not r]
clay = J['clay'].get(job['frame'], {})
p = os.path.join(REPO, clay.get('local', ''))
sha = hashlib.sha256(open(p, 'rb').read()).hexdigest() if clay.get('local') and os.path.exists(p) else None
args = dict(model='gpt-image-2-5', type='image-to-image', quality='sunburst', resolution='2K', aspect_ratio='16:9',
            image_url=clay.get('var2_url'), image_refs=refs, prompt=prompt, idempotency_key=job['idempotency_key'])
out = dict(id=jid, frame=job['frame'], prompt_chars=len(prompt), ascii=prompt.isascii(), refs=len(refs), missing_refs=missing,
           clay=clay.get('local'), clay_sha256=sha, clay_sha_matches_upload=(sha == clay.get('sha256')), args=args)
json.dump(out, open(os.path.join(HERE, f'job-{jid}.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != 'args'}))
