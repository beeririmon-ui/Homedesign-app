#!/bin/bash
# QA S17 (2026-11-12): an isolated copy of commit a988b099, outside the live tree.
# - git archive of site/, data/, status/, docs/, .github/ at a988b099 (nothing read from the live working tree for these);
# - assets/manifest.json pinned from a988b099; the other assets dirs linked read-only to the live tree (the build reads
#   assets/renders for the house layers and story frames; render-agent writes only untracked files under
#   products/img1-pilot-2026-11-12 and phase2-2026-11-10 work dirs; the tracked files the build reads are checked
#   against a988b099 at the start and the end, see data/live-tree-*.txt);
# - qa/reports frozen as links to the entries that exist at the start of the round;
# - node_modules hard-linked from the S15–S16 copy (same package-lock.json: git diff 43cee016 a988b099 is empty);
# - the supplier-image cache hard-linked from the S15–S16 copy (the build runs --offline, no network).
set -euo pipefail
COMMIT=a988b099
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
DST=$QA/build-s17
OLD=$QA/build-s1516
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
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv17.js.tmp"
rm -f "$DST/site/node_modules/wrangler/wrangler-dist/qasrv1516.js"
mv "$DST/site/node_modules/wrangler/wrangler-dist/qasrv17.js.tmp" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv17.js"
mkdir -p "$DST/site/.cache"
cp -al "$OLD/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
du -sh "$DST" 2>/dev/null | tail -1
