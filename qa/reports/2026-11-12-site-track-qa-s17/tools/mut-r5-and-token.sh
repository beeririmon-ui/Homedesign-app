#!/bin/bash
# In the public copy, after build-public.sh (dummy token): web rebuilds only, each followed by the checks it concerns, then
# the clean public build with the dummy token is rebuilt last (the one that is served).
#   R5        the public build reads the full supplier manifest (the vite alias removed) → check:rights (and my scan)
#   T-none    HD_PUBLIC=1 without CF_ANALYTICS_TOKEN → beacons in dist
#   T-flag    behind the flag (no HD_PUBLIC) WITH a dummy token → beacons in dist
#   T-bad     HD_PUBLIC=1 with tokens of the wrong shape → the build's exit and message; T-upper: upper-case hex
source "$(dirname "$0")/noNet.sh"
QA=$(cd "$(dirname "$0")/.." && pwd)
cd "$QA/build-s17-pub/site"
T=$QA/s17-tmp; D=$QA/s17-data
GOOD=a17a17a17a17a17a17a17a17a17a17a1
beacons() { echo "beacon tags in dist: $(grep -rl --include=*.html 'static.cloudflareinsights.com/beacon.min.js' web/dist | wc -l) of $(find web/dist -name '*.html' | wc -l) html files"; }
web() { npm run build -w @hd/web > "$T/web-build.log" 2>&1; local e=$?; grep -E "prerendered|prerender:|analytics" "$T/web-build.log" | head -3; echo "web build exit $e"; return $e; }
echo "=== R5 the public build reads the full supplier manifest (the alias removed), rebuilt"
cp web/vite.config.ts "$T/vite.config.ts.bak"
sed -i 's#...(PUBLIC ? \[{ find: /^@generated\\/supplier-images\\.json$/, replacement: PUBLIC_SUPPLIER }\] : \[\]),#// QA R5: alias removed#' web/vite.config.ts
grep -c "QA R5" web/vite.config.ts
HD_PUBLIC=1 CF_ANALYTICS_TOKEN=$GOOD web
HD_PUBLIC=1 npx --no-install tsx tools/check-image-rights.ts --json="$D/rights-r5.json" > "$T/r5.log" 2>&1; echo "check:rights exit $?"; grep -E "by content|issues|would ship|names products" "$T/r5.log" | head -3 | cut -c1-260
NODE_PATH=$PWD/node_modules node "$QA/s17-tools/rights-scan.mjs" web/dist "$QA/build-s17/site/web/public/media/products" .cache/supplier-images ../data/products "$D/qa-scan-r5.json" | head -1
cp "$T/vite.config.ts.bak" web/vite.config.ts; cmp -s web/vite.config.ts "$QA/build-s17/site/web/vite.config.ts" && echo "vite.config.ts restored, identical to the clean copy"
echo "=== T-none: HD_PUBLIC=1, no token"; HD_PUBLIC=1 CF_ANALYTICS_TOKEN= web; beacons
echo "=== T-flag: behind the flag, with the dummy token"; CF_ANALYTICS_TOKEN=$GOOD web; beacons
for bad in "a17a17a17a17a17a17a17a17a17a17a" "a17a17a17a17a17a17a17a17a17a17a17" "g17a17a17a17a17a17a17a17a17a17a1" "a17a17a17a17a17a17a17a17a17a17a1'><script>alert(1)</script>" "a17a17a17a17a17a17a17a17a17a17a1;"; do
  echo "=== T-bad: '${bad:0:40}' (${#bad} chars)"; HD_PUBLIC=1 CF_ANALYTICS_TOKEN="$bad" web
done
echo "=== T-upper: upper-case hex, with spaces around"; HD_PUBLIC=1 CF_ANALYTICS_TOKEN="  A17A17A17A17A17A17A17A17A17A17A1 " web; beacons; grep -oh "data-cf-beacon='[^']*'" web/dist/index.html | head -1
echo "=== the clean public build with the dummy token, rebuilt (web, then the API build, the budget, check:rights)"
HD_PUBLIC=1 CF_ANALYTICS_TOKEN=$GOOD web; beacons
HD_PUBLIC=1 npm run build -w @hd/api > "$T/api-build.log" 2>&1; echo "api build exit $?"
HD_PUBLIC=1 npm run budget 2>&1 | tail -14
HD_PUBLIC=1 npx --no-install tsx tools/check-image-rights.ts --json="$D/rights-check-public.json" 2>&1 | tail -2 | cut -c1-400; echo "check:rights exit ${PIPESTATUS[0]}"
