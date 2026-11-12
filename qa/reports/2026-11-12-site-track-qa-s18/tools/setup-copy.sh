#!/bin/bash
# QA S18 (2026-11-12): an isolated copy of commit 3013d630, outside the live tree (session scratchpad).
# - git archive of site/, data/, status/, docs/, .github/, qa/reports/2026-11-07-site-track/s18 at 3013d630;
# - assets/manifest.json pinned from 3013d630; the other assets dirs linked read-only to the live tree (the build reads
#   assets/renders; the tracked files it reads are checked against 3013d630 at the start and the end);
# - node_modules hard-linked from the live tree (clean at 3013d630 at the start; package-lock.json unchanged), read-only use;
# - the supplier-image cache hard-linked from the live tree (the build runs --offline, no network).
set -euo pipefail
COMMIT=3013d630
REPO=/home/user/homedesign-app
QA=$(cd "$(dirname "$0")/.." && pwd)
DST=$QA/build-s18
[ -e "$DST" ] && { echo "exists: $DST"; exit 1; }
mkdir -p "$DST"
git -C "$REPO" archive "$COMMIT" site data status docs .github qa/reports/2026-11-07-site-track/s18 | tar -x -C "$DST"
mkdir -p "$DST/assets"
git -C "$REPO" show "$COMMIT:assets/manifest.json" > "$DST/assets/manifest.json"
for d in blockout brand prompts qa renders review; do ln -s "$REPO/assets/$d" "$DST/assets/$d"; done
ln -s "$REPO/studio" "$DST/studio"
for e in "$REPO"/qa/reports/*; do b=$(basename "$e"); [ -e "$DST/qa/reports/$b" ] || ln -s "$e" "$DST/qa/reports/$b"; done
cp -al "$REPO/site/node_modules" "$DST/site/node_modules"
for w in api web; do [ -d "$REPO/site/$w/node_modules" ] && cp -al "$REPO/site/$w/node_modules" "$DST/site/$w/node_modules"; done
# a private name for this round's wrangler, so I can stop my own servers without touching anyone else's
cp "$DST/site/node_modules/wrangler/wrangler-dist/cli.js" "$DST/site/node_modules/wrangler/wrangler-dist/qasrv18.js"
mkdir -p "$DST/site/.cache"
cp -al "$REPO/site/.cache/supplier-images" "$DST/site/.cache/supplier-images"
echo "commit $COMMIT -> $DST"
