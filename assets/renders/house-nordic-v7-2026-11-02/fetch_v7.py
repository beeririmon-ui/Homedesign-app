#!/usr/bin/env python3
"""Download a finished var2 image (result URL) to the job's raw path and run process_v7.py on it. 0 tokens.
usage: python3 fetch_v7.py <job id> <result url>"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
J = json.load(open(os.path.join(HERE, 'jobs.json')))
jid, url = sys.argv[1:3]
job = next(j for j in J['jobs'] if j['id'] == jid)
ext = os.path.splitext(url.split('?')[0])[1].lower() or '.png'
out_dir = os.path.join(REPO, job['out_dir'])
os.makedirs(os.path.join(out_dir, 'raw'), exist_ok=True)
dl = os.path.join('/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-results', jid + ext)
os.makedirs(os.path.dirname(dl), exist_ok=True)
r = subprocess.run(['curl', '-sS', '-L', '--max-time', '180', '-o', dl, '-w', '%{http_code}', url], capture_output=True, text=True)
print('GET', r.stdout.strip(), os.path.getsize(dl) if os.path.exists(dl) else None)
clay = os.path.join(REPO, J['clay'][job['frame']]['local'])
sc = os.path.join(REPO, 'assets/blockout/house/framing/round4/selfcheck.json')
subprocess.run(['python3.13', os.path.join(HERE, 'process_v7.py'), jid, dl, clay, job['frame'], out_dir, sc])
