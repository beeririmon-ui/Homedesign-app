#!/bin/bash
# ת49: the deploy check from other folders, with no network (noNet.sh: every proxy-aware tool points at a closed port,
# npm offline). Dry runs only, in the public copy (not the copy the e2e server serves). Before and after: ~/.npm/_npx.
# The mutation (production SUPPLIER_PROVIDER "CJ") is reverted at the end from a copy of the original.
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
API=$QA/build-s17-pub/site/api
T=$QA/s17-tmp/deploy; rm -rf "$T"; mkdir -p "$T"
WJS=$QA/build-s17-pub/site/node_modules/wrangler/bin/wrangler.js
npx_state() { echo "~/.npm/_npx: $(ls -A ~/.npm/_npx 2>/dev/null | wc -l) entries"; }
run() { local name=$1 dir=$2; shift 2; echo "--- $name (cwd: ${dir/#$QA/<qa>})"; ( cd "$dir" && "$@" ) > "$T/run.log" 2>&1; local e=$?
  grep -E "custom build|check-config|provider settings would not run|production:|Cannot find module|ERR_MODULE|npm warn exec|will be installed|ERROR|✘|--dry-run: exiting|Total Upload|SUPPLIER_PROVIDER|ENOTFOUND|ECONNREFUSED|fetch failed" "$T/run.log" | sed "s#$QA#<qa>#g" | head -8; echo "exit $e"; }
npx_state
cp "$API/wrangler.jsonc" "$T/wrangler.orig.jsonc"
run "0. as committed, from site/api: wrangler deploy --dry-run --env production" "$API" node "$WJS" deploy --dry-run --env production --outdir "$T/wd0"
run "1. as committed, from site/: wrangler deploy -c api/wrangler.jsonc --dry-run --env production" "$API/.." node "$WJS" deploy -c api/wrangler.jsonc --dry-run --env production --outdir "$T/wd1"
run "2. as committed, from the copy's root: -c site/api/wrangler.jsonc" "$API/../.." node "$WJS" deploy -c site/api/wrangler.jsonc --dry-run --env production --outdir "$T/wd2"
run "3. as committed, from /: -c <abs>" / node "$WJS" deploy -c "$API/wrangler.jsonc" --dry-run --env production --outdir "$T/wd3"
run "4. as committed, from site/web (../node_modules/tsx exists there): -c ../api/wrangler.jsonc" "$API/../web" node "$WJS" deploy -c ../api/wrangler.jsonc --dry-run --env production --outdir "$T/wd4"
run "5. as committed, from site/tools: -c ../api/wrangler.jsonc" "$API/../tools" node "$WJS" deploy -c ../api/wrangler.jsonc --dry-run --env production --outdir "$T/wd5"
run "6. as committed, from site/api: wrangler versions upload --dry-run --env production" "$API" node "$WJS" versions upload --dry-run --env production --outdir "$T/wd6"
python3 -I - "$API/wrangler.jsonc" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read()
i=s.index('"production"'); j=s.index('"SUPPLIER_PROVIDER"', i); k=s.index('"cj"', j)
open(p,'w').write(s[:k]+'"CJ"'+s[k+4:])
PY
echo "mutated: $(grep -c '"CJ"' "$API/wrangler.jsonc") line with \"CJ\""
run "7. mutated (production SUPPLIER_PROVIDER CJ), from site/api: wrangler deploy --dry-run --env production" "$API" node "$WJS" deploy --dry-run --env production --outdir "$T/wd7"
run "8. mutated, from site/api: npm run deploy -w @hd/api -- --dry-run --env production (the runbook's way)" "$API/.." npm run deploy -w @hd/api -- --dry-run --env production --outdir "$T/wd8"
run "9. mutated, from /: -c <abs>" / node "$WJS" deploy -c "$API/wrangler.jsonc" --dry-run --env production --outdir "$T/wd9"
cp "$T/wrangler.orig.jsonc" "$API/wrangler.jsonc"
echo "restored: $(grep -c '"CJ"' "$API/wrangler.jsonc") CJ left; identical to the clean copy: $(cmp -s "$API/wrangler.jsonc" "$QA/build-s17/site/api/wrangler.jsonc" && echo yes || echo NO)"
run "10. as committed, --var SUPPLIER_PROVIDER:CJ on the command line (ת49b, the runbook's rule)" "$API" node "$WJS" deploy --dry-run --env production --var SUPPLIER_PROVIDER:CJ --outdir "$T/wd10"
grep -ho '"SUPPLIER_PROVIDER[^,}]*' "$T"/wd10/*.js 2>/dev/null | head -2
npx_state
rm -rf "$T"/wd*
