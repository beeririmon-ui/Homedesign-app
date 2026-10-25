#!/usr/bin/env python3
"""PUT a round-3 clay PNG to its signed var2 upload URL, download it back, compare sha256, record in jobs.json['clay'][frame]. 0 tokens.
usage: python3 put_clay.py <frame> <local clay path (repo-relative)> <object name> <token>"""
import hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
frame, local, name, tok = sys.argv[1:5]
B = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/'; P = 'generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'
url = B + 'upload/sign/' + P + name + '?token=' + tok; pub = B + 'public/' + P + name
p = os.path.join(REPO, local)
sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
r = subprocess.run(['curl', '-sS', '-X', 'PUT', '--data-binary', '@' + p, '-H', 'Content-Type: image/png', '-o', '/dev/null', '-w', '%{http_code}', url], capture_output=True, text=True)
tmp = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/clay-back.png'
r2 = subprocess.run(['curl', '-sS', '-o', tmp, '-w', '%{http_code}', pub], capture_output=True, text=True)
sha2 = hashlib.sha256(open(tmp, 'rb').read()).hexdigest() if os.path.exists(tmp) else None
J = json.load(open(os.path.join(HERE, 'jobs.json')))
J['clay'][frame] = dict(local=local, sha256=sha, var2_url=pub, put=r.stdout.strip(), verified=bool(sha == sha2), size=os.path.getsize(p))
json.dump(J, open(os.path.join(HERE, 'jobs.json'), 'w'), indent=1, ensure_ascii=False)
print(frame, 'PUT', r.stdout.strip(), 'GET', r2.stdout.strip(), 'sha identical', sha == sha2, 'size', os.path.getsize(p))
