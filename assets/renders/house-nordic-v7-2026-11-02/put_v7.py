#!/usr/bin/env python3
"""PUT a local file to its signed var2 upload URL (from var2_request_upload), download it back, compare sha256, print the public URL.
0 tokens. The upload token is passed on the command line and never printed.
usage: python3 put_v7.py <local path> <object name, e.g. 5d42e9bc-....jpg> <token> [content-type]"""
import hashlib, os, subprocess, sys
local, name, tok = sys.argv[1:4]
ct = sys.argv[4] if len(sys.argv) > 4 else ("image/png" if local.endswith(".png") else "image/jpeg")
B = 'https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/'; P = 'generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/'
url = B + 'upload/sign/' + P + name + '?token=' + tok
pub = B + 'public/' + P + name
sha = hashlib.sha256(open(local, 'rb').read()).hexdigest()
r = subprocess.run(['curl', '-sS', '-X', 'PUT', '--data-binary', '@' + local, '-H', 'Content-Type: ' + ct, '-o', '/dev/null', '-w', '%{http_code}', url], capture_output=True, text=True)
tmp = '/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/put-back.bin'
r2 = subprocess.run(['curl', '-sS', '-o', tmp, '-w', '%{http_code}', pub], capture_output=True, text=True)
sha2 = hashlib.sha256(open(tmp, 'rb').read()).hexdigest() if os.path.exists(tmp) else None
print(os.path.basename(local), 'PUT', r.stdout.strip(), 'GET', r2.stdout.strip(), 'verified', sha == sha2, pub)
