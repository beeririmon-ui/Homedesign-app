#!/usr/bin/env python3
"""PUT reference crops to signed var2 upload URLs (from var2_request_upload) and record the public URLs. 0 tokens.
usage: python3 put.py '<json: {"<file index>": ["<object name>", "<token>"], ...}>'"""
import json, os, subprocess, sys
R = '/home/user/homedesign-app/'
D = R + 'assets/renders/house-nordic-2026-10-25/refs/'
idx = json.load(open(D + 'index.json'))
files = sorted(set(v['file'] for v in idx['refs'].values()))
B = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/'
P = 'generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'
up = json.load(open(D + 'uploads.json')) if os.path.exists(D + 'uploads.json') else {}
batch = json.loads(sys.argv[1])
for n, (name, tok) in batch.items():
    f = files[int(n)]
    url = B + 'upload/sign/' + P + name + '?token=' + tok
    pub = B + 'public/' + P + name
    r = subprocess.run(['curl', '-sS', '-X', 'PUT', '--data-binary', '@' + R + f, '-H', 'Content-Type: image/jpeg', '-o', '/dev/null', '-w', '%{http_code}', url], capture_output=True, text=True)
    r2 = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code} %{size_download}', pub], capture_output=True, text=True)
    up[f] = dict(public_url=pub, put=r.stdout.strip(), get=r2.stdout.strip(), size=os.path.getsize(R + f))
    ok = r.stdout.strip() == '200' and r2.stdout.strip() == '200 %d' % os.path.getsize(R + f)
    print(n, 'OK' if ok else 'FAIL', r.stdout.strip(), r2.stdout.strip(), os.path.getsize(R + f))
json.dump(up, open(D + 'uploads.json', 'w'), indent=1)
for k, v in idx['refs'].items():
    u = up.get(v['file'])
    if u and u['put'] == '200':
        v['var2_url'] = u['public_url']
json.dump(idx, open(D + 'index.json', 'w'), indent=1, ensure_ascii=False)
print('uploaded', sum(1 for v in idx['refs'].values() if v.get('var2_url')), 'of', len(idx['refs']))
