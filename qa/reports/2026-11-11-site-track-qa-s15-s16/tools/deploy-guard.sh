#!/bin/bash
# ה7: a direct `wrangler deploy` (no npm script) is stopped by check-config. Run in the public copy's site/api (not the copy
# the e2e server watches). Dry runs only: nothing leaves the machine. The mutation is reverted at the end (cp of the original).
cd "$(dirname "$0")/../build-s1516-pub/site/api"
export PATH=/opt/node22/bin:$PATH WRANGLER_SEND_METRICS=false NO_UPDATE_NOTIFIER=1
W="node ../node_modules/wrangler/bin/wrangler.js"
T=$(cd ../../../s1516-tmp && pwd)
cp wrangler.jsonc "$T/wrangler.orig.jsonc"
ORIG="$T/wrangler.orig.jsonc"
run() { echo "--- $1"; shift; "$@" > ../../deploy-run.log 2>&1; local e=$?; grep -E "custom build|check-config|provider settings would not run|production:|ERROR|✘|--dry-run: exiting|Total Upload|SUPPLIER_PROVIDER" ../../deploy-run.log | head -8; echo "exit $e"; }
# 0. the file as committed: a direct deploy of production passes the check
run "0. as committed: wrangler deploy --dry-run --env production" $W deploy --dry-run --env production --outdir $T/wd0
# 1. the mutation: production supplier "CJ" (a typo the check exists for)
python3 - <<'PY'
import re
s=open('wrangler.jsonc').read()
i=s.index('"production"'); j=s.index('"SUPPLIER_PROVIDER"', i)
k=s.index('"cj"', j)
s=s[:k]+'"CJ"'+s[k+4:]
open('wrangler.jsonc','w').write(s)
PY
grep -n '"CJ"' wrangler.jsonc | head -2
run "1. mutated (production SUPPLIER_PROVIDER CJ): wrangler deploy --dry-run --env production" $W deploy --dry-run --env production --outdir $T/wd1
run "2. mutated: wrangler versions upload --dry-run --env production" $W versions upload --dry-run --env production --outdir $T/wd2
( cd ../.. && run "3. mutated, from site/: wrangler deploy -c api/wrangler.jsonc --dry-run --env production" node node_modules/wrangler/bin/wrangler.js deploy -c api/wrangler.jsonc --dry-run --env production --outdir $T/wd3 )
( cd / && run "4. mutated, from / : wrangler deploy -c <abs> --dry-run --env production" node "$OLDPWD/../node_modules/wrangler/bin/wrangler.js" deploy -c "$OLDPWD/wrangler.jsonc" --dry-run --env production --outdir $T/wd4 )
cp "$ORIG" wrangler.jsonc
echo "restored: $(grep -c '"CJ"' wrangler.jsonc) CJ left"
# 5. the file as committed, the provider overridden on the command line
run "5. as committed, --var SUPPLIER_PROVIDER:CJ on the command line" $W deploy --dry-run --env production --var SUPPLIER_PROVIDER:CJ --outdir $T/wd5
grep -o '"SUPPLIER_PROVIDER[^,}]*' $T/wd5/*.js 2>/dev/null | head -2
rm -rf "$T"/wd*
