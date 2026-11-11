"""qa-agent 2026-11-10 (S8-S10), v2 (a word boundary on sk-, ripgrep with file names): a secret scan of the repository that never prints or stores a secret. Three passes:
  tree     every file under the repo root: tracked, untracked and ignored (.git and node_modules skipped), by ripgrep
  history  every unique text blob reachable from any ref (rev-list --all --objects, cat-file --batch)
  commit   the history's hits whose blob is in the commit's tree
A hit is reported as file, line, rule and a masked value: its first 3 characters and its length, never the value.
Files that hold secrets by design and are ignored by git (site/api/.dev.vars) are reported by their variable names only.
Usage: python3 -I scan_secrets.py <repo> <commit> <out.json>"""
import json, re, subprocess, sys

repo, commit, out = sys.argv[1:4]
RULES = {
    'aws_access_key': r'AKIA[0-9A-Z]{16}',
    'openai_or_anthropic_key': r'\bsk-(?:proj-|ant-api\d\d-|ant-)?[A-Za-z0-9_\-]{24,}',
    'github_token': r'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}',
    'slack_token': r'xox[abprs]-[A-Za-z0-9\-]{10,}',
    'google_api_key': r'AIza[0-9A-Za-z_\-]{35}',
    'google_oauth_secret': r'GOCSPX-[A-Za-z0-9_\-]{20,}',
    'private_key_block': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----',
    'cj_api_key': r'CJ\d{4,}@api@[0-9a-fA-F]{16,}',
    'jwt': r'eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}',
    'stripe_like': r'(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}',
    'bearer_literal': r'(?i)bearer\s+[A-Za-z0-9_\-\.=]{24,}',
    'assigned_secret': r'''(?i)\b[A-Z0-9_]*(?:API_?KEY|APP_?SECRET|CLIENT_SECRET|WEBHOOK_SECRET|SECRET_KEY|ACCESS_TOKEN|REFRESH_TOKEN|AUTH_TOKEN|PASSWORD|PRIVATE_KEY)\b["']?\s*[:=]\s*["']([A-Za-z0-9+/_\-.@]{16,})["']''',
}
COMPILED = {k: re.compile(v) for k, v in RULES.items()}
BENIGN = re.compile(r'(?i)(replace|example|placeholder|not[-_]?real|dummy|test[-_]?secret|test[-_]webhook|xxx|your[-_]|changeme|fake|mock|sample|redacted|qa-dummy|0123456789|abcdef)')


def mask(v):
    return f'{v[:3]}…({len(v)})'


def scan_line(line, emit):
    for rule, rx in COMPILED.items():
        for m in rx.finditer(line[:20000]):
            val = m.group(1) if m.groups() else m.group(0)
            if BENIGN.search(line[max(0, m.start() - 40): m.end() + 40]):
                continue
            if rule == 'jwt' and len(val) < 60:
                continue
            emit(rule, val)


res = {'commit': commit, 'rules': RULES, 'passes': {}}

# 1. the tree, by ripgrep: every rule, every file (ignored ones too), no binaries
hits = []
for rule, rx in RULES.items():
    p = subprocess.run(['rg', '--no-ignore', '--hidden', '-n', '--with-filename', '--no-heading', '-g', '!.git', '-g', '!node_modules', '-g', '!*.lock', '-g', '!package-lock.json',
                        '-o', '--max-columns', '0', '-e', rx.replace('(?i)', ''), '-i' if rx.startswith('(?i)') else '-s', repo], capture_output=True, text=True, errors='replace')
    for line in p.stdout.splitlines():
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        f, n, val = parts
        found = []
        scan_line(val, lambda r, v: found.append((r, v)))
        for r, v in found:
            hits.append({'where': f.replace(repo + '/', ''), 'line': int(n) if n.isdigit() else n, 'rule': r, 'value': mask(v)})
res['passes']['tree'] = {'hits': hits}

# the ignored secrets file, by name only
dv = subprocess.run(['git', '-C', repo, 'ls-files', '--others', '--ignored', '--exclude-standard', '--', 'site/api/.dev.vars', 'site/.dev.vars', '.env'], capture_output=True, text=True).stdout.split()
res['ignored_env_files'] = []
for f in dv:
    names = []
    for line in open(f'{repo}/{f}', encoding='utf8', errors='replace'):
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            names.append({'name': k.strip(), 'value_length': len(v.strip().strip('"'))})
    tracked = subprocess.run(['git', '-C', repo, 'log', '--all', '--oneline', '--', f], capture_output=True, text=True).stdout.strip()
    res['ignored_env_files'].append({'file': f, 'ignored_by_git': True, 'ever_committed': bool(tracked), 'variables': names})

# 3. the history: every unique blob once
objs = subprocess.run(['git', '-C', repo, 'rev-list', '--all', '--objects'], capture_output=True, text=True).stdout.splitlines()
path_of = {}
for o in objs:
    sha, _, path = o.partition(' ')
    if path and sha not in path_of:
        path_of[sha] = path
SKIP = ('.png', '.jpg', '.jpeg', '.webp', '.avif', '.gif', '.exr', '.blend', '.mp4', '.webm', '.woff', '.woff2', '.ttf', '.zip', '.gz', '.pdf', '.ico', '.glb', '.hdr', '.npy', '.npz', '.psd', '.tif', '.tiff', '.mov', '.wasm', '.bin', 'package-lock.json')
cand = [s for s, p in path_of.items() if not p.lower().endswith(SKIP)]
types = subprocess.run(['git', '-C', repo, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], input='\n'.join(cand) + '\n', capture_output=True, text=True).stdout.splitlines()
blobs = [t.split()[0] for t in types if len(t.split()) == 3 and t.split()[1] == 'blob' and int(t.split()[2]) < 8_000_000]
hits = []
proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for sha in blobs:
    proc.stdin.write((sha + '\n').encode())
    proc.stdin.flush()
    header = proc.stdout.readline().split()
    size = int(header[2])
    data = proc.stdout.read(size)
    proc.stdout.read(1)
    if b'\0' in data[:8000]:
        continue
    text = data.decode('utf8', 'replace')
    for n, line in enumerate(text.splitlines(), 1):
        scan_line(line, lambda r, v: hits.append({'blob': sha[:10], 'where': path_of[sha], 'line': n, 'rule': r, 'value': mask(v)}))
proc.stdin.close()
proc.wait()
res['passes']['history'] = {'unique_text_blobs': len(blobs), 'hits': hits}
# 2. the commit: the history's hits whose blob is in the commit's tree
tree = {}
for line in subprocess.run(['git', '-C', repo, 'ls-tree', '-r', commit], capture_output=True, text=True).stdout.splitlines():
    meta, path = line.split('\t', 1)
    tree.setdefault(meta.split()[2][:10], []).append(path)
res['passes']['commit'] = {'tracked_files': sum(len(v) for v in tree.values()), 'hits': [dict(h, where=p) for h in hits if h['blob'] in tree for p in tree[h['blob']]]}

json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
for k, v in res['passes'].items():
    print(k, {x: y for x, y in v.items() if x != 'hits'}, 'hits', len(v['hits']))
    seen = set()
    for h in v['hits']:
        key = (h['where'], h['rule'])
        if key in seen:
            continue
        seen.add(key)
        print('   ', h)
print('ignored env files', json.dumps(res['ignored_env_files'], ensure_ascii=False))
