#!/usr/bin/env python3
"""Upload (signed PUT, verified by download) and register a round-4 clay or a frame reference. 0 tokens. Token never printed.
  python3 register_v7.py clay <frame> <local repo-relative path> <object name> <token>
  python3 register_v7.py ref <frame> <1-based position in refs/index-v7.json frames[frame]> <local path> <object name> <token>
  python3 register_v7.py pose-ref <key> <local path> <object name> <token>            (stored under refs/index-v7.json frame_refs[key])"""
import hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
B = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/'; P = 'generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'


def put(local, name, tok):
    ct = "image/png" if local.endswith(".png") else "image/jpeg"
    sha = hashlib.sha256(open(local, 'rb').read()).hexdigest()
    r = subprocess.run(['curl', '-sS', '-X', 'PUT', '--data-binary', '@' + local, '-H', 'Content-Type: ' + ct, '-o', '/dev/null', '-w', '%{http_code}',
                        B + 'upload/sign/' + P + name + '?token=' + tok], capture_output=True, text=True)
    tmp = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/put-back.bin'
    r2 = subprocess.run(['curl', '-sS', '-o', tmp, '-w', '%{http_code}', B + 'public/' + P + name], capture_output=True, text=True)
    sha2 = hashlib.sha256(open(tmp, 'rb').read()).hexdigest()
    return dict(sha256=sha, var2_url=B + 'public/' + P + name, put=r.stdout.strip(), verified=bool(sha == sha2), size=os.path.getsize(local))


kind = sys.argv[1]
if kind == 'clay':
    frame, local, name, tok = sys.argv[2:6]
    info = put(os.path.join(REPO, local), name, tok)
    J = json.load(open(os.path.join(HERE, 'jobs.json')))
    J['clay'][frame] = dict(local=local, **info)
    json.dump(J, open(os.path.join(HERE, 'jobs.json'), 'w'), indent=1, ensure_ascii=False)
elif kind == 'ref':
    frame, pos, local, name, tok = sys.argv[2:7]
    info = put(os.path.join(REPO, local) if not local.startswith('/') else local, name, tok)
    I = json.load(open(os.path.join(HERE, 'refs', 'index-v7.json')))
    e = I['frames'][frame][int(pos) - 1]
    e.update(file=local, var2_url=info['var2_url'], sha256=info['sha256'], verified=info['verified'])
    json.dump(I, open(os.path.join(HERE, 'refs', 'index-v7.json'), 'w'), indent=1, ensure_ascii=False)
else:
    key, local, name, tok = sys.argv[2:6]
    info = put(os.path.join(REPO, local) if not local.startswith('/') else local, name, tok)
    I = json.load(open(os.path.join(HERE, 'refs', 'index-v7.json')))
    I.setdefault('frame_refs', {})[key] = dict(file=local, **info)
    json.dump(I, open(os.path.join(HERE, 'refs', 'index-v7.json'), 'w'), indent=1, ensure_ascii=False)
print(kind, sys.argv[2], 'PUT', info['put'], 'verified', info['verified'], info['var2_url'])
