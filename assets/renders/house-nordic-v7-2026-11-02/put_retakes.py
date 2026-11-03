#!/usr/bin/env python3
"""PUT a local file to its signed var2 upload URL (var2_request_upload), download it back from the public URL, compare sha256,
and record the public URL in refs/index-retakes-2026-11-03.json under <key> (or in jobs-retakes-2026-11-03.json clay[<key>] with
--clay). 0 tokens. The signed URL (with its token) is never printed.
usage: python3 put_retakes.py <local> <upload_url> <public_url> <key> [--clay]"""
import hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
local, up, pub, key = sys.argv[1:5]
clay = '--clay' in sys.argv
ct = 'image/png' if local.lower().endswith('.png') else 'image/jpeg'
sha = hashlib.sha256(open(local, 'rb').read()).hexdigest()
r = subprocess.run(['curl', '-sS', '-X', 'PUT', '--data-binary', '@' + local, '-H', 'Content-Type: ' + ct, '-o', '/dev/null', '-w', '%{http_code}', up], capture_output=True, text=True)
tmp = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/put-back.bin'
r2 = subprocess.run(['curl', '-sS', '-L', '--max-time', '120', '-o', tmp, '-w', '%{http_code}', pub], capture_output=True, text=True)
sha2 = hashlib.sha256(open(tmp, 'rb').read()).hexdigest() if os.path.exists(tmp) else None
ok = (r.stdout.strip() == '200' and sha == sha2)
rec = dict(var2_url=pub, put=r.stdout.strip(), get=r2.stdout.strip(), verified=ok, size=os.path.getsize(local), sha256=sha)
if clay:
    p = os.path.join(HERE, 'jobs-retakes-2026-11-03.json')
    J = json.load(open(p)) if os.path.exists(p) else {'clay': {}, 'jobs': []}
    J.setdefault('clay', {})[key] = dict(local=os.path.relpath(local, REPO), **rec)
    json.dump(J, open(p, 'w'), indent=1, ensure_ascii=False)
else:
    p = os.path.join(HERE, 'refs', 'index-retakes-2026-11-03.json')
    idx = json.load(open(p))
    idx['refs'][key].update(rec)
    json.dump(idx, open(p, 'w'), indent=1, ensure_ascii=False)
print(key, os.path.basename(local), 'PUT', r.stdout.strip(), 'GET', r2.stdout.strip(), 'verified', ok)
