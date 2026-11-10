"""qa-agent 2026-11-10 (S8-S10): every hard-coded http(s) URL in the tracked files of site/ at a commit, by host and
file, with the code paths (src/) separated from tests and tools. Usage: python3 scan_urls.py <repo> <commit> <out.json>"""
import json, re, subprocess, sys
from collections import defaultdict
repo, commit, out = sys.argv[1:4]
files = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', commit, '--', 'site'], capture_output=True, text=True, check=True).stdout.split()
URL = re.compile(r"https?://([A-Za-z0-9.\-]+|\$\{[^}]+\}|\[[^\]]+\])(:\d+)?([^\s'\"`)<>]*)")
by_host = defaultdict(lambda: defaultdict(list))
for f in files:
    if f.endswith(('package-lock.json', '.png', '.jpg', '.webp', '.avif', '.woff2', '.ico')) or '/prototype/' in f:
        continue
    blob = subprocess.run(['git', '-C', repo, 'show', f'{commit}:{f}'], capture_output=True).stdout
    try:
        text = blob.decode('utf8')
    except UnicodeDecodeError:
        continue
    for n, line in enumerate(text.splitlines(), 1):
        for m in URL.finditer(line):
            by_host[m.group(1).lower()][f].append({'line': n, 'url': m.group(0)[:160]})
def kind(f):
    if '/test/' in f or f.endswith(('.test.ts', '.spec.ts')) or f.startswith('site/e2e/'): return 'test'
    if f.startswith('site/tools/') or f.endswith('README.md') or f.startswith('site/screens/'): return 'tool/doc'
    return 'code'
res = {h: {f: {'kind': kind(f), 'hits': v} for f, v in fs.items()} for h, fs in sorted(by_host.items())}
json.dump({'commit': commit, 'hosts': res}, open(out, 'w'), indent=1, ensure_ascii=False)
for h, fs in sorted(res.items()):
    kinds = sorted({x['kind'] for x in fs.values()})
    print(f"{h:45s} {','.join(kinds):18s} {', '.join(sorted(fs))[:150]}")
