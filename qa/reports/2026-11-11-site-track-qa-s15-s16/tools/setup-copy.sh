#!/bin/bash
# QA S15–S16 (2026-11-11): an isolated copy of commit 43cee016, outside the live tree.
# - git archive of site/, data/, status/, docs/, .github/ at 43cee016 (nothing read from the live working tree for these);
# - assets/manifest.json pinned from 43cee016; the other assets dirs linked read-only to the live tree (the build reads
#   assets/renders for the house layers and story frames; tracked files there equal 43cee016 at the start, render-agent
#   writes only untracked files under phase2-2026-11-10/work-r5);
# - qa/reports frozen as links to the entries that exist at the start of the round;
# - node_modules hard-linked from the S13–S14 copy (same package-lock.json: git diff a8104956 43cee016 is empty);
# - the supplier-image cache hard-linked from the S13–S14 copy (the build runs --offline, no network).
set -euo pipefail
COMMIT=43cee016
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
DST=$QA/build-s1516
OLD=$QA/build-s1314
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site data status docs .github | tar -x -C "$DST"
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
mkdir -p "$DST/qa/reports"
for e in "$REPO"/qa/reports/*; do ln -s "$e" "$DST/qa/reports/$(basename "$e")"; done
cp -al "$OLD/site/node_modules" "$DST/site/node_modules"
for w in api web; do [ -d "$OLD/site/$w/node_modules" ] && cp -al "$OLD/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I can stop my own servers without touching anyone else's
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1516.js.tmp"
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1112.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1314.js"
mv "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1516.js.tmp" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1516.js"
mkdir -p "$DST/site/.cache"
cp -al "$OLD/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
du -sh "$DST" 2>/dev/null | tail -1
